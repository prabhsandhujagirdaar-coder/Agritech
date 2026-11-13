"""
AgriChain AI - Multi-Fruit Dataset Acquisition & Verification Script (Phase 14B)
Acquires verified raw datasets from official Mendeley Data endpoints:
1. BananaID (DOI: 10.17632/h6n5srjjyw.1) - Original unaugmented ripeness and variety subsets.
2. Apple Phenotyping (DOI: 10.17632/gfcmdbvw65.4) - 1,406 orchard images + original VIA JSON annotations.
3. Harumanis Mango (DOI: 10.17632/x6bcr3fkj5.4) - 272 original images + metadata and annotations.
"""

import os
import sys
import json
import hashlib
import zipfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = WORKSPACE_ROOT / "ml" / "data" / "raw"
MANIFESTS_DIR = WORKSPACE_ROOT / "ml" / "data" / "manifests"

BANANA_DIR = RAW_DIR / "banana"
APPLE_DIR = RAW_DIR / "apple"
MANGO_DIR = RAW_DIR / "mango"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"


def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def download_file(url: str, dest_path: Path, expected_size: int = None, description: str = "") -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        actual_size = dest_path.stat().st_size
        if expected_size and actual_size == expected_size:
            print(f"[SKIP] {dest_path.name} already exists and matches expected size ({actual_size:,} bytes).")
            return dest_path
        elif actual_size > 0 and expected_size is None:
            print(f"[SKIP] {dest_path.name} already exists ({actual_size:,} bytes).")
            return dest_path

    print(f"[DOWNLOAD] {description or dest_path.name} from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    
    with urllib.request.urlopen(req, timeout=180) as resp, open(temp_path, "wb") as f:
        total_len = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        last_pct = -1
        while chunk := resp.read(1048576):  # 1MB chunks
            f.write(chunk)
            downloaded += len(chunk)
            if total_len > 0:
                pct = int((downloaded / total_len) * 100)
                if pct % 20 == 0 and pct != last_pct:
                    print(f"  Progress: {pct}% ({downloaded / (1024*1024):.1f}/{total_len / (1024*1024):.1f} MB)")
                    last_pct = pct

    temp_path.replace(dest_path)
    print(f"[DONE] Saved {dest_path.name} ({dest_path.stat().st_size:,} bytes).")
    return dest_path


def acquire_banana():
    print("\n=======================================================")
    print("STEP 1: ACQUIRING BANANAID DATASET")
    print("=======================================================")
    archive_dir = BANANA_DIR / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 1. Banana Ripeness Dataset.zip (Original unaugmented)
    ripeness_url = "https://data.mendeley.com/public-files/datasets/h6n5srjjyw/files/ba61311a-63f2-4005-8fe5-66434d659a07/file_downloaded"
    ripeness_zip = archive_dir / "Banana_Ripeness_Dataset.zip"
    download_file(ripeness_url, ripeness_zip, expected_size=25998413, description="Banana Ripeness Dataset (Original)")

    # 2. Banana Variety Dataset.zip (Original unaugmented)
    variety_url = "https://data.mendeley.com/public-files/datasets/h6n5srjjyw/files/223b0a68-f088-415c-ac65-9e244bf832c6/file_downloaded"
    variety_zip = archive_dir / "Banana_Variety_Dataset.zip"
    download_file(variety_url, variety_zip, expected_size=25957121, description="Banana Variety Dataset (Original)")

    # Extract ripeness
    extract_ripeness = BANANA_DIR / "ripeness"
    if not extract_ripeness.exists() or not any(extract_ripeness.iterdir()):
        print(f"[EXTRACT] Extracting {ripeness_zip.name} to {extract_ripeness}...")
        with zipfile.ZipFile(ripeness_zip, "r") as z:
            z.extractall(extract_ripeness)
        print(f"[DONE] Extracted ripeness files.")
    else:
        print(f"[SKIP] {extract_ripeness} already contains extracted files.")

    # Extract variety
    extract_variety = BANANA_DIR / "variety"
    if not extract_variety.exists() or not any(extract_variety.iterdir()):
        print(f"[EXTRACT] Extracting {variety_zip.name} to {extract_variety}...")
        with zipfile.ZipFile(variety_zip, "r") as z:
            z.extractall(extract_variety)
        print(f"[DONE] Extracted variety files.")
    else:
        print(f"[SKIP] {extract_variety} already contains extracted files.")


def acquire_apple():
    print("\n=======================================================")
    print("STEP 2: ACQUIRING APPLE PHENOTYPING DATASET")
    print("=======================================================")
    archive_dir = APPLE_DIR / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)

    apple_url = "https://data.mendeley.com/public-files/datasets/gfcmdbvw65/files/f543b8ca-0adb-40ef-9ce5-540d2cb9ce14/file_downloaded"
    apple_zip = archive_dir / "dataset-20260508.zip"
    download_file(apple_url, apple_zip, expected_size=290131787, description="Apple Phenotyping Dataset (Original)")

    extract_dir = APPLE_DIR / "dataset"
    if not extract_dir.exists() or not any(extract_dir.iterdir()):
        print(f"[EXTRACT] Extracting {apple_zip.name} to {extract_dir}...")
        with zipfile.ZipFile(apple_zip, "r") as z:
            z.extractall(extract_dir)
        print(f"[DONE] Extracted apple files.")
    else:
        print(f"[SKIP] {extract_dir} already contains extracted files.")


