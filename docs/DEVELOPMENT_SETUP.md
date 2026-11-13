# AgriChain AI — Development Setup & Operations Runbook

## 1. Prerequisites

Before setting up AgriChain AI, ensure you have the following installed on your machine:

- **Operating System**: Windows 10/11, Ubuntu 22.04+, or macOS
- **Python**: 3.10, 3.11, 3.12, or 3.13 (Python 3.13.7 verified with CUDA 12.8)
- **Node.js**: v18.0.0 or higher (v22.19.0 verified)
- **npm**: v9.0.0 or higher
- **Git & Git LFS**: Ensure `git-lfs` is installed (`git lfs version`)
- **GPU (Optional)**: NVIDIA CUDA-capable GPU (RTX 3050/4050 or higher recommended for accelerated CNN inference; CPU fallback supported automatically)

---

## 2. Repository Setup

```bash
# 1. Clone the repository
git clone https://github.com/prabhsandhujagirdaar-coder/Agritech.git
cd Agritech

# 2. Pull large model weights via Git LFS
git lfs pull
```

---

## 3. Python Virtual Environment & Backend Setup

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install PyTorch with CUDA support (or CPU version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# Install backend dependencies
pip install -r backend/requirements.txt
```

---

## 4. Frontend Web App Setup

```bash
cd apps/web
npm install
cd ../..
```

---

## 5. Environment Configuration

Copy the sample environment templates:

```powershell
# Root template
Copy-Item .env.example .env

# Web dashboard template
Copy-Item apps/web/.env.example apps/web/.env.local
```

The default values connect the Next.js frontend on `http://localhost:3000` to the FastAPI backend on `http://127.0.0.1:8000`.

---

## 6. Running Locally

### Option A: One-Click Launch (Recommended for Windows)

In the root directory, run:
```cmd
.\start.bat
```
This script frees ports 8000 and 3000, launches FastAPI in one titled window, launches Next.js in another, and initializes the environment cleanly.

To stop both services:
```cmd
.\stop.bat
```

### Option B: PowerShell Automation Script
```powershell
powershell -ExecutionPolicy Bypass -File .\start_servers.ps1
```
To stop:
```powershell
powershell -ExecutionPolicy Bypass -File .\stop_servers.ps1
```

### Option C: Manual Terminal Windows

**Terminal 1 — FastAPI Backend**:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation available at: `http://127.0.0.1:8000/docs`

**Terminal 2 — Next.js Frontend**:
```powershell
cd apps/web
npm run dev
```
Web Application available at: `http://localhost:3000`

---

## 7. Verification & Test Execution

Run the full verification suite to validate system integrity:

```powershell
$env:PYTHONPATH="backend"

# 1. Unit & inventory tests
.\.venv\Scripts\python.exe backend/tests/test_inventory.py

# 2. Authoritative shipment routing test
.\.venv\Scripts\python.exe scripts/verify_shipment_routing.py

# 3. Selected shipment sync & map focus test
.\.venv\Scripts\python.exe scripts/verify_shipment_sync_and_map_focus.py

# 4. Simulation route integrity & corridor traversal test
.\.venv\Scripts\python.exe scripts/verify_simulation_route_integrity.py

# 5. Frontend unit tests & linter
npm --prefix apps/web test
npm --prefix apps/web run lint
```
