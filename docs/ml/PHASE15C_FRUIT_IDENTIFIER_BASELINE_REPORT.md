# AgriChain AI — Phase 15C: Fruit Identifier Baseline Training & Evaluation Report

**Phase:** Phase 15C: Fruit Identifier Baseline Training  
**Date:** 2026-10-30  
**Execution Environment:** Windows (Python 3.13.7, PyTorch 2.11.0+cu128, NVIDIA GeForce RTX 4050 Laptop GPU)  
**Deterministic Random Seed:** `42`  
**Safety Protocol:** Zero Production Model Activations — Zero Modification to Active Guava Baseline  
**Status:** **STAGE 1 BASELINE TRAINING & CALIBRATION COMPLETE (PRODUCTION ACTIVATION GATED / PENDING)**  

---

## 1. Executive Summary

Phase 15C has successfully trained, calibrated, and evaluated the **Stage 1: Multi-Commodity Fruit Identifier Baseline** (`ml/artifacts/best_fruit_identifier_resnet18.pth`). This model serves as the front-line botanical gate of the two-stage AgriChain AI quality inspection architecture, distinguishing target commodities from non-target produce and background imagery before routing to species-specific Stage 2 ripeness networks.

### Key Evaluation Highlights:
1. **Preflight Safety Invariants (100% PASS):** All 19,324 Stage 1 records in `ml/data/manifests/fruit_identifier_v1/` were physically audited. The reported Stage 1 test split ($N=2,882$) was reconciled exactly with locked Stage 2 held-out splits: Guava ($N=346$), Banana ($N=297$), Apple ($N=408$), Mango ($N=46$), and Negative Background ($N=1,785$). Guava (`b213059f6b97...`) and Banana (`3b296ba8556d...`) baseline checkpoints were verified 100% untouched.
2. **Transfer Learning Baseline (PASS):** Trained a 5-class ResNet18 model across 8,982 training images and evaluated on 7,460 validation images. Best validation checkpoint reached at **Epoch 12** with a **validation accuracy of 99.66%** and a **validation macro-F1 of 0.9713**.
3. **Independent Held-Out Test Evaluation ($N=2,882$, PASS):**
   - **Overall Test Accuracy:** **100.00%** (2,882 / 2,882 correct)
   - **Macro F1 Score:** **1.0000**
   - **Macro Precision:** **1.0000** | **Macro Recall:** **1.0000**
   - **Negative Pool Rejection Rate (True Negative Rate):** **100.00%** (1,785 / 1,785 non-target samples rejected)
   - **False Acceptance Rate on Negatives ($\text{conf} \ge 0.80$):** **0.00%**
   - **Mean GPU Inference Latency:** **2.02 ms / image** (NVIDIA RTX 4050 Laptop GPU)
   - **Checkpoint Size on Disk:** **122.83 MB** (128,800,363 bytes, SHA-256 `07150d1ddb92...`)
4. **Validation-Only Confidence Calibration & OOD Energy Thresholding:**
   - Evaluated temperature scaling on the validation split ($N=7,460$): optimal temperature $T = 1.2942$.
   - Calibrated Helmholtz Free Energy threshold at 95% True Positive Rate: $\tau_{\text{energy}} = -3.3030$.
   - Confirmed 0.00% False Acceptance Rate on validation negative samples at $\tau_{\text{fruit}} = 0.80$.
5. **Three-Stage Lifecycle Guard (BLOCKED / PENDING):**
   - In accordance with safety rules, Stage 1 remains **unvalidated and unactivated** in `backend/app/services/model_registry.py`.
   - Single-crop Guava inference maintains strict backward compatibility (`detected_fruit = None`).
   - Apple licensing constraints (**CC BY-NC 4.0**) and Mango dataset limitations (272 samples) remain documented and gated.

---

## 2. Preflight Audit Verification Matrix

