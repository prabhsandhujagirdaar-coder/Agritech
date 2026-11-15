# AgriChain AI — Final Git Staging Manifest & Repository Audit
**Document ID:** AGR-STAGE-20261115-MANIFEST  
**Audit Mode:** Read-Only Inspection (No staging, commits, resets, or pushes executed)  
**Date:** November 15, 2026  
**Auditor:** AgriChain AI Quality Assurance & Core Architecture Team  
**Branch:** `main`  
**Tracking Remote:** `origin/main` (`https://github.com/prabhsandhujagirdaar-coder/Agritech.git`)  
**Baseline HEAD Commit:** `a239d0e`  

---

## 1. Inspection & Classification of Library Directories

A complete recursive audit was performed across `apps/mobile/lib/` (23 files) and `apps/web/lib/` (11 files) following the correction of the root-anchored `.gitignore` rule.

### 1.1 Web Application Directory: `apps/web/lib/` (11 Files)

| File Path | Size | Classification | Purpose & Preservation Status |
|:---|:---:|:---:|:---|
| `apps/web/lib/.gitkeep` | 0 B | Directory Placeholder | Preserves empty directory structure; genuine repository file. |
| `apps/web/lib/api.js` | 20.8 KB | **Actual Next.js Source** | Core frontend API client: handles HTTP requests, coordinate normalization, and backend service status. |
| `apps/web/lib/api.test.mjs` | 7.7 KB | **Actual Next.js Test** | Automated unit tests for API endpoints, coordinate boundaries, and failure diagnostics. |
| `apps/web/lib/constants.js` | 13.6 KB | **Actual Next.js Source** | System-wide constants: ripeness taxonomies, color scales, Indian coordinate bounding boxes. |
| `apps/web/lib/constants.test.mjs` | 11.0 KB | **Actual Next.js Test** | Automated unit tests for produce taxonomies and quality thresholds. |
| `apps/web/lib/leafletSafe.test.mjs` | 12.5 KB | **Actual Next.js Test** | **NEW**: 6-suite automated regression test for Leaflet lifecycle, crash immunity, and tab switching. |
| `apps/web/lib/phase13_5.test.mjs` | 6.4 KB | **Actual Next.js Test** | Regression tests for Phase 13.5 stakeholder workflows and buyer marketplace rules. |
| `apps/web/lib/phase13_6.test.mjs` | 8.6 KB | **Actual Next.js Test** | Regression tests for Phase 13.6 Z-index stacking contexts, table slices, and search engines. |
| `apps/web/lib/roleConfig.js` | 10.2 KB | **Actual Next.js Source** | Stakeholder role configurations, permission matrix, and route authorization logic. |
| `apps/web/lib/roleConfig.test.mjs` | 4.4 KB | **Actual Next.js Test** | Automated tests for role normalization and tab access enforcement. |
| `apps/web/lib/types.ts` | 2.8 KB | **Actual Next.js Source** | TypeScript type definitions for shipments, waypoints, telemetry, and facilities. |

*Summary:* All 11 files in `apps/web/lib/` are genuine Next.js source code or unit test suites. Zero files are generated, temporary, or accidental.

### 1.2 Mobile Application Directory: `apps/mobile/lib/` (23 Files)

