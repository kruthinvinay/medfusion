"""
MedFusion — Database Layer
SQLite database manager with async support via aiosqlite.
All CRUD operations for surveillance events, alerts, time series, and more.
"""

import aiosqlite
import json
import logging
from typing import List, Dict, Any, Optional
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize the database and create all tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS diseases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name TEXT UNIQUE NOT NULL,
                icd10_code TEXT,
                icd11_code TEXT,
                category TEXT,
                description TEXT,
                aliases TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS surveillance_events (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                disease_name TEXT,
                disease_raw TEXT,
                icd10_code TEXT,
                country_code TEXT,
                country_name TEXT,
                region TEXT,
                latitude REAL,
                longitude REAL,
                cases INTEGER,
                deaths INTEGER,
                recovered INTEGER,
                incidence_rate REAL,
                prevalence REAL,
                severity TEXT DEFAULT 'unknown',
                confidence REAL DEFAULT 0.5,
                title TEXT,
                description TEXT,
                date_reported TEXT,
                date_event TEXT,
                source_url TEXT,
                raw_data TEXT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS time_series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_name TEXT NOT NULL,
                source TEXT NOT NULL,
                country_code TEXT,
                country_name TEXT,
                region TEXT,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                date TEXT NOT NULL,
                UNIQUE(disease_name, source, country_code, metric, date)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                disease_name TEXT,
                severity TEXT DEFAULT 'medium',
                title TEXT NOT NULL,
                description TEXT,
                country_code TEXT,
                country_name TEXT,
                region TEXT,
                latitude REAL,
                longitude REAL,
                date_issued TEXT,
                url TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gene_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_name TEXT NOT NULL,
                gene_symbol TEXT NOT NULL,
                gene_name TEXT,
                association_score REAL,
                evidence_type TEXT,
                source TEXT DEFAULT 'open_targets',
                UNIQUE(disease_name, gene_symbol, source)
            );

            CREATE TABLE IF NOT EXISTS drug_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_name TEXT NOT NULL,
                drug_name TEXT NOT NULL,
                pubchem_cid TEXT,
                mechanism TEXT,
                who_essential INTEGER DEFAULT 0,
                approval_status TEXT,
                source TEXT DEFAULT 'pubchem',
                UNIQUE(disease_name, drug_name)
            );

            CREATE TABLE IF NOT EXISTS source_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                source_type TEXT,
                last_successful_fetch TEXT,
                last_attempt TEXT,
                status TEXT DEFAULT 'unknown',
                records_fetched INTEGER DEFAULT 0,
                total_records INTEGER DEFAULT 0,
                error_message TEXT,
                response_time_ms REAL
            );

            CREATE INDEX IF NOT EXISTS idx_events_disease ON surveillance_events(disease_name);
            CREATE INDEX IF NOT EXISTS idx_events_country ON surveillance_events(country_code);
            CREATE INDEX IF NOT EXISTS idx_events_source ON surveillance_events(source);
            CREATE INDEX IF NOT EXISTS idx_events_date ON surveillance_events(date_reported);
            CREATE INDEX IF NOT EXISTS idx_ts_disease ON time_series(disease_name);
            CREATE INDEX IF NOT EXISTS idx_ts_country ON time_series(country_code);
            CREATE INDEX IF NOT EXISTS idx_alerts_disease ON alerts(disease_name);
            CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(is_active);
        """)
        await db.commit()
    logger.info("[Database] ✅ All tables initialized")


async def insert_events(events: List[Dict[str, Any]]):
    """Bulk insert surveillance events with deduplication via ON CONFLICT IGNORE."""
    if not events:
        return 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        inserted = 0
        for event in events:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO surveillance_events
                    (id, source, event_type, disease_name, disease_raw, icd10_code,
                     country_code, country_name, region, latitude, longitude,
                     cases, deaths, recovered, incidence_rate, prevalence,
                     severity, confidence, title, description,
                     date_reported, date_event, source_url, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.get("id"), event.get("source"), event.get("event_type"),
                    event.get("disease_name"), event.get("disease_raw"), event.get("icd10_code"),
                    event.get("country_code"), event.get("country_name"), event.get("region"),
                    event.get("latitude"), event.get("longitude"),
                    event.get("cases"), event.get("deaths"), event.get("recovered"),
                    event.get("incidence_rate"), event.get("prevalence"),
                    event.get("severity", "unknown"), event.get("confidence", 0.5),
                    event.get("title"), event.get("description"),
                    event.get("date_reported"), event.get("date_event"),
                    event.get("source_url"),
                    json.dumps(event.get("raw_data")) if event.get("raw_data") else None
                ))
                inserted += 1
            except Exception as e:
                logger.debug(f"Event insert skipped: {e}")
        await db.commit()
        return inserted


async def insert_time_series(records: List[Dict[str, Any]]):
    """Bulk insert time series records with dedup."""
    if not records:
        return 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for rec in records:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO time_series
                    (disease_name, source, country_code, country_name, region, metric, value, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.get("disease_name"), rec.get("source"),
                    rec.get("country_code"), rec.get("country_name"), rec.get("region"),
                    rec.get("metric"), rec.get("value"), rec.get("date")
                ))
            except Exception as e:
                logger.debug(f"Time series insert skipped: {e}")
        await db.commit()
        return len(records)


async def insert_alerts(alerts: List[Dict[str, Any]]):
    """Bulk insert alerts."""
    if not alerts:
        return 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for alert in alerts:
            try:
                await db.execute("""
                    INSERT INTO alerts
                    (source, disease_name, severity, title, description,
                     country_code, country_name, region, latitude, longitude,
                     date_issued, url, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.get("source"), alert.get("disease_name"),
                    alert.get("severity", "medium"), alert.get("title", ""),
                    alert.get("description"), alert.get("country_code"),
                    alert.get("country_name"), alert.get("region"),
                    alert.get("latitude"), alert.get("longitude"),
                    alert.get("date_issued"), alert.get("url"),
                    1 if alert.get("is_active", True) else 0
                ))
            except Exception as e:
                logger.debug(f"Alert insert skipped: {e}")
        await db.commit()
        return len(alerts)


