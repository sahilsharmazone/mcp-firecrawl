import os
import time
import json
import requests
import schedule
from dotenv import load_dotenv

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TARGET_URL = "https://www.audiwestisland.com/fr/inventaire/occasion/"

import asyncio
from playwright_scraper import scrape_audi_inventory

def crawl_data():
    logging.info("Starting crawl job using Playwright Scraper...")
    try:
        vehicles = asyncio.run(scrape_audi_inventory())
        logging.info(f"Crawl completed. Found {len(vehicles)} unique vehicles.")
        return vehicles
    except Exception as e:
        logging.error(f"Exception during crawl: {e}")
        return None

def save_to_supabase(vehicles):
    if not vehicles:
        logging.info("No vehicles to save.")
        return

    logging.info("Saving data to Supabase...")
    
    # Define all expected columns to ensure consistent keys across all records
    expected_keys = ['title', 'vin', 'price', 'mileage', 'year', 'fuel_type', 
                     'transmission', 'listing_url', 'website_url', 'exterior_color', 
                     'engine', 'trim', 'scraped_at']
    
    # Add scraped_at timestamp and deduplicate based on listing_url
    current_time = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    
    unique_vehicles = {}
    for v in vehicles:
        # Normalize: ensure all keys exist
        normalized = {}
        for key in expected_keys:
            if key == 'scraped_at':
                normalized[key] = current_time
            else:
                normalized[key] = v.get(key)  # None if missing
        
        # Use listing_url as key to deduplicate
        url_key = normalized.get('listing_url')
        if url_key:
            unique_vehicles[url_key] = normalized
            
    vehicles_to_upsert = list(unique_vehicles.values())
    
    if not vehicles_to_upsert:
        logging.info("No unique vehicles to save.")
        return

    logging.info(f"deduplicated from {len(vehicles)} to {len(vehicles_to_upsert)} unique vehicles.")


    # Add on_conflict parameter to URL for explicit UPSERT
    url = f"{SUPABASE_URL}/rest/v1/vehicles?on_conflict=listing_url"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates" 
    }

    try:
        # Batch upsert
        response = requests.post(url, headers=headers, json=vehicles_to_upsert)
        response.raise_for_status()
        logging.info("Successfully saved data to Supabase.")
    except Exception as e:
        logging.error(f"Error saving to Supabase: {e}")
        if 'response' in locals():
            logging.error(f"Response content: {response.text}")

def job():
    vehicles = crawl_data()
    if vehicles:
        save_to_supabase(vehicles)

def main():
    logging.info("Scheduler started. Job will run every day at 00:00.")
    # Run once immediately for verification
    # job()
    
    schedule.every().day.at("00:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
