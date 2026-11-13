# AgriChain AI — Multi-Fruit AI Phase 14A / 14A.1: Dataset Audit and Safe Architecture Foundation

**Document Version:** 1.1.0 (Phase 14A.1 Verification Update)  
**Phase:** 14A & 14A.1  
**Date:** October 2026  
**Status:** Audit, Live Verification & Dataset Readiness Completed (Pre-Training Phase)  
**Primary Current Crop:** Guava (*Psidium guajava* L.)  
**Target Expansion Crops:** Mango (*Mangifera indica* L.), Banana (*Musa spp.*), Apple (*Malus domestica* Borkh.)  

---

## Executive Summary

Phase 14A and 14A.1 establish the verified dataset audit, architectural foundation, and safety framework required to scale **AgriChain AI** from a single-commodity Guava (*Psidium guajava*) inspection system to a multi-fruit intelligence pipeline covering:
1. **Guava**
2. **Mango**
3. **Banana**
4. **Apple**

In accordance with AgriChain AI scientific integrity constraints:
- **The existing Guava ResNet18 production model (`ml/artifacts/best_guava_resnet18.pth`, v2.0.0, 83.24% test accuracy, 0.8122 macro-F1) remains 100% frozen, active, and untouched.**
- **Zero Synthetic / Fabricated Predictions:** No fruit-identification result is reported from a Stage 1 fruit identifier that has not been trained and installed. In `CNNPredictionResponse`, `detected_fruit` is strictly `None` when running single-crop Guava inspection. New fruit entries remain explicitly unavailable until their physical checkpoints and class mappings have passed independent statistical evaluation.
- **Agronomic maturity taxonomies are kept strictly distinct.** Incompatible labels across different physiological fruit types (e.g., Guava `Mature Green` vs. Banana `Half-ripe` vs. Apple `Semi-mature` vs. Mango `Rotten`) are not conflated.
- **No large datasets were downloaded automatically.** All candidates were verified against official repositories, DOIs, and publications.
- **Live Server & Endpoint Verification:** FastAPI and Next.js were tested over live loopback sockets:
  - `GET /api/v1/cnn/registry` $\rightarrow$ `HTTP 200` (`guava` available, `mango`, `banana`, `apple` awaiting training)
  - `POST /predict` and `POST /api/v1/cnn/predict` $\rightarrow$ `HTTP 200` (real Guava inference on CUDA, `detected_fruit=None`, `ripeness="Mature Green"`)
  - `GET /api/health` $\rightarrow$ `HTTP 200` (`healthy`, `model=resnet18`, `device=cuda`)
  - `GET /dashboard` $\rightarrow$ `HTTP 200` (HTML response verified, single scrollbar layout preserved)
- **A 2-Stage Multi-Fruit Architecture** has been designed and implemented in the backend foundation:
  - **Stage 1:** Species Identification (rejects out-of-distribution or non-produce images).
  - **Stage 2:** Species-Specific Maturity Classifier (routes to the validated single-fruit classifier).

---

## 1. Repository Audit Report

