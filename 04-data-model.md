# AgentOS — Data Model

## 0. Document Control

| Field | Value |
| --- | --- |
| Document ID | 04 |
| Title | Data Model |
| Version | 1.0 |
| Status | Draft for review |
| Owner | Mohit Agarwal |
| Audience | Mohit, OpenClaw, Codex, future-Mohit |
| Repo location | `04-data-model.md` |
| Related ADRs | ADR-002, ADR-005, ADR-011, ADR-013, ADR-014, ADR-022, ADR-025, ADR-026 |

---

## 1. Purpose

This document defines the complete schema for AgentOS Postgres. It covers:
- All four schemas (`coverage`, `filings`, `ingestion_raw`, `ops`)
- Three-layer provenance (source / derivation / claim)
- Indian-conventions richness (corporate actions, accounting policies, consolidation basis, restatements)
- Idempotency (deterministic fingerprints)
- Role-based GRANTs
- pgvector embedding tables
- Indices, constraints, and the rationale behind them

This is the document Codex turns into Alembic migrations. Schema changes start here, not in code.

---

## 2. Conventions

### 2.1 Naming

- All tables `snake_case`, plural where natural (`companies`, `financials`), singular for single-row state (`system_state`).
- Primary keys: `id UUID` unless natural keys exist (`bse_code` for companies, fingerprints for ingestion).
- Foreign key columns: `<entity>_id` (e.g., `company_id`).
- Timestamps: `created_at`, `updated_at`, `<event>_at` for specific events. All `TIMESTAMPTZ` in UTC.
- Booleans: `is_<x>` or `has_<x>`.
- Enums: stored as `TEXT` with `CHECK` constraints, not Postgres enums (easier to migrate).

### 2.2 Period representation

Indian FY conventions throughout. Two columns per period-bearing row:

- `period_label TEXT NOT NULL` — the human format: `FY26`, `1QFY26`, `H1FY26`
- `period_end_date DATE NOT NULL` — the exact end date: `2026-03-31`, `2025-06-30`, `2025-09-30`

Both are required. `period_label` is for display and reporting. `period_end_date` is for sorting, querying, and joins. They must be consistent (validation in `core/utils/period.py`).

### 2.3 Money

- Currency stored as ISO code in `currency CHAR(3) NOT NULL` — typically `INR` or `USD`
- Values stored as `NUMERIC(20, 4)` — sufficient precision, avoids float drift
- Unit stored as `unit TEXT NOT NULL` — `crore` (₹), `million` (USD), `thousand` (USD), `units` (counts), `pct` (percentages), `bps` (basis points)
- No assumption that "INR" implies "crore" — explicit unit always

### 2.4 Provenance columns

Every fact row carries:

- `source_provenance_id UUID NULL` — for raw extracted facts
- `derivation_provenance_id UUID NULL` — for derived/computed facts
- `claim_provenance_id UUID NULL` — for synthesised narrative claims (rare on numeric tables; common on thesis/note tables)

At least one must be non-null. Validated by trigger.

### 2.5 Audit columns

Every table that experiences updates carries:

- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (with trigger)
- `created_by TEXT NOT NULL` — role or workflow_run_id that wrote
- `last_updated_by TEXT NULL`

Hard-delete is forbidden by convention; use `is_active BOOLEAN` or status fields. Exception: `ingestion_raw.*` can be aggressively pruned per retention policy.

### 2.6 Soft delete vs versioning

For `coverage.financials` and other estimate tables: superseded rows get `is_active = false` and a `superseded_by_id` link to the new row. Original retained for audit.

For theses: prose lives in git (ADR-022); only metadata is in DB; `coverage.theses_meta` has version pointer fields.

### 2.7 Identifiers

Companies use `bse_code` as the canonical identifier (TEXT, not numeric — leading zeros possible). NSE symbol stored separately. UUID `id` exists too for FK convenience.

---

## 3. Schemas Overview

