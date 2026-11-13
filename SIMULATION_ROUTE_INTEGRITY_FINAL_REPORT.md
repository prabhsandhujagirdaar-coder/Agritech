# AgriChain AI — Simulation Route Integrity Final Report

**Date**: 2026-11-13  
**Status**: **PASS (100% VERIFIED)**  
**Environment**: Windows 11, Python 3.13.7 (CUDA Enabled, RTX 4050 GPU), Node.js v22.19.0, Next.js 14.2.35  
**Active Services**:
- **FastAPI Backend**: `http://127.0.0.1:8000` (`/api/v1/health` -> HTTP 200 `{"status": "healthy", "device": "cuda"}`)
- **Next.js Web App**: `http://localhost:3000` (HTTP 200 `OK`)

---

## 1. Executive Summary

This report documents the resolution and end-to-end verification of the route-integrity defect observed in the AgriChain AI Simulation Studio. 

### Defect Identified:
Previously, when selecting shipment `SHP-2026-004` (Abohar → Bathinda, 89.39 km), the Simulation Studio route preview correctly showed 89.39 km, but the active simulation HUD displayed an old, unrelated session (`SIM-20261101152526-013`, Abohar → Azadpur APMC Mandi, Delhi) showing:
- Road distance travelled: 71.0 km
- Total distance: 374.7 km
- Progress: 19.0%
- Vehicle coordinates progressing along the Delhi highway corridor instead of the Bathinda corridor.

### Root Cause Analysis:
1. **Frontend Session Leakage**: On mount, `ShipmentsTracking.js` invoked `fetchSimulationSessions()` without scoping by `selectedShipment.id` and blindly bound `activeSimulation` to the first active/paused session in repository history.
2. **Missing Shipment Isolation Guard in HUD**: The Simulation HUD did not isolate sessions per shipment ID; selecting a new shipment card did not invalidate or hide existing sessions belonging to other corridors.
3. **Backend Route Decoupling**: Simulation creation allowed independent calculation of total distance via dense haversine summation rather than locking strictly to the authoritative distance and vertices resolved by `get_shipment_route()`.
4. **Asyncio Lock Binding in Windows Subshells**: `SimulationEngine._lock` was instantiated at module import time, which bound to an inactive loop or deadlocked during cross-corridor programmatic test execution in Windows subshells.

### Architectural Solution Applied:
1. **Authoritative Single Source of Truth**:
   - `CreateSimulationRequest` now supports `route_identifier` and `total_distance_km`.
   - When initialized with `shipment_id`, `create_simulation` queries the authoritative route via `get_shipment_route(shipment_id)` and strictly locks `total_distance_km = float(auth_route["distance_km"])`, `route_geojson = auth_route["geometry"]`, `start_point = coords[0]`, and `route_identifier = f"ROUTE-{shipment_id}-{round(total_dist_km, 2)}"`.
2. **Strict Session Isolation**:
   - When a shipment is selected, `ShipmentsTracking.js` filters sessions via `fetchSimulationSessions(selectedShipment.id)` and sets `activeSimulation` **only** if `s.shipment_id === selectedShipment.id`.
   - If no active simulation exists for the selected shipment, the UI displays a clean "Simulation Ready: Route Verified" card showing 0.0 km travelled (0.0%) and the verified highway distance.
   - `TrackingMap.js` restricts simulation layers and vehicles strictly to the matching `shipment_id`.
3. **Lazy Asyncio Lock**:
   - `SimulationEngine._get_lock()` dynamically discovers the active running event loop, eliminating deadlock.
4. **Endpoint Arrival Clamp**:
   - In `_advance_step`, when `current_distance_km >= total_dist_km`, vehicle coordinates are clamped strictly to destination point `coords[-1]`, and status is set to `COMPLETED`.

---

## 2. Fresh Simulation Verification: SHP-2026-004 (Abohar → Bathinda)

Verification performed using clean test execution against the live FastAPI backend:

| Metric | Route Preview | Backend Simulation Session | Verified Result |
| :--- | :--- | :--- | :--- |
| **Shipment ID** | `SHP-2026-004` | `SHP-2026-004` | **MATCH** |
| **Origin Facility** | Abohar Post-Harvest Center, Punjab | Abohar Post-Harvest Center, Punjab | **MATCH** |
| **Origin Coordinates** | `(30.1227° N, 74.1566° E)` | `(30.1226° N, 74.1566° E)` (coords[0]) | **MATCH** |
| **Destination Facility** | Bathinda Central Agri Godown | Bathinda Central Agri Godown | **MATCH** |
| **Destination Coordinates** | `(30.1798° N, 74.9654° E)` | `(30.1798° N, 74.9654° E)` (coords[-1]) | **MATCH** |
| **Highway Distance** | **89.39 km** | **89.39 km** | **EXACT MATCH (0.00% err)** |
| **Route Vertices** | 831 coordinates | 831 coordinates | **MATCH** |
| **Initial Vehicle Coordinate** | N/A | `(30.1226° N, 74.1566° E)` at 0.0 km (0.0%) | **ORIGIN START** |
| **Coordinate After Step (+15 km)** | N/A | `(30.1653° N, 74.2635° E)` at 15.0 km (16.8%) | **HIGHWAY ADVANCE** |
| **Coordinate At Completion** | N/A | `(30.1798° N, 74.9654° E)` at 89.4 km (100.0%) | **DESTINATION ARRIVAL** |

```
[TEST LOG OUTPUT]
TASK 2: VERIFYING ACTUAL SIMULATION ROUTE FOR SHP-2026-004 (Abohar -> Bathinda)
  Shipment ID:             SHP-2026-004
  Origin:                  Abohar Post-Harvest Center, Punjab (30.1227°N, 74.1566°E)
  Destination:             Bathinda Central Agri Godown (30.1798°N, 74.9654°E)
  First Geometry Coord:    Lon 74.1566, Lat 30.1226
  Last Geometry Coord:     Lon 74.9654, Lat 30.1798
  Highway Preview Dist:    89.39 km (831 vertices)

  Simulation Session ID:   SIM-20261113122414-027
  Route Identifier:        ROUTE-SHP-2026-004-89.39
  Session Total Distance:  89.39 km
  Distance Mismatch:       0.0000 km (0.00% difference)
  Initial Vehicle Coord:   (30.1226°N, 74.1566°E) at 0.0 km
  Vehicle After Step 1:    (30.1653°N, 74.2635°E) at 15.0 km (Progress: 16.8%)
  Vehicle At Completion:   (30.1798°N, 74.9654°E) at 89.4 km (Status: COMPLETED)
  [PASS] SHP-2026-004 completed full journey strictly on road polyline from coords[0] to coords[-1]!
```

---

## 3. Session Isolation Verification

Test verification proved that multiple active simulation sessions for different shipments remain strictly segregated:

1. Invalidate/stop all stale legacy sessions: **PASS** (Cleared stale running sessions).
2. Spawn Session A for `SHP-2026-004` (Abohar → Bathinda, 89.39 km): Initial position = 0.0 km.
3. Spawn Session B for `SHP-2026-003` (Fazilka → Amritsar, 188.96 km): Advanced vehicle by +30.0 km.
4. Query filtered sessions via `/api/v1/simulations/?shipment_id=SHP-2026-004`:
   - All returned sessions strictly belong to `SHP-2026-004`.
   - Session A retains 0.0 km travelled / 89.39 km total.
   - Zero telemetry, coordinate, or distance contamination from Session B.
5. Result: **PASS**.

---

## 4. Multi-Corridor Traversal Test Table

All 4 commercial corridors were executed with fresh sessions, multi-step road movement (+20 km, +40 km), telemetry validation, and 100% destination completion:

| Corridor ID | Route Description | Vertices | Route Distance | Session Distance | Discrepancy | Step 1 (20 km) Coord | Step 2 (60 km) Coord | Final Arrival Coord | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SHP-2026-004** | Abohar → Bathinda | 831 | 89.39 km | 89.39 km | 0.00 km (0.0%) | `(30.1736°N, 74.3143°E)` | `(30.2191°N, 74.7217°E)` | `(30.1798°N, 74.9654°E)` | **PASS** |
| **SHP-2026-003** | Fazilka → Amritsar | 1,732 | 188.96 km | 188.96 km | 0.00 km (0.0%) | `(30.5463°N, 74.1306°E)` | `(30.7857°N, 74.4152°E)` | `(31.6044°N, 74.8723°E)` | **PASS** |
| **SHP-2026-002** | Fazilka → Ludhiana | 2,235 | 226.14 km | 226.14 km | 0.00 km (0.0%) | `(30.5463°N, 74.1306°E)` | `(30.4943°N, 74.4825°E)` | `(30.8497°N, 75.9860°E)` | **PASS** |
| **SHP-2026-010** | Jaipur → Agra | 2,473 | 256.06 km | 256.06 km | 0.00 km (0.0%) | `(26.9171°N, 75.8040°E)` | `(26.8660°N, 76.1836°E)` | `(27.1767°N, 78.0081°E)` | **PASS** |

Each corridor verified:
- Initial position starts at `coords[0]`.
- Discrete step calls strictly interpolate coordinates forward along road geometry.
- Rolling LSTM cold-chain sensor telemetry (temp, humidity, delay, risk) is logged.
- Full traversal completes strictly at `coords[-1]`.

---

## 5. Live Services Verification

Both application servers are actively running without duplicate listener conflicts:

| Service | Port | Process ID | Health Endpoint | Response Status |
| :--- | :---: | :---: | :--- | :--- |
| **FastAPI Backend** | `8000` | PID 4840 | `http://127.0.0.1:8000/api/v1/health` | `HTTP 200 OK` (Service: AgriChain AI Backend, Device: CUDA) |
| **Next.js Web App** | `3000` | PID 29456 | `http://localhost:3000` | `HTTP 200 OK` (Next.js 14.2.35 ready, compiled `/`) |

---

## 6. Regression Test Suite Results

| Test Suite | Command | Result | Notes |
| :--- | :--- | :---: | :--- |
| **Route Integrity Acceptance** | `python scripts/verify_simulation_route_integrity.py` | **PASS** | 4 corridors, strict isolation, ML weights |
| **Shipment Sync & Focus** | `python scripts/verify_shipment_sync_and_map_focus.py` | **PASS** | Auto-sync, manual override, map focus |
| **Dynamic Shipment Routing** | `python scripts/verify_shipment_routing.py` | **PASS** | All 4 independent shipment routes verified |
| **Inventory Unit Tests** | `python backend/tests/test_inventory.py` | **PASS** | 5/5 unit tests passed |
| **Frontend Unit Tests** | `npm --prefix apps/web test` | **PASS** | 5/5 test suites passed (Taxonomy, Geo, Phase 13.5, Phase 13.6, Phase 19) |
| **Web Linter** | `npm --prefix apps/web run lint` | **PASS** | 0 errors |

---

## 7. Frozen ML Checkpoints Cryptographic Verification

All 5 frozen machine learning model checkpoints were audited via SHA-256 cryptographic hashing:

| Artifact File | Checkpoint Size | Authoritative SHA-256 Hash | Integrity Status |
| :--- | :---: | :--- | :---: |
| `best_guava_resnet18.pth` | 44,796,363 bytes | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | **FROZEN UNTOUCHED** |
| `best_banana_resnet18.pth` | 128,791,659 bytes | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | **FROZEN UNTOUCHED** |
| `best_fruit_identifier_mobilenet_v3_large.pth` | 17,044,655 bytes | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` | **FROZEN UNTOUCHED** |
| `best_fruit_identifier_resnet18.pth` | 128,800,363 bytes | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | **FROZEN UNTOUCHED** |
| `best_apple_yolov8n.pt` | 6,502,250 bytes | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` | **FROZEN UNTOUCHED** |

Zero model checkpoints were retrained, modified, or altered.

---

## 8. Final Verdict

**OVERALL VERDICT: PASS (100% VERIFIED)**

The simulation route integrity bug is completely fixed. When any registered shipment (such as `SHP-2026-004`) is selected, the Simulation Studio, route preview, simulation session creation, map polyline, HUD progress, and vehicle coordinate progression reflect that exact journey with 0.00% distance discrepancy and complete session isolation.

