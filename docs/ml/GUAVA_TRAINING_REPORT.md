# AgriChain AI — Phase 3: Guava CNN Baseline Training & Leakage Evaluation Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Model Architecture:** ResNet18 Transfer Learning Baseline  
**Hardware Executed:** NVIDIA GeForce RTX 4050 Laptop GPU (CUDA 12.8, PyTorch 2.11.0)  
**Date:** October 2026  
**Status:** Completed Baseline Training & Rigorous Evaluation

---

## Executive Summary

In Phase 3, we addressed the potential same-fruit multi-angle image leakage in the Guava dataset, trained a reproducible ResNet18 transfer-learning baseline with inverse class frequency weighting and color fidelity constraints, and evaluated the model on a strictly held-out test set.

### Headline Results
- **Held-Out Test Accuracy (V2 Group-Aware):** **83.24%**
- **Test Macro-F1:** **0.8122** (Macro-Recall: **86.56%**, Macro-Precision: **78.20%**)
- **Single-Image Inference Latency:** **4.95 ms** on NVIDIA RTX 4050 GPU
- **Model Checkpoint Size:** **44.80 MB** (`best_guava_resnet18.pth`)
- **Key Scientific Finding on Leakage:** Naive stratified splitting yields an artificially inflated test accuracy of **88.12%** (Macro-F1 0.8808) due to rotated views of identical fruits leaking across splits. When candidate fruit clusters are strictly isolated (V2), the genuine generalization accuracy is **83.24%** (Macro-F1 0.8122). This proves an empirical leakage inflation effect of **+4.88% accuracy** and **+0.0686 Macro-F1** if multi-angle frames are not grouped.

---

## 1. Phase A — Leakage Review & Mitigation

