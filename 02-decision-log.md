# AgentOS — Decision Log

## 0. Document Control

| Field | Value |
| --- | --- |
| Document ID | 02 |
| Title | Decision Log |
| Version | 1.0 (initial seeding) |
| Status | Living document — append only |
| Owner | Mohit Agarwal |
| Audience | Mohit, OpenClaw, Codex, future-Mohit |
| Repo location | `docs/02-decision-log.md` |
| Related docs | `01-vision-and-architecture.md`, all subsequent docs |

---

## 1. Purpose

This document records every architectural decision made for AgentOS. It exists because:

1. **Memory decays.** Six months from now, "why did we choose X over Y?" becomes archaeology without a written record.
2. **Codex needs context.** When Codex is asked to extend or modify the system, it needs to know what's settled and why, not just what's currently true.
3. **Reversibility requires history.** A decision can only be deliberately reversed if the original reasoning is captured.
4. **Drift detection.** When a principle is being violated in practice, the decision log is what makes the drift visible.

This is an append-only log. Entries are never edited after acceptance — they are *superseded* by new entries, with explicit cross-references.

---

## 2. Entry Format

Each entry follows this format:

```
### ADR-NNN: <short title>

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by ADR-NNN | Reversed by ADR-NNN
**Tags:** <comma-separated, e.g., schema, ingestion, modeling, scope>

**Context.** What was the situation that required a decision.

**Decision.** What we decided.

**Alternatives considered.** What else was on the table, briefly.

**Rationale.** Why this option won.

**Consequences.** What this means downstream — both good and bad.

**What would change our mind.** The conditions under which we'd reopen this.
```

Numbering is monotonic. Skip no numbers. Once accepted, never edited.

---

## 3. Seed Entries

The following entries capture decisions made during the design phase (v1.0 → v1.1 of the architecture document). They are dated as of the architecture v1.1 lock.

---

### ADR-001: Single VPS deployment, no cloud-managed services

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** infrastructure, deployment, scope

**Context.** The system needs to run somewhere. Options range from full cloud-managed (RDS, ECS, managed schedulers) to bare metal. The user has a VPS already provisioned.

**Decision.** AgentOS runs on a single VPS. Postgres self-hosted. Vector store self-hosted (pgvector). Scheduler in-process (APScheduler). UI self-hosted (Streamlit). Only LLM, embedding, and Visible Alpha APIs are external.

**Alternatives considered.** Managed Postgres (RDS / Supabase); Kubernetes; multi-region; serverless functions for ingestion.

**Rationale.** Solo user, eight covered names, modest data volume. Managed services add cost and lock-in for capabilities we don't use. A single VPS is simpler to reason about, cheaper, and sufficient.

**Consequences.** We own backup, restore, OS patching, and uptime. Tradeoff accepted.

**What would change our mind.** Sustained downtime impacting earnings season; data volume crossing what a single VPS can handle (>1TB, >10 concurrent heavy workflows); a second user being added.

---

### ADR-002: Single Postgres database, multiple schemas

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, infrastructure

**Context.** The system stores company data, filings, ingestion artefacts, and operational logs. These could live in separate databases or one database with multiple schemas.

**Decision.** One Postgres database. Four schemas: `coverage`, `filings`, `ingestion_raw`, `ops`. Cross-schema joins are allowed.

**Alternatives considered.** Separate databases per concern; SQLite (too restrictive for concurrent writes); DuckDB (analytical-first, less mature for transactional workload).

**Rationale.** Cross-schema joins are needed often (e.g., "filings on companies whose thesis hasn't been reviewed in 90 days"). One DB simplifies backup, restore, and migration. Schemas provide enough isolation for the actual concerns.

**Consequences.** A single DB outage takes everything down — accepted, given backup discipline. Role-based GRANTs (ADR-013) provide write-level isolation.

**What would change our mind.** A specific compliance or scaling reason that genuinely requires separate databases.

---

### ADR-003: Monorepo with directory-based modules

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** repo, build

**Context.** The codebase has clear logical modules (ingestion, extraction, agents, modeling, web, orchestrator). Should they live in one repo or many?

**Decision.** One repository. Modules separated by directory under `agentos/`. Module boundaries documented in `CONTRIBUTING.md`.

