"""
AgriChain AI — Phase 16B: Workstream C — Banana Ripeness Benchmark
=================================================================
Benchmarks 3 architectures on banana ripeness classification:
  1. ResNet18
  2. EfficientNet-B0
  3. MobileNetV3-Large

Dataset: ml/data/manifests/banana_ripeness/
Classes (4):
  0: Unripe
  1: Half_Ripe
  2: Ripe
  3: Overripe

Evaluates:
  - Macro F1
  - Per-class precision, recall, F1
  - Confusion matrix (Half_Ripe vs Unripe and Ripe vs Overripe)
  - Calibration error (ECE)
  - Inference latency
  - Model size and peak VRAM
  - Preserves existing baseline checkpoint ml/artifacts/best_banana_resnet18.pth
"""

import os
import sys
import json
import time
import copy
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "manifests" / "banana_ripeness"
EXP_ROOT = WORKSPACE_ROOT / "ml" / "experiments" / "phase16b" / "banana_ripeness"
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

CLASS_MAP = {
    "Unripe": 0,
    "Half_Ripe": 1,
    "Ripe": 2,
    "Overripe": 3
}

class BananaDataset(Dataset):
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
            
        label = rec.get("target")
        if label is None:
            label = CLASS_MAP[rec["label"]]
        return x, int(label), idx

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

def build_model(arch: str, num_classes: int = 4):
    if arch == "resnet18":
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        in_feat = model.fc.in_features
        model.fc = nn.Sequential(nn.Dropout(0.2), nn.Linear(in_feat, num_classes))
    elif arch == "efficientnet_b0":
        model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        in_feat = model.classifier[1].in_features
        model.classifier = nn.Sequential(nn.Dropout(0.2), nn.Linear(in_feat, num_classes))
    elif arch == "mobilenet_v3_large":
        model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        in_feat = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_feat, num_classes)
    else:
        raise ValueError(f"Unknown architecture: {arch}")
    return model

