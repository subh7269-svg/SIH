@echo off
echo ===================================================================
echo Starting TraceX - Bitcoin Investigation & Risk Intelligence Platform
echo Problem Statement: SIH26146 (Smart India Hackathon 2026)
echo Mode: 100% Offline-Ready
echo ===================================================================

echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 > nul

echo [2/2] Launching React Vite Frontend on http://localhost:5173 ...
cd frontend
start cmd /k "npm run dev"

echo.
echo TraceX is active! Open http://localhost:5173 in your browser.
echo ===================================================================
