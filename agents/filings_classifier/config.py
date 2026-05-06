"""Filings Classifier Agent configuration (S-03).

ADR-016: Haiku for classification.
ADR-027: hard ceilings on token and tool usage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FilingsClassifierConfig:
    model: str = "claude-3-5-haiku-20241022"
    max_tool_calls: int = 10
    max_tokens: int = 30000
    temperature: float = 0.0
    max_documents_per_run: int = 20
    max_financial_rows_per_document: int = 80
    max_text_chars: int = 50000
    max_table_rows_per_table: int = 40


def load_config() -> FilingsClassifierConfig:
    import os

    return FilingsClassifierConfig(
        max_tool_calls=int(os.getenv("FILINGS_CLASSIFIER_MAX_TOOL_CALLS", "10")),
        max_tokens=int(os.getenv("FILINGS_CLASSIFIER_MAX_TOKENS", "30000")),
    )

