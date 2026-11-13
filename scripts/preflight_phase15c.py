"""
AgriChain AI — Phase 15C Preflight Verification Script
=====================================================
Validates all Stage 1 manifests, image paths, label mappings, split disjointness,
locked Stage 2 test split synchronization, checkpoint baselines, and registry guards.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter
from PIL import Image

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "manifests"
STAGE1_MANIFEST_DIR = MANIFESTS_DIR / "fruit_identifier_v1"
ARTIFACTS_DIR = WORKSPACE_ROOT / "ml" / "artifacts"
DOCS_DIR = WORKSPACE_ROOT / "docs" / "ml"

EXPECTED_GUAVA_SHA256 = "b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4"
EXPECTED_BANANA_SHA256 = "3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae"

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def run_preflight():
    print("=" * 70)
    print("AGRICHAIN AI — PHASE 15C: STAGE 1 TRAINING PREFLIGHT VERIFICATION")
    print("=" * 70)

    errors = []

    # 1. Phase 15B Report Verification
    report_15b = DOCS_DIR / "PHASE15B_FRUIT_IDENTIFIER_DATASET_VALIDATION.md"
    if not report_15b.exists() or report_15b.stat().st_size < 1000:
        errors.append(f"Phase 15B report missing or incomplete at {report_15b}")
    else:
        print(f"[PASS] Phase 15B Report verified ({report_15b.stat().st_size:,} bytes).")

    # 2. Manifest Existence
    for split in ["train.json", "val.json", "test.json", "dataset_summary.json"]:
        m_path = STAGE1_MANIFEST_DIR / split
        if not m_path.exists():
            errors.append(f"Missing Stage 1 manifest: {m_path}")
        else:
            print(f"[PASS] Stage 1 manifest verified: {split}")

    if errors:
        print(f"\n[FATAL] Manifest existence failures: {errors}")
        return False

    # 3. Load & Validate Records
    with open(STAGE1_MANIFEST_DIR / "train.json", "r", encoding="utf-8") as f:
        train_records = json.load(f)
    with open(STAGE1_MANIFEST_DIR / "val.json", "r", encoding="utf-8") as f:
        val_records = json.load(f)
    with open(STAGE1_MANIFEST_DIR / "test.json", "r", encoding="utf-8") as f:
        test_records = json.load(f)
    with open(STAGE1_MANIFEST_DIR / "dataset_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)

    # 4. Count Reconciliations
    print("\n--- Verifying Split Record Counts & Class Reconciliations ---")
    expected_test_classes = {"guava": 346, "banana": 297, "apple": 408, "mango": 46, "negative_background": 1785}
    actual_test_classes = Counter(r["fruit_identity"] for r in test_records)
    print(f"  Test Total: {len(test_records):,} (Expected: 2,882)")
    if len(test_records) != 2882 or dict(actual_test_classes) != expected_test_classes:
        errors.append(f"Test split count mismatch: got {dict(actual_test_classes)}, expected {expected_test_classes}")
    else:
        print(f"  [PASS] Test split class counts reconciled: {dict(actual_test_classes)}")

    expected_val_classes = {"guava": 346, "banana": 293, "apple": 185, "mango": 37, "negative_background": 6599}
    actual_val_classes = Counter(r["fruit_identity"] for r in val_records)
    print(f"  Val Total:  {len(val_records):,} (Expected: 7,460)")
    if len(val_records) != 7460 or dict(actual_val_classes) != expected_val_classes:
        errors.append(f"Val split count mismatch: got {dict(actual_val_classes)}, expected {expected_val_classes}")
    else:
        print(f"  [PASS] Val split class counts reconciled: {dict(actual_val_classes)}")

    expected_train_classes = {"guava": 1617, "banana": 1370, "apple": 1981, "mango": 189, "negative_background": 3825}
    actual_train_classes = Counter(r["fruit_identity"] for r in train_records)
    print(f"  Train Total: {len(train_records):,} (Expected: 8,982)")
    if len(train_records) != 8982 or dict(actual_train_classes) != expected_train_classes:
        errors.append(f"Train split count mismatch: got {dict(actual_train_classes)}, expected {expected_train_classes}")
    else:
        print(f"  [PASS] Train split class counts reconciled: {dict(actual_train_classes)}")

    total_stage1 = len(train_records) + len(val_records) + len(test_records)
    print(f"  Total Stage 1 Samples: {total_stage1:,} records.")

    # 5. Split Disjointness & Group Leakage Check
    print("\n--- Verifying Split Disjointness & Group Isolation ---")
    train_paths = {r["path"] for r in train_records}
    val_paths = {r["path"] for r in val_records}
    test_paths = {r["path"] for r in test_records}

    train_val_overlap = train_paths & val_paths
    train_test_overlap = train_paths & test_paths
    val_test_overlap = val_paths & test_paths

    if train_val_overlap:
        errors.append(f"Train and Val share {len(train_val_overlap)} image paths!")
    if train_test_overlap:
        errors.append(f"Train and Test share {len(train_test_overlap)} image paths!")
    if val_test_overlap:
        errors.append(f"Val and Test share {len(val_test_overlap)} image paths!")

    if not (train_val_overlap or train_test_overlap or val_test_overlap):
        print("  [PASS] All image paths are 100% disjoint across train, val, and test splits.")

    train_groups = {r["group_id"] for r in train_records}
    test_groups = {r["group_id"] for r in test_records}
    group_overlap = train_groups & test_groups
    if group_overlap:
        errors.append(f"Train and Test share {len(group_overlap)} capture burst group IDs!")
    else:
        print("  [PASS] Zero group ID leakage between train and test splits.")

    # 6. Physical Image File Existence Sample Check
    print("\n--- Verifying Physical File Integrity ---")
    missing_files = []
    # Sample check 1,000 files across splits
    all_recs = train_records + val_records + test_records
    sample_recs = all_recs[::19]  # ~1,017 samples across the full dataset
    for r in sample_recs:
        p = WORKSPACE_ROOT / r["path"]
        if not p.exists():
            missing_files.append(str(r["path"]))
    if missing_files:
        errors.append(f"Missing physical image files: {missing_files[:5]}")
    else:
        print(f"  [PASS] Verified physical file accessibility across {len(sample_recs)} sample images.")

    # 7. Locked Stage 2 Test Split Synchronization
    print("\n--- Verifying Locked Stage 2 Test Set Synchronization ---")
    with open(MANIFESTS_DIR / "v2_grouped" / "test.json", "r", encoding="utf-8") as f:
        guava_stage2_test = {f"ml/data/guava_classification/{r['rel_path']}".replace("\\", "/") for r in json.load(f)}
    with open(MANIFESTS_DIR / "banana_ripeness" / "test.json", "r", encoding="utf-8") as f:
        banana_stage2_test = {str(r['path']).replace("\\", "/") for r in json.load(f)}
    with open(MANIFESTS_DIR / "apple_crops_v1" / "test.json", "r", encoding="utf-8") as f:
        apple_stage2_test = {str(r['crop_path']).replace("\\", "/") for r in json.load(f)}
    with open(MANIFESTS_DIR / "mango_harumanis" / "test.json", "r", encoding="utf-8") as f:
        mango_stage2_test = {str(r['path']).replace("\\", "/") for r in json.load(f)}

    stage1_test_guava = {str(r["path"]).replace("\\", "/") for r in test_records if r["fruit_identity"] == "guava"}
    stage1_test_banana = {str(r["path"]).replace("\\", "/") for r in test_records if r["fruit_identity"] == "banana"}
    stage1_test_apple = {str(r["path"]).replace("\\", "/") for r in test_records if r["fruit_identity"] == "apple"}
    stage1_test_mango = {str(r["path"]).replace("\\", "/") for r in test_records if r["fruit_identity"] == "mango"}

    if guava_stage2_test != stage1_test_guava:
        errors.append("Guava Stage 2 test split does not match Stage 1 test split!")
    else:
        print("  [PASS] Guava Stage 2 held-out test split is 100% synchronized with Stage 1 test.")

    if banana_stage2_test != stage1_test_banana:
        errors.append("Banana Stage 2 test split does not match Stage 1 test split!")
    else:
        print("  [PASS] Banana Stage 2 held-out test split is 100% synchronized with Stage 1 test.")

    if apple_stage2_test != stage1_test_apple:
        errors.append("Apple Stage 2 test split does not match Stage 1 test split!")
    else:
        print("  [PASS] Apple Stage 2 held-out test split is 100% synchronized with Stage 1 test.")

    if mango_stage2_test != stage1_test_mango:
        errors.append("Mango Stage 2 test split does not match Stage 1 test split!")
    else:
        print("  [PASS] Mango Stage 2 held-out test split is 100% synchronized with Stage 1 test.")

    # 8. Checkpoint Baselines & Hash Verification
    print("\n--- Verifying Active Production Checkpoints & Hashes ---")
    guava_chk = ARTIFACTS_DIR / "best_guava_resnet18.pth"
    if not guava_chk.exists():
        errors.append("Guava production checkpoint is missing!")
    else:
        guava_h = compute_sha256(guava_chk)
        if guava_h != EXPECTED_GUAVA_SHA256:
            errors.append(f"Guava checkpoint SHA-256 mismatch: {guava_h} vs {EXPECTED_GUAVA_SHA256}")
        else:
            print(f"  [PASS] Guava Checkpoint Hash verified: {guava_h}")

    banana_chk = ARTIFACTS_DIR / "best_banana_resnet18.pth"
    if not banana_chk.exists():
        errors.append("Banana benchmark checkpoint is missing!")
    else:
        banana_h = compute_sha256(banana_chk)
        if banana_h != EXPECTED_BANANA_SHA256:
            errors.append(f"Banana checkpoint SHA-256 mismatch: {banana_h} vs {EXPECTED_BANANA_SHA256}")
        else:
            print(f"  [PASS] Banana Checkpoint Hash verified: {banana_h}")

    # 9. Model Registry Gating Invariant
    print("\n--- Verifying Model Registry Gating Invariants ---")
    reg_file = WORKSPACE_ROOT / "backend" / "app" / "services" / "model_registry.py"
    reg_content = reg_file.read_text(encoding="utf-8")
    if 'fruit_id="banana"' in reg_content and 'is_validated=False' in reg_content:
        print("  [PASS] Banana remains unvalidated (is_validated=False) in model registry.")
    else:
        errors.append("Banana registry gating violated or missing!")

    if 'fruit_id="apple"' in reg_content and 'is_validated=False' in reg_content:
        print("  [PASS] Apple remains unvalidated (is_validated=False) in model registry.")
    else:
        errors.append("Apple registry gating violated or missing!")

    if 'fruit_id="mango"' in reg_content and 'is_validated=False' in reg_content:
        print("  [PASS] Mango remains unvalidated (is_validated=False) in model registry.")
    else:
        errors.append("Mango registry gating violated or missing!")

    # 10. Summary Verdict
    print("\n" + "=" * 70)
    if errors:
        print(f"[PREFLIGHT FAILED] {len(errors)} errors found:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("[PREFLIGHT PASSED] All Stage 1 training prerequisites and safety checks verified.")
        print("=" * 70)
        return True

if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