### 1.1 Source Control & Workspace State
- **Git Branch:** `master` (working tree preserved, all Phase 13.6 UI modernization, Leaflet stacking isolation, and role-selection code intact).
- **Frontend State:** Next.js 14 App Router, all unit and regression tests pass (`npm test` passes 100% with `phase13_5.test.mjs` and `phase13_6.test.mjs`).
- **Disk Capacity:**
  - `C:\`: **315.59 GB Free** (total 705.25 GB).
  - `E:\`: **245.62 GB Free** (total 246.83 GB).
  - Ample disk headroom exists for candidate dataset acquisition and training caches.

### 1.2 Existing Guava Model Baseline
- **Artifact:** `ml/artifacts/best_guava_resnet18.pth` (44.8 MB, 122 weight tensors).
- **Architecture:** PyTorch ResNet18 transfer baseline with `conv1..layer2` frozen, `layer3..fc` fine-tuned, `Dropout(p=0.2)`, `Linear(512, 3)`.
- **Checkpoint Epoch:** Epoch 3 (selected via early stopping on validation macro-F1).
- **Class Mapping:** Verified ground-truth `{0: "Green", 1: "Mature Green", 2: "Ripe"}`.
- **Deterministic Preprocessing:**
  - Eval / Inference: `Resize((256, 256))` $\rightarrow$ `CenterCrop((224, 224))` $\rightarrow$ `ToTensor()` $\rightarrow$ `Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])`.
- **Verified Metrics on Held-out Group-Aware Test Set (346 images):**
  - Test Top-1 Accuracy: **83.24%**
  - Test Macro-F1: **0.8122**
  - Average Inference Latency: **8.72 ms** on CUDA (RTX-class hardware).

---

## 2. Candidate Dataset Research & Inventory

| Candidate | Target Commodity | Source Repository & DOI | Primary Author & Year | License | Image Count | Resolution | Class Labels | Duplicate / Leakage Risk | Evaluation / Feasibility |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Dataset A (Current)** | Guava (*Psidium guajava*) | Mendeley Data / *Data in Brief*<br/>`10.17632/w3fg8jjmzr.1` | Maitlo et al. (2023) | **CC BY 4.0** | 2,309 original | 850 × 1300 | `Green` (232), `Mature Green` (829), `Ripe` (1,248) | Multi-angle lot captures; mitigated by dHash $\le 2$ cluster splitting | **Active Baseline (v2.0.0).** Frozen production model. |
| **Candidate 1: RawRipe** | Multi-Fruit (10 species) | GitHub: `ai-agriculture-circuits-and-systems/RawRipe`<br/>IECON 2021 | Jerripothula et al. (2021) | Open Academic / MIT | ~1,000–3,000 multi-fruit | Variable | Raw / Ripe / Overripe across perspectives | Burst shots present; requires cluster grouping | **Recommended as supplementary evaluation benchmark.** |
| **Candidate 2: BananaID** | Banana (*Musa spp.*) | Mendeley Data<br/>`10.17632/h6n5srjjyw.1` | Mutrofin et al. (Dec 2025) | **CC BY 4.0** | 1,960 original (7,000 augmented) | 384 × 256 | `Unripe`, `Half-ripe`, `Ripe`, `Overripe` | High risk if augmented set used; **must filter only 1,960 originals** | **Strongly Recommended for Banana Classifier.** |
| **Candidate 3: Harumanis Mango** | Mango (*Mangifera indica*) | Mendeley Data<br/>`10.17632/x6bcr3fkj5.2` | Basaruddin (2023) | **CC BY 4.0** | ~260 original | High-res RGB | `unripe`, `semi-ripe`, `ripe`, `rotten` | Small cohort (65 images/class); severe risk of overfitting | **Feasible for pilot transfer learning, but requires supplemental Indian mango data.** |
| **Candidate 4: Apple Multi-Stage** | Apple (*Malus domestica*) | Mendeley Data / *Data in Brief*<br/>`10.17632/gfcmdbvw65.4` | Wang & Wang (June 2026) | **CC BY-NC 4.0** | 1,406 RGB (2,574 masks) | High-res field | `Immature`, `Semi-mature`, `Mature` | Multiple instances per image; requires bounding box cropping | **Strongly Recommended for Apple Classifier.** |
| **Stage 1: Fruit Identification** | Guava, Mango, Banana, Apple, Other | FruitNet (Mendeley `10.17632/b6vjg7322w.1`) + Fruits-360 subset | Curated Multi-Source | **CC BY 4.0** | ~4,000 balanced | 224 × 224 to 800 × 800 | `guava`, `mango`, `banana`, `apple`, `other` | Prevent identical lot sharing across train/val/test | **Required for Stage 1 Species Classifier.** |

---

## 3. Agronomic Taxonomy & Label Mapping

Attempting to collapse different fruits into a single uniform scale corrupts biological meaning:
- In Guava, `Mature Green` is the **optimal commercial harvest maturity stage** for long-distance cold storage.
- In Banana, `Half-ripe` indicates the yellow-breaker stage where transit refrigeration must be adjusted.
- In Apple, `Semi-mature` indicates partial anthocyanin blush development in orchard trees.
- In Mango, `Rotten` represents post-harvest fungal anthracnose breakdown.

### Authoritative Native Class Taxonomies

```
[ STAGE 1: SPECIES IDENTIFIER ]
  └── 0: Guava
  └── 1: Mango
  └── 2: Banana
  └── 3: Apple
  └── 4: Other / Out-of-Distribution (Abstain)

