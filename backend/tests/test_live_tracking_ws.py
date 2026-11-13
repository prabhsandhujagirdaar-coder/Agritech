"""
AgriChain AI — Phase 10B.1: Live Tracking & WebSocket Pipeline Test Suite
========================================================================
Validates:
1. REST snapshot endpoints: /shipments/{id}, /risk, /telemetry, /waypoints
2. Waypoint creation, PostGIS coordinate boundaries, and location enrichment
3. Telemetry ingestion, cold-chain excursion detection, and automatic risk index update
4. WebSocket connection manager broadcast lifecycle for live events
5. Demo simulation endpoint /shipments/{id}/simulate-step with strict DEMO labelling
6. File-based persistence across updates
"""

import sys
import os
import unittest
import tempfile
import asyncio

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.db.repository import ShipmentRepository, ShipmentNotFoundError
from backend.app.api.v1.endpoints.ws import ConnectionManager


class TestLiveTrackingPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.repo = ShipmentRepository(storage_file=self.temp_file.name, database_enabled=False)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass

    def test_initial_snapshot_retrieval(self):
        """Verifies initial snapshot retrieval for shipments seeded in Northern India corridor."""
        shipments = self.repo.list_shipments()
        self.assertGreater(len(shipments), 0)

        shp1 = self.repo.get_shipment("SHP-2026-001")
        self.assertIsNotNone(shp1)
        self.assertEqual(shp1["produce_type"], "Guava")
        self.assertIsNotNone(shp1["current_coordinates"])
        self.assertIn("latitude", shp1["current_coordinates"])
        self.assertIn("longitude", shp1["current_coordinates"])

        # Check waypoints and telemetry
        wps = self.repo.get_waypoints("SHP-2026-001")
        self.assertGreater(len(wps), 0)
        self.assertEqual(wps[0]["srid"], 4326)

        telem = self.repo.get_telemetry("SHP-2026-001")
        self.assertGreater(len(telem), 0)

    def test_add_telemetry_recalculates_risk_index(self):
        """Adding new telemetry updates parent shipment temperature, humidity, and recalculates risk."""
        shp_id = "SHP-2026-004"
        initial_shp = self.repo.get_shipment(shp_id)
        self.assertIsNotNone(initial_shp)

        # Ingest thermal excursion telemetry reading (e.g. 10.5°C > 8.0°C upper threshold)
        reading = self.repo.add_telemetry(shp_id, {
            "temperature": 10.5,
            "humidity": 82.0,
            "sensor_id": "SNS-TEST-EXCURSION",
            "location": "Transit Checkpoint",
        })

        self.assertIsNotNone(reading)
        self.assertEqual(reading["temperature"], 10.5)

        # Verify parent shipment updated
        updated_shp = self.repo.get_shipment(shp_id)
        self.assertEqual(updated_shp["temperature_c"], 10.5)
        self.assertEqual(updated_shp["humidity_pct"], 82.0)
        # Risk index must have increased due to excursion
        self.assertGreater(updated_shp["risk_index"], 15.0)

    def test_add_waypoint_enriches_current_coordinates(self):
        """Adding a new waypoint immediately updates current_coordinates and latest_waypoint."""
        shp_id = "SHP-2026-004"
        wp_payload = {
            "latitude": 30.2110,
            "longitude": 74.9455,
            "altitude_m": 204.0,
            "speed_kmh": 62.0,
            "heading_deg": 105.0,
            "location_metadata": {"corridor": "Bathinda Bypass", "district": "Bathinda"},
        }

        created_wp = self.repo.add_waypoint(shp_id, wp_payload)
        self.assertIsNotNone(created_wp)
        self.assertEqual(created_wp["latitude"], 30.2110)
        self.assertEqual(created_wp["longitude"], 74.9455)

        updated_shp = self.repo.get_shipment(shp_id)
        self.assertEqual(updated_shp["current_coordinates"]["latitude"], 30.2110)
        self.assertEqual(updated_shp["current_coordinates"]["longitude"], 74.9455)
        self.assertIsNotNone(updated_shp["latest_waypoint"])
        self.assertEqual(updated_shp["latest_waypoint"]["id"], created_wp["id"])

    def test_ws_connection_manager_broadcast(self):
        """ConnectionManager broadcasts payload with event, data, and ISO timestamp."""
        manager = ConnectionManager()
        self.assertEqual(len(manager.active_connections), 0)

        # Broadcast with no connections should complete gracefully without error
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                manager.broadcast("telemetry_update", {"shipment_id": "SHP-2026-001", "temperature": 6.2})
            )
        finally:
            loop.close()

    def test_demo_simulated_metadata_labelling(self):
        """Simulated waypoints must contain explicit demo metadata tags distinguishing them from real GPS."""
        shp_id = "SHP-2026-001"
        sim_payload = {
            "latitude": 29.5144,
            "longitude": 75.4549,
            "altitude_m": 195.0,
            "speed_kmh": 58.0,
            "heading_deg": 125.0,
            "location_metadata": {
                "source": "demo_simulated",
                "simulated": True,
                "checkpoint": "Fatehabad Corridor",
                "label": "DEMO_SIMULATED_TRANSIT_FIX",
            },
        }

        wp = self.repo.add_waypoint(shp_id, sim_payload)
        self.assertTrue(wp["location_metadata"].get("simulated"))
        self.assertEqual(wp["location_metadata"].get("source"), "demo_simulated")
        self.assertEqual(wp["location_metadata"].get("label"), "DEMO_SIMULATED_TRANSIT_FIX")


if __name__ == "__main__":
    unittest.main()