| Schema | Purpose | Write role | Read |
| --- | --- | --- | --- |
| `coverage` | Companies, financials, estimates, drivers, catalysts, theses metadata, three provenance tables, corporate actions, accounting policies | `approval_processor_role` only | All app roles |
| `filings` | BSE filings (raw + parsed), transcripts (when available) | `ingestion_filings_role`, `extraction_role` | All app roles |
| `ingestion_raw` | Pre-classification dumps (post-v1 sources) | Respective ingestion roles | All app roles |
| `ops` | Workflow runs, approval queue, tier rules, evals, alerts, system state | `orchestrator_role`, `approval_processor_role` | All app roles |

### 3.1 Role-based GRANTs (ADR-013)

```sql
-- Roles
CREATE ROLE ingestion_filings_role NOINHERIT;
CREATE ROLE extraction_role NOINHERIT;
CREATE ROLE orchestrator_role NOINHERIT;
CREATE ROLE approval_processor_role NOINHERIT;
CREATE ROLE web_role NOINHERIT;

-- Read access (all roles)
GRANT USAGE ON SCHEMA coverage, filings, ingestion_raw, ops TO
  ingestion_filings_role, extraction_role, orchestrator_role,
  approval_processor_role, web_role;

GRANT SELECT ON ALL TABLES IN SCHEMA coverage, filings, ingestion_raw, ops TO
  ingestion_filings_role, extraction_role, orchestrator_role,
  approval_processor_role, web_role;

-- Write access (per-role)
GRANT INSERT ON ALL TABLES IN SCHEMA filings TO ingestion_filings_role;
GRANT INSERT ON ALL TABLES IN SCHEMA ingestion_raw TO ingestion_filings_role;

GRANT UPDATE (parsed_text, parsed_tables, extraction_status, extracted_at)
  ON filings.documents TO extraction_role;

GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA ops TO orchestrator_role;

GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA coverage TO approval_processor_role;
GRANT INSERT, UPDATE ON ops.review_queue TO approval_processor_role;

GRANT INSERT ON ops.review_queue TO web_role;  -- analyst rejections via UI
```

Role grants live in `db/roles/grants.sql` and are re-applied on every migration.

---

## 4. The `coverage` Schema

The structured knowledge base. Only `approval_processor_role` writes here.

### 4.1 Companies

```sql
CREATE TABLE coverage.companies (
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
  active_thesis_version INTEGER NULL,  -- denormalised pointer; source of truth is theses_meta
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL,
  last_updated_by TEXT NULL
);

CREATE INDEX idx_companies_status ON coverage.companies (coverage_status);
CREATE INDEX idx_companies_sector ON coverage.companies (sector);
```

### 4.2 Financials

The central fact table. Long format, not wide.

```sql
CREATE TABLE coverage.financials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  period_label TEXT NOT NULL,
  period_end_date DATE NOT NULL,
  metric TEXT NOT NULL,  -- e.g., 'revenue', 'ebitda', 'pat', 'segment_revenue_arv', 'gross_margin_pct'
  value NUMERIC(20, 4) NOT NULL,
  currency CHAR(3) NOT NULL,
  unit TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN (
    'actual', 'our_estimate', 'consensus', 'guidance', 'prior_estimate', 'prior_consensus'
  )),
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
    source_provenance_id IS NOT NULL
    OR derivation_provenance_id IS NOT NULL
    OR claim_provenance_id IS NOT NULL
  )
);

-- One active row per (company, period, metric, type, basis, scenario)
CREATE UNIQUE INDEX uq_financials_active ON coverage.financials (
  company_id, period_end_date, metric, type, consolidation_basis, scenario
) WHERE is_active = true;

CREATE INDEX idx_financials_company_period ON coverage.financials (company_id, period_end_date DESC);
CREATE INDEX idx_financials_metric ON coverage.financials (metric);
CREATE INDEX idx_financials_type ON coverage.financials (type);
```

**Why long format:** Metrics evolve (new segments, new ratios), differ per company (Laurus has `segment_revenue_arv`; Cohance has `segment_revenue_specialty_chemicals`), and consensus often covers a subset of metrics. Wide format would force schema migrations for every new metric and hold consensus alongside our estimates awkwardly. Long format is the right call.

**Why scenarios:** Bull/bear sensitivities should sit in the same table, tagged. Querying "show me bull-case FY27 EBITDA across coverage" is one filter, not a separate table.

