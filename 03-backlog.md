# AgentOS — Backlog

## 0. Document Control

| Field | Value |
| --- | --- |
| Document ID | 03 |
| Title | Backlog |
| Version | 1.0 (initial seeding for v1 vertical slice) |
| Status | Living document — updated weekly |
| Owner | Mohit Agarwal |
| Audience | Mohit, OpenClaw, Codex, future-Mohit |
| Repo location | `03-backlog.md` |
| Related docs | All — this is the operational driver |

---

## 1. Purpose & Format

### 1.1 What this is

The backlog is the operational driver of the build. It is the document the analyst opens when starting a Codex session. Each item is scoped tightly enough that a single Codex session can land it.

### 1.2 What it is not

Not a roadmap. Not a wishlist. Not a vision document. The backlog is **only** items that are ready or near-ready to build.

### 1.3 Item format

Every item follows this format:

```
### [PHASE-NN] <short title>

**Status:** Ready | Blocked | In Progress | In Review | Done | Deferred
**Phase:** Foundation | Slice | Operate | Expand
**Estimated complexity:** S (≤1 session) | M (2–3 sessions) | L (1–2 weeks) | XL (>2 weeks; consider splitting)
**Dependencies:** PHASE-NN, PHASE-NN
**Blocks:** PHASE-NN, PHASE-NN

**Goal.** One sentence: what is this and why.

**Scope.**
- What's in
- What's in
- What's NOT in (explicitly)

**Acceptance criteria.**
- [ ] Concrete, checkable
- [ ] Concrete, checkable

**Constraints / notes.**
- Anything Codex needs to know that isn't obvious from the docs
- ADRs that govern this work (linked)

**Spec references.**
- Doc and section
- Doc and section
```

### 1.4 Status values

- **Ready** — all dependencies done; can start now
- **Blocked** — waiting on a dependency
- **In Progress** — actively being worked
- **In Review** — Codex submitted; analyst reviewing diff
- **Done** — merged, smoke-tested, decision log updated
- **Deferred** — out of v1 scope per ADR

### 1.5 Phasing

Items are tagged with one of four phases corresponding to the vertical-slice build sequence (ADR-009):

- **Foundation** — schema, infrastructure, role grants, project skeleton, contracts in `core/`
- **Slice** — the actual end-to-end vertical slice: ingestion → extraction → classification → adapter → variance → prep → briefing → eval harness
- **Operate** — running the slice through one earnings season; observing friction
- **Expand** — post-slice work informed by what was learned

Items in Operate and Expand are intentionally sparse in this seed; they will be populated from observed friction during the Operate phase.

### 1.6 Maintenance

- Updated weekly (calendar event).
- Done items move to `## 9. Completed Items` with completion date.
- Deferred items move to `## 10. Deferred Items` with the deferring decision-log entry.
- New items added at the bottom of the relevant phase, then re-ranked.

---

## 2. Foundation Phase

These items establish the platform on which everything else is built. None of the synthesis or extraction work can begin until Foundation is complete.

Pre-step before `F-01`: perform a documentation hygiene checkpoint to ensure all cross-document references resolve to current root-level filenames (especially `01-vision-and-architecture-v1.1.md`).

---

### [F-01] Repository scaffolding

**Status:** Done (2026-05-05)
**Phase:** Foundation
**Estimated complexity:** S
**Dependencies:** —
**Blocks:** Everything

**Goal.** Stand up the monorepo skeleton with module directories, `pyproject.toml`, dev tooling, and CI scaffolding.

**Scope.**
- Directory structure per `01-vision-and-architecture-v1.1.md` §7.1
- `pyproject.toml` with single package definition
- `CONTRIBUTING.md` documenting module boundaries (per ADR-004)
- `pre-commit` configuration (ruff, black, mypy)
- `pytest` configured
- `docker-compose.yml` with Postgres service
- `.env.example` with placeholders for all secrets
- README pointing to the canonical planning docs

**NOT in scope.**
- No actual module code; this is scaffolding only
- No `import-linter` (deferred per ADR-004)

**Acceptance criteria.**
- [x] `pip install -e .` succeeds in a fresh venv
- [x] `docker-compose up -d postgres` brings up Postgres reachable via `psql` (validated in local Docker environment; not runnable in this sandbox)
- [x] `pre-commit run --all-files` passes
- [x] `CONTRIBUTING.md` documents the import boundaries

**Constraints / notes.**
- Python 3.12+
- `pyproject.toml` uses `setuptools` or `hatch`; analyst preference
- Postgres 16+ with `pgvector` extension preinstalled in the Docker image

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §7
- ADR-003, ADR-004

---

### [F-02] Postgres schemas, roles, and base migration
**Status:** In Progress
**Phase:** Foundation
**Estimated complexity:** M
**Dependencies:** F-01
**Blocks:** F-03, F-04, all data tables

