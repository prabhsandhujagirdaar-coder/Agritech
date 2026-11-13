"""
AgriChain AI — Perceptual Hash & Near-Duplicate Auditing Script
Computes 64-bit difference hashes (dHash) for all 2,309 images
and computes minimum Hamming distance between Train, Val, and Test splits.
"""
import os
import json
from PIL import Image
from collections import defaultdict

MANIFEST_PATH = r"c:\Users\PrabSandhu\Documents\codes\Agritech_\ml\data\manifests"

def dhash(image, hash_size=8):
    # Resize to (hash_size + 1, hash_size), grayscale
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

def audit_near_duplicates():
    print("=" * 60)
    print("AUDITING NEAR-DUPLICATES ACROSS SPLITS")
    
    with open(os.path.join(MANIFEST_PATH, "train.json"), "r") as fp:
        train_data = json.load(fp)
    with open(os.path.join(MANIFEST_PATH, "val.json"), "r") as fp:
        val_data = json.load(fp)
    with open(os.path.join(MANIFEST_PATH, "test.json"), "r") as fp:
        test_data = json.load(fp)
        
    print(f"Loaded records - Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")
    
    print("Computing perceptual dHash (64-bit) for all images...")
    train_hashes = {}
    for r in train_data:
        with Image.open(r["abs_path"]) as im:
            train_hashes[r["rel_path"]] = dhash(im)
            
    val_hashes = {}
    for r in val_data:
        with Image.open(r["abs_path"]) as im:
            val_hashes[r["rel_path"]] = dhash(im)
            
    test_hashes = {}
    for r in test_data:
        with Image.open(r["abs_path"]) as im:
            test_hashes[r["rel_path"]] = dhash(im)
            
    print(f"Computed {len(train_hashes)} train, {len(val_hashes)} val, {len(test_hashes)} test hashes.")
    
    # Check for identical perceptual hashes (Hamming distance == 0) across splits
    zero_dist_tv = []
    for vpath, vh in val_hashes.items():
        for tpath, th in train_hashes.items():
            if vh == th:
                zero_dist_tv.append((vpath, tpath))
                
    zero_dist_tt = []
    for testpath, testh in test_hashes.items():
        for tpath, th in train_hashes.items():
            if testh == th:
                zero_dist_tt.append((testpath, tpath))
                
    print(f"Identical perceptual hashes (Hamming dist = 0) between Train and Val: {len(zero_dist_tv)}")
    print(f"Identical perceptual hashes (Hamming dist = 0) between Train and Test: {len(zero_dist_tt)}")
    
    # Near-duplicates (Hamming dist <= 2, i.e. >= 96.8% visual bit match)
    near_dup_tt = []
    for testpath, testh in test_hashes.items():
        for tpath, th in train_hashes.items():
            dist = hamming_distance(testh, th)
            if dist <= 2:
                near_dup_tt.append((testpath, tpath, dist))
                
    print(f"Near-duplicate candidates (Hamming dist <= 2 / 64) between Train and Test: {len(near_dup_tt)}")
    if near_dup_tt:
        print("Sample near-duplicate candidate pairs (test vs train):")
        for s in near_dup_tt[:5]:
            print(f"  Test: {s[0]} <-> Train: {s[1]} (dist={s[2]})")
            
    # Report summary
    summary_res = {
        "identical_perceptual_hash_train_val": len(zero_dist_tv),
        "identical_perceptual_hash_train_test": len(zero_dist_tt),
        "near_duplicate_candidates_dist_le_2": len(near_dup_tt)
    }
    with open(os.path.join(MANIFEST_PATH, "leakage_audit.json"), "w") as fp:
        json.dump(summary_res, fp, indent=2)
        
    print(f"Near-duplicate audit saved to {os.path.join(MANIFEST_PATH, 'leakage_audit.json')}")

if __name__ == "__main__":
    audit_near_duplicates()
