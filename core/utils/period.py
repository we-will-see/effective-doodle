"""Indian fiscal period helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from core.exceptions import PeriodValidationError

FY_LABEL_RE = re.compile(r"^FY(?P<yy>\d{2})$")
QUARTER_LABEL_RE = re.compile(r"^(?P<q>[1-4])QFY(?P<yy>\d{2})$")
HALF_LABEL_RE = re.compile(r"^(?P<h>[12])HFY(?P<yy>\d{2})$")


@dataclass(frozen=True)
class PeriodInfo:
    label: str
    end_date: date


def fiscal_year_from_date(value: date) -> int:
    return value.year + 1 if value.month >= 4 else value.year


def fy_label_from_date(value: date) -> str:
    return f"FY{fiscal_year_from_date(value) % 100:02d}"


def _fy_start_year_from_label(label: str) -> int:
    match = FY_LABEL_RE.match(label)
    if not match:
        raise PeriodValidationError(f"invalid FY label: {label}")
    return 2000 + int(match.group("yy")) - 1


def period_end_date_from_label(label: str) -> date:
    if FY_LABEL_RE.match(label):
        year = _fy_start_year_from_label(label) + 1
        return date(year, 3, 31)
    if m := QUARTER_LABEL_RE.match(label):
        fy_start = _fy_start_year_from_label(f"FY{m.group('yy')}")
        quarter = int(m.group("q"))
        mapping = {
            1: date(fy_start, 6, 30),
            2: date(fy_start, 9, 30),
            3: date(fy_start, 12, 31),
            4: date(fy_start + 1, 3, 31),
        }
        return mapping[quarter]
    if m := HALF_LABEL_RE.match(label):
        fy_start = _fy_start_year_from_label(f"FY{m.group('yy')}")
        half = int(m.group("h"))
        return date(fy_start, 9, 30) if half == 1 else date(fy_start + 1, 3, 31)
    raise PeriodValidationError(f"invalid period label: {label}")


def period_label_from_date(value: date) -> str:
    if value.month == 3 and value.day == 31:
        return fy_label_from_date(value)
    if value.month == 6 and value.day == 30:
        return f"1Q{fy_label_from_date(value)}"
    if value.month == 9 and value.day == 30:
        return f"2Q{fy_label_from_date(value)}"
    if value.month == 12 and value.day == 31:
        return f"3Q{fy_label_from_date(value)}"
    raise PeriodValidationError(f"unsupported period end date: {value.isoformat()}")


def half_year_label_from_date(value: date) -> str:
    if value.month == 9 and value.day == 30:
        return f"H1{fy_label_from_date(value)}"
    if value.month == 3 and value.day == 31:
        return f"H2{fy_label_from_date(value)}"
    raise PeriodValidationError(f"unsupported half-year end date: {value.isoformat()}")


def validate_period(label: str, end_date: date) -> None:
    expected = period_end_date_from_label(label)
    if expected != end_date:
        raise PeriodValidationError(
            f"period_label {label} inconsistent with period_end_date {end_date.isoformat()}"
        )


def period_label_from_end_date(value: date) -> str:
    return period_label_from_date(value)


def period_info_from_label(label: str) -> PeriodInfo:
    return PeriodInfo(label=label, end_date=period_end_date_from_label(label))
