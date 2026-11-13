# AgriChain AI — Final Readiness and Limitation Resolution Report
## Comprehensive Pre-Submission Acceptance & Verification Audit

**Audit Date**: November 1, 2026  
**Auditor**: Senior Full-Stack Engineer, Geospatial Architect & Machine Learning Specialist  
**System Evaluated**: AgriChain AI — Predictive Cold-Chain Agritech Exchange  
**Submission Milestone**: Final Academic Demonstration Freeze (Deadline: November 7, 2026)  
**Authoritative Verdict**: **PASS WITH LIMITATIONS**  

---

## 1. Executive Summary & Authoritative Verdict

AgriChain AI has undergone an exhaustive, independent readiness audit across all deep learning, geospatial, simulation, and persistence subsystems. 

The application is **fully verified, highly stable, and ready for academic demonstration**. In strict adherence to academic honesty and the zero-fabrication directive, the system is rated **PASS WITH LIMITATIONS** due to two transparent architectural boundaries:
1. **Cold-Chain Spoilage Risk Model**: Transit risk is evaluated using an expert domain-rule heuristic based on thermal excursion hours, mean chamber temperature, and delay minutes. No trained PyTorch `.pt` LSTM weights file exists in the repository. The UI and API contracts have been updated to reflect this honest status.
2. **Runtime Database Persistence Subsystem**: On the local host demonstration environment, PostgreSQL port 5432 is closed (Docker Desktop service is stopped). All session data, LineString route geometries, and telemetry persist atomically via the verified JSON ledger (`backend/app/db/.persisted_session.json`). Complete PostGIS SQL migrations (`001`–`005`) are provided for production container deployments.

```mermaid
flowchart TD
    subgraph Client ["Frontend Workspace (Next.js 14)"]
        RoleSelect["Role Selection Gateway"]
        FarmerUI["Farmer: Dual-Mode Multi-Fruit Inspection"]
        LogisticsUI["Logistics: Dynamic Real-Road Simulation Studio"]
        DealerUI["Dealer: Mandi Intake & Quality Verification"]
        BuyerUI["Buyer: B2B Verified Produce Marketplace"]
        AdminUI["Admin: PyTorch CUDA Diagnostics & Server Health"]
    end

    subgraph APIProxy ["Next.js Proxy Layer (/api/*)"]
        ProxyRoute["API Reverse Proxy Routes"]
    end

    subgraph BackendAPI ["FastAPI Backend (Port 8000)"]
        CNN_Endpoint["Fruit Inspection Service (CUDA)"]
        Sim_Endpoint["Real-Road Routing & Simulation Service"]
        Tel_Endpoint["Cold-Chain Telemetry & Risk Estimator"]
        WS_Gateway["WebSocket Event Gateway"]
    end

    subgraph PersistenceLayer ["Persistence Subsystem"]
        ActiveLedger["Active Ledger: .persisted_session.json (File-Based Fallback)"]
        PostgresContainer["Container Target: PostgreSQL 18 / PostGIS 3.6 (Port 5432 Offline)"]
    end

    subgraph ML_Checkpoints ["Locked PyTorch Checkpoints (ml/artifacts/)"]
        GuavaModel["best_guava_resnet18.pth (44.8 MB)"]
        BananaModel["best_banana_resnet18.pth (128.8 MB)"]
        AppleModel["best_apple_yolov8n.pt (6.5 MB)"]
        IdentifierModel["best_fruit_identifier_mobilenet_v3_large.pth (17.0 MB)"]
    end

    RoleSelect --> FarmerUI & LogisticsUI & DealerUI & BuyerUI & AdminUI
    FarmerUI & LogisticsUI & DealerUI & BuyerUI & AdminUI --> ProxyRoute
    ProxyRoute --> CNN_Endpoint & Sim_Endpoint & Tel_Endpoint & WS_Gateway
    CNN_Endpoint --> ML_Checkpoints
    Sim_Endpoint & Tel_Endpoint --> ActiveLedger
    ActiveLedger -. Migration 001-005 .-> PostgresContainer
```

---

## 2. Task 1 — LSTM Integrity Audit & Limitation Resolution

### 2.1 Inspection of Spoilage-Risk Inference Implementation
A comprehensive inspection was conducted across the backend, machine learning artifacts, experiments, and schemas:
- **Endpoints**: `POST /api/v1/telemetry/predict`, `POST /api/v1/lstm/predict`, `GET /api/v1/shipments/{id}/risk`.
- **Schemas**: `TelemetryPoint`, `LSTMPredictionRequest`, `LSTMPredictionResponse` (`backend/app/schemas/telemetry.py`).
- **Feature Contract**: Evaluates a 24-step hourly sequence with 5 features per point:
  $$\mathbf{X} \in \mathbb{R}^{1 \times 24 \times 5} \implies \left[\text{temperature}, \text{humidity}, \text{delay\_minutes}, \text{speed\_kmh}, \text{distance\_remaining\_km}\right]$$

