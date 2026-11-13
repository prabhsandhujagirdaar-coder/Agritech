@echo off
title AgriChain AI Launcher
echo ===================================================
echo       Starting AgriChain AI Platform...
echo ===================================================

REM 1. Terminate any lingering processes on ports 8000 and 3000
echo [1/3] Checking and clearing ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Releasing port 8000 (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo Releasing port 3000 (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

REM 2. Start Backend (Port 8000)
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "AgriChain Backend (Port 8000)" cmd /k "cd /d %~dp0 && set PYTHONPATH=backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM Wait 3 seconds for backend models to load
timeout /t 3 /nobreak >nul

REM 3. Start Frontend (Port 3000)
echo [3/3] Starting Next.js Web App on http://localhost:3000 ...
start "AgriChain Frontend (Port 3000)" cmd /k "cd /d %~dp0apps\web && npm run dev"

echo.
echo ===================================================
echo AgriChain AI is running!
echo   - Web UI:      http://localhost:3000
echo   - API Swagger: http://127.0.0.1:8000/docs
echo ===================================================
echo Keep the two opened windows running.
echo To stop everything later, run: stop.bat
echo.

