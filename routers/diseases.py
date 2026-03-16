"""
MedFusion — Diseases Router
Disease listing, detail, and country breakdown endpoints.
"""

from fastapi import APIRouter, Path, Query
from typing import Optional

import database as db
from models import APIResponse
from normalization.disease_mapper import map_disease_name, get_disease_info, DISEASE_ONTOLOGY

router = APIRouter(prefix="/diseases", tags=["🦠 Diseases"])


@router.get("", response_model=APIResponse, summary="List all tracked diseases")
async def list_diseases():
    """List all tracked diseases with basic aggregated statistics."""
    db_diseases = await db.get_all_diseases()

    results = []
    for d in db_diseases:
        name = d.get("disease_name", "")
        ontology = DISEASE_ONTOLOGY.get(name, {})
        results.append({
            "canonical_name": name,
            "icd10_code": d.get("icd10_code") or ontology.get("icd10"),
            "category": ontology.get("category"),
            "description": ontology.get("description"),
            "total_cases": d.get("total_cases"),
            "total_deaths": d.get("total_deaths"),
            "countries_affected": d.get("countries_affected"),
            "sources_reporting": d.get("sources_reporting"),
            "latest_update": d.get("latest_update"),
        })

    return APIResponse(
        status="success",
        data=results,
        meta={"total_diseases": len(results)}
    )


@router.get("/{disease_name}", response_model=APIResponse, summary="Disease deep dive")
async def get_disease(
    disease_name: str = Path(..., description="Disease name (e.g., COVID-19, Malaria)"),
):
    """
    Get detailed information for a specific disease including ICD-10 info,
    total cases, deaths, countries affected, and associated data.
    """
    detail = await db.get_disease_detail(disease_name)
    if not detail:
        return APIResponse(status="error", error=f"Disease '{disease_name}' not found")

    ontology = get_disease_info(detail.get("disease_name", disease_name))
    genes = await db.get_gene_associations(disease_name)
    drugs = await db.get_drug_associations(disease_name)
    countries = await db.get_disease_countries(disease_name)
    
    # Get recent alerts
    alerts = await db.get_alerts(disease=disease_name, limit=5)

    result = {
        "canonical_name": detail.get("disease_name"),
        "icd10_code": detail.get("icd10_code") or (ontology.get("icd10_code") if ontology else None),
        "category": ontology.get("category") if ontology else None,
        "description": ontology.get("description") if ontology else None,
        "total_cases": detail.get("total_cases"),
        "total_deaths": detail.get("total_deaths"),
        "countries_affected": detail.get("countries_affected"),
        "sources_reporting": detail.get("sources_reporting"),
        "latest_update": detail.get("latest_update"),
        "top_countries": countries[:10],
        "recent_alerts": alerts[:5],
        "gene_associations": genes[:10],
        "drug_associations": drugs[:10],
    }

    return APIResponse(status="success", data=result)


@router.get("/{disease_name}/countries", response_model=APIResponse, summary="Countries affected by disease")
async def get_disease_countries_endpoint(
    disease_name: str = Path(..., description="Disease name"),
):
    """Get all countries with data for this disease, sorted by total cases."""
    countries = await db.get_disease_countries(disease_name)
    if not countries:
        return APIResponse(status="error", error=f"No data found for disease '{disease_name}'")

    return APIResponse(
        status="success",
        data=countries,
        meta={"total_countries": len(countries), "disease": disease_name}
    )
