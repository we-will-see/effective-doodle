from __future__ import annotations

import re
from dataclasses import dataclass

SCENARIOS = ("base", "bull", "bear")
EXCEL_MODEL_NAMED_RANGE_PATTERN = re.compile(
    r"^(?P<metric>[a-z][a-z0-9_]*)_(?P<period>(?:FY\d{2}|[1-4]QFY\d{2}|H[12]FY\d{2}))_(?P<scenario>base|bull|bear)$"
)


@dataclass(frozen=True, slots=True)
class NamedRangeParts:
    metric: str
    period: str
    scenario: str


def validate_metric(metric: str) -> str:
    if not metric or metric != metric.lower() or not re.fullmatch(r"[a-z][a-z0-9_]*", metric):
        raise ValueError(f"invalid metric: {metric!r}")
    return metric


def validate_period(period: str) -> str:
    if not period or not re.fullmatch(r"(?:FY\d{2}|[1-4]QFY\d{2}|H[12]FY\d{2})", period):
        raise ValueError(f"invalid period: {period!r}")
    return period


def validate_scenario(scenario: str) -> str:
    if scenario not in SCENARIOS:
        raise ValueError(f"invalid scenario: {scenario!r}")
    return scenario


def parse_named_range(name: str) -> NamedRangeParts:
    match = EXCEL_MODEL_NAMED_RANGE_PATTERN.fullmatch(name or "")
    if not match:
        raise ValueError(f"invalid named range: {name!r}")
    metric = validate_metric(match.group("metric"))
    period = validate_period(match.group("period"))
    scenario = validate_scenario(match.group("scenario"))
    return NamedRangeParts(metric=metric, period=period, scenario=scenario)


def validate_named_range(name: str) -> NamedRangeParts:
    return parse_named_range(name)


def build_named_range(metric: str, period: str, scenario: str) -> str:
    metric = validate_metric(metric)
    period = validate_period(period)
    scenario = validate_scenario(scenario)
    return f"{metric}_{period}_{scenario}"