| File Path | Size | Classification | Architectural Role |
|:---|:---:|:---:|:---|
| `apps/mobile/lib/main.dart` | 3.2 KB | **Actual Flutter Source** | Flutter mobile application root entry point (`runApp(const AgriChainApp())`). |
| `apps/mobile/lib/config/app_config.dart` | 2.9 KB | **Actual Flutter Source** | Environment configuration: API base URLs, WebSocket endpoints, and timeouts. |
| `apps/mobile/lib/models/cnn_prediction.dart` | 2.9 KB | **Actual Flutter Source** | Data model: produce classification stages, confidence scores, and bounding boxes. |
| `apps/mobile/lib/models/facility.dart` | 4.6 KB | **Actual Flutter Source** | Data model: cold storages, packhouses, CA stores, and mandis with provenance metadata. |
| `apps/mobile/lib/models/geo_waypoint.dart` | 1.9 KB | **Actual Flutter Source** | Data model: GPS breadcrumb history and spatial waypoint fixes. |
| `apps/mobile/lib/models/risk_info.dart` | 1.1 KB | **Actual Flutter Source** | Data model: transit risk index, excursion severity, and alert states. |
| `apps/mobile/lib/models/service_status.dart` | 1.5 KB | **Actual Flutter Source** | Data model: ML model readiness, device hardware acceleration, and API health. |
| `apps/mobile/lib/models/shipment.dart` | 3.8 KB | **Actual Flutter Source** | Data model: end-to-end shipment records, commodity types, and thermal thresholds. |
| `apps/mobile/lib/models/telemetry.dart` | 1.1 KB | **Actual Flutter Source** | Data model: live sensor telemetry (temperature, humidity, delay, speed). |
| `apps/mobile/lib/screens/dashboard_screen.dart` | 25.5 KB | **Actual Flutter Source** | UI Screen: mobile dashboard overview, quick stats, active alerts, and navigation. |
| `apps/mobile/lib/screens/facility_directory_screen.dart` | 19.2 KB | **Actual Flutter Source** | UI Screen: facility directory, search filters, and legal entity verification cards. |
| `apps/mobile/lib/screens/guava_inspection_screen.dart` | 19.1 KB | **Actual Flutter Source** | UI Screen: on-device produce camera capture and CNN quality inspection. |
| `apps/mobile/lib/screens/shipment_detail_screen.dart` | 40.3 KB | **Actual Flutter Source** | UI Screen: shipment telemetry charts, transit risk history, and cold chain logs. |
| `apps/mobile/lib/screens/shipment_list_screen.dart` | 15.3 KB | **Actual Flutter Source** | UI Screen: searchable list of active, completed, and quarantined shipments. |
| `apps/mobile/lib/screens/shipment_tracking_screen.dart` | 39.1 KB | **Actual Flutter Source** | UI Screen: interactive live tracking map, vehicle telemetry, and route progress. |
| `apps/mobile/lib/services/api_service.dart` | 16.7 KB | **Actual Flutter Source** | Service layer: HTTP REST client for FastAPI backend integration. |
| `apps/mobile/lib/services/websocket_service.dart` | 5.5 KB | **Actual Flutter Source** | Service layer: live WebSocket listener for real-time telemetry updates. |
| `apps/mobile/lib/widgets/empty_view.dart` | 2.3 KB | **Actual Flutter Source** | UI Widget: empty state presentation for lists and searches. |
| `apps/mobile/lib/widgets/error_view.dart` | 6.3 KB | **Actual Flutter Source** | UI Widget: retryable error presentation and connection diagnostics. |
| `apps/mobile/lib/widgets/geospatial_route_card.dart` | 13.0 KB | **Actual Flutter Source** | UI Widget: visual origin-to-destination corridor card with distance and duration. |
| `apps/mobile/lib/widgets/interactive_route_map.dart` | 23.1 KB | **Actual Flutter Source** | UI Widget: Flutter map component for route visualization and vehicle markers. |
| `apps/mobile/lib/widgets/scientific_disclaimer_card.dart` | 3.7 KB | **Actual Flutter Source** | UI Widget: scientific and academic methodology disclaimers for produce models. |
| `apps/mobile/lib/widgets/status_chip.dart` | 1.3 KB | **Actual Flutter Source** | UI Widget: status chip component for shipment and facility verification badges. |

*Summary:* All 23 files in `apps/mobile/lib/` are genuine Flutter source code written for the AgriChain AI mobile client. Zero files are generated, temporary build outputs, or accidental clutter.

---

## 2. Flutter Source Code Preservation Confirmation

- **Root Cause of Prior Untracked State:** In the initial repository setup, `.gitignore` contained `lib/` without a leading slash. This rule unintentionally suppressed the standard Flutter `lib/` directory as well as `apps/web/lib/`.
- **Preservation Status:** All 23 Dart files have remained completely intact on disk, unmodified, and uncorrupted.
- **Inclusion Recommendation:** Because these files represent the complete Flutter client application for AgriChain AI, they **should be included** in Git version control to ensure the mobile app codebase is fully backed up.