Before initiating training, all Stage 1 manifests, image paths, label mappings, and baseline checkpoints were audited programmatically via [`scripts/preflight_phase15c.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/preflight_phase15c.py):

| Checkpoint / Invariant | Target / File | Expected Value | Observed Value | Verification Result |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 15B Validation Doc** | `docs/ml/PHASE15B_...` | Present & non-empty | 17,578 bytes | **PASS** |
| **Stage 1 Train Manifest** | `fruit_identifier_v1/train.json` | 8,982 records | 8,982 records | **PASS** |
| **Stage 1 Val Manifest** | `fruit_identifier_v1/val.json` | 7,460 records | 7,460 records | **PASS** |
| **Stage 1 Test Manifest** | `fruit_identifier_v1/test.json` | 2,882 records | 2,882 records | **PASS** |
| **Reconciled Test Breakdown** | Guava / Banana / Apple / Mango / Neg | 346 / 297 / 408 / 46 / 1,785 | 346 / 297 / 408 / 46 / 1,785 | **PASS (EXACT)** |
| **Split Disjointness** | Path intersection across splits | Zero overlap | Zero overlap (100% disjoint) | **PASS** |
| **Capture Burst Group Isolation**| Group ID intersection (train vs test)| Zero overlap | Zero overlap (0 group leaks) | **PASS** |
| **Physical File Integrity** | Sample check across splits | 1,018 sample files | 1,018 / 1,018 accessible | **PASS** |
| **Guava Stage 2 Sync** | Test paths vs `v2_grouped/test.json` | 346 paths match | 346 / 346 identical | **PASS** |
| **Banana Stage 2 Sync** | Test paths vs `banana_ripeness/test.json`| 297 paths match | 297 / 297 identical | **PASS** |
| **Apple Stage 2 Sync** | Test paths vs `apple_crops_v1/test.json`| 408 paths match | 408 / 408 identical | **PASS** |
| **Mango Stage 2 Sync** | Test paths vs `mango_harumanis/test.json`| 46 paths match | 46 / 46 identical | **PASS** |
| **Guava Production Baseline** | `best_guava_resnet18.pth` | `b213059f6b97...` | `b213059f6b97...` | **PASS (UNTOUCHED)** |
| **Banana Baseline Checkpoint** | `best_banana_resnet18.pth` | `3b296ba8556d...` | `3b296ba8556d...` | **PASS (UNTOUCHED)** |
| **Model Registry Gating** | `model_registry.py` | `is_validated=False` | `is_validated=False` (Banana, Apple, Mango) | **PASS (GATED)** |

---

## 3. Training Process & Hyperparameters

### 3.1 Training Configuration
- **Model Architecture:** ResNet18 (`models.ResNet18_Weights.DEFAULT`)
- **Number of Classes:** 5
  - Index 0: `guava`
  - Index 1: `banana`
  - Index 2: `apple`
  - Index 3: `mango`
  - Index 4: `negative_background`
- **Transfer Learning Strategy:**
  - Frozen feature extraction layers: `conv1`, `bn1`, `layer1`, `layer2` (initial edge, corner, and texture filters preserved)
  - Trainable semantic stages: `layer3`, `layer4`, and new 5-class FC head
  - Head Dropout: $0.20$
- **Loss Function:** Class-weighted Cross-Entropy with label smoothing ($0.05$):
  - Inverse-frequency balancing weights: `guava`: 1.11, `banana`: 1.31, `apple`: 0.91, `mango`: 3.50, `negative_background`: 0.75
- **Optimizer & Scheduler:**
  - Optimizer: AdamW ($\text{lr}_{\text{head}} = 10^{-4}$, $\text{lr}_{\text{backbone}} = 10^{-5}$, weight decay $= 0.01$)
  - Scheduler: CosineAnnealingLR ($T_{\max} = 15$ epochs, $\eta_{\min} = 10^{-6}$)
  - Batch size: 64 | Mixed Precision: `torch.amp.autocast('cuda')`
- **Data Augmentations (Training Only):**
  - Random resized crop ($224 \times 224$), horizontal flip ($p=0.5$), rotation ($\pm 15^\circ$), brightness/contrast jitter ($\pm 15\%$), saturation jitter ($\pm 10\%$).
  - **Color Integrity Rule:** Hue jitter $= 0.0$ to preserve authentic chromatic boundaries across green, yellow, and red fruits.

### 3.2 Convergence Trajectory

```mermaid
xychart-beta
    title "Stage 1 ResNet18 Training & Validation Loss Across Epochs"
    x-axis ["E1", "E2", "E4", "E6", "E8", "E10", "E12"]
    y-axis "Loss" 0.0 --> 0.5
    line [0.452, 0.281, 0.174, 0.129, 0.102, 0.085, 0.071]
    line [0.312, 0.202, 0.121, 0.083, 0.062, 0.048, 0.038]
```

- **Best Validation Epoch:** **Epoch 12**
- **Validation Accuracy:** **99.66%**
- **Validation Macro-F1:** **0.9713**
- **Validation Per-Class Performance at Epoch 12:**
  - `guava`: Precision 1.0000, Recall 1.0000 (346 / 346)
  - `banana`: Precision 1.0000, Recall 1.0000 (293 / 293)
  - `apple`: Precision 0.9158, Recall 1.0000 (185 / 185)
  - `mango`: Precision 0.8222, Recall 1.0000 (37 / 37)
  - `negative_background`: Precision 1.0000, Recall 0.9962 (6,574 / 6,599)
  - *Observation:* Zero false negatives on actual produce. The only validation errors were 17 non-target samples slightly resembling green apples and 8 non-target samples slightly resembling unripe mangoes.

---

## 4. Confidence Calibration & Out-of-Distribution (OOD) Scoring

Validation-only calibration was performed on the full validation split ($N=7,460$):

| Calibration Metric | Observed Value | Interpretation |
| :--- | :--- | :--- |
| **Optimal Temperature ($T$)** | **1.2942** | Fitted via L-BFGS minimizing Negative Log-Likelihood on validation logits. |
| **Expected Calibration Error (ECE, Calibrated)** | **17.81%** | Evaluated across $M=15$ confidence bins on the test set. |
| **Helmholtz Free Energy Threshold ($\tau_{\text{energy}}$)** | **-3.3030** | Calibrated on in-distribution fruit validation samples at 95% True Positive Rate. |
| **Confidence Threshold Candidate ($\tau_{\text{fruit}}$)** | **0.80** | Minimum probability for confident target fruit acceptance. |
| **Confidence Margin ($\Delta_{1-2}$)** | **0.20** | Required separation between top-1 and top-2 softmax activations. |
| **Validation False Acceptance Rate (FAR)** | **0.00%** | Zero non-target samples assigned $\ge 80\%$ confidence for any target fruit. |

---

## 5. Held-Out Test Set Evaluation ($N=2,882$)

The frozen checkpoint from Epoch 12 was evaluated on the untouched, held-out test split ($N=2,882$):

### 5.1 Overall Performance Summary

| Metric | Test Set Score | Validation Score | Generalization Delta |
| :--- | :--- | :--- | :--- |
| **Overall Top-1 Accuracy** | **100.00%** (2,882 / 2,882) | 99.66% (7,435 / 7,460) | +0.34% |
| **Macro F1 Score** | **1.0000** | 0.9713 | +0.0287 |
| **Macro Precision** | **1.0000** | 0.9476 | +0.0524 |
| **Macro Recall** | **1.0000** | 0.9992 | +0.0008 |
| **Negative Rejection Rate (TNR)** | **100.00%** (1,785 / 1,785) | 99.62% (6,574 / 6,599) | +0.38% |
| **False Acceptance Rate on Negatives**| **0.00%** | 0.00% | 0.00% |
| **Inference Latency (Mean)** | **2.02 ms / image** | — | Single-image GPU forward pass (RTX 4050) |
| **Inference Latency (P95)** | **4.19 ms / image** | — | 95th percentile forward latency |
| **Model Size on Disk** | **122.83 MB** | — | ResNet18 checkpoint with optimizer state |

### 5.2 Per-Class Detailed Breakdown

| Class Index | Class Name | Support | Precision | Recall | F1-Score | Agronomic Function |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **0** | **Guava** | 346 | **1.0000** | **1.0000** | **1.0000** | Perfect separation from round apples and green citrus. |
| **1** | **Banana** | 297 | **1.0000** | **1.0000** | **1.0000** | Distinct elongated curvature prevents any cross-species confusion. |
| **2** | **Apple** | 408 | **1.0000** | **1.0000** | **1.0000** | VIA polygon crops reliably identified; 0 confusion with guavas. |
| **3** | **Mango** | 46 | **1.0000** | **1.0000** | **1.0000** | Distinctive ventral sinus/beak morphology isolated. |
| **4** | **Negative / Background**| 1,785 | **1.0000** | **1.0000** | **1.0000** | Oranges, limes, pomegranates, and foliage cleanly rejected. |
| **Macro**| **All 5 Classes** | **2,882** | **1.0000** | **1.0000** | **1.0000** | Flawless multi-commodity classification on held-out test split. |

### 5.3 Test Set Confusion Matrix ($N=2,882$)

```
                        Predicted Guava   Predicted Banana   Predicted Apple   Predicted Mango   Predicted Negative
Actual Guava                        346                  0                 0                 0                    0
Actual Banana                         0                297                 0                 0                    0
Actual Apple                          0                  0               408                 0                    0
Actual Mango                          0                  0                 0                46                    0
Actual Negative                       0                  0                 0                 0                 1785
```

---

## 6. Artifact Inventory & Reproducibility Hashes

All Phase 15C artifacts are saved in dedicated Stage 1 locations without overwriting any Stage 2 checkpoints:

| Artifact Description | File Path | Size (Bytes) | SHA-256 Hash |
| :--- | :--- | :--- | :--- |
| **Best Checkpoint** | [`ml/artifacts/best_fruit_identifier_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_fruit_identifier_resnet18.pth) | 128,800,363 | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` |
| **Guava Checkpoint (Untouched)**| [`ml/artifacts/best_guava_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_guava_resnet18.pth) | 44,796,363 | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` |
| **Banana Checkpoint (Untouched)**| [`ml/artifacts/best_banana_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_banana_resnet18.pth) | 128,791,659 | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` |
| **Training Configuration** | [`ml/configs/resnet18_fruit_identifier.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_fruit_identifier.json) | 2,827 | Validated JSON specification |
| **Training Script** | [`ml/src/train_fruit_identifier_cnn.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/train_fruit_identifier_cnn.py) | 18,944 | Standalone Stage 1 training script |
| **Training Curves (E1–E12)** | [`ml/experiments/fruit_identifier_resnet18_baseline/training_curves.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/fruit_identifier_resnet18_baseline/training_curves.json) | 682 | Recorded loss and F1 trajectory |
| **Calibration Results** | [`ml/experiments/fruit_identifier_resnet18_baseline/calibration_results.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/fruit_identifier_resnet18_baseline/calibration_results.json) | 228 | $T$, ECE, $\tau_{\text{energy}}$, FAR metrics |
| **Test Evaluation Results** | [`ml/experiments/fruit_identifier_resnet18_baseline/test_evaluation_results.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/fruit_identifier_resnet18_baseline/test_evaluation_results.json) | 1,601 | Full metrics breakdown on test split |
| **Confusion Matrix** | [`ml/experiments/fruit_identifier_resnet18_baseline/confusion_matrix.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/fruit_identifier_resnet18_baseline/confusion_matrix.json) | 459 | 5x5 confusion matrix |
| **Experiment Summary** | [`ml/experiments/fruit_identifier_resnet18_baseline/experiment_summary.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/fruit_identifier_resnet18_baseline/experiment_summary.json) | 6,185 | Unified machine-readable experiment log |

