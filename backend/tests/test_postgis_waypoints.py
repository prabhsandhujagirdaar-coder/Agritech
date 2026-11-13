"""
AgriChain AI — Phase 10A: PostGIS & Waypoints Unit Test Suite

Tests:
1. Coordinate boundary validation (-90 <= lat <= 90, -180 <= lon <= 180).
2. Waypoint creation, chronological ordering, and persistence.
3. Shipment coordinates enrichment: latest waypoint coordinates attached as current_coordinates.
4. Shipments without waypoints correctly have current_coordinates = None.
5. Non-fabrication: ensure no fake default coordinates (e.g. 0,0) are assigned.
"""

import sys
import os
import unittest
import tempfile
from datetime import datetime, timezone

# Ensure project root and backend dir are in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app.db.repository import ShipmentRepository, ShipmentNotFoundError
from backend.app.schemas.telemetry import GeoWaypointCreate


class TestPostgisWaypoints(unittest.TestCase):
    def setUp(self):
        # Create a clean temporary storage file for each test
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.repo = ShipmentRepository(storage_file=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass

    def test_add_waypoint_valid_coordinates(self):
        """Valid WGS84 coordinates should succeed and enrich shipment current_coordinates."""
        shipment = self.repo.create_shipment({
            "id": "SHP-TEST-001",
            "produce_type": "Guava",
            "produce": "Guava",
            "origin": "Lahore Farm",
            "destination": "Islamabad Cold Hub",
            "quantity": 1000.0,
            "quantity_crates": 50,
            "status": "in_transit"
        })
        self.assertIsNotNone(shipment)
        self.assertIsNone(shipment.get("current_coordinates"))

        wp_payload = {
            "latitude": 31.5204,
            "longitude": 74.3587,
            "speed_kmh": 45.5,
        }
        created_wp = self.repo.add_waypoint("SHP-TEST-001", wp_payload)
        self.assertIsNotNone(created_wp)
        self.assertEqual(created_wp["latitude"], 31.5204)
        self.assertEqual(created_wp["longitude"], 74.3587)

        # Re-fetch shipment and verify enriched coordinates
        updated_shipment = self.repo.get_shipment("SHP-TEST-001")
        self.assertIsNotNone(updated_shipment)
        self.assertIsNotNone(updated_shipment.get("current_coordinates"))
        self.assertEqual(updated_shipment["current_coordinates"]["latitude"], 31.5204)
        self.assertEqual(updated_shipment["current_coordinates"]["longitude"], 74.3587)
        self.assertIsNotNone(updated_shipment.get("latest_waypoint"))

    def test_add_waypoint_invalid_coordinates_rejected(self):
        """Out-of-bounds coordinates must raise ValueError and not corrupt state."""
        self.repo.create_shipment({
            "id": "SHP-TEST-002",
            "produce_type": "Guava",
            "produce": "Guava",
            "origin": "Multan",
            "destination": "Lahore",
            "quantity": 500.0,
            "quantity_crates": 25,
            "status": "in_transit"
        })

        # Test Latitude > 90
        with self.assertRaises(ValueError):
            self.repo.add_waypoint("SHP-TEST-002", {"latitude": 91.0, "longitude": 74.0})

        # Test Latitude < -90
        with self.assertRaises(ValueError):
            self.repo.add_waypoint("SHP-TEST-002", {"latitude": -90.1, "longitude": 74.0})

        # Test Longitude > 180
        with self.assertRaises(ValueError):
            self.repo.add_waypoint("SHP-TEST-002", {"latitude": 31.0, "longitude": 180.5})

        # Test Longitude < -180
        with self.assertRaises(ValueError):
            self.repo.add_waypoint("SHP-TEST-002", {"latitude": 31.0, "longitude": -181.0})

    def test_waypoints_chronological_ordering(self):
        """Multiple waypoints should be chronologically tracked and latest becomes current_coordinates."""
        self.repo.create_shipment({
            "id": "SHP-TEST-003",
            "produce_type": "Guava",
            "produce": "Guava",
            "origin": "Faisalabad",
            "destination": "Rawalpindi",
            "quantity": 800.0,
            "quantity_crates": 40,
            "status": "in_transit"
        })

        # Add waypoint 1 (Lahore)
        self.repo.add_waypoint("SHP-TEST-003", {
            "latitude": 31.5204,
            "longitude": 74.3587,
            "speed_kmh": 40.0
        })

        # Add waypoint 2 (Gujranwala - further north)
        self.repo.add_waypoint("SHP-TEST-003", {
            "latitude": 32.1877,
            "longitude": 74.1945,
            "speed_kmh": 55.0
        })

        # Add waypoint 3 (Rawalpindi destination)
        self.repo.add_waypoint("SHP-TEST-003", {
            "latitude": 33.5651,
            "longitude": 73.0169,
            "speed_kmh": 30.0
        })

        waypoints = self.repo.get_waypoints("SHP-TEST-003")
        self.assertEqual(len(waypoints), 3)

        shipment = self.repo.get_shipment("SHP-TEST-003")
        # Latest coordinates must match the 3rd waypoint (Rawalpindi)
        self.assertEqual(shipment["current_coordinates"]["latitude"], 33.5651)
        self.assertEqual(shipment["current_coordinates"]["longitude"], 73.0169)

    def test_shipment_without_waypoints_has_null_coordinates(self):
        """Shipments with no waypoints must return None for current_coordinates (no default spoofing)."""
        self.repo.create_shipment({
            "id": "SHP-TEST-004",
            "produce_type": "Guava",
            "produce": "Guava",
            "origin": "Sargodha",
            "destination": "Karachi",
            "quantity": 1200.0,
            "quantity_crates": 60,
            "status": "created"
        })

        shipment = self.repo.get_shipment("SHP-TEST-004")
        self.assertIsNotNone(shipment)
        self.assertIsNone(shipment.get("current_coordinates"))
        self.assertIsNone(shipment.get("latest_waypoint"))

        # Ensure in list_shipments it also returns None
        all_shipments = self.repo.list_shipments()
        target = next((s for s in all_shipments if s["id"] == "SHP-TEST-004"), None)
        self.assertIsNotNone(target)
        self.assertIsNone(target.get("current_coordinates"))

    def test_schema_validation(self):
        """Test GeoWaypointCreate Pydantic schema boundary constraints."""
        valid_wp = GeoWaypointCreate(latitude=31.5204, longitude=74.3587, speed_kmh=50.0)
        self.assertEqual(valid_wp.latitude, 31.5204)
        self.assertEqual(valid_wp.longitude, 74.3587)

        # Out-of-bounds in schema validation
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            GeoWaypointCreate(latitude=95.0, longitude=74.3587)
        with self.assertRaises(ValidationError):
            GeoWaypointCreate(latitude=31.5204, longitude=185.0)


if __name__ == "__main__":
    unittest.main()
