"""Foundation base: extensions, schemas, and roles.

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op


revision = "20260505_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.execute("CREATE SCHEMA IF NOT EXISTS coverage;")
    op.execute("CREATE SCHEMA IF NOT EXISTS filings;")
    op.execute("CREATE SCHEMA IF NOT EXISTS ingestion_raw;")
    op.execute("CREATE SCHEMA IF NOT EXISTS ops;")

    op.execute(
        "DO $$ BEGIN CREATE ROLE ingestion_filings_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE ROLE extraction_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE ROLE orchestrator_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE ROLE approval_processor_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE ROLE web_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    # Minimal tables required for role grants and workflow wiring in early F-02.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_type TEXT NOT NULL DEFAULT 'bse',
            source_id TEXT NOT NULL,
            title TEXT NULL,
            filing_date TIMESTAMPTZ NULL,
            raw_text TEXT NULL,
            parsed_text TEXT NULL,
            parsed_tables JSONB NULL,
            extraction_status TEXT NULL,
            extracted_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.review_queue (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            write_type TEXT NOT NULL,
            tier INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
            status TEXT NOT NULL DEFAULT 'pending_review',
            proposed_payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ NULL
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ops.review_queue;")
    op.execute("DROP TABLE IF EXISTS filings.documents;")

    op.execute("DROP ROLE IF EXISTS web_role;")
    op.execute("DROP ROLE IF EXISTS approval_processor_role;")
    op.execute("DROP ROLE IF EXISTS orchestrator_role;")
    op.execute("DROP ROLE IF EXISTS extraction_role;")
    op.execute("DROP ROLE IF EXISTS ingestion_filings_role;")

    op.execute("DROP SCHEMA IF EXISTS ops CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS ingestion_raw CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS filings CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS coverage CASCADE;")
