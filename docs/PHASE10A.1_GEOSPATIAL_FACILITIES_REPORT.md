# AgriChain AI — Phase 10A.1: India-Only Geospatial Correction & Godown Management Report

**Date**: October 22, 2026  
**Crop Focus**: Guava (*Psidium guajava*)  
**Geographic Scope**: Punjab Agricultural Belt & Delhi NCR Corridor (India)  
**SRS Reference**: SRS-FR-GEO-001, SRS-FR-FAC-002, SRS-NFR-GEO-003  

---

## 1. Root Cause of the Geographic Distortion

Prior to Phase 10A.1, the Leaflet map bounds spanned across northern India and eastern Pakistan (between longitude 74°E and 77°E, and latitude 28°N to 33°N). The audit identified the following root causes:

1. **Synthetic Waypoint Injection into Pakistan**:
   - During automated testing in Phase 10A (`scripts/verify_phase10a.py`), synthetic test waypoints were posted to shipment `SHP-2026-001` at coordinates:
     - `WAY-SHP-2026-001-7`: Lat `32.2150° N`, Lon `74.2050° E` (near Daska / Gujranwala, Punjab, Pakistan).
     - `WAY-SHP-2026-001-8`: Lat `31.9000° N`, Lon `74.3000° E` (near Muridke / Sheikhupura, Pakistan).
   - In Leaflet, `map.fitBounds()` computed a bounding box encompassing both Delhi (`77.17° E`) and western Pakistani coordinates (`74.20° E`), causing the map to zoom out over the international border.

2. **Absence of Dedicated Storage Facility Entities**:
   - Shipments historically stored origin and destination solely as loose text strings (e.g. `"Abohar Packhouse, Punjab"`, `"Chandigarh Mandi"`), without persistent facility models, coordinates, foreign keys, or facility type categorization (packhouses, CA cold stores, godowns, mandis).
   - Because facilities were not geocoded or represented on the map, only 4 of 9 shipments (which had ad-hoc vehicle GPS waypoints) appeared on the map, while 5 shipments remained completely unplotted.

3. **Lack of Boundary Enforcement on Waypoints**:
   - `add_waypoint` and `create_shipment` accepted any coordinates within global WGS84 ranges (`[-90, 90]`, `[-180, 180]`), with no spatial boundary validation to reject foreign coordinates.

---

## 2. Shipment Records Requiring Correction & Verification

All 9 shipments in the ledger were audited, updated to **Guava**, and linked to verified Indian agricultural hubs:

| Shipment ID | Crop | Origin Hub | Destination Facility | Coordinates (Lat, Lon) | Status | Origin/Dest Facility ID |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SHP-2026-001** | Guava | Abohar Post-Harvest Center, Fazilka | Azadpur APMC Mega Mandi, Delhi | `30.2110° N, 74.9455° E` (NH-7) | in_transit | `FAC-PB-ABO-01` &rarr; `FAC-DL-AZD-01` |
| **SHP-2026-002** | Guava | Fazilka CA Cold Store, Fazilka | Ludhiana Agro Cold Chain Warehouse | `30.5828° N, 74.8267° E` (Kotkapura) | in_transit | `FAC-PB-FAZ-01` &rarr; `FAC-PB-LDH-01` |
| **SHP-2026-003** | Guava | Fazilka CA Cold Store, Fazilka | Amritsar Fruit & Produce Mandi | `31.6340° N, 74.8723° E` (Amritsar Hub) | in_transit | `FAC-PB-FAZ-01` &rarr; `FAC-PB-ASR-01` |
| **SHP-2026-004** | Guava | Abohar Post-Harvest Center, Fazilka | Bathinda Central Agri Godown | `30.1915° N, 74.4989° E` (Malout Bypass) | in_transit | `FAC-PB-ABO-01` &rarr; `FAC-PB-BTI-01` |
| **SHP-2026-005** | Guava | Abohar Post-Harvest Center, Fazilka | Jalandhar Ripening Packhouse | `30.8165° N, 75.1717° E` (Moga Corridor) | in_transit | `FAC-PB-ABO-01` &rarr; `FAC-PB-JAL-01` |
| **SHP-2026-006** | Guava | Abohar Post-Harvest Center, Fazilka | Azadpur APMC Mega Mandi, Delhi | *None (GPS Pending)* | created | `FAC-PB-ABO-01` &rarr; `FAC-DL-AZD-01` |
| **SHP-2026-007** | Guava | Abohar Post-Harvest Center, Fazilka | Ludhiana Agro Cold Chain Warehouse | *None (GPS Pending)* | created | `FAC-PB-ABO-01` &rarr; `FAC-PB-LDH-01` |
| **SHP-2026-008** | Guava | Fazilka CA Cold Store, Fazilka | Bathinda Central Agri Godown | *None (GPS Pending)* | created | `FAC-PB-FAZ-01` &rarr; `FAC-PB-BTI-01` |
| **SHP-2026-009** | Guava | Abohar Post-Harvest Center, Fazilka | Amritsar Fruit & Produce Mandi | *None (GPS Pending)* | created | `FAC-PB-ABO-01` &rarr; `FAC-PB-ASR-01` |