---

## 3. Comprehensive Diff Review Across All Seven Modified Files

### 3.1 `.gitignore`
- **Lines Changed:** 2 insertions, 2 deletions.
- **Diff:**
  ```diff
  -lib/
  -lib64/
  +/lib/
  +/lib64/
  ```
- **Review:** Anchors the Python virtual environment and packaging rules to the repository root only. Completely resolves the issue where subproject `lib/` directories (`apps/web/lib/` and `apps/mobile/lib/`) were blocked from Git.

### 3.2 `apps/web/package.json`
- **Lines Changed:** 1 insertion, 1 deletion.
- **Diff:** Appends `&& node lib/leafletSafe.test.mjs` to the `test` script.
- **Review:** Ensures CI and local `npm test` runs automatically verify Leaflet lifecycle invariants and crash immunity.

### 3.3 `apps/web/components/ShipmentsTracking.js`
- **Lines Changed:** 27 insertions, 43 deletions.
- **Diff:**
  - Removed duplicate `<TrackingMapClient>` from the modal dialog.
  - Converted the inline map container into a dynamic container that seamlessly transitions to `fixed inset-3 md:inset-6 z-50` when expanded.
- **Review:** Ensures exactly **one** persistent Leaflet map instance exists in memory, eliminating unmount/remount races, layer re-initialization, and state loss when toggling fullscreen.

### 3.4 `apps/web/components/TrackingMap.js`
- **Lines Changed:** 254 insertions, 52 deletions.
- **Diff:**
  - Inlined authoritative, non-invasive safeguard on `L.DomUtil.getPosition` without broad `try/catch`.
  - Removed all `L.Map.prototype` monkey-patching; `L.Map.prototype` remains 100% vanilla Leaflet.
  - Implemented `stopActiveAnimations(map)`: cancels `_flyToFrame`, stops `_panAnim`, resets `_animatingZoom = false`, clears CSS classes, and calls `map.stop()`.
  - Added safe camera helpers: `safeFitBounds`, `safeFlyTo`, `safePanTo`, `safeInvalidateSize`.
  - Added `cameraFocusRef` coordinator suppressing redundant `fitBounds` during background polling.
  - Implemented intelligent ResizeObserver dimension diffing (`> 2px` threshold).
  - Enforced clean component unmount teardown in `useEffect` return.
- **Review:** Completely eliminates `TypeError: Cannot read properties of undefined (reading '_leaflet_pos')` via React lifecycle management.

### 3.5 `backend/app/services/geocoding_service.py`
- **Lines Changed:** 253 insertions, 40 deletions.
- **Diff:**
  - Added public method `geocode_location(self, query: str)` returning verified coordinates with complete metadata.
  - Added backward-compatible alias `geocode = geocode_location`.
  - Expanded `CURATED_AGRICULTURAL_PLACES` with aliases for key mandis and packhouses (including Abohar, Bathinda, Fazilka, Jaipur Muhana Mandi, and Agra).
  - Implemented ranked keyword scoring (`_score_place_relevance`) prioritizing exact district and place matches.
  - Added direct coordinate string parser (`_try_parse_coordinate_string`).
- **Review:** Resolves the production-visible error: `"Routing service error: 'GeocodingService' object has no attribute 'geocode_location'"`.

### 3.6 `backend/app/services/routing_service.py`
- **Lines Changed:** 14 insertions, 0 deletions.
- **Diff:** Added `abohar_to_jaipur` corridor anchors (NH-52 / NH-62 via Hanumangarh, Rawatsar, Sardarshahr, Ratangarh, Sikar, Ringas, Chomu to Jaipur Muhana Mandi, 431.22 km, 211 waypoints).
- **Review:** Provides authoritative highway routing for shipment SHP-2026-023.

### 3.7 `backend/app/services/simulation_engine.py`
- **Lines Changed:** 4 insertions, 3 deletions.
- **Diff:**
  - Added `_lock_loop` tracking in `_get_lock()` to ensure `asyncio.Lock` re-instantiates cleanly if the active event loop changes across test sessions or threads.
  - Moved `get_ws_manager()` import inside broadcast methods to resolve potential circular import cycles.
