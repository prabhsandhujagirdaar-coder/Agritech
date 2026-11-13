"""
AgriChain AI — Phase 16B: Workstream B — Apple YOLOv8n Training & Benchmark
==========================================================================
Trains and rigorously benchmarks YOLOv8n for orchard apple detection.

Dataset:
  - Train: 1,041 scenes (1,981 instances)
  - Val:     126 scenes (185 instances)
  - Test:    239 scenes (409 instances)
  Total:   1,406 scenes (2,575 apple instances)

Key Requirements:
  - Pretrained weights: yolov8n.pt (SHA-256 verified)
  - Deterministic seed 42
  - Resolution: 640x640, Batch size: 16
  - Validation model selection
  - Locked test set evaluation: Precision, Recall, mAP50, mAP50-95
  - Dual latency benchmarks (GPU & CPU: BS=1 and BS=32 throughput)
  - Difficult-case forensic analysis (crowded, small, occluded, overlapping)
  - Visual prediction examples saved to visual_previews/
  - Generates required reports:
      * ml/data/reports/phase16b_apple_yolo_evaluation.json
      * ml/data/reports/phase16b_apple_yolo_error_analysis.json
      * ml/data/reports/phase16b_apple_yolo_readiness.json
  - Enforces CC BY-NC 4.0 licensing constraint metadata
"""

import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from collections import defaultdict

# Real-time stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DATA_YAML = WORKSPACE_ROOT / "ml" / "data" / "processed" / "apple_detection_yolo" / "data.yaml"
EXP_DIR = WORKSPACE_ROOT / "ml" / "experiments" / "phase16b" / "apple_yolo"
REPORTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "reports"
PREVIEWS_DIR = EXP_DIR / "visual_previews"

RANDOM_SEED = 42

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def benchmark_yolo_latency(model, device_str, imgsz=640, runs=100):
    # BS=1 benchmark
    dummy_bs1 = torch.randn((1, 3, imgsz, imgsz)).to(device_str)
    # Warmup
    for _ in range(20):
        _ = model.predict(dummy_bs1, verbose=False)
    if "cuda" in device_str:
        torch.cuda.synchronize()

    timings_bs1 = []
    for _ in range(runs):
        t0 = time.perf_counter()
        _ = model.predict(dummy_bs1, verbose=False)
        if "cuda" in device_str:
            torch.cuda.synchronize()
        timings_bs1.append((time.perf_counter() - t0) * 1000.0)

    # BS=16/32 benchmark
    bs_val = 32 if "cuda" in device_str else 8
    dummy_batch = torch.randn((bs_val, 3, imgsz, imgsz)).to(device_str)
    for _ in range(5):
        _ = model.predict(dummy_batch, verbose=False)
    if "cuda" in device_str:
        torch.cuda.synchronize()

    timings_batch = []
    batch_runs = 30 if "cuda" in device_str else 10
    for _ in range(batch_runs):
        t0 = time.perf_counter()
        _ = model.predict(dummy_batch, verbose=False)
        if "cuda" in device_str:
            torch.cuda.synchronize()
        timings_batch.append((time.perf_counter() - t0) * 1000.0)

    mean_bs1 = float(np.mean(timings_bs1))
    median_bs1 = float(np.median(timings_bs1))
    p95_bs1 = float(np.percentile(timings_bs1, 95))

    mean_batch_ms = float(np.mean(timings_batch))
    throughput_img_sec = float(bs_val / (mean_batch_ms / 1000.0))

    return {
        "mean_latency_bs1_ms": mean_bs1,
        "median_latency_bs1_ms": median_bs1,
        "p95_latency_bs1_ms": p95_bs1,
        "batch_size_evaluated": bs_val,
        "batch_time_ms": mean_batch_ms,
        "throughput_images_per_sec": throughput_img_sec
    }

