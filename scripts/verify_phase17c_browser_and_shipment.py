"""
AgriChain AI — Phase 17C Live End-to-End Acceptance: Shipment Integration & UI Verification
========================================================================================
Validates Tasks 4, 5, and 6 of Phase 17C:
- End-to-end multi-fruit inspection via Next.js proxy (/api/inspect) & FastAPI backend (/api/v1/cnn/inspect).
- Full Produce Shipment association with AI inspection verdict & quality grade.
- File-based / PostGIS ledger persistence, event logging (shipment_created, quality_inspection_recorded).
- Transit simulation step progression, GPS waypoint updates, cold-chain telemetry and risk index.
- Dealer and Farmer view queries.
- Automated headless browser UI captures for all tabs under docs/screenshots/phase17c/.
"""

import json
import os
import subprocess
import time
from pathlib import Path
import urllib.request
import urllib.parse

WORKSPACE = Path(__file__).resolve().parent.parent
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"
SCREENSHOT_DIR = WORKSPACE / "docs" / "screenshots" / "phase17c"
RESULTS_FILE = WORKSPACE / "ml" / "experiments" / "phase17c_full_e2e_results.json"

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def post_multipart(url, fields, files):
    """Simple multipart/form-data POST using standard urllib."""
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
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


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


def capture_screenshot(url, output_path, width=1280, height=900):
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--window-size={width},{height}",
        f"--screenshot={str(output_path)}",
        url,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
    exists = output_path.exists() and output_path.stat().st_size > 0
    size = output_path.stat().st_size if exists else 0
    return exists, size


