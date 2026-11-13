# AgriChain AI — Dataset Architecture & Acquisition Guide

## 1. Overview & Strategy

AgriChain AI trains on verified agricultural produce datasets sourced from Mendeley Data, Kaggle research archives, and verified orchard collections.

Because raw high-resolution image sets exceed **5.4 GB (45,000+ files)**, they are excluded from Git version control to keep the repository lightweight and responsive. The repository tracks dataset manifests, class label taxonomies, splitting scripts, and verification utilities in `ml/data/manifests/` and `scripts/`.

---

## 2. Directory Layout

When populated locally, datasets follow this directory structure:

```
ml/data/
├── guava_classification/       # Local Sindhi & Allahabad Safeda guava images
│   └── Local Sindhi/
│       ├── Green/              # Unripe / firm export grade
│       ├── Mature Green/       # Harvest maturity
│       └── Ripe/               # Table consumption grade
├── raw/                        # Original uncompressed archives
├── processed/                  # Normalized 224x224 RGB tensors
├── manifests/                  # CSV/JSON manifests tracking splits & hashes
├── reports/                    # Preflight validation audit logs
└── interim/                    # Working cache for cropping & alignment
```

---

## 3. Dataset Provenance & Sources

| Crop | Dataset Name | Source Citation | Images | Primary Classes |
| :--- | :--- | :--- | :---: | :--- |
| **Guava** | Mendeley Guava Classification | Mendeley Data (Local Sindhi variety) | 1,440 | Green, Mature Green, Ripe |
| **Banana** | Banana Ripeness Multi-Class | Kaggle / University Research Archive | 2,100 | Underripe, Barely Ripe, Ripe, Overripe |
| **Apple** | Apple Defect & Scab Benchmark | FruitNet Agricultural Vision | 1,200 | Sound, Scab Lesion, Rot Spot |
| **Multi-Fruit** | Produce Benchmark Collection | Merged Agritech Vision Benchmarks | 6,500 | Guava, Banana, Apple, Mango, Kinnow, Foliage |

---

## 4. Re-acquiring & Preparing Datasets

Automated scripts are included in `scripts/` to fetch and unpack dataset archives:

```powershell
$env:PYTHONPATH="backend"

# 1. Fetch raw archives into ml/data/raw/
.\.venv\Scripts\python.exe scripts/acquire_multi_fruit_datasets.py

# 2. Extract and organize guava taxonomy
.\.venv\Scripts\python.exe scripts/prepare_guava_dataset.py

# 3. Verify dataset directory structure and manifest alignment
.\.venv\Scripts\python.exe scripts/verify_raw_datasets.py
```

