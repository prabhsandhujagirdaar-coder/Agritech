# AgriChain AI - Server Startup Script
# Starts both FastAPI Backend (port 8000) and Next.js Frontend (port 3000)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Starting AgriChain AI Platform...      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

# 1. Clean up any stale processes on ports 8000 and 3000
Write-Host "[1/4] Checking ports 8000 and 3000..." -ForegroundColor Yellow
$activePorts = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
if ($activePorts) {
    Write-Host "Releasing existing ports..." -ForegroundColor DarkYellow
    foreach ($conn in $activePorts) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "  Terminated process $($conn.OwningProcess) on port $($conn.LocalPort)" -ForegroundColor Gray
        } catch {}
    }
    Start-Sleep -Seconds 1
}

# 2. Start FastAPI Backend on Port 8000 in a new PowerShell window
Write-Host "[2/4] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$backendCmd = "`$Host.UI.RawUI.WindowTitle = 'AgriChain Backend (Port 8000)'; Set-Location '$scriptDir'; `$env:PYTHONPATH='backend'; & '$scriptDir\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 3. Wait 3 seconds for backend to start up
Start-Sleep -Seconds 3

# 4. Start Next.js Frontend on Port 3000 in a new PowerShell window
Write-Host "[3/4] Starting Next.js Web App on http://localhost:3000 ..." -ForegroundColor Green
$frontendCmd = "`$Host.UI.RawUI.WindowTitle = 'AgriChain Frontend (Port 3000)'; Set-Location '$scriptDir\apps\web'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# 5. Wait for frontend to be ready
Write-Host "[4/4] Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

Write-Host "`nAgriChain AI is running!" -ForegroundColor Cyan
Write-Host "  -> Web UI:  http://localhost:3000" -ForegroundColor White
Write-Host "  -> API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "`nTo stop all services later, run: .\stop_servers.ps1 or .\stop.bat" -ForegroundColor Gray
