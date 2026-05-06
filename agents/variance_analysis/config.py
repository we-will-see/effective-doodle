"""Variance Analysis Agent configuration (S-05).

ADR-016: Sonnet for synthesis.
ADR-027: hard ceilings on token and tool usage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VarianceAnalysisConfig:
    model: str = "claude-3-5-sonnet-20241022"
    max_tool_calls: int = 15
    max_tokens: int = 100000
    temperature: float = 0.0
    max_metrics_per_run: int = 20
    max_text_chars: int = 50000
    max_driver_rows: int = 20
    max_thesis_chars: int = 20000


def load_config() -> VarianceAnalysisConfig:
    import os

    return VarianceAnalysisConfig(
        max_tool_calls=int(os.getenv("VARIANCE_ANALYSIS_MAX_TOOL_CALLS", "15")),
        max_tokens=int(os.getenv("VARIANCE_ANALYSIS_MAX_TOKENS", "100000")),
    )
