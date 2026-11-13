# AgriChain AI — Phase 2: FruitNet Ripeness Dataset Validation & Annotation Readiness Audit

**Document**: `ml/data/reports/fruitnet_annotation_readiness_audit.md`  
**Date**: October 15, 2026  
**Auditor**: Senior Computer Vision Engineer & ML Researcher  
**Active Workspace**: `C:\Users\PrabSandhu\Documents\codes\Agritech_`  
**Target Subject**: FruitNet Orange Cohort (`Orange_Good`: 1,216 images, `Orange_Mixed`: 125 images; 1,341 primary candidates)  
**Safety Protocol**: Strict Read-Only Audit (Zero model training, zero dataset modification, zero Git reset/commit)

---

## 1. Executive Summary

This audit assesses whether the 1,341 primary candidate orange images from the **FruitNet: Indian Fruits Dataset** can support a scientifically defensible, three-stage preliminary citrus ripeness classification experiment (`underripe`, `partially_ripe`, `fully_ripe`), and evaluates the readiness of the annotation tooling and data partitioning logic.

### Key Audit Findings:
1. **Colorimetry Technical Trustworthiness (Qualified)**:
   The central 50% crop and HSV thresholding pipeline provides a reasonable macroscopic summary of peel chromaticity for centered, intact fruit. However, it cannot be used as automated ground truth because background table surfaces (wood grain), shadows, and specular highlights can contaminate the chromatic pixel pool. Moreover, **peel flavedo color is an optical proxy, not a biological maturity ground truth**. Citrus is non-climacteric; chlorophyll degradation in the peel can decouple from internal sugar:acid (Brix:TA) maturation.
2. **Cluster & Leakage Vulnerability (High Risk)**:
   The reported 403 clusters obtained from graph clustering (`dhash <= 6` OR `timestamp delta <= 5s`) contain severe transitive chaining. The single largest connected component contains **426 images** (31.8% of all primary candidates), and the second contains **126 images**. These clusters do **not** represent individual fruit specimens; they represent continuous photography burst sessions on shared tabletops. Furthermore, `audit_datasets.py` derived `group_id` via `stem[:13]`, which mistakenly slices by **hour** (`IMG2020072814`) rather than minute, and for `IMG_20190924_...` images collapses an entire 24-hour day (573 images) into a single bucket. This grouping is currently **unsafe** for naive train/validation/test splitting without refinement.
3. **Annotation Tool Readiness (Conditional)**:
   [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py) successfully isolates the 1,341 primary candidates, excludes `Orange_Bad` rot specimens from the primary queue, supports pausing/resuming, and isolates the `uncertain` class. However, **it overwrites annotations in place without preserving revision history**. A reviewer edit erases previous timestamps, notes, and labels. An append-only audit ledger is required before large-scale multi-annotator labeling.
4. **Cultivar Reality**:
   The FruitNet dataset consists of Indian domestic market oranges (primarily Nagpur Mandarin / *Citrus reticulata* and Mosambi / *Citrus sinensis*). **It does not contain verified Punjab Kinnow Mandarin** (*Citrus nobilis* $\times$ *Citrus deliciosa*). Any model trained on this data must be explicitly labeled an *exploratory citrus/orange proxy model*, never a verified Kinnow ripeness classifier.

---

## 2. Inspected Workspace Files & Scripts

Every finding in this audit was verified against existing, unmodified files in the active workspace:

| File Path | Description / Role in Audit | Status / Verification |
| :--- | :--- | :--- |
| [`ml/src/curate_maturity_subset.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/curate_maturity_subset.py) | Manifest generator filtering FruitNet orange categories into candidate review CSV. | Verified (179 lines; intact) |
| [`ml/src/audit_datasets.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/audit_datasets.py) | Dataset inventory, dhash calculation, and group ID assignment script. | Verified (389 lines; intact) |
| [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py) | Web and CLI human-in-the-loop annotation tool. | Verified (781 lines; passing 21 unit tests) |
| [`ml/data/processed/citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) | Master review manifest of 2,500 candidates. | Verified (SHA-256: `3d30aa0549ead...`, 2,500 rows) |
| [`ml/data/processed/citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv) | Active annotation ledger with 4 quarantined pilot records. | Verified (4 quarantined pilot rows intact) |
| [`ml/data/reports/pilot_annotations_v1_backup.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/reports/pilot_annotations_v1_backup.csv) | Permanent raw backup of pilot annotations. | Verified (Archived raw copy) |
| [`ml/data/processed/duplicate_report.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/duplicate_report.csv) | SHA-256 and dhash duplicate analysis output. | Verified (2,283 duplicate groups recorded) |
| [`ml/data/reports/dataset_audit.json`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/reports/dataset_audit.json) | Structured machine-readable audit report. | Verified (Valid JSON) |
| [`docs/deep-learning/annotation_guide.md`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/docs/deep-learning/annotation_guide.md) | Multi-attribute human annotation guidelines. | Verified (133 lines) |
| [`docs/deep-learning/kinnow_dataset_research.md`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/docs/deep-learning/kinnow_dataset_research.md) | Botanical and PAU standards for Kinnow maturity. | Verified (155 lines) |

