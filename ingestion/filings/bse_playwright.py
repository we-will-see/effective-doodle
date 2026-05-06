"""BSE scraper using Playwright for full browser automation.

This runs a real browser to handle JavaScript-rendered content.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class BSEPlaywrightScraper:
    """Scrape BSE using Playwright browser automation."""
    
    BASE_URL = "https://www.bseindia.com"
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        )
        self.page = await self.context.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()
    
    async def fetch_announcements(
        self,
        security_code: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch corporate announcements for a security.
        
        Args:
            security_code: BSE security code (e.g., "540222")
            from_date: Start date (DD-MM-YYYY)
            to_date: End date (DD-MM-YYYY)
            
        Returns:
            List of announcements
        """
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=90)).strftime("%d-%m-%Y")
        if to_date is None:
            to_date = datetime.now().strftime("%d-%m-%Y")
        
        # Navigate to corporate announcements page
        await self.page.goto(f"{self.BASE_URL}/corporate-announcement.html")
        
        # Wait for page to load
        await self.page.wait_for_load_state("networkidle")
        
        announcements = []
        
        try:
            # The BSE website uses Angular/React - selectors may vary
            # Wait for search form
            await self.page.wait_for_selector("input[placeholder*='Security']", timeout=5000)
            
            # Fill security code
            await self.page.fill("input[placeholder*='Security']", security_code)
            
            # Fill dates if selectors exist
            from_selectors = await self.page.query_selector_all("input[type='date']")
            if len(from_selectors) >= 2:
                await from_selectors[0].fill(from_date)
                await from_selectors[1].fill(to_date)
            
            # Click search
            search_btn = await self.page.query_selector("button:has-text('Search')")
            if search_btn:
                await search_btn.click()
                
                # Wait for results
                await self.page.wait_for_timeout(3000)
                
                # Extract table data
                rows = await self.page.query_selector_all("table tr")
                for row in rows[1:]:  # Skip header
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 3:
                        announcement = {
                            "date": await cells[0].inner_text() if len(cells) > 0 else "",
                            "category": await cells[1].inner_text() if len(cells) > 1 else "",
                            "headline": await cells[2].inner_text() if len(cells) > 2 else "",
                        }
                        announcements.append(announcement)
            
            logger.info(f"Found {len(announcements)} announcements")
            
        except Exception as e:
            logger.error(f"Failed to scrape: {e}")
            # Take screenshot for debugging
            await self.page.screenshot(path="/tmp/bse_error.png")
        
        return announcements
    
    async def test_page(self):
        """Test that page loads."""
        await self.page.goto(f"{self.BASE_URL}/corporate-announcement.html")
        await self.page.wait_for_timeout(5000)
        
        title = await self.page.title()
        html_len = len(await self.page.content())
        
        await self.page.screenshot(path="/tmp/bse_page.png")
        
        print(f"Page title: {title}")
        print(f"HTML length: {html_len}")
        print(f"Screenshot saved: /tmp/bse_page.png")
        
        return title, html_len


async def main():
    """Test scraper."""
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 60)
    print("BSE Playwright Scraper Test")
    print("=" * 60 + "\n")
    
    async with BSEPlaywrightScraper() as scraper:
        print("Testing page load...")
        title, html_len = await scraper.test_page()
        
        print(f"\nTrying to fetch announcements for Laurus Labs...")
        anns = await scraper.fetch_announcements("540222")
        print(f"Found: {len(anns)}")
        
        for i, ann in enumerate(anns[:5], 1):
            print(f"{i}. {ann}")


if __name__ == "__main__":
    asyncio.run(main())