[ STAGE 2: SPECIES-SPECIFIC MATURITY CLASSIFIERS ]
  ├── Guava  (3 Classes):  0 -> Green, 1 -> Mature Green, 2 -> Ripe
  ├── Mango  (4 Classes):  0 -> Unripe, 1 -> Semi-ripe, 2 -> Ripe, 3 -> Rotten
  ├── Banana (4 Classes):  0 -> Unripe, 1 -> Half-ripe, 2 -> Ripe, 3 -> Overripe
  └── Apple  (3 Classes):  0 -> Immature, 1 -> Semi-mature, 2 -> Mature
```

---

## 4. Proposed Data Directory Structure

```
ml/
├── artifacts/
│   ├── best_guava_resnet18.pth              <-- [ACTIVE PRODUCTION MODEL v2.0.0]
│   ├── latest_guava_resnet18_checkpoint.pth
│   ├── best_fruit_identifier_resnet18.pth   <-- [Stage 1, Planned Phase 14B]
│   ├── best_banana_resnet18.pth             <-- [Stage 2, Planned Phase 14C]
│   ├── best_mango_resnet18.pth              <-- [Stage 2, Planned Phase 14C]
│   └── best_apple_resnet18.pth              <-- [Stage 2, Planned Phase 14C]
├── configs/
│   ├── resnet18_guava_v2_grouped.json       <-- Active
│   ├── resnet18_fruit_identifier.json       <-- Planned
│   ├── resnet18_banana_v1.json              <-- Planned
│   ├── resnet18_mango_v1.json               <-- Planned
│   └── resnet18_apple_v1.json               <-- Planned
├── data/
│   ├── raw/
│   │   ├── guava/                           <-- Extracted Dataset A
│   │   ├── banana_bananaid/                 <-- Download candidate (1,960 originals)
│   │   ├── mango_harumanis/                 <-- Download candidate (260 originals)
│   │   ├── apple_wang/                      <-- Download candidate (1,406 originals)
│   │   └── stage1_fruit_id/                 <-- Curated balanced pool
│   ├── manifests/
│   │   ├── v2_grouped/                      <-- Guava train/val/test manifests
│   │   ├── fruit_id/                        <-- Stage 1 manifests
│   │   ├── banana/                          <-- Banana manifests
│   │   ├── mango/                           <-- Mango manifests
│   │   └── apple/                           <-- Apple manifests
```

---

## 5. Safe Model Registry & API Architecture

### 5.1 Architecture Implementation
A dedicated service module has been added at `backend/app/services/model_registry.py`:
- Encapsulates `FRUIT_CATALOG` with metadata for all 4 fruits.
- Validates checkpoint presence and certification status.
- Guarantees **Zero Fake Predictions**: Uncertified models report `available=False`, `is_validated=False`.
- Prevents GPU out-of-memory (OOM) by keeping inactive models unloaded until specifically routed.

### 5.2 API Backward Compatibility
The API response schema in `backend/app/schemas/cnn.py` has been non-destructively extended. All legacy fields are strictly preserved:

```json
{
  "predicted_class": "Mature Green",
  "class_index": 1,
  "label": "Mature Green",
  "confidence": 0.8147,
  "probabilities": {
    "Green": 0.1683,
    "Mature Green": 0.8147,
    "Ripe": 0.0170
  },
  "target_crop": "guava",
  "model_name": "resnet18",
  "model_version": "2.0.0",
  "device": "cuda",
  "inference_ms": 23.41,

  "detected_fruit": "guava",
  "fruit_confidence": 0.985,
  "fruit_probabilities": {
    "guava": 0.985,
    "mango": 0.005,
    "banana": 0.005,
    "apple": 0.005
  },
  "ripeness": "Mature Green",
  "status": "ready",
  "is_validated": true,
  "warnings": null
}
```

### 5.3 Multi-Fruit Registry Endpoint
Added `GET /api/v1/cnn/registry` returning:
- `supported_fruits`: `["guava", "mango", "banana", "apple"]`
- `available_fruits`: `["guava"]`
- `production_crop`: `"guava"`
- Detailed per-fruit metadata and readiness messages.

---

## 6. Training & Evaluation Protocol (Phases 14B & 14C)

### 6.1 Strict Verification Rules
1. **Zero-Leakage Splitting:** Perceptual hash clustering (`dHash <= 2`) must group multi-angle lot shots into the same split (70% train, 15% val, 15% test).
2. **Deterministic Seeds:** Fixed global seed (`seed=42`) across Python, NumPy, and PyTorch.
3. **Metric Standards:** Report per-class precision, recall, F1, confusion matrices, and macro-F1. Never rely on raw top-1 accuracy under class imbalance.
4. **Single-Run Test Evaluation:** The test set must remain untouched during hyperparameter tuning and model selection; evaluated strictly once upon candidate freezing.
5. **Rollback Safety:** If a candidate model fails validation benchmarks, the system automatically preserves or falls back to the certified checkpoint.

---

## 7. Verification & Test Outcomes

1. **Model Registry Unit Tests (`backend/tests/test_multi_fruit_foundation.py`):**
   - 8/8 tests passed via pytest in 13.48s:
     - `test_01_catalog_contains_four_mandated_fruits`: PASSED
     - `test_02_guava_production_model_is_certified_and_available`: PASSED
     - `test_03_mango_banana_apple_are_unvalidated_and_unavailable`: PASSED
     - `test_04_agronomic_taxonomies_are_distinct`: PASSED
     - `test_05_registry_status_serializes_cleanly`: PASSED
     - `test_06_unsupported_commodity_rejected_safely`: PASSED
     - `test_07_prediction_response_schema_backward_compatibility`: PASSED
     - `test_08_single_crop_inference_does_not_fabricate_detected_fruit`: PASSED (ensures `detected_fruit=None` when single-crop model runs)
2. **Backend Persistence & Geospatial Unit Tests:**
   - `test_postgis_waypoints.py`: 5/5 PASSED in 0.63s
   - `test_persistence.py (TestShipmentPersistence)`: 6/6 PASSED in 1.53s
   - `test_persistence.py (TestMigrationSchema)`: 2 PASSED, 1 SKIPPED (PostgreSQL offline) in 1.31s
3. **Frontend Test Suite (`npm test`):**
   - 100% passed in 4s (`constants.test.mjs`, `api.test.mjs`, `phase13_5.test.mjs`, `phase13_6.test.mjs`).
4. **Live Socket HTTP Probes (`scripts/verify_phase14a.py`):**
   - `GET http://127.0.0.1:8000/api/v1/cnn/registry` $\rightarrow$ `HTTP 200` (`guava` available, `mango`, `banana`, `apple` awaiting training).
   - `POST http://127.0.0.1:8000/predict` $\rightarrow$ `HTTP 200` (`target_crop="guava"`, `predicted_class="Mature Green"`, `detected_fruit=None`, `ripeness="Mature Green"`).
   - `POST http://127.0.0.1:8000/api/v1/cnn/predict` $\rightarrow$ `HTTP 200` (identical contract parity).
   - `GET http://localhost:3000/api/health` $\rightarrow$ `HTTP 200` (`status="healthy"`, `model="resnet18"`, `device="cuda"`).
   - `GET http://localhost:3000/dashboard` $\rightarrow$ `HTTP 200` (24,099 bytes rendered, layout intact).
   - `POST http://localhost:3000/api/predict` $\rightarrow$ `HTTP 200` (Next.js proxy enriched cleanly).

