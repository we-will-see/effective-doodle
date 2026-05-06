from __future__ import annotations

from decimal import Decimal

import pytest

from modeling.excel_adapter.conventions import build_named_range, parse_named_range, validate_named_range
from modeling.excel_adapter.diff import compare_estimates
from modeling.excel_adapter.reader import WorkbookEstimate


def test_named_range_parsing_round_trip() -> None:
    name = build_named_range("revenue", "FY26", "base")
    parts = parse_named_range(name)
    assert parts.metric == "revenue"
    assert parts.period == "FY26"
    assert parts.scenario == "base"
    assert validate_named_range("ebitda_1QFY27_bull").scenario == "bull"


def test_named_range_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError):
        validate_named_range("Revenue_FY26_base")


def test_compare_estimates_only_returns_changes() -> None:
    current = [
        WorkbookEstimate(
            company_id="c1",
            company_key="lauruslabs",
            workbook_path="/data/excel/laurus/model.xlsx",
            worksheet="Sheet1",
            named_range="revenue_FY26_base",
            metric="revenue",
            period="FY26",
            scenario="base",
            value=Decimal("100"),
            cell_reference="Sheet1!B2",
            raw_value=100,
        )
    ]
    previous = [{"company_id": "c1", "period_label": "FY26", "metric": "revenue", "scenario": "base", "value": "90"}]
    diffs = compare_estimates(current, previous)
    assert len(diffs) == 1
    assert diffs[0].delta == Decimal("10")
    assert diffs[0].pct_change == Decimal("10") / Decimal("90")
