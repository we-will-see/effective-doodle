from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agents.filings_classifier.config import FilingsClassifierConfig, load_config
from agents.filings_classifier.output import ClassificationResult, ClassifiedFinancial, SourceProvenanceRef
from agents.variance_analysis import run_variance_analysis
from core.types.sqlalchemy_models import Classification, Document, ReviewQueue, WorkflowRun
from core.utils.logging import log_tool_call

logger = logging.getLogger(__name__)


class FilingsClassifierRunner:
    def __init__(self, config: Optional[FilingsClassifierConfig] = None):
        self.config = config or load_config()

    def get_pending_documents(self, db_session: Session) -> list[Document]:
        return (
            db_session.query(Document)
            .filter(Document.extraction_status == "extracted", Document.classification_status == "pending")
            .order_by(Document.filed_at.asc())
            .limit(self.config.max_documents_per_run)
            .all()
        )

    def _system_prompt(self) -> str:
        prompt_path = Path(__file__).with_name("prompt.md")
        return prompt_path.read_text(encoding="utf-8")

    def _format_table_rows(self, tables: Any) -> list[dict[str, Any]]:
        payload = tables or {}
        tables_out: list[dict[str, Any]] = []
        for idx, table in enumerate(payload.get("tables", [])):
            rows = table.get("sample") or []
            tables_out.append(
                {
                    "table_index": idx,
                    "page": table.get("page"),
                    "bbox": table.get("bbox"),
                    "sample_rows": rows[: self.config.max_table_rows_per_table],
                }
            )
        return tables_out

    def _build_user_payload(self, document: Document) -> dict[str, Any]:
        parsed_text = document.parsed_text or document.raw_text or ""
        return {
            "document_id": str(document.id),
            "company_id": str(document.company_id),
            "filing_title": document.filing_title,
            "filed_at": document.filed_at.isoformat(),
            "source_id": document.source_id,
            "parsed_text": parsed_text[: self.config.max_text_chars],
            "parsed_tables": self._format_table_rows(document.parsed_tables),
            "constraints": {
                "max_tool_calls": self.config.max_tool_calls,
                "max_tokens": self.config.max_tokens,
                "do_not_generate_numbers": True,
            },
        }

    def _call_claude(self, document: Document) -> dict[str, Any]:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic SDK is required for filings classifier") from exc

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=self._system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(self._build_user_payload(document), ensure_ascii=True),
                }
            ],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return {"response": response, "text": text}

    def _parse_result(self, document: Document, response_payload: dict[str, Any]) -> ClassificationResult:
        data = json.loads(response_payload["text"])
        data.setdefault("document_id", str(document.id))
        return ClassificationResult.model_validate(data)

    def _queue_financials(self, db_session: Session, document: Document, result: ClassificationResult, workflow_run_id: str) -> list[ReviewQueue]:
        items: list[ReviewQueue] = []
        bundle_id = uuid4()
        for fin in result.extracted_financials[: self.config.max_financial_rows_per_document]:
            payload = {
                "company_id": str(fin.company_id),
                "period_label": fin.period_label,
                "period_end_date": fin.period_end_date.isoformat(),
                "metric": fin.metric,
                "value": str(fin.value),
                "currency": fin.currency,
                "unit": fin.unit,
                "type": fin.type,
                "consolidation_basis": fin.consolidation_basis,
                "accounting_policy_version": fin.accounting_policy_version,
                "scenario": fin.scenario,
                "source_provenance": fin.source_provenance.model_dump(mode="json"),
                "confidence_score": str(fin.confidence_score) if fin.confidence_score is not None else None,
                "verify_flag": fin.verify_flag,
                "notes": fin.notes,
            }
            item = ReviewQueue(
                tier=2,
                bundle_id=bundle_id,
                workflow_run_id=workflow_run.id,
                write_type="coverage.financials.proposed",
                target_schema="coverage",
                target_table="financials",
                target_row_id=None,
                proposed_payload=payload,
                current_state=None,
                source_provenance_id=None,
                derivation_provenance_id=None,
                claim_provenance_id=None,
                confidence_score=fin.confidence_score,
                verify_flags=[f for f in result.verify_flags if f],
                state="pending_review",
                pending_since=datetime.now(timezone.utc),
            )
            db_session.add(item)
            items.append(item)
        return items

    def run(self, db_session: Session) -> dict[str, Any]:
        pending = self.get_pending_documents(db_session)
        if not pending:
            return {"processed": 0, "message": "No pending documents"}

        workflow_run = WorkflowRun(
            workflow_name="filings_classifier",
            workflow_version="s-03",
            triggered_by="system",
            status="running",
            tool_calls_count=0,
            tokens_used=0,
            cost_usd=Decimal("0"),
        )
        db_session.add(workflow_run)
        db_session.flush()

        results: list[dict[str, Any]] = []
        for call_index, document in enumerate(pending):
            started = datetime.now(timezone.utc).timestamp()
            try:
                response_payload = self._call_claude(document)
                log_tool_call(
                    db_session,
                    "anthropic.messages.create",
                    {"document_id": str(document.id), "model": self.config.model},
                    {"text_length": len(response_payload["text"])},
                    started,
                )
                classification = self._parse_result(document, response_payload)

                db_session.add(
                    Classification(
                        document_id=document.id,
                        classifier_version=self.config.model,
                        document_type=classification.document_type,
                        document_subtype=classification.document_subtype,
                        materiality_score=classification.materiality_score,
                        reasoning=classification.reasoning,
                        extracted_metrics={
                            "rows": [row.model_dump(mode="json") for row in classification.extracted_financials],
                            "verify_flags": classification.verify_flags,
                        },
                        workflow_run_id=workflow_run.id,
                    )
                )

                self._queue_financials(db_session, document, classification, str(workflow_run.id))
                document.document_type = classification.document_type
                document.document_subtype = classification.document_subtype
                document.classification_status = "classified"
                document.classified_at = datetime.now(timezone.utc)
                document.materiality_score = classification.materiality_score
                document.is_material = classification.materiality_score >= Decimal("0.5")

                detail: dict[str, Any] = {
                    "document_id": str(document.id),
                    "document_type": classification.document_type,
                    "queued_financial_rows": len(classification.extracted_financials),
                }
                if classification.document_type in {"results_announcement", "earnings_release"}:
                    try:
                        variance_result = run_variance_analysis(db_session, document.id)
                        detail["variance_analysis"] = {
                            "queue_item_id": variance_result["queue_item_id"],
                            "variant_perception": variance_result["variant_perception"],
                        }
                    except Exception as variance_exc:
                        logger.exception("variance analysis failed for document %s", document.id)
                        detail["variance_analysis_error"] = str(variance_exc)

                results.append(detail)
            except Exception as exc:
                logger.exception("filings classifier failed for document %s", document.id)
                results.append({"document_id": str(document.id), "error": str(exc)})

        workflow_run.status = "completed"
        workflow_run.completed_at = datetime.now(timezone.utc)
        workflow_run.tool_calls_count = len(results)
        workflow_run.tokens_used = 0
        workflow_run.cost_usd = Decimal("0")

        db_session.commit()
        logger.info("filings_classifier completed processed=%s", len(results))
        return {"processed": len(results), "details": results}


def run_filings_classifier(db_session: Session) -> dict[str, Any]:
    return FilingsClassifierRunner().run(db_session)
