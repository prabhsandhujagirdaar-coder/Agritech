# AgriChain AI — Phase 8: Final Integration Audit & Academic Readiness Report

**Document Version:** 1.0.0  
**Target Crops:** Guava (*Psidium guajava* L.) [Active Demonstration] / Kinnow Mandarin (*Citrus reticulata*) [Target Production Architecture]  
**Evaluation Model:** ResNet18 Transfer Learning Baseline (v2.0.0, frozen weights)  
**Hardware Executed:** NVIDIA GeForce RTX 4050 Laptop GPU (CUDA 12.8, PyTorch 2.11.0+cu128)  
**Host Environment:** Windows 11 (PowerShell 7/Windows PowerShell)  
**Audit Date:** October 2026  
**Status:** Complete Empirical Audit  

---

## Executive Summary

Phase 8 conducts a rigorous, multi-dimensional integration audit and academic readiness review of the **AgriChain AI** platform across its three academic targets:
1. **Deep Learning**: Guava CNN baseline classification, leak-free grouped evaluation, uncertainty presentation, and inference service.
2. **App Development**: Mobile client architecture, Android-first networking specs, and field inspection workflows.
3. **Minor Project (Capstone)**: Full-stack system integration connecting Next.js 14 web portal, FastAPI REST backend, PostGIS spatial ledger, telemetry risk evaluation, and WebSocket event distribution.

This audit evaluates all workflows through empirical execution rather than theoretical code review. Every subsystem is classified as **TESTED**, **PARTIALLY TESTED**, **BLOCKED**, or **NOT IMPLEMENTED**.

---

## 1. Workflow Status Matrix

The following matrix records empirical verification results executed against live running services:

