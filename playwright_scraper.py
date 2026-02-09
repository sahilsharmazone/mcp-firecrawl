import asyncio
from playwright.async_api import async_playwright
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_number(text):
    """Remove all non-digit characters except decimal point"""
    if not text:
        return None
    # Remove all whitespace (including non-breaking spaces \xa0) and non-numeric chars
    cleaned = re.sub(r'[^\d.]', '', text.replace('\xa0', '').replace(',', ''))
    try:
        return float(cleaned) if cleaned else None
    except:
        return None

async def extract_vehicle_details(page, listing_url):
    """Navigate to a vehicle detail page and extract all available data"""
    try:
        await page.goto(listing_url, timeout=30000)
        await page.wait_for_timeout(5000)  # Wait for JS to render
        
        page_text = await page.evaluate("() => document.body.innerText")
        # Normalize whitespace (replace non-breaking spaces with regular spaces)
        page_text = page_text.replace('\xa0', ' ')
        
        data = {
            'listing_url': listing_url,
            'website_url': 'https://www.audiwestisland.com'
        }
        
        # Extract VIN (pattern: 17 alphanumeric characters)
        vin_match = re.search(r'(?:VIN|Numéro de série|No de série)[:\s]*([A-HJ-NPR-Z0-9]{17})', page_text, re.IGNORECASE)
        if vin_match:
            data['vin'] = vin_match.group(1)
        else:
            vin_pattern = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', page_text)
            if vin_pattern:
                data['vin'] = vin_pattern.group(1)
        
        # Extract Year
        year_match = re.search(r'\b(20[1-2][0-9])\b.*Audi|Audi.*\b(20[1-2][0-9])\b', page_text)
        if year_match:
            data['year'] = int(year_match.group(1) or year_match.group(2))
        else:
            year_alt = re.search(r'(?:Année|Year)[:\s]*(\d{4})', page_text, re.IGNORECASE)
            if year_alt:
                data['year'] = int(year_alt.group(1))
        
        # Extract Title
        title_match = re.search(r'(20[1-2][0-9]\s+Audi\s+[A-Za-z0-9\-\s]+)', page_text)
        if title_match:
            data['title'] = title_match.group(1).strip()[:100]  # Limit length
        
        # Extract Price - handle all whitespace types
        price_match = re.search(r'(\d[\d\s\xa0,]*)\s*\$|\$\s*(\d[\d\s\xa0,]*)', page_text)
        if price_match:
            price_str = price_match.group(1) or price_match.group(2)
            data['price'] = clean_number(price_str)
        
        # Extract Mileage
        mileage_match = re.search(r'(\d[\d\s\xa0]*)\s*(?:km|Kilomètres|Kilométrage)', page_text, re.IGNORECASE)
        if mileage_match:
            data['mileage'] = clean_number(mileage_match.group(1))
        
        # Extract Fuel Type
        fuel_patterns = ['Essence', 'Diesel', 'Électrique', 'Hybride', 'Gasoline', 'Electric', 'Hybrid']
        for fuel in fuel_patterns:
            if fuel.lower() in page_text.lower():
                data['fuel_type'] = fuel
                break
        
        # Extract Transmission
        if 'automatique' in page_text.lower() or 'automatic' in page_text.lower():
            data['transmission'] = 'Automatique'
        elif 'manuelle' in page_text.lower() or 'manual' in page_text.lower():
            data['transmission'] = 'Manuelle'
        
        # Extract Exterior Color
        color_match = re.search(r'(?:Couleur extérieure|Exterior Color|Couleur)[:\s]*([A-Za-zÀ-ÿ\s]+?)(?:\n|,|$)', page_text, re.IGNORECASE)
        if color_match:
            data['exterior_color'] = color_match.group(1).strip()[:50]
        
        # Extract Engine
        engine_match = re.search(r'(?:Moteur|Engine)[:\s]*([^\n]{3,50})', page_text, re.IGNORECASE)
        if engine_match:
            data['engine'] = engine_match.group(1).strip()
        else:
            engine_alt = re.search(r'(\d+[.,]\d+\s*L|\d+\s*cylindres?)', page_text, re.IGNORECASE)
            if engine_alt:
                data['engine'] = engine_alt.group(1).strip()
        
        # Extract Trim
        trim_patterns = ['Technik', 'Komfort', 'Progressiv', 'Premium', 'Sport', 'S line', 'Quattro']
        for trim in trim_patterns:
            if trim.lower() in page_text.lower():
                data['trim'] = trim
                break
        
        return data
        
    except Exception as e:
        logger.warning(f"Error extracting details from {listing_url}: {e}")
        return {'listing_url': listing_url, 'website_url': 'https://www.audiwestisland.com'}