**Goal.** Create the four schemas, the five roles with table-level GRANTs, and the initial Alembic migration carrying every base table from `04-data-model.md`.

**Scope.**
- Alembic initialised with multi-schema support
- Migration creates schemas: `coverage`, `filings`, `ingestion_raw`, `ops`
- Migration creates roles: `ingestion_filings_role`, `extraction_role`, `orchestrator_role`, `approval_processor_role`, `web_role`
- All tables from `04-data-model.md` §4–7 created
- All indices, constraints, triggers from §4–8 applied
- `db/roles/grants.sql` re-applied in the migration
- Seed script for `coverage.companies` (8 names) ready but not run

**NOT in scope.**
- No data seeding (separate item)
- No application code reading the schema
- No `pgvector` index tuning beyond defaults

**Acceptance criteria.**
- [ ] `alembic upgrade head` creates all schemas, tables, indices on a fresh DB
- [ ] `alembic downgrade base` reverses cleanly (dev only)
- [ ] All five roles exist with the correct GRANTs (verified by a SQL test)
- [ ] Triggers (`updated_at`, period validation, supersedence integrity) fire correctly on inserts (verified by integration test)
- [ ] Provenance non-null check on `coverage.financials` rejects rows with all three provenance columns null

**Constraints / notes.**
- Migrations are forward-only in production (per `04-data-model.md` §10.2)
- Period validation trigger calls a Postgres function; mirror Python logic from `core/utils/period.py`
- Use `pgcrypto` extension for `gen_random_uuid()`
- Implementation checkpoint (2026-05-05): Alembic scaffold + base migration for extensions/schemas/roles committed; minimal `filings.documents` and `ops.review_queue` tables added to unblock grant wiring. Full table DDL and role-verification tests pending.
- Issue cleanup checkpoint (2026-05-05):
  - [x] CI now installs the package (`pip install -e .`) before checks.
  - [x] `pre-commit` Black hook pinned to a stable version tag.
  - [x] Alembic supports `DATABASE_URL` override for non-local environments.
  - [x] Added migration/readme usage commands for apply/current/downgrade.
  - [ ] Full F-02 schema + role-verification integration tests still pending.

**Spec references.**
- `04-data-model.md` §3–8
- ADR-002, ADR-013

---

### [F-03] `core/` types and utilities

**Status:** Blocked (by F-02)
**Phase:** Foundation
**Estimated complexity:** M
**Dependencies:** F-02
**Blocks:** All modules

**Goal.** Build the shared contracts every module depends on: SQLAlchemy models, Pydantic schemas, period utilities, fingerprinting, logging, exceptions.

**Scope.**
- `core/types/` — SQLAlchemy models for every table in `04-data-model.md`
- `core/types/` — Pydantic schemas for tool inputs/outputs
- `core/utils/period.py` — FY math, period_label ↔ period_end_date conversion (mirrors the Postgres function from F-02)
- `core/utils/fingerprint.py` — content_hash + (source_type, source_id) idempotency fingerprint
- `core/utils/logging.py` — structured logging configuration
- `core/exceptions.py` — domain exceptions (extraction errors, queue conflicts, etc.)
- Unit tests for all utilities

**NOT in scope.**
- Tools (`core/tools/`) — separate item, F-04
- Database session management

**Acceptance criteria.**
- [ ] SQLAlchemy reflection round-trip works (write a row, read it back, types match)
- [ ] Period utility passes tests for: `FY26` ↔ `2026-03-31`, `1QFY26` ↔ `2025-06-30`, `H1FY27` ↔ `2026-09-30`
- [ ] Fingerprint utility produces stable hashes for identical inputs and different hashes for changed content
- [ ] Logging emits structured JSON with `workflow_run_id` propagated through context

**Constraints / notes.**
- Use SQLAlchemy 2.0 typed style (`Mapped[…]`)
- Pydantic v2
- All datetimes are TZ-aware UTC

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §5.12 (Indian conventions)
- `04-data-model.md` §2 (conventions)

---

### [F-04] `core/tools/` — read tools

**Status:** Blocked (by F-03)
**Phase:** Foundation
**Estimated complexity:** M
**Dependencies:** F-03
**Blocks:** All agents

**Goal.** Build the read-only tool layer that agents will use to access the substrate. No write tools yet — those go through the queue and are added in F-05.

**Scope.**
- `core/tools/query_companies.py` — list and fetch companies
- `core/tools/query_financials.py` — query by company/period/metric/type
- `core/tools/search_filings.py` — text search and metadata filter on filings
- `core/tools/get_thesis.py` — fetch active thesis (loads markdown from disk per `coverage.theses_meta.markdown_path`)
- `core/tools/get_drivers.py` — fetch drivers and their statuses
- `core/tools/get_catalysts.py` — fetch upcoming/recent catalysts
- `core/tools/get_consensus.py` — fetch latest Visible Alpha consensus rows
- `core/tools/get_corporate_actions.py` — fetch corporate actions
- Each tool has Pydantic input/output schema, integration test against a seeded test DB

