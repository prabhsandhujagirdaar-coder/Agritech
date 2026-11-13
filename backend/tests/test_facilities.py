"""
AgriChain AI — Phase 12: Storage Facilities & Godown Management Unit Tests
Sourced Real Facility Data, Provenance Verification, Spatial Integrity & Regression Tests

Tests:
1. Sourced initial facilities (PAGREXCO Bara Farm, Kangmai, Alamgarh; PSWC godowns; NHB cold stores).
2. Non-fabrication & transparency:
   - Verified facilities have documented source URLs, source records, and provenance notes.
   - Dry storage/PDS godowns have null temperatures (no fabricated cold-room values).
   - Facilities without documented capacity have null capacity (no invented numbers).
3. Facility listing, search (q), and multi-criteria filtering (by facility_type, district, verification_status).
4. Schema validation & nullable optional fields (null coordinates, null capacity, null contact).
5. Coordinate validation:
   - Coordinates inside India pass.
   - Coordinates outside India boundary are rejected (422 / ValueError).
   - Null coordinates are accepted (records without GPS geocoding).
6. Duplicate prevention on restarts / re-initializations.
7. Shipment-facility relationship consistency & backwards compatibility:
   - Shipments link to real facilities without foreign key regression.
   - Enriched facility metadata is serialized properly.
"""

import sys
import os
import unittest
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.core.geo import is_within_india, is_within_punjab_corridor, validate_indian_coordinate
from app.db.repository import ShipmentRepository
from app.schemas.facility import FacilityVerificationStatus
from app.main import app