async def query_events(
    disease: Optional[str] = None,
    country: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Flexible query for surveillance events with optional filters."""
    conditions = []
    params = []

    if disease:
        conditions.append("disease_name LIKE ?")
        params.append(f"%{disease}%")
    if country:
        conditions.append("(country_code = ? OR country_name LIKE ?)")
        params.extend([country.upper(), f"%{country}%"])
    if date_from:
        conditions.append("date_reported >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date_reported <= ?")
        params.append(date_to)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM surveillance_events {where} ORDER BY date_reported DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def count_events(
    disease: Optional[str] = None,
    country: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
) -> int:
    """Count surveillance events matching the filters."""
    conditions = []
    params = []

    if disease:
        conditions.append("disease_name LIKE ?")
        params.append(f"%{disease}%")
    if country:
        conditions.append("(country_code = ? OR country_name LIKE ?)")
        params.extend([country.upper(), f"%{country}%"])
    if date_from:
        conditions.append("date_reported >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date_reported <= ?")
        params.append(date_to)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT COUNT(*) FROM surveillance_events {where}"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_diseases() -> List[Dict[str, Any]]:
    """List all unique diseases with aggregated stats."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT disease_name,
                   icd10_code,
                   SUM(cases) as total_cases,
                   SUM(deaths) as total_deaths,
                   COUNT(DISTINCT country_code) as countries_affected,
                   COUNT(DISTINCT source) as sources_reporting,
                   MAX(date_reported) as latest_update
            FROM surveillance_events
            WHERE disease_name IS NOT NULL
            GROUP BY disease_name
            ORDER BY total_cases DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_disease_detail(name: str) -> Optional[Dict[str, Any]]:
    """Get aggregated stats for a single disease."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT disease_name,
                   icd10_code,
                   SUM(cases) as total_cases,
                   SUM(deaths) as total_deaths,
                   COUNT(DISTINCT country_code) as countries_affected,
                   COUNT(DISTINCT source) as sources_reporting,
                   MAX(date_reported) as latest_update
            FROM surveillance_events
            WHERE disease_name LIKE ?
            GROUP BY disease_name
        """, (f"%{name}%",)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_disease_countries(name: str) -> List[Dict[str, Any]]:
    """Get all countries with data for a disease, sorted by cases."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT country_code, country_name,
                   SUM(cases) as total_cases,
                   SUM(deaths) as total_deaths,
                   MAX(date_reported) as latest_update,
                   latitude, longitude
            FROM surveillance_events
            WHERE disease_name LIKE ?
            GROUP BY country_code
            ORDER BY total_cases DESC
        """, (f"%{name}%",)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_alerts(
    active_only: bool = True,
    severity: Optional[str] = None,
    disease: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get filtered outbreak alerts."""
    conditions = []
    params = []

    if active_only:
        conditions.append("is_active = 1")
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if disease:
        conditions.append("disease_name LIKE ?")
        params.append(f"%{disease}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM alerts {where} ORDER BY date_issued DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_recent_alerts(hours: int = 24) -> List[Dict[str, Any]]:
    """Get alerts from the last N hours."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM alerts
            WHERE datetime(created_at) >= datetime('now', ? || ' hours')
            ORDER BY created_at DESC
        """, (f"-{hours}",)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_time_series(
    disease: Optional[str] = None,
    country: Optional[str] = None,
    metric: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get time series data with optional filters."""
    conditions = []
    params = []

    if disease:
        conditions.append("disease_name LIKE ?")
        params.append(f"%{disease}%")
    if country:
        conditions.append("country_code = ?")
        params.append(country.upper())
    if metric:
        conditions.append("metric = ?")
        params.append(metric)
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"SELECT * FROM time_series {where} ORDER BY date ASC"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_source_health(
    source_name: str,
    display_name: str = "",
    source_type: str = "api",
    status: str = "unknown",
    records: int = 0,
    error: Optional[str] = None,
    response_time: Optional[float] = None,
    last_fetch: Optional[str] = None
):
    """Update source health monitoring record."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO source_health (source_name, display_name, source_type, status,
                                       records_fetched, total_records, error_message,
                                       response_time_ms, last_successful_fetch, last_attempt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(source_name) DO UPDATE SET
                display_name = excluded.display_name,
                source_type = excluded.source_type,
                status = excluded.status,
                records_fetched = excluded.records_fetched,
                total_records = excluded.total_records,
                error_message = excluded.error_message,
                response_time_ms = excluded.response_time_ms,
                last_successful_fetch = CASE WHEN excluded.status = 'active'
                    THEN excluded.last_successful_fetch ELSE source_health.last_successful_fetch END,
                last_attempt = datetime('now')
        """, (source_name, display_name, source_type, status, records, records,
              error, response_time, last_fetch))
        await db.commit()


async def get_source_health() -> List[Dict[str, Any]]:
    """Get health status for all sources."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM source_health ORDER BY source_name") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_gene_associations(disease: str) -> List[Dict[str, Any]]:
    """Get gene associations for a disease."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM gene_associations
            WHERE disease_name LIKE ?
            ORDER BY association_score DESC
        """, (f"%{disease}%",)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_drug_associations(disease: str) -> List[Dict[str, Any]]:
    """Get drug associations for a disease."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM drug_associations
            WHERE disease_name LIKE ?
            ORDER BY drug_name
        """, (f"%{disease}%",)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def insert_gene_associations(records: List[Dict[str, Any]]):
    """Bulk insert gene-disease associations."""
    if not records:
        return
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for rec in records:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO gene_associations
                    (disease_name, gene_symbol, gene_name, association_score, evidence_type, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    rec.get("disease_name"), rec.get("gene_symbol"),
                    rec.get("gene_name"), rec.get("association_score"),
                    rec.get("evidence_type"), rec.get("source", "open_targets")
                ))
            except Exception as e:
                logger.debug(f"Gene assoc insert skipped: {e}")
        await db.commit()


async def insert_drug_associations(records: List[Dict[str, Any]]):
    """Bulk insert drug-disease associations."""
    if not records:
        return
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for rec in records:
            try:
                await db.execute("""
                    INSERT OR IGNORE INTO drug_associations
                    (disease_name, drug_name, pubchem_cid, mechanism, who_essential, approval_status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.get("disease_name"), rec.get("drug_name"),
                    rec.get("pubchem_cid"), rec.get("mechanism"),
                    1 if rec.get("who_essential") else 0,
                    rec.get("approval_status"), rec.get("source", "pubchem")
                ))
            except Exception as e:
                logger.debug(f"Drug assoc insert skipped: {e}")
        await db.commit()


async def get_summary_stats() -> Dict[str, Any]:
    """Get dashboard summary statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Total events
        async with db.execute("SELECT COUNT(*) FROM surveillance_events") as c:
            total_events = (await c.fetchone())[0]
        # Total diseases
        async with db.execute("SELECT COUNT(DISTINCT disease_name) FROM surveillance_events WHERE disease_name IS NOT NULL") as c:
            total_diseases = (await c.fetchone())[0]
        # Total countries
        async with db.execute("SELECT COUNT(DISTINCT country_code) FROM surveillance_events WHERE country_code IS NOT NULL") as c:
            total_countries = (await c.fetchone())[0]
        # Active alerts
        async with db.execute("SELECT COUNT(*) FROM alerts WHERE is_active = 1") as c:
            active_alerts = (await c.fetchone())[0]
        # Source stats
        async with db.execute("SELECT COUNT(*) FROM source_health") as c:
            sources_total = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM source_health WHERE status = 'active'") as c:
            sources_active = (await c.fetchone())[0]

        return {
            "total_events": total_events,
            "total_diseases": total_diseases,
            "total_countries": total_countries,
            "active_alerts": active_alerts,
            "sources_active": sources_active,
            "sources_total": sources_total,
        }
