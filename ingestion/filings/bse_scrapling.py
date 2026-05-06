"""BSE scraper using Scrapling for robust extraction.

Scrapling is resilient to DOM changes using AST-based selectors.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from scrapling import Fetcher

logger = logging.getLogger(__name__)


class BSEScraplingScraper:
    """Scrape BSE using Scrapling for resilient extraction."""
    
    BASE_URL = "https://www.bseindia.com"
    CORP_ANN_URL = "https://www.bseindia.com/corpann/indices.html"
    
    def __init__(self):
        self.fetcher = Fetcher(stealth=True)
        self.session = None
    
    def fetch_corporate_announcements(
        self,
        security_code: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch corporate announcements for a security.
        
        Args:
            security_code: BSE security code (e.g., "540222" for Laurus)
            from_date: Start date (DD-MM-YYYY)
            to_date: End date (DD-MM-YYYY)
            
        Returns:
            List of announcement dicts
        """
        from scrapling import Fetcher
        
        # BSE uses POST with query params
        url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
        
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y")
        if to_date is None:
            to_date = datetime.now().strftime("%d-%m-%Y")
        
        params = {
            "strCat": "Company",
            "strScrip": security_code,
            "strSearch": "S",
            "FromDate": from_date,
            "ToDate": to_date,
            "segment": "All",
        }
        
        logger.info(f"Fetching BSE announcements for {security_code}")
        
        try:
            # Use Fetcher with stealth mode
            page = self.fetcher.fetch(
                url,
                params=params,
                stealth=True,
            )
            
            # Parse JSON response
            data = json.loads(page.text)
            
            # Extract announcements from response structure
            if isinstance(data, list):
                announcements = data
            elif isinstance(data, dict) and "Table" in data:
                announcements = data["Table"]
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                announcements = []
            
            logger.info(f"Found {len(announcements)} announcements for {security_code}")
            return announcements
            
        except Exception as e:
            logger.error(f"Failed to fetch announcements: {e}")
            return []
    
    def extract_announcement_data(self, announcement: dict) -> dict[str, Any]:
        """Extract normalized data from BSE announcement.
        
        Args:
            announcement: Raw announcement dict from BSE API
            
        Returns:
            Normalized announcement dict
        """
        return {
            "news_id": str(announcement.get("NEWSID", "")),
            "headline": announcement.get("HEADLINE", "").strip(),
            "category": announcement.get("CATEGORY", ""),
            "sub_category": announcement.get("SUB_CATEGORY", ""),
            "attachment_name": announcement.get("ATTACHMENTNAME", ""),
            "attachment_url": announcement.get("ATTACHMENTURL", ""),
            "news_date": announcement.get("NEWS_DT", ""),
            "news_date_time": announcement.get("NEWS_DATE", ""),
            "dissemination_time": announcement.get("DISSEMINATION_TIME", ""),
            "scraped_at": datetime.now().isoformat(),
        }
    
    def download_pdf(self, announcement: dict, output_dir: Path) -> Optional[Path]:
        """Download PDF attachment for announcement.
        
        Args:
            announcement: Announcement dict with ATTACHMENTURL
            output_dir: Where to save
            
        Returns:
            Path to downloaded file or None
        """
        attachment_url = announcement.get("ATTACHMENTURL", "")
        if not attachment_url:
            logger.warning("No attachment URL in announcement")
            return None
        
        news_id = str(announcement.get("NEWSID", ""))
        
        if attachment_url.startswith("/"):
            full_url = f"https://www.bseindia.com{attachment_url}"
        else:
            full_url = attachment_url
        
        output_path = output_dir / f"{news_id}.pdf"
        
        try:
            page = self.fetcher.fetch(full_url, stealth=True)
            
            if page.status == 200:
                output_path.write_bytes(page.body)
                logger.info(f"Downloaded: {output_path} ({len(page.body)} bytes)")
                return output_path
            else:
                logger.error(f"Failed to download: HTTP {page.status}")
                return None
                
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None


def test_cohance():
    """Test with Laurus Labs."""
    from pathlib import Path
    
    logging.basicConfig(level=logging.INFO)
    
    scraper = BSEScraplingScraper()
    
    # Laurus Labs
    security_code = "540222"
    
    print(f"\n{'='*60}")
    print(f"Fetching BSE announcements for Laurus Labs ({security_code})")
    print(f"{'='*60}\n")
    
    # Get last 30 days
    announcements = scraper.fetch_corporate_announcements(
        security_code=security_code,
        from_date=(datetime.now() - timedelta(days=90)).strftime("%d-%m-%Y"),
        to_date=datetime.now().strftime("%d-%m-%Y"),
    )
    
    print(f"\nFound {len(announcements)} announcements\n")
    
    # Create storage directory
    storage = Path(f"/data/raw/bse/{security_code}")
    storage.mkdir(parents=True, exist_ok=True)
    
    # Extract and download
    for i, ann in enumerate(announcements[:10], 1):
        data = scraper.extract_announcement_data(ann)
        
        print(f"{i}. {data['headline'][:70]}")
        print(f"   Date: {data['news_date']}")
        print(f"   Category: {data['category']}")
        
        if data['attachment_url']:
            print(f"   PDF URL: {data['attachment_url'][:50]}...")
            # Uncomment to download:
            # pdf_path = scraper.download_pdf(ann, storage)
        print()
    
    return announcements


if __name__ == "__main__":
    test_cohance()
