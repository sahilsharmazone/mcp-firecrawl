import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def investigate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Try start=12 (since we found 12 items on page 1)
        # or maybe pg=2 ?
        # Let's try start=12 first as many Dealer.com sites use start index.
        url = "https://www.audiwestisland.com/fr/inventaire/occasion/?start=12"
        logger.info(f"Navigating to {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(10000) 
        
        logger.info("Searching for elements containing '$'...")
        prices = page.get_by_text("$", exact=False)
        p_count = await prices.count()
        logger.info(f"Found {p_count} elements containing '$'")
        
        if p_count > 0:
             for i in range(min(p_count, 3)):
                element = prices.nth(i)
                text = await element.text_content()
                logger.info(f"Price Element {i}: {text.strip()[:50]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate())
