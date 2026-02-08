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

def crawl_data():
    logging.info("Starting crawl job...")
    
    # Use the crawl endpoint to traverse pages
    url = "https://api.firecrawl.dev/v1/crawl"
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    schema = {
        "type": "object", 
        "properties": {
            "vehicles": {
                "type": "array", 
                "items": {
                    "type": "object", 
                    "properties": {
                        "title": {"type": "string"}, 
                        "vin": {"type": "string"}, 
                        "price": {"type": "number"}, 
                        "mileage": {"type": "number"}, 
                        "year": {"type": "number"}, 
                        "fuel_type": {"type": "string"}, 
                        "transmission": {"type": "string"}, 
                        "listing_url": {"type": "string"}, 
                        "website_url": {"type": "string"}, 
                        "exterior_color": {"type": "string"}, 
                        "engine": {"type": "string"}, 
                        "trim": {"type": "string"}
                    }
                }
            }
        }
    }

    # Crawl payload
    payload = {
        "url": TARGET_URL,
        "limit": 100, # Limit to 100 pages/items to be safe but cover 80+ cars
        "scrapeOptions": {
            "formats": ["extract"],
            "extract": {
                "schema": schema
            }
        }
    }

    try:
        # 1. Submit Crawl Job
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        job_data = response.json()
        
        if not job_data.get("success"):
            logging.error(f"Failed to start crawl job: {job_data}")
            return None
            
        job_id = job_data.get("id")
        logging.info(f"Crawl job started with ID: {job_id}. Waiting for completion...")
        
        # 2. Poll for results
        while True:
            status_url = f"https://api.firecrawl.dev/v1/crawl/{job_id}"
            status_response = requests.get(status_url, headers=headers)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            status = status_data.get("status")
            logging.info(f"Crawl Status: {status}")
            
            if status == "completed":
                # Aggregate results
                all_vehicles = []
                data_list = status_data.get("data", [])
                for item in data_list:
                    # Each item is a page result
                    extract = item.get("extract", {})
                    # Sometimes extract is nested or None
                    if extract:
                        vehicles = extract.get("vehicles", [])
                        if vehicles:
                            all_vehicles.extend(vehicles)
                
                logging.info(f"Crawl completed. Found {len(all_vehicles)} total vehicles across {len(data_list)} pages.")
                return all_vehicles
                
            elif status == "failed":
                logging.error(f"Crawl job failed: {status_data}")
                return None
            
            # Wait before polling again
            time.sleep(5)
            
    except Exception as e:
        logging.error(f"Exception during crawl: {e}")
        return None

def save_to_supabase(vehicles):
    if not vehicles:
        logging.info("No vehicles to save.")
        return

    logging.info("Saving data to Supabase...")
    
    # Add scraped_at timestamp and deduplicate based on listing_url
    current_time = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    
    unique_vehicles = {}
    for v in vehicles:
        v['scraped_at'] = current_time
        # Use listing_url as key to deduplicate. checking if it exists.
        url_key = v.get('listing_url')
        if url_key:
            unique_vehicles[url_key] = v
        else:
            # If no listing_url, just add it (or skip? likely essential)
            # using a random key or skipping. Let's skip to be safe for upsert
            pass
            
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
