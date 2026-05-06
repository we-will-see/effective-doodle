"""Integration tests for database migrations.

Tests that migrations apply cleanly and meet spec requirements.
"""

import pytest
import subprocess
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import os

# Use test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/agentos_test"
)


class TestMigrations:
    """Test migration integrity and spec compliance."""

    @pytest.fixture(scope="class")
    def engine(self):
        """Create test database engine."""
        engine = create_engine(TEST_DATABASE_URL)
        yield engine
        # Cleanup after tests
        engine.dispose()

    @pytest.fixture(scope="function")
    def db_session(self, engine):
        """Create database session for tests."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_migration_applies_cleanly(self):
        """Test that alembic upgrade head runs without errors."""
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd="/root/.openclaw/workspace/effective-doodle"
        )
        assert result.returncode == 0, f"Migration failed: {result.stderr}"

    def test_all_schemas_exist(self, engine):
        """Test that all four schemas are created."""
        inspector = inspect(engine)
        schemas = inspector.get_schema_names()
        required = {"coverage", "filings", "ingestion_raw", "ops"}
        assert required.issubset(set(schemas)), f"Missing schemas: {required - set(schemas)}"

    def test_core_tables_exist(self, engine):
        """Test that critical tables from spec exist."""
        inspector = inspect(engine)
        
        # Check coverage tables
        coverage_tables = inspector.get_table_names(schema="coverage")
        critical_coverage = {
            "companies", "financials", "source_provenance", 
            "derivations", "claim_provenance"
        }
        assert critical_coverage.issubset(set(coverage_tables)), \
            f"Missing coverage tables: {critical_coverage - set(coverage_tables)}"

        # Check filings tables
        filings_tables = inspector.get_table_names(schema="filings")
        critical_filings = {"documents", "parsed_versions", "classifications"}
        assert critical_filings.issubset(set(filings_tables)), \
            f"Missing filings tables: {critical_filings - set(filings_tables)}"

    def test_triggers_exist(self, db_session):
        """Test that updated_at triggers are installed."""
        result = db_session.execute(text("""
            SELECT trigger_name, event_object_table, event_object_schema
            FROM information_schema.triggers
            WHERE trigger_schema = 'coverage'
            AND trigger_name LIKE 'trg_%_updated_at'
        """))
        triggers = result.fetchall()
        assert len(triggers) > 0, "No updated_at triggers found in coverage schema"

    def test_roles_exist(self, db_session):
        """Test that required PostgreSQL roles exist."""
        result = db_session.execute(text("""
            SELECT rolname FROM pg_roles 
            WHERE rolname IN (
                'ingestion_filings_role',
                'extraction_role', 
                'orchestrator_role',
                'approval_processor_role',
                'web_role'
            )
        """))
        roles = [r[0] for r in result.fetchall()]
        required = {
            'ingestion_filings_role', 'extraction_role', 
            'orchestrator_role', 'approval_processor_role', 'web_role'
        }
        assert required.issubset(set(roles)), f"Missing roles: {required - set(roles)}"

    def test_provenance_constraint(self, db_session):
        """Test that financials requires at least one provenance type."""
        # This should fail - no provenance provided
        with pytest.raises(Exception):
            db_session.execute(text("""
                INSERT INTO coverage.financials (
                    company_id, period_label, period_end_date, metric,
                    value, type, consolidation_basis, accounting_policy_version
                ) VALUES (
                    'test-co', '1QFY26', '2025-06-30', 'revenue',
                    100.0, 'actual', 'consolidated', 'IndAS-1.0'
                )
            """))
            db_session.commit()

    def test_idempotency_fingerprint_unique(self, db_session):
        """Test that fingerprint constraint prevents duplicates."""
        # Insert first document
        db_session.execute(text("""
            INSERT INTO filings.documents (
                source_type, source_id, content_hash, raw_path, status
            ) VALUES (
                'BSE', 'DOC001', 'abc123', '/data/test.pdf', 'pending'
            )
        """))
        db_session.commit()

        # Same fingerprint should fail
        with pytest.raises(Exception):
            db_session.execute(text("""
                INSERT INTO filings.documents (
                    source_type, source_id, content_hash, raw_path, status
                ) VALUES (
                    'BSE', 'DOC001', 'abc123', '/data/test2.pdf', 'pending'
                )
            """))
            db_session.commit()
