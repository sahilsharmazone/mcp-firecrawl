import os
import joblib
import pandas as pd
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import the crawl function from the scraper script (assuming it's in the parent dir)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import crawl_data, save_to_supabase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# App Setup
app = FastAPI(title="Audi West Island Inventory API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
import requests

# ... (rest of imports)

# Supabase Setup (REST API)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env")

# Helper for Supabase Requests
def supabase_request(method, endpoint, params=None, json=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json)
        else:
            return None
            
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Supabase request failed: {e}")
        return None

# Load ML Model
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml', 'model.pkl')
model = None

try:
    model = joblib.load(MODEL_PATH)
    logging.info(f"ML Model loaded from {MODEL_PATH}")
except Exception as e:
    logging.warning(f"Failed to load ML model: {e}. Predictions will be unavailable.")

# Pydantic Models
class Vehicle(BaseModel):
    id: int
    title: Optional[str]
    vin: Optional[str]
    price: Optional[float]
    mileage: Optional[float]
    year: Optional[float]
    fuel_type: Optional[str]
    transmission: Optional[str]
    listing_url: Optional[str]
    website_url: Optional[str]
    exterior_color: Optional[str]
    engine: Optional[str]
    trim: Optional[str]
    scraped_at: Optional[str]

class Prediction(BaseModel):
    vehicle_id: int
    predicted_price: float
    actual_price: Optional[float]
    difference: Optional[float]

class SyncStatus(BaseModel):
    status: str
    message: str

@app.get("/vehicles", response_model=List[Vehicle])
def get_vehicles(limit: int = 100):
    """
    Fetch all vehicles from the database.
    """
    params = {
        "select": "*",
        "limit": limit
    }
    data = supabase_request("GET", "vehicles", params=params)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch vehicles")
    return data

@app.get("/vehicles/{id}", response_model=Vehicle)
def get_vehicle(id: int):
    """
    Fetch a single vehicle by ID.
    """
    params = {
        "select": "*",
        "id": f"eq.{id}"
    }
    data = supabase_request("GET", "vehicles", params=params)
    if not data:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return data[0]

@app.get("/vehicles/{id}/predict", response_model=Prediction)
def predict_price(id: int):
    """
    Predict the price of a vehicle based on its features.
    """
    if not model:
        raise HTTPException(status_code=503, detail="ML model is not available.")

    # Fetch vehicle
    params = {
        "select": "*",
        "id": f"eq.{id}"
    }
    data = supabase_request("GET", "vehicles", params=params)
    if not data:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = data[0]
    
    # Prepare features for model (Must match training columns)
    # create DataFrame with 1 row
    features = pd.DataFrame([vehicle])
    
    # Ensure correct data types (similar to training)
    # The pipeline handles encoding/scaling, but we need correct columns.
    # Training expected: year, mileage, fuel_type, transmission, exterior_color, trim
    
    # Check for missing required features
    try:
        prediction = model.predict(features)[0]
    except Exception as e:
        logging.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    return {
        "vehicle_id": id,
        "predicted_price": round(prediction, 2),
        "actual_price": vehicle.get("price"),
        "difference": round(prediction - (vehicle.get("price") or 0), 2)
    }

def run_sync_job():
    logging.info("Starting manual sync job...")
    try:
        vehicles = crawl_data()
        if vehicles:
            save_to_supabase(vehicles)
        logging.info("Manual sync job completed.")
    except Exception as e:
        logging.error(f"Manual sync failed: {e}")

@app.post("/trigger-sync", response_model=SyncStatus)
def trigger_sync(background_tasks: BackgroundTasks):
    """
    Trigger the scraper manually in the background.
    """
    background_tasks.add_task(run_sync_job)
    return {"status": "started", "message": "Scraper job has been triggered in the background."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