**NOT in scope.**
- Write tools (F-05)
- Embedding-based vector search (F-06)
- Tools for ingestion sources beyond filings (post-v1)

**Acceptance criteria.**
- [ ] Each tool callable with typed inputs returns typed outputs
- [ ] Integration tests pass against a seeded test DB
- [ ] All tools log their inputs/outputs to `ops.tool_calls` when invoked from a workflow run context
- [ ] Tools use `web_role` (read-only) connection by default

**Spec references.**
- `04-data-model.md` (every read tool corresponds to a query against schemas there)
- `01-vision-and-architecture-v1.1.md` §8.3 (tool layer)

---

### [F-05] Approval queue processor and write tools

**Status:** Blocked (by F-04)
**Phase:** Foundation
**Estimated complexity:** L
**Dependencies:** F-04
**Blocks:** F-09, F-10, F-11, F-12

**Goal.** Build the approval queue processor (the only entity that writes to `coverage.*`) and the write tools that propose items into the queue.

**Scope.**
- `core/tools/propose_to_queue.py` — generic write tool that creates a `ops.review_queue` row at the appropriate tier
- `core/queue/tiering.py` — `classify_tier(write_proposal) -> Tier` (per `05-approval-queue-design.md` §3.4)
- `core/queue/processor.py` — the queue processor service: applies accepted writes, runs staleness sweep, walks derivations on correction, runs sample audit
- `ops.tier_rules` seeded with default tier classifications for every known write type
- `core/queue/audit.py` — sample-audit logic for Tier 1 writes
- `core/queue/blast_radius.py` — derivation-walk logic for post-approval corrections (per ADR-026)
- Integration tests: full lifecycle (propose → review → apply), staleness expiry, tier auto-promotion, blast-radius walking

**NOT in scope.**
- The UI for reviewing queue items (F-08)
- Write tools for specific write types (those wrap `propose_to_queue` and are built per consumer)

**Acceptance criteria.**
- [ ] Tier 1 write proposed → applied in same transaction (auto-apply)
- [ ] Tier 2 bundle proposed → all rows in single bundle, single approval applies all atomically
- [ ] Tier 3 item proposed → requires explicit approval before apply
- [ ] Stale Tier 2 item (>7 days) auto-rejects with reason `expired`, alert raised
- [ ] Correction to an applied row triggers blast-radius walk; downstream rows queued in `coverage.recompute_queue`
- [ ] Sample audit (5%) of Tier 1 writes creates `ops.queue_audits` rows
- [ ] Tier auto-promotion fires when Tier 2 rejection rate >30% over 14 days
- [ ] Queue processor runs under `approval_processor_role`; cannot be bypassed

**Constraints / notes.**
- Queue processor is a long-running process under systemd
- All writes to `coverage.*` MUST go through this processor; there is no other way (enforced by GRANTs)
- Use Postgres advisory locks to prevent concurrent processing of the same bundle

**Spec references.**
- `05-approval-queue-design.md` (entire doc)
- ADR-010, ADR-013, ADR-024, ADR-026, ADR-027

---

### [F-06] Embeddings pipeline (Voyage AI)

**Status:** Blocked (by F-03)
**Phase:** Foundation
**Estimated complexity:** S
**Dependencies:** F-03
**Blocks:** F-07 (vector search tool)

**Goal.** Build the embedding generation pipeline so that newly inserted rows in chosen tables get embedded and indexed in `coverage.coverage_embeddings` / `filings.filings_embeddings`.

**Scope.**
- `core/embeddings/embedder.py` — wraps Voyage SDK with batching and error handling
- `core/embeddings/pipeline.py` — listener that detects new rows in `filings.documents`, `filings.transcript_turns` (when present), `coverage.estimate_rationale`, `coverage.theses_meta` and embeds them
- Chunking strategy documented and implemented (default: 512-token chunks with 64-token overlap)
- Backfill script for existing rows
- Cost monitoring (cost per embed logged to `ops.workflow_runs` when triggered as a workflow)

**NOT in scope.**
- Vector search retrieval tool (F-07)
- Reranking (post-v1 if needed)

**Acceptance criteria.**
- [ ] Inserting a new row into `filings.documents` with parsed_text triggers embedding within 60 seconds
- [ ] Embeddings stored with model name and dim in `coverage_embeddings` / `filings_embeddings`
- [ ] Backfill script processes existing rows in batches
- [ ] Cost per 1000 tokens logged

