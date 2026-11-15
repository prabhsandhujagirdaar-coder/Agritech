# AgriChain AI - Server Shutdown Script
# Terminates processes listening on ports 8000 (Backend) and 3000 (Frontend)

Write-Host "Stopping AgriChain AI services on ports 8000 and 3000..." -ForegroundColor Yellow

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$mgrScript = Join-Path $scriptDir "scripts\process_manager.py"

if (Test-Path $pythonExe) {
    & $pythonExe $mgrScript stop --ports 8000 3000
} else {
    $conns = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
    if ($conns) {
        foreach ($conn in $conns) {
            try {
                $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Stopping $($proc.ProcessName) (PID $($proc.Id)) on port $($conn.LocalPort)..." -ForegroundColor Red
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
    }
}

Write-Host "[DONE] All AgriChain AI services on ports 8000 and 3000 are stopped." -ForegroundColor Green
