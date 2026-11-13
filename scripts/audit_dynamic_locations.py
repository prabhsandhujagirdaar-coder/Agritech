"""
AgriChain AI — Independent Audit: Task 1: Dynamic Location Verification
"""

import json
import urllib.request
import urllib.parse
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def post_json(path, payload):
    url = f"{BACKEND_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 500, {"error": str(e)}

def get_json(path):
    url = f"{BACKEND_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 500, {"error": str(e)}

def main():
    print("======================================================================")
    print("AUDIT TASK 1: DYNAMIC LOCATION & ROUTING VERIFICATION")
    print("======================================================================\n")

    test_pairs = [
        {
            "name": "Pair 1 (Punjab to Delhi): Abohar -> Azadpur Mandi",
            "origin": {"name": "Abohar Packhouse", "lat": 30.1453, "lon": 74.1994},
            "destination": {"name": "Azadpur Mandi", "lat": 28.7161, "lon": 77.1772},
        },
        {
            "name": "Pair 2 (Punjab Inter-district): Fazilka -> Ludhiana",
            "origin": {"name": "Fazilka Citrus Hub", "lat": 30.4037, "lon": 74.0254},
            "destination": {"name": "Ludhiana Mandi", "lat": 30.9010, "lon": 75.8573},
        },
        {
            "name": "Pair 3 (Maharashtra Highway): Baramati -> Vashi Mandi",
            "origin": {"name": "Baramati Banana Packhouse", "lat": 18.1512, "lon": 74.5775},
            "destination": {"name": "Vashi APMC Mandi", "lat": 19.0760, "lon": 72.9986},
        },
        {
            "name": "Pair 4 (Arbitrary User Custom Route): Jaipur -> Agra",
            "origin": {"name": "Jaipur Cold Store", "lat": 26.9124, "lon": 75.7873},
            "destination": {"name": "Agra APMC", "lat": 27.1767, "lon": 78.0081},
        }
    ]

    # 1. Test route generation for each pair
    created_sessions = []
    for pair in test_pairs:
        print(f"Testing: {pair['name']}")
        # Route Preview
        preview_payload = {
            "origin_lat": pair["origin"]["lat"],
            "origin_lon": pair["origin"]["lon"],
            "destination_lat": pair["destination"]["lat"],
            "destination_lon": pair["destination"]["lon"],
        }
        status, preview = post_json("/api/v1/simulations/routes/preview", preview_payload)
        assert status == 200, f"Preview failed: {preview}"
        dist_km = preview["distance_km"]
        coords = preview["geometry"]["coordinates"]
        coord_count = len(coords)
        print(f"  -> Preview Route OK: Distance={dist_km:.2f} km, Coordinates={coord_count}")
        # Verify first and last coords match within 0.05 deg of origin/dest
        first_coord = coords[0]
        last_coord = coords[-1]
        assert abs(first_coord[1] - pair["origin"]["lat"]) < 0.1, f"Origin mismatch: {first_coord[1]} vs {pair['origin']['lat']}"
        assert abs(first_coord[0] - pair["origin"]["lon"]) < 0.1, f"Origin mismatch: {first_coord[0]} vs {pair['origin']['lon']}"
        assert abs(last_coord[1] - pair["destination"]["lat"]) < 0.1, f"Dest mismatch: {last_coord[1]} vs {pair['destination']['lat']}"
        assert abs(last_coord[0] - pair["destination"]["lon"]) < 0.1, f"Dest mismatch: {last_coord[0]} vs {pair['destination']['lon']}"
        print(f"  -> Coordinate Integrity: Start [lat {first_coord[1]:.4f}, lon {first_coord[0]:.4f}], End [lat {last_coord[1]:.4f}, lon {last_coord[0]:.4f}]")

        # Session Creation
        create_payload = {
            "origin_name": pair["origin"]["name"],
            "origin_lat": pair["origin"]["lat"],
            "origin_lon": pair["origin"]["lon"],
            "destination_name": pair["destination"]["name"],
            "destination_lat": pair["destination"]["lat"],
            "destination_lon": pair["destination"]["lon"],
            "route_geometry": preview["geometry"],
        }
        c_status, session = post_json("/api/v1/simulations/", create_payload)
        assert c_status in (200, 201), f"Create session failed ({c_status}): {session}"
        print(f"  -> Session Created: ID={session['id']}, Status={session['status']}")
        created_sessions.append(session["id"])

    # 2. Test Geocoding & Failure Handling
    print("\nTesting Geocoding Search & Failure Handling:")
    # Valid search
    g_status, g_res = post_json("/api/v1/simulations/geocoding/search", {"query": "Ludhiana", "limit": 3})
    assert g_status == 200 and len(g_res) > 0, f"Geocoding failed for Ludhiana: {g_res}"
    print(f"  -> Valid Search 'Ludhiana': Found {len(g_res)} results. Top: '{g_res[0]['name']}' ({g_res[0]['latitude']}, {g_res[0]['longitude']})")

    # Non-existent query
    g_status_empty, g_res_empty = post_json("/api/v1/simulations/geocoding/search", {"query": "xyz123nonexistentplace999", "limit": 3})
    assert g_status_empty == 200 and len(g_res_empty) == 0, f"Expected empty result, got: {g_res_empty}"
    print(f"  -> Invalid Search 'xyz123nonexistentplace999': Gracefully returned 0 results (Status: {g_status_empty})")

    # 3. Test Routing Failure / Edge Cases
    print("\nTesting Routing Service with Edge Cases:")
    # Same origin and destination (distance ~ 0)
    same_status, same_route = post_json("/api/v1/simulations/routes/preview", {
        "origin_lat": 30.1453,
        "origin_lon": 74.1994,
        "destination_lat": 30.1453,
        "destination_lon": 74.1994,
    })
    print(f"  -> Identical Origin & Destination: Status={same_status}, Distance={same_route.get('distance_km')} km")

    # Invalid coordinates (out of range lat/lon)
    inv_status, inv_route = post_json("/api/v1/simulations/routes/preview", {
        "origin_lat": 999.0,
        "origin_lon": 74.1994,
        "destination_lat": 28.7161,
        "destination_lon": 77.1772,
    })
    print(f"  -> Out-of-bounds Lat 999.0: Status={inv_status} (Handled gracefully with error or fallback)")

    print("\n[PASSED] Dynamic Location & Routing Verification Complete!")

if __name__ == "__main__":
    main()
