# Contributing

This repository is document-driven. Do not write code from a vague instruction. Start from `03-backlog.md`, pick one item, and implement only that item's stated scope and acceptance criteria.

## Required Context

Before implementation, read:

- `01-vision-and-architecture-v1.1.md`
- `02-decision-log.md`
- `03-backlog.md`
- `04-data-model.md`
- `05-approval-queue-design.md`

If the work touches a subsystem with a later module charter or runbook, read that too.

## Scope Discipline

- Vertical slice before platform.
- No Valuepickr, Telegram, news, sector preview, client meeting prep, or thesis review work until the Operate phase produces evidence for expansion.
- No Python projection engine in v1; Excel remains the source of truth.
- No autonomous structured writes to coverage tables; use the approval queue.
- No LLM-generated numbers; parsers extract, LLMs map and synthesize.

## Definition of Done

A work item is done only when:

- Its backlog acceptance criteria are satisfied.
- Relevant tests or smoke checks pass.
- Any architectural decision is appended to `02-decision-log.md`.
- Any schema change is reflected in `04-data-model.md`.
- The change is small enough to review directly.

## Repository Boundaries

The planned monorepo module boundaries are documented in the architecture and backlog. Until `F-01` is implemented, avoid creating project structure opportunistically. Let `F-01` create the first code-facing scaffold in one focused change.