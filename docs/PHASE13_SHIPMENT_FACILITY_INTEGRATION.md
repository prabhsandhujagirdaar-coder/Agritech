# AgriChain AI — Phase 13: Real Guava Shipment & Facility Integration Report

**Date:** October 28, 2026  
**Primary Crop:** Guava (*Psidium guajava*)  
**Status:** Completed & Tested (72 Backend Pytest Tests, 100% Frontend Unit Tests, Zero Lint Errors, Production Build Verified)

---

## 1. Executive Summary

Phase 13 establishes truthful, verifiable end-to-end integration between genuine North Indian agricultural facilities (audited in Phase 12.2) and the guava shipment lifecycle. 

Previous phases successfully indexed 12 authentic agricultural facilities across Punjab and Delhi. Phase 13 eliminates synthetic assumptions by strictly enforcing a 4-dimensional suitability model:
1. **Guava Trading:** Verified presence of guava commercial auctions and e-NAM price discovery (e.g. Azadpur APMC, Bhagtanwala Mandi).
2. **Guava Handling:** Verified packhouse pre-cooling, grading, and packing lines (e.g. PAGREXCO Kangmai and Bara Farm).
3. **Guava Cold-Chain Capability:** Verified refrigerated cold stores operating at guava-safe temperatures (8–10°C). Crucially, ambient grain godowns (e.g. PSWC Malout, Fazilka, Bathinda, Ludhiana) are **strictly flagged as unsuitable**, preventing catastrophic spoilage.
4. **Current Operational Availability:** Live operational status (`active`, `unknown`, `maintenance`). In compliance with strict truthfulness rules, unknown availability is **never** converted into confirmed availability.

---

## 2. API Endpoints & Contract Specifications

### 2.1 Facility Suitability Verification
- **Endpoint:** `GET /api/v1/facilities/{facility_id}/suitability`
- **Next.js Proxy:** `GET /api/facilities/{id}/suitability`
- **Query Parameters:**
  - `operation` (`string`, optional): Requested operation (`packhouse_cooling`, `cold_storage`, `market_auction`, `transit_hub`, `harvesting_aggregation`).
  - `crop` (`string`, default: `"Guava"`): Target agricultural commodity.
- **Response Schema (`FacilitySuitabilityResponse`):**
  ```json
  {
    "facility_id": "FAC-DL-AZD-01",
    "facility_name": "Azadpur APMC Fruit & Vegetable Mega Mandi",
    "operation": "market_auction",
    "crop": "Guava",
    "suitable": true,
    "suitability_status": "verified_guava_trading",
    "capabilities": {
      "guava_trading": "verified",
      "guava_handling": "not_verified",
      "guava_cold_chain": "partially_verified",
      "operational_availability": "active"
    },
    "warnings": [],
    "evidence_summary": "Facility 'Azadpur APMC Fruit & Vegetable Mega Mandi' (MANDI): Trading=VERIFIED, Handling=NOT_VERIFIED, ColdChain=PARTIALLY_VERIFIED, Availability=ACTIVE.",
    "source_citation": {
      "source_name": "APMC Azadpur (Market of National Importance) / Govt of NCT of Delhi",
      "source_record": "APMC Azadpur Terminal Market Directory & e-NAM Trading Hub",
      "source_url": "https://apmcazadpurdelhi.com/",
      "source_citation_type": "official_portal",
      "verification_status": "verified",
      "coordinate_source": "Azadpur APMC Market Office Complex, WGS84 Geocode",
      "geocoding_confidence": "facility_campus"
    }
  }
  ```

### 2.2 Multi-Hub Shipment Association
- **Endpoint:** `POST /api/v1/shipments`
- **Next.js Proxy:** `POST /api/shipments`
- **Supported Association Fields:**
  - `origin_facility_id` (`string`, optional): Must match an existing facility in the registry.
  - `destination_facility_id` (`string`, optional): Must match an existing facility in the registry.
  - `intermediate_facility_id` (`string`, optional): Optional transit hub / holding packhouse.
  - `origin_operation` (`string`, default: `"packhouse_cooling"`).
  - `destination_operation` (`string`, default: `"market_auction"`).
  - `intermediate_operation` (`string`, default: `"transit_hub"`).
  - `planned_departure` (`string` ISO-8601, optional).
  - `planned_arrival` (`string` ISO-8601, optional).
- **Backend Validation:**
  - Nonexistent facility IDs return HTTP `422 Unprocessable Content`.
  - Automatically evaluates facility suitability for all assigned operations and attaches `suitability_warnings` to the shipment record.
  - Automatically emits `shipment_created` and `facility_association_updated` custody events.

### 2.3 Auditable Shipment Custody & Event Timeline
- **Endpoints:**
  - `GET /api/v1/shipments/{shipment_id}/events`
  - `POST /api/v1/shipments/{shipment_id}/events`
- **Event Schema (`ShipmentEventRecord`):**
  ```json
  {
    "id": "EVT-SHP-2026-001-1",
    "shipment_id": "SHP-2026-001",
    "event_type": "facility_handover",
    "facility_id": "FAC-PB-PAG-BARA",
    "description": "Pre-cooling verified at PAGREXCO Bara Farm packhouse chambers.",
    "source": "manual_operator",
    "timestamp": "2026-10-22T08:30:00Z"
  }
  ```
- **Duplicate Prevention:**
  - Submissions within 60 seconds with identical `event_type` and `facility_id` are detected as duplicate retries.
  - The repository returns the existing event record idempotently (`HTTP 201`) without appending duplicate timeline entries.

