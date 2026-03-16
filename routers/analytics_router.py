"""
MedFusion — Analytics Router
Anomaly detection, risk scoring, and correlation analysis endpoints.
"""

from fastapi import APIRouter, Query
from typing import Optional

import database as db
from models import APIResponse
from analytics.anomaly import detect_anomalies
from analytics.risk_score import calculate_risk_score
from analytics.trends import calculate_trend

router = APIRouter(prefix="/analytics", tags=["📊 Analytics"])


@router.get("/anomalies", response_model=APIResponse, summary="Detected anomalies in time series data")
async def get_anomalies(
    disease: Optional[str] = Query(None, description="Disease name filter"),
    country: Optional[str] = Query(None, description="Country code filter"),
    threshold: float = Query(2.0, description="Z-score threshold for anomaly detection"),
    window: int = Query(28, ge=7, le=90, description="Rolling window size in days"),
):
    """Detect anomalies in time series data using rolling Z-scores."""
    ts_data = await db.get_time_series(disease=disease, country=country, metric="cases")
    
    if not ts_data:
        ts_data = await db.get_time_series(disease=disease, country=country)

    if not ts_data or len(ts_data) < window:
        return APIResponse(
            status="success",
            data=[],
            meta={"message": "Insufficient data for anomaly detection", "required_points": window, "available": len(ts_data)}
        )

    # Add disease/country info to each point
    enriched = [
        {
            "date": r["date"],
            "value": r["value"],
            "disease_name": r.get("disease_name", disease or "Unknown"),
            "country_code": r.get("country_code", country),
        }
        for r in ts_data
    ]

    anomalies = detect_anomalies(enriched, window=window, threshold=threshold)

    return APIResponse(
        status="success",
        data=anomalies,
        meta={
            "total_anomalies": len(anomalies),
            "disease": disease,
            "country": country,
            "threshold": threshold,
            "window": window,
            "data_points_analyzed": len(ts_data),
        }
    )


@router.get("/risk-score", response_model=APIResponse, summary="Disease risk assessment")
async def get_risk_score(
    disease: str = Query(..., description="Disease name"),
    country: Optional[str] = Query(None, description="Country code (optional)"),
):
    """Compute multi-factor risk assessment for a disease/country combination."""
    # Get disease stats
    detail = await db.get_disease_detail(disease)
    if not detail:
        return APIResponse(status="error", error=f"No data found for disease '{disease}'")

    # Get trend data
    ts_data = await db.get_time_series(disease=disease, country=country)
    data_points = [{"date": r["date"], "value": r["value"]} for r in ts_data]
    trend_info = calculate_trend(data_points)

    # Build risk input
    disease_data = {
        "disease_name": detail.get("disease_name", disease),
        "country_code": country,
        "total_cases": detail.get("total_cases", 0),
        "total_deaths": detail.get("total_deaths", 0),
        "countries_affected": detail.get("countries_affected", 1),
        "sources_reporting": detail.get("sources_reporting", 1),
        "trend_direction": trend_info.get("trend_direction", "stable"),
        "percent_change": trend_info.get("percent_change_wow", 0),
    }

    risk = calculate_risk_score(disease_data)

    return APIResponse(
        status="success",
        data=risk,
        meta={"disease": disease, "country": country}
    )


@router.get("/correlation", response_model=APIResponse, summary="Cross-country correlation analysis")
async def get_correlation(
    disease: str = Query(..., description="Disease name"),
    countries: str = Query(..., description="Comma-separated country codes (e.g., IND,USA,GBR,BRA)"),
):
    """Analyze correlation between disease trends across countries."""
    import numpy as np

    country_list = [c.strip().upper() for c in countries.split(",")]
    country_data = {}

    for country in country_list:
        ts_data = await db.get_time_series(disease=disease, country=country, metric="cases")
        if ts_data:
            country_data[country] = {r["date"]: r["value"] for r in ts_data}

    if len(country_data) < 2:
        return APIResponse(
            status="success",
            data={"correlations": [], "message": "Insufficient data for correlation analysis"},
            meta={"disease": disease, "countries": country_list}
        )

    # Find common dates
    all_dates = set()
    for dates in country_data.values():
        all_dates.update(dates.keys())
    common_dates = sorted(all_dates)

    # Build matrix
    correlations = []
    countries_with_data = list(country_data.keys())

    for i, c1 in enumerate(countries_with_data):
        for j, c2 in enumerate(countries_with_data):
            if i >= j:
                continue

            v1 = [country_data[c1].get(d, 0) for d in common_dates]
            v2 = [country_data[c2].get(d, 0) for d in common_dates]

            if len(v1) < 3:
                continue

            try:
                corr = float(np.corrcoef(v1, v2)[0, 1])
                if np.isnan(corr):
                    corr = 0.0
            except Exception:
                corr = 0.0

            correlations.append({
                "country_1": c1,
                "country_2": c2,
                "correlation": round(corr, 4),
                "data_points": len(common_dates),
                "interpretation": (
                    "Strong positive" if corr > 0.7 else
                    "Moderate positive" if corr > 0.4 else
                    "Weak positive" if corr > 0.1 else
                    "No correlation" if abs(corr) <= 0.1 else
                    "Weak negative" if corr > -0.4 else
                    "Moderate negative" if corr > -0.7 else
                    "Strong negative"
                ),
            })

    return APIResponse(
        status="success",
        data={"correlations": correlations},
        meta={
            "disease": disease,
            "countries": countries_with_data,
            "common_dates": len(common_dates),
        }
    )
