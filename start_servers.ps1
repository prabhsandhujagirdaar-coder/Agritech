# AgriChain AI - Server Startup Script
# Starts both FastAPI Backend (port 8000) and Next.js Frontend (port 3000)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Starting AgriChain AI Platform...      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$mgrScript = Join-Path $scriptDir "scripts\process_manager.py"

# 1. Clean up any stale AgriChain processes on ports 8000 and 3000
Write-Host "[1/4] Auditing and clearing ports 8000 and 3000..." -ForegroundColor Yellow
if (Test-Path $pythonExe) {
    & $pythonExe $mgrScript stop --ports 8000 3000
} else {
    $activeConns = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
    foreach ($conn in $activeConns) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        } catch {}
    }
}

# 2. Start FastAPI Backend on Port 8000 in a new PowerShell window
Write-Host "`n[2/4] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$backendCmd = "`$Host.UI.RawUI.WindowTitle = 'AgriChain Backend (Port 8000)'; Set-Location '$scriptDir'; `$env:PYTHONPATH='backend'; & '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 3. Probe backend readiness
Write-Host "[3/4] Awaiting PyTorch model load and backend health readiness..." -ForegroundColor Yellow
if (Test-Path $pythonExe) {
    & $pythonExe $mgrScript wait-backend --port 8000 --timeout 35
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERROR] FastAPI backend failed to become ready. Inspect the backend window for error traces." -ForegroundColor Red
        exit 1
    }
} else {
    Start-Sleep -Seconds 10
}

# 4. Start Next.js Frontend on Port 3000 in a new PowerShell window
Write-Host "`n[4/4] Starting Next.js Web App on http://localhost:3000 ..." -ForegroundColor Green
$frontendCmd = "`$Host.UI.RawUI.WindowTitle = 'AgriChain Frontend (Port 3000)'; Set-Location '$scriptDir\apps\web'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# 5. Probe frontend readiness
if (Test-Path $pythonExe) {
    & $pythonExe $mgrScript wait-frontend --port 3000 --timeout 30
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "AgriChain AI Platform is ACTIVE and HEALTHY!" -ForegroundColor Green
Write-Host "  -> Web UI:     http://localhost:3000" -ForegroundColor White
Write-Host "  -> API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  -> Health API: http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "To stop all services later, run: .\stop_servers.ps1 or .\stop.bat" -ForegroundColor Gray
