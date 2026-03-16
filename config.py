"""
MedFusion — Application Configuration
Contains all API endpoints, intervals, and settings.
"""

# App settings
APP_NAME = "MedFusion"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Unified Disease Surveillance Intelligence Platform"
DATABASE_PATH = "medfusion.db"
HOST = "0.0.0.0"
PORT = 8000

# Data refresh intervals (in minutes)
REFRESH_INTERVAL_FAST = 15       # Disease.sh, alerts
REFRESH_INTERVAL_MEDIUM = 60     # WHO, CDC, ECDC
REFRESH_INTERVAL_SLOW = 360      # IHME, UK Gov (static/slow-updating)

# Source API endpoints
DISEASE_SH_BASE = "https://disease.sh/v3"
WHO_GHO_BASE = "https://ghoapi.azureedge.net/api"
CDC_OPEN_DATA_BASE = "https://data.cdc.gov/resource"
CDC_FLUVIEW_RSS = "https://www.cdc.gov/flu/weekly/flureport.xml"
PROMED_RSS = "https://promedmail.org/feed/"
HEALTHMAP_BASE = "https://www.healthmap.org/en/"
ECDC_BASE = "https://opendata.ecdc.europa.eu/covid19"
IHME_GHDX_BASE = "https://ghdx.healthdata.org"
UK_GOV_API = "https://api.coronavirus.data.gov.uk/v1/data"

# CDC Open Data dataset IDs (Socrata)
CDC_DATASETS = {
    "covid_cases": "pwn4-m3yp",
    "nndss": "x9gk-5huc",
    "wonder_mortality": "bi63-dtpu",
}

# WHO GHO Indicators
WHO_INDICATORS = [
    "MALARIA001",           # Malaria cases
    "TB_e_inc_num",         # TB incidence
    "CHOLERA_0000000001",   # Cholera cases
    "WHS3_49",              # HIV prevalence
    "MEAS_INCCOUNTRY",      # Measles cases
]

# Open Targets API (for gene-disease associations)
OPEN_TARGETS_API = "https://api.platform.opentargets.org/api/v4"

# PubChem API (for drug information)
PUBCHEM_API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