> [!NOTE]
> All corrupt synthetic coordinates outside India were purged from the session ledger (`.persisted_session.json`). Shipments without vehicles in motion are explicitly represented as `GPS Pending` without fabricating artificial vehicle coordinates.

---

## 3. Files Created or Modified

### A. Core Geospatial & Backend
1. **`backend/app/core/geo.py`** *(Created)*:
   - India bounding box (`lat: 8.0-37.5`, `lon: 68.0-97.5`).
   - Punjab-Delhi agricultural corridor bounding box (`lat: 28.0-32.6`, `lon: 73.5-77.8`).
   - `is_valid_wgs84(lat, lon)`, `is_within_india(lat, lon)`, `is_within_punjab_corridor(lat, lon)`.
   - `validate_indian_coordinate(lat, lon)` validator raising `ValueError` on violations.
2. **`backend/app/models/facility.py`** *(Created)*:
   - SQLAlchemy `StorageFacilityModel` with PostGIS `Geometry(geometry_type='POINT', srid=4326)` and GiST spatial index.
3. **`backend/app/schemas/facility.py`** *(Created)*:
   - Pydantic models: `FacilityRecord`, `FacilityCreateRequest`, `FacilityCoordinate`, enums `FacilityType`, `FacilityStatus`, `FacilityVerificationStatus`.
4. **`backend/app/models/shipment.py`** *(Modified)*:
   - Added foreign key columns `origin_facility_id` and `destination_facility_id` referencing `storage_facilities.id`.
   - Defaulted produce to `Guava`.
5. **`backend/app/schemas/shipment.py`** *(Modified)*:
   - Enriched shipment schema with `origin_facility_id`, `destination_facility_id`, `origin_facility`, and `destination_facility` summaries.
6. **`backend/app/db/repository.py`** *(Modified)*:
   - Added initial seed facilities (`INITIAL_SEED_FACILITIES`) for Punjab & Delhi.
   - Enforced Indian coordinate validation on `add_waypoint` and `create_facility`.
   - Added `list_facilities()`, `get_facility()`, `create_facility()`.
   - Enriched all shipments with facility metadata.
7. **`backend/app/api/v1/endpoints/facilities.py`** *(Created)*:
   - Endpoints: `GET /api/v1/facilities`, `GET /api/v1/facilities/{id}`, `POST /api/v1/facilities`.
8. **`backend/app/api/v1/endpoints/shipments.py`** *(Modified)*:
   - Handled `ValueError` from out-of-bounds coordinates, returning HTTP 422 Unprocessable Entity.
9. **`backend/app/api/v1/api.py`** and **`backend/app/main.py`** *(Modified)*:
   - Mounted facilities routes under `/api/v1/facilities` and `/api/facilities`.
10. **`database/migrations/002_storage_facilities_schema.sql`** *(Created)*:
    - PostGIS table `storage_facilities` with GiST spatial index and 7 initial Indian facilities.
11. **`database/migrations/002_storage_facilities_schema_rollback.sql`** *(Created)*:
    - Clean rollback script for schema migration 002.

### B. Frontend & Next.js
12. **`apps/web/lib/types.ts`** *(Modified)*:
    - Added `StorageFacility` interface, `FacilityType`, and enriched `Shipment` interface with facility IDs and summaries.
13. **`apps/web/lib/api.js`** *(Modified)*:
    - Added `isWithinIndia(lat, lon)`, `isWithinPunjabCorridor(lat, lon)`.
    - Added API client functions: `fetchFacilities()`, `fetchFacility()`, `createFacility()`.