**Alternatives considered.** Polyrepo with shared `agentos-core` package; submodule-based monorepo; mixed.

**Rationale.** Single user, single VPS, no team coordination. Polyrepo's benefits (independent release, team isolation, blast-radius containment) don't apply. Polyrepo's costs (version-pinning, contract drift, multi-clone dev setup, scattered Codex sessions) are real. Atomic refactors across modules are routine in this system.

**Consequences.** Codex can grep the entire codebase. Schema changes are atomic PRs. Dev setup is one clone. Discipline must be enforced via convention rather than physical separation.

**What would change our mind.** A module becoming reusable as a standalone product; team growth (>1 active developer); a module needing a different release cadence than the rest.

---

### ADR-004: No `import-linter` for v1; boundaries documented in `CONTRIBUTING.md`

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** repo, build

**Context.** Module boundaries need to be enforced somehow. The original plan was `import-linter` with declarative rules.

**Decision.** No automated boundary enforcement in v1. Boundaries documented in `CONTRIBUTING.md`. Codex follows the documentation. Diff review catches violations.

**Alternatives considered.** `import-linter` from day one; custom AST checks; nothing at all.

**Rationale.** For a one-person + Codex codebase, lint-enforced boundaries are premature. Diff review catches violations more reliably and without false positives. The configuration overhead of `import-linter` exceeds its benefit at this scale.

**Consequences.** Some risk of accidental coupling; mitigated by review.

**What would change our mind.** Codex repeatedly creating cross-module dependencies that pass review unnoticed; codebase complexity reaching a point where review can't catch boundary violations reliably.

---

### ADR-005: Excel as source of truth for projections in v1

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** modeling, scope

**Context.** The original v1.0 plan included a generic Python `modeling/engine` that would replace Excel models. Five frontier models reviewed this and unanimously flagged it as the highest-risk over-commitment.

**Decision.** For v1, Excel remains the source of truth for projections. The `modeling/excel_adapter` module reads named ranges from per-company `.xlsx` files and writes assumption *proposals* to the approval queue when ingestion-driven events suggest a model assumption needs revisiting. No Python projection engine. No two-way sync. No per-company config DSL.

**Alternatives considered.** Build a generic Python projection engine in v1 (original plan); drop Excel entirely (Gemini's position); one-way Python generator with Excel input (Opus's position); hybrid (selected).

**Rationale.** Generic modeling engines reliably mutate into pseudo-DSLs full of exceptions and overrides. Excel models already exist, are battle-tested, and the analyst's mental model is built around them. Reading Excel preserves the analyst's existing workflow while enabling the system to participate. The cost of building a Python engine in v1 is high; the marginal benefit is unclear until we have observed friction.

**Consequences.** Excel becomes a critical dependency. The named-range convention must be enforced. If a workbook breaks structurally, the adapter breaks. The system cannot project independently — every projection comes from a workbook the analyst maintains.

**What would change our mind.** After two quarters across three or more companies, if genuine repeated structure emerges that Excel cannot represent cleanly, consider a one-way Python generator. **Two-way sync is permanently out of scope unless this ADR is explicitly reversed.**

**Supersedes:** v1.0 §18.6 (Open Question on auto-modeling output format).

---

### ADR-006: Visible Alpha as consensus data source

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** data, integration

**Context.** Variance analysis requires consensus estimates. Options include Bloomberg, Visible Alpha, manual entry from broker notes, or no consensus.

**Decision.** Visible Alpha is the single consensus data source.

**Alternatives considered.** Bloomberg (more comprehensive but more expensive and harder to integrate programmatically); manual entry (unsustainable at the cadence required); no consensus (variance workflow becomes half-blind).

**Rationale.** Visible Alpha is the analyst's existing tool. License is in place. Consensus is a deliverable input, not an analytical output — not a place to add an integration burden.

**Consequences.** Variance workflow depends on Visible Alpha availability. Integration mechanics (API, refresh frequency, license terms for storage) are still open (§19.1 of architecture doc).

**What would change our mind.** Visible Alpha becoming unavailable or unaffordable; a second source providing materially better coverage.

---

### ADR-007: No Quartr, no third-party transcript provider

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** data, integration, scope

