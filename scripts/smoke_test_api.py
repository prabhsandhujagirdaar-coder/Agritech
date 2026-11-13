"""
AgriChain AI - Live HTTP Integration Smoke Test
===============================================
Exercises live endpoints against running FastAPI server at http://127.0.0.1:8000.
Tests:
- Root and versioned health checks
- CNN status reporting
- Multipart image validation (415, 400)
- 503 missing-model state (zero fabrication)
- Shipment and telemetry endpoints
"""

import io
import json
import urllib.error
import urllib.request
from PIL import Image

BASE_URL = "http://127.0.0.1:8000"


def get(endpoint: str):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8"))


def post_json(endpoint: str, payload: dict):
    url = f"{BASE_URL}{endpoint}"
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


def post_multipart(endpoint: str, filename: str, content_type: str, file_bytes: bytes):
    url = f"{BASE_URL}{endpoint}"
    boundary = "----WebKitFormBoundarySmokeTest2026"
    header_bytes = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    footer_bytes = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = header_bytes + file_bytes + footer_bytes

    req = urllib.request.Request(
        url,
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
    print("AGRICHAIN AI — LIVE HTTP SMOKE TEST (FastAPI at 127.0.0.1:8000)")
    print("=" * 70)

    # 1. Health checks
    st, body = get("/health")
    print(f"[1] GET /health                 -> HTTP {st} | status='{body.get('status')}', crop='{body.get('target_crop')}'")
    assert st == 200, f"Expected 200, got {st}"

    st, body = get("/api/v1/health")
    print(f"[2] GET /api/v1/health          -> HTTP {st} | service='{body.get('service')}'")
    assert st == 200, f"Expected 200, got {st}"

    # 2. CNN status
    st, body = get("/api/v1/cnn/status")
    print(f"[3] GET /api/v1/cnn/status      -> HTTP {st} | status='{body.get('status')}', available={body.get('model_available')}")
    assert st == 200, f"Expected 200, got {st}"
    assert body.get("model_available") is False, "Model must be marked unavailable without trained checkpoint"

    # 3. Validation: Unsupported media type (415)
    st, body = post_multipart("/predict", "document.pdf", "application/pdf", b"%PDF-1.4 sample pdf")
    print(f"[4] POST /predict (PDF)         -> HTTP {st} | detail='{body.get('detail')}'")
    assert st == 415, f"Expected 415, got {st}"

    # 4. Validation: Corrupt image (400)
    st, body = post_multipart("/predict", "corrupted.jpg", "image/jpeg", b"this is not real jpeg content")
    print(f"[5] POST /predict (Corrupt)     -> HTTP {st} | detail='{body.get('detail')}'")
    assert st == 400, f"Expected 400, got {st}"

    # 5. Validation: Empty upload (400)
    st, body = post_multipart("/predict", "empty.png", "image/png", b"")
    print(f"[6] POST /predict (Empty)       -> HTTP {st} | detail='{body.get('detail')}'")
    assert st == 400, f"Expected 400, got {st}"

    # 6. Valid Image upload when Model Artifact is missing -> HTTP 503
    buf = io.BytesIO()
    Image.new("RGB", (128, 128), color=(255, 140, 0)).save(buf, format="JPEG")
    st, body = post_multipart("/predict", "valid_kinnow.jpg", "image/jpeg", buf.getvalue())
    print(f"[7] POST /predict (Valid JPEG)  -> HTTP {st} | detail='{body.get('detail')}'")
    assert st == 503, f"Expected 503, got {st}"
    assert "unavailable" in body.get("detail", "").lower(), "Expected unavailable notice in 503 detail"
    assert "confidence" not in body, "Must NEVER fabricate confidence scores"
    assert "probabilities" not in body, "Must NEVER fabricate probabilities"

    # 7. Endpoint Parity: /api/v1/cnn/predict
    st, body = post_multipart("/api/v1/cnn/predict", "valid_kinnow.jpg", "image/jpeg", buf.getvalue())
    print(f"[8] POST /api/v1/cnn/predict    -> HTTP {st} | parity verified")
    assert st == 503, f"Expected 503, got {st}"

    # 8. Shipments
    st, body = get("/api/v1/shipments")
    print(f"[9] GET /api/v1/shipments       -> HTTP {st} | {len(body)} shipments listed")
    assert st == 200 and len(body) > 0, "Shipments list failed"

    st, body = get("/api/v1/shipments/SHP-2026-001")
    print(f"[10] GET /api/v1/shipments/ID   -> HTTP {st} | id='{body.get('id')}', origin='{body.get('origin')}'")
    assert st == 200 and body.get("id") == "SHP-2026-001", "Shipment detail failed"

    # 9. Telemetry & LSTM
    lstm_payload = {
        "shipment_id": "SHP-2026-001",
        "sequence": [
            {
                "hour": i,
                "temperature": 5.8 + (i * 0.1),
                "humidity": 87.0,
                "delay_minutes": i * 3,
                "speed_kmh": 60.0,
                "distance_remaining_km": 450.0 - (i * 18),
            }
            for i in range(24)
        ],
    }
    st, body = post_json("/api/v1/telemetry/predict", lstm_payload)
    print(f"[11] POST /api/v1/telemetry/predict -> HTTP {st} | current_risk={body.get('current_risk')}, alert={body.get('alert')}")
    assert st == 200 and "current_risk" in body, "Telemetry prediction failed"

    print("=" * 70)
    print("ALL 11 LIVE SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
