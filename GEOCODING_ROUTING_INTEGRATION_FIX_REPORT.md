# AgriChain AI — GeocodingService & Route Integration Fix Report
**Document ID:** AGR-FIX-20261115-023  
**Status:** RESOLVED & VERIFIED  
**Date:** November 15, 2026  
**Target Shipment:** `SHP-2026-023` (Kinnow Mandarin, 350 kg, Origin: *Abohar Packhouse, Punjab*, Destination: *Jaipur Mandi, Rajasthan*)  

---

## 1. Executive Summary

A critical runtime error was identified in the shipment route resolution and simulation pipeline:
```text
Routing service error: 'GeocodingService' object has no attribute 'geocode_location'
```
This error prevented shipment `SHP-2026-023` from resolving road routes, calculating highway driving distance and estimated transit duration, rendering route waypoints, and initializing dynamic vehicle simulation sessions.

This report documents the end-to-end investigation, root cause diagnosis, architectural fix, verification test outputs across 5 core agricultural corridors, frozen ML checkpoint validation, and production safeguards.

---

## 2. Root Cause Analysis

### 2.1 Missing Method Contract (`geocode_location`)
In `backend/app/api/v1/endpoints/shipments.py` (lines 156–168), the shipment route endpoint `get_shipment_route(shipment_id)` relies on `GeocodingService` to resolve geographic coordinates when a shipment's origin or destination does not already carry fixed facility IDs:
```python
# backend/app/api/v1/endpoints/shipments.py
geo = get_geocoding_service()
origin_res = geo.geocode_location(shipment["origin_name"])
dest_res = geo.geocode_location(shipment["destination_name"])
```
However, `GeocodingService` in `backend/app/services/geocoding_service.py` originally only provided:
```python
def search_locations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]
```
Because no `geocode_location(query: str)` method was declared or implemented on the service, any invocation attempting to resolve a single location query directly crashed with an `AttributeError`, surfacing as HTTP 500: `Routing service error: 'GeocodingService' object has no attribute 'geocode_location'`.

### 2.2 State-Level Search Scoring Bleeding
During the investigation of candidate matching, a secondary relevance scoring vulnerability was identified:
When evaluating candidate locations against a user query such as `"Bathinda, Punjab"`, the legacy matcher performed a simple substring check `place["state"].lower() in q_lower`. Because all Punjab facilities shared the state token `"Punjab"`, candidates were scored identically regardless of whether the district or place name matched. As a result, searching for `"Bathinda, Punjab"` incorrectly returned the first Punjab entry in the list (*Abohar Kinnow & Guava Packhouse*) instead of the actual Bathinda facility.

### 2.3 Missing Abohar → Jaipur Highway Corridor Anchors
`backend/app/services/routing_service.py` defines curated fallback highway corridors in `_CORRIDOR_ANCHORS` for high-reliability offline navigation across Northern India. While Fazilka–Delhi, Fazilka–Ludhiana, Abohar–Bathinda, and Jaipur–Agra corridors existed, there was no direct anchor chain connecting Abohar (Punjab) to Jaipur (Rajasthan) via the NH-52 / NH-62 trunk route (Hanumangarh, Rawatsar, Sardarshahr, Ratangarh, Fatehpur, Sikar, Ringas, Chomu).

### 2.4 Circular Import & Cross-Loop Asyncio Lock in Simulation Engine
`backend/app/services/simulation_engine.py` imported `from app.api.v1.endpoints.ws import get_ws_manager` at the module level. This created a circular import chain (`ws` -> `api_router` -> `simulations` -> `simulation_engine`). Furthermore, `_get_lock()` attempted to access `self._lock._loop`, which was removed in Python 3.10+, leading to stale locks across separate event loops.

---

## 3. Architecture & Code Changes

### 3.1 `backend/app/services/geocoding_service.py`

#### A. Implemented `geocode_location` and `geocode` Alias
Added a robust single-point geocoding resolution method with internal LRU cache, direct coordinate parsing, bounds checking, and graceful fallback:

```python
def geocode_location(self, query: str) -> Optional[Dict[str, Any]]:
    """
    Geocodes a location query into a single verified Indian geographic coordinate dict.
    Resolves coordinates from curated agricultural landmarks, facilities, or Nominatim.

    Returns:
        Dict with 'name', 'display_name', 'latitude', 'longitude', 'type', 'state', 'source'
        or None if unresolvable.
    """
    q = (query or "").strip()
    if not q or len(q) < 2:
        return None

    q_lower = q.lower()
    if q_lower in self._single_cache:
        return self._single_cache[q_lower]

    # 1. Direct coordinate string check (e.g. "30.1453, 74.1994")
    coord_pair = _try_parse_coordinate_string(q)
    if coord_pair is not None:
        c_lat, c_lon = coord_pair
        direct_res = {
            "name": f"Coordinate ({c_lat:.4f}, {c_lon:.4f})",
            "display_name": f"Coordinate Location ({c_lat:.4f}° N, {c_lon:.4f}° E)",
            "latitude": c_lat,
            "longitude": c_lon,
            "type": "coordinate",
            "state": "India",
            "source": "coordinate_input",
        }
        self._single_cache[q_lower] = direct_res
        return direct_res

    # 2. Search candidates via search_locations
    candidates = self.search_locations(q, limit=5)
    for cand in candidates:
        lat = cand.get("latitude")
        lon = cand.get("longitude")
        if lat is not None and lon is not None:
            try:
                f_lat = float(lat)
                f_lon = float(lon)
                if is_within_india(f_lat, f_lon):
                    resolved = {
                        "name": cand.get("name") or q,
                        "display_name": cand.get("display_name") or cand.get("name") or q,
                        "latitude": f_lat,
                        "longitude": f_lon,
                        "type": cand.get("type", "location"),
                        "state": cand.get("state", "India"),
                        "source": cand.get("source", "curated_agri_directory"),
                    }
                    self._single_cache[q_lower] = resolved
                    return resolved
            except (ValueError, TypeError):
                continue

    # 3. Direct Nominatim fallback if search_locations yielded nothing
    osm_matches = self._query_osm_nominatim(q, limit=3)
    for item in osm_matches:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is not None and lon is not None:
            try:
                f_lat = float(lat)
                f_lon = float(lon)
                if is_within_india(f_lat, f_lon):
                    self._single_cache[q_lower] = item
                    return item
            except (ValueError, TypeError):
                continue

    self._single_cache[q_lower] = None
    return None

# Backward compatibility alias
geocode = geocode_location
```

#### B. Distinctive Token Scoring & Disambiguation (`_score_place_relevance`)
Replaced naive substring matching with an intelligent multi-tier relevance scoring function:
- **Distinctive Tokens** (e.g. `bathinda`, `abohar`, `jaipur`): +200 for exact name match, +150 for district match, +80 for display name.
- **Generic Agri Keywords** (`mandi`, `packhouse`, `hub`, `terminal`, `godown`): +20 weight.
- **State Token Guard**: If a query contains distinctive non-state tokens and NONE match the place's name or district, matching the state name alone yields a score of 0, completely preventing state-bleeding misattribution.

#### C. Curated Directory Enhancements
Added explicit entries and comprehensive alias arrays for:
- `Abohar Packhouse` (`30.1453° N, 74.1994° E`, Fazilka, Punjab)
- `Jaipur Mandi` / `Jaipur APMC Muhana Fruit & Vegetable Terminal Mandi` (`26.7937° N, 75.7381° E`, Jaipur, Rajasthan)
- Aliases for `Bathinda Multimodal Transit Hub`, `Fazilka CA Cold Store Hub`, `Ludhiana Agro Cold Chain Terminal`, etc.

---

### 3.2 `backend/app/services/routing_service.py`

Added the authoritative `abohar_to_jaipur` highway corridor anchor chain (~431.22 km, 211 road waypoints) along NH-52 / NH-62:
```python
"abohar_to_jaipur": [
    (30.1453, 74.1994),  # Abohar Packhouse
    (29.5800, 74.3200),  # Hanumangarh Junction
    (29.2800, 74.3800),  # Rawatsar
    (28.8900, 74.4500),  # Pallu
    (28.4400, 74.4900),  # Sardarshahr
    (28.0800, 74.6200),  # Ratangarh NH-11 Junction
    (27.9800, 74.9500),  # Fatehpur Shekhawati
    (27.6100, 75.1400),  # Sikar Bypass NH-52
    (27.3500, 75.5600),  # Ringas Junction NH-52
    (27.1700, 75.7200),  # Chomu NH-52
    (26.7937, 75.7381),  # Jaipur Muhana Terminal Mandi
],
```

---

### 3.3 `backend/app/services/simulation_engine.py`

1. **Circular Import Elimination**: Removed top-level `from app.api.v1.endpoints.ws import get_ws_manager`. Deferred import into `_broadcast_status()` and `_broadcast_telemetry()`.
2. **Event Loop Tracking**: Introduced `self._lock_loop` to track the running event loop explicitly, ensuring lock recreation when executed in varying event loops across threads or async runners.

---

## 4. Method Contracts (Before vs. After)

| Method / Property | Before Fix | After Fix |
|:---|:---|:---|
| `GeocodingService.geocode_location(query)` | ❌ Did not exist (`AttributeError`) | ✅ `(query: str) -> Optional[Dict[str, Any]]` |
| `GeocodingService.geocode(query)` | ❌ Did not exist | ✅ Backward compatibility alias for `geocode_location` |
| `GeocodingService.search_locations(query, limit)` | Naive substring match; state bleeding | Scored token ranking; distinctive disambiguation |
| Coordinate Parsing (`"lat, lon"`) | ❌ Unhandled | ✅ Parsed via regex `_try_parse_coordinate_string` |
| Boundary Validation | Partial | Strict WGS84 & Indian bounds check (`is_within_india`) |
| Corridors Supported | 4 corridors | 5 corridors (including Abohar → Jaipur) |

---

## 5. Verification Test Results

### 5.1 Verification Suite (`scripts/verify_geocoding_routes.py`)

Executed with exit code 0:

```text
============================================================
STEP 1: Verify GeocodingService Method Contracts
============================================================
  [OK] 'Abohar Packhouse, Punjab' -> Abohar Packhouse (30.1453, 74.1994)
  [OK] 'Jaipur Mandi, Rajasthan' -> Jaipur Mandi (26.7937, 75.7381)
  [OK] Non-existent query gracefully returns None
  [OK] Ranked search for 'Bathinda, Punjab' correctly prioritized: Bathinda Multimodal Transit Hub
  [OK] Direct coordinate string parsed and geocoded accurately

============================================================
STEP 2: Verify SHP-2026-023 Route Resolution via Shipment Endpoint
============================================================
  Shipment ID:       SHP-2026-023
  Origin Name:       Abohar Packhouse, Punjab (30.1453° N, 74.1994° E)
  Destination Name:  Jaipur Mandi, Rajasthan (26.7937° N, 75.7381° E)
  Highway Distance:  431.22 km
  Duration:          7.84 hours
  Waypoints Count:   211
  Routing Source:    fallback_corridor
  [OK] SHP-2026-023 route resolved without errors

============================================================
STEP 3: Verify the 5 Required Route Corridors
============================================================
  [OK] Abohar Packhouse, Punjab  -> Jaipur Mandi, Rajasthan   | Distance: 431.22 km | Waypoints:  211 | Source: fallback_corridor
  [OK] Abohar                    -> Bathinda                  | Distance:  72.23 km | Waypoints:   35 | Source: fallback_corridor
  [OK] Fazilka                   -> Amritsar                  | Distance: 200.45 km | Waypoints:   97 | Source: fallback_corridor
  [OK] Fazilka                   -> Ludhiana                  | Distance: 189.72 km | Waypoints:   92 | Source: fallback_corridor
  [OK] Jaipur                    -> Agra                      | Distance: 238.41 km | Waypoints:  117 | Source: fallback_corridor

============================================================
STEP 4: Verify Simulation Session Creation for SHP-2026-023
============================================================
  Session ID:        SIM-20261115070223-038
  Shipment ID:       SHP-2026-023
  Route Identifier:  ROUTE-SHP-2026-023-431.22
  Total Distance:    431.22 km
  Status:            READY
  [OK] Simulation session successfully created and matched to Abohar -> Jaipur corridor

============================================================
ALL GEOCODING & ROUTE INTEGRITY TESTS PASSED SUCCESSFULLY!
============================================================
```

### 5.2 Backend Unit Tests
- `TestDynamicVehicleSimulation.test_01_geocoding_search`: **PASSED**
- `TestDynamicVehicleSimulation.test_02_haversine_and_bearing`: **PASSED**
- `TestDynamicVehicleSimulation.test_03_road_route_generation`: **PASSED**
- `TestDynamicVehicleSimulation.test_04_polyline_distance_interpolation`: **PASSED**
- `TestPostgisWaypoints (5 tests)`: **ALL 5 PASSED**

### 5.3 Frontend Unit & Regression Suite (`npm --prefix apps/web test`)
- Guava & Produce CNN Class Labels & Ripeness Taxonomy Tests: **PASSED**
- Geospatial & Indian Boundary Normalization Unit Tests: **PASSED**
- Phase 13.5 Frontend Unit & Regression Tests: **PASSED**
- Phase 13.6 Frontend Unit & UI/UX Regression Tests: **PASSED**
- Phase 19 Role Configuration & Access Control Unit Tests: **PASSED**

---

## 6. Frozen ML Model Checkpoints Verification

In strict accordance with project rules, zero ML model checkpoints were retrained, overwritten, or modified. All 5 cryptographic SHA-256 hashes were recomputed from disk and verified bit-for-bit identical to the frozen baselines:

| Model Checkpoint Artifact | Baseline SHA-256 Hash | Current Computed Hash | Match Status |
|:---|:---|:---|:---:|
| `ml/artifacts/best_guava_resnet18.pth` | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | ✅ 100% MATCH |
| `ml/artifacts/best_banana_resnet18.pth` | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | ✅ 100% MATCH |
| `ml/artifacts/best_fruit_identifier_mobilenet_v3_large.pth` | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` | `273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356` | ✅ 100% MATCH |
| `ml/artifacts/best_fruit_identifier_resnet18.pth` | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | ✅ 100% MATCH |
| `ml/artifacts/best_apple_yolov8n.pt` | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` | `02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2` | ✅ 100% MATCH |

---

## 7. Known Limitations & Recommendations

1. **OSM Nominatim Fallback Rate Limit**:
   Nominatim is rate-limited to 1 request per second. The curated local agricultural directory and in-memory single-result and search caches cover all standard operational locations instantly without triggering network requests.
2. **Offline Host Persistence**:
   The active persistence ledger remains `.persisted_session.json`. PostgreSQL/PostGIS services remain offline on the local development host; the fallback highway corridor anchor network guarantees reliable offline routing regardless of external database connectivity.
3. **Multi-hop Geocoding**:
   Locations outside the curated North Indian agricultural network will fall back to Nominatim when network connectivity is present, or return structured `None` when unreachable, preventing application crashes.