**Context.** The original brainstorming considered Quartr (transcript provider) as a data source.

**Decision.** No Quartr integration. Transcripts come from BSE filings (where available) or are out of scope for v1.

**Alternatives considered.** Quartr API integration; building a Quartr-equivalent scraper.

**Rationale.** No API access available. Self-built transcript handling is in scope as a deferred capability — "the user is building something like Quartr but better" — but not for v1.

**Consequences.** v1 has no transcripts. Variance analysis works from filings only in v1. This is a real coverage gap; mitigated by analyst's existing access to Visible Alpha which surfaces summary commentary.

**What would change our mind.** A reliable, low-cost transcript pipeline being available; the user's own transcript tool maturing to production.

---

### ADR-008: No Twitter ingestion in v1 or near-term

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** ingestion, scope

**Context.** Twitter is a potential signal source. Three options: official API ($100/month Basic, $5K/month Pro), third-party scraper (Apify, ~$30–50/month), or skip.

**Decision.** Skip Twitter for v1 and the foreseeable near-term. Revisit only after three months of operation if news + Valuepickr coverage proves insufficient.

**Alternatives considered.** Official API at Basic tier; third-party scraping; community-contributed scrapers (Twikit, ToS-violating).

**Rationale.** Most actionable FinTwit signal flows into Valuepickr threads or financial press within hours. Twitter cost-per-signal is poor compared to the alternatives. Adding a flaky scraper to v1 increases maintenance burden without clear marginal value.

**Consequences.** A class of fast-moving sentiment signals is not captured.

**What would change our mind.** Sustained evidence that material signals are reaching Twitter and not other monitored sources.

---

### ADR-009: Vertical slice before platform — v1 scope is one end-to-end workflow

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** scope, build-philosophy

**Context.** The model council's strongest unanimous recommendation was to ship one end-to-end vertical slice before building the broader platform. The original v1.0 plan had nine agents, four ingestion sources, and a modeling engine — platform-scoped before any single workflow had been validated.

**Decision.** v1 is a single vertical slice: **BSE filing → deterministic numeric extraction → variance against Excel model → tiered approval queue → analyst review with structured rejection feedback → accepted output flows to coverage tables.** The slice runs through one full earnings season before any expansion. Valuepickr, Telegram, news, sector preview, client meeting prep, thesis review, and the modeling engine are all deferred until post-slice.

**Alternatives considered.** Build the broader v1 plan (original); build only filings classification (too narrow); build slice + Valuepickr (still too broad).

**Rationale.** Speculative architecture is the dominant failure mode of solo builds. Earning each subsequent piece from observed friction in a working slice is the antidote. One earnings season is the minimum operating window to see the system stressed under real conditions.

**Consequences.** v1 has narrower coverage (only filings, only four agents) but real depth on the slice. v2 planning is data-driven, not speculative. The build phase is shorter (8–10 weeks vs. several months for the original plan).

**What would change our mind.** Slice operation revealing that the slice itself was the wrong shape — e.g., that variance analysis requires news context to be useful. Unlikely but possible.

---

### ADR-010: Tiered approval queue, not flat

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** ux, safety

**Context.** The original v1.0 plan had a single approval queue for all structured writes. The model council unanimously flagged this as a fantasy — "10–20 minutes/day" is impossible during earnings season at hundreds of items/day.

**Decision.** The approval queue is tiered:
- **Auto-apply** (low-risk, high-frequency): writes happen, sample-audited later.
- **Batch-approve by event** (mid-risk): grouped by source event (e.g., one filing → many extracted rows reviewed together).
- **Line-item** (high-risk, low-frequency): one-by-one approval required.

Tier rules and peak-load behaviour are designed in `05-approval-queue-design.md`.

**Alternatives considered.** Flat queue (original); fully autonomous (rejected on safety); fully line-item (rejected on operability).

**Rationale.** Different writes carry different risk. Treating all writes identically forces the analyst to either rubber-stamp during peak load (defeating the safety guarantee) or fall behind (defeating the operability guarantee). Tiering matches review effort to actual risk.

**Consequences.** Tier classification logic must be designed and maintained. Sample auditing of auto-applied writes becomes a permanent operational practice. UI complexity increases.