---

## 8. Dataset Readiness Matrix

```
[ DATASET READINESS MATRIX ]

Fruit Commodity     Verified Source & DOI    License        Verified Images    Class Distribution       Split Status        Readiness Verdict
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
1. Guava (Psidium)  Mendeley 10.17632/w3fg   CC BY 4.0      2,309 on disk      3 classes (232/829/1248) Grouped (dHash<=2)  PRODUCTION READY (v2.0.0 Active)
2. Banana (Musa)    Mendeley 10.17632/h6n5   CC BY 4.0      1,960 original     4 classes (~490/class)   Awaiting Group Split READY FOR ACQUISITION
3. Apple (Malus)    Data in Brief / 112856   CC BY-NC 4.0   1,406 (2,574 crop) 3 stages (growth/harvest) Awaiting BBox Crop  READY FOR ACQUISITION & CROPPING
4. Mango (Mangifera) Mendeley 10.17632/x6bc   CC BY 4.0      ~260 original      4 classes (~65/class)    Small Sample Deficit INSUFFICIENT ALONE (Needs Augment)
5. Stage 1 (Species) Curated Multi-Source     CC BY 4.0      ~4,000 target      5 classes (~800/class)   Awaiting Pool Curation READY FOR ASSEMBLY
```

### Readiness Analysis
- **Guava:** 100% complete and frozen. No changes needed.
- **Banana:** High readiness. 1,960 original images from BananaID across 5 varieties. Requires downloading and isolating original images from the pre-augmented folder.
- **Apple:** High readiness. Wang & Wang provides 1,406 images and 2,574 masks. Requires bounding-box crop extraction.
- **Mango:** Insufficient alone. 260 images (~65 per class) is severely inadequate for standalone ResNet18 fine-tuning. Requires supplemental public images of Indian commercial mangoes (Dashehari / Alphonso / Chaunsa) to reach $\ge 1,000$ images before training.
- **Stage 1 Identifier:** Ready for assembly using balanced specimens from Guava Dataset A, BananaID originals, Apple crops, Mango candidates, and non-fruit/other produce negatives.

