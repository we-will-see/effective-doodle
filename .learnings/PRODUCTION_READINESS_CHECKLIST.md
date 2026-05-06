# AgentOS Production Readiness Checklist

**Generated:** 2026-05-05
**Target:** MVP completion (F-01 to F-08, S-01 to S-09)

---

## ✅ Completed (Ready for Production)

| Item | Status | Notes |
|------|--------|-------|
| F-01 Repository scaffolding | ✅ | pyproject.toml, CI, pre-commit, Docker |
| F-02 Base migration | ✅ | 29 tables, 5 roles, 28 indexes, triggers |
| Architecture docs | ✅ | All 6 core docs are comprehensive |
| Decision log (30 ADRs) | ✅ | Solid architectural foundation |

---

## 🔄 In Progress / Needs Work

### Critical Path (Blocks Everything)

| Item | Current | Needed | Action |
|------|---------|--------|--------|
| F-02 Migration testing | Partial | Full integration tests | Add pytest fixtures, CI job |
| F-02 Role verification | SQL only | Integration tested | Write role-permission tests |
| Grant re-application | Manual | Automated on deploy | Add to deployment script |
| Constraint validation | Some | All spec constraints | Verify provenance CHECK |

### Important (Blocks Slice Phase)

| Item | Current | Needed | Action |
|------|---------|--------|--------|
| F-03 core/ types | Not started | SQLAlchemy + Pydantic | Spawn Codex |
| F-04 core/tools/ | Not started | Read tools | Spawn Codex |
| F-05 Approval queue | Not started | Processor + write tools | Spawn Codex |
| F-06 Embeddings | Not started | pgvector integration | Spawn Codex |
| F-07 Vector search | Not started | Semantic search tools | Spawn Codex |
| F-08 Streamlit UI | Not started | Queue UI + dashboards | Spawn Codex |

---

## 🔴 Blockers (Must Resolve)

### From Architecture §19 Open Questions

1. **BSE codes for 3 companies** (Cohance, Sai Life, Anthem)
   - Status: TBD
   - Blocks: DB seeding
   - Action: Research BSE codes

2. **Earnings season operating window**
   - Status: TBD  
   - Blocks: Build deadline
   - Action: Determine which FY quarter

3. **Visible Alpha integration mechanics**
   - Status: TBD
   - Blocks: S-01 filings variance workflow
   - Action: API research needed

4. **Excel named-range convention**
   - Status: TBD
   - Blocks: F-04 Excel adapter
   - Action: Document convention

5. **Daily briefing delivery channel**
   - Status: TBD
   - Blocks: F-12 acceptance
   - Action: Decide email/Slack/UI

6. **Off-VPS backup target**
   - Status: TBD
   - Blocks: Production deployment
   - Action: Choose B2/Wasabi/S3

---

## 💡 Improvements Identified

### Database / Schema
- [ ] Add migration rollback tests
- [ ] Add pgvector index tuning
- [ ] Create seed data for 8 companies
- [ ] Verify all triggers fire correctly
- [ ] Test role-based isolation

### CI/CD
- [ ] Add migration test job
- [ ] Add role verification job
- [ ] Add constraint validation job
- [ ] Container build caching
- [ ] Security scanning (bandit, safety)

### Testing
- [ ] Unit tests for core/ utilities
- [ ] Integration tests for DB
- [ ] End-to-end provenance tests
- [ ] Golden set seed (for eval harness)

### Operations
- [ ] Backup automation script
- [ ] Restore runbook
- [ ] Health check endpoint
- [ ] Monitoring/alerting setup
- [ ] Log aggregation

---

## 📊 Cost & Attention Tracking

**Current Session:**
- Tokens: ~50k in / ~300 out
- Cost: ~$0.036
- Time: 1.5 hours

**Remaining Estimate:**
- Foundation (F-03 to F-08): ~40 hours
- Slice (S-01 to S-09): ~60 hours
- Total MVP: ~100 hours (12.5 weeks @ 8 hrs/week)

---

## 🎯 Recommended Immediate Actions

### Tonight (While user sleeps)
1. ✅ Verify F-02 migration completeness vs spec
2. ✅ Add integration test scaffold
3. 🔄 Spawn Codex for F-03 (core/ types)
4. 🔄 Resolve open questions where possible

### Tomorrow (2026-05-06)
1. Review Codex output
2. Test F-03 types
3. Begin F-04 tools
4. Update decision log

### This Week
1. Complete Foundation (F-03 to F-08)
2. Seed golden set for eval harness
3. Build first agent (filings_classifier)
4. End-to-end smoke test

---

## 📝 Logged Learnings

See `.learnings/` for detailed entries:
- LRN-20260505-001: Git merge conflict verification workflow
- [Pending] Research from subagent