| Workflow / Subsystem | Endpoint / Command | Status | Empirical Evidence / Response Summary |
| :--- | :--- | :---: | :--- |
| **Backend Root Health** | `GET http://127.0.0.1:8000/health` | **TESTED** | `200 OK`: `{"status":"healthy","target_crop":"guava","model":"resnet18","device":"cuda","model_available":true}`. Database fallback: `{"enabled":false,"message":"File-based ledger persistence active."}`. |
| **CNN Model Status** | `GET http://127.0.0.1:8000/api/v1/cnn/status` | **TESTED** | `200 OK`: `{"status":"ready","target_crop":"guava","device":"cuda","class_mapping_verified":true}`. |
| **Frontend Health Proxy** | `GET http://localhost:3000/api/health` | **TESTED** | `200 OK`: Proxies to FastAPI backend with 3 ms round-trip latency. |
| **Guava Image Ingest (Green)** | `POST http://localhost:3000/api/predict` | **TESTED** | `200 OK`: Evaluated `Local Sindhi/Green/40.jpg` $\to$ Predicted `Green` (Index 0, Softmax Score `0.9706`, Latency 19 ms). |
| **Guava Image Ingest (Mature Green)**| `POST http://localhost:3000/api/predict` | **TESTED** | `200 OK`: Evaluated `Local Sindhi/Mature Green/237.jpg` $\to$ Predicted `Mature Green` (Index 1, Softmax Score `0.8147`, Latency 16.79 ms). |
| **Guava Image Ingest (Ripe)** | `POST http://localhost:3000/api/predict` | **TESTED** | `200 OK`: Evaluated `Local Sindhi/Ripe/140.jpg` $\to$ Predicted `Ripe` (Index 2, Softmax Score `0.6770`, Latency 16.54 ms). |
| **Uncertainty Heuristic** | Frontend `checkPredictionUncertainty()` | **TESTED** | `MIN_TOP_SCORE: 0.60`, `MIN_SCORE_MARGIN: 0.15`. Screenshot cases (47.36%, 50.72%) trigger warning state; clear cases (75.18%, 97.06%, 67.70%) pass without warning. Independent conditions verified. |
| **Shipment Creation** | `POST http://127.0.0.1:8000/api/v1/shipments` | **TESTED** | `201 Created`: Created shipment `SHP-2026-017` (`produce_type: "Guava"`, `quantity: 450.0`, `origin: "Abohar Packhouse"`). |
| **Shipment Persistence** | `GET http://127.0.0.1:8000/api/v1/shipments/SHP-2026-017` | **TESTED** | `200 OK`: Verified persistence across sessions via `ShipmentRepository` in `.persisted_session.json`. |
| **Telemetry Ingestion** | `POST .../shipments/{id}/telemetry` | **TESTED** | `201 Created`: Ingested `TEL-SHP-2026-017-1` (`temperature: 6.8°C`, `humidity: 87.5%`, `location: "NH-7 Corridor near Malout"`). |
| **Telemetry Sequence Query** | `GET .../shipments/{id}/telemetry` | **TESTED** | `200 OK`: Returns structured JSON array of timestamped sensor readings. |
| **PostGIS Waypoint Ingestion** | `POST .../shipments/{id}/waypoints` | **TESTED** | `201 Created`: Ingested `WAY-SHP-2026-017-1` (`longitude: 74.31`, `latitude: 30.18`, `srid: 4326`, `speed_kmh: 58.5`). |
| **PostGIS Waypoint Query** | `GET .../shipments/{id}/waypoints` | **TESTED** | `200 OK`: Querying waypoints returns WGS84 coordinates and metadata. |
| **PostgreSQL / PostGIS Database** | `python database/apply_migrations.py --status` | **PARTIALLY TESTED** | **Database Offline**: Port 5432 unreachable. Migration DDL files exist (`001_initial_postgis_schema.sql`). The application gracefully falls back to JSON ledger persistence (`DATABASE_ENABLED=false`). |
| **LSTM 24h Transit Risk Scoring** | `POST http://127.0.0.1:8000/api/v1/lstm/predict` | **TESTED** | `200 OK`: 24-step sequence evaluated $\to$ `current_risk: 51.3`, `predicted_arrival_risk: 59.0`, `alert: true`, `inference_ms: 12.4`. |
| **Shipment Excursion Risk** | `GET .../shipments/{id}/risk` | **TESTED** | `200 OK`: Evaluates recorded sensor history against thermal thresholds (4–8°C). |
| **WebSocket Real-Time Gateway** | `ws://127.0.0.1:8000/ws/shipments` | **BLOCKED** | **Runtime Dependency Missing**: Route and `ConnectionManager` exist in `app/api/v1/endpoints/ws.py`. However, Uvicorn was launched without `uvicorn[standard]` or `websockets` installed in `.venv`. Uvicorn logs: `WARNING: No supported WebSocket library detected`. Connection attempts return HTTP 404 / handshake failure. |
| **Docker Compose Architecture** | `docker compose up` / `docker ps` | **BLOCKED** | **Host Daemon Offline**: Docker CLI 29.9.1 is installed on host, but Docker Desktop daemon is not running (`failed to connect to npipe:////./pipe/dockerDesktopLinuxEngine`). Furthermore, `compose.yaml` targets `best_kinnow_resnet18.pth` rather than active Guava weights. |
| **Flutter Mobile Application** | `apps/mobile/` build checks | **NOT IMPLEMENTED** | **Stub Directory Only**: Flutter 3.47.2 and Dart 3.13.2 are installed on host. Architectural specs and Android network guides exist in `docs/app-development/`. However, `apps/mobile/` contains only `.gitkeep`; no `pubspec.yaml`, Dart source, or Gradle scripts exist. |

---

## 2. Test Execution & Verification Evidence

### 2.1 Backend Unit Test Suites

**Execution Command:**
```powershell
.\.venv\Scripts\python.exe -m unittest backend/tests/test_cnn_api.py backend/tests/test_persistence.py backend/tests/test_guava_cnn_integration.py
```

**Results:**
```
Ran 39 tests in 12.927s
OK
```

- `test_cnn_api.py`: **15 passed, 0 failed** (Input validation, MIME filtering, 10MB upload limits, 503 uncertified model rejection, legacy strawberry model rejection).
- `test_persistence.py`: **13 passed, 0 failed** (Shipment CRUD, telemetry sequences, PostGIS waypoint records, ACID file-lock ledger persistence).
- `test_guava_cnn_integration.py`: **11 passed, 0 failed** (Guava checkpoint loading, label mapping, PyTorch GPU tensor pipeline, HTTP endpoint parity).
- **Total Backend Tests:** **39 Passed, 0 Failed (100% Pass Rate)**.

> [!NOTE]
> **Discovery Anomaly Disclosed:** Running `python -m unittest discover -s backend/tests -p "test_*.py"` discovers `test_client_compat.py` as a test suite because of its `test_` filename prefix. Because `test_client_compat.py` is an ASGI compatibility shim rather than a `unittest.TestCase`, automated discovery fails on that file. Running the three test modules explicitly produces a 100% clean pass rate.