class TestFacilitiesPhase12(unittest.TestCase):
    def setUp(self):
        import app.db.repository as repo_module
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.repo = ShipmentRepository(storage_file=self.temp_file.name)
        self._orig_repo = repo_module._repository_instance
        repo_module._repository_instance = self.repo
        self.client = TestClient(app)

    def tearDown(self):
        import app.db.repository as repo_module
        repo_module._repository_instance = self._orig_repo
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass

    def test_geo_boundary_functions(self):
        """Test Indian and Punjab corridor bounding box checks."""
        # Punjab - Sirhind (Bara Farm)
        self.assertTrue(is_within_india(30.6283, 76.3863))
        self.assertTrue(is_within_punjab_corridor(30.6283, 76.3863))

        # Punjab - Kangmai (Hoshiarpur)
        self.assertTrue(is_within_india(31.6677, 75.7923))
        self.assertTrue(is_within_punjab_corridor(31.6677, 75.7923))

        # Delhi - Azadpur Mandi
        self.assertTrue(is_within_india(28.7161, 77.1706))
        self.assertTrue(is_within_punjab_corridor(28.7161, 77.1706))

        # Far outside India - London (51.5, -0.1)
        self.assertFalse(is_within_india(51.5074, -0.1278))
        self.assertFalse(is_within_punjab_corridor(51.5074, -0.1278))

        # Outside India throws ValueError
        with self.assertRaises(ValueError):
            validate_indian_coordinate(51.5, 0.0)

        # Valid Indian coordinate passes without error
        validate_indian_coordinate(30.6283, 76.3863)

    def test_list_facilities_seeded_with_sourced_records(self):
        """GET /api/v1/facilities returns sourced facilities with provenance metadata."""
        response = self.client.get("/api/v1/facilities")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 12)

        # Map by ID for assertion checks
        fac_by_id = {f["id"]: f for f in data}

        # 1. PAGREXCO Bara Farm (Sirhind)
        self.assertIn("FAC-PB-PAG-BARA", fac_by_id)
        bara = fac_by_id["FAC-PB-PAG-BARA"]
        self.assertIn("Bara Farm", bara["name"])
        self.assertEqual(bara["district"], "Fatehgarh Sahib")
        self.assertEqual(bara["capacity"], 24.0)
        self.assertEqual(bara["capacity_unit"], "MT")
        self.assertEqual(bara["verification_status"], "verified")
        self.assertIn("punjabagro.gov.in", bara["source_url"])
        self.assertIn("Horticultural Produce", bara["supported_commodities"])

        # 2. PAGREXCO Kangmai (Hoshiarpur)
        self.assertIn("FAC-PB-PAG-KANG", fac_by_id)
        kang = fac_by_id["FAC-PB-PAG-KANG"]
        self.assertIn("Kangmai", kang["name"])
        self.assertEqual(kang["district"], "Hoshiarpur")
        self.assertEqual(kang["capacity"], 54.0)
        self.assertEqual(kang["verification_status"], "verified")

        # 3. PSWC Godown (Bathinda) - Dry grain storage must NOT have fabricated temperatures
        self.assertIn("FAC-PB-BTI-01", fac_by_id)
        pswc_bti = fac_by_id["FAC-PB-BTI-01"]
        self.assertEqual(pswc_bti["facility_type"], "godown")
        self.assertIsNone(pswc_bti["storage_temperature_min_c"])
        self.assertIsNone(pswc_bti["storage_temperature_max_c"])
        self.assertEqual(pswc_bti["verification_status"], "verified")
        self.assertIn("pswc.in", pswc_bti["source_url"])

        # 4. NHB Cold Store (Rabb Cold Store Shahkot) - Unconfirmed capacity kept null per audit rules
        self.assertIn("FAC-PB-JAL-01", fac_by_id)
        rabb = fac_by_id["FAC-PB-JAL-01"]
        self.assertEqual(rabb["facility_type"], "cold_storage")
        self.assertIsNone(rabb["capacity"])
        self.assertEqual(rabb["verification_status"], "partially_verified")
        self.assertIn("nhb.gov.in", rabb["source_url"])

        # 5. Azadpur APMC (Delhi) - Sourced from official APMC Delhi portal
        self.assertIn("FAC-DL-AZD-01", fac_by_id)
        azd = fac_by_id["FAC-DL-AZD-01"]
        self.assertEqual(azd["facility_type"], "mandi")
        self.assertEqual(azd["verification_status"], "verified")
        self.assertIn("apmcazadpurdelhi.com", azd["source_url"])
        self.assertEqual(azd["contact_phone"], "011-27691807")
        self.assertIn("Guava", azd["supported_commodities"])

    def test_filter_facilities_by_type_district_and_status(self):
        """Test facility filtering by type, district, verification_status and search keyword q."""
        # 1. Filter packhouses
        res = self.client.get("/api/v1/facilities?facility_type=packhouse")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(all(f["facility_type"] == "packhouse" for f in data))
        self.assertGreaterEqual(len(data), 3)

        # 2. Filter by district (Fatehgarh Sahib)
        res = self.client.get("/api/v1/facilities?district=Fatehgarh Sahib")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(all(f["district"] == "Fatehgarh Sahib" for f in data))
        self.assertGreaterEqual(len(data), 1)

        # 3. Filter by verification status (verified = 5, partially_verified = 7)
        res_v = self.client.get("/api/v1/facilities?verification_status=verified")
        self.assertEqual(res_v.status_code, 200)
        data_v = res_v.json()
        self.assertTrue(all(f["verification_status"] == "verified" for f in data_v))
        self.assertGreaterEqual(len(data_v), 5)

        res_pv = self.client.get("/api/v1/facilities?verification_status=partially_verified")
        self.assertEqual(res_pv.status_code, 200)
        data_pv = res_pv.json()
        self.assertTrue(all(f["verification_status"] == "partially_verified" for f in data_pv))
        self.assertGreaterEqual(len(data_pv), 7)

        # 4. Search query (q=Sirhind)
        res = self.client.get("/api/v1/facilities?q=Sirhind")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertTrue(any("Sirhind" in f["address"] or "Sirhind" in f["village_or_city"] for f in data))

    def test_get_facility_by_id_and_provenance(self):
        """GET /api/v1/facilities/{id} returns complete provenance for a sourced facility."""
        res_ok = self.client.get("/api/v1/facilities/FAC-PB-PAG-BARA")
        self.assertEqual(res_ok.status_code, 200)
        facility = res_ok.json()
        self.assertEqual(facility["id"], "FAC-PB-PAG-BARA")
        self.assertEqual(facility["village_or_city"], "Bara Farm")
        self.assertIn("Sirhind", facility["address"])
        self.assertEqual(facility["verification_status"], "verified")
        self.assertIn("EOI for Pack House cum Cold Storage", facility["source_record"])
        self.assertIn("EOI-Pack-House-cum-Cold-Storage.pdf", facility["source_url"])
        self.assertIsNotNone(facility["data_provenance"])
        self.assertIsNotNone(facility["verification_date"])

        # 404 for unknown facility
        res_404 = self.client.get("/api/v1/facilities/FAC-NON-EXISTENT")
        self.assertEqual(res_404.status_code, 404)

    def test_create_facility_with_nullable_optional_fields(self):
        """POST /api/v1/facilities accepts missing coordinates and optional fields without inventing defaults."""
        payload_missing_coords = {
            "name": "Muktsar Regional Warehouse Lead",
            "facility_type": "warehouse",
            "address": "Kotkapura Road, Muktsar",
            "village_or_city": "Sri Muktsar Sahib",
            "district": "Muktsar",
            "state": "Punjab",
            "postal_code": None,
            "latitude": None,
            "longitude": None,
            "capacity": None,
            "capacity_unit": None,
            "contact_phone": None,
            "contact_email": None,
            "supported_commodities": None,
            "source_name": "Punjab Mandi Board Directory",
            "source_url": "https://epos.punjab.gov.in/",
            "source_record": "District Warehouse Register Vol 4",
            "verification_status": "partially_verified",
            "coordinate_source": None,
            "geocoding_confidence": "unverified",
            "data_provenance": "Record listed in district food-supply ledger; GPS pending field verification."
        }

        res = self.client.post("/api/v1/facilities", json=payload_missing_coords)
        self.assertEqual(res.status_code, 201)
        created = res.json()
        self.assertEqual(created["name"], "Muktsar Regional Warehouse Lead")
        self.assertIsNone(created["latitude"])
        self.assertIsNone(created["longitude"])
        self.assertIsNone(created["coordinates"])
        self.assertIsNone(created["capacity"])
        self.assertIsNone(created["contact_phone"])
        self.assertEqual(created["verification_status"], "partially_verified")
        self.assertEqual(created["geocoding_confidence"], "unverified")

    def test_create_facility_coordinate_validation(self):
        """POST /api/v1/facilities rejects coordinates outside Indian territory."""
        invalid_geo_payload = {
            "name": "Invalid Coordinate Godown",
            "facility_type": "godown",
            "address": "Offshore location",
            "village_or_city": "Nowhere",
            "district": "Unknown",
            "state": "Punjab",
            "latitude": 10.0,
            "longitude": 10.0,
            "source_name": "Test Source",
            "source_url": "https://example.com/test",
            "verification_status": "unverified"
        }
        res_geo = self.client.post("/api/v1/facilities", json=invalid_geo_payload)
        self.assertEqual(res_geo.status_code, 422)

    def test_duplicate_prevention_on_repository_restart(self):
        """Repository initialization must be idempotent and prevent duplicate facilities."""
        initial_count = len(self.repo.list_facilities())
        self.assertGreaterEqual(initial_count, 12)

        # Re-initialize using the same storage file
        repo_restart = ShipmentRepository(storage_file=self.temp_file.name)
        new_count = len(repo_restart.list_facilities())

        self.assertEqual(initial_count, new_count, "Facility count must not change on restart")

        # Verify specific stable IDs are preserved
        self.assertIsNotNone(repo_restart.get_facility("FAC-PB-PAG-BARA"))
        self.assertIsNotNone(repo_restart.get_facility("FAC-PB-PAG-KANG"))
        self.assertIsNotNone(repo_restart.get_facility("FAC-PB-ABO-01"))

    def test_shipments_facility_enrichment_regression(self):
        """Existing shipments link to real sourced facilities without regressions."""
        res = self.client.get("/api/v1/shipments/SHP-2026-001")
        self.assertEqual(res.status_code, 200)
        shp = res.json()
        self.assertEqual(shp["id"], "SHP-2026-001")
        self.assertEqual(shp["origin_facility_id"], "FAC-PB-ABO-01")
        self.assertEqual(shp["destination_facility_id"], "FAC-DL-AZD-01")

        # Verify enriched facility summaries are present and reflect Phase 12 real data
        origin = shp.get("origin_facility")
        self.assertIsNotNone(origin)
        self.assertEqual(origin["id"], "FAC-PB-ABO-01")
        self.assertIn("PAGREXCO", origin["name"])

        destination = shp.get("destination_facility")
        self.assertIsNotNone(destination)
        self.assertEqual(destination["id"], "FAC-DL-AZD-01")
        self.assertIn("Azadpur", destination["name"])

    def test_guava_supply_chain_categories(self):
        """Phase 12.2: Verify facilities are categorized into distinct guava supply-chain tiers."""
        # 1. Guava Handling Confirmed (only terminal markets/packhouses with documented guava handling)
        res_gc = self.client.get("/api/v1/facilities?guava_suitability=guava_confirmed")
        self.assertEqual(res_gc.status_code, 200)
        data_gc = res_gc.json()
        self.assertEqual(len(data_gc), 1)
        self.assertEqual(data_gc[0]["id"], "FAC-DL-AZD-01")
        self.assertEqual(data_gc[0]["guava_suitability_category"], "guava_confirmed")

        # 2. General Horticultural (suitability unconfirmed)
        res_hu = self.client.get("/api/v1/facilities?guava_suitability=horticulture_unconfirmed")
        self.assertEqual(res_hu.status_code, 200)
        data_hu = res_hu.json()
        self.assertEqual(len(data_hu), 3)
        hu_ids = {f["id"] for f in data_hu}
        self.assertEqual(hu_ids, {"FAC-PB-PAG-BARA", "FAC-PB-PAG-KANG", "FAC-PB-ABO-01"})

        # 3. Ambient Grain Godowns (PSWC complexes - not suitable for guava)
        res_ag = self.client.get("/api/v1/facilities?guava_suitability=ambient_grain")
        self.assertEqual(res_ag.status_code, 200)
        data_ag = res_ag.json()
        self.assertEqual(len(data_ag), 4)
        ag_ids = {f["id"] for f in data_ag}
        self.assertEqual(ag_ids, {"FAC-PB-FAZ-01", "FAC-PB-BTI-01", "FAC-PB-LDH-01", "FAC-PB-PSW-MAL"})

        # 4. Commercial Cold Stores (unknown commodity compatibility)
        res_cs = self.client.get("/api/v1/facilities?guava_suitability=cold_store_unknown")
        self.assertEqual(res_cs.status_code, 200)
        data_cs = res_cs.json()
        self.assertEqual(len(data_cs), 3)
        cs_ids = {f["id"] for f in data_cs}
        self.assertEqual(cs_ids, {"FAC-PB-JAL-01", "FAC-PB-NHB-TALW", "FAC-PB-NHB-BURJ"})

        # 5. Wholesale Produce Markets
        res_wm = self.client.get("/api/v1/facilities?guava_suitability=wholesale_market")
        self.assertEqual(res_wm.status_code, 200)
        data_wm = res_wm.json()
        self.assertEqual(len(data_wm), 1)
        self.assertEqual(data_wm[0]["id"], "FAC-PB-ASR-01")

    def test_evidence_transparency_and_unknowns(self):
        """Phase 12.2: Evidence transparency, explicit unknowns, and separated verification."""
        res = self.client.get("/api/v1/facilities")
        self.assertEqual(res.status_code, 200)
        facilities = res.json()
        self.assertEqual(len(facilities), 12)

        valid_citation_tiers = {
            "direct_document",
            "facility_page",
            "official_portal",
            "committee_proceeding",
            "directory_level_reference",
        }

        for f in facilities:
            # Source citation tier must be classified
            self.assertIn(
                f.get("source_citation_type"),
                valid_citation_tiers,
                f"Facility {f['id']} missing valid source_citation_type",
            )
            # Source URL must be a non-empty string
            self.assertTrue(
                bool(f.get("source_url")),
                f"Facility {f['id']} missing source_url",
            )
            # Separate legal entity verification from physical site verification
            self.assertEqual(
                f.get("legal_entity_verification"),
                "verified",
                f"Facility {f['id']} must have legal entity verification",
            )
            self.assertIn(
                f.get("physical_facility_verification"),
                {"verified", "partially_verified"},
                f"Facility {f['id']} must have physical verification status",
            )

        # Check explicit unconfirmed operational status for commercial cold stores without on-site confirmation
        cold_stores = [f for f in facilities if f["guava_suitability_category"] == "cold_store_unknown"]
        for cs in cold_stores:
            self.assertIsNone(
                cs.get("operational_status"),
                f"Cold store {cs['id']} must not claim active status without on-site audit",
            )
            self.assertIsNone(
                cs.get("capacity"),
                f"Cold store {cs['id']} must have null capacity if unlisted",
            )

        # Check documented capacities are positive numbers, not zero or fabricated
        documented_cap = [f for f in facilities if f["capacity"] is not None]
        self.assertEqual(len(documented_cap), 2)  # Bara Farm (24 MT) and Kangmai (54 MT)
        for dc in documented_cap:
            self.assertGreater(dc["capacity"], 0)
            self.assertEqual(dc["capacity_unit"], "MT")

    def test_geospatial_accuracy_and_approximate_village_markers(self):
        """Phase 12.2: Village-level centroid markers are explicitly disclosed and geocoded."""
        res = self.client.get("/api/v1/facilities")
        self.assertEqual(res.status_code, 200)
        facilities = res.json()

        for f in facilities:
            lat = f.get("latitude")
            lon = f.get("longitude")
            self.assertIsNotNone(lat)
            self.assertIsNotNone(lon)
            self.assertTrue(is_within_india(lat, lon))
            self.assertIn(
                f.get("geocoding_confidence"),
                {"village_level", "facility_campus"},
            )
            # Coordinate source must be documented
            self.assertTrue(bool(f.get("coordinate_source")))

            # Only Azadpur APMC is a campus-level geocode; others are village/town centroid approximations
            if f["id"] == "FAC-DL-AZD-01":
                self.assertEqual(f["geocoding_confidence"], "facility_campus")
            else:
                self.assertEqual(f["geocoding_confidence"], "village_level")


if __name__ == "__main__":
    unittest.main()

