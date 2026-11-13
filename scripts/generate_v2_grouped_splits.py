"""
AgriChain AI — Version 2: Perceptual Cluster Group-Aware Split Generator
Groups images with dHash distance <= 2 into 606 candidate fruit/session clusters,
and performs group-aware stratified splitting across the 9 (variety, class) strata.
Saves versioned manifests in ml/data/manifests/v2_grouped/.
"""
import os
import json
import csv
import random
from collections import defaultdict, Counter
from PIL import Image

RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

TARGET_DIR = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\manifests\v2_grouped"

def dhash(image, hash_size=8):
    image = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = list(image.getdata())
    difference = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_left = pixels[row * (hash_size + 1) + col]
            pixel_right = pixels[row * (hash_size + 1) + col + 1]
            difference.append(pixel_left > pixel_right)
    decimal_value = 0
    hex_string = []
    for index, value in enumerate(difference):
        if value:
            decimal_value += 2 ** (index % 8)
        if (index % 8) == 7:
            hex_string.append(hex(decimal_value)[2:].rjust(2, '0'))
            decimal_value = 0
    return "".join(hex_string)

def hamming_distance(h1, h2):
    b1 = bytes.fromhex(h1)
    b2 = bytes.fromhex(h2)
    return sum(bin(x ^ y).count("1") for x, y in zip(b1, b2))