---

## 3. Task A — Color Analysis Validation Findings

The colorimetric heuristic previously evaluated the 1,341 primary candidates using the central 50% crop, HSV conversion, chromatic pixel masking, and hue binning.

### 1. Central 50% Crop Approximation & Background Contamination
- **Geometry**: The crop box is defined as `[0.25 * width, 0.25 * height, 0.75 * width, 0.75 * height]`, sampling 25% of the total image area centered in the frame.
- **Physical Validity**: In FruitNet, the fruit is typically placed centrally on a flat surface (tabletop, paper, cloth, or floor). For images where the fruit fills $\ge 60\%$ of the frame, the central 50% crop lands entirely on the fruit flavedo.
- **Contamination Risk**: When fruit is shot from a distance, or when the camera is angled, the central 50% crop encompasses substantial background:
  - Neutral / white paper: Successfully suppressed by the saturation filter ($S < 0.25$).
  - Wooden table surfaces: Highly problematic. Natural wood possesses warm yellowish-brown hues ($30^\circ \le H \le 50^\circ$) and saturation $S \ge 0.30$. Wood grain pixels are easily misclassified as "turning" or "orange" fruit flavedo.
  - Dark shadow crevices: Suppressed by Value cutoff ($V \ge 0.20$).

### 2. HSV Hue Thresholds and Ratios
- **Vectorized Formulation**: The implementation uses standard RGB-to-HSV math:
  $$V = \max(R, G, B), \quad S = \frac{\Delta}{V} \quad (\text{if } V > 0)$$
  $$H = 60^\circ \times \begin{cases} 
  ((G - B)/\Delta) \bmod 6 & \text{if } V = R \\
  ((B - R)/\Delta) + 2 & \text{if } V = G \\
  ((R - G)/\Delta) + 4 & \text{if } V = B 
  \end{cases}$$
- **Hue Bands Evaluated**:
  - Green ratio: $65^\circ \le H \le 165^\circ$
  - Yellow/Turning ratio: $38^\circ \le H < 65^\circ$
  - Orange ratio: $8^\circ \le H < 38^\circ$
- **Technical Correctness**: The thresholds accurately reflect optical bands for chlorophyll-a/b ($65^\circ\text{--}165^\circ$), lutein/$\beta$-cryptoxanthin color break ($38^\circ\text{--}65^\circ$), and concentrated carotenoids ($8^\circ\text{--}38^\circ$).

### 3. Handling of Wraparound, Shadows, and Glare
- **Wraparound**: In HSV, red wraps around $0^\circ / 360^\circ$. The orange threshold terminates at $8^\circ$. Pixels with $0^\circ \le H < 8^\circ$ (deep red) or $300^\circ \le H \le 360^\circ$ (purple/magenta) are treated as out-of-band. In citrus flavedo, red tones below $8^\circ$ are rare, but overly dark wood tables with reddish mahogany stains are excluded, which prevents false orange inflation.
- **Shadows and Specular Highlights**: Masking with $V \ge 0.20$ and $V \le 0.95$ effectively excludes deep shadow voids and clipped specular reflections.
- **Mixed Lighting**: Direct camera flash introduces high-saturation yellowish halo rings around glare spots, which can slightly elevate the turning/orange ratio.

### 4. Verification of Denominator and Cohort Proportions
- **Pixel-Level Ratio Denominator**: The denominator is strictly the count of **chromatic fruit pixels surviving the filter** (`len(h_vals)`), not total image pixels. This avoids penalizing images with large black or white borders.
- **Cohort Proportions**: Evaluated across all 1,341 primary candidates:
  - **Predominantly Green**: 871 images (**64.95%**, rounded to **65.0%**)
  - **Color-Break / Turning**: 363 images (**27.07%**, rounded to **27.1%**)
  - **Predominantly Orange**: 107 images (**7.98%**, rounded to **8.0%**)
  - Total: $871 + 363 + 107 = 1,341$ images ($100.0\%$).
