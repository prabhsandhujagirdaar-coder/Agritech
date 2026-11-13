#!/usr/bin/env python3
"""
AgriChain AI - Citrus Image Curation and Human Review Manifest Generator
========================================================================
Phase 3A: Selects candidate orange images from the FruitNet Indian Citrus
cohort and generates the unannotated review manifest for human labeling.

Rules & Invariants:
- Never automatically convert Good/Bad/Mixed quality into maturity labels.
- Never infer Kinnow identity from the generic name 'Orange'.
- Do not apply color thresholds to create ground truth.
- Preserve burst-capture group IDs (group_id) for zero-leakage splitting.
- Provide clean, empty schema fields for expert human review.
"""

import os
import sys
import csv
import time
from pathlib import Path
from collections import Counter
from PIL import Image

WORKSPACE = Path(r"C:\Users\PrabSandhu\Documents\codes\Agritech_")
RAW_DIR = WORKSPACE / "ml" / "data" / "raw"
PROCESSED_DIR = WORKSPACE / "ml" / "data" / "processed"
MANIFEST_PATH = PROCESSED_DIR / "image_manifest.csv"
OUTPUT_REVIEW_CSV = PROCESSED_DIR / "citrus_candidate_review.csv"

# Allowed values for the human review field
ALLOWED_MATURITY_LABELS = {"underripe", "partially_ripe", "fully_ripe", "uncertain"}

EXPECTED_ORANGE_CATEGORIES = {
    "Good Quality_Fruits/Orange_Good": "good_quality",
    "Bad Quality_Fruits/Orange_Bad": "bad_quality",
    "Mixed Qualit_Fruits/Orange": "mixed_quality"
}

def curate_candidates(source_filter="fruitnet"):
    print("=" * 70)
    print("AGRICHAIN AI — CITRUS CANDIDATE CURATION & REVIEW MANIFEST")
    print("=" * 70)

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Source manifest not found: {MANIFEST_PATH}. Run audit_datasets.py first.")

    t0 = time.time()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    candidates = []
    seen_paths = set()
    category_counts = Counter()
    missing_files = []
    unreadable_files = []
    unexpected_labels = []

    print(f"Reading source manifest from {MANIFEST_PATH}...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dataset_source = row.get("dataset_source", "")
            fruit_type = row.get("fruit_type", "")
            original_class = row.get("original_class", "")

            # Filter for orange images from specified source
            if dataset_source == source_filter and fruit_type == "orange":
                rel_path = row["rel_path"]
                full_path = RAW_DIR / rel_path

                # 1. Validation: Duplicate path check
                if rel_path in seen_paths:
                    raise ValueError(f"Duplicate path encountered in manifest: {rel_path}")
                seen_paths.add(rel_path)

                # 2. Validation: File existence check
                if not full_path.exists():
                    missing_files.append(rel_path)
                    continue

                # 3. Validation: Image readability check
                try:
                    with Image.open(full_path) as img:
                        img.verify()
                except Exception as err:
                    unreadable_files.append((rel_path, str(err)))
                    continue

                # 4. Validation: Expected label mapping check
                if original_class not in EXPECTED_ORANGE_CATEGORIES:
                    unexpected_labels.append((rel_path, original_class))
                    quality_cat = "unclassified"
                else:
                    quality_cat = EXPECTED_ORANGE_CATEGORIES[original_class]

                category_counts[original_class] += 1

                # Suitability flag:
                # - good_quality & mixed_quality: Intact rinds suitable as primary maturity candidates
                # - bad_quality: Severe fungal rot/decomposition that obscures rind maturity
                if quality_cat in ("good_quality", "mixed_quality"):
                    suitability_flag = "primary_candidate"
                else:
                    suitability_flag = "defective_rot_specimen"

                candidate_id = f"CAND-{len(candidates) + 1:04d}"

                record = {
                    "candidate_id": candidate_id,
                    "rel_path": rel_path,
                    "dataset_source": dataset_source,
                    "original_quality_label": original_class,
                    "quality_category": quality_cat,
                    "width": row.get("width", ""),
                    "height": row.get("height", ""),
                    "format": row.get("format", ""),
                    "size_bytes": row.get("size_bytes", ""),
                    "sha256": row.get("sha256", ""),
                    "dhash": row.get("dhash", ""),
                    "group_id": row.get("group_id", ""),
                    "candidate_suitability_flag": suitability_flag,
                    # Explicit empty fields for human expert review:
                    "reviewer_maturity_label": "",
                    "reviewer_id": "",
                    "review_confidence": "",
                    "review_notes": "",
                    "cultivar_verified": "",
                    "ground_truth_method": ""
                }
                candidates.append(record)

    # Report validation checks
    print(f"\n--- Validation Checks ---")
    print(f"Total candidate images evaluated : {len(candidates)}")
    print(f"Missing file count              : {len(missing_files)}")
    print(f"Unreadable / corrupted files     : {len(unreadable_files)}")
    print(f"Unexpected label count           : {len(unexpected_labels)}")

    if missing_files:
        print(f"ERROR: {len(missing_files)} files missing from disk! Sample: {missing_files[:5]}")
        sys.exit(1)
    if unreadable_files:
        print(f"ERROR: {len(unreadable_files)} images corrupted! Sample: {unreadable_files[:5]}")
        sys.exit(1)
    if unexpected_labels:
        print(f"WARNING: Unexpected labels found: {unexpected_labels[:5]}")

    # Output to CSV
    fieldnames = [
        "candidate_id", "rel_path", "dataset_source", "original_quality_label",
        "quality_category", "width", "height", "format", "size_bytes",
        "sha256", "dhash", "group_id", "candidate_suitability_flag",
        "reviewer_maturity_label", "reviewer_id", "review_confidence",
        "review_notes", "cultivar_verified", "ground_truth_method"
    ]

    with open(OUTPUT_REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)

    print(f"\n--- Review Manifest Written ---")
    print(f"Destination : {OUTPUT_REVIEW_CSV}")
    print(f"Row count   : {len(candidates)} candidates")
    print(f"\nBreakdown by Quality Category:")
    for cat, cnt in category_counts.items():
        print(f"  - {cat}: {cnt} images")

    suitability_counts = Counter(c["candidate_suitability_flag"] for c in candidates)
    print(f"\nBreakdown by Candidate Suitability Flag:")
    for flag, cnt in suitability_counts.items():
        print(f"  - {flag}: {cnt} images")

    print(f"\nExecution time: {time.time() - t0:.2f} seconds.")
    print("=" * 70)
    return len(candidates)

if __name__ == "__main__":
    curate_candidates()
