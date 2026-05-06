# Production Readiness Research Report

**Research Date**: 2026-05-05
**Scope**: AgentOS improvements for production deployment

---

## 1. Alembic Migration Best Practices

### Testing Strategies

**Current Gaps in AgentOS**:
- No automated migration testing in CI
- No rollback verification
- No multi-environment deployment strategy

**Recommendations**:

1. **Migration Testing Pipeline**
   ```python
   # test_migrations.py
   import pytest
   from alembic.command import upgrade, downgrade
   from alembic.config import Config

   def test_migrations_upgrade_downgrade():
       """Test that all migrations can go up and down cleanly"""
       alembic_cfg = Config("alembic.ini")
       
       # Upgrade to head
       upgrade(alembic_cfg, "head")
       
       # Downgrade to base
       downgrade(alembic_cfg, "base")
       
       # Upgrade again to verify idempotency
       upgrade(alembic_cfg, "head")
   ```

2. **Offline Migration Validation**
   ```bash
   # Generate SQL without executing
   alembic upgrade head --sql > migration.sql
   
   # Review before applying
   psql -f migration.sql --dry-run
   ```

3. **Branch Coverage Testing**
   - Test migrations against production database snapshots
   - Verify data integrity after each migration
   - Use `pytest-alembic` for automated testing

### Rollback Strategies

**Implementation**:
```python
# Always implement downgrade() operations
def downgrade():
    """Revert changes - REQUIRED for production"""
    op.drop_table('new_table')
    op.drop_column('existing_table', 'new_column')
```

**Production Deployment**:
1. Take database snapshot before migration
2. Deploy to staging first
3. Apply to production with `--sql` review
4. Monitor for 30 minutes before declaring success
5. Keep rollback plan ready

### Multi-Environment Deployments

**Best Practice**:
- **Development**: Auto-migrate on startup
- **Staging**: Manual migration approval via CI
- **Production**: Managed migrations with approval gates

```yaml
# .github/workflows/migrate.yml
name: Database Migration
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
      confirm:
        required: true
        description: 'Type "migrate" to confirm'
```

---

## 2. PostgreSQL Production Configuration

### Connection Pooling with PgBouncer

**Recommended Setup**:

```ini
# pgbouncer.ini
[databases]
agentos = host=postgres port=5432 dbname=agentos

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pooling modes
# transaction: Best for Django/FastAPI (default)
# session: For long-running connections
# statement: For high-concurrency short queries
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
reserve_pool_timeout = 5

# Timeouts
server_idle_timeout = 600
server_lifetime = 3600
client_idle_timeout = 0
client_login_timeout = 60

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
```

**Application Changes**:
```python
# Update DATABASE_URL
DATABASE_URL = "postgresql://user:pass@pgbouncer:6432/agentos"

# Use NullPool for migrations (PgBouncer handles pooling)
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

engine = create_engine(DATABASE_URL, poolclass=NullPool)
```

### Monitoring

**Key Metrics**:
```sql
-- Connection usage
SELECT count(*) FROM pg_stat_activity;
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- Table bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Tools**:
- **pg_stat_statements**: Built-in query statistics
- **pgwatch2**: Advanced monitoring dashboard
- **Prometheus + Grafana**: Custom metrics and alerting

### Backup Strategies

**3-2-1 Backup Rule**:
- 3 copies of data
- 2 different media types
- 1 off-site

**Implementation**:
```bash
#!/bin/bash
# backup.sh - Run via cron

BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Base backup (weekly)
pg_basebackup -D $BACKUP_DIR/base -Ft -z -P

# WAL archiving (continuous)
parchive_wal /wal_archive /backups/wal

# Offsite sync (daily)
aws s3 sync $BACKUP_DIR s3://agentos-backups/
```

**Recovery Time Objective (RTO)**: < 15 minutes
**Recovery Point Objective (RPO)**: < 5 minutes (with WAL archiving)

---

## 3. Python Project Structure

### Monorepo Patterns

**Recommended Structure**:
```
agentos/
├── pyproject.toml              # Root package config
├── packages/
│   ├── agentos-core/          # Core types, database models
│   ├── agentos-api/           # API layer
│   ├── agentos-agents/        # Agent implementations
│   └── agentos-ui/            # Streamlit frontend
├── services/
│   ├── ingestion/             # BSE poller service
│   ├── extraction/            # LLM extraction service
│   └── orchestration/         # Workflow engine
├── tools/
│   └── migrations/            # Alembic migrations
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── docker/
    ├── Dockerfile.api
    └── Dockerfile.poller
