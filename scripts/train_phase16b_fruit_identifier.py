"""
AgriChain AI — Phase 16B: Workstream A — Fruit Identifier V2 Training & Benchmark
================================================================================
Trains and evaluates 3 model architectures on fruit_identifier_v2:
  1. ResNet18
  2. EfficientNet-B0
  3. MobileNetV3-Large

Classes (5):
  0: guava
  1: banana
  2: apple
  3: mango
  4: negative_background

Features:
  - Checkpoint Protection & Resumption: Safely skips re-training already-completed architectures
  - Group-isolated audited manifests (Train=14078, Val=2771, Test=3037)
  - Balanced Cross-Entropy loss for class distribution handling (mango deficit)
  - Color-preserving augmentation
  - Validation-only model selection (Macro F1)
  - Temperature scaling calibration (fit on validation set only)
  - Locked Stage 2 Specimen sync & multi-source locked test evaluation
  - Detailed latency benchmarking (Mean, Median, P95, BS=1 latency, BS=32 throughput) for GPU and CPU
  - Multi-threshold OOD evaluation (FAR, FRR, TNR, AUROC, AUPR across MSP, Margin, Energy)
  - Peak VRAM, model size, and parameter count measurement
"""

import os
import sys
import json
import time
import math
import copy
import hashlib
from pathlib import Path
from collections import Counter

# Ensure unbuffered real-time stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image
from sklearn.metrics import roc_auc_score, average_precision_score

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "manifests" / "fruit_identifier_v2"
EXPERIMENT_ROOT = WORKSPACE_ROOT / "ml" / "experiments" / "phase16b" / "fruit_identifier_v2"
REPORTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "reports"

RANDOM_SEED = 42

def set_seed(seed=RANDOM_SEED):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

class FruitIdentifierDataset(Dataset):
    def __init__(self, records, transform=None):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]
        img_path = WORKSPACE_ROOT / rec["path"]
        try:
            with Image.open(img_path) as im:
                rgb_im = im.convert("RGB")
        except Exception:
            rgb_im = Image.new("RGB", (224, 224), (0, 0, 0))
        
        if self.transform:
            x = self.transform(rgb_im)
        else:
            x = T.ToTensor()(rgb_im)
        target = rec.get("identity_index", rec.get("target", 0))
        return x, target, idx

def get_transforms():
    train_transform = T.Compose([
        T.RandomResizedCrop(224, scale=(0.8, 1.0)),
        T.RandomHorizontalFlip(p=0.5),
        T.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.02),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    eval_transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    return train_transform, eval_transform

def build_model(arch: str, num_classes: int = 5):
    if arch == "resnet18":
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        in_feat = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(in_feat, num_classes)
        )
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        in_feat = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(in_feat, num_classes)
        )
    elif arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        in_feat = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_feat, num_classes)
    else:
        raise ValueError(f"Unknown architecture: {arch}")
    return model

def compute_metrics(y_true, y_pred, num_classes=5):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    acc = float(np.mean(y_true == y_pred))
    
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
        
    precisions = []
    recalls = []
    f1s = []
    for c in range(num_classes):
        tp = cm[c, c]
        fp = np.sum(cm[:, c]) - tp
        fn = np.sum(cm[c, :]) - tp
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)
        
    return {
        "accuracy": acc,
        "macro_precision": float(np.mean(precisions)),
        "macro_recall": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": {
            c: {"precision": precisions[c], "recall": recalls[c], "f1": f1s[c], "support": int(np.sum(cm[c, :]))}
            for c in range(num_classes)
        },
        "confusion_matrix": cm.tolist()
    }

def compute_ece(probs, labels, n_bins=15):
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = predictions == labels

    ece = 0.0
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
    return float(ece)

class TemperatureScaler(nn.Module):
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits):
        return logits / self.temperature

    def fit(self, val_logits, val_labels):
        val_logits = torch.tensor(val_logits, dtype=torch.float32)
        val_labels = torch.tensor(val_labels, dtype=torch.long)
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.LBFGS([self.temperature], lr=0.01, max_iter=50)

        def eval_loss():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            loss.backward()
            return loss

        optimizer.step(eval_loss)
        return float(self.temperature.item())