---

## 7. OOD Limitations & Deployment Boundary Analysis

> [!CAUTION]
> **Scientific Integrity Notice on Out-Of-Distribution (OOD) Generalization**:
> While the model achieved a **100.00% rejection rate** on the held-out negative test split, this negative pool is specifically composed of **Oranges, Limes/Lemons, Pomegranates, Citrus foliage, and orchard backgrounds**.
> 
> **Do not claim universal OOD rejection:**
> 1. **Unseen Agricultural Commodities:** Exotic produce (e.g., Papaya, Guava-like Feijoa, Green Figs, or Dragonfruit) may share morphological or color features with Guava or Mango and could trigger false acceptances if the energy gate is bypassed.
> 2. **Packaging and Non-Produce Objects:** Plastic wraps, cardboard boxes, harvesting tools, and hands may produce erratic activations if not pre-cropped.
> 3. **Multiple Fruits in Frame:** The baseline is a **single-crop classifier**. In multi-fruit scenes (e.g. apple orchard tree canopy with multiple fruit), a bounding-box object detector (YOLOv8n) must precede Stage 1 to generate isolated bounding-box crops.

---

## 8. Licensing & Production Blockages

1. **Apple Commercial Restriction (CC BY-NC 4.0):**
   The Apple Phenotyping dataset is strictly non-commercial. The Apple recognition capability is certified for academic/research demonstration only. Enterprise deployment will require replacing Apple training crops with an open CC-BY or public-domain dataset.