```

**Benefits**:
- Shared dependencies managed in root
- Independent service deployment
- Clear dependency boundaries
- Easier testing isolation

### Dependency Management

**Lockfile Strategy**:
```toml
# pyproject.toml
[project]
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
    "openai>=1.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest", "black", "ruff", "mypy"]
monitoring = ["prometheus-client", "opentelemetry-api"]
```

**Docker Optimization**:
```dockerfile
# Multi-stage build
FROM python:3.12-slim as builder

# Install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production image
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app

CMD ["python", "-m", "agentos"]
```

---

## 4. CI/CD Improvements

### Parallel Testing

**GitHub Actions**:
```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    test-group: [unit, integration, migration]
    
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          if [ "${{ matrix.test-group }}" == "migration" ]; then
            pytest tests/migrations/ -v
          elif [ "${{ matrix.test-group }}" == "integration" ]; then
            pytest tests/integration/ -v --db
          else
            pytest tests/unit/ -v
          fi
```

### Caching

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Docker layers
  uses: actions/cache@v4
  with:
    path: /tmp/.buildx-cache
    key: ${{ runner.os }}-buildx-${{ github.sha }}
```

### Security Scanning

```yaml
- name: Run Bandit
  run: |
    pip install bandit
    bandit -r agentos/ -f json -o bandit-report.json

- name: Dependency check
  run: |
    pip install safety
    safety check --json --output safety-report.json

- name: Secret scanning
  uses: trufflesecurity/trufflehog@main
  with:
    path: ./
    base: main
    head: HEAD
```

---

## 5. Role-Based Access Control (RBAC)

### Implementation Strategy

**Current AgentOS Model**:
```sql
-- Five roles defined in grants.sql
-- Need validation that GRANTs are applied correctly
```

**Recommended Implementation**:

1. **Database Level (Present)**:
   - `ingestion_filings_role`: INSERT-only on raw data tables
   - `extraction_role`: UPDATE on parsed documents
   - `orchestrator_role`: Full access to ops tables
   - `approval_processor_role`: Coverage table access
   - `web_role`: READ + queue INSERT

2. **Application Level (Needed)**:
   ```python
   # decorators/rbac.py
   from functools import wraps
   from fastapi import HTTPException

   def require_role(role: str):
       def decorator(func):
           @wraps(func)
           async def wrapper(*args, **kwargs):
               user = kwargs.get('current_user')
               if role not in user.roles:
                   raise HTTPException(403, "Insufficient permissions")
               return await func(*args, **kwargs)
           return wrapper
       return decorator

   # Usage
   @app.post("/filings")
   @require_role("ingestion_filings")
   async def create_filing(...):
       pass
   ```

3. **Row Level Security (RLS)** for multi-tenant scenarios:
   ```sql
   -- Enable RLS on sensitive tables
   ALTER TABLE coverage.financials ENABLE ROW LEVEL SECURITY;
   
   CREATE POLICY user_own_data ON coverage.financials
   FOR ALL TO approval_processor_role
   USING (created_by = current_setting('app.current_user_id')::int);
   ```

### Validation Tests

```python
# tests/test_rbac.py
def test_ingestion_role_cannot_delete():
    """Verify least privilege principle"""
    with db.connect("ingestion_filings_role") as conn:
        with pytest.raises(InsufficientPrivilege):
            conn.execute("DELETE FROM filings.documents")
```

---

## 6. Error Handling and Observability

### Structured Logging

**Implementation**:
```python
# agentos/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()

# Usage
logger.info(
    "filing_ingested",
    bse_code="500209",
    filing_id="DOC-2026-0001",
    processing_time_ms=1450,
)
```

### Metrics

