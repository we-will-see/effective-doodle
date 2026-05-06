"""Daily Briefing Agent configuration (S-08).

Produces a digest of queue depth, staleness, open variances, 
thesis-contradictory signals from prior 24h.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass
class DailyBriefingConfig:
    """Configuration for daily briefing agent."""
    
    # Model config per ADR-016
    model: str = "claude-3-5-sonnet-20241022"  # Sonnet for synthesis
    max_tokens: int = 4000
    temperature: float = 0.3
    
    # Scheduling
    cron_hour: int = 7  # 7 AM
    cron_minute: int = 0
    timezone: str = "Asia/Kolkata"  # IST
    
    # Output constraints
    max_words: int = 500  # One screen
    
    # Sections to include
    include_queue_depth: bool = True
    include_stale_items: bool = True
    include_recent_variance: bool = True
    include_thesis_signals: bool = True
    
    # Thresholds
    stale_days_threshold: int = 3
    max_stale_items: int = 3
    max_thesis_signals: int = 3


def load_config() -> DailyBriefingConfig:
    """Load configuration."""
    import os
    
    return DailyBriefingConfig(
        max_words=int(os.getenv("BRIEFING_MAX_WORDS", "500")),
        stale_days_threshold=int(os.getenv("BRIEFING_STALE_DAYS", "3")),
    )
