# AgriChain AI — Phase 2 Dataset Audit & Validation Report

**Date**: 2026-10-14T15:55:43Z  
**Scope**: Comprehensive inventory, integrity check, duplicate analysis, and suitability assessment for three-stage Kinnow Mandarin ripeness classification.

---

## 1. Executive Summary Table

| Source Dataset | Total Files | Valid Images | Corrupted | Confirmed Kinnow | Ground-Truth Ripeness Labels | Usable for Target Task | License |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`oranges_in_field`** | 10059 | 5025 | 0 | 0 (Unspecified orange) | None (1 class: `orange` detection) | Unusable for 3-class ripeness | Unknown / Missing |
| **`fruitnet`** | 19526 | 19526 | 0 | 0 (Nagpur/Indian orange cohort) | None (Good/Bad/Mixed commercial quality) | Candidate for manual re-annotation | CC BY 4.0 |
| **`citrus_disease`** | 759 | 759 | 0 | 0 (Generic citrus pathology) | None (Plant diseases) | Unusable (Pathology) | Open Academic |
| **TOTALS** | **30344** | **25310** | **0** | **0** | **0** | **0 (Native)** | — |

---

## 2. Granular Inventory & Class Breakdowns

### A. Oranges in the Field (`ml/data/raw/oranges_in_field`)
- **Valid Images**: 5025 (Format: {'JPEG': 5025})
- **Task**: Object detection in orchard canopies.
- **Classes**: 9 environmental capture subfolders (time/weather conditions):
  - `MS_CLIP_MOR_SUN`: 2768 images
  - `AC_CLIP_AFT_CLO`: 1082 images
  - `AS_CLIP_AFT_SUN`: 625 images
  - `ES_CLIP_EVE_SUN`: 224 images
  - `MC_CLIP_MOR_CLO`: 126 images
  - `NI_CLIP_NIGHT`: 96 images
  - `IN_CLIP_INDOOR`: 57 images
  - `EC_CLIP_EVE_CLO`: 34 images
  - `AR_CLIP_AFT_RAI`: 13 images

- **Annotations**: 5,025 YOLO bounding box files (`labels/*.txt`) with single category `orange`.
- **Ripeness Ground Truth**: Zero.

### B. FruitNet: Indian Fruits Dataset (`ml/data/raw/fruitnet`)
- **Valid Images**: 19526 (Format: {'JPEG': 19526})
- **Fruit Distribution**:
  - `pomegranate`: 7252 images
  - `orange`: 2500 images
  - `banana`: 2485 images
  - `lime_lemon`: 2457 images
  - `guava`: 2429 images
  - `apple`: 2403 images

- **Citrus Cohort Analysis**:
  - **Orange**: 2,500 images across `Good Quality` (1,216), `Bad Quality` (1,159), `Mixed Quality` (125).
  - **Lime / Lemon**: 2,457 images across `Good Quality` (1,094), `Bad Quality` (1,085), `Mixed Quality` (278).
- **Ripeness Ground Truth**: Zero. Labels represent post-harvest physical decay and marketability, not biological maturity stages.

### C. Citrus Plant Disease Dataset (`ml/data/raw/citrus_disease`)
- **Valid Images**: 759 (Format: {'JPEG': 165, 'PNG': 594})
- **Breakdown**:
  - Leaves: 609 images (Greening: 204, Black spot: 171, Canker: 163, Healthy: 58, Melanose: 13)
  - Fruits: 150 images (Canker: 78, Healthy: 22, Black spot: 19, Greening: 16, Scab: 15)
- **Ripeness Ground Truth**: Zero.

---

## 3. Duplicate & Burst Leakage Analysis

- **Exact Duplicate Hashes (SHA-256)**: 19 groups affecting 38 images.
- **Near-Duplicate / Burst Groups (dhash)**: 2262 clusters affecting 5936 images.
- **Critical Leakage Risk**: In `FruitNet`, multiple photos of the exact same fruit specimen were taken in burst sequences. Partitioning images randomly without grouping by acquisition timestamp (`group_id`) results in identical fruit instances appearing across train and test sets.

---

## 4. Suitability Assessment for Three-Stage Kinnow Ripeness

| Target Maturity Stage | Available Ground Truth Images | Source Provenance | Suitability Verdict |
| :--- | :---: | :---: | :--- |
| **`underripe`** | **0** | None | Native ground-truth absent across all 3 archives. |
| **`partially_ripe`** | **0** | None | Native ground-truth absent across all 3 archives. |
| **`fully_ripe`** | **0** | None | Native ground-truth absent across all 3 archives. |

### Core Scientific Findings:
1. **Taxonomy Mismatch**: Commercial rot/quality (`Bad Quality` vs `Good Quality`) and disease pathology (`Huanglongbing` / Canker) are fundamentally distinct biological dimensions from ripeness stages (`underripe`, `partially_ripe`, `fully_ripe`).
2. **Cultivar Specificity**: None of the three datasets verify the Kinnow Mandarin hybrid (*King* $	imes$ *Willow Leaf*).
3. **No Synthetic / Color Shortcuts**: In accordance with rigorous scientific practices, heuristic color thresholding or automated label synthesis has been strictly rejected.

---

## 5. Final Recommendation & Next Steps

1. **Model Training Must Pause**: Long-running model training cannot begin on unverified or mismatched labels.
2. **Actionable Paths Forward**:
   - **Path A**: Acquire a certified Kinnow Mandarin maturity dataset (e.g., from Punjab Agricultural University or ICAR-CCRI repositories).
   - **Path B**: Curate an isolated subset of 600–900 individual Indian citrus images from `FruitNet` (`Orange_Good` and `Orange_Mixed`) and apply an expert-validated agricultural grading rubric for the three maturity stages with burst-level group splitting.