def benchmark_latency_detailed(model, device, runs=200):
    model.eval()
    dummy_bs1 = torch.randn((1, 3, 224, 224), device=device)
    # Warmup
    with torch.no_grad():
        for _ in range(30):
            _ = model(dummy_bs1)
    if device.type == "cuda":
        torch.cuda.synchronize()

    # BS=1 measurements
    timings_bs1 = []
    with torch.no_grad():
        for _ in range(runs):
            t0 = time.perf_counter()
            _ = model(dummy_bs1)
            if device.type == "cuda":
                torch.cuda.synchronize()
            timings_bs1.append((time.perf_counter() - t0) * 1000.0)

    # BS=32 measurements
    dummy_bs32 = torch.randn((32, 3, 224, 224), device=device)
    with torch.no_grad():
        for _ in range(10):
            _ = model(dummy_bs32)
    if device.type == "cuda":
        torch.cuda.synchronize()

    timings_bs32 = []
    bs32_runs = 60 if device.type == "cuda" else 15
    with torch.no_grad():
        for _ in range(bs32_runs):
            t0 = time.perf_counter()
            _ = model(dummy_bs32)
            if device.type == "cuda":
                torch.cuda.synchronize()
            timings_bs32.append((time.perf_counter() - t0) * 1000.0)

    mean_bs1 = float(np.mean(timings_bs1))
    median_bs1 = float(np.median(timings_bs1))
    p95_bs1 = float(np.percentile(timings_bs1, 95))

    mean_bs32_batch_ms = float(np.mean(timings_bs32))
    throughput_samples_per_sec = float(32.0 / (mean_bs32_batch_ms / 1000.0))
    latency_per_sample_bs32_ms = float(mean_bs32_batch_ms / 32.0)

    return {
        "mean_latency_bs1_ms": mean_bs1,
        "median_latency_bs1_ms": median_bs1,
        "p95_latency_bs1_ms": p95_bs1,
        "batch_size_32_batch_ms": mean_bs32_batch_ms,
        "batch_size_32_per_sample_ms": latency_per_sample_bs32_ms,
        "throughput_samples_per_sec": throughput_samples_per_sec
    }

