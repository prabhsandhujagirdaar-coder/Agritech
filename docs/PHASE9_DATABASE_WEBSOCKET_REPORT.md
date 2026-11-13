# AgriChain AI — Phase 9: PostgreSQL/PostGIS & WebSocket Restoration Report

**Document Version:** 1.0.0  
**Target Crops:** Guava (*Psidium guajava* L.) [Active Demonstration] / Kinnow Mandarin (*Citrus reticulata*)  
**Database Backend:** PostgreSQL 16 + PostGIS 3.4 (`agrichain-db` container on port 5432)  
**Real-Time Gateway:** WebSocket Event Gateway (`/api/v1/ws/shipments` via `websockets 17.3`)  
**ML Model:** ResNet18 Transfer Learning Baseline (v2.0.0 on CUDA GPU)  
**Execution Date:** October 2026  
**Status:** Successfully Restored & Fully Verified  

---

## Executive Summary

In Phase 8, the integration audit identified two runtime gaps:
1. **PostgreSQL / PostGIS Database:** The database service was offline on host port 5432 because Docker port mapping was disabled in `compose.yaml`, causing the application to operate in file-based JSON fallback mode.
2. **WebSocket Gateway:** Uvicorn rejected WebSocket upgrade requests with HTTP 404 because the Python virtual environment lacked a supported WebSocket library (`websockets` or `wsproto`).

In Phase 9, both subsystems were restored to full operational status:
- The PostgreSQL 16 + PostGIS 3.4 database was exposed on `127.0.0.1:5432`, schema migrations were applied, and the repository was verified writing live relational and spatial data (EPSG:4326).
- The `websockets` library was declared in `backend/requirements.txt` and installed in `.venv`. The WebSocket gateway was empirically verified handling handshakes, heartbeat ping/pong frames, and real-time broadcasts for shipment creation and telemetry updates.
- Zero regression was maintained across Guava CNN inference (CUDA), LSTM cold-chain risk scoring, frontend unit tests, and all 40 backend test cases.

---

## 1. Task 1 — PostgreSQL / PostGIS Restoration & Verification

### 1.1 Docker Desktop & Container State
- Checked Docker status on Windows host: Docker Desktop daemon is active.
- Container `agrichain-db` running image `postgis/postgis:16-3.4` with persistent volume `agrichain_pgdata`.
- To avoid port conflicts on 8000 and 3000 with the host development processes, the containerized `agrichain-backend` and `agrichain-frontend` containers were stopped, leaving only `agrichain-db` running in Docker.

### 1.2 Port Mapping Configuration (`compose.yaml`)
Uncommented localhost port mapping for `agrichain-db`:
```yaml
    # Expose PostgreSQL / PostGIS to localhost for host backend and migration tooling
    ports:
      - "127.0.0.1:5432:5432"
```
Recreated container with `docker compose up -d db`:
```
CONTAINER ID   IMAGE                    COMMAND                  STATUS                   PORTS                      NAMES
8988399ee768   postgis/postgis:16-3.4   "docker-entrypoint.s…"   Up (healthy)             127.0.0.1:5432->5432/tcp   agrichain-db
```
The named volume `agrichain_pgdata` was preserved without data loss or reset.

### 1.3 Database Migration Execution
Ran migration runner tool:
```powershell
.\.venv\Scripts\python.exe database/apply_migrations.py --apply
```
**Outcome:**
```
Reading migration file: 001_initial_postgis_schema.sql...
Successfully executed migration '001_initial_postgis_schema.sql'.
```
Verified database schema relations with `psql`:
- `shipments` (Relational lifecycle ledger)
- `telemetry_logs` (Sensor readings linked via foreign key to `shipments.id`)
- `geo_waypoints` (Spatial table containing PostGIS `coordinates geometry(Point, 4326)`)

### 1.4 Live Connection Probe
Restarted the host backend with `$env:DATABASE_ENABLED="true"`:
```bash
curl.exe -s http://127.0.0.1:8000/health
```
**Response:**
```json
{
  "status": "healthy",
  "target_crop": "guava",
  "model": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "model_available": true,
  "message": "Model loaded successfully on cuda for guava.",
  "database": {
    "enabled": true,
    "connected": true,
    "message": "PostgreSQL port 5432 on 'localhost' is reachable."
  }
}
```

### 1.5 Database CRUD & PostGIS Spatial Verification

