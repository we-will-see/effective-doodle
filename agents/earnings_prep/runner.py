from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from agents.earnings_prep.config import EarningsPrepConfig, load_config
from agents.earnings_prep.output import EarningsPrepResult
from core.tools.get_catalysts import get_catalysts
from core.tools.get_consensus import get_consensus
from core.tools.get_drivers import get_drivers
from core.tools.get_thesis import get_thesis
from core.tools.query_companies import query_companies
from core.tools.query_financials import query_financials
from core.tools.schemas import CatalystQueryIn, CompanyQueryIn, ConsensusQueryIn, FinancialQueryIn, FilingSearchIn
from core.tools.search_filings import search_filings
from core.types.sqlalchemy_models import Company, ReviewQueue, WorkflowRun
from core.utils.logging import log_tool_call

logger = logging.getLogger(__name__)


class EarningsPrepRunner:
    def __init__(self, config: Optional[EarningsPrepConfig] = None):
        self.config = config or load_config()

    def _system_prompt(self) -> str:
        return Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")

    def _call_claude(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic SDK is required for earnings prep") from exc

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

    def _resolve_company(self, db_session: Session, company_id: Optional[str], company_query: Optional[str]) -> Company:
        if company_id:
            company = db_session.get(Company, company_id)
            if company is None:
                raise LookupError(f"company not found: {company_id}")
            return company

        if company_query:
            matches = query_companies(CompanyQueryIn(), db_session)
            for company in matches:
                if company_query.lower() in company.display_name.lower() or company_query.lower() in company.legal_name.lower():
                    return db_session.get(Company, company.id) or Company.model_validate(company)

        raise LookupError("company context is required for earnings prep")

    def _latest_period_label(self, db_session: Session, company_id) -> Optional[str]:
        rows = query_financials(FinancialQueryIn(company_id=company_id), db_session)
        if not rows:
            return None
        return rows[0].period_label

    def _build_payload(self, db_session: Session, company: Company, event_date: Optional[str]) -> dict[str, Any]:
        latest_period_label = self._latest_period_label(db_session, company.id)
        financials = query_financials(FinancialQueryIn(company_id=company.id, period_label=latest_period_label), db_session)
        consensus = get_consensus(ConsensusQueryIn(company_id=company.id, period_label=latest_period_label), db_session)
        thesis = get_thesis(CompanyQueryIn(company_id=company.id), db_session)
        drivers = get_drivers(CompanyQueryIn(company_id=company.id), db_session)
        catalysts = get_catalysts(CatalystQueryIn(company_id=company.id), db_session)
        filings = search_filings(FilingSearchIn(company_id=company.id, query=company.display_name), db_session)
        thesis_payload = json.dumps(thesis.model_dump(mode="json"), ensure_ascii=True)
        return {
            "company": {
                "company_id": str(company.id),
                "display_name": company.display_name,
                "legal_name": company.legal_name,
                "sector": company.sector,
                "sub_sector": company.sub_sector,
                "fy_convention": company.fy_convention,
                "coverage_status": company.coverage_status,
                "primary_analyst": company.primary_analyst,
                "active_thesis_version": company.active_thesis_version,
            },
            "event_date": event_date,
            "latest_period_label": latest_period_label,
            "latest_financials": [row.model_dump(mode="json") for row in financials[: self.config.max_financial_rows]],
            "consensus": [row.model_dump(mode="json") for row in consensus[: self.config.max_financial_rows]],
            "thesis": thesis_payload[: self.config.max_thesis_chars],
            "drivers": [row.model_dump(mode="json") for row in drivers[: self.config.max_driver_rows]],
            "catalysts": [row.model_dump(mode="json") for row in catalysts[: self.config.max_catalyst_rows]],
            "recent_filings": [row.model_dump(mode="json") for row in filings[: self.config.max_recent_filings]],
            "constraints": {
                "max_tool_calls": self.config.max_tool_calls,
                "max_tokens": self.config.max_tokens,
                "one_pager_only": True,
                "no_fabricated_numbers": True,
            },
        }

    def _parse_result(self, text: str, company: Company, event_date: Optional[str]) -> EarningsPrepResult:
        data = json.loads(text)
        data.setdefault("company", {})
        data["company"].setdefault("company_id", str(company.id))
        data["company"].setdefault("display_name", company.display_name)
        if event_date:
            data.setdefault("event_date", event_date)
        return EarningsPrepResult.model_validate(data)

    def _format_markdown(self, result: EarningsPrepResult) -> str:
        lines = [f"# Earnings Prep — {result.company.get('display_name', 'Unknown')}", "", f"- Event date: {result.event_date.isoformat()}"]
        lines.append("")
        lines.append("## Our Estimates vs Consensus")
        for row in result.our_consensus_comparison:
            lines.append(
                f"- {row.metric}: our {row.our_estimate if row.our_estimate is not None else '[VERIFY]'} vs consensus {row.consensus if row.consensus is not None else '[VERIFY]'}"
            )
        lines.append("")
        lines.append("## Driver Outlook")
        for item in result.driver_outlook:
            lines.append(f"- {item.driver_name}: {item.current_status or '[VERIFY]'}")
        lines.append("")
        lines.append("## What to Watch")
        for item in result.what_to_watch:
            lines.append(f"- {item.focus}: {item.signal_to_watch or '[VERIFY]'}")
        lines.append("")
        lines.append("## Key Questions")
        for item in result.key_questions:
            lines.append(f"- {item.question}")
        lines.append("")
        lines.append("## Key Risks")
        for item in result.key_risks:
            lines.append(f"- {item.risk}")
        return "\n".join(lines)

    def _queue_one_pager(self, db_session: Session, workflow_run: WorkflowRun, company: Company, result: EarningsPrepResult, markdown: str) -> ReviewQueue:
        queue_item = ReviewQueue(
            tier=3,
            bundle_id=uuid4(),
            workflow_run_id=workflow_run.id,
            write_type="coverage.earnings_prep.one_pager.proposed",
            target_schema="coverage",
            target_table="claim_provenance",
            target_row_id=None,
            proposed_payload={
                "company_id": str(company.id),
                "company_name": company.display_name,
                "event_date": result.event_date.isoformat(),
                "one_pager_markdown": markdown,
                "earnings_prep_summary": result.model_dump(mode="json"),
            },
            current_state=None,
            source_provenance_id=None,
            derivation_provenance_id=None,
            claim_provenance_id=None,
            confidence_score=None,
            verify_flags=[],
            state="pending_review",
            pending_since=datetime.now(timezone.utc),
        )
        db_session.add(queue_item)
        return queue_item

    def run(self, db_session: Session, company_id: Optional[str] = None, company_query: Optional[str] = None, event_date: Optional[str] = None) -> dict[str, Any]:
        company = self._resolve_company(db_session, company_id, company_query)

        workflow_run = WorkflowRun(
            workflow_name="earnings_prep",
            workflow_version="s-07",
            triggered_by="ui",
            triggered_by_detail=f"company:{company.id}",
            input_params={"company_id": str(company.id), "company_query": company_query, "event_date": event_date},
            status="running",
            started_at=datetime.now(timezone.utc),
            tool_calls_count=0,
            tokens_used=0,
            cost_usd=Decimal("0"),
        )
        db_session.add(workflow_run)
        db_session.flush()

        started = datetime.now(timezone.utc).timestamp()
        response_payload = self._call_claude(self._build_payload(db_session, company, event_date))
        log_tool_call(
            db_session,
            "anthropic.messages.create",
            {"company_id": str(company.id), "model": self.config.model},
            {"text_length": len(response_payload["text"])},
            started,
        )
        result = self._parse_result(response_payload["text"], company, event_date)
        markdown = self._format_markdown(result)
        queue_item = self._queue_one_pager(db_session, workflow_run, company, result, markdown)

        workflow_run.status = "completed"
        workflow_run.completed_at = datetime.now(timezone.utc)
        workflow_run.output_summary = {
            "company_id": str(company.id),
            "company_name": company.display_name,
            "event_date": result.event_date.isoformat(),
            "queue_item_id": str(queue_item.id),
        }
        workflow_run.tool_calls_count = 6
        workflow_run.tokens_used = 0
        workflow_run.cost_usd = Decimal("0")
        db_session.commit()

        return {
            "company_id": str(company.id),
            "workflow_run_id": str(workflow_run.id),
            "queue_item_id": str(queue_item.id),
            "event_date": result.event_date.isoformat(),
            "markdown_note": markdown,
        }


def run_earnings_prep(db_session: Session, company_id: Optional[str] = None, company_query: Optional[str] = None, event_date: Optional[str] = None) -> dict[str, Any]:
    return EarningsPrepRunner().run(db_session, company_id=company_id, company_query=company_query, event_date=event_date)
