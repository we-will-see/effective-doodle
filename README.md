# AgentOS

AgentOS is a personal research operating system for a single institutional sell-side pharma analyst. The v1 goal is a narrow vertical slice: BSE filing ingestion, deterministic numeric extraction, variance against Excel models, tiered approval, analyst review, and accepted writes into coverage tables.

This repository has completed initial scaffolding (`F-01`) and is now ready to begin schema and workflow implementation for the v1 vertical slice.

## Current Status

- Product and architecture: drafted
- Decision log: seeded
- Backlog: seeded for Foundation, Slice, Operate, and deferred Expand work
- Data model: drafted
- Approval queue design: drafted
- Application code: scaffolding created (`F-01`), feature modules not implemented

## Build Rule

Read these documents before starting any implementation work:

1. `01-vision-and-architecture-v1.1.md`
2. `02-decision-log.md`
3. `03-backlog.md`
4. `04-data-model.md`
5. `05-approval-queue-design.md`

The load-bearing principles are:

- Build the v1 vertical slice before expanding the platform.
- Use deterministic extraction for numbers; LLMs map and synthesize, never generate numbers.
- Preserve source, derivation, and claim provenance.
- Route structured writes through the tiered approval queue.
- Keep Excel as the source of truth for projections in v1.

## Next Work

Proceed to backlog item `F-02 Postgres schemas, roles, and base migration`.