**Prometheus Integration**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
filings_ingested = Counter('filings_ingested_total', 'Total filings ingested', ['bse_code'])
extraction_duration = Histogram('extraction_duration_seconds', 'LLM extraction time')
queue_depth = Gauge('approval_queue_depth', 'Items awaiting review')

# Usage
filings_ingested.labels(bse_code='500209').inc()
extraction_duration.observe(2.5)
```

### Distributed Tracing

**OpenTelemetry**:
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Instrument SQLAlchemy
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
SQLAlchemyInstrumentor().instrument()

# Custom spans
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("extract_financials")
def extract_financials(doc_id: str):
    # Tracked automatically
    return llm_client.extract(doc_id)
```

---

## 7. Database Seeding Strategies

### BSE Codes

**Strategy**:
```python
# scripts/seed_bse_codes.py

def seed_bse_codes():
    """Load BSE codes from public source"""
    codes = [
        ("500209", "Infosys Ltd", "Technology"),
        ("500010", "HDFC Bank Ltd", "Banking"),
        # ... 
    ]
    
    with Session() as session:
        for code, name, sector in codes:
            session.merge(Company(
                bse_code=code,
                name=name,
                sector=sector,
                is_active=True,
            ))
        session.commit()
```

### Initial Data

**Migration vs Fixture**:
- **Migrations**: Schema changes
- **Fixtures**: Reference data (BSE codes, tier rules)
- **Seed scripts**: Development/test data

**Recommendation**:
```bash
# Production - only reference data
alembic upgrade head
python -m scripts.seed_bse_codes
python -m scripts.seed_tier_rules

# Development - add sample data
python -m scripts.seed_development_data
```

---

## 8. Earnings Season Operational Patterns

### Peak Load Handling

**Scaling Strategy**:
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  poller:
    deploy:
      replicas: 5  # Scale up during earnings
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
  
  extraction:
    deploy:
      replicas: 10  # LLM workers
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
```

**Queue Management**:
```python
# During peak, switch to batch processing
class BatchProcessor:
    async def process_queue(self):
        # Pull N items at once
        items = await self.queue.get_batch(size=100)
        
        # Process in parallel with semaphore
        semaphore = asyncio.Semaphore(50)
        await asyncio.gather(*[
            self.process_with_limit(item, semaphore)
            for item in items
        ])
```

**Rate Limiting**:
```python
from asyncio import Semaphore

class RateLimitedLLMClient:
    def __init__(self, max_requests: int = 100):
        self.semaphore = Semaphore(max_requests)
    
    async def extract(self, document):
        async with self.semaphore:
            return await self._call_llm(document)
```

### Monitoring During Peak

**Alerts**:
- Queue depth > 1000 items
- Extraction latency > 5 seconds p95
- Failed extractions > 5% error rate
- Database connections > 80% capacity

---

## Immediate Action Items for AgentOS

| Priority | Action | Owner | Effort |
|----------|--------|-------|--------|
| P0 | Verify F-02 migration has all 32 tables with proper constraints | Codex | 2h |
| P1 | Add migration tests (upgrade/downgrade) | Codex | 4h |
| P1 | Implement RBAC validation tests | Codex | 3h |
| P2 | Add structured logging (structlog) | Codex | 2h |
| P2 | Configure PgBouncer connection pooling | Manual | 2h |
| P3 | Add Prometheus metrics endpoints | Codex | 4h |
| P3 | Create BSE code seed script | Codex | 2h |
| P4 | Setup Docker multi-stage builds | Codex | 3h |
| P4 | Add security scanning to CI | Codex | 2h |
| P5 | Implement RLS for multi-tenant support | Future | 8h |

---

## Key Findings Summary

1. **Alembic**: Needs automated testing and rollback verification
2. **PostgreSQL**: PgBouncer pooling essential for peak loads
3. **CI/CD**: Parallel testing and caching will speed up builds
4. **RBAC**: Application-level enforcement needed beyond DB grants
5. **Observability**: Structured logging + metrics + tracing required
6. **Seeding**: Separate reference data (migrations) from test data
7. **Earnings**: Scale horizontally with queue batch processing

---

**Research completed by**: Subagent
**For**: AgentOS Production Readiness Review
