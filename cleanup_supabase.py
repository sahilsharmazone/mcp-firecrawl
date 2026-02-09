"""
Script to clean up duplicate records in Supabase vehicles table.
Run this ONCE to remove all existing records before running the enhanced scraper.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def delete_all_vehicles():
    """Delete all records from vehicles table"""
    url = f"{SUPABASE_URL}/rest/v1/vehicles"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    
    # Delete all records (Supabase requires a filter, so we use a never-false condition)
    response = requests.delete(f"{url}?id=gt.0", headers=headers)
    
    if response.status_code in [200, 204]:
        print("✅ Successfully deleted all vehicle records from Supabase!")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    confirm = input("⚠️  This will DELETE ALL records from the vehicles table. Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        delete_all_vehicles()
    else:
        print("Cancelled.")
