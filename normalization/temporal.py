"""
MedFusion — Temporal Normalization
Handles date format normalization from various source formats.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Optional
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

# MMWR week to approximate date mapping helper
def _mmwr_week_to_date(year: int, week: int) -> str:
    """Convert MMWR year and week to approximate ISO date."""
    from datetime import timedelta
    jan1 = datetime(year, 1, 1)
    # MMWR week 1 starts on first Sunday of January
    day_offset = (6 - jan1.weekday()) % 7
    week1_start = jan1 + timedelta(days=day_offset)
    target = week1_start + timedelta(weeks=week - 1)
    return target.strftime("%Y-%m-%dT00:00:00Z")


def normalize_date(raw_date) -> Optional[str]:
    """
    Normalize a date from various formats into ISO 8601 format.
    
    Handles:
    - ISO format: "2025-03-15" or "2025-03-15T10:30:00Z"
    - US format: "03/15/2025"
    - European format: "15/03/2025"
    - Text format: "March 15, 2025"
    - MMWR week: "Week 11, 2025"
    - Unix timestamps (integers or floats)
    - RSS date formats: "Sun, 15 Mar 2025 10:00:00 GMT"
    - Year-only: "2025"
    
    Returns:
        ISO 8601 date string or None if parsing fails
    """
    if raw_date is None:
        return None

    # Handle numeric timestamps
    if isinstance(raw_date, (int, float)):
        try:
            if raw_date > 1e12:  # milliseconds
                raw_date = raw_date / 1000
            dt = datetime.fromtimestamp(raw_date, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OSError, OverflowError):
            return None

    raw = str(raw_date).strip()
    if not raw:
        return None

    # MMWR week format: "Week 11, 2025" or "MMWR Week 11 2025"
    mmwr_match = re.match(r'(?:MMWR\s+)?Week\s+(\d+)[,\s]+(\d{4})', raw, re.IGNORECASE)
    if mmwr_match:
        week = int(mmwr_match.group(1))
        year = int(mmwr_match.group(2))
        return _mmwr_week_to_date(year, week)

    # Year only
    if re.match(r'^\d{4}$', raw):
        return f"{raw}-01-01T00:00:00Z"

    # Year-month only
    ym_match = re.match(r'^(\d{4})-(\d{2})$', raw)
    if ym_match:
        return f"{raw}-01T00:00:00Z"

    # European format DD/MM/YYYY — try to detect
    eu_match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', raw)
    if eu_match:
        day, month, year = int(eu_match.group(1)), int(eu_match.group(2)), int(eu_match.group(3))
        if day > 12:
            # Definitely day/month/year
            try:
                dt = datetime(year, month, day)
                return dt.strftime("%Y-%m-%dT00:00:00Z")
            except ValueError:
                pass

    # Try dateutil parser (handles most formats)
    try:
        dt = dateutil_parser.parse(raw, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, dateutil_parser.ParserError):
        pass

    logger.debug(f"Could not parse date: {raw_date}")
    return None


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_date(dt: datetime) -> str:
    """Format a datetime object to ISO 8601 string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
