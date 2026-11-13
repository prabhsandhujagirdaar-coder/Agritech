"""
AgriChain AI — Comparative Evaluation Script (v1 Stratified vs v2 Grouped)
Evaluates best_guava_resnet18.pth on both test splits to empirically demonstrate
the impact of near-duplicate multi-angle frame leakage on reported metrics.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import torch
from ml.src.train_guava_cnn import GuavaDataset, build_transforms, evaluate_dataloader, build_model

def evaluate_comparison():
    config_path = "ml/configs/resnet18_guava_v2_grouped.json"
    with open(config_path) as f:
        config = json.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    best_path = config["checkpointing"]["best_checkpoint_path"]
    ckpt = torch.load(best_path, map_location=device)
    
    model = build_model(config).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    _, eval_transform = build_transforms(config)
    criterion = torch.nn.CrossEntropyLoss()

    # 1. Evaluate on V2 Grouped (Ground Truth Independent Clusters)
    v2_test_ds = GuavaDataset("ml/data/manifests/v2_grouped/test.json", transform=eval_transform)
    v2_loader = torch.utils.data.DataLoader(v2_test_ds, batch_size=32, shuffle=False)
    v2_metrics, _, _, _, _ = evaluate_dataloader(model, v2_loader, criterion, device)

    # 2. Evaluate on V1 Naive Stratified (Contains multi-angle rotation overlap)
    v1_test_ds = GuavaDataset("ml/data/manifests/test.json", transform=eval_transform)
    v1_loader = torch.utils.data.DataLoader(v1_test_ds, batch_size=32, shuffle=False)
    v1_metrics, _, _, _, _ = evaluate_dataloader(model, v1_loader, criterion, device)

    results = {
        "v2_grouped_test": {
            "description": "Group-aware split isolating 606 candidate fruit clusters (leakage mitigated)",
            "accuracy": round(v2_metrics["accuracy"] * 100, 2),
            "macro_f1": round(v2_metrics["macro_f1"], 4),
            "macro_recall": round(v2_metrics["macro_recall"], 4),
            "macro_precision": round(v2_metrics["macro_precision"], 4),
            "per_class_f1": [round(x, 4) for x in v2_metrics["per_class_f1"]],
            "confusion_matrix": v2_metrics["confusion_matrix"]
        },
        "v1_stratified_test": {
            "description": "Naive stratified split with random multi-angle rotation frames in both splits",
            "accuracy": round(v1_metrics["accuracy"] * 100, 2),
            "macro_f1": round(v1_metrics["macro_f1"], 4),
            "macro_recall": round(v1_metrics["macro_recall"], 4),
            "macro_precision": round(v1_metrics["macro_precision"], 4),
            "per_class_f1": [round(x, 4) for x in v1_metrics["per_class_f1"]],
            "confusion_matrix": v1_metrics["confusion_matrix"]
        }
    }

    out_file = "ml/experiments/guava_resnet18_v2_grouped/comparative_evaluation.json"
    with open(out_file, "w") as fp:
        json.dump(results, fp, indent=2)

    print("=" * 65)
    print("COMPARATIVE EVALUATION RESULTS")
    print("=" * 65)
    print(f"V2 Group-Aware Test: Accuracy = {results['v2_grouped_test']['accuracy']}% | Macro-F1 = {results['v2_grouped_test']['macro_f1']}")
    print(f"V1 Stratified Test:  Accuracy = {results['v1_stratified_test']['accuracy']}% | Macro-F1 = {results['v1_stratified_test']['macro_f1']}")
    print("=" * 65)
    return results

if __name__ == "__main__":
    evaluate_comparison()