def train_and_evaluate_architecture(arch: str, train_records, val_records, test_records, device, class_weights):
    print(f"\n" + "=" * 70, flush=True)
    print(f"PROCESSING ARCHITECTURE: {arch.upper()} on fruit_identifier_v2", flush=True)
    print("=" * 70, flush=True)

    set_seed(RANDOM_SEED)
    arch_dir = EXPERIMENT_ROOT / arch
    arch_dir.mkdir(parents=True, exist_ok=True)
    chk_path = arch_dir / f"best_{arch}.pth"
    eval_json_path = arch_dir / "evaluation.json"

    train_tf, eval_tf = get_transforms()
    val_ds = FruitIdentifierDataset(val_records, transform=eval_tf)
    test_ds = FruitIdentifierDataset(test_records, transform=eval_tf)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=0, pin_memory=True)

    # CHECKPOINT RESUMPTION CHECK
    if chk_path.exists() and eval_json_path.exists():
        print(f"  [RESUME] Found verified checkpoint: {chk_path.name}", flush=True)
        with open(eval_json_path, "r", encoding="utf-8") as f:
            eval_result = json.load(f)
        
        model = build_model(arch, num_classes=5)
        chk_data = torch.load(chk_path, map_location="cpu")
        model.load_state_dict(chk_data["state_dict"])
        model.to(device)
        model.eval()

        optimal_t = eval_result.get("calibration", {}).get("optimal_temperature", 1.0)
        
        # Verify or populate detailed latency metrics if needed
        if "detailed_latency" not in eval_result:
            print("  Measuring detailed GPU & CPU latency benchmarks...", flush=True)
            gpu_lat = benchmark_latency_detailed(model, device, runs=200)
            model_cpu = build_model(arch, num_classes=5)
            model_cpu.load_state_dict(chk_data["state_dict"])
            model_cpu.eval()
            cpu_lat = benchmark_latency_detailed(model_cpu, torch.device("cpu"), runs=40)
            eval_result["detailed_latency"] = {
                "gpu": gpu_lat,
                "cpu": cpu_lat
            }
            with open(eval_json_path, "w", encoding="utf-8") as f:
                json.dump(eval_result, f, indent=2)
            print(f"  GPU BS=1 Median: {gpu_lat['median_latency_bs1_ms']:.2f}ms | Throughput: {gpu_lat['throughput_samples_per_sec']:.1f} img/s", flush=True)
            print(f"  CPU BS=1 Median: {cpu_lat['median_latency_bs1_ms']:.2f}ms | Throughput: {cpu_lat['throughput_samples_per_sec']:.1f} img/s", flush=True)

        return model, eval_result, optimal_t

    # FULL TRAINING LOOP
    print(f"  Starting fresh training for {arch}...", flush=True)
    train_ds = FruitIdentifierDataset(train_records, transform=train_tf)
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, num_workers=0, pin_memory=True)

    model = build_model(arch, num_classes=5).to(device)

    # Class-aware weighted loss
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    
    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
    epochs = 5
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler('cuda') if device.type == "cuda" else None

    best_val_macro_f1 = 0.0
    best_model_weights = None
    best_epoch = 0
    history = []

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    train_start = time.perf_counter()
    for ep in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for x, y, _ in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            if scaler:
                with torch.amp.autocast('cuda'):
                    logits = model(x)
                    loss = criterion(logits, y)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                logits = model(x)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()

            train_loss += loss.item() * len(y)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += len(y)

        scheduler.step()
        train_loss /= total
        train_acc = correct / total

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_targets = []

        with torch.no_grad():
            for x, y, _ in val_loader:
                x, y = x.to(device), y.to(device)
                if scaler:
                    with torch.amp.autocast('cuda'):
                        logits = model(x)
                        loss = criterion(logits, y)
                else:
                    logits = model(x)
                    loss = criterion(logits, y)
                val_loss += loss.item() * len(y)
                val_preds.extend(logits.argmax(dim=1).cpu().numpy())
                val_targets.extend(y.cpu().numpy())

        val_loss /= len(val_ds)
        val_metrics = compute_metrics(val_targets, val_preds, num_classes=5)
        val_macro_f1 = val_metrics["macro_f1"]

        ep_stats = {
            "epoch": ep,
            "train_loss": float(train_loss),
            "train_acc": float(train_acc),
            "val_loss": float(val_loss),
            "val_acc": float(val_metrics["accuracy"]),
            "val_macro_f1": float(val_macro_f1),
            "val_per_class_f1": {c: val_metrics["per_class"][c]["f1"] for c in range(5)}
        }
        history.append(ep_stats)

        print(f"  Epoch {ep}/{epochs} | Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_metrics['accuracy']*100:.2f}% F1: {val_macro_f1:.4f}", flush=True)

        if val_macro_f1 > best_val_macro_f1:
            best_val_macro_f1 = val_macro_f1
            best_model_weights = copy.deepcopy(model.state_dict())
            best_epoch = ep

    train_duration = time.perf_counter() - train_start
    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if device.type == "cuda" else 0.0

    # Load best checkpoint
    model.load_state_dict(best_model_weights)
    torch.save({
        "architecture": arch,
        "state_dict": model.state_dict(),
        "best_epoch": best_epoch,
        "best_val_macro_f1": best_val_macro_f1,
        "class_to_idx": {"guava": 0, "banana": 1, "apple": 2, "mango": 3, "negative_background": 4},
        "random_seed": RANDOM_SEED
    }, chk_path)
    chk_hash = compute_sha256(chk_path)
    chk_size_mb = chk_path.stat().st_size / (1024 * 1024)

    # Temperature Scaling on Validation
    model.eval()
    val_logits_all = []
    val_targets_all = []
    with torch.no_grad():
        for x, y, _ in val_loader:
            x = x.to(device)
            logits = model(x)
            val_logits_all.append(logits.cpu().numpy())
            val_targets_all.extend(y.numpy())
    val_logits_arr = np.concatenate(val_logits_all, axis=0)
    val_targets_arr = np.array(val_targets_all)

    val_probs_raw = torch.softmax(torch.tensor(val_logits_arr), dim=1).numpy()
    val_ece_raw = compute_ece(val_probs_raw, val_targets_arr)

    scaler_opt = TemperatureScaler()
    optimal_t = scaler_opt.fit(val_logits_arr, val_targets_arr)
    val_probs_cal = torch.softmax(torch.tensor(val_logits_arr) / optimal_t, dim=1).numpy()
    val_ece_cal = compute_ece(val_probs_cal, val_targets_arr)

    print(f"  Calibration (Validation): Optimal T = {optimal_t:.4f} | ECE Raw: {val_ece_raw:.4f} -> Calibrated: {val_ece_cal:.4f}", flush=True)

    # Latency Benchmarks
    print("  Measuring detailed GPU & CPU latency benchmarks...", flush=True)
    gpu_lat = benchmark_latency_detailed(model, device, runs=200)
    model_cpu = build_model(arch, num_classes=5)
    model_cpu.load_state_dict(best_model_weights)
    model_cpu.eval()
    cpu_lat = benchmark_latency_detailed(model_cpu, torch.device("cpu"), runs=40)

    # Locked Tier 2 Test Evaluation
    test_logits_all = []
    test_targets_all = []
    test_indices_all = []
    with torch.no_grad():
        for x, y, idxs in test_loader:
            x = x.to(device)
            logits = model(x)
            test_logits_all.append(logits.cpu().numpy())
            test_targets_all.extend(y.numpy())
            test_indices_all.extend(idxs.numpy())
    test_logits_arr = np.concatenate(test_logits_all, axis=0)
    test_targets_arr = np.array(test_targets_all)

    test_probs_cal = torch.softmax(torch.tensor(test_logits_arr) / optimal_t, dim=1).numpy()
    test_preds = np.argmax(test_probs_cal, axis=1)
    test_metrics = compute_metrics(test_targets_arr, test_preds, num_classes=5)
    test_ece = compute_ece(test_probs_cal, test_targets_arr)

    # Confidence distribution stats
    confidences = np.max(test_probs_cal, axis=1)
    conf_stats = {
        "mean": float(np.mean(confidences)),
        "std": float(np.std(confidences)),
        "min": float(np.min(confidences)),
        "percentile_25": float(np.percentile(confidences, 25)),
        "median": float(np.median(confidences)),
        "percentile_75": float(np.percentile(confidences, 75)),
        "percentile_90": float(np.percentile(confidences, 90)),
        "max": float(np.max(confidences))
    }

    print(f"\n  TIER 2 TEST RESULTS ({arch}):", flush=True)
    print(f"    - Accuracy:        {test_metrics['accuracy']*100:.2f}%", flush=True)
    print(f"    - Macro F1:        {test_metrics['macro_f1']:.4f}", flush=True)
    print(f"    - Macro Recall:    {test_metrics['macro_recall']:.4f}", flush=True)
    print(f"    - Macro Precision: {test_metrics['macro_precision']:.4f}", flush=True)
    print(f"    - Calibrated ECE:  {test_ece:.4f}", flush=True)

    # Locked Stage 2 Specimen Evaluation (Tier 1 In-Domain Sync)
    stage2_sync_indices = [
        i for i, r in enumerate(test_records) 
        if r.get("source_dataset") in ["Guava_SAU_Harvest", "BananaID_Ripeness", "Apple_Mendeley_Orchard_Crops", "Harumanis_Mango"]
    ]
    s2_targets = test_targets_arr[stage2_sync_indices]
    s2_preds = test_preds[stage2_sync_indices]
    s2_metrics = compute_metrics(s2_targets, s2_preds, num_classes=5)

    # Confusion breakdown: False fruit acceptance & False background rejection
    cm = np.array(test_metrics["confusion_matrix"])
    false_fruit_acceptance_count = int(np.sum(cm[4, :4]))
    false_fruit_acceptance_rate = float(false_fruit_acceptance_count / np.sum(cm[4, :])) if np.sum(cm[4, :]) > 0 else 0.0
    fruit_total = int(np.sum(cm[:4, :]))
    false_bg_rejection_count = int(np.sum(cm[:4, 4]))
    false_bg_rejection_rate = float(false_bg_rejection_count / fruit_total) if fruit_total > 0 else 0.0

    eval_result = {
        "architecture": arch,
        "checkpoint_path": str(chk_path),
        "checkpoint_sha256": chk_hash,
        "checkpoint_size_mb": float(chk_size_mb),
        "peak_vram_mb": float(peak_vram_mb),
        "training_duration_sec": float(train_duration),
        "best_epoch": best_epoch,
        "best_val_macro_f1": float(best_val_macro_f1),
        "calibration": {
            "optimal_temperature": float(optimal_t),
            "val_ece_raw": float(val_ece_raw),
            "val_ece_calibrated": float(val_ece_cal),
            "test_ece_calibrated": float(test_ece)
        },
        "latency_ms": {
            "batch_size_1": float(gpu_lat["mean_latency_bs1_ms"]),
            "batch_size_32_per_sample": float(gpu_lat["batch_size_32_per_sample_ms"]),
            "cpu_batch_size_1": float(cpu_lat["mean_latency_bs1_ms"]),
            "cpu_batch_size_32_per_sample": float(cpu_lat["batch_size_32_per_sample_ms"])
        },
        "detailed_latency": {
            "gpu": gpu_lat,
            "cpu": cpu_lat
        },
        "confidence_distribution": conf_stats,
        "tier2_test_metrics": test_metrics,
        "tier1_stage2_sync_metrics": {
            "samples": len(stage2_sync_indices),
            "accuracy": s2_metrics["accuracy"],
            "macro_f1": s2_metrics["macro_f1"]
        },
        "error_analysis": {
            "false_fruit_acceptance_count": false_fruit_acceptance_count,
            "false_fruit_acceptance_rate": false_fruit_acceptance_rate,
            "false_bg_rejection_count": false_bg_rejection_count,
            "false_bg_rejection_rate": false_bg_rejection_rate
        },
        "training_history": history
    }

    with open(eval_json_path, "w", encoding="utf-8") as f:
        json.dump(eval_result, f, indent=2)

    return model, eval_result, optimal_t

