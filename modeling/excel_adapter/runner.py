from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from core.types.sqlalchemy_models import Company, Financial, ReviewQueue, SourceProvenance, WorkflowRun
from core.utils.period import period_end_date_from_label

from .diff import compare_estimates
from .reader import WorkbookEstimate, read_workbook


@dataclass(frozen=True, slots=True)
class ExcelRunResult:
    company_id: str
    company_key: str
    workbook_path: str
    read_count: int
    queued_count: int
    diffs: list[dict[str, Any]]


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def _resolve_company(db_session: Session, company_key: str) -> Company | None:
    companies = db_session.scalars(select(Company)).all()
    key = _slugify(company_key)
    for company in companies:
        candidates = {_slugify(company.display_name), _slugify(company.legal_name), _slugify(company.bse_code)}
        if key in candidates:
            return company
    return None


def _last_persisted_estimates(db_session: Session, company_id) -> list[dict[str, Any]]:
    rows = db_session.scalars(
        select(Financial)
        .where(
            Financial.company_id == company_id,
            Financial.type == "our_estimate",
            Financial.is_active.is_(True),
        )
        .order_by(Financial.period_end_date.desc(), Financial.metric.asc())
    ).all()
    return [
        {
            "company_id": str(company_id),
            "period_label": row.period_label,
            "metric": row.metric,
            "scenario": row.scenario,
            "value": str(row.value),
            "financial_id": str(row.id),
        }
        for row in rows
    ]


def _queue_diff_bundle(
    db_session: Session,
    workflow_run: WorkflowRun,
    company: Company,
    workbook_path: Path,
    diffs: list[Any],
) -> int:
    bundle_id = uuid4()
    queued = 0
    for diff in diffs:
        estimate: WorkbookEstimate = diff.current
        source = SourceProvenance(
            source_type="excel_model",
            source_id=workbook_path.name,
            document_path=str(workbook_path),
            cell_reference=estimate.named_range,
            raw_text=str(estimate.raw_value) if estimate.raw_value is not None else None,
            extracted_by="openpyxl",
            extraction_confidence=Decimal("1.000"),
        )
        db_session.add(source)
        db_session.flush()

        current_state = diff.previous
        proposed_payload = {
            "company_id": str(company.id),
            "period_label": estimate.period,
            "period_end_date": period_end_date_from_label(estimate.period).isoformat(),
            "metric": estimate.metric,
            "value": str(estimate.value) if estimate.value is not None else None,
            "currency": "INR",
            "unit": "abs",
            "type": "our_estimate",
            "consolidation_basis": "consolidated",
            "accounting_policy_version": "v1",
            "scenario": estimate.scenario,
            "source_provenance": {
                "source_type": "excel_model",
                "source_id": workbook_path.name,
                "document_path": str(workbook_path),
                "cell_reference": estimate.named_range,
                "extracted_by": "openpyxl",
            },
            "notes": f"Imported from {estimate.named_range}",
        }
        db_session.add(
            ReviewQueue(
                tier=2,
                bundle_id=bundle_id,
                workflow_run_id=workflow_run.id,
                write_type="coverage.financials.proposed",
                target_schema="coverage",
                target_table="financials",
                target_row_id=None if current_state is None else current_state.get("financial_id"),
                proposed_payload=proposed_payload,
                current_state=current_state,
                source_provenance_id=source.id,
                confidence_score=Decimal("1.000"),
                verify_flags=["excel_model_diff"],
                state="pending_review",
                pending_since=datetime.now(timezone.utc),
            )
        )
        queued += 1
    return queued


def run_excel_adapter(db_session: Session, base_dir: str | Path = "/data/excel", created_by: str = "excel_adapter") -> dict[str, Any]:
    base_path = Path(base_dir)
    workflow_run = WorkflowRun(
        workflow_name="excel_adapter",
        workflow_version="s-04",
        triggered_by="system",
        status="running",
        input_params={"base_dir": str(base_path)},
        started_at=datetime.now(timezone.utc),
        tool_calls_count=0,
        tokens_used=0,
        cost_usd=Decimal("0"),
    )
    db_session.add(workflow_run)
    db_session.flush()

    results: list[ExcelRunResult] = []
    for company_dir in sorted([path for path in base_path.iterdir() if path.is_dir()]):
        company = _resolve_company(db_session, company_dir.name)
        if company is None:
            continue
        for workbook_path in sorted(company_dir.glob("*.xlsx")):
            current = read_workbook(workbook_path, str(company.id), company_dir.name)
            previous = _last_persisted_estimates(db_session, company.id)
            diffs = compare_estimates(current, previous)
            queued = _queue_diff_bundle(db_session, workflow_run, company, workbook_path, diffs) if diffs else 0
            results.append(
                ExcelRunResult(
                    company_id=str(company.id),
                    company_key=company_dir.name,
                    workbook_path=str(workbook_path),
                    read_count=len(current),
                    queued_count=queued,
                    diffs=[diff.to_dict() for diff in diffs],
                )
            )

    workflow_run.status = "completed"
    workflow_run.completed_at = datetime.now(timezone.utc)
    workflow_run.tool_calls_count = len(results)
    workflow_run.output_summary = {
        "companies_processed": len(results),
        "workbooks": [asdict(item) for item in results],
    }
    db_session.commit()
    return workflow_run.output_summary
