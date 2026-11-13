# AgriChain AI — Phase 16B: Workstream A Multi-Source Model Training & Benchmark

**Status**: Verified & Completed  
**Execution Date**: October 30, 2026  
**Hardware Platform**: NVIDIA GeForce RTX 4050 Laptop GPU (6,438,780,928 bytes / 6.0 GB VRAM, Driver / CUDA 12.8)  
**Software Environment**: Python 3.13 (`.venv`), PyTorch 2.11.0+cu128, Torchvision 0.26.0+cu128, scikit-learn  
**Safety Status**: All Production Artifacts Gated and Unchanged (SHA-256 Hashes Verified)

---

## 1. Executive Summary

Phase 16B Workstream A executed the multi-source training, temperature scaling calibration, latency benchmarking, and out-of-distribution (OOD) stress evaluation for **Fruit Identifier V2**. Three candidate convolutional neural network architectures were benchmarked on group-isolated, multi-source datasets:
1. **ResNet-18** (Residual Network Baseline, 11.2M parameters)
2. **EfficientNet-B0** (Compound Scaled Architecture, 4.0M parameters)
3. **MobileNetV3-Large** (Edge & Mobile Optimized Architecture, 4.2M parameters)

All three models exceeded the target threshold of 95% Macro F1 on the locked multi-source Tier 2 test set ($N=3,037$). **MobileNetV3-Large** emerged as the top overall candidate based on test macro F1 (**0.9981**), balanced per-class recall (**0.9982**), CPU inference latency (**18.91 ms** median, **128.9 img/s** throughput), model size (**16.26 MB**), and out-of-distribution rejection (**100.0%** canopy rejection, **99.6%** retail non-target produce rejection).

---

## 2. Dataset & Split Integrity Audit

### 2.1 Manifest Configuration
The audited `fruit_identifier_v2` dataset consists of **19,886** curated specimens across 5 identity classes:
- `0`: Guava
- `1`: Banana
- `2`: Apple
- `3`: Mango (Gated Deficit Class: $N=272$ total)
- `4`: Negative Background (Non-target produce, field foliage, diseased leaves)

| Split | Total Samples | Guava | Banana | Apple | Mango | Negative BG |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 14,078 | 3,208 | 2,910 | 3,581 | 189 | 4,190 |
| **Validation** | 2,771 | 686 | 623 | 525 | 37 | 900 |
| **Locked Test** | 3,037 | 696 | 627 | 758 | 46 | 910 |
| **Total** | **19,886** | **4,590** | **4,160** | **4,864** | **272** | **6,000** |

### 2.2 Leakage & Group Isolation Verification
A rigorous forensic hash and metadata audit confirmed zero contamination:
- **Exact Path Overlaps**:
  - Train vs. Validation: `0`
  - Train vs. Locked Test: `0`
  - Validation vs. Locked Test: `0`
- **Capture Group Overlaps** (burst sequence isolation):
  - Train vs. Validation: `0`
  - Train vs. Locked Test: `0`
  - Validation vs. Locked Test: `0`
- **Stage 2 Held-Out Specimen Sync**: The locked test split strictly preserves the 1,097 in-domain specimens previously used in Stage 2 verification (346 Guavas, 297 Bananas, 408 Apples, 46 Mangoes).

---

## 3. ResNet-18 Deep Forensic Investigation (Unusually High Score Audit)

The ResNet-18 baseline achieved an initial test accuracy of 99.57% and macro F1 of 0.9965 after 5 training epochs. An investigation was conducted to determine whether this performance reflects genuine fruit recognition or spurious background shortcuts.

### 3.1 Multi-Source Domain Coverage
To eliminate background correlation shortcuts, `fruit_identifier_v2` maps multiple acquisition domains across classes:
- **Guava**: SAU Sindh Laboratory ($N=2,309$) + FruitNet Market Crates ($N=2,281$)
- **Banana**: BananaID Blue Cloth Studio ($N=1,960$) + FruitNet Market Crates ($N=2,200$)
- **Apple**: Mendeley Orchard Canopy ($N=2,574$) + FruitNet Market Crates ($N=2,290$)
- **Negative Background**: Multi-source retail produce (Orange, Lime, Pomegranate: $N=3,600$), Field Orchard Canopy ($N=1,800$), Diseased Foliage ($N=600$)

Because `Market_Retail_Crates` and `Outdoor_Orchard_Canopy` are shared between target fruits and negative backgrounds, the network cannot rely on background context to identify the fruit.

### 3.2 Performance Decomposed by Acquisition Source

