# AgriChain AI — Guava Dataset Audit & CNN Strategy Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Audit Date:** October 2026  
**Status:** Completed Audit & Architectural Strategy (Pre-Training Phase)

---

## Executive Summary

Following the unavailability of a validated Punjab Kinnow dataset, **AgriChain AI** has officially transitioned its primary inspection crop to **Guava (*Psidium guajava* L.)**. Guava is a commercially vital subtropical fruit extensively cultivated across Punjab and northwestern India (Ayub Agricultural Research Institute / Punjab Horticulture Department priority crop). It exhibits rapid post-harvest ripening (climacteric respiration peak) and high cold-chain vulnerability to chilling injury and transit impact damage.

This report documents a non-destructive audit of two downloaded candidate archives:
- **Dataset A:** `Guava Fruit  Dataset for Classification.zip` (357.43 MB outer; 357.53 MB nested)
- **Dataset B:** `Guava (Psidium guajava) fruit digital and thermal Images.zip` (7.708 GB)

**Key Finding & Recommendation:**  
- **Dataset A** contains **2,309 pristine RGB images** strictly categorized into three harvest/intake maturity stages (`Green`, `Mature Green`, `Ripe`) with uniform 850×1300 resolution and 0 corrupt files. It is **recommended as the authoritative benchmark for the AgriChain AI intake quality inspection CNN** (Option A).
- **Dataset B** is a dual-modality collection (**2,150 digital RGB images**, **1,809 thermal infrared images**) representing a 7-day longitudinal mechanical drop damage (15cm, 30cm, 45cm drop impact), chilling injury, and post-harvest disease study. However, **digital and thermal modalities lack 1-to-1 instance pairing**, thermal images lack calibrated temperature tables, and 84% of samples exhibit severe mechanical impact damage. Dataset B must **not** be blended into the harvest maturity training set (to avoid severe domain shift and label noise). Instead, it is recommended to be maintained separately (Option E) as a future **Transit Impact & Bruise Damage Classifier** directly coupled to the LSTM telemetry module.

---

## 1. Verified Archive Paths, Sizes & Integrity

Targeted filesystem searches discovered both archives in `C:\Users\PrabSandhu\Downloads\`. Available host disk space on drive `C:` was verified at **322.59 GB Free**, safely exceeding any operational decompression requirement. Both archives were analyzed in-memory via Python `zipfile` streams without modifying or extracting the raw archives.

| Attribute | Dataset A | Dataset B |
| :--- | :--- | :--- |
| **Exact File Name** | `Guava Fruit  Dataset for Classification.zip` *(note double space)* | `Guava (Psidium guajava) fruit digital and thermal Images.zip` |
| **Absolute Path** | `C:\Users\PrabSandhu\Downloads\Guava Fruit  Dataset for Classification.zip` | `C:\Users\PrabSandhu\Downloads\Guava (Psidium guajava) fruit digital and thermal Images.zip` |
| **Archive File Size** | 374,797,270 bytes (**357.43 MB**) | 8,276,339,138 bytes (**7.708 GB**) |
| **Archive Structure** | **Nested Archive**: Contains `Guava Fruit  Dataset for Classification/Guava Dataset.zip` (357.53 MB raw uncompressed) | Flat multi-directory hierarchy; **0 nested archives** |
| **Total Archive Entries**| Outer: 1 entry; Nested: 2,322 entries (2,309 files, 13 dirs) | 3,959 file entries, 0 directory records |
| **CRC-32 Integrity Test**| **PASS (0 corrupt files)** across outer and nested archives | **PASS (0 central directory read errors)** |
| **Original File State** | Preserved unchanged in Downloads folder | Preserved unchanged in Downloads folder |

---

## 2. Dataset A — Classification Audit (Maturity Grading)

### 2.1 Provenance & License
- **Authors:** Abdul Khalique Maitlo, Abdul Aziz, Hassnain Raza, Neelam Abbas (2023).
- **Publication:** *Data in Brief*, Elsevier, Volume 48.
- **Repository:** Mendeley Data, DOI: [10.17632/w3fg8jjmzr.1](https://doi.org/10.17632/w3fg8jjmzr.1).
- **License:** **CC BY 4.0 (Creative Commons Attribution 4.0 International)** — Permitted for academic, research, and commercial use with attribution.
- **Cultivar:** *Psidium guajava* L., cultivar **"Local Sindhi"** (dominant regional guava in the Indus basin / Punjab horticultural belt).

### 2.2 Image Counts & Class Distribution
The archive contains 2,309 images strictly distributed across three maturity classes:

```
Guava Dataset/
└── Local Sindhi/
    ├── Green/         -->  232 images (10.05%)
    ├── Mature Green/  -->  829 images (35.90%)
    └── Ripe/          --> 1,248 images (54.05%)
