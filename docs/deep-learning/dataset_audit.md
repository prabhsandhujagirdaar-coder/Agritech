# AgriChain AI — ML Dataset Audit & Validation Report

**Document**: `docs/deep-learning/dataset_audit.md`  
**Evaluation Target**: Three-Class Ripeness Classifier for Kinnow Mandarin (*Citrus reticulata*)  
- **Class 0**: Underripe (Immature green / greenish-yellow rind, high acidity, firm)
- **Class 1**: Partially Ripe (Breaker stage, turning yellow-orange, transitional sugar/acid balance)
- **Class 2**: Fully Ripe (Full golden-orange rind, optimal brix, peak market harvest)

**Auditor**: Senior Computer Vision & ML Dataset Auditor  
**Date**: October 14, 2026  
**Workspace**: `C:\Users\PrabSandhu\Documents\codes\Agritech_`  

---

## 1. Executive Summary & Integrity Assessment

Three downloaded dataset archives located in `C:\Users\PrabSandhu\Downloads` were audited using non-destructive in-memory stream inspections and local ZIP header verification. No original files were modified, moved, or deleted, and no multi-gigabyte files were extracted unnecessarily to disk.

| Archive | File Size | Location | Archive Integrity | Usable Kinnow Ripeness Images |
| :--- | :---: | :--- | :---: | :---: |
| **`Oranges in the field.zip`** | 775.00 MB | `C:\Users\PrabSandhu\Downloads\` | **Valid** (CRC Verified) | **0** (Detection only, 1 class: `orange`) |
| **`b6fftwbr2v-3.zip`** (FruitNet) | 6,202.37 MB (6.06 GB) | `C:\Users\PrabSandhu\Downloads\` | **Valid** (Header Verified) | **0** (Pre-labeled as Good/Bad/Mixed quality) |
| **`A Citrus Fruits and Leaves Dataset...zip`** | 63.83 MB | `C:\Users\PrabSandhu\Downloads\` | **Valid** (CRC Verified) | **0** (Plant pathology disease classes) |

### Core Scientific Verdict
**None of the three downloaded archives contain ground-truth, three-class ripeness annotations for Kinnow Mandarin.**
1. `Oranges in the field` is an **object detection** dataset (YOLO bounding boxes) with a single class (`orange`) taken in orchard canopies.
2. `FruitNet` is an Indian fruit **commercial quality/defect** dataset (Good, Bad, Mixed) covering 6 fruits; its 2,500 orange images categorize rot and physical damage, **not** ripening maturity stages.
3. `Citrus Fruits and Leaves` is a **phytopathology disease** dataset (Black spot, Canker, Greening/HLB, Scab).
4. **Conclusion**: Training a three-class Kinnow ripeness classifier directly from the raw labels of these archives would be scientifically invalid. Genuine Kinnow maturity data or an explicit, expert-validated re-annotation protocol is strictly required.

---

## 2. Granular Dataset Audits

### Dataset 1: `Oranges in the field.zip`

- **Archive Path**: `C:\Users\PrabSandhu\Downloads\Oranges in the field.zip`
- **File Size**: 812,649,381 bytes (775.00 MB)
- **Integrity Check**: Passed (ZIP CRC check returned zero errors).
- **Total Entries in Archive**: 10,059 entries
  - **Images**: 5,025 files (all `.jpg` format).
  - **Non-Image Files**: 5,034 files (9 `annotations.json` files and 5,025 `.txt` YOLO bounding box files).
- **Image Specifications**:
  - Resolution: Uniform $640 \times 640$ pixels.
  - Channels: 3-channel RGB, JPEG format.
- **Folder Structure**:
  Structured into 9 environmental lighting and weather subdirectories:
  - `AC_CLIP_AFT_CLO/` (Afternoon, Cloudy)
  - `AR_CLIP_AFT_RAI/` (Afternoon, Rain)
  - `AS_CLIP_AFT_SUN/` (Afternoon, Sunny)
  - `EC_CLIP_EVE_CLO/` (Evening, Cloudy)
  - `ES_CLIP_EVE_SUN/` (Evening, Sunny)
  - `IN_CLIP_INDOOR/` (Indoor benchmark)
  - `MC_CLIP_MOR_CLO/` (Morning, Cloudy)
  - `MS_CLIP_MOR_SUN/` (Morning, Sunny)
  - `NI_CLIP_NIGHT/` (Night with artificial lighting)
- **Label Analysis**:
  - `annotations.json` reveals: `categories: [{'id': 0, 'name': 'orange'}]`.
  - Individual text annotations follow YOLO format: `0 <center_x> <center_y> <width> <height>`.
  - **Target Task**: Object detection (fruit localization in tree canopies).
  - **Ripeness Labels**: **None**.
- **Citrus & Kinnow Evidence**:
  - Imagery depicts whole trees and foliage with oranges hanging on branches.
  - No cultivar documentation is provided; whether these are sweet oranges (*Citrus sinensis*), mandarins, or valencia oranges is unspecified. It does **not** document Kinnow Mandarin (*King* $\times$ *Willow Leaf*).
- **Duplicate & Leakage Risks**:
  - Filenames indicate consecutive video frames extracted from short clips (e.g., `AC068_2025-01-20_02.jpg`, `AC068_2025-01-20_03.jpg`). Extremely high temporal correlation and visual redundancy across adjacent frames.
- **License & Attribution**:
  - No `LICENSE.txt` or `README.md` bundled inside the archive. Likely exported from Roboflow Universe or Kaggle detection challenges. Attribution is untraceable within the file payload.

---

### Dataset 2: `b6fftwbr2v-3.zip` (FruitNet: Indian Fruits Dataset)

- **Archive Path**: `C:\Users\PrabSandhu\Downloads\b6fftwbr2v-3.zip`
- **File Size**: 6,503,656,782 bytes (6.06 GB / 6,202.37 MB)
- **Integrity Check**: Passed (outer central directory and inner zip local headers verified).
- **Internal Structure**:
  - `b6fftwbr2v-3/FruitNet_Processed Images.rar` (3,252.08 MB)
  - `b6fftwbr2v-3/FruitNetDataset.zip` (3,253.46 MB)
- **Total Image Count (FruitNetDataset.zip)**: **19,547 images** (all JPEG format).
- **Per-Class Breakdown Across All 6 Fruits**:
  - **Apple**: 1,149 Good, 1,141 Bad, 113 Mixed (Total: 2,403)
  - **Banana**: 1,113 Good, 1,087 Bad, 285 Mixed (Total: 2,485)
  - **Guava**: 1,152 Good, 1,129 Bad, 148 Mixed (Total: 2,429)
  - **Pomegranate**: 5,940 Good, 1,187 Bad, 125 Mixed (Total: 7,252)
  - **Orange**: 1,216 Good, 1,159 Bad, 125 Mixed (**Total: 2,500**)
  - **Lime / Lemon**: 1,094 Good, 1,085 Bad, 278 Mixed (**Total: 2,457**)
  - *Total Citrus Images (Orange + Lime)*: **4,957 images**.
- **Image Specifications (Orange Subset)**:
  - Resolution: $192 \times 256$ and $256 \times 192$ pixels.
  - Channels: 3-channel RGB, JPEG format.
  - Framing: Individual fruits captured against controlled and real-world backgrounds using mobile cameras.
- **Label Analysis**:
  - Classes represent **physical commercial quality and rot/decay**:
    - `Good Quality`: Intact, undamaged, fresh market fruit.
    - `Bad Quality`: Fungal rot, heavy mold, severe bruising, decomposition.
    - `Mixed Quality`: Minor physical blemishes, surface scuffs.
  - **Ripeness Labels**: **None**. A completely green (underripe) orange that has no rot is categorized as "Good Quality", while a perfectly ripe fruit that has mold is categorized as "Bad Quality". Quality $\neq$ Ripeness.
- **Citrus & Kinnow Evidence**:
  - Origin: Collected across wholesale and retail fruit markets in Maharashtra, India.
  - Cultivars: Indian market oranges in Maharashtra are predominantly **Nagpur Mandarin** (*Citrus reticulata*) and **Mosambi** (*Citrus sinensis*). While Nagpur Mandarin shares the *Citrus reticulata* species with Kinnow, the dataset **does not identify Kinnow Mandarin** (*King* $\times$ *Willow Leaf* hybrid of Punjab).
- **Duplicate & Leakage Risks**:
  - Sample analysis of filenames (`IMG20200728140705.jpg`, `IMG20200728140708.jpg`, `IMG20200728140710.jpg`) proves that individual fruit specimens were photographed in rapid bursts (1–3 seconds apart) while rotating the fruit.
  - **Severe Data Leakage Risk**: If images are partitioned via standard random shuffle, the exact same individual fruit will appear in both the training set and the test set, leading to artificially inflated, scientifically invalid test accuracies.
- **License & Attribution**:
  - Source: Mendeley Data (DOI: [10.17632/b6fftwbr2v.3](https://doi.org/10.17632/b6fftwbr2v.3)).
  - Peer-Reviewed Publication: Patil, K., & Meshram, V. (2022). *FruitNet: Indian fruits image dataset with quality for machine learning applications*. **Data in Brief**, 40, 107686.
  - License: **CC BY 4.0** (Open Access with attribution).

---

### Dataset 3: `A Citrus Fruits and Leaves Dataset for Detection and Classification of Citrus Diseases through Machine Learning.zip`

- **Archive Path**: `C:\Users\PrabSandhu\Downloads\A Citrus Fruits and Leaves Dataset...zip`
- **File Size**: 66,932,231 bytes (63.83 MB)
- **Integrity Check**: Passed (Nested archive `Citrus.zip` CRC verified).
- **Total Images**: **759 images** (594 PNG, 164 JPG, 1 JPEG).
- **Image Specifications**:
  - Resolution: Uniform $256 \times 256$ pixels.
  - Channels: 3-channel RGB.
- **Class Breakdown**:
  - **Fruits (150 images total)**:
    - Black spot: 19
    - Canker: 78
    - Greening (*Huanglongbing*): 16
    - Scab: 15
    - Healthy: 22
  - **Leaves (609 images total)**:
    - Black spot: 171
    - Canker: 163
    - Greening: 204
    - Melanose: 13
    - Healthy: 58
- **Label Analysis**:
  - Classes represent **botanical pathology / plant diseases**.
  - **CRITICAL DISTINCTION**: The label `"Greening"` in this dataset refers strictly to **Citrus Greening Disease** (*Huanglongbing* / Candidatus Liberibacter asiaticus), a devastating bacterial infection that causes mottled leaves and misshapen fruit. It has **no relation** to green/underripe maturity.
- **Citrus & Kinnow Evidence**:
  - Generic laboratory and field specimens of citrus leaves and fruit. No Kinnow documentation.
- **Usability for Ripeness Classifier**: **0% (Unusable)**. Disease classification cannot be re-purposed as a ripeness proxy.

---

## 3. Dataset Suitability & Limitation Matrix

| Metric / Requirement | `Oranges in the field` | `FruitNet` (Patil et al.) | `Citrus Diseases` |
| :--- | :---: | :---: | :---: |
| **Authentic Kinnow Mandarin?** | No (Unverified orange) | No (Nagpur / Indian orange) | No (Generic citrus) |
| **Three Ripeness Stages?** | No (Single class) | No (Quality: Good/Bad/Mixed) | No (Disease categories) |
| **Annotation Type** | Object Detection (BBox) | Whole-image Quality Class | Whole-image Pathology Class |
| **Single Isolated Fruits?** | No (Tree canopy scenes) | **Yes** (Individual fruits) | Mixed (Leaf/Fruit crops) |
| **Indian Citrus Context?** | Unknown | **Yes** (Indian markets) | Unverified |
| **Licensing Status** | Unverified / Missing | **CC BY 4.0** (Open Access) | Open Academic |
| **Direct Usability for Ripeness** | **Unsuitable** | **Unsuitable as-is** | **Completely Unusable** |

---

## 4. Methodological Pitfalls to Avoid

1. **The "Color Shortcut" Fallacy**:
   Automating a heuristic script that relabels orange images as "underripe" if green pixels exceed a threshold is scientifically indefensible. Citrus rind color depends on nighttime temperatures (chlorophyll degradation) as well as maturity; greening disease, surface scars, or shadows can easily deceive color thresholds.
2. **The "Quality Equals Ripeness" Fallacy**:
   Treating `Bad Quality` as "overripe" or `Good Quality` as "fully ripe" introduces massive label noise. A bruised green orange is bad quality but underripe; a pristine breaker orange is mixed color but top quality.
3. **Specimen Data Leakage**:
   In `FruitNet`, burst captures of the same fruit specimen occur consecutively. A standard random train/validation split will leak near-identical frames of the same orange into both training and testing, producing 99% artificial accuracy that collapses on real farm-gate intake.

---

## 5. Defensible Machine Learning Strategy

To ensure AgriChain AI produces an academically rigorous, peer-reviewable deep learning submission:

```
                            [ DATASET SOURCING STRATEGY ]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [ Pre-Training Backbone ]                       [ Kinnow Target Domain ]
     • ImageNet Pre-trained ResNet18                • Genuine Kinnow Mandarin imagery
     • Optional feature transfer from               • 3 verified harvest maturity classes:
       FruitNet Good/Bad Indian Citrus                 - Class 0: Underripe
                                                       - Class 1: Partially Ripe
                                                       - Class 2: Fully Ripe
                                                                  │
                                                                  ▼
                                                      [ Group-Aware Splitting ]
                                                    • Group by Specimen / Burst ID
                                                    • Zero specimen overlap across:
                                                      Train (70%) / Val (15%) / Test (15%)
                                                                  │
                                                                  ▼
                                                   [ Experimental Comparison ]
                                                    • Baseline: 4-Layer Custom CNN
                                                    • Candidate: ResNet18 Transfer Learning
                                                                  │
                                                                  ▼
                                                      [ Comprehensive Metrics ]
                                                    • Accuracy, Precision, Recall, F1
                                                    • Normalized Confusion Matrix
                                                    • Independent Punjab Kinnow Test Set
