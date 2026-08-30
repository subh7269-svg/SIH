#!/usr/bin/env bash
set -e

echo "==================================================================="
echo "Starting TraceX - Bitcoin Investigation & Risk Intelligence Platform"
echo "Problem Statement: SIH26146 (Smart India Hackathon 2026)"
echo "Mode: 100% Offline-Ready"
echo "==================================================================="

# Start backend in background
echo "[1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ..."
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

# Start frontend
echo "[2/2] Launching React Vite Frontend on http://localhost:5173 ..."
cd frontend
npm run dev

# Trap exit
trap "kill $BACKEND_PID" EXIT