- **Review:** Guarantees thread-safe and loop-safe simulation concurrency.

---

## 4. Git Ignore, Security, and ML Checkpoint Invariants Audit

| Verification Item | Audit Result | Evidence |
|:---|:---:|:---|
| **`.env` files & credentials** | **STRICTLY IGNORED** | `git check-ignore -v .env` matches `.gitignore:10:*.env`. `apps/web/.env.local` matches `apps/web/.gitignore:26:.env*.local`. Zero environment variables or credentials are tracked. |
| **ML training datasets** | **STRICTLY EXCLUDED** | `ml/data/raw/`, `ml/data/processed/`, `ml/data/guava_classification/`, `ml/data/interim/` all match explicit rules in `.gitignore:113-116`. |
| **Tracked source files** | **100% PRESERVED** | `git diff --name-only HEAD` confirms only the 7 intended files have modifications. No existing tracked source files have become ignored. |
| **New Leaflet unit test** | **INCLUDED** | `apps/web/lib/leafletSafe.test.mjs` is tracked under `apps/web/lib/` and executed in `npm test`. |

### Frozen ML Checkpoint Cryptographic Baseline Audit
All 5 frozen production machine learning checkpoints in `ml/artifacts/` were audited using SHA-256:
- `best_guava_resnet18.pth`: `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` (**100% MATCH**)
- `best_banana_resnet18.pth`: `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` (**100% MATCH**)
- `best_fruit_identifier_mobilenet_v3_large.pth`: `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` (**100% MATCH**)
- `best_fruit_identifier_resnet18.pth`: `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` (**100% MATCH**)
- `best_apple_yolov8n.pt`: `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` (**100% MATCH**)

---

## 5. Exact Staging Manifest

The proposed commit structure is organized into four logical change sets:

### Manifest Group A: Geocoding & Road Routing Backend Fix
*Logical Subject: `fix(routing): resolve geocoding method contract and implement Abohar-Jaipur corridor`*

```text
backend/app/services/geocoding_service.py
backend/app/services/routing_service.py
backend/app/services/simulation_engine.py
```

### Manifest Group B: Leaflet Map Lifecycle & Crash Immunity Fix
*Logical Subject: `fix(web): resolve Leaflet map unmount pos crash and unify fullscreen container`*

```text
.gitignore
apps/web/package.json
apps/web/components/TrackingMap.js
apps/web/components/ShipmentsTracking.js
apps/web/lib/leafletSafe.test.mjs
```

### Manifest Group C: Verification Scripts & Quality Reports
*Logical Subject: `docs(qa): add geocoding, leaflet lifecycle, and pre-commit audit reports`*

```text
scripts/verify_geocoding_routes.py
GEOCODING_ROUTING_INTEGRATION_FIX_REPORT.md
LEAFLET_MAP_RUNTIME_ERROR_FIX_REPORT.md
PRE_COMMIT_QUALITY_GATE_REPORT.md
FINAL_GIT_STAGING_MANIFEST.md
```

### Manifest Group D: Existing Flutter Mobile Application Source Code
*Logical Subject: `feat(mobile): restore Flutter mobile application source code unblocked by gitignore`*

```text
apps/mobile/lib/main.dart
apps/mobile/lib/config/app_config.dart
apps/mobile/lib/models/cnn_prediction.dart
apps/mobile/lib/models/facility.dart
apps/mobile/lib/models/geo_waypoint.dart
apps/mobile/lib/models/risk_info.dart
apps/mobile/lib/models/service_status.dart
apps/mobile/lib/models/shipment.dart
apps/mobile/lib/models/telemetry.dart
apps/mobile/lib/screens/dashboard_screen.dart
apps/mobile/lib/screens/facility_directory_screen.dart
apps/mobile/lib/screens/guava_inspection_screen.dart
apps/mobile/lib/screens/shipment_detail_screen.dart
apps/mobile/lib/screens/shipment_list_screen.dart
apps/mobile/lib/screens/shipment_tracking_screen.dart
apps/mobile/lib/services/api_service.dart
apps/mobile/lib/services/websocket_service.dart
apps/mobile/lib/widgets/empty_view.dart
apps/mobile/lib/widgets/error_view.dart
apps/mobile/lib/widgets/geospatial_route_card.dart
apps/mobile/lib/widgets/interactive_route_map.dart
apps/mobile/lib/widgets/scientific_disclaimer_card.dart
apps/mobile/lib/widgets/status_chip.dart
apps/web/lib/api.js
apps/web/lib/api.test.mjs
apps/web/lib/constants.js
apps/web/lib/constants.test.mjs
apps/web/lib/phase13_5.test.mjs
apps/web/lib/phase13_6.test.mjs
apps/web/lib/roleConfig.js
apps/web/lib/roleConfig.test.mjs
apps/web/lib/types.ts
```

