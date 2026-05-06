"""Cohance BSE page scraper using Scrapling.

Scrapes: https://www.bseindia.com/stock-share-price/cohance-lifesciences-ltd/cohance/543064/corp-announcements
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from scrapling import Fetcher

logger = logging.getLogger(__name__)


class CohanceBSEScraper:
    """Scrape Cohance corporate announcements from BSE."""
    
    COHANCE_URL = "https://www.bseindia.com/stock-share-price/cohance-lifesciences-ltd/cohance/543064/corp-announcements"
    BASE_URL = "https://www.bseindia.com"
    
    def __init__(self):
        self.fetcher = Fetcher()
    
    def fetch_page(self) -> Optional[Any]:
        """Fetch the Cohance corporate announcements page."""
        logger.info(f"Fetching: {self.COHANCE_URL}")
        
        try:
            page = self.fetcher.get(self.COHANCE_URL)
            logger.info(f"Status: {page.status}, URL: {page.url}")
            
            if page.status != 200:
                logger.error(f"Failed: HTTP {page.status}")
                return None
            
            # Check if we got redirected to login
            if "login" in page.url.lower() or "showinterest" in page.url.lower():
                logger.error("Redirected to login page")
                return None
            
            return page
            
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def parse_announcements(self, page: Any) -> list[dict[str, Any]]:
        """Parse announcement data from Scrapling page.
        
        Uses Scrapling's adaptive selectors to find announcement elements.
        """
        announcements = []
        
        try:
            # Try multiple selector patterns for BSE tables
            selectors = [
                "table tbody tr",
                ".table-responsive tbody tr",
                "[class*='table'] tbody tr",
                "tr[data-announcement]",
                ".announcement-item",
            ]
            
            for selector in selectors:
                rows = page.find_all(selector)
                if rows and len(rows) > 0:
                    logger.info(f"Found {len(rows)} rows with selector: {selector}")
                    break
            else:
                logger.warning("No announcement rows found with known selectors")
                # Save HTML for debugging
                debug_path = Path("/tmp/cohance_debug.html")
                page.save(str(debug_path))
                logger.info(f"Saved debug HTML: {debug_path}")
                return []
            
            for row in rows:
                try:
                    # Extract cells
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    
                    # Parse based on typical BSE structure
                    # Usually: Date | Description | PDF Link
                    announcement = {
                        "date": self._extract_text(cells[0]),
                        "headline": self._extract_text(cells[1]),
                        "category": self._extract_category(cells),
                        "pdf_url": self._extract_pdf_link(row, cells),
                        "scraped_at": datetime.now().isoformat(),
                    }
                    
                    if announcement["headline"]:
                        announcements.append(announcement)
                        
                except Exception as e:
                    logger.debug(f"Failed to parse row: {e}")
                    continue
            
            return announcements
            
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            return []
    
    def _extract_text(self, element) -> str:
        """Extract clean text from element."""
        try:
            return element.get_text(strip=True)
        except:
            return ""
    
    def _extract_category(self, cells) -> str:
        """Try to extract category from cells."""
        for cell in cells:
            text = self._extract_text(cell).lower()
            if "result" in text:
                return "Results"
            if "dividend" in text or "bonus" in text:
                return "Corporate Action"
            if "board" in text or "meeting" in text:
                return "Board Meeting"
        return "Corporate Announcement"
    
    def _extract_pdf_link(self, row, cells) -> str:
        """Extract PDF attachment URL."""
        try:
            # Look for PDF links
            for cell in cells:
                links = cell.find_all("a", href=True)
                for link in links:
                    href = link.get('href', '')
                    if href and ('.pdf' in href.lower() or 'download' in href.lower()):
                        if href.startswith("http"):
                            return href
                        else:
                            return urljoin(self.BASE_URL, href)
            
            # Also check for onclick handlers
            pdf_btn = row.find("[onclick*='pdf']")
            if pdf_btn:
                onclick = pdf_btn.get('onclick', '')
                # Extract URL from onclick="window.open('url')"
                import re
                match = re.search(r"['\"](.*?\.pdf.*?)['\"]", onclick, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    if not url.startswith("http"):
                        url = urljoin(self.BASE_URL, url)
                    return url
            
            return ""
            
        except Exception as e:
            logger.debug(f"Failed to extract PDF link: {e}")
            return ""
    
    def scrape(self) -> list[dict[str, Any]]:
        """Full scrape workflow."""
        page = self.fetch_page()
        if not page:
            return []
        
        return self.parse_announcements(page)


def test_cohance():
    """Test Cohance scraping."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    scraper = CohanceBSEScraper()
    
    print("\n" + "=" * 70)
    print("Cohance BSE Scrapling Test")
    print("=" * 70 + "\n")
    
    announcements = scraper.scrape()
    
    print(f"\n{'='*70}")
    print(f"Found {len(announcements)} announcements")
    print(f"{'='*70}\n")
    
    for i, ann in enumerate(announcements[:10], 1):
        print(f"{i}. {ann['headline'][:70]}")
        print(f"   Date: {ann['date']}")
        print(f"   Category: {ann['category']}")
        if ann['pdf_url']:
            print(f"   PDF: {ann['pdf_url'][:60]}...")
        print()
    
    return announcements


if __name__ == "__main__":
    test_cohance()
