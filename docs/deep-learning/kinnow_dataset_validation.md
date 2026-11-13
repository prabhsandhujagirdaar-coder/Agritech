# AgriChain AI — Phase 4 Kinnow Dataset Validation Report

**Document**: `docs/deep-learning/kinnow_dataset_validation.md`  
**Dataset Archive**: `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip`  
**Evaluation Mode**: In-Memory Stream Inspection (Zero Project/Disk Extraction)  
**Evaluation Date**: 2026-10-15  
**Auditor**: AgriChain AI Data & ML Engineering Team  

---

## 1. Executive Summary & Archive Verification

A non-destructive, read-only inspection of the downloaded Kinnow dataset was performed directly from the archive in `C:\Users\PrabSandhu\Downloads\` using Python's standard `zipfile` stream parser.

| Metric | Measured Value | Status |
| :--- | :--- | :---: |
| **Archive Location** | `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip` | Confirmed |
| **Exact Archive Size** | **893,106,586 bytes** (851.73 MB) | Verified |
| **Uncompressed Footprint** | **892,889,229 bytes** (851.53 MB) | Verified |
| **CRC-32 Integrity (`testzip`)** | **PASSED** (0 corrupted blocks / 0 corrupted files) | Pristine |
| **Total Archive Entries** | 1,008 entries | Validated |
| **Total Images** | 502 images (100% JPEG) | Validated |
| **Total Annotation Files** | 502 `.txt` files (YOLO bounding box format) | Validated |
| **License** | Creative Commons Attribution 4.0 International (**CC BY 4.0**) | Open Academic |

### Internal Directory Structure
```text
Kinnow.v1i.yolov8.zip
├── data.yaml                  (Dataset configuration — 2 duplicate directory entries)
├── README.dataset.txt         (Roboflow Universe metadata & license)
├── README.roboflow.txt        (Export metadata & platform notes)
├── train/
│   ├── images/                (354 images: *.jpg)
│   └── labels/                (354 labels: *.txt)
└── valid/
    ├── images/                (148 images: *.jpg)
    └── labels/                (148 labels: *.txt)
