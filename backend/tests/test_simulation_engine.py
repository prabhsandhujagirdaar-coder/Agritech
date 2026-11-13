"""
AgriChain AI — Unit & Integration Tests for Dynamic Vehicle Simulation
======================================================================
Verifies:
1. Geocoding search across Indian mandis, facilities, and boundary enforcement.
2. Road routing service geometry, distance calculations, and bearing.
3. Distance-based polyline interpolation accuracy (vehicle stays on road).
4. SimulationEngine state machine, controls, speed multipliers, and scenarios.
5. Rolling 24-step LSTM transit risk engine.
6. API endpoint contracts and repository persistence.
"""

import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.db.repository import get_shipment_repository
from app.services.geocoding_service import get_geocoding_service
from app.services.routing_service import (
    get_routing_service,
    haversine_distance_km,
    calculate_bearing_deg,
)
from app.services.simulation_engine import get_simulation_engine


class TestDynamicVehicleSimulation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.repo = get_shipment_repository()
        self.routing = get_routing_service()
        self.geocoding = get_geocoding_service()
        self.engine = get_simulation_engine()

    def test_01_geocoding_search(self):
        """Verifies geocoding returns verified Indian agricultural locations."""
        results = self.geocoding.search_locations("Abohar", limit=5)
        self.assertGreater(len(results), 0)
        abohar = results[0]
        self.assertIn("abohar", abohar["name"].lower())
        self.assertTrue(28.0 <= abohar["latitude"] <= 32.6)
        self.assertTrue(73.5 <= abohar["longitude"] <= 77.8)

        # Search Azadpur
        azadpur_res = self.geocoding.search_locations("Azadpur", limit=5)
        self.assertGreater(len(azadpur_res), 0)
        self.assertIn("azadpur", azadpur_res[0]["name"].lower())

    def test_02_haversine_and_bearing(self):
        """Verifies Haversine distance and bearing calculations."""
        # Abohar to Azadpur Mandi approx 330-360 km
        dist = haversine_distance_km(30.1453, 74.1994, 28.7161, 77.1772)
        self.assertGreater(dist, 300.0)
        self.assertLess(dist, 400.0)

        # Bearing from Abohar (NW) towards Delhi (SE) should be roughly 100° - 150°
        bearing = calculate_bearing_deg(30.1453, 74.1994, 28.7161, 77.1772)
        self.assertGreater(bearing, 90.0)
        self.assertLess(bearing, 180.0)

    def test_03_road_route_generation(self):
        """Verifies road routing produces valid GeoJSON LineString coordinates."""
        route = self.routing.get_route(30.1453, 74.1994, 28.7161, 77.1772)
        self.assertIn("geometry", route)
        self.assertEqual(route["geometry"]["type"], "LineString")
        coords = route["geometry"]["coordinates"]
        self.assertGreaterEqual(len(coords), 10)
        self.assertGreater(route["distance_km"], 300.0)
        self.assertGreater(route["duration_s"], 10000.0)

        # Verify coordinates are [lon, lat] pairs within India
        for pt in coords:
            self.assertEqual(len(pt), 2)
            lon, lat = pt[0], pt[1]
            self.assertTrue(68.0 <= lon <= 97.5)
            self.assertTrue(8.0 <= lat <= 37.5)

    def test_04_polyline_distance_interpolation(self):
        """Verifies precise distance-based interpolation along road polyline."""
        route = self.routing.get_route(30.1453, 74.1994, 28.7161, 77.1772)
        coords = route["geometry"]["coordinates"]
        total_km = route["distance_km"]

        # At 0 km: must be origin
        fix_0 = self.routing.interpolate_polyline_position(coords, 0.0)
        self.assertAlmostEqual(fix_0["latitude"], coords[0][1], places=4)
        self.assertAlmostEqual(fix_0["longitude"], coords[0][0], places=4)
        self.assertEqual(fix_0["progress_pct"], 0.0)
        self.assertFalse(fix_0["is_completed"])

        # At halfway: progress must be ~50%
        fix_mid = self.routing.interpolate_polyline_position(coords, total_km * 0.5)
        self.assertAlmostEqual(fix_mid["progress_pct"], 50.0, delta=1.0)
        self.assertFalse(fix_mid["is_completed"])
        self.assertGreater(fix_mid["distance_remaining_km"], 0.0)

        # At 100% distance: must be destination point and completed
        fix_end = self.routing.interpolate_polyline_position(coords, total_km + 10.0)
        self.assertAlmostEqual(fix_end["latitude"], coords[-1][1], places=4)
        self.assertAlmostEqual(fix_end["longitude"], coords[-1][0], places=4)
        self.assertEqual(fix_end["progress_pct"], 100.0)
        self.assertTrue(fix_end["is_completed"])

    def test_05_api_simulation_lifecycle(self):
        """Verifies full API lifecycle: create, step, scenario switch, telemetry retrieval."""
        # 1. Search location
        search_res = self.client.post("/api/v1/simulations/geocoding/search", json={"query": "Fazilka"})
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()
        self.assertGreater(len(results), 0)

        # 2. Preview route
        prev_res = self.client.post(
            "/api/v1/simulations/routes/preview",
            json={
                "origin_name": "Fazilka CA Store",
                "origin_lat": 30.4037,
                "origin_lon": 74.0254,
                "destination_name": "Ludhiana Agro",
                "destination_lat": 30.9010,
                "destination_lon": 75.8573,
            },
        )
        self.assertEqual(prev_res.status_code, 200)
        prev_data = prev_res.json()
        self.assertGreater(prev_data["distance_km"], 100.0)
        self.assertEqual(prev_data["geometry"]["type"], "LineString")

        # 3. Create simulation session
        create_res = self.client.post(
            "/api/v1/simulations/",
            json={
                "origin_name": "Fazilka CA Store",
                "origin_lat": 30.4037,
                "origin_lon": 74.0254,
                "destination_name": "Ludhiana Agro",
                "destination_lat": 30.9010,
                "destination_lon": 75.8573,
                "speed_multiplier": 2.0,
                "scenario": "normal",
            },
        )
        self.assertEqual(create_res.status_code, 201)
        sim_data = create_res.json()
        sim_id = sim_data["id"]
        self.assertEqual(sim_data["status"], "READY")
        self.assertEqual(sim_data["step_count"], 0)

        # 4. Step simulation
        step_res = self.client.post(f"/api/v1/simulations/{sim_id}/step?advance_km=15.0")
        self.assertEqual(step_res.status_code, 200)
        step_data = step_res.json()
        self.assertEqual(step_data["step_count"], 1)
        self.assertGreater(step_data["current_distance_km"], 10.0)

        # 5. Check telemetry
        tel_res = self.client.get(f"/api/v1/simulations/{sim_id}/telemetry")
        self.assertEqual(tel_res.status_code, 200)
        points = tel_res.json()
        self.assertEqual(len(points), 1)
        first_pt = points[0]
        self.assertEqual(first_pt["data_source"], "simulation")
        self.assertEqual(first_pt["sensor_id"], "SNS-SIM-DEMO")
        self.assertTrue(3.0 <= first_pt["temperature_c"] <= 10.0)

        # 6. Update scenario to temperature excursion
        ctrl_res = self.client.patch(
            f"/api/v1/simulations/{sim_id}/controls",
            json={"action": "update", "scenario": "temperature_excursion"},
        )
        self.assertEqual(ctrl_res.status_code, 200)
        self.assertEqual(ctrl_res.json()["scenario"], "temperature_excursion")

        # Advance 4 more steps to trigger excursion risk alert
        for _ in range(4):
            self.client.post(f"/api/v1/simulations/{sim_id}/step?advance_km=20.0")

        history_res = self.client.get(f"/api/v1/simulations/{sim_id}/history")
        self.assertEqual(history_res.status_code, 200)
        hist = history_res.json()
        self.assertEqual(hist["total_steps"], 5)
        latest_tel = hist["telemetry_points"][-1]
        self.assertGreater(latest_tel["temperature_c"], 7.0)
        self.assertGreater(latest_tel["risk_score"], 15.0)

        # 7. Reset simulation
        reset_res = self.client.post(f"/api/v1/simulations/{sim_id}/reset")
        self.assertEqual(reset_res.status_code, 200)
        self.assertEqual(reset_res.json()["status"], "READY")
        self.assertEqual(reset_res.json()["current_distance_km"], 0.0)


if __name__ == "__main__":
    unittest.main()