async def scrape_audi_inventory():
    """Scrape all vehicles by scrolling, then visit each detail page for complete data"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.audiwestisland.com/fr/inventaire/occasion/"
        logger.info(f"Navigating to {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(10000)
        
        # Scroll and click Load More to get all vehicle URLs
        all_vehicle_urls = set()
        max_scroll_attempts = 20
        scroll_attempt = 0
        
        while scroll_attempt < max_scroll_attempts:
            links = await page.evaluate('''() => {
                const allLinks = Array.from(document.querySelectorAll('a[href*="vehicleId"]'));
                return allLinks.map(a => a.href);
            }''')
            
            new_links = set(links) - all_vehicle_urls
            all_vehicle_urls.update(links)
            
            logger.info(f"Scroll {scroll_attempt}: Found {len(new_links)} new vehicles, total: {len(all_vehicle_urls)}")
            
            if len(new_links) == 0 and scroll_attempt > 2:
                load_more = await page.query_selector('button:has-text("Voir plus"), button:has-text("Load more"), button:has-text("Afficher plus")')
                if load_more:
                    logger.info("Found 'Load More' button, clicking...")
                    try:
                        await load_more.click()
                        await page.wait_for_timeout(3000)
                        scroll_attempt -= 1
                    except:
                        pass
                else:
                    logger.info("No more content to load")
                    break
            
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            scroll_attempt += 1
        
        logger.info(f"=== Found {len(all_vehicle_urls)} vehicle URLs. Now extracting detailed data... ===")
        
        # Visit each vehicle detail page to extract complete data
        vehicles = []
        for i, vehicle_url in enumerate(all_vehicle_urls):
            logger.info(f"Extracting vehicle {i+1}/{len(all_vehicle_urls)}")
            vehicle_data = await extract_vehicle_details(page, vehicle_url)
            
            # Only add if we got meaningful data
            if vehicle_data.get('price') or vehicle_data.get('title') or vehicle_data.get('vin'):
                vehicles.append(vehicle_data)
                logger.info(f"  -> {vehicle_data.get('title', 'No title')[:40]} - ${vehicle_data.get('price', 'N/A')}")
            else:
                logger.warning(f"  -> No data extracted")
            
            await page.wait_for_timeout(500)
        
        await browser.close()
        
        logger.info(f"Extracted complete data for {len(vehicles)} vehicles")
        return vehicles


if __name__ == "__main__":
    vehicles = asyncio.run(scrape_audi_inventory())
    print(f"\n=== SCRAPED {len(vehicles)} VEHICLES ===")
    for i, v in enumerate(vehicles[:3]):
        print(f"\n{i+1}. {v.get('title', 'No title')}")
        print(f"   Price: ${v.get('price', 'N/A')}")
        print(f"   VIN: {v.get('vin', 'N/A')}")
        print(f"   Year: {v.get('year', 'N/A')}")
        print(f"   Mileage: {v.get('mileage', 'N/A')} km")
        print(f"   Fuel: {v.get('fuel_type', 'N/A')}")
        print(f"   Transmission: {v.get('transmission', 'N/A')}")
    if len(vehicles) > 3:
        print(f"\n... and {len(vehicles) - 3} more")