**What would change our mind.** Tier classifications proving systematically wrong (auto-applied items frequently containing errors, or line-item items being trivial). In which case rebalance — but the tiered approach itself stays.

---

### ADR-011: Three-layer provenance — source, derivation, claim

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, provenance, safety

**Context.** The original v1.0 plan had a single `source` notion of provenance. The model council (GPT-5.4 in particular) flagged this as the deepest architectural gap: a number can be perfectly sourced and still be the wrong number for the claim being made.

**Decision.** Three layers of provenance, each first-class in the schema:

1. **Source provenance** — raw extraction location: document, page, table, cell.
2. **Derivation provenance** — formula + input row IDs + formula version hash.
3. **Claim provenance** — evidence bundles (filing IDs, transcript turn IDs, prior thesis versions) supporting synthetic narrative.

Designed in `04-data-model.md`.

**Alternatives considered.** Single `source` column (original); two layers (source + derivation); free-text provenance.

**Rationale.** These are genuinely different concepts and conflating them creates silent errors. A derived number whose source provenance points to its formula inputs is misleading. A synthesised narrative claim has no single source — it has a bundle of evidence. The schema must respect the difference.

**Consequences.** More tables, more joins, more discipline at write time. Worth it for correctness.

**What would change our mind.** Operating experience showing that one of the three layers is never used or never queried — would consider collapsing.

---

### ADR-012: Deterministic extraction; LLMs map and synthesise; LLMs do not generate numbers

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** safety, architecture

**Context.** The original framing of "zero numerical hallucinations" was aspirational without a mechanism. The council recommended deterministic extraction (pdfplumber, table libs, regex) as the right architecture.

**Decision.** Numbers are extracted by deterministic parsers. LLMs map extracted structures to schema fields and synthesise narrative — they never generate numbers. Every number in a deliverable traces to a parser output, not an LLM completion.

**Alternatives considered.** LLM-only extraction; LLM extraction with verification; deterministic with LLM fallback.

**Rationale.** LLMs hallucinate numbers in ways that are hard to detect. Deterministic parsers fail in obvious ways (parse error, no extraction) that can be flagged. The cost of building parsers is one-time per document type; the benefit is permanent.

**Consequences.** Parser maintenance becomes a real workstream. New filing formats may break extraction; mitigated by extraction confidence scoring and the `[VERIFY]` flag.

**What would change our mind.** A specific class of documents where deterministic extraction is genuinely impossible (e.g., handwritten scans). Even there, OCR + verification beats free-form LLM extraction.

---

### ADR-013: Separate Postgres roles per writer

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, security

**Context.** v1.0 §5.10 stated "no auth complexity, no role-based access." The council pushed back: writes should be impossible by default, not impolite. Single user does not mean single privilege.

**Decision.** Five Postgres roles, each with table-level GRANTs:

| Role | Write privilege |
| --- | --- |
| `ingestion_role` | INSERT on `filings.*`, `ingestion_raw.*` only |
| `extraction_role` | UPDATE on `filings.*` (parsed columns) only |
| `orchestrator_role` | INSERT/UPDATE on `ops.*` only |
| `approval_processor_role` | INSERT/UPDATE on `coverage.*` only — the only role that can write coverage data |
| `web_role` | SELECT only; INSERT on `ops.review_queue` for analyst-initiated rejections |

Application connections use the appropriate role per service.

**Alternatives considered.** Single superuser role (original); Row-Level Security; full RBAC.

**Rationale.** Cheap, mature, prevents an entire class of errors (e.g., a buggy ingestion script writing to `coverage.financials`). Single user → no UI auth needed; role separation is a write-isolation mechanism, not an auth mechanism.

**Consequences.** Connection-string management. Migrations need to grant correctly. Easy to get wrong; mitigated by `db/roles/` SQL files being source-controlled and re-run on deploy.

**What would change our mind.** Role separation creating more friction than it prevents. Unlikely.

---

### ADR-014: Idempotency via deterministic fingerprints on every ingested artefact

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** ingestion, schema, reliability

**Context.** The council flagged that most production errors aren't dramatic outages — they're duplicate filings, partial parses, replayed events, and races. Without idempotency, the provenance layer becomes silently inconsistent.

