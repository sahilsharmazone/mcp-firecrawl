import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_all_with_scroll():
    """Scrape all vehicles by scrolling to trigger lazy loading"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.audiwestisland.com/fr/inventaire/occasion/"
        logger.info(f"Navigating to {url}")
        await page.goto(url, timeout=60000)
        
        # Wait for initial load
        await page.wait_for_timeout(10000)
        
        # Get initial vehicle count
        all_vehicle_urls = set()
        max_scroll_attempts = 20
        scroll_attempt = 0
        
        while scroll_attempt < max_scroll_attempts:
            # Extract current vehicle links
            links = await page.evaluate('''() => {
                const allLinks = Array.from(document.querySelectorAll('a[href*="vehicleId"]'));
                return allLinks.map(a => a.href);
            }''')
            
            new_links = set(links) - all_vehicle_urls
            all_vehicle_urls.update(links)
            
            logger.info(f"Scroll {scroll_attempt}: Found {len(new_links)} new vehicles, total: {len(all_vehicle_urls)}")
            
            if len(new_links) == 0 and scroll_attempt > 2:
                # No new links after scrolling, try clicking "Load More" or similar
                load_more = await page.query_selector('button:has-text("Voir plus"), button:has-text("Load more"), button:has-text("Afficher plus")')
                if load_more:
                    logger.info("Found 'Load More' button, clicking...")
                    try:
                        await load_more.click()
                        await page.wait_for_timeout(3000)
                        scroll_attempt -= 1  # Reset scroll attempts after button click
                    except:
                        pass
                else:
                    logger.info("No more content to load")
                    break
            
            # Scroll down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            scroll_attempt += 1
        
        logger.info(f"=== FINAL RESULTS ===")
        logger.info(f"Total unique vehicle URLs found: {len(all_vehicle_urls)}")
        
        # Now extract data from all vehicle cards
        vehicles = []
        seen_urls = set()
        
        # Find all "Audi" text elements to identify vehicle cards
        price_elements = await page.get_by_text("$", exact=False).all()
        logger.info(f"Found {len(price_elements)} price elements")
        
        for element in price_elements:
            try:
                text = await element.text_content()
                if not text or len(text) > 50:
                    continue
                
                # Find parent card
                card_data = await element.evaluate('''el => {
                    let p = el.parentElement;
                    while (p) {
                        if (p.innerText.includes('$') && p.innerText.includes('Audi') && 
                            (p.innerText.includes('km') || p.innerText.includes('Kilom'))) {
                            if (p.tagName === 'BODY' || p.tagName === 'HTML') return null;
                            
                            const text = p.innerText;
                            const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                            
                            let price = 0;
                            const priceMatch = text.match(/(\\d[\\d\\s,]*)\\s?\\$/) || text.match(/\\$\\s?(\\d[\\d\\s,]*)/);
                            if (priceMatch) {
                                price = parseFloat(priceMatch[1].replace(/[^0-9.]/g, '')) || 0;
                            }

                            let mileage = 0;
                            const mileageMatch = text.match(/([0-9]{1,3}(?:\\s?[0-9]{3})*)\\s?(?:km|Kilom)/i);
                            if (mileageMatch) {
                                mileage = parseInt(mileageMatch[1].replace(/\\s/g, '')) || 0;
                            }

                            let title = "Unknown Audi";
                            const titleLine = lines.find(l => l.includes('Audi'));
                            if (titleLine) title = titleLine;

                            const linkEl = p.querySelector('a');
                            const listing_url = linkEl ? linkEl.href : "";
                            
                            return {title, price, mileage, listing_url};
                        }
                        p = p.parentElement;
                    }
                    return null;
                }''')
                
                if card_data and card_data.get('listing_url') and card_data['listing_url'] not in seen_urls:
                    seen_urls.add(card_data['listing_url'])
                    vehicles.append(card_data)
                    
            except Exception as e:
                logger.warning(f"Error processing element: {e}")
        
        logger.info(f"Extracted {len(vehicles)} unique vehicles with data")
        
        await browser.close()
        return vehicles

if __name__ == "__main__":
    vehicles = asyncio.run(scrape_all_with_scroll())
    print(f"\n=== SCRAPED {len(vehicles)} VEHICLES ===")
    for i, v in enumerate(vehicles[:5]):
        print(f"{i+1}. {v['title']} - ${v['price']} - {v['mileage']}km")
    if len(vehicles) > 5:
        print(f"... and {len(vehicles) - 5} more")
