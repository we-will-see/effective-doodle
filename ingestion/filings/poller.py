"""BSE filings poller — fetches corporate announcements from BSE India.

S-01: Hourly polling during market hours (9am-4pm IST), 4-hourly off-hours.
Fetches new filings, downloads PDFs, stores with fingerprint-based dedup.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from sqlalchemy.orm import Session

from ingestion.filings.poller_config import BSEPollerConfig, load_config_from_env

logger = logging.getLogger(__name__)


class BSEPoller:
    """Polls BSE for new corporate announcements.
    
    Implements S-01 from backlog:
    - Hourly polling during market hours (9am-4pm IST)
    - 4-hourly polling off-hours
    - Fingerprint-based deduplication
    - Polite scraping with rate limiting
    """
    
    def __init__(self, config: Optional[BSEPollerConfig] = None):
        self.config = config or load_config_from_env()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AgentOS-BSE-Poller/1.0 (Research Data Collection)",
            "Accept": "application/json",
        })
        
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        time.sleep(1.0 / self.config.requests_per_second)
    
    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """Make a request with retries and exponential backoff."""
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                response = self.session.request(method, url, timeout=30, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                wait = self.config.retry_backoff_base ** attempt
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
        raise RuntimeError("Unreachable")
    
    def fetch_announcements(
        self,
        bse_code: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Fetch announcements for a single company.
        
        Args:
            bse_code: BSE security code (e.g., "500001")
            from_date: Start date (defaults to yesterday)
            to_date: End date (defaults to today)
            
        Returns:
            List of announcement records
        """
        if from_date is None:
            from_date = datetime.now(timezone.utc) - timedelta(days=1)
        if to_date is None:
            to_date = datetime.now(timezone.utc)
            
        from_str = from_date.strftime("%Y%m%d")
        to_str = to_date.strftime("%Y%m%d")
        
        # BSE API expects parameters
        params = {
            "strCat": "Company",
            "strScrip": bse_code,
            "strSearch": "S",
            "FromDate": from_str,
            "ToDate": to_str,
            "segment": "All",
        }
        
        logger.info(f"Fetching announcements for {bse_code} from {from_str} to {to_str}")
        
        try:
            response = self._make_request("GET", self.config.announcements_url, params=params)
            data = response.json()
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "Table" in data:
                return data["Table"]
            else:
                logger.warning(f"Unexpected response format for {bse_code}: {type(data)}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch announcements for {bse_code}: {e}")
            return []
    
    def download_pdf(self, pdf_url: str, dest_path: Path) -> bool:
        """Download a PDF file.
        
        Args:
            pdf_url: URL to download
            dest_path: Where to save
            
        Returns:
            True if successful
        """
        try:
            response = self._make_request("GET", pdf_url)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(response.content)
            logger.info(f"Downloaded PDF to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {pdf_url}: {e}")
            return False
    
    def compute_fingerprint(self, content: bytes) -> str:
        """Compute SHA256 fingerprint for deduplication."""
        return hashlib.sha256(content).hexdigest()
    
    def poll_company(self, bse_code: str, db_session: Session) -> dict[str, Any]:
        """Poll a single company for new filings.
        
        Args:
            bse_code: BSE code to poll
            db_session: Database session
            
        Returns:
            Summary of found/new/updated filings
        """
        from core.types.sqlalchemy_models import Document
        from core.utils.fingerprint import compute_fingerprint
        
        announcements = self.fetch_announcements(bse_code)
        
        found = 0
        new_count = 0
        skipped = 0
        errors = 0
        
        for ann in announcements:
            found += 1
            
            # Extract announcement metadata
            ann_id = str(ann.get("NEWSID", ""))
            title = ann.get("HEADLINE", "")
            pdf_url = ann.get("ATTACHMENTURL", "")
            ann_date_str = ann.get("NEWS_DT", "")
            category = ann.get("CATEGORY", "")
            
            if not ann_id or not pdf_url:
                logger.warning(f"Skipping announcement with missing ID/URL: {ann}")
                errors += 1
                continue
            
            # Check if already exists
            existing = db_session.query(Document).filter_by(
                source_id=ann_id,
                source="bse"
            ).first()
            
            if existing:
                logger.debug(f"Already have {ann_id}, skipping")
                skipped += 1
                continue
            
            # Download PDF
            company_dir = Path(self.config.raw_storage_path) / bse_code / datetime.now().strftime("%Y/%m/%d")
            pdf_path = company_dir / f"{ann_id}.pdf"
            
            if not self.download_pdf(pdf_url, pdf_path):
                errors += 1
                continue
            
            # Compute fingerprint
            content = pdf_path.read_bytes()
            fingerprint = compute_fingerprint(content)
            
            # Check for fingerprint collision (same content, different ID)
            existing_fp = db_session.query(Document).filter_by(
                content_hash=fingerprint
            ).first()
            
            if existing_fp:
                logger.info(f"Fingerprint collision for {ann_id} -> {existing_fp.source_id}, skipping")
                skipped += 1
                pdf_path.unlink()  # Remove duplicate
                continue
            
            # Parse date
            try:
                filed_at = datetime.strptime(ann_date_str, "%d-%b-%Y %H:%M")
                filed_at = filed_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                filed_at = datetime.now(timezone.utc)
            
            # Get company_id from coverage
            from core.types.sqlalchemy_models import Company
            company = db_session.query(Company).filter_by(bse_code=bse_code).first()
            company_id = company.id if company else None
            
            if not company_id:
                logger.warning(f"Company with BSE code {bse_code} not in coverage universe")
                continue
            
            # Create database record
            doc = Document(
                company_id=company_id,
                source="bse",
                source_id=ann_id,
                content_hash=fingerprint,
                document_type=self._classify_category(category),
                document_subtype=self._classify_subtype(title),
                filing_title=title,
                filed_at=filed_at,
                filesystem_path=str(pdf_path),
                extraction_status="pending",
                classification_status="pending",
            )
            db_session.add(doc)
            new_count += 1
            logger.info(f"Added new filing: {ann_id} - {title[:60]}")
        
        return {
            "bse_code": bse_code,
            "found": found,
            "new": new_count,
            "skipped": skipped,
            "errors": errors,
        }
    
    def _classify_category(self, category: str) -> Optional[str]:
        """Classify BSE category to document_type."""
        category_map = {
            "Result": "results",
            "Company Update": "exchange_filing",
            "Board Meeting": "board_meeting",
            "AGM/EGM": "shareholder_meeting",
            "Corporate Action": "corporate_action",
            "Analyst/Investor Meet": "investor_meeting",
            "Insider Trading": "insider_trading",
        }
        return category_map.get(category, "exchange_filing")
    
    def _classify_subtype(self, title: str) -> Optional[str]:
        """Classify title to document_subtype."""
        title_lower = title.lower()
        
        if "quarterly" in title_lower or "q1" in title_lower or "q2" in title_lower or "q3" in title_lower or "q4" in title_lower:
            return "quarterly_results"
        elif "annual" in title_lower:
            return "annual_report"
        elif "press release" in title_lower:
            return "press_release"
        elif "investor" in title_lower or "presentation" in title_lower:
            return "investor_presentation"
        elif "esg" in title_lower:
            return "esg_report"
        
        return None
    
    def poll_all(self, db_session: Session) -> list[dict[str, Any]]:
        """Poll all companies in coverage universe.
        
        Returns:
            List of per-company summaries
        """
        results = []
        
        # Load coverage universe from DB
        from core.types.sqlalchemy_models import Company
        companies = db_session.query(Company).filter(
            Company.bse_code.isnot(None)
        ).all()
        
        if not companies:
            logger.warning("No companies with bse_code found in coverage")
            return []
        
        for company in companies:
            if not company.bse_code:
                continue
            
            try:
                result = self.poll_company(company.bse_code, db_session)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to poll {company.bse_code}: {e}")
                results.append({
                    "bse_code": company.bse_code,
                    "error": str(e),
                })
        
        return results
    
    def should_poll_now(self) -> bool:
        """Determine if polling should happen now based on schedule."""
        from datetime import time as dt_time
        
        now = datetime.now(timezone.utc)
        # Convert to IST (UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        ist_now = now + ist_offset
        
        current_time = ist_now.time()
        
        # Check if market hours
        is_market_hours = (
            self.config.market_open_time <= current_time <= self.config.market_close_time
        )
        
        # TODO: Check last poll time against interval
        # For now, always return True
        return True


