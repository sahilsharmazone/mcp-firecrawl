import os
import pandas as pd
import joblib
import logging
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

import requests

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env")

def fetch_data():
    logging.info("Fetching data from Supabase...")
    # Fetch all vehicles using REST API
    url = f"{SUPABASE_URL}/rest/v1/vehicles?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if not data:
            logging.warning("No data found in Supabase.")
            return None
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None

def train_model():
    df = fetch_data()
    if df is None or df.empty:
        return

    logging.info(f"Data fetched: {len(df)} rows.")

    # Data Preprocessing
    # Features to use: year, mileage, fuel_type, transmission, make/model (from title?), trim
    # For simplicity in this first pass, we use: year, mileage, fuel_type, transmission, engine, trim
    
    # Target variable
    target = 'price'
    
    # Drop rows without price
    df = df.dropna(subset=[target])
    
    # Features
    numeric_features = ['year', 'mileage']
    categorical_features = ['fuel_type', 'transmission', 'exterior_color', 'trim'] # engine might be too high cardinality or dirty
    
    X = df[numeric_features + categorical_features]
    y = df[target]

    # Preprocessing Pipeline
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])

    # Model Pipeline
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
    ])

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    logging.info("Training model...")
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    logging.info(f"Model Performance:")
    logging.info(f"MAE: {mae:.2f}")
    logging.info(f"RMSE: {rmse:.2f}")
    logging.info(f"R² Score: {r2:.2f}")

    # Save model
    model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
    joblib.dump(model, model_path)
    logging.info(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
