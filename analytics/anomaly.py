"""
MedFusion — Anomaly Detection Module
Detects anomalies in time series data using rolling Z-scores.
"""

import numpy as np
from typing import List, Dict, Any


def detect_anomalies(
    time_series: List[Dict[str, Any]],
    window: int = 28,
    threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Detect anomalies in time series data using rolling Z-scores.
    
    For each data point, computes: z = (value - rolling_mean) / rolling_std
    If |z| > threshold, the point is flagged as anomalous.
    
    Args:
        time_series: List of dicts with 'date', 'value', 'disease_name' keys
        window: Rolling window size for computing stats
        threshold: Z-score threshold for anomaly flagging
        
    Returns:
        List of AnomalyAlert dicts
    """
    if not time_series or len(time_series) < window:
        return []

    # Sort by date
    sorted_data = sorted(time_series, key=lambda x: x.get("date", ""))
    values = np.array([float(d.get("value", 0)) for d in sorted_data])
    
    anomalies = []
    
    for i in range(window, len(values)):
        window_data = values[i - window: i]
        mean = np.mean(window_data)
        std = np.std(window_data)
        
        if std == 0:
            continue
        
        z_score = (values[i] - mean) / std
        abs_z = abs(z_score)
        
        if abs_z > threshold:
            # Classify severity
            if abs_z > 3.0:
                severity = "critical"
            elif abs_z > 2.5:
                severity = "high"
            else:
                severity = "medium"
            
            point = sorted_data[i]
            direction = "above" if z_score > 0 else "below"
            
            disease = point.get("disease_name", "Unknown")
            country = point.get("country_code", "")
            date = point.get("date", "")
            
            anomalies.append({
                "disease_name": disease,
                "country_code": country,
                "date": date,
                "observed_value": float(values[i]),
                "expected_value": round(float(mean), 2),
                "z_score": round(float(z_score), 2),
                "severity": severity,
                "message": (
                    f"Anomaly detected: {disease} in {country or 'global'} on {date}. "
                    f"Observed value ({values[i]:,.0f}) is {abs_z:.1f} standard deviations "
                    f"{direction} the {window}-day rolling average ({mean:,.0f}). "
                    f"Severity: {severity.upper()}"
                ),
            })
    
    return anomalies