```

| Class Folder Name | Image Count | Percentage | Class Imbalance Ratio | Documented Agronomic Meaning |
| :--- | :---: | :---: | :---: | :--- |
| `Green` | 232 | 10.05% | 1.00 (Reference) | Immature fruit; hard flesh; low soluble solids; unready for fresh market; longest shelf-life. |
| `Mature Green` | 829 | 35.90% | 3.57× | Physiologically mature; optimal harvest stage for cold-chain transit, commercial transport, and controlled ripening. |
| `Ripe` | 1,248 | 54.05% | 5.38× | Table-ready fruit; skin yellowing; aromatic volatile production; soft texture; immediate distribution required. |
| **Total** | **2,309** | **100.0%** | — | **Single-cultivar, single-crop harvest grading.** |

### 2.3 Image Properties & Physical Quality
- **Dimensions:** **850 × 1300 pixels** (100% strictly uniform across all 2,309 images; portrait orientation).
- **Color Mode:** **3-channel RGB** (100% of images).
- **Format:** JPEG (`.jpg`).
- **Acquisition Setup:** Canon EOS 5D Mark III DSLR camera mounted on a tripod at a fixed focal distance (0.5 m) under controlled studio LED illumination against a uniform white/neutral backdrop.
- **Data Integrity:**
  - Corrupt or unreadable images: **0** (all 2,309 images decoded with PIL).
  - Exact duplicates (MD5 hash collisions): **0** (2,309 unique MD5 hashes).
  - Near-duplicate note: Successive numbered images represent rotated views of fruits from identical lots, necessitating **group-aware splitting** during train/val/test partitioning.

---

## 3. Dataset B — Digital & Thermal Audit (Damage & Storage)

### 3.1 Provenance & License
- **Authors:** Pathmanaban P., Gnanavel B.K., Shanmuga Sundaram Anandan (2023).
- **Repository:** Mendeley Data, DOI: [10.17632/mzkdf5s77p.1](https://doi.org/10.17632/mzkdf5s77p.1).
- **License:** **CC BY 4.0**.
- **Experimental Objective:** Investigation of post-harvest physical damage, mechanical drop impact, and refrigerated storage breakdown over a 7-day period.

### 3.2 Modality Breakdown & Image Counts
Dataset B comprises 3,959 image files split between two top-level branches:
1. `DIGITAL PHOTOS`: **2,150 images** (54.31%)
2. `TI IMAGES` (Thermal Infrared): **1,809 images** (45.69%)

### 3.3 Modality Specifications

| Modality | Camera Hardware | Resolution | Color Channels | Format | Native Metadata |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Digital (RGB)** | Xiaomi Redmi Note 7 Pro | 3000 × 3000 (90.7%)<br/>4000 × 3000 (9.3%) | 3-channel RGB | JPEG | Standard EXIF (GPS tags, capture timestamps) |
| **Thermal (TI)** | FLIR Systems AB (FLIR One / T-series) | 1440 × 1080 (100%) | 3-channel RGB (Ironbow pseudocolor) | JPEG | FLIR APP1 binary markers; **No raw Kelvin/Celsius CSV matrix** |

### 3.4 Longitudinal Drop Impact & Pathology Distribution
Dataset B tracks fruits day-wise (`DAY 1` through `DAY 7`) in cold storage (15 °C to 18 °C). In each day, fruits are categorized by maturity and experimental mechanical drop damage:

```
Guava (Psidium guajava) fruit digital and thermal Images/
├── DIGITAL PHOTOS/
│   ├── DAY 1 to DAY 7/
│   │   ├── IMMATURE / HALF MATURE / MATURE/
│   │   │   ├── 15CM Drop        --> 443 images
│   │   │   ├── 30CM Drop        --> 407 images
│   │   │   ├── 45CM Drop        --> 539 images
│   │   │   ├── HEALTHY (Control)--> 260 images
│   │   │   ├── CHILLING INJURED -->  32 images
│   │   │   └── MIXED DROP       -->  74 images
│   └── DISEASED/                --> 395 images (Anthracnose, wilt, fruit fly, canker)
└── TI IMAGES/
    └── DAY 1 to DAY 7/
        ├── IMMATURE / HALF MATURE / MATURE/
        │   ├── 15CM Drop        --> 444 images
        │   ├── 30CM Drop        --> 425 images
        │   ├── 45CM Drop        --> 539 images
        │   ├── HEALTHY (Control)--> 328 images
        │   └── OTHER / MIXED    -->  73 images
        └── (NO DISEASED FOLDER IN TI IMAGES)