```

### Actionable Training Plan:
1. **Target Taxonomy**:
   - `Class 0 (Underripe)`: Fruit with $>60\%$ dark green surface, firm rind, harvested early or unmarketable for immediate table consumption.
   - `Class 1 (Partially Ripe)`: Breaker stage with $20\% - 60\%$ orange coloration, yellow-green transition.
   - `Class 2 (Fully Ripe)`: Mature commercial Kinnow with $>80\%$ uniform deep golden-orange rind.
2. **Leakage-Resistant Partitioning**:
   - Parse image filename timestamps (`IMGYYYYMMDDHHMMSS`). Group frames taken within 60 seconds of each other as a single `specimen_group_id`.
   - Apply `GroupShuffleSplit` or `StratifiedGroupKFold` using `specimen_group_id` so that an individual fruit's angles exist exclusively in train OR validation OR test.
3. **Model Benchmark**:
   - **Baseline CNN**: 4-stage convolutional pipeline (Conv2D $\rightarrow$ BatchNorm $\rightarrow$ ReLU $\rightarrow$ MaxPool) with Dropout (0.3) and Linear classifier head.
   - **Transfer Learning**: ResNet18 pretrained on ImageNet, replacing `fc` layer with `Linear(512, 3)` with cosine annealing learning rate scheduler and AdamW optimizer.
4. **Evaluation Protocol**:
   - Per-class Precision, Recall, F1-Score, Overall Accuracy, and Confusion Matrix.
   - Latency benchmark on NVIDIA RTX 4050 GPU (<15 ms per frame target).

---

## 6. Sourcing Genuine Kinnow Data

Because the three downloaded datasets do not contain ground-truth Kinnow ripeness labels, the following two paths are recommended:

### Path A (Primary): Targeted Kinnow Dataset Acquisition
Search and acquire an authentic Kinnow Mandarin dataset from:
1. **Zenodo / Mendeley / Kaggle**: Repositories specifically indexing *Kinnow Mandarin* or *Citrus reticulata Blanco* from Punjab Agricultural University (PAU), Ludhiana, or ICAR-Central Citrus Research Institute (CCRI).
2. **Indian Agritech Benchmarks**: Agricultural image datasets from north Indian mandi intakes.

### Path B (Supplementary): Curated & Documented FruitNet Annotation
If an external Kinnow ripeness dataset is unavailable:
1. Select only single-fruit, healthy/marketable Indian citrus images from `FruitNet` (`Good Quality_Fruits/Orange_Good` and `Mixed Qualit_Fruits/Orange`).
2. Implement a formalized, documented annotation protocol with an agricultural grading rubric to manually label a subset (e.g., 600–900 images) into Underripe, Partially Ripe, and Fully Ripe.
3. Clearly state in the project report: *"Evaluated on Indian Citrus reticulata (FruitNet cohort) annotated under Punjab Kinnow commercial grading standards, with validation pending local mandi field capture."*

---

## 7. Immediate Next Steps

1. Conduct a targeted search for verified open-access **Kinnow Mandarin ripeness datasets** (e.g., PAU / ICAR / Kaggle Kinnow datasets).
2. If genuine Kinnow ripeness data is acquired, prepare the manifest and audit its class balance.
3. Formulate the leak-free data split script in `ml/src/data/`.
4. Proceed to Stage 5: Implement the Baseline CNN and ResNet18 transfer learning pipelines.