def acquire_mango():
    print("\n=======================================================")
    print("STEP 3: ACQUIRING HARUMANIS MANGO DATASET")
    print("=======================================================")
    metadata_dir = MANGO_DIR / "metadata"
    original_dir = MANGO_DIR / "original"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    original_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch Mendeley dataset metadata to get exact file IDs
    print("[API] Fetching Harumanis Mango file catalog from Mendeley Data API...")
    mango_api_url = "https://data.mendeley.com/public-api/datasets/x6bcr3fkj5"
    req = urllib.request.Request(mango_api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        mango_data = json.loads(resp.read().decode('utf-8'))

    files = mango_data.get("files", [])
    print(f"[CATALOG] Found {len(files)} total files in Harumanis Mango dataset.")

    # 2. Download metadata files (CSV, README, Excel lists)
    meta_files = [f for f in files if not f.get("filename", "").lower().endswith((".jpg", ".jpeg", ".png"))]
    print(f"[METADATA] Downloading {len(meta_files)} metadata files...")
    for mf in meta_files:
        mf_name = mf.get("filename")
        mf_id = mf.get("id")
        mf_size = mf.get("size")
        mf_url = f"https://data.mendeley.com/public-files/datasets/x6bcr3fkj5/files/{mf_id}/file_downloaded"
        dest = metadata_dir / mf_name
        download_file(mf_url, dest, expected_size=mf_size, description=f"Metadata: {mf_name}")

    # 3. Read original image basenames from CSV and README
    labels_csv = metadata_dir / "labels original 272 images.csv"
    orig_names = set()
    if labels_csv.exists():
        with open(labels_csv, "r", encoding="utf-8-sig") as f:
            for line in f:
                parts = line.strip().split(",")
                if parts and parts[0].startswith("IMG-"):
                    orig_names.add(parts[0].strip().lower())

    # Ensure IMG-140 (the 23rd Rotten mango) is included per README
    orig_names.add("img-140")
    print(f"[TARGET] Identified {len(orig_names)} original mango images to acquire.")

    # 4. Filter the exact files matching the original 272 images (exclude augmented variants like flip, 180, etc.)
    # In Mendeley, original images are named "IMG-X.jpg" or "IMG-X.jpeg" (without flip/rotation suffixes)
    original_files_to_download = []
    for f in files:
        fname = f.get("filename", "")
        stem = Path(fname).stem.strip().lower()
        if stem in orig_names:
            original_files_to_download.append(f)

    # Some files may have duplicate entries in Mendeley; deduplicate by filename
    seen_names = {}
    deduped_files = []
    for f in original_files_to_download:
        fname = f.get("filename")
        if fname not in seen_names:
            seen_names[fname] = f
            deduped_files.append(f)

    print(f"[FILTER] Found {len(deduped_files)} original image files in catalog.")
    total_size = sum(f.get("size", 0) for f in deduped_files)
    print(f"[VOLUME] Total payload: {total_size / (1024*1024):.2f} MB.")

    # 5. Concurrent download of original images
    def download_image_task(f_info):
        fname = f_info.get("filename")
        fid = f_info.get("id")
        fsize = f_info.get("size")
        dest = original_dir / fname
        if dest.exists() and dest.stat().st_size == fsize:
            return fname, "skipped", fsize
        url = f"https://data.mendeley.com/public-files/datasets/x6bcr3fkj5/files/{fid}/file_downloaded"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        temp_dest = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp_dest, "wb") as out:
            out.write(resp.read())
        temp_dest.replace(dest)
        return fname, "downloaded", dest.stat().st_size

    print(f"[DOWNLOAD] Downloading {len(deduped_files)} images using 8 parallel connections...")
    downloaded_count = 0
    skipped_count = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_image_task, f): f for f in deduped_files}
        for future in as_completed(futures):
            try:
                fname, status, sz = future.result()
                if status == "downloaded":
                    downloaded_count += 1
                else:
                    skipped_count += 1
                total_done = downloaded_count + skipped_count
                if total_done % 50 == 0 or total_done == len(deduped_files):
                    print(f"  Progress: {total_done}/{len(deduped_files)} images processed ({downloaded_count} downloaded, {skipped_count} cached).")
            except Exception as e:
                print(f"  [ERROR] Image download failed: {e}")

    print(f"[DONE] Harumanis Mango acquisition complete: {len(list(original_dir.glob('*')))} files in {original_dir}.")


if __name__ == "__main__":
    acquire_banana()
    acquire_apple()
    acquire_mango()
