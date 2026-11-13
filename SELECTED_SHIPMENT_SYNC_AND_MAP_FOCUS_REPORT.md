# AgriChain AI — Selected Shipment Auto-Sync & Single-Shipment Map Focus Report

**Verdict**: **PASS**  
**Date**: November 13, 2026  
**Workspace**: `Agritech_` Monorepo  

---

## 1. Executive Summary

This phase implements a seamless, synchronized shipment-selection workflow and single-shipment map focus mode in AgriChain AI. Previously, selecting a registered shipment card did not automatically populate the Simulation Studio fields, requiring users to manually re-enter coordinates, and the map simultaneously displayed all facilities and shipment markers, cluttering the view.

With this implementation:
1. **Auto-Populate Simulation Studio (Task 1)**: Clicking any registered shipment card in *Registered Batches* immediately synchronizes the Simulation Studio inputs (Origin, Destination, GPS coordinates, Shipment ID, highway route geometry, road distance, and estimated duration) without manual data entry.
2. **Single-Shipment Map Focus vs. Global Overview (Task 2)**:
   - **Mode A (Global Overview)**: When no shipment is selected or the user clicks `Show All Shipments`, the map displays all storage facilities, godowns, mandis, cold stores, and all active vehicle markers.
   - **Mode B (Single-Shipment Focus)**: When a shipment is selected, the map immediately hides all unrelated facilities, godowns, and other vehicles. It renders **only**:
     - **Point A (Green)**: Origin endpoint marker.
     - **Point B (Red)**: Destination endpoint marker.
     - **Highway Polyline (`#2563eb`)**: High-contrast blue road-following polyline.
     - **Active Vehicle Marker**: Focused vehicle marker at its current position (if GPS fix exists).
     - **Header Pill**: Displays `Focused: #<ID> | Origin -> Destination` and a one-click `[ Show All Shipments ]` button to return to Global Overview.
3. **Simulation Studio Linked with Manual Override (Task 3)**:
   - Default linked mode displays an emerald badge: `[ Using Selected Shipment: #<ID> ]`.
   - If the user manually edits the origin or destination, the studio seamlessly switches to an amber badge: `[ Custom Route ]` without altering the underlying registered shipment.
   - A dedicated `[ Use Selected Shipment Route ]` button allows the user to immediately revert simulation inputs to the selected shipment's authoritative data.
4. **Leaflet Layer Cleanup (Task 4)**: Prevents stale polyline artifacts and orphan markers when switching between shipments or toggling overview mode.
5. **Data & API Integrity (Task 5)**: Server endpoint `GET /api/shipments/{id}/route` provides deterministic road routing with client-side `AbortController` cancellation to prevent race conditions during rapid card switching.

---

## 2. Implementation Details

### A. Frontend Architecture (`apps/web/components/ShipmentsTracking.js`)
- **State Management**:
  - `isCustomRoute` (boolean): Tracks whether Simulation Studio is using the selected shipment (`false`) or user-customized coordinates (`true`).
  - Auto-sync `useEffect` hooked to `selectedShipment?.id`:
    - Automatically populates `simAssociateShipmentId`, `simOriginQuery`, `simDestQuery`, `simOriginCoords`, and `simDestCoords`.
    - Resets `isCustomRoute(false)`.
  - Authoritative route synchronization in `fetchShipmentRoute`:
    - Synchronizes `routePreviewData` and `simulationRoute` with the calculated highway geometry (`distance_km`, `duration_s`).
  - Manual override handlers:
    - `handleSelectPreset`, `handleSearchOrigin`, `handleSearchDest`, and `handleMapPick` switch `isCustomRoute` to `true`.
  - Reversion handler:
    - `handleRevertToSelectedShipment`: Restores `isCustomRoute(false)` and resyncs origin, destination, coordinates, and route preview from the selected shipment.
  - Linked Banner in Simulation Studio:
    - Displays selected batch ID, produce type, quantity, origin, destination, road distance, and travel duration.
    - Conditionally renders `[ Using Selected Shipment ]` or `[ Custom Route ]` with the reversion action button.

### B. Map Component (`apps/web/components/TrackingMap.js`)
- **Facilities Layer (`facilitiesLayerRef`)**:
  - In Mode B (`selectedShipment != null`), calls `facilitiesLayer.clearLayers()` to eliminate visual clutter.
  - In Mode A (`selectedShipment == null`), renders all storage facilities, godowns, mandis, and cold stores with category filtering.
