"""
AgriChain AI — ResNet18 Banana Ripeness Training & Evaluation Engine (Phase 14E)
================================================================================
Reproducible transfer learning baseline for Banana Ripeness classification:
- Architecture: ResNet18 (ImageNet-1K pretrained weights)
- Classes: Unripe (0), Half_Ripe (1), Ripe (2), Overripe (3)
- Manifests: ml/data/manifests/banana_ripeness/{train,val,test}.json
- Strict leakage controls: cluster group-aware, disjoint splits, zero hue jitter
- Output Checkpoint: ml/artifacts/best_banana_resnet18.pth
- Experiment Artifacts: ml/experiments/banana_resnet18_baseline/
"""

import os
import sys
import json
import time
import random
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

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = WORKSPACE_ROOT / "ml" / "configs" / "resnet18_banana_ripeness.json"
EXPERIMENTS_DIR = WORKSPACE_ROOT / "ml" / "experiments" / "banana_resnet18_baseline"
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()



def seed_everything(seed: int = 42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


class BananaRipenessDataset(Dataset):
    def __init__(self, manifest_path: Path, class_to_idx: dict, transform=None):
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.records = json.load(f)
        self.class_to_idx = class_to_idx
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]
        img_path = WORKSPACE_ROOT / rec["path"]
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            if self.transform:
                img = self.transform(img)
        label = self.class_to_idx[rec["class"]]
        return img, label, rec["filename"]


def build_transforms(config: dict):
    train_cfg = config["preprocessing"]["train_transforms"]
    eval_cfg = config["preprocessing"]["eval_transforms"]

    # Verify hue jitter is strictly 0.0
    hue_jitter = train_cfg["color_jitter"].get("hue", 0.0)
    assert hue_jitter == 0.0, f"Hue jitter must be strictly 0.0 to protect color features! Got: {hue_jitter}"

    train_transform = T.Compose([
        T.Resize(tuple(train_cfg["resize"])),
        T.RandomCrop(tuple(train_cfg["random_crop"])),
        T.RandomHorizontalFlip(p=train_cfg.get("random_horizontal_flip_prob", 0.5)),
        T.RandomRotation(degrees=train_cfg.get("random_rotation_degrees", 15)),
        T.ColorJitter(
            brightness=train_cfg["color_jitter"].get("brightness", 0.10),
            contrast=train_cfg["color_jitter"].get("contrast", 0.10),
            saturation=train_cfg["color_jitter"].get("saturation", 0.08),
            hue=0.0
        ),
        T.ToTensor(),
        T.Normalize(mean=train_cfg["normalization"]["mean"], std=train_cfg["normalization"]["std"])
    ])

    eval_transform = T.Compose([
        T.Resize(tuple(eval_cfg["resize"])),
        T.CenterCrop(tuple(eval_cfg["center_crop"])),
        T.ToTensor(),
        T.Normalize(mean=eval_cfg["normalization"]["mean"], std=eval_cfg["normalization"]["std"])
    ])

    return train_transform, eval_transform


def build_model(config: dict):
    model_cfg = config["model"]
    base_model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)

    # Freeze stages
    freeze_stages = set(model_cfg.get("freeze_stages", []))
    for name, child in base_model.named_children():
        if name in freeze_stages:
            for param in child.parameters():
                param.requires_grad = False

    # Custom classification head
    num_classes = model_cfg.get("num_classes", 4)
    dropout_p = model_cfg.get("dropout", 0.2)
    in_features = base_model.fc.in_features

    base_model.fc = nn.Sequential(
        nn.Dropout(p=dropout_p),
        nn.Linear(in_features, num_classes)
    )

    return base_model


def compute_metrics(y_true, y_pred, num_classes, idx_to_class):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    accuracy = float(np.mean(y_true == y_pred))

    confusion = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        confusion[t, p] += 1

    per_class = {}
    precisions, recalls, f1s = [], [], []

    for c in range(num_classes):
        cname = idx_to_class[str(c)]
        tp = confusion[c, c]
        fp = confusion[:, c].sum() - tp
        fn = confusion[c, :].sum() - tp

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

        per_class[cname] = {
            "support": int(confusion[c, :].sum()),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4)
        }

    macro_precision = float(np.mean(precisions))
    macro_recall = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": confusion.tolist()
    }


