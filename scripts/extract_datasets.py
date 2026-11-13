#!/usr/bin/env python3
"""
AgriChain AI - Selective Dataset Extraction Script
===================================================
Extracts downloaded raw datasets into ml/data/raw/ safely and selectively.
- oranges_in_field : Extracted from 'Oranges in the field.zip'
- fruitnet         : Extracted from 'b6fftwbr2v-3/FruitNetDataset.zip' (skipping duplicate RAR)
- citrus_disease   : Extracted from nested 'Citrus.zip'
"""

import os
import sys
import zipfile
import shutil
import time
from pathlib import Path

WORKSPACE = Path(r"C:\Users\PrabSandhu\Documents\codes\Agritech_")
DOWNLOADS = Path(r"C:\Users\PrabSandhu\Downloads")

ORANGES_ZIP = DOWNLOADS / "Oranges in the field.zip"
FRUITNET_ZIP = DOWNLOADS / "b6fftwbr2v-3.zip"
CITRUS_DISEASE_ZIP = DOWNLOADS / "A Citrus Fruits and Leaves Dataset for Detection and Classification of Citrus Diseases through Machine Learning.zip"

RAW_DIR = WORKSPACE / "ml" / "data" / "raw"
DEST_ORANGES = RAW_DIR / "oranges_in_field"
DEST_FRUITNET = RAW_DIR / "fruitnet"
DEST_CITRUS_DISEASE = RAW_DIR / "citrus_disease"

def extract_oranges():
    print("\n" + "=" * 60)
    print("1. Extracting Oranges in the field...")
    print("=" * 60)
    if not ORANGES_ZIP.exists():
        print(f"ERROR: {ORANGES_ZIP} not found!")
        return False
    
    DEST_ORANGES.mkdir(parents=True, exist_ok=True)
    existing = list(DEST_ORANGES.glob("*"))
    if len(existing) > 0:
        print(f"Target directory {DEST_ORANGES} already contains {len(existing)} items. Skipping extraction.")
        return True

    t0 = time.time()
    with zipfile.ZipFile(ORANGES_ZIP, "r") as z:
        total = len(z.infolist())
        print(f"Extracting {total} items from {ORANGES_ZIP.name}...")
        z.extractall(DEST_ORANGES)
    print(f"Extracted successfully in {time.time() - t0:.2f} seconds.")
    return True

def extract_citrus_disease():
    print("\n" + "=" * 60)
    print("2. Extracting Citrus Fruits & Leaves Disease Dataset...")
    print("=" * 60)
    if not CITRUS_DISEASE_ZIP.exists():
        print(f"ERROR: {CITRUS_DISEASE_ZIP} not found!")
        return False

    DEST_CITRUS_DISEASE.mkdir(parents=True, exist_ok=True)
    existing = list(DEST_CITRUS_DISEASE.glob("*"))
    if len(existing) > 0:
        print(f"Target directory {DEST_CITRUS_DISEASE} already contains {len(existing)} items. Skipping extraction.")
        return True

    t0 = time.time()
    with zipfile.ZipFile(CITRUS_DISEASE_ZIP, "r") as outer_z:
        nested_names = [n for n in outer_z.namelist() if n.endswith("Citrus.zip")]
        if not nested_names:
            print("ERROR: Citrus.zip not found inside outer zip!")
            return False
        nested_zip_name = nested_names[0]
        print(f"Extracting nested archive {nested_zip_name} to memory...")
        nested_bytes = outer_z.read(nested_zip_name)

    import io
    with zipfile.ZipFile(io.BytesIO(nested_bytes)) as inner_z:
        total = len(inner_z.infolist())
        print(f"Extracting {total} items from inner Citrus.zip to {DEST_CITRUS_DISEASE}...")
        inner_z.extractall(DEST_CITRUS_DISEASE)
    
    print(f"Extracted successfully in {time.time() - t0:.2f} seconds.")
    return True

def extract_fruitnet():
    print("\n" + "=" * 60)
    print("3. Extracting FruitNet (FruitNetDataset.zip only)...")
    print("=" * 60)
    if not FRUITNET_ZIP.exists():
        print(f"ERROR: {FRUITNET_ZIP} not found!")
        return False

    DEST_FRUITNET.mkdir(parents=True, exist_ok=True)
    existing = list(DEST_FRUITNET.glob("*"))
    if len(existing) > 0:
        print(f"Target directory {DEST_FRUITNET} already contains {len(existing)} items. Skipping extraction.")
        return True

    t0 = time.time()
    temp_inner_zip = DEST_FRUITNET / "FruitNetDataset.zip"
    print(f"Streaming 'b6fftwbr2v-3/FruitNetDataset.zip' from outer 6.1 GB archive...")
    
    with zipfile.ZipFile(FRUITNET_ZIP, "r") as outer_z:
        with outer_z.open("b6fftwbr2v-3/FruitNetDataset.zip") as src, open(temp_inner_zip, "wb") as dst:
            shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)
    print(f"Extracted temporary inner zip ({temp_inner_zip.stat().st_size / 1e6:.2f} MB) in {time.time() - t0:.2f}s.")

    print(f"Unpacking FruitNetDataset.zip into {DEST_FRUITNET}...")
    t1 = time.time()
    with zipfile.ZipFile(temp_inner_zip, "r") as inner_z:
        inner_z.extractall(DEST_FRUITNET)
    print(f"Unpacked all files in {time.time() - t1:.2f}s.")

    # Remove temporary inner zip to prevent duplicate storage
    if temp_inner_zip.exists():
        temp_inner_zip.unlink()
        print(f"Removed temporary archive {temp_inner_zip.name} to preserve disk space.")

    print(f"FruitNet extraction complete in {time.time() - t0:.2f} seconds.")
    return True

def main():
    print("Starting selective dataset extraction for AgriChain AI...")
    success_oranges = extract_oranges()
    success_disease = extract_citrus_disease()
    success_fruitnet = extract_fruitnet()

    print("\n" + "=" * 60)
    print("Extraction Summary:")
    print(f"  - Oranges in the field : {'SUCCESS' if success_oranges else 'FAILED'}")
    print(f"  - Citrus Disease       : {'SUCCESS' if success_disease else 'FAILED'}")
    print(f"  - FruitNet             : {'SUCCESS' if success_fruitnet else 'FAILED'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
