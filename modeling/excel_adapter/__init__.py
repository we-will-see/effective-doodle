"""Excel adapter for analyst-maintained financial models."""

from .conventions import (
    EXCEL_MODEL_NAMED_RANGE_PATTERN,
    SCENARIOS,
    NamedRangeParts,
    build_named_range,
    parse_named_range,
    validate_metric,
    validate_named_range,
    validate_period,
    validate_scenario,
)
from .diff import compare_estimates, diff_estimates
from .reader import ExcelModelReader, WorkbookEstimate, read_workbook

__all__ = [
    "EXCEL_MODEL_NAMED_RANGE_PATTERN",
    "SCENARIOS",
    "NamedRangeParts",
    "build_named_range",
    "parse_named_range",
    "validate_metric",
    "validate_named_range",
    "validate_period",
    "validate_scenario",
    "compare_estimates",
    "diff_estimates",
    "ExcelModelReader",
    "WorkbookEstimate",
    "read_workbook",
]

