from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from openpyxl import load_workbook

from .conventions import NamedRangeParts, parse_named_range, validate_named_range


@dataclass(frozen=True, slots=True)
class WorkbookEstimate:
    company_id: str
    company_key: str
    workbook_path: str
    worksheet: str
    named_range: str
    metric: str
    period: str
    scenario: str
    value: Decimal | float | int | str | None
    cell_reference: str | None
    raw_value: Any

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if isinstance(self.value, Decimal):
            payload["value"] = str(self.value)
        return payload


def _coerce_value(value: Any) -> Decimal | float | int | str | None:
    if value is None:
        return None
    if isinstance(value, (Decimal, int, float, str)):
        return value
    return str(value)


def _destination_reference(dests: list[Any]) -> str | None:
    if not dests:
        return None
    dest = dests[0]
    sheet = getattr(dest, "sheet_name", None)
    coord = getattr(dest, "coord", None)
    if sheet and coord:
        return f"{sheet}!{coord}"
    if coord:
        return str(coord)
    return None


class ExcelModelReader:
    def __init__(self, workbook_path: str | Path, company_id: str, company_key: str):
        self.workbook_path = Path(workbook_path)
        self.company_id = company_id
        self.company_key = company_key

    def read(self) -> list[WorkbookEstimate]:
        workbook = load_workbook(self.workbook_path, data_only=True, read_only=False)
        estimates: list[WorkbookEstimate] = []
        for defined_name in workbook.defined_names.values():
            name = getattr(defined_name, "name", None) or getattr(defined_name, "name", "")
            if not name:
                continue
            try:
                parts = validate_named_range(name)
            except ValueError:
                continue
            destinations = list(defined_name.destinations)
            for sheet_name, cell_ref in destinations:
                worksheet = workbook[sheet_name]
                value = worksheet[cell_ref].value
                estimates.append(
                    WorkbookEstimate(
                        company_id=self.company_id,
                        company_key=self.company_key,
                        workbook_path=str(self.workbook_path),
                        worksheet=sheet_name,
                        named_range=name,
                        metric=parts.metric,
                        period=parts.period,
                        scenario=parts.scenario,
                        value=_coerce_value(value),
                        cell_reference=f"{sheet_name}!{cell_ref}",
                        raw_value=value,
                    )
                )
        return estimates


def read_workbook(workbook_path: str | Path, company_id: str, company_key: str) -> list[WorkbookEstimate]:
    return ExcelModelReader(workbook_path, company_id, company_key).read()
