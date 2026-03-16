"""
MedFusion — Location Resolution Engine
Resolves country names, codes, and coordinates from various input formats.
"""

import json
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Load data files
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_json(filename: str) -> dict:
    """Load a JSON data file."""
    filepath = os.path.join(_DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load {filename}: {e}")
        return {}

COUNTRY_CODES = _load_json("country_codes.json")
COUNTRY_COORDS = _load_json("country_coords.json")

# Build reverse lookup: ISO3 code -> canonical country name
_ISO3_TO_NAME: Dict[str, str] = {}
for name, code in COUNTRY_CODES.items():
    if code not in _ISO3_TO_NAME:
        _ISO3_TO_NAME[code] = name.title()

# Common ISO2 to ISO3 mapping for the most common countries
_ISO2_TO_ISO3 = {
    "AF": "AFG", "AL": "ALB", "DZ": "DZA", "AD": "AND", "AO": "AGO",
    "AG": "ATG", "AR": "ARG", "AM": "ARM", "AU": "AUS", "AT": "AUT",
    "AZ": "AZE", "BS": "BHS", "BH": "BHR", "BD": "BGD", "BB": "BRB",
    "BY": "BLR", "BE": "BEL", "BZ": "BLZ", "BJ": "BEN", "BT": "BTN",
    "BO": "BOL", "BA": "BIH", "BW": "BWA", "BR": "BRA", "BN": "BRN",
    "BG": "BGR", "BF": "BFA", "BI": "BDI", "KH": "KHM", "CM": "CMR",
    "CA": "CAN", "CF": "CAF", "TD": "TCD", "CL": "CHL", "CN": "CHN",
    "CO": "COL", "KM": "COM", "CG": "COG", "CD": "COD", "CR": "CRI",
    "HR": "HRV", "CU": "CUB", "CY": "CYP", "CZ": "CZE", "DK": "DNK",
    "DJ": "DJI", "DM": "DMA", "DO": "DOM", "EC": "ECU", "EG": "EGY",
    "SV": "SLV", "GQ": "GNQ", "ER": "ERI", "EE": "EST", "SZ": "SWZ",
    "ET": "ETH", "FJ": "FJI", "FI": "FIN", "FR": "FRA", "GA": "GAB",
    "GM": "GMB", "GE": "GEO", "DE": "DEU", "GH": "GHA", "GR": "GRC",
    "GD": "GRD", "GT": "GTM", "GN": "GIN", "GW": "GNB", "GY": "GUY",
    "HT": "HTI", "HN": "HND", "HU": "HUN", "IS": "ISL", "IN": "IND",
    "ID": "IDN", "IR": "IRN", "IQ": "IRQ", "IE": "IRL", "IL": "ISR",
    "IT": "ITA", "CI": "CIV", "JM": "JAM", "JP": "JPN", "JO": "JOR",
    "KZ": "KAZ", "KE": "KEN", "KI": "KIR", "KP": "PRK", "KR": "KOR",
    "KW": "KWT", "KG": "KGZ", "LA": "LAO", "LV": "LVA", "LB": "LBN",
    "LS": "LSO", "LR": "LBR", "LY": "LBY", "LI": "LIE", "LT": "LTU",
    "LU": "LUX", "MG": "MDG", "MW": "MWI", "MY": "MYS", "MV": "MDV",
    "ML": "MLI", "MT": "MLT", "MH": "MHL", "MR": "MRT", "MU": "MUS",
    "MX": "MEX", "FM": "FSM", "MD": "MDA", "MC": "MCO", "MN": "MNG",
    "ME": "MNE", "MA": "MAR", "MZ": "MOZ", "MM": "MMR", "NA": "NAM",
    "NR": "NRU", "NP": "NPL", "NL": "NLD", "NZ": "NZL", "NI": "NIC",
    "NE": "NER", "NG": "NGA", "MK": "MKD", "NO": "NOR", "OM": "OMN",
    "PK": "PAK", "PW": "PLW", "PS": "PSE", "PA": "PAN", "PG": "PNG",
    "PY": "PRY", "PE": "PER", "PH": "PHL", "PL": "POL", "PT": "PRT",
    "QA": "QAT", "RO": "ROU", "RU": "RUS", "RW": "RWA", "KN": "KNA",
    "LC": "LCA", "VC": "VCT", "WS": "WSM", "SM": "SMR", "ST": "STP",
    "SA": "SAU", "SN": "SEN", "RS": "SRB", "SC": "SYC", "SL": "SLE",
    "SG": "SGP", "SK": "SVK", "SI": "SVN", "SB": "SLB", "SO": "SOM",
    "ZA": "ZAF", "SS": "SSD", "ES": "ESP", "LK": "LKA", "SD": "SDN",
    "SR": "SUR", "SE": "SWE", "CH": "CHE", "SY": "SYR", "TW": "TWN",
    "TJ": "TJK", "TZ": "TZA", "TH": "THA", "TL": "TLS", "TG": "TGO",
    "TO": "TON", "TT": "TTO", "TN": "TUN", "TR": "TUR", "TM": "TKM",
    "TV": "TUV", "UG": "UGA", "UA": "UKR", "AE": "ARE", "GB": "GBR",
    "US": "USA", "UY": "URY", "UZ": "UZB", "VU": "VUT", "VA": "VAT",
    "VE": "VEN", "VN": "VNM", "YE": "YEM", "ZM": "ZMB", "ZW": "ZWE",
    "HK": "HKG", "MO": "MAC", "PR": "PRI", "GU": "GUM",
}


def resolve_country(raw_input: str) -> Dict[str, Optional[any]]:
    """
    Resolve a country name, ISO-2 code, or ISO-3 code to full country information.
    
    Args:
        raw_input: Country name, ISO-2 code, or ISO-3 code
        
    Returns:
        Dict with country_code (ISO3), country_name, latitude, longitude
    """
    if not raw_input:
        return {"country_code": None, "country_name": None, "latitude": None, "longitude": None}

    cleaned = raw_input.strip()

    # Check if already an ISO-3 code
    if len(cleaned) == 3 and cleaned.upper() in COUNTRY_COORDS:
        iso3 = cleaned.upper()
        coords = COUNTRY_COORDS.get(iso3, {})
        return {
            "country_code": iso3,
            "country_name": _ISO3_TO_NAME.get(iso3, iso3),
            "latitude": coords.get("lat"),
            "longitude": coords.get("lon"),
        }

    # Check if ISO-2 code
    if len(cleaned) == 2 and cleaned.upper() in _ISO2_TO_ISO3:
        iso3 = _ISO2_TO_ISO3[cleaned.upper()]
        coords = COUNTRY_COORDS.get(iso3, {})
        return {
            "country_code": iso3,
            "country_name": _ISO3_TO_NAME.get(iso3, iso3),
            "latitude": coords.get("lat"),
            "longitude": coords.get("lon"),
        }

    # Check country name lookup
    lower = cleaned.lower()
    if lower in COUNTRY_CODES:
        iso3 = COUNTRY_CODES[lower]
        coords = COUNTRY_COORDS.get(iso3, {})
        return {
            "country_code": iso3,
            "country_name": cleaned.title(),
            "latitude": coords.get("lat"),
            "longitude": coords.get("lon"),
        }

    # Fuzzy: check if any known country name is a substring
    for name, code in COUNTRY_CODES.items():
        if name in lower or lower in name:
            coords = COUNTRY_COORDS.get(code, {})
            return {
                "country_code": code,
                "country_name": name.title(),
                "latitude": coords.get("lat"),
                "longitude": coords.get("lon"),
            }

    logger.debug(f"Could not resolve country: {raw_input}")
    return {"country_code": None, "country_name": cleaned, "latitude": None, "longitude": None}


def get_country_name(iso3_code: str) -> str:
    """Get the country name for an ISO-3 code."""
    return _ISO3_TO_NAME.get(iso3_code, iso3_code)


def get_country_coords(iso3_code: str) -> Optional[Dict[str, float]]:
    """Get lat/lon coordinates for an ISO-3 code."""
    return COUNTRY_COORDS.get(iso3_code)