**Constraints / notes.**
- Voyage Finance-2 (or current best finance-tuned model); confirm model name at build time
- Embedding is one-time per chunk per model; never re-embed on read

**Spec references.**
- `04-data-model.md` §4.14, §5.5
- ADR-016

---

### [F-07] Vector search tool

**Status:** Blocked (by F-06)
**Phase:** Foundation
**Estimated complexity:** S
**Dependencies:** F-06
**Blocks:** F-12 (earnings prep), F-11 (variance analysis)

**Goal.** A read tool that does semantic search across embedded content with filter support.

**Scope.**
- `core/tools/search_semantic.py` — accepts query text, filters (company, date range, source type), and returns ranked results
- Query embedding via Voyage
- Cosine similarity via pgvector
- Result post-filtering (company, date, source type)
- Returns chunks + parent row IDs for joining back to source

**NOT in scope.**
- Hybrid search (BM25 + dense). Defer to post-v1 unless retrieval quality is insufficient.

**Acceptance criteria.**
- [ ] Tool returns top-k results within 200ms on a corpus of 10K chunks
- [ ] Filters narrow results before ranking
- [ ] Each result includes `source_table`, `source_row_id`, `chunk_text`, `similarity_score`
- [ ] Logged to `ops.tool_calls`

**Spec references.**
- `04-data-model.md` §4.14, §5.5

---

### [F-08] Streamlit UI — approval queue review

**Status:** Blocked (by F-05)
**Phase:** Foundation
**Estimated complexity:** L
**Dependencies:** F-05
**Blocks:** Operating the slice

**Goal.** Build the analyst's primary surface: the approval queue review UI, with source-side-by-side, batch operations, keyboard navigation, and rejection taxonomy.

**Scope.**
- Streamlit app entry point
- Queue list view (filtered by tier, ordered by priority per `05-approval-queue-design.md` §5.2)
- Tier 2 bundle view (source pane left, writes pane right; per `05-approval-queue-design.md` §6.2)
- Tier 3 single-item view (per `05-approval-queue-design.md` §6.3)
- Source rendering: PDF viewer with page jump, table image rendering, Excel grid view
- Edit-in-place for individual rows in a Tier 2 bundle
- Keyboard shortcuts: J/K (nav), A/R/E (accept/reject/edit), 1-2-3 (quality rating), `?` (rejection reason picker)
- Daily briefing dashboard showing queue depth, staleness, etc.

**NOT in scope.**
- Multi-user collaboration
- Mobile-optimised view
- Notification system (delivery channel TBD per architecture §19.4)

**Acceptance criteria.**
- [ ] Analyst can review a Tier 2 bundle and accept-all in <5 minutes
- [ ] Analyst can review a Tier 3 item and approve/reject in <10 minutes
- [ ] Source PDF page jumps to the cited region
- [ ] Excel cell view shows surrounding context
- [ ] Keyboard shortcuts work
- [ ] Daily briefing surfaces queue depth and staleness
- [ ] All UI interactions logged to `ops.workflow_runs` (as `triggered_by='analyst'` runs)

**Constraints / notes.**
- Streamlit is single-user-friendly but can struggle with complex layouts; use `st.columns` with widget state careful management
- For PDF rendering, embed `pdf.js` via custom component if Streamlit native is insufficient
- Authentication: VPS SSH boundary is sufficient (single user); UI binds to localhost behind a VPN/SSH tunnel

**Spec references.**
- `05-approval-queue-design.md` §6 (UI)

---

## 3. Slice Phase

The actual end-to-end build. This is what the system is for v1.

---

### [S-01] BSE filings poller

**Status:** Blocked (by F-02, F-03)
**Phase:** Slice
**Estimated complexity:** L
**Dependencies:** F-02, F-03
**Blocks:** S-02, S-03

**Goal.** Build the BSE filings poller: scheduled fetch, fingerprint-based dedup, raw storage, registration in `filings.documents`.

**Scope.**
- `ingestion/filings/poller.py` — APScheduler-driven poll for the coverage universe
- BSE corporate announcements endpoint (research and pin at build time)
- For each new filing: download PDF, store under `/data/raw/bse/<company>/<yyyy>/<mm>/<dd>/`, fingerprint, insert into `filings.documents`
- Idempotency: skip if `(source, source_id, content_hash)` already present
- Polling cadence: hourly during BSE hours (9am–4pm IST), 4-hourly off-hours
- Failure alerting via `ops.alerts`
- Polite scraping: 1 req/sec, exponential backoff on errors
- Telemetry: `ops.workflow_runs` row per poll cycle

**NOT in scope.**
- PDF parsing (S-02)
- Classification (S-03)
- Transcript handling (post-v1)