- The previously reported percentages use the exact and correct denominator ($N = 1,341$).

### 5. Multi-Fruit and Background Complications
In `Mixed Qualit_Fruits/Orange` (125 images), several frames contain multiple oranges or mixed items in a crate. In these multi-fruit frames, the central crop intersects multiple fruit surfaces and gaps between fruit, producing blended hue histograms that do not represent any single specimen.

### 6. Biological Validity Assessment
> [!CAUTION]
> **COLOR CATEGORIES ARE NOT BIOLOGICAL MATURITY LABELS**:
> Citrus is a **non-climacteric** fruit. Internal ripening (accumulation of sugars, reduction of citric acid, elevation of TSS/TA ratio) is physiologically decoupled from peel degreening. In tropical and sub-tropical climates (such as central and southern India where FruitNet was gathered), mature, sweet citrus often retains a green rind due to warm night temperatures preventing chlorophyll breakdown.
> Labeling green oranges as "immature" or orange ones as "fully ripe" based purely on RGB hue is scientifically indefensible. The color categories must strictly be treated as **visual surface color stages**.

---

## 4. Task B — Cluster & Leakage Logic Audit

A critical objective in dataset auditing is preventing data leakage (where the same fruit specimen or burst sequence appears in both training and test sets).

### 1. Timestamp Extraction and Slicing Flaw
Image filenames in FruitNet follow three formats:
1. `IMGYYYYMMDDHHMMSS.jpg` (e.g., `IMG20200728140705.jpg`)
2. `IMG_YYYYMMDD_HHMMSS.jpg` (e.g., `IMG_20190924_153210.jpg`)
3. `IMG_####.jpg` sequential camera IDs (e.g., `IMG_5033.jpg`)

In [`ml/src/audit_datasets.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/audit_datasets.py) (lines 77–78), the grouping logic derives `group_id` using:
```python
if stem.startswith("IMG") and len(stem) >= 15:
    return stem[:13]  # Comment claims: "Group by minute: IMG + YYYYMMDD + HHMM"
```
**Audit Finding — Slicing Error**:
- Slicing 13 characters from `IMG20200728140705` yields `IMG2020072814`.
  - `IMG` = 3 characters
  - `20200728` = 8 characters (Date)
  - `14` = 2 characters (Hour)
  - Total = 13 characters.
- **The code actually sliced by HOUR, not minute!** It grouped all photos taken between 14:00:00 and 14:59:59 into a single group.
- For `IMG_20190924_153210`:
  - `IMG_` = 4 characters
  - `20190924` = 8 characters
  - `_` = 1 character
  - Total = 13 characters (`IMG_20190924_`).
  - **This grouped all 573 images taken on September 24, 2019 across the ENTIRE DAY into a single `group_id`!**

### 2. Graph Clustering: The Perceptual-Hash / Temporal OR Condition
The preliminary audit used connected components on a graph where an edge connected image $i$ and image $j$ if:
$$\text{dhash\_hamming}(i, j) \le 6 \quad \mathbf{OR} \quad |\Delta t| \le 5\text{ seconds}$$
This logic was intended to cluster near-duplicates and rapid burst shots.

**Audit Finding — Transitive Chaining and Giant Component**:
Graph connected components possess transitivity: if $A \sim B$ and $B \sim C$, then $A$ and $C$ belong to the same component, even if $\text{dhash}(A, C) = 25$.
- When evaluated on the 1,341 primary candidates:
  - Total connected components: **403**.
  - Components with size 1 (singletons): **329**.
  - Components with size 2–5: **45**.
  - Components with size 6–20: **25**.
  - Components with size 21–50: **2**.
  - Components with size >50: **2**.
- **Top 5 cluster sizes**: `[426, 126, 28, 21, 19]`.
- **The single largest cluster contains 426 images (31.8% of the entire primary dataset)!**
- The second largest cluster contains **126 images**.
- Together, just two clusters encompass **552 images** (41.2% of the candidate pool).

```
                      [ GRAPH CONNECTIVITY DECOMPOSITION ]
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
    Pure Time (<= 5s)                                        Pure dhash (<= 6)
  • 465 components                                         • 790 components
  • Largest component: 101 images                          • Largest component: 251 images
           │                                                         │
           └────────────────────────────┬────────────────────────────┘
                                        ▼  [ Combined via OR ]
                       Connected Components: 403
                       Largest Component: 426 images (31.8% of dataset!)
                       Second Largest: 126 images (9.4% of dataset!)
```

### 3. What Do These Clusters Actually Represent?
- They do **NOT** represent individual fruit specimens.
- A single orange fruit was never photographed 426 times in a 5-second burst.
- Inspection of file paths in cluster 426 reveals that photographers set up a tripod/station above a tabletop and photographed hundreds of oranges consecutively over hours or days.
- Because adjacent fruit images share the identical background table, identical camera distance, and similar lighting, their `dhash` distance is frequently $\le 6$.
- The transitive union of continuous burst shots ($|\Delta t| \le 5\text{s}$) with background-dominated hash similarity ($\text{dhash} \le 6$) created an enormous artificial chain that lumped hundreds of distinct fruits into a single giant cluster.

### 4. Leakage Assessment for Train / Validation / Test Splits
- **Unsafe for Standard GroupKFold**: If cluster 426 is assigned to `test`, the test split is monopolized by one capture session (31.8% of data). If assigned to `train`, a massive portion of the dataset is unavailable for testing.
- **Unsafe for Random Splitting**: Naive random splitting would scatter 5-second burst shots of the same fruit across train and test sets, causing artificial test performance inflation.
- **Proposed Correction (For Future Implementation)**:
  1. Replace the `OR` condition with an `AND` condition for specimen deduplication: link two images as the *same fruit specimen* only if $|\Delta t| \le 3\text{s}$ **AND** $\text{dhash} \le 4$.
  2. For split leakage prevention, define capture sessions by true date-hour blocks (e.g., `IMG_YYYYMMDD_HH` formatted via regex parsing, not fixed stem slicing).
  3. Break up giant components by eliminating transitive dhash chaining across distinct capture intervals.

---

## 5. Task C — Annotation Suitability & Tooling Audit

An audit of [`ml/data/processed/citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) and [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py) was conducted.