#### Step A: Create Shipment in Database
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/shipments" -Method Post -ContentType "application/json" -Body '{"produce_type": "Guava", "origin": "Abohar Research Station", "destination": "Chandigarh Mandi", "quantity": 300.0, "status": "created"}'
```
- **Response:** `SHP-2026-004` created.
- **Direct Database SQL Verification:**
  ```sql
  SELECT id, produce_type, origin, destination, quantity FROM shipments WHERE id = 'SHP-2026-004';
  ```
  Result: `SHP-2026-004 | Guava | Abohar Research Station | Chandigarh Mandi | 300.00` (1 row).

#### Step B: Ingest Sensor Telemetry into Database
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/shipments/SHP-2026-004/telemetry" -Method Post -ContentType "application/json" -Body '{"temperature": 6.3, "humidity": 86.8, "sensor_id": "SNS-GUAVA-01", "location": "Malout Corridor"}'
```
- **Response:** `TEL-SHP-2026-004-1` created.
- **Direct Database SQL Verification:**
  ```sql
  SELECT id, shipment_id, temperature, humidity, sensor_id FROM telemetry_logs WHERE shipment_id = 'SHP-2026-004';
  ```
  Result: `TEL-SHP-2026-004-1 | SHP-2026-004 | 6.30 | 86.80 | SNS-GUAVA-01` (1 row).

#### Step C: Ingest & Query PostGIS Spatial Waypoints (SRID 4326)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/shipments/SHP-2026-004/waypoints" -Method Post -ContentType "application/json" -Body '{"longitude": 74.4989, "latitude": 30.1915, "altitude_m": 195.0, "speed_kmh": 62.0, "heading_deg": 55.0, "location_metadata": {"checkpoint": "Malout Toll", "corridor": "NH-7"}}'
```
- **Response:** `WAY-SHP-2026-004-1` created.
- **Direct PostGIS SQL Spatial Query:**
  ```sql
  SELECT id, shipment_id, ST_AsText(coordinates) as wkt, ST_SRID(coordinates) as srid, ST_X(coordinates) as lon, ST_Y(coordinates) as lat, altitude_m, speed_kmh FROM geo_waypoints WHERE shipment_id = 'SHP-2026-004';
  ```
- **PostGIS Output:**
  ```
           id         | shipment_id  |          wkt           | srid |   lon   |   lat   | altitude_m | speed_kmh 
  --------------------+--------------+------------------------+------+---------+---------+------------+-----------
   WAY-SHP-2026-004-1 | SHP-2026-004 | POINT(74.4989 30.1915) | 4326 | 74.4989 | 30.1915 |     195.00 |     62.00
  ```
Confirmed: The coordinates are stored as native binary geometries in PostGIS with spatial reference system WGS84 (`SRID 4326`), and spatial functions `ST_X`, `ST_Y`, and `ST_AsText` query them cleanly.

---

## 2. Task 2 — WebSocket Runtime Restoration & Real-Time Broadcasts

### 2.1 Dependency Declaration & Installation
1. Updated [`backend/requirements.txt`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/requirements.txt):
   ```text
   fastapi>=0.115.0
   uvicorn[standard]>=0.30.0
   websockets>=12.0
   ```
2. Installed into virtual environment:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install websockets psycopg2-binary
   ```
   Installed: `websockets-17.3`, `psycopg2_binary-2.9.13`.

### 2.2 Endpoint Architecture & Broadcast Wiring
Inspected [`backend/app/api/v1/endpoints/ws.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/app/api/v1/endpoints/ws.py) and [`backend/app/api/v1/endpoints/shipments.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/app/api/v1/endpoints/shipments.py):
- Singleton `ConnectionManager` maintains active client WebSockets and broadcasts JSON events with ISO timestamps.
- Endpoint routes registered at:
  - `ws://127.0.0.1:8000/api/v1/ws/shipments`
  - `ws://127.0.0.1:8000/ws/shipments`
- Broadcast triggers already wired:
  - `create_shipment()` $\to$ `await get_ws_manager().broadcast("shipment_created", record)`
  - `update_shipment_status()` $\to$ `await get_ws_manager().broadcast("shipment_update", updated)`
  - `add_shipment_telemetry()` $\to$ `await get_ws_manager().broadcast("telemetry_update", reading)`
  - `add_shipment_waypoint()` $\to$ `await get_ws_manager().broadcast("waypoint_update", waypoint)`

