"""
MedFusion — Alerts Router
Outbreak alert endpoints.
"""

from fastapi import APIRouter, Query
from typing import Optional

import database as db
from models import APIResponse

router = APIRouter(prefix="/alerts", tags=["⚠️ Alerts"])


@router.get("", response_model=APIResponse, summary="Outbreak alerts")
async def list_alerts(
    active_only: bool = Query(True, description="Show only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    disease: Optional[str] = Query(None, description="Filter by disease name"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
):
    """Get outbreak alerts from ProMED, HealthMap, CDC, and other sources."""
    alerts = await db.get_alerts(
        active_only=active_only,
        severity=severity,
        disease=disease,
        limit=limit,
    )
    return APIResponse(
        status="success",
        data=alerts,
        meta={"total_alerts": len(alerts), "active_only": active_only}
    )


@router.get("/recent", response_model=APIResponse, summary="Recent alerts")
async def recent_alerts(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
):
    """Get alerts from the last N hours."""
    alerts = await db.get_recent_alerts(hours=hours)
    return APIResponse(
        status="success",
        data=alerts,
        meta={"hours": hours, "total_alerts": len(alerts)}
    )
