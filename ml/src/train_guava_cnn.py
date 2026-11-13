"""
AgriChain AI — ResNet18 Guava Baseline Training & Evaluation Engine
Phase 3 Implementation:
- Reproducible transfer learning baseline on verified Guava dataset.
- Group-aware v2 manifests with strict leakage controls.
- Validation-based model selection and resumable checkpointing.
- Comprehensive test evaluation with precision, recall, macro-F1, confusion matrix,
  and inference latency benchmarking.
"""
import os
import sys
import json
import time
import argparse
import random
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image

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

class GuavaDataset(Dataset):
    def __init__(self, manifest_path: str, transform=None):
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.records = json.load(f)
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]
        img_path = rec["abs_path"]
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            if self.transform:
                img = self.transform(img)
        label = int(rec["label"])
        return img, label, rec["rel_path"]

def build_transforms(config: dict):
    train_cfg = config["preprocessing"]["train_transforms"]
    eval_cfg = config["preprocessing"]["eval_transforms"]

    train_transform = T.Compose([
        T.Resize(tuple(train_cfg["resize"])),
        T.RandomCrop(tuple(train_cfg["random_crop"])),
        T.RandomHorizontalFlip(p=train_cfg.get("random_horizontal_flip_prob", 0.5)),
        T.RandomVerticalFlip(p=train_cfg.get("random_vertical_flip_prob", 0.5)),
        T.RandomRotation(degrees=train_cfg.get("random_rotation_degrees", 15)),
        T.ColorJitter(
            brightness=train_cfg["color_jitter"].get("brightness", 0.1),
            contrast=train_cfg["color_jitter"].get("contrast", 0.1),
            saturation=train_cfg["color_jitter"].get("saturation", 0.08),
            hue=train_cfg["color_jitter"].get("hue", 0.0) # Strictly 0.0
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

    # Replace fc head
    num_classes = model_cfg.get("num_classes", 3)
    dropout_p = model_cfg.get("dropout", 0.2)
    in_features = base_model.fc.in_features
    base_model.fc = nn.Sequential(
        nn.Dropout(p=dropout_p),
        nn.Linear(in_features, num_classes)
    )
    return base_model

def calculate_metrics(y_true, y_pred, num_classes=3):
    total = len(y_true)
    correct = sum(t == p for t, p in zip(y_true, y_pred))
    accuracy = correct / total if total > 0 else 0.0

    confusion_matrix = [[0] * num_classes for _ in range(num_classes)]
    for t, p in zip(y_true, y_pred):
        confusion_matrix[t][p] += 1

    per_class_precision = []
    per_class_recall = []
    per_class_f1 = []

    for c in range(num_classes):
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[i][c] for i in range(num_classes) if i != c)
        fn = sum(confusion_matrix[c][j] for j in range(num_classes) if j != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class_precision.append(prec)
        per_class_recall.append(rec)
        per_class_f1.append(f1)

    macro_precision = sum(per_class_precision) / num_classes
    macro_recall = sum(per_class_recall) / num_classes
    macro_f1 = sum(per_class_f1) / num_classes

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class_precision": per_class_precision,
        "per_class_recall": per_class_recall,
        "per_class_f1": per_class_f1,
        "confusion_matrix": confusion_matrix
    }

def evaluate_dataloader(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []
    all_paths = []
    all_probs = []

    with torch.no_grad():
        for images, labels, paths in dataloader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item() * images.size(0)

            probs = torch.softmax(outputs, dim=1)
            preds = torch.argmax(probs, dim=1)

            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(labels.cpu().tolist())
            all_paths.extend(paths)
            all_probs.extend(probs.cpu().tolist())

    avg_loss = total_loss / len(dataloader.dataset)
    metrics = calculate_metrics(all_targets, all_preds, num_classes=3)
    metrics["loss"] = avg_loss
    return metrics, all_targets, all_preds, all_paths, all_probs

def run_training(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    seed = config["training"].get("random_seed", 42)
    seed_everything(seed)

    device_str = config["training"].get("device", "cuda")
    if device_str == "cuda" and not torch.cuda.is_available():
        print("[WARN] CUDA requested but not available. Falling back to CPU.")
        device_str = "cpu"
    device = torch.device(device_str)
    print(f"Executing on hardware device: {device} ({torch.cuda.get_device_name(0) if device_str == 'cuda' else 'CPU'})")

    train_transform, eval_transform = build_transforms(config)

    train_manifest = config["dataset_manifests"]["train"]
    val_manifest = config["dataset_manifests"]["val"]
    test_manifest = config["dataset_manifests"]["test"]

    train_dataset = GuavaDataset(train_manifest, transform=train_transform)
    val_dataset = GuavaDataset(val_manifest, transform=eval_transform)
    test_dataset = GuavaDataset(test_manifest, transform=eval_transform)

    batch_size = config["training"].get("batch_size", 32)
    num_workers = config["training"].get("num_workers", 0)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    print(f"DataLoaders prepared: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")

    # Class weights for imbalance
    train_labels = [r["label"] for r in train_dataset.records]
    class_counts = Counter(train_labels)
    total_samples = len(train_labels)
    num_classes = config["model"].get("num_classes", 3)
    weights = [total_samples / (num_classes * class_counts[c]) for c in range(num_classes)]
    class_weights_tensor = torch.tensor(weights, dtype=torch.float32).to(device)
    print(f"Computed inverse class weights: {class_weights_tensor.tolist()} (Counts: {dict(class_counts)})")

    label_smoothing = config["training"]["loss"].get("label_smoothing", 0.05)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor, label_smoothing=label_smoothing)

    model = build_model(config).to(device)

    # Optimizer with distinct learning rates
    opt_cfg = config["training"]["optimizer"]
    head_params = [p for p in model.fc.parameters() if p.requires_grad]
    backbone_params = [p for n, p in model.named_parameters() if p.requires_grad and "fc" not in n]

    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": opt_cfg.get("lr_backbone", 1e-5)},
        {"params": head_params, "lr": opt_cfg.get("lr_head", 1e-4)}
    ], weight_decay=opt_cfg.get("weight_decay", 0.01))

    epochs = config["training"].get("epochs", 20)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    use_amp = config["training"].get("mixed_precision", True) and device_str == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    # Output paths
    best_ckpt_path = config["checkpointing"]["best_checkpoint_path"]
    latest_ckpt_path = config["checkpointing"]["latest_checkpoint_path"]
    os.makedirs(os.path.dirname(best_ckpt_path), exist_ok=True)
    os.makedirs(os.path.dirname(latest_ckpt_path), exist_ok=True)

    exp_dir = os.path.join("ml", "experiments", config["experiment_name"])
    os.makedirs(exp_dir, exist_ok=True)

    early_stop_cfg = config["training"].get("early_stopping", {})
    patience = early_stop_cfg.get("patience", 5)
    best_val_f1 = -1.0
    patience_counter = 0

    training_logs = []
    print("=" * 70)
    print("STARTING TRAINING LOOP")
    print("=" * 70)

    start_time_all = time.time()
    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        train_preds, train_targets = [], []

        for images, labels, _ in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            with torch.cuda.amp.autocast(enabled=use_amp):
                outputs = model(images)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1)
            train_preds.extend(preds.cpu().tolist())
            train_targets.extend(labels.cpu().tolist())

        scheduler.step()

        train_loss_avg = train_loss / len(train_dataset)
        train_metrics = calculate_metrics(train_targets, train_preds, num_classes=3)

        # Validation
        val_metrics, _, _, _, _ = evaluate_dataloader(model, val_loader, criterion, device)
        val_loss = val_metrics["loss"]
        val_acc = val_metrics["accuracy"]
        val_f1 = val_metrics["macro_f1"]

        epoch_time = time.time() - t0
        log_entry = {
            "epoch": epoch,
            "train_loss": round(train_loss_avg, 4),
            "train_acc": round(train_metrics["accuracy"], 4),
            "train_macro_f1": round(train_metrics["macro_f1"], 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
            "val_macro_f1": round(val_f1, 4),
            "val_per_class_f1": [round(x, 4) for x in val_metrics["per_class_f1"]],
            "epoch_seconds": round(epoch_time, 2)
        }
        training_logs.append(log_entry)

        print(f"Epoch [{epoch:02d}/{epochs:02d}] "
              f"Train Loss: {train_loss_avg:.4f} Acc: {train_metrics['accuracy']*100:.1f}% F1: {train_metrics['macro_f1']:.3f} | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.1f}% F1: {val_f1:.3f} | "
              f"Time: {epoch_time:.1f}s")

        # Save latest resumable checkpoint
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "scaler_state_dict": scaler.state_dict(),
            "val_metrics": val_metrics,
            "config": config,
            "random_seed": seed,
            "crop": "guava"
        }, latest_ckpt_path)

        # Check for best checkpoint
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_metrics": val_metrics,
                "config": config,
                "random_seed": seed,
                "crop": "guava",
                "class_mapping": config["model"]["idx_to_class"]
            }, best_ckpt_path)
            print(f"  --> [NEW BEST CHECKPOINT] Val Macro-F1: {val_f1:.4f} saved to {best_ckpt_path}")
        else:
            patience_counter += 1
            if early_stop_cfg.get("enabled", True) and patience_counter >= patience:
                print(f"[EARLY STOPPING TRIGGERED] No improvement in val_macro_f1 for {patience} epochs.")
                break

    total_training_time = time.time() - start_time_all
    print(f"\nTraining completed in {total_training_time:.1f} seconds. Best Val Macro-F1: {best_val_f1:.4f}")

    # Save training logs
    log_file = os.path.join(exp_dir, "training_log.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(training_logs, f, indent=2)

    # -------------------------------------------------------------------------
    # PHASE C: HELD-OUT TEST EVALUATION
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("PHASE C: HELD-OUT TEST EVALUATION (Using Best Validation Checkpoint)")
    print("=" * 70)

    best_ckpt = torch.load(best_ckpt_path, map_location=device)
    model.load_state_dict(best_ckpt["model_state_dict"])
    model.eval()

    test_metrics, y_true, y_pred, test_paths, test_probs = evaluate_dataloader(model, test_loader, criterion, device)

    # Latency benchmark
    print("Benchmarking single-image inference latency...")
    dummy_input = torch.randn(1, 3, 224, 224, device=device)
    # Warmup
    for _ in range(20):
        _ = model(dummy_input)
    if device_str == "cuda":
        torch.cuda.synchronize()

    times = []
    for _ in range(100):
        t_start = time.perf_counter()
        _ = model(dummy_input)
        if device_str == "cuda":
            torch.cuda.synchronize()
        times.append((time.perf_counter() - t_start) * 1000.0)
    latency_ms = float(np.median(times))
    print(f"Median inference latency on {device_str}: {latency_ms:.2f} ms per frame.")

    # Model size
    model_size_mb = os.path.getsize(best_ckpt_path) / (1024 * 1024)

    # Identify misclassifications
    idx_to_class = config["model"]["idx_to_class"]
    misclassified = []
    for t, p, path, probs in zip(y_true, y_pred, test_paths, test_probs):
        if t != p:
            misclassified.append({
                "rel_path": path,
                "true_label": idx_to_class[str(t)],
                "pred_label": idx_to_class[str(p)],
                "confidence": round(float(probs[p]), 4),
                "true_class_prob": round(float(probs[t]), 4)
            })

    test_report = {
        "evaluation_protocol": "v2_grouped_held_out_test",
        "best_epoch": best_ckpt["epoch"],
        "device": device_str,
        "model_architecture": "resnet18",
        "model_size_mb": round(model_size_mb, 2),
        "median_inference_latency_ms": round(latency_ms, 2),
        "test_samples": len(y_true),
        "test_loss": round(test_metrics["loss"], 4),
        "accuracy": round(test_metrics["accuracy"], 4),
        "macro_precision": round(test_metrics["macro_precision"], 4),
        "macro_recall": round(test_metrics["macro_recall"], 4),
        "macro_f1": round(test_metrics["macro_f1"], 4),
        "per_class": {
            "Green (0)": {
                "precision": round(test_metrics["per_class_precision"][0], 4),
                "recall": round(test_metrics["per_class_recall"][0], 4),
                "f1": round(test_metrics["per_class_f1"][0], 4),
                "support": sum(1 for y in y_true if y == 0)
            },
            "Mature Green (1)": {
                "precision": round(test_metrics["per_class_precision"][1], 4),
                "recall": round(test_metrics["per_class_recall"][1], 4),
                "f1": round(test_metrics["per_class_f1"][1], 4),
                "support": sum(1 for y in y_true if y == 1)
            },
            "Ripe (2)": {
                "precision": round(test_metrics["per_class_precision"][2], 4),
                "recall": round(test_metrics["per_class_recall"][2], 4),
                "f1": round(test_metrics["per_class_f1"][2], 4),
                "support": sum(1 for y in y_true if y == 2)
            }
        },
        "confusion_matrix": test_metrics["confusion_matrix"],
        "confusion_matrix_labels": ["Green", "Mature Green", "Ripe"],
        "total_misclassifications": len(misclassified),
        "sample_misclassifications": misclassified[:10]
    }

    test_metric_file = os.path.join(exp_dir, "test_metrics.json")
    with open(test_metric_file, "w", encoding="utf-8") as f:
        json.dump(test_report, f, indent=2)

    print("\n" + "=" * 70)
    print("FINAL TEST EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Test Accuracy:       {test_report['accuracy']*100:.2f}%")
    print(f"Test Macro-F1:       {test_report['macro_f1']:.4f}")
    print(f"Test Macro-Recall:   {test_report['macro_recall']:.4f}")
    print(f"Test Macro-Precision:{test_report['macro_precision']:.4f}")
    print("\nPer-Class Breakdown:")
    for cname, d in test_report["per_class"].items():
        print(f"  {cname:18s} -> Precision: {d['precision']:.4f} | Recall: {d['recall']:.4f} | F1: {d['f1']:.4f} (Support: {d['support']})")

    print("\nConfusion Matrix (Rows=True, Cols=Pred):")
    print("                Pred: Green   Mature Green   Ripe")
    for idx, cname in enumerate(["Green", "Mature Green", "Ripe"]):
        row = test_report["confusion_matrix"][idx]
        print(f"  True: {cname:12s}     {row[0]:4d}         {row[1]:4d}   {row[2]:4d}")

    print(f"\nMisclassifications: {len(misclassified)} / {len(y_true)} ({len(misclassified)/len(y_true)*100:.2f}%)")
    print(f"Metrics saved to: {test_metric_file}")
    return test_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgriChain AI Guava CNN Training & Evaluation")
    parser.add_argument("--config", type=str, default="ml/configs/resnet18_guava_v2_grouped.json", help="Path to config file")
    args = parser.parse_args()
    run_training(args.config)
