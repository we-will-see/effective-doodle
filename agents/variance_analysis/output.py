from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentOSModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class VarianceFacts(AgentOSModel):
    company_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    period_label: Optional[str] = None
    period_end_date: Optional[date] = None
    actuals: list[dict[str, Any]] = Field(default_factory=list)


class VarianceComparison(AgentOSModel):
    metric: str
    actual_value: Decimal
    estimate_value: Optional[Decimal] = None
    delta_value: Optional[Decimal] = None
    delta_pct: Optional[Decimal] = None
    direction: Optional[str] = None
    notes: Optional[str] = None


class EvidenceDeltaItem(AgentOSModel):
    driver_name: str
    driver_type: Optional[str] = None
    current_status: Optional[str] = None
    relationship: Optional[str] = None
    evidence: Optional[str] = None


class VarianceAnalysisResult(AgentOSModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    facts: VarianceFacts
    consensus_comparison: list[VarianceComparison] = Field(default_factory=list)
    our_estimate_comparison: list[VarianceComparison] = Field(default_factory=list)
    evidence_delta: list[EvidenceDeltaItem] = Field(default_factory=list)
    variant_perception: str
    verify_flags: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