**Acceptance criteria.**
- [ ] Poll cycle for the 8-name universe completes in <5 minutes during BSE hours
- [ ] New filings appear in `filings.documents` within 60 seconds of detection
- [ ] Re-run is a no-op (no duplicate rows)
- [ ] Endpoint failures alert without crashing the poller
- [ ] Filings stored on disk with deterministic paths

**Constraints / notes.**
- BSE endpoints have changed historically; build modular fetcher that can be swapped
- Save raw HTML/JSON of the index as well as the PDF (helps debug parsing changes)
- `ingestion_filings_role` connection only

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §10.1
- `04-data-model.md` §5.1
- ADR-014

---

### [S-02] Deterministic PDF extraction

**Status:** Blocked (by S-01)
**Phase:** Slice
**Estimated complexity:** L
**Dependencies:** S-01
**Blocks:** S-03, S-05

**Goal.** Build the deterministic extraction layer: pdfplumber for text, camelot for tables, with confidence scoring and bounding-box capture.

**Scope.**
- `extraction/pdf/text.py` — pdfplumber wrapper, returns `parsed_text` with page boundaries
- `extraction/tables/camelot.py` — camelot wrapper, returns structured tables with bounding boxes
- `extraction/pipeline.py` — listener that detects `filings.documents.extraction_status='pending'`, runs extraction, populates `parsed_text`, `parsed_tables`, updates `extraction_status`, writes `filings.parsed_versions`
- Bounding boxes stored in `coverage.source_provenance.bounding_box` for any extracted facts (those facts queued in S-03)
- Confidence scoring: heuristic based on table structure quality (cell merge ratio, missing values, etc.)
- Failure handling: `extraction_status='extraction_failed'`, alert raised, original PDF retained for manual review

**NOT in scope.**
- LLM-based extraction (deliberately not — per ADR-012)
- OCR for scanned PDFs (post-v1 if needed)
- Slide-deck-specific extraction (post-v1)

**Acceptance criteria.**
- [ ] Extraction runs within 30 seconds for a typical results filing PDF
- [ ] Tables extracted with 80%+ structural integrity on a hand-curated test set of 20 BSE filings
- [ ] Bounding boxes round-trip: given a (page, row, col), can render the cropped image
- [ ] Failed extractions alert and don't block the pipeline
- [ ] `parsed_versions` records every parse attempt

**Constraints / notes.**
- Use `extraction_role` connection
- Camelot has lattice and stream modes; pick lattice for ruled tables, stream for unstructured — let the parser choose based on heuristics
- Tune `pgvector` `lists` only after F-06 has data flowing

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §5.2 (deterministic extraction)
- ADR-012

---

### [S-03] `filings_classifier` agent

**Status:** Blocked (by S-02, F-04, F-05)
**Phase:** Slice
**Estimated complexity:** M
**Dependencies:** S-02, F-04, F-05
**Blocks:** S-04, S-05

**Goal.** Build the first agent: takes an extracted filing, classifies its type and materiality, maps extracted numbers to schema fields, queues structured writes.

**Scope.**
- `agents/filings_classifier/prompt.md` — system prompt; classification taxonomy aligned with `filings.documents.document_type` values
- `agents/filings_classifier/output.py` — Pydantic output schema
- `agents/filings_classifier/config.py` — Haiku model, max 10 tool calls, max 30K tokens
- `agents/filings_classifier/runner.py` — agent loop
- Reads: `parsed_text`, `parsed_tables`
- Writes: `filings.classifications` (Tier 1, auto-applies), proposes `coverage.financials` rows (Tier 2 bundle, awaits review)
- Source provenance for every proposed financial: page, table, row from camelot bounding box
- `[VERIFY]` flags surfaced for low-confidence extractions

**NOT in scope.**
- Thesis-impact analysis (deferred per ADR-009)
- Cross-filing reasoning

**Acceptance criteria.**
- [ ] Classifier processes a typical results filing in <60 seconds
- [ ] Classification accuracy ≥90% on a test set of 30 filings
- [ ] Extracted financial rows have full source provenance
- [ ] Queue items appear in the UI with bounding-box source rendering
- [ ] Workflow run logged with token cost

**Constraints / notes.**
- Use Haiku per ADR-016
- Hard limits enforced per ADR-027
- LLM does NOT generate numbers; it maps extracted values to metric names and periods

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §8.5
- `05-approval-queue-design.md` (queue interaction)

---

### [S-04] Excel adapter

**Status:** Blocked (by F-03, F-05)
**Phase:** Slice
**Estimated complexity:** M
**Dependencies:** F-03, F-05
**Blocks:** S-05, S-06

**Goal.** Build the read-only Excel adapter: scans `/data/excel/<company>/*.xlsx`, reads named ranges per a defined convention, proposes `coverage.financials` rows (Tier 2 bundle, type=`our_estimate`).