---

## 3. Truthful Tracking & Telemetry Semantics

AgriChain AI strictly rejects deceptive labeling of simulation data:

| Status Badge | Criteria | Interface Behavior |
| :--- | :--- | :--- |
| **LIVE GPS ACTIVE** | Genuine GNSS hardware tracker stream verified via server-side configuration. | Green pulsing badge, coordinate freshness timestamp, satellite icon. |
| **DEMO / SIMULATED ROUTE** | Synthetically advanced PostGIS coordinates or route waypoints. | Amber badge, clear disclaimer that no physical tracker is attached. |
| **LAST KNOWN LOCATION** | GNSS signal lost or connection terminated. | Dark slate badge, preserved timestamp of the last verified position fix. |
| **LIVE IOT SENSOR STREAM** | Physical certified temperature/humidity probe reporting. | Green badge, sensor identifier, excursion monitoring. |
| **SIMULATED TELEMETRY (DEMO)** | Numerically synthesized thermal values. | Amber banner: *"Telemetry values are synthetically simulated for demonstration. No physical probe connected."* |
| **SENSOR HARDWARE UNAVAILABLE**| No telemetry records logged. | Slate badge: *"Sensor readings unavailable."* |

---

## 4. PostgreSQL/PostGIS Readiness & Migration Safeguards

The development environment operates in local file-based mode (`DATABASE_ENABLED=false`). The persistent ledger is safely maintained in `backend/app/db/.persisted_session.json`.

### 4.1 Migration `004_shipment_facilities_and_events.sql`
A reversible, idempotent SQL migration is prepared at `database/migrations/004_shipment_facilities_and_events.sql`:
- Extends table `shipments` with `intermediate_facility_id`, operation types, planned/actual timestamps, `tracking_mode`, and `telemetry_mode`.
- Creates table `shipment_events` with spatial foreign keys and indexing.
- Establishes foreign keys with `ON DELETE SET NULL` to prevent destructive cascading deletes.

### 4.2 Migration Commands (When PostgreSQL is Available)

1. **Pre-Migration Database Backup:**
   ```powershell
   pg_dump -U postgres -h localhost -p 5432 -d agrichain_db -F c -b -v -f "database/backups/backup_pre_phase13_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
   ```

2. **Apply Migration 004:**
   ```powershell
   python database/apply_migrations.py --target 004
   # Or using psql directly:
   psql -U postgres -h localhost -d agrichain_db -f database/migrations/004_shipment_facilities_and_events.sql
   ```

3. **Revert Migration 004 (Rollback):**
   ```powershell
   psql -U postgres -h localhost -d agrichain_db -f database/migrations/004_shipment_facilities_and_events_rollback.sql
   ```

---

## 5. Verification & Test Suite Summary

### Automated Test Runs
1. **Backend Tests (pytest):**
   - Command: `..\.venv\Scripts\pytest -q`
   - Result: **72 passed, 1 skipped** in 26.10s.
   - Coverage: Facility suitability, multi-hub routing, invalid facility IDs, tracking mode classification, telemetry mode classification, duplicate prevention, and file persistence.
2. **Frontend Unit Tests (node:test):**
   - Command: `npm test`
   - Result: **100% Passed**. Verified geospatial boundaries, facility suitability taxonomy, and Phase 13 lifecycle constants.
3. **Frontend Lint (next lint):**
   - Command: `npm run lint`
   - Result: **0 errors**, clean pass across all components and pages.
4. **Frontend Production Build (next build):**
   - Command: `npm run build`
   - Result: **Compiled successfully (10/10 static pages & dynamic API routes)**.

---

## 6. Manual Verification Walkthrough

1. **Start Services:**
   - FastAPI: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   - Next.js: `npm run dev` in `apps/web`
2. **Open Web Browser:** Navigate to `http://localhost:3000/dashboard` and select the **Shipments & Logistics** tab.
3. **Inspect Active Shipment:**
   - Click `SHP-2026-001`.
   - Observe the top **Tracking Transparency Header**: shows `DEMO / SIMULATED ROUTE` or `LIVE GPS ACTIVE` with last fix timestamp.
   - Observe the **Connected Agricultural Facilities** section: displays origin (`PAGREXCO Bara Farm`), destination (`Azadpur APMC Mandi`), verified capability badges (`Trading: Verified`, `Cold Chain: Partial`), and source provenance links.
   - Observe the **Auditable Shipment Custody & Event Timeline**: chronological history with event badges and facility references.
4. **Register a New Multi-Hub Shipment:**
   - Click **+ New Shipment**.
   - Select Origin: `PAGREXCO Packhouse, Kangmai` (Pre-Cooling). Note the dynamic green suitability badge.
   - Select Intermediate Hub: `PSWC Malout` (Cold Storage). Note the dynamic red warning: *"CRITICAL: Facility is a dry ambient grain warehouse with NO refrigeration."*
   - Select Destination: `Azadpur APMC Mega Mandi` (Market Auction). Note the green trading suitability badge.
   - Enter quantity and click **Create Shipment**.
   - Verify the shipment appears with full provenance cards and suitability warnings.
5. **Log a Custody Event:**
   - Click **Record Event** in the event timeline.
   - Choose `Facility Handover Recorded`, select facility, enter notes, and submit.
   - Verify the timeline updates immediately. Submitting the exact same form within 60 seconds is idempotently prevented from duplicating.
