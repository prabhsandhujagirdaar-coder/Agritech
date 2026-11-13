# AgriChain AI — Phase 4A: Read-Only Verification and 60-Image Pilot Preparation Audit

**Document**: `ml/data/reports/phase4a_pilot_sampling_audit.md`  
**Date**: October 15, 2026  
**Auditor / Engineer**: Senior Computer Vision Engineer & ML Researcher  
**Active Workspace**: `C:\Users\PrabSandhu\Documents\codes\Agritech_`  
**Status**: Strict Read-Only Audit & Sampling Plan Verification  
**Primary Deliverable**: [`ml/data/processed/fruitnet_pilot_60_sample.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/fruitnet_pilot_60_sample.csv)  

---

## 1. Executive Summary

This audit evaluates the reliability, write-safety, and crash-recovery characteristics of the Phase 3 annotation history implementation, and establishes a scientifically defensible, leak-resistant 60-image sampling manifest for the upcoming dual-reviewer manual annotation pilot.

### Key Audit Conclusions:
1. **Phase 3 Implementation Verification (Qualified Approval)**:
   The append-only history ledger ([`citrus_annotation_history.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotation_history.csv)) and current view snapshot ([`citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv)) operate safely for single-reviewer interactive annotation (both Web GUI and CLI). State recovery (`_reconcile_state`) correctly reconstructs current views from history without data loss. However, **the implementation does not provide distributed ACID transactional durability or inter-process file locking**. It is safe for single-annotator or partitioned manual review, but concurrent multi-worker writes to a single shared file without a coordinator could risk race conditions.
2. **Defensible Grouping Re-Engineering**:
   The previously reported 403 clusters were rejected due to the discovery of a **426-image giant connected component** caused by transitive chaining under an `OR` condition (`dhash <= 6` OR `timestamp delta <= 5s`), along with coarse filename stem slicing (`stem[:13]`). We formulated a refined, defensible pairwise grouping rule requiring strict perceptual similarity (`dhash <= 4`) or conjunctively constrained burst proximity ($|\Delta t| \le 10\text{s} \text{ AND } \text{dhash} \le 8$), producing **695 defensible capture groups** (540 singletons).
3. **Reproducible 60-Image Pilot Manifest Generated**:
   Using fixed random seed `42`, an exact 60-candidate manifest was generated at [`ml/data/processed/fruitnet_pilot_60_sample.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/fruitnet_pilot_60_sample.csv). The sample contains exactly **20 green-dominant**, **20 color-break/turning**, and **20 orange-dominant** candidates. Crucially, **all 60 samples belong to 60 globally unique capture groups** (zero intra-sample duplicate, burst, or session sharing).
4. **Zero Pre-Filled Maturity Labels**:
   In strict adherence to scientific rigor, the sampling manifest contains only preliminary optical visual strata (`green_dominant`, `color_break_turning`, `orange_dominant`) derived from peel colorimetry, with zero automated maturity ground-truth labels.

---

## 2. Part 1: Detailed Verification of Phase 3 Implementation

Every aspect of the Phase 3 ledger implementation was inspected against the codebase, active data files, and automated unit test suite.

| Verification Item | Implementation Evaluation | Scientific & Operational Verdict |
| :--- | :--- | :---: |
| **1. Event ID Uniqueness & Idempotency** | Event IDs follow `EVT-YYYYMMDDHHMMSS-<candidate_id>-<seq:04d>` or accept explicit IDs. The manager checks `if event_id in self.event_ids: return existing_record`. Tested in `test_17`. | **VERIFIED IDEMPOTENT** (Unique per session; single-second collisions prevented by sequence counter). |
| **2. Append vs. Rewrite Behavior** | Standard annotation saves invoke `_append_history_event`, which opens the file in append mode (`"a"`), appends a single row, and calls `f.flush()` and `os.fsync(fileno)`. Bulk rewrites (`_flush_history`) occur only during initial bootstrap seeding. Tested in `test_13` and `test_14`. | **VERIFIED APPEND-ONLY**. |
| **3. Current View Reconstruction** | `_reconcile_state()` maps each candidate to its latest history event and materializes missing or outdated records into `citrus_annotations.csv`. Tested in `test_19` (simulated crash). | **VERIFIED RECOVERABLE** (History serves as self-healing authoritative log). |
| **4. Concurrency Risks** | `AnnotationManager` does not acquire an OS file lock (`msvcrt.locking` / `fcntl`) or a Python `threading.Lock` during write operations. If two separate processes write to the same CSV simultaneously, interleaved writes could occur. | **KNOWN LIMITATION** (Safe for single annotator; concurrent multi-process writes to a shared file require partitioning). |
| **5. Partial Writes & Power Loss** | History append calls `os.fsync()`. Current view uses atomic write via `.tmp` file and `os.replace()`. A mid-write crash during history append could leave a trailing partial line. | **QUALIFIED DURABILITY** (High resilience against sudden shutdown, but lacks write-ahead journal rollback). |
| **6. State Reconciliation Invariants** | `_reconcile_state()` iterates only over candidates present in history. If a candidate was marked `uncertain` in event 1 and `fully_ripe` in event 2, the latest event (`fully_ripe`) is materialized. It never resurrects superseded states. | **VERIFIED CORRECT**. |
| **7. Historical Pilot Representation** | Pilot records (`CAND-0001`..`0004`) are seeded as `historical_pilot` with `previous_event_id="none"`, `protocol_version="legacy_pilot_v0"`, and original timestamps. No unverified facts were invented. Tested in `test_20`. | **VERIFIED ACCURATE**. |
| **8. Quarantine Filter Efficacy** | `get_stage2_training_annotations()` filters by `primary_candidate`, excludes `uncertain`, and excludes `[PILOT_QUARANTINE`. Returns exactly 0 training records on current data. Tested in `test_11` and `test_12`. | **VERIFIED QUARANTINED**. |
| **9. Test Isolation** | `TestAnnotationTool.setUp()` creates temporary CSV paths inside `tempfile.TemporaryDirectory()`. Manager co-locates `history_path` with custom `annotations_path`. Master manifest is verified unchanged via SHA-256. | **VERIFIED ISOLATED**. |

---

## 3. Part 2: Sampling Input Validation

A full inventory and integrity scan was executed across all primary candidate inputs:

### 1. Primary Candidate Accessibility & Image Integrity
- Total entries in master review manifest ([`citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv)): **2,500 candidates**.
- Primary candidates evaluated (`candidate_suitability_flag == "primary_candidate"`): **1,341 candidates**.
  - `Good Quality_Fruits/Orange_Good`: **1,216 images** (`CAND-1160` to `CAND-2375`).
  - `Mixed Qualit_Fruits/Orange`: **125 images** (`CAND-2376` to `CAND-2500`).
- **File System Verification**:
  - Missing image files: **0**.
  - Corrupted / unreadable image files (via PIL `verify()`): **0**.
  - **100% of the 1,341 primary candidate images exist on disk and are verified readable.**

### 2. Optical Visual Strata vs. Biological Ground Truth
The primary candidate cohort was evaluated using the central 50% peel colorimetry heuristic ($S \ge 0.25$, $0.20 \le V \le 0.95$):
- **Green-Dominant** ($\text{mean\_hue} > 60^\circ$ or $\text{green\_ratio} \ge 0.35$): **871 images** (65.0%).
- **Color-Break / Turning** ($40^\circ \le \text{mean\_hue} \le 60^\circ$ or $0.10 \le \text{green\_ratio} < 0.35$): **363 images** (27.1%).
- **Orange-Dominant** ($\text{mean\_hue} < 40^\circ$ and $\text{green\_ratio} < 0.10$): **107 images** (8.0%).

> [!WARNING]
> **PRELIMINARY OPTICAL STRATA DISCLAIMER**:  
> These three strata represent macroscopic flavedo color distributions. They are **not** verified maturity labels (`underripe`, `partially_ripe`, `fully_ripe`). In citrus, peel degreening can occur prematurely under cold temperatures, or lag behind internal maturity in warm harvest tracts. These optical strata serve exclusively as sampling strata to ensure balanced visual representation during the human pilot.

---

## 4. Part 3: Defensible Grouping & 60-Image Sampling Methodology

### 1. Why the Previous 403 Clusters Were Rejected
In Phase 2, audit of the clustering algorithm revealed severe transitive chaining:
- Grouping linked images if $\text{dhash\_hamming} \le 6$ **`OR`** $|\Delta t| \le 5\text{ seconds}$.
- Because transitive graph connections chain edges ($A \sim B$ and $B \sim C \implies A \sim C$), background similarity across consecutive tabletop photos merged **426 distinct fruit photos** into a single monolithic component.
- Furthermore, filename slicing `stem[:13]` grouped all images from an entire 24-hour day (`IMG_20190924_`) into one group ID.
- Relying on the 403 clusters would have allowed hundreds of images from one capture session to masquerade as a single cluster or distorted sampling probabilities.

### 2. Refined Defensible Pairwise Grouping Rules
To isolate authentic burst shots and near-duplicate specimens, we established a conjunctively constrained graph grouping model:
1. **Rule 1 (Near-Duplicate Identity)**: Linked if $\text{dhash\_hamming}(i, j) \le 4$. (Captures near-identical frames regardless of filename).
2. **Rule 2 (Temporal Burst Sequence)**: If both images contain valid capture timestamps on the same date, linked if:
   $$|\Delta t| \le 10\text{ seconds} \quad \mathbf{AND} \quad \text{dhash\_hamming}(i, j) \le 8$$
3. **Rule 3 (Sequential Camera Burst)**: For sequential camera filenames (`IMG_####`), linked if:
   $$|\text{seq}_i - \text{seq}_j| \le 2 \quad \mathbf{AND} \quad \text{dhash\_hamming}(i, j) \le 8$$

### 3. Resulting Defensible Group Distribution
Applying this refined rule across all 1,341 primary candidates produced **695 defensible capture groups** (with 540 singletons).
Across the three visual strata:
- **`green_dominant`**: **448 independent groups** (871 images).
- **`color_break_turning`**: **188 independent groups** (363 images).
- **`orange_dominant`**: **87 independent groups** (107 images).

Even in the scarcest stratum (`orange_dominant`), 87 independent groups exist. Therefore, extracting 20 independent groups per stratum is **statistically robust and readily achievable without relaxing criteria**.

### 4. Reproducible Sampling Procedure (Seed = 42)
1. **Rarest Stratum First**: To eliminate cross-strata burst leakage, groups were sampled sequentially starting from the rarest stratum:
   - First: `orange_dominant` (sampled 20 groups from 87 available).
   - Second: `color_break_turning` (sampled 20 groups from remaining unselected groups).
   - Third: `green_dominant` (sampled 20 groups from remaining unselected groups).
2. **Global Group Uniqueness Enforcement**: A global set tracking selected group IDs ensured that if a multi-image burst group contained images spanning two strata, that entire group was restricted to only one stratum sample.
3. **Intra-Group Representative Selection**: For multi-image groups, the median specimen in the group was selected to represent the group.
4. **Ordering**: The 60 samples are indexed in clean sequential order:
   - Samples 1–20: `green_dominant`
   - Samples 21–40: `color_break_turning`
   - Samples 41–60: `orange_dominant`

---

## 5. Part 4: The 60-Image Pilot Sampling Manifest

The sampling manifest has been written to:  
[`ml/data/processed/fruitnet_pilot_60_sample.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/fruitnet_pilot_60_sample.csv)

### Manifest Structure & Summary Statistics:
- Total Samples: **60 candidate images**.
- Unique Capture Groups: **60 of 60 (100% independent; zero duplicate/burst sharing)**.
- Stratum Representation:
  - `green_dominant`: **20 candidates** (Mean hue: $62.0^\circ$ to $127.9^\circ$).
  - `color_break_turning`: **20 candidates** (Mean hue: $41.3^\circ$ to $59.8^\circ$).
  - `orange_dominant`: **20 candidates** (Mean hue: $18.3^\circ$ to $39.9^\circ$).
- Source Category Representation:
  - `Good Quality_Fruits/Orange_Good`: **52 candidates** (86.7%).
  - `Mixed Qualit_Fruits/Orange`: **8 candidates** (13.3%).
- Proposed Maturity Labels: **None** (Fields restricted to objective colorimetry, capture group ID, selection reason, and `review_status = "unreviewed_pilot_candidate"`).

### Representative Sample Excerpts:

| Order | Candidate ID | Visual Stratum | Source Category | Capture Group ID | Mean Hue | Selection Rationale |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `CAND-2402` | `green_dominant` | `Mixed Qualit_Fruits/Orange` | `GRP-1242` | $115.0^\circ$ | Stratum 'green_dominant' sample #1; sole representative of independent capture group GRP-1242; hue=115.0° |
| **10** | `CAND-1168` | `green_dominant` | `Good Quality_Fruits/Orange_Good` | `GRP-0008` | $75.6^\circ$ | Stratum 'green_dominant' sample #10; sole representative of independent capture group GRP-0008; hue=75.6° |
| **21** | `CAND-1484` | `color_break_turning` | `Good Quality_Fruits/Orange_Good` | `GRP-0324` | $54.2^\circ$ | Stratum 'color_break_turning' sample #1; sole representative of independent capture group GRP-0324; hue=54.2° |
| **30** | `CAND-1250` | `color_break_turning` | `Good Quality_Fruits/Orange_Good` | `GRP-0090` | $48.2^\circ$ | Stratum 'color_break_turning' sample #10; sole representative of independent capture group GRP-0090; hue=48.2° |
| **41** | `CAND-1281` | `orange_dominant` | `Good Quality_Fruits/Orange_Good` | `GRP-0121` | $34.9^\circ$ | Stratum 'orange_dominant' sample #1; sole representative of independent capture group GRP-0121; hue=34.9° |
| **50** | `CAND-1188` | `orange_dominant` | `Good Quality_Fruits/Orange_Good` | `GRP-0028` | $29.8^\circ$ | Stratum 'orange_dominant' sample #10; sole representative of independent capture group GRP-0028; hue=29.8° |

---

## 6. Safety & Invariant Verification Checklist

| Verification Item | File / Target | State / Hash | Verification Result |
| :--- | :--- | :--- | :---: |
| **Candidate Manifest** | [`citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) | `3d30aa0549ead9f8a196d580fb6181f900f73ee8502ae2096845a07ea720a0a0` | **UNMODIFIED** (2,501 lines) |
| **Current Annotations** | [`citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv) | `53dac40dad1ae72b830b05b8d0c5166e4d90e858a70ac2bbd38fe26ae98f4ea4` | **UNMODIFIED** (5 lines) |
| **History Ledger** | [`citrus_annotation_history.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotation_history.csv) | `4ddde6ea009e3afd80282b094298617ab6d61ac51b88fd11c976adb8d2267737` | **UNMODIFIED** (5 lines) |
| **Pilot Backup** | [`citrus_annotations_pre_phase3_backup.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/reports/citrus_annotations_pre_phase3_backup.csv) | `53dac40dad1ae72b830b05b8d0c5166e4d90e858a70ac2bbd38fe26ae98f4ea4` | **IDENTICAL TO CURRENT** |
| **Raw Images** | `ml/data/raw/` | All files intact | **UNTOUCHED** |
| **Git Working Tree** | `git status` | Clean / untracked audit deliverables only | **ZERO COMMITS / RESETS** |
| **Unit Test Suite** | `python -m unittest discover -s ml/tests` | 29 tests passing | **ALL TESTS PASS (0.82s)** |

---

## 7. Pilot Readiness Verdict & Exact Next Step

### Final Audit Decisions:
1. **Is Phase 3 safe enough for a small pilot?**  
   👉 **YES**. The append-only history ledger, write-ahead logging with `os.fsync()`, atomic current view updates, and crash recovery reconciliation are thoroughly validated and completely safe for manual pilot review. For multi-reviewer annotation, each reviewer will operate on an independent reviewer session or local instance to avoid uncoordinated concurrency.
2. **Was a defensible 60-image sample actually produced?**  
   👉 **YES**. The 60-image sample in [`fruitnet_pilot_60_sample.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/fruitnet_pilot_60_sample.csv) is strictly stratified (20 green, 20 turning, 20 orange), completely free of burst or near-duplicate leakage (60 unique groups), fully reproducible (seed 42), and free of synthetic maturity labels.

> [!IMPORTANT]
> **STOP CONDITION SATISFIED**:  
> No manual annotations have been recorded for the 60 candidates. No CNN models have been trained. All files remain in a read-only verified state.
> 
> **Awaiting explicit user approval before launching the dual-reviewer annotation exercise.**
