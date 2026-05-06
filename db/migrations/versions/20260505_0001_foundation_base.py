"""Foundation base: extensions, schemas, roles, and core schema."""

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

    op.execute("DO $$ BEGIN CREATE ROLE ingestion_filings_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE ROLE extraction_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE ROLE orchestrator_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE ROLE approval_processor_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE ROLE web_role NOINHERIT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.companies (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          bse_code TEXT NOT NULL UNIQUE,
          nse_symbol TEXT NULL UNIQUE,
          isin TEXT NULL UNIQUE,
          legal_name TEXT NOT NULL,
          display_name TEXT NOT NULL,
          sector TEXT NOT NULL,
          sub_sector TEXT NULL,
          market_cap_bucket TEXT NULL CHECK (market_cap_bucket IN ('large', 'mid', 'small', 'micro') OR market_cap_bucket IS NULL),
          fy_convention TEXT NOT NULL DEFAULT 'apr-mar' CHECK (fy_convention = 'apr-mar'),
          coverage_status TEXT NOT NULL CHECK (coverage_status IN ('active', 'passive', 'dropped')),
          primary_analyst TEXT NOT NULL,
          active_thesis_version INTEGER NULL,
          notes TEXT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_status ON coverage.companies (coverage_status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_sector ON coverage.companies (sector);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.workflow_runs (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          workflow_name TEXT NOT NULL,
          workflow_version TEXT NOT NULL,
          triggered_by TEXT NOT NULL CHECK (triggered_by IN ('analyst', 'cron', 'event', 'eval_harness')),
          triggered_by_detail TEXT NULL,
          input_params JSONB NOT NULL DEFAULT '{}'::jsonb,
          status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'partial', 'timeout')),
          started_at TIMESTAMPTZ NULL,
          completed_at TIMESTAMPTZ NULL,
          output_summary JSONB NULL,
          error_details JSONB NULL,
          tool_calls_count INTEGER NOT NULL DEFAULT 0,
          tokens_used INTEGER NOT NULL DEFAULT 0,
          cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
          golden_set_run_id UUID NULL,
          parent_run_id UUID NULL REFERENCES ops.workflow_runs(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_runs_workflow ON ops.workflow_runs (workflow_name, created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON ops.workflow_runs (status) WHERE status IN ('pending', 'running', 'failed', 'partial', 'timeout');")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.source_provenance (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_type TEXT NOT NULL CHECK (source_type IN (
            'bse_filing', 'transcript', 'excel_model', 'visible_alpha', 'manual_entry',
            'press_release', 'investor_presentation', 'broker_note',
            'valuepickr_post', 'telegram_message', 'news_article', 'twitter_post'
          )),
          source_id TEXT NOT NULL,
          document_path TEXT NULL,
          page_number INTEGER NULL,
          table_index INTEGER NULL,
          row_number INTEGER NULL,
          cell_reference TEXT NULL,
          bounding_box JSONB NULL,
          raw_text TEXT NULL,
          extracted_by TEXT NOT NULL,
          extraction_confidence NUMERIC(4, 3) NULL,
          extracted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          notes TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_source_provenance_source ON coverage.source_provenance (source_type, source_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.derivations (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          formula TEXT NOT NULL,
          formula_hash TEXT NOT NULL,
          formula_version INTEGER NOT NULL DEFAULT 1,
          inputs JSONB NOT NULL,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          computed_by TEXT NOT NULL,
          notes TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_derivations_formula_hash ON coverage.derivations (formula_hash);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.claim_provenance (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          claim_text TEXT NOT NULL,
          evidence JSONB NOT NULL,
          workflow_run_id UUID NULL,
          synthesised_by TEXT NOT NULL,
          synthesised_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          notes TEXT NULL
        );
        """
    )
    op.execute(
        "ALTER TABLE coverage.claim_provenance ADD CONSTRAINT fk_claim_provenance_workflow_run FOREIGN KEY (workflow_run_id) REFERENCES ops.workflow_runs(id);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_claim_provenance_workflow ON coverage.claim_provenance (workflow_run_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.financials (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          period_label TEXT NOT NULL,
          period_end_date DATE NOT NULL,
          metric TEXT NOT NULL,
          value NUMERIC(20, 4) NOT NULL,
          currency CHAR(3) NOT NULL,
          unit TEXT NOT NULL,
          type TEXT NOT NULL CHECK (type IN ('actual', 'our_estimate', 'consensus', 'guidance', 'prior_estimate', 'prior_consensus')),
          consolidation_basis TEXT NOT NULL CHECK (consolidation_basis IN ('consolidated', 'standalone')),
          accounting_policy_version TEXT NOT NULL,
          scenario TEXT NOT NULL DEFAULT 'base' CHECK (scenario IN ('base', 'bull', 'bear')),
          source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
          derivation_provenance_id UUID NULL REFERENCES coverage.derivations(id),
          claim_provenance_id UUID NULL REFERENCES coverage.claim_provenance(id),
          confidence_score NUMERIC(4, 3) NULL,
          notes TEXT NULL,
          is_active BOOLEAN NOT NULL DEFAULT true,
          superseded_by_id UUID NULL REFERENCES coverage.financials(id),
          superseded_at TIMESTAMPTZ NULL,
          superseded_reason TEXT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL,
          CONSTRAINT financials_provenance_required CHECK (
            source_provenance_id IS NOT NULL OR derivation_provenance_id IS NOT NULL OR claim_provenance_id IS NOT NULL
          )
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_financials_active ON coverage.financials (company_id, period_end_date, metric, type, consolidation_basis, scenario) WHERE is_active = true;"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_financials_company_period ON coverage.financials (company_id, period_end_date DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_financials_metric ON coverage.financials (metric);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_financials_type ON coverage.financials (type);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.estimate_rationale (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          financials_id UUID NOT NULL REFERENCES coverage.financials(id),
          rationale_text TEXT NOT NULL,
          key_assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
          sensitivities JSONB NOT NULL DEFAULT '[]'::jsonb,
          key_risks JSONB NOT NULL DEFAULT '[]'::jsonb,
          claim_provenance_id UUID NULL REFERENCES coverage.claim_provenance(id),
          is_active BOOLEAN NOT NULL DEFAULT true,
          superseded_by_id UUID NULL REFERENCES coverage.estimate_rationale(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_estimate_rationale_financials ON coverage.estimate_rationale (financials_id) WHERE is_active = true;"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.theses_meta (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          version INTEGER NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived', 'superseded')),
          written_at TIMESTAMPTZ NOT NULL,
          activated_at TIMESTAMPTZ NULL,
          archived_at TIMESTAMPTZ NULL,
          superseded_by_version INTEGER NULL,
          markdown_path TEXT NOT NULL,
          markdown_git_sha TEXT NOT NULL,
          variant_perception_summary TEXT NULL,
          key_drivers JSONB NULL,
          time_horizon_months INTEGER NULL,
          next_review_due DATE NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL,
          CONSTRAINT one_active_per_company UNIQUE (company_id, status) DEFERRABLE INITIALLY DEFERRED
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_theses_one_active ON coverage.theses_meta (company_id) WHERE status = 'active';")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.drivers (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          driver_type TEXT NOT NULL CHECK (driver_type IN ('revenue', 'cost', 'margin', 'volume', 'mix', 'pricing', 'other')),
          driver_name TEXT NOT NULL,
          description TEXT NOT NULL,
          current_status TEXT NOT NULL CHECK (current_status IN ('tracking', 'ahead', 'behind', 'deteriorating', 'unknown')),
          status_last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
          status_evidence_claim_id UUID NULL REFERENCES coverage.claim_provenance(id),
          is_active BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL,
          CONSTRAINT uq_driver_company_name UNIQUE (company_id, driver_name)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.catalysts (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          catalyst_type TEXT NOT NULL CHECK (catalyst_type IN ('earnings', 'guidance', 'regulatory', 'capacity', 'product', 'corporate_action', 'macro', 'other')),
          description TEXT NOT NULL,
          expected_date DATE NULL,
          date_confidence TEXT NOT NULL CHECK (date_confidence IN ('exact', 'estimated', 'range', 'unknown')),
          probability NUMERIC(4, 3) NULL,
          expected_impact_direction TEXT NULL CHECK (expected_impact_direction IN ('positive', 'negative', 'mixed', 'unknown') OR expected_impact_direction IS NULL),
          expected_impact_magnitude TEXT NULL CHECK (expected_impact_magnitude IN ('high', 'medium', 'low') OR expected_impact_magnitude IS NULL),
          status TEXT NOT NULL CHECK (status IN ('pending', 'realised', 'missed', 'cancelled')),
          notes TEXT NULL,
          is_active BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalysts_company_date ON coverage.catalysts (company_id, expected_date);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_catalysts_status ON coverage.catalysts (status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.corporate_actions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          action_type TEXT NOT NULL CHECK (action_type IN ('split', 'bonus', 'rights', 'buyback', 'demerger', 'merger', 'acquisition', 'dividend_special', 'capital_reduction', 'name_change', 'isin_change', 'other')),
          effective_date DATE NOT NULL,
          ratio_or_amount TEXT NOT NULL,
          adjustment_factor NUMERIC(20, 8) NULL,
          description TEXT NOT NULL,
          source_filing_id UUID NULL,
          source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_corp_actions_company_date ON coverage.corporate_actions (company_id, effective_date);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.accounting_policies (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          policy_version TEXT NOT NULL,
          effective_from DATE NOT NULL,
          effective_to DATE NULL,
          notes TEXT NOT NULL,
          source_filing_id UUID NULL,
          source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL,
          last_updated_by TEXT NULL,
          CONSTRAINT uq_policy_company_version UNIQUE (company_id, policy_version)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.consensus_pulls (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          pulled_at TIMESTAMPTZ NOT NULL,
          source TEXT NOT NULL DEFAULT 'visible_alpha',
          raw_payload JSONB NOT NULL,
          processed BOOLEAN NOT NULL DEFAULT false,
          notes TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_consensus_pulls_company_time ON coverage.consensus_pulls (company_id, pulled_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.recompute_queue (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          triggered_by_correction_id UUID NOT NULL,
          affected_table TEXT NOT NULL,
          affected_row_id UUID NOT NULL,
          derivation_id UUID NOT NULL REFERENCES coverage.derivations(id),
          walk_distance INTEGER NOT NULL,
          status TEXT NOT NULL CHECK (status IN ('pending', 'recomputed', 'manually_resolved', 'dismissed')),
          recomputed_value NUMERIC(20, 4) NULL,
          resolution_queue_item_id UUID NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          resolved_at TIMESTAMPTZ NULL,
          resolved_by TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_recompute_pending ON coverage.recompute_queue (status, created_at) WHERE status = 'pending';")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS coverage.coverage_embeddings (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_table TEXT NOT NULL,
          source_row_id UUID NOT NULL,
          chunk_index INTEGER NOT NULL DEFAULT 0,
          chunk_text TEXT NOT NULL,
          embedding VECTOR(1024) NOT NULL,
          embedding_model TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_coverage_embedding UNIQUE (source_table, source_row_id, chunk_index, embedding_model)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_coverage_embeddings_vec ON coverage.coverage_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.documents (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          source TEXT NOT NULL DEFAULT 'bse' CHECK (source IN ('bse', 'nse', 'company_website', 'manual')),
          source_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          document_type TEXT NULL,
          document_subtype TEXT NULL,
          filing_title TEXT NOT NULL,
          filed_at TIMESTAMPTZ NOT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          filesystem_path TEXT NOT NULL,
          page_count INTEGER NULL,
          raw_text TEXT NULL,
          parsed_text TEXT NULL,
          parsed_tables JSONB NULL,
          extraction_status TEXT NOT NULL DEFAULT 'pending' CHECK (extraction_status IN ('pending', 'extracted', 'extraction_failed', 'partial')),
          extracted_at TIMESTAMPTZ NULL,
          classification_status TEXT NOT NULL DEFAULT 'pending' CHECK (classification_status IN ('pending', 'classified', 'classification_failed')),
          classified_at TIMESTAMPTZ NULL,
          materiality_score NUMERIC(4, 3) NULL,
          is_material BOOLEAN NULL,
          notes TEXT NULL,
          CONSTRAINT uq_filings_fingerprint UNIQUE (source, source_id, content_hash)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_company_filed ON filings.documents (company_id, filed_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_extraction_status ON filings.documents (extraction_status) WHERE extraction_status != 'extracted';")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_classification_status ON filings.documents (classification_status) WHERE classification_status != 'classified';")
    op.execute("CREATE INDEX IF NOT EXISTS idx_filings_material ON filings.documents (is_material, filed_at DESC) WHERE is_material = true;")

    op.execute("ALTER TABLE coverage.corporate_actions ADD CONSTRAINT fk_corporate_actions_source_filing FOREIGN KEY (source_filing_id) REFERENCES filings.documents(id);")
    op.execute("ALTER TABLE coverage.accounting_policies ADD CONSTRAINT fk_accounting_policies_source_filing FOREIGN KEY (source_filing_id) REFERENCES filings.documents(id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.parsed_versions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id UUID NOT NULL REFERENCES filings.documents(id),
          parser_name TEXT NOT NULL,
          parser_version TEXT NOT NULL,
          parsed_text TEXT NULL,
          parsed_tables JSONB NULL,
          extraction_confidence NUMERIC(4, 3) NULL,
          is_current BOOLEAN NOT NULL DEFAULT true,
          parsed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          notes TEXT NULL
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_parsed_current ON filings.parsed_versions (document_id) WHERE is_current = true;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.classifications (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id UUID NOT NULL REFERENCES filings.documents(id),
          classifier_version TEXT NOT NULL,
          document_type TEXT NOT NULL,
          document_subtype TEXT NULL,
          materiality_score NUMERIC(4, 3) NOT NULL,
          reasoning TEXT NULL,
          extracted_metrics JSONB NULL,
          workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_classifications_document ON filings.classifications (document_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.transcripts (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id UUID NOT NULL REFERENCES coverage.companies(id),
          event_type TEXT NOT NULL CHECK (event_type IN ('earnings_call', 'analyst_meet', 'investor_day', 'other')),
          event_date DATE NOT NULL,
          source TEXT NOT NULL,
          source_id TEXT NULL,
          full_text TEXT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          notes TEXT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.transcript_turns (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          transcript_id UUID NOT NULL REFERENCES filings.transcripts(id),
          turn_index INTEGER NOT NULL,
          speaker TEXT NULL,
          speaker_role TEXT NULL CHECK (speaker_role IN ('management', 'analyst', 'moderator', 'unknown') OR speaker_role IS NULL),
          text TEXT NOT NULL,
          timestamp_seconds INTEGER NULL,
          CONSTRAINT uq_turn_index UNIQUE (transcript_id, turn_index)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_turns_transcript ON filings.transcript_turns (transcript_id, turn_index);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS filings.filings_embeddings (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_table TEXT NOT NULL,
          source_row_id UUID NOT NULL,
          chunk_index INTEGER NOT NULL DEFAULT 0,
          chunk_text TEXT NOT NULL,
          embedding VECTOR(1024) NOT NULL,
          embedding_model TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_filings_embedding UNIQUE (source_table, source_row_id, chunk_index, embedding_model)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_filings_embeddings_vec ON filings.filings_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_raw.valuepickr_posts (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          thread_id TEXT NOT NULL,
          thread_title TEXT NOT NULL,
          post_id TEXT NOT NULL,
          post_url TEXT NOT NULL,
          author TEXT NOT NULL,
          posted_at TIMESTAMPTZ NOT NULL,
          raw_html TEXT NOT NULL,
          text_content TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          classification_status TEXT NOT NULL DEFAULT 'pending',
          signal_score NUMERIC(4, 3) NULL,
          related_company_ids JSONB NULL,
          CONSTRAINT uq_vp_post UNIQUE (post_id, content_hash)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_raw.telegram_messages (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          channel_id TEXT NOT NULL,
          channel_name TEXT NOT NULL,
          message_id TEXT NOT NULL,
          posted_at TIMESTAMPTZ NOT NULL,
          text_content TEXT NULL,
          has_attachment BOOLEAN NOT NULL DEFAULT false,
          attachment_path TEXT NULL,
          content_hash TEXT NOT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          classification_status TEXT NOT NULL DEFAULT 'pending',
          signal_score NUMERIC(4, 3) NULL,
          related_company_ids JSONB NULL,
          CONSTRAINT uq_tg_msg UNIQUE (channel_id, message_id)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_raw.news_articles (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_publication TEXT NOT NULL,
          url TEXT NOT NULL,
          title TEXT NOT NULL,
          author TEXT NULL,
          published_at TIMESTAMPTZ NOT NULL,
          raw_html TEXT NULL,
          text_content TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          classification_status TEXT NOT NULL DEFAULT 'pending',
          relevance_score NUMERIC(4, 3) NULL,
          related_company_ids JSONB NULL,
          CONSTRAINT uq_news_url UNIQUE (url, content_hash)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.tool_calls (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
          call_index INTEGER NOT NULL,
          tool_name TEXT NOT NULL,
          arguments JSONB NOT NULL,
          result_summary JSONB NULL,
          status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
          error_details TEXT NULL,
          duration_ms INTEGER NULL,
          called_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT uq_tool_call_idx UNIQUE (workflow_run_id, call_index)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_run ON ops.tool_calls (workflow_run_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.review_queue (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          tier SMALLINT NOT NULL CHECK (tier IN (1, 2, 3)),
          bundle_id UUID NULL,
          workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
          write_type TEXT NOT NULL,
          target_schema TEXT NOT NULL,
          target_table TEXT NOT NULL,
          target_row_id TEXT NULL,
          proposed_payload JSONB NOT NULL,
          current_state JSONB NULL,
          source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
          derivation_provenance_id UUID NULL REFERENCES coverage.derivations(id),
          claim_provenance_id UUID NULL REFERENCES coverage.claim_provenance(id),
          confidence_score NUMERIC(4,3) NULL,
          verify_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
          state TEXT NOT NULL CHECK (state IN ('created', 'pending_review', 'under_review', 'accepted', 'rejected', 'accepted_with_edits', 'escalated', 'expired', 'failed')),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          pending_since TIMESTAMPTZ NULL,
          opened_at TIMESTAMPTZ NULL,
          resolved_at TIMESTAMPTZ NULL,
          resolved_by TEXT NULL CHECK (resolved_by IN ('analyst', 'auto_applied', 'expired') OR resolved_by IS NULL),
          rejection_reason TEXT NULL,
          rejection_notes TEXT NULL,
          quality_rating SMALLINT NULL CHECK (quality_rating IN (1, 2, 3) OR quality_rating IS NULL),
          edited_payload JSONB NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_state_tier ON ops.review_queue (state, tier);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_bundle ON ops.review_queue (bundle_id) WHERE bundle_id IS NOT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_pending ON ops.review_queue (pending_since) WHERE state IN ('pending_review', 'under_review');")
    op.execute(
        "ALTER TABLE coverage.recompute_queue ADD CONSTRAINT fk_recompute_queue_resolution_queue_item FOREIGN KEY (resolution_queue_item_id) REFERENCES ops.review_queue(id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.tier_rules (
          write_type TEXT PRIMARY KEY,
          base_tier SMALLINT NOT NULL CHECK (base_tier IN (1, 2, 3)),
          current_tier SMALLINT NOT NULL CHECK (current_tier IN (1, 2, 3)),
          tier_promoted_until TIMESTAMPTZ NULL,
          tier_promoted_reason TEXT NULL,
          notes TEXT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.queue_audits (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          audited_item_id UUID NOT NULL REFERENCES ops.review_queue(id),
          audited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          audited_by TEXT NOT NULL DEFAULT 'analyst',
          audit_result TEXT NOT NULL CHECK (audit_result IN ('correct', 'incorrect', 'flagged')),
          audit_notes TEXT NULL
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.eval_golden_set (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          eval_type TEXT NOT NULL,
          input_payload JSONB NOT NULL,
          expected_output JSONB NOT NULL,
          source_workflow_run_id UUID NULL REFERENCES ops.workflow_runs(id),
          source_queue_item_id UUID NULL,
          notes TEXT NULL,
          is_active BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          created_by TEXT NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_golden_eval_type ON ops.eval_golden_set (eval_type) WHERE is_active = true;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.eval_runs (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          golden_id UUID NOT NULL REFERENCES ops.eval_golden_set(id),
          workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
          ran_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          passed BOOLEAN NOT NULL,
          diff JSONB NULL,
          failure_categories JSONB NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_eval_runs_golden_time ON ops.eval_runs (golden_id, ran_at DESC);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.alerts (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'error', 'critical')),
          source TEXT NOT NULL,
          alert_type TEXT NOT NULL,
          message TEXT NOT NULL,
          details JSONB NULL,
          acknowledged BOOLEAN NOT NULL DEFAULT false,
          acknowledged_at TIMESTAMPTZ NULL,
          acknowledged_by TEXT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_alerts_unack ON ops.alerts (severity, created_at DESC) WHERE acknowledged = false;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ops.system_state (
          key TEXT PRIMARY KEY,
          value JSONB NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_by TEXT NOT NULL
        );
        """
    )

    op.execute(
        "CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;"
    )

    op.execute("GRANT USAGE ON SCHEMA coverage, filings, ingestion_raw, ops TO ingestion_filings_role, extraction_role, orchestrator_role, approval_processor_role, web_role;")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA coverage, filings, ingestion_raw, ops TO ingestion_filings_role, extraction_role, orchestrator_role, approval_processor_role, web_role;")
    op.execute("GRANT INSERT ON ALL TABLES IN SCHEMA filings TO ingestion_filings_role;")
    op.execute("GRANT INSERT ON ALL TABLES IN SCHEMA ingestion_raw TO ingestion_filings_role;")
    op.execute("GRANT UPDATE (parsed_text, parsed_tables, extraction_status, extracted_at) ON filings.documents TO extraction_role;")
    op.execute("GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA ops TO orchestrator_role;")
    op.execute("GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA coverage TO approval_processor_role;")
    op.execute("GRANT INSERT, UPDATE ON ops.review_queue TO approval_processor_role;")
    op.execute("GRANT INSERT ON ops.review_queue TO web_role;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ops.queue_audits;")
    op.execute("DROP TABLE IF EXISTS ops.eval_runs;")
    op.execute("DROP TABLE IF EXISTS ops.eval_golden_set;")
    op.execute("DROP TABLE IF EXISTS ops.alerts;")
    op.execute("DROP TABLE IF EXISTS ops.system_state;")

    op.execute("DROP TABLE IF EXISTS filings.filings_embeddings;")
    op.execute("DROP TABLE IF EXISTS filings.transcript_turns;")
    op.execute("DROP TABLE IF EXISTS filings.transcripts;")
    op.execute("DROP TABLE IF EXISTS filings.classifications;")
    op.execute("DROP TABLE IF EXISTS filings.parsed_versions;")

    op.execute("DROP TABLE IF EXISTS ingestion_raw.news_articles;")
    op.execute("DROP TABLE IF EXISTS ingestion_raw.telegram_messages;")
    op.execute("DROP TABLE IF EXISTS ingestion_raw.valuepickr_posts;")

    op.execute("DROP TABLE IF EXISTS coverage.coverage_embeddings;")
    op.execute("DROP TABLE IF EXISTS coverage.recompute_queue;")
    op.execute("DROP TABLE IF EXISTS ops.review_queue;")
    op.execute("DROP TABLE IF EXISTS ops.tier_rules;")
    op.execute("DROP TABLE IF EXISTS ops.tool_calls;")
    op.execute("DROP TABLE IF EXISTS coverage.accounting_policies;")
    op.execute("DROP TABLE IF EXISTS coverage.corporate_actions;")
    op.execute("DROP TABLE IF EXISTS coverage.consensus_pulls;")
    op.execute("DROP TABLE IF EXISTS coverage.catalysts;")
    op.execute("DROP TABLE IF EXISTS coverage.drivers;")
    op.execute("DROP TABLE IF EXISTS coverage.theses_meta;")
    op.execute("DROP TABLE IF EXISTS coverage.estimate_rationale;")
    op.execute("DROP TABLE IF EXISTS coverage.financials;")
    op.execute("DROP TABLE IF EXISTS coverage.claim_provenance;")
    op.execute("DROP TABLE IF EXISTS coverage.derivations;")
    op.execute("DROP TABLE IF EXISTS coverage.source_provenance;")
    op.execute("DROP TABLE IF EXISTS filings.documents;")
    op.execute("DROP TABLE IF EXISTS coverage.companies;")

    op.execute("DROP TABLE IF EXISTS ops.workflow_runs;")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    op.execute("DROP ROLE IF EXISTS web_role;")
    op.execute("DROP ROLE IF EXISTS approval_processor_role;")
    op.execute("DROP ROLE IF EXISTS orchestrator_role;")
    op.execute("DROP ROLE IF EXISTS extraction_role;")
    op.execute("DROP ROLE IF EXISTS ingestion_filings_role;")

    op.execute("DROP SCHEMA IF EXISTS ops CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS ingestion_raw CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS filings CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS coverage CASCADE;")