**Decision.** Every ingested artefact has fingerprint `(source_type, source_id, content_hash)`. Unique constraint enforced. Re-ingestion of the same artefact is a no-op. Re-runs of any workflow are safe.

**Alternatives considered.** No idempotency (original); fingerprint on `(source_type, source_id)` only (vulnerable to silent updates); UUID per ingest (no dedup).

**Rationale.** Three-component fingerprint catches both duplicates and silent updates (same URL, new content). Cheap to compute, simple to enforce.

**Consequences.** Fingerprinting logic in ingestion modules. Hash collisions theoretically possible but irrelevant at this volume.

**What would change our mind.** Hash collision causing a real incident. Move to a longer hash.

---

### ADR-015: Variant perception is a finding, not a frame

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** prompt-design, safety

**Context.** v1.0 §5.3 stated "every synthesis step starts with 'what does the market not know.'" The council (GPT-5.5) flagged that this prompt structure encourages manufactured contrarianism: LLMs are highly responsive to requested framing.

**Decision.** Synthesis output ordering is: facts → consensus view → our prior view → evidence delta → variant perception (if any) → open `[VERIFY]` items. "No material variant perception found" is a valid and rewarded output.

**Alternatives considered.** Variant-perception-first (original); no variant perception in templates; variant perception as a flag only.

**Rationale.** The market is often right about the obvious things. The right action is sometimes to confirm consensus faster, not invent a debate. Asking for variant perception in slot one will produce one whether or not it exists.

**Consequences.** Agent prompts must enforce the ordering. Outputs that lack variant perception are not flagged as problems.

**What would change our mind.** Operating experience showing that the analyst's actual variant views are being suppressed by this ordering. Adjust then.

**Supersedes:** v1.0 §5.3 framing.

---

### ADR-016: LLM tier split — Haiku for classification, Sonnet for synthesis

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** cost, architecture

**Context.** Cost discipline requires matching model capability to task. Haiku is cheap and fast; Sonnet is more capable.

**Decision.** Haiku is used for classification tasks (filings classification, materiality scoring, entity tagging on news/forum content when those are added). Sonnet is used for synthesis (earnings prep, variance analysis, daily briefing). Embeddings via Voyage AI.

**Alternatives considered.** Sonnet for everything; Haiku for everything; mixed by content rather than task.

**Rationale.** Classification is high-volume, low-stakes, and well-suited to a smaller model. Synthesis is low-volume, high-stakes, and benefits from a more capable model. Mixing them up burns money or ships hallucinations.

**Consequences.** Two SDKs configured with different defaults. Per-agent config specifies which tier. Migration to a different provider would require updating both.

**What would change our mind.** Sonnet pricing dropping to Haiku levels (use Sonnet everywhere); Haiku quality dropping for classification (revisit).

---

### ADR-017: Codex used directly by analyst, not as an architectural role

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** workflow, scope

**Context.** v1.0 §8.5 framed Codex as one of three architectural roles ("Builder") alongside OpenClaw and the workflow agents, with orchestrator-dispatched Codex as a future capability. The council (Opus, GPT-5.4, GPT-5.5) flagged this as premature meta-automation.

**Decision.** Codex is a tool the analyst uses directly from the terminal. There is no orchestrator-dispatched Codex in v1. The "Builder" framing is removed from architecture documentation.

**Alternatives considered.** Builder framing retained (original); Codex never invoked at all (rejected — the analyst will use it).

**Rationale.** A system that modifies itself before the base system exists is second-order overreach. Direct invocation is simpler, more controllable, and fully sufficient.

**Consequences.** No automated code-change pipeline. Routine maintenance (e.g., bumping a metric definition) is a manual Codex session.

**What would change our mind.** A clear, repeated maintenance pattern emerging that is amenable to automation, after the base system has been operational for several months.

**Supersedes:** v1.0 §8.5.

---

### ADR-018: OpenClaw is "orchestrator," not "kernel"

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** terminology

**Context.** v1.0 used "kernel" as a metaphor for OpenClaw's role. The council found this unnecessarily grandiose for what is a job dispatcher and queue manager.

