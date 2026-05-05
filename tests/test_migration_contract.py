from pathlib import Path


MIGRATION = Path("db/migrations/versions/20260505_0001_foundation_base.py").read_text()


def test_foundation_migration_creates_core_schemas() -> None:
    assert "CREATE SCHEMA IF NOT EXISTS coverage" in MIGRATION
    assert "CREATE SCHEMA IF NOT EXISTS filings" in MIGRATION
    assert "CREATE SCHEMA IF NOT EXISTS ingestion_raw" in MIGRATION
    assert "CREATE SCHEMA IF NOT EXISTS ops" in MIGRATION


def test_foundation_migration_creates_minimum_tables() -> None:
    assert "CREATE TABLE IF NOT EXISTS filings.documents" in MIGRATION
    assert "CREATE TABLE IF NOT EXISTS ops.review_queue" in MIGRATION