### 2.3 End-to-End WebSocket Lifecycle Verification
Created automated verification tool [`scripts/verify_websocket_broadcast.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/verify_websocket_broadcast.py):
```powershell
.\.venv\Scripts\python.exe scripts/verify_websocket_broadcast.py
```

**Execution Log & Empirical Evidence:**
```
1. Connecting to WebSocket gateway at ws://127.0.0.1:8000/api/v1/ws/shipments...
   [GREETING RECEIVED]: event='connected', message='AgriChain AI WebSocket Stream Active'

2. Testing Heartbeat Ping/Pong...
   [PONG RECEIVED]: type='pong', timestamp='2026-10-22T06:06:28.957958+00:00'

3. Testing real-time broadcast delivery during shipment creation...
   [HTTP POST CREATED]: id='SHP-2026-005', origin='Abohar Nursery Hub'
   [WS BROADCAST RECEIVED]: event='shipment_created', shipment_id='SHP-2026-005'

4. Testing real-time broadcast delivery during telemetry addition...
   [HTTP POST TELEMETRY]: id='TEL-SHP-2026-005-1', temp=5.9C
   [WS BROADCAST RECEIVED]: event='telemetry_update', reading_id='TEL-SHP-2026-005-1'

[ALL WEBSOCKET TESTS PASSED]: Connection, Ping/Pong, Shipment Creation Broadcast, and Telemetry Broadcast fully verified!
```

---

## 3. Task 3 — Regression Tests & Safety Verification

### 3.1 Backend Test Suite Execution
```powershell
.\.venv\Scripts\python.exe -m unittest backend/tests/test_cnn_api.py backend/tests/test_persistence.py backend/tests/test_guava_cnn_integration.py
```

**Results:**
```
Ran 40 tests in 15.435s
OK
```
- `test_cnn_api.py`: **15 passed, 0 failed**.
- `test_persistence.py`: **14 passed, 0 failed** (includes test verifying online database probe when PostgreSQL is reachable, test verifying offline database probe without crashing, and failure safeguards).
- `test_guava_cnn_integration.py`: **11 passed, 0 failed**.
- **Aggregate Backend Tests:** **40 Passed, 0 Failed (100% Pass Rate)**.

### 3.2 Frontend Unit Tests & Linter
```bash
# In apps/web
npm test
npm run lint
```
- `npm test`: **All 9 test suites passed** (produce taxonomy, guava class labels, and Phase 7 uncertainty heuristics).
- `npm run lint`: **0 errors**.

### 3.3 Core Functionality Integrity Checks
1. **Guava ResNet18 Inference (CUDA):**
   ```powershell
   curl.exe -s -F "file=@ml/data/guava_classification/Local Sindhi/Green/40.jpg" http://localhost:3000/api/predict
   ```
   Returned: `predicted_class: "Green"`, `confidence: 0.9706`, `target_crop: "guava"`, `device: "cuda"`.
2. **LSTM 24h Transit Risk Scoring:**
   ```powershell
   # 24 steps evaluation on SHP-2026-004
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/lstm/predict" -Method Post ...
   ```
   Returned: `current_risk: 51.3`, `predicted_arrival_risk: 59.0`, `alert: true`, `inference_ms: 12.4`.

---

## 4. Files Changed

| File | Change Type | Summary of Changes |
| :--- | :--- | :--- |
| [`compose.yaml`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/compose.yaml) | Edit | Uncommented `127.0.0.1:5432:5432` port mapping on `agrichain-db` container to enable host backend and migration runner connectivity. |
| [`backend/requirements.txt`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/requirements.txt) | Edit | Added `websockets>=12.0` under FastAPI & Core Server dependencies. |
| [`backend/tests/test_persistence.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/tests/test_persistence.py) | Edit | Patched offline test cases to use unreachable ports and added test confirming online probe when PostgreSQL is reachable. |
| [`backend/tests/test_cnn_api.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/backend/tests/test_cnn_api.py) | Edit | Updated `test_14` to assert `"Abohar"` origin exists within the shipments list without assuming it is strictly the 0th item. |
| [`scripts/verify_websocket_broadcast.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/verify_websocket_broadcast.py) | Create | Automated verification script testing WebSocket handshake, ping/pong, and live HTTP shipment/telemetry broadcasts. |
| [`docs/PHASE9_DATABASE_WEBSOCKET_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/PHASE9_DATABASE_WEBSOCKET_REPORT.md) | Create | Comprehensive Phase 9 report documenting database restoration, PostGIS query verification, WebSocket lifecycle tests, and regression results. |

---

## 5. Remaining Gaps & Boundaries

1. **Flutter Mobile Application:** The mobile client in `apps/mobile/` remains an architectural stub (`.gitkeep` only). Full documentation and Android network specs exist in `docs/app-development/`.
2. **Dockerized Backend GPU Passthrough:** Running the backend container inside Docker on Windows defaults to CPU inference unless NVIDIA Container Toolkit is installed. The host `.venv` process maintains direct CUDA access on the NVIDIA RTX 4050 GPU.
3. **Softmax Score Calibration:** Softmax scores remain uncalibrated heuristic scores (as documented in Phase 7). Temperature scaling on validation logits remains recommended for formal statistical confidence estimation.