**Decision.** OpenClaw is referred to as "the orchestrator." The term "kernel" is removed from documentation and design language.

**Alternatives considered.** Keep "kernel" (original); use "scheduler" (too narrow); use "hub" (too vague).

**Rationale.** Naming sets expectations. "Kernel" implies low-level operating-system semantics that don't apply. "Orchestrator" is what it is.

**Consequences.** Cosmetic; no impact on implementation.

---

### ADR-019: Four-plane formalism dropped; modules and dependencies are the design primitive

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** terminology, architecture

**Context.** v1.0 organised the architecture around four "planes" (Substrate, Tool, Agent, Orchestration). The council unanimously found this conceptual ceremony — the directory structure already communicates the same information.

**Decision.** The four-plane formalism is dropped. The topology diagram remains as an onboarding artefact. Design discussions use modules-and-dependencies language. "Plane" is removed from the glossary.

**Alternatives considered.** Keep planes (original); remove diagram entirely.

**Rationale.** Taxonomy that doesn't change behaviour is dead weight. The diagram is useful for onboarding; the prose framing was not.

**Consequences.** Less ceremony, more clarity.

**Supersedes:** v1.0 §6.1.

---

### ADR-020: Daily briefing workflow added to v1 agent inventory

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** scope, workflow

**Context.** The council (Opus) noted that a 7am IST digest of queue depth, stale items, open variances, and thesis-contradictory signals from the prior 24h was higher-leverage than four of the agents in the original v1.0 inventory.

**Decision.** `daily_briefing` is added to the v1 agent inventory. Cron-triggered at 7am IST. Output: digest in defined format, delivered via channel TBD (§19.4 of architecture doc).

**Alternatives considered.** Defer to v2; build as a UI dashboard only without an agent.

**Rationale.** The briefing closes the loop on the entire system: it surfaces what needs attention each morning, in one place, without requiring the analyst to poll the UI. It is the most natural daily entry point.

**Consequences.** One additional agent in v1. Modest cost increase. Delivery channel decision deferred.

---

### ADR-021: Three living docs + two design docs + lazy charters/runbooks/prompts

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** documentation, process

**Context.** v1.0 specified nine documents with a fixed sequence. The council found this process scaffolding for a five-person team, not a one-person project.

**Decision.** Documentation structure:

**Living docs (always current):**
- `01-vision-and-architecture.md`
- `02-decision-log.md`
- `03-backlog.md`
- `04-data-model.md`

**Design docs (created before the corresponding subsystem):**
- `05-approval-queue-design.md` (before any module charter)
- `06-eval-harness-design.md` (before second synthesis agent ships)

**Lazy docs (created when needed):**
- `module-charters/<name>.md` — when module is being implemented
- `runbooks/<name>.md` — when first operational procedure is needed
- `prompt-library.md` — when first agent ships