**Restatement workflow:** When a company restates an actual, the old row is marked `is_active=false`, `superseded_by_id` set, `superseded_reason` filled. New row inserted as the active version. Original is retained.

### 4.3 Source provenance

```sql
CREATE TABLE coverage.source_provenance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL CHECK (source_type IN (
    'bse_filing', 'transcript', 'excel_model', 'visible_alpha', 'manual_entry',
    'press_release', 'investor_presentation', 'broker_note',
    -- post-v1 additions:
    'valuepickr_post', 'telegram_message', 'news_article', 'twitter_post'
  )),
  source_id TEXT NOT NULL,  -- the upstream ID (filing UUID, Excel filename, VA pull ID, etc.)
  document_path TEXT NULL,  -- filesystem path for binary sources
  page_number INTEGER NULL,
  table_index INTEGER NULL,
  row_number INTEGER NULL,
  cell_reference TEXT NULL,  -- "B27" for Excel, "page-3-table-2-row-4" for PDFs
  bounding_box JSONB NULL,  -- camelot/pdfplumber coords for image rendering in UI
  raw_text TEXT NULL,  -- the actual extracted snippet
  extracted_by TEXT NOT NULL,  -- 'pdfplumber', 'camelot', 'openpyxl', 'manual', etc.
  extraction_confidence NUMERIC(4, 3) NULL,
  extracted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT NULL
);

CREATE INDEX idx_source_provenance_source ON coverage.source_provenance (source_type, source_id);
```

### 4.4 Derivation provenance

```sql
CREATE TABLE coverage.derivations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  formula TEXT NOT NULL,  -- human-readable: "revenue * gross_margin_pct"
  formula_hash TEXT NOT NULL,  -- SHA256 of canonicalised formula for change detection
  formula_version INTEGER NOT NULL DEFAULT 1,
  inputs JSONB NOT NULL,  -- array of {role: 'revenue', source_row_id: UUID, source_table: 'coverage.financials'}
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  computed_by TEXT NOT NULL,  -- 'modeling/excel_adapter', 'agents/variance_analysis', etc.
  notes TEXT NULL
);

CREATE INDEX idx_derivations_formula_hash ON coverage.derivations (formula_hash);
```

The `inputs` JSONB encodes the dependency graph. When a source row is corrected, blast-radius walking traverses this column to identify dependents. (See §4.16 below for `recompute_queue`.)

### 4.5 Claim provenance

```sql
CREATE TABLE coverage.claim_provenance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_text TEXT NOT NULL,  -- the synthesised sentence/paragraph this evidence supports
  evidence JSONB NOT NULL,  -- array of {type: 'filing', id: UUID, snippet: '...', relevance: 0.9}
  workflow_run_id UUID NULL REFERENCES ops.workflow_runs(id),
  synthesised_by TEXT NOT NULL,  -- agent name + version
  synthesised_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT NULL
);

CREATE INDEX idx_claim_provenance_workflow ON coverage.claim_provenance (workflow_run_id);
```

Used primarily for narrative claims in earnings prep, variance analysis, and thesis revisions. Each evidence array entry links to a concrete source row (filing turn, source_provenance, prior thesis version).

### 4.6 Estimate rationale

```sql
CREATE TABLE coverage.estimate_rationale (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  financials_id UUID NOT NULL REFERENCES coverage.financials(id),
  rationale_text TEXT NOT NULL,
  key_assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,  -- array of {name, value, unit, notes}
  sensitivities JSONB NOT NULL DEFAULT '[]'::jsonb,  -- array of {variable, range, impact}
  key_risks JSONB NOT NULL DEFAULT '[]'::jsonb,
  claim_provenance_id UUID NULL REFERENCES coverage.claim_provenance(id),
  is_active BOOLEAN NOT NULL DEFAULT true,
  superseded_by_id UUID NULL REFERENCES coverage.estimate_rationale(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL,
  last_updated_by TEXT NULL
);

CREATE INDEX idx_estimate_rationale_financials ON coverage.estimate_rationale (financials_id) WHERE is_active = true;
```

Hangs off rows in `financials` where `type='our_estimate'`. Captures the *why*. Versioned same way as financials.