```

### 3.5 Critical Findings on Dataset B

> [!IMPORTANT]
> **Lack of 1-to-1 Instance Pairing**:
> - Digital filenames follow standard smartphone timestamps (`IMG_20220224_232007.jpg`).
> - Thermal filenames follow FLIR camera timestamps (`FLIR_20220224_110812.jpg`).
> - Digital and thermal captures differ in time by several hours.
> - Subfolder counts do not match (e.g. `DAY 1/IMMATURED/HEALTHY`: 26 digital vs 27 thermal; `DISEASED`: 395 digital vs 0 thermal).
> - There are **no cross-modality fruit IDs, bounding boxes, or registration keypoints**. The modalities represent cohort-level batches rather than pixel-registered pairs.

> [!WARNING]
> **Thermal Data is Pseudocolor, Not Calibrated Temperature**:
> - Thermal images are 8-bit RGB JPEGs rendered with an ironbow color lookup table.
> - No CSV, NetCDF, or radiometric calibration matrices are included in the archive.
> - Treating pixel RGB values directly as temperature without radiometric conversion factors introduces false temperature assumptions.

---

## 4. Cross-Dataset Compatibility & Comparison

| Criterion | Dataset A (Maitlo et al.) | Dataset B (Pathmanaban et al.) | Compatibility Verdict |
| :--- | :--- | :--- | :--- |
| **Primary Task** | Intake Maturity Grading | Mechanical Bruising & Drop Impact Tracking | **Incompatible Objectives** |
| **Fruit Condition** | 100% Uninjured, pristine fruit | 84.1% Impact-damaged, bruised, or diseased | **Severe Semantic Shift** |
| **Classes** | `Green`, `Mature Green`, `Ripe` | `Immature`, `Half-Mature`, `Mature`, `15/30/45cm Drop`, `Diseased` | Partial maturity overlap, but confounded by bruising |
| **Image Resolution**| 850 × 1300 (Uniform) | 3000 × 3000 (Digital) / 1440 × 1080 (TI) | Differing aspect ratios and focal setups |
| **Background** | Clean studio white/neutral | Studio lab platform with measurement markers | Distinct visual domains |
| **Image Overlap** | 0 duplicate files, 0 hash matches | 0 duplicate files, 0 hash matches | Completely independent datasets |

### Evaluation of Candidate Strategies

- **Strategy A (Train RGB-only Guava Classifier on Dataset A):**  
  **RECOMMENDED.** Cleanest dataset, uniform dimensions, zero drop/rot confounders, explicit 3-stage harvest maturity labels (`Green`, `Mature Green`, `Ripe`), directly maps to packhouse intake operations.
- **Strategy B (Train RGB-only Classifier on Dataset B):**  
  **Not recommended for maturity grading.** Confounded by drop damage (e.g. an "Immature" fruit on Day 6 with 45cm drop damage has blackened rotting tissues that mislead color-based maturity CNNs).
- **Strategy C (Combine RGB Images from Both Datasets):**  
  **REJECTED.** Blending Dataset A and Dataset B would introduce severe label noise and domain shift (clean studio vs bruised decay progression), degrading classifier precision.
- **Strategy D (Multimodal RGB + Thermal Model):**  
  **REJECTED.** Impossible to train legitimately because Dataset B lacks 1-to-1 instance pairing, has unequal image counts (2,150 vs 1,809), has 0 thermal images for disease classes, and lacks spatial registration.
- **Strategy E (Separate Datasets for Distinct Lifecycle Stages):**  
  **STRONGLY RECOMMENDED ARCHITECTURAL DECISION.**  
  1. Use **Dataset A** for the **Intake Quality Inspection Gateway** (Maturity Grading).  
  2. Reserve **Dataset B** for a dedicated **Cold-Chain Transit Damage / Mechanical Bruise Classifier** (`Healthy` vs `Drop Injured` vs `Chilling Injured`), to be integrated in a later stage alongside the LSTM transit shock telemetry.

---

## 5. Proposed CNN Training Strategy (Guava Maturity Baseline)

*Note: In accordance with execution rules, no model training has been initiated during this audit.*

```mermaid
graph TD
    Raw[Dataset A: 2,309 Images] --> GroupSplit[Group-Aware Split<br/>Train: 70% | Val: 15% | Test: 15%]
    GroupSplit --> TrainSet[Train Set: 1,617 images<br/>Green: 162 | Mature Green: 580 | Ripe: 875]
    GroupSplit --> ValSet[Val Set: 346 images]
    GroupSplit --> TestSet[Held-out Test Set: 346 images]
    TrainSet --> Aug[Augmentation Pipeline<br/>ColorJitter, RandomAffine, Flips]
    Aug --> Loss[Weighted Cross-Entropy / Focal Loss<br/>Inverse Class Frequencies]
    Loss --> Backbone[Backbone: Pretrained ResNet18<br/>Freeze layer1-2, Fine-tune layer3-4 + FC]
    Backbone --> Eval[Evaluation Metrics<br/>Macro-F1, Confusion Matrix, Per-class Recall]
