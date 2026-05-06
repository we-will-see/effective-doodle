from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from core.types.sqlalchemy_models import Company, ConsensusPull, Financial, SourceProvenance
from ingestion.consensus.visible_alpha import VisibleAlphaClient, VisibleAlphaConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConsensusRunnerConfig:
    workflow_name: str = "consensus_ingestion"
    workflow_version: str = "S-09"
    source_name: str = "visible_alpha"
    earnings_season_days: int = 21
    created_by: str = "consensus_ingestion"


class ConsensusRunner:
    def __init__(
        self,
        config: Optional[ConsensusRunnerConfig] = None,
        client: Optional[VisibleAlphaClient] = None,
    ):
        self.config = config or ConsensusRunnerConfig()
        self.client = client or VisibleAlphaClient(VisibleAlphaConfig.from_env())

    def is_earnings_season(self, today: Optional[date] = None) -> bool:
        today = today or datetime.now(timezone.utc).date()
        for quarter_end in (date(today.year, 3, 31), date(today.year, 6, 30), date(today.year, 9, 30), date(today.year, 12, 31)):
            if quarter_end <= today <= quarter_end + timedelta(days=self.config.earnings_season_days):
                return True
        return False

    def cadence(self, today: Optional[date] = None) -> str:
        return "daily" if self.is_earnings_season(today) else "weekly"

    def _normalize_row(self, company: Company, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company_id": company.id,
            "period_label": str(row["period_label"]),
            "period_end_date": row.get("period_end_date") or row.get("period_end") or row.get("period_end_dt"),
            "metric": str(row["metric"]),
            "value": self.client.parse_numeric(row["value"]),
            "currency": str(row.get("currency", "INR")),
            "unit": str(row.get("unit", "value")),
            "type": "consensus",
            "consolidation_basis": str(row.get("consolidation_basis", "consolidated")),
            "accounting_policy_version": str(row.get("accounting_policy_version", "visible_alpha")),
            "scenario": str(row.get("scenario", "base")),
            "confidence_score": row.get("confidence_score"),
            "notes": row.get("notes"),
            "created_by": self.config.created_by,
        }

    def _build_source_provenance(self, company: Company, row: dict[str, Any], pulled_at: datetime) -> SourceProvenance:
        source_id = ":".join(
            [
                str(company.id),
                str(row.get("period_label", "")),
                str(row.get("metric", "")),
                str(row.get("period_end_date", row.get("period_end", row.get("period_end_dt", "")))),
            ]
        )
        return SourceProvenance(
            source_type="visible_alpha",
            source_id=source_id,
            extracted_by=self.config.created_by,
            raw_text=None,
            extraction_confidence=row.get("confidence_score"),
            extracted_at=pulled_at,
            notes=row.get("notes"),
        )

    def _archive_existing(self, db: Session, existing: Financial, reason: str) -> None:
        existing.type = "prior_consensus"
        existing.is_active = False
        existing.superseded_at = datetime.now(timezone.utc)
        existing.superseded_reason = reason
        existing.last_updated_by = self.config.created_by

    def _upsert_company_rows(self, db: Session, company: Company, rows: list[dict[str, Any]], pulled_at: datetime) -> dict[str, int]:
        inserted = 0
        archived = 0
        for row in rows:
            normalized = self._normalize_row(company, row)
            period_end_date = normalized["period_end_date"]
            if isinstance(period_end_date, str):
                period_end_date = date.fromisoformat(period_end_date)
            normalized["period_end_date"] = period_end_date
            provenance = self._build_source_provenance(company, row, pulled_at)
            db.add(provenance)
            db.flush()

            existing = db.scalar(
                select(Financial).where(
                    Financial.company_id == company.id,
                    Financial.period_label == normalized["period_label"],
                    Financial.period_end_date == normalized["period_end_date"],
                    Financial.metric == normalized["metric"],
                    Financial.type == "consensus",
                    Financial.consolidation_basis == normalized["consolidation_basis"],
                    Financial.scenario == normalized["scenario"],
                    Financial.is_active.is_(True),
                )
            )
            if existing is not None:
                self._archive_existing(db, existing, "visible_alpha refresh")
                archived += 1

            db.add(
                Financial(
                    **normalized,
                    source_provenance_id=provenance.id,
                    derivation_provenance_id=None,
                    claim_provenance_id=None,
                    is_active=True,
                    created_at=pulled_at,
                    updated_at=pulled_at,
                )
            )
            inserted += 1
        return {"inserted": inserted, "archived": archived}

    def run(self, db_session: Session) -> dict[str, Any]:
        pulled_at = datetime.now(timezone.utc)
        companies = db_session.scalars(
            select(Company).where(Company.coverage_status.in_(("active", "covered"))).order_by(Company.display_name)
        ).all()

        processed = []
        total_inserted = 0
        total_archived = 0

        for company in companies:
            payload = self.client.fetch_consensus(company, as_of=pulled_at.date())
            raw_rows = self.client.extract_rows(payload)
            db_session.add(
                ConsensusPull(
                    company_id=company.id,
                    pulled_at=pulled_at,
                    source=self.config.source_name,
                    raw_payload=payload,
                    processed=True,
                )
            )
            stats = self._upsert_company_rows(db_session, company, raw_rows, pulled_at)
            total_inserted += stats["inserted"]
            total_archived += stats["archived"]
            processed.append(
                {
                    "company_id": str(company.id),
                    "company": company.display_name,
                    "rows": len(raw_rows),
                    "cadence": self.cadence(pulled_at.date()),
                }
            )

        db_session.commit()
        return {
            "workflow_name": self.config.workflow_name,
            "workflow_version": self.config.workflow_version,
            "source": self.config.source_name,
            "cadence": self.cadence(pulled_at.date()),
            "companies": len(processed),
            "rows_inserted": total_inserted,
            "rows_archived": total_archived,
            "processed_companies": processed,
        }
