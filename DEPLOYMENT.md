# Deployment Guide: Audi Inventory System

## 1. Push to GitHub
1. Initialize Git repository (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Audi Inventory System"
   ```
2. Create a new repository on GitHub.
3. Push your code:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

## 2. Deploy to Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New..."** -> **"Project"**.
2. Import your GitHub repository.
3. **Configure Settings**:
   - **Framework Preset**: Next.js (should detect automatically).
   - **Root Directory**: `./` (default).
   - **Environment Variables**: Add the variables from your `.env` file:
     - `SUPABASE_URL`
     - `SUPABASE_KEY`
     - `FIRECRAWL_API_KEY` (if you plan to run scraping from Vercel, though see note below).

4. Click **Deploy**.

### Important Notes
- **Vercel Limitations**: The scraping job (`main.crawl_data`) takes several minutes. Vercel Serverless Functions have a timeout limit (10s on free tier, 60s on Pro).
- **Recommendation**:
    - Use Vercel for the **Dashboard** and **API (Read Operations)**.
    - Run the **Scraper** (`main.py`) on a separate persistent server (like your local machine, a VP, or Render.com background worker) or use a scheduled GitHub Action.
    - The API endpoint `/trigger-sync` will likely timeout on Vercel if it waits for the job. We implemented it as a `BackgroundTask`, which might survive for a short while but isn't guaranteed for long jobs.

## 3. Local Development
- **Backend**: `uvicorn api.main:app --reload`
- **Frontend**: `cd dashboard && npm run dev`
- **Scraper**: `python main.py` (runs daily at midnight)
