@echo off
title AgriChain AI Launcher
echo ===================================================
echo       Starting AgriChain AI Platform...
echo ===================================================

REM 1. Safely stop only AgriChain-owned processes and release ports
echo [1/4] Auditing and clearing ports 8000 and 3000...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\process_manager.py stop --ports 8000 3000
) else (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
        echo Releasing port 8000 (PID %%a)...
        taskkill /f /t /pid %%a >nul 2>&1
    )
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
        echo Releasing port 3000 (PID %%a)...
        taskkill /f /t /pid %%a >nul 2>&1
    )
)

REM 2. Start FastAPI Backend (Port 8000) in dedicated window
echo.
echo [2/4] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "AgriChain Backend (Port 8000)" cmd /k "cd /d %~dp0 && title AgriChain Backend (Port 8000) && set PYTHONPATH=backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

REM 3. Probe backend readiness
echo.
echo [3/4] Awaiting PyTorch model load and backend health readiness...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\process_manager.py wait-backend --port 8000 --timeout 35
    if errorlevel 1 (
        echo.
        echo [ERROR] Backend failed to report healthy within 35s. Check the Backend window for error traces.
        pause
        exit /b 1
    )
) else (
    timeout /t 10 /nobreak >nul
)

REM 4. Start Next.js Frontend (Port 3000) in dedicated window
echo.
echo [4/4] Starting Next.js Web App on http://localhost:3000 ...
start "AgriChain Frontend (Port 3000)" cmd /k "cd /d %~dp0apps\web && title AgriChain Frontend (Port 3000) && npm run dev"

REM 5. Probe frontend readiness
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\process_manager.py wait-frontend --port 3000 --timeout 30
)

echo.
echo ===================================================
echo AgriChain AI Platform is ACTIVE and HEALTHY!
echo   - Web UI:      http://localhost:3000
echo   - API Swagger: http://127.0.0.1:8000/docs
echo   - Health:      http://127.0.0.1:8000/health
echo ===================================================
echo Keep the two opened service windows running.
echo To gracefully stop all services: run stop.bat
echo.