- **Markers Layer (`markersLayerRef`)**:
  - In Mode B, filters out all other vehicles and renders exclusively the active vehicle marker for `selectedShipment` (if coordinates are valid).
  - In Mode A, renders all geolocated vehicles across India.
- **Route Layer (`routeLayerRef`)**:
  - Renders the high-contrast royal blue highway polyline (`#2563eb`), green Point A (Origin), and red Point B (Destination).
  - Automatically executes `map.fitBounds(bounds, { padding: [60, 60], maxZoom: 12 })` to frame the route.
- **Floating Header Controls**:
  - Displays focused shipment banner with a prominent `[ Show All Shipments ]` button.
  - Clicking `[ Show All Shipments ]` invokes `onSelectShipment(null)`, restoring Global Overview.

---

## 3. Verification Test Results

### 1. Shipment Route Resolution Tests (`scripts/verify_shipment_routing.py`)
| Shipment ID | Origin | Destination | Road Distance | Waypoints | Status |
|:---|:---|:---|:---:|:---:|:---:|
| `SHP-2026-003` | Fazilka CA Cold Store | Amritsar APMC Terminal | 197.23 km | 95 | **PASS** |
| `SHP-2026-002` | Fazilka CA Cold Store | Ludhiana Agro Warehouse | 201.16 km | 98 | **PASS** |
| `SHP-2026-001` | Abohar Post-Harvest Center | Azadpur APMC Mandi, Delhi | 396.59 km | 192 | **PASS** |
| `SHP-2026-010` | Jaipur Muhana APMC Mandi | Agra Cold Logistics Hub | 238.41 km | 117 | **PASS** |

### 2. Auto-Sync & Map Focus Verification (`scripts/verify_shipment_sync_and_map_focus.py`)
- **Test 1 — ShipmentsTracking.js Contract**: PASSED
  - `isCustomRoute` declared and managed.
  - `selectedShipment.id` triggers automatic field population.
  - `fetchShipmentRoute` updates route preview and simulation route.
  - Manual edits switch badge to `Custom Route`.
  - `Use Selected Shipment Route` reverts cleanly.
  - `AbortController` guards against race conditions.
- **Test 2 — TrackingMap.js Focus & Overview Modes**: PASSED
  - Mode A (Global Overview): All facilities and active vehicles visible.
  - Mode B (Single-Shipment Focus): Facilities and unrelated vehicles hidden.
  - Point A (green) and Point B (red) rendered at exact highway endpoints.
  - Highway polyline rendered in `#2563eb`.
  - `Show All Shipments` button restores Global Overview cleanly.
- **Test 3 — Backend Shipment Routing**: PASSED
- **Test 4 — Frozen ML Checkpoints**: PASSED
  - `best_guava_resnet18.pth`: Verified SHA-256 (`b213059f...`)
  - `best_banana_resnet18.pth`: Verified SHA-256 (`3b296ba8...`)
  - `best_fruit_identifier_mobilenet_v3_large.pth`: Verified SHA-256 (`273674bc...`)

### 3. Suite Regressions
- `npm --prefix apps/web run lint`: **0 errors**.
- `npm --prefix apps/web test`: **All 5 test suites passed**.
- `npm --prefix apps/web run build`: **Next.js 14 production build completed successfully**.
- `python scripts/verify_acceptance_tests.py`: **6/6 passed**.
- `python scripts/verify_enhancements.py`: **30/30 passed**.
- `python backend/tests/test_inventory.py`: **5/5 passed**.

---

## 4. How to Run the Platform

To resolve the `localhost refused to connect` error, ensure both backend and frontend servers are running:

### Option A: 1-Click PowerShell Launchers (Recommended)
Run the automated startup script in PowerShell:
```powershell
.\start_servers.ps1
```
*This script terminates any zombie processes holding ports 8000/3000, launches FastAPI on port 8000 in a dedicated window, launches Next.js on port 3000 in a dedicated window, and confirms when services are ready.*

To stop all services later:
```powershell
.\stop_servers.ps1
```

### Option B: Manual Two-Terminal Execution
Open two PowerShell terminals in `c:\Users\PrabSandhu\Documents\codes\Agritech_`:

**Terminal 1 (Backend)**:
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend)**:
```powershell
npm --prefix apps/web run dev -- -p 3000
```

Once started, open [http://localhost:3000](http://localhost:3000) in your browser.