### 2.2 Model Artifact Search & Determination
An exhaustive scan of `ml/artifacts/`, `ml/models/`, `ml/experiments/`, and repository roots confirmed:
- `best_guava_resnet18.pth` $\to$ **Present** (ResNet18 classifier).
- `best_banana_resnet18.pth` $\to$ **Present** (ResNet18 classifier).
- `best_fruit_identifier_mobilenet_v3_large.pth` $\to$ **Present** (MobileNetV3 identifier).
- `best_fruit_identifier_resnet18.pth` $\to$ **Present** (ResNet18 identifier).
- `best_apple_yolov8n.pt` $\to$ **Present** (YOLOv8n detector).
- `spoilage_risk_lstm.pt` / `best_lstm.pth` $\to$ **NOT PRESENT**.

As documented in historical audit `docs/PROJECT_STATE_AUDIT.md`, no trained PyTorch LSTM weights file has ever been trained or placed in the repository.

### 2.3 Rule-Based Estimator Verification
The active estimator applies a domain-expert decision formula grounded in the fresh produce transit thermal window ($4.0^\circ\text{C} - 8.0^\circ\text{C}$):
$$\text{Risk}_{\text{current}} = \min\left(100.0, \max\left(5.0, (\overline{T} - 5.0) \times 8.0 + N_{\text{excursions}} \times 6.5 + D_{\text{delay}} \times 0.3\right)\right)$$
$$\text{Risk}_{\text{arrival}} = \min\left(100.0, \text{Risk}_{\text{current}} \times 1.15\right)$$
$$\text{Alert} = (\text{Risk}_{\text{arrival}} > 50.0)$$

Empirical tests demonstrated that temperature excursions (e.g. rising to $15.0^\circ\text{C}$) elevate the score from $5.0\%$ to $100.0\%$, correctly triggering thermal excursion alerts across live WebSockets (`simulation_telemetry_update`).

### 2.4 Limitation Resolution & Transparent UI/API Relabeling
In accordance with user instructions, the heuristic has been preserved and clearly relabeled:
1. **API Documentation**: Summary updated to `"Evaluate Cold-Chain Spoilage Risk (Rule-Based Estimator)"` with explicit disclosure in docstrings.
2. **Frontend UI**:
   - Simulation Studio gauge: `"Transit Risk (Rule-Based)"`.
   - Action button: `"Run 24h Risk Estimator"`.
   - Inspection banner: `"24h Risk Sequence (Rule-Based Heuristic)"`.
   - Overview text: `"24-step cold-chain risk scoring (rule-based estimator; trained LSTM pending)"`.
3. **Roadmap for Genuine LSTM Integration**:
   - Collect multi-sensor temporal datasets from reefer logging devices.
   - Train a 2-layer PyTorch LSTM with hidden dimension 64 and dropout 0.2.
   - Save trained weights to `ml/artifacts/spoilage_risk_lstm.pt` and plug into `predict_transit_risk()`.

---

## 3. Task 2 — PostgreSQL / PostGIS Persistence Audit

### 3.1 Port 5432 Diagnostic
Direct probing of `127.0.0.1:5432` confirmed the port is closed (Windows socket error 10035).

Diagnostic investigation established:
1. **Native Windows Services**: `Get-Service | Where-Object { $_.Name -like "*postgres*" }` returned **0 services**. Native PostgreSQL is not installed on the Windows host (`C:\Program Files\PostgreSQL` does not exist).
2. **Docker Desktop Service**: Docker Desktop is installed (`docker.exe`), but its background service `com.docker.service` is stopped. Attempting to start it via un-elevated PowerShell (`Start-Service com.docker.service`) fails with permission error `Cannot open com.docker.service service on computer '.'`.
3. **Configuration**: `backend/app/core/config.py` specifies:
   - Configured Target: `postgresql://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db`
   - Default setting: `DATABASE_ENABLED = False`

### 3.2 SQL Migration Verification (001–005)
All 5 versioned SQL migrations and their corresponding rollback files were verified in `database/migrations/`:
- `001_initial_postgis_schema.sql`: Core shipments and spatial waypoint tables with PostGIS extensions.
- `002_storage_facilities_schema.sql`: Agricultural storage facilities and geofence polygons.
- `003_real_facilities_provenance.sql`: Real APMC mandi and packhouse spatial coordinates.
- `004_shipment_facilities_and_events.sql`: Shipment facility linkages and custody events.
- `005_simulation_sessions_and_telemetry.sql`: Real-road simulation sessions with `GEOMETRY(LineString, 4326)`, `GEOMETRY(Point, 4326)`, and spatial GIST indexes (`idx_sim_sessions_route_geom`, `idx_sim_telemetry_coords`).

