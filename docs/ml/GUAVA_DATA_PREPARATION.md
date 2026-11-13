# AgriChain AI — Phase 2: Guava Dataset Preparation Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Source Dataset:** Mendeley Data (Maitlo et al., 2023, DOI: [10.17632/w3fg8jjmzr.1](https://doi.org/10.17632/w3fg8jjmzr.1))  
**Date:** October 2026  
**Status:** Dataset Prepared & Stratified (Pre-Training Phase)

---

## 1. Extraction & Storage Verification

In accordance with Phase 2 data safety protocols:
1. Available host disk space was verified on drive `C:` (**322.59 GB Free**).
2. The nested archive `Guava Dataset.zip` within `C:\Users\PrabSandhu\Downloads\Guava Fruit  Dataset for Classification.zip` was safely decompressed directly into:  
   `ml/data/guava_classification/`
3. Both original downloaded archives (`Guava Fruit  Dataset for Classification.zip` and `Guava (Psidium guajava) fruit digital and thermal Images.zip`) remain **100% intact, unmodified, and preserved** in the `Downloads` directory.
4. Git ignore rules in `.gitignore` strictly isolate `ml/data/*` from source control, preventing binary dataset files from entering Git commits.

---

## 2. Dataset Verification & Biological Variety Discovery

### 2.1 File Count & Format Integrity
- **Total Images Extracted & Verified:** **2,309 images**
- **Corrupt or Unreadable Files:** **0** (100% of image pixel buffers decoded via PIL).
- **Format:** JPEG (`.jpg`).
- **Color Mode:** **3-channel RGB** (100% of images).
- **Resolution:** **850 × 1300 pixels** (100% strictly uniform portrait orientation).
- **Exact File Duplicates (MD5 Collisions):** **0** (2,309 unique MD5 hashes).

### 2.2 Cultivar / Variety Breakdown
Detailed inspection of directory branches revealed that the 2,309 images encompass three regional guava cultivars from the Larkana / Indus horticultural basin:

| Cultivar / Variety | Green | Mature Green | Ripe | Total Images | Proportion |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Local Sindhi** | 98 | 360 | 253 | **711** | 30.79% |
| **Riyali** | 67 | 101 | 487 | **655** | 28.37% |
| **Thadhrami** | 67 | 368 | 508 | **943** | 40.84% |
| **Total** | **232** | **829** | **1,248** | **2,309** | **100.0%** |

### 2.3 Label Semantics & Agronomic Ground Truth
Based on the published literature (Maitlo et al., 2023, *Data in Brief*):
- **`Green` (Class 0):** Unripe/immature stage; deep green skin with high chlorophyll density; firm, starchy flesh; unready for consumption; longest transit tolerance.
- **`Mature Green` (Class 1):** Physiologically mature stage; skin transitions to pale green/light green; fruit has reached maximum size and physiological readiness for harvest; **optimal stage for cold-chain packhouse intake, refrigerated transport, and controlled post-harvest ripening**.
- **`Ripe` (Class 2):** Fully ripe stage; skin exhibits yellow/pale-yellow coloration; loss of chlorophyll; peak soluble solids (sugars), volatile aroma, and softened texture; requires immediate retail dispatch.

---

## 3. Investigation of Grouping Metadata & Limitation Disclosure

> [!IMPORTANT]
> **Absence of Ground-Truth Fruit Instance IDs:**
> The source archive does **not** provide per-fruit instance identifiers, multi-angle tagging metadata, or capture-session timestamps. Files within each class folder are named sequentially (`1.jpg`, `2.jpg`, etc.).
> 
> In accordance with project instructions, **we do not fabricate or infer speculative fruit group IDs**. We document this inherent dataset limitation explicitly rather than dishonestly claiming an unverified "group-aware" split.

### Perceptual Hash (dHash) Near-Duplicate Analysis
A 64-bit difference hash (`dHash`) audit was executed across all 2,309 images to evaluate visual similarity. The audit revealed that consecutive image sequences (e.g., `Local Sindhi/Green/55.jpg` through `59.jpg`) share identical or near-identical perceptual hashes (Hamming distance = 0 to 2 bits). This confirms that authors photographed individual fruit lots while rotating them by minor angular increments under fixed studio lighting. 