**Scope.**
- `modeling/excel_adapter/conventions.py` — defines the named-range convention all model files must follow
- `modeling/excel_adapter/reader.py` — openpyxl-based reader that extracts values from named ranges
- `modeling/excel_adapter/diff.py` — compares latest read to last persisted estimate for the same `(company, period, metric, scenario)`; only proposes writes for changed values
- `modeling/excel_adapter/runner.py` — invoked on-demand by the analyst (initially) or post-acceptance of a variance bundle (later)
- Source provenance: `source_type='excel_model'`, `cell_reference=<named_range>`, `document_path=<.xlsx path>`

**NOT in scope.**
- Writing back to Excel (out of scope per ADR-005)
- Generic Python projection (deferred to v2 per ADR-005)
- Multi-scenario sweeps (the adapter reads whatever scenarios exist in the workbook)

**Acceptance criteria.**
- [ ] One worked example: Laurus model has named ranges for FY26 revenue, EBITDA, PAT (base/bull/bear); adapter reads them and proposes diffs
- [ ] Named-range convention documented in `modeling/excel_adapter/conventions.py` and referenced from the model file's instructions sheet
- [ ] Re-run with no changes proposes nothing
- [ ] Re-run with changes proposes only the changed rows

**Constraints / notes.**
- Convention to be agreed during F-03 / S-04 design — recommended: `<metric>_<period>_<scenario>` (e.g., `revenue_FY26_base`, `ebitda_1QFY27_bull`)
- One workbook per company under `/data/excel/<company>/<filename>.xlsx`
- Adapter is read-only by design; never mutate workbooks

**Spec references.**
- ADR-005
- `01-vision-and-architecture-v1.1.md` §13

---

### [S-05] `variance_analysis` agent

**Status:** Blocked (by S-03, S-04, F-07)
**Phase:** Slice
**Estimated complexity:** L
**Dependencies:** S-03, S-04, F-07
**Blocks:** S-06 (depends on what variance produces)

**Goal.** Triggered post-earnings filing: compares reported actuals to our estimates and Visible Alpha consensus, attributes variance to drivers, drafts a variance note for review.

**Scope.**
- `agents/variance_analysis/prompt.md` — system prompt with synthesis ordering per ADR-015
- `agents/variance_analysis/output.py` — Pydantic schema: facts (extracted actuals), consensus, our prior, evidence delta, variant perception, [VERIFY] items
- `agents/variance_analysis/config.py` — Sonnet, max 15 tool calls, max 100K tokens
- Reads: filings, `coverage.financials` (actuals + our estimates + consensus), `coverage.drivers`, active thesis, related transcript turns (if available — out of scope for v1)
- Writes: variance note as a markdown draft + Tier 3 queue item with the structured variance summary
- Trigger: when a filing is classified as `document_type='results'`, automatically dispatch this workflow

**NOT in scope.**
- Auto-updating drivers based on variance (high-stakes; analyst does this in subsequent thesis review)
- Multi-quarter trend analysis (post-v1)

**Acceptance criteria.**
- [ ] Triggered automatically after S-03 classifies a results filing
- [ ] Output follows ADR-015 ordering (facts → consensus → our prior → delta → variant perception)
- [ ] "No material variant perception found" is a valid output (rewarded, not flagged)
- [ ] Numbers traceable to filings extractions or Visible Alpha pulls
- [ ] Synthesised claims have `claim_provenance_id` set
- [ ] Tier 3 queue item created with full structured payload

**Constraints / notes.**
- Sonnet per ADR-016
- Hard limits per ADR-027
- Variant perception is found, not framed (ADR-015)

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §8.4, §8.5
- ADR-015

---

### [S-06] Eval harness — golden set + nightly run

**Status:** Blocked (by S-03, can build alongside S-05)
**Phase:** Slice
**Estimated complexity:** L
**Dependencies:** S-03
**Blocks:** S-07 (must exist before second synthesis agent ships per ADR-023)

**Goal.** Build the eval harness: 50–100 row golden set, nightly run, regression detection, blocking of deploys that regress.

**Scope.**
- See full design in `06-eval-harness-design.md`
- Golden set seeded from real S-03 outputs that were analyst-edited (the edited values become ground truth)
- Nightly cron runs every active eval against the current code
- Regression detection: pass-rate decreases trigger alerts; new failures trigger blocking
- `ops.eval_runs` populated; trends visualised in the UI dashboard
- CI integration: PR cannot merge if eval pass rate decreases

