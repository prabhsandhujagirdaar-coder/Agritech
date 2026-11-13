# AgriChain AI — Roboflow Kinnow Dataset Audit Report

**Report Path**: `ml/data/reports/kinnow_roboflow_audit.md`  
**Dataset Target**: `ml/data/raw/kinnow_roboflow/`  
**Archive Source**: `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip` (851.73 MB)  
**Audit Mode**: Read-Only Non-Destructive Inspection  
**Audit Date**: 2026-10-15  

---

## 1. Extraction Status & Location Check

- **Target Path**: `ml/data/raw/kinnow_roboflow/`
- **Status**: **NOT EXTRACTED**.
- **Action Taken**: In accordance with the non-destructive audit mandate, the archive was **not automatically extracted**. All inspections were conducted in-memory directly from `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip`.

---

## 2. Archive Integrity & Metadata Overview

- **Archive File**: `Kinnow.v1i.yolov8.zip`
- **Actual Size**: **893,106,586 bytes** (~851.73 MB)
- **Uncompressed Size**: **892,889,229 bytes** (~851.53 MB)
- **Integrity Check (`zipfile.testzip()`)**: **PASSED** (0 corrupt files, 0 CRC-32 errors across all 1,008 archive entries).
- **Configuration File (`data.yaml`)**:
  ```yaml
  train: ../train/images
  val: ../valid/images
  test: ../test/images

  nc: 10
  names: ['Bruised', 'DU', 'Fungal', 'Healthy-kinnow', 'Insect attack', 'Unhealthy-kinnow', 'black spot', 'depresion', 'healthy-kinnow', 'orange']

  roboflow:
    workspace: fruit-mtdup
    project: kinnow-428er
    version: 1
    license: CC BY 4.0
    url: https://universe.roboflow.com/fruit-mtdup/kinnow-428er/dataset/1
  ```
- **Splits & Directories**:
  - `train/`: 354 images, 354 labels
  - `valid/`: 148 images, 148 labels
  - `test/`: **Missing entirely** from the archive (0 files), despite reference in `data.yaml`.
- **Image Dimensions & Format**:
  - 100% JPEG (`RGB`).
  - High-resolution canopy imagery: $4000 \times 3000$ (169), $4032 \times 3024$ (132), $4624 \times 3472$ (81), $4160 \times 3120$ (41), $3468 \times 4624$ (33), $6936 \times 9248$ (22), $3264 \times 2448$ (13), $3120 \times 4160$ (7), $4000 \times 2250$ (4).

---

## 3. Label Semantics: Detection vs. Ripeness

The labels in this dataset represent **object detection, physical condition, and pathological diseases/defects**, NOT biological ripeness stages:

- **Fruit Detection / Localization**: `Healthy-kinnow`, `healthy-kinnow`, `orange`
- **Fruit Condition / Marketability**: `Healthy-kinnow`, `Unhealthy-kinnow`, `healthy-kinnow`
- **Pathology / Mechanical / Pest Damage**: `Bruised`, `DU`, `Fungal`, `Insect attack`, `black spot`, `depresion`

### Three-Stage Ripeness Class Verification
- `underripe`: **0 instances** (Absent)
- `partially_ripe`: **0 instances** (Absent)
- `fully_ripe`: **0 instances** (Absent)

> [!CAUTION]
> **NO RIPENESS GROUND TRUTH**:
> Biological maturity (`underripe`, `partially_ripe`, `fully_ripe`) cannot be inferred from peel health or defect labels. A healthy fruit can be immature and underripe; a fully ripe fruit can be bruised or infected with fungal rot.

---

## 4. Class Distribution & Annotation Integrity

### Image Counts per Class (Images depicting at least one instance)
Total unique labeled images: 447 (plus 55 empty background images = 502 total images).

| Class ID | Class Name | Nature | Total Images | Train Images | Valid Images | Total Bounding Boxes |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **`0`** | `Bruised` | Physical injury | **109** | 77 | 32 | 131 |
| **`1`** | `DU` | Defect acronym | **1** | 1 | 0 | 1 |
| **`2`** | `Fungal` | Pathology (rot/mold) | **106** | 69 | 37 | 128 |
| **`3`** | `Healthy-kinnow` | Condition (Title Case) | **198** | 137 | 61 | 269 |
| **`4`** | `Insect attack` | Pest puncture | **110** | 81 | 29 | 123 |
| **`5`** | `Unhealthy-kinnow` | Condition (general) | **9** | 5 | 4 | 9 |
| **`6`** | `black spot` | Pathology (*Guignardia*) | **9** | 8 | 1 | 9 |
| **`7`** | `depresion` | Defect (Typo) | **1** | 1 | 0 | 1 |
| **`8`** | `healthy-kinnow` | Condition (Lower Case) | **11** | 7 | 4 | 13 |
| **`9`** | `orange` | Generic detection | **3** | 3 | 0 | 3 |

### Missing & Empty Annotation Files
- **Missing Label Files**: **0** (100% 1-to-1 pairing between images and `.txt` files).
- **Empty Label Files (Background/Negative Images)**:
  - `train/`: 40 empty files (11.3%)
  - `valid/`: 15 empty files (10.1%)
  - **Total**: **55 empty label files** depicting orchard canopy without labeled fruit.

---

## 5. Duplication & Evaluation Leakage Analysis

1. **Exact Content Duplicates**: **0** (all 502 images have distinct SHA-256 hashes).
2. **Taxonomic Inconsistency**:
   - `Healthy-kinnow` (class 3) and `healthy-kinnow` (class 8) are duplicate classes separated only by capitalization (combined: 209 unique images, 282 boxes).
   - Class 7 has a spelling typo (`depresion` instead of `depression`).
3. **Severe Train/Validation Leakage (Random Burst Splitting)**:
   - Images were partitioned using naive uniform random sampling rather than tree/burst-aware grouping.
   - All capture dates (`2023-02-01`, `2023-02-12`, `2023-01-28`) are interleaved across both `train` and `valid`.
   - Photos taken within 21 seconds of each other on the same tree (e.g. `20230201_103800` in valid vs `20230201_103821` in train) appear across splits.
   - Sequential camera indices (e.g. `IMG_1451`/`IMG_1452` in valid vs `IMG_1453` in train) are split, creating canopy and illumination leakage.

---

## 6. Limitations & Safest Next Steps

### Limitations:
1. **Not Suitable for Ripeness Classification**: Lacks any biological maturity stages.
2. **Missing Test Split**: Only 70/30 train/valid splits provided.
3. **Severe Class Imbalance & Unrepresented Validation Classes**: Classes `DU`, `depresion`, and `orange` have 0 instances in validation.

### Safest Next Step:
1. **Leave the Dataset Unextracted**: Do not extract into `ml/data/raw/` at this stage. Keep `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip` as-is.
2. **Do Not Train a Ripeness Model on this Dataset**: Avoid using these labels for Phase 3 maturity modeling.
3. **Continue Phase 3 Ripeness Annotation via FruitNet**: Proceed with annotating the 1,341 `primary_candidate` images in [`ml/data/processed/citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) (`Orange_Good` and `Orange_Mixed`) using the multi-attribute rubric.
4. **Future Use Case (Phase 4B)**: If on-tree fruit detection/cropping is implemented later, extract this dataset into an isolated directory and merge classes 3 and 8 to train a binary Kinnow canopy detector.