---

## 9. Unresolved Items & Recommended Acquisition Plan

### Decisions for User Alignment
1. **Mango Supplemental Dataset:**
   Confirm whether to augment Harumanis with an open Indian mango dataset (e.g. Mendeley / Kaggle Alphonso/Dashehari sets) to reach a reliable training baseline ($\ge 1,000$ samples).
2. **Apple Bounding-Box Cropping:**
   Confirm that the automated pipeline should crop the 2,574 labeled bounding boxes from Wang & Wang whole-tree scenes into individual 224x224 produce specimens.
3. **Stage 1 Out-of-Distribution Rejection Cutoff:**
   Recommended: Softmax score $< 0.65$ or Shannon entropy $> 1.10$ triggers an explicit `unknown_fruit` abstention with manual inspection advice.

### Recommended Dataset Acquisition Order (Phase 14B)
1. **Step 1 — Acquire BananaID (`10.17632/h6n5srjjyw.1`):**
   - Download the 1,960 original images (exclude augmented pool).
   - Generate `ml/data/manifests/banana/` using `dHash <= 2` cluster grouping (70/15/15).
2. **Step 2 — Acquire Apple Dataset (`10.17632/gfcmdbvw65.4`):**
   - Download the 1,406 orchard images and VIA annotations.
   - Run crop manifest generator to output individual fruit instances into `ml/data/raw/apple_crops/`.
3. **Step 3 — Acquire Mango Dataset & Approved Supplemental Cohort (`10.17632/x6bcr3fkj5.2`):**
   - Download Harumanis (~260 images) and merge approved supplemental Indian mango varieties.
4. **Step 4 — Assemble Stage 1 Species Identification Pool:**
   - Sample 800 specimens per class across Guava, Banana, Apple, Mango, and Other/Background.
   - Generate `ml/data/manifests/species_id/train.json`, `val.json`, and `test.json`.