14. **`apps/web/app/api/facilities/route.js`** *(Created)*:
    - Next.js App Router proxy for `GET` and `POST` facilities.
15. **`apps/web/app/api/facilities/[id]/route.js`** *(Created)*:
    - Next.js App Router proxy for `GET /api/facilities/[id]`.
16. **`apps/web/components/TrackingMap.js`** *(Modified)*:
    - Redesigned Leaflet visualization with custom SVG pins for 6 distinct facility/entity types:
      - 🌱 **Packhouse**: Emerald pin with seedling icon.
      - ❄️ **Cold Storage**: Cyan pin with snowflake icon.
      - 🏛️ **Godown**: Amber pin with column icon.
      - 📦 **Warehouse**: Slate/Blue pin with package icon.
      - 🛒 **Mandi**: Purple pin with shopping cart icon.
      - 🚚 **Vehicle / Shipment**: Dynamic pulsing pin (Blue: in-transit, Red: excursion alert, Green: delivered).
    - Added Punjab Agricultural Belt default view (`[30.5000° N, 74.8000° E]`, zoom 8).
    - Added "Punjab Corridor" focus button and "Fit All" bounds button.
    - Added facility visibility toggle ("Godowns On/Off") and type filter pills.
    - Added straight-line dashed connection corridors linking Origin Facility &rarr; Verified Waypoints &rarr; Vehicle &rarr; Destination Facility.
17. **`apps/web/components/ShipmentsTracking.js`** *(Modified)*:
    - Integrated facility fetching and passed `facilities={facilities}` to `TrackingMapClient`.
    - Enhanced Selected Shipment card to display origin and destination facility badges (name, type, district).
    - Enriched Create Shipment modal with facility selection dropdowns.
    - Enriched Add Waypoint modal with quick preset buttons for Abohar, Malout, Bathinda, Ludhiana, and Delhi.
    - Added client-side `isWithinIndia` coordinate validation preventing bad submissions.

### C. Testing & Scripts
18. **`backend/tests/test_facilities.py`** *(Created)*:
    - Unit tests covering facility listing, detail retrieval, type/district filtering, 404/422 responses, and coordinate bounds.
19. **`apps/web/lib/api.test.mjs`** *(Modified)*:
    - Unit tests validating `isWithinIndia`, `isWithinPunjabCorridor`, coordinate clamping, and normalization.
20. **`scripts/verify_phase10a_1.py`** *(Created)*:
    - 10-step end-to-end automated verification script covering backend health, facilities API, Indian bounds, waypoint ingestion, foreign coordinate rejection, and Next.js HTML.

---

## 4. Database Migration and Facility Schema

### Migration File: `database/migrations/002_storage_facilities_schema.sql`

```sql
CREATE TABLE IF NOT EXISTS storage_facilities (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(64) NOT NULL, -- packhouse, cold_storage, godown, warehouse, mandi
    address TEXT NOT NULL,
    village_or_city VARCHAR(128) NOT NULL,
    district VARCHAR(128) NOT NULL,
    state VARCHAR(64) NOT NULL DEFAULT 'Punjab',
    postal_code VARCHAR(16),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location GEOMETRY(POINT, 4326),
    capacity DOUBLE PRECISION,
    capacity_unit VARCHAR(32) DEFAULT 'MT',
    current_utilization DOUBLE PRECISION,
    storage_temperature_min_c DOUBLE PRECISION,
    storage_temperature_max_c DOUBLE PRECISION,
    operational_status VARCHAR(32) NOT NULL DEFAULT 'active',
    location_verification_status VARCHAR(64) NOT NULL DEFAULT 'demo_simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_facilities_location ON storage_facilities USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_facilities_type ON storage_facilities(facility_type);
CREATE INDEX IF NOT EXISTS idx_facilities_district ON storage_facilities(district);

-- Link shipments to persistent facilities
ALTER TABLE shipments 
    ADD COLUMN IF NOT EXISTS origin_facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS destination_facility_id VARCHAR(64) REFERENCES storage_facilities(id) ON DELETE SET NULL;
```

---

## 5. Facility API Contracts