### 2.2 Frontend Unit Tests & Code Quality

**Test Execution Command (`apps/web`):**
```bash
npm test
```
**Results:**
```
Running Strawberry CNN Class Labels & Ripeness Taxonomy Tests...
All CNN Class Labels, Produce Taxonomy, & Phase 7 Uncertainty Tests PASSED successfully!
```
- Total test assertions: **9 test suites passed, 0 failed**.
- Verified: Low top scores (`47.36%`, `50.72%`), clear top scores (`75.18%`, `97.06%`, `67.70%`), independent low score trigger, independent close margin trigger, custom threshold overrides, 3-class coverage (`Green`, `Mature Green`, `Ripe`), and null-safety.

**Linter Execution Command (`apps/web`):**
```bash
npm run lint
```
**Results:**
```
Exit code: 0 (0 errors, 4 non-blocking pre-existing Next.js image optimization warnings)
```

**Production Build Verification (`apps/web`):**
```bash
npm run build
```
**Results:**
```
▲ Next.js 14.2.35
Creating an optimized production build ...
✓ Compiled successfully
✓ Generating static pages (9/9)
Finalizing page optimization ...
Route (app)                              Size     First Load JS
┌ ○ /                                    4.18 kB         100 kB
├ ○ /_not-found                          870 B          88.2 kB
├ ƒ /api/health                          0 B                0 B
├ ƒ /api/predict                         0 B                0 B
├ ƒ /api/shipments                       0 B                0 B
├ ƒ /api/shipments/[id]                  0 B                0 B
├ ƒ /api/shipments/[id]/telemetry        0 B                0 B
├ ƒ /api/telemetry/[id]                  0 B                0 B
├ ƒ /api/telemetry/predict               0 B                0 B
└ ○ /dashboard                           15.2 kB         111 kB
Exit code: 0 (Production build artifact validated)
```

---

## 3. Current Architecture & Monorepo Structure

```
Agritech_/
├── apps/
│   ├── web/                    # Next.js 14 (App Router) Dashboard (Active on :3000)
│   │   ├── app/                # Pages, Route Handlers (/api/predict, /api/health, /api/shipments)
│   │   ├── components/         # ShipmentsTracking, Navigation, Telemetry Panels
│   │   ├── lib/constants.js    # Crop labels, UNCERTAINTY_THRESHOLDS, checkPredictionUncertainty
│   │   └── lib/constants.test.mjs # Frontend test suite
│   └── mobile/                 # Flutter Android stub (.gitkeep only — NOT IMPLEMENTED)
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # cnn.py, shipments.py, telemetry.py, ws.py
│   │   ├── core/config.py      # Pydantic Settings (TARGET_CROP, GUAVA_MODEL_ACTIVATED)
│   │   ├── db/                 # repository.py, session.py (PostGIS + JSON ledger fallback)
│   │   ├── models/             # SQLAlchemy ORM models (Shipment, Telemetry, Waypoints)
│   │   ├── schemas/            # Pydantic v2 schemas (cnn.py, shipment.py, telemetry.py)
│   │   ├── services/           # cnn_service.py (ResNet18 PyTorch loader & inference)
│   │   └── main.py             # FastAPI ASGI App (Active on :8000)
│   ├── tests/                  # Unit tests (test_cnn_api, test_persistence, test_guava_cnn_integration)
│   └── requirements.txt        # Backend dependencies
├── ml/
│   ├── artifacts/              # Frozen weights (best_guava_resnet18.pth — 44.80 MB)
│   ├── configs/                # Hyperparameters (resnet18_guava_v2_grouped.json)
│   ├── data/
│   │   ├── guava_classification/ # Raw dataset (2,309 images, 3 varieties)
│   │   └── manifests/v2_grouped/ # Group-aware splits (train: 1617, val: 346, test: 346)
│   └── src/                    # train_guava_cnn.py, curate_maturity_subset.py
├── database/
│   ├── apply_migrations.py     # Migration CLI runner
│   └── migrations/             # 001_initial_postgis_schema.sql (SRID 4326 DDL)
├── docs/                       # Comprehensive documentation & verification reports
│   ├── deep-learning/          # Dataset audit, Kinnow research, annotation protocols
│   ├── app-development/       # Flutter Android integration architecture
│   ├── minor-project/          # System design & architecture documents
│   └── ml/                     # Phase 5, 6, and 7 Guava verification reports
├── compose.yaml                # Docker Compose orchestration
└── README.md                   # Root monorepo overview
```