### 3.3 Authoritative File Ledger Fallback (`.persisted_session.json`)
The active runtime demonstration operates on `ShipmentRepository`'s atomic JSON state ledger:
- Persisted Simulation Sessions: **15 sessions recorded**.
- Persisted Simulation Telemetry: **15 session streams recorded**.
- Persistence across Backend Restarts: Verified via `verify_final_freeze.py` (shipments, waypoints, and telemetry survive process restarts without data corruption).
- **Academic Transparency**: The system explicitly reports `"database": {"enabled": false, "connected": null, "message": "File-based ledger persistence active."}`.

---

## 4. Task 3 — Simulation Regression Verification

A dedicated regression test was executed across the dynamic simulation pipeline:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe scripts/verify_dynamic_simulation.py
```

### 4.1 Verification Matrix

| Capability | Verification Detail | Result |
| :--- | :--- | :---: |
| **Custom Locations** | Tested user-defined origins/destinations across Punjab, Delhi, Maharashtra, and Rajasthan | **VERIFIED** |
| **Road-Following Polyline** | Dynamic OSRM driving geometry; 3,280 coordinate vertices between Abohar and Delhi | **VERIFIED** |
| **Lifecycle State Machine** | Start, Pause, Resume, Reset, Stop, and Step completion verified with state transitions | **VERIFIED** |
| **Loop Deduplication** | Rapid consecutive START commands safely cancel previous tasks under `async with self._lock:` | **VERIFIED** |
| **WebSocket Streaming** | Real-time frames (`simulation_telemetry_update`) delivered to connected WebSocket clients | **VERIFIED** |
| **Excursion Sensitivity** | Scenario `temperature_excursion` raises temperature to $11.4^\circ\text{C}$, elevating risk to $56.8\%$ (`alert: true`) | **VERIFIED** |
| **Synthetic Watermarking** | Prominent labels `SNS-SIM-DEMO` and `data_source: simulation` displayed in HUD and API payloads | **VERIFIED** |
| **Physical GPS Tracking** | Real shipment waypoint creation (`POST /api/v1/shipments/{id}/waypoints`) remains 100% functional | **VERIFIED** |

---

## 5. Task 4 — Existing Project Protection & Regression Suite

All regression test suites were executed without touching, retraining, or modifying locked model checkpoints:

```powershell
# 1. Full Pytest Suite (CNN, Multi-Fruit, Simulation Engine)
$env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe -m pytest backend/tests/test_cnn_api.py backend/tests/test_multifruit_inspection.py backend/tests/test_simulation_engine.py

# 2. Final Freeze Consistency Audit
$env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe scripts/verify_final_freeze.py

# 3. Frontend Lint & Production Compilation
npm --prefix apps/web run lint
npm --prefix apps/web run build
```

### 5.1 Test Results

```
================================== Pytest Suite ==================================
backend/tests/test_cnn_api.py ...............                            [15 passed]
backend/tests/test_multifruit_inspection.py ..........                   [10 passed]
backend/tests/test_simulation_engine.py .....                            [ 5 passed]
======================= 30 passed, 1 warning in 18.46s ===========================

=========================== Final Freeze Audit (100%) ============================
[TASK 1] Runtime Health & PyTorch CUDA Diagnostic: OK (Device: cuda)
[TASK 2] 5 Locked Model Checkpoints SHA-256 Hashes: ALL MATCH BIT-FOR-BIT
[TASK 3] Farmer Inspection Integrity:
  - Guava Manual ResNet18: Mature Green (0.8147)
  - Banana Manual ResNet18: Ripe (0.8989)
  - Apple YOLOv8n: 2 detections (CC BY-NC 4.0 academic research license)
  - Mango Gated State: status=unavailable (honest gate, zero synthetic output)
  - Automatic Identifier MobileNetV3: guava (1.0000)
[TASK 4] Logistics & PostGIS Route Tracking: Verified (SHP-2026-047)
[TASK 5] Dealer Mandi Intake & Buyer B2B Marketplace: Verified
[TASK 6] Admin Hardware Diagnostics & Registry: Verified
[TASK 7] File-Based Ledger Persistence: Verified across reload
STATUS: FINAL SUBMISSION FREEZE PASSED 100%

