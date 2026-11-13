# AgriChain AI — Phase 14B: Multi-Fruit Dataset Acquisition & Verification Report

**Phase:** Phase 14B: Dataset Acquisition  
**Date:** 2026-10-29  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary

Phase 14B has successfully acquired, extracted, and verified raw, unaugmented datasets for all target commodities in the AgriChain AI multi-fruit expansion:
1. **Guava (Psidium guajava):** Active baseline preserved untouched. Model checkpoint certified active at `ml/artifacts/best_guava_resnet18.pth`.
2. **Banana (Musa acuminata / paradisiaca):** Acquired official **BananaID** (DOI `10.17632/h6n5srjjyw.1`, CC BY 4.0). Extracted unaugmented Ripeness (4 classes, 1,960 images) and Variety (5 varieties, 1,960 images) subsets; excluded 7,000 pre-augmented duplicates.
3. **Apple (Malus domestica):** Acquired official **Apple Multi-Stage Phenotyping Dataset** (DOI `10.17632/gfcmdbvw65.4`, CC BY-NC 4.0). Extracted 1,406 orchard images across train/val/test splits and preserved original VIA JSON annotations (2,574 polygon masks across Immature, Semi-mature, Mature).
4. **Mango (Mangifera indica):** Acquired official **Harumanis Mango Dataset** (DOI `10.17632/x6bcr3fkj5.4`, CC BY 4.0). Downloaded all 14 metadata files and 272 original field images across 4 classes; documented sample size deficit.

---

## 2. Dataset Inventory & Verification Matrix

| Commodity | Official Source & DOI | License | Local Raw Path | Original Samples | Classes / Taxonomy | Integrity Check | Checkpoint Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Guava** | Sindh Agriculture Univ / Local Harvest | Academic | `ml/data/guava_classification/` | 2,309 images | Green, Mature Green, Ripe (3 classes) | 100% OK (0 corrupt) | **CERTIFIED ACTIVE** (v2.0.0, ResNet18) |
| **Banana** | BananaID (`10.17632/h6n5srjjyw.1`) | CC BY 4.0 | `ml/data/raw/banana/` | 1,960 ripeness / 1,960 variety | Unripe, Half-ripe, Ripe, Overripe (4 classes) | 100% OK (0 corrupt) | *AWAITING TRAINING* |
| **Apple** | Apple Phenotyping (`10.17632/gfcmdbvw65.4`) | CC BY-NC 4.0 | `ml/data/raw/apple/` | 1,406 orchard images | Immature, Semi-mature, Mature (3 classes, 2,574 masks) | 100% OK (0 corrupt) | *AWAITING TRAINING* |
| **Mango** | Harumanis Mango (`10.17632/x6bcr3fkj5.4`) | CC BY 4.0 | `ml/data/raw/mango/` | 272 field images | UNRIPE, SEMI-RIPE, RIPE, ROTTEN (4 classes) | 100% OK (0 corrupt) | *AWAITING TRAINING* |

---

## 3. Detailed Dataset Audits

### 3.1 Guava (Production Baseline)
- **Status:** CERTIFIED ACTIVE
- **Checkpoint:** `ml/artifacts/best_guava_resnet18.pth` (44,796,363 bytes, SHA-256: `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4`)
- **Total Images:** 2309
- **Varieties:** Local Sindhi, Riyali, Thadhrami
- **Stage Distribution:** {
  "Green": 232,
  "Mature Green": 829,
  "Ripe": 1248
}

### 3.2 Banana (BananaID)
- **Source:** *BananaID: An image dataset of banana varieties and ripeness stages in Indonesia designed for classification* (Mutrofin et al., Dec 2025).
- **DOI:** `10.17632/h6n5srjjyw.1` | **License:** CC BY 4.0
- **Archives Downloaded:**
  - `Banana_Ripeness_Dataset.zip`: 25,998,413 bytes (SHA-256: `ee5c165ab6d117c646419ad0e500c01783db68723dddf90c97b64727a7096c12`)
  - `Banana_Variety_Dataset.zip`: 25,957,121 bytes (SHA-256: `1f4c59a46a09838e6c220f928182a4aa0cce25dd26f9db1396cb89b0d9efef74`)
- **Augmentation Separation:** We deliberately isolated and downloaded only the unaugmented zip archives (total ~50 MB), bypassing the pre-augmented duplicates (635 MB).
- **Ripeness Classes:** {
  "Half_Ripe": 488,
  "Overripe": 448,
  "Ripe": 616,
  "Unripe": 408
}
- **Variety Classes:** {
  "Ambon": 468,
  "Cavendish": 380,
  "Mas": 376,
  "Raja": 424,
  "Saba": 312
}
- **Image Specifications:** Resolution ['384x256'], RGB mode, 0 corrupted files.

### 3.3 Apple Multi-Stage Phenotyping
- **Source:** *A multi-stage, pixel-level annotated apple dataset for precision agriculture research* (Data in Brief, June 2026).
- **DOI:** `10.17632/gfcmdbvw65.4` | **License:** CC BY-NC 4.0
- **Archive Downloaded:** `dataset-20260508.zip` (290,131,787 bytes, SHA-256: `049591afd4fc3529aedbd31ef9119f5ec0601ebcb8cbbd4a25b7e883fde147ce`)
- **VIA Annotations Intact:** All JSON files (`train.json`, `val.json`, `test.json` and resized counterparts) are intact and validated.
- **Instance Breakdown:**
  - Immature Apple: 921 polygon instances
  - Semi-mature Apple: 814 polygon instances
  - Mature Apple: 839 polygon instances
  - Total Instances: 2,575 polygon masks across 1,406 orchard images.

### 3.4 Harumanis Mango
- **Source:** *Dataset of Harumanis mango images for multi-modal maturity classification using ventral texture and size features* (Basaruddin, 2026).
- **DOI:** `10.17632/x6bcr3fkj5.4` | **License:** CC BY 4.0
- **Original Images Acquired:** 272 original field images collected from 5 orchards across 3 harvest seasons (2023, 2024, 2025).
- **Class Breakdown:**
  - `RIPE`: 129
  - `SEMI-RIPE`: 61
  - `UNRIPE`: 59
  - `ROTTEN`: 23 (includes IMG-140 per dataset specification)
  - Total: 272
- **Sample Deficit Notice:** With only 272 total images (~68 samples per class, and 23 for Rotten), this dataset alone is insufficient for robust generalized deep learning. For production model training, supplemental Indian mango datasets (e.g. Alphonso/Dashehari) or rigorous transfer learning strategies are required.

---

## 4. Preservation & Non-Destructive Invariants

1. **Guava Production Model:** Checkpoint `ml/artifacts/best_guava_resnet18.pth` was not touched, renamed, or retrained.
2. **Registry Status:** Models for Mango, Banana, and Apple remain gated in `AWAITING_TRAINING` (`is_validated=False`, `available=False`).
3. **No Fabricated Predictions:** Single-crop Guava inference maintains strict boundary isolation (`detected_fruit=None`).
4. **Reproducibility:** All datasets are checksummed and documented in `ml/data/manifests/raw_dataset_inventory.json`.