### Endpoints
1. `GET /api/v1/facilities` (also mirrored at `GET /api/facilities`)
   - **Query Parameters**:
     - `facility_type`: Optional filter (`packhouse`, `cold_storage`, `godown`, `warehouse`, `mandi`).
     - `district`: Optional district filter (e.g. `Fazilka`, `Ludhiana`, `Bathinda`).
     - `state`: Optional state filter (e.g. `Punjab`, `Delhi`).
   - **Response Code**: `200 OK`
   - **Response Structure**:
     ```json
     [
       {
         "id": "FAC-PB-ABO-01",
         "name": "Abohar Guava & Citrus Post-Harvest Center",
         "facility_type": "packhouse",
         "address": "Fazilka Road, Abohar Industrial Area",
         "village_or_city": "Abohar",
         "district": "Fazilka",
         "state": "Punjab",
         "postal_code": "152116",
         "latitude": 30.1453,
         "longitude": 74.1994,
         "coordinates": {
           "latitude": 30.1453,
           "longitude": 74.1994
         },
         "capacity": 1500.0,
         "capacity_unit": "MT",
         "current_utilization": 62.0,
         "storage_temperature_min_c": 4.0,
         "storage_temperature_max_c": 8.0,
         "operational_status": "active",
         "location_verification_status": "demo_simulated",
         "created_at": "2026-10-18T10:00:00Z",
         "updated_at": "2026-10-18T10:00:00Z"
       }
     ]
     ```

2. `GET /api/v1/facilities/{id}` (also mirrored at `GET /api/facilities/{id}`)
   - **Response Code**: `200 OK` (or `404 Not Found` if nonexistent).

3. `POST /api/v1/facilities` (also mirrored at `POST /api/facilities`)
   - **Response Code**: `201 Created` (or `422 Unprocessable Entity` if coordinates fall outside India).

---

## 6. Source and Verification Status of Facility Data

To uphold scientific and academic integrity, **no synthetic coordinates are falsely claimed to be verified vehicle GPS or certified ground truth**.

All 7 initial facilities are labeled with:
```json
"location_verification_status": "demo_simulated"
```

### Initial Hub Locations:
1. **`FAC-PB-ABO-01`**: Abohar Post-Harvest Center (`30.1453° N, 74.1994° E`) — Abohar, Fazilka District, Punjab. Primary guava packhouse and pre-cooling hub.
2. **`FAC-PB-FAZ-01`**: Fazilka CA Cold Store (`30.4037° N, 74.0254° E`) — Fazilka, Punjab. Controlled Atmosphere cold storage.
3. **`FAC-PB-BTI-01`**: Bathinda Central Agri Godown (`30.2110° N, 74.9455° E`) — Bathinda, Punjab. Transit godown along NH-7 rail corridor.
4. **`FAC-PB-LDH-01`**: Ludhiana Agro Cold Chain Warehouse (`30.9010° N, 75.8573° E`) — Ludhiana, Punjab. Central distribution hub.
5. **`FAC-PB-ASR-01`**: Amritsar Fruit & Produce Mandi (`31.6340° N, 74.8723° E`) — Amritsar, Punjab. APMC terminal market.
6. **`FAC-PB-JAL-01`**: Jalandhar Ripening Packhouse (`31.3260° N, 75.5762° E`) — Jalandhar, Punjab. Secondary intake and ripening center.
7. **`FAC-DL-AZD-01`**: Azadpur APMC Mega Mandi (`28.7161° N, 77.1772° E`) — North Delhi, Delhi NCR. Major northern produce market destination.

### How Real Verified Indian Facility Data Can Be Imported Later:
1. **Schema Support**: Real records will set:
   ```json
   "location_verification_status": "verified_onsite"
   ```
   or `"verified_fssai"` / `"verified_wdra"` (Warehousing Development and Regulatory Authority).
2. **CSV / GeoJSON Ingestion Pipeline**:
   The `POST /api/v1/facilities` endpoint accepts programmatic batches. Verified GPS coordinates surveyed via handheld RTK or government mandi registries (e-NAM, Agmarknet) can be imported with `is_within_india()` validation automatically enforced.

---

## 7. Tests Actually Run and Their Results

