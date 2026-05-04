# AgentOS — Approval Queue Design

## 0. Document Control

| Field | Value |
| --- | --- |
| Document ID | 05 |
| Title | Approval Queue Design |
| Version | 1.0 |
| Status | Draft for review |
| Owner | Mohit Agarwal |
| Audience | Mohit, OpenClaw, Codex, future-Mohit |
| Repo location | `docs/05-approval-queue-design.md` |
| Related ADRs | ADR-010 (tiered queue), ADR-024 (rejection taxonomy), ADR-026 (blast-radius tooling) |

---

## 1. Why This Document Exists First

The model council was unanimous: the approval queue is the load-bearing safety mechanism for AgentOS, but it was treated as plumbing in the v1.0 architecture. The original "10–20 minutes/day" budget collapses under earnings-season load (4–8 names report in 3 weeks → queue depth 20–40 items per day or more), forcing either rubber-stamping (defeating the safety guarantee) or backlog (defeating the operability guarantee).

This document designs the queue as a real system before any module charter is written. It exists because:

1. **The queue is the product.** Every other workflow output flows through it.
2. **Tier rules drive schema.** The data model needs to know which writes are tiered which way.
3. **Peak-load behaviour is a hard requirement.** Earnings season is a known, recurring load spike.
4. **UI design constrains everything else.** What the analyst sees during review determines what the agents must produce.

If this design is wrong, the system is unsafe at peak load. If this design is right, the rest of the system can be built with confidence.

---

## 2. Goals

A correctly-designed approval queue must:

1. **Make substantive review tractable.** Each item the analyst sees should be reviewable in under the time budget for its tier.
2. **Enforce safety.** No coverage write happens without explicit or sampled human approval.
3. **Survive earnings season.** Peak load is 5–10× normal; the queue must not collapse under it.
4. **Generate learning signal.** Every reject must teach the system something via the rejection taxonomy.
5. **Match risk to attention.** Low-risk writes consume less attention; high-risk writes consume more.
6. **Surface staleness.** Items that have been in the queue too long must escalate or auto-resolve.
7. **Show provenance natively.** The analyst must see source-side-by-side with the proposed write.
8. **Support batch operations.** Reviewing 30 extracted rows from one filing must be one operation, not 30.

---

## 3. Three Tiers

The queue is tiered by risk. Tier classification is a property of the write, not of the workflow that produced it.

### 3.1 Tier 1 — Auto-Apply

**What:** Low-risk, high-frequency writes that auto-apply without per-item approval. Sample-audited later.

**Examples:**
- Filing metadata (BSE filing arrived, type classified, ingested timestamp recorded)
- Source provenance rows (the *fact* that a filing was ingested at location X)
- Idempotency fingerprints
- Workflow run logs (`ops.workflow_runs`)
- Eval harness results
- Daily briefing generation log

