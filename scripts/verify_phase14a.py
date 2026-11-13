"""
AgriChain AI - Phase 14A.1 Live Endpoint Verification Script
"""
import io
import json
import urllib.request
from PIL import Image

def main():
    print("=== 1. Multi-Fruit Registry Endpoint ===")
    req = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/cnn/registry")
    data = json.loads(req.read().decode("utf-8"))
    print(f"HTTP {req.status}")
    print("Supported fruits:", data["supported_fruits"])
    print("Available fruits:", data["available_fruits"])
    for f, info in data["fruits"].items():
        print(f"  {f}: available={info['available']}, validated={info['is_validated']}, status={info['status']}")

    print("\n=== 2. Legacy Guava Prediction Endpoints ===")
    buf = io.BytesIO()
    Image.new("RGB", (224, 224), color=(34, 139, 34)).save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    boundary = "----WebKitFormBoundaryPhase14Test"
    c_disp = 'Content-Disposition: form-data; name="file"; filename="guava_sample.jpg"'
    c_type = "Content-Type: image/jpeg"
    header = (f"--{boundary}\r\n{c_disp}\r\n{c_type}\r\n\r\n").encode("utf-8")
    footer = (f"\r\n--{boundary}--\r\n").encode("utf-8")
    body = header + jpeg_bytes + footer

    for ep in ["/predict", "/api/v1/cnn/predict"]:
        req2 = urllib.request.Request(
            f"http://127.0.0.1:8000{ep}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        res2 = urllib.request.urlopen(req2)
        pred = json.loads(res2.read().decode("utf-8"))
        print(f"{ep} -> HTTP {res2.status}")
        print(f"  target_crop={pred.get('target_crop')}, predicted_class={pred.get('predicted_class')}, confidence={pred.get('confidence')}")
        print(f"  detected_fruit={pred.get('detected_fruit')}, ripeness={pred.get('ripeness')}, status={pred.get('status')}")

    print("\n=== 3. Next.js Health Proxy ===")
    req3 = urllib.request.urlopen("http://localhost:3000/api/health")
    health = json.loads(req3.read().decode("utf-8"))
    print(f"HTTP {req3.status}: status={health.get('status')}, model={health.get('model')}, device={health.get('device')}")

    print("\n=== 4. Next.js Dashboard ===")
    req4 = urllib.request.urlopen("http://localhost:3000/dashboard")
    print(f"HTTP {req4.status}: HTML length={len(req4.read())} bytes")

    print("\n=== 5. Next.js Prediction Proxy ===")
    req5 = urllib.request.Request(
        "http://localhost:3000/api/predict",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    res5 = urllib.request.urlopen(req5)
    pred5 = json.loads(res5.read().decode("utf-8"))
    print(f"HTTP {res5.status}: target_crop={pred5.get('target_crop')}, class={pred5.get('class')}, label={pred5.get('label')}")
    print(f"  detected_fruit={pred5.get('detected_fruit')}")

if __name__ == "__main__":
    main()

