#!/usr/bin/env python3
"""End-to-end smoke tests for AgentOS vertical slice.

Tests the complete flow:
1. Database connectivity
2. Model imports and validation
3. Tool imports
4. Agent imports
5. Extraction pipeline (dry run)
6. Configuration validation
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test all modules import successfully."""
    print("\n=== Testing Imports ===")
    
    errors = []
    
    # Core types
    try:
        from core.types.sqlalchemy_models import Company, Document, Financial
        from core.types.sqlalchemy_models import Driver, Catalyst, ThesisMeta
        print("✅ core.types imports OK")
    except Exception as e:
        errors.append(f"core.types: {e}")
        print(f"❌ core.types: {e}")
    
    # Core tools
    try:
        from core.tools import query_companies, query_financials, search_filings
        from core.tools.schemas import CompanyQueryIn, FinancialQueryIn
        print("✅ core.tools imports OK")
    except Exception as e:
        errors.append(f"core.tools: {e}")
        print(f"❌ core.tools: {e}")
    
    # Extraction (may fail without pdfplumber installed)
    try:
        from extraction.pdf.text import extract_text_from_pdf
        from extraction.tables.camelot import extract_tables_from_pdf
        from extraction.pipeline.listener import ExtractionPipeline
        print("✅ extraction imports OK")
    except ImportError as e:
        print(f"⚠️  extraction: {e} (optional dependency)")
    except Exception as e:
        errors.append(f"extraction: {e}")
        print(f"❌ extraction: {e}")
    
    # Ingestion
    try:
        from ingestion.filings.poller import BSEPoller
        from ingestion.filings.poller_config import BSEPollerConfig
        print("✅ ingestion.filings imports OK")
    except Exception as e:
        errors.append(f"ingestion.filings: {e}")
        print(f"❌ ingestion.filings: {e}")
    
    # Agents
    try:
        from agents.filings_classifier.runner import FilingsClassifierRunner
        from agents.filings_classifier.output import ClassificationResult
        from agents.variance_analysis.runner import VarianceAnalysisRunner
        from agents.earnings_prep.runner import EarningsPrepRunner
        from agents.daily_briefing.runner import DailyBriefingRunner
        print("✅ agents imports OK")
    except Exception as e:
        errors.append(f"agents: {e}")
        print(f"❌ agents: {e}")
    
    # Modeling
    try:
        from modeling.excel_adapter.conventions import validate_named_range
        from modeling.excel_adapter.reader import WorkbookEstimate
        from modeling.excel_adapter.diff import compare_estimates
        print("✅ modeling.excel_adapter imports OK")
    except Exception as e:
        errors.append(f"modeling: {e}")
        print(f"❌ modeling: {e}")
    
    # Scheduler (may fail without apscheduler)
    try:
        from scripts.scheduler import setup_scheduler
        print("✅ scheduler imports OK")
    except ImportError as e:
        print(f"⚠️  scheduler: {e} (optional dependency)")
    except Exception as e:
        errors.append(f"scheduler: {e}")
        print(f"❌ scheduler: {e}")
    
    return len(errors) == 0, errors


def test_configurations():
    """Test configuration objects load."""
    print("\n=== Testing Configurations ===")
    
    errors = []
    
    try:
        from ingestion.filings.poller_config import BSEPollerConfig
        config = BSEPollerConfig()
        assert config.requests_per_second == 1.0
        print("✅ BSEPollerConfig OK")
    except Exception as e:
        errors.append(f"BSEPollerConfig: {e}")
        print(f"❌ BSEPollerConfig: {e}")
    
    try:
        from agents.filings_classifier.config import FilingsClassifierConfig
        config = FilingsClassifierConfig()
        assert config.model == "claude-3-haiku-20240307"
        assert config.max_tool_calls == 10
        print("✅ FilingsClassifierConfig OK")
    except Exception as e:
        errors.append(f"FilingsClassifierConfig: {e}")
        print(f"❌ FilingsClassifierConfig: {e}")
    
    try:
        from agents.variance_analysis.config import VarianceAnalysisConfig
        config = VarianceAnalysisConfig()
        assert "sonnet" in config.model.lower()
        assert config.max_tool_calls == 15
        print("✅ VarianceAnalysisConfig OK")
    except Exception as e:
        errors.append(f"VarianceAnalysisConfig: {e}")
        print(f"❌ VarianceAnalysisConfig: {e}")
    
    try:
        from agents.earnings_prep.config import EarningsPrepConfig
        config = EarningsPrepConfig()
        assert config.max_tool_calls <= 15
        print("✅ EarningsPrepConfig OK")
    except Exception as e:
        errors.append(f"EarningsPrepConfig: {e}")
        print(f"❌ EarningsPrepConfig: {e}")
    
    try:
        from agents.daily_briefing.config import DailyBriefingConfig
        config = DailyBriefingConfig()
        assert config.cron_hour == 7
        assert config.max_words == 500
        print("✅ DailyBriefingConfig OK")
    except Exception as e:
        errors.append(f"DailyBriefingConfig: {e}")
        print(f"❌ DailyBriefingConfig: {e}")
    
    return len(errors) == 0, errors