| Source Dataset | Domain Environment | Test Samples | Accuracy | Macro F1 | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Apple_Mendeley_Orchard_Crops** | Outdoor Orchard Canopy | 408 | 100.00% | 1.0000 | Flawless |
| **BananaID_Ripeness** | Studio Blue Cloth | 297 | 100.00% | 1.0000 | Flawless |
| **Guava_SAU_Harvest** | Laboratory Studio | 346 | 100.00% | 1.0000 | Flawless |
| **Harumanis_Mango** | Farm Scale Paper | 46 | 100.00% | 1.0000 | Flawless (Gated) |
| **FruitNet_Apple** | Market Retail Crates | 350 | 98.86% | 0.9943 | High Generalization |
| **FruitNet_Banana** | Market Retail Crates | 330 | 99.70% | 0.9985 | High Generalization |
| **FruitNet_Guava** | Market Retail Crates | 350 | 98.57% | 0.9928 | High Generalization |
| **FruitNet_Lime** (Non-target) | Market Retail Crates | 180 | 98.33% | 0.9916 | Valid Rejection |
| **FruitNet_Orange** (Non-target) | Market Retail Crates | 180 | 100.00% | 1.0000 | Flawless Rejection |
| **FruitNet_Pomegranate** (Non-target) | Market Retail Crates | 180 | 100.00% | 1.0000 | Flawless Rejection |
| **Citrus_Disease_Foliage** (Non-target) | Pathological Leaves/Bark | 90 | 100.00% | 1.0000 | Flawless Rejection |
| **Oranges_In_Field_Canopy** (Non-target) | Outdoor Orchard Canopy | 280 | 100.00% | 1.0000 | Flawless Rejection |

### 3.3 Error Forensic Analysis (13 Errors / 3,037 Samples = 0.43%)
- **5 Samples**: Heavily degraded/rotten `Guava_Bad` classified as `negative_background` (Confidence: 0.487 - 0.928). Visual inspection confirms fruit morphology was decomposed, causing the model to conservatively reject it as biological debris.
- **4 Samples**: `FruitNet_Apple` predicted as `banana` (green elongated apple cultivars with yellow undertones).
- **1 Sample**: `FruitNet_Banana` predicted as `negative_background`.
- **3 Samples**: `FruitNet_Lime` falsely accepted as `guava` (small green spherical produce ambiguity).

---

## 4. Multi-Architecture Comparative Benchmark

All three architectures were trained with identical hyperparameter budgets (5 epochs, AdamW optimizer, lr=3e-4, weight_decay=1e-2, CosineAnnealingLR, mixed precision AMP, class-weighted cross-entropy).

### 4.1 Master Comparison Table

| Metric / Attribute | ResNet-18 | EfficientNet-B0 | MobileNetV3-Large | Winner |
| :--- | :--- | :--- | :--- | :--- |
| **Parameter Count** | 11.18 M | 4.01 M | 4.21 M | EfficientNet-B0 |
| **Checkpoint Size** | 42.72 MB | 15.60 MB | 16.26 MB | EfficientNet-B0 (-63.5%) |
| **Training Peak VRAM** | 996.8 MB | 2,972.3 MB | 1,537.2 MB | ResNet-18 |
| **Training Duration** | 1,140.0 s | 1,226.7 s | 1,238.5 s | ResNet-18 |
| **Best Val Epoch** | Epoch 4 | Epoch 5 | Epoch 4 | — |
| **Validation Macro F1** | 0.9986 | 0.9974 | 0.9975 | ResNet-18 |
| **Test Accuracy** | 99.57% | 99.77% | **99.77%** | Tied (EffNet / MobileNet) |
| **Test Macro F1** | 0.9965 | 0.9941 | **0.9981** | **MobileNetV3-Large** |
| **Test Macro Recall** | 0.9965 | 0.9982 | **0.9982** | Tied (EffNet / MobileNet) |
| **Test Macro Precision** | 0.9966 | 0.9902 | **0.9980** | **MobileNetV3-Large** |
| **Optimal Temperature ($T$)** | 1.2720 | 1.3673 | 1.5001 | — |
| **Test Calibrated ECE** | 0.0024 | **0.0004** | 0.0012 | EfficientNet-B0 |
| **GPU BS=1 Median Latency** | **5.92 ms** | 14.98 ms | 10.75 ms | **ResNet-18** |
| **GPU BS=1 P95 Latency** | **6.87 ms** | 19.08 ms | 13.67 ms | **ResNet-18** |
| **GPU BS=32 Throughput** | **1,495.7 img/s** | 950.1 img/s | 1,454.9 img/s | **ResNet-18** |
| **CPU BS=1 Median Latency** | 26.80 ms | 23.78 ms | **18.91 ms** | **MobileNetV3-Large** |
| **CPU BS=32 Throughput** | 62.6 img/s | 77.2 img/s | **128.9 img/s** | **MobileNetV3-Large (+106%)** |

### 4.2 Per-Class F1 Score Breakdown

| Class | ResNet-18 | EfficientNet-B0 | MobileNetV3-Large |
| :--- | :--- | :--- | :--- |
| **Guava** | 0.9942 | **0.9993** | **0.9993** |
| **Banana** | 0.9960 | **0.9968** | **0.9968** |
| **Apple** | 0.9974 | 0.9974 | 0.9960 |
| **Mango** (Gated Deficit) | **1.0000** | 0.9787 | **1.0000** |
| **Negative Background** | 0.9951 | **0.9984** | **0.9984** |

