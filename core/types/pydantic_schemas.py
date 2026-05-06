from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.utils.fingerprint import content_hash, idempotency_fingerprint
from core.utils.period import period_end_date_from_label, validate_period


class AgentOSModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PeriodSchema(AgentOSModel):
    period_label: str
    period_end_date: date

    @model_validator(mode="after")
    def _validate_period(self) -> "PeriodSchema":
        validate_period(self.period_label, self.period_end_date)
        return self


class FinancialIn(AgentOSModel):
    company_id: UUID
    period_label: str
    period_end_date: date
    metric: str
    value: Decimal
    currency: str = Field(min_length=3, max_length=3)
    unit: str
    type: Literal["actual", "our_estimate", "consensus", "guidance", "prior_estimate", "prior_consensus"]
    consolidation_basis: Literal["consolidated", "standalone"]
    accounting_policy_version: str
    scenario: Literal["base", "bull", "bear"] = "base"
    source_provenance_id: Optional[UUID] = None
    derivation_provenance_id: Optional[UUID] = None
    claim_provenance_id: Optional[UUID] = None
    confidence_score: Optional[Decimal] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self) -> "FinancialIn":
        validate_period(self.period_label, self.period_end_date)
        if self.source_provenance_id is None and self.derivation_provenance_id is None and self.claim_provenance_id is None:
            raise ValueError("at least one provenance reference is required")
        return self


class FingerprintInput(AgentOSModel):
    source_type: str
    source_id: str
    content: str

    @field_validator("source_type", "source_id", "content")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    def content_hash(self) -> str:
        return content_hash(self.content)

    def fingerprint(self) -> str:
        return idempotency_fingerprint(self.source_type, self.source_id, self.content_hash())


class WorkflowRunOut(AgentOSModel):
    id: UUID
    workflow_name: str
    workflow_version: str
    triggered_by: str
    status: str
    created_at: datetime


class ToolCallIn(AgentOSModel):
    workflow_run_id: UUID
    call_index: int = Field(ge=0)
    tool_name: str
    arguments: dict[str, Any]