### 1. Candidate Accessibility & File Mapping
- Total candidates in manifest: **2,500**.
- Accessible on disk: **2,500** ($100\%$). Zero missing or unreadable files.
- Manifest indices:
  - `CAND-0001` to `CAND-1159`: `Bad Quality_Fruits/Orange_Bad` (1,159 images, flagged as `defective_rot_specimen`).
  - `CAND-1160` to `CAND-2375`: `Good Quality_Fruits/Orange_Good` (1,216 images, flagged as `primary_candidate`).
  - `CAND-2376` to `CAND-2500`: `Mixed Qualit_Fruits/Orange` (125 images, flagged as `primary_candidate`).
- All 1,341 primary candidates (`CAND-1160` to `CAND-2500`) are fully mapped and accessible.

### 2. Exclusion of `Orange_Bad`
- The manifest explicitly tags `Orange_Bad` with `candidate_suitability_flag = "defective_rot_specimen"`.
- `annotation_tool.py` defaults to `primary_only=True`, skipping `Orange_Bad` and jumping directly to `CAND-1160` on startup.
- `get_stage2_training_annotations()` filters out non-primary candidates and any records containing `[PILOT_QUARANTINE`.

### 3. Pause, Resume, and Quarantine Handling
- **Pause & Resume**: Fully functional. The tool inspects existing annotations in `citrus_annotations.csv` and advances to the first unannotated primary candidate.
- **Quarantined Pilot Records**:
  The 4 pilot annotations (`CAND-0001` to `CAND-0004`) were sourced from `Orange_Bad`. They remain safely archived in `ml/data/reports/pilot_annotations_v1_backup.csv`, and in `citrus_annotations.csv` their notes contain `[PILOT_QUARANTINE: defective_rot_specimen excluded from Stage-2 maturity training...]`. They are excluded from all downstream training functions while preserving historical traceability.

### 4. Critical Tool Limitation: In-Place Overwrites & Lack of Revision History
- In [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py), `AnnotationManager.save_annotation()` updates the in-memory dictionary `self.annotations[candidate_id] = record` and flushes all records to `citrus_annotations.csv`.
- **Defect**: If an annotator revisits a candidate to change a label (e.g., from `underripe` to `partially_ripe`), the prior annotation, previous timestamp, previous confidence, and previous notes are **permanently overwritten and lost**.
- **Required Architecture for Production Phase**:
  An append-only revision ledger (e.g., `ml/data/processed/citrus_annotation_history.csv`) must be established, recording every annotation event with a unique `revision_id`, `event_type` (`create`, `update`, `quarantine`), and `reviewer_id`.

