# AgentOS — Vision & Architecture

## 0. Document Control

| Field | Value |
| --- | --- |
| Document ID | 01 |
| Title | Vision & Architecture |
| Version | 1.1 |
| Status | Draft for review |
| Owner | Mohit Agarwal |
| Audience | Mohit, OpenClaw, Codex, future-Mohit |
| Repo location | `docs/01-vision-and-architecture.md` |
| Supersedes | v1.0 |
| Related docs | `02-decision-log.md`, `03-backlog.md`, `04-data-model.md`, `05-approval-queue-design.md`, `06-eval-harness-design.md`, `module-charters/` (lazy), `runbooks/` (lazy), `prompt-library.md` (lazy) |
| Major changes from v1.0 | Stripped four-plane formalism; cut agents to v1 set of four; added daily briefing workflow; deferred modeling engine to v2 with Excel-as-source-of-truth for v1; locked Visible Alpha as consensus source; added three-layer provenance; added Indian-conventions richness (corporate actions, accounting policies, consolidation basis); demoted OpenClaw from "kernel" to "orchestrator"; removed Codex-as-Builder role framing; deferred Valuepickr/Telegram/news to post-slice; added attention budget; reordered variant-perception in synthesis sequence; committed to vertical-slice-first build philosophy |

---

## 1. Purpose & Use of This Document

### 1.1 What this document is

The master document for AgentOS. Defines what the system is, why it exists, what shape it takes, and the principles that govern downstream decisions. Read first by any agent, tool, or future-self acquiring context.

### 1.2 Audience

- **Mohit** — when remembering why a decision was made, or onboarding self after a long break
- **OpenClaw** — when retrieving project context for orchestration decisions
- **Codex** — at the start of every implementation session, to ground its work in the right framing
- **Future-Mohit** — six months from now, when immediate context has faded

### 1.3 Scope

Covers vision, scope, success criteria, principles, architecture, modules, agents, data, workflows, build philosophy, technology stack, cost, attention budget, risks, coverage universe, glossary.

Does NOT cover detailed schemas (`04-data-model.md`), approval queue design (`05-approval-queue-design.md`), eval harness design (`06-eval-harness-design.md`), per-module specifications (`module-charters/<name>.md`), build sequence detail (`03-backlog.md`), decision history (`02-decision-log.md`), operational procedures (`runbooks/<name>.md`), or agent prompts (`prompt-library.md`).

### 1.4 How to read this document

End-to-end on first read. Reference specific sections for downstream decisions. Update only when fundamental assumptions change; updates require a corresponding entry in the decision log.

---

## 2. Executive Summary

AgentOS is a personal research operating system that automates the high-volume, low-judgment portions of an institutional sell-side analyst's workflow — leaving the analyst to focus on variant perception, channel work, client conversations, and investment calls.

It runs on a single VPS, uses a single Postgres database with multiple schemas and role-separated write access, and is composed of modular Python services in a monorepo. OpenClaw orchestrates workflows. Codex (used directly by the analyst) maintains and extends the codebase. Workflow-specific Claude API agents handle synthesis. The analyst architects, approves all structured data writes via a tiered review queue, and edits final outputs.

The v1 build is a single end-to-end vertical slice — BSE filing → deterministic numeric extraction → variance against an Excel model → tiered approval queue → analyst review with structured rejection feedback → accepted output flows to coverage tables. The slice runs through one full earnings season before any expansion. Everything else (additional ingestion sources, additional agents, the modeling engine) is deferred until the slice has demonstrated real friction patterns.

The design optimises for solo operation, low cost (~$100–180/month all-in), explicit human approval on structured writes, deterministic extraction for numbers (LLMs map; parsers extract), and a tight feedback loop from analyst edits back into prompt and system quality.

---

## 3. Background & Problem Statement

### 3.1 Current state of analyst work

The work of a senior pharma sell-side analyst decomposes into four buckets:

1. **Reading** — filings, transcripts, news, broker reports, forum posts, social. 4–6 hours/day at peak.
2. **Modeling** — maintaining detailed company models in Excel, updating estimates, running scenarios. 6–10 hours per company per quarter.
3. **Synthesis** — writing notes, sector views, client materials. Variable; often weekend work.
4. **Conversations** — client calls, management meetings, channel checks, internal team discussions. The actual point of the job.

Buckets (1) and (2) consume the majority of working hours but produce the minority of differentiated value. Buckets (3) and (4) are where the analyst competes. Time stolen by (1) and (2) is opportunity cost on (3) and (4).

### 3.2 Specific pain points

- New BSE filings discovered hours or days late because monitoring is manual
- Earnings prep starts from a blank page each quarter despite the model being similar
- Variance analysis post-results is repetitive and mechanical
- Forum and news scanning is unbounded and hard to delegate
- Each new client meeting requires fresh research even when the underlying view hasn't changed
- The analyst's own reasoning lives in Word docs and Excel cells, not queryable, not versioned
- Cross-company analysis (e.g., "which covered names have margin trajectory similar to Cohance pre-acquisition") requires opening 8 Excel files

### 3.3 Why now

LLMs are good enough to do classification and synthesis reliably with proper guardrails. Tooling (Claude API, Codex, OpenClaw, pgvector, Streamlit) makes this a one-person project. Cost has collapsed to the low hundreds of dollars per month for a single user.

### 3.4 The 80/20 framing — load-bearing

This is the single most important framing in the entire project. Misunderstanding it leads to bad design choices.

**AgentOS does not replace the analyst. It eliminates the work that crowds out the analyst's actual job.**

