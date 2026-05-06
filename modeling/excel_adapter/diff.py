from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .reader import WorkbookEstimate


@dataclass(frozen=True, slots=True)
class EstimateDiff:
    key: tuple[str, str, str, str]
    current: WorkbookEstimate
    previous: dict[str, Any] | None
    delta: Decimal | None
    pct_change: Decimal | None
    is_new: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": list(self.key),
            "current": self.current.to_dict(),
            "previous": self.previous,
            "delta": str(self.delta) if self.delta is not None else None,
            "pct_change": str(self.pct_change) if self.pct_change is not None else None,
            "is_new": self.is_new,
        }


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _match_key(item: WorkbookEstimate | dict[str, Any]) -> tuple[str, str, str, str]:
    if isinstance(item, WorkbookEstimate):
        return (item.company_id, item.period, item.metric, item.scenario)
    return (
        str(item["company_id"]),
        str(item["period_label"]),
        str(item["metric"]),
        str(item.get("scenario", "base")),
    )


def compare_estimates(
    current: list[WorkbookEstimate],
    last_persisted: list[dict[str, Any]],
) -> list[EstimateDiff]:
    previous_map = {_match_key(row): row for row in last_persisted}
    diffs: list[EstimateDiff] = []
    for estimate in current:
        key = _match_key(estimate)
        previous = previous_map.get(key)
        current_value = _as_decimal(estimate.value)
        previous_value = _as_decimal(previous["value"]) if previous else None
        if previous is not None and current_value == previous_value:
            continue
        delta = None
        pct_change = None
        is_new = previous is None
        if current_value is not None and previous_value is not None:
            delta = current_value - previous_value
            if previous_value != 0:
                pct_change = delta / previous_value
        diffs.append(EstimateDiff(key=key, current=estimate, previous=previous, delta=delta, pct_change=pct_change, is_new=is_new))
    return diffs


def diff_estimates(current: list[WorkbookEstimate], last_persisted: list[dict[str, Any]]) -> list[EstimateDiff]:
    return compare_estimates(current, last_persisted)
