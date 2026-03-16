# 🏥 MedFusion — Disease Surveillance Intelligence Platform

A unified **FastAPI backend** that ingests real-time data from **9 public health surveillance sources**, normalizes it into a common schema, stores it in SQLite, runs analytics (anomaly detection, trend analysis, risk scoring), and serves everything through a clean REST API.

Built for **MedFusion Hackfest 2026** 🧬

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
# Open http://localhost:8000/docs
```

On startup, MedFusion automatically:
1. Creates the SQLite database with 7 tables
2. Connects to all 9 data sources concurrently
3. Normalizes and deduplicates all records
4. Loads 29 gene + 30 drug associations
5. Schedules auto-refresh every 15 minutes

## 📊 Data Sources (9)

| # | Source | Type | URL | Data |
|---|--------|------|-----|------|
| 1 | **Disease.sh** | REST API | `disease.sh/v3` | Real-time COVID-19 for 200+ countries |
| 2 | **WHO GHO** | OData API | `ghoapi.azureedge.net` | Malaria, TB, Cholera, HIV, Measles indicators |
| 3 | **CDC Open Data** | Socrata API | `data.cdc.gov` | US NNDSS weekly surveillance tables |
| 4 | **CDC FluView** | RSS Feed | `cdc.gov/flu` | US influenza surveillance reports |
| 5 | **ProMED Mail** | RSS Feed | `promedmail.org` | Global outbreak alerts |
| 6 | **HealthMap** | Web Scraper | `healthmap.org` | Outbreak monitoring with fallback |
| 7 | **IHME GHDx** | Curated | `ghdx.healthdata.org` | India disease burden (GBD estimates) |
| 8 | **ECDC** | REST API | `opendata.ecdc.europa.eu` | European COVID-19 data |
| 9 | **UK Gov** | REST API | `api.coronavirus.data.gov.uk` | UK health statistics |

### How APIs Were Obtained

All data sources are **publicly accessible** — no API keys required:

- **Disease.sh** — Open-source community API for COVID-19 data, freely available at `https://disease.sh`
- **WHO GHO** — World Health Organization's public OData API for global health indicators
- **CDC Open Data / FluView** — US Centers for Disease Control public datasets via Socrata and RSS
- **ProMED / HealthMap** — Public outbreak monitoring feeds (RSS/web scraping)
- **IHME GHDx** — Published GBD research estimates (pre-structured from peer-reviewed data)
- **ECDC** — European Centre for Disease Prevention and Control open data portal
- **UK Gov** — UK Government open coronavirus data API

Each collector has **multiple fallback strategies** (API → scrape → curated data) to ensure the demo always works, even if a source is temporarily unavailable.

## 🛠️ API Endpoints (17)

### 🏥 Surveillance
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/surveillance/query` | Multi-source query with filters (disease, country, date, source) |
| GET | `/api/v1/surveillance/summary` | Dashboard summary statistics |

### 🦠 Diseases
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/diseases` | List all tracked diseases with stats |
| GET | `/api/v1/diseases/{name}` | Deep dive with genes, drugs, countries |
| GET | `/api/v1/diseases/{name}/countries` | Countries affected by disease |

### ⚠️ Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alerts` | Outbreak alerts (filtered by severity/disease) |
| GET | `/api/v1/alerts/recent` | Recent alerts by time window |

### 📈 Trends
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/trends/{disease}` | Time series with trend analysis |
| GET | `/api/v1/trends/compare` | Cross-country comparison |

### 🧬 Genomics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/genomics/{disease}` | Gene-disease associations |
| GET | `/api/v1/genomics/{disease}/network` | Knowledge graph (nodes + edges) |

### 💊 Drugs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/drugs/{disease}` | Drug associations with mechanisms |

### 📊 Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/anomalies` | Z-score anomaly detection |
| GET | `/api/v1/analytics/risk-score` | Multi-factor risk assessment |
| GET | `/api/v1/analytics/correlation` | Cross-country correlation |

### 🔧 System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sources/health` | Data source status |
| GET | `/api/v1/health` | Application health check |

## 🧠 Architecture

```
medfusion/
├── main.py                     # FastAPI app, startup, scheduler
├── config.py                   # All API endpoints and settings
├── database.py                 # Async SQLite (7 tables, full CRUD)
├── models.py                   # Pydantic request/response schemas
├── requirements.txt
├── data/
│   ├── icd10_mapping.json      # 30 disease ICD-10/ICD-11 codes
│   ├── country_codes.json      # 180+ country name → ISO-3 mappings
│   └── country_coords.json     # Country centroid coordinates
├── normalization/
│   ├── disease_mapper.py       # 25-disease ontology + fuzzy matching
│   ├── location_resolver.py    # Country code/name resolution
│   └── temporal.py             # Date format normalization
├── collectors/
│   ├── base.py                 # Abstract base collector
│   ├── disease_sh.py           # Disease.sh COVID-19 API
│   ├── who_gho.py              # WHO GHO OData API
│   ├── cdc_open.py             # CDC Open Data (Socrata)
│   ├── cdc_fluview.py          # CDC FluView RSS
│   ├── promed.py               # ProMED Mail RSS
│   ├── healthmap.py            # HealthMap scraper
│   ├── ihme_ghdx.py            # IHME GBD estimates
│   ├── ecdc.py                 # ECDC European data
│   └── uk_gov.py               # UK Government API
├── analytics/
│   ├── trends.py               # Moving averages, linear regression
│   ├── anomaly.py              # Rolling Z-score anomaly detection
│   └── risk_score.py           # Multi-factor risk scoring (0-100)
└── routers/
    ├── surveillance.py         # /surveillance/query, /summary
    ├── diseases.py             # /diseases CRUD
    ├── alerts.py               # /alerts endpoints
    ├── trends.py               # /trends time series
    ├── genomics.py             # /genomics gene associations
    ├── drugs.py                # /drugs therapeutics
    ├── analytics_router.py     # /analytics anomaly/risk/correlation
    └── sources.py              # /sources health monitoring
```

## 📦 Tech Stack

- **Python 3.11+** with **FastAPI** + **Uvicorn**
- **SQLite** via **aiosqlite** (async)
- **httpx** (async HTTP client)
- **feedparser** (RSS parsing)
- **BeautifulSoup4** (web scraping)
- **pandas** + **numpy** (analytics)
- **APScheduler** (periodic data refresh)
- **Pydantic v2** (data validation)

## 📈 Sample Stats (Startup)

```
✅ 971 events from 9 sources
✅ 12,480 time series records
✅ 90 outbreak alerts
✅ 19 diseases tracked
✅ 236 countries covered
✅ 29 gene associations
✅ 30 drug associations
✅ Auto-refresh every 15 minutes
```

## 👥 Team

Built for MedFusion Hackfest 2026 — Mahindra University