def run_poll(db_session: Session) -> dict[str, Any]:
    """Run a single poll cycle.
    
    Entry point for scheduled execution.
    """
    poller = BSEPoller()
    
    if not poller.should_poll_now():
        logger.info("Skipping poll based on schedule")
        return {"skipped": True}
    
    results = poller.poll_all(db_session)
    
    # Compute totals
    total_new = sum(r.get("new", 0) for r in results)
    total_found = sum(r.get("found", 0) for r in results)
    total_errors = sum(r.get("errors", 0) for r in results)
    
    summary = {
        "companies_polled": len(results),
        "total_found": total_found,
        "total_new": total_new,
        "total_errors": total_errors,
        "details": results,
    }
    
    logger.info(f"Poll complete: {total_new} new filings from {total_found} total")
    
    return summary


if __name__ == "__main__":
    # Manual run for testing
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    # Test with a specific BSE code if provided
    bse_code = sys.argv[1] if len(sys.argv) > 1 else None
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.types.sqlalchemy_models import Base
    
    db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/agentos")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    poller = BSEPoller()
    
    if bse_code:
        result = poller.poll_company(bse_code, db)
        print(json.dumps(result, indent=2, default=str))
    else:
        result = poller.poll_all(db)
        print(json.dumps(result, indent=2, default=str))