```

> [!NOTE]
> **Missing Test Split**: While `data.yaml` references `test: ../test/images`, there is **no `test` folder** in the ZIP archive. The dataset consists solely of `train` (70.5%) and `valid` (29.5%).

---

## 2. Dataset Metadata & Configuration

### Dataset Configuration File (`data.yaml`)
Extracted and parsed directly from the archive root:

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

### Class Mapping & Global Bounding Box Frequency (687 Total Boxes)
The dataset contains **10 configured classes** with severe distribution skew and taxonomic flaws:

| Class ID | Class Name | Category Nature | Train Count | Valid Count | Total Boxes | % Share |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **`0`** | `Bruised` | Mechanical Damage | 99 | 32 | 131 | 19.07% |
| **`1`** | `DU` | Defect / Acronym | 1 | 0 | 1 | 0.15% |
| **`2`** | `Fungal` | Pathology (Mold/Rot) | 85 | 43 | 128 | 18.63% |
| **`3`** | `Healthy-kinnow` | Fruit Quality (Title Case) | 175 | 94 | 269 | 39.16% |
| **`4`** | `Insect attack` | Pest Damage | 90 | 33 | 123 | 17.90% |
| **`5`** | `Unhealthy-kinnow` | Fruit Quality (General) | 5 | 4 | 9 | 1.31% |
| **`6`** | `black spot` | Pathology (*Guignardia*) | 8 | 1 | 9 | 1.31% |
| **`7`** | `depresion` | Defect (Typo) | 1 | 0 | 1 | 0.15% |
| **`8`** | `healthy-kinnow` | Fruit Quality (Lower Case) | 9 | 4 | 13 | 1.89% |
| **`9`** | `orange` | Generic Detection | 3 | 0 | 3 | 0.44% |
| **TOTAL** | — | — | **486** | **201** | **687** | **100.0%** |

---

## 3. Image Properties & Annotation Integrity

### Image Characteristics
- **Format**: 100% JPEG (`RGB` mode, 24-bit color depth).
- **Resolution**: Very high resolution canopy and orchard images.
  - `4000 × 3000`: 169 images (33.7%)
  - `4032 × 3024`: 132 images (26.3%)
  - `4624 × 3472`: 81 images (16.1%)
  - `4160 × 3120`: 41 images (8.2%)
  - `3468 × 4624` (Portrait): 33 images (6.6%)
  - `6936 × 9248` (Ultra-high res ~64 MP): 22 images (4.4%)
  - `3264 × 2448`: 13 images (2.6%)
  - `3120 × 4160` (Portrait): 7 images (1.4%)
  - `4000 × 2250` (16:9 widescreen): 4 images (0.8%)

### Annotation Quality & Verification
- **Pairing**: Exactly 502 images match 502 label files (0 orphaned images, 0 orphaned label files).
- **Annotation Format**: Standard YOLO normalized bounding box format (`<class_id> <x_center> <y_center> <width> <height>`).
- **Coordinate Integrity**:
  - All 687 boxes have normalized coordinates within $[0.0, 1.0]$.
  - Zero degenerate boxes ($w \le 0$ or $h \le 0$).
  - Zero invalid class IDs ($< 0$ or $> 9$).
- **Background / Negative Images**:
  - `train`: 40 empty label files (11.3% of train split)
  - `valid`: 15 empty label files (10.1% of valid split)
  - Total empty images: **55 background images** without labeled fruit objects.

---

## 4. Ripeness Suitability Assessment

> [!CAUTION]
> **CRITICAL SCIENTIFIC FINDING: ZERO RIPENESS LABELS FOUND**  
> This dataset does **NOT** contain three-stage ripeness ground truth. It is **unusable** in its current form for training or evaluating ripeness classification models.

### Scientific Justifications:
1. **Absence of Ripeness Classes**:
   - `underripe`: **0 instances**
   - `partially_ripe`: **0 instances**
   - `fully_ripe`: **0 instances**
2. **Taxonomic Separation (Quality/Pathology vs. Ripeness)**:
   The classes present in the dataset reflect **external cosmetic defects, entomological damage, and fungal pathologies**:
   - Pest & Pathology: `Fungal`, `Insect attack`, `black spot`, `depresion`
   - Mechanical: `Bruised`
   - Health status: `Healthy-kinnow` vs `Unhealthy-kinnow`
3. **No Inference from Quality or Color**:
   In strict adherence to post-harvest citrus physiology:
   - "Healthy Kinnow" cannot be conflated with "Fully Ripe" (an unblemished, green, immature Kinnow is healthy but underripe).
   - "Unhealthy / Bruised / Fungal" cannot be treated as ripeness stages (a fully ripe, high-Brix Kinnow can have fungal rot, and an underripe Kinnow can suffer bruising).

---

## 5. Data Quality & Evaluation Leakage Analysis

### A. Taxonomic Inconsistencies
1. **Duplicate Class Names (`Healthy-kinnow` vs `healthy-kinnow`)**:
   - Class ID 3 (`Healthy-kinnow`) and Class ID 8 (`healthy-kinnow`) represent the exact same concept, differing only by the capital `H`.
   - Combined, they represent 282 bounding boxes (41.05% of all boxes).
2. **Spelling Typo**:
   - Class ID 7 is spelled `depresion` instead of `depression`.
3. **Extreme Underrepresentation in Validation**:
   - Class `1` (`DU`), Class `7` (`depresion`), and Class `9` (`orange`) have **zero instances in the validation split**. Any evaluation metrics ($mAP@50$, $mAP@50\text{-}95$) for these classes will be undefined ($0/0$ or $0.0$).
   - Class `6` (`black spot`) has only 1 instance in validation.

### B. Evaluation Leakage (Split Interleaving)
A forensic audit of image acquisition timestamps and sequential camera indices revealed that the dataset author applied a **naive random split** rather than a session/tree-aware split:

- **Capture Date Co-occurrence**:
  - `20230201` (Feb 1, 2023): 201 images in `train`, 88 images in `valid`.
  - `20230212` (Feb 12, 2023): 39 images in `train`, 18 images in `valid`.
  - `20230128` (Jan 28, 2023): 17 images in `train`, 7 images in `valid`.
- **Temporal Burst Proximity**:
  - `valid/images/20230201_103800...jpg` vs `train/images/20230201_103821...jpg` were captured **21 seconds apart** in the same orchard block.
  - Sequential camera index leakage: `IMG_1451` and `IMG_1452` are placed in `valid`, while `IMG_1453` is placed in `train`.
- **Impact**: Evaluating a model on the provided validation set yields inflated performance metrics due to canopy, lighting, and orchard background leakage.

---

## 6. Proposed Storage & Extraction Footprint

If the project requires extracting these images in a subsequent phase:

- **Required Disk Space**: **851.53 MB** (uncompressed) + safety buffer $\approx$ **1.2 GB free space required**.
- **Proposed Extraction Target**:
  `ml/data/raw/kinnow_yolov8/`
- **Isolation Invariant**:
  Must remain completely isolated from the primary maturity curation pipeline (`ml/data/processed/citrus_candidate_review.csv`) to avoid polluting candidate review pools with incompatible bounding box schemas.

---

## 7. Conclusions & Recommended Next Steps

### Summary Verdict:
The archive `Kinnow.v1i.yolov8.zip` is a valid, high-resolution object-detection dataset depicting verified Pakistani/Indian Kinnow Mandarins in orchard and harvest settings under CC BY 4.0. However, **it provides zero three-stage ripeness labels**.

### Recommended Action Plan:
1. **DO NOT Train a Ripeness Model on this Dataset**:
   Attempting to train the Phase 3 ripeness classifier on this dataset will fail to learn maturity stages and will introduce erroneous defect-to-ripeness biases.
2. **Keep the ZIP Archived**:
   Retain the ZIP file in `C:\Users\PrabSandhu\Downloads\Kinnow.v1i.yolov8.zip` without extracting it into the Git repository or workspace.
3. **Strategic Value for Future Phases**:
   - **Phase 4B (Kinnow Object Detection & Canopy Localization)**:
     Merge class 3 (`Healthy-kinnow`) and class 8 (`healthy-kinnow`) into a unified `kinnow` class, and use this dataset to train a YOLOv8-nano orchard detector to crop individual fruit from canopy photos.
   - **Phase 4C (Kinnow Ripeness Re-annotation)**:
     The 502 raw images are high-resolution, verified Kinnow specimens. Detected fruit crops can be imported into `ml/src/annotation_tool.py` to generate genuine human ground-truth labels for `underripe`, `partially_ripe`, and `fully_ripe`.
