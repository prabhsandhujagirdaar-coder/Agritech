# AgriChain AI — Phase 3: Safe Annotation Ledger Implementation Report

**Document**: `ml/data/reports/phase3_annotation_history_implementation.md`  
**Date**: October 15, 2026  
**Auditor / Engineer**: Senior Computer Vision Engineer & ML Researcher  
**Active Workspace**: `C:\Users\PrabSandhu\Documents\codes\Agritech_`  
**Target Subject**: Non-destructive annotation revision history and state recovery implementation  
**Safety Protocol**: Read-only dataset protection, verified backup before execution, zero model training, zero unapproved Git operations  

---

## 1. Executive Summary

In Phase 2, the dataset audit identified that [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py) performed in-place overwrites in [`ml/data/processed/citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv). When an annotator revised a label or note, the previous assessment, reviewer ID, confidence level, and timestamp were permanently lost.

In Phase 3, we designed, implemented, and verified a **Dual-Storage Architecture** combining:
1. An **Append-Only History Ledger** ([`ml/data/processed/citrus_annotation_history.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotation_history.csv)):
   Every annotation save, revision, or reassessment appends an immutable event record containing a unique event ID, event type (`initial_annotation`, `revision`, `reassessment`, `historical_pilot`), event timestamp, protocol version, and a backward pointer (`previous_event_id`) to the superseded event. Prior annotations are **never deleted or overwritten**.