### 4.7 Theses metadata (prose in git per ADR-022)

```sql
CREATE TABLE coverage.theses_meta (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  version INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived', 'superseded')),
  written_at TIMESTAMPTZ NOT NULL,
  activated_at TIMESTAMPTZ NULL,
  archived_at TIMESTAMPTZ NULL,
  superseded_by_version INTEGER NULL,
  markdown_path TEXT NOT NULL,  -- 'coverage_theses/laurus/v3.md'
  markdown_git_sha TEXT NOT NULL,  -- locked git SHA when this version was activated
  -- denormalised from front matter for queryability:
  variant_perception_summary TEXT NULL,
  key_drivers JSONB NULL,
  time_horizon_months INTEGER NULL,
  next_review_due DATE NULL,
  -- audit:
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL,
  last_updated_by TEXT NULL,
  CONSTRAINT one_active_per_company UNIQUE (company_id, status) DEFERRABLE INITIALLY DEFERRED
);

-- Only one active thesis per company at a time
CREATE UNIQUE INDEX uq_theses_one_active ON coverage.theses_meta (company_id) WHERE status = 'active';
```

Loader script `scripts/sync_theses.py` runs at startup and after any merge to populate `theses_meta` from front matter in `coverage_theses/<company>/v<n>.md`. Front-matter schema:

```yaml
---
company: laurus
version: 3
status: active
written_at: 2026-04-15
variant_perception_summary: "CDMO ramp ahead of consensus"
key_drivers:
  - name: cdmo_revenue
    direction: up
    magnitude: high
  - name: arv_pricing
    direction: down
    magnitude: medium
time_horizon_months: 12
next_review_due: 2026-07-15
---
```

### 4.8 Drivers

```sql
CREATE TABLE coverage.drivers (
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
```

Driver status changes are Tier 3 writes (high-stakes); flips from `tracking` to `behind/deteriorating` are inline with thesis health.

### 4.9 Catalysts

```sql
CREATE TABLE coverage.catalysts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  catalyst_type TEXT NOT NULL CHECK (catalyst_type IN (
    'earnings', 'guidance', 'regulatory', 'capacity', 'product', 'corporate_action', 'macro', 'other'
  )),
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

CREATE INDEX idx_catalysts_company_date ON coverage.catalysts (company_id, expected_date);
CREATE INDEX idx_catalysts_status ON coverage.catalysts (status);
```

### 4.10 Corporate actions (ADR-025)

```sql
CREATE TABLE coverage.corporate_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  action_type TEXT NOT NULL CHECK (action_type IN (
    'split', 'bonus', 'rights', 'buyback', 'demerger', 'merger', 'acquisition',
    'dividend_special', 'capital_reduction', 'name_change', 'isin_change', 'other'
  )),
  effective_date DATE NOT NULL,
  ratio_or_amount TEXT NOT NULL,  -- "1:5" for split, "100 INR/share" for buyback, etc.
  adjustment_factor NUMERIC(20, 8) NULL,  -- multiplier for historical price/share series
  description TEXT NOT NULL,
  source_filing_id UUID NULL REFERENCES filings.documents(id),
  source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL,
  last_updated_by TEXT NULL
);

CREATE INDEX idx_corp_actions_company_date ON coverage.corporate_actions (company_id, effective_date);
```

### 4.11 Accounting policies (ADR-025)

```sql
CREATE TABLE coverage.accounting_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  policy_version TEXT NOT NULL,  -- 'IndAS-2018', 'IndAS-2020-segment-reclassification', etc.
  effective_from DATE NOT NULL,
  effective_to DATE NULL,
  notes TEXT NOT NULL,
  source_filing_id UUID NULL REFERENCES filings.documents(id),
  source_provenance_id UUID NULL REFERENCES coverage.source_provenance(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL,
  last_updated_by TEXT NULL,
  CONSTRAINT uq_policy_company_version UNIQUE (company_id, policy_version)
);
```

`coverage.financials.accounting_policy_version` references the `policy_version` here, allowing financials rows to declare which policy they were prepared under.

### 4.12 Visible Alpha consensus