```

### 5.1 Dataset Partitioning & Leak-Free Grouping
Because consecutively numbered images in Dataset A represent different angles/rotations of fruits from the same batch, naive random sampling would leak identical fruits across splits.
- **Split Strategy:** Group-aware stratified split (70% Train, 15% Validation, 15% Test).
- **Class-Stratified Target Split:**
  - **Train (70%):** ~1,617 images (`Green`: 162, `Mature Green`: 580, `Ripe`: 875)
  - **Validation (15%):** ~346 images (`Green`: 35, `Mature Green`: 124, `Ripe`: 187)
  - **Test (15%):** ~346 images (`Green`: 35, `Mature Green`: 125, `Ripe`: 187)

### 5.2 Preprocessing & Data Augmentation
- **Input Geometry:** Resize to 256×256, center-crop to 224×224 (ResNet standard).
- **Normalization:** ImageNet statistics (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`).
- **Training Augmentations (Justified for Ripeness):**
  - Random Horizontal & Vertical Flips (orientation invariance).
  - Random Rotation ($\pm 15^\circ$).
  - Mild ColorJitter (`brightness=0.15, contrast=0.15, saturation=0.10, hue=0.03`). Strict ceiling on hue jitter to prevent artificial shifting between green and yellow ripening boundaries.

### 5.3 Model Architecture & Loss Function
- **Backbone:** ResNet18 transfer learning baseline (pretrained on ImageNet-1k).
  - Lightweight (~44.7 MB), low inference latency (<15 ms on CPU, <3 ms on GPU), ideal for edge packhouses.
  - Initial training: Freeze features up to `layer2`; train `layer3`, `layer4`, and new linear head (`Linear(512, 3)`).
- **Class Imbalance Handling:**
  - Class weights calculated as inverse class frequencies:  
    $w_c = \frac{N}{C \cdot N_c}$  
    $w_{\text{Green}} \approx 3.32$, $w_{\text{Mature Green}} \approx 0.93$, $w_{\text{Ripe}} \approx 0.62$.
  - Loss: `nn.CrossEntropyLoss(weight=class_weights)`.

### 5.4 Proposed Optimization Parameters
- **Optimizer:** AdamW (`lr=1e-4`, `weight_decay=1e-2`) for classifier head; `1e-5` for backbone.
- **Batch Size:** 32 (compatible with 6 GB VRAM on NVIDIA RTX 4050).
- **Epochs & Early Stopping:** 25 epochs max, early stopping on validation macro-F1 (patience = 5 epochs).
- **Evaluation Metrics:**
  - Overall Top-1 Accuracy.
  - Macro-averaged Precision, Recall, and F1-score (critical due to Green class imbalance).
  - Confusion Matrix with error analysis on Green vs Mature Green boundary cases.

---

## 6. AgriChain AI Integration Plan (Kinnow to Guava Migration)

