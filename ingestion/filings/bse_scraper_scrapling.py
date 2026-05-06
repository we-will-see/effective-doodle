"""BSE scraper using Scrapling for anti-bot detection bypass.

Scrapling 0.4+ uses curl-cffi to mimic real browser TLS/JA3 fingerprints.
Stealth is enabled by default in the Fetcher.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from scrapling import Fetcher

logger = logging.getLogger(__name__)


class BSEScraplingFetcher:
    """Scrape BSE using Scrapling's anti-detection features."""
    
    ANNOUNCEMENTS_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    
    def __init__(self):
        # Scrapling 0.4+ Fetcher has anti-bot built-in
        self.fetcher = Fetcher()
    
    def get_announcements(
        self,
        bse_code: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict]:
        """Get corporate announcements for a security."""
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=90)).strftime("%d-%m-%Y")
        if to_date is None:
            to_date = datetime.now().strftime("%d-%m-%Y")
        
        params = {
            "strCat": "Company",
            "strScrip": bse_code,
            "strSearch": "S",
            "FromDate": from_date,
            "ToDate": to_date,
            "segment": "All",
        }
        
        logger.info(f"Fetching BSE: {bse_code}")
        
        try:
            response = self.fetcher.get(
                self.ANNOUNCEMENTS_API,
                params=params,
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if isinstance(data, dict) and "Table" in data:
                        announcements = data["Table"]
                    elif isinstance(data, list):
                        announcements = data
                    else:
                        announcements = []
                    
                    logger.info(f"Found {len(announcements)} announcements")
                    return announcements
                    
                except Exception as e:
                    logger.error(f"JSON parse failed: {e}")
                    return []
            else:
                logger.error(f"HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []
    
    def parse_announcement(self, ann: dict) -> dict:
        """Parse raw announcement."""
        return {
            "news_id": str(ann.get("NEWSID", "")),
            "headline": ann.get("HEADLINE", "").strip(),
            "category": ann.get("CATEGORY", ""),
            "date": ann.get("NEWS_DT", ""),
            "pdf_url": ann.get("ATTACHMENTURL", ""),
        }


def test_laurus():
    """Test with Laurus Labs."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    scraper = BSEScraplingFetcher()
    
    print("\n" + "=" * 60)
    print("BSE Scrapling Test - Laurus Labs (540222)")
    print("=" * 60 + "\n")
    
    announcements = scraper.get_announcements(
        bse_code="540222",
        from_date=(datetime.now() - timedelta(days=180)).strftime("%d-%m-%Y"),
    )
    
    print(f"\nTotal: {len(announcements)}\n")
    
    for i, ann in enumerate(announcements[:10], 1):
        data = scraper.parse_announcement(ann)
        print(f"{i}. {data['headline'][:70]}")
        print(f"   Date: {data['date']}")
        if data['pdf_url']:
            print(f"   PDF: {data['pdf_url'][:50]}...")
        print()


if __name__ == "__main__":
    test_laurus()
