# AgriChain AI — Project State Audit

Date: 2026-10-22
Auditor: automated read-only repository audit (Phase 0)
Scope: repository structure, backend, website, mobile, database, ML artifacts, live services.

This audit reports only what was directly observed in the repository or from the
running services on the audit date. Claims from earlier phase reports are marked
as "reported" until independently verified.

---

## 1. Repository structure (observed)

```
Agritech_/
├── apps/
│   ├── web/          Next.js 14 App Router website (JavaScript, Tailwind)
│   └── mobile/       Flutter Android MVP (Dart)
├── backend/          FastAPI application (app/api/v1, app/db, app/services, ...)
├── ml/               Training code (src/), configs, artifacts (guava checkpoints)
├── database/         migrations/001_initial_postgis_schema.sql (+ rollback)
├── docs/             Phase reports (PHASE8/9/10), docs/ml guava reports
├── scripts/          Dataset, smoke-test and verification scripts
└── compose.yaml      db (PostGIS 16-3.4) + backend + frontend services
```

Git state: branch `master`, **zero commits**. All files are staged or untracked.
This is a data-loss risk — an initial commit is the highest-priority housekeeping task.

---

## 2. Runtime state at audit time

| Service | State | Evidence |
|---|---|---|
| Next.js website | Running, port 3000 | `netstat` LISTENING PID 20784 |
| FastAPI backend | Running, port 8000 | `netstat` LISTENING PID 1248 |
| PostgreSQL/PostGIS | **Not running** | Port 5432 not listening; `docker ps` empty |
| Guava CNN model | **Loaded and ready** on CUDA | `GET /health` → `model_available: true`, `device: cuda`, `model_version: 2.0.0` |
| Database persistence | **Disabled** | `/health` → `database.enabled: false`, "File-based ledger persistence active" |

Toolchain observed: Python 3.13.7, Node v22.19.0.

### Backend configuration risk
There is **no `backend/.env` file**. The running backend process serves guava
(`target_crop: "guava"`), which means it was started with environment variables
(`TARGET_CROP=guava`, `GUAVA_MODEL_ACTIVATED=true`) set only in that process.
If the backend restarts without them, it falls back to `TARGET_CROP=kinnow`,
cannot find `best_kinnow_resnet18.pth` (does not exist), and the CNN endpoint
returns HTTP 503. Recreating `backend/.env` is required before any restart.

---

## 3. API surface (observed in code)

Canonical prefix: `/api/v1`. Compatibility routes are also mounted.

| Route | Purpose | Notes |
|---|---|---|
| `GET /health`, `GET /api/v1/health` | Health + DB + CNN status | Working |
| `POST /predict`, `POST /api/v1/cnn/predict` | Guava image inference | Working (CUDA) |
| `GET /api/v1/cnn/status` | Model status | Working |
| `GET/POST /api/v1/shipments` (+ `/api/shipments` compat) | Shipment CRUD | Working, JSON ledger |
| `GET/PATCH /api/v1/shipments/{id}` | Detail / status update | Working |
| `GET /api/v1/shipments/{id}/risk` | Risk (heuristic formula) | Works, not an ML model |
| `GET/POST .../{id}/telemetry` | Telemetry ingest/read | Working |
| `GET/POST .../{id}/waypoints` | PostGIS-style waypoints | Stored in JSON; PostGIS offline |
| `POST /api/v1/telemetry/predict` (+ `/api/v1/lstm/predict`) | "LSTM" risk | **Heuristic, no LSTM exists** |
| `GET /api/v1/telemetry/{id}` | Single telemetry point | **Fabricates demo data on miss** |
| `WS /ws`, `WS /ws/shipments` | Real-time events | Code present, not re-tested this session |

No authentication or authorization exists on any endpoint.

---

## 4. Feature inventory

