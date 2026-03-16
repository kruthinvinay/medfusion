"""
MedFusion — Disease.sh REST API Collector
Fetches real-time COVID-19 data from disease.sh API.
"""

import hashlib
from typing import List, Dict, Any
from datetime import datetime, timezone

from collectors.base import BaseCollector
from normalization.location_resolver import resolve_country, get_country_name
from normalization.temporal import get_current_timestamp
from config import DISEASE_SH_BASE


class DiseaseSHCollector(BaseCollector):
    """Collector for Disease.sh COVID-19 REST API."""

    source_name = "disease_sh"
    display_name = "Disease.sh API"
    source_type = "rest_api"
    base_url = DISEASE_SH_BASE

    def _make_id(self, country_code: str, date: str) -> str:
        """Generate deterministic ID for deduplication."""
        raw = f"disease_sh|COVID-19|{country_code}|{date}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _classify_severity(self, active_per_million: float) -> str:
        """Classify severity based on active cases per million."""
        if active_per_million > 10000:
            return "critical"
        elif active_per_million > 5000:
            return "high"
        elif active_per_million > 1000:
            return "medium"
        return "low"

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch COVID-19 country data and historical data from disease.sh."""
        results = []

        # Fetch current country-level data
        resp = await self.client.get(f"{self.base_url}/covid-19/countries")
        resp.raise_for_status()
        countries = resp.json()
        results.append({"type": "countries", "data": countries})

        # Fetch historical data (last 30 days to keep it manageable)
        try:
            hist_resp = await self.client.get(
                f"{self.base_url}/covid-19/historical",
                params={"lastdays": "30"}
            )
            hist_resp.raise_for_status()
            historical = hist_resp.json()
            results.append({"type": "historical", "data": historical})
        except Exception:
            pass  # Historical endpoint may fail; not critical

        return results

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize disease.sh data into unified events and time series."""
        events = []
        self._time_series = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now = get_current_timestamp()

        for batch in raw_data:
            if batch["type"] == "countries":
                for c in batch["data"]:
                    try:
                        info = c.get("countryInfo", {})
                        iso3 = info.get("iso3")
                        if not iso3:
                            continue

                        pop = c.get("population", 1)
                        active_per_m = (c.get("activePerOneMillion", 0) or 0)

                        event = {
                            "id": self._make_id(iso3, today),
                            "source": self.source_name,
                            "event_type": "case_report",
                            "disease_name": "COVID-19",
                            "disease_raw": "COVID-19",
                            "icd10_code": "U07.1",
                            "country_code": iso3,
                            "country_name": c.get("country", get_country_name(iso3)),
                            "region": c.get("continent"),
                            "latitude": info.get("lat"),
                            "longitude": info.get("long"),
                            "cases": c.get("cases"),
                            "deaths": c.get("deaths"),
                            "recovered": c.get("recovered"),
                            "incidence_rate": c.get("casesPerOneMillion"),
                            "severity": self._classify_severity(active_per_m),
                            "confidence": 0.9,
                            "title": f"COVID-19 in {c.get('country', iso3)}",
                            "description": (
                                f"Cases: {c.get('cases', 0):,} | Deaths: {c.get('deaths', 0):,} | "
                                f"Active: {c.get('active', 0):,} | Recovered: {c.get('recovered', 0):,}"
                            ),
                            "date_reported": now,
                            "date_event": now,
                            "source_url": "https://disease.sh/v3/covid-19/countries",
                            "raw_data": {
                                "todayCases": c.get("todayCases"),
                                "todayDeaths": c.get("todayDeaths"),
                                "active": c.get("active"),
                                "critical": c.get("critical"),
                                "tests": c.get("tests"),
                            }
                        }
                        events.append(event)

                        # Time series for today
                        self._time_series.append({
                            "disease_name": "COVID-19",
                            "source": self.source_name,
                            "country_code": iso3,
                            "country_name": c.get("country"),
                            "metric": "cases",
                            "value": c.get("cases", 0),
                            "date": today,
                        })
                        if c.get("deaths"):
                            self._time_series.append({
                                "disease_name": "COVID-19",
                                "source": self.source_name,
                                "country_code": iso3,
                                "country_name": c.get("country"),
                                "metric": "deaths",
                                "value": c.get("deaths", 0),
                                "date": today,
                            })
                    except Exception:
                        continue

            elif batch["type"] == "historical":
                for entry in batch.get("data", []):
                    try:
                        country = entry.get("country", "")
                        province = entry.get("province")
                        if province:
                            continue  # Skip provinces, just use country-level

                        timeline = entry.get("timeline", {})
                        cases_tl = timeline.get("cases", {})
                        deaths_tl = timeline.get("deaths", {})

                        loc = resolve_country(country)
                        iso3 = loc.get("country_code")
                        if not iso3:
                            continue

                        for date_str, val in cases_tl.items():
                            try:
                                # disease.sh dates are M/D/YY
                                dt = datetime.strptime(date_str, "%m/%d/%y")
                                iso_date = dt.strftime("%Y-%m-%d")
                                self._time_series.append({
                                    "disease_name": "COVID-19",
                                    "source": self.source_name,
                                    "country_code": iso3,
                                    "country_name": loc.get("country_name"),
                                    "metric": "cumulative_cases",
                                    "value": val,
                                    "date": iso_date,
                                })
                            except Exception:
                                continue

                        for date_str, val in deaths_tl.items():
                            try:
                                dt = datetime.strptime(date_str, "%m/%d/%y")
                                iso_date = dt.strftime("%Y-%m-%d")
                                self._time_series.append({
                                    "disease_name": "COVID-19",
                                    "source": self.source_name,
                                    "country_code": iso3,
                                    "country_name": loc.get("country_name"),
                                    "metric": "cumulative_deaths",
                                    "value": val,
                                    "date": iso_date,
                                })
                            except Exception:
                                continue
                    except Exception:
                        continue

        return events
