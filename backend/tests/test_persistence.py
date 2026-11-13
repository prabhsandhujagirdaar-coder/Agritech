"""
AgriChain AI — Phase 3 Persistence & PostGIS Test Suite
======================================================
Tests shipment creation, telemetry ingestion, PostGIS waypoint handling,
foreign key enforcement, restart persistence, database failure safeguards,
and API contract parity.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.db.repository import ShipmentRepository, get_shipment_repository
from app.db.session import (
    DatabaseConnectionError,
    ForeignKeyViolationError,
    ShipmentNotFoundError,
    probe_database_connection,
)
from app.main import app
from tests.test_client_compat import TestClient


class TestShipmentPersistence(unittest.TestCase):
    """Unit tests for ShipmentRepository and data persistence layer."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_storage = Path(self.temp_dir.name) / "test_storage.json"
        self.repo = ShipmentRepository(
            storage_file=self.temp_storage,
            database_enabled=False,
        )

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_initial_seed_shipments(self):
        """Repository initializes with default Punjab corridor seeds when file is fresh."""
        shipments = self.repo.list_shipments()
        self.assertGreaterEqual(len(shipments), 2)
        shp1 = self.repo.get_shipment("SHP-2026-001")
        self.assertIsNotNone(shp1)
        self.assertEqual(shp1["produce_type"], "Guava")
        self.assertIn("Abohar", shp1["origin"])

    def test_create_shipment(self):
        """Shipment creation returns proper fields and increments list."""
        count_before = len(self.repo.list_shipments())
        new_shp = self.repo.create_shipment({
            "produce_type": "Kinnow Mandarin",
            "origin": "Hoshiarpur Packhouse, Punjab",
            "destination": "Chandigarh Mandi, Punjab",
            "quantity": 300.0,
            "status": "created",
        })
        self.assertTrue(new_shp["id"].startswith("SHP-2026-"))
        self.assertEqual(new_shp["produce_type"], "Kinnow Mandarin")
        self.assertEqual(new_shp["quantity"], 300.0)
        self.assertEqual(len(self.repo.list_shipments()), count_before + 1)

        # Confirm retrieval
        fetched = self.repo.get_shipment(new_shp["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["origin"], "Hoshiarpur Packhouse, Punjab")

    def test_telemetry_insertion_and_fk_enforcement(self):
        """Telemetry must reference an existing shipment; non-existent shipment raises error."""
        # 1. Valid shipment telemetry
        telemetry = self.repo.add_telemetry("SHP-2026-001", {
            "temperature": 5.8,
            "humidity": 89.2,
            "sensor_id": "SNS-TEST-01",
            "location": "Bathinda Bypass, Punjab",
        })
        self.assertEqual(telemetry["shipment_id"], "SHP-2026-001")
        self.assertEqual(telemetry["temperature"], 5.8)

        # Verify parent shipment was updated with latest reading
        shp = self.repo.get_shipment("SHP-2026-001")
        self.assertEqual(shp["temperature_c"], 5.8)
        self.assertEqual(shp["humidity_pct"], 89.2)

        # 2. Foreign-key violation: non-existent shipment
        with self.assertRaises(ShipmentNotFoundError):
            self.repo.add_telemetry("SHP-NON-EXISTENT", {
                "temperature": 12.0,
                "humidity": 70.0,
                "sensor_id": "SNS-TEST-02",
            })

    def test_geo_waypoints_srid_4326(self):
        """Waypoints record explicit GPS coordinates with PostGIS SRID 4326 without fabricating coordinates."""
        # Waypoint for SHP-2026-001 (Abohar)
        waypoint = self.repo.add_waypoint("SHP-2026-001", {
            "longitude": 74.1994,
            "latitude": 30.1453,
            "altitude_m": 186.5,
            "speed_kmh": 50.0,
            "heading_deg": 90.0,
            "location_metadata": {"station": "Abohar Toll Plaza"},
        })
        self.assertEqual(waypoint["shipment_id"], "SHP-2026-001")
        self.assertEqual(waypoint["srid"], 4326)
        self.assertEqual(waypoint["longitude"], 74.1994)
        self.assertEqual(waypoint["latitude"], 30.1453)

        waypoints = self.repo.get_waypoints("SHP-2026-001")
        self.assertTrue(any(w["id"] == waypoint["id"] for w in waypoints))

        # Waypoint for non-existent shipment raises ShipmentNotFoundError
        with self.assertRaises(ShipmentNotFoundError):
            self.repo.add_waypoint("SHP-GHOST", {
                "longitude": 75.0,
                "latitude": 31.0,
            })

    def test_persistence_across_restarts(self):
        """Data written to storage file must persist across a simulated process restart."""
        # Session 1: Create shipment and telemetry in repo instance 1
        shp = self.repo.create_shipment({
            "produce_type": "Kinnow Mandarin",
            "origin": "Fazilka Cluster, Punjab",
            "destination": "Ludhiana APMC, Punjab",
            "quantity": 500.0,
        })
        shp_id = shp["id"]
        self.repo.add_telemetry(shp_id, {
            "temperature": 6.8,
            "humidity": 85.0,
            "sensor_id": "SNS-RESTART-01",
            "location": "Muktsar Road",
        })
        self.repo.add_waypoint(shp_id, {
            "longitude": 74.5123,
            "latitude": 30.4821,
            "altitude_m": 190.0,
        })

        # Simulate Restart: re-initialize repo pointing to the same storage ledger file
        restarted_repo = ShipmentRepository(
            storage_file=self.temp_storage,
            database_enabled=False,
        )

        # Verify shipment persisted
        restarted_shp = restarted_repo.get_shipment(shp_id)
        self.assertIsNotNone(restarted_shp, f"Shipment '{shp_id}' did not survive restart!")
        self.assertEqual(restarted_shp["origin"], "Fazilka Cluster, Punjab")
        self.assertEqual(restarted_shp["temperature_c"], 6.8)

        # Verify telemetry persisted
        telemetry_list = restarted_repo.get_telemetry(shp_id)
        self.assertEqual(len(telemetry_list), 1)
        self.assertEqual(telemetry_list[0]["sensor_id"], "SNS-RESTART-01")

        # Verify waypoint persisted
        waypoint_list = restarted_repo.get_waypoints(shp_id)
        self.assertEqual(len(waypoint_list), 1)
        self.assertEqual(waypoint_list[0]["srid"], 4326)
        self.assertEqual(waypoint_list[0]["longitude"], 74.5123)

    @patch.dict(os.environ, {"SYNC_DATABASE_URL": "postgresql://127.0.0.1:5439/unreachable", "DATABASE_URL": "postgresql+asyncpg://127.0.0.1:5439/unreachable"})
    def test_no_silent_fallback_when_database_enabled_and_unreachable(self):
        """When DATABASE_ENABLED=True and database is offline, raise DatabaseConnectionError."""
        # Attempt to create repository with database_enabled=True when DB is unreachable
        with self.assertRaises(DatabaseConnectionError) as ctx:
            ShipmentRepository(
                storage_file=self.temp_storage,
                database_enabled=True,
            )
        self.assertIn("Silent fallback to in-memory fixtures is strictly disabled", str(ctx.exception))


class TestAPIContractParity(unittest.TestCase):
    """Verifies that API endpoint responses match expected contracts."""

    def setUp(self):
        self.client = TestClient(app)

    def test_list_shipments_api(self):
        """GET /api/v1/shipments returns 200 and list of shipments."""
        resp = self.client.get("/api/v1/shipments")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("id", data[0])
        self.assertIn("produce_type", data[0])

    def test_create_and_get_shipment_api(self):
        """POST /api/v1/shipments creates shipment (201); GET returns shipment detail (200)."""
        payload = {
            "produce_type": "Kinnow Mandarin",
            "origin": "Abohar Packhouse, Punjab",
            "destination": "Jaipur Mandi, Rajasthan",
            "quantity": 350.0,
            "status": "created",
        }
        create_resp = self.client.post("/api/v1/shipments", json=payload)
        self.assertEqual(create_resp.status_code, 201)
        created = create_resp.json()
        shp_id = created["id"]
        self.assertEqual(created["produce_type"], "Kinnow Mandarin")
        self.assertEqual(created["quantity"], 350.0)

        # GET detail
        get_resp = self.client.get(f"/api/v1/shipments/{shp_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], shp_id)

    def test_telemetry_post_and_foreign_key_api(self):
        """Telemetry ingestion adheres to status codes: 201 on success, 404 for missing shipment."""
        # Valid shipment
        tel_payload = {
            "temperature": 6.3,
            "humidity": 87.5,
            "sensor_id": "SNS-TEST-42",
            "location": "Bathinda Bypass",
        }
        resp = self.client.post("/api/v1/shipments/SHP-2026-001/telemetry", json=tel_payload)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["temperature"], 6.3)

        # Invalid shipment -> 404
        bad_resp = self.client.post("/api/v1/shipments/NON-EXISTENT-ID/telemetry", json=tel_payload)
        self.assertEqual(bad_resp.status_code, 404)

    def test_waypoints_api(self):
        """GET & POST /api/v1/shipments/{id}/waypoints."""
        way_payload = {
            "longitude": 74.2000,
            "latitude": 30.1500,
            "altitude_m": 185.0,
            "speed_kmh": 48.0,
            "heading_deg": 80.0,
            "location_metadata": {"checkpoint": "Punjab Border"},
        }
        post_resp = self.client.post("/api/v1/shipments/SHP-2026-001/waypoints", json=way_payload)
        self.assertEqual(post_resp.status_code, 201)
        self.assertEqual(post_resp.json()["srid"], 4326)

        get_resp = self.client.get("/api/v1/shipments/SHP-2026-001/waypoints")
        self.assertEqual(get_resp.status_code, 200)
        self.assertIsInstance(get_resp.json(), list)

    def test_nextjs_proxy_routes_compatibility(self):
        """Next.js proxy routes /api/shipments and /api/telemetry/predict maintain 100% parity."""
        # /api/shipments
        resp = self.client.get("/api/shipments")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

        # /api/telemetry/predict
        pred_payload = {
            "shipment_id": "SHP-2026-001",
            "sequence": [
                {"temperature": 6.2, "humidity": 88.0, "timestamp": "2026-10-18T10:00:00Z"},
                {"temperature": 6.5, "humidity": 87.5, "timestamp": "2026-10-18T11:00:00Z"},
            ],
        }
        pred_resp = self.client.post("/api/telemetry/predict", json=pred_payload)
        self.assertEqual(pred_resp.status_code, 200)
        data = pred_resp.json()
        self.assertIn("current_risk", data)
        self.assertIn("predicted_arrival_risk", data)
        self.assertIn("alert", data)
        self.assertIn("inference_ms", data)


class TestMigrationSchema(unittest.TestCase):
    """Verifies PostGIS migration scripts syntax, tables, SRID, indexes and CLI."""

    def test_migration_sql_files_exist_and_contain_postgis(self):
        """Migration SQL files must define postgis extension, SRID 4326 geometry, and GiST index."""
        schema_file = backend_dir.parent / "database" / "migrations" / "001_initial_postgis_schema.sql"
        rollback_file = backend_dir.parent / "database" / "migrations" / "001_initial_postgis_schema_rollback.sql"

        self.assertTrue(schema_file.exists(), f"Missing schema migration: {schema_file}")
        self.assertTrue(rollback_file.exists(), f"Missing rollback migration: {rollback_file}")

        sql = schema_file.read_text(encoding="utf-8")
        self.assertIn("CREATE EXTENSION IF NOT EXISTS postgis;", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS shipments", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS telemetry_logs", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS geo_waypoints", sql)
        self.assertIn("coordinates geometry(Point, 4326)", sql)
        self.assertIn("USING GIST (coordinates);", sql)
        self.assertIn("REFERENCES shipments(id) ON DELETE CASCADE", sql)

        # Rollback check
        rollback_sql = rollback_file.read_text(encoding="utf-8")
        self.assertIn("DROP TABLE IF EXISTS geo_waypoints", rollback_sql)
        self.assertIn("DROP TABLE IF EXISTS telemetry_logs", rollback_sql)
        self.assertIn("DROP TABLE IF EXISTS shipments", rollback_sql)

    @patch.dict(os.environ, {"SYNC_DATABASE_URL": "postgresql://127.0.0.1:5439/unreachable"})
    def test_database_probe_reports_offline_without_crashing(self):
        """Database probe accurately reports offline status when port is closed."""
        is_open, msg = probe_database_connection()
        self.assertFalse(is_open)
        self.assertIn("unreachable", msg.lower())

    def test_database_probe_reports_online_when_database_is_reachable(self):
        """Database probe accurately reports online status when PostgreSQL is reachable."""
        is_open, msg = probe_database_connection()
        if not is_open:
            self.skipTest("PostgreSQL container is offline on host port 5432.")
        self.assertTrue(is_open)
        self.assertIn("reachable", msg.lower())


if __name__ == "__main__":
    unittest.main()
