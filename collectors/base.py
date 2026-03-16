"""
MedFusion — Abstract Base Collector
All source-specific collectors inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
import time
import logging

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all data source collectors."""
    
    source_name: str = "unknown"
    display_name: str = "Unknown Source"
    source_type: str = "api"  # "api", "rss", "csv", "scraper"
    base_url: str = ""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "MedFusion/1.0 Disease Surveillance Platform"}
        )
        self.last_fetch_time = None
        self.records_fetched = 0
        self.status = "unknown"
        self.error_message = None
        self.response_time_ms = None
        self._events = []
        self._time_series = []
        self._alerts = []

    @abstractmethod
    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch raw data from the source. Must be implemented by each collector."""
        pass

    @abstractmethod
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize raw data into unified SurveillanceEvent format."""
        pass

    async def collect(self) -> List[Dict[str, Any]]:
        """Main collection method. Fetches, normalizes, and returns unified events."""
        start_time = time.time()
        try:
            logger.info(f"[{self.source_name}] Starting data collection...")
            raw_data = await self.fetch_raw()
            normalized = self.normalize(raw_data)

            elapsed = (time.time() - start_time) * 1000
            self.response_time_ms = round(elapsed, 2)
            self.records_fetched = len(normalized)
            self.status = "active"
            self.error_message = None
            self.last_fetch_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._events = normalized

            logger.info(f"[{self.source_name}] ✅ Collected {len(normalized)} records in {elapsed:.0f}ms")
            return normalized

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            self.response_time_ms = round(elapsed, 2)
            self.status = "error"
            self.error_message = str(e)
            logger.error(f"[{self.source_name}] ❌ Error: {e}")
            return []

    def get_health(self) -> dict:
        """Return health status for this source."""
        return {
            "source_name": self.source_name,
            "display_name": self.display_name,
            "source_type": self.source_type,
            "status": self.status,
            "last_successful_fetch": self.last_fetch_time,
            "records_fetched": self.records_fetched,
            "total_records": self.records_fetched,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
        }

    def get_time_series(self) -> List[Dict[str, Any]]:
        """Return time series records generated during collection."""
        return self._time_series

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Return alert records generated during collection."""
        return self._alerts

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
