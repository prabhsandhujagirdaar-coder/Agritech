"""
AgriChain AI Live Container Stack Verification Script
Validates all Phase 8 testing criteria against the live Docker containers.
"""
import io
import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8000"
WEB_URL = "http://127.0.0.1:3000"

def log_test(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name} - {detail}")
    return passed

def create_dummy_jpeg() -> bytes:
    try:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (32, 32), color=(255, 140, 0)) # Kinnow orange
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        # Fallback minimal 1x1 JPEG
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xBF, 0x80, 0xFF, 0xD9
        ])

def run_tests():
    all_passed = True

    # 1. Root Health
    try:
        req = urllib.request.Request(f"{BASE_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            db_conn = data.get("database", {}).get("connected") == True
            is_kinnow = data.get("target_crop") == "kinnow"
            all_passed &= log_test("Root Health Endpoint", db_conn and is_kinnow, f"Crop: {data.get('target_crop')}, DB Connected: {db_conn}")
    except Exception as e:
        all_passed &= log_test("Root Health Endpoint", False, str(e))

    # 2. API v1 Health
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/v1/health")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            db_conn = data.get("database", {}).get("connected") == True
            all_passed &= log_test("API v1 Health Endpoint", db_conn, f"Status: {data.get('status')}, DB: {db_conn}")
    except Exception as e:
        all_passed &= log_test("API v1 Health Endpoint", False, str(e))

    # 3. Next.js Web Health Proxy
    try:
        req = urllib.request.Request(f"{WEB_URL}/api/health")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            has_backend = "backend" in data
            all_passed &= log_test("Next.js Health Route Proxy", has_backend, f"Status: {res.status}, Latency: {data.get('latencyMs')}ms")
    except Exception as e:
        all_passed &= log_test("Next.js Health Route Proxy", False, str(e))

    # 4. List Shipments
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/v1/shipments")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode())
            count = len(data)
            all_passed &= log_test("List Shipments", count >= 2, f"Found {count} shipments")
    except Exception as e:
        all_passed &= log_test("List Shipments", False, str(e))

    # 5. Create Test Shipment
    created_id = None
    try:
        payload = {
            "origin": "Fazilka Mandi",
            "destination": "Amritsar Cold Hub",
            "produce_type": "Kinnow Mandarin",
            "quantity": 450.0,
            "status": "in_transit"
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/shipments",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            created_id = res_data.get("id")
            created_ok = created_id is not None and res_data.get("origin") == "Fazilka Mandi"
            all_passed &= log_test("Create Shipment (PostGIS Dual-Persist)", created_ok, f"Created {created_id}")
    except Exception as e:
        all_passed &= log_test("Create Shipment (PostGIS Dual-Persist)", False, str(e))

    active_id = created_id or "SHP-2026-001"

    # 6. Patch Shipment Status
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/shipments/{active_id}",
            data=json.dumps({"status": "delivered"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            updated = res_data.get("status") == "delivered"
            all_passed &= log_test("Patch Shipment Status", updated, f"Updated {active_id} status to: {res_data.get('status')}")
    except Exception as e:
        all_passed &= log_test("Patch Shipment Status", False, str(e))

    # 7. Post Telemetry Log
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/shipments/{active_id}/telemetry",
            data=json.dumps({
                "temperature": 4.8,
                "humidity": 90.0,
                "sensor_id": "SNS-ABOHAR-01",
                "location": "Near Malout Bypass"
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            telem_ok = res_data.get("temperature") == 4.8 or res_data.get("shipment_id") == active_id
            all_passed &= log_test("Ingest Telemetry (PostgreSQL Dual-Persist)", telem_ok, f"Logged for {active_id}: {res_data.get('temperature')}°C")
    except Exception as e:
        all_passed &= log_test("Ingest Telemetry (PostgreSQL Dual-Persist)", False, str(e))

    # 8. Post Geo Waypoint
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/shipments/{active_id}/waypoints",
            data=json.dumps({
                "longitude": 74.0254,
                "latitude": 30.4038,
                "altitude_m": 185.0,
                "speed_kmh": 58.0,
                "heading_deg": 45.0
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            wp_ok = res_data.get("shipment_id") == active_id and res_data.get("srid") == 4326
            all_passed &= log_test("Ingest PostGIS Waypoint (SRID 4326 GiST)", wp_ok, f"Recorded Waypoint {res_data.get('id')} with SRID {res_data.get('srid')}")
    except Exception as e:
        all_passed &= log_test("Ingest PostGIS Waypoint (SRID 4326 GiST)", False, str(e))

    # 9. Get Shipment Risk Calculation
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/v1/shipments/{active_id}/risk")
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            risk_ok = "current_risk" in res_data and "predicted_arrival_risk" in res_data
            all_passed &= log_test("Shipment Risk Evaluation", risk_ok, f"Risk: {res_data.get('current_risk')}, Arrival: {res_data.get('predicted_arrival_risk')}")
    except Exception as e:
        all_passed &= log_test("Shipment Risk Evaluation", False, str(e))

    # 10. ML CNN Scientific Integrity Check (Expect HTTP 503 since Kinnow weights not deployed)
    try:
        jpeg_bytes = create_dummy_jpeg()
        boundary = "AgriChainTestBoundary12345"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="kinnow_sample.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + jpeg_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/cnn/predict",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            all_passed &= log_test("CNN Scientific Integrity", False, "Unexpected 200 OK when Kinnow model missing!")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        status_ok = e.code == 503 and "Kinnow" in err_body
        all_passed &= log_test("CNN Scientific Integrity (HTTP 503)", status_ok, f"Code: {e.code}, Detail: {err_body}")
    except Exception as e:
        all_passed &= log_test("CNN Scientific Integrity (HTTP 503)", False, str(e))

    # 11. LSTM Telemetry Prediction
    try:
        telem_payload = {
            "shipment_id": active_id,
            "sequence": [
                {"hour": 0, "temperature": 4.5, "humidity": 88.0, "delay_minutes": 0, "speed_kmh": 50.0, "distance_remaining_km": 150.0},
                {"hour": 1, "temperature": 4.8, "humidity": 89.0, "delay_minutes": 10, "speed_kmh": 45.0, "distance_remaining_km": 105.0}
            ]
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/telemetry/predict",
            data=json.dumps(telem_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            res_data = json.loads(res.read().decode())
            has_risk = "predicted_arrival_risk" in res_data
            all_passed &= log_test("LSTM Telemetry Risk Prediction", has_risk, f"Current: {res_data.get('current_risk')}, Predicted: {res_data.get('predicted_arrival_risk')}, Alert: {res_data.get('alert')}")
    except Exception as e:
        all_passed &= log_test("LSTM Telemetry Risk Prediction", False, str(e))

    # 12. Next.js Web UI Delivery
    try:
        req = urllib.request.Request(f"{WEB_URL}/dashboard")
        with urllib.request.urlopen(req, timeout=5) as res:
            html = res.read().decode()
            web_ok = res.status == 200 and ("AgriChain" in html or "Shipment" in html or "Dashboard" in html)
            all_passed &= log_test("Next.js Dashboard UI Delivery", web_ok, f"Status: {res.status}, Length: {len(html)} bytes")
    except Exception as e:
        all_passed &= log_test("Next.js Dashboard UI Delivery", False, str(e))

    print("\n==========================================")
    print(f"OVERALL LIVE SUITE RESULT: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print("==========================================")
    return all_passed

if __name__ == "__main__":
    run_tests()