### 1.1 The Source of Same-Fruit Leakage
The source dataset (Maitlo et al., 2023, Mendeley Data [DOI: 10.17632/w3fg8jjmzr.1](https://doi.org/10.17632/w3fg8jjmzr.1)) contains 2,309 images of Guava across three varieties (*Local Sindhi*, *Thadhrami*, *Riyali*). 
- In the laboratory capture setup, each physical fruit lot was photographed under fixed illumination against a uniform backdrop while being rotated by minor angular increments (e.g. 3 to 6 shots per fruit).
- Within the archive, files are named sequentially (`1.jpg`, `2.jpg` ... `N.jpg`) without explicit fruit-instance tags or multi-view metadata.
- Pixel-level mean absolute error (MAE) between consecutive frames (e.g. `55.jpg` and `56.jpg`) is very low (**5.85 to 8.43**), compared to **28.0 to 34.5** between distinct fruits in the same class.

### 1.2 Connected Component Perceptual Clustering
To prevent multi-angle rotation frames of the same fruit from leaking across evaluation splits without inventing speculative grouping rules, a **perceptual hash clustering algorithm** was implemented:
- 64-bit difference hashes (`dHash`) were computed for all 2,309 images.
- Images within the same `(Variety, Class)` stratum with Hamming distance $\le 2$ bits (representing visual equivalence $\ge 96.8\%$) were grouped as connected components.
- This partition yielded **606 candidate fruit clusters** across the 9 strata (median cluster size = 3 to 4 images, matching the physical 3-to-4 angle capture protocol).

### 1.3 Split Comparison: V1 Stratified vs V2 Group-Aware

| Metric | V1 Stratified (Naive Frame Split) | V2 Group-Aware (Cluster Split) | Impact of Mitigation |
| :--- | :---: | :---: | :--- |
| **Manifest Path** | `ml/data/manifests/` | `ml/data/manifests/v2_grouped/` | Versioned isolation |
| **Train Samples** | 1,618 (70.07%) | 1,617 (70.03%) | Preserved 70% target |
| **Val Samples** | 346 (14.98%) | 346 (14.98%) | Preserved 15% target |
| **Test Samples** | 345 (14.94%) | 346 (14.98%) | Preserved 15% target |
| **Identical dHash (dist=0) Train vs Val** | **437 pairs** | **1 pair** | **99.8% reduction** |
| **Identical dHash (dist=0) Train vs Test** | **383 pairs** | **4 pairs** | **99.0% reduction** |
| **Near-Duplicate (dist <= 2) Train vs Test**| **974 pairs** | **12 pairs** | **98.8% reduction** |

---

## 2. Phase B — CNN Baseline Training Dynamics

### 2.1 Training Configuration & Hyperparameters
- **Configuration File:** [`ml/configs/resnet18_guava_v2_grouped.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_guava_v2_grouped.json)
- **Random Seed:** Deterministic fixed seed `42`.
- **Pretrained Weights:** ImageNet-1k default (`torchvision.models.ResNet18_Weights.DEFAULT`).
- **Frozen Stages:** `conv1`, `bn1`, `layer1`, `layer2` (initial feature extractors frozen).
- **Trainable Stages:** `layer3`, `layer4`, and new linear head (`Dropout(0.2)` + `Linear(512, 3)`).
- **Class Imbalance Handling:** Inverse class frequency loss weighting:  
  $w_{\text{Green}} = 3.327$, $w_{\text{Mature Green}} = 0.931$, $w_{\text{Ripe}} = 0.615$ with label smoothing $0.05$.
- **Color Fidelity:** Augmentations restricted to flips, 15° rotation, mild brightness/contrast jitter, and **strictly 0.0 hue jitter** (`hue=0.0`), preserving natural chlorophyll and carotenoid spectra.
- **Optimizer:** AdamW (`lr_head = 1e-4`, `lr_backbone = 1e-5`, `weight_decay = 0.01`).
- **Scheduler:** CosineAnnealingLR ($T_{\max} = 20$, $\eta_{\min} = 10^{-6}$).
- **Precision:** Mixed precision training (`torch.cuda.amp.autocast`).

### 2.2 Epoch-by-Epoch Convergence Table

```
===================================================================================================
Epoch    Train Loss    Train Acc    Train F1    Val Loss    Val Acc    Val Macro-F1    Time (s)
===================================================================================================
01       0.9309        58.7%        0.541       0.7861      75.4%      0.7319          57.9s
02       0.7054        76.1%        0.706       0.6838      83.8%      0.8278          54.4s
03       0.6224        79.8%        0.764       0.5976      91.0%      0.9185 [BEST]   52.8s
04       0.5647        85.0%        0.823       0.5679      90.8%      0.8967          54.4s
05       0.5405        84.8%        0.822       0.5585      91.0%      0.8960          46.0s
06       0.5363        86.9%        0.836       0.5786      90.2%      0.8861          45.1s
07       0.5057        87.6%        0.855       0.5644      89.6%      0.8818          42.7s
08       0.4895        89.3%        0.872       0.5659      88.7%      0.8591          43.4s
===================================================================================================
[EARLY STOPPING TRIGGERED] Epoch 8: No improvement in val_macro_f1 for 5 epochs.
Total Training Time: 399.9 seconds (~6.7 minutes). Best Val Macro-F1: 0.9185 (Epoch 3).
===================================================================================================
```

---

## 3. Phase C — Held-Out Test Set Evaluation

Model evaluation was executed strictly using the checkpoint selected on validation data (**Epoch 3**, `ml/artifacts/best_guava_resnet18.pth`). At no point were test results used to guide hyperparameter selection or early stopping.

### 3.1 Test Performance Metrics (V2 Group-Aware Test Set)

| Metric | Measured Value | Standard Deviation / Notes |
| :--- | :---: | :--- |
| **Top-1 Test Accuracy** | **83.24%** | 288 correct out of 346 test images |
| **Macro-Averaged F1-Score** | **0.8122** | Balances performance across imbalanced classes |
| **Macro-Averaged Recall** | **86.56%** | High sensitivity across all ripening stages |
| **Macro-Averaged Precision**| **78.20%** | Moderate precision on transitional green boundary |
| **Test Cross-Entropy Loss** | **0.5542** | Stable loss without divergence |
| **Inference Latency (GPU)** | **4.95 ms** | Median over 100 benchmark iterations (RTX 4050) |
| **Model Size on Disk** | **44.80 MB** | Lightweight, ideal for edge packhouse deployment |

### 3.2 Per-Class Breakdown

| Class Index & Name | Precision | Recall | F1-Score | Test Support | Class Characteristics |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **0 — Green** | **0.6444** | **0.9667** | **0.7733** | 30 | High recall (29/30 detected); captures virtually all underripe intake. |
| **1 — Mature Green**| **0.7669** | **0.7907** | **0.7786** | 129 | Critical cold-chain export stage; 102/129 correctly sorted. |
| **2 — Ripe** | **0.9345** | **0.8396** | **0.8845** | 187 | High precision (93.5%); prevents overripe fruit from entering cold storage. |

### 3.3 Confusion Matrix (V2 Group-Aware)

```
                       Predicted: Green     Predicted: Mature Green     Predicted: Ripe
True: Green                    29                      1                       0
True: Mature Green             16                    102                      11
True: Ripe                      0                     30                     157
```

#### Diagnostic Error Analysis:
1. **Zero Categorical Inversion:**
   - **True Green is NEVER misclassified as Ripe** (0 images).
   - **True Ripe is NEVER misclassified as Green** (0 images).
2. **Physiological Ripening Gradient:**
   - All 58 misclassifications occur strictly across the continuous biological boundary between contiguous stages:
     - 16 `Mature Green` fruits were classified as `Green` (early harvest specimens with high surface chlorophyll).
     - 1 `Green` fruit was classified as `Mature Green`.
     - 30 `Ripe` fruits were classified as `Mature Green` (breaker stage fruit with partial yellowing).
     - 11 `Mature Green` fruits were classified as `Ripe`.
   - In commercial packhouses, transitional border grading is resolved by dual-angle inspection or minimum brix verification.

### 3.4 Comparative Evaluation: V1 vs V2 Test Sets
To demonstrate the empirical impact of near-duplicate multi-angle rotation leakage:

| Evaluation Split | Test Accuracy | Macro-F1 | Macro-Recall | Macro-Precision | Leakage Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **V1 Stratified Test** | **88.12%** | **0.8808** | **0.9022** | **0.8654** | Inflated by multi-angle rotation frames |
| **V2 Group-Aware Test** | **83.24%** | **0.8122** | **0.8656** | **0.7820** | **Genuine generalization performance** |
| **Empirical Leakage Gap** | **+4.88%** | **+0.0686** | **+0.0366** | **+0.0834** | Quantified leakage inflation effect |

---

## 4. Phase D — Integration Readiness & Checkpoint Verification

### 4.1 Saved Checkpoint Artifacts
- **Best Validation Checkpoint:** [`ml/artifacts/best_guava_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_guava_resnet18.pth) (44.80 MB)  
  Contains `epoch`, `model_state_dict`, `val_metrics`, `config`, `random_seed`, `crop: "guava"`, and `class_mapping: {0: "Green", 1: "Mature Green", 2: "Ripe"}`.
- **Latest Resumable Checkpoint:** [`ml/artifacts/latest_guava_resnet18_checkpoint.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/latest_guava_resnet18_checkpoint.pth) (128.79 MB)  
  Contains full training state including `optimizer_state_dict`, `scheduler_state_dict`, and `scaler_state_dict`.

### 4.2 Backend Loading Verification
A direct architectural loading simulation was executed against `backend/app/services/cnn_service.py`:
- `models.resnet18(weights=None)` with custom head `nn.Sequential(nn.Dropout(0.3), nn.Linear(512, 3))`.
- Loaded `best_guava_resnet18.pth`:  
  **Result:** `<All keys matched successfully>` (0 missing keys, 0 unexpected keys).

### 4.3 Required Integration Changes (Awaiting Installation)
In accordance with execution safeguards, the running application containers were **not modified**, and `GET /health` continues to report `model_available: false` while `POST /api/v1/cnn/predict` returns **HTTP 503 Service Unavailable**.

To formally enable live Guava predictions in the containerized deployment in the next step:
1. Update `TARGET_CROP: str = "guava"` in `backend/app/core/config.py`.
2. Update `MODEL_WEIGHTS_PATH: str = "ml/artifacts/best_guava_resnet18.pth"` in `backend/app/core/config.py`.
3. Set `CLASS_MAPPING_VERIFIED: bool = True` and configure `GUAVA_CLASSES: List[str] = ["Green", "Mature Green", "Ripe"]`.
4. Copy or mount `best_guava_resnet18.pth` into the container volume and restart the backend service.

---

## 5. Summary of Deliverables Created

| Deliverable Item | Path | Status |
| :--- | :--- | :--- |
| **Comprehensive Report** | [`docs/ml/GUAVA_TRAINING_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_TRAINING_REPORT.md) | Created |
| **V2 Grouped Config** | [`ml/configs/resnet18_guava_v2_grouped.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/configs/resnet18_guava_v2_grouped.json) | Created |
| **Training Engine** | [`ml/src/train_guava_cnn.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/train_guava_cnn.py) | Created & Verified |
| **Comparative Evaluator** | [`scripts/compare_v1_v2_evaluation.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/compare_v1_v2_evaluation.py) | Executed |
| **Epoch Training Logs** | [`ml/experiments/guava_resnet18_v2_grouped/training_log.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/guava_resnet18_v2_grouped/training_log.json) | Generated |
| **Test Evaluation Metrics**| [`ml/experiments/guava_resnet18_v2_grouped/test_metrics.json`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/experiments/guava_resnet18_v2_grouped/test_metrics.json) | Generated |
| **Best Checkpoint** | [`ml/artifacts/best_guava_resnet18.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/best_guava_resnet18.pth) | Verified (44.8 MB) |
| **Resumable Checkpoint** | [`ml/artifacts/latest_guava_resnet18_checkpoint.pth`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/ml/artifacts/latest_guava_resnet18_checkpoint.pth) | Verified (128.8 MB) |
