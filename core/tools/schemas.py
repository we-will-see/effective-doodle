from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DateRange(ToolModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CompanyOut(ToolModel):
    id: UUID
    bse_code: str
    nse_symbol: Optional[str] = None
    isin: Optional[str] = None
    legal_name: str
    display_name: str
    sector: str
    sub_sector: Optional[str] = None
    market_cap_bucket: Optional[str] = None
    fy_convention: str
    coverage_status: str
    primary_analyst: str
    active_thesis_version: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None


class CompanyQueryIn(ToolModel):
    company_id: Optional[UUID] = None


class FinancialQueryIn(ToolModel):
    company_id: UUID
    period_label: Optional[str] = None
    metric: Optional[str] = None
    type: Optional[str] = None


class FinancialOut(ToolModel):
    id: UUID
    company_id: UUID
    period_label: str
    period_end_date: date
    metric: str
    value: Decimal
    currency: str
    unit: str
    type: str
    consolidation_basis: str
    accounting_policy_version: str
    scenario: str
    source_provenance_id: Optional[UUID] = None
    derivation_provenance_id: Optional[UUID] = None
    claim_provenance_id: Optional[UUID] = None
    confidence_score: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: bool
    superseded_by_id: Optional[UUID] = None
    superseded_at: Optional[datetime] = None
    superseded_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None


class FilingSearchIn(ToolModel):
    company_id: Optional[UUID] = None
    query: str = Field(min_length=1)
    date_range: Optional[DateRange] = None


class FilingOut(ToolModel):
    id: UUID
    company_id: UUID
    source: str
    source_id: str
    content_hash: str
    document_type: Optional[str] = None
    document_subtype: Optional[str] = None
    filing_title: str
    filed_at: datetime
    ingested_at: datetime
    filesystem_path: str
    page_count: Optional[int] = None
    raw_text: Optional[str] = None
    parsed_text: Optional[str] = None
    parsed_tables: Optional[dict[str, Any]] = None
    extraction_status: str
    extracted_at: Optional[datetime] = None
    classification_status: str
    classified_at: Optional[datetime] = None
    materiality_score: Optional[Decimal] = None
    is_material: Optional[bool] = None
    notes: Optional[str] = None


class ThesisOut(ToolModel):
    id: UUID
    company_id: UUID
    version: int
    status: str
    written_at: datetime
    activated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    superseded_by_version: Optional[int] = None
    markdown_path: str
    markdown_git_sha: str
    variant_perception_summary: Optional[str] = None
    key_drivers: Optional[dict[str, Any]] = None
    time_horizon_months: Optional[int] = None
    next_review_due: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None


class DriverOut(ToolModel):
    id: UUID
    company_id: UUID
    driver_type: str
    driver_name: str
    description: str
    current_status: str
    status_last_updated: datetime
    status_evidence_claim_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None


class CatalystQueryIn(ToolModel):
    company_id: UUID
    date_range: Optional[DateRange] = None


class CatalystOut(ToolModel):
    id: UUID
    company_id: UUID
    catalyst_type: str
    description: str
    expected_date: Optional[date] = None
    date_confidence: str
    probability: Optional[Decimal] = None
    expected_impact_direction: Optional[str] = None
    expected_impact_magnitude: Optional[str] = None
    status: str
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None


class ConsensusQueryIn(ToolModel):
    company_id: UUID
    period_label: Optional[str] = None


class ConsensusOut(ToolModel):
    id: UUID
    company_id: UUID
    pulled_at: datetime
    source: str
    raw_payload: dict[str, Any]
    processed: bool
    notes: Optional[str] = None


class CorporateActionQueryIn(ToolModel):
    company_id: UUID
    date_range: Optional[DateRange] = None


class CorporateActionOut(ToolModel):
    id: UUID
    company_id: UUID
    action_type: str
    effective_date: date
    ratio_or_amount: str
    adjustment_factor: Optional[Decimal] = None
    description: str
    source_filing_id: Optional[UUID] = None
    source_provenance_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    last_updated_by: Optional[str] = None
