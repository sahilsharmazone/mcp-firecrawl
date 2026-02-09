import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def compare_pages():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        base_url = "https://www.audiwestisland.com/fr/inventaire/occasion/"
        
        for offset in [0, 12, 24]:
            current_url = f"{base_url}?start={offset}"
            logger.info(f"=== Checking offset {offset} ===")
            
            await page.goto(current_url, timeout=60000)
            await page.wait_for_timeout(10000)
            
            # Get page content to check for total count
            content = await page.content()
            
            # Try to find total count in page
            # Look for patterns like "89 véhicules" or similar
            import re
            count_match = re.search(r'(\d+)\s*(?:véhicules?|vehicles?|résultats?)', content, re.IGNORECASE)
            if count_match:
                logger.info(f"Found count text: {count_match.group(0)}")
            
            # Find all links that look like vehicle detail pages
            links = await page.evaluate('''() => {
                const allLinks = Array.from(document.querySelectorAll('a[href*="vehicleId"]'));
                return allLinks.map(a => a.href);
            }''')
            
            unique_links = list(set(links))
            logger.info(f"Found {len(unique_links)} unique vehicle links at offset {offset}")
            
            for i, link in enumerate(unique_links[:5]):
                logger.info(f"  Vehicle {i+1}: {link}")
            
            if len(unique_links) > 5:
                logger.info(f"  ... and {len(unique_links) - 5} more")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(compare_pages())
