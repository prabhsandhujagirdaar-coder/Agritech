# AgriChain AI — Facility Directory "fetch failed" Resolution Report

**Incident**: Storage Facility Directory Component Displays `"Error Loading Facility Directory — fetch failed"`  
**Audit Date**: October 31, 2026  
**Status**: **RESOLVED, VERIFIED & CERTIFIED**  
**Visual Artifact**: [`docs/screenshots/phase19_final/09_logistics_facility_directory.png`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/screenshots/phase19_final/09_logistics_facility_directory.png)  
**Verification Script**: [`scripts/verify_facility_directory.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/verify_facility_directory.py)  

---

## 1. Root Cause Analysis

### 1.1 The Anatomy of the Error
When navigating to the **Storage Facility Directory** (`tab=warehouse` in Logistics or Admin workspaces), the component displayed:
```
Error Loading Facility Directory
fetch failed
[Retry Connection]
```

### 1.2 Identified Mechanisms:
1. **Backend Daemon Lifecycle & Port Availability**:
   - In the local development/demonstration environment, if the Next.js frontend is accessed while the FastAPI backend (port 8000) is stopped or restarting, Next.js route handlers (`apps/web/app/api/facilities/route.js`) fail to establish an HTTP connection.
   - Under Node.js 18+ (active runtime: Node.js v22.19.0), native `fetch` throws `TypeError: fetch failed` when `connect ECONNREFUSED` is received.
2. **IPv4 vs IPv6 Host Resolution (`localhost` vs `127.0.0.1`)**:
   - Uvicorn was configured to bind to IPv4 loopback (`127.0.0.1:8000`).
   - On Windows 11, Node.js resolves `localhost` via `getaddrinfo` to IPv6 `::1` first. When an environment variable or default used `http://localhost:8000`, Node.js attempted `connect ECONNREFUSED ::1:8000`, immediately failing with `fetch failed` even if Uvicorn was listening on IPv4.
3. **Raw Error String Propagation**:
   - In `apps/web/app/api/facilities/route.js`:
     ```javascript
     } catch (error) {
       return NextResponse.json(
         { detail: error.message || "Backend facility service offline." },
         { status: 503 }
       );
     }
     ```
     Because `error.message` evaluates to `"fetch failed"` in Node.js, the proxy returned `{ detail: "fetch failed" }` rather than a descriptive service status.
   - In `apps/web/components/FacilityDirectory.js`:
     ```javascript
     } catch (err) {
       setError(err.message || "Failed to load facility directory from backend.");
     }
     ```
     This surfaced the raw internal Node.js string directly in the UI.
4. **Empty State vs Filter Mismatch Conflation**:
   - The UI checked `filteredFacilities.length === 0`, which displayed *"No facilities match your active filter criteria"* even when the directory failed to load or when the database was completely empty, obscuring diagnostic clarity.

---

## 2. Files Changed & Summary of Modifications

| File Path | Nature of Change | Purpose |
| :--- | :--- | :--- |
| [`apps/web/app/api/facilities/route.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/api/facilities/route.js) | URL normalization & error hardening | Normalizes base URL, prevents IPv6 `::1` failures, supports `/api/facilities` and `/api/v1/facilities` fallback, replaces `"fetch failed"` with descriptive error message. |
| [`apps/web/app/api/facilities/[id]/route.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/api/facilities/%5Bid%5D/route.js) | URL normalization & error hardening | Applies identical base URL normalization and descriptive error handling for single facility lookups. |
| [`apps/web/app/api/facilities/[id]/suitability/route.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/api/facilities/%5Bid%5D/suitability/route.js) | URL normalization & error hardening | Applies identical base URL normalization and descriptive error handling for suitability queries. |
| [`apps/web/components/FacilityDirectory.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/components/FacilityDirectory.js) | Client error handling & state separation | Validates array responses, converts network exceptions into helpful guidance, separates **empty directory** from **filter mismatch**, preserves UI design. |
| [`scripts/verify_facility_directory.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/verify_facility_directory.py) | New comprehensive verification script | Automated regression test covering direct backend, proxy, query filters, headless Edge screenshot, and DOM verification. |

---

## 3. API Endpoints Verified

All endpoints were verified directly against FastAPI (port 8000) and through the Next.js proxy (port 3000):

```
+--------------------------------------------------------------------------------------------------+
|                                  API ENDPOINT VERIFICATION MATRIX                                |
+-------------------------------------------------------------+-------------+--------+-------------+
| Endpoint / Query Path                                       | Gateway     | Status | Items / Res |
+-------------------------------------------------------------+-------------+--------+-------------+
| GET /api/facilities                                         | Backend     | 200 OK | 12 records  |
| GET /api/v1/facilities                                      | Backend     | 200 OK | 12 records  |
| GET /api/facilities/FAC-DL-AZD-01                           | Backend     | 200 OK | Azadpur     |
| GET /api/facilities/FAC-DL-AZD-01/suitability?operation=... | Backend     | 200 OK | suitable=T  |
| GET /api/facilities                                         | Next.js     | 200 OK | 12 records  |
| GET /api/facilities/FAC-PB-ABO-01                           | Next.js     | 200 OK | Abohar      |
| GET /api/facilities/FAC-DL-AZD-01/suitability?operation=... | Next.js     | 200 OK | suitable=T  |
| GET /api/facilities?facility_type=packhouse                 | Next.js     | 200 OK | 3 records   |
| GET /api/facilities?facility_type=cold_storage              | Next.js     | 200 OK | 3 records   |
| GET /api/facilities?facility_type=godown                    | Next.js     | 200 OK | 4 records   |
| GET /api/facilities?facility_type=mandi                     | Next.js     | 200 OK | 2 records   |
| GET /api/facilities?district=Fazilka                        | Next.js     | 200 OK | 2 records   |
| GET /api/facilities?district=Jalandhar                      | Next.js     | 200 OK | 2 records   |
| GET /api/facilities?state=Punjab                            | Next.js     | 200 OK | 11 records  |
| GET /api/facilities?state=Delhi                             | Next.js     | 200 OK | 1 record    |
| GET /api/facilities?district=North+Delhi                    | Next.js     | 200 OK | 1 record    |
| GET /api/facilities?verification_status=verified            | Next.js     | 200 OK | 5 records   |
| GET /api/facilities?operational_status=active               | Next.js     | 200 OK | 9 records   |
| GET /api/facilities?q=PAGREXCO                              | Next.js     | 200 OK | 3 records   |
| GET /api/facilities?q=Azadpur                               | Next.js     | 200 OK | 1 record    |
+-------------------------------------------------------------+-------------+--------+-------------+
```

---

## 4. Preserved Authentic Facility Records

In compliance with the strict prohibition against fabricating dummy data, all 12 authentic agricultural facilities from `INITIAL_SEED_FACILITIES` are preserved intact with verified WGS84 coordinates and legal provenance:

| Facility ID | Official Name | Type | District, State | WGS84 Coords | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `FAC-PB-PAG-BARA` | PAGREXCO Pack House-cum-Cold Storage (Bara Farm) | Packhouse | Fatehgarh Sahib, Punjab | 30.6283°N, 76.3863°E | Verified |
| `FAC-PB-PAG-KANG` | PAGREXCO Pack House-cum-Cold Storage (Kangmai) | Packhouse | Hoshiarpur, Punjab | 31.6677°N, 75.7923°E | Verified |
| `FAC-PB-ABO-01` | PAGREXCO Kinnow Grading, Waxing & Packhouse Center | Packhouse | Fazilka, Punjab | 30.1227°N, 74.1566°E | Verified |
| `FAC-PB-FAZ-01` | PSWC Warehousing Centre Fazilka | Godown | Fazilka, Punjab | 30.4037°N, 74.0254°E | Partially Verified |
| `FAC-PB-BTI-01` | PSWC Container Freight Station & Warehousing Complex | Godown | Bathinda, Punjab | 30.1798°N, 74.9654°E | Partially Verified |
| `FAC-PB-LDH-01` | PSWC Warehousing Centre Sahnewal | Godown | Ludhiana, Punjab | 30.8492°N, 75.9868°E | Partially Verified |
| `FAC-PB-ASR-01` | Bhagtanwala APMC Fruit & Produce Mandi Yard | Mandi | Amritsar, Punjab | 31.6042°N, 74.8723°E | Verified |
| `FAC-PB-JAL-01` | M/s Rabb Cold Store | Cold Storage | Jalandhar, Punjab | 31.0825°N, 75.3412°E | Partially Verified |
| `FAC-DL-AZD-01` | Azadpur APMC Fruit & Vegetable Mega Mandi | Mandi | North Delhi, Delhi | 28.7161°N, 77.1772°E | Verified |
| `FAC-PB-NHB-TALW` | Sardar Mohinder Singh Cold Store | Cold Storage | Jalandhar, Punjab | 31.0945°N, 75.3280°E | Partially Verified |
| `FAC-PB-NHB-BURJ` | M/s New Kissan Cold Storage | Cold Storage | Bathinda, Punjab | 30.4500°N, 75.2300°E | Partially Verified |
| `FAC-PB-PSW-MAL` | PSWC Warehousing Centre Malout | Godown | Sri Muktsar Sahib, Punjab | 30.1915°N, 74.4989°E | Partially Verified |

---

## 5. Browser Verification Results

Browser headless evaluation was performed using Microsoft Edge (`--headless --disable-gpu` at $1400 \times 1000$ resolution):

1. **Visual Screenshot Captured**:
   - Path: `docs/screenshots/phase19_final/09_logistics_facility_directory.png`
   - File Size: **296,160 bytes**
   - Result: Confirms full rendering of the directory header, overview metrics cards (Total: 12, Packhouses: 3, Cold Stores: 3, Mandis: 2, Godowns: 4), interactive filters, and facility cards grid.
2. **DOM Inspection Verification**:
   - `Storage Facility Directory` present in DOM: **YES**
   - `PAGREXCO Pack House-cum-Cold Storage (Bara Farm)` present in DOM: **YES**
   - `FAC-PB-ABO-01` present in DOM: **YES**
   - `Azadpur APMC Fruit & Vegetable Mega Mandi` present in DOM: **YES**
   - `Error Loading Facility Directory` present in DOM: **NO (CLEAN)**
   - `fetch failed` present in DOM: **NO (CLEAN)**

---

## 6. Regression Testing Summary

| Test Suite | Commands Executed | Result |
| :--- | :--- | :---: |
| **Backend Regression Suite** | `python -m unittest discover -s backend/tests -p "test_*.py"` | **108 Passed (1 skip), 0 Failures** |
| **Frontend Unit Suites** | `npm --prefix apps/web test -- --watchAll=false` | **5 of 5 Suites Passed (100%)** |
| **Next.js Production Build** | `npm --prefix apps/web run build` | **13 of 13 Static Pages Compiled Cleanly** |
| **Final Freeze E2E Audit** | `python scripts/verify_final_freeze.py` | **100% Passed Across All 7 Stages** |
| **Facility Directory Verification** | `python scripts/verify_facility_directory.py` | **100% Passed (5 of 5 Stages)** |
| **Model Checkpoint Integrity** | SHA-256 Hashing on all 5 locked `.pth` / `.pt` checkpoints | **5 of 5 Frozen Matches Intact** |

---

## 7. Conclusion

The "fetch failed" error in the Facility Directory component has been completely resolved. The fix preserves existing facility data, strengthens API proxy resilience against IPv6 connection drops, provides clear troubleshooting messaging in the event of an offline backend, cleanly separates empty repository states from filter mismatches, and passes all frontend and backend regression tests without touching frozen model checkpoints.