```sql
CREATE TABLE coverage.consensus_pulls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  pulled_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL DEFAULT 'visible_alpha',
  raw_payload JSONB NOT NULL,  -- full VA response
  processed BOOLEAN NOT NULL DEFAULT false,
  notes TEXT NULL
);

CREATE INDEX idx_consensus_pulls_company_time ON coverage.consensus_pulls (company_id, pulled_at DESC);
```

Each pull is a snapshot. Individual consensus values are extracted into `coverage.financials` with `type='consensus'` and `source_provenance` pointing at the pull. When a new pull supersedes an old one, prior consensus rows get `type='prior_consensus'`.

### 4.13 Recompute queue (ADR-026 — blast-radius tooling)

```sql
CREATE TABLE coverage.recompute_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  triggered_by_correction_id UUID NOT NULL,  -- the corrected row that triggered this walk
  affected_table TEXT NOT NULL,
  affected_row_id UUID NOT NULL,
  derivation_id UUID NOT NULL REFERENCES coverage.derivations(id),
  walk_distance INTEGER NOT NULL,  -- 1 = direct dependent, 2 = dependent of dependent, etc.
  status TEXT NOT NULL CHECK (status IN ('pending', 'recomputed', 'manually_resolved', 'dismissed')),
  recomputed_value NUMERIC(20, 4) NULL,
  resolution_queue_item_id UUID NULL REFERENCES ops.review_queue(id),  -- the queue item created to handle this
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ NULL,
  resolved_by TEXT NULL
);

CREATE INDEX idx_recompute_pending ON coverage.recompute_queue (status, created_at) WHERE status = 'pending';
```

When a `coverage.financials` row is corrected post-application, the queue processor walks `coverage.derivations.inputs` to find rows that referenced the corrected row, populates `recompute_queue`, and queues each as a new Tier 3 review item.

### 4.14 Embeddings

```sql
CREATE TABLE coverage.coverage_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_table TEXT NOT NULL,  -- 'coverage.estimate_rationale', 'coverage.theses_meta', etc.
  source_row_id UUID NOT NULL,
  chunk_index INTEGER NOT NULL DEFAULT 0,
  chunk_text TEXT NOT NULL,
  embedding VECTOR(1024) NOT NULL,  -- Voyage AI dimension
  embedding_model TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_coverage_embedding UNIQUE (source_table, source_row_id, chunk_index, embedding_model)
);

CREATE INDEX idx_coverage_embeddings_vec ON coverage.coverage_embeddings
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 5. The `filings` Schema

Raw documents and parsed extracts. `ingestion_filings_role` writes raw rows; `extraction_role` updates parsed columns.

### 5.1 Documents

```sql
CREATE TABLE filings.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  source TEXT NOT NULL DEFAULT 'bse' CHECK (source IN ('bse', 'nse', 'company_website', 'manual')),
  source_id TEXT NOT NULL,  -- BSE filing ID
  content_hash TEXT NOT NULL,  -- SHA256 of binary content
  document_type TEXT NULL,  -- populated by classifier; 'results', 'press_release', 'investor_presentation', 'corporate_action', 'other'
  document_subtype TEXT NULL,  -- 'quarterly_results', 'annual_results', 'segment_disclosure', etc.
  filing_title TEXT NOT NULL,
  filed_at TIMESTAMPTZ NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  filesystem_path TEXT NOT NULL,
  page_count INTEGER NULL,
  raw_text TEXT NULL,  -- pdfplumber output
  parsed_tables JSONB NULL,  -- camelot output
  extraction_status TEXT NOT NULL DEFAULT 'pending' CHECK (extraction_status IN (
    'pending', 'extracted', 'extraction_failed', 'partial'
  )),
  extracted_at TIMESTAMPTZ NULL,
  classification_status TEXT NOT NULL DEFAULT 'pending' CHECK (classification_status IN (
    'pending', 'classified', 'classification_failed'
  )),
  classified_at TIMESTAMPTZ NULL,
  materiality_score NUMERIC(4, 3) NULL,  -- 0.0–1.0 from classifier
  is_material BOOLEAN NULL,  -- derived: materiality_score > threshold
  notes TEXT NULL,
  CONSTRAINT uq_filings_fingerprint UNIQUE (source, source_id, content_hash)
);