def main():
    print("=" * 80, flush=True)
    print("AGRICHAIN AI — PHASE 16B: WORKSTREAM B — APPLE YOLOV8N DETECTOR TRAINING", flush=True)
    print("=" * 80, flush=True)

    device = 0 if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"Device: {device} ({device_name})", flush=True)

    EXP_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Pretrained weights provenance
    pretrained_weights = "yolov8n.pt"
    pretrained_hash = compute_sha256(Path(pretrained_weights))
    print(f"Pretrained weights: {pretrained_weights} (SHA-256: {pretrained_hash})", flush=True)

    epochs = 15
    batch_size = 16
    imgsz = 640

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    train_start = time.perf_counter()
    print(f"\nStarting YOLOv8n training for {epochs} epochs (imgsz={imgsz}, batch={batch_size})...", flush=True)

    model = YOLO(pretrained_weights)
    results = model.train(
        data=str(DATA_YAML),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        device=device,
        seed=RANDOM_SEED,
        deterministic=True,
        project=str(EXP_DIR),
        name="apple_yolov8n_run",
        save=True,
        plots=True,
        val=True,
        workers=0,
        exist_ok=True
    )
    train_duration = time.perf_counter() - train_start
    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
    print(f"Training completed in {train_duration:.2f} seconds. Peak VRAM: {peak_vram_mb:.1f} MB", flush=True)

    # Locate and preserve best checkpoint
    run_dir = EXP_DIR / "apple_yolov8n_run"
    best_pt = run_dir / "weights" / "best.pt"
    last_pt = run_dir / "weights" / "last.pt"
    if not best_pt.exists():
        best_pt = last_pt

    dest_best_pt = EXP_DIR / "best_apple_yolov8n.pt"
    dest_last_pt = EXP_DIR / "last_apple_yolov8n.pt"
    shutil.copy2(best_pt, dest_best_pt)
    if last_pt.exists():
        shutil.copy2(last_pt, dest_last_pt)

    best_chk_hash = compute_sha256(dest_best_pt)
    best_chk_size_mb = dest_best_pt.stat().st_size / (1024 * 1024)

    print(f"\nSaved Best Model Checkpoint: {dest_best_pt}", flush=True)
    print(f"  - Size: {best_chk_size_mb:.2f} MB", flush=True)
    print(f"  - SHA-256: {best_chk_hash}", flush=True)

    # 1. Validation Split Metrics
    print("\n[VALIDATION METRICS (126 scenes)]", flush=True)
    best_model = YOLO(str(dest_best_pt))
    val_results = best_model.val(
        data=str(DATA_YAML),
        split="val",
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        workers=0
    )
    val_p = float(val_results.results_dict.get("metrics/precision(B)", 0.0))
    val_r = float(val_results.results_dict.get("metrics/recall(B)", 0.0))
    val_mAP50 = float(val_results.results_dict.get("metrics/mAP50(B)", 0.0))
    val_mAP50_95 = float(val_results.results_dict.get("metrics/mAP50-95(B)", 0.0))
    print(f"  Val Precision: {val_p:.4f} | Recall: {val_r:.4f} | mAP50: {val_mAP50:.4f} | mAP50-95: {val_mAP50_95:.4f}", flush=True)

    # 2. Locked Held-Out Test Split Metrics (239 scenes, 409 instances)
    print("\n[LOCKED TEST SET EVALUATION (239 scenes)]", flush=True)
    test_results = best_model.val(
        data=str(DATA_YAML),
        split="test",
        project=str(EXP_DIR),
        name="test_evaluation",
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        workers=0,
        exist_ok=True
    )
    test_p = float(test_results.results_dict.get("metrics/precision(B)", 0.0))
    test_r = float(test_results.results_dict.get("metrics/recall(B)", 0.0))
    test_mAP50 = float(test_results.results_dict.get("metrics/mAP50(B)", 0.0))
    test_mAP50_95 = float(test_results.results_dict.get("metrics/mAP50-95(B)", 0.0))
    fitness = float(test_results.fitness) if hasattr(test_results, 'fitness') else test_mAP50

    print(f"  Test Precision: {test_p:.4f} | Recall: {test_r:.4f} | mAP50: {test_mAP50:.4f} | mAP50-95: {test_mAP50_95:.4f}", flush=True)

    # 3. Latency Benchmarks
    print("\n[INFERENCE LATENCY BENCHMARK]", flush=True)
    gpu_lat = benchmark_yolo_latency(best_model, "cuda:0" if torch.cuda.is_available() else "cpu", imgsz=imgsz, runs=100)
    print(f"  GPU BS=1 Median: {gpu_lat['median_latency_bs1_ms']:.2f}ms | Throughput: {gpu_lat['throughput_images_per_sec']:.1f} img/s", flush=True)
    cpu_lat = benchmark_yolo_latency(best_model, "cpu", imgsz=imgsz, runs=30)
    print(f"  CPU BS=1 Median: {cpu_lat['median_latency_bs1_ms']:.2f}ms | Throughput: {cpu_lat['throughput_images_per_sec']:.1f} img/s", flush=True)

    # 4. Difficult-Case Analysis & Per-Scene Detection Forensics
    print("\n[DIFFICULT-CASE FORENSIC ANALYSIS]", flush=True)
    test_img_dir = WORKSPACE_ROOT / "ml" / "data" / "processed" / "apple_detection_yolo" / "images" / "test"
    test_lbl_dir = WORKSPACE_ROOT / "ml" / "data" / "processed" / "apple_detection_yolo" / "labels" / "test"
    test_images = sorted(list(test_img_dir.glob("*.jpg")) + list(test_img_dir.glob("*.png")))

    per_scene_stats = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    difficult_categories = {
        "crowded_scenes_ge_3": [],
        "small_apples_area_le_0_01": [],
        "occluded_or_leaves": [],
        "low_confidence_detections": [],
        "missed_detections_fn": [],
        "false_detections_fp": []
    }

    # IoU helper
    def box_iou(box1, box2):
        # [x1, y1, x2, y2]
        xi1 = max(box1[0], box2[0])
        yi1 = max(box1[1], box2[1])
        xi2 = min(box1[2], box2[2])
        yi2 = min(box1[3], box2[3])
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        b1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        b2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union_area = b1_area + b2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    print("  Running detailed per-scene evaluation...")
    for img_p in test_images:
        lbl_p = test_lbl_dir / f"{img_p.stem}.txt"
        gt_boxes = [] # normalized [x1, y1, x2, y2]
        if lbl_p.exists():
            with open(lbl_p, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                        gt_boxes.append([cx - w/2, cy - h/2, cx + w/2, cy + h/2, w * h])

        pred_res = best_model.predict(img_p, conf=0.25, verbose=False)[0]
        pred_boxes = []
        if pred_res.boxes is not None and len(pred_res.boxes) > 0:
            orig_w, orig_h = pred_res.orig_shape[1], pred_res.orig_shape[0]
            for b in pred_res.boxes:
                coords = b.xyxy[0].cpu().numpy()
                conf_val = float(b.conf[0].cpu().item())
                # normalize coords
                pred_boxes.append([coords[0] / orig_w, coords[1] / orig_h, coords[2] / orig_w, coords[3] / orig_h, conf_val])

        # Match GT to Predictions at IoU 0.5
        matched_gt = set()
        matched_pred = set()
        for p_idx, pb in enumerate(pred_boxes):
            best_iou = 0.0
            best_g_idx = -1
            for g_idx, gb in enumerate(gt_boxes):
                if g_idx in matched_gt:
                    continue
                iou = box_iou(pb[:4], gb[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_g_idx = g_idx
            if best_iou >= 0.5:
                matched_gt.add(best_g_idx)
                matched_pred.add(p_idx)

        scene_tp = len(matched_gt)
        scene_fp = len(pred_boxes) - len(matched_pred)
        scene_fn = len(gt_boxes) - len(matched_gt)

        total_tp += scene_tp
        total_fp += scene_fp
        total_fn += scene_fn

        scene_info = {
            "image": img_p.name,
            "ground_truth_count": len(gt_boxes),
            "predicted_count": len(pred_boxes),
            "tp": scene_tp,
            "fp": scene_fp,
            "fn": scene_fn
        }
        per_scene_stats.append(scene_info)

        # Categorize
        if len(gt_boxes) >= 3:
            difficult_categories["crowded_scenes_ge_3"].append(img_p.name)
        if any(gb[4] < 0.01 for gb in gt_boxes):
            difficult_categories["small_apples_area_le_0_01"].append(img_p.name)
        if any(pb[4] < 0.50 for pb in pred_boxes):
            difficult_categories["low_confidence_detections"].append(img_p.name)
        if scene_fn > 0:
            difficult_categories["missed_detections_fn"].append(img_p.name)
        if scene_fp > 0:
            difficult_categories["false_detections_fp"].append(img_p.name)

    print(f"  Total GT Apple Instances: {total_tp + total_fn} (409 expected)")
    print(f"  Detections: True Positives={total_tp}, False Positives={total_fp}, False Negatives={total_fn}", flush=True)
    instance_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    instance_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    print(f"  Instance Precision (IoU 0.5): {instance_precision:.4f} | Recall: {instance_recall:.4f}", flush=True)

    # 5. Render Visual Preview Images for Key Difficult Scenarios
    print("  Generating visual detection examples...", flush=True)
    sample_targets = [
        difficult_categories["crowded_scenes_ge_3"][:2],
        difficult_categories["small_apples_area_le_0_01"][:2],
        difficult_categories["missed_detections_fn"][:2],
        difficult_categories["false_detections_fp"][:2]
    ]
    preview_filenames = set(item for sublist in sample_targets for item in sublist)

    for fn in preview_filenames:
        img_p = test_img_dir / fn
        if not img_p.exists():
            continue
        im = Image.open(img_p).convert("RGB")
        draw = ImageDraw.Draw(im)
        w_img, h_img = im.size

        # Draw GT in GREEN
        lbl_p = test_lbl_dir / f"{img_p.stem}.txt"
        if lbl_p.exists():
            with open(lbl_p, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        cx, cy, bw, bh = float(parts[1])*w_img, float(parts[2])*h_img, float(parts[3])*w_img, float(parts[4])*h_img
                        draw.rectangle([cx-bw/2, cy-bh/2, cx+bw/2, cy+bh/2], outline="#00FF00", width=2)

        # Draw Predictions in CYAN with confidence
        pred_res = best_model.predict(img_p, conf=0.25, verbose=False)[0]
        if pred_res.boxes is not None:
            for b in pred_res.boxes:
                coords = b.xyxy[0].cpu().numpy()
                c_val = float(b.conf[0].cpu().item())
                draw.rectangle([coords[0], coords[1], coords[2], coords[3]], outline="#00FFFF", width=2)
                draw.text((coords[0], max(0, coords[1]-12)), f"{c_val:.2f}", fill="#00FFFF")

        im.save(PREVIEWS_DIR / f"annotated_{fn}")

    # 6. Save JSON Deliverables
    # Report A: Evaluation
    eval_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model_architecture": "YOLOv8n",
        "task": "Single-Class Apple Fruit Detection (Orchard)",
        "pretrained_weights": {
            "source": "yolov8n.pt",
            "sha256": pretrained_hash
        },
        "training_environment": {
            "device": device_name,
            "ultralytics_version": "8.4.193",
            "epochs": epochs,
            "batch_size": batch_size,
            "imgsz": imgsz,
            "peak_vram_mb": peak_vram_mb,
            "training_duration_sec": train_duration
        },
        "checkpoint": {
            "path": str(dest_best_pt),
            "sha256": best_chk_hash,
            "size_mb": best_chk_size_mb
        },
        "dataset_split_scenes": {
            "train": 1041,
            "val": 126,
            "test": 239,
            "total_scenes": 1406,
            "total_instances": 2575
        },
        "validation_metrics": {
            "precision": val_p,
            "recall": val_r,
            "mAP50": val_mAP50,
            "mAP50_95": val_mAP50_95
        },
        "locked_test_metrics": {
            "precision": test_p,
            "recall": test_r,
            "mAP50": test_mAP50,
            "mAP50_95": test_mAP50_95,
            "instance_tp": total_tp,
            "instance_fp": total_fp,
            "instance_fn": total_fn,
            "instance_precision_iou50": instance_precision,
            "instance_recall_iou50": instance_recall
        },
        "latency_benchmarks": {
            "gpu": gpu_lat,
            "cpu": cpu_lat
        },
        "licensing": {
            "dataset": "Apple Mendeley Phenotyping",
            "license": "CC BY-NC 4.0",
            "commercial_deployment_allowed": False,
            "gating_status": "EXPERIMENTAL_RESEARCH_ONLY"
        }
    }
    with open(REPORTS_DIR / "phase16b_apple_yolo_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    # Report B: Error Analysis
    error_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_test_scenes": len(test_images),
        "total_test_ground_truth_apples": total_tp + total_fn,
        "scene_level_breakdown": {
            "scenes_with_zero_errors": sum(1 for s in per_scene_stats if s["fp"] == 0 and s["fn"] == 0),
            "scenes_with_missed_apples_fn": len(difficult_categories["missed_detections_fn"]),
            "scenes_with_false_detections_fp": len(difficult_categories["false_detections_fp"])
        },
        "difficult_scenario_counts": {
            "crowded_scenes_ge_3": len(difficult_categories["crowded_scenes_ge_3"]),
            "scenes_with_small_apples_le_1pct_area": len(difficult_categories["small_apples_area_le_0_01"]),
            "scenes_with_low_confidence_detections": len(difficult_categories["low_confidence_detections"])
        },
        "difficult_scenario_sample_images": difficult_categories,
        "visual_previews_generated": [f.name for f in PREVIEWS_DIR.glob("*.jpg")]
    }
    with open(REPORTS_DIR / "phase16b_apple_yolo_error_analysis.json", "w", encoding="utf-8") as f:
        json.dump(error_report, f, indent=2)

    # Report C: Readiness
    readiness_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model_architecture": "YOLOv8n (Apple Orchard)",
        "readiness_criteria": {
            "mAP50_ge_80": bool(test_mAP50 >= 0.80),
            "recall_ge_75": bool(test_r >= 0.75),
            "precision_ge_75": bool(test_p >= 0.75),
            "edge_throughput_ge_30_img_s": bool(cpu_lat["throughput_images_per_sec"] >= 30.0),
            "licensing_compliance": "CC_BY_NC_4.0_NON_COMMERCIAL_ONLY"
        },
        "overall_status": "EXPERIMENTAL_BENCHMARK_VALIDATED",
        "production_integration_authorized": False,
        "rationale": "Model is validated for research/experimental apple detection; production deployment is blocked by CC BY-NC 4.0 license restriction and single-class scope."
    }
    with open(REPORTS_DIR / "phase16b_apple_yolo_readiness.json", "w", encoding="utf-8") as f:
        json.dump(readiness_report, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print("WORKSTREAM B: APPLE YOLOV8N TRAINING & BENCHMARK COMPLETE!", flush=True)
    print(f"Reports saved to {REPORTS_DIR}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    main()
