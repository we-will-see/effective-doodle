from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def tz_now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "coverage"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bse_code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    nse_symbol: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    isin: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    sector: Mapped[str] = mapped_column(Text, nullable=False)
    sub_sector: Mapped[Optional[str]] = mapped_column(Text)
    market_cap_bucket: Mapped[Optional[str]] = mapped_column(Text)
    fy_convention: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'apr-mar'"))
    coverage_status: Mapped[str] = mapped_column(Text, nullable=False)
    primary_analyst: Mapped[str] = mapped_column(Text, nullable=False)
    active_thesis_version: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)

    financials = relationship(back_populates="company")
    documents = relationship(back_populates="company")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    workflow_name: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_version: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by_detail: Mapped[Optional[str]] = mapped_column(Text)
    input_params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    output_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    error_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    tool_calls_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), server_default=text("0"), nullable=False)
    golden_set_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    parent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ops.workflow_runs.id"))
    created_at: Mapped[datetime] = tz_now()

    parent_run = relationship(remote_side="WorkflowRun.id", back_populates="child_runs")
    child_runs = relationship(back_populates="parent_run")


class SourceProvenance(Base):
    __tablename__ = "source_provenance"
    __table_args__ = {"schema": "coverage"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_path: Mapped[Optional[str]] = mapped_column(Text)
    page_number: Mapped[Optional[int]] = mapped_column(Integer)
    table_index: Mapped[Optional[int]] = mapped_column(Integer)
    row_number: Mapped[Optional[int]] = mapped_column(Integer)
    cell_reference: Mapped[Optional[str]] = mapped_column(Text)
    bounding_box: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_by: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    extracted_at: Mapped[datetime] = tz_now()
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Derivation(Base):
    __tablename__ = "derivations"
    __table_args__ = {"schema": "coverage"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    formula_hash: Mapped[str] = mapped_column(Text, nullable=False)
    formula_version: Mapped[int] = mapped_column(Integer, server_default=text("1"), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = tz_now()
    computed_by: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class ClaimProvenance(Base):
    __tablename__ = "claim_provenance"
    __table_args__ = {"schema": "coverage"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ops.workflow_runs.id"))
    synthesised_by: Mapped[str] = mapped_column(Text, nullable=False)
    synthesised_at: Mapped[datetime] = tz_now()
    notes: Mapped[Optional[str]] = mapped_column(Text)

    workflow_run = relationship()


class Financial(Base):
    __tablename__ = "financials"
    __table_args__ = {"schema": "coverage"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    period_label: Mapped[str] = mapped_column(Text, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    consolidation_basis: Mapped[str] = mapped_column(Text, nullable=False)
    accounting_policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, server_default=text("'base'"), nullable=False)
    source_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.source_provenance.id"))
    derivation_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.derivations.id"))
    claim_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.claim_provenance.id"))
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.financials.id"))
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    superseded_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)

    company = relationship(back_populates="financials")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": "filings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    source: Mapped[str] = mapped_column(Text, server_default=text("'bse'"), nullable=False)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[Optional[str]] = mapped_column(Text)
    document_subtype: Mapped[Optional[str]] = mapped_column(Text)
    filing_title: Mapped[str] = mapped_column(Text, nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = tz_now()
    filesystem_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text)
    parsed_tables: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    extraction_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"), nullable=False)
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    classification_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"), nullable=False)
    classified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    materiality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    is_material: Mapped[Optional[bool]] = mapped_column(Boolean)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    company = relationship(back_populates="documents")


class ParsedVersion(Base):
    __tablename__ = "parsed_versions"
    __table_args__ = {"schema": "filings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("filings.documents.id"), nullable=False)
    parser_name: Mapped[str] = mapped_column(Text, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text)
    parsed_tables: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    extraction_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    parsed_at: Mapped[datetime] = tz_now()
    notes: Mapped[Optional[str]] = mapped_column(Text)


class Classification(Base):
    __tablename__ = "classifications"
    __table_args__ = {"schema": "filings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("filings.documents.id"), nullable=False)
    classifier_version: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_subtype: Mapped[Optional[str]] = mapped_column(Text)
    materiality_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    extracted_metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.workflow_runs.id"), nullable=False)
    created_at: Mapped[datetime] = tz_now()


class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = {"schema": "filings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(Text)
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    ingested_at: Mapped[datetime] = tz_now()
    notes: Mapped[Optional[str]] = mapped_column(Text)


class TranscriptTurn(Base):
    __tablename__ = "transcript_turns"
    __table_args__ = {"schema": "filings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    transcript_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("filings.transcripts.id"), nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[Optional[str]] = mapped_column(Text)
    speaker_role: Mapped[Optional[str]] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_seconds: Mapped[Optional[int]] = mapped_column(Integer)


class ValuepickrPost(Base):
    __tablename__ = "valuepickr_posts"
    __table_args__ = {"schema": "ingestion_raw"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    thread_id: Mapped[str] = mapped_column(Text, nullable=False)
    thread_title: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[str] = mapped_column(Text, nullable=False)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_html: Mapped[str] = mapped_column(Text, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = tz_now()
    classification_status: Mapped[str] = mapped_column(Text, nullable=False)
    signal_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    related_company_ids: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    __table_args__ = {"schema": "ingestion_raw"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel_name: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    has_attachment: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    attachment_path: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = tz_now()
    classification_status: Mapped[str] = mapped_column(Text, nullable=False)
    signal_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    related_company_ids: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = {"schema": "ingestion_raw"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_publication: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_html: Mapped[Optional[str]] = mapped_column(Text)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = tz_now()
    classification_status: Mapped[str] = mapped_column(Text, nullable=False)
    relevance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    related_company_ids: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.workflow_runs.id"), nullable=False)
    call_index: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    called_at: Mapped[datetime] = tz_now()


class ReviewQueue(Base):
    __tablename__ = "review_queue"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.workflow_runs.id"), nullable=False)
    write_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_schema: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str] = mapped_column(Text, nullable=False)
    target_row_id: Mapped[Optional[str]] = mapped_column(Text)
    proposed_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    current_state: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    source_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.source_provenance.id"))
    derivation_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.derivations.id"))
    claim_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.claim_provenance.id"))
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    verify_flags: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = tz_now()
    pending_since: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(Text)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    rejection_notes: Mapped[Optional[str]] = mapped_column(Text)
    quality_rating: Mapped[Optional[int]] = mapped_column(SmallInteger)
    edited_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)


class TierRule(Base):
    __tablename__ = "tier_rules"
    __table_args__ = {"schema": "ops"}
    write_type: Mapped[str] = mapped_column(Text, primary_key=True)
    base_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    current_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tier_promoted_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tier_promoted_reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = tz_now()


class QueueAudit(Base):
    __tablename__ = "queue_audits"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    audited_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.review_queue.id"), nullable=False)
    audited_at: Mapped[datetime] = tz_now()
    audited_by: Mapped[str] = mapped_column(Text, server_default=text("'analyst'"), nullable=False)
    audit_result: Mapped[str] = mapped_column(Text, nullable=False)
    audit_notes: Mapped[Optional[str]] = mapped_column(Text)


class EvalGoldenSet(Base):
    __tablename__ = "eval_golden_set"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    eval_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected_output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ops.workflow_runs.id"))
    source_queue_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    golden_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.eval_golden_set.id"), nullable=False)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops.workflow_runs.id"), nullable=False)
    ran_at: Mapped[datetime] = tz_now()
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    diff: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    failure_categories: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "ops"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    acknowledged: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = tz_now()


class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = {"schema": "ops"}
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = tz_now()
    updated_by: Mapped[str] = mapped_column(Text, nullable=False)


class EstimateRationale(Base):
    __tablename__ = "estimate_rationale"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    financials_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.financials.id"), nullable=False)
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    key_assumptions: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    sensitivities: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    key_risks: Mapped[list[Any]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    claim_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.claim_provenance.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.estimate_rationale.id"))
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class ThesisMeta(Base):
    __tablename__ = "theses_meta"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    superseded_by_version: Mapped[Optional[int]] = mapped_column(Integer)
    markdown_path: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_git_sha: Mapped[str] = mapped_column(Text, nullable=False)
    variant_perception_summary: Mapped[Optional[str]] = mapped_column(Text)
    key_drivers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    time_horizon_months: Mapped[Optional[int]] = mapped_column(Integer)
    next_review_due: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    driver_type: Mapped[str] = mapped_column(Text, nullable=False)
    driver_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    current_status: Mapped[str] = mapped_column(Text, nullable=False)
    status_last_updated: Mapped[datetime] = tz_now()
    status_evidence_claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.claim_provenance.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class Catalyst(Base):
    __tablename__ = "catalysts"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    catalyst_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_date: Mapped[Optional[date]] = mapped_column(Date)
    date_confidence: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    expected_impact_direction: Mapped[Optional[str]] = mapped_column(Text)
    expected_impact_magnitude: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    ratio_or_amount: Mapped[str] = mapped_column(Text, nullable=False)
    adjustment_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_filing_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("filings.documents.id"))
    source_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.source_provenance.id"))
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class AccountingPolicy(Base):
    __tablename__ = "accounting_policies"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_filing_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("filings.documents.id"))
    source_provenance_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("coverage.source_provenance.id"))
    created_at: Mapped[datetime] = tz_now()
    updated_at: Mapped[datetime] = tz_now()
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated_by: Mapped[Optional[str]] = mapped_column(Text)


class ConsensusPull(Base):
    __tablename__ = "consensus_pulls"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.companies.id"), nullable=False)
    pulled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, server_default=text("'visible_alpha'"), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class RecomputeQueue(Base):
    __tablename__ = "recompute_queue"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    triggered_by_correction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    affected_table: Mapped[str] = mapped_column(Text, nullable=False)
    affected_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    derivation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coverage.derivations.id"), nullable=False)
    walk_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    recomputed_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4))
    resolution_queue_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("ops.review_queue.id"))
    created_at: Mapped[datetime] = tz_now()
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(Text)


class CoverageEmbedding(Base):
    __tablename__ = "coverage_embeddings"
    __table_args__ = {"schema": "coverage"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = tz_now()


class FilingsEmbedding(Base):
    __tablename__ = "filings_embeddings"
    __table_args__ = {"schema": "filings"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    source_table: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = tz_now()


class _Noop(Base):
    __abstract__ = True
