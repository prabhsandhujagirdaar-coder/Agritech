# AgriChain AI — Phase 14D: Banana Training Preparation & Apple Fruit-Crop Generation Report

**Phase:** Phase 14D: Banana Training Preparation and Apple Fruit-Crop Generation  
**Date:** 2026-10-29  
**Execution Environment:** Windows (Python 3.13 Virtualenv, Pillow, PyTorch)  
**Status:** **100% COMPLETE & VERIFIED (READY FOR TRAINING REVIEW)**  

---

## 1. Executive Summary

Phase 14D has completed the prerequisites for multi-fruit model training:
1. **Banana Ripeness Classifier Preparation (PASS):**
   - Validated all 1,960 image paths, labels, and file integrity across `train` (1,370), `val` (293), and `test` (297) splits.
   - Verified 100% disjointness by both image SHA-256 hash and capture cluster group.
   - Confirmed synchronized split partitioning with the Banana Variety dataset.
   - Proposed a reproducible transfer-learning ResNet18 baseline configuration (`ml/configs/resnet18_banana_ripeness.json`).
   - Strict rule honored: **Zero training executed** pending review.
2. **Apple Individual-Fruit Crop Generation (PASS):**
   - Read VIA polygon annotations and successfully extracted **2,574 valid individual-fruit crops** with a 5% margin.
   - Excluded the single non-standard `unknown` instance (`test/IMG_54350.jpg`, region index 3) with full audit logging.
   - Preserved scene-level split boundaries: all crops inherited the exact split (`train`, `val`, `test`) of their source orchard image.
   - Stored crops in `ml/data/processed/apple_crops_v1/` and created versioned manifests in `ml/data/manifests/apple_crops_v1/`.
   - Documented the **CC BY-NC 4.0** license restriction.
3. **Mango & Guava Safeguards (PASS):**
   - Active Guava checkpoint (`best_guava_resnet18.pth`, SHA-256 `b213059f6b974491...`) certified untouched.
   - Mango Harumanis strictly maintained in `BLOCKED` status for production deployment due to small sample size ($N=23$ Rotten).
   - No models activated in the registry.

---

## 2. Banana Ripeness Dataset Verification Matrix

### 2.1 Split Disjointness & Integrity

| Split | Images | Corrupted Files | SHA-256 Disjointness | Group ID Disjointness | Synchronized with Variety Split? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 1,370 | 0 | 100% Disjoint (0 overlap) | 100% Disjoint (0 overlap) | **YES (100% SHA match)** |
| **Val** | 293 | 0 | 100% Disjoint (0 overlap) | 100% Disjoint (0 overlap) | **YES (100% SHA match)** |
| **Test** | 297 | 0 | 100% Disjoint (0 overlap) | 100% Disjoint (0 overlap) | **YES (100% SHA match)** |
| **Total** | **1,960** | **0** | **ZERO LEAKAGE** | **ZERO LEAKAGE** | **PERFECT ALIGNMENT** |

### 2.2 Class Distribution Across Splits

| Class Name | Train Split (70%) | Val Split (15%) | Test Split (15%) | Total Original Samples | Class % |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Half_Ripe** | 340 | 73 | 75 | 488 | 24.9% |
| **Overripe** | 314 | 66 | 68 | 448 | 22.9% |
| **Ripe** | 431 | 93 | 92 | 616 | 31.4% |
| **Unripe** | 285 | 61 | 62 | 408 | 20.8% |
| **Total** | **1,370** | **293** | **297** | **1,960** | **100.0%** |

