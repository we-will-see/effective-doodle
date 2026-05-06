from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentOSModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class SourceProvenanceRef(AgentOSModel):
    page_number: int = Field(ge=1)
    table_index: Optional[int] = Field(default=None, ge=0)
    row_number: Optional[int] = Field(default=None, ge=0)
    bounding_box: Optional[dict[str, Any]] = None
    source_text: Optional[str] = None


class ExtractedValue(AgentOSModel):
    period_label: Optional[str] = None
    period_end_date: Optional[date] = None
    metric: str
    value: Decimal
    currency: Optional[str] = None
    unit: Optional[str] = None
    consolidation_basis: Optional[Literal["consolidated", "standalone"]] = None
    accounting_policy_version: Optional[str] = None
    source_provenance: SourceProvenanceRef
    confidence_score: Optional[Decimal] = None
    verify_flag: bool = False
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_value(self) -> "ExtractedValue":
        return self


class ClassifiedFinancial(AgentOSModel):
    company_id: UUID
    period_label: str
    period_end_date: date
    metric: str
    value: Decimal
    currency: str
    unit: str
    type: Literal["actual", "our_estimate", "consensus", "guidance", "prior_estimate", "prior_consensus"]
    consolidation_basis: Literal["consolidated", "standalone"]
    accounting_policy_version: str
    scenario: Literal["base", "bull", "bear"] = "base"
    source_provenance: SourceProvenanceRef
    confidence_score: Optional[Decimal] = None
    verify_flag: bool = False
    notes: Optional[str] = None


class ClassificationResult(AgentOSModel):
    document_id: UUID
    document_type: Literal[
        "results_announcement",
        "earnings_release",
        "investor_presentation",
        "annual_report",
        "quarterly_report",
        "shareholding_pattern",
        "corporate_action",
        "board_meeting_outcome",
        "regulatory_disclosure",
        "other",
    ]
    document_subtype: Optional[str] = None
    materiality_score: Decimal
    reasoning: Optional[str] = None
    extracted_financials: list[ClassifiedFinancial] = Field(default_factory=list)
    verify_flags: list[str] = Field(default_factory=list)
    source_provenance: list[SourceProvenanceRef] = Field(default_factory=list)
    model_name: Optional[str] = None
    raw_response_id: Optional[str] = None
