# Audi West Island Scraper (Python)

This project automates the daily scraping of used car inventory from Audi West Island and saves it to a Supabase database.

## Prerequisites

1.  **Python 3.x** installed.
2.  **Supabase Project** set up (Table `vehicles` created using `schema.sql`).

## Installation

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  The `.env` file is already created with your credentials. Ensure it contains:
    -   `FIRECRAWL_API_KEY`
    -   `SUPABASE_URL`
    -   `SUPABASE_KEY`

## Usage

1.  Run the script:
    ```bash
    python main.py
    ```

2.  The script will start a scheduler that runs the scraper every day at **00:00** (midnight).
3.  Keep the terminal open or run the script in the background (e.g., using `nohup`, `screen`, or a system service).

## Database Schema

Refer to `schema.sql` to create the necessary table in Supabase.

## Customization

-   **Schedule**: Modify the `schedule.every().day.at("00:00")` line in `main.py` to change the time.
-   **Extraction Schema**: valid JSON schema is defined in the `scrape_data` function in `main.py`.