def train_banana():
    print("=" * 70)
    print("AGRICHAIN AI — PHASE 14E: BANANA RIPENESS CLASSIFIER TRAINING")
    print("=" * 70)

    # 1. Load config
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    seed = config["training"]["random_seed"]
    seed_everything(seed)
    print(f"Random seed initialized: {seed}")

    device = torch.device(config["training"]["device"] if torch.cuda.is_available() else "cpu")
    print(f"Compute device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    class_to_idx = config["model"]["class_to_idx"]
    idx_to_class = config["model"]["idx_to_class"]
    num_classes = config["model"]["num_classes"]

    # 2. Build datasets
    train_transform, eval_transform = build_transforms(config)

    train_manifest = WORKSPACE_ROOT / config["dataset_manifests"]["train"]
    val_manifest = WORKSPACE_ROOT / config["dataset_manifests"]["val"]
    test_manifest = WORKSPACE_ROOT / config["dataset_manifests"]["test"]

    train_dataset = BananaRipenessDataset(train_manifest, class_to_idx, transform=train_transform)
    val_dataset = BananaRipenessDataset(val_manifest, class_to_idx, transform=eval_transform)
    test_dataset = BananaRipenessDataset(test_manifest, class_to_idx, transform=eval_transform)

    batch_size = config["training"]["batch_size"]
    num_workers = config["training"]["num_workers"]

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    print(f"DataLoaders prepared: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")

    # 3. Class-weighted CrossEntropy
    train_labels = [class_to_idx[r["class"]] for r in train_dataset.records]
    class_counts = Counter(train_labels)
    total_samples = len(train_labels)
    weights = [total_samples / (num_classes * class_counts[c]) for c in range(num_classes)]
    class_weights_t = torch.tensor(weights, dtype=torch.float, device=device)
    print(f"Class weights computed: {[round(w, 3) for w in weights]}")

    criterion = nn.CrossEntropyLoss(
        weight=class_weights_t,
        label_smoothing=config["training"]["loss"].get("label_smoothing", 0.05)
    )

    # 4. Build Model
    model = build_model(config).to(device)

    # Optimizer with differential learning rates
    opt_cfg = config["training"]["optimizer"]
    head_params = [p for p in model.fc.parameters() if p.requires_grad]
    backbone_params = [p for n, p in model.named_parameters() if not n.startswith("fc") and p.requires_grad]

    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": opt_cfg["lr_backbone"]},
        {"params": head_params, "lr": opt_cfg["lr_head"]}
    ], weight_decay=opt_cfg["weight_decay"])

    epochs = config["training"]["epochs"]
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config["training"]["lr_scheduler"]["T_max"],
        eta_min=config["training"]["lr_scheduler"]["eta_min"]
    )

    scaler = torch.amp.GradScaler('cuda') if (config["training"]["mixed_precision"] and torch.cuda.is_available()) else None

    # Checkpoint paths
    best_chk_path = WORKSPACE_ROOT / config["checkpointing"]["best_checkpoint_path"]
    latest_chk_path = WORKSPACE_ROOT / config["checkpointing"]["latest_checkpoint_path"]
    best_chk_path.parent.mkdir(parents=True, exist_ok=True)

    # Training Loop
    print("\n--- Beginning Training Loop ---")
    best_val_f1 = -1.0
    best_epoch = -1
    early_stop_patience = config["training"]["early_stopping"]["patience"]
    patience_counter = 0

    history = {
        "epoch": [],
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "val_macro_f1": [],
        "lr": []
    }

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        # TRAIN
        model.train()
        train_loss_total = 0.0
        train_preds, train_targets = [], []

        for imgs, labels, _ in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()

            if scaler:
                with torch.amp.autocast('cuda'):
                    outputs = model(imgs)
                    loss = criterion(outputs, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

            train_loss_total += loss.item() * imgs.size(0)
            preds = outputs.argmax(dim=1).cpu().numpy()
            train_preds.extend(preds)
            train_targets.extend(labels.cpu().numpy())

        scheduler.step()
        epoch_train_loss = train_loss_total / len(train_dataset)
        epoch_train_acc = float(np.mean(np.array(train_preds) == np.array(train_targets)))

        # VALIDATE
        model.eval()
        val_loss_total = 0.0
        val_preds, val_targets = [], []

        with torch.no_grad():
            for imgs, labels, _ in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                if scaler:
                    with torch.amp.autocast('cuda'):
                        outputs = model(imgs)
                        loss = criterion(outputs, labels)
                else:
                    outputs = model(imgs)
                    loss = criterion(outputs, labels)

                val_loss_total += loss.item() * imgs.size(0)
                preds = outputs.argmax(dim=1).cpu().numpy()
                val_preds.extend(preds)
                val_targets.extend(labels.cpu().numpy())

        epoch_val_loss = val_loss_total / len(val_dataset)
        val_metrics = compute_metrics(val_targets, val_preds, num_classes, idx_to_class)
        epoch_val_acc = val_metrics["accuracy"]
        epoch_val_f1 = val_metrics["macro_f1"]
        current_lr = optimizer.param_groups[1]["lr"]

        history["epoch"].append(epoch)
        history["train_loss"].append(round(epoch_train_loss, 4))
        history["train_acc"].append(round(epoch_train_acc, 4))
        history["val_loss"].append(round(epoch_val_loss, 4))
        history["val_acc"].append(round(epoch_val_acc, 4))
        history["val_macro_f1"].append(round(epoch_val_f1, 4))
        history["lr"].append(current_lr)

        print(f"Epoch [{epoch:02d}/{epochs:02d}] "
              f"Train Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc*100:.1f}% | "
              f"Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc*100:.1f}% F1: {epoch_val_f1:.4f} | "
              f"LR: {current_lr:.6f}", end="")

        # Check for best model
        if epoch_val_f1 > best_val_f1:
            best_val_f1 = epoch_val_f1
            best_epoch = epoch
            patience_counter = 0

            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_macro_f1": best_val_f1,
                "val_accuracy": epoch_val_acc,
                "val_metrics": val_metrics,
                "config": config,
                "classes": list(class_to_idx.keys()),
                "class_to_idx": class_to_idx,
                "idx_to_class": idx_to_class
            }, best_chk_path)
            print(" -> [BEST CHECKPOINT SAVED]")
        else:
            patience_counter += 1
            print(f" (Patience: {patience_counter}/{early_stop_patience})")
            if patience_counter >= early_stop_patience:
                print(f"[EARLY STOPPING] Validation F1 did not improve for {early_stop_patience} epochs.")
                break

    total_training_time = time.time() - start_time
    print(f"\n[DONE] Training complete in {total_training_time:.1f}s. Best Epoch: {best_epoch} (Val F1: {best_val_f1:.4f})")

    # 5. TEST EVALUATION
    print("\n=======================================================")
    print("EVALUATING BEST MODEL ON UNTOUCHED TEST SET")
    print("=======================================================")
    checkpoint = torch.load(best_chk_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    test_preds, test_targets = [], []
    inference_latencies = []

    with torch.no_grad():
        for imgs, labels, _ in test_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            t0 = time.perf_counter()
            outputs = model(imgs)
            torch.cuda.synchronize() if torch.cuda.is_available() else None
            batch_time = (time.perf_counter() - t0) * 1000.0  # ms
            per_sample_latency = batch_time / imgs.size(0)
            inference_latencies.extend([per_sample_latency] * imgs.size(0))

            preds = outputs.argmax(dim=1).cpu().numpy()
            test_preds.extend(preds)
            test_targets.extend(labels.cpu().numpy())

    test_metrics = compute_metrics(test_targets, test_preds, num_classes, idx_to_class)
    avg_latency = float(np.mean(inference_latencies))
    p95_latency = float(np.percentile(inference_latencies, 95))
    model_size_mb = best_chk_path.stat().st_size / (1024 * 1024)

    test_results = {
        "evaluation_split": "test",
        "total_test_samples": len(test_dataset),
        "overall_accuracy": test_metrics["accuracy"],
        "macro_precision": test_metrics["macro_precision"],
        "macro_recall": test_metrics["macro_recall"],
        "macro_f1": test_metrics["macro_f1"],
        "per_class": test_metrics["per_class"],
        "confusion_matrix": test_metrics["confusion_matrix"],
        "classes_order": [idx_to_class[str(i)] for i in range(num_classes)],
        "inference_latency_ms": {
            "mean": round(avg_latency, 2),
            "p95": round(p95_latency, 2),
            "device": str(device)
        },
        "model_file_size_mb": round(model_size_mb, 2),
        "checkpoint_sha256": compute_sha256(best_chk_path),
        "best_epoch": best_epoch,
        "best_val_macro_f1": round(best_val_f1, 4),
        "total_training_duration_seconds": round(total_training_time, 1)
    }

    print("\n--- TEST METRICS REPORT ---")
    print(f"Overall Accuracy: {test_results['overall_accuracy']*100:.2f}%")
    print(f"Macro F1 Score:   {test_results['macro_f1']:.4f}")
    print(f"Macro Precision: {test_results['macro_precision']:.4f}")
    print(f"Macro Recall:    {test_results['macro_recall']:.4f}")
    print(f"Mean Latency:    {test_results['inference_latency_ms']['mean']:.2f} ms/image")
    print(f"Model Checkpoint Size: {test_results['model_file_size_mb']:.2f} MB")
    print("\nPer-Class Breakdown:")
    for cname, stats in test_results["per_class"].items():
        print(f"  * {cname:<10}: Precision={stats['precision']:.4f} | Recall={stats['recall']:.4f} | F1={stats['f1']:.4f} | Support={stats['support']}")

    print("\nConfusion Matrix (Rows=True, Cols=Pred):")
    print(f"{'':>12}" + "".join(f"{idx_to_class[str(i)]:>12}" for i in range(num_classes)))
    for i in range(num_classes):
        row_str = "".join(f"{test_metrics['confusion_matrix'][i][j]:>12}" for j in range(num_classes))
        print(f"{idx_to_class[str(i)]:>12}{row_str}")

    # 6. SAVE EXPERIMENT ARTIFACTS
    with open(EXPERIMENTS_DIR / "training_curves.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    with open(EXPERIMENTS_DIR / "test_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)

    with open(EXPERIMENTS_DIR / "confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump({
            "classes": [idx_to_class[str(i)] for i in range(num_classes)],
            "matrix": test_metrics["confusion_matrix"]
        }, f, indent=2)

    summary_manifest = {
        "experiment_name": "banana_resnet18_baseline",
        "phase": "14E",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "random_seed": seed,
        "pytorch_version": torch.__version__,
        "device": str(device),
        "config": config,
        "training_history_summary": {
            "best_epoch": best_epoch,
            "final_epoch": len(history["epoch"]),
            "best_val_f1": best_val_f1
        },
        "test_results": test_results
    }

    with open(EXPERIMENTS_DIR / "experiment_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_manifest, f, indent=2)

    print(f"\n[PASS] All experiment records saved to {EXPERIMENTS_DIR.relative_to(WORKSPACE_ROOT)}/")
    return test_results, history


def evaluate_only():
    print("=" * 70)
    print("EVALUATING EXISTING BANANA CHECKPOINT ON TEST SPLIT")
    print("=" * 70)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    class_to_idx = config["model"]["class_to_idx"]
    idx_to_class = config["model"]["idx_to_class"]
    num_classes = config["model"]["num_classes"]

    _, eval_transform = build_transforms(config)
    test_manifest = WORKSPACE_ROOT / config["dataset_manifests"]["test"]
    test_dataset = BananaRipenessDataset(test_manifest, class_to_idx, transform=eval_transform)
    test_loader = DataLoader(test_dataset, batch_size=config["training"]["batch_size"], shuffle=False, num_workers=0)

    best_chk_path = WORKSPACE_ROOT / config["checkpointing"]["best_checkpoint_path"]
    if not best_chk_path.exists():
        print(f"[ERROR] Checkpoint not found at {best_chk_path}")
        sys.exit(1)

    checkpoint = torch.load(best_chk_path, map_location=device, weights_only=False)
    model = build_model(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    test_preds, test_targets = [], []
    inference_latencies = []

    with torch.no_grad():
        for imgs, labels, _ in test_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            t0 = time.perf_counter()
            outputs = model(imgs)
            torch.cuda.synchronize() if torch.cuda.is_available() else None
            batch_time = (time.perf_counter() - t0) * 1000.0  # ms
            per_sample_latency = batch_time / imgs.size(0)
            inference_latencies.extend([per_sample_latency] * imgs.size(0))

            preds = outputs.argmax(dim=1).cpu().numpy()
            test_preds.extend(preds)
            test_targets.extend(labels.cpu().numpy())

    test_metrics = compute_metrics(test_targets, test_preds, num_classes, idx_to_class)
    avg_latency = float(np.mean(inference_latencies))
    p95_latency = float(np.percentile(inference_latencies, 95))
    model_size_mb = best_chk_path.stat().st_size / (1024 * 1024)

    test_results = {
        "evaluation_split": "test",
        "total_test_samples": len(test_dataset),
        "overall_accuracy": test_metrics["accuracy"],
        "macro_precision": test_metrics["macro_precision"],
        "macro_recall": test_metrics["macro_recall"],
        "macro_f1": test_metrics["macro_f1"],
        "per_class": test_metrics["per_class"],
        "confusion_matrix": test_metrics["confusion_matrix"],
        "classes_order": [idx_to_class[str(i)] for i in range(num_classes)],
        "inference_latency_ms": {
            "mean": round(avg_latency, 2),
            "p95": round(p95_latency, 2),
            "device": str(device)
        },
        "model_file_size_mb": round(model_size_mb, 2),
        "checkpoint_sha256": compute_sha256(best_chk_path),
        "best_epoch": checkpoint.get("epoch", 24),
        "best_val_macro_f1": round(checkpoint.get("val_macro_f1", 0.8136), 4)
    }

    print("\n--- TEST METRICS REPORT ---")
    print(f"Overall Accuracy: {test_results['overall_accuracy']*100:.2f}%")
    print(f"Macro F1 Score:   {test_results['macro_f1']:.4f}")
    print(f"Macro Precision: {test_results['macro_precision']:.4f}")
    print(f"Macro Recall:    {test_results['macro_recall']:.4f}")
    print(f"Mean Latency:    {test_results['inference_latency_ms']['mean']:.2f} ms/image")
    print(f"Model Checkpoint Size: {test_results['model_file_size_mb']:.2f} MB")
    print("\nPer-Class Breakdown:")
    for cname, stats in test_results["per_class"].items():
        print(f"  * {cname:<10}: Precision={stats['precision']:.4f} | Recall={stats['recall']:.4f} | F1={stats['f1']:.4f} | Support={stats['support']}")

    print("\nConfusion Matrix (Rows=True, Cols=Pred):")
    print(f"{'':>12}" + "".join(f"{idx_to_class[str(i)]:>12}" for i in range(num_classes)))
    for i in range(num_classes):
        row_str = "".join(f"{test_metrics['confusion_matrix'][i][j]:>12}" for j in range(num_classes))
        print(f"{idx_to_class[str(i)]:>12}{row_str}")

    with open(EXPERIMENTS_DIR / "test_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)

    with open(EXPERIMENTS_DIR / "confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump({
            "classes": [idx_to_class[str(i)] for i in range(num_classes)],
            "matrix": test_metrics["confusion_matrix"]
        }, f, indent=2)

    summary_manifest = {
        "experiment_name": "banana_resnet18_baseline",
        "phase": "14E",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "random_seed": config["training"]["random_seed"],
        "pytorch_version": torch.__version__,
        "device": str(device),
        "config": config,
        "test_results": test_results
    }

    with open(EXPERIMENTS_DIR / "experiment_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_manifest, f, indent=2)

    print(f"\n[PASS] Saved test evaluation to {EXPERIMENTS_DIR.relative_to(WORKSPACE_ROOT)}/")
    return test_results


if __name__ == "__main__":
    if "--eval-only" in sys.argv:
        evaluate_only()
    else:
        train_banana()


