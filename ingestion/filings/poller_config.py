"""BSE poller configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any


@dataclass
class BSEPollerConfig:
    """Configuration for BSE filings poller."""
    
    # API endpoints
    announcements_url: str = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    
    # Rate limiting
    requests_per_second: float = 1.0
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    
    # Polling schedule
    market_open_time: time = time(9, 0)  # 9:00 AM IST
    market_close_time: time = time(16, 0)  # 4:00 PM IST
    market_hours_interval_minutes: int = 60  # Poll every hour during market
    off_hours_interval_minutes: int = 240  # Poll every 4 hours off-market
    
    # Data paths
    raw_storage_path: str = "/data/raw/bse"
    
    # Coverage universe (BSE codes to monitor)
    # Default: 8 pharma names - to be configured
    coverage_universe: list[str] = None
    
    def __post_init__(self):
        if self.coverage_universe is None:
            # Default coverage: major Indian pharma companies
            # To be replaced with actual BSE codes from coverage.companies
            self.coverage_universe = []


def load_config_from_env() -> BSEPollerConfig:
    """Load configuration from environment variables."""
    import os
    
    coverage = os.environ.get("BSE_COVERAGE_UNIVERSE", "").split(",")
    coverage = [c.strip() for c in coverage if c.strip()]
    
    return BSEPollerConfig(
        coverage_universe=coverage or [],
    )