```
CURRENT IN-PLACE OVERWRITE (Risk of Data Loss):
[ Reviewer revisits CAND-1160 ] ──> Overwrites Row in citrus_annotations.csv ──> Prior Label & Timestamp LOST

RECOMMENDED APPEND-ONLY AUDIT LEDGER (Auditable & Reversible):
[ Reviewer revisits CAND-1160 ] ──┬──> Appends new record to citrus_annotation_history.csv
                                  └──> Updates current view snapshot in citrus_annotations.csv
```

### 5. Separation of Ripeness from Defects & Quality
- The tool currently provides only 4 maturity buttons: `underripe`, `partially_ripe`, `fully_ripe`, and `uncertain`.
- It does **not** have dedicated checkboxes for superficial defects (e.g., thrips scarring, hail marks, sooty mold, mechanical skin cracks).
- As a consequence, reviewers must either put defect notes into a free-text field or misclassify blemished fruit as `uncertain`.

---

## 6. Risks and Unresolved Questions

| Risk Factor | Current Workspace Status | Scientific & Engineering Impact | Proposed Mitigation |
| :--- | :--- | :--- | :--- |
| **Cultivar Ambiguity** | FruitNet labels say "Orange". Research indicates Nagpur Mandarin / Mosambi. | Model cannot be claimed as a certified Kinnow classifier. | Disclose cultivar as *unverified Indian citrus proxy*. Conduct Kinnow-specific field intake. |
| **Internal Maturity Disconnect** | Visual peel flavedo is not ground-truth Brix or titratable acidity. | Risk of false grading (e.g. green fruit with high Brix or orange fruit with low sugar). | Frame problem strictly as *visual peel-color stage classification*, not internal physiological maturity. |
| **Cluster Chaining** | 426 images chained into one component via transitive dhash OR 5s time. | Random split leads to test leakage; GroupKFold on 403 components imbalances folds. | Re-engineer session grouping with `AND` logic; split by date-hour blocks. |
| **Annotation Volatility** | Single-reviewer in-place overwrites in `annotation_tool.py`. | Inter-rater discrepancies cannot be audited; revision trail is erased. | Implement append-only revision history table before large-scale annotation. |
| **Defect Confounding** | `Orange_Mixed` contains scuffed, scratched, or multi-fruit images. | Model may learn defect artifacts as maturity signals. | Two-stage pipeline: Stage 1 screens quality/defects; Stage 2 classifies intact fruit maturity. |

---

## 7. Proposed Annotation Protocol (Summary)

A dedicated, comprehensive protocol proposal has been authored at:  
[`docs/deep-learning/fruitnet_annotation_protocol_proposal.md`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/docs/deep-learning/fruitnet_annotation_protocol_proposal.md).

### The Three Visual Maturity Categories:
1. **`underripe` (Predominantly Green / Immature Peel)**:
   - Surface flavedo exhibits $>60\%$ deep green, olive green, or yellowish-green pigmentation.
   - Oil glands are tightly packed, raised, and firm.
   - Calyx (button) is firmly attached and pale green.
2. **`partially_ripe` (Color-Break / Breaker Stage)**:
   - Flavedo exhibits $25\%$ to $60\%$ yellow-orange breaker coloration.
   - Green pigmentation remains pronounced around the calyx button, stem shoulder, or blossom end.
   - Distinct two-tone transition across the rind.
3. **`fully_ripe` (Mature Golden-Orange Peel)**:
   - Flavedo exhibits $>80\%$ uniform golden-orange, deep orange, or amber coloration.
   - Green pigmentation is $<10\%$ (restricted to a minor ring around the pedicel).
   - Oil glands are flattened, glossy, and pliable.
4. **`uncertain` (Quarantine / Ambiguous / Unusable)**:
   - Specular flash glare obscuring $>30\%$ of the central fruit surface.
   - Severe out-of-focus blur or motion blur.
   - Extensive rot, decay, or mold concealing the underlying rind.
   - Ambiguous boundary between green and orange that cannot be resolved with medium confidence.

---

## 8. Task E — Small Manual Pilot Design

Before annotating the entire 1,341 primary candidate pool, a targeted, manageable manual pilot must be conducted.

