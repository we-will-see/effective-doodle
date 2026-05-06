# Daily Briefing Delivery Channel

**Status:** Decided (Option 3 - Sensible Default)
**Channel:** Email (Primary)
**Date:** 2026-05-06
**Owner:** Automatic Decision

## Decision

Daily briefing delivered via **Email** at 7:00 AM IST.

## Rationale

Email chosen as v1 channel because:
1. **Simplest to implement** — No external integrations needed
2. **Reliable** — SMTP is mature, well-understood
3. **Async consumption** — Analyst reviews when ready
4. **Archivable** — Easy to search historical briefings
5. **No lock-in** — Easy to add Slack/UI later

## Implementation

### Configuration

Environment variables:
```bash
BRIEFING_SMTP_HOST=smtp.gmail.com
BRIEFING_SMTP_PORT=587
BRIEFING_SMTP_USER=your-email@gmail.com
BRIEFING_SMTP_PASS=app-specific-password
BRIEFING_RECIPIENT=your-email@gmail.com
```

### Content Format

**Subject:** `[AgentOS Briefing] <YYYY-MM-DD> — <n> items requiring attention`

**Body:**
- Summary dashboard (3-5 key metrics)
- New filings overnight
- Theses needing review
- Queue items pending approval
- Today's catalysts

### Schedule

- **Delivery:** 7:00 AM IST daily
- **Cron:** `0 7 * * *` (server TZ)

## Future Options

| Channel | When | Effort |
|---------|------|--------|
| Slack | Post-slice if email insufficient | Medium |
| In-UI dashboard | F-08 (Streamlit) | Low (same build) |
| WhatsApp | Deferred indefinitely | High |

## Acceptance Criteria

- [ ] Email sent at 7:00 AM IST ± 5 minutes
- [ ] Contains actionable summary (not full dumps)
- [ ] Links to approval queue for items needing review
- [ ] No sensitive data in subject lines
- [ ] Responsive design for mobile reading

## ADR Reference

- ADR-029 — Daily briefing delivery channel (placeholder resolved)
