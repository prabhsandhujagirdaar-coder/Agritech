# AgriChain AI — Citrus Maturity Annotation Guide

**Document**: `docs/deep-learning/annotation_guide.md`  
**Tool**: [`ml/src/annotation_tool.py`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/src/annotation_tool.py)  
**Manifest Source**: `ml/data/processed/citrus_candidate_review.csv` (Read-Only)  
**Output Destination**: `ml/data/processed/citrus_annotations.csv`  

---

## 1. Scientific Disclaimer & Research Restraint

> [!WARNING]
> **UNVERIFIED PROXY COHORT CAVEAT**:  
> The candidate images in this review manifest originate from the **FruitNet Indian Fruits Dataset** (`Orange_Good`, `Orange_Bad`, `Orange_Mixed`). While these images depict Indian citrus (*Citrus reticulata* / Nagpur Mandarin), they are **NOT confirmed Punjab Kinnow Mandarin** (*King* $\times$ *Willow Leaf* hybrid).  
> Furthermore, **external visual appearance alone cannot measure internal biochemical maturity (TSS/Brix and Titratable Acidity)**. This annotation tool establishes an initial visual maturity baseline for model development, which must subsequently be validated against farm-gate harvest testing.

---

## 2. Launching the Annotation Tool

The annotation tool is completely self-contained within Python's standard library. It requires zero third-party GUI or web framework dependencies and runs in two distinct modes:

### Mode A: Lightweight Web Server (Recommended)
Launches a local, responsive web application with keyboard shortcuts and instant image rendering:

```powershell
# From the project root:
& ".venv\Scripts\python.exe" ml\src\annotation_tool.py
```
Open your browser to:
```text
http://127.0.0.1:8080
```
*(To use a different port, append `--port <number>`, e.g., `--port 8085`)*

### Mode B: Terminal / CLI Mode (Headless)
Runs directly in the PowerShell console for rapid inspection without a web browser:

```powershell
& ".venv\Scripts\python.exe" ml\src\annotation_tool.py --cli
```

---

## 3. Web Interface & Keyboard Navigation

The web interface is designed for rapid, low-friction evaluation with one-key shortcuts:

| Key | Action | Description |
| :---: | :--- | :--- |
| **`1`** | Select **Underripe** | $>60\%$ deep green or yellowish-green peel, tightly packed oil glands |
| **`2`** | Select **Partially Ripe** | $25\% - 60\%$ yellow-orange breaker coloration |
| **`3`** | Select **Fully Ripe** | $>80\%$ uniform golden-orange peel, smooth flavedo |
| **`4`** | Select **Uncertain / Quarantine** | Heavy glare, rot/decay, motion blur, or ambiguous coloration |
| **`Q`** | Confidence: **High** | Clear view, unambiguous multi-attribute consensus |
| **`W`** | Confidence: **Medium** | Transitional breaker or minor cosmetic surface blemish |
| **`E`** | Confidence: **Low** | Difficult lighting or conflicting visual indicators |
| **`Enter`** | **Save & Next** | Saves annotation to `citrus_annotations.csv` and loads next image |
| **`Space`** / **`→`** | **Skip / Next** | Advances to next candidate without recording an annotation |
| **`←`** | **Previous** | Returns to previous candidate to inspect or revise annotation |

---

## 4. Multi-Attribute Agricultural Grading Rubric

Annotators must evaluate each citrus specimen using a **four-attribute physical rubric**, rather than relying on peel color alone:

```
                            [ MULTI-ATTRIBUTE EVALUATION ]
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         ▼                                ▼                                ▼
  [ 1. Flavedo Hue ]            [ 2. Gland Texture ]           [ 3. Calyx / Button ]
 • Underripe: >60% dark green   • Underripe: Raised, pebble    • Underripe: Firm, light green
 • Partial: 25%–60% breaker     • Partial: Moderate stretch    • Partial: Greenish-yellow
 • Ripe: >80% golden-orange     • Ripe: Expanded, glossy, pliant• Ripe: Intact, dry ring
```

### Detailed Evaluation Standards:
1. **Flavedo Color Progression**:
   - `underripe`: Deep dark green or olive green covering $>60\%$ of rind.
   - `partially_ripe`: Color-break stage with $25\%$ to $60\%$ yellow-orange transition.
   - `fully_ripe`: Rich golden-orange covering $>80\%$ of rind.
2. **Oil Gland Morphology (Flavedo Texture)**:
   - Immature fruit exhibits dense, raised, protruding oil glands (coarse pebble texture).
   - Mature fruit exhibits expanded, flattened, glossy glands and loose peel pliancy.
