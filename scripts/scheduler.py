"""APScheduler-based job scheduler for AgentOS workflows.

Schedules:
- BSE filings poller (hourly during market hours, 4-hourly off-hours)
- Daily briefing (7am IST)
- Visible Alpha consensus pull (configurable)
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from datetime import datetime
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def setup_scheduler() -> BackgroundScheduler:
    """Set up the job scheduler with all workflows."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    scheduler = BackgroundScheduler()
    scheduler.configure(
        timezone="Asia/Kolkata",
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
        },
    )
    
    # Database session factory
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    
    def run_bse_poll():
        """Job wrapper for BSE poller."""
        from ingestion.filings.poller import run_poll
        
        db = Session()
        try:
            result = run_poll(db)
            db.commit()
            logger.info(f"BSE poll complete: {result}")
        except Exception as e:
            logger.error(f"BSE poll failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def run_daily_briefing():
        """Job wrapper for daily briefing."""
        from agents.daily_briefing.runner import run_daily_briefing
        
        db = Session()
        try:
            digest = run_daily_briefing(db)
            db.commit()
            
            # TODO: Deliver via channel (Telegram/email)
            # For now, log to console
            print("=" * 60)
            print(digest["markdown"])
            print("=" * 60)
            
            logger.info(f"Daily briefing complete: {digest['word_count']} words")
        except Exception as e:
            logger.error(f"Daily briefing failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    # Schedule BSE poller
    # Hourly during market hours (9am-4pm IST), 4-hourly otherwise
    # Simplified: run every hour at minute 0
    scheduler.add_job(
        run_bse_poll,
        trigger=CronTrigger(hour="9-16", minute=0),  # Market hours
        id="bse_poll_market_hours",
        name="BSE Filings Poll (Market Hours)",
        replace_existing=True,
    )
    
    # Off-hours poll every 4 hours
    scheduler.add_job(
        run_bse_poll,
        trigger=CronTrigger(hour="0,4,20", minute=0),  # Off-hours
        id="bse_poll_off_hours",
        name="BSE Filings Poll (Off Hours)",
        replace_existing=True,
    )
    
    # Schedule daily briefing at 7am IST
    scheduler.add_job(
        run_daily_briefing,
        trigger=CronTrigger(hour=7, minute=0),
        id="daily_briefing",
        name="Daily Briefing",
        replace_existing=True,
    )
    
    logger.info("Scheduler configured with jobs: "
                "BSE poll (market hours 9-16, off-hours 0/4/20), "
                "Daily briefing (7am)")
    
    return scheduler


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logger.info("Starting AgentOS scheduler")
    
    # Setup graceful shutdown
    scheduler = setup_scheduler()
    
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    # Start
    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    # Keep running
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown(None, None)


if __name__ == "__main__":
    main()