def test_schemas():
    """Test Pydantic schemas validate."""
    print("\n=== Testing Schemas ===")
    
    errors = []
    
    try:
        from core.tools.schemas import CompanyQueryIn, FinancialQueryIn
        
        query = CompanyQueryIn()
        assert query.limit == 100  # Default
        print("✅ CompanyQueryIn OK")
    except Exception as e:
        errors.append(f"CompanyQueryIn: {e}")
        print(f"❌ CompanyQueryIn: {e}")
    
    try:
        from agents.filings_classifier.output import ClassificationResult
        from datetime import datetime, timezone
        from decimal import Decimal
        from uuid import uuid4
        
        out = ClassificationResult(
            document_id=uuid4(),
            document_type="results_announcement",
            materiality_score=Decimal("0.8"),
        )
        assert out.document_type == "results_announcement"
        print("✅ ClassificationResult OK")
    except Exception as e:
        errors.append(f"ClassificationResult: {e}")
        print(f"❌ ClassificationResult: {e}")
    
    try:
        from modeling.excel_adapter.conventions import validate_named_range
        
        result = validate_named_range("revenue_FY26_base")
        assert result.metric == "revenue"
        assert result.period == "FY26"
        assert result.scenario == "base"
        print("✅ Named range validation OK")
    except Exception as e:
        errors.append(f"Named range validation: {e}")
        print(f"❌ Named range validation: {e}")
    
    try:
        from agents.variance_analysis.output import VarianceAnalysisResult
        from uuid import uuid4
        from decimal import Decimal
        
        result = VarianceAnalysisResult(
            document_id=uuid4(),
            company_id=uuid4(),
            variant_perception="Test finding",
            materiality_score=Decimal("0.7"),
        )
        assert result.variant_perception == "Test finding"
        print("✅ VarianceAnalysisResult OK")
    except Exception as e:
        errors.append(f"VarianceAnalysisResult: {e}")
        print(f"❌ VarianceAnalysisResult: {e}")
    
    try:
        from agents.earnings_prep.output import EarningsPrepResult
        from uuid import uuid4
        from datetime import date
        
        result = EarningsPrepResult(
            company_id=uuid4(),
            event_date=date.today(),
        )
        print("✅ EarningsPrepResult OK")
    except Exception as e:
        errors.append(f"EarningsPrepResult: {e}")
        print(f"❌ EarningsPrepResult: {e}")
    
    return len(errors) == 0, errors


def test_utilities():
    """Test utility functions."""
    print("\n=== Testing Utilities ===")
    
    errors = []
    
    try:
        from core.utils.period import parse_period_label
        
        result = parse_period_label("1QFY26")
        assert result is not None
        print("✅ Period utilities OK")
    except Exception as e:
        errors.append(f"Period utilities: {e}")
        print(f"❌ Period utilities: {e}")
    
    try:
        from core.utils.fingerprint import fingerprint
        
        fp = fingerprint(b"test content")
        assert len(fp) == 64  # SHA256 hex
        print("✅ Fingerprint utility OK")
    except Exception as e:
        errors.append(f"Fingerprint: {e}")
        print(f"❌ Fingerprint: {e}")
    
    return len(errors) == 0, errors


def test_file_structure():
    """Test that all expected files exist."""
    print("\n=== Testing File Structure ===")
    
    expected_files = [
        "pyproject.toml",
        "docker-compose.yml",
        "alembic.ini",
        "core/__init__.py",
        "core/types/sqlalchemy_models.py",
        "core/tools/__init__.py",
        "agents/filings_classifier/runner.py",
        "agents/variance_analysis/runner.py",
        "agents/earnings_prep/runner.py",
        "agents/daily_briefing/runner.py",
        "ingestion/filings/poller.py",
        "modeling/excel_adapter/reader.py",
        "extraction/pdf/text.py",
        "extraction/tables/camelot.py",
        "ui/streamlit_app.py",
        "scripts/scheduler.py",
    ]
    
    errors = []
    base = Path(__file__).parent.parent
    
    for path in expected_files:
        full = base / path
        if full.exists():
            print(f"✅ {path}")
        else:
            errors.append(f"Missing: {path}")
            print(f"❌ {path}")
    
    return len(errors) == 0, errors


def test_database_integration():
    """Test database connectivity if available."""
    print("\n=== Testing Database Integration ===")
    
    import os
    db_url = os.environ.get("TEST_DATABASE_URL")
    
    if not db_url:
        print("⚠️  Skipping database tests (TEST_DATABASE_URL not set)")
        return True, []
    
    errors = []
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        print("✅ Database connection OK")
        
        # Test model reflection
        from core.types.sqlalchemy_models import Company
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Just check the query compiles, don't execute
        query = session.query(Company).filter(Company.bse_code == "500001")
        str(query)  # Will raise if model is broken
        
        print("✅ ORM models OK")
        session.close()
        
    except Exception as e:
        errors.append(f"Database: {e}")
        print(f"❌ Database: {e}")
    
    return len(errors) == 0, errors


def main():
    """Run all smoke tests."""
    print("=" * 60)
    print("AGENTOS E2E SMOKE TESTS")
    print("=" * 60)
    
    all_passed = []
    all_errors = []
    
    passed, errors = test_imports()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    passed, errors = test_file_structure()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    passed, errors = test_configurations()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    passed, errors = test_schemas()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    passed, errors = test_utilities()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    passed, errors = test_database_integration()
    all_passed.append(passed)
    all_errors.extend(errors)
    
    print("\n" + "=" * 60)
    if all(all_passed) and not all_errors:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print(f"❌ TESTS FAILED: {len(all_errors)} errors")
        print("=" * 60)
        for err in all_errors:
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
