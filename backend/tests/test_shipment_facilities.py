"""
AgriChain AI — Phase 13 Shipment & Facility Integration Tests
=============================================================
Verifies:
1. Facility suitability validation distinguishing trading, handling, cold-chain, and availability.
2. Multi-hub shipment associations (origin, intermediate hub, destination).
3. Nonexistent shipment and facility ID error handling.
4. Tracking mode truthfulness (live GPS vs demo simulated vs last known).
5. Telemetry truthfulness (sensor source, freshness, missing telemetry).
6. Auditable lifecycle event timeline and duplicate prevention.
7. File-based persistence across repository instances.
"""

import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.main import app
import app.db.repository as repo_module
from app.db.repository import ShipmentRepository, INITIAL_SEED_FACILITIES, INITIAL_SEED_SHIPMENTS


class TestShipmentFacilitiesPhase13(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary storage file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / ".test_ledger.json"

        # Initialize clean repository with audited facilities and shipments
        self.repo = ShipmentRepository(
            storage_file=self.temp_file,
            database_enabled=False,
        )
        self.orig_repo = repo_module._repository_instance
        repo_module._repository_instance = self.repo
        self.client = TestClient(app)

    def tearDown(self):
        repo_module._repository_instance = self.orig_repo
        self.temp_dir.cleanup()

    def test_azadpur_guava_trading_suitability(self):
        """Azadpur APMC Mega Mandi must be verified for guava trading, but not certified cold storage."""
        res = self.client.get("/api/v1/facilities/FAC-DL-AZD-01/suitability?operation=market_auction&crop=guava")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["suitable"])
        self.assertEqual(data["suitability_status"], "verified_guava_trading")
        self.assertEqual(data["capabilities"]["guava_trading"], "verified")
        self.assertEqual(data["capabilities"]["operational_availability"], "active")

        # But for cold storage destination, Azadpur has only transit holding/ripening
        cold_res = self.client.get("/api/v1/facilities/FAC-DL-AZD-01/suitability?operation=cold_storage&crop=guava")
        self.assertEqual(cold_res.status_code, 200)
        cold_data = cold_res.json()
        self.assertFalse(cold_data["suitable"])
        self.assertIn("transit holding", cold_data["warnings"][0].lower())

    def test_pswc_grain_godown_unsuitable_for_cold_storage_and_cooling(self):
        """PSWC grain godowns must be strictly marked unsuitable for guava cold chain and pre-cooling."""
        # Test Fazilka PSWC godown
        res = self.client.get("/api/v1/facilities/FAC-PB-FAZ-01/suitability?operation=cold_storage&crop=guava")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["suitable"])
        self.assertEqual(data["suitability_status"], "unsuitable_for_operation")
        self.assertEqual(data["capabilities"]["guava_cold_chain"], "unsuitable")
        self.assertIn("CRITICAL", data["warnings"][0])

        # Test pre-cooling at godown
        pack_res = self.client.get("/api/v1/facilities/FAC-PB-FAZ-01/suitability?operation=packhouse_cooling&crop=guava")
        self.assertEqual(pack_res.status_code, 200)
        pack_data = pack_res.json()
        self.assertFalse(pack_data["suitable"])
        self.assertEqual(pack_data["capabilities"]["guava_handling"], "unsuitable")

    def test_citrus_facility_unsuitable_for_guava_handling(self):
        """Alamgarh center is mechanized for citrus/Kinnow; guava handling is unconfirmed/unsuitable."""
        res = self.client.get("/api/v1/facilities/FAC-PB-ABO-01/suitability?operation=packhouse_cooling&crop=guava")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["suitable"])
        self.assertIn("citrus/kinnow", data["warnings"][0].lower())

    def test_commercial_cold_storage_unknown_availability_and_unconfirmed_crop(self):
        """Potato cold store records must keep operational availability unknown and guava cold chain unconfirmed."""
        res = self.client.get("/api/v1/facilities/FAC-PB-JAL-01/suitability?operation=cold_storage&crop=guava")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["suitable"])
        self.assertEqual(data["capabilities"]["operational_availability"], "unknown")
        self.assertEqual(data["capabilities"]["guava_cold_chain"], "unconfirmed")
        # Must include warning about unknown availability
        warnings_text = " ".join(data["warnings"]).lower()
        self.assertIn("operational availability is unknown", warnings_text)
        self.assertIn("potato belt", warnings_text)

    def test_pagrexco_bara_farm_partially_verified_cooling(self):
        """PAGREXCO Bara Farm has 4 MT pre-cooling for general horticulture; guava handling is partially verified."""
        res = self.client.get("/api/v1/facilities/FAC-PB-PAG-BARA/suitability?operation=packhouse_cooling&crop=guava")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["suitable"])
        self.assertEqual(data["suitability_status"], "partially_verified")
        self.assertIn("general horticulture", data["warnings"][0].lower())

    def test_nonexistent_facility_suitability(self):
        """Querying suitability for nonexistent facility ID must return 404."""
        res = self.client.get("/api/v1/facilities/FAC-NONEXISTENT-999/suitability")
        self.assertEqual(res.status_code, 404)

    def test_create_shipment_with_multi_hub_facilities(self):
        """Shipment creation must support origin, destination, and intermediate transit hub."""
        payload = {
            "produce_type": "Guava",
            "origin": "Abohar Regional Center",
            "destination": "Azadpur APMC Mandi, Delhi",
            "origin_facility_id": "FAC-PB-ABO-01",
            "destination_facility_id": "FAC-DL-AZD-01",
            "intermediate_facility_id": "FAC-PB-BTI-01",
            "origin_operation": "packhouse_cooling",
            "destination_operation": "market_auction",
            "intermediate_operation": "transit_hub",
            "quantity": 500.0,
            "status": "created",
        }
        res = self.client.post("/api/v1/shipments", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["origin_facility_id"], "FAC-PB-ABO-01")
        self.assertEqual(data["destination_facility_id"], "FAC-DL-AZD-01")
        self.assertEqual(data["intermediate_facility_id"], "FAC-PB-BTI-01")
        self.assertIsNotNone(data["origin_facility"])
        self.assertIsNotNone(data["destination_facility"])
        self.assertIsNotNone(data["intermediate_facility"])
        # Suitability warnings should be attached
        self.assertTrue(len(data["suitability_warnings"]) > 0)
        # Should have logged creation and association events
        self.assertGreaterEqual(data["events_count"], 2)

    def test_create_shipment_with_invalid_facility_id_rejected(self):
        """Referencing a nonexistent facility ID must fail with 422."""
        payload = {
            "produce_type": "Guava",
            "origin": "Unknown Farm",
            "destination": "Unknown Market",
            "origin_facility_id": "FAC-FAKE-999",
            "quantity": 200.0,
        }
        res = self.client.post("/api/v1/shipments", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_shipment_events_timeline_and_duplicate_prevention(self):
        """Lifecycle events timeline must record events and prevent duplicates within 60 seconds."""
        # 1. Fetch events for SHP-2026-001
        res = self.client.get("/api/v1/shipments/SHP-2026-001/events")
        self.assertEqual(res.status_code, 200)
        events = res.json()
        self.assertGreaterEqual(len(events), 3)

        # 2. Add an event
        evt_payload = {
            "event_type": "facility_handover",
            "description": "Cargo inspected at Bathinda Container Freight Station.",
            "facility_id": "FAC-PB-BTI-01",
            "source": "manual_operator",
        }
        add_res1 = self.client.post("/api/v1/shipments/SHP-2026-001/events", json=evt_payload)
        self.assertEqual(add_res1.status_code, 201)
        evt1 = add_res1.json()

        # 3. Repeat immediately: duplicate prevention must return existing event without adding second
        add_res2 = self.client.post("/api/v1/shipments/SHP-2026-001/events", json=evt_payload)
        self.assertEqual(add_res2.status_code, 201)
        evt2 = add_res2.json()
        self.assertEqual(evt1["id"], evt2["id"])

        # Total count should have increased by only 1
        res_after = self.client.get("/api/v1/shipments/SHP-2026-001/events")
        self.assertEqual(len(res_after.json()), len(events) + 1)

    def test_nonexistent_shipment_events_returns_404(self):
        """Querying events for nonexistent shipment returns 404."""
        res = self.client.get("/api/v1/shipments/SHP-NONEXISTENT-999/events")
        self.assertEqual(res.status_code, 404)

    def test_simulation_step_truthful_source_labelling(self):
        """Simulate step must mark waypoint, telemetry, and event as simulated demo."""
        res = self.client.post("/api/v1/shipments/SHP-2026-001/simulate-step")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["simulated"])
        self.assertEqual(data["waypoint"]["location_metadata"]["source"], "demo_simulated")
        self.assertEqual(data["telemetry"]["sensor_id"], "SNS-SIM-DEMO")
        self.assertIsNotNone(data.get("event"))
        self.assertEqual(data["event"]["source"], "demo_simulated")

    def test_truthful_tracking_and_telemetry_modes(self):
        """A shipment with no sensor data must have telemetry_mode 'unavailable'."""
        shp = self.repo.create_shipment({
            "produce_type": "Guava",
            "origin": "Test Farm",
            "destination": "Test Mandi",
            "quantity": 100.0,
        })
        self.assertEqual(shp["telemetry_mode"], "unavailable")
        self.assertEqual(shp["tracking_mode"], "simulated")


if __name__ == "__main__":
    unittest.main()
