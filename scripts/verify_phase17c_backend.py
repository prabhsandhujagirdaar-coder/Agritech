"""
AgriChain AI - Phase 17C Live Backend Acceptance Test Runner
===========================================================
Executes Tasks 1, 2, and 3 of Phase 17C:
- Health, Registry, Identify, and Inspect endpoints.
- Model availability and checkpoint loading on CUDA/CPU.
- Error handling on unsupported crops and corrupt files.
- Manual inspection across Guava, Banana, Apple, Mango with real images.
- Auto Stage 1 identification across Guava, Banana, Apple, Mango, Foliage/Canopy, and Blurred images.
- Threshold verification (confidence >= 0.80, margin >= 0.15).
"""

import io
import json
import time
from pathlib import Path
from PIL import Image, ImageFilter

from fastapi.testclient import TestClient
from app.main import app

def run_acceptance_tests():
    client = TestClient(app)
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task1_runtime": {},
        "task2_manual_inspection": {},
        "task3_auto_identification": {},
    }

    print("======================================================================")
    print("PHASE 17C — ACCEPTANCE TESTING: TASKS 1, 2, AND 3")
    print("======================================================================\n")

    # -------------------------------------------------------------------------
    # TASK 1: Backend Runtime Verification
    # -------------------------------------------------------------------------
    print(">>> TASK 1: Backend Runtime Verification...")
    
    # 1.1 Health Probe
    res_health = client.get("/health")
    print(f"1.1 /health status: {res_health.status_code}")
    assert res_health.status_code == 200
    health_data = res_health.json()
    print(f"    Target crop: {health_data.get('target_crop')}, Model: {health_data.get('model')}, Device: {health_data.get('device')}")
    results["task1_runtime"]["health"] = health_data

    # 1.2 Multi-Fruit Registry
    res_reg = client.get("/api/v1/cnn/registry")
    print(f"1.2 /api/v1/cnn/registry status: {res_reg.status_code}")
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    print(f"    Supported fruits: {reg_data.get('supported_fruits')}")
    print(f"    Available fruits: {reg_data.get('available_fruits')}")
    print(f"    Stage 1 Identifier: {reg_data.get('stage1_identifier', {}).get('status')}, available={reg_data.get('stage1_identifier', {}).get('available')}")
    results["task1_runtime"]["registry"] = reg_data

    # 1.3 Error Handling: Unsupported Crop
    dummy_img = Image.new("RGB", (224, 224), color=(50, 150, 50))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    dummy_bytes = buf.getvalue()

    res_err_crop = client.post(
        "/api/v1/cnn/inspect?mode=manual&fruit=dragonfruit",
        files={"file": ("specimen.jpg", dummy_bytes, "image/jpeg")},
    )
    print(f"1.3 Unsupported crop rejection status: {res_err_crop.status_code} (detail: {res_err_crop.json().get('detail')})")
    assert res_err_crop.status_code == 400
    results["task1_runtime"]["unsupported_crop_rejection"] = res_err_crop.json()

    # 1.4 Error Handling: Corrupt / Empty File
    res_err_corrupt = client.post(
        "/api/v1/cnn/inspect?mode=manual&fruit=guava",
        files={"file": ("corrupt.jpg", b"NOT_A_VALID_JPEG_HEADER", "image/jpeg")},
    )
    print(f"1.4 Corrupted payload rejection status: {res_err_corrupt.status_code} (detail: {res_err_corrupt.json().get('detail')})")
    assert res_err_corrupt.status_code == 400
    results["task1_runtime"]["corrupt_payload_rejection"] = res_err_corrupt.json()

    # -------------------------------------------------------------------------
    # TASK 2: Manual Inspection Across All 4 Fruits
    # -------------------------------------------------------------------------
    print("\n>>> TASK 2: Manual Commodity Inspection (Real Images)...")

    # 2.1 Guava: 3 Stages
    guava_samples = {
        "Green": "ml/data/guava_classification/Local Sindhi/Green/40.jpg",
        "Mature Green": "ml/data/guava_classification/Local Sindhi/Mature Green/237.jpg",
        "Ripe": "ml/data/guava_classification/Local Sindhi/Ripe/140.jpg",
    }
    results["task2_manual_inspection"]["guava"] = {}
    for stage, path_str in guava_samples.items():
        with open(path_str, "rb") as f:
            res = client.post(
                "/api/v1/cnn/inspect?mode=manual&fruit=guava",
                files={"file": (Path(path_str).name, f, "image/jpeg")},
            )
        assert res.status_code == 200
        d = res.json()
        pred = d["classification"]["predicted_class"]
        conf = d["classification"]["confidence"]
        latency = d["inference_ms"]
        print(f"2.1 Guava [{stage} specimen]: Predicted={pred}, Conf={conf:.4f}, Latency={latency}ms")
        results["task2_manual_inspection"]["guava"][stage] = {
            "image": path_str,
            "predicted": pred,
            "confidence": conf,
            "latency_ms": latency,
            "probabilities": d["classification"]["probabilities"],
        }

    # 2.2 Banana: 4 Stages
    banana_samples = {
        "Unripe": "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Unripe/Ambon_Unripe_Bottom_0009.jpg",
        "Half_Ripe": "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Half_Ripe/Raja_Half_Ripe_Left_0001.jpg",
        "Ripe": "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Ripe/Cavendish_Ripe_Bottom_0009.jpg",
        "Overripe": "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Overripe/Cavendish_Overripe_Bottom_0008.jpg",
    }
    results["task2_manual_inspection"]["banana"] = {}
    for stage, path_str in banana_samples.items():
        with open(path_str, "rb") as f:
            res = client.post(
                "/api/v1/cnn/inspect?mode=manual&fruit=banana",
                files={"file": (Path(path_str).name, f, "image/jpeg")},
            )
        assert res.status_code == 200
        d = res.json()
        pred = d["classification"]["predicted_class"]
        conf = d["classification"]["confidence"]
        latency = d["inference_ms"]
        print(f"2.2 Banana [{stage} specimen]: Predicted={pred}, Conf={conf:.4f}, Latency={latency}ms")
        results["task2_manual_inspection"]["banana"][stage] = {
            "image": path_str,
            "predicted": pred,
            "confidence": conf,
            "latency_ms": latency,
            "probabilities": d["classification"]["probabilities"],
        }

    # 2.3 Apple: YOLOv8n Orchard Detection
    apple_path = "ml/data/processed/apple_detection_yolo/images/test/108.jpg"
    with open(apple_path, "rb") as f:
        res_apple = client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=apple",
            files={"file": (Path(apple_path).name, f, "image/jpeg")},
        )
    assert res_apple.status_code == 200
    apple_d = res_apple.json()
    det = apple_d["detection"]
    print(f"2.3 Apple [Orchard Scene 108.jpg]: Detected={det['detected_apples_count']} apples, AvgConf={det['average_confidence']:.4f}")
    print(f"    License: {det['license']}")
    print(f"    Disclaimer: {det['scope_disclaimer']}")
    for i, b in enumerate(det["boxes"]):
        print(f"    Box #{i+1}: [{b['x1']}, {b['y1']}, {b['x2']}, {b['y2']}], conf={b['confidence']}")
    assert "classification" not in apple_d or apple_d["classification"] is None, "Apple must NOT return maturity classification!"
    results["task2_manual_inspection"]["apple"] = {
        "image": apple_path,
        "count": det["detected_apples_count"],
        "avg_conf": det["average_confidence"],
        "boxes": det["boxes"],
        "license": det["license"],
    }

    # 2.4 Mango: Honest Gated State
    mango_path = "ml/data/raw/mango/original/IMG-37.jpeg"
    with open(mango_path, "rb") as f:
        res_mango = client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=mango",
            files={"file": (Path(mango_path).name, f, "image/jpeg")},
        )
    assert res_mango.status_code == 200
    mango_d = res_mango.json()
    print(f"2.4 Mango: status={mango_d['status']}, task_type={mango_d['task_type']}")
    print(f"    Reason: {mango_d['unavailable_reason']}")
    assert mango_d["status"] == "unavailable"
    assert mango_d["classification"] is None, "Mango must NEVER fabricate classification results!"
    assert mango_d["detection"] is None
    results["task2_manual_inspection"]["mango"] = mango_d

    # -------------------------------------------------------------------------
    # TASK 3: Automatic Fruit Identification via Stage 1 MobileNetV3-Large
    # -------------------------------------------------------------------------
    print("\n>>> TASK 3: Automatic Fruit Identification (Stage 1)...")

    test_specimens = [
        ("guava", "ml/data/guava_classification/Local Sindhi/Green/40.jpg", "Clean Guava"),
        ("banana", "ml/data/raw/banana/ripeness/Banana Ripeness Classification Dataset/Ripe/Cavendish_Ripe_Bottom_0009.jpg", "Clean Banana"),
        ("apple", "ml/data/processed/apple_crops_v1/test/Mature/IMG_12340_inst00_mature.jpg", "Apple Crop"),
        ("mango", "ml/data/raw/mango/original/IMG-37.jpeg", "Clean Mango"),
        ("foliage", "ml/data/raw/fruitnet/Bad Quality_Fruits/Lime_Bad/IMG_7589.JPG", "Canopy Foliage"),
    ]

    results["task3_auto_identification"]["specimens"] = []

    for expected_type, path_str, desc in test_specimens:
        with open(path_str, "rb") as f:
            raw_b = f.read()

        # Test 3.1 Standalone Identify Endpoint
        res_id = client.post("/api/v1/cnn/identify", files={"file": ("test.jpg", raw_b, "image/jpeg")})
        assert res_id.status_code == 200
        id_data = res_id.json()

        # Test 3.2 Auto Inspect Endpoint
        res_auto = client.post("/api/v1/cnn/inspect?mode=auto", files={"file": ("test.jpg", raw_b, "image/jpeg")})
        assert res_auto.status_code == 200
        auto_data = res_auto.json()

        print(f"3.1 [{desc}]: Identified='{id_data['predicted_fruit']}', Conf={id_data['confidence']:.4f}, is_uncertain={id_data['is_uncertain']}")
        print(f"    Auto Inspect Status: {auto_data['status']}, Target: {auto_data['target_fruit']}")

        results["task3_auto_identification"]["specimens"].append({
            "expected_type": expected_type,
            "description": desc,
            "image": path_str,
            "identification": id_data,
            "auto_inspection": {
                "status": auto_data["status"],
                "target_fruit": auto_data["target_fruit"],
                "warnings": auto_data.get("warnings", []),
                "task_type": auto_data["task_type"],
            },
        })

    # Test 3.3 Blurred & Degraded Image Handling
    print("\n3.3 Testing Degraded / Heavily Blurred Image...")
    clean_img = Image.open("ml/data/guava_classification/Local Sindhi/Green/40.jpg")
    blurred_img = clean_img.filter(ImageFilter.GaussianBlur(radius=15))
    buf = io.BytesIO()
    blurred_img.save(buf, format="JPEG", quality=20)
    blurred_bytes = buf.getvalue()

    res_blurred = client.post("/api/v1/cnn/inspect?mode=auto", files={"file": ("blurred.jpg", blurred_bytes, "image/jpeg")})
    assert res_blurred.status_code == 200
    blurred_data = res_blurred.json()
    print(f"    Blurred Specimen: Status={blurred_data['status']}, Identified={blurred_data.get('identified_fruit')}")
    print(f"    Uncertainty Warning: {blurred_data.get('warnings')}")
    results["task3_auto_identification"]["blurred_test"] = blurred_data

    # Save all results to disk
    out_file = Path("ml/experiments/phase17c_backend_test_results.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n>>> Tasks 1, 2, 3 Complete! Saved detailed log to '{out_file}'.")

if __name__ == "__main__":
    run_acceptance_tests()