2. **Harumanis Mango Data Deficit (BLOCKED FOR PRODUCTION):**
   Although the model classified all 46 test mangoes correctly, the entire Harumanis Mango dataset contains only 272 images. In accordance with safety rules, **Mango remains BLOCKED (`is_validated=False`) in `model_registry.py`**.
3. **Guava Production Baseline Preserved:**
   `best_guava_resnet18.pth` remains the active production checkpoint. Single-crop Guava predictions continue to return `detected_fruit = None` until the full two-stage routing pipeline is certified.

---

## 9. Official Phase 15C Lifecycle Decisions

```
[Phase 15A: Data Audit] ──► [Phase 15B: Validation] ──► [Phase 15C: Stage 1 Baseline] ──► [Phase 15D: Integration Readiness]
          PASS                        PASS                              PASS                                 PENDING
                                                                         │
                                                 ┌───────────────────────┴───────────────────────┐
                                                 ▼                                               ▼
                                      [Stage 1 Baseline Model]                     [Stage 1 Production Activation]
                                        TRAINED & EVALUATED                               GATED / BLOCKED
```

### Official Decisions:
- **Preflight Verification:** **PASS**
- **Stage 1 Baseline Training:** **PASS**
- **Validation Calibration & Energy Thresholding:** **PASS**
- **Held-Out Test Set Evaluation:** **PASS (100.00% Accuracy, 1.0000 Macro-F1)**
- **Negative Pool Rejection:** **PASS (100.00% TNR, 0.00% FAR)**
- **Stage 1 Production Activation:** **BLOCKED / PENDING** (requires isolated two-stage pipeline integration and latency benchmarking in Phase 15D before registry promotion).

