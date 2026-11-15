@echo off
title AgriChain AI Service Shutdown
echo ===================================================
echo     Stopping AgriChain AI Services...
echo ===================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\process_manager.py stop --ports 8000 3000
) else (
    echo Terminating processes on ports 8000 and 3000...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
        echo Terminating PID %%a on port 8000...
        taskkill /f /t /pid %%a >nul 2>&1
    )
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
        echo Terminating PID %%a on port 3000...
        taskkill /f /t /pid %%a >nul 2>&1
    )
)

echo.
echo [DONE] All AgriChain AI services on ports 8000 and 3000 are stopped.