2. A **Current View Snapshot** ([`ml/data/processed/citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv)):
   Maintains exactly one materialized row per candidate reflecting its latest valid assessment, ensuring 100% backward compatibility with existing unit tests, training filters, and data inspection scripts.

All 4 historical pilot annotations (`CAND-0001` through `CAND-0004`) were bootstrapped into the history ledger without inventing missing facts, and their quarantined status remains preserved. A comprehensive suite of 29 unit tests across `ml/tests/` passed cleanly in 0.82 seconds.

---

## 2. Pre-Implementation Safety & Backup Verification

Before modifying any code, a verified backup of the existing annotations ledger was created and validated:

- **Source File**: `ml/data/processed/citrus_annotations.csv`
- **Backup Destination**: `ml/data/reports/citrus_annotations_pre_phase3_backup.csv`
- **Source SHA-256**: `53dac40dad1ae72b830b05b8d0c5166e4d90e858a70ac2bbd38fe26ae98f4ea4`
- **Backup SHA-256**: `53dac40dad1ae72b830b05b8d0c5166e4d90e858a70ac2bbd38fe26ae98f4ea4`
- **Status**: Verified byte-for-byte identical.

The master review manifest [`ml/data/processed/citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) was inspected and verified with SHA-256 `3d30aa0549ead9f8a196d580fb6181f900f73ee8502ae2096845a07ea720a0a0` across 2,500 candidates.

---

## 3. Schema Specifications

### A. Append-Only History Ledger (`citrus_annotation_history.csv`)
File: [`ml/data/processed/citrus_annotation_history.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotation_history.csv)

| Column Name | Type | Description | Example Value |
| :--- | :--- | :--- | :--- |
| **`event_id`** | String | Unique, traceable event identifier. | `EVT-20261015124500-CAND-1160-0001` |
| **`candidate_id`** | String | Candidate manifest identifier. | `CAND-1160` |
| **`rel_path`** | String | Path to raw image file relative to `ml/data/raw/`. | `fruitnet/Good Quality_Fruits/Orange_Good/IMG20200728130753.jpg` |
| `dataset_source` | String | Data source repository. | `fruitnet` |
| `original_quality_label`| String | Source class label. | `Good Quality_Fruits/Orange_Good` |
| `quality_category` | String | Normalized quality group. | `good_quality` |
| `width`, `height` | Integer| Image pixel dimensions. | `256`, `192` |
| `format` | String | Image file encoding. | `JPEG` |
| `size_bytes` | Integer| File size in bytes. | `15420` |
| `sha256` | String | Cryptographic content hash of raw image. | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `dhash` | String | 64-bit difference hash for perceptual comparison. | `3c3c78e0e0f0f000` |
| `group_id` | String | Camera burst or sequence grouping identifier. | `IMG2020072813` |
| `candidate_suitability_flag`| String | Suitability flag for Stage-2 maturity training. | `primary_candidate` vs `defective_rot_specimen` |
| **`reviewer_maturity_label`**| String | Assessed visual maturity stage. | `underripe`, `partially_ripe`, `fully_ripe`, `uncertain` |
| **`reviewer_id`** | String | Identifier of human rater. | `reviewer_01` |
| **`review_confidence`** | String | Rater confidence rating. | `high`, `medium`, `low` |
| **`review_notes`** | String | Free-text morphological and quality defect notes. | `Flavedo shows 40% breaker orange` |
| `cultivar_verified` | Boolean| Boolean indicator of botanical verification. | `false` |
| `ground_truth_method` | String | Ground truth determination technique. | `human_visual_review` |
| **`event_type`** | String | Functional nature of the record. | `initial_annotation`, `revision`, `reassessment`, `historical_pilot` |
| **`previous_event_id`** | String | Pointer to superseded event (`none` if initial). | `EVT-20261015124500-CAND-1160-0001` or `none` |
| **`protocol_version`** | String | Active grading rubric specification. | `fruitnet_pilot_v1` (or `legacy_pilot_v0`) |
| **`event_at`** | Timestamp | ISO 8601 UTC timestamp of event generation. | `2026-10-15T12:45:00Z` |

### B. Current View Materialized Schema (`citrus_annotations.csv`)
File: [`ml/data/processed/citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv)  
Contains the 20 canonical fields representing the effective state of each annotated candidate. When an annotator revises an image, the history file appends event $N+1$, while `citrus_annotations.csv` materializes event $N+1$ in place for that candidate, guaranteeing that training loops only encounter the latest approved label.

---

## 4. Write-Safety Design & Crash Recovery

The implementation utilizes a **Two-Phase Write-Ahead Logging (WAL)** pattern with hardware-level synchronization:

```
[ Human Rater Submits Annotation / Revision ]
                     │
                     ▼
           [ 1. Input Validation ]
      • candidate_id in candidate_map
      • reviewer_maturity_label in ALLOWED_LABELS
      • review_confidence in ALLOWED_CONFIDENCE
                     │
                     ▼
       [ 2. Idempotency / Dedup Check ]
      • If event_id already recorded in self.event_ids:
        Return existing record (no duplicate write)
                     │
                     ▼
   [ PHASE 1: Write-Ahead History Append ]
      • Open citrus_annotation_history.csv in "a" mode
      • Append new event record (with previous_event_id link)
      • Flush buffer and call os.fsync(fileno)
      • Update in-memory history cache & latest event map
                     │
                     ▼
     [ PHASE 2: Current View Materialization ]
      • Update self.annotations[candidate_id] in memory
      • Write all active annotations to citrus_annotations.csv.tmp
      • Flush and call os.fsync(fileno)
      • Atomically replace destination via os.replace()
                     │
                     ▼
          [ Return Success to Client ]
```

### Crash Recovery Mechanism (`_reconcile_state`)
If a catastrophic power loss or process termination occurs during Phase 2 (after the history event is written to disk but before `citrus_annotations.csv` is replaced):
1. Upon restarting, [`AnnotationManager`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py#L48-L230) invokes `_reconcile_state()`.
2. It constructs a mapping of the latest historical event for each candidate from `citrus_annotation_history.csv`.
3. It compares this map against the materialized records in `citrus_annotations.csv`.
4. If any candidate is missing or contains an older timestamp than the latest history event, it immediately updates the in-memory state from history and triggers an atomic flush to `citrus_annotations.csv`.
5. **Guarantee**: History is the unalterable source of truth. The current view is self-healing and can be completely reconstructed from history if deleted or corrupted.

### Test Isolation Guard
To ensure that unit tests never pollute or corrupt the production workspace history:
- When `AnnotationManager` is initialized with a custom `annotations_path` (e.g. inside a `tempfile.TemporaryDirectory`), `history_path` automatically defaults to a co-located temporary file (`annotations_path.parent / f"{annotations_path.stem}_history.csv"`).
- Production files in `ml/data/processed/` are never touched during automated testing.

---

## 5. Preservation of Pilot Records & Quarantine

The four existing pilot records (`CAND-0001` through `CAND-0004`) were bootstrapped into the history ledger on initialization:
- **`event_id`**: `EVT-HIST-CAND-0001` through `EVT-HIST-CAND-0004`.
- **`event_type`**: Marked as `historical_pilot`.
- **`previous_event_id`**: Set to `none`.
- **`protocol_version`**: Marked as `legacy_pilot_v0`.
- **`event_at`**: Preserves original capture timestamps (`2026-10-14T16:43:39Z` to `16:44:55Z`).
- **`review_notes`**: Preserves quarantine string: `[PILOT_QUARANTINE: defective_rot_specimen excluded from Stage-2 maturity training; original_notes=...]`.
- **Stage 2 Training Filter**: `get_stage2_training_annotations()` continues to exclude all 4 pilot records because they originate from `Orange_Bad` (`candidate_suitability_flag == "defective_rot_specimen"`).

---

## 6. Comprehensive Test Results

All unit tests were executed using Python's standard library test runner:

```powershell
& ".venv\Scripts\python.exe" -m unittest discover -s ml/tests
```

### Test Suite Execution Output
```text
Ran 29 tests in 0.819s

OK
```

### Detailed Breakdown of Unit Tests:

#### A. Annotation Tool & History Ledger Tests (`ml/tests/test_annotation_tool.py` — 20 Tests)
| Test Identifier | Description / Tested Invariant | Result |
| :--- | :--- | :---: |
| `test_01_allowed_labels_validation` | Validates rejection of unauthorized labels and acceptance of allowed classes. | **PASS** |
| `test_02_allowed_confidence_validation`| Validates `high`, `medium`, `low` constraint. | **PASS** |
| `test_03_save_writes_to_separate_csv` | Confirms writes occur to designated annotations file, not manifest. | **PASS** |
| `test_04_original_manifest_unmodified` | Confirms candidate review manifest SHA-256 remains byte-identical. | **PASS** |
| `test_05_metadata_and_group_id_preserved`| Verifies burst `group_id`, resolution, and hashes are preserved in annotations. | **PASS** |
| `test_06_resume_functionality` | Verifies re-opening manager reloads state and counts correctly. | **PASS** |
| `test_07_revisiting_and_overwriting` | Current view has exactly one row per candidate when revised. | **PASS** |
| `test_08_skipping_logic` | Advances without leaving ghost records. | **PASS** |
| `test_09_uncertain_quarantine_support` | Verifies `uncertain` category persistence. | **PASS** |
| `test_10_primary_only_default_skips_defective`| Verifies default skips `Orange_Bad` and lands on `CAND-1160`. | **PASS** |
| `test_11_stage2_training_filter_excludes_defective_and_uncertain`| Tests `get_stage2_training_annotations()`. | **PASS** |
| `test_12_pilot_records_preserved_and_quarantined`| Verifies real `citrus_annotations.csv` pilot records remain quarantined. | **PASS** |
| `test_13_first_annotation_creates_history_event`| First save creates history event with `event_type="initial_annotation"`. | **PASS** |
| `test_14_revising_label_preserves_original_event`| Revision appends second event; event 1 is preserved intact. | **PASS** |
| `test_15_current_view_reflects_latest_valid_annotation`| Current view reflects final revision (`fully_ripe`), not prior stages. | **PASS** |
| `test_16_uncertain_annotation_and_reassessment`| Reassessing `uncertain` fruit logs `event_type="reassessment"` with backlink. | **PASS** |
| `test_17_deduplication_retried_writes` | Repeated identical `event_id` writes do not append duplicate records. | **PASS** |
| `test_18_malformed_history_file_fails_safely` | Corrupted history file missing required fields raises descriptive `ValueError`. | **PASS** |
| `test_19_crash_recovery_reconciles_missing_current_view`| Materializes missing current view records from existing history events. | **PASS** |
| `test_20_existing_pilot_records_in_real_history`| Confirms `citrus_annotation_history.csv` has 4 `historical_pilot` records. | **PASS** |

#### B. Review Manifest Tests (`ml/tests/test_curation.py` — 9 Tests)
| Test Identifier | Description / Tested Invariant | Result |
| :--- | :--- | :---: |
| `test_01_manifest_exists_and_row_count` | Confirms exactly 2,500 candidates exist in manifest. | **PASS** |
| `test_02_required_fieldnames_present` | Confirms all 19 required schema columns exist. | **PASS** |
| `test_03_zero_automated_ripeness_labels` | Asserts no synthetic or heuristic labels pre-exist in manifest. | **PASS** |
| `test_04_human_review_fields_empty` | Confirms all human review fields are clean pending review. | **PASS** |
| `test_05_category_breakdown` | Verifies 1,216 Good, 1,159 Bad, 125 Mixed distribution. | **PASS** |
| `test_06_suitability_flag_mapping` | Confirms 1,341 primary vs 1,159 defective split. | **PASS** |
| `test_07_relative_paths_exist_and_readable`| Asserts 100% of candidate images exist and open with PIL. | **PASS** |
| `test_08_group_id_preserved` | Verifies group IDs are populated. | **PASS** |
| `test_09_sha256_integrity` | Verifies file hashes match disk contents. | **PASS** |

---

## 7. Known Limitations & Architectural Notes

1. **Local Single-User Concurrency**:  
   The current file-locking and `fsync` strategy is optimized for a single annotator operating via local web browser or CLI. If multiple reviewers simultaneously write to the same network share without a coordinator, write contention could occur. For the upcoming 60-image pilot, reviewers will operate on independent split files or independent local instances, and their history ledgers will be merged deterministically via `event_id`.
2. **Sequential Memory Footprint**:  
   `AnnotationManager` currently caches the 2,500 candidate records and history events in memory. At 2,500 rows, this consumes less than 5 MB of RAM. If scaling to $>500,000$ images in future multi-season ingestion, streaming cursors or SQLite storage should replace in-memory dictionaries.

---

## 8. Exact Manual Steps for Running the Annotation Tool

The annotation tool requires zero external dependencies and runs in two distinct modes from the active workspace:

### Mode A: Responsive Local Web Interface (Recommended)

1. Open PowerShell in the project root:
   ```powershell
   cd C:\Users\PrabSandhu\Documents\codes\Agritech_
   ```
2. Launch the local annotation server:
   ```powershell
   & ".venv\Scripts\python.exe" ml\src\annotation_tool.py
   ```
3. Open a browser to:
   ```text
   http://127.0.0.1:8080
   ```
4. **Interface Controls**:
   - Keys `1`, `2`, `3`, `4`: Select `underripe`, `partially_ripe`, `fully_ripe`, `uncertain`.
   - Keys `Q`, `W`, `E`: Select confidence `high`, `medium`, `low`.
   - Key `Enter`: Save annotation to history + current view, and advance to next candidate.
   - Keys `Space` or `→`: Skip candidate without recording an annotation.
   - Key `←`: Navigate to previous candidate to inspect previous label or history event count.
   - The UI automatically displays the number of historical revision events recorded for each candidate.
   - The UI defaults to **Primary Candidates Only**, automatically skipping the 1,159 `Orange_Bad` rot specimens.

### Mode B: Headless Terminal / CLI Mode

For rapid terminal review without a web browser:
```powershell
& ".venv\Scripts\python.exe" ml\src\annotation_tool.py --cli
```
- Prompts for Reviewer ID.
- Displays candidate resolution, burst group, and existing historical events count.
- Accepts `1`, `2`, `3`, `4`, `s` (skip), `p` (previous), `q` (quit).

---

## 9. Next Steps

With Phase 3 complete:
- The history ledger is operational and verified.
- The 4 pilot annotations are quarantined and preserved.
- The candidate manifest and current view schemas are intact.
- **The workspace is ready for Phase 4: Selection and execution of the 60-image stratified dual-rater pilot.**