def compute_metrics(y_true, y_pred, num_classes=4):
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

    class_names = ["Unripe", "Half_Ripe", "Ripe", "Overripe"]
    return {
        "accuracy": acc,
        "macro_precision": float(np.mean(precisions)),
        "macro_recall": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "per_class": {
            class_names[c]: {"precision": precisions[c], "recall": recalls[c], "f1": f1s[c], "support": int(np.sum(cm[c, :]))}
            for c in range(num_classes)
        },
        "confusion_matrix": cm.tolist(),
        "key_boundary_confusions": {
            "Half_Ripe_as_Unripe": int(cm[1, 0]),
            "Unripe_as_Half_Ripe": int(cm[0, 1]),
            "Ripe_as_Overripe": int(cm[2, 3]),
            "Overripe_as_Ripe": int(cm[3, 2])
        }
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

def benchmark_latency(model, device, input_size=(1, 3, 224, 224), runs=300):
    model.eval()
    dummy = torch.randn(input_size, device=device)
    with torch.no_grad():
        for _ in range(30):
            _ = model(dummy)
    if device.type == "cuda":
        torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad():
        for _ in range(runs):
            _ = model(dummy)
    if device.type == "cuda":
        torch.cuda.synchronize()
    total_ms = (time.perf_counter() - start) * 1000.0
    return float(total_ms / runs)

def train_and_eval_banana(arch: str, train_records, val_records, test_records, device):
    print(f"\n" + "=" * 70)
    print(f"BANANA RIPENESS BENCHMARK: {arch.upper()}")
    print("=" * 70)

    set_seed(RANDOM_SEED)
    arch_dir = EXP_ROOT / arch
    arch_dir.mkdir(parents=True, exist_ok=True)

    train_tf, eval_tf = get_transforms()
    train_ds = BananaDataset(train_records, transform=train_tf)
    val_ds = BananaDataset(val_records, transform=eval_tf)
    test_ds = BananaDataset(test_records, transform=eval_tf)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False, num_workers=0, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0, pin_memory=True)

    model = build_model(arch, num_classes=4).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
    epochs = 10
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler('cuda')

    best_val_macro_f1 = 0.0
    best_weights = None
    best_ep = 0
    history = []

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()

    start_t = time.perf_counter()
    for ep in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for x, y, _ in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast('cuda'):
                logits = model(x)
                loss = criterion(logits, y)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * len(y)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += len(y)

        scheduler.step()
        train_loss /= total
        train_acc = correct / total

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_targets = []

        with torch.no_grad():
            for x, y, _ in val_loader:
                x, y = x.to(device), y.to(device)
                with torch.amp.autocast('cuda'):
                    logits = model(x)
                    loss = criterion(logits, y)
                val_loss += loss.item() * len(y)
                val_preds.extend(logits.argmax(dim=1).cpu().numpy())
                val_targets.extend(y.cpu().numpy())

        val_loss /= len(val_ds)
        val_metrics = compute_metrics(val_targets, val_preds, num_classes=4)
        val_macro_f1 = val_metrics["macro_f1"]

        ep_stats = {
            "epoch": ep,
            "train_loss": float(train_loss),
            "train_acc": float(train_acc),
            "val_loss": float(val_loss),
            "val_acc": float(val_metrics["accuracy"]),
            "val_macro_f1": float(val_macro_f1)
        }
        history.append(ep_stats)

        print(f"  Epoch {ep:2d}/{epochs} | Train Loss: {train_loss:.4f} Acc: {train_acc*100:.1f}% | Val Loss: {val_loss:.4f} Acc: {val_metrics['accuracy']*100:.1f}% F1: {val_macro_f1:.4f}")

        if val_macro_f1 > best_val_macro_f1:
            best_val_macro_f1 = val_macro_f1
            best_weights = copy.deepcopy(model.state_dict())
            best_ep = ep

    duration = time.perf_counter() - start_t
    peak_vram = torch.cuda.max_memory_allocated() / (1024 * 1024) if device.type == "cuda" else 0.0

    # Save best checkpoint
    model.load_state_dict(best_weights)
    chk_path = arch_dir / f"best_{arch}.pth"
    torch.save({
        "architecture": arch,
        "state_dict": model.state_dict(),
        "best_epoch": best_ep,
        "best_val_macro_f1": best_val_macro_f1,
        "class_to_idx": CLASS_MAP,
        "random_seed": RANDOM_SEED
    }, chk_path)
    chk_hash = compute_sha256(chk_path)
    chk_size_mb = chk_path.stat().st_size / (1024 * 1024)

    # Latency Benchmark
    latency_bs1 = benchmark_latency(model, device, input_size=(1, 3, 224, 224), runs=300)

    # Test Set Evaluation
    test_logits_all = []
    test_targets_all = []
    with torch.no_grad():
        for x, y, _ in test_loader:
            x = x.to(device)
            logits = model(x)
            test_logits_all.append(logits.cpu().numpy())
            test_targets_all.extend(y.numpy())

    test_logits_arr = np.concatenate(test_logits_all, axis=0)
    test_targets_arr = np.array(test_targets_all)
    test_probs = torch.softmax(torch.tensor(test_logits_arr), dim=1).numpy()
    test_preds = np.argmax(test_probs, axis=1)
    test_metrics = compute_metrics(test_targets_arr, test_preds, num_classes=4)
    test_ece = compute_ece(test_probs, test_targets_arr)

    print(f"\n  TEST RESULTS ({arch}):")
    print(f"    - Accuracy: {test_metrics['accuracy']*100:.2f}% | Macro F1: {test_metrics['macro_f1']:.4f}")
    print(f"    - Half_Ripe as Unripe: {test_metrics['key_boundary_confusions']['Half_Ripe_as_Unripe']}")
    print(f"    - Ripe as Overripe:     {test_metrics['key_boundary_confusions']['Ripe_as_Overripe']}")

    result = {
        "architecture": arch,
        "checkpoint_path": str(chk_path),
        "checkpoint_sha256": chk_hash,
        "checkpoint_size_mb": float(chk_size_mb),
        "peak_vram_mb": float(peak_vram),
        "training_duration_sec": float(duration),
        "best_epoch": best_ep,
        "best_val_macro_f1": float(best_val_macro_f1),
        "latency_ms_bs1": float(latency_bs1),
        "test_ece": float(test_ece),
        "test_metrics": test_metrics,
        "training_history": history
    }

    with open(arch_dir / "banana_benchmark_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result

def main():
    print("=" * 80)
    print("AGRICHAIN AI — PHASE 16B: WORKSTREAM C — BANANA RIPENESS BENCHMARK")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    with open(MANIFESTS_DIR / "train.json", "r", encoding="utf-8") as f:
        train_records = json.load(f)
    with open(MANIFESTS_DIR / "val.json", "r", encoding="utf-8") as f:
        val_records = json.load(f)
    with open(MANIFESTS_DIR / "test.json", "r", encoding="utf-8") as f:
        test_records = json.load(f)

    print(f"Banana Manifests Loaded: Train={len(train_records)}, Val={len(val_records)}, Test={len(test_records)}")

    architectures = ["resnet18", "efficientnet_b0", "mobilenet_v3_large"]
    results = {}
    for arch in architectures:
        res = train_and_eval_banana(arch, train_records, val_records, test_records, device)
        results[arch] = res

    out_file = REPORTS_DIR / "phase16b_banana_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "random_seed": RANDOM_SEED,
            "classes": ["Unripe", "Half_Ripe", "Ripe", "Overripe"],
            "benchmarks": results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("WORKSTREAM C BENCHMARK COMPLETE!")
    print(f"Results saved to: {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()