### 2.3 Proposed Banana ResNet18 Training Configuration
Saved at [`ml/configs/resnet18_banana_ripeness.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_banana_ripeness.json):
- **Base Architecture:** ResNet18 (PyTorch `ResNet18_Weights.DEFAULT`)
- **Number of Classes:** 4 (`Unripe`: 0, `Half_Ripe`: 1, `Ripe`: 2, `Overripe`: 3)
- **Transfer Learning Strategy:** Freeze `conv1`, `bn1`, `layer1`, `layer2`; fine-tune `layer3`, `layer4`, and `fc` head.
- **Dropout:** 0.2 before final projection.
- **Optimizer:** AdamW (lr_head = 1e-4, lr_backbone = 1e-5, weight_decay = 0.01).
- **Scheduler:** CosineAnnealingLR (T_max = 25, eta_min = 1e-6).
- **Loss Function:** Weighted Cross-Entropy Loss with label smoothing ($0.05$).
- **Color Invariant Augmentations:** Random crop (224 x 224), horizontal flip (p=0.5), rotation (+/- 15 deg), mild brightness/contrast jitter (+/- 10%). **Hue jitter is strictly 0.0** to preserve critical ripeness color cues.
- **Early Stopping:** Patience $= 6$ epochs on validation macro-F1.

---

## 3. Apple Individual-Fruit Crop Generation

### 3.1 Cropping Methodology
- **Source Dataset:** *A multi-stage, pixel-level annotated apple dataset for precision agriculture research* (DOI `10.17632/gfcmdbvw65.4`).
- **Polygon Mask Processing:** Each closed polygon mask in `train.json`, `val.json`, and `test.json` was converted to its tight bounding box `[x_min, y_min, x_max, y_max]`.
- **5% Margin Application:**
  - `pad_x = round(0.05 * w)`, `pad_y = round(0.05 * h)`
  - `bbox_crop = [max(0, x_min - pad_x), max(0, y_min - pad_y), min(W, x_max + pad_x), min(H, y_max + pad_y)]`
- **Scene-Level Split Invariance:** Crops extracted from an orchard image in split $S$ are stored strictly in split $S$. Zero orchard-scene cross-contamination exists.

### 3.2 Crop Distribution Matrix

| Split | Immature Crops | Semi-Mature Crops | Mature Crops | Total Valid Crops | Source Orchard Scenes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 713 | 618 | 650 | **1,981** | 1,041 |
| **Val** | 67 | 60 | 58 | **185** | 126 |
| **Test** | 141 | 136 | 131 | **408** | 239 |
| **Total** | **921** | **814** | **839** | **2,574** | **1,406** |

### 3.3 Excluded Annotations Record
- Exactly 1 annotation was excluded across the entire dataset:
  - **Source Scene:** `test/IMG_54350.jpg` (key `IMG_54350.jpg77789`, region index 3)
  - **Label:** `"unknown"`
  - **Reason:** Non-standard classification label; does not correspond to an agronomic maturity stage.
  - **Log Location:** [`ml/data/manifests/apple_crops_v1/exclusions.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/apple_crops_v1/exclusions.json)

### 3.4 Quality & Resolution Profile
- **Degraded Polygons (<3 points):** 0
- **Empty Bounding Boxes ($w=0$ or $h=0$):** 0
- **Tiny Crops (<20 px):** 1 crop ($12 	imes 17$ px, distant canopy fruit) flagged in manifest.
- **Median Crop Size:** $97 	imes 96$ px.
- **Maximum Crop Size:** $264 	imes 277$ px.

### 3.5 License Constraint Notice
> [!WARNING]
> **CC BY-NC 4.0 Compliance Notice:**  
> The generated apple crops inherit the Creative Commons Attribution-NonCommercial 4.0 license from the original authors (Wang & Wang, 2026). These crops and any models trained on them are approved for research, benchmarking, and internal evaluation within AgriChain AI, but cannot be deployed into commercial production without separate commercial licensing.

---

## 4. Safeguards & System Invariants

1. **Guava Production Model:** Checkpoint `ml/artifacts/best_guava_resnet18.pth` (SHA-256 `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4`) is certified unchanged.
2. **Model Registry State:** Model registry `backend/app/services/model_registry.py` strictly enforces `CERTIFIED_ACTIVE` for Guava and `AWAITING_TRAINING` for Banana, Apple, and Mango.
3. **Mango Restriction:** Mango Harumanis remains blocked from production training due to sample size deficit ($N=23$ Rotten).
4. **Zero Model Training:** In strict compliance with Phase 14D instructions, no training epochs were executed.

---

## 5. Artifact & Manifest File Locations

- **Banana Manifests:** [`ml/data/manifests/banana_ripeness/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/banana_ripeness/)
- **Banana ResNet18 Training Config:** [`ml/configs/resnet18_banana_ripeness.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_banana_ripeness.json)
- **Apple Crops Output:** [`ml/data/processed/apple_crops_v1/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/apple_crops_v1/)
- **Apple Crop Manifests:** [`ml/data/manifests/apple_crops_v1/`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/apple_crops_v1/)
- **Exclusion Ledger:** [`ml/data/manifests/apple_crops_v1/exclusions.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/manifests/apple_crops_v1/exclusions.json)