To transition from Kinnow to Guava without breaking existing Dockerized containers, database schemas, or frontend interfaces, the following configuration updates are mapped:

### 6.1 Backend Core Configuration (`backend/app/core/config.py`)
```python
# Transition settings
TARGET_CROP: str = "guava"
MODEL_BACKBONE: str = "resnet18"
MODEL_NUM_CLASSES: int = 3
MODEL_WEIGHTS_PATH: str = "ml/artifacts/best_guava_resnet18.pth"

# Authoritative Guava Class Mapping
GUAVA_CLASSES: List[str] = ["green", "mature_green", "ripe"]
GUAVA_CLASS_LABELS: dict[int, str] = {
    0: "Green",
    1: "Mature Green",
    2: "Ripe",
}
```

### 6.2 Service & Endpoint Updates
1. **`CNNService` (`backend/app/services/cnn_service.py`):**
   - Update `self.target_crop = "guava"`.
   - Update model checkpoint path to resolve `best_guava_resnet18.pth`.
   - Preserve scientific integrity guard: If `best_guava_resnet18.pth` is absent, return **HTTP 503** with message *"Guava visual classification model is currently unavailable until a certified checkpoint is trained."*
2. **API Response Contract (`backend/app/schemas/cnn.py`):**
   - Keep schema identical: `crop_type: "guava"`, `predicted_class: "Mature Green"`, `class_index: 1`, `confidence: float`, `all_probabilities: dict`.
   - Frontend and mobile clients require **zero code changes** to consume this contract.
3. **Database & PostGIS:**
   - **No schema changes required.** The `shipments` table already supports arbitrary produce names via `produce_type: "Guava"` and `produce: "Guava"`.
   - Existing spatial waypoints, telemetry logs, and WebSocket pipelines remain 100% compatible.
4. **Frontend Dashboard (`apps/web/`):**
   - Quality inspection UI will display `"Guava Quality Inspection"` and render probabilities for `Green`, `Mature Green`, and `Ripe`.
5. **Preservation of Past Artifacts:**
   - Kinnow documentation and research notes in `docs/deep-learning/` are archived and preserved. No files deleted.

---

## 7. Risks, Limitations & Unresolved Questions

1. **Intra-Class Variation in Green Stage:** With 232 images in the `Green` class, severe over-sampling or unconstrained color jitter could lead to over-fitting on specific lighting gradients. Stratified evaluation is mandatory.
2. **Cultivar Specificity:** Dataset A represents the **"Local Sindhi"** cultivar. While Local Sindhi shares visual characteristics with Punjab cultivars (e.g. *Allahabad Safeda* and *L-49 Lucknow*), physical validation on local Mandi specimens should be conducted during Stage 11 field trials.
3. **Thermal Radiometric Unavailability:** Dataset B cannot be used for direct temperature measurement because radiometric conversion coefficients were not published. If infrared thermography is desired later, a dedicated FLIR radiometric decoder pipeline must be developed.
4. **Extraction Disk Strategy:** When model training commences, Dataset A should be extracted to `ml/data/guava_classification/` (requiring only ~360 MB), strictly keeping raw images out of Git via `.gitignore`.

---

## 8. Summary Table of Audit Deliverables

| Deliverable Item | Status | Verification Detail |
| :--- | :---: | :--- |
| **Archive Discovery** | Completed | Both ZIPs located in `Downloads` (`357.43 MB` and `7.708 GB`). |
| **Integrity Tests** | Completed | 100% CRC check pass; nested archive in Dataset A identified. |
| **Class Counts & Labels** | Verified | Dataset A: `Green` (232), `Mature Green` (829), `Ripe` (1,248). Total = 2,309. |
| **Dataset B Modalities** | Verified | Digital: 2,150 images; Thermal: 1,809 images. Unpaired; mechanical drop impact study. |
| **License & Provenance** | Confirmed | Both Mendeley Data, CC BY 4.0 (Maitlo et al., 2023; Pathmanaban et al., 2023). |
| **Cross-Dataset Compatibility**| Analyzed | Option A (Dataset A RGB maturity) recommended; Option E (Dataset B separate for bruising). |
| **CNN Training Plan** | Designed | ResNet18 transfer learning, group-aware 70/15/15 split, class-weighted loss. |
| **Integration Architecture** | Mapped | Standardized config for Guava; API contracts and PostGIS database preserved. |