**Approval mechanism:** None at write time. A daily sample audit (5% of yesterday's auto-applied writes) is reviewed during the morning briefing flow. Errors found in the sample audit auto-promote the corresponding write *type* to Tier 2 for the next 30 days.

**Time budget:** 0 minutes/item at write. ~5 minutes/day for sample audit.

**Tier-1 rule:** A write is Tier 1 only if **rolling back is trivial** (no derivations depend on it) AND **the write does not touch a coverage table**. Anything that touches `coverage.*` is at minimum Tier 2.

### 3.2 Tier 2 — Batch-Approve by Event

**What:** Mid-risk writes grouped by source event. The analyst reviews a *bundle* of related writes together, with one approval action that accepts all, rejects all, or accepts-with-edits.

**Examples:**
- Filing classification (one filing → classification + extracted numbers + materiality score, reviewed as one bundle)
- Variance analysis output (one earnings event → reported actuals + our estimates + consensus + computed variances + driver attribution, reviewed as one bundle)
- Excel adapter read (one workbook save → all updated `coverage.financials` rows, reviewed as one bundle)

**Approval mechanism:** UI presents the bundle with source side-by-side, semantic diffs vs. prior state, confidence scores per row, and `[VERIFY]` flags surfaced. Analyst can accept-all, reject-all, or open-and-edit individual items. Edits are tracked separately from raw approvals for the rejection taxonomy.

**Time budget:** 3–10 minutes per bundle. Typical bundle is 10–30 atomic writes.

**Tier-2 rule:** A write is Tier 2 if it **touches a coverage table** AND **is part of a coherent event** (one filing, one earnings call, one workbook save). High-stakes thesis-level writes are Tier 3 regardless.

### 3.3 Tier 3 — Line-Item

**What:** High-risk, low-frequency writes that require one-by-one approval with full context.

**Examples:**
- Thesis revisions (new version of `coverage_theses/<company>/v<n>.md`)
- Driver status changes (e.g., flipping ARV API from `tracking` to `deteriorating`)
- Catalyst additions or material changes
- Estimate revisions where the proposed change crosses a configured magnitude threshold (default: >5% on revenue, >10% on EBITDA, any sign change)
- Any write the analyst manually escalated from Tier 2 during review
- Recompute queue items from blast-radius walks (ADR-026)

**Approval mechanism:** UI presents one item at a time, with full source provenance, derivation chain (if applicable), claim provenance, prior state, proposed state, confidence, and any related `[VERIFY]` flags. Analyst writes a brief justification on accept/reject (free text + structured rejection reason).

**Time budget:** 5–15 minutes per item.

**Tier-3 rule:** Any write that is thesis-affecting, exceeds a magnitude threshold, or has been escalated from Tier 2 is Tier 3.

### 3.4 Tier classification logic

Implemented as a pure function `classify_tier(write_proposal) -> Tier` in `core/queue/tiering.py`. Function is deterministic, unit-tested, and inspected by Codex when adding new write types. Any new write type without an explicit tier classification is **Tier 3 by default** — fail safe.

### 3.5 Tier auto-tightening

If a Tier 1 write type has corrections found in sample audit, that write type auto-promotes to Tier 2 for 30 days. After 30 days, it auto-demotes back to Tier 1 unless another correction has been found.

If a Tier 2 write type has rejection rate >30% over 14 days, it auto-promotes to Tier 3 until the rejection rate drops below 15% over 14 days.

If a Tier 3 write type has acceptance rate >95% with zero corrections over 60 days, it is *flagged for review* (not auto-demoted) so the analyst can decide whether to demote. Auto-demotion is too risky for Tier 3.

These rules are stored in `ops.tier_rules` and enforced by the queue processor.

---

## 4. Queue Lifecycle

### 4.1 States

Each queue item moves through these states:

```
created → pending_review → under_review → (accepted | rejected | accepted_with_edits | escalated | expired)
```

- **created** — write proposal generated by an upstream workflow; not yet visible in UI
- **pending_review** — visible in UI; awaiting analyst attention
- **under_review** — analyst has opened it; lock prevents concurrent edits (relevant only if the analyst opens it on multiple devices)
- **accepted** — write applied to target table
- **rejected** — write discarded; rejection reason recorded
- **accepted_with_edits** — analyst modified the proposed write before accepting; edited values applied; original proposal retained for the eval harness
- **escalated** — analyst moved a Tier 1 or Tier 2 item up to Tier 3 for closer review (resets review state)
- **expired** — item exceeded its tier's staleness threshold (see §4.3); auto-rejected with reason `expired`; alert raised

### 4.2 Lifecycle metadata per item

```
queue_item:
  id
  tier (1 | 2 | 3)
  bundle_id (nullable; non-null only for Tier 2 bundles)
  workflow_run_id (FK to ops.workflow_runs)
  write_type (string; e.g., 'filings.classification', 'coverage.financials.row')
  target_schema, target_table, target_row_id (where this would write)
  proposed_payload (JSONB)
  current_state (JSONB; the prior value being replaced, or null for inserts)
  source_provenance_id (FK to coverage.source_provenance)
  derivation_provenance_id (FK to coverage.derivations, nullable)
  claim_provenance_id (FK to coverage.claim_provenance, nullable)
  confidence_score (0.0–1.0; from the upstream workflow)
  verify_flags (JSONB array of [VERIFY] markers)
  created_at, pending_since, opened_at, resolved_at
  resolved_by ('analyst' | 'auto_applied' | 'expired')
  rejection_reason (enum, nullable)
  rejection_notes (text, nullable)
  quality_rating (1–3, nullable)
```

### 4.3 Staleness thresholds

| Tier | Staleness threshold | Action on expiry |
| --- | --- | --- |
| Tier 1 | n/a (auto-applied) | n/a |
| Tier 2 | 7 days | Auto-reject; alert; item retained for review even after rejection |
| Tier 3 | 14 days | Auto-reject; alert; analyst notified during daily briefing |

Staleness is a real concern — old proposals based on filings that have been superseded should not be applied. The 7- and 14-day windows are intentionally short to prevent stale-data writes.

### 4.4 Atomicity

A bundle (Tier 2) is atomic: accept-all applies all rows in one transaction; if any row fails (FK violation, constraint violation), the entire bundle is rolled back and the item moves to a `failed` sub-state for inspection.

Tier 3 items are individually atomic.

---

## 5. Peak-Load Behaviour — Earnings Season

### 5.1 Expected load

A typical earnings season for the coverage universe of 8 names:
- 8 filings (results announcements) over ~3 weeks, clustered toward the end
- 8 transcripts (when available) — out of scope for v1 BSE-only ingestion (ADR-007)
- ~30–60 follow-up filings (investor presentations, conference call audio if filed, segment disclosures)
- ~10 broker note PDFs per company per week (when news ingestion ships post-v1)

Per filing in v1: ~10–30 extracted rows + 1 classification + 1 variance analysis (post-results filings) + ~3–8 derived estimates from Excel adapter on assumption updates.

**Peak day during earnings season:** 3 results announcements simultaneously → ~30–90 extracted rows + 3 variance analyses + ~10–24 derived estimates = **40–120 atomic writes**, organised into ~6–12 bundles.

**Peak day's approval time at 5 min/bundle average:** 30–60 minutes.

### 5.2 Peak-load mitigations

1. **Aggressive Tier 1 classification.** During build, audit which write types are genuinely safe to auto-apply. The more write types in Tier 1, the lower the analyst's peak load.

2. **Bundle prioritisation.** During earnings season, bundles are ordered by:
   - Tier 3 first (always)
   - Tier 2 ordered by: (a) earnings-event proximity (results filings before follow-ups), (b) company priority (active > passive coverage), (c) age (older first within the same priority)

3. **Earnings-season mode flag.** A toggle in the UI (`ops.system_mode = 'earnings_season'`) that activates:
   - Higher staleness thresholds (Tier 2: 14 days, Tier 3: 21 days) — reflects analyst's reality during peak
   - Bundle prioritisation as above
   - Daily briefing emphasises queue depth and projects clearance time at current pace
   - Eval harness regression alerts severity-elevated to interrupt-worthy

4. **Pre-earnings warm-up.** 5 trading days before each earnings event, the system runs:
   - A pre-earnings checklist (covered name, prior estimates, latest thesis, last 4 quarters of variance) staged in a single Tier 2 bundle
   - This lets the analyst pre-load context, reducing the per-bundle review time during the actual earnings filing

5. **Backlog visualisation.** UI shows a 14-day rolling queue depth chart, projected clearance time at current review pace, and per-tier breakdown. The analyst sees the slope before it becomes a crisis.

### 5.3 What the system does NOT do at peak load

- **Does not auto-approve to clear backlog.** Tier 1 promotion is the only tier-mobility mechanism, and it is triggered by tier rules (§3.5), not by backlog depth.
- **Does not down-tier items to clear backlog.** Tier classification is by risk, not by load.
- **Does not skip review.** Backlog is treated as a signal to slow ingestion (e.g., pause news ingestion when news is built), not as a reason to skip review.

### 5.4 Backlog-clearing strategy

If the queue exceeds defined thresholds:

| Threshold | Action |
| --- | --- |
| Tier 2 queue >50 bundles | Daily briefing escalation; suggest pausing non-critical ingestion |
| Tier 3 queue >10 items | Daily briefing escalation; flag specific items aging >7 days |
| Total queue depth >2× rolling 30-day median | Daily briefing alert; recommend a "queue Saturday" working session |

These are advisory thresholds, not automatic actions.

---

## 6. Review UI

### 6.1 Information architecture

The approval queue UI is the primary surface of AgentOS. The analyst spends more time here than in any other view. UI design priorities:

1. **One screen per item.** No tabs, no modals layered on modals.
2. **Source side-by-side.** The proposed write is on the right; the source (filing PDF page, Excel cell, or evidence bundle) is on the left.
3. **Diffs over dumps.** Show what changed vs. prior state, not just the new state.
4. **Confidence visible.** The agent's confidence score is on screen, not buried.
5. **`[VERIFY]` flags front and centre.** Never below the fold.
6. **Keyboard-first.** `J` next item, `K` prev item, `A` accept, `R` reject, `E` edit, `S` skip, `1`/`2`/`3` quality rating, `?` rejection-reason picker. Mouse is fallback.

### 6.2 Layout — Tier 2 bundle

```
┌────────────────────────────────────────────────────────────────────┐
│ BUNDLE — Filing Classification: LAURUS 4QFY26 results announcement │
│ 23 atomic writes  |  confidence: 0.91  |  3 [VERIFY] flags         │
├──────────────────────────────────────────────┬─────────────────────┤
│  SOURCE                                       │  PROPOSED WRITES    │
│  [PDF viewer of the filing, page-jump to     │  [Table of writes:  │
│   relevant section per row]                   │   target_table,     │
│                                               │   field, prior,     │
│                                               │   proposed, conf,   │
│                                               │   verify-flag]      │
│                                               │                     │
│                                               │  Rows highlighted:  │
│                                               │  - red if [VERIFY]  │
│                                               │  - yellow if conf   │
│                                               │    < 0.8            │
│                                               │  - green if accept-├┤
│                                               │    able             │
└──────────────────────────────────────────────┴─────────────────────┤
│ [ Accept All ]  [ Reject All ]  [ Edit Selected ]  [ Escalate ]    │
│ Quality: 1 ●  2 ○  3 ○                                             │
└────────────────────────────────────────────────────────────────────┘
```

### 6.3 Layout — Tier 3 single item

```
┌────────────────────────────────────────────────────────────────────┐
│ THESIS REVISION — Cohance Lifesciences — proposed v3                │
│ confidence: 0.74  |  2 [VERIFY] flags  |  age: 1d 4h               │
├──────────────────────────────────────────────┬─────────────────────┤
│  EVIDENCE BUNDLE (claim provenance)           │  PROPOSED THESIS    │
│  - Filing #12345 (4QFY26 results)             │  [Markdown render   │
│  - Transcript turn #67 [VERIFY: turn boundary]│   of new version    │
│  - Prior thesis v2 (active since 2026-02-12) │   with diff         │
│  - 3 Valuepickr posts [post-v1; placeholder] │   highlighting vs.  │
│                                               │   v2]               │
│  PRIOR STATE                                  │                     │
│  Thesis v2 — variant: CDMO ramp ahead of plan │                     │
├──────────────────────────────────────────────┴─────────────────────┤
│ Justification (required):                                          │
│ [                                                                ] │
│                                                                    │
│ [ Accept ]  [ Reject ]  [ Accept with edits ]                      │
│ Rejection reason (if reject): ▼                                    │
│ Quality: 1 ●  2 ○  3 ○                                             │
└────────────────────────────────────────────────────────────────────┘
```

### 6.4 Source-side-by-side requirements

For each write type, the UI must know how to render the source pane:

| Source type | Render mode |
| --- | --- |
| BSE filing PDF | Embedded PDF viewer, jump to extracted page/region |
| BSE filing table | Cropped image of the table region (camelot bounding box) + structured table render |
| Excel cell | Excel-style grid showing surrounding rows/columns + named range highlighted |
| Transcript (post-v1) | Text view, jump to turn |
| Forum/news post (post-v1) | Rendered markdown/HTML with original link |
| Derivation | Formula display + linked source rows for inputs |
| Claim provenance | List of evidence items, each clickable into its own source view |

This is non-negotiable. Reviewing without seeing the source is rubber-stamping.

### 6.5 Edit semantics

When the analyst clicks "Edit" on a row in a Tier 2 bundle:
- The row enters edit mode inline (not modal)
- Original agent-proposed value is shown alongside the edit field
- On save, the edit is recorded as `accepted_with_edits` with both values retained
- Edits feed the eval harness as labelled data (the analyst-edited value is the "correct" output for that input)

### 6.6 Daily briefing integration

The daily briefing (ADR-020) runs at 7am IST and surfaces:
- Total queue depth and per-tier breakdown
- Items aging beyond their tier's staleness threshold
- Items with rejection rates trending up for the past 14 days
- Specific Tier 3 items the analyst should plan to handle today

The briefing is the analyst's morning entry point to the queue.

---

## 7. Rejection Taxonomy

Per ADR-024, every rejected item has a structured rejection reason. The taxonomy:

| Reason | Definition | Implication |
| --- | --- | --- |
| `source_wrong` | The agent extracted from the wrong source (e.g., wrong filing, wrong page) | Extraction or retrieval bug |
| `extraction_wrong` | Right source, wrong number — extraction failed within the right document | Parser bug |
| `period_unit_consolidation` | Number is correct but mistagged (wrong period, wrong unit, consolidated/standalone confusion) | Schema/extraction bug — distinct because it's the most common silent error |
| `stale` | Information has been superseded since extraction | Ingestion lag or queue staleness |
| `duplicate` | Item duplicates another in the queue | Idempotency bug |
| `wording` | Synthesis output is correct in substance but poorly phrased | Prompt iteration |
| `thesis_disagreement` | The analyst disagrees with the analytical conclusion (not a system error) | Genuine analytical input — feeds prompt and thesis |
| `confidence_too_low` | Item should not have been queued at this confidence level | Tier or threshold tuning |
| `other` | Free text only | Triage manually |

### 7.1 Aggregation and review

Monthly aggregation (per ADR-024 and §8.8 of architecture doc):
- Distribution of rejection reasons per workflow
- Trend lines (is `extraction_wrong` increasing? — parser regression)
- Top 5 most-edited fields (where the agent is closest-but-wrong)
- Rejection rate per tier (compared to tier-tightening thresholds in §3.5)

Aggregation drives:
- Prompt revisions (for `wording`, `thesis_disagreement` patterns)
- Parser fixes (for `extraction_wrong`, `period_unit_consolidation`)
- Schema fixes (if a rejection reason is consistently misapplied because the schema doesn't capture the right distinction)
- Tier rule updates

---

## 8. Quality Rating

Per ADR-024, every queue item carries a 1–3 quality rating:

- **1 (poor)** — output required substantial editing or rejection
- **2 (acceptable)** — output was usable as-is or with minor edits
- **3 (excellent)** — output was high-quality and saved meaningful time

Ratings are independent of acceptance. An item can be accepted with quality=1 (the analyst accepted because it was easier than rejecting and rebuilding) or rejected with quality=2 (the analyst rejected on `thesis_disagreement` despite the extraction being clean).

Aggregated monthly to track agent quality trends.

---

## 9. Schema Sketch

This is the high-level schema; full DDL is in `04-data-model.md`.

```sql
-- ops.review_queue
CREATE TABLE ops.review_queue (
  id UUID PRIMARY KEY,
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
  state TEXT NOT NULL CHECK (state IN (
    'created', 'pending_review', 'under_review',
    'accepted', 'rejected', 'accepted_with_edits',
    'escalated', 'expired', 'failed'
  )),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  pending_since TIMESTAMPTZ NULL,
  opened_at TIMESTAMPTZ NULL,
  resolved_at TIMESTAMPTZ NULL,
  resolved_by TEXT NULL CHECK (resolved_by IN ('analyst', 'auto_applied', 'expired') OR resolved_by IS NULL),
  rejection_reason TEXT NULL,
  rejection_notes TEXT NULL,
  quality_rating SMALLINT NULL CHECK (quality_rating IN (1, 2, 3) OR quality_rating IS NULL),
  edited_payload JSONB NULL  -- populated if accepted_with_edits
);

CREATE INDEX idx_review_queue_state_tier ON ops.review_queue (state, tier);
CREATE INDEX idx_review_queue_bundle ON ops.review_queue (bundle_id) WHERE bundle_id IS NOT NULL;
CREATE INDEX idx_review_queue_pending ON ops.review_queue (pending_since) WHERE state IN ('pending_review', 'under_review');

-- ops.tier_rules
CREATE TABLE ops.tier_rules (
  write_type TEXT PRIMARY KEY,
  base_tier SMALLINT NOT NULL CHECK (base_tier IN (1, 2, 3)),
  current_tier SMALLINT NOT NULL CHECK (current_tier IN (1, 2, 3)),
  tier_promoted_until TIMESTAMPTZ NULL,
  tier_promoted_reason TEXT NULL,
  notes TEXT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ops.queue_audits (sample audit of Tier 1 auto-applies)
CREATE TABLE ops.queue_audits (
  id UUID PRIMARY KEY,
  audited_item_id UUID NOT NULL REFERENCES ops.review_queue(id),
  audited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  audited_by TEXT NOT NULL DEFAULT 'analyst',
  audit_result TEXT NOT NULL CHECK (audit_result IN ('correct', 'incorrect', 'flagged')),
  audit_notes TEXT NULL
);
```

(Full schema, including FKs to `coverage.*` provenance tables, lives in `04-data-model.md`.)

---

## 10. The Queue Processor

A dedicated process (running under `approval_processor_role`, ADR-013) is the only thing that writes to `coverage.*` tables. Its responsibilities:

1. **Apply accepted writes.** For each item in state `accepted` or `accepted_with_edits`, apply the payload (or edited payload) to the target table in a single transaction. Update `state` to one of `accepted` (if write succeeded) or `failed`.

2. **Auto-apply Tier 1.** For items created at Tier 1, apply the write immediately in the same transaction as creation. State becomes `accepted` directly with `resolved_by='auto_applied'`.

3. **Run staleness sweep.** Every hour, mark items as `expired` per the staleness thresholds (§4.3). Raise alerts.

4. **Sample-audit Tier 1 writes.** Daily, sample 5% of yesterday's auto-applied writes and create corresponding `ops.queue_audits` rows in `pending` state for the analyst to review during morning briefing.

5. **Process tier-mobility rules.** Daily, evaluate the auto-tightening and auto-loosening rules in §3.5 and update `ops.tier_rules`.

6. **Walk derivations on correction.** When an accepted-and-applied row is later corrected, walk `coverage.derivations` to flag downstream rows; create new queue items in `coverage.recompute_queue` for the analyst.

The queue processor is the only entity that mutates `coverage.*`. Everything else proposes via the queue.

---

## 11. Error Handling

### 11.1 Write failures

If applying an accepted write fails (FK violation, constraint, etc.):
- State becomes `failed`
- `error_details` field populated
- Daily briefing surfaces failed items
- Item retained for inspection — does NOT auto-retry

### 11.2 Bundle partial failures

If a bundle's atomic transaction fails mid-apply, the entire bundle rolls back. State becomes `failed`. The analyst opens the failed bundle in the UI to see which row caused the failure and can fix the upstream proposal or delete the offending row.

### 11.3 Stale-data conflicts

If an accepted write is applied but the target row has been modified since the proposal was created (timestamp comparison), the apply fails with `state='failed'`, reason `stale_target`. Analyst handles manually.

### 11.4 Restoration after Postgres recovery

After a Postgres restore (per backup runbook), the queue may contain items whose `current_state` no longer matches reality. A reconciliation script (in `scripts/queue_reconcile.py`) walks the queue and re-validates each pending item's `current_state` against the live DB. Mismatches are flagged for analyst review.

---

## 12. Metrics & Observability

The queue exposes these metrics, surfaced in the UI dashboard and the daily briefing:

| Metric | Target | Surfaced where |
| --- | --- | --- |
| Queue depth, total | <50 normal; <150 earnings season | Dashboard, briefing |
| Queue depth, Tier 3 | <10 | Dashboard, briefing |
| Median time-to-resolution, Tier 2 | <24h normal; <72h earnings season | Dashboard, monthly review |
| Median time-to-resolution, Tier 3 | <72h | Dashboard, monthly review |
| Tier 1 sample audit error rate | <2% | Monthly review |
| Tier 2 rejection rate | <20% | Monthly review |
| Tier 3 acceptance rate | <80% | Monthly review (>80% triggers tier review) |
| Quality rating mean, by workflow | >2.0 | Monthly review |
| Daily approval time (analyst self-report) | <30 min normal; <90 min earnings | Weekly self-report |

---

## 13. What This Doc Does Not Cover

- **Detailed UI implementation** — Streamlit-specific component design lives in `module-charters/web.md` when web is built.
- **Notification mechanism** — alert routing (email, Slack, push) depends on the daily briefing channel decision (open question §19.4 of architecture doc).
- **Multi-user collaboration on queue items** — out of scope (single user).
- **Queue export / audit-export for compliance** — out of scope unless a compliance need arises.

---

## 14. Open Questions

1. **Tier 3 magnitude thresholds.** Default >5% revenue, >10% EBITDA, any sign change. Resolve once Excel adapter is built and we've seen real estimate-revision distributions.
2. **Sample audit cadence and percentage.** Default 5% daily. Tune after first 30 days of operation.
3. **Bundle size cap.** Should a single Tier 2 bundle cap at, say, 50 atomic writes? Default unlimited; revisit if a bundle ever exceeds 100.
4. **Queue retention.** How long are resolved items kept? Proposal: 1 year hot in `ops.review_queue`, then archived to a `ops.review_queue_archive` table indefinitely. Confirm.

---

## 15. Revision History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | 2026-05-04 | Mohit Agarwal | Initial draft, locked tier model, peak-load behaviour, UI requirements, schema sketch |
