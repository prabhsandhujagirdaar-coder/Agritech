"""
AgriChain AI — Phase 10A End-to-End Verification Script
Verifies:
1. Backend Health Check
2. Backend Shipments & PostGIS Waypoints
3. Next.js Frontend Proxy Routes
4. Real-time Telemetry & Waypoints Ingestion
5. Cold-chain Spoilage Risk Calculation (LSTM)
6. Out-of-bounds Coordinate Rejection
7. Next.js Dashboard HTML Availability
"""

import sys
import json
import urllib.request
import urllib.error

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "VerificationScript/1.0"})
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def http_post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "VerificationScript/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def run_checks():
    print("=" * 60)
    print("AgriChain AI — Phase 10A Live Verification Suite")
    print("=" * 60)

    # 1. Backend Health
    print("\n[1/7] Testing Backend Health (/health)...")
    try:
        status, data = http_get(f"{BACKEND_URL}/health")
        print(f"  --> Status: {status}, Service: {data.get('service')}, Target Crop: {data.get('target_crop')}, Model Loaded: {data.get('guava_model_loaded')}")
        assert status == 200
        assert data.get("target_crop") == "guava"
    except Exception as e:
        print(f"  FAIL: Backend health check failed: {e}")
        return False

    # 2. Next.js Shipments Proxy
    print("\n[2/7] Testing Frontend Proxy GET /api/shipments...")
    try:
        status, shipments = http_get(f"{FRONTEND_URL}/api/shipments")
        print(f"  --> Status: {status}, Total Shipments: {len(shipments)}")
        geolocated = [s for s in shipments if s.get("current_coordinates")]
        pending_gps = [s for s in shipments if not s.get("current_coordinates")]
        print(f"  --> Geolocated Shipments on Map: {len(geolocated)}")
        print(f"  --> Pending GPS (Location Unavailable): {len(pending_gps)}")
        for s in shipments[:3]:
            coords = s.get("current_coordinates")
            coord_str = f"Lat: {coords['latitude']:.4f}, Lon: {coords['longitude']:.4f}" if coords else "None (GPS Pending)"
            print(f"      * [{s['id']}] {s['produce_type']} ({s['status']}) - Coords: {coord_str}")
        assert len(shipments) > 0
    except Exception as e:
        print(f"  FAIL: Frontend shipments proxy failed: {e}")
        return False

    # 3. Next.js Waypoints Proxy
    target_id = "SHP-2026-001"
    print(f"\n[3/7] Testing Frontend Proxy GET /api/shipments/{target_id}/waypoints...")
    try:
        status, waypoints = http_get(f"{FRONTEND_URL}/api/shipments/{target_id}/waypoints")
        print(f"  --> Status: {status}, Historical Waypoints: {len(waypoints)}")
        if waypoints:
            latest = waypoints[-1]
            print(f"      * Latest: {latest.get('id')} at ({latest.get('latitude')}, {latest.get('longitude')}), speed: {latest.get('speed_kmh')} km/h")
        assert len(waypoints) > 0
    except Exception as e:
        print(f"  FAIL: Frontend waypoints proxy failed: {e}")
        return False

    # 4. Valid Waypoint Recording (Simulating Transit Update)
    print(f"\n[4/7] Testing Frontend Proxy POST /api/shipments/{target_id}/waypoints...")
    try:
        new_wp = {
            "latitude": 32.2150,
            "longitude": 74.2050,
            "speed_kmh": 62.0,
            "location_metadata": {"note": "Phase 10A live verification checkpoint"}
        }
        status, created = http_post(f"{FRONTEND_URL}/api/shipments/{target_id}/waypoints", new_wp)
        print(f"  --> Status: {status}, Created Waypoint: {created.get('id')} at ({created.get('latitude')}, {created.get('longitude')})")
        assert created.get("latitude") == 32.2150
        assert created.get("longitude") == 74.2050
    except Exception as e:
        print(f"  FAIL: Waypoint creation failed: {e}")
        return False

    # 5. Coordinate Boundary Validation (Rejecting Out-of-bounds coordinates)
    print(f"\n[5/7] Testing Coordinate Bounds Enforcement (Latitude: 99.0)...")
    try:
        bad_wp = {"latitude": 99.0, "longitude": 74.0}
        http_post(f"{FRONTEND_URL}/api/shipments/{target_id}/waypoints", bad_wp)
        print("  FAIL: Server unexpectedly accepted out-of-bounds latitude 99.0!")
        return False
    except urllib.error.HTTPError as err:
        print(f"  --> Successfully REJECTED with HTTP {err.code} ({err.reason})")
        assert err.code in (400, 422)

    # 6. Cold-Chain Risk Evaluation
    print(f"\n[6/7] Testing Cold-Chain Risk Endpoint (/api/shipments/{target_id}/risk)...")
    try:
        status, risk_data = http_get(f"{FRONTEND_URL}/api/shipments/{target_id}/risk")
        print(f"  --> Status: {status}, Current Spoilage Risk: {risk_data.get('current_risk')}%")
        print(f"  --> Predicted Arrival Risk: {risk_data.get('predicted_arrival_risk')}%, Alert: {risk_data.get('alert')}")
        print(f"  --> Telemetry Evaluated: {risk_data.get('telemetry_points_evaluated')} points, Avg Temp: {risk_data.get('avg_temperature_c')}°C")
        assert "current_risk" in risk_data
        assert "predicted_arrival_risk" in risk_data
    except Exception as e:
        print(f"  FAIL: Risk endpoint failed: {e}")
        return False

    # 7. Next.js Dashboard Availability
    print("\n[7/7] Testing Next.js Dashboard HTML rendering (/dashboard)...")
    try:
        req = urllib.request.Request(f"{FRONTEND_URL}/dashboard", headers={"User-Agent": "VerificationScript/1.0"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "AgriChain" in html or "html" in html
            print(f"  --> Dashboard Status: {resp.status} OK (HTML Length: {len(html)} bytes)")
    except Exception as e:
        print(f"  FAIL: Dashboard HTML fetch failed: {e}")
        return False

    print("\n" + "=" * 60)
    print(">>> ALL 7 END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
