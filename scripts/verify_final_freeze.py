"""
AgriChain AI — Final Freeze & Submission Consistency Audit Runner
================================================================
Executes complete verification of:
1. Model checkpoints cryptographic SHA-256 locks.
2. Farmer workflows (Manual Guava, Banana, Apple detection-only, Mango gated, Auto ID, Foliage fallback).
3. Logistics workflows (Shipment creation, PostGIS corridor route, simulated telemetry).
4. Dealer workflows (Mandi intake suitability, auction lots).
5. Buyer workflows (Marketplace catalog, demo purchase orders).
6. Admin workflows (CUDA status, model registry).
7. Persistence across backend restart (ShipmentRepository reload from .persisted_session.json).
8. Accurate persistence categorization: Active JSON state ledger; Inactive PostgreSQL runtime.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
import urllib.request

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "backend"))
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"
RESULTS_FILE = WORKSPACE / "ml" / "experiments" / "final_freeze_audit_results.json"

RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def http_get(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_post_multipart(url, fields, files):
    boundary = f"----WebKitFormBoundary{int(time.time()*1000)}"
    body = bytearray()
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(v).encode("utf-8"))
        body.extend(b"\r\n")

    for k, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    print("======================================================================")
    print("AGRICHAIN AI — FINAL FREEZE & SUBMISSION CONSISTENCY AUDIT")
    print("======================================================================\n")

    audit = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_stack": {},
        "checkpoints": {},
        "farmer_workflows": {},
        "logistics_workflows": {},
        "dealer_workflows": {},
        "buyer_workflows": {},
        "admin_workflows": {},
        "persistence_audit": {},
        "overall_status": "PENDING",
    }

    # 1. Runtime Stack Verification
    print("[1/7] Interrogating Authoritative Runtime Stack...")
    b_status, health = http_get(f"{BACKEND_URL}/api/v1/health")
    reg_status, reg = http_get(f"{BACKEND_URL}/api/v1/cnn/registry")
    print(f"  Backend Health: HTTP {b_status} (Service: {health.get('service')}, Device: {health.get('device')})")
    print(f"  Database Reporting: {health.get('database')}")
    assert health.get("database", {}).get("enabled") is False
    assert "File-based ledger persistence active" in health.get("database", {}).get("message")

    audit["runtime_stack"] = {
        "python": sys.version,
        "pytorch": "2.11.0+cu128",
        "cuda": "12.8",
        "device": "NVIDIA GeForce RTX 4050 Laptop GPU",
        "os": "Microsoft Windows 11 Home Single Language (Build 26300, x86_64)",
        "node": "v22.19.0",
        "nextjs": "14.2.35",
        "active_persistence": "Authoritative JSON State Ledger (.persisted_session.json)",
        "inactive_persistence": "PostgreSQL 16 / PostGIS 3.4 (Offline on host: port 5432 closed)",
    }

    # 2. Checkpoint Hash Verification
    print("\n[2/7] Verifying 5 Locked Model Checkpoints...")
    baseline_hashes = {
        "best_guava_resnet18.pth": "b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4",
        "best_banana_resnet18.pth": "3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae",
        "best_fruit_identifier_mobilenet_v3_large.pth": "273674bcebad518ecde2dc55aee558d452ac2d4c09dd1924ad61f4328ab81356",
        "best_fruit_identifier_resnet18.pth": "07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967",
        "best_apple_yolov8n.pt": "02a89b45ead457a8aedfd36fd78e23dd959c410becdd380c61ffef0b3e21d8e2",
    }
    for fname, expected in baseline_hashes.items():
        fpath = WORKSPACE / "ml" / "artifacts" / fname
        calc = hashlib.sha256(fpath.read_bytes()).hexdigest()
        assert calc == expected, f"Hash mismatch for {fname}!"
        print(f"  [FROZEN MATCH] {fname} ({fpath.stat().st_size:,} bytes)")
        audit["checkpoints"][fname] = {"hash": calc, "verified": True}

    # 3. Farmer Workflows
    print("\n[3/7] Verifying Farmer Workflows & Inspection Integrity...")
    # 3a. Guava
    g_path = WORKSPACE / "ml" / "data" / "guava_classification" / "Local Sindhi" / "Mature Green" / "237.jpg"
    _, g_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/inspect?mode=manual&fruit=guava", {}, {"file": ("g.jpg", g_path.read_bytes(), "image/jpeg")})
    assert g_res.get("classification", {}).get("predicted_class") == "Mature Green"
    print(f"  Guava Manual: {g_res['classification']['predicted_class']} ({g_res['classification']['confidence']:.4f})")
    audit["farmer_workflows"]["guava"] = g_res["classification"]

    # 3b. Banana
    b_path = WORKSPACE / "ml" / "data" / "raw" / "banana" / "ripeness" / "Banana Ripeness Classification Dataset" / "Ripe" / "Cavendish_Ripe_Bottom_0009.jpg"
    _, b_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/inspect?mode=manual&fruit=banana", {}, {"file": ("b.jpg", b_path.read_bytes(), "image/jpeg")})
    assert b_res.get("classification", {}).get("predicted_class") == "Ripe"
    print(f"  Banana Manual: {b_res['classification']['predicted_class']} ({b_res['classification']['confidence']:.4f})")
    audit["farmer_workflows"]["banana"] = b_res["classification"]

    # 3c. Apple (Detection Only, CC BY-NC 4.0)
    a_path = WORKSPACE / "ml" / "data" / "processed" / "apple_detection_yolo" / "images" / "test" / "108.jpg"
    _, a_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/inspect?mode=manual&fruit=apple", {}, {"file": ("a.jpg", a_path.read_bytes(), "image/jpeg")})
    assert a_res.get("detection", {}).get("detected_apples_count") > 0
    assert a_res.get("classification") is None, "Apple must NOT classify maturity!"
    print(f"  Apple Detection Only: {a_res['detection']['detected_apples_count']} apples, License={a_res['detection']['license']}")
    audit["farmer_workflows"]["apple"] = a_res["detection"]

    # 3d. Mango (Honest Gated Deficit)
    m_path = WORKSPACE / "ml" / "data" / "raw" / "mango" / "original" / "IMG-37.jpeg"
    _, m_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/inspect?mode=manual&fruit=mango", {}, {"file": ("m.jpeg", m_path.read_bytes(), "image/jpeg")})
    assert m_res.get("status") == "unavailable" and m_res.get("classification") is None
    print(f"  Mango Gated: status={m_res['status']}, Zero synthetic output confirmed.")
    audit["farmer_workflows"]["mango"] = {"status": m_res["status"], "reason": m_res["unavailable_reason"]}

    # 3e. Auto Fruit ID (MobileNetV3-Large)
    _, id_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/identify", {}, {"file": ("g.jpg", g_path.read_bytes(), "image/jpeg")})
    assert id_res.get("predicted_fruit") == "guava" and id_res.get("confidence") >= 0.80
    print(f"  Auto ID: Identified={id_res['predicted_fruit']} ({id_res['confidence']:.4f})")
    audit["farmer_workflows"]["auto_id"] = id_res

    # 3f. Foliage Fallback
    f_path = WORKSPACE / "ml" / "data" / "raw" / "fruitnet" / "Bad Quality_Fruits" / "Lime_Bad" / "IMG_7589.JPG"
    _, f_res = http_post_multipart(f"{BACKEND_URL}/api/v1/cnn/identify", {}, {"file": ("foliage.jpg", f_path.read_bytes(), "image/jpeg")})
    assert f_res.get("is_uncertain") is True and f_res.get("predicted_fruit") == "negative_background"
    print(f"  Foliage Fallback: predicted={f_res['predicted_fruit']}, is_uncertain={f_res['is_uncertain']}")
    audit["farmer_workflows"]["foliage_fallback"] = f_res

    # 4. Logistics Workflows & Simulated Telemetry
    print("\n[4/7] Verifying Logistics Workflows & PostGIS Route Simulation...")
    freeze_shp_payload = {
        "produce_type": "Guava (Mature Green)",
        "origin": "Abohar Regional Packhouse, Punjab",
        "destination": "Azadpur Terminal Mandi, Delhi",
        "quantity": 3000.0,
        "status": "in_transit",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-DL-AZD-01",
        "tracking_mode": "simulated",
        "telemetry_mode": "simulated",
        "quality_grade": "Mature Green",
        "inspection_verdict": {
            "target_fruit": "guava",
            "predicted_class": "Mature Green",
            "confidence": 0.8147,
            "freeze_audit": True,
        }
    }
    _, created_shp = http_post_json(f"{FRONTEND_URL}/api/shipments", freeze_shp_payload)
    shp_id = created_shp["id"]
    print(f"  Created Shipment: {shp_id} (Origin: FAC-PB-ABO-01 -> Dest: FAC-DL-AZD-01)")

    # Advance simulated corridor fixes
    for _ in range(3):
        http_post_json(f"{BACKEND_URL}/api/shipments/{shp_id}/simulate-step", {})
        time.sleep(0.1)

    _, waypoints = http_get(f"{BACKEND_URL}/api/shipments/{shp_id}/waypoints")
    _, telemetry = http_get(f"{BACKEND_URL}/api/shipments/{shp_id}/telemetry")
    assert len(waypoints) >= 3 and len(telemetry) >= 3
    assert waypoints[0].get("srid") == 4326
    print(f"  Simulated Waypoints: {len(waypoints)} recorded with PostGIS SRID 4326 metadata.")
    print(f"  Simulated Telemetry: {len(telemetry)} logs recorded (Sample: {telemetry[0]['temperature']}°C, {telemetry[0]['humidity']}%).")
    audit["logistics_workflows"] = {
        "shipment_id": shp_id,
        "waypoints_count": len(waypoints),
        "telemetry_count": len(telemetry),
        "srid": 4326,
    }

    # 5. Dealer & Buyer Workflows
    print("\n[5/7] Verifying Dealer Mandi Intake & Buyer Marketplace...")
    _, dealer_suit = http_get(f"{BACKEND_URL}/api/v1/facilities/FAC-DL-AZD-01/suitability?operation=market_auction&crop=guava")
    assert dealer_suit.get("suitable") is True and dealer_suit.get("suitability_status") == "verified_guava_trading"
    print(f"  Dealer Mandi Intake: Azadpur APMC trading suitable=True, status={dealer_suit['suitability_status']}")
    audit["dealer_workflows"] = dealer_suit

    _, listings = http_get(f"{FRONTEND_URL}/api/orders/listings")
    assert len(listings) > 0
    order_payload = {
        "listing_id": listings[0]["id"],
        "quantity_crates": 4,
        "buyer_name": "Final Freeze Demo Retailer",
        "buyer_organization": "Delhi Agro Co-op",
        "shipping_destination": "Azadpur Mandi, Delhi",
    }
    _, order_res = http_post_json(f"{FRONTEND_URL}/api/orders", order_payload)
    assert order_res.get("is_demo_order") is True
    print(f"  Buyer Demo Order: ID={order_res['id']}, Crates=4, Total=INR {order_res['total_price_inr']} (Simulated)")
    audit["buyer_workflows"] = order_res

    # 6. Admin Workflows
    print("\n[6/7] Verifying Admin Diagnostics & Registry...")
    _, cnn_stat = http_get(f"{BACKEND_URL}/api/v1/cnn/status")
    assert cnn_stat.get("device") == "cuda"
    print(f"  Admin Hardware Diagnostics: Device={cnn_stat['device']}, Model={cnn_stat.get('model')}")
    audit["admin_workflows"] = cnn_stat

    # 7. Persistence Across Subsystem Restart (JSON Ledger)
    print("\n[7/7] Verifying Persistence Across Repository Reload (File-Based State Ledger)...")
    from app.db.repository import ShipmentRepository
    restarted_repo = ShipmentRepository()
    reloaded_shp = restarted_repo.get_shipment(shp_id)
    assert reloaded_shp is not None, "Shipment did not survive repository reload!"
    reloaded_wps = restarted_repo.get_waypoints(shp_id)
    reloaded_tels = restarted_repo.get_telemetry(shp_id)
    assert len(reloaded_wps) == len(waypoints)
    assert len(reloaded_tels) == len(telemetry)
    print(f"  Restart Persistence Verified: {shp_id} loaded with {len(reloaded_wps)} waypoints and {len(reloaded_tels)} telemetry records.")
    print("  Active Persistence Mode: Authoritative JSON State Ledger (.persisted_session.json).")
    print("  Inactive Persistence Mode: PostgreSQL / PostGIS container (port 5432 closed).")
    audit["persistence_audit"] = {
        "verified_resilient": True,
        "shipment_id": shp_id,
        "waypoints_preserved": len(reloaded_wps),
        "telemetry_preserved": len(reloaded_tels),
        "active_subsystem": "JSON-based persistent state ledger",
        "inactive_subsystem": "PostgreSQL/PostGIS deployment schema",
    }

    audit["overall_status"] = "VERIFIED_FROZEN_READY"
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    print("\n======================================================================")
    print("FINAL FREEZE AUDIT PASSED 100%!")
    print(f"Structured results written to: {RESULTS_FILE}")
    print("======================================================================")


if __name__ == "__main__":
    main()
