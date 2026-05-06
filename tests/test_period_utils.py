from datetime import date

import pytest

from core.exceptions import PeriodValidationError
from core.utils.period import (
    half_year_label_from_date,
    period_end_date_from_label,
    period_label_from_date,
    period_label_from_end_date,
    validate_period,
)


@pytest.mark.parametrize(
    ("label", "end_date"),
    [
        ("FY26", date(2026, 3, 31)),
        ("1QFY26", date(2025, 6, 30)),
        ("2QFY26", date(2025, 9, 30)),
        ("3QFY26", date(2025, 12, 31)),
        ("H1FY26", date(2025, 9, 30)),
        ("H2FY26", date(2026, 3, 31)),
    ],
)
def test_period_label_end_date_round_trip(label: str, end_date: date) -> None:
    assert period_end_date_from_label(label) == end_date
    validate_period(label, end_date)


def test_period_labels_from_end_dates() -> None:
    assert period_label_from_date(date(2026, 3, 31)) == "FY26"
    assert period_label_from_date(date(2025, 6, 30)) == "1QFY26"
    assert period_label_from_date(date(2025, 9, 30)) == "2QFY26"
    assert period_label_from_date(date(2025, 12, 31)) == "3QFY26"
    assert half_year_label_from_date(date(2025, 9, 30)) == "H1FY26"
    assert half_year_label_from_date(date(2026, 3, 31)) == "H2FY26"


def test_period_label_from_end_date_alias() -> None:
    assert period_label_from_end_date(date(2026, 3, 31)) == "FY26"


def test_invalid_period_rejected() -> None:
    with pytest.raises(PeriodValidationError):
        period_end_date_from_label("FY2026")

