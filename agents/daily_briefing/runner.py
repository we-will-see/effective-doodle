"""Daily Briefing Agent runner (S-08).

Produces a morning digest for the analyst covering:
- Queue depth and staleness
- Recent variance analyses
- Thesis-contradictory signals from prior 24h

Cron-scheduled at 7am IST by APScheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agents.daily_briefing.config import DailyBriefingConfig, load_config

logger = logging.getLogger(__name__)


class DailyBriefingRunner:
    """Runs the daily briefing workflow."""
    
    def __init__(self, config: Optional[DailyBriefingConfig] = None):
        self.config = config or load_config()
    
    def gather_queue_stats(self, db_session: Session) -> dict[str, Any]:
        """Gather review queue statistics.
        
        Returns counts by tier and staleness info.
        """
        from core.types.sqlalchemy_models import ReviewQueue
        
        # Queue depth by tier
        by_tier = db_session.execute(
            select(
                ReviewQueue.tier,
                func.count().label("count")
            ).where(
                ReviewQueue.status.in_(["pending", "in_review"])
            ).group_by(
                ReviewQueue.tier
            )
        ).all()
        
        tier_counts = {row.tier: row.count for row in by_tier}
        
        # Stale items (> stale_days_threshold)
        stale_since = datetime.now(timezone.utc) - timedelta(
            days=self.config.stale_days_threshold
        )
        
        stale_items = db_session.query(ReviewQueue).filter(
            ReviewQueue.created_at < stale_since,
            ReviewQueue.status.in_(["pending", "in_review"])
        ).order_by(
            ReviewQueue.priority.desc()
        ).limit(
            self.config.max_stale_items
        ).all()
        
        stale_summary = [
            {
                "id": str(item.id),
                "tier": item.tier,
                "title": item.summary[:80] if item.summary else "Untitled",
                "age_days": (datetime.now(timezone.utc) - item.created_at).days,
            }
            for item in stale_items
        ]
        
        return {
            "total_pending": sum(tier_counts.values()),
            "tier_breakdown": tier_counts,
            "stale_count": len(stale_items),
            "stale_items": stale_summary,
        }
    
    def gather_recent_variance(self, db_session: Session) -> list[dict[str, Any]]:
        """Gather recent variance analyses from past 24h.
        
        Returns variance notes that completed recently.
        """
        from core.types.sqlalchemy_models import WorkflowRun
        
        since = datetime.now(timezone.utc) - timedelta(days=1)
        
        runs = db_session.query(WorkflowRun).filter(
            WorkflowRun.workflow_name == "variance_analysis",
            WorkflowRun.completed_at >= since,
            WorkflowRun.status == "completed"
        ).order_by(
            WorkflowRun.completed_at.desc()
        ).limit(5).all()
        
        # Get associated queue items for output summary
        from core.types.sqlalchemy_models import ReviewQueue
        
        results = []
        for run in runs:
            # Find the queue item for this run
            queue_item = db_session.query(ReviewQueue).filter_by(
                workflow_run_id=run.id
            ).first()
            
            if queue_item and queue_item.output_summary:
                summary = json.loads(queue_item.output_summary) if isinstance(queue_item.output_summary, str) else queue_item.output_summary
                results.append({
                    "company": queue_item.company.display_name if queue_item.company else "Unknown",
                    "filing_title": queue_item.summary[:60] if queue_item.summary else "",
                    "status": queue_item.status,
                    "key_findings": summary.get("key_findings", [])[:3] if summary else [],
                })
        
        return results
    
    def gather_thesis_signals(self, db_session: Session) -> list[dict[str, Any]]:
        """Gather signals that may contradict active theses.
        
        Looks for:
        - Estimates that missed consensus significantly
        - Companies where our thesis assumed something but actuals diverged
        - Driver status changes
        """
        from core.types.sqlalchemy_models import Financial, Company, ThesisMeta, Driver, ConsensusPull
        
        since = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Find recent actuals vs our estimates
        signals = []
        
        # Query for recent actuals with large variances
        from sqlalchemy import Float
        
        companies = db_session.query(Company).filter(
            Company.coverage_status == "covered"
        ).all()
        
        for company in companies:
            # Check if recent actuals exist
            recent_actuals = db_session.query(Financial).filter(
                Financial.company_id == company.id,
                Financial.type == "actual",
                Financial.created_at >= since
            ).all()
            
            for actual in recent_actuals:
                # Get our estimate for this period/metric
                our_estimate = db_session.query(Financial).filter(
                    Financial.company_id == company.id,
                    Financial.period_label == actual.period_label,
                    Financial.metric == actual.metric,
                    Financial.type == "our_estimate",  # Or scenario-based
                ).first()
                
                if our_estimate and our_estimate.value != 0:
                    variance_pct = abs(
                        (actual.value - our_estimate.value) / our_estimate.value * 100
                    )
                    
                    if variance_pct > 10:  # >10% variance
                        signals.append({
                            "company": company.display_name,
                            "period": actual.period_label,
                            "metric": actual.metric,
                            "actual": float(actual.value),
                            "our_estimate": float(our_estimate.value),
                            "variance_pct": round(variance_pct, 1),
                            "signal_type": "estimate_miss",
                        })
            
            if len(signals) >= self.config.max_thesis_signals:
                break
        
        # Also check for driver status changes recently
        recent_drivers = db_session.query(Driver).filter(
            Driver.company_id.in_([c.id for c in companies]),
            Driver.updated_at >= since if hasattr(Driver, 'updated_at') else False
        ).limit(5).all()
        
        return signals[:self.config.max_thesis_signals]
    
    def generate_digest(
        self,
        queue_stats: dict[str, Any],
        recent_variance: list[dict[str, Any]],
        thesis_signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate the briefing digest.
        
        Returns structured data for rendering and a markdown summary.
        """
        # Build sections
        sections = []
        
        # Header
        today = date.today().isoformat()
        sections.append(f"# Daily Briefing — {today}\n")
        
        # Queue summary
        if self.config.include_queue_depth:
            sections.append("## Approval Queue Status")
            sections.append(f"**{queue_stats['total_pending']}** items pending")
            
            if queue_stats['tier_breakdown']:
                tier_str = ", ".join(
                    f"Tier {tier}: {count}"
                    for tier, count in sorted(queue_stats['tier_breakdown'].items())
                )
                sections.append(f"({tier_str})")
            
            sections.append("")
        
        # Stale items
        if self.config.include_stale_items and queue_stats['stale_count'] > 0:
            sections.append(f"## Stale Items ({queue_stats['stale_count']} > 3 days)")
            for item in queue_stats['stale_items']:
                sections.append(f"- **{item['title']}** — {item['age_days']} days old")
            sections.append("")
        
        # Recent variance
        if self.config.include_recent_variance and recent_variance:
            sections.append("## Recent Variance Analyses (24h)")
            for v in recent_variance:
                sections.append(f"- **{v['company']}**: {v['filing_title']}")
                if v.get('key_findings'):
                    for finding in v['key_findings']:
                        sections.append(f"  - {finding}")
            sections.append("")
        
        # Thesis signals
        if self.config.include_thesis_signals and thesis_signals:
            sections.append("## Thesis Signals")
            for signal in thesis_signals:
                if signal['signal_type'] == 'estimate_miss':
                    sections.append(
                        f"- **{signal['company']}**: {signal['metric']} variance "
                        f"{signal['variance_pct']}% (actual {signal['actual']} vs "
                        f"estimate {signal['our_estimate']})"
                    )
            sections.append("")
        
        # Footer
        sections.append("---")
        sections.append("*Review in UI or reply with 'queue' to see full queue.*")
        
        markdown = "\n".join(sections)
        
        return {
            "date": today,
            "queue_stats": queue_stats,
            "recent_variance": recent_variance,
            "thesis_signals": thesis_signals,
            "markdown": markdown,
            "word_count": len(markdown.split()),
        }
    
    def run(self, db_session: Session) -> dict[str, Any]:
        """Run the complete daily briefing workflow.
        
        Returns the digest data.
        """
        logger.info("Starting daily briefing generation")
        
        # Gather data
        queue_stats = self.gather_queue_stats(db_session)
        recent_variance = self.gather_recent_variance(db_session)
        thesis_signals = self.gather_thesis_signals(db_session)
        
        # Generate digest
        digest = self.generate_digest(queue_stats, recent_variance, thesis_signals)
        
        logger.info(
            f"Briefing complete: {len(digest['markdown'])} chars, "
            f"{digest['word_count']} words, "
            f"{queue_stats['total_pending']} pending, "
            f"{len(thesis_signals)} thesis signals"
        )
        
        return digest


def run_daily_briefing(db_session: Session) -> dict[str, Any]:
    """Entry point for scheduled execution."""
    runner = DailyBriefingRunner()
    return runner.run(db_session)


if __name__ == "__main__":
    # Manual run for testing
    import logging
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    db_url = "postgresql://localhost/agentos"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    runner = DailyBriefingRunner()
    digest = runner.run(db)
    
    print("=" * 60)
    print(digest["markdown"])
    print("=" * 60)
    print(f"\nWord count: {digest['word_count']}")
