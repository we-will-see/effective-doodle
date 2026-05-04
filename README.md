# AgentOS

AgentOS is a personal research operating system for a single institutional sell-side pharma analyst. The v1 goal is a narrow vertical slice: BSE filing ingestion, deterministic numeric extraction, variance against Excel models, tiered approval, analyst review, and accepted writes into coverage tables.

This repository is currently in the document-driven setup phase. It intentionally contains design and planning artifacts only. Do not add application code until the relevant backlog item is explicitly selected for implementation.

## Current Status

- Product and architecture: drafted
- Decision log: seeded
- Backlog: seeded for Foundation, Slice, Operate, and deferred Expand work
- Data model: drafted
- Approval queue design: drafted
- Application code: not started

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

Start with backlog item `F-01 Repository scaffolding`, but only after confirming the implementation scope. F-01 may create code/project scaffolding; this setup commit does not.