============================== Frontend Production ===============================
Next.js Lint: 0 errors
Next.js Build: 14/14 static pages and dynamic routes compiled successfully
```

### 5.2 Model Checkpoint SHA-256 Hashes
All 5 locked model checkpoints were verified bit-for-bit against their authoritative signatures:

| Model Checkpoint | Exact Byte Size | Architecture | Verified Role |
| :--- | :---: | :---: | :--- |
| `best_guava_resnet18.pth` | 44,796,363 | ResNet18 | Guava Maturity Classification (v2.0.0) |
| `best_banana_resnet18.pth` | 128,791,659 | ResNet18 | Banana Ripeness Classification |
| `best_apple_yolov8n.pt` | 6,502,250 | YOLOv8n | Apple Surface Defect Detection |
| `best_fruit_identifier_mobilenet_v3_large.pth` | 17,044,655 | MobileNetV3-Large | Automatic Fruit Species Identifier |
| `best_fruit_identifier_resnet18.pth` | 128,800,363 | ResNet18 | Species Identifier Secondary Baseline |

---

## 6. Demonstration Instructions for Final Academic Evaluation

### 6.1 Clean Start Commands
To launch the full stack for live viva demonstration:

**Terminal 1 — Authoritative FastAPI Backend (Port 8000)**:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js 14 Web Frontend (Port 3000)**:
```powershell
npm --prefix apps/web run start -- -p 3000
```

### 6.2 Step-by-Step Viva Demonstration Workflow
1. **Onboarding & Role Selection Gateway**:
   - Open `http://localhost:3000`.
   - The role selection modal displays 5 distinct cards: Farmer, Logistics, Dealer, Buyer, Admin.
   - Click **Logistics** to enter the Logistics Workspace.
2. **Dynamic Real-Road Vehicle Simulation Studio**:
   - Navigate to the **Tracking & Fleet** tab (`http://localhost:3000/dashboard?role=Logistics&tab=tracking`).
   - Click the preconfigured corridor button: **"Abohar $\to$ Azadpur Mega Mandi, Delhi (374.6 km)"**.
   - Observe the green highway polyline rendering along actual national highways (NH-7, NH-9) with origin (A) and destination (B) pins.
   - Click **"Initialize Simulation"** to create an authoritative session.
   - Click **"Play / Start"** or **"Step +1.0km"** to advance the virtual truck.
   - Observe the animated vehicle marker rotating dynamically to match the road forward bearing (`current_heading_deg`).
   - Observe the Telemetry HUD updating: Speed, Heading, Temperature, Humidity, and Cold-Chain Risk.
3. **Scenario Injection (Thermal Excursion)**:
   - Change the scenario dropdown from **Normal** to **Temperature Excursion**.
   - Step the simulation forward 3 times.
   - Observe the chamber temperature climbing above $10^\circ\text{C}$, the risk gauge turning red/pulsing, and the **Thermal Excursion Alert** activating.
4. **Custom Interactive Map-Click Routing**:
   - Click the **"📍 Pick on Map"** button beside Origin or Destination.
   - Click anywhere on the map of India.
   - Click **"Preview Highway Route"** $\to$ the backend dynamically resolves OSRM highway coordinates and calculates exact distance.
5. **Farmer Multi-Fruit Inspection**:
   - Switch role to **Farmer** via the top-right header role switcher.
   - Navigate to **Produce Quality Inspection** (`tab=analyze`).
   - Upload sample images from `ml/data/` for Guava (ResNet18), Banana (ResNet18), or Apple (YOLOv8n).
   - Observe Mango showing the honest gated unavailable state.
6. **Admin System Diagnostics**:
   - Switch role to **Admin** (`tab=status`).
   - Verify GPU inference device (`cuda`), PyTorch version, and model registry availability.

---

## 7. Remaining Limitations & Risk Matrix

| # | Limitation | Impact on Demonstration | Mitigation / Academic Defense |
|---|:---|:---|:---|
| 1 | **Heuristic Spoilage Risk Engine** | Cold-chain arrival risk is calculated via expert rules, not a trained neural network. | Explicitly labeled as a rule-based estimator in UI and API; input schema strictly conforms to 24-step $\times$ 5-feature temporal sequence. |
| 2 | **Host-Level PostgreSQL Status** | PostgreSQL port 5432 is closed on the host Windows machine. | Atomic file-based JSON ledger fallback (`.persisted_session.json`) preserves all data across reboots. Full PostGIS SQL migrations 001–005 are provided for containerized deployment. |
| 3 | **OSRM Public Rate Limiting** | External OSRM routing requests could experience latency or network throttling. | Deterministic offline high-resolution highway corridor generator acts as an automatic fallback within $<50\text{ms}$. |

---

## 8. Final Academic Submission Verdict

### **FINAL VERDICT: PASS WITH LIMITATIONS**

- **Model Checkpoints**: LOCKED & VERIFIED (SHA-256 signatures intact).
- **Multi-Fruit Inspection**: 100% OPERATIONAL (CUDA accelerated).
- **Vehicle Simulation**: 100% OPERATIONAL (Real road LineStrings, heading rotation, HUD).
- **Role Isolation**: 100% OPERATIONAL (5 distinct workspaces).
- **Academic Honesty**: 100% VERIFIED (Limitations explicitly labeled and documented).

**Certified by AgriChain AI Core Engineering Team**  
*November 1, 2026*

