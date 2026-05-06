"""BSE scraper using direct HTTP requests.

More reliable than API for getting corporate announcements.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BSEScraper:
    """Scrape BSE corporate announcements."""
    
    BASE_URL = "https://www.bseindia.com"
    ANNOUNCEMENTS_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.bseindia.com/",
        })
    
    def fetch_announcements(
        self,
        security_code: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch corporate announcements for a security.
        
        Args:
            security_code: BSE security code (e.g., "540222" for Laurus Labs)
            from_date: Start date (DD-MM-YYYY)
            to_date: End date (DD-MM-YYYY)
            category: Announcement category filter
            
        Returns:
            List of announcement dictionaries
        """
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y")
        if to_date is None:
            to_date = datetime.now().strftime("%d-%m-%Y")
        
        params = {
            "strCat": category or "Company",
            "strScrip": security_code,
            "strSearch": "S",
            "FromDate": from_date,
            "ToDate": to_date,
            "segment": "All",
        }
        
        logger.info(f"Fetching BSE announcements for {security_code}")
        
        try:
            response = self.session.get(
                self.ANNOUNCEMENTS_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            if isinstance(data, list):
                announcements = data
            elif isinstance(data, dict) and "Table" in data:
                announcements = data["Table"]
            else:
                announcements = []
            
            logger.info(f"Found {len(announcements)} announcements for {security_code}")
            return announcements
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch announcements: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            return []
    
    def download_pdf(self, pdf_url: str, output_path: str) -> bool:
        """Download a PDF attachment.
        
        Args:
            pdf_url: URL to download
            output_path: Where to save
            
        Returns:
            True if successful
        """
        try:
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF: {output_path} ({len(response.content)} bytes)")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF: {e}")
            return False
    
    def extract_metadata(self, announcement: dict) -> dict[str, Any]:
        """Extract normalized metadata from announcement.
        
        Returns:
            Normalized announcement dict
        """
        return {
            "news_id": str(announcement.get("NEWSID", "")),
            "headline": announcement.get("HEADLINE", ""),
            "category": announcement.get("CATEGORY", ""),
            "sub_category": announcement.get("SUB_CATEGORY", ""),
            "attachment_url": announcement.get("ATTACHMENTURL", ""),
            "news_date": announcement.get("NEWS_DT", ""),
            "posted_date": announcement.get("NEWS_DATE", ""),
            "scraped_at": datetime.now().isoformat(),
        }


def test_cohance_scraper():
    """Test scraper with Laurus Labs."""
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    scraper = BSEScraper()
    
    # Laurus Labs (Cohance)
    security_code = "540222"
    
    # Get last 10 announcements
    announcements = scraper.fetch_announcements(
        security_code=security_code,
        from_date=(datetime.now() - timedelta(days=90)).strftime("%d-%m-%Y"),
        to_date=datetime.now().strftime("%d-%m-%Y"),
    )
    
    print(f"\n{'='*60}")
    print(f"BSE Announcements for Laurus Labs (540222)")
    print(f"{'='*60}")
    print(f"Total found: {len(announcements)}\n")
    
    for i, ann in enumerate(announcements[:10], 1):
        meta = scraper.extract_metadata(ann)
        print(f"{i}. {meta['headline'][:80]}")
        print(f"   Date: {meta['news_date']}")
        print(f"   Category: {meta['category']}")
        if meta['attachment_url']:
            print(f"   PDF: {meta['attachment_url'][:60]}...")
        print()
    
    return announcements


if __name__ == "__main__":
    test_cohance_scraper()
