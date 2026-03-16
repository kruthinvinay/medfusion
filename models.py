"""
MedFusion — Pydantic Models
Request/response schemas for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class SurveillanceEvent(BaseModel):
    """A unified surveillance event from any data source."""
    id: str
    source: str
    event_type: str
    disease_name: Optional[str] = None
    disease_raw: Optional[str] = None
    icd10_code: Optional[str] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cases: Optional[int] = None
    deaths: Optional[int] = None
    recovered: Optional[int] = None
    incidence_rate: Optional[float] = None
    prevalence: Optional[float] = None
    severity: Optional[str] = "unknown"
    confidence: Optional[float] = 0.5
    title: Optional[str] = None
    description: Optional[str] = None
    date_reported: Optional[str] = None
    date_event: Optional[str] = None
    source_url: Optional[str] = None
    ingested_at: Optional[str] = None


class Alert(BaseModel):
    """An outbreak alert from ProMED, HealthMap, CDC, etc."""
    id: int
    source: str
    disease_name: Optional[str] = None
    severity: str = "medium"
    title: str
    description: Optional[str] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    date_issued: Optional[str] = None
    url: Optional[str] = None
    is_active: bool = True


class TimeSeriesPoint(BaseModel):
    """A single data point in a time series."""
    date: str
    value: float
    metric: str
    source: Optional[str] = None


class TrendData(BaseModel):
    """Time series data with trend analysis."""
    disease_name: str
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    metric: str
    data_points: List[TimeSeriesPoint] = []
    trend_direction: Optional[str] = None
    percent_change: Optional[float] = None


class DiseaseInfo(BaseModel):
    """Disease information with aggregated statistics."""
    canonical_name: str
    icd10_code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    total_cases: Optional[int] = None
    total_deaths: Optional[int] = None
    countries_affected: Optional[int] = None
    sources_reporting: Optional[int] = None
    latest_update: Optional[str] = None


class GeneAssociation(BaseModel):
    """Gene-disease association record."""
    gene_symbol: str
    gene_name: Optional[str] = None
    association_score: Optional[float] = None
    evidence_type: Optional[str] = None
    source: str = "open_targets"


class DrugAssociation(BaseModel):
    """Drug-disease association record."""
    drug_name: str
    pubchem_cid: Optional[str] = None
    mechanism: Optional[str] = None
    who_essential: bool = False
    approval_status: Optional[str] = None


class SourceHealth(BaseModel):
    """Health status of a data source."""
    source_name: str
    display_name: str
    source_type: str
    status: str
    last_successful_fetch: Optional[str] = None
    records_fetched: int = 0
    total_records: int = 0
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class AnomalyAlert(BaseModel):
    """Detected anomaly in time series data."""
    disease_name: str
    country_code: Optional[str] = None
    date: str
    observed_value: float
    expected_value: float
    z_score: float
    severity: str
    message: str


class RiskAssessment(BaseModel):
    """Risk assessment for a disease/country combination."""
    disease_name: str
    country_code: Optional[str] = None
    risk_score: float
    risk_level: str
    factors: dict
    explanation: str


class SummaryStats(BaseModel):
    """Dashboard summary statistics."""
    total_events: int = 0
    total_diseases: int = 0
    total_countries: int = 0
    active_alerts: int = 0
    sources_active: int = 0
    sources_total: int = 0
    last_updated: str = ""


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    status: str = "success"
    data: Any = None
    meta: Optional[dict] = None
    error: Optional[str] = None
