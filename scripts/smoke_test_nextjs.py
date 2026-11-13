"""
AgriChain AI - Next.js Web Frontend Integration Smoke Test
===========================================================
Validates that Next.js proxies correctly to the FastAPI backend at 127.0.0.1:8000:
1. /api/health
2. /api/shipments
3. /api/shipments/SHP-2026-001/telemetry
4. /api/predict (missing file -> 400)
5. /api/predict (valid image with missing model -> 503)
6. HTML rendering of /dashboard
"""

import io
import json
import urllib.error
import urllib.request
from PIL import Image

BASE_URL = "http://localhost:3000"

def get(path: str):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))

def post_json(path: str, payload: dict):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))

def post_multipart(path: str, filename: str, content_type: str, file_bytes: bytes):
    boundary = "----WebKitFormBoundaryNextTest2026"
    header_bytes = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    footer_bytes = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header_bytes + file_bytes + footer_bytes

    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))

def main():
    print("=" * 70)
    print("AGRICHAIN AI — NEXT.JS WEB APP SMOKE TEST (http://localhost:3000)")
    print("=" * 70)

    # 1. Health
    st, body = get("/api/health")
    print(f"[1] GET /api/health                   -> HTTP {st} | status='{body.get('status')}', crop='{body.get('target_crop')}'")
    assert st == 200, f"Expected 200, got {st}"

    # 2. Shipments list proxy
    st, body = get("/api/shipments")
    print(f"[2] GET /api/shipments                -> HTTP {st} | count={len(body)}")
    assert st == 200 and len(body) > 0, f"Shipments failed with {st}: {body}"

    # 3. Shipment telemetry proxy
    st, body = get("/api/shipments/SHP-2026-001/telemetry")
    print(f"[3] GET /api/shipments/ID/telemetry   -> HTTP {st} | telemetry count={len(body)}")
    assert st == 200 and len(body) > 0, f"Telemetry failed with {st}: {body}"

    # 4. Predict: Empty / Missing file -> 400
    st, body = post_multipart("/api/predict", "", "application/octet-stream", b"")
    print(f"[4] POST /api/predict (Empty)         -> HTTP {st} | detail='{body.get('detail')}'")
    assert st in (400, 422), f"Expected 400 or 422, got {st}"

    # 5. Predict: Valid image -> 503 (Missing model checkpoint, zero fabrication)
    buf = io.BytesIO()
    Image.new("RGB", (128, 128), color=(255, 140, 0)).save(buf, format="JPEG")
    st, body = post_multipart("/api/predict", "sample.jpg", "image/jpeg", buf.getvalue())
    print(f"[5] POST /api/predict (Valid JPEG)    -> HTTP {st} | detail='{body.get('detail')}'")
    assert st == 503, f"Expected 503, got {st}"
    assert "unavailable" in body.get("detail", "").lower(), "Expected unavailable in detail"

    # 6. Dashboard page HTML
    req = urllib.request.Request(f"{BASE_URL}/dashboard")
    with urllib.request.urlopen(req) as res:
        html = res.read().decode("utf-8")
        has_title = "AgriChain AI" in html or "Kinnow" in html
        print(f"[6] GET /dashboard                    -> HTTP {res.status} | HTML size={len(html)} bytes | Kinnow text present={has_title}")
        assert res.status == 200, f"Expected 200, got {res.status}"

    # 7. Telemetry Risk Prediction Proxy
    lstm_payload = {
        "shipment_id": "SHP-2026-001",
        "sequence": [
            {
                "hour": i,
                "temperature": 6.0 + (i * 0.1),
                "humidity": 87.0,
                "delay_minutes": i * 2,
                "speed_kmh": 60.0,
                "distance_remaining_km": 400.0 - (i * 15),
            }
            for i in range(24)
        ],
    }
    st, body = post_json("/api/telemetry/predict", lstm_payload)
    print(f"[7] POST /api/telemetry/predict        -> HTTP {st} | current_risk={body.get('current_risk')}, alert={body.get('alert')}")
    assert st == 200 and "current_risk" in body, f"Telemetry prediction failed: {body}"

    print("=" * 70)
    print("ALL 7 NEXT.JS SMOKE TESTS PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    main()
