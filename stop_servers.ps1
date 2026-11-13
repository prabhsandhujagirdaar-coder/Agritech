# AgriChain AI - Server Shutdown Script
# Terminates processes listening on ports 8000 (Backend) and 3000 (Frontend)

Write-Host "Stopping AgriChain AI services on ports 8000 and 3000..." -ForegroundColor Yellow

$stopped = 0
$conns = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($conn in $conns) {
        try {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "Stopping $($proc.ProcessName) (PID $($proc.Id)) on port $($conn.LocalPort)..." -ForegroundColor Red
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        } catch {}
    }
}

if ($stopped -gt 0) {
    Write-Host "All AgriChain AI services stopped successfully." -ForegroundColor Green
} else {
    Write-Host "No active AgriChain AI services were found on ports 8000 or 3000." -ForegroundColor Gray
}

