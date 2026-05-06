"""Simple BSE scraper using requests with retry logic."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


class SimpleBSEScraper:
    """Simple BSE scraper with basic retry logic."""
    
    # BSE API endpoints (observed from browser network tab)
    ANNOUNCEMENTS_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    PDF_BASE_URL = "https://www.bseindia.com"
    
    def __init__(self):
        self.session = requests.Session()
        
        # Add retry logic
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Headers that mimic real browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.bseindia.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
    
    def get_announcements(
        self,
        security_code: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: str = "Company",
    ) -> list[dict[str, Any]]:
        """Get corporate announcements for a security.
        
        Args:
            security_code: BSE security code (e.g., "540222")
            from_date: DD-MM-YYYY format
            to_date: DD-MM-YYYY format
            category: Announcement category
            
        Returns:
            List of announcement dicts
        """
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=90)).strftime("%d-%m-%Y")
        if to_date is None:
            to_date = datetime.now().strftime("%d-%m-%Y")
        
        params = {
            "strCat": category,
            "strScrip": security_code,
            "strSearch": "S",
            "FromDate": from_date,
            "ToDate": to_date,
            "segment": "All",
        }
        
        logger.info(f"Fetching BSE: {security_code} from {from_date} to {to_date}")
        
        try:
            response = self.session.get(
                self.ANNOUNCEMENTS_API,
                params=params,
                timeout=30,
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Handle different response structures
                    if isinstance(data, list):
                        announcements = data
                    elif isinstance(data, dict):
                        if "Table" in data:
                            announcements = data["Table"]
                        elif "data" in data:
                            announcements = data["data"]
                        else:
                            announcements = list(data.values()) if data else []
                    else:
                        announcements = []
                    
                    logger.info(f"Found {len(announcements)} announcements")
                    return announcements
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response")
                    return []
            else:
                logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []
    
    def extract_meta(self, ann: dict) -> dict[str, Any]:
        """Extract normalized metadata."""
        return {
            "news_id": str(ann.get("NEWSID", "")),
            "headline": ann.get("HEADLINE", "").strip(),
            "category": ann.get("CATEGORY", ""),
            "date": ann.get("NEWS_DT", ""),
            "attachment": ann.get("ATTACHMENTURL", ""),
        }


def test_laurus():
    """Test with Laurus Labs."""
    logging.basicConfig(level=logging.INFO)
    
    scraper = SimpleBSEScraper()
    
    print(f"\n{'='*60}")
    print("Testing BSE scraper for Laurus Labs (540222)")
    print(f"{'='*60}\n")
    
    announcements = scraper.get_announcements(
        security_code="540222",
        from_date=(datetime.now() - timedelta(days=180)).strftime("%d-%m-%Y"),
    )
    
    print(f"\nTotal announcements: {len(announcements)}\n")
    
    for i, ann in enumerate(announcements[:10], 1):
        meta = scraper.extract_meta(ann)
        print(f"{i}. {meta['headline'][:70]}")
        print(f"   Date: {meta['date']}")
        print(f"   Category: {meta['category']}")
        if meta['attachment']:
            print(f"   PDF: {meta['attachment'][:50]}...")
        print()
    
    return announcements


if __name__ == "__main__":
    test_laurus()
