"""
MedFusion — Sources Router
Data source health monitoring endpoints.
"""

from fastapi import APIRouter

import database as db
from models import APIResponse

router = APIRouter(prefix="/sources", tags=["🔧 System"])


@router.get("/health", response_model=APIResponse, summary="Data source health status")
async def get_source_health():
    """Get health status of all 9 data sources."""
    sources = await db.get_source_health()

    active = sum(1 for s in sources if s.get("status") == "active")
    degraded = sum(1 for s in sources if s.get("status") == "degraded")
    error = sum(1 for s in sources if s.get("status") == "error")

    return APIResponse(
        status="success",
        data=sources,
        meta={
            "total_sources": len(sources),
            "active_sources": active,
            "degraded_sources": degraded,
            "error_sources": error,
        }
    )
