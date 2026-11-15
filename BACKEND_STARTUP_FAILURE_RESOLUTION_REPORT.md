# AgriChain AI — Windows Backend Startup Failure (WinError 10013) Resolution Report

**Date**: 2026-11-15  
**Engineer**: Antigravity DeepMind Agent  
**Component**: FastAPI Backend Service & Windows Process/Port Lifecycle  
**Status**: **RESOLVED & VERIFIED (PASS)**

---

## 1. Executive Summary

When launching the AgriChain AI FastAPI backend via:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
the application failed immediately with:
```text
ERROR: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

A root-cause investigation revealed that a stale background Uvicorn worker process spawned from an earlier session was actively holding the `127.0.0.1:8000` socket. On Windows, Python's `asyncio` and `socket` libraries enforce `SO_EXCLUSIVEADDRUSE` by default to prevent port-hijacking exploits. When a new Uvicorn instance attempts to bind to an already-held port under `SO_EXCLUSIVEADDRUSE`, the Windows Sockets (Winsock) subsystem raises `WSAEACCES` (10013) rather than the standard `WSAEADDRINUSE` (10048).

A dedicated, safe process and port lifecycle manager (`scripts/process_manager.py`) was implemented and integrated into `start.bat`, `stop.bat`, `start_servers.ps1`, and `stop_servers.ps1`. The solution safely terminates process trees (parent + reload workers) belonging strictly to AgriChain AI, never touches unrelated workloads, and performs real HTTP readiness probes (`/health`) before declaring startup success.

---

## 2. Phase A — Diagnostic Evidence

The following PowerShell and system diagnostics were executed outside sandbox boundaries:

### 2.1 Port 8000 Listener Audit
```powershell
netstat -ano | findstr :8000
TCP    127.0.0.1:8000    0.0.0.0:0    LISTENING    32360
```
- **Finding**: Process ID `32360` was actively listening on `127.0.0.1:8000`.
- **Process Inspection**:
  ```powershell
  Get-CimInstance Win32_Process -Filter "ProcessId = 32360 or ProcessId = 32348"
  PID 32348: C:\Users\PrabSandhu\Documents\codes\Agritech_\.venv\Scripts\python.exe -m uvicorn app.main:app ...
  PID 32360: C:\Python313\python.exe (child Uvicorn reload worker)
  ```
- **Verdict**: Port 8000 was occupied by a stale, backgrounded AgriChain Uvicorn reload child process.

### 2.2 Windows Excluded Port Range Audit
```powershell
netsh int ipv4 show excludedportrange protocol=tcp
netsh int ipv6 show excludedportrange protocol=tcp
```
- **Output**:
  ```text
  Protocol tcp Port Exclusion Ranges
  Start Port    End Port
  ----------    --------
       50000       50059     *
  * - Administered port exclusions.
  ```
- **Finding**: Port 8000 is **NOT** reserved or excluded by Windows Hyper-V, WSL2, or WinNAT. Port 8000 is completely free for userland TCP binding once released.

### 2.3 Process Footprint Audit
```powershell
Get-Process python,pythonw,node -ErrorAction SilentlyContinue
```
- **Finding**: Stale Python processes were running from the local `.venv`, while stale Node.js dev processes were lingering in TCP `FIN_WAIT_1` socket teardown states on port 3000.

### 2.4 Why Winsock Returned Error 10013 (WSAEACCES)
On Windows:
1. Sockets created by Uvicorn set `SO_EXCLUSIVEADDRUSE = 1`.
2. If another process or orphaned child worker already holds `127.0.0.1:8000`, the Windows kernel prohibits address sharing and returns error `10013 (WSAEACCES)`.
3. Legacy scripts (`start.bat` / `stop.bat`) ran `taskkill /f /pid %%a` without the `/t` (tree kill) switch, which killed only the reload supervisor or only the child, leaving the other process holding the socket.

---

## 3. Phase B & C — Port Selection & Configuration Alignment

### 3.1 Port Selection
- **Selected Port**: **8000** (canonical port).
- **Reason**: Port 8000 is not excluded by Windows, matches existing client and proxy routes, and is verified completely functional once stale AgriChain processes are cleanly managed.

### 3.2 Configuration Alignment
All configuration files were verified to maintain synchronization:
- `backend/app/core/config.py`: CORS origins expanded to cover ports `3000`, `3001`, and `3002` across both `localhost` and `127.0.0.1`.
- `apps/web/.env.local`: `ML_API_URL=http://127.0.0.1:8000`, `BACKEND_API_URL=http://127.0.0.1:8000`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`.
- `apps/web/app/api/inspect/route.js`: Candidate URLs resolve dynamically with IPv4 (`127.0.0.1`) and `localhost` dual-host retry, typed in-memory `Blob` buffering, and `X-Request-ID` tracing.
- `backend/app/main.py`: Added direct `if __name__ == "__main__":` entrypoint with environment port override support and registered `/api/inspect` alias.

