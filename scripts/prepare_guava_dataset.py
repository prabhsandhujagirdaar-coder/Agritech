"""
AgriChain AI — Phase 2: Guava Dataset Extraction & Manifest Generator
Extracts Dataset A into ml/data/guava_classification/, verifies integrity,
and generates reproducible stratified train/val/test splits (70/15/15).
"""
import zipfile
import os
import sys
import io
import json
import csv
import hashlib
from collections import Counter, defaultdict
from PIL import Image
import random

SOURCE_ARCHIVE = r"C:\Users\PrabSandhu\Downloads\Guava Fruit  Dataset for Classification.zip"
TARGET_DIR = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\guava_classification"
MANIFEST_DIR = os.path.join(TARGET_DIR, "manifests")
ALT_MANIFEST_DIR = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\manifests"

RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Canonical mapping
CLASS_MAP = {
    "Green": 0,
    "Mature Green": 1,
    "Ripe": 2
}

def extract_dataset():
    print("=" * 60)
    print("1. DISK SPACE & EXTRACTION")
    print(f"Source Archive: {SOURCE_ARCHIVE}")
    print(f"Target Directory: {TARGET_DIR}")
    
    if not os.path.exists(SOURCE_ARCHIVE):
        raise FileNotFoundError(f"Source archive not found: {SOURCE_ARCHIVE}")
        
    os.makedirs(TARGET_DIR, exist_ok=True)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    os.makedirs(ALT_MANIFEST_DIR, exist_ok=True)
    
    # Read outer zip
    with zipfile.ZipFile(SOURCE_ARCHIVE, 'r') as outer_z:
        nested_name = outer_z.namelist()[0]
        print(f"Reading nested archive: {nested_name}")
        nested_bytes = outer_z.read(nested_name)
        
    extracted_count = 0
    with zipfile.ZipFile(io.BytesIO(nested_bytes), 'r') as inner_z:
        infolist = inner_z.infolist()
        for member in infolist:
            # We strip the leading 'Guava Dataset/' if present so paths become:
            # ml/data/guava_classification/<variety>/<class>/<filename>
            parts = member.filename.replace('\\', '/').split('/')
            parts = [p for p in parts if p]
            if len(parts) >= 4 and parts[0] == "Guava Dataset":
                rel_path = os.path.join(*parts[1:])
                dest_path = os.path.join(TARGET_DIR, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f_out:
                    f_out.write(inner_z.read(member.filename))
                extracted_count += 1
                
    print(f"[EXTRACTION COMPLETE] Extracted {extracted_count} image files into {TARGET_DIR}")
    return extracted_count

def verify_and_index():
    print("=" * 60)
    print("2. VERIFYING EXTRACTED FILES & INTEGRITY")
    
    records = []
    hashes = {}
    corrupt_files = []
    sizes = Counter()
    modes = Counter()
    
    for root, dirs, files in os.walk(TARGET_DIR):
        if "manifests" in root:
            continue
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, TARGET_DIR).replace('\\', '/')
                parts = rel_path.split('/')
                
                # Expected structure: <variety>/<class>/<filename>
                if len(parts) != 3:
                    continue
                variety, class_name, filename = parts
                if class_name not in CLASS_MAP:
                    continue
                    
                # Compute MD5
                with open(filepath, "rb") as fp:
                    data = fp.read()
                    md5 = hashlib.md5(data).hexdigest()
                    file_size = len(data)
                    
                # Decode image
                try:
                    with Image.open(io.BytesIO(data)) as img:
                        sizes[img.size] += 1
                        modes[img.mode] += 1
                        width, height = img.size
                except Exception as e:
                    corrupt_files.append((filepath, str(e)))
                    continue
                    
                record = {
                    "rel_path": rel_path,
                    "abs_path": os.path.abspath(filepath),
                    "filename": filename,
                    "variety": variety,
                    "class_name": class_name,
                    "label": CLASS_MAP[class_name],
                    "width": width,
                    "height": height,
                    "size_bytes": file_size,
                    "md5": md5
                }
                records.append(record)
                hashes[md5] = rel_path

    print(f"Total verified image records: {len(records)}")
    print(f"Corrupt or unreadable files: {len(corrupt_files)}")
    print(f"Color modes: {dict(modes)}")
    print(f"Dimensions: {dict(sizes)}")
    print(f"Unique MD5 hashes: {len(hashes)}")
    
    # Class distribution
    class_counts = Counter(r["class_name"] for r in records)
    print("\nOverall Class Distribution:")
    for c, cnt in sorted(class_counts.items()):
        print(f"  - {c}: {cnt} ({cnt / len(records) * 100:.2f}%)")
        
    variety_counts = Counter(r["variety"] for r in records)
    print("\nOverall Variety Distribution:")
    for v, cnt in sorted(variety_counts.items()):
        print(f"  - {v}: {cnt} ({cnt / len(records) * 100:.2f}%)")
        
    strata_counts = Counter((r["variety"], r["class_name"]) for r in records)
    print("\nJoint (Variety, Class) Strata Distribution:")
    for (v, c), cnt in sorted(strata_counts.items()):
        print(f"  - {v} | {c}: {cnt}")
        
    return records