3. **Calyx ("Button") Status**:
   - `underripe`: Tightly bound, pale green button adhering firmly to the stem end.
   - `fully_ripe`: Slightly darkened, dry-ringed button; intact pedicel.
   - *Quarantine Flag*: Blackened, moldy button indicates *Diplodia* stem-end rot.
4. **When to Mark `uncertain`**:
   - Severe specular reflection (flash glare) obscuring $>30\%$ of the fruit surface.
   - Heavy camera defocus / motion blur.
   - Rotted fruit (`defective_rot_specimen`) where fungal mycelium or decomposition conceals the natural peel color.

---

## 5. Persistence, Resuming, and Safety Invariants

### 1. Dual-Storage Architecture: History Ledger vs Current View
To ensure complete audibility and zero data loss during multi-reviewer annotation or revisions, the system maintains two synchronized artifacts:
1. **Append-Only History Ledger** ([`ml/data/processed/citrus_annotation_history.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotation_history.csv)):
   Every save or label revision appends a new immutable record with an event ID, event type (`initial_annotation`, `revision`, `reassessment`), timestamp, and a reference pointer to the previous event (`previous_event_id`). Previous annotations are **never overwritten or deleted**.
2. **Current View Snapshot** ([`ml/data/processed/citrus_annotations.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_annotations.csv)):
   Maintains exactly one materialized record per candidate reflecting its latest active annotation, ensuring 100% backward compatibility with downstream training scripts.

### 2. Two-Phase Write Safety & Crash Recovery
- **Write-Ahead Log (WAL)**: When an annotation is submitted, it is flushed to the append-only history ledger with `os.fsync()` before updating the current view.
- **Atomic Replacement**: Updates to `citrus_annotations.csv` are written to a `.tmp` file and atomically replaced.
- **Crash Recovery**: If an unexpected crash occurs between writes, the `AnnotationManager` automatically reconciles `citrus_annotations.csv` from the latest events in `citrus_annotation_history.csv` on startup.

### 3. Source Manifest Preservation
- The candidate manifest [`ml/data/processed/citrus_candidate_review.csv`](file:///C:/Users/PrabSandhu/Documents/codes/Agritech_/ml/data/processed/citrus_candidate_review.csv) is strictly **read-only**.
- All annotations and revisions are recorded without touching the master candidate manifest.

---

## 6. Output Schemas

### A. Current View Schema (`citrus_annotations.csv`)

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `candidate_id` | String | Unique identifier (e.g., `CAND-0001` to `CAND-2500`). |
| `rel_path` | String | Relative path to image file in `ml/data/raw/`. |
| `dataset_source` | String | `fruitnet` |
| `original_quality_label` | String | Original category (e.g. `Good Quality_Fruits/Orange_Good`). |
| `quality_category` | String | `good_quality`, `bad_quality`, `mixed_quality`. |
| `width`, `height` | Integer | Image pixel dimensions. |
| `sha256`, `dhash` | String | Cryptographic and perceptual content hashes. |
| `group_id` | String | Sequence/burst grouping identifier. |
| `candidate_suitability_flag` | String | `primary_candidate` vs `defective_rot_specimen`. |
| **`reviewer_maturity_label`** | String | `underripe`, `partially_ripe`, `fully_ripe`, or `uncertain`. |
| **`reviewer_id`** | String | Identifier of the annotator (e.g. `reviewer_01`). |
| **`review_confidence`** | String | `high`, `medium`, or `low`. |
| **`review_notes`** | String | Free-text morphological or defect observations. |
| **`cultivar_verified`** | Boolean | `false` (records that cultivar is unverified Indian citrus). |
| **`ground_truth_method`** | String | `human_visual_review` |
| **`annotated_at`** | Timestamp | ISO 8601 UTC timestamp of latest annotation save. |

### B. Append-Only History Ledger Schema (`citrus_annotation_history.csv`)

In addition to all candidate metadata, the history ledger records:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `event_id` | String | Unique event ID (e.g., `EVT-20261015124500-CAND-1160-0001`). |
| `event_type` | String | `initial_annotation`, `revision`, `reassessment`, or `historical_pilot`. |
| `previous_event_id` | String | `none` for initial events, or ID of the superseded revision event. |
| `protocol_version` | String | Protocol specification version (e.g. `fruitnet_pilot_v1`). |
| `event_at` | Timestamp | ISO 8601 UTC timestamp of this specific event. |

