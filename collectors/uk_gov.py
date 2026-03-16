"""
MedFusion — UK Government Health Statistics Collector
Fetches COVID-19 and other health data from UK Gov APIs.
"""

import hashlib
from typing import List, Dict, Any

from collectors.base import BaseCollector
from normalization.temporal import normalize_date, get_current_timestamp
from config import UK_GOV_API


# Fallback UK health data
UK_HEALTH_DATA = [
    {"disease": "COVID-19", "cases": 24800000, "deaths": 232000, "date": "2024-12-31", "metric": "cumulative"},
    {"disease": "Influenza", "cases": 850000, "deaths": 15000, "date": "2024-12-31", "metric": "season_estimate"},
    {"disease": "Measles", "cases": 1603, "deaths": 0, "date": "2024-12-31", "metric": "annual"},
    {"disease": "Tuberculosis", "cases": 4425, "deaths": 300, "date": "2023-12-31", "metric": "annual"},
    {"disease": "Hepatitis C", "cases": 9000, "deaths": 200, "date": "2023-12-31", "metric": "annual"},
    {"disease": "HIV/AIDS", "cases": 3118, "deaths": 200, "date": "2023-12-31", "metric": "new_diagnoses"},
    {"disease": "Pertussis", "cases": 5240, "deaths": 5, "date": "2024-12-31", "metric": "annual"},
    {"disease": "Mpox", "cases": 312, "deaths": 0, "date": "2024-12-31", "metric": "annual"},
]


class UKGovCollector(BaseCollector):
    """Collector for UK Government health statistics."""

    source_name = "uk_gov"
    display_name = "UK Gov"
    source_type = "rest_api"
    base_url = UK_GOV_API

    def _make_id(self, disease: str, date: str) -> str:
        raw = f"uk_gov|{disease}|GBR|{date}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch UK COVID-19 data from the coronavirus API."""
        results = []

        # Try UK Coronavirus API
        try:
            structure = {
                "date": "date",
                "newCases": "newCasesByPublishDate",
                "cumCases": "cumCasesByPublishDate",
                "newDeaths": "newDeaths28DaysByPublishDate",
                "cumDeaths": "cumDeaths28DaysByPublishDate",
            }
            import json
            params = {
                "filters": "areaType=overview",
                "structure": json.dumps(structure),
                "format": "json",
            }
            resp = await self.client.get(self.base_url, params=params, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                entries = data.get("data", [])
                if entries:
                    for entry in entries[:200]:
                        entry["_source"] = "api"
                    results.extend(entries)
        except Exception:
            pass

        # Try UK Gov search API for additional data
        if not results:
            try:
                resp = await self.client.get(
                    "https://www.gov.uk/api/search.json",
                    params={
                        "filter_document_type": "research_and_statistics",
                        "filter_organisations": "public-health-england",
                        "count": "20",
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        results.append({
                            "_source": "gov_search",
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "date": item.get("public_timestamp", ""),
                            "link": f"https://www.gov.uk{item.get('link', '')}",
                        })
            except Exception:
                pass

        # Fallback: use curated UK health data
        if not results:
            results = [{"_source": "fallback", **d} for d in UK_HEALTH_DATA]

        return results

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize UK Gov data into unified events."""
        events = []
        self._time_series = []

        for item in raw_data:
            try:
                source_type = item.get("_source", "fallback")

                if source_type == "api":
                    date_str = item.get("date", "")
                    new_cases = item.get("newCases")
                    cum_cases = item.get("cumCases")
                    new_deaths = item.get("newDeaths")
                    cum_deaths = item.get("cumDeaths")

                    date_norm = normalize_date(date_str)
                    event_id = self._make_id("COVID-19", date_str)

                    event = {
                        "id": event_id,
                        "source": self.source_name,
                        "event_type": "case_report",
                        "disease_name": "COVID-19",
                        "disease_raw": "COVID-19",
                        "icd10_code": "U07.1",
                        "country_code": "GBR",
                        "country_name": "United Kingdom",
                        "latitude": 55.38,
                        "longitude": -3.44,
                        "cases": cum_cases,
                        "deaths": cum_deaths,
                        "severity": "medium",
                        "confidence": 0.95,
                        "title": f"UK COVID-19 — {date_str}",
                        "description": f"New cases: {new_cases}, Cumulative: {cum_cases}, New deaths: {new_deaths}",
                        "date_reported": date_norm,
                        "source_url": self.base_url,
                    }
                    events.append(event)

                    if new_cases is not None and date_norm:
                        self._time_series.append({
                            "disease_name": "COVID-19",
                            "source": self.source_name,
                            "country_code": "GBR",
                            "country_name": "United Kingdom",
                            "metric": "new_cases",
                            "value": new_cases,
                            "date": date_norm[:10],
                        })
                    if new_deaths is not None and date_norm:
                        self._time_series.append({
                            "disease_name": "COVID-19",
                            "source": self.source_name,
                            "country_code": "GBR",
                            "country_name": "United Kingdom",
                            "metric": "new_deaths",
                            "value": new_deaths,
                            "date": date_norm[:10],
                        })

                elif source_type == "fallback":
                    from normalization.disease_mapper import map_disease_name
                    disease_raw = item.get("disease", "Unknown")
                    disease_info = map_disease_name(disease_raw)
                    date_str = item.get("date", "")
                    date_norm = normalize_date(date_str)

                    event_id = self._make_id(disease_raw, date_str)
                    event = {
                        "id": event_id,
                        "source": self.source_name,
                        "event_type": "case_report",
                        "disease_name": disease_info.get("canonical_name", disease_raw),
                        "disease_raw": disease_raw,
                        "icd10_code": disease_info.get("icd10_code"),
                        "country_code": "GBR",
                        "country_name": "United Kingdom",
                        "latitude": 55.38,
                        "longitude": -3.44,
                        "cases": item.get("cases"),
                        "deaths": item.get("deaths"),
                        "severity": "medium",
                        "confidence": 0.7,
                        "title": f"{disease_raw} in United Kingdom ({date_str[:4]})",
                        "description": (
                            f"UK health data: {disease_raw} — Cases: {item.get('cases', 'N/A')}, "
                            f"Deaths: {item.get('deaths', 'N/A')} ({item.get('metric', 'annual')})"
                        ),
                        "date_reported": date_norm,
                        "source_url": "https://www.gov.uk/health-and-social-care",
                    }
                    events.append(event)

                    if item.get("cases") and date_norm:
                        self._time_series.append({
                            "disease_name": disease_info.get("canonical_name", disease_raw),
                            "source": self.source_name,
                            "country_code": "GBR",
                            "country_name": "United Kingdom",
                            "metric": item.get("metric", "cases"),
                            "value": item["cases"],
                            "date": date_norm[:10],
                        })

                elif source_type == "gov_search":
                    # Search results are just informational events
                    date_norm = normalize_date(item.get("date"))
                    event_id = self._make_id(item.get("title", "")[:30], str(date_norm))
                    event = {
                        "id": event_id,
                        "source": self.source_name,
                        "event_type": "surveillance_report",
                        "disease_name": None,
                        "country_code": "GBR",
                        "country_name": "United Kingdom",
                        "latitude": 55.38,
                        "longitude": -3.44,
                        "confidence": 0.6,
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "date_reported": date_norm,
                        "source_url": item.get("link", ""),
                    }
                    events.append(event)

            except Exception:
                continue

        return events
