"""Cohance scraper using Playwright with JavaScript execution.

Handles SPAs by waiting for content to load after initial page load.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class CohancePlaywrightScraper:
    """Scrape Cohance using Playwright with JS execution."""
    
    COHANCE_URL = "https://www.bseindia.com/stock-share-price/cohance-lifesciences-ltd/cohance/543064/corp-announcements"
    
    async def scrape(self, timeout: int = 30) -> List[dict[str, Any]]:
        """Scrape Cohance announcements using real browser.
        
        Args:
            timeout: Seconds to wait for content to load
            
        Returns:
            Announcements list
        """
        announcements = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            )
            
            page = await context.new_page()
            
            try:
                logger.info(f"Navigating to {self.COHANCE_URL}")
                
                # Navigate and wait for page load
                await page.goto(self.COHANCE_URL, wait_until="networkidle")
                
                # Wait for announcements to load (JavaScript-rendered)
                # Try multiple strategies
                logger.info("Waiting for content to load...")
                
                # Strategy 1: Wait for table with announcements
                try:
                    await page.wait_for_selector("table tbody tr", timeout=timeout*1000)
                    logger.info("Found table rows")
                except:
                    logger.warning("No table rows found, trying other selectors...")
                    
                    # Strategy 2: Wait for any content
                    await page.wait_for_timeout(5000)
                
                # Get page HTML after JS execution
                html = await page.content()
                logger.info(f"Page loaded, HTML size: {len(html)}")
                
                # Extract using Playwright's built-in selectors
                # Try multiple selector patterns
                selectors_to_try = [
                    "table tbody tr",
                    "table tbody tr:not(:first-child)",
                    "#announcementTable tbody tr",
                    "[class*='announcement']",
                    "[class*='corporate'] tr",
                    ".bse-table tbody tr",
                    "data-testid*='announcement'",
                ]
                
                rows = []
                for selector in selectors_to_try:
                    rows = await page.query_selector_all(selector)
                    if rows:
                        logger.info(f"Found {len(rows)} elements with: {selector}")
                        break
                
                if not rows:
                    logger.warning("No announcement rows found")
                    # Save screenshot for debugging
                    await page.screenshot(path="/tmp/cohance_screenshot.png")
                    logger.info("Screenshot saved: /tmp/cohance_screenshot.png")
                
                # Extract data from rows
                for row in rows[:50]:  # Limit to 50
                    try:
                        # Try to get all cells
                        cells = await row.query_selector_all("td")
                        
                        if len(cells) >= 2:
                            ann = {
                                "date": await self._get_text(cells[0]),
                                "headline": await self._get_text(cells[1]),
                                "category": await self._detect_category(cells),
                                "pdf_url": await self._extract_pdf_link(row, cells),
                                "scraped_at": datetime.now().isoformat(),
                            }
                            
                            if ann["headline"] and ann["date"]:
                                announcements.append(ann)
                                
                    except Exception as e:
                        logger.debug(f"Row parse error: {e}")
                
            except Exception as e:
                logger.error(f"Scrape failed: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                await context.close()
                await browser.close()
        
        return announcements
    
    async def _get_text(self, element) -> str:
        """Extract text from element."""
        try:
            text = await element.inner_text()
            return text.strip() if text else ""
        except:
            return ""
    
    async def _detect_category(self, cells) -> str:
        """Detect category from cell content."""
        for cell in cells:
            text = (await self._get_text(cell)).lower()
            if "result" in text:
                return "Results"
            if "dividend" in text or "bonus" in text or "split" in text:
                return "Corporate Action"
            if "board" in text:
                return "Board Meeting"
        return "Corporate Announcement"
    
    async def _extract_pdf_link(self, row, cells) -> str:
        """Extract PDF download link."""
        try:
            # Look for links with PDF or download
            links = await row.query_selector_all("a[href]")
            for link in links:
                href = await link.get_attribute("href")
                onclick = await link.get_attribute("onclick")
                
                if href and ".pdf" in href.lower():
                    return href if href.startswith("http") else f"https://www.bseindia.com{href}"
                
                if onclick and "pdf" in onclick.lower():
                    # Extract URL from onclick="window.open('url')"
                    import re
                    match = re.search(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick, re.I)
                    if match:
                        url = match.group(1)
                        if not url.startswith("http"):
                            url = f"https://www.bseindia.com{url}"
                        return url
            
            return ""
            
        except Exception as e:
            logger.debug(f"PDF extract error: {e}")
            return ""


async def main():
    """Test Cohance scraper."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("\n" + "=" * 70)
    print("Cohance Playwright Scraping Test")
    print("=" * 70 + "\n")
    
    scraper = CohancePlaywrightScraper()
    announcements = await scraper.scrape()
    
    print(f"\n{'='*70}")
    print(f"Total: {len(announcements)} announcements")
    print(f"{'='*70}\n")
    
    for i, ann in enumerate(announcements[:10], 1):
        print(f"{i}. {ann['headline'][:70]}")
        print(f"   Date: {ann['date']}")
        print(f"   Category: {ann['category']}")
        if ann['pdf_url']:
            print(f"   PDF: {ann['pdf_url'][:60]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
