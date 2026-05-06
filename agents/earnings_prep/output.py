from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentOSModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class EstimateComparison(AgentOSModel):
    metric: str
    our_estimate: Optional[Decimal] = None
    consensus: Optional[Decimal] = None
    delta_value: Optional[Decimal] = None
    delta_pct: Optional[Decimal] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class DriverOutlookItem(AgentOSModel):
    driver_name: str
    driver_type: Optional[str] = None
    current_status: Optional[str] = None
    expected_direction: Optional[str] = None
    evidence: Optional[str] = None
    thesis_link: Optional[str] = None


class WatchItem(AgentOSModel):
    focus: str
    why_it_matters: Optional[str] = None
    signal_to_watch: Optional[str] = None
    source_hint: Optional[str] = None


class QuestionItem(AgentOSModel):
    question: str
    rationale: Optional[str] = None


class RiskItem(AgentOSModel):
    risk: str
    impact: Optional[str] = None
    likelihood: Optional[str] = None
    mitigation: Optional[str] = None


class EarningsPrepResult(AgentOSModel):
    company: dict[str, Any]
    event_date: date
    our_consensus_comparison: list[EstimateComparison] = Field(default_factory=list)
    driver_outlook: list[DriverOutlookItem] = Field(default_factory=list)
    what_to_watch: list[WatchItem] = Field(default_factory=list)
    key_questions: list[QuestionItem] = Field(default_factory=list)
    key_risks: list[RiskItem] = Field(default_factory=list)
