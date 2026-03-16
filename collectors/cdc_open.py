"""
MedFusion — CDC Open Data (Socrata API) Collector
Fetches public health data from CDC's Open Data Portal.
"""

import hashlib
from typing import List, Dict, Any

from collectors.base import BaseCollector
from normalization.disease_mapper import map_disease_name
from normalization.temporal import normalize_date, get_current_timestamp
from config import CDC_OPEN_DATA_BASE, CDC_DATASETS


class CDCOpenCollector(BaseCollector):
    """Collector for CDC Open Data Portal via Socrata API."""

    source_name = "cdc_open"
    display_name = "CDC Open Data"
    source_type = "socrata_api"
    base_url = CDC_OPEN_DATA_BASE

    def _make_id(self, dataset: str, key: str) -> str:
        raw = f"cdc_open|{dataset}|{key}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch data from CDC Socrata datasets."""
        all_data = []

        # Try NNDSS weekly tables
        try:
            url = f"{self.base_url}/{CDC_DATASETS['nndss']}.json"
            resp = await self.client.get(url, params={
                "$limit": "2000",
                "$order": "mmwr_year DESC",
            })
            resp.raise_for_status()
            data = resp.json()
            for item in data:
                item["_dataset"] = "nndss"
            all_data.extend(data)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"CDC NNDSS fetch failed: {e}")

        # Try alternative COVID dataset if NNDSS fails or is small
        if len(all_data) < 100:
            try:
                url = f"{self.base_url}/9mfq-cb36.json"
                resp = await self.client.get(url, params={
                    "$limit": "2000",
                    "$order": "submission_date DESC",
                })
                resp.raise_for_status()
                data = resp.json()
                for item in data:
                    item["_dataset"] = "covid_state"
                all_data.extend(data)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"CDC COVID state data failed: {e}")

        return all_data

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize CDC data into unified events."""
        events = []
        self._time_series = []

        for item in raw_data:
            try:
                dataset = item.get("_dataset", "unknown")

                if dataset == "nndss":
                    disease_raw = item.get("label", item.get("disease", item.get("current_week_flag", "")))
                    if not disease_raw:
                        continue

                    disease_info = map_disease_name(disease_raw)
                    mmwr_year = item.get("mmwr_year", "")
                    mmwr_week = item.get("mmwr_week", "")
                    state = item.get("reporting_area", item.get("states", ""))

                    current_week = item.get("current_week")
                    cum_ytd = item.get("cum_2024", item.get("cum_2023", item.get("cumulative_ytd")))

                    try:
                        cases = int(current_week) if current_week and str(current_week).strip() not in ("-", "N", "U", "NN", "") else None
                    except (ValueError, TypeError):
                        cases = None

                    date_str = normalize_date(f"Week {mmwr_week}, {mmwr_year}") if mmwr_year and mmwr_week else None

                    event_id = self._make_id("nndss", f"{disease_raw}|{state}|{mmwr_year}|{mmwr_week}")

                    event = {
                        "id": event_id,
                        "source": self.source_name,
                        "event_type": "case_report",
                        "disease_name": disease_info.get("canonical_name"),
                        "disease_raw": disease_raw,
                        "icd10_code": disease_info.get("icd10_code"),
                        "country_code": "USA",
                        "country_name": "United States",
                        "region": state,
                        "latitude": 37.09,
                        "longitude": -95.71,
                        "cases": cases,
                        "severity": "medium",
                        "confidence": 0.9,
                        "title": f"{disease_raw} — {state} (MMWR Week {mmwr_week}, {mmwr_year})",
                        "description": f"NNDSS: {disease_raw} current week: {current_week}, cumulative YTD: {cum_ytd}",
                        "date_reported": date_str,
                        "source_url": f"https://data.cdc.gov/resource/{CDC_DATASETS['nndss']}",
                    }
                    events.append(event)

                    if cases is not None and date_str:
                        self._time_series.append({
                            "disease_name": disease_info.get("canonical_name"),
                            "source": self.source_name,
                            "country_code": "USA",
                            "country_name": "United States",
                            "region": state,
                            "metric": "weekly_cases",
                            "value": cases,
                            "date": date_str[:10],
                        })

                elif dataset == "covid_state":
                    state = item.get("state", "")
                    date = item.get("submission_date", "")
                    new_cases = item.get("new_case", item.get("tot_cases"))
                    new_deaths = item.get("new_death", item.get("tot_death"))

                    try:
                        cases_val = int(float(new_cases)) if new_cases else None
                    except (ValueError, TypeError):
                        cases_val = None
                    try:
                        deaths_val = int(float(new_deaths)) if new_deaths else None
                    except (ValueError, TypeError):
                        deaths_val = None

                    date_norm = normalize_date(date)
                    event_id = self._make_id("covid_state", f"{state}|{date}")

                    event = {
                        "id": event_id,
                        "source": self.source_name,
                        "event_type": "case_report",
                        "disease_name": "COVID-19",
                        "disease_raw": "COVID-19",
                        "icd10_code": "U07.1",
                        "country_code": "USA",
                        "country_name": "United States",
                        "region": state,
                        "latitude": 37.09,
                        "longitude": -95.71,
                        "cases": cases_val,
                        "deaths": deaths_val,
                        "severity": "medium",
                        "confidence": 0.95,
                        "title": f"COVID-19 — {state}",
                        "description": f"Cases: {cases_val}, Deaths: {deaths_val}",
                        "date_reported": date_norm,
                        "source_url": "https://data.cdc.gov/resource/9mfq-cb36",
                    }
                    events.append(event)

                    if cases_val is not None and date_norm:
                        self._time_series.append({
                            "disease_name": "COVID-19",
                            "source": self.source_name,
                            "country_code": "USA",
                            "country_name": "United States",
                            "region": state,
                            "metric": "cases",
                            "value": cases_val,
                            "date": date_norm[:10],
                        })
            except Exception:
                continue

        return events
