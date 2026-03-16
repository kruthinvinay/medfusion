"""
MedFusion — Outbreak Risk Scoring Module
Computes multi-factor risk scores (0-100) for disease/country combinations.
"""

from typing import Dict, Any, Optional


def calculate_risk_score(disease_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a 0-100 risk score based on multiple factors.
    
    Factors and weights:
    - trend_acceleration (0.25): Is the case count accelerating?
    - case_count_level (0.20): Absolute number relative to population
    - death_rate (0.20): Case fatality rate
    - geographic_spread (0.15): Number of countries/regions affected
    - source_agreement (0.10): How many sources report this?
    - historical_deviation (0.10): Is this above normal for the season?
    
    Args:
        disease_data: Dict with keys like total_cases, total_deaths, 
                      countries_affected, sources_reporting, trend_direction,
                      percent_change, disease_name, country_code
                      
    Returns:
        Dict with risk_score, risk_level, factors, and explanation
    """
    disease_name = disease_data.get("disease_name", "Unknown")
    country_code = disease_data.get("country_code")
    
    # Calculate individual factor scores (each 0-100)
    factors = {}
    
    # 1. Trend Acceleration (weight: 0.25)
    trend = disease_data.get("trend_direction", "stable")
    pct_change = disease_data.get("percent_change", 0) or 0
    if trend == "accelerating":
        trend_score = min(100, 70 + abs(pct_change) * 0.5)
    elif trend == "rising":
        trend_score = min(100, 40 + abs(pct_change) * 0.8)
    elif trend == "stable":
        trend_score = 20
    else:  # falling
        trend_score = max(0, 10 - abs(pct_change) * 0.3)
    factors["trend_acceleration"] = round(trend_score, 1)
    
    # 2. Case Count Level (weight: 0.20)
    total_cases = disease_data.get("total_cases", 0) or 0
    if total_cases > 10_000_000:
        case_score = 100
    elif total_cases > 1_000_000:
        case_score = 80
    elif total_cases > 100_000:
        case_score = 60
    elif total_cases > 10_000:
        case_score = 40
    elif total_cases > 1_000:
        case_score = 25
    else:
        case_score = 10
    factors["case_count_level"] = case_score
    
    # 3. Death Rate (weight: 0.20)
    total_deaths = disease_data.get("total_deaths", 0) or 0
    if total_cases > 0 and total_deaths > 0:
        cfr = (total_deaths / total_cases) * 100
        if cfr > 10:
            death_score = 100
        elif cfr > 5:
            death_score = 80
        elif cfr > 2:
            death_score = 60
        elif cfr > 1:
            death_score = 40
        elif cfr > 0.1:
            death_score = 20
        else:
            death_score = 10
    else:
        death_score = 15
        cfr = 0
    factors["death_rate"] = death_score
    
    # 4. Geographic Spread (weight: 0.15)
    countries = disease_data.get("countries_affected", 1) or 1
    if countries > 100:
        geo_score = 100
    elif countries > 50:
        geo_score = 80
    elif countries > 20:
        geo_score = 60
    elif countries > 5:
        geo_score = 40
    elif countries > 1:
        geo_score = 25
    else:
        geo_score = 10
    factors["geographic_spread"] = geo_score
    
    # 5. Source Agreement (weight: 0.10)
    sources = disease_data.get("sources_reporting", 1) or 1
    source_score = min(100, sources * 20)
    factors["source_agreement"] = source_score
    
    # 6. Historical Deviation (weight: 0.10)
    # Use percent change as a proxy if no historical baseline
    if abs(pct_change) > 50:
        hist_score = 90
    elif abs(pct_change) > 25:
        hist_score = 70
    elif abs(pct_change) > 10:
        hist_score = 50
    else:
        hist_score = 20
    factors["historical_deviation"] = hist_score
    
    # Weighted composite score
    weights = {
        "trend_acceleration": 0.25,
        "case_count_level": 0.20,
        "death_rate": 0.20,
        "geographic_spread": 0.15,
        "source_agreement": 0.10,
        "historical_deviation": 0.10,
    }
    
    risk_score = sum(factors[k] * weights[k] for k in weights)
    risk_score = round(min(100, max(0, risk_score)), 1)
    
    # Classify risk level
    if risk_score > 80:
        risk_level = "critical"
    elif risk_score > 60:
        risk_level = "high"
    elif risk_score > 40:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate explanation
    top_factors = sorted(factors.items(), key=lambda x: -x[1])[:3]
    factor_explanations = []
    for name, score in top_factors:
        if name == "trend_acceleration" and score > 50:
            factor_explanations.append(f"{'accelerating' if trend == 'accelerating' else 'rising'} case trend ({pct_change:+.1f}% change)")
        elif name == "case_count_level" and score > 50:
            factor_explanations.append(f"high case count ({total_cases:,} total)")
        elif name == "death_rate" and score > 50:
            factor_explanations.append(f"elevated case fatality rate ({cfr:.1f}%)")
        elif name == "geographic_spread" and score > 50:
            factor_explanations.append(f"widespread geographic distribution ({countries} countries)")
        elif name == "source_agreement" and score > 50:
            factor_explanations.append(f"confirmed by {sources} independent sources")
        elif name == "historical_deviation" and score > 50:
            factor_explanations.append(f"significant deviation from historical baseline")
    
    explanation = (
        f"{disease_name}{' in ' + country_code if country_code else ''} shows "
        f"{risk_level.upper()} risk (score: {risk_score}). "
    )
    if factor_explanations:
        explanation += "Contributing factors: " + ", ".join(factor_explanations) + "."
    
    return {
        "disease_name": disease_name,
        "country_code": country_code,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "factors": factors,
        "explanation": explanation,
    }