**NOT in scope.**
- Eval for variance_analysis (added in S-05's acceptance)
- Synthetic data generation (use real outputs)

**Acceptance criteria.**
- [ ] 50+ golden items active for `filings_classifier` and `variance_analysis`
- [ ] Nightly run produces a pass rate per eval type
- [ ] Regression alert triggers when pass rate drops >5pp
- [ ] CI integration blocks PRs that drop pass rate
- [ ] UI dashboard shows pass rate trend per workflow

**Spec references.**
- `06-eval-harness-design.md`
- ADR-023

---

### [S-07] `earnings_prep` agent

**Status:** Blocked (by S-05, S-06)
**Phase:** Slice
**Estimated complexity:** L
**Dependencies:** S-05, S-06 (eval harness MUST exist before this ships per ADR-023)
**Blocks:** —

**Goal.** On-demand workflow: triggered by analyst before an upcoming earnings event; produces a one-pager covering our estimates vs consensus, drivers, what-to-watch.

**Scope.**
- `agents/earnings_prep/prompt.md` — system prompt with synthesis ordering per ADR-015
- `agents/earnings_prep/output.py` — Pydantic schema for the one-pager
- `agents/earnings_prep/config.py` — Sonnet, max 15 tool calls, max 100K tokens
- Reads: company metadata, latest financials (actuals + our estimates + consensus), thesis (markdown via theses_meta), drivers, catalysts, recent filings, related transcript turns (post-v1)
- Output: markdown one-pager + Tier 3 queue item for the structured forecast summary
- Trigger: on-demand from UI ("run earnings prep for Laurus 4QFY26")

**Acceptance criteria.**
- [ ] Cycle time from trigger to draft <3 minutes
- [ ] One-pager follows ADR-015 ordering
- [ ] Numbers traceable; synthesised claims have claim_provenance
- [ ] Eval harness has at least 10 golden items for this workflow
- [ ] Output template renders cleanly in the UI

**Spec references.**
- `01-vision-and-architecture-v1.1.md` §8.5

---

### [S-08] `daily_briefing` agent

**Status:** Blocked (by F-08, S-05)
**Phase:** Slice
**Estimated complexity:** M
**Dependencies:** F-08, S-05
**Blocks:** —

**Goal.** Cron-scheduled at 7am IST: produces a digest of queue depth, staleness, open variances, thesis-contradictory signals from prior 24h.

**Scope.**
- `agents/daily_briefing/prompt.md` — system prompt
- `agents/daily_briefing/output.py` — Pydantic schema for the digest
- `agents/daily_briefing/config.py` — Sonnet (small context); tight token budget
- Reads: `ops.review_queue` (depth/staleness), `ops.workflow_runs` (yesterday's runs), `coverage.theses_meta` (active theses), recent filings flagged material
- Output: digest delivered via channel TBD (per architecture §19.4)
- Cron triggers via APScheduler at 7am IST

**Acceptance criteria.**
- [ ] Runs daily at 7am IST without manual trigger
- [ ] Digest fits on one screen (≤500 words equivalent)
- [ ] Includes queue depth, top 3 stale items, top 3 thesis-contradictory signals
- [ ] Output rendered in UI dashboard regardless of delivery-channel decision
- [ ] Cost per run <$0.05

**Spec references.**
- ADR-020
- `01-vision-and-architecture-v1.1.md` §8.5

---

### [S-09] Visible Alpha integration

**Status:** Blocked (by F-02, integration mechanics decision needed)
**Phase:** Slice
**Estimated complexity:** M
**Dependencies:** F-02, decision on integration mechanics (open question per architecture §19.1)
**Blocks:** S-05 partial functionality (variance without consensus is half-blind)

**Goal.** Pull consensus from Visible Alpha and persist to `coverage.consensus_pulls` and `coverage.financials` (`type='consensus'`).

**Scope.**
- `ingestion/consensus/visible_alpha.py` — VA client; fetches consensus for the coverage universe
- Cadence: TBD (likely daily during earnings season, weekly otherwise)
- Each pull stored in `coverage.consensus_pulls` (raw payload) + extracted into `coverage.financials` with `type='consensus'`
- When a new pull supersedes prior consensus, prior rows get `type='prior_consensus'`
- Source provenance points at the pull row

**NOT in scope.**
- Real-time consensus (post-v1 if needed)
- Multi-source consensus (Visible Alpha is the single source per ADR-006)

**Acceptance criteria.**
- [ ] Daily pull during earnings season succeeds
- [ ] Consensus rows match VA UI on spot-check
- [ ] Prior consensus retained
- [ ] Variance analysis (S-05) can join to current consensus via a single tool call

**Constraints / notes.**
- Integration mechanics still open: API access, refresh frequency, license terms for storage. Resolve before this item starts.

**Spec references.**
- ADR-006

---

## 4. Operate Phase

The phase where the v1 slice runs through one earnings season. Items here are observation, friction-tracking, and small fixes.

---

### [O-01] Operate one earnings season

**Status:** Blocked (by all S-* items)
**Phase:** Operate
**Estimated complexity:** Continuous over ~6–8 weeks
**Dependencies:** Slice complete

**Goal.** Use the v1 slice through one full earnings season (8 names × 1 quarter = ~8–12 events). Track everything.

**Scope.**
- Operating discipline: every queue item reviewed substantively
- Daily briefing reviewed
- Friction tracked in a `friction_log.md` document (free-form, dated entries)
- Monthly review entries in `02-decision-log.md` covering: cost, attention, hours saved, hours redirected, eval pass rate trends, queue performance
- Mid-season retro: 4 weeks in, audit what's working and what isn't
- End-of-season retro: full audit informing v2 backlog

**Acceptance criteria.**
- [ ] All 8 covered names had earnings prep runs
- [ ] All earnings filings had variance analysis runs
- [ ] Daily briefing ran every morning
- [ ] Friction log has at least 20 entries
- [ ] Monthly review entries in decision log
- [ ] End-of-season retro produces v2 backlog

**Constraints / notes.**
- This is the gate before any Expand-phase work begins
- If observed friction reveals the slice itself was misshaped, address with a small-scope fix; do not expand surface area until the fix is complete

---

## 5. Expand Phase (Post-Slice)

Items here are intentionally sparse — they are placeholders only. Real Expand items will be defined from observed friction during Operate.

---

### [E-PLACEHOLDER-1] Valuepickr ingestion

**Status:** Deferred (per ADR-009, ADR-028)
**Phase:** Expand
**Estimated complexity:** L (estimate only)
**Dependencies:** O-01 complete

**Goal.** Add Valuepickr ingestion if Operate-phase observation shows it provides signal not captured elsewhere.

(Detailed scope to be drafted post-Operate.)

---

### [E-PLACEHOLDER-2] News ingestion

**Status:** Deferred (per ADR-009, ADR-028)
**Phase:** Expand
**Estimated complexity:** L (estimate only)
**Dependencies:** O-01 complete

(Detailed scope to be drafted post-Operate.)

---

### [E-PLACEHOLDER-3] Telegram ingestion

**Status:** Deferred (per ADR-009, ADR-028)
**Phase:** Expand
**Estimated complexity:** M (estimate only)
**Dependencies:** O-01 complete

(Detailed scope to be drafted post-Operate.)

---

### [E-PLACEHOLDER-4] `sector_preview`, `client_meeting_prep`, `thesis_review` agents

**Status:** Deferred (per ADR-009)
**Phase:** Expand
**Estimated complexity:** L each (estimate only)
**Dependencies:** O-01 complete

(Detailed scope to be drafted post-Operate.)

---

## 6. Cross-Cutting Concerns

These are recurring tasks that don't fit a single phase:

- **Backup runbook** — write `runbooks/postgres-restore.md` before first deploy
- **Cost monitor** — daily cron checking `ops.workflow_runs.cost_usd` aggregate; alert on >2× rolling average
- **Schema documentation drift check** — monthly: ensure `04-data-model.md` matches live schema
- **Disk fill monitor** — daily cron checking `/data/raw/` and Postgres data dir; alert at 70% full
- **Quarterly Postgres restore drill** — calendar event

---

## 7. Build Order Summary

The minimum sequence to a running v1 slice:

1. F-01 → F-02 → F-03 → F-04 → F-05 → F-08
2. F-06 → F-07 (can parallel with F-04/F-05 once F-03 is done)
3. S-01 → S-02 → S-03
4. S-04 (parallel with S-03)
5. S-09 (parallel with S-04, when integration mechanics resolved)
6. S-05 (depends on S-03, S-04, S-09)
7. S-06 (parallel with S-05)
8. S-07 (depends on S-05, S-06)
9. S-08 (parallel with S-07)
10. O-01 — operate

Estimated calendar time at sustainable pace: 8–12 weeks of build, then the Operate phase.

---

## 8. Open Backlog Items (Awaiting Decisions)

Items that cannot be specified until an open question resolves:

- **Visible Alpha integration mechanics** → blocks S-09 detailed scope
- **Daily briefing delivery channel** → minor; blocks final S-08 acceptance
- **Cohance, Sai Life, Anthem BSE codes** → blocks DB seed
- **Off-VPS backup target** → blocks backup runbook
- **Excel named-range convention finalisation** → blocks S-04 detailed scope

These are tracked in `01-vision-and-architecture-v1.1.md` §19.

---

## 9. Completed Items

(Empty in initial seeding. Populated as items move to Done.)

---

## 10. Deferred Items

(Empty in initial seeding. Populated when items are explicitly deferred.)

---

## 11. Revision History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | 2026-05-04 | Mohit Agarwal | Initial seeding with Foundation + Slice phases fully populated; Operate and Expand placeholders only |
