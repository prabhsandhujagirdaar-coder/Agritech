@echo off
echo Stopping AgriChain AI services on ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Terminating PID %%a on port 8000...
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo Terminating PID %%a on port 3000...
    taskkill /f /pid %%a >nul 2>&1
)
echo All AgriChain AI services stopped.