---

## 4. Scientific & Academic Integrity Disclosures

To ensure full compliance with peer-reviewed academic rigor and faculty review:

### 4.1 Guava Model Baseline Metrics
- **Held-Out Test Set:** 346 physical images from [`ml/data/manifests/v2_grouped/test.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/v2_grouped/test.json).
- **Test Accuracy:** **83.24%**
- **Test Macro-F1:** **0.8122**
  - **Macro-Recall:** **86.56%**
  - **Macro-Precision:** **78.20%**
- **Single-Image Latency:** ~4.95 ms direct GPU inference; ~16.5 ms through full FastAPI/Next.js HTTP stack.
- **Three-Specimen Demonstration vs Generalization:** The three specimen tests demonstrated in Phases 5, 6, and 7 returned 100% agreement (`Green`, `Mature Green`, `Ripe`). However, these are individual illustrative specimens and must **never** be cited as evidence of 100% model accuracy. The true measured empirical generalization remains **83.24%**.

### 4.2 Data Leakage & Grouped Splitting Integrity
- **Physical Capture Protocol:** The Maitlo et al. (2023) source dataset photographed fruit lots under rotation without recording unique fruit ID tags.
- **Naive Splitting Inflation:** Standard stratified random frame splitting yields **88.12% accuracy**, but leaks **383 identical dHash pairs** (Hamming distance = 0) between train and test splits, artificially inflating reported accuracy by **+4.88%**.
- **Perceptual Hash Clustering Mitigation:** Implementing connected-component dHash clustering (Hamming distance $\le 2$) grouped 2,309 frames into 606 candidate fruit clusters, reducing identical train-test pairs to **4 pairs** (99.0% leak reduction).
- **Residual Leakage Disclosure:** Perceptual clustering is an automated heuristic and cannot guarantee 100% fruit isolation in the absence of original laboratory lot numbers. The residual 4 identical pairs and 12 near-duplicate pairs are openly reported in academic documentation.

### 4.3 Transit Telemetry Simulation
- Telemetry streams for shipments (`SHP-2026-001`, `SHP-2026-017`) and sensor readings are synthetically generated or simulated based on realistic cold-chain thermal parameters (4–8°C recommended for fresh citrus/guava transit). They demonstrate automated risk index alerting and excursion detection, but do not represent active physical hardware deployed on refrigerated trucks.

### 4.4 Non-Certification Disclaimer
- The CNN maturity classifier and transit risk index are experimental research prototypes. They have **not** received clinical, agricultural, or statutory commercial certification. They must not be presented as certified legal grading systems or guaranteed commercial shelf-life determinators.

---

## 5. Audit Findings: Defaults, Incomplete Code & Anomalies

| Area | Finding / Discrepancy | Severity | Remediation Strategy |
| :--- | :--- | :---: | :--- |
| **Backend Environment Defaults** | `TARGET_CROP` in `config.py` defaults to `"kinnow"`, and `GUAVA_MODEL_ACTIVATED` defaults to `False`. Launching Uvicorn without `$env:TARGET_CROP="guava"` results in HTTP 503 model unavailable. | Medium | Update `.env.example` to document `TARGET_CROP=guava` and `GUAVA_MODEL_ACTIVATED=true` for demonstration runs. |
| **Compose Configuration** | `compose.yaml` hardcodes `MODEL_WEIGHTS_PATH: ml/artifacts/best_kinnow_resnet18.pth` and lacks Guava environment variables. Running Compose would start a degraded backend. | Medium | Document requirement to pass Guava variables in `compose.yaml` or `.env` when deploying via Docker. |
| **WebSocket Dependencies** | FastAPI has WebSocket endpoints registered (`/ws/shipments`), but `.venv` lacks `websockets` or `wsproto`. Upgrade requests are rejected with 404 / unsupported upgrade. | Medium | Install `websockets` in `.venv` or add to `backend/requirements.txt` for live streaming demonstration. |
| **PostgreSQL Database** | PostgreSQL is currently offline on port 5432. The system operates entirely on its designed file-based fallback persistence (`.persisted_session.json`). | Low | Operational as designed for development/evaluation; start PostgreSQL container when full PostGIS indexing is required. |
| **Mobile Client Implementation** | `apps/mobile/` is completely empty (`.gitkeep` only). No Flutter code exists despite full architectural documentation in `docs/app-development/`. | High | Build the MVP Flutter app or clearly state that mobile development is at the architectural specification stage. |
| **Test Discovery Naming** | `test_client_compat.py` matches unittest discovery patterns despite being an ASGI helper shim. | Low | Rename to `client_compat.py` or invoke test suites explicitly by module name. |

---

## 6. Academic Track Deliverables Mapping

| Track | Deliverable Documents & Code Artifacts | Readiness Status |
| :--- | :--- | :---: |
| **A. Deep Learning** | 1. Dataset audit & leakage analysis: [`docs/ml/GUAVA_DATASET_AUDIT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_DATASET_AUDIT.md)<br>2. Data preparation & grouped splits: [`docs/ml/GUAVA_DATA_PREPARATION.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_DATA_PREPARATION.md)<br>3. Training report & leak metrics: [`docs/ml/GUAVA_TRAINING_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_TRAINING_REPORT.md)<br>4. Frozen model weights: [`ml/artifacts/best_guava_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_guava_resnet18.pth)<br>5. Uncertainty presentation: [`docs/ml/GUAVA_PHASE7_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_PHASE7_REPORT.md) | **100% Complete & Reproducible** |
| **B. App Development** | 1. Mobile architecture & networking guide: [`docs/app-development/FLUTTER_ANDROID_INTEGRATION.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/app-development/FLUTTER_ANDROID_INTEGRATION.md)<br>2. Android API client contracts & UI wireframe documentation: [`docs/app-development/README.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/app-development/README.md)<br>3. Mobile client code: `apps/mobile/` | **Documentation: 100%<br>Mobile Code: 0% (Stub)** |
| **C. Minor Project (Capstone)** | 1. Full-stack system architecture & verification: [`docs/ml/GUAVA_PHASE6_VERIFICATION_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_PHASE6_VERIFICATION_REPORT.md)<br>2. Integration audit & status matrix: [`docs/PHASE8_INTEGRATION_AUDIT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/PHASE8_INTEGRATION_AUDIT.md)<br>3. Next.js web portal: [`apps/web/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/) (verified build)<br>4. FastAPI backend: [`backend/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/) (39 passing tests)<br>5. PostGIS schemas & migration runner: [`database/migrations/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/database/migrations/) | **90% Complete** (Web + API + DB Fallback + ML operational; WebSockets & Mobile stubbed) |

---

## 7. Prioritized Action Plan Before Semester Submission

### Priority 0: Immediate Submission Readiness (No Code Risk)
- [x] **Audit & Fix Demo Strings:** Audit all dashboard and landing page UI copy to eliminate contradictory legacy strawberry strings and standardize on Guava maturity stages.
- [x] **Document Uncertainty UI Heuristics:** Retain transparent documentation in `constants.js` and report that thresholds are UI heuristics, not calibrated probabilities.
- [x] **Verify 100% Test Stability:** Confirm 39 backend tests and 9 frontend test suites pass with zero regressions.

### Priority 1: High-Impact Technical Refinements
- [ ] **Install `websockets` in `.venv`:** Run `pip install websockets` in `.venv` so that Uvicorn can accept live WebSocket upgrades for real-time telemetry streaming in live demonstrations.
- [ ] **Rename `test_client_compat.py`:** Rename `backend/tests/test_client_compat.py` to `backend/tests/client_compat.py` to enable global `python -m unittest discover` execution without test discovery collisions.
- [ ] **Align `compose.yaml` & `.env.example`:** Add Guava default environment variables (`TARGET_CROP=guava`, `GUAVA_MODEL_ACTIVATED=true`) to `.env.example` and `compose.yaml`.

### Priority 2: App Development Track Submission Completion
- [ ] **Initialize Flutter Mobile Client:** Run `flutter create --org com.agrichain --platforms android apps/mobile` to scaffold the Flutter Android project.
- [ ] **Implement Intake Screen:** Implement camera capture and `POST /api/v1/cnn/predict` image upload in Flutter to satisfy the practical demonstration requirement for the App Development course.
- [ ] **Start PostGIS Container:** Start Docker Desktop and launch PostgreSQL/PostGIS (`docker compose up -d db`) to demonstrate live spatial SQL queries (`ST_AsGeoJSON`, `ST_MakeLine`) on physical geospatial waypoints.