CREATE INDEX idx_filings_company_filed ON filings.documents (company_id, filed_at DESC);
CREATE INDEX idx_filings_extraction_status ON filings.documents (extraction_status) WHERE extraction_status != 'extracted';
CREATE INDEX idx_filings_classification_status ON filings.documents (classification_status) WHERE classification_status != 'classified';
CREATE INDEX idx_filings_material ON filings.documents (is_material, filed_at DESC) WHERE is_material = true;
```

**Idempotency (ADR-014):** The unique constraint on `(source, source_id, content_hash)` enforces it. Re-ingestion of the same artefact is a no-op; same URL with new content gets a new row (the previous filing isn't lost — both retained).

### 5.2 Document parsings (multi-version)

When a parser is improved and re-run on existing documents, we want the new parse without losing the old.

```sql
CREATE TABLE filings.parsed_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES filings.documents(id),
  parser_name TEXT NOT NULL,  -- 'pdfplumber-1.0', 'camelot-2.1', etc.
  parser_version TEXT NOT NULL,
  parsed_text TEXT NULL,
  parsed_tables JSONB NULL,
  extraction_confidence NUMERIC(4, 3) NULL,
  is_current BOOLEAN NOT NULL DEFAULT true,
  parsed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT NULL
);

CREATE UNIQUE INDEX uq_parsed_current ON filings.parsed_versions (document_id) WHERE is_current = true;
```

The columns on `filings.documents.parsed_text` and `parsed_tables` reflect the current parse for convenience. The `parsed_versions` table is the audit history.

### 5.3 Document classifications

Output of the `filings_classifier` agent (Haiku).

```sql
CREATE TABLE filings.classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES filings.documents(id),
  classifier_version TEXT NOT NULL,
  document_type TEXT NOT NULL,
  document_subtype TEXT NULL,
  materiality_score NUMERIC(4, 3) NOT NULL,
  reasoning TEXT NULL,  -- agent's brief justification
  extracted_metrics JSONB NULL,  -- candidate (metric, period, value, unit) tuples for staging
  workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_classifications_document ON filings.classifications (document_id);
```

The `extracted_metrics` JSONB stages candidate financial extractions. They flow into the approval queue as a Tier 2 bundle. On acceptance, they become rows in `coverage.financials` (with `type='actual'` and source provenance pointing at the document).

### 5.4 Transcripts (placeholder for future)

```sql
CREATE TABLE filings.transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES coverage.companies(id),
  event_type TEXT NOT NULL CHECK (event_type IN ('earnings_call', 'analyst_meet', 'investor_day', 'other')),
  event_date DATE NOT NULL,
  source TEXT NOT NULL,  -- 'bse_audio', 'company_website', 'manual', 'self_built_quartr_replacement'
  source_id TEXT NULL,
  full_text TEXT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT NULL
);

CREATE TABLE filings.transcript_turns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id UUID NOT NULL REFERENCES filings.transcripts(id),
  turn_index INTEGER NOT NULL,
  speaker TEXT NULL,
  speaker_role TEXT NULL CHECK (speaker_role IN ('management', 'analyst', 'moderator', 'unknown') OR speaker_role IS NULL),
  text TEXT NOT NULL,
  timestamp_seconds INTEGER NULL,
  CONSTRAINT uq_turn_index UNIQUE (transcript_id, turn_index)
);

CREATE INDEX idx_turns_transcript ON filings.transcript_turns (transcript_id, turn_index);
```

Out of scope for v1 ingestion (per ADR-007); schema present so claim provenance can reference transcript turns once they exist.

### 5.5 Filings embeddings

```sql
CREATE TABLE filings.filings_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_table TEXT NOT NULL,  -- 'filings.documents', 'filings.transcript_turns'
  source_row_id UUID NOT NULL,
  chunk_index INTEGER NOT NULL DEFAULT 0,
  chunk_text TEXT NOT NULL,
  embedding VECTOR(1024) NOT NULL,
  embedding_model TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_filings_embedding UNIQUE (source_table, source_row_id, chunk_index, embedding_model)
);

CREATE INDEX idx_filings_embeddings_vec ON filings.filings_embeddings
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 6. The `ingestion_raw` Schema

