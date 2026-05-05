# Alembic Migrations

This folder contains database migrations for AgentOS.

## Local usage

1. Start Postgres (Docker):
   - `docker compose up -d postgres`
   - Optional: set `DATABASE_URL` to override `alembic.ini` connection.
2. Apply migrations:
   - `alembic -c alembic.ini upgrade head`
3. Show current revision:
   - `alembic -c alembic.ini current`
4. Roll back one step:
   - `alembic -c alembic.ini downgrade -1`
