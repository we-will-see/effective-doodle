from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from agents.variance_analysis.config import VarianceAnalysisConfig, load_config
from agents.variance_analysis.output import EvidenceDeltaItem, VarianceAnalysisResult, VarianceComparison, VarianceFacts
from core.tools.get_drivers import get_drivers
from core.tools.get_thesis import get_thesis
from core.tools.query_financials import query_financials
from core.tools.schemas import CompanyQueryIn, FinancialQueryIn
from core.types.sqlalchemy_models import ClaimProvenance, Company, Document, Financial, ReviewQueue, WorkflowRun
from core.utils.logging import log_tool_call

logger = logging.getLogger(__name__)


class VarianceAnalysisRunner:
    def __init__(self, config: Optional[VarianceAnalysisConfig] = None):
        self.config = config or load_config()

    def _system_prompt(self) -> str:
        return Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")

    def _call_claude(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic SDK is required for variance analysis") from exc

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._system_prompt(),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=True)}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return {"response": response, "text": text}

    def _latest_actual_period(self, db_session: Session, company_id) -> list[Financial]:
        stmt = (
            select(Financial)
            .where(Financial.company_id == company_id, Financial.type == "actual", Financial.is_active.is_(True))
            .order_by(desc(Financial.period_end_date), Financial.metric)
        )
        return list(db_session.scalars(stmt).all())

    def _build_payload(self, db_session: Session, document: Document) -> dict[str, Any]:
        company = db_session.get(Company, document.company_id)
        if company is None:
            raise LookupError(f"company not found for document {document.id}")

        actuals = self._latest_actual_period(db_session, company.id)[: self.config.max_metrics_per_run]
        if not actuals:
            raise LookupError(f"no actual financials found for company {company.id}")

        period_end_date = actuals[0].period_end_date
        period_label = actuals[0].period_label

        consensus_rows = query_financials(FinancialQueryIn(company_id=company.id, period_label=period_label, type="consensus"), db_session)
        our_estimate_rows = query_financials(FinancialQueryIn(company_id=company.id, period_label=period_label, type="our_estimate"), db_session)
        driver_rows = get_drivers(CompanyQueryIn(company_id=company.id), db_session)
        thesis = get_thesis(CompanyQueryIn(company_id=company.id), db_session)

        return {
            "document_id": str(document.id),
            "company": {
                "company_id": str(company.id),
                "display_name": company.display_name,
                "sector": company.sector,
            },
            "period": {"period_label": period_label, "period_end_date": period_end_date.isoformat()},
            "actuals": [
                {
                    "financial_id": str(row.id),
                    "metric": row.metric,
                    "value": str(row.value),
                    "currency": row.currency,
                    "unit": row.unit,
                    "source_provenance_id": str(row.source_provenance_id) if row.source_provenance_id else None,
                    "claim_provenance_id": str(row.claim_provenance_id) if row.claim_provenance_id else None,
                }
                for row in actuals
            ],
            "consensus": [row.model_dump(mode="json") for row in consensus_rows[: self.config.max_metrics_per_run]],
            "our_estimates": [row.model_dump(mode="json") for row in our_estimate_rows[: self.config.max_metrics_per_run]],
            "drivers": [row.model_dump(mode="json") for row in driver_rows[: self.config.max_driver_rows]],
            "thesis": thesis.model_dump(mode="json"),
            "constraints": {
                "max_tool_calls": self.config.max_tool_calls,
                "max_tokens": self.config.max_tokens,
                "traceable_numbers_only": True,
                "variant_perception_policy": "found_not_framed",
            },
        }

    def _parse_result(self, response_payload: dict[str, Any], document: Document) -> VarianceAnalysisResult:
        data = json.loads(response_payload["text"])
        data.setdefault("facts", {})
        data["facts"].setdefault("document_id", str(document.id))
        return VarianceAnalysisResult.model_validate(data)

    def _format_markdown(self, result: VarianceAnalysisResult, company_name: str) -> str:
        lines = [f"# Variance Note — {company_name}", "", "## Facts"]
        facts = result.facts
        lines.append(f"- Period: {facts.period_label or '[VERIFY]'}")
        lines.append(f"- Actual rows: {len(facts.actuals)}")
        lines.append("")
        lines.append("## Consensus")
        for row in result.consensus_comparison:
            lines.append(f"- {row.metric}: actual {row.actual_value} vs consensus {row.estimate_value if row.estimate_value is not None else '[VERIFY]'}")
        lines.append("")
        lines.append("## Our Prior")
        for row in result.our_estimate_comparison:
            lines.append(f"- {row.metric}: actual {row.actual_value} vs our estimate {row.estimate_value if row.estimate_value is not None else '[VERIFY]'}")
        lines.append("")
        lines.append("## Delta")
        for item in result.evidence_delta:
            lines.append(f"- {item.driver_name}: {item.relationship or '[VERIFY]'}")
        lines.append("")
        lines.append("## Variant Perception")
        lines.append(result.variant_perception)
        if result.key_findings:
            lines.append("")
            lines.append("## Key Findings")
            for finding in result.key_findings:
                lines.append(f"- {finding}")
        return "\n".join(lines)

    def _queue_review(self, db_session: Session, workflow_run: WorkflowRun, document: Document, result: VarianceAnalysisResult, markdown_note: str) -> ReviewQueue:
        claim = ClaimProvenance(
            claim_text=markdown_note,
            evidence={
                "document_id": str(document.id),
                "facts": result.facts.model_dump(mode="json"),
                "consensus_comparison": [row.model_dump(mode="json") for row in result.consensus_comparison],
                "our_estimate_comparison": [row.model_dump(mode="json") for row in result.our_estimate_comparison],
                "evidence_delta": [row.model_dump(mode="json") for row in result.evidence_delta],
            },
            workflow_run_id=workflow_run.id,
            synthesised_by="variance_analysis@S-05",
        )
        db_session.add(claim)
        db_session.flush()

        payload = {
            "document_id": str(document.id),
            "company_id": str(document.company_id),
            "markdown_note": markdown_note,
            "variance_summary": result.model_dump(mode="json"),
            "claim_provenance_id": str(claim.id),
        }
        queue_item = ReviewQueue(
            tier=3,
            bundle_id=uuid4(),
            workflow_run_id=workflow_run.id,
            write_type="coverage.variance_note.proposed",
            target_schema="coverage",
            target_table="claim_provenance",
            target_row_id=str(claim.id),
            proposed_payload=payload,
            current_state=None,
            source_provenance_id=None,
            derivation_provenance_id=None,
            claim_provenance_id=claim.id,
            confidence_score=None,
            verify_flags=result.verify_flags,
            state="pending_review",
            pending_since=datetime.now(timezone.utc),
        )
        db_session.add(queue_item)
        return queue_item

    def run_for_document(self, db_session: Session, document_id) -> dict[str, Any]:
        document = db_session.get(Document, document_id)
        if document is None:
            raise LookupError(f"document not found: {document_id}")

        workflow_run = WorkflowRun(
            workflow_name="variance_analysis",
            workflow_version="s-05",
            triggered_by="system",
            triggered_by_detail=f"filings_classifier:{document.id}",
            input_params={"document_id": str(document.id)},
            status="running",
            started_at=datetime.now(timezone.utc),
            tool_calls_count=0,
            tokens_used=0,
            cost_usd=Decimal("0"),
        )
        db_session.add(workflow_run)
        db_session.flush()

        started = datetime.now(timezone.utc).timestamp()
        response_payload = self._call_claude(self._build_payload(db_session, document))
        log_tool_call(
            db_session,
            "anthropic.messages.create",
            {"document_id": str(document.id), "model": self.config.model},
            {"text_length": len(response_payload["text"])},
            started,
        )
        result = self._parse_result(response_payload, document)
        company = db_session.get(Company, document.company_id)
        markdown_note = self._format_markdown(result, company.display_name if company else "Unknown")
        queue_item = self._queue_review(db_session, workflow_run, document, result, markdown_note)

        workflow_run.status = "completed"
        workflow_run.completed_at = datetime.now(timezone.utc)
        workflow_run.output_summary = {
            "document_id": str(document.id),
            "company_id": str(document.company_id),
            "variant_perception": result.variant_perception,
            "key_findings": result.key_findings,
            "queue_item_id": str(queue_item.id),
        }
        workflow_run.tool_calls_count = 4
        workflow_run.tokens_used = 0
        workflow_run.cost_usd = Decimal("0")
        db_session.commit()

        return {
            "document_id": str(document.id),
            "workflow_run_id": str(workflow_run.id),
            "queue_item_id": str(queue_item.id),
            "variant_perception": result.variant_perception,
            "key_findings": result.key_findings,
            "verify_flags": result.verify_flags,
            "markdown_note": markdown_note,
        }


def run_variance_analysis(db_session: Session, document_id) -> dict[str, Any]:
    return VarianceAnalysisRunner().run_for_document(db_session, document_id)
