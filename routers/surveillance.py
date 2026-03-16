"""
MedFusion — Surveillance Router
Main surveillance query and summary endpoints.
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone

import database as db
from models import APIResponse

router = APIRouter(prefix="/surveillance", tags=["🏥 Surveillance"])


@router.get("/query", response_model=APIResponse, summary="Unified multi-source surveillance query")
async def query_surveillance(
    disease: Optional[str] = Query(None, description="Disease name filter"),
    country: Optional[str] = Query(None, description="Country code or name"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    source: Optional[str] = Query(None, description="Data source name"),
    event_type: Optional[str] = Query(None, description="Event type filter"),
    limit: int = Query(100, ge=1, le=5000, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Query surveillance events across all data sources with flexible filters.
    All parameters are optional — omit them to browse all data.
    """
    events = await db.query_events(
        disease=disease, country=country,
        date_from=date_from, date_to=date_to,
        source=source, event_type=event_type,
        limit=limit, offset=offset,
    )
    total = await db.count_events(
        disease=disease, country=country,
        date_from=date_from, date_to=date_to,
        source=source, event_type=event_type,
    )

    # Collect unique sources
    sources_included = list(set(e.get("source", "") for e in events if e.get("source")))

    return APIResponse(
        status="success",
        data=events,
        meta={
            "total_results": total,
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "limit": limit,
            "offset": offset,
            "sources_included": sources_included,
            "query": {
                k: v for k, v in {
                    "disease": disease, "country": country,
                    "date_from": date_from, "date_to": date_to,
                    "source": source, "event_type": event_type,
                }.items() if v is not None
            },
        }
    )


@router.get("/summary", response_model=APIResponse, summary="Dashboard summary statistics")
async def get_summary():
    """Get high-level summary statistics for the dashboard."""
    stats = await db.get_summary_stats()
    stats["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return APIResponse(status="success", data=stats)