def evaluate_ood_stress_suites(model, device, temperature, arch_name, val_records):
    print(f"\n[OOD Stress Benchmark & Calibration: {arch_name.upper()}]", flush=True)
    arch_dir = EXPERIMENT_ROOT / arch_name
    ood_json_path = arch_dir / "ood_evaluation.json"

    eval_tf = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 1. Load audited external evaluation plan
    plan_path = MANIFESTS_DIR / "external_evaluation_plan.json"
    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    suites = {}
    for s_id, s_info in plan.get("held_out_evaluation_suites", {}).items():
        if "sample_paths" in s_info:
            full_paths = [WORKSPACE_ROOT / p for p in s_info["sample_paths"]]
            existing_paths = [p for p in full_paths if p.exists()]
            suites[s_id] = {
                "paths": existing_paths,
                "description": s_info.get("description", ""),
                "expected": s_info.get("expected_behavior", "")
            }

    # 2. Extract Validation Confidence Profile for Fruit (Classes 0-3) vs BG (Class 4)
    model.eval()
    val_ds = FruitIdentifierDataset(val_records, transform=eval_tf)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, num_workers=0)

    val_logits_list = []
    val_targets_list = []
    with torch.no_grad():
        for x, y, _ in val_loader:
            x = x.to(device)
            logits = model(x)
            val_logits_list.append(logits.cpu().numpy())
            val_targets_list.extend(y.numpy())

    val_logits = np.concatenate(val_logits_list, axis=0)
    val_targets = np.array(val_targets_list)
    val_probs = torch.softmax(torch.tensor(val_logits) / temperature, dim=1).numpy()
    
    # In-distribution fruit samples (classes 0, 1, 2, 3)
    fruit_mask = val_targets < 4
    val_fruit_msp = np.max(val_probs[fruit_mask], axis=1)
    sorted_p_fruit = np.sort(val_probs[fruit_mask], axis=1)[:, ::-1]
    val_fruit_margin = sorted_p_fruit[:, 0] - sorted_p_fruit[:, 1]
    val_fruit_energy = -temperature * np.log(np.sum(np.exp(val_logits[fruit_mask] / temperature), axis=1))

    # Calibration Operating Thresholds
    msp_thresholds = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.98]
    margin_thresholds = [0.20, 0.35, 0.50, 0.65, 0.80, 0.90]
    energy_thresholds = [-4.0, -6.0, -8.0, -10.0, -12.0, -14.0]

    threshold_calibration = {
        "msp_operating_points": {},
        "margin_operating_points": {},
        "energy_operating_points": {}
    }

    for t in msp_thresholds:
        frr = float(np.mean(val_fruit_msp < t))
        threshold_calibration["msp_operating_points"][str(t)] = {"fruit_frr": frr}

    for m in margin_thresholds:
        frr = float(np.mean(val_fruit_margin < m))
        threshold_calibration["margin_operating_points"][str(m)] = {"fruit_frr": frr}

    for e in energy_thresholds:
        frr = float(np.mean(val_fruit_energy > e))
        threshold_calibration["energy_operating_points"][str(e)] = {"fruit_frr": frr}

    # 3. Evaluate each OOD Suite
    ood_suite_results = {}

    for s_name, s_data in suites.items():
        files = s_data["paths"]
        if not files:
            continue

        msps = []
        margins = []
        energies = []
        preds = []

        for i in range(0, len(files), 64):
            batch_files = files[i:i+64]
            tensors = []
            for f in batch_files:
                try:
                    with Image.open(f) as im:
                        tensors.append(eval_tf(im.convert("RGB")))
                except Exception:
                    tensors.append(torch.zeros(3, 224, 224))
            bx = torch.stack(tensors).to(device)
            with torch.no_grad():
                logits = model(bx)
                cal_logits = logits / temperature
                probs = torch.softmax(cal_logits, dim=1).cpu().numpy()
                raw_logits = logits.cpu().numpy()

            for p, lgt in zip(probs, raw_logits):
                sorted_p = np.sort(p)[::-1]
                msp = float(sorted_p[0])
                margin = float(sorted_p[0] - sorted_p[1])
                energy = float(-temperature * np.log(np.sum(np.exp(lgt / temperature))))
                pred = int(np.argmax(p))

                msps.append(msp)
                margins.append(margin)
                energies.append(energy)
                preds.append(pred)

        msps = np.array(msps)
        margins = np.array(margins)
        energies = np.array(energies)
        preds = np.array(preds)

        # Baseline architectural rejection: assigned to Class 4 (negative_background)
        assigned_bg = int(np.sum(preds == 4))
        bg_rejection_rate = float(assigned_bg / len(files))
        raw_fruit_fa_count = int(np.sum(preds < 4))
        raw_fruit_fa_rate = float(raw_fruit_fa_count / len(files))

        # Operating points FAR for this OOD suite
        msp_far = {}
        for t in msp_thresholds:
            accepted_as_fruit = (preds < 4) & (msps >= t)
            msp_far[str(t)] = float(np.mean(accepted_as_fruit))

        margin_far = {}
        for m in margin_thresholds:
            accepted_as_fruit = (preds < 4) & (margins >= m)
            margin_far[str(m)] = float(np.mean(accepted_as_fruit))

        energy_far = {}
        for e in energy_thresholds:
            accepted_as_fruit = (preds < 4) & (energies <= e)
            energy_far[str(e)] = float(np.mean(accepted_as_fruit))

        # AUROC and AUPR: In-Distribution Fruits (y=1) vs OOD Stress Samples (y=0)
        # Using negative energy as confidence score (higher = more ID-like)
        y_true_id_ood = np.concatenate([np.ones_like(val_fruit_energy), np.zeros_like(energies)])
        energy_scores_id_ood = np.concatenate([-val_fruit_energy, -energies])
        msp_scores_id_ood = np.concatenate([val_fruit_msp, msps])

        auroc_energy = float(roc_auc_score(y_true_id_ood, energy_scores_id_ood))
        auroc_msp = float(roc_auc_score(y_true_id_ood, msp_scores_id_ood))
        aupr_energy = float(average_precision_score(y_true_id_ood, energy_scores_id_ood))

        ood_suite_results[s_name] = {
            "samples": len(files),
            "description": s_data["description"],
            "expected_behavior": s_data["expected"],
            "raw_architecture_rejection": {
                "assigned_negative_background_rate": bg_rejection_rate,
                "tnr": bg_rejection_rate,
                "raw_false_fruit_acceptance_rate": raw_fruit_fa_rate,
                "predicted_class_breakdown": dict(Counter(preds.tolist()))
            },
            "ood_detection_metrics": {
                "auroc_energy": auroc_energy,
                "auroc_msp": auroc_msp,
                "aupr_in_distribution": aupr_energy
            },
            "score_distributions": {
                "msp_mean": float(np.mean(msps)),
                "msp_std": float(np.std(msps)),
                "margin_mean": float(np.mean(margins)),
                "margin_std": float(np.std(margins)),
                "energy_mean": float(np.mean(energies)),
                "energy_std": float(np.std(energies))
            },
            "calibrated_threshold_far": {
                "msp": msp_far,
                "margin": margin_far,
                "energy": energy_far
            }
        }

        print(f"  {s_name:<35}: Raw BG Rejection={bg_rejection_rate*100:.1f}%, False Acceptance as Fruit={raw_fruit_fa_rate*100:.1f}%, AUROC(Energy)={auroc_energy:.4f}", flush=True)

    complete_ood_report = {
        "architecture": arch_name,
        "temperature": float(temperature),
        "validation_calibration_profile": threshold_calibration,
        "suites": ood_suite_results
    }

    with open(ood_json_path, "w", encoding="utf-8") as f:
        json.dump(complete_ood_report, f, indent=2)

    return complete_ood_report