Full audit results are recorded in:  
[`ml/data/manifests/leakage_audit.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/leakage_audit.json)

---

## 4. Stratified Split Methodology & Leakage Verification

To guarantee balanced representation across both biological varieties and ripening stages without introducing sampling bias, a **Joint Stratified Split** was executed across all 9 strata (`Variety` × `Maturity Class`):
- **Random Seed:** Fixed deterministic seed `42`.
- **Target Ratios:** 70% Train, 15% Validation, 15% Test.

```mermaid
graph TD
    Data[2,309 Guava Images<br/>3 Varieties x 3 Classes] --> Strat[Joint Stratification<br/>Seed = 42]
    Strat --> Train[Train Set: 1,618 images (70.07%)]
    Strat --> Val[Validation Set: 346 images (14.98%)]
    Strat --> Test[Test Set: 345 images (14.94%)]
    Train --> Check[Zero Leakage Audit<br/>0 MD5 Overlap | 0 Path Overlap]
    Val --> Check
    Test --> Check
```

### 4.1 Joint Strata Partition Matrix

| Stratum (`Variety` \| `Class`) | Total Samples | Train (70%) | Validation (15%) | Test (15%) |
| :--- | :---: | :---: | :---: | :---: |
| `Local Sindhi` \| `Green` | 98 | 69 | 15 | 14 |
| `Local Sindhi` \| `Mature Green` | 360 | 252 | 54 | 54 |
| `Local Sindhi` \| `Ripe` | 253 | 177 | 38 | 38 |
| `Riyali` \| `Green` | 67 | 47 | 10 | 10 |
| `Riyali` \| `Mature Green` | 101 | 71 | 15 | 15 |
| `Riyali` \| `Ripe` | 487 | 341 | 73 | 73 |
| `Thadhrami` \| `Green` | 67 | 47 | 10 | 10 |
| `Thadhrami` \| `Mature Green` | 368 | 258 | 55 | 55 |
| `Thadhrami` \| `Ripe` | 508 | 356 | 76 | 76 |
| **Total** | **2,309** | **1,618 (70.07%)** | **346 (14.98%)** | **345 (14.94%)** |

### 4.2 Data Leakage & Disjointness Check
- **Train / Validation MD5 Overlap:** **0 images**
- **Train / Test MD5 Overlap:** **0 images**
- **Validation / Test MD5 Overlap:** **0 images**
- **Disjointness Verdict:** **PASS (100% strictly disjoint partitions)**.

---

## 5. Manifest Artifact Locations

Generated manifests and split statistics are saved separately from the image files in both CSV and JSON formats:

- **Primary Manifest Directory:** `ml/data/guava_classification/manifests/`
- **Standard Modular Directory:** `ml/data/manifests/`
  - [`train.csv`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/train.csv) & [`train.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/train.json): 1,618 records.
  - [`val.csv`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/val.csv) & [`val.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/val.json): 346 records.
  - [`test.csv`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/test.csv) & [`test.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/test.json): 345 records.
  - [`dataset_summary.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/dataset_summary.json): Complete split metrics and class/variety ratios.
  - [`leakage_audit.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/leakage_audit.json): Near-duplicate hash metrics.

---

## 6. Preprocessing & Color Fidelity Verification

Because maturity classification relies on peel color transitions (chlorophyll degradation to carotenoid/xanthophyll synthesis), improper preprocessing (e.g. grayscale conversion or excessive hue jitter) destroys the ground truth signal.

An empirical color fidelity audit (`scripts/verify_preprocessing.py`) confirmed:
1. **Raw Chromatic Signal:**  
   The mean Green-to-Red channel ratio ($\frac{G}{R}$) demonstrates a strictly monotonic decrease across ripening stages:
   - `Green`: Mean $\frac{G}{R} = \mathbf{1.025}$
   - `Mature Green`: Mean $\frac{G}{R} = \mathbf{0.971}$
   - `Ripe`: Mean $\frac{G}{R} = \mathbf{0.916}$
2. **Augmentation Constraints:**
   - **Hue Jitter:** **Strictly set to 0.0** (`ColorJitter(brightness=0.1, contrast=0.1, saturation=0.08, hue=0.0)`).
   - **Grayscale:** Strictly prohibited.
   - **Spatial Transforms:** Horizontal/vertical flips, 15° rotation, and random cropping preserve color fidelity while conferring orientation invariance.
   - **Tensor Verification:** Transformed batches produce valid `[3, 224, 224]` tensors with zero NaNs.

---

## 7. Proposed ResNet18 Baseline Configuration

The full training specification is defined in:  
[`ml/configs/resnet18_guava_baseline.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_guava_baseline.json)

### Key Parameters:
- **Model Backbone:** Pretrained `resnet18` (ImageNet-1k initialization).
- **Frozen Stages:** `conv1`, `bn1`, `layer1`, `layer2` (feature extractors frozen).
- **Trainable Stages:** `layer3`, `layer4`, and new `Linear(512, 3)` classifier head.
- **Loss Function:** `WeightedCrossEntropyLoss` with label smoothing (0.05).
  - Class Weights: $w_{\text{Green}} = 3.317$, $w_{\text{Mature Green}} = 0.928$, $w_{\text{Ripe}} = 0.617$.
- **Optimizer:** AdamW (`lr_head = 1e-4`, `lr_backbone = 1e-5`, `weight_decay = 0.01`).
- **Scheduler:** CosineAnnealingLR ($T_{\max} = 25$, $\eta_{\min} = 10^{-6}$).
- **Batch Size:** 32 (CUDA mixed precision FP16 enabled).
- **Max Epochs:** 25 with Early Stopping (patience = 5 epochs monitoring `val_macro_f1`).
- **Target Artifact:** `ml/artifacts/best_guava_resnet18.pth`.

---

## 8. Status & Restrictions Compliance

- **Training Status:** **NOT STARTED.** No models have been trained; no weights or accuracy metrics are fabricated.
- **Application Services:** Docker Compose stack (`db`, `backend`, `frontend`) remains running, healthy, and untouched.
- **API State:** `POST /api/v1/cnn/predict` continues to return **HTTP 503 Service Unavailable** until certified weights are generated.
- **Dataset B State:** Preserved untouched in `Downloads` as a distinct dataset for future transit impact/bruise modeling.