def generate_stratified_splits(records):
    print("=" * 60)
    print(f"3. GENERATING STRATIFIED SPLITS (Seed={RANDOM_SEED})")
    
    random.seed(RANDOM_SEED)
    
    # Group records by joint stratum: (variety, class_name)
    strata = defaultdict(list)
    for r in records:
        strata[(r["variety"], r["class_name"])].append(r)
        
    train_records = []
    val_records = []
    test_records = []
    
    for (variety, class_name), items in sorted(strata.items()):
        # Deterministic shuffle within stratum
        items_sorted = sorted(items, key=lambda x: x["rel_path"])
        random.shuffle(items_sorted)
        
        n = len(items_sorted)
        n_train = int(round(n * TRAIN_RATIO))
        n_val = int(round(n * VAL_RATIO))
        n_test = n - n_train - n_val
        
        # Adjust if rounding edge cases occur
        if n_test < 1 and n >= 3:
            n_test = 1
            if n_train > n_val:
                n_train -= 1
            else:
                n_val -= 1
                
        train_slice = items_sorted[:n_train]
        val_slice = items_sorted[n_train:n_train + n_val]
        test_slice = items_sorted[n_train + n_val:]
        
        train_records.extend(train_slice)
        val_records.extend(val_slice)
        test_records.extend(test_slice)
        
        print(f"  Stratum ({variety} | {class_name}): Total={n} -> Train={len(train_slice)}, Val={len(val_slice)}, Test={len(test_slice)}")
        
    print(f"\nFinal Split Totals:")
    print(f"  Train: {len(train_records)} ({len(train_records) / len(records) * 100:.2f}%)")
    print(f"  Val:   {len(val_records)} ({len(val_records) / len(records) * 100:.2f}%)")
    print(f"  Test:  {len(test_records)} ({len(test_records) / len(records) * 100:.2f}%)")
    print(f"  Total: {len(train_records) + len(val_records) + len(test_records)}")
    
    # Leakage & Disjointness Verification
    train_hashes = set(r["md5"] for r in train_records)
    val_hashes = set(r["md5"] for r in val_records)
    test_hashes = set(r["md5"] for r in test_records)
    
    tv_overlap = train_hashes.intersection(val_hashes)
    tt_overlap = train_hashes.intersection(test_hashes)
    vt_overlap = val_hashes.intersection(test_hashes)
    
    print("\nData Leakage & Disjointness Check:")
    print(f"  Train/Val MD5 overlap: {len(tv_overlap)}")
    print(f"  Train/Test MD5 overlap: {len(tt_overlap)}")
    print(f"  Val/Test MD5 overlap: {len(vt_overlap)}")
    assert len(tv_overlap) == 0 and len(tt_overlap) == 0 and len(vt_overlap) == 0, "DATA LEAKAGE DETECTED!"
    print("  [LEAKAGE CHECK PASS] Splits are strictly disjoint across MD5 hashes and filepaths.")
    
    # Save manifests
    for m_dir in [MANIFEST_DIR, ALT_MANIFEST_DIR]:
        save_manifest(os.path.join(m_dir, "train.csv"), train_records)
        save_manifest(os.path.join(m_dir, "val.csv"), val_records)
        save_manifest(os.path.join(m_dir, "test.csv"), test_records)
        save_json(os.path.join(m_dir, "train.json"), train_records)
        save_json(os.path.join(m_dir, "val.json"), val_records)
        save_json(os.path.join(m_dir, "test.json"), test_records)
        
        # Summary statistics
        summary = {
            "total_images": len(records),
            "random_seed": RANDOM_SEED,
            "ratios": {"train": TRAIN_RATIO, "val": VAL_RATIO, "test": TEST_RATIO},
            "split_counts": {
                "train": len(train_records),
                "val": len(val_records),
                "test": len(test_records)
            },
            "train_class_distribution": dict(Counter(r["class_name"] for r in train_records)),
            "val_class_distribution": dict(Counter(r["class_name"] for r in val_records)),
            "test_class_distribution": dict(Counter(r["class_name"] for r in test_records)),
            "train_variety_distribution": dict(Counter(r["variety"] for r in train_records)),
            "val_variety_distribution": dict(Counter(r["variety"] for r in val_records)),
            "test_variety_distribution": dict(Counter(r["variety"] for r in test_records)),
        }
        with open(os.path.join(m_dir, "dataset_summary.json"), "w") as fp:
            json.dump(summary, fp, indent=2)
            
    print(f"\nManifests saved to: {MANIFEST_DIR} and {ALT_MANIFEST_DIR}")
    return train_records, val_records, test_records

def save_manifest(filepath, records):
    fieldnames = ["rel_path", "abs_path", "variety", "class_name", "label", "width", "height", "size_bytes", "md5"]
    with open(filepath, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in fieldnames})

def save_json(filepath, records):
    with open(filepath, "w", encoding="utf-8") as fp:
        json.dump(records, fp, indent=2)

if __name__ == "__main__":
    extract_dataset()
    records = verify_and_index()
    generate_stratified_splits(records)
