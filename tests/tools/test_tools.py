"""Test suite for agent tools.

Note: Full test coverage requires PostgreSQL due to schema usage.
Run with: TEST_DATABASE_URL=postgresql://... pytest tests/tools/
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.tools import (
    get_catalysts,
    get_consensus,
    get_corporate_actions,
    get_drivers,
    get_thesis,
    query_companies,
    query_financials,
    search_filings,
)
from core.tools.schemas import (
    CatalystQueryIn,
    CompanyQueryIn,
    ConsensusQueryIn,
    CorporateActionQueryIn,
    FilingSearchIn,
    FinancialQueryIn,
)

# Check if we have PostgreSQL for full testing
USES_POSTGRES = os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql")

# Skip tests if no PostgreSQL
pytestmark = pytest.mark.skipif(
    not USES_POSTGRES,
    reason="Full tool tests require PostgreSQL due to schema usage. Run with TEST_DATABASE_URL=postgresql://..."
)


def get_base():
    """Import Base conditionally to avoid early module load."""
    from core.types.sqlalchemy_models import Base
    return Base


def get_models():
    """Import models conditionally."""
    from core.types.sqlalchemy_models import (
        Base,
        Catalyst,
        Company,
        ConsensusPull,
        CorporateAction,
        Document,
        Driver,
        Financial,
        ThesisMeta,
        ToolCall,
        WorkflowRun,
    )
    return {
        "Base": Base,
        "Catalyst": Catalyst,
        "Company": Company,
        "ConsensusPull": ConsensusPull,
        "CorporateAction": CorporateAction,
        "Document": Document,
        "Driver": Driver,
        "Financial": Financial,
        "ThesisMeta": ThesisMeta,
        "ToolCall": ToolCall,
        "WorkflowRun": WorkflowRun,
    }


@pytest.fixture()
def session():
    """Create database session for testing.
    
    Requires TEST_DATABASE_URL environment variable pointing to PostgreSQL.
    """
    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")
    
    engine = create_engine(db_url)
    models = get_models()
    Base = models["Base"]
    
    # Create schemas if they don't exist
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS coverage"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS filings"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ingestion_raw"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis"))
        conn.commit()
    
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    run_id = uuid4()
    db.add(
        WorkflowRun(
            id=run_id,
            workflow_name="test",
            workflow_version="1",
            triggered_by="pytest",
            status="running",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        Company(
            id=uuid4(),
            bse_code="500001",
            nse_symbol="ABC",
            isin="INE000A01028",
            legal_name="ABC Ltd",
            display_name="ABC",
            sector="Industrials",
            sub_sector="Industrial Goods",
            market_cap_bucket="mid",
            fy_convention="apr-mar",
            coverage_status="covered",
            primary_analyst="Analyst",
            active_thesis_version=1,
            notes="note",
            created_by="pytest",
            last_updated_by=None,
        )
    )
    company = db.query(Company).one()
    db.add_all(
        [
            Financial(
                company_id=company.id,
                period_label="1QFY26",
                period_end_date=date(2025, 6, 30),
                metric="revenue",
                value=Decimal("100"),
                currency="INR",
                unit="crore",
                type="actual",
                consolidation_basis="consolidated",
                accounting_policy_version="v1",
                scenario="base",
                is_active=True,
                created_by="pytest",
            ),
            ThesisMeta(
                company_id=company.id,
                version=1,
                status="active",
                written_at=datetime.now(timezone.utc),
                markdown_path="theses/abc/v1.md",
                markdown_git_sha="abc123",
                created_by="pytest",
            ),
            Driver(
                company_id=company.id,
                driver_type="volume",
                driver_name="Exports",
                description="Export demand",
                current_status="positive",
                created_by="pytest",
            ),
            Catalyst(
                company_id=company.id,
                catalyst_type="earnings",
                description="Quarterly results",
                expected_date=date(2025, 8, 1),
                date_confidence="high",
                status="upcoming",
                created_by="pytest",
            ),
            ConsensusPull(
                company_id=company.id,
                pulled_at=datetime.now(timezone.utc),
                raw_payload={"period_label": "1QFY26", "revenue": 105},
                processed=True,
            ),
            CorporateAction(
                company_id=company.id,
                action_type="split",
                effective_date=date(2025, 5, 1),
                ratio_or_amount="1:2",
                description="Stock split",
                created_by="pytest",
            ),
            Document(
                company_id=company.id,
                source="bse",
                source_id="DOC1",
                content_hash="hash1",
                document_type="exchange_filing",
                document_subtype="results",
                filing_title="Quarterly Results",
                filed_at=datetime(2025, 6, 30, tzinfo=timezone.utc),
                filesystem_path="/tmp/doc1",
                raw_text="Revenue was strong",
                parsed_text="Revenue was strong",
                extraction_status="done",
                classification_status="done",
            ),
        ]
    )
    db.commit()
    db.info["workflow_run_id"] = run_id
    yield db
    db.close()
    # Cleanup
    Base.metadata.drop_all(engine)


def test_tool_workflow_simulation(session, monkeypatch):
    from core.types.sqlalchemy_models import WorkflowRun
    
    run_id = str(session.info["workflow_run_id"])
    monkeypatch.setenv("AGENTOS_WORKFLOW_RUN_ID", run_id)
    company = session.query(Company).one()

    companies = query_companies(CompanyQueryIn(), session=session)
    assert len(companies) == 1
    assert query_companies(CompanyQueryIn(company_id=company.id), session=session).id == company.id
    assert len(query_financials(FinancialQueryIn(company_id=company.id, metric="revenue"), session=session)) == 1
    assert len(search_filings(FilingSearchIn(query="Revenue"), session=session)) == 1
    assert get_thesis(CompanyQueryIn(company_id=company.id), session=session).company_id == company.id
    assert len(get_drivers(CompanyQueryIn(company_id=company.id), session=session)) == 1
    assert len(get_catalysts(CatalystQueryIn(company_id=company.id), session=session)) == 1
    assert len(get_consensus(ConsensusQueryIn(company_id=company.id, period_label="1QFY26"), session=session)) == 1
    assert len(get_corporate_actions(CorporateActionQueryIn(company_id=company.id), session=session)) == 1

    assert session.query(ToolCall).count() >= 7