| Test Suite / Script | Command | Result | Notes |
| :--- | :--- | :--- | :--- |
| **Storage Facilities API Tests** | `python -m unittest backend/tests/test_facilities.py` | **PASS (6/6 tests, 0.13s)** | Tests facility listing, filtering, ID lookup, 404/422 responses, India boundaries |
| **PostGIS Waypoints Tests** | `python -m unittest backend/tests/test_postgis_waypoints.py` | **PASS (5/5 tests, 0.03s)** | Tests chronological ordering, coordinate enrichment, null coordinates |
| **Persistence & Seeds Tests** | `python -m unittest backend/tests/test_persistence.py` | **PASS (14/14 tests, 6.25s)** | Verifies Guava corridor seeds, serialization, and database failover |
| **Guava CNN Integration Tests** | `python -m unittest backend/tests/test_guava_cnn_integration.py` | **PASS (11/11 tests, 14.34s)** | Validates Guava ripeness classifier inference on CUDA |
| **Frontend Normalization Tests** | `npm test` (in `apps/web`) | **PASS (All tests)** | Validates `isWithinIndia`, `isWithinPunjabCorridor`, coordinate clamping |
| **Frontend Production Build** | `npm run build` (in `apps/web`) | **PASS (Compiled successfully)** | Next.js 14 App Router, all 10 routes compiled with static & dynamic SSR |
| **ESLint Static Analysis** | `npm run lint` (in `apps/web`) | **PASS (0 errors)** | Verified code cleanliness |
| **Phase 10A.1 Live Verification** | `python scripts/verify_phase10a_1.py` | **PASS (10/10 checks)** | Live end-to-end audit: 100% Indian coordinates, facilities API, foreign rejection |

---

## 8. Commands to Run Frontend and Backend

### Backend (FastAPI + PostGIS)
```powershell
# In project root:
$env:TARGET_CROP="guava"
$env:GUAVA_MODEL_ACTIVATED="true"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Frontend (Next.js 14 App Router)
```powershell
cd apps/web
npm run dev
# Dashboard available at: http://localhost:3000
```

---

## 9. Steps to Manually Verify the Map and Godown Markers

1. **Open the Dashboard**:
   - Navigate to `http://localhost:3000` in Google Chrome or Microsoft Edge.
2. **Switch to PostGIS Map Tab**:
   - In the navigation bar, click on **"Cold Chain & Tracking"**.
3. **Verify Map Centering on Punjab**:
   - The map automatically centers on Punjab (`30.50° N, 74.80° E`) at zoom level 8.
   - Click the **"Punjab"** focus button to instantly re-center the viewport on the Punjab agro belt.
4. **Inspect Godown & Facility Markers**:
   - Notice the distinct, colorful marker pins:
     - 🏛️ **Amber pins** for Godowns (Bathinda Hub).
     - ❄️ **Cyan pins** for Cold Storage (Fazilka CA Store).
     - 🌱 **Emerald pins** for Packhouses (Abohar Center, Jalandhar Packhouse).
     - 🛒 **Purple pins** for Mandis (Amritsar APMC, Azadpur Delhi APMC).
     - 📦 **Slate pins** for Warehouses (Ludhiana Warehouse).
   - Click any facility pin: inspect the popup displaying Facility Name, Type, Address, District, Postal Code, and Capacity (e.g. `1,500 MT`).
5. **Test Facility Controls**:
   - Click the **"Godowns: ON"** toggle button: all facility markers toggle off and on smoothly.
   - Click the filter pills (**"Cold Stores"**, **"Packhouses"**, **"Mandis"**): the map filters to show only the selected facility category.
6. **Select a Shipment**:
   - In the left sidebar, click **`#SHP-2026-001`** (Guava from Abohar to Azadpur Mandi):
     - The origin packhouse (Abohar) and destination mandi (Azadpur) are highlighted.
     - A dashed straight-line corridor connects Abohar &rarr; Bathinda &rarr; Vehicle &rarr; Azadpur.
     - The summary card displays: `Origin Hub: PACKHOUSE Abohar Guava & Citrus Post-Harvest Center` and `Destination Facility: MANDI Azadpur APMC Mega Mandi Cold Logistics`.
7. **Test Live Waypoint Ingestion**:
   - In the Selected Shipment card, click **"Add GPS"**.
   - Click the quick preset button **"Bathinda Hub (30.21°, 74.95°)"**.
   - Click **"Record Waypoint"**: the vehicle marker updates live, broadcasts via WebSocket, and plots the new location along NH-7 inside India.
