"""
AgriChain AI — Farmer Stock & Inventory Management Tests
========================================================
Comprehensive unit test suite verifying:
- Schema validation (positive integer crates, positive float price, valid crop)
- Server-authoritative total stock value calculation
- Ownership authorization & role isolation (Farmer vs Farmer B vs Admin)
- Repository CRUD operations
- Endpoint handlers & HTTP exception enforcement
- Persistence across ledger file reloads
"""

import asyncio
import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pydantic import ValidationError
from fastapi import HTTPException

from app.schemas.inventory import (
    SUPPORTED_MARKETPLACE_CROPS,
    CreateInventoryRequest,
    UpdateInventoryRequest,
    InventoryItemResponse,
)
from app.db.repository import ShipmentRepository
from app.api.v1.endpoints.inventory import (
    get_crop_catalogue,
    list_inventory,
    create_inventory_item,
    get_inventory_item,
    update_inventory_item,
    delete_inventory_item,
)


class TestInventoryManagement(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        self.temp_file.write("{}")
        self.temp_file.close()
        self.repo = ShipmentRepository(storage_file=self.temp_file.name, database_enabled=False)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            try:
                os.unlink(self.temp_file.name)
            except OSError:
                pass

    def test_01_crop_catalogue_metadata(self):
        """Verifies crop catalogue contains required crops with strict separation of AI availability."""
        crops = get_crop_catalogue()
        self.assertGreaterEqual(len(crops), 5)
        by_id = {c.crop_id: c for c in crops}

        self.assertIn("guava", by_id)
        self.assertIn("banana", by_id)
        self.assertIn("apple", by_id)
        self.assertIn("mango", by_id)
        self.assertIn("kinnow", by_id)

        # Separation of concerns
        self.assertTrue(by_id["guava"].ai_classification_available)
        self.assertIn("ResNet18", by_id["guava"].ai_model)

        self.assertTrue(by_id["banana"].ai_classification_available)
        self.assertIn("ResNet18", by_id["banana"].ai_model)

        self.assertFalse(by_id["apple"].ai_classification_available)
        self.assertEqual(by_id["apple"].ai_task, "detection_only")

        self.assertFalse(by_id["mango"].ai_classification_available)
        self.assertEqual(by_id["mango"].ai_task, "unavailable")

        self.assertFalse(by_id["kinnow"].ai_classification_available)
        self.assertEqual(by_id["kinnow"].ai_task, "unavailable")

    def test_02_schema_validation(self):
        """Verifies rejection of invalid crate quantities, prices, or unsupported crops."""
        # Valid schema
        req = CreateInventoryRequest(
            crop_type="guava",
            crate_quantity=100,
            price_per_crate=450.0,
        )
        self.assertEqual(req.crate_quantity, 100)
        self.assertEqual(req.price_per_crate, 450.0)

        # Zero or negative crate quantity rejected
        with self.assertRaises(ValidationError):
            CreateInventoryRequest(crop_type="guava", crate_quantity=0, price_per_crate=450.0)

        with self.assertRaises(ValidationError):
            CreateInventoryRequest(crop_type="guava", crate_quantity=-5, price_per_crate=450.0)

        # Zero or negative price rejected
        with self.assertRaises(ValidationError):
            CreateInventoryRequest(crop_type="guava", crate_quantity=50, price_per_crate=0.0)

        with self.assertRaises(ValidationError):
            CreateInventoryRequest(crop_type="guava", crate_quantity=50, price_per_crate=-120.0)

        # Unsupported crop rejected
        with self.assertRaises(ValidationError):
            CreateInventoryRequest(crop_type="unsupported_crop_123", crate_quantity=50, price_per_crate=100.0)

    def test_03_server_authoritative_total_value_calculation(self):
        """Verifies total_stock_value = round(crate_quantity * price_per_crate, 2)."""
        auth_farmer = {"role": "farmer", "farmer_id": "FARMER-PB-001", "user_id": "FARMER-PB-001"}
        req = CreateInventoryRequest(
            crop_type="guava",
            crate_quantity=85,
            price_per_crate=515.50,
            location="Abohar Orchard Gate, Punjab",
            harvest_date="2026-11-02",
            description="Grade A export harvest",
        )

        item = create_inventory_item(req, auth=auth_farmer, repo=self.repo)
        expected_total = round(85 * 515.50, 2)
        self.assertEqual(item.total_stock_value, expected_total)
        self.assertEqual(item.crate_quantity, 85)
        self.assertEqual(item.price_per_crate, 515.50)
        self.assertEqual(item.farmer_id, "FARMER-PB-001")
        self.assertEqual(item.crop_type, "guava")

    def test_04_ownership_authorization(self):
        """Verifies a farmer cannot modify or delete another farmer's stock records (HTTP 403)."""
        auth_farmer_a = {"role": "farmer", "farmer_id": "FARMER-PB-001", "user_id": "FARMER-PB-001"}
        auth_farmer_b = {"role": "farmer", "farmer_id": "FARMER-PB-999", "user_id": "FARMER-PB-999"}
        auth_admin = {"role": "admin", "farmer_id": "ADMIN-ROOT", "user_id": "ADMIN-ROOT"}

        # Farmer A creates stock item
        req_create = CreateInventoryRequest(
            crop_type="banana",
            crate_quantity=60,
            price_per_crate=380.0,
        )
        created = create_inventory_item(req_create, auth=auth_farmer_a, repo=self.repo)
        item_id = created.id

        # Farmer B tries to edit -> 403 Forbidden
        req_update = UpdateInventoryRequest(crate_quantity=999)
        with self.assertRaises(HTTPException) as ctx:
            update_inventory_item(item_id, req_update, auth=auth_farmer_b, repo=self.repo)
        self.assertEqual(ctx.exception.status_code, 403)

        # Farmer B tries to delete -> 403 Forbidden
        with self.assertRaises(HTTPException) as ctx:
            delete_inventory_item(item_id, auth=auth_farmer_b, repo=self.repo)
        self.assertEqual(ctx.exception.status_code, 403)

        # Farmer A updates own stock -> 200 OK
        req_update_valid = UpdateInventoryRequest(crate_quantity=75, price_per_crate=400.0)
        updated = update_inventory_item(item_id, req_update_valid, auth=auth_farmer_a, repo=self.repo)
        self.assertEqual(updated.crate_quantity, 75)
        self.assertEqual(updated.total_stock_value, round(75 * 400.0, 2))

        # Admin can delete -> 200 OK
        del_resp = delete_inventory_item(item_id, auth=auth_admin, repo=self.repo)
        self.assertEqual(del_resp["status"], "success")

    def test_05_persistence_and_reload(self):
        """Verifies inventory records persist to disk ledger and survive repository reload."""
        item_data = {
            "farmer_id": "FARMER-PB-001",
            "crop_type": "kinnow",
            "crate_quantity": 250,
            "price_per_crate": 530.0,
            "location": "Fazilka Processing Yard",
        }
        created = self.repo.create_inventory_item(item_data)
        item_id = created["id"]
        self.assertEqual(created["total_stock_value"], 132500.0)

        # Instantiate fresh repository from the same storage file to test restart persistence
        reloaded_repo = ShipmentRepository(storage_file=self.temp_file.name, database_enabled=False)
        found = reloaded_repo.get_inventory_item(item_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["crop_type"], "kinnow")
        self.assertEqual(found["crate_quantity"], 250)
        self.assertEqual(found["total_stock_value"], 132500.0)


if __name__ == "__main__":
    unittest.main()
