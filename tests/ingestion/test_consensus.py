from __future__ import annotations

from datetime import date

import pytest

from ingestion.consensus.runner import ConsensusRunner, ConsensusRunnerConfig
from ingestion.consensus.visible_alpha import VisibleAlphaClient


def test_extract_rows_handles_common_envelopes() -> None:
    payload = {"data": [{"period_label": "1QFY26", "metric": "revenue", "value": 123}]}
    assert VisibleAlphaClient.extract_rows(payload) == payload["data"]


def test_extract_rows_handles_flat_payload() -> None:
    payload = {"period_label": "1QFY26", "metric": "revenue", "value": 123}
    assert VisibleAlphaClient.extract_rows(payload) == [payload]


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 4, 1), True),
        (date(2026, 8, 15), False),
    ],
)
def test_earnings_season_detection(today: date, expected: bool) -> None:
    runner = ConsensusRunner(config=ConsensusRunnerConfig(earnings_season_days=21), client=object())
    assert runner.is_earnings_season(today) is expected

