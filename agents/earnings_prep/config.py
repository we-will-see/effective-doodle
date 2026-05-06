"""Earnings Prep Agent configuration (S-07).

ADR-015: Sonnet for synthesis with strict token ceilings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EarningsPrepConfig:
    model: str = "claude-3-5-sonnet-20241022"
    max_tool_calls: int = 12
    max_tokens: int = 12000
    temperature: float = 0.0
    max_financial_rows: int = 24
    max_recent_filings: int = 5
    max_driver_rows: int = 12
    max_catalyst_rows: int = 8
    max_thesis_chars: int = 16000
    max_text_chars: int = 30000


def load_config() -> EarningsPrepConfig:
    import os

    return EarningsPrepConfig(
        max_tool_calls=int(os.getenv("EARNINGS_PREP_MAX_TOOL_CALLS", "12")),
        max_tokens=int(os.getenv("EARNINGS_PREP_MAX_TOKENS", "12000")),
    )
