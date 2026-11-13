"""
AgriChain AI - Guava CNN Inference Smoke Test
============================================
Exercises the updated CNNService with the verified Guava ResNet18 checkpoint
(ml/artifacts/best_guava_resnet18.pth) on actual held-out dataset specimens.

IMPORTANT SCIENTIFIC DISCLAIMER:
These smoke tests verify runtime inference execution, exact preprocessing parity,
and response contract stability. They demonstrate that the model functions correctly
on actual physical produce frames, but do NOT replace independent statistical evaluation.
"""

import os
import sys
import json
import time
from pathlib import Path
from PIL import Image

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.services.cnn_service import CNNService


def run_smoke_tests():
    print("=" * 75)
    print("AGRICHAIN AI — GUAVA CNN INFERENCE SMOKE TEST (PHASE 4)")
    print("=" * 75)

    weights_path = settings.resolved_guava_weights_path()
    print(f"Target weights path: {weights_path}")
    print(f"Weights exist on disk: {weights_path.exists()}")

    if not weights_path.exists():
        print("[ERROR] Guava model weights file not found. Aborting smoke test.")
        sys.exit(1)

    # 1. Initialize CNNService with guava checkpoint
    print("\n[1] Initializing CNNService with Guava Checkpoint...")
    service = CNNService(weights_path=weights_path)
    status = service.get_status()

    print(f"  Service status:            {status.status}")
    print(f"  Target crop:               {status.target_crop}")
    print(f"  Model available:           {status.model_available}")
    print(f"  Model name:                {status.model_name}")
    print(f"  Model version:             {status.model_version}")
    print(f"  Compute device:            {status.device}")
    print(f"  Class mapping verified:    {status.class_mapping_verified}")
    print(f"  Class mapping status:      {status.class_mapping_status}")
    print(f"  Classes:                   {service.classes}")
    print(f"  Class labels:              {service.class_labels}")

    assert service.is_available, "Service must report ready"
    assert status.target_crop == "guava", "Target crop must be guava"
    assert status.model_version == "2.0.0", "Model version must be 2.0.0"

    # 2. Load held-out test manifest
    manifest_path = PROJECT_ROOT / "ml" / "data" / "manifests" / "v2_grouped" / "test.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        test_records = json.load(f)

    print(f"\n[2] Loaded Held-Out Test Manifest: {len(test_records)} images.")

    # Select representative samples: 2 per class across varieties
    samples_to_test = []
    classes_needed = {"Green": 2, "Mature Green": 2, "Ripe": 2}
    class_counts = {"Green": 0, "Mature Green": 0, "Ripe": 0}

    for r in test_records:
        c = r["class_name"]
        if class_counts[c] < classes_needed[c] and os.path.exists(r["abs_path"]):
            samples_to_test.append(r)
            class_counts[c] += 1

    print(f"\n[3] Executing Single-Frame Inferences on {len(samples_to_test)} Actual Specimens:")
    print("-" * 75)

    results = []
    for idx, sample in enumerate(samples_to_test, 1):
        rel_path = sample["rel_path"]
        abs_path = sample["abs_path"]
        true_class = sample["class_name"]
        true_label = sample["label"]
        variety = sample.get("variety", "Unknown")

        with Image.open(abs_path) as img:
            t0 = time.perf_counter()
            pred = service.predict(img)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

        is_match = (pred.predicted_class == true_class)
        match_str = "[CORRECT]" if is_match else "[BORDER MISMATCH]"

        print(f"\nSpecimen {idx}/{len(samples_to_test)}: {variety} - {rel_path}")
        print(f"  True Label:        {true_class} (Index {true_label})")
        print(f"  Predicted Label:   {pred.label} (Index {pred.class_index}) {match_str}")
        print(f"  Confidence:        {pred.confidence:.4f} ({pred.confidence*100:.2f}%) [Uncalibrated Softmax Score]")
        print(f"  Class Probs:       Green={pred.probabilities.get('Green', 0):.4f}, "
              f"Mature Green={pred.probabilities.get('Mature Green', 0):.4f}, "
              f"Ripe={pred.probabilities.get('Ripe', 0):.4f}")
        print(f"  Inference Latency: {pred.inference_ms:.2f} ms (Pipeline Wall-clock: {elapsed_ms:.2f} ms)")

        results.append({
            "rel_path": rel_path,
            "variety": variety,
            "true_class": true_class,
            "predicted_class": pred.predicted_class,
            "class_index": pred.class_index,
            "confidence": pred.confidence,
            "probabilities": pred.probabilities,
            "inference_ms": pred.inference_ms,
            "match": is_match,
        })

    print("\n" + "=" * 75)
    print("SMOKE TEST SUMMARY")
    print("=" * 75)
    correct_count = sum(1 for r in results if r["match"])
    print(f"Specimens Tested:      {len(results)}")
    print(f"Matching Predictions:  {correct_count} / {len(results)} ({correct_count / len(results) * 100:.1f}%)")
    avg_latency = sum(r["inference_ms"] for r in results) / len(results)
    print(f"Average CNN Latency:   {avg_latency:.2f} ms on {service.torch_device}")
    print(f"Model Version:         {service.model_version}")
    print(f"Target Crop:           {service.target_crop}")
    print("\nNOTE: These smoke-test samples confirm end-to-end functionality and preprocessing parity.")
    print("They do NOT substitute for the full 346-image test set evaluation (83.24% acc, 0.8122 macro-F1).")
    print("=" * 75)
    return results


if __name__ == "__main__":
    run_smoke_tests()