Pre-classification dumps for sources beyond filings. Empty in v1; structure defined for future use.

```sql
CREATE TABLE ingestion_raw.valuepickr_posts (
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

CREATE TABLE ingestion_raw.telegram_messages (
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

CREATE TABLE ingestion_raw.news_articles (
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
```

Retention: 180 days hot; older pruned unless referenced by a `coverage.*` row via provenance. Pruning script `scripts/prune_ingestion_raw.py`.

---

## 7. The `ops` Schema

Operational state — workflow runs, approval queue, evals, alerts, system state.

### 7.1 Workflow runs

```sql
CREATE TABLE ops.workflow_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_name TEXT NOT NULL,
  workflow_version TEXT NOT NULL,
  triggered_by TEXT NOT NULL CHECK (triggered_by IN ('analyst', 'cron', 'event', 'eval_harness')),
  triggered_by_detail TEXT NULL,  -- analyst session ID, cron expression, parent event ID, etc.
  input_params JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'partial', 'timeout')),
  started_at TIMESTAMPTZ NULL,
  completed_at TIMESTAMPTZ NULL,
  output_summary JSONB NULL,
  error_details JSONB NULL,
  tool_calls_count INTEGER NOT NULL DEFAULT 0,
  tokens_used INTEGER NOT NULL DEFAULT 0,
  cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
  golden_set_run_id UUID NULL,  -- non-null if this is an eval-harness invocation
  parent_run_id UUID NULL REFERENCES ops.workflow_runs(id),  -- for child workflows
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_runs_workflow ON ops.workflow_runs (workflow_name, created_at DESC);
CREATE INDEX idx_runs_status ON ops.workflow_runs (status) WHERE status IN ('pending', 'running', 'failed', 'partial', 'timeout');
```

### 7.2 Tool call log

```sql
CREATE TABLE ops.tool_calls (
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

CREATE INDEX idx_tool_calls_run ON ops.tool_calls (workflow_run_id);
```

### 7.3 Review queue (full DDL from `05-approval-queue-design.md`)

See §9 of `05-approval-queue-design.md`. Tables: `ops.review_queue`, `ops.tier_rules`, `ops.queue_audits`.

### 7.4 Evals

```sql
CREATE TABLE ops.eval_golden_set (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  eval_type TEXT NOT NULL,  -- 'filings_extraction', 'filings_classification', 'variance_attribution', etc.
  input_payload JSONB NOT NULL,  -- inputs for the eval (e.g., filing path + expected metric list)
  expected_output JSONB NOT NULL,  -- the ground truth
  source_workflow_run_id UUID NULL REFERENCES ops.workflow_runs(id),  -- if seeded from a real run
  source_queue_item_id UUID NULL,  -- if seeded from an analyst-edited queue item
  notes TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by TEXT NOT NULL
);

CREATE INDEX idx_golden_eval_type ON ops.eval_golden_set (eval_type) WHERE is_active = true;

CREATE TABLE ops.eval_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  golden_id UUID NOT NULL REFERENCES ops.eval_golden_set(id),
  workflow_run_id UUID NOT NULL REFERENCES ops.workflow_runs(id),
  ran_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  passed BOOLEAN NOT NULL,
  diff JSONB NULL,  -- structured diff between expected and actual
  failure_categories JSONB NULL  -- e.g., ['period_unit_consolidation', 'extraction_wrong']
);

CREATE INDEX idx_eval_runs_golden_time ON ops.eval_runs (golden_id, ran_at DESC);
```

Detailed in `06-eval-harness-design.md`.

### 7.5 Alerts

```sql
CREATE TABLE ops.alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'error', 'critical')),
  source TEXT NOT NULL,  -- 'ingestion/filings', 'queue_processor', 'eval_harness', etc.
  alert_type TEXT NOT NULL,  -- 'extraction_failure', 'queue_stale', 'cost_spike', etc.
  message TEXT NOT NULL,
  details JSONB NULL,
  acknowledged BOOLEAN NOT NULL DEFAULT false,
  acknowledged_at TIMESTAMPTZ NULL,
  acknowledged_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alerts_unack ON ops.alerts (severity, created_at DESC) WHERE acknowledged = false;
```

