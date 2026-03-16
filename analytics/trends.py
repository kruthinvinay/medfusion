"""
MedFusion — Trend Analysis Module
Provides time series trend analysis, moving averages, and classification.
"""

import numpy as np
from typing import List, Dict, Any, Optional


def calculate_moving_average(values: List[float], window: int) -> List[Optional[float]]:
    """
    Calculate moving average over a list of values.
    
    Args:
        values: List of numeric values
        window: Window size for the moving average
        
    Returns:
        List of moving average values (None for positions with insufficient data)
    """
    if not values or window <= 0:
        return []
    
    result = [None] * len(values)
    for i in range(window - 1, len(values)):
        window_values = values[i - window + 1: i + 1]
        result[i] = round(sum(window_values) / len(window_values), 2)
    return result


def classify_trend(values: List[float]) -> str:
    """
    Classify trend direction using linear regression slope.
    
    Returns: "rising", "falling", "stable", or "accelerating"
    """
    if not values or len(values) < 3:
        return "stable"
    
    arr = np.array(values, dtype=float)
    x = np.arange(len(arr))
    
    # Remove NaN/inf values
    mask = np.isfinite(arr)
    if mask.sum() < 3:
        return "stable"
    
    x_clean = x[mask]
    y_clean = arr[mask]
    
    # Linear regression
    try:
        coeffs = np.polyfit(x_clean, y_clean, 1)
        slope = coeffs[0]
        mean_val = np.mean(y_clean)
        
        if mean_val == 0:
            return "stable"
        
        relative_slope = slope / abs(mean_val)
        
        # Check for acceleration (quadratic fit)
        if len(y_clean) >= 5:
            coeffs2 = np.polyfit(x_clean, y_clean, 2)
            accel = coeffs2[0]
            if abs(accel) > abs(slope) * 0.1 and accel > 0 and slope > 0:
                return "accelerating"
        
        if relative_slope > 0.05:
            return "rising"
        elif relative_slope < -0.05:
            return "falling"
        else:
            return "stable"
    except Exception:
        return "stable"


def calculate_trend(data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze a time series and return trend information.
    
    Args:
        data_points: List of dicts with 'date' and 'value' keys
        
    Returns:
        Dict with trend_direction, percent_change, moving_averages, etc.
    """
    if not data_points:
        return {
            "trend_direction": "stable",
            "percent_change_wow": 0.0,
            "percent_change_mom": 0.0,
            "moving_avg_7": [],
            "moving_avg_14": [],
            "moving_avg_28": [],
            "data_count": 0,
        }
    
    # Sort by date
    sorted_points = sorted(data_points, key=lambda x: x.get("date", ""))
    values = [p.get("value", 0) for p in sorted_points]
    
    # Trend direction
    trend = classify_trend(values)
    
    # Percent changes
    wow = _percent_change(values, 7)
    mom = _percent_change(values, 30)
    
    # Moving averages
    ma7 = calculate_moving_average(values, 7)
    ma14 = calculate_moving_average(values, 14)
    ma28 = calculate_moving_average(values, 28)
    
    return {
        "trend_direction": trend,
        "percent_change_wow": round(wow, 2) if wow is not None else 0.0,
        "percent_change_mom": round(mom, 2) if mom is not None else 0.0,
        "moving_avg_7": ma7,
        "moving_avg_14": ma14,
        "moving_avg_28": ma28,
        "data_count": len(values),
        "min_value": min(values) if values else 0,
        "max_value": max(values) if values else 0,
        "latest_value": values[-1] if values else 0,
    }


def _percent_change(values: List[float], period: int) -> Optional[float]:
    """Calculate percent change over a given period."""
    if len(values) < period + 1:
        return None
    
    old_val = values[-period - 1]
    new_val = values[-1]
    
    if old_val == 0:
        return 100.0 if new_val > 0 else 0.0
    
    return ((new_val - old_val) / abs(old_val)) * 100