---

## 4. Phase D — Improved Startup & Shutdown Scripts

A dedicated process manager was created: `scripts/process_manager.py`.

### Key Features of `scripts/process_manager.py`:
1. **Workspace Process Isolation**: Verifies process `CWD`, executable path, and command-line arguments. If an unrelated process occupies port 8000 or 3000, it warns the user and **never** terminates foreign workloads.
2. **Process Tree Termination**: Calls `proc.children(recursive=True)` to kill Uvicorn reload supervisors and worker children simultaneously, preventing socket hijacking.
3. **Multi-State TCP Socket Scanning**: Scans `psutil.net_connections()` across all connection states (`LISTEN`, `FIN_WAIT`, `CLOSE_WAIT`) to prevent race conditions during port release.
4. **Real HTTP Readiness Probing**:
   - `wait-backend`: Queries `http://127.0.0.1:8000/health` until HTTP 200 with `status: "healthy"` is returned.
   - `wait-frontend`: Queries `http://localhost:3000` until HTTP 200/304 is returned.

### Updated Scripts:
- **`start.bat`**: Runs safe port cleanup, launches FastAPI in a titled window, waits for backend model load and `/health` HTTP 200 (timeout: 35s), launches Next.js in a titled window, and waits for frontend readiness.
- **`stop.bat`**: Safely terminates AgriChain services on ports 8000 and 3000 and confirms port release.
- **`start_servers.ps1`**: PowerShell equivalent with colorized logs and health probing.
- **`stop_servers.ps1`**: PowerShell equivalent for clean service shutdown.

---

## 5. Phase E — End-to-End Verification Results

### 5.1 Service Readiness
1. **FastAPI Backend (Port 8000)**:
   - Command: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Result: `INFO: Uvicorn running on http://127.0.0.1:8000` (Zero `WinError 10013`).
   - Health Probe: `http://127.0.0.1:8000/health` -> `HTTP 200 OK` (`status: healthy`, `device: cuda`).
   - Swagger Documentation: `http://127.0.0.1:8000/docs` -> `HTTP 200 OK`.
2. **Next.js Frontend (Port 3000)**:
   - Command: `npm run dev`
   - Result: `http://localhost:3000` -> `HTTP 200 OK` (Ready in 3.4s).

