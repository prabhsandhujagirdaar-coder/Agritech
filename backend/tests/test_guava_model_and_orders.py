"""
Phase 13.5 Test Suite: Guava Model, Health Probes, and Demo Orders
==================================================================
Tests for:
1. Health endpoint reporting distinct API online, model status, and database status.
2. Real Guava ResNet18 checkpoint loading, inference, and unavailable model fallback.
3. Invalid image upload rejection (corrupted, empty, unsupported type).
4. Marketplace produce listings retrieval.
5. Demo order creation with server-side price computation and stock deduction.
6. Order rejection on quantity exceeding available stock.
7. Order rejection on nonexistent listing ID.
8. Order duplicate submission idempotency within 60-second window.
9. File-based persistence verification when DATABASE_ENABLED=false.
"""

import io
import time
import unittest
from pathlib import Path
from PIL import Image

try:
    from fastapi.testclient import TestClient
except Exception:
    from tests.test_client_compat import TestClient

from app.core.config import settings
from app.db.repository import get_shipment_repository
from app.main import app
from app.services.cnn_service import CNNService


def _create_synthetic_guava_image(format: str = "JPEG", size: tuple = (128, 128), color: tuple = (34, 139, 34)) -> bytes:
    """Generate in-memory RGB image simulating guava produce specimen."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


class TestGuavaModelAndOrders(unittest.TestCase):
    """Integration tests for Phase 13.5 backend requirements."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    # -------------------------------------------------------------------------
    # 1. Health Endpoint Behavior & Distinct Component Status
    # -------------------------------------------------------------------------
    def test_01_health_endpoint_reports_distinct_states(self):
        """Verify /health returns api_status, model_available, and database status."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["api_status"], "online")
        self.assertIn("model_available", body)
        self.assertIn("database", body)
        self.assertEqual(body["target_crop"], "guava")
        # Ensure database reports file-based ledger since PostgreSQL is offline
        self.assertFalse(body["database"]["enabled"])
        self.assertIn("File-based ledger", body["database"]["message"])

    # -------------------------------------------------------------------------
    # 2. Guava ResNet18 Model Checkpoint Loading & Inference
    # -------------------------------------------------------------------------
    def test_02_guava_checkpoint_loading_and_inference(self):
        """Verify real Guava ResNet18 checkpoint performs valid inference on test image."""
        jpeg_bytes = _create_synthetic_guava_image()
        resp = self.client.post(
            "/api/v1/cnn/predict",
            files={"file": ("guava_sample.jpg", jpeg_bytes, "image/jpeg")},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()

        self.assertEqual(body["target_crop"], "guava")
        self.assertIn(body["predicted_class"], ["Green", "Mature Green", "Ripe"])
        self.assertIn(body["label"], ["Green", "Mature Green", "Ripe"])
        self.assertGreaterEqual(body["confidence"], 0.0)
        self.assertLessEqual(body["confidence"], 1.0)
        self.assertEqual(set(body["probabilities"].keys()), {"Green", "Mature Green", "Ripe"})

    def test_03_missing_model_returns_503(self):
        """Verify that when a model checkpoint is missing, HTTP 503 is returned."""
        original_service = app.state.cnn_service
        try:
            missing_service = CNNService(weights_path=Path("non_existent_guava_model.pth"))
            app.state.cnn_service = missing_service
            self.assertFalse(missing_service.is_available)

            jpeg_bytes = _create_synthetic_guava_image()
            resp = self.client.post(
                "/api/v1/cnn/predict",
                files={"file": ("guava_sample.jpg", jpeg_bytes, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 503)
            body = resp.json()
            self.assertIn("unavailable", body["detail"].lower())
        finally:
            app.state.cnn_service = original_service

    def test_04_invalid_image_payloads_rejected(self):
        """Verify empty, corrupted, and unsupported payloads return appropriate 4xx codes."""
        # Missing file
        resp = self.client.post("/api/v1/cnn/predict")
        self.assertEqual(resp.status_code, 422)

        # Unsupported file type (PDF)
        resp = self.client.post(
            "/api/v1/cnn/predict",
            files={"file": ("sample.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        self.assertEqual(resp.status_code, 415)

        # Empty image file
        resp = self.client.post(
            "/api/v1/cnn/predict",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        self.assertEqual(resp.status_code, 400)

        # Corrupted image file
        resp = self.client.post(
            "/api/v1/cnn/predict",
            files={"file": ("corrupt.jpg", b"NOT_AN_IMAGE_PAYLOAD", "image/jpeg")},
        )
        self.assertEqual(resp.status_code, 400)

    # -------------------------------------------------------------------------
    # 3. Marketplace Listings & Order Lifecycle
    # -------------------------------------------------------------------------
    def test_05_marketplace_listings_returns_guava_catalog(self):
        """Verify /api/v1/orders/listings returns active guava listings with required fields."""
        resp = self.client.get("/api/v1/orders/listings")
        self.assertEqual(resp.status_code, 200)
        listings = resp.json()
        self.assertIsInstance(listings, list)
        self.assertGreaterEqual(len(listings), 1)

        first = listings[0]
        self.assertIn("id", first)
        self.assertEqual(first["crop"], "guava")
        self.assertIn("variety", first)
        self.assertIn("price_per_crate_inr", first)
        self.assertIn("available_crates", first)
        self.assertGreaterEqual(first["available_crates"], 0)

    def test_06_order_creation_server_side_pricing_and_stock_deduction(self):
        """Verify buyer demo order calculates total price on backend and updates stock."""
        # Fetch current listings
        resp = self.client.get("/api/v1/orders/listings")
        listings = resp.json()
        target_listing = next(item for item in listings if item["available_crates"] >= 5)
        lid = target_listing["id"]
        initial_stock = target_listing["available_crates"]
        price_per_crate = target_listing["price_per_crate_inr"]

        order_payload = {
            "listing_id": lid,
            "quantity_crates": 3,
            "buyer_name": "Test Wholesale Buyer",
            "buyer_organization": "Fresh Retailers Punjab",
            "delivery_address": "Sector 26 Grain Market, Chandigarh",
            "payment_method": "DEMO_INVOICE",
            "notes": "Urgent morning delivery requested",
        }

        resp = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(resp.status_code, 201)
        order = resp.json()

        self.assertIn("id", order)
        self.assertEqual(order["listing_id"], lid)
        self.assertEqual(order["quantity_crates"], 3)
        # Server-side pricing check: 3 * price_per_crate
        expected_total = 3 * price_per_crate
        self.assertEqual(order["total_price_inr"], expected_total)
        self.assertEqual(order["currency"], "INR")
        self.assertEqual(order["status"].lower(), "confirmed")
        self.assertTrue(order["is_demo_order"])

        # Check stock deduction
        resp_after = self.client.get("/api/v1/orders/listings")
        after_listings = resp_after.json()
        updated_listing = next(item for item in after_listings if item["id"] == lid)
        self.assertEqual(updated_listing["available_crates"], initial_stock - 3)

    def test_07_order_rejection_on_insufficient_stock(self):
        """Verify requesting more crates than available returns HTTP 400."""
        resp = self.client.get("/api/v1/orders/listings")
        listings = resp.json()
        target = listings[0]
        lid = target["id"]
        excessive_qty = target["available_crates"] + 9999

        order_payload = {
            "listing_id": lid,
            "quantity_crates": excessive_qty,
            "buyer_name": "Greedy Buyer",
            "buyer_organization": "Overstock Corp",
            "delivery_address": "Ludhiana Mandi",
        }
        resp = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("exceeds available stock", resp.json()["detail"].lower())

    def test_08_order_rejection_on_invalid_listing_id(self):
        """Verify ordering with unknown listing ID returns HTTP 404."""
        order_payload = {
            "listing_id": "NON_EXISTENT_LISTING_9999",
            "quantity_crates": 2,
            "buyer_name": "Buyer Unknown",
            "buyer_organization": "Unknown Co",
            "delivery_address": "Amritsar",
        }
        resp = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("does not exist", resp.json()["detail"].lower())

    def test_09_order_duplicate_submission_idempotency(self):
        """Verify identical submission within 60s returns existing order without duplicate charging."""
        resp = self.client.get("/api/v1/orders/listings")
        target = next(item for item in resp.json() if item["available_crates"] >= 2)
        lid = target["id"]
        initial_stock = target["available_crates"]

        unique_buyer = f"Idempotent Buyer {time.time()}"
        order_payload = {
            "listing_id": lid,
            "quantity_crates": 2,
            "buyer_name": unique_buyer,
            "buyer_organization": "Twin Orders Ltd",
            "delivery_address": "Jalandhar Mandi Gate 2",
        }

        # Submission 1
        resp1 = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(resp1.status_code, 201)
        order1 = resp1.json()

        # Immediate Duplicate Submission 2
        resp2 = self.client.post("/api/v1/orders", json=order_payload)
        self.assertEqual(resp2.status_code, 201)
        order2 = resp2.json()

        # Should be identical order ID
        self.assertEqual(order1["id"], order2["id"])

        # Available crates should only have decreased by 2, not 4
        resp_after = self.client.get("/api/v1/orders/listings")
        updated = next(item for item in resp_after.json() if item["id"] == lid)
        self.assertEqual(updated["available_crates"], initial_stock - 2)

    def test_10_file_persistence_ledger_intact(self):
        """Verify repo data persists safely in json storage when DATABASE_ENABLED=false."""
        repo = get_shipment_repository()
        listings = repo.get_marketplace_listings()
        orders = repo.get_orders()
        self.assertIsInstance(listings, list)
        self.assertIsInstance(orders, list)
        # Check that persistence file exists or in-memory backup holds orders
        persisted_file = Path("app/db/.persisted_session.json")
        if persisted_file.exists():
            self.assertGreater(persisted_file.stat().st_size, 0)
