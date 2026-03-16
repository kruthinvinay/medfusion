"""
MedFusion — WHO Global Health Observatory (GHO) OData API Collector
Fetches disease indicators from the WHO GHO API.
"""

import hashlib
from typing import List, Dict, Any

from collectors.base import BaseCollector
from normalization.disease_mapper import map_disease_name
from normalization.location_resolver import resolve_country
from normalization.temporal import normalize_date
from config import WHO_GHO_BASE, WHO_INDICATORS


# Map WHO indicator codes to disease names
INDICATOR_DISEASE_MAP = {
    "MALARIA001": "Malaria",
    "TB_e_inc_num": "Tuberculosis",
    "CHOLERA_0000000001": "Cholera",
    "WHS3_49": "HIV/AIDS",
    "MEAS_INCCOUNTRY": "Measles",
    "NCD_BMI_30A": "Obesity",
}

INDICATOR_METRIC_MAP = {
    "MALARIA001": "estimated_cases",
    "TB_e_inc_num": "estimated_incidence",
    "CHOLERA_0000000001": "reported_cases",
    "WHS3_49": "prevalence",
    "MEAS_INCCOUNTRY": "reported_cases",
    "NCD_BMI_30A": "prevalence",
}


class WHOGHOCollector(BaseCollector):
    """Collector for WHO Global Health Observatory OData API."""

    source_name = "who_gho"
    display_name = "WHO GHO API"
    source_type = "odata_api"
    base_url = WHO_GHO_BASE

    def _make_id(self, indicator: str, country: str, year: str) -> str:
        raw = f"who_gho|{indicator}|{country}|{year}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch data for each WHO indicator."""
        all_data = []
        for indicator in WHO_INDICATORS:
            try:
                url = f"{self.base_url}/{indicator}"
                params = {"$filter": "TimeDim ge 2018", "$top": "500"}
                resp = await self.client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                values = data.get("value", [])
                for v in values:
                    v["_indicator"] = indicator
                all_data.extend(values)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"WHO indicator {indicator} failed: {e}")
                continue
        return all_data

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize WHO GHO data into unified events."""
        events = []
        self._time_series = []

        for item in raw_data:
            try:
                indicator = item.get("_indicator", "")
                disease_name = INDICATOR_DISEASE_MAP.get(indicator, indicator)
                metric = INDICATOR_METRIC_MAP.get(indicator, "value")
                
                country_code = item.get("SpatialDim", "")
                if not country_code or len(country_code) != 3:
                    continue

                year = item.get("TimeDim")
                value = item.get("NumericValue")
                if value is None:
                    continue

                loc = resolve_country(country_code)
                disease_info = map_disease_name(disease_name)
                date_str = f"{year}-01-01T00:00:00Z" if year else None

                event = {
                    "id": self._make_id(indicator, country_code, str(year)),
                    "source": self.source_name,
                    "event_type": "indicator",
                    "disease_name": disease_info.get("canonical_name", disease_name),
                    "disease_raw": indicator,
                    "icd10_code": disease_info.get("icd10_code"),
                    "country_code": country_code,
                    "country_name": loc.get("country_name"),
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "cases": int(value) if metric in ("estimated_cases", "reported_cases", "estimated_incidence") else None,
                    "prevalence": value if metric == "prevalence" else None,
                    "severity": "medium",
                    "confidence": 0.85,
                    "title": f"{disease_name} in {loc.get('country_name', country_code)} ({year})",
                    "description": f"WHO {indicator}: {value:,.0f} ({metric})",
                    "date_reported": date_str,
                    "date_event": date_str,
                    "source_url": f"{self.base_url}/{indicator}",
                }
                events.append(event)

                # Time series
                self._time_series.append({
                    "disease_name": disease_info.get("canonical_name", disease_name),
                    "source": self.source_name,
                    "country_code": country_code,
                    "country_name": loc.get("country_name"),
                    "metric": metric,
                    "value": value,
                    "date": f"{year}-01-01" if year else None,
                })
            except Exception:
                continue

        return events