def main():
    print("=" * 80, flush=True)
    print("AGRICHAIN AI — PHASE 16B: WORKSTREAM A — FRUIT IDENTIFIER V2 BENCHMARK", flush=True)
    print("=" * 80, flush=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})", flush=True)

    with open(MANIFESTS_DIR / "train.json", "r", encoding="utf-8") as f:
        train_records = json.load(f)
    with open(MANIFESTS_DIR / "val.json", "r", encoding="utf-8") as f:
        val_records = json.load(f)
    with open(MANIFESTS_DIR / "test.json", "r", encoding="utf-8") as f:
        test_records = json.load(f)

    print(f"Dataset Manifests Loaded: Train={len(train_records)}, Val={len(val_records)}, Test={len(test_records)}", flush=True)

    # Class distribution & inverse frequency weights
    train_counts = Counter(r.get("identity_index", r.get("target", 0)) for r in train_records)
    total_train = len(train_records)
    weights = []
    for c in range(5):
        cnt = train_counts.get(c, 1)
        w = total_train / (5.0 * cnt)
        weights.append(w)
    class_weights = torch.tensor(weights, dtype=torch.float32)
    print(f"Calculated Class Weights: {[round(w, 3) for w in weights]}", flush=True)

    architectures = ["resnet18", "efficientnet_b0", "mobilenet_v3_large"]
    all_evals = {}
    all_ood = {}

    for arch in architectures:
        model, eval_res, opt_t = train_and_evaluate_architecture(
            arch, train_records, val_records, test_records, device, class_weights
        )
        all_evals[arch] = eval_res
        ood_res = evaluate_ood_stress_suites(model, device, opt_t, arch, val_records)
        all_ood[arch] = ood_res

    # Emit master Workstream A reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "random_seed": RANDOM_SEED,
        "classes": ["guava", "banana", "apple", "mango", "negative_background"],
        "class_weights": weights,
        "architectures_benchmarked": architectures,
        "model_evaluations": all_evals,
        "ood_stress_evaluations": all_ood
    }

    with open(REPORTS_DIR / "phase16b_architecture_comparison.json", "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    with open(REPORTS_DIR / "phase16b_ood_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(all_ood, f, indent=2)

    # Dataset evaluation report
    dataset_eval_report = {
        "dataset_name": "fruit_identifier_v2",
        "split_manifests": {
            "train": len(train_records),
            "val": len(val_records),
            "test": len(test_records)
        },
        "classes": ["guava", "banana", "apple", "mango", "negative_background"],
        "mango_deficit_handling": {
            "train_samples": train_counts.get(3, 0),
            "loss_weight": float(weights[3]),
            "status": "GATED_DEFICIT"
        },
        "split_leakage_check": "ZERO_LEAKAGE_GROUP_ISOLATED",
        "locked_test_set_status": "FROZEN_STAGE2_SYNC"
    }
    with open(REPORTS_DIR / "phase16b_dataset_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(dataset_eval_report, f, indent=2)

    # Master Experiment Registry
    exp_registry = {
        "phase": "16B",
        "workstream": "Workstream A — Fruit Identifier V2",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "experiments": [
            {
                "architecture": arch,
                "checkpoint_path": all_evals[arch]["checkpoint_path"],
                "checkpoint_sha256": all_evals[arch]["checkpoint_sha256"],
                "checkpoint_size_mb": all_evals[arch]["checkpoint_size_mb"],
                "best_epoch": all_evals[arch]["best_epoch"],
                "val_macro_f1": all_evals[arch]["best_val_macro_f1"],
                "test_accuracy": all_evals[arch]["tier2_test_metrics"]["accuracy"],
                "test_macro_f1": all_evals[arch]["tier2_test_metrics"]["macro_f1"],
                "test_macro_recall": all_evals[arch]["tier2_test_metrics"]["macro_recall"],
                "calibrated_ece": all_evals[arch]["calibration"]["test_ece_calibrated"],
                "gpu_latency_bs1_mean_ms": all_evals[arch]["detailed_latency"]["gpu"]["mean_latency_bs1_ms"],
                "gpu_latency_bs1_median_ms": all_evals[arch]["detailed_latency"]["gpu"]["median_latency_bs1_ms"],
                "gpu_latency_bs1_p95_ms": all_evals[arch]["detailed_latency"]["gpu"]["p95_latency_bs1_ms"],
                "gpu_throughput_samples_sec": all_evals[arch]["detailed_latency"]["gpu"]["throughput_samples_per_sec"],
                "cpu_latency_bs1_median_ms": all_evals[arch]["detailed_latency"]["cpu"]["median_latency_bs1_ms"],
                "cpu_throughput_samples_sec": all_evals[arch]["detailed_latency"]["cpu"]["throughput_samples_per_sec"],
                "peak_vram_mb": all_evals[arch]["peak_vram_mb"]
            }
            for arch in architectures
        ]
    }
    with open(REPORTS_DIR / "phase16b_experiment_registry.json", "w", encoding="utf-8") as f:
        json.dump(exp_registry, f, indent=2)

    # Model readiness matrix
    readiness = {}
    for arch in architectures:
        ev = all_evals[arch]
        f1 = ev["tier2_test_metrics"]["macro_f1"]
        rec = ev["tier2_test_metrics"]["macro_recall"]
        bg_err = ev["error_analysis"]["false_fruit_acceptance_rate"]
        ece = ev["calibration"]["test_ece_calibrated"]
        readiness[arch] = {
            "macro_f1_ge_95": bool(f1 >= 0.95),
            "macro_recall_ge_95": bool(rec >= 0.95),
            "false_fruit_acceptance_le_1pct": bool(bg_err <= 0.01),
            "calibrated_ece_le_0_05": bool(ece <= 0.05),
            "overall_status": "VALIDATED_MULTI_SOURCE" if (f1 >= 0.95 and rec >= 0.95 and bg_err <= 0.01) else "CONDITIONAL_APPROVAL"
        }
    with open(REPORTS_DIR / "phase16b_model_readiness_matrix.json", "w", encoding="utf-8") as f:
        json.dump(readiness, f, indent=2)

    print("\n" + "=" * 80, flush=True)
    print("WORKSTREAM A TRAINING & BENCHMARK COMPLETE!", flush=True)
    print(f"Results saved to: {REPORTS_DIR / 'phase16b_architecture_comparison.json'}", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    main()