| Feature | Current status | Evidence | Defect or missing dependency | Priority | Next action |
|---|---|---|---|---|---|
| Backend API server | Verified working | `/health` returns 200 healthy | Config only in process env; no `.env` file | High | Create `backend/.env` |
| Guava CNN inference | Verified working | `/api/v1/cnn/status` ready, cuda, v2.0.0 | — | — | Preserve; do not retrain |
| "LSTM" cold-chain risk | **Missing (faked)** | `telemetry.py /predict` is a hand formula `(avg_temp-5)*8 + excursions*6.5`; no LSTM artifact anywhere in `ml/artifacts/` | No trained model exists | High | Label honestly as heuristic; plan real model or remove LSTM claims |
| Telemetry GET by ID | Partially working | Returns fabricated demo record when ID not found (`telemetry.py` fallback) | Violates no-fabrication rule | Medium | Return 404 instead |
| Shipment CRUD (REST) | Verified working | `curl /api/shipments` returns records; create/patch endpoints present | Persists to JSON ledger only, not PostgreSQL | High | Enable DB, then re-test |
| PostGIS waypoint storage | Blocked | Migration `001` defines `geo_waypoints` with GiST index; DB server offline | PostgreSQL not running | High | Start `db` service, apply migration |
| PostgreSQL/PostGIS | Blocked | Port 5432 closed; `docker ps` empty; `DATABASE_ENABLED=false` | Docker/compose not started; no `.env` | High | `docker compose up -d db`; set `DATABASE_ENABLED=true` |
| WebSocket gateway | Implemented but unverified | `/ws/shipments` code broadcasts shipment/telemetry/waypoint events | Not exercised this session | Medium | Run `scripts/test_websocket.py` |
| Website landing page | Implemented but unverified | `app/page.js` exists; server on :3000 | Claims "Model Accuracy 97.18%" — conflicts with reported grouped-test accuracy 83.24% and is unverifiable | High | Remove/replace claim; browser-test |
| Dashboard shell + tabs | Partially working | Sidebar lists 9 tabs; single 45 KB `dashboard/page.js` | Farmer/dealer/marketplace/warehouse/analytics tabs have no backend workflows behind them | Medium | Inventory each tab; mark stubs clearly |
| Produce Analysis (CNN upload UI) | Implemented but unverified | Analyze tab + `/api/predict` Next.js proxy route | Browser test pending | High | Test upload end-to-end in browser |
| Logistics Tracking UI | Partially working | Shipment table, create/telemetry modals, WS badge in `ShipmentsTracking.js` | **No map of any kind** | Critical | Add Leaflet map |
| Live tracking map | **Missing** | `leaflet` absent from `package.json`; no map DOM, no tile requests | Never implemented (root cause of "blank map") | Critical | Implement Leaflet + OSM tiles, markers from waypoints |
| Driver GPS tracking | Missing | No `geolocator`/location package in `pubspec.yaml`; no driver location endpoint | — | Phase 3 | Plan after map works |
| Authentication & RBAC | Missing | No auth code, no users table, no login endpoints | — | Phase 4 | Design auth before role workflows |
| Crop batches / orders / traceability | Missing | No endpoints, models or tables | — | Phase 4+ | Design schema after auth |
| Flutter MVP | Implemented but unverified | 4 screens + api_service; `build/` dir shows prior build; `pubspec` has http + image_picker | Not tested this session; no auth; no GPS | Medium | `flutter analyze` + `flutter test` |
| Automated tests | Implemented but unverified | `backend/tests/*` (6 files), `lib/constants.test.mjs` | Not run this session | Medium | Run both suites |
| Git history | Blocked | Zero commits on `master` | Data-loss risk | High | Initial commit |
| Seed data crop label | Partially working | Seed shipments say "Kinnow Mandarin"; live backend crop is guava | Cosmetic/data migration leftover | Low | Update seeds to guava when DB is re-seeded |

---

## 5. Critical risks (ranked)

1. **No git history.** One accidental delete loses the entire project. Make an initial commit immediately.
2. **The map does not exist.** Earlier reports of a "missing/blank map" are explained: no mapping library was ever installed. This is the highest-priority website defect.
3. **"LSTM" is a heuristic formula presented under an ML name.** No model artifact, no training code for it. For academic honesty it must be relabeled (decision-support heuristic) or replaced with a real trained model before Submission C claims it.
4. **PostgreSQL is not actually in use.** All live data sits in `backend/app/db/.persisted_session.json`. A Docker restart of the `db` service plus `DATABASE_ENABLED=true` is needed before claiming PostGIS persistence.
5. **Backend configuration is not persisted** (no `backend/.env`); a restart silently degrades the CNN to HTTP 503.
6. **No authentication.** Every endpoint is public. Required before real users, drivers, or grades are stored.
7. Landing page accuracy claim (97.18%) contradicts the reported 83.24% grouped test metric.
8. `GET /api/v1/telemetry/{id}` fabricates a demo record for unknown IDs.

---

## 6. What is genuinely solid (preserve)

- Guava ResNet18 checkpoint (`ml/artifacts/best_guava_resnet18.pth`, v2.0.0) loads on CUDA with verified class mapping (Green / Mature Green / Ripe) read from checkpoint metadata.
- CNN service layer has honest guards: rejects strawberry checkpoints, refuses to predict without weights, validates image type/size.
- PostGIS migration SQL is well-formed (shipments, telemetry_logs, geo_waypoints with GiST index) and matches the repository's dataclasses.
- Pydantic schemas are clean and shared between the website proxy routes and the backend.
- Flutter app config handles emulator vs physical-device base URLs correctly (`10.0.2.2` + `--dart-define` override) and carries the scientific disclaimers.
- Uncertainty heuristic (top score 0.60 / margin 0.15) is implemented consistently in web and mobile and correctly labeled as a heuristic.

---

## 7. Recommended phase plan (confirmed against audit)

1. **Immediate housekeeping** — initial git commit; create `backend/.env`; fix the two honesty defects (landing accuracy claim, telemetry fabrication fallback).
2. **Phase 1 — Website stabilization** — implement the Leaflet map in the tracking tab; browser-test guava upload; verify each dashboard tab and label stubs.
3. **Phase 2 — Map & tracking** — connect markers to shipment waypoints, WebSocket live updates, simulated-tracking demo clearly labeled as simulated; then bring PostgreSQL up and point persistence at it.
4. **Phase 3 — Android verification** — `flutter analyze`, `flutter test`, APK smoke test against the shared backend.
5. **Phase 4 — Auth & roles** — authentication, then farmer/dealer workflows incrementally.
6. **Phase 5/6** — end-to-end integration and academic documentation, with the LSTM limitation stated plainly.

## 8. First implementation task

Implement the live tracking map: install `leaflet`, add a client-only map component
(dynamic import, OSM tiles, Punjab-centered default view, markers from shipment
waypoints, attribution, empty/loading/error states), and render it inside the
Logistics Tracking tab. Verify in a real browser before marking done.