def generate_v2_splits():
    print("=" * 60)
    print("GENERATING V2 GROUP-AWARE SPLITS (Seed=42)")
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    manifest_dir = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\manifests"
    all_records = []
    for split in ['train', 'val', 'test']:
        with open(os.path.join(manifest_dir, f"{split}.json")) as f:
            all_records.extend(json.load(f))
            
    print(f"Loaded {len(all_records)} images.")
    
    # 1. Compute dHash
    hashes = {}
    for r in all_records:
        with Image.open(r["abs_path"]) as im:
            hashes[r["rel_path"]] = dhash(im)
            
    # 2. Form clusters within each (variety, class)
    strata = defaultdict(list)
    for r in all_records:
        strata[(r["variety"], r["class_name"])].append(r)
        
    random.seed(RANDOM_SEED)
    
    train_records = []
    val_records = []
    test_records = []
    cluster_manifest = []
    
    cluster_id = 0
    for (variety, class_name), records in sorted(strata.items()):
        n = len(records)
        adj = defaultdict(list)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = records[i]["rel_path"]
                r2 = records[j]["rel_path"]
                if hamming_distance(hashes[r1], hashes[r2]) <= 2:
                    adj[i].append(j)
                    adj[j].append(i)
                    
        # Connected components
        visited = set()
        components = []
        for i in range(n):
            if i not in visited:
                comp = []
                q = [i]
                visited.add(i)
                while q:
                    curr = q.pop(0)
                    comp.append(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            q.append(nbr)
                components.append([records[idx] for idx in comp])
                
        # Shuffle components deterministically
        for comp in components:
            for item in comp:
                item["cluster_id"] = f"{variety}_{class_name}_c{cluster_id:04d}"
            cluster_id += 1
            
        components.sort(key=lambda c: (len(c), c[0]["rel_path"]))
        random.shuffle(components)
        
        # Greedy knapsack to assign clusters to train/val/test aiming for 70/15/15
        total_imgs = n
        target_train = int(round(total_imgs * TRAIN_RATIO))
        target_val = int(round(total_imgs * VAL_RATIO))
        target_test = total_imgs - target_train - target_val
        
        s_train, s_val, s_test = [], [], []
        c_train, c_val, c_test = 0, 0, 0
        
        for comp in components:
            comp_len = len(comp)
            # Find which split needs images most relative to targets
            deficit_train = target_train - c_train
            deficit_val = target_val - c_val
            deficit_test = target_test - c_test
            
            # Prioritize test or val if they have large deficits
            if deficit_train >= deficit_val and deficit_train >= deficit_test and deficit_train > 0:
                s_train.extend(comp)
                c_train += comp_len
            elif deficit_val >= deficit_test and deficit_val > 0:
                s_val.extend(comp)
                c_val += comp_len
            elif deficit_test > 0:
                s_test.extend(comp)
                c_test += comp_len
            else:
                # All targets reached, assign to smallest
                if c_train <= c_val and c_train <= c_test:
                    s_train.extend(comp)
                    c_train += comp_len
                elif c_val <= c_test:
                    s_val.extend(comp)
                    c_val += comp_len
                else:
                    s_test.extend(comp)
                    c_test += comp_len
                    
        train_records.extend(s_train)
        val_records.extend(s_val)
        test_records.extend(s_test)
        print(f"  {variety} | {class_name}: {n} imgs ({len(components)} clusters) -> Train={len(s_train)}, Val={len(s_val)}, Test={len(s_test)}")
        
    print(f"\nV2 Grouped Split Totals:")
    print(f"  Train: {len(train_records)} ({len(train_records)/len(all_records)*100:.2f}%)")
    print(f"  Val:   {len(val_records)} ({len(val_records)/len(all_records)*100:.2f}%)")
    print(f"  Test:  {len(test_records)} ({len(test_records)/len(all_records)*100:.2f}%)")
    
    # Check cluster leakage
    train_c = set(r["cluster_id"] for r in train_records)
    val_c = set(r["cluster_id"] for r in val_records)
    test_c = set(r["cluster_id"] for r in test_records)
    
    assert len(train_c.intersection(val_c)) == 0
    assert len(train_c.intersection(test_c)) == 0
    assert len(val_c.intersection(test_c)) == 0
    print("  [LEAKAGE CHECK PASS] 0 cluster ID overlap across splits!")
    
    # Near duplicate check in v2
    train_h = {r["rel_path"]: hashes[r["rel_path"]] for r in train_records}
    val_h = {r["rel_path"]: hashes[r["rel_path"]] for r in val_records}
    test_h = {r["rel_path"]: hashes[r["rel_path"]] for r in test_records}
    
    zero_dist_tv = sum(1 for v in val_h.values() for t in train_h.values() if v == t)
    zero_dist_tt = sum(1 for te in test_h.values() for t in train_h.values() if te == t)
    print(f"  Identical dHash (dist=0) Train vs Val in V2: {zero_dist_tv}")
    print(f"  Identical dHash (dist=0) Train vs Test in V2: {zero_dist_tt}")
    
    # Save v2 manifests
    for name, recs in [("train", train_records), ("val", val_records), ("test", test_records)]:
        csv_path = os.path.join(TARGET_DIR, f"{name}.csv")
        json_path = os.path.join(TARGET_DIR, f"{name}.json")
        with open(csv_path, "w", newline="", encoding="utf-8") as fp:
            fieldnames = ["rel_path", "abs_path", "filename", "variety", "class_name", "label", "cluster_id", "width", "height", "size_bytes", "md5"]
            writer = csv.DictWriter(fp, fieldnames=fieldnames)
            writer.writeheader()
            for r in recs:
                writer.writerow(r)
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(recs, fp, indent=2)
            
    summary_v2 = {
        "split_version": "v2_grouped",
        "description": "Perceptual cluster group-aware split (dHash <= 2 clustering)",
        "random_seed": RANDOM_SEED,
        "total_images": len(all_records),
        "total_clusters": cluster_id,
        "split_counts": {
            "train": len(train_records),
            "val": len(val_records),
            "test": len(test_records)
        },
        "train_class_distribution": dict(Counter(r["class_name"] for r in train_records)),
        "val_class_distribution": dict(Counter(r["class_name"] for r in val_records)),
        "test_class_distribution": dict(Counter(r["class_name"] for r in test_records)),
    }
    with open(os.path.join(TARGET_DIR, "dataset_summary.json"), "w") as fp:
        json.dump(summary_v2, fp, indent=2)
        
    print(f"Saved v2 manifests to {TARGET_DIR}")

if __name__ == "__main__":
    generate_v2_splits()