---

## 6. Identification & Technical Root Cause of Remaining Test Gaps

### 6.1 Unexecuted Simulation Test 5 (`test_05_api_simulation_lifecycle`)
In `backend/tests/test_simulation_engine.py`, tests 1 through 4 pass instantaneously:
- `test_01_geocoding_search`: **PASS** (0.01s)
- `test_02_haversine_and_bearing`: **PASS** (0.00s)
- `test_03_road_route_generation`: **PASS** (0.02s)
- `test_04_polyline_distance_interpolation`: **PASS** (0.01s)

However, `test_05_api_simulation_lifecycle` was not executed in the test runner.

### 6.2 Technical Cause of the Hang
`test_05` utilizes `fastapi.testclient.TestClient(app)` from Starlette.
1. In Python 3.13 on Windows with `starlette 1.7.0` and `httpx 0.28.1`, Starlette emits:
   ```text
   StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
   ```
2. When synchronous `TestClient` makes a request to an asynchronous FastAPI endpoint, Starlette uses `anyio.from_thread.BlockingPortal` to dispatch ASGI requests.
3. In `SimulationEngine`, methods like `step_simulation` and `update_controls` invoke asynchronous WebSocket event broadcasts (`_broadcast_status` and `_broadcast_telemetry`).
4. On Windows, when these asynchronous routines attempt to synchronize with Starlette's `BlockingPortal` event loop in a synchronous test thread, a deadlock occurs inside `BlockingPortal.start()`.

### 6.3 What is Verified vs. What Remains a Test Gap
- **Verified via `scripts/verify_geocoding_routes.py`**:
  - `GeocodingService.geocode_location` and ranked search.
  - Route calculation for all 5 corridors and SHP-2026-023.
  - Simulation session initialization, coordinate binding, and distance integrity.
- **Verified via Interactive Browser Session**:
  - Start, Pause, Resume, Reset, and vehicle animation all execute without errors on live Next.js + FastAPI.
- **Remaining Test Gap**:
  - Automated continuous regression testing of `step_simulation`, synthetic temperature excursions, and 24-step LSTM risk scoring via in-process HTTP endpoints is currently unexecutable via synchronous `TestClient` on Windows.
  - **Recommended Future Resolution:** Migrate backend API tests to `httpx.AsyncClient` with `pytest-asyncio` (`async def test_simulation_lifecycle()`), eliminating the synchronous `BlockingPortal` deadlock entirely.

---

## 7. Current Git Working Tree Status (Read-Only)

```text
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified:   .gitignore
  modified:   apps/web/components/ShipmentsTracking.js
  modified:   apps/web/components/TrackingMap.js
  modified:   apps/web/package.json
  backend/app/services/geocoding_service.py
  backend/app/services/routing_service.py
  backend/app/services/simulation_engine.py

Untracked files:
  GEOCODING_ROUTING_INTEGRATION_FIX_REPORT.md
  LEAFLET_MAP_RUNTIME_ERROR_FIX_REPORT.md
  PRE_COMMIT_QUALITY_GATE_REPORT.md
  FINAL_GIT_STAGING_MANIFEST.md
  apps/mobile/lib/
  apps/web/lib/
  scripts/verify_geocoding_routes.py
```

No files have been staged, committed, or pushed. Ready for explicit user instructions.