### 1. Pilot Sample Size & Selection Architecture
- **Sample Size**: **60 candidate images** (manageable in a 45–60 minute manual session).
- **Stratification**:
  - 20 images from **Predominantly Green** cohort
  - 20 images from **Color-Break / Turning** cohort
  - 20 images from **Predominantly Orange** cohort
- **Independence Enforcement**:
  - Sample exactly **one image per independent cluster** to ensure zero duplicate or burst correlation within the pilot.
  - Draw from both `Orange_Good` (50 images) and `Orange_Mixed` (10 images).
  - Explicitly include 10 borderline/ambiguous images (e.g. mean hue $45^\circ\text{--}55^\circ$) to measure reviewer boundary handling.

### 2. Multi-Reviewer Procedure & Agreement Metric
- Two independent raters (`reviewer_01` and `reviewer_02`) annotate the identical 60 candidates blindly (without seeing each other's labels).
- Inter-rater agreement is computed using **Cohen's Kappa ($\kappa$)** and overall percentage concordance:
  $$\kappa = \frac{P_o - P_e}{1 - P_e}$$
- Pilot Acceptance Threshold: $\kappa \ge 0.75$ and raw agreement $\ge 85\%$.
- Discrepancies are reviewed collaboratively to refine edge-case boundary definitions before the full dataset queue is opened.

---

## 9. Task F — Go / No-Go Decision Framework

Before initiating CNN model training, eight objective acceptance criteria must be satisfied:

| Criterion | Evaluation Standard | FruitNet Status | Recommendation Status |
| :--- | :--- | :---: | :---: |
| **1. Dataset Provenance & License** | Explicit commercial/research open license and verified origin. | CC BY 4.0 (Mendeley Data / Patil & Meshram 2022). | **SATISFIED** |
| **2. Target Cultivar Verification** | Images verified as authentic Punjab Kinnow Mandarin. | Unverified Indian orange (Nagpur Mandarin / Mosambi proxy). | **NOT SATISFIED** (Proxy only) |
| **3. Annotation Reliability & Agreement** | Multi-rater agreement Cohen's $\kappa \ge 0.75$ on pilot. | Pending execution of 60-image manual pilot. | **PENDING PILOT** |
| **4. Class Representation** | Minimum 80–100 independent specimens per class. | Primary pool contains 871 green, 363 turning, 107 orange. | **SATISFIED** (Imbalanced but viable) |
| **5. Leakage & Burst Prevention** | Split strictly isolates burst capture sequences and sessions. | Current 403 clusters suffer from 426-image giant component. | **NEEDS CORRECTION** |
| **6. Defect / Rot Separation** | Rotted or decayed fruit segregated from maturity training. | `Orange_Bad` successfully quarantined. | **SATISFIED** |
| **7. Metric & Split Independence** | Leak-proof GroupKFold or Stratified Group split. | Blocked by cluster re-engineering. | **BLOCKED** |
| **8. Auditability & Traceability** | Append-only revision tracking and hash verification. | Manifest hashed; tool requires append-only history. | **NEEDS UPGRADE** |

### Explicit Decision Rulings:
1. **Proceeding with a Manual Annotation Pilot (60 Images)**:  
   👉 **GO**. A 60-image stratified pilot is safe, requires no external dependencies, and provides essential empirical data on reviewer consistency.
2. **Building a Preliminary Orange-Ripeness Research Dataset**:  
   👉 **CONDITIONAL GO**. Conditioned upon pilot agreement ($\kappa \ge 0.75$) and replacing in-place CSV overwrites with an append-only revision ledger.
3. **Claiming Kinnow-Specific Ripeness Classification**:  
   👉 **NO-GO**. FruitNet is an unconfirmed Indian citrus cohort. Claiming Kinnow cultivar specificity on this data would be scientifically false.
4. **Training and Reporting a Final Production Model**:  
   👉 **NO-GO**. A production model for AgriChain AI must be trained on authentic farm-gate Kinnow imagery collected during the Punjab harvest window with laboratory-verified Brix/acidity measurements.

---

## 10. Exact Next Step

> [!IMPORTANT]
> **SINGLE IMMEDIATE RECOMMENDED ACTION**:  
> Upgrade [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py) to support an append-only revision history ledger (`ml/data/processed/citrus_annotation_history.csv`), then select and execute the **60-image manual annotation pilot** using the proposed protocol.
> 
> **Do not train any CNN model, do not annotate the full 1,341 dataset, and do not modify the original data files.**
