"""
MedFusion — Main Application Entry Point
Disease Surveillance Intelligence Platform powered by FastAPI.

Run: python main.py
Docs: http://localhost:8000/docs
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the medfusion directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, HOST, PORT
import database as db

# Import routers
from routers.surveillance import router as surveillance_router
from routers.diseases import router as diseases_router
from routers.alerts import router as alerts_router
from routers.trends import router as trends_router
from routers.genomics import router as genomics_router
from routers.drugs import router as drugs_router
from routers.sources import router as sources_router
from routers.analytics_router import router as analytics_router

# Import collectors
from collectors.disease_sh import DiseaseSHCollector
from collectors.who_gho import WHOGHOCollector
from collectors.cdc_open import CDCOpenCollector
from collectors.cdc_fluview import CDCFluViewCollector
from collectors.promed import ProMEDCollector
from collectors.healthmap import HealthMapCollector
from collectors.ihme_ghdx import IHMEGHDxCollector
from collectors.ecdc import ECDCCollector
from collectors.uk_gov import UKGovCollector

# Gene and drug data for initial population
from routers.genomics import GENE_DISEASE_DATA
from routers.drugs import DRUG_DISEASE_DATA

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title=f"{APP_NAME} API",
    description=(
        f"**{APP_DESCRIPTION}**\n\n"
        "MedFusion ingests data from 9 real-world public health surveillance sources, "
        "normalizes it into a unified schema, runs analytics (anomaly detection, trend analysis, "
        "risk scoring), and serves everything through this REST API.\n\n"
        "### Data Sources\n"
        "- 🌐 Disease.sh — Real-time COVID-19 global statistics\n"
        "- 🏛️ WHO GHO — Global health indicators (Malaria, TB, Cholera, HIV, Measles)\n"
        "- 🇺🇸 CDC Open Data — US disease surveillance (NNDSS)\n"
        "- 🤧 CDC FluView — US influenza surveillance\n"
        "- 📡 ProMED Mail — Outbreak alert reports\n"
        "- 🗺️ HealthMap — Disease outbreak monitoring\n"
        "- 🇮🇳 IHME GHDx — India disease burden estimates\n"
        "- 🇪🇺 ECDC — European COVID-19 data\n"
        "- 🇬🇧 UK Gov — UK health statistics\n"
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for hackathon/demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers under /api/v1
app.include_router(surveillance_router, prefix="/api/v1")
app.include_router(diseases_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(genomics_router, prefix="/api/v1")
app.include_router(drugs_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

# Global collector instances
collectors = []


# ──────────────────────────────────────────────
# Root & Health Endpoints
# ──────────────────────────────────────────────

@app.get("/", tags=["🔧 System"], summary="App info")
async def root():
    """MedFusion application information and links."""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "api_base": "/api/v1",
        "endpoints": {
            "surveillance_query": "/api/v1/surveillance/query",
            "surveillance_summary": "/api/v1/surveillance/summary",
            "diseases": "/api/v1/diseases",
            "alerts": "/api/v1/alerts",
            "trends": "/api/v1/trends/{disease_name}",
            "genomics": "/api/v1/genomics/{disease_name}",
            "drugs": "/api/v1/drugs/{disease_name}",
            "analytics_anomalies": "/api/v1/analytics/anomalies",
            "analytics_risk": "/api/v1/analytics/risk-score",
            "source_health": "/api/v1/sources/health",
        },
    }


@app.get("/api/v1/health", tags=["🔧 System"], summary="App health check")
async def health_check():
    """Application health status."""
    stats = await db.get_summary_stats()
    source_health = await db.get_source_health()
    active = sum(1 for s in source_health if s.get("status") == "active")
    return {
        "status": "healthy" if active > 0 else "degraded",
        "app": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "database": {
            "total_events": stats.get("total_events", 0),
            "total_diseases": stats.get("total_diseases", 0),
            "total_countries": stats.get("total_countries", 0),
            "active_alerts": stats.get("active_alerts", 0),
        },
        "sources": {
            "active": active,
            "total": len(source_health),
        },
    }


# ──────────────────────────────────────────────
# Startup: Data Collection
# ──────────────────────────────────────────────

async def run_all_collectors():
    """Run all collectors concurrently and store data."""
    global collectors

    collector_classes = [
        DiseaseSHCollector,
        WHOGHOCollector,
        CDCOpenCollector,
        CDCFluViewCollector,
        ProMEDCollector,
        HealthMapCollector,
        IHMEGHDxCollector,
        ECDCCollector,
        UKGovCollector,
    ]

    collectors = [cls() for cls in collector_classes]
    total_events = 0
    total_ts = 0
    total_alerts = 0

    # Run all collectors concurrently
    results = await asyncio.gather(
        *[c.collect() for c in collectors],
        return_exceptions=True,
    )

    for i, result in enumerate(results):
        c = collectors[i]
        if isinstance(result, Exception):
            logger.error(f"[{c.source_name}] ❌ Exception: {result}")
            c.status = "error"
            c.error_message = str(result)
            events = []
        else:
            events = result

        # Store events
        if events:
            await db.insert_events(events)
            total_events += len(events)

        # Store time series
        ts = c.get_time_series()
        if ts:
            await db.insert_time_series(ts)
            total_ts += len(ts)

        # Store alerts
        alerts = c.get_alerts()
        if alerts:
            await db.insert_alerts(alerts)
            total_alerts += len(alerts)

        # Update source health
        health = c.get_health()
        await db.update_source_health(
            source_name=health["source_name"],
            display_name=health["display_name"],
            source_type=health["source_type"],
            status=health["status"],
            records=health["records_fetched"],
            error=health["error_message"],
            response_time=health["response_time_ms"],
            last_fetch=health["last_successful_fetch"],
        )

    logger.info(f"[{APP_NAME}] ✅ Total: {total_events} events, {total_ts} time series, {total_alerts} alerts from {len(collectors)} sources")
    return total_events


async def populate_gene_drug_data():
    """Populate gene and drug association tables with curated data."""
    logger.info(f"[{APP_NAME}] 🧬 Loading genomic associations...")
    gene_records = []
    for disease, genes in GENE_DISEASE_DATA.items():
        for g in genes:
            gene_records.append({
                "disease_name": disease,
                "gene_symbol": g["gene_symbol"],
                "gene_name": g["gene_name"],
                "association_score": g["score"],
                "evidence_type": g["evidence"],
                "source": "open_targets",
            })
    await db.insert_gene_associations(gene_records)
    logger.info(f"[{APP_NAME}] ✅ Loaded {len(gene_records)} gene associations")

    logger.info(f"[{APP_NAME}] 💊 Loading drug associations...")
    drug_records = []
    for disease, drugs in DRUG_DISEASE_DATA.items():
        for d in drugs:
            drug_records.append({
                "disease_name": disease,
                "drug_name": d["drug_name"],
                "pubchem_cid": d["pubchem_cid"],
                "mechanism": d["mechanism"],
                "who_essential": d["who_essential"],
                "approval_status": d["approval_status"],
                "source": "pubchem",
            })
    await db.insert_drug_associations(drug_records)
    logger.info(f"[{APP_NAME}] ✅ Loaded {len(drug_records)} drug associations")


@app.on_event("startup")
async def startup_event():
    """Initialize database, collect data from all sources, populate knowledge bases."""
    logger.info(f"[{APP_NAME}] 🚀 Starting MedFusion Disease Surveillance Platform...")
    logger.info(f"[{APP_NAME}] 📦 Initializing database...")
    
    await db.init_db()
    
    logger.info(f"[{APP_NAME}] 🔄 Starting data collection from 9 sources...")
    await run_all_collectors()

    # Populate gene and drug data
    await populate_gene_drug_data()

    logger.info(f"[{APP_NAME}] 📊 Running initial analytics...")
    
    # Schedule periodic refresh
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_all_collectors, "interval", minutes=15, id="data_refresh")
        scheduler.start()
        logger.info(f"[{APP_NAME}] ⏰ Scheduled data refresh every 15 minutes")
    except Exception as e:
        logger.warning(f"[{APP_NAME}] ⚠️ Could not start scheduler: {e}")

    logger.info(f"[{APP_NAME}] ✅ MedFusion is ready at http://{HOST}:{PORT}")
    logger.info(f"[{APP_NAME}] 📚 API docs at http://{HOST}:{PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up collector HTTP clients on shutdown."""
    for c in collectors:
        try:
            await c.close()
        except Exception:
            pass
    logger.info(f"[{APP_NAME}] 🛑 MedFusion shutdown complete")


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
