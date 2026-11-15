"""
AgriChain AI — Geocoding & Route Integrity Verification Script
=============================================================
Tests GeocodingService method contracts, location scoring, shipment route resolution
for SHP-2026-023, and verifies the 5 primary test corridors.
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.geo import is_within_india, validate_indian_coordinate
from app.services.geocoding_service import get_geocoding_service
from app.services.routing_service import get_routing_service
from app.db.repository import get_shipment_repository
from app.api.v1.endpoints.shipments import get_shipment_route
from app.schemas.simulation import CreateSimulationRequest, SimulationSessionResponse


def test_geocoding_service_contract():
    print("\n" + "=" * 60)
    print("STEP 1: Verify GeocodingService Method Contracts")
    print("=" * 60)

    geo = get_geocoding_service()

    # 1. Has geocode_location method
    assert hasattr(geo, "geocode_location"), "GeocodingService missing geocode_location"
    assert hasattr(geo, "geocode"), "GeocodingService missing backward-compat geocode alias"
    assert hasattr(geo, "search_locations"), "GeocodingService missing search_locations"

    # 2. Test exact query resolution for SHP-2026-023 locations
    abohar_res = geo.geocode_location("Abohar Packhouse, Punjab")
    assert abohar_res is not None, "Failed to geocode 'Abohar Packhouse, Punjab'"
    assert is_within_india(abohar_res["latitude"], abohar_res["longitude"]), "Abohar coordinates not within India"
    assert abs(abohar_res["latitude"] - 30.1453) < 0.05, f"Unexpected Abohar lat: {abohar_res['latitude']}"
    assert abs(abohar_res["longitude"] - 74.1994) < 0.05, f"Unexpected Abohar lon: {abohar_res['longitude']}"
    print(f"  [OK] 'Abohar Packhouse, Punjab' -> {abohar_res['name']} ({abohar_res['latitude']:.4f}, {abohar_res['longitude']:.4f})")

    jaipur_res = geo.geocode_location("Jaipur Mandi, Rajasthan")
    assert jaipur_res is not None, "Failed to geocode 'Jaipur Mandi, Rajasthan'"
    assert is_within_india(jaipur_res["latitude"], jaipur_res["longitude"]), "Jaipur coordinates not within India"
    assert abs(jaipur_res["latitude"] - 26.7937) < 0.05, f"Unexpected Jaipur lat: {jaipur_res['latitude']}"
    assert abs(jaipur_res["longitude"] - 75.7381) < 0.05, f"Unexpected Jaipur lon: {jaipur_res['longitude']}"
    print(f"  [OK] 'Jaipur Mandi, Rajasthan' -> {jaipur_res['name']} ({jaipur_res['latitude']:.4f}, {jaipur_res['longitude']:.4f})")

    # 3. Test non-existent location returns None
    none_res = geo.geocode_location("xyz123nonexistentplace999")
    assert none_res is None, f"Expected None for non-existent place, got {none_res}"
    print("  [OK] Non-existent query gracefully returns None")

    # 4. Test search_locations returns ranked results for 'Bathinda, Punjab' (must NOT pick Abohar)
    bti_res = geo.search_locations("Bathinda, Punjab", limit=5)
    assert len(bti_res) > 0, "No results for 'Bathinda, Punjab'"
    assert "bathinda" in bti_res[0]["name"].lower(), f"First result for 'Bathinda, Punjab' was not Bathinda: {bti_res[0]['name']}"
    print(f"  [OK] Ranked search for 'Bathinda, Punjab' correctly prioritized: {bti_res[0]['name']}")

    # 5. Test direct coordinate string geocoding
    coord_res = geo.geocode_location("30.1453, 74.1994")
    assert coord_res is not None, "Failed to geocode direct coordinate string"
    assert abs(coord_res["latitude"] - 30.1453) < 0.001
    assert abs(coord_res["longitude"] - 74.1994) < 0.001
    print("  [OK] Direct coordinate string parsed and geocoded accurately")


def test_shp_2026_023_route_resolution():
    print("\n" + "=" * 60)
    print("STEP 2: Verify SHP-2026-023 Route Resolution via Shipment Endpoint")
    print("=" * 60)

    route = get_shipment_route("SHP-2026-023")

    assert route["shipment_id"] == "SHP-2026-023"
    assert "origin" in route and "destination" in route
    assert "geometry" in route and route["geometry"]["type"] == "LineString"

    coords = route["geometry"]["coordinates"]
    assert len(coords) >= 10, f"Expected at least 10 waypoints, got {len(coords)}"

    o_lat = route["origin"]["latitude"]
    o_lon = route["origin"]["longitude"]
    d_lat = route["destination"]["latitude"]
    d_lon = route["destination"]["longitude"]

    validate_indian_coordinate(o_lat, o_lon, "SHP-2026-023 origin")
    validate_indian_coordinate(d_lat, d_lon, "SHP-2026-023 destination")

    # First and last coordinate in GeoJSON [lon, lat]
    first_coord = coords[0]
    last_coord = coords[-1]
    assert abs(first_coord[1] - o_lat) < 0.05, f"First coord lat {first_coord[1]} does not match origin {o_lat}"
    assert abs(first_coord[0] - o_lon) < 0.05, f"First coord lon {first_coord[0]} does not match origin {o_lon}"
    assert abs(last_coord[1] - d_lat) < 0.05, f"Last coord lat {last_coord[1]} does not match destination {d_lat}"
    assert abs(last_coord[0] - d_lon) < 0.05, f"Last coord lon {last_coord[0]} does not match destination {d_lon}"

    dist_km = route["distance_km"]
    assert dist_km > 350.0 and dist_km < 550.0, f"Unexpected distance for Abohar->Jaipur: {dist_km} km"

    print(f"  Shipment ID:       {route['shipment_id']}")
    print(f"  Origin Name:       {route['origin_name']} ({o_lat:.4f}° N, {o_lon:.4f}° E)")
    print(f"  Destination Name:  {route['destination_name']} ({d_lat:.4f}° N, {d_lon:.4f}° E)")
    print(f"  Highway Distance:  {dist_km} km")
    print(f"  Duration:          {route['duration_s'] / 3600.0:.2f} hours")
    print(f"  Waypoints Count:   {len(coords)}")
    print(f"  Routing Source:    {route['routing_source']}")
    print("  [OK] SHP-2026-023 route resolved without errors")


def test_5_required_corridors():
    print("\n" + "=" * 60)
    print("STEP 3: Verify the 5 Required Route Corridors")
    print("=" * 60)

    geo = get_geocoding_service()
    routing = get_routing_service()

    corridor_pairs = [
        ("Abohar Packhouse, Punjab", "Jaipur Mandi, Rajasthan", 350.0, 550.0),
        ("Abohar", "Bathinda", 60.0, 110.0),
        ("Fazilka", "Amritsar", 150.0, 250.0),
        ("Fazilka", "Ludhiana", 160.0, 260.0),
        ("Jaipur", "Agra", 200.0, 300.0),
    ]

    for orig_str, dest_str, min_d, max_d in corridor_pairs:
        o_res = geo.geocode_location(orig_str)
        d_res = geo.geocode_location(dest_str)

        assert o_res is not None, f"Could not geocode origin: {orig_str}"
        assert d_res is not None, f"Could not geocode destination: {dest_str}"

        validate_indian_coordinate(o_res["latitude"], o_res["longitude"], f"{orig_str} origin")
        validate_indian_coordinate(d_res["latitude"], d_res["longitude"], f"{dest_str} destination")

        route = routing.get_route(
            o_res["latitude"],
            o_res["longitude"],
            d_res["latitude"],
            d_res["longitude"],
        )

        dist = route["distance_km"]
        coords = route["geometry"]["coordinates"]
        assert route["geometry"]["type"] == "LineString"
        assert len(coords) >= 2, f"Too few waypoints for {orig_str} -> {dest_str}"
        assert min_d <= dist <= max_d, f"Distance {dist} km out of range [{min_d}, {max_d}] for {orig_str} -> {dest_str}"

        # Coordinate order verification: GeoJSON is [lon, lat]
        c_first = coords[0]
        c_last = coords[-1]
        assert is_within_india(c_first[1], c_first[0]), "First point outside India"
        assert is_within_india(c_last[1], c_last[0]), "Last point outside India"

        print(f"  [OK] {orig_str:25} -> {dest_str:25} | Distance: {dist:6.2f} km | Waypoints: {len(coords):4d} | Source: {route['routing_source']}")


def test_simulation_session_integrity():
    print("\n" + "=" * 60, flush=True)
    print("STEP 4: Verify Simulation Session Creation for SHP-2026-023", flush=True)
    print("=" * 60, flush=True)

    repo = get_shipment_repository()
    route = get_shipment_route("SHP-2026-023")

    session_data = {
        "shipment_id": "SHP-2026-023",
        "route_identifier": f"ROUTE-SHP-2026-023-{round(route['distance_km'], 2)}",
        "origin_name": route["origin_name"],
        "origin_lat": float(route["origin"]["latitude"]),
        "origin_lon": float(route["origin"]["longitude"]),
        "destination_name": route["destination_name"],
        "destination_lat": float(route["destination"]["latitude"]),
        "destination_lon": float(route["destination"]["longitude"]),
        "route_geojson": route["geometry"],
        "total_distance_km": round(float(route["distance_km"]), 2),
        "estimated_duration_s": round(float(route["duration_s"]), 1),
        "current_distance_km": 0.0,
        "current_lat": float(route["origin"]["latitude"]),
        "current_lon": float(route["origin"]["longitude"]),
        "current_heading_deg": 0.0,
        "current_speed_kmh": 0.0,
        "speed_multiplier": 5.0,
        "status": "READY",
        "scenario": "normal",
        "step_count": 0,
    }
    created = repo.create_simulation_session(session_data)
    session = SimulationSessionResponse(**created)

    assert session.shipment_id == "SHP-2026-023", f"Unexpected shipment_id: {session.shipment_id}"
    assert session.route_identifier.startswith("ROUTE-SHP-2026-023-"), f"Unexpected route_id: {session.route_identifier}"
    assert session.total_distance_km > 350.0, f"Session total distance too short: {session.total_distance_km}"
    assert len(session.route_geojson.get("coordinates", [])) >= 10, "Session route has no coordinates"

    # Verify origin / dest match geocoded Abohar -> Jaipur
    assert abs(session.origin_lat - 30.1453) < 0.05
    assert abs(session.origin_lon - 74.1994) < 0.05
    assert abs(session.destination_lat - 26.7937) < 0.05
    assert abs(session.destination_lon - 75.7381) < 0.05

    print(f"  Session ID:        {session.id}")
    print(f"  Shipment ID:       {session.shipment_id}")
    print(f"  Route Identifier:  {session.route_identifier}")
    print(f"  Total Distance:    {session.total_distance_km} km")
    print(f"  Status:            {session.status}")
    print("  [OK] Simulation session successfully created and matched to Abohar -> Jaipur corridor")


if __name__ == "__main__":
    try:
        test_geocoding_service_contract()
        test_shp_2026_023_route_resolution()
        test_5_required_corridors()
        test_simulation_session_integrity()
        print("\n" + "=" * 60)
        print("ALL GEOCODING & ROUTE INTEGRITY TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
    except AssertionError as err:
        print(f"\n[FAIL] Assertion failed: {err}")
        sys.exit(1)
    except Exception as exc:
        import traceback
        print(f"\n[ERROR] Unexpected error: {exc}")
        traceback.print_exc()
        sys.exit(1)
