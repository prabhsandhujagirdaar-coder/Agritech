"""
AgriChain AI — Verification Script for Phase Enhancements
=========================================================
Verifies:
1. Feature 1: Dynamic Map Marker Visibility During Simulation
2. Feature 2: Farmer Stock & Inventory Management (Validation, Valuation, Ownership, CRUD, Persistence)
3. Feature 3: Increased Map Height & Layout Responsiveness
"""

import sys
import os
import json
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
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
)
from app.db.repository import ShipmentRepository
from app.api.v1.endpoints.inventory import (
    get_crop_catalogue,
    list_inventory,
    create_inventory_item,
    update_inventory_item,
    delete_inventory_item,
)


def run_verification():
    passed = 0
    total = 0

    def check(name, condition, detail=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name} {detail}")
        else:
            print(f"  [FAIL] {name} {detail}")
            sys.exit(1)

    print("\n" + "=" * 70)
    print("AGRICHAIN AI — VERIFYING ENHANCEMENTS")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST SUITE 1: Crop Catalogue & AI Separation of Concerns
    # -------------------------------------------------------------------------
    print("\n[1] Testing Crop Catalogue & AI Model Separation of Concerns...")
    crops = get_crop_catalogue()
    check("Catalogue returns supported crops", len(crops) >= 5, f"(Found {len(crops)} crops)")

    crop_map = {c.crop_id: c for c in crops}
    check("Guava has active ResNet18 v2 model", crop_map["guava"].ai_classification_available is True and "ResNet18" in crop_map["guava"].ai_model)
    check("Banana has active ResNet18 v1 model", crop_map["banana"].ai_classification_available is True and "ResNet18" in crop_map["banana"].ai_model)
    check("Apple is explicitly detection only (CC BY-NC 4.0)", crop_map["apple"].ai_classification_available is False and crop_map["apple"].ai_task == "detection_only")
    check("Mango is commercial trade with NO active model", crop_map["mango"].ai_classification_available is False and crop_map["mango"].ai_task == "unavailable")
    check("Kinnow is commercial trade with NO active model", crop_map["kinnow"].ai_classification_available is False and crop_map["kinnow"].ai_task == "unavailable")

    # -------------------------------------------------------------------------
    # TEST SUITE 2: Input Validation (Zero/Negative crates & prices, Bad crops)
    # -------------------------------------------------------------------------
    print("\n[2] Testing Inventory Input Validation & Pydantic Constraints...")
    # Zero crate quantity
    try:
        CreateInventoryRequest(crop_type="guava", crate_quantity=0, price_per_crate=450.0)
        check("Rejection of zero crates", False)
    except ValidationError:
        check("Rejection of zero crates", True, "(ValidationError raised as expected)")

    # Negative crate quantity
    try:
        CreateInventoryRequest(crop_type="guava", crate_quantity=-10, price_per_crate=450.0)
        check("Rejection of negative crates", False)
    except ValidationError:
        check("Rejection of negative crates", True, "(ValidationError raised as expected)")

    # Zero price per crate
    try:
        CreateInventoryRequest(crop_type="guava", crate_quantity=50, price_per_crate=0.0)
        check("Rejection of zero price per crate", False)
    except ValidationError:
        check("Rejection of zero price per crate", True, "(ValidationError raised as expected)")

    # Negative price per crate
    try:
        CreateInventoryRequest(crop_type="guava", crate_quantity=50, price_per_crate=-150.0)
        check("Rejection of negative price per crate", False)
    except ValidationError:
        check("Rejection of negative price per crate", True, "(ValidationError raised as expected)")

    # Unsupported crop
    try:
        CreateInventoryRequest(crop_type="pineapple_unsupported", crate_quantity=50, price_per_crate=100.0)
        check("Rejection of unsupported crop", False)
    except ValidationError:
        check("Rejection of unsupported crop", True, "(ValidationError raised as expected)")

    # Valid schema passes
    valid_req = CreateInventoryRequest(
        crop_type="guava",
        crate_quantity=100,
        price_per_crate=450.0,
        location="Abohar Orchard Gate, Punjab",
    )
    check("Valid schema instantiation", valid_req.crate_quantity == 100 and valid_req.price_per_crate == 450.0)

    # -------------------------------------------------------------------------
    # TEST SUITE 3: Server-Authoritative Stock Value Calculation
    # -------------------------------------------------------------------------
    print("\n[3] Testing Server-Authoritative Stock Valuation Calculation...")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
    temp_file.write(json.dumps({"inventory": []}))
    temp_file.close()

    repo = ShipmentRepository(storage_file=temp_file.name, database_enabled=False)

    auth_farmer_a = {"role": "farmer", "farmer_id": "FARMER-PB-001", "user_id": "FARMER-PB-001"}
    auth_farmer_b = {"role": "farmer", "farmer_id": "FARMER-PB-999", "user_id": "FARMER-PB-999"}
    auth_admin = {"role": "admin", "farmer_id": "ADMIN-ROOT", "user_id": "ADMIN-ROOT"}

    req_create = CreateInventoryRequest(
        crop_type="guava",
        crate_quantity=125,
        price_per_crate=485.50,
        location="Abohar Regional Mandi",
        harvest_date="2026-11-02",
        description="Allahabad Safeda Grade A stock",
    )
    created = create_inventory_item(req_create, auth=auth_farmer_a, repo=repo)
    expected_value = round(125 * 485.50, 2)
    check(
        "Total stock value accurately calculated server-side",
        created.total_stock_value == expected_value,
        f"(125 * 485.50 = INR {created.total_stock_value})",
    )
    check("Farmer tenant ID correctly bound", created.farmer_id == "FARMER-PB-001")

    # -------------------------------------------------------------------------
    # TEST SUITE 4: Role-Based Ownership & Access Control
    # -------------------------------------------------------------------------
    print("\n[4] Testing Role-Based Ownership & Isolation...")
    item_id = created.id

    # Farmer B attempts to update Farmer A's stock -> 403 Forbidden
    try:
        update_inventory_item(item_id, UpdateInventoryRequest(crate_quantity=999), auth=auth_farmer_b, repo=repo)
        check("Farmer B cannot edit Farmer A's stock", False)
    except HTTPException as e:
        check("Farmer B cannot edit Farmer A's stock", e.status_code == 403, f"(HTTP {e.status_code} Forbidden)")

    # Farmer B attempts to delete Farmer A's stock -> 403 Forbidden
    try:
        delete_inventory_item(item_id, auth=auth_farmer_b, repo=repo)
        check("Farmer B cannot delete Farmer A's stock", False)
    except HTTPException as e:
        check("Farmer B cannot delete Farmer A's stock", e.status_code == 403, f"(HTTP {e.status_code} Forbidden)")

    # Farmer A updates own stock -> 200 OK with value recomputation
    updated = update_inventory_item(
        item_id,
        UpdateInventoryRequest(crate_quantity=150, price_per_crate=500.0),
        auth=auth_farmer_a,
        repo=repo,
    )
    check("Farmer A can update own stock", updated.crate_quantity == 150)
    check(
        "Server recalculates valuation upon update",
        updated.total_stock_value == round(150 * 500.0, 2),
        f"(150 * 500.0 = INR {updated.total_stock_value})",
    )

    # Admin oversight: Admin can delete item
    del_res = delete_inventory_item(item_id, auth=auth_admin, repo=repo)
    check("Admin has platform oversight to delete listing", del_res["status"] == "success")

    # -------------------------------------------------------------------------
    # TEST SUITE 5: Persistence Across Backend Reload
    # -------------------------------------------------------------------------
    print("\n[5] Testing Persistence Across Repository Reload...")
    new_item = repo.create_inventory_item({
        "farmer_id": "FARMER-PB-001",
        "crop_type": "kinnow",
        "crate_quantity": 300,
        "price_per_crate": 520.0,
        "location": "Fazilka Processing Yard",
    })
    new_id = new_item["id"]

    # Reload repo from same file
    reloaded_repo = ShipmentRepository(storage_file=temp_file.name, database_enabled=False)
    retrieved = reloaded_repo.get_inventory_item(new_id)
    check("Item retrieved after storage reload", retrieved is not None and retrieved["id"] == new_id)
    check("Persisted stock valuation matches", retrieved["total_stock_value"] == 156000.0)

    # Clean up temp file
    try:
        os.unlink(temp_file.name)
    except OSError:
        pass

    # -------------------------------------------------------------------------
    # TEST SUITE 6: Frontend Feature Verification (Static Code Audits)
    # -------------------------------------------------------------------------
    print("\n[6] Verifying Frontend Enhancements & Map Layout...")
    tracking_map_path = os.path.join(ROOT_DIR, "apps", "web", "components", "TrackingMap.js")
    with open(tracking_map_path, "r", encoding="utf-8") as f:
        tm_src = f.read()

    check("Feature 1: TrackingMap detects active simulation mode", "isSimActive" in tm_src and 'simulationSession.status === "RUNNING"' in tm_src)
    check("Feature 1: Facilities layer hidden during active simulation", "facilitiesLayer.clearLayers()" in tm_src and "if (isSimActive) {" in tm_src)
    check("Feature 1: Shipment markers hidden during active simulation", "markersLayer.clearLayers()" in tm_src)
    check("Feature 1: Starting point (Point A) marker rendered", 'Point A: Starting Point' in tm_src or 'Point A' in tm_src)
    check("Feature 1: Destination point (Point B) marker rendered", 'Point B: Destination' in tm_src or 'Point B' in tm_src)

    shipment_tracking_path = os.path.join(ROOT_DIR, "apps", "web", "components", "ShipmentsTracking.js")
    with open(shipment_tracking_path, "r", encoding="utf-8") as f:
        st_src = f.read()

    check("Feature 3: Map height updated noticeably in ShipmentsTracking.js", "h-[580px]" in st_src and "lg:h-[720px]" in st_src)

    dashboard_path = os.path.join(ROOT_DIR, "apps", "web", "app", "dashboard", "page.js")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        dash_src = f.read()

    check("Feature 2: FarmerInventoryManager imported in dashboard/page.js", "import FarmerInventoryManager" in dash_src)
    check("Feature 2: FarmerInventoryManager mounted in Farmer tab", "<FarmerInventoryManager" in dash_src)

    inv_comp_path = os.path.join(ROOT_DIR, "apps", "web", "components", "FarmerInventoryManager.js")
    check("Feature 2: FarmerInventoryManager component exists", os.path.exists(inv_comp_path))

    print("\n" + "=" * 70)
    print(f"ALL ENHANCEMENT TESTS PASSED: {passed}/{total}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_verification()