### 5.2 Produce Specimen Inspection Flow (`scripts/test_inspection_flow.mjs`)
Live execution against active Next.js (port 3000) and FastAPI (port 8000) servers:
```text
=================================================================
  AgriChain AI — Produce Specimen Inspection Test Suite
=================================================================

[PASS] 1. FastAPI Backend Health Check (/health)
       Details: {"status":200,"target_crop":"guava","model_available":true,"device":"cuda"}
[PASS] 2. Auto Mode: Identify Species & Inspect Produce (Guava)
       Details: {"status":200,"identified_fruit":"guava","maturity_verdict":"Mature Green","confidence":0.6618,"requestId":"insp_1794723072374_48k28l"}
[PASS] 3. Manual Mode: Guava Harvest Maturity (ResNet18)
       Details: {"status":200,"target_fruit":"guava","predicted_class":"Mature Green","confidence":0.6618}
[PASS] 4. Manual Mode: Banana Ripeness Classifier (ResNet18)
       Details: {"status":200,"target_fruit":"banana","predicted_class":"Unripe","model":"resnet18"}
[PASS] 5. Manual Mode: Apple YOLOv8n Object Detection (CC BY-NC 4.0)
       Details: {"status":200,"task_type":"object_detection","model":"yolov8n","license":"Academic / Non-Commercial Research Only (CC BY-NC 4.0)"}
[PASS] 6. Gated Mango Inspection: Honest Deficit Disclosure
       Details: {"status":200,"target_fruit":"mango","status_field":"unavailable","unavailable_reason":"Mango maturity prediction is unavailable. Awaiting validated..."}
[PASS] 7. Security & Validation: Reject Non-Image File Format
       Details: {"status":415,"expected":"415 Unsupported Media Type or 400 Bad Request","detail":"Unsupported content type 'text/plain'. Expected one of ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].","error_category":"validation"}
[PASS] 8. Validation: Reject Empty Specimen Upload
       Details: {"status":400,"error_category":"validation","detail":"No produce image file uploaded. Please upload a JPEG, PNG, or WEBP image."}

=================================================================
  VERDICT: ALL 8 INSPECTION FLOW TESTS PASSED 100%
=================================================================
```

### 5.3 Regression Test Suites
- **Backend Tests** (`pytest backend/tests/test_multifruit_inspection.py`): **10 / 10 PASSED** in 14.06s.
- **Frontend Tests** (`npm --prefix apps/web test`): **All 5 suites PASSED** (Constants, Geospatial, Phase 13.5, Phase 13.6, Role config).
- **Frontend Lint** (`npm --prefix apps/web run lint`): **0 errors**.

---

## 6. Cryptographic Model Hash Verification

All 5 frozen production checkpoints match their baseline SHA-256 hashes:

| Checkpoint File | Format / Architecture | Size | Expected SHA-256 Hash | Status |
| :--- | :--- | :---: | :--- | :---: |
| `best_guava_resnet18.pth` | PyTorch ResNet-18 | 44,796,363 B | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | **PASS (100%)** |
| `best_banana_resnet18.pth` | PyTorch ResNet-18 | 128,791,659 B | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | **PASS (100%)** |
| `best_fruit_identifier_mobilenet_v3_large.pth` | MobileNetV3-Large | 17,044,655 B | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` | **PASS (100%)** |
| `best_fruit_identifier_resnet18.pth` | PyTorch ResNet-18 | 128,800,363 B | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | **PASS (100%)** |
| `best_apple_yolov8n.pt` | Ultralytics YOLOv8n | 6,502,250 B | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` | **PASS (100%)** |

**Zero model weights were modified, retrained, or replaced.**

---

## 7. How to Run the Platform Reliably

### One-Click Startup (Recommended)
From your root folder in PowerShell or Command Prompt:
```cmd
.\start.bat
```
or in PowerShell:
```powershell
.\start_servers.ps1
```

### Manual Individual Commands
If running manually in separate terminal tabs:

**Terminal 1 — Backend (FastAPI)**:
```powershell
cd C:\Users\PrabSandhu\Documents\codes\Agritech_
.\.venv\Scripts\python.exe scripts\process_manager.py stop --ports 8000
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (Next.js)**:
```powershell
cd C:\Users\PrabSandhu\Documents\codes\Agritech_\apps\web
npm run dev
```

### Clean Shutdown
```cmd
.\stop.bat
```
*(or `.\stop_servers.ps1`)*