### 7.6 System state

```sql
CREATE TABLE ops.system_state (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL
);

-- Seeded:
-- ('mode', '{"value": "normal"}', ...)  -- 'normal' | 'earnings_season'
-- ('embedding_model', '{"name": "voyage-finance-2", "dim": 1024}', ...)
-- ('cost_budget_monthly_usd', '{"value": 200}', ...)
```

---

## 8. Triggers and Constraints (Cross-Cutting)

### 8.1 `updated_at` auto-bump

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied to every table with updated_at column.
```

### 8.2 Provenance non-null check on financials

```sql
-- Already in CHECK constraint on coverage.financials.
-- Reproduced here for completeness:
-- CONSTRAINT financials_provenance_required CHECK (
--   source_provenance_id IS NOT NULL
--   OR derivation_provenance_id IS NOT NULL
--   OR claim_provenance_id IS NOT NULL
-- )
```

### 8.3 Period validation trigger

A trigger validates that `period_label` and `period_end_date` are consistent on every row that has both.

```sql
CREATE OR REPLACE FUNCTION validate_period()
RETURNS TRIGGER AS $$
DECLARE
  expected_label TEXT;
BEGIN
  expected_label := period_label_from_date(NEW.period_end_date);
  IF expected_label != NEW.period_label THEN
    RAISE EXCEPTION 'period_label % inconsistent with period_end_date %', NEW.period_label, NEW.period_end_date;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- period_label_from_date() implemented in core/utils/period.py and
-- mirrored as a Postgres function via Alembic migration.
```

### 8.4 Supersedence integrity

When `is_active=false`, `superseded_by_id` and `superseded_at` must be set. Enforced via CHECK and trigger.

---

## 9. Indexing Strategy

Every table has its primary key. Beyond that, indices are added based on:

1. **Foreign key joins** — every FK column has an index unless the table is small (<1000 rows expected at maturity).
2. **Filtered queries** — partial indices on common filter conditions (e.g., `WHERE is_active = true`).
3. **Time-range queries** — `(entity_id, period_end_date DESC)` for time-series access.
4. **Vector similarity** — `ivfflat` on embedding columns.

Indices not added pre-emptively. Performance is measured before optimisation. `pg_stat_statements` enabled for monitoring.

---

## 10. Migration Discipline

### 10.1 Process

1. Schema change is designed in this document or a successor.
2. Alembic migration is generated.
3. Migration reviewed for backwards compatibility.
4. Applied to dev DB; tests run.
5. Applied to live DB during a designated window (default: outside BSE trading hours).
6. Rollback step verified before apply.

### 10.2 Forward-only in production

Migrations are forward-only on the production DB. Reversal is via a new migration that undoes the change. (Alembic's downgrade is reserved for dev.)

### 10.3 Breaking changes

Require a decision-log entry with:
- What is breaking
- Why
- Rollback plan (the new migration that would undo it if needed)
- Data migration plan if existing rows must be transformed

---

## 11. Backups and Restoration

Detailed in `runbooks/postgres-restore.md` (created when written). Summary:

- `pg_dump --format=custom` daily to off-VPS encrypted bucket
- Retention: 30 days daily, 1 year weekly
- Quarterly restore drill (calendar event)
- Restore time target: <2 hours to a new VPS

---

## 12. Open Questions

1. **Embedding dimension.** Voyage Finance-2 is 1024 dim; if a different model is selected, schema must be updated.
2. **`raw_text` size limits.** Some filings may have very large `raw_text`. Consider TOAST tuning if average row size becomes a hotspot.
3. **`pgvector` index list count.** `lists=100` is a default; tune after first 10K vectors.
4. **Retention on `ops.tool_calls`.** High-volume table. Consider partitioning by month and pruning >180 days.
5. **Multi-currency reporting.** Every value has explicit currency, but cross-currency reports require an FX table — out of scope for v1; revisit when first multi-currency report is needed.

---

## 13. Revision History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | 2026-05-04 | Mohit Agarwal | Initial draft, full schema for all four schemas, three-layer provenance, Indian conventions, role-based grants, idempotency, pgvector tables |