def main():
    print("======================================================================")
    print("PHASE 17C — LIVE END-TO-END ACCEPTANCE TESTING")
    print("Shipment Association, PostGIS Telemetry & Browser Verification")
    print("======================================================================\n")

    test_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "health_checks": {},
        "inspection_tests": {},
        "shipment_lifecycle": {},
        "browser_screenshots": {},
    }

    # 1. System Health Verification
    print("[1/5] Verifying System Services...")
    try:
        status, be_health = http_get(f"{BACKEND_URL}/health")
        print(f"  Backend (/health): HTTP {status} — status={be_health.get('status')}, device={be_health.get('device')}")
        test_results["health_checks"]["backend"] = be_health
    except Exception as e:
        print(f"  Backend health check failed: {e}")
        return

    try:
        status, fe_health = http_get(f"{FRONTEND_URL}/api/health")
        print(f"  Next.js Bridge (/api/health): HTTP {status} — status={fe_health.get('status')}")
        test_results["health_checks"]["frontend"] = fe_health
    except Exception as e:
        print(f"  Frontend health check failed: {e}")
        return

    # 2. Live Multi-Fruit Inspection via Next.js Proxy
    print("\n[2/5] Running Multi-Fruit Inspections via Next.js Proxy (/api/inspect)...")
    
    # 2.1 Guava Specimen
    guava_img_path = WORKSPACE / "ml/data/guava_classification/Local Sindhi/Green/40.jpg"
    with open(guava_img_path, "rb") as f:
        img_bytes = f.read()
    status, guava_res = post_multipart(
        f"{FRONTEND_URL}/api/inspect?mode=manual&fruit=guava",
        {"fruit": "guava", "mode": "manual"},
        {"file": ("guava_sample.jpg", img_bytes, "image/jpeg")}
    )
    guava_cls = guava_res.get("classification", {})
    print(f"  Guava Manual: HTTP {status} — Class={guava_cls.get('predicted_class')}, Conf={guava_cls.get('confidence', 0):.4f}, Latency={guava_res.get('inference_ms')}ms")
    test_results["inspection_tests"]["guava"] = guava_res

    # 2.2 Banana Specimen
    banana_img_path = WORKSPACE / "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Unripe/Ambon_Unripe_Bottom_0009.jpg"
    with open(banana_img_path, "rb") as f:
        img_bytes = f.read()
    status, banana_res = post_multipart(
        f"{FRONTEND_URL}/api/inspect?mode=manual&fruit=banana",
        {"fruit": "banana", "mode": "manual"},
        {"file": ("banana_sample.jpg", img_bytes, "image/jpeg")}
    )
    banana_cls = banana_res.get("classification", {})
    print(f"  Banana Manual: HTTP {status} — Class={banana_cls.get('predicted_class')}, Conf={banana_cls.get('confidence', 0):.4f}")
    test_results["inspection_tests"]["banana"] = banana_res

    # 2.3 Apple Specimen (Detection)
    apple_img_path = WORKSPACE / "ml/data/processed/apple_detection_yolo/images/test/108.jpg"
    with open(apple_img_path, "rb") as f:
        img_bytes = f.read()
    status, apple_res = post_multipart(
        f"{FRONTEND_URL}/api/inspect?mode=manual&fruit=apple",
        {"fruit": "apple", "mode": "manual"},
        {"file": ("apple_sample.jpg", img_bytes, "image/jpeg")}
    )
    apple_det = apple_res.get("detection", {})
    print(f"  Apple Manual: HTTP {status} — Detected={apple_det.get('detected_apples_count')} apples, License={apple_det.get('license')}")
    test_results["inspection_tests"]["apple"] = apple_res

    # 2.4 Mango Specimen (Unavailable / Gated)
    mango_img_path = WORKSPACE / "ml/data/raw/mango/original/IMG-37.jpeg"
    with open(mango_img_path, "rb") as f:
        img_bytes = f.read()
    status, mango_res = post_multipart(
        f"{FRONTEND_URL}/api/inspect?mode=manual&fruit=mango",
        {"fruit": "mango", "mode": "manual"},
        {"file": ("mango_sample.jpeg", img_bytes, "image/jpeg")}
    )
    print(f"  Mango Manual: HTTP {status} — Status={mango_res.get('status')}, Reason={mango_res.get('unavailable_reason', '')[:60]}...")
    test_results["inspection_tests"]["mango"] = mango_res

    # 2.5 Auto Mode: Negative Leaf Foliage (Uncertainty Gated)
    leaf_img_path = WORKSPACE / "ml/data/raw/fruitnet/Bad Quality_Fruits/Lime_Bad/IMG_7589.JPG"
    with open(leaf_img_path, "rb") as f:
        img_bytes = f.read()
    status, auto_res = post_multipart(
        f"{FRONTEND_URL}/api/inspect?mode=auto",
        {"mode": "auto"},
        {"file": ("foliage_negative.jpg", img_bytes, "image/jpeg")}
    )
    auto_id = auto_res.get("stage1_identification", {})
    print(f"  Auto Mode (Canopy Foliage): HTTP {status} — Predicted={auto_id.get('predicted_fruit')}, Uncertain={auto_id.get('is_uncertain')}, Status={auto_res.get('status')}")
    test_results["inspection_tests"]["auto_negative_foliage"] = auto_res

    # 3. Associate Inspection Result with a Produce Shipment
    print("\n[3/5] Testing Inspection Result Association with Shipment Lifecycle...")
    guava_stage = guava_cls.get("predicted_class", "Green")
    shipment_payload = {
        "produce_type": f"Guava ({guava_stage})",
        "origin": "Abohar Regional Packhouse, Punjab",
        "destination": "Azadpur Terminal Mandi, Delhi",
        "quantity": 1850.0,
        "status": "in_transit",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-DL-AZD-01",
        "tracking_mode": "simulated",
        "telemetry_mode": "simulated",
        "quality_grade": guava_stage,
        "inspection_verdict": {
            "target_fruit": "guava",
            "task_type": "classification",
            "predicted_class": guava_cls.get("predicted_class"),
            "stage": guava_stage,
            "confidence": guava_cls.get("confidence"),
            "probabilities": guava_cls.get("probabilities"),
            "model_version": "2.0.0",
            "inspection_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

    status, created_shipment = http_post_json(f"{FRONTEND_URL}/api/shipments", shipment_payload)
    shipment_id = created_shipment.get("id")
    print(f"  Created Shipment via /api/shipments: HTTP {status} — ID: {shipment_id}")
    print(f"    Produce: {created_shipment.get('produce_type')}")
    print(f"    Quality Grade: {created_shipment.get('quality_grade')}")
    print(f"    Origin Facility: {created_shipment.get('origin_facility_id')} ({created_shipment.get('origin_facility', {}).get('name')})")
    print(f"    Destination Facility: {created_shipment.get('destination_facility_id')} ({created_shipment.get('destination_facility', {}).get('name')})")
    test_results["shipment_lifecycle"]["created"] = created_shipment

    # 3.2 Audit Event History
    status, events = http_get(f"{BACKEND_URL}/api/shipments/{shipment_id}/events")
    event_types = [e.get("event_type") for e in events]
    print(f"  Shipment Events: HTTP {status} — Total Events: {len(events)} -> {event_types}")
    assert "shipment_created" in event_types, "shipment_created event missing!"
    assert "quality_inspection_recorded" in event_types, "quality_inspection_recorded event missing!"
    test_results["shipment_lifecycle"]["initial_events"] = events

    # 3.3 Run Multi-Step Transit Simulation
    print("\n[4/5] Progressing Transit Simulation (PostGIS Waypoint Updates)...")
    simulated_steps = []
    for step_num in range(1, 4):
        status, step_result = http_post_json(f"{BACKEND_URL}/api/shipments/{shipment_id}/simulate-step", {})
        wp = step_result.get("waypoint", {})
        telem = step_result.get("telemetry", {})
        lat = wp.get("latitude")
        lon = wp.get("longitude")
        temp = telem.get("temperature")
        humidity = telem.get("humidity")
        print(f"  Simulation Step {step_num}: Lat={lat}, Lon={lon}, Temp={temp}C, Humidity={humidity}%")
        simulated_steps.append(step_result)
        time.sleep(0.5)

    test_results["shipment_lifecycle"]["simulated_steps"] = simulated_steps

    # 3.4 Check Cold-Chain Risk Calculation
    status, risk_data = http_get(f"{BACKEND_URL}/api/shipments/{shipment_id}/risk")
    print(f"  Cold-Chain Risk Score: HTTP {status} — Current Risk: {risk_data.get('current_risk')}%, Predicted Arrival: {risk_data.get('predicted_arrival_risk')}%, Alert={risk_data.get('alert')}")
    test_results["shipment_lifecycle"]["risk_assessment"] = risk_data

    # 3.5 Dealer & Public In-Transit Queries
    status, in_transit_shipments = http_get(f"{FRONTEND_URL}/api/shipments?status=in_transit")
    matching = [s for s in in_transit_shipments if s.get("id") == shipment_id]
    print(f"  In-Transit Filter Query: HTTP {status} — Shipment {shipment_id} found in active transit: {len(matching) > 0}")
    assert len(matching) > 0, f"Shipment {shipment_id} not returned by in_transit filter!"

    # 4. Automated UI Screenshot Capture
    print("\n[5/5] Capturing Headless Browser UI Acceptance Screenshots...")
    screens = [
        ("01_dashboard_analyze_manual_guava.png", f"{FRONTEND_URL}/dashboard?role=Farmer&tab=analyze"),
        ("02_dashboard_shipments_tracking.png", f"{FRONTEND_URL}/dashboard?role=Logistics&tab=tracking"),
        ("03_dashboard_dealer_dashboard.png", f"{FRONTEND_URL}/dashboard?role=Dealer&tab=dealer"),
        ("04_dashboard_farmer_dashboard.png", f"{FRONTEND_URL}/dashboard?role=Farmer&tab=farmer"),
        ("05_dashboard_marketplace.png", f"{FRONTEND_URL}/dashboard?role=Buyer&tab=marketplace"),
        ("06_dashboard_admin_system_status.png", f"{FRONTEND_URL}/dashboard?role=Admin&tab=status"),
    ]

    for fname, url in screens:
        out_file = SCREENSHOT_DIR / fname
        ok, size = capture_screenshot(url, out_file)
        status_str = f"OK ({size:,} bytes)" if ok else "FAILED"
        print(f"  Captured {fname}: {status_str}")
        test_results["browser_screenshots"][fname] = {
            "path": str(out_file),
            "size_bytes": size,
            "success": ok,
            "url": url,
        }

    # Save complete test suite artifact
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)
    print(f"\n[OK] All Phase 17C E2E Acceptance Checks Complete! Results saved to:\n   {RESULTS_FILE}")


if __name__ == "__main__":
    main()
