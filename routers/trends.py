"""
MedFusion — Trends Router
Time series trend analysis and cross-country comparison endpoints.
"""

from fastapi import APIRouter, Path, Query
from typing import Optional, List

import database as db
from models import APIResponse, TimeSeriesPoint, TrendData
from analytics.trends import calculate_trend

router = APIRouter(prefix="/trends", tags=["📈 Trends"])


@router.get("/compare", response_model=APIResponse, summary="Cross-country trend comparison")
async def compare_trends(
    disease: str = Query(..., description="Disease name"),
    countries: str = Query(..., description="Comma-separated country codes (e.g., IND,USA,GBR)"),
    metric: str = Query("cases", description="Metric: cases, deaths, incidence"),
):
    """Compare disease trends across multiple countries."""
    country_list = [c.strip().upper() for c in countries.split(",")]
    results = []

    for country in country_list:
        ts_data = await db.get_time_series(disease=disease, country=country, metric=metric)
        if ts_data:
            data_points = [{"date": r["date"], "value": r["value"]} for r in ts_data]
            trend_info = calculate_trend(data_points)
            results.append({
                "country_code": country,
                "disease_name": disease,
                "metric": metric,
                "data_points": [
                    {"date": r["date"], "value": r["value"], "metric": metric, "source": r.get("source")}
                    for r in ts_data
                ],
                "trend_direction": trend_info["trend_direction"],
                "percent_change_wow": trend_info["percent_change_wow"],
                "data_count": trend_info["data_count"],
            })

    return APIResponse(
        status="success",
        data=results,
        meta={"disease": disease, "countries": country_list, "metric": metric}
    )


@router.get("/{disease_name}", response_model=APIResponse, summary="Disease time series trends")
async def get_trends(
    disease_name: str = Path(..., description="Disease name"),
    country: Optional[str] = Query(None, description="Country code filter"),
    metric: str = Query("cases", description="Metric: cases, deaths, incidence, prevalence"),
    period: str = Query("6M", description="Time period: 3M, 6M, 1Y, ALL"),
):
    """Get time series data with trend analysis for a disease."""
    # Calculate date range
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    period_map = {"3M": 90, "6M": 180, "1Y": 365, "ALL": 3650}
    days = period_map.get(period.upper(), 180)
    date_from = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    ts_data = await db.get_time_series(
        disease=disease_name, country=country,
        metric=metric, date_from=date_from,
    )

    if not ts_data:
        # Try without metric filter
        ts_data = await db.get_time_series(
            disease=disease_name, country=country,
            date_from=date_from,
        )

    data_points = [{"date": r["date"], "value": r["value"]} for r in ts_data]
    trend_info = calculate_trend(data_points)

    result = {
        "disease_name": disease_name,
        "country_code": country,
        "metric": metric,
        "period": period,
        "data_points": [
            {"date": r["date"], "value": r["value"], "metric": r.get("metric", metric), "source": r.get("source")}
            for r in ts_data
        ],
        "trend_direction": trend_info["trend_direction"],
        "percent_change_wow": trend_info["percent_change_wow"],
        "percent_change_mom": trend_info["percent_change_mom"],
        "data_count": trend_info["data_count"],
        "min_value": trend_info["min_value"],
        "max_value": trend_info["max_value"],
        "latest_value": trend_info["latest_value"],
    }

    return APIResponse(status="success", data=result)