The goal is to recover the 15–25 hours per week currently spent on ingestion, synthesis, and mechanical model updates so that time can be spent on:
- Variant perception (genuinely original views the street doesn't hold)
- Channel work (talking to industry contacts, distributors, doctors, ex-employees)
- Client conversations (the actual product the buyside pays for)
- Judgment calls on theses (when to flip, when to hold, when to escalate)
- Investment in proprietary research (multi-quarter projects no one else is doing)

Two failure modes from getting this framing wrong:

1. **Over-automation of judgment.** The system attempts to make calls. It will be wrong sometimes. Being wrong on a client call is a career problem, not a UX problem. The system must never produce an output that bypasses human review on anything client-facing or thesis-affecting.
2. **Atrophy of the analyst.** Over time, the human stops developing the analytical muscle because the system handles it. Within a year the human in the loop has degraded enough to be useless as a check, and the system's hallucinations propagate unchallenged.

To prevent atrophy, the analyst's review must be **substantive** — genuinely engaging with the content — not perfunctory. The approval queue's tiering (§7) is designed to make substantive review tractable; the review-time-per-item targets are described there.

This framing dictates downstream decisions. Whenever a tradeoff arises between "automate more" and "human approves more", default to **human approves more** on anything client-facing or structurally sensitive.

---

## 4. Vision

### 4.1 What AgentOS IS

A modular operating system for one analyst, deployed on a single VPS, that:
- Continuously ingests information from defined sources for a defined coverage universe
- Maintains a structured knowledge base of company financials, estimates, reasoning, theses, drivers, and catalysts
- Runs scheduled monitoring workflows (filings, news scans, thesis health checks)
- Runs on-demand deliverable workflows (earnings prep, variance analysis, sector previews, client meetings, thesis reviews)
- Reads Excel models as source of truth for projections and writes assumption *proposals* to the approval queue when source events suggest the model needs an update
- Produces drafts that the analyst reviews, refines, and ships
- Maintains source / derivation / claim provenance on every data point and every claim

### 4.2 What AgentOS IS NOT

- Not a portfolio management or trading system
- Not a recommendation engine that issues calls autonomously
- Not a public product or external-facing tool
- Not a team collaboration platform
- Not a replacement for primary research or channel work
- Not a system that touches client materials without human approval
- Not a Bloomberg replacement (it sits on top of market data, not under it)
- Not a quant platform (no factor models, backtesting, signal generation)
- Not a knowledge graph or wiki where the LLM writes structured entries autonomously
- Not a Python projection engine (Excel remains source of truth for v1; see §13)

### 4.3 Success criteria

**Quantitative:**
- Reading time on filings/news reduced by ≥70%, measured by weekly self-report
- Earnings prep cycle time reduced from ~6 hours per name to ≤45 minutes per name
- 100% of structured DB writes have source / derivation / claim provenance
- ≥85% of expected BSE filings ingested within 4 hours of posting
- Numerical extractions match deterministic-parser ground truth on golden set ≥95%
- Monthly all-in cost ≤ $200 USD
- Daily approval queue processing time ≤30 minutes outside earnings season; ≤90 minutes during earnings season

**Qualitative:**
- Within 3 months of go-live, demonstrably more time is being spent on differentiated work
- The analyst trusts the system enough to use it under deadline pressure
- The analyst does NOT trust the system enough to skip review on client-facing output
- Codex sessions are productive — clear specs, one-shot success rate ≥70%
- Six months in, returning to the project after a vacation feels manageable, not overwhelming

### 4.4 Anti-criteria

The system is failing if any of these become true:
- The analyst is spending more time managing the system than doing analytical work
- Client-facing outputs ship without explicit human review
- Schema or agent prompt drift has made the codebase opaque to its own author
- Cost is climbing without a corresponding increase in output volume or quality
- Codex sessions require multiple rounds because specs are unclear
- The approval queue is consistently rubber-stamped (>95% acceptance rate without correction)
- The analyst's own analytical instincts have measurably degraded vs. baseline

---

## 5. Guiding Principles

These principles are load-bearing. Whenever a design or implementation question is ambiguous, default to these. If a principle is being violated, it requires an explicit decision-log entry.

### 5.1 Vertical slice before platform

Build one end-to-end workflow that touches every layer (ingestion → extraction → DB → synthesis → queue → review → feedback) before adding additional sources, agents, or workflows. Earn each subsequent piece from observed friction in the slice, not from speculative architecture.

### 5.2 Deterministic extraction; LLMs map and synthesise

Numbers are extracted by deterministic parsers (pdfplumber, table extraction libraries, regex). LLMs are used to *map* extracted structures to schema fields and to synthesise narrative claims — never to generate the numbers themselves. A number in a deliverable can always be traced to a parser output, not an LLM completion.

### 5.3 Three-layer provenance

Every structured fact carries one of three provenance types:

- **Source provenance** — raw extraction. "This number came from page 3 of XYZ's 4QFY26 results filing, table 2, row 4."
- **Derivation provenance** — formula. "This number is `revenue × 0.18`, where revenue is row #1234 (FY26 actuals) and 0.18 is the assumption from row #5678 (assumption: gross margin %)."
- **Claim provenance** — evidence bundle for synthetic narrative. "This sentence is supported by: filing row #2345, transcript turn #6789, prior thesis version #3."

The data model treats each as a first-class concept. Never a single `source` column papering over the distinction.

### 5.4 Human approves all structured writes (tiered)

Every write to coverage tables (`financials`, `estimate_rationale`, `theses`, `drivers`, `catalysts`) passes through the approval queue. The queue is **tiered** — low-risk auto-applies with sample audit, mid-risk batch-approves by event, high-risk requires line-item approval. Tiers and rules defined in `05-approval-queue-design.md`.

### 5.5 Variant perception is a finding, not a frame

Synthesis output structure: facts → consensus view → our prior view → evidence delta → variant perception (if any). "No material variant perception found" is a valid and rewarded output. Asking the LLM to lead with variant perception encourages manufactured contrarianism.

### 5.6 [VERIFY] flag convention

Any data point or claim the agent cannot confirm from a primary source is surfaced inline with `[VERIFY]`. Never silently estimate. Never paper over uncertainty. Resolution of `[VERIFY]` flags is a primary purpose of analyst review.

### 5.7 Modular composition

Workflows are sequences of tool calls. Adding a new workflow means writing a new system prompt and selecting a tool subset. Tools do one thing and return structured output.

### 5.8 Contracts before code

Inter-module interfaces (DB schema, tool signatures, agent input/output shapes) are designed before implementation. Codex implements against contracts.

### 5.9 Documentation IS infrastructure (in moderation)

Three living docs (architecture, decision log, backlog) plus a data-model doc plus design docs for the two genuinely complex subsystems (approval queue, eval harness). Module charters and runbooks created when the module ships, not before. Don't pre-write process scaffolding for a one-person team.

### 5.10 Cost discipline

Token spend, infrastructure cost, and engineering time are all real budgets. Default to Haiku for classification, Sonnet for synthesis. Every workflow has token and tool-call budgets. Monthly cost reviewed in the decision log.

### 5.11 Attention discipline

Build hours, maintenance hours, and review hours are also budgets — usually the dominant ones. Tracked in §14. Any feature whose review burden cannot be sustained at 30 min/day baseline is rejected or redesigned.

### 5.12 Indian conventions throughout

- FY runs Apr–Mar; quarter format `1QFY26`–`4QFY26`; annual `FY26`
- Indian financials in ₹ crore; export values in USD million; market caps in ₹ crore
- Every `financials` row carries `consolidation_basis` (consolidated | standalone) and `accounting_policy_version` (IndAS revision tag)
- Corporate actions (splits, bonuses, demergers, buybacks) tracked in `coverage.corporate_actions` with effective date and adjustment factor
- Restated numbers carry a `supersedes` link to the prior row; original row retained for audit
- Quarterly vs half-yearly disclosure variance is explicit; H1/H2 placeholders allowed

### 5.13 Solo-user simplicity (with guardrails)

No multi-tenancy, no auth UI, no role-based access in the application. But: separate Postgres roles per writer (ingestion / orchestrator / web / approval-processor) with table-level GRANTs, so that wrong writes are impossible by default rather than impolite. Encrypted backups. Prompt-injection sanitisation on free-text fields ingested from external sources.

### 5.14 Local-first, cloud-light

VPS is the entire production environment. Self-hosted Postgres, vector store, scheduler, UI. External services only for LLM, embeddings, and Visible Alpha consensus.

### 5.15 Reversibility over speed

Schema changes are backwards-compatible by default; breaking changes require a decision-log entry with a rollback plan. Every Codex change is a small PR.

### 5.16 Idempotency on ingestion

Every ingested artefact has a deterministic fingerprint (`source_type`, `source_id`, `content_hash`). Re-ingestion of the same artefact produces no duplicate row. Re-runs of any workflow are safe.

### 5.17 Feedback loop is mandatory

Every workflow output that reaches the approval queue carries a structured rejection-reason taxonomy and a 1–3 quality rating field. Aggregate review monthly to identify prompt regressions and ingestion blind spots. Drift audits monthly, not biannually.

---

## 6. System Architecture

### 6.1 Topology

```
┌────────────────────────────────────────────────────────────────────┐
│                            VPS (single host)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │   OpenClaw orchestrator  |  APScheduler  |  Streamlit UI   │  │
│  └────────┬────────────────────┬───────────────────┬────────────┘  │
│           │                    │                   │               │
│  ┌────────▼─────────┐  ┌───────▼────────┐  ┌───────▼─────────┐    │
│  │  workflow agents │  │ ingestion jobs │  │   approval      │    │
│  │  (Claude API)    │  │ (cron-driven)  │  │   queue UI      │    │
│  └────────┬─────────┘  └───────┬────────┘  └───────┬─────────┘    │
│           │                    │                   │               │
│  ┌────────▼────────────────────▼───────────────────▼─────────┐    │
│  │         tools  (core/tools/ — read/write functions)        │    │
│  └────────┬────────────────────────────────────────┬──────────┘    │
│           │                                        │               │
│  ┌────────▼─────────┐                    ┌─────────▼──────────┐   │
│  │  Postgres        │                    │   Filesystem       │   │
│  │  schemas:        │                    │  /data/raw/        │   │
│  │  coverage        │                    │  (PDFs, HTML)      │   │
│  │  filings         │                    │  /data/excel/      │   │
│  │  ingestion_raw   │                    │  (model files)     │   │
│  │  ops             │                    └────────────────────┘   │
│  │  pgvector tables │                                              │
│  └──────────────────┘                                              │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
        ▲                                          ▲
        │                                          │
   ┌────┴─────┐                           ┌────────┴────────┐
   │  CODEX   │ (used directly by analyst │  Claude API,    │
   │          │  from terminal)           │  embeddings,    │
   └──────────┘                           │  BSE, Visible   │
                                          │  Alpha          │
                                          └─────────────────┘
```

### 6.2 Data flow — typical paths

**Ingestion (autonomous):**
```
External source → Ingestion job (cron) → Idempotency check (fingerprint)
              → Raw store (filesystem + ingestion_raw)
              → Deterministic extraction (parser)
              → LLM mapping to schema (Haiku)
              → Approval queue (tiered) → Coverage/filings tables
```

**Deliverable (on-demand):**
```
Analyst request → OpenClaw → Workflow agent → Tool calls →
Substrate reads → Synthesis (Sonnet) → Draft output →
Approval queue → Analyst review (with rejection taxonomy) →
Final output (file or DB write) → Feedback aggregated for prompt review
```

**Code change:**
```
Analyst writes spec → Codex (direct invocation from terminal) →
Code changes → Tests → PR → Analyst review → Merge → Deploy
```

### 6.3 Failure isolation

- **Postgres failure:** all workflows pause until restored. Daily backups, restore runbook, quarterly restore drill.
- **Single ingestion source failure:** that source pauses; others continue. Alert raised.
- **Tool failure:** calling agent catches; retry with backoff or surface failure in output.
- **Agent failure:** orchestrator logs partial state, alerts analyst, partial outputs in quarantine.
- **Orchestrator failure:** ingestion crons continue (independent processes); on-demand workflows unavailable until restart (auto via systemd).

---

## 7. Module Architecture

### 7.1 Monorepo structure

Single repository, modules separated by directory. Boundaries documented in `CONTRIBUTING.md` and enforced via diff review (no `import-linter` for v1; revisit when codebase complexity warrants).

```
agentos/
├── core/                     # shared contracts — types, tools, utils, exceptions
│   ├── types/                # Pydantic / SQLAlchemy models
│   ├── tools/                # tool functions exposed to agents
│   ├── utils/                # FY math, period conversion, fingerprinting, logging
│   └── exceptions.py
├── db/                       # alembic migrations, seed scripts, role grants
│   ├── migrations/
│   ├── seeds/
│   ├── roles/                # SQL for role-based GRANTs
│   └── README.md
├── ingestion/
│   └── filings/              # BSE filings monitor (v1 — only ingestion source)
├── extraction/               # deterministic parsers for filings/transcripts
│   ├── pdf/
│   ├── tables/
│   └── transcripts/
├── modeling/
│   └── excel_adapter/        # reads named ranges from Excel models (v1)
├── agents/                   # workflow agents (4 in v1)
│   ├── filings_classifier/
│   ├── earnings_prep/
│   ├── variance_analysis/
│   └── daily_briefing/
├── orchestrator/             # OpenClaw configs, scheduled jobs, deploy scripts
├── web/                      # Streamlit UI (approval queue is the primary surface)
├── evals/                    # golden set + harness
├── scripts/                  # ad-hoc admin scripts
├── tests/                    # mirrors module structure
├── docs/                     # all design and tracking documents
├── pyproject.toml
├── docker-compose.yml
├── CONTRIBUTING.md           # module boundary documentation
└── README.md
```

### 7.2 v1 module inventory

| Module | Type | Purpose | Status in v1 |
| --- | --- | --- | --- |
| `core` | Library | Shared contracts | Required |
| `db` | Migrations | Schema source of truth | Required |
| `ingestion/filings` | Service (cron) | BSE polling, fingerprinting | Required |
| `extraction` | Library | Deterministic parsers | Required |
| `modeling/excel_adapter` | Library | Read Excel named ranges | Required |
| `agents/filings_classifier` | Service | Classify + map extracted filings | Required |
| `agents/earnings_prep` | Service (on-demand) | Per-event prep workflow | Required |
| `agents/variance_analysis` | Service (event-triggered) | Post-results variance | Required |
| `agents/daily_briefing` | Service (cron, 7am IST) | Daily digest | Required |
| `orchestrator` | Service | OpenClaw, scheduler, queues | Required |
| `web` | Service | Streamlit UI (queue + dashboards) | Required |
| `evals` | Library | Golden set + nightly harness | Required |

### 7.3 Deferred modules (v2+)

Built only after the v1 slice has run through one earnings season:

- `ingestion/valuepickr` — Discourse forum scraping
- `ingestion/telegram` — Telegram intake
- `ingestion/news` — RSS + targeted scrapers
- `agents/sector_preview` — multi-company quarterly preview
- `agents/client_meeting_prep` — meeting brief generation
- `agents/thesis_review` — thesis health and revision
- `agents/filings_thesis_impact` — per-filing thesis impact check
- `modeling/engine` — Python projection engine (only if Excel adapter proves insufficient after 2 quarters)

### 7.4 Inter-module communication

Three patterns only:

1. **Imports from `core/`** — every module imports types, tools, and utils from `core/`.
2. **DB reads/writes** — restricted by Postgres role per writer (see §5.13).
3. **Tool calls (agent → tools)** — agents access the substrate only via `core/tools/`.

### 7.5 Deployment model

Single Docker image with multiple entry points. `docker-compose.yml` brings up Postgres + the application container with appropriate entry points. Long-running processes (orchestrator, web) under systemd; cron jobs invoked by APScheduler within the orchestrator process.

---

## 8. Agent Architecture

### 8.1 Roles

| Role | Implementation | Responsibility |
| --- | --- | --- |
| Orchestrator | OpenClaw | Receive requests, dispatch workflows, manage queues, log everything |
| Workflow agents | Claude API loops | Execute one workflow end-to-end |
| Coding tool | Codex (used directly from terminal) | Modify the codebase |
| Architect / Reviewer / Editor | Mohit | Design, approve, refine, drive |

Codex is a tool the analyst uses, not a role in the architecture. There is no orchestrator-dispatched Codex in v1. (Reconsider only if a clear, repeated maintenance pattern emerges.)

### 8.2 OpenClaw responsibilities

- Accept workflow requests (analyst-triggered via UI, scheduled, event-triggered)
- Resolve and invoke the right workflow agent
- Pass context and stream/log the run
- Route output (file, approval queue, alert)
- Maintain `ops.workflow_runs`
- Manage approval queue lifecycle
- Surface failures and partial states

OpenClaw does NOT synthesise content, modify code, or make analytical judgments.

### 8.3 Workflow agent template

Common shape, differences in system prompt, tool subset, and output contract:

| Component | Lives in |
| --- | --- |
| Persona prompt fragment | `agents/_shared/persona.md` |
| Workflow system prompt | `agents/<workflow>/prompt.md` |
| Tool subset | `agents/<workflow>/tools.py` |
| Output contract (Pydantic) | `agents/<workflow>/output.py` |
| Token / call budget | `agents/<workflow>/config.py` |

The first two agents are built **without** a shared loop abstraction. After both are working, common patterns are extracted into `agents/_shared/` only if they are genuinely shared. Standardising before variance is observed creates the wrong abstraction.

### 8.4 Synthesis output ordering

For all narrative-producing agents, the structured output follows this sequence:

1. Facts (deterministically extracted, with source provenance)
2. Consensus view (from Visible Alpha)
3. Our prior view (from coverage tables)
4. Evidence delta (what's new since prior view, with claim provenance)
5. Variant perception (if any; "no material variant perception found" is a valid and rewarded output)
6. Open `[VERIFY]` items

This ordering exists to prevent manufactured contrarianism. Agent prompts enforce it explicitly.

### 8.5 v1 workflow agent inventory

| Agent | Trigger | Output | LLM tier |
| --- | --- | --- | --- |
| `filings_classifier` | Per filing, ingestion-time | Filing type + materiality + structured map of extracted numbers | Haiku |
| `earnings_prep` | On-demand, per company per quarter | One-pager: estimates vs Visible Alpha consensus, drivers, what-to-watch | Sonnet |
| `variance_analysis` | Event-triggered (post-earnings filing) | Variance note: actuals vs ours vs consensus, attribution to drivers | Sonnet |
| `daily_briefing` | Cron, 7am IST | Digest: queue depth, stale items, open variances, thesis-contradictory signals from prior 24h | Sonnet (small context) |

### 8.6 Agent loop discipline

Multi-step agent loops with open-ended "Gap Check" steps are unstable (LLMs get stuck calling tools that don't return missing info). Constraints:

- Hard ceiling on tool calls per run (per-agent config; default 15)
- Hard ceiling on total tokens per run
- Explicit "no further useful tool calls" exit condition in the prompt
- State machine wrapping the loop (Plan → Retrieve → Synthesize → Output); no recursion

### 8.7 Codex working pattern

Direct invocation from terminal. For each session:

1. Open the relevant module charter (or this doc for cross-cutting work) and decision log
2. Write a focused spec (problem, scope, acceptance criteria, constraints, references)
3. Hand to Codex with explicit instruction to ask clarifying questions before coding
4. Review the diff before merge
5. Update the decision log if any architectural choice was made
6. Run the eval harness on any change touching agents, prompts, or extraction

Special case: any Codex change touching `core/types/`, output contracts, or tool signatures must run an end-to-end provenance integration test. The catastrophic-risk path is code change, not LLM inference.

### 8.8 Drift prevention

Monthly, not biannual:
- Aggregate rejection-reason taxonomy distributions
- Spot-check 5 randomly-sampled approved items per workflow per month
- If approval rate >95% with no corrections for two consecutive months on a workflow, tighten that workflow's tier
- If approval rate <70%, the workflow's prompt or extraction is broken — investigate

Recorded in `02-decision-log.md`.

### 8.9 Human role

The analyst is:
- **Architect** — structural decisions, design approvals, principle changes
- **Reviewer** — substantive review of all queued items
- **Operator** — triggers on-demand workflows, monitors scheduled ones
- **Editor** — refines deliverables before they ship
- **Driver** — assumptions, judgment calls, investment views

The analyst is NOT implementer (Codex), orchestrator (OpenClaw), synthesiser (workflow agents), or data entry clerk (ingestion).

---

## 9. Data Architecture (Summary; full detail in `04-data-model.md`)

### 9.1 Single Postgres, four schemas

| Schema | Purpose | Write role |
| --- | --- | --- |
| `coverage` | Companies, financials, estimates, theses (metadata), drivers, catalysts, derivations, corporate actions, accounting policies | `approval_processor_role` only |
| `filings` | BSE filings, transcripts (when available), parsed and raw | `ingestion_filings_role` + classifier agent role |
| `ingestion_raw` | Pre-classification dumps (post-v1 sources) | Respective ingestion roles |
| `ops` | Workflow runs, approval queue, evals, alerts, audit log | `orchestrator_role` |

### 9.2 Three-layer provenance tables

- `coverage.source_provenance` — links a fact row to source document + page/cell/table location + extracted_by + extracted_at
- `coverage.derivations` — formula, input row IDs, formula version hash; downstream rows are rebuildable from this
- `coverage.claim_provenance` — evidence bundles (filing IDs, transcript turn IDs, prior-thesis version IDs) supporting synthetic narrative claims

Detailed in `04-data-model.md`.

### 9.3 Theses

Hybrid model: prose lives as Markdown files in `coverage_theses/<company>/v<n>.md` in git (full version history, diffable, rich formatting). Metadata (active version pointer, dates, status, links to evidence) lives in `coverage.theses_meta`. Best of both: git history for the writing, DB for queryability.

### 9.4 pgvector

Same DB, separate tables for embeddings (`<schema>_embeddings`). Adequate at v1 corpus size (estimated <500K chunks at maturity). Migration path to Qdrant documented if hit.

### 9.5 Object storage

Raw PDFs and HTML on VPS filesystem under `/data/raw/<source>/<company>/<yyyy>/<mm>/<dd>/`. Excel models under `/data/excel/<company>/<filename>.xlsx`. Path stored in DB rows. Retention policy: raw artefacts kept indefinitely if referenced by a coverage row; orphaned raw artefacts pruned after 90 days. Backed up nightly off-VPS (encrypted).

### 9.6 Idempotency

Every ingested artefact has fingerprint `(source_type, source_id, content_hash)`. Unique constraint enforced. Re-ingestion is safe.

### 9.7 Backup and DR

- Daily encrypted Postgres dump to off-VPS storage, retained 30 days
- Weekly full backup retained 1 year
- Filesystem synced nightly to same off-VPS bucket (encrypted)
- Restore runbook in `runbooks/postgres-restore.md` (created when written)
- Quarterly restore test (calendar event)

### 9.8 Schema evolution

All schema changes via Alembic migrations. Backwards-compatible by default. Breaking changes require decision-log entry. No schema changes without corresponding update to `04-data-model.md`.

### 9.9 Blast-radius tooling

When a coverage row is corrected (post-approval), the derivation log is walked to identify all downstream rows that depend on it. Those rows are flagged for recompute via a `coverage.recompute_queue` table. Prevents silent inconsistency between primary data and derived estimates after an error.

---

## 10. Workflow Inventory

### 10.1 v1 workflows

| Workflow | Trigger | Frequency | Sync/Async | Outputs to | LLM |
| --- | --- | --- | --- | --- | --- |
| Filings ingestion | Cron | Hourly during BSE hours, 4-hourly off-hours | Async | `filings.*` | (none — parser) |
| Filings classification | Per-filing | Event | Async | `ops.review_queue` (mid-tier) | Haiku |
| Variance analysis | Event-triggered post-earnings | Per-event | Async | `ops.review_queue` (high-tier) | Sonnet |
| Earnings prep | On-demand | Per-event | Sync | Draft file + `ops.review_queue` (high-tier) | Sonnet |
| Daily briefing | Cron, 7am IST | Daily | Async | Email/Slack + UI dashboard | Sonnet (small) |
| Excel model read | On-demand or post-approval | Per-event | Sync | `coverage.financials` (via queue) | (none) |
| Eval harness | Cron, nightly | Daily | Async | `ops.evals` + alert on regression | (mocked) |

### 10.2 Deferred workflows

Built post-slice: `sector_preview`, `client_meeting_prep`, `thesis_review`, `thesis_impact`, news/forum/telegram classifiers, modeling refresh.

### 10.3 Workflow lifecycle

Every workflow run row in `ops.workflow_runs`:
- `id`, `workflow_name`, `triggered_by` (analyst | cron | event), `triggered_at`
- `status` (pending | running | succeeded | failed | partial)
- `input_params`, `output_summary`, `error_details`
- `tool_calls_count`, `tokens_used`, `cost_usd`
- `started_at`, `completed_at`
- `golden_set_run_id` (if part of nightly eval)

---

## 11. Build Philosophy

### 11.1 Document-driven build

No code without a spec. Every Codex session begins with one. Order: ideate → architect → spec → implement → review → merge → document outcomes.

### 11.2 Vertical slice first

The v1 build is the slice in §2. Sequence:

1. Schema (data model, migrations, role grants)
2. Approval queue UI (tiered, with rejection taxonomy)
3. BSE filings ingestion + idempotency
4. Deterministic extraction
5. `filings_classifier` agent
6. Excel adapter (read-only, named ranges)
7. `variance_analysis` agent
8. `earnings_prep` agent
9. `daily_briefing` agent
10. Eval harness + golden set seed
11. Operate through one earnings season
12. Review observed friction; plan v2 from data, not speculation

Detailed sequencing in `03-backlog.md`.

### 11.3 Test strategy

- **Unit tests** for `core/` types, utilities, fingerprinting, FY math — required
- **Integration tests** for ingestion modules against fixture documents — required
- **Eval harness** for agents: golden set of (input → expected structured output), nightly run, regressions blocked from deploy — required for any agent shipping to production
- **End-to-end provenance test** for any Codex PR touching types/contracts/tools — required
- **Manual smoke tests** post-deploy

### 11.4 Eval harness commitment

Built before the **second** synthesis agent ships (not the third). Without it, "zero hallucinations" and "≥95% extraction accuracy" are aspirational. Designed in `06-eval-harness-design.md`. Golden set seeded with 50–100 rows initially, grown organically from real rejected items.

### 11.5 Migration discipline

- Schema changes backwards-compatible by default
- Breaking changes require decision-log entry with rollback step
- All migrations reviewed before live application
- `db/migrations/` is the source of truth; live schema must always match latest migration

### 11.6 What "done" means

A feature is done when:
- Code merged
- Unit + integration tests pass
- Eval harness passes (if applicable)
- Module charter (or relevant doc) reflects the implementation
- Architectural choices recorded in decision log
- Smoke-tested end-to-end on the live VPS
- Backlog item closed

---

## 12. Technology Stack

| Component | Choice | Rationale |
| --- | --- | --- |
| LLM (synthesis) | Claude Sonnet | Best tool-use, long context, financial reasoning |
| LLM (classification) | Claude Haiku | Cost/quality balance for high-volume cheap classification |
| Embedding | Voyage AI | Best retrieval accuracy for financial/technical text |
| Structured DB | Postgres | Multi-process write concurrency, mature, runs on VPS |
| Vector store | pgvector | Same DB, no separate infra, adequate at scale |
| PDF extraction | pdfplumber + camelot | Deterministic; handles BSE filing formats well |
| Excel adapter | openpyxl | Reads named ranges; no Excel runtime dependency |
| Migrations | Alembic | Standard with SQLAlchemy |
| ORM / typing | SQLAlchemy + Pydantic | Type-safe; Codex understands |
| Scheduler | APScheduler | In-process, no broker, sufficient for this scale |
| Orchestrator | OpenClaw | Already chosen |
| Coding tool | Codex | Already chosen; direct invocation only in v1 |
| UI | Streamlit | Fast, single-user sweet spot |
| Deployment | Docker Compose | Simplest reproducible deployment |
| Backup | `pg_dump` + cron + encrypted off-VPS | Cheap, sufficient |
| LLM SDK | `anthropic` Python SDK | Direct; LangChain abstraction not needed |
| Consensus data | Visible Alpha | Locked decision; integration TBD |

---

## 13. Modeling Engine — Locked Decision

For v1: **Excel is the source of truth for projections.** No Python projection engine, no two-way sync, no per-company config DSL.

The `modeling/excel_adapter` module reads named ranges from per-company `.xlsx` files (one workbook per name, conventions documented in `04-data-model.md` §model-files). It writes:
- Read-only mirror of model outputs into `coverage.financials` (with `type=our_estimate`, source = excel + named range + cell)
- Assumption *proposals* into the approval queue when ingestion-driven events suggest a model assumption needs revisiting

The analyst edits assumptions in Excel as today. The system reads the new outputs after the analyst saves and approves the diff.

Re-evaluation point: after 2 quarters of operation across 3+ companies. If genuine repeated structure emerges that Excel can't represent cleanly, consider a one-way Python generator. **Two-way sync is permanently out of scope** unless a future decision explicitly reopens it.

This decision is recorded in `02-decision-log.md` and supersedes the §18.6 open question from v1.0.

---

## 14. Cost & Attention Model

### 14.1 Monetary cost

| Component | Estimated monthly cost (USD) | Notes |
| --- | --- | --- |
| VPS (4–8 vCPU, 16GB RAM, 200GB SSD) | $30–40 | Hetzner / DigitalOcean |
| Off-VPS encrypted backup | $2–5 | <50GB at maturity |
| Claude API (Sonnet, synthesis) | $20–40 | v1 has 4 agents; lower than v1.0 estimate |
| Claude API (Haiku, classification) | $5–10 | v1 has only filings classification; lower than v1.0 estimate |
| Embedding API | $1–3 | One-time embed for new docs only |
| Visible Alpha access | TBD | Existing license assumed; if not, factor in |
| Domain / DNS | $1–2 | Optional |
| **Total v1 baseline** | **$60–100** | Lower than v1.0 because surface area is smaller |
| **Total post-v2 (all sources, all agents)** | **$100–180** | Original estimate stands |

### 14.2 Attention budget

Tracked monthly in the decision log. Targets:

| Activity | Build phase target | Steady-state target |
| --- | --- | --- |
| Build hours (analyst + Codex sessions) | 8–12 hrs/week | <2 hrs/week |
| Maintenance hours (broken scrapers, schema fixes) | n/a | <2 hrs/week |
| Approval queue review | 30 min/day baseline | 30 min/day baseline; 90 min/day during earnings |
| Eval harness review | 1 hr/week | 1 hr/week |
| Strategic review (decision log, principles, drift audit) | 1 hr/month | 1 hr/month |

If steady-state crosses 8 hours/week of total system overhead for two consecutive months, the system is failing the 80/20 framing — pause feature work and simplify.

### 14.3 Hours-saved measurement

Track weekly (self-report; honest, not optimistic):
- Reading hours saved (filings, news once added, transcripts)
- Earnings prep hours saved per name per quarter
- Variance analysis hours saved per quarter
- Hours redirected to channel work / client conversations / proprietary research

The success criterion is not "hours saved" in isolation; it's "hours saved AND redirected to high-leverage work." Hours saved that get spent managing the system don't count.

### 14.4 Cost discipline mechanisms

- Per-workflow token and tool-call budgets enforced in code
- Daily cost monitor with alert on >2× rolling average
- Monthly cost review entry in decision log
- Quarterly cost-vs-output audit

---

## 15. Risk Register

### 15.1 Technical risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| BSE endpoint changes / rate-limiting | High over time | Medium | Modular scraper, fallback to direct HTML, alerting on extraction failure |
| Postgres failure | Low | High | Daily backups, restore runbook, quarterly drill |
| Claude API outage | Low–medium | Medium | Retry with backoff; surface failure; non-critical workflows queue |
| Costs spike from runaway agent loop | Medium | Medium | Hard token/call budgets per workflow; daily cost monitor |
| Schema drift between modules | Medium | High | Contracts in `core/`; CONTRIBUTING.md; review discipline |
| Codex generates wrong code that passes tests | Medium | Variable | Mandatory diff review; provenance integration test on type/contract changes |
| pgvector performance degrades at scale | Low at <500K chunks | Medium | Migration path to Qdrant documented |
| Excel adapter breaks on workbook structure changes | Medium | Medium | Named-range convention enforced; smoke test on each model file weekly |
| Visible Alpha integration unavailable / changes | Medium | High | Fallback to manual consensus entry; flag in UI |

### 15.2 Operational risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Analyst falls behind on approval queue | High during busy weeks | Medium | Tiered queue; daily briefing surfaces depth; auto-apply for low-tier |
| Analyst rubber-stamps approvals (drift) | Medium over time | High | Monthly drift audit; sample-check; tier auto-tightening rules |
| Documentation falls behind code | High | High | "Done" definition includes doc update |
| Single-VPS failure | Low | High | Backups; restore runbook; <2 hours to provision replacement |
| Disk fill on `/data/raw/` | Medium over time | Medium | Retention policy (§9.5); monthly disk-usage check |

### 15.3 Epistemic risks (most important category)

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Hallucinated number reaches client material | Low with deterministic extraction | Catastrophic | Numbers from parsers, not LLMs; provenance traceable; human review on all outputs; eval harness catches regressions |
| Wrong number — right source, wrong period/unit/consolidation | Medium | High | Period/unit/consolidation tags required on every numerical row; eval harness checks |
| Manufactured contrarianism in synthesis | Medium without controls | Medium | Variant perception is finding-not-frame (§5.5); "no variant perception" is rewarded output |
| Claim provenance gaps (synthetic narrative without evidence) | Medium | High | Three-layer provenance enforced; claim_provenance row required for every synthesised paragraph |
| Thesis ossifies (system reproduces yesterday's view) | Medium over time | High | Variant perception ordering; quarterly thesis review |
| Analyst skills atrophy | Medium over years | High | Substantive review (not rubber-stamp); periodic "manual mode" exercises |
| Over-reliance in client meetings | Medium | High | System never produces final client output without human edit |
| Prompt-injection via ingested free text | Low at v1 (BSE only); rises with forum/telegram | Medium | Sanitisation on free-text fields; LLM never executes instructions from ingested content |

### 15.4 Risk review cadence

Monthly during the cost/attention review. New risks added as encountered.

---

## 16. Coverage Universe

### 16.1 Current coverage

| Company | BSE Code | Coverage status | Sub-sector |
| --- | --- | --- | --- |
| Laurus Labs | 540222 | Active | CDMO + ARV API + FDF |
| Cohance Lifesciences | TBD | Active | CDMO + Specialty Chemicals |
| Divi's Laboratories | 532488 | Active | CDMO + API |
| Syngene International | 539268 | Active | CRO + CDMO |
| Piramal Pharma | 543635 | Active | CDMO + Hospital + Consumer |
| Sai Life Sciences | TBD | Active | CRO + CDMO |
| Anthem Biosciences | TBD | Active | CRDMO |
| Neuland Laboratories | 524558 | Active | CDMO + API |

(BSE codes to be confirmed and locked in `coverage.companies` during DB seed.)

### 16.2 Coverage status definitions

- **Active** — full coverage; all workflows run; thesis maintained
- **Passive** — monitored; ingestion runs; no on-demand workflows
- **Dropped** — historical only; no ingestion; data retained

### 16.3 Onboarding a new name

1. Add row to `coverage.companies` with status=passive
2. Wire to ingestion (BSE code, NSE code)
3. Backfill 8 quarters of filings
4. Backfill 8 quarters of financials manually or from Excel model
5. Initial thesis drafted by analyst (`coverage_theses/<company>/v1.md`)
6. Status flipped to active

---

## 17. Glossary

### 17.1 Domain terms

- **CDMO** — Contract Development and Manufacturing Organisation
- **CRDMO** — Contract Research, Development and Manufacturing Organisation
- **CRO** — Contract Research Organisation
- **API** (pharma) — Active Pharmaceutical Ingredient
- **ARV** — Antiretroviral
- **FDF** — Finished Dosage Form
- **DRHP** — Draft Red Herring Prospectus
- **EV/EBITDA** — Enterprise Value over EBITDA
- **FY26** — Indian financial year, April 2025 – March 2026
- **4QFY26** — Fourth quarter of FY26 (Jan–Mar 2026)
- **Variant perception** — A view that differs materially from consensus
- **Channel check** — Primary research with industry participants
- **₹ crore** — Indian unit of value, 10 million rupees
- **BSE / NSE** — Bombay Stock Exchange / National Stock Exchange
- **Visible Alpha** — Consensus data provider
- **`[VERIFY]`** — Inline marker for unconfirmed data points

### 17.2 System terms

- **AgentOS** — this system
- **Vertical slice** — the v1 end-to-end build (filing → extraction → variance → queue → review → feedback)
- **Source provenance** — raw extraction location for a fact
- **Derivation provenance** — formula + inputs for a derived number
- **Claim provenance** — evidence bundle for a synthetic narrative claim
- **Approval queue** — `ops.review_queue`, tiered structured-write approval
- **Workflow run** — one invocation of a workflow agent
- **Eval harness** — golden-set regression tests for agents and extractors
- **Excel adapter** — module that reads named ranges from Excel models
- **Daily briefing** — 7am IST digest workflow

---

## 18. Document Map

| Doc | Purpose | Status |
| --- | --- | --- |
| `01-vision-and-architecture.md` | This document | v1.1 draft |
| `02-decision-log.md` | Architectural decisions and rationale | To draft (seed entries from this doc) |
| `03-backlog.md` | Active work items, ranked, Codex-ready | To populate from §11.2 sequence |
| `04-data-model.md` | Full schema (coverage + filings + ops merged), three-layer provenance | To draft |
| `05-approval-queue-design.md` | Tiering, batching, peak load, review UI | To draft before any module charter |
| `06-eval-harness-design.md` | Golden set design, nightly run, regression tracking | To draft before second synthesis agent ships |
| `module-charters/<name>.md` | Per-module spec | Created when module ships |
| `runbooks/<name>.md` | Operational procedures | Created when first needed |
| `prompt-library.md` | All workflow agent system prompts | Created when first agent ships |

---

## 19. Open Questions

Resolved since v1.0:
- ~~Modeling engine scope~~ → Excel-as-source-of-truth; deferred Python engine to v2 contingent on observed need
- ~~Consensus data source~~ → Visible Alpha
- ~~v1 scope~~ → Vertical slice through one earnings season

Still open:
1. **Visible Alpha integration mechanics** — API access, refresh frequency, license terms for storing the data. Resolve before variance workflow ships.
2. **Cohance, Sai Life, Anthem BSE codes** — Lock during DB seed.
3. **Excel named-range convention** — Per-company workbook structure. Document in `04-data-model.md`.
4. **Daily briefing delivery channel** — Email, Slack, in-UI dashboard, or all three. Resolve when `daily_briefing` agent is built.
5. **Off-VPS backup target** — Backblaze B2, Wasabi, S3, or VPS provider's object store. Resolve before first deploy.
6. **Earnings-season slice operation window** — Which quarter is the v1 slice operating window? (Affects build deadline.)

---

## 20. Revision History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | TBD | Mohit Agarwal | Initial draft |
| 1.1 | TBD | Mohit Agarwal | Council critique incorporated: stripped four-plane formalism; cut to v1 agent set of four; deferred modeling engine to v2 with Excel-as-source-of-truth; locked Visible Alpha consensus; added three-layer provenance; added Indian-conventions richness; demoted OpenClaw to "orchestrator"; cut Codex-as-Builder; deferred Valuepickr/Telegram/news; added attention budget; reordered variant-perception in synthesis; added eval harness commitment; added daily briefing workflow; added idempotency / blast-radius / role-based DB security; vertical-slice-first build philosophy |
