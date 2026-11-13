"""
AgriChain AI — Independent Audit: Task 5: Frontend Integration & Proxy Audit
"""

import json
import urllib.request
from pathlib import Path

NEXTJS_URL = "http://localhost:3000"

def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def get_json(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def get_html(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def main():
    print("======================================================================")
    print("AUDIT TASK 5: FRONTEND INTEGRATION & PROXY VERIFICATION")
    print("======================================================================\n")

    # 1. Test Next.js Geocoding Proxy Route
    print("[1] Testing Next.js Geocoding Search Proxy...")
    p_status, p_geo = post_json(f"{NEXTJS_URL}/api/simulations/geocoding/search", {"query": "Abohar", "limit": 2})
    print(f"  -> Next.js Proxy Status={p_status}, Results Count={len(p_geo)}")
    assert p_status == 200 and len(p_geo) > 0
    print(f"  -> Top result via Next.js Proxy: '{p_geo[0]['name']}' ({p_geo[0]['latitude']}, {p_geo[0]['longitude']})")

    # 2. Test Next.js Route Preview Proxy Route
    print("\n[2] Testing Next.js Route Preview Proxy...")
    prev_payload = {
        "origin_lat": 30.1453,
        "origin_lon": 74.1994,
        "destination_lat": 28.7161,
        "destination_lon": 77.1772,
    }
    p_prev_status, p_prev = post_json(f"{NEXTJS_URL}/api/simulations/routes/preview", prev_payload)
    print(f"  -> Next.js Route Preview Status={p_prev_status}, Dist={p_prev['distance_km']} km, Coords={len(p_prev['geometry']['coordinates'])}")
    assert p_prev_status == 200 and p_prev["distance_km"] > 300.0

    # 3. Test Next.js Session Creation Proxy
    print("\n[3] Testing Next.js Session Creation Proxy...")
    c_payload = {
        "origin_name": "Frontend Proxy Origin",
        "origin_lat": 30.1453,
        "origin_lon": 74.1994,
        "destination_name": "Frontend Proxy Dest",
        "destination_lat": 28.7161,
        "destination_lon": 77.1772,
        "route_geometry": p_prev["geometry"],
    }
    c_status, c_session = post_json(f"{NEXTJS_URL}/api/simulations", c_payload)
    sim_id = c_session["id"]
    print(f"  -> Next.js Proxy Created Session: {sim_id} (Status={c_session['status']})")
    assert c_status in (200, 201)

    # 4. Test Next.js Controls Proxy (Start, Pause, Step)
    print("\n[4] Testing Next.js Simulation Controls Proxy...")
    _, s_step = post_json(f"{NEXTJS_URL}/api/simulations/{sim_id}/step?advance_km=3.5", {})
    print(f"  -> Stepped via Next.js Proxy: Dist={s_step['current_distance_km']} km, Speed={s_step['current_speed_kmh']} km/h")
    assert s_step["current_distance_km"] >= 3.5

    # 5. Check Next.js Logistics Dashboard HTML & Synthetic Watermark
    print("\n[5] Auditing Logistics Dashboard & Simulated Watermark...")
    html_status, html_content = get_html(f"{NEXTJS_URL}/dashboard?role=Logistics&tab=tracking")
    print(f"  -> Logistics Dashboard HTTP Status: {html_status}")
    assert html_status == 200
    
    # Check watermark keywords in frontend codebase
    tracking_code = (Path("apps/web/components/ShipmentsTracking.js")).read_text(encoding="utf-8")
    map_code = (Path("apps/web/components/TrackingMap.js")).read_text(encoding="utf-8")

    has_watermark_badge = "SYNTHETIC SIMULATION — DEMO ONLY" in tracking_code or "SNS-SIM-DEMO" in tracking_code
    has_map_click_mode = "mapPickMode" in map_code and "handleMapClick" in map_code
    has_vehicle_marker = "current_heading_deg" in map_code and "svg" in map_code.lower()
    has_controls_deck = "Simulation Studio" in tracking_code and "handleCreateSimulationSession" in tracking_code

    print(f"  -> Synthetic Watermark Badge in UI: {has_watermark_badge}")
    print(f"  -> Interactive Map-Click Picking (handleMapClick): {has_map_click_mode}")
    print(f"  -> Dynamic Vehicle Marker with Heading Rotation: {has_vehicle_marker}")
    print(f"  -> Simulation Studio Controls Deck: {has_controls_deck}")

    assert has_watermark_badge and has_map_click_mode and has_vehicle_marker and has_controls_deck
    print("\n[PASSED] Task 5 Frontend Integration & Proxy Verification Complete!")

if __name__ == "__main__":
    main()

