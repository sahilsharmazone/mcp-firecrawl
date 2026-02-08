@echo off
echo Starting Audi Inventory System...

echo Starting API Server...
start "API Server" cmd /k "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

echo Starting Dashboard...
start "Dashboard" cmd /k "cd dashboard && if not exist node_modules (echo Installing dependencies... && call npm install) && npm run dev"

echo System Started. check the popup windows.
pause