**Alternatives considered.** Original nine-doc plan; three docs only (Opus's recommendation); ad-hoc.

**Rationale.** Documents that aren't being maintained are worse than no documents. Lazy creation matches doc creation to actual need. Six fixed docs (4 living + 2 design) is the minimum that covers the genuinely complex areas.

**Consequences.** Some areas are undocumented until they ship — accepted, since documenting unbuilt systems is largely speculation.

**Supersedes:** v1.0 §17 doc map.

---

### ADR-022: Theses as Markdown in git, with thin DB metadata table

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, modeling

**Context.** v1.0 had `coverage.theses` as a fully-structured DB table with versioned rows. The council (Opus) flagged this as structurally premature — theses are prose, and forcing prose into DB rows loses richness without gaining much queryability.

**Decision.** Hybrid model:
- Prose lives in `coverage_theses/<company>/v<n>.md` in git, with YAML front matter for metadata (status, dates, author, key drivers).
- A thin `coverage.theses_meta` table stores the active version pointer, status, dates, and links to evidence rows for queryability.

Theses are diffable in git, fully versioned by git history, and queryable via the metadata table.

**Alternatives considered.** Full DB table (original); pure markdown without metadata table.

**Rationale.** Best of both: rich prose with version history; structured queryability where needed. Migrate to a fuller DB representation only after 6+ thesis versions across 4+ companies show genuine repeated structure.

**Consequences.** Two storage locations to keep in sync. Mitigated by tooling (`git`-based loader at startup populates `theses_meta` from front matter).

**What would change our mind.** Querying needs growing beyond what front matter supports.

**Supersedes:** v1.0 §9.1 theses table design.

---

### ADR-023: Eval harness before second synthesis agent ships

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** safety, process

**Context.** v1.0 stated success criteria like "zero numerical hallucinations" and "≥85% extraction accuracy" without a mechanism to measure them. The council unanimously flagged this as the most important missing piece.

**Decision.** An eval harness is built before the second synthesis agent (`variance_analysis`, since `earnings_prep` will likely be first) ships. The harness includes:
- Golden set of 50–100 (input → expected structured output) pairs across filings extraction and variance scenarios
- Nightly run against current code/prompts
- Regression alerts blocking deploy
- `ops.evals` table tracking historical pass rates

Designed in `06-eval-harness-design.md`.

**Alternatives considered.** Defer eval harness to v2; build before any agent ships (too early — no agent to test); build after v1 ships (too late — regressions will have shipped).

**Rationale.** Without measurement, claims of accuracy are aspirational. The second synthesis agent is the right gate because by then the patterns are clear enough to seed a meaningful golden set, and one synthesis agent has already been validated by hand.

**Consequences.** Eval harness build is a real workstream (~1 week). Golden set curation is a recurring task. Worth it.

---

### ADR-024: Rejection-reason taxonomy + 1–3 quality rating on every queued item

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** ux, feedback

**Context.** The council flagged that the system had no feedback loop from analyst edits back into prompt or system quality. Without this, prompts can degrade silently and there's no signal for improvement.

**Decision.** Every approval queue item carries:
- A 1–3 quality rating field (1=poor, 2=acceptable, 3=excellent)
- A structured rejection reason (when rejected) from a defined taxonomy: `source_wrong`, `extraction_wrong`, `stale`, `duplicate`, `wording`, `thesis_disagreement`, `period_unit_consolidation`, `other` (with optional free-text)

Aggregated monthly. Drives prompt and extraction improvements.

**Alternatives considered.** Free-text rejection only; no rejection field; six-monthly drift audit (original — too slow).

**Rationale.** Trivial to add, closes the most important learning loop, generates labelled data for prompt iteration.

**Consequences.** UI complexity slightly higher. Monthly review becomes a real practice.

---

### ADR-025: Indian conventions richness — corporate actions, accounting policies, consolidation basis on every financials row

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, indian-markets

**Context.** v1.0 §5.9 covered FY conventions and units but missed restatements (consolidated vs. standalone), IndAS transitions, corporate actions (splits, bonuses, demergers), and quarterly-vs-half-yearly disclosure variance.

**Decision.** Schema additions:
- `coverage.corporate_actions` table: `(company_id, effective_date, type, ratio_or_amount, source_filing_id)`
- `coverage.accounting_policies` table: `(company_id, version, effective_from, notes, source_filing_id)`
- Every `coverage.financials` row carries `consolidation_basis` (consolidated | standalone) and `accounting_policy_version`
- Restated rows carry a `supersedes` link; original retained for audit

**Alternatives considered.** Skip and handle ad-hoc (original); a single "notes" free-text column.

**Rationale.** These will bite eventually — restatements happen, corporate actions distort historical comparisons, IndAS transitions invalidate prior numbers. Adding structure now is cheap; retrofitting later is expensive.

**Consequences.** Schema is more complex. Ingestion and extraction must populate these fields.

---

### ADR-026: Blast-radius tooling — derivation log walks for post-approval corrections

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** schema, safety

**Context.** The council (Opus) flagged that there was no exit/rollback for a wrong row that *did* get approved. Once a wrong number propagates to estimates, then to a sector preview that already shipped, there's no tooling to flag downstream rows.

**Decision.** When a coverage row is corrected (post-approval), the derivation log (`coverage.derivations`) is walked to identify all downstream rows that depend on it. Those rows are flagged for recompute via `coverage.recompute_queue`. Analyst reviews the recompute queue as part of the regular approval flow.

**Alternatives considered.** No blast-radius tooling (original); fully automatic recompute (rejected — analyst review required).

**Rationale.** Errors will happen. Without blast-radius tooling, a single corrected row leaves silent inconsistency throughout dependent estimates. With it, corrections are propagated systematically.

**Consequences.** Derivation log must be complete (every derived row has an entry). Recompute queue is another UI surface.

---

### ADR-027: Per-agent token and tool-call hard ceilings

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** cost, reliability

**Context.** The council (Gemini) flagged that multi-step agent loops with open-ended "Gap Check" steps are notoriously unstable — LLMs get stuck calling tools that don't return missing info. The original v1.0 plan had no hard ceilings.

**Decision.** Every agent has hard ceilings configured in `agents/<workflow>/config.py`:
- Maximum tool calls per run (default 15)
- Maximum total tokens per run (default by tier — Haiku 50K, Sonnet 200K)
- Explicit "no further useful tool calls" exit condition in the prompt
- State machine wrapping the loop (Plan → Retrieve → Synthesize → Output); no recursion

When a ceiling is hit, the agent surfaces the partial state and exits with status `partial`.

**Alternatives considered.** No ceilings (original); soft ceilings with warnings; cost-based ceilings.

**Rationale.** Hard ceilings prevent runaway loops, runaway costs, and infinite-tool-call patterns. Surfacing partial state lets the analyst see what was gathered.

**Consequences.** Some workflows may exit partial more often initially; tunable per agent.

---

### ADR-028: Deferred ingestion sources — Valuepickr, Telegram, news — added post-slice

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** scope, ingestion

**Context.** The original v1.0 plan included Valuepickr, Telegram, and news as parallel ingestion streams. Per ADR-009 (vertical slice first), these are deferred.

**Decision.** Valuepickr, Telegram, and news ingestion are deferred until after the v1 slice has run through one earnings season. Each will be evaluated based on what the slice operation reveals about gaps in coverage.

**Alternatives considered.** Build all three in v1 (original); pick one for v1; never build them.

**Rationale.** The slice can be evaluated cleanly without these sources. Adding them increases v1 surface area and dilutes focus. After the slice, we'll have data on which signals are actually missing — choose then.

**Consequences.** v1 misses some classes of signal. Mitigated by analyst's existing manual workflow for these sources continuing during v1.

**What would change our mind.** Slice operation revealing a specific source as essential to the slice itself.

---

### ADR-029: Daily briefing delivery channel — TBD until agent is built

**Date:** 2026-05-04
**Status:** Accepted (placeholder; resolve when `daily_briefing` ships)
**Tags:** ux, scope

**Context.** The daily briefing needs to reach the analyst at 7am IST. Options: email, Slack, in-UI dashboard, push notification.

**Decision.** Defer the channel decision until the agent is being built. All four are technically straightforward; the right answer depends on the analyst's morning workflow.

**Alternatives considered.** Lock to email (default); lock to Slack; lock to UI only.

**Rationale.** Premature channel choice. Decide based on observed behaviour during build.

**Consequences.** None until `daily_briefing` is implemented.

---

### ADR-030: Build/maintenance/review attention budget tracked monthly

**Date:** 2026-05-04
**Status:** Accepted
**Tags:** process, cost

**Context.** The council (GPT-5.5) flagged that monetary cost was tracked precisely while attention cost — the dominant cost — was vague. "Hours saved" claims need a denominator.

**Decision.** Monthly attention budget tracked in the decision log:
- Build hours (analyst + Codex sessions)
- Maintenance hours (broken scrapers, schema fixes, debugging)
- Review hours (approval queue, eval harness, drift audit)
- Hours saved (self-report against pre-system baseline)
- Hours redirected (to channel work, client conversations, proprietary research)

Targets in `01-vision-and-architecture.md` §14.2. If steady-state crosses 8 hours/week of total system overhead for two consecutive months, pause feature work and simplify.

**Alternatives considered.** No tracking (original); only build hours; only hours saved.

**Rationale.** "Hours saved that get spent managing the system don't count." The discipline is to track both sides.

**Consequences.** Honest weekly self-report becomes a recurring task.

---

## 4. Future Entries Template

When adding new entries, copy the format in §2. Keep entries concise — one screenful is the target. Cross-reference superseded entries explicitly. Never edit accepted entries.