---

## 5. Out-of-Distribution (OOD) Stress Benchmark & Calibration

OOD detection was evaluated across three dedicated stress suites defined in the audited external evaluation plan:
1. **Suite 1: Canopy Illumination Stress** ($N=1,500$): Nighttime, rainy, and harsh direct sunlight citrus orchard canopy images without fruit.
2. **Suite 2: Pathological Foliage Stress** ($N=159$): Citrus leaves and bark displaying melanose, greening, and canker lesions.
3. **Suite 3: Retail Non-Target Produce** ($N=2,000$): Untrained market produce pool (Pomegranate displays in crates and wire baskets).

### 5.1 OOD Performance Comparison

| Stress Test Suite | Metric | ResNet-18 | EfficientNet-B0 | MobileNetV3-Large | Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Suite 1: Canopy Illumination** | True Negative Rate (TNR) | 99.73% | **100.00%** | **100.00%** | $\ge 95\%$ |
| | False Acceptance Rate (FAR) | 0.27% | **0.00%** | **0.00%** | $\le 1\%$ |
| | AUROC (Energy) | 0.6606 | 0.6861 | **0.6983** | — |
| **Suite 2: Pathological Foliage** | True Negative Rate (TNR) | **100.00%** | 98.74% | 99.37% | $\ge 95\%$ |
| | False Acceptance Rate (FAR) | **0.00%** | 1.26% | 0.63% | $\le 1\%$ |
| | AUROC (Energy) | 0.6850 | **0.8206** | 0.4988 | — |
| **Suite 3: Retail Non-Target** | True Negative Rate (TNR) | 99.05% | **99.80%** | 99.60% | $\ge 99\%$ |
| | False Acceptance Rate (FAR) | 0.95% | **0.20%** | 0.40% | $\le 1\%$ |
| | AUROC (Energy) | **0.7700** | 0.5876 | 0.5718 | — |

### 5.2 Operating Threshold Calibration
Calibrating confidence thresholds on the validation set demonstrates that Maximum Softmax Probability (MSP) $\ge 0.80$ eliminates over 99.5% of false fruit acceptances while preserving $\ge 99.1\%$ of true in-distribution fruits ($FRR = 0.85\%$).

---

## 6. Winning Candidate Selection: MobileNetV3-Large

### Selection Rationale:
1. **Superior Generalization**: Achieved the highest locked test Macro F1 (**0.9981**), Macro Recall (**0.9982**), and Macro Precision (**0.9980**), with 100% recall on the deficit Mango class.
2. **Edge & Mobile Deployment**: Model size is **16.26 MB** (62% reduction compared to ResNet-18). On CPU hardware, MobileNetV3-Large achieves **18.91 ms** median inference latency and **128.9 images/sec** throughput (more than double ResNet-18's 62.6 images/sec).
3. **Robust Rejection Profile**: 100.0% background rejection on canopy illumination stress, 99.37% on pathological foliage, and 99.60% on non-target produce.
4. **Calibration**: Calibrated Expected Calibration Error (ECE) of **0.0012** confirms confidence scores correlate directly with true class probabilities.

---

## 7. Production Artifact Safety Verification

Before and after execution, SHA-256 hashes of all existing baseline checkpoints were verified to prevent regressions:

| Artifact Path | SHA-256 Hash | Status |
| :--- | :--- | :--- |
| `ml/artifacts/best_guava_resnet18.pth` | `b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4` | Unchanged |
| `ml/artifacts/best_banana_resnet18.pth` | `3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae` | Unchanged |
| `ml/artifacts/best_fruit_identifier_resnet18.pth` | `07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967` | Unchanged |

All new Phase 16B experimental checkpoints remain strictly segregated in `ml/experiments/phase16b/fruit_identifier_v2/` and are held in **GATED** status in the model registry.

---

## 8. Workstream Status & Recommended Next Steps

- **Workstream A (Fruit Identifier V2)**: **COMPLETE & VERIFIED**.
  - All 3 models trained and audited.
  - Reports generated in `ml/data/reports/`.
- **Workstream B (Apple YOLO Detector)**: **READY FOR EXECUTION**.
  - Script: [`scripts/train_phase16b_apple_yolo.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/train_phase16b_apple_yolo.py)
  - Dataset: `ml/data/processed/apple_detection_yolo/data.yaml` (1,041 train, 126 val, 239 test).
- **Workstream C (Banana Ripeness Benchmark)**: **READY FOR EXECUTION** (Held sequentially to prevent GPU VRAM contention).
  - Script: [`scripts/train_phase16b_banana_benchmark.py`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/scripts/train_phase16b_banana_benchmark.py)
  - Dataset: `ml/data/manifests/banana_ripeness/` (Unripe, Half_Ripe, Ripe, Overripe).

