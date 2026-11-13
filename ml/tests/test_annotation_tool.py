#!/usr/bin/env python3
"""
AgriChain AI - Unit Tests for Citrus Annotation Tool
====================================================
Tests:
- Label & confidence validation (allowed vs rejected values)
- Safe persistence into separate CSV (citrus_annotations.csv)
- Strict preservation of the source review manifest (hash unchanged)
- Resuming previous annotations seamlessly
- Revisiting / overwriting existing annotations
- Skipping candidates without generating false records
- Group ID and metadata preservation
"""

import unittest
import hashlib
import tempfile
import csv
import sys
from pathlib import Path

# Add project root to path
WORKSPACE = Path(r"C:\Users\PrabSandhu\Documents\codes\Agritech_")
sys_path = str(WORKSPACE)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from ml.src.annotation_tool import AnnotationManager, ALLOWED_LABELS, ALLOWED_CONFIDENCE

REVIEW_MANIFEST = WORKSPACE / "ml" / "data" / "processed" / "citrus_candidate_review.csv"

def get_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class TestAnnotationTool(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_annotations_csv = Path(self.temp_dir.name) / "test_annotations.csv"
        self.temp_history_csv = Path(self.temp_dir.name) / "test_annotations_history.csv"
        # Record initial manifest hash
        self.initial_manifest_hash = get_file_sha256(REVIEW_MANIFEST)
        self.manager = AnnotationManager(
            manifest_path=REVIEW_MANIFEST,
            annotations_path=self.temp_annotations_csv,
            history_path=self.temp_history_csv
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_allowed_labels_validation(self):
        """Valid labels must be accepted; invalid labels must raise ValueError."""
        # Valid labels
        for label in ["underripe", "partially_ripe", "fully_ripe", "uncertain"]:
            record = self.manager.save_annotation(
                candidate_id="CAND-0001",
                label=label,
                confidence="high",
                reviewer_id="test_reviewer"
            )
            self.assertEqual(record["reviewer_maturity_label"], label)

        # Invalid labels
        for invalid in ["ripe", "green", "sweet", "mature", "bad_quality", ""]:
            with self.assertRaises(ValueError):
                self.manager.save_annotation(
                    candidate_id="CAND-0001",
                    label=invalid,
                    confidence="high"
                )

    def test_02_allowed_confidence_validation(self):
        """Confidence must be high, medium, or low."""
        for conf in ["high", "medium", "low"]:
            record = self.manager.save_annotation(
                candidate_id="CAND-0001",
                label="underripe",
                confidence=conf
            )
            self.assertEqual(record["review_confidence"], conf)

        for invalid in ["very_high", "100%", "maybe", ""]:
            with self.assertRaises(ValueError):
                self.manager.save_annotation(
                    candidate_id="CAND-0001",
                    label="underripe",
                    confidence=invalid
                )

    def test_03_save_writes_to_separate_csv(self):
        """Annotations must write to the separate CSV without touching the manifest."""
        self.manager.save_annotation(
            candidate_id="CAND-0001",
            label="underripe",
            confidence="high",
            notes="Very green test specimen"
        )
        self.assertTrue(self.temp_annotations_csv.exists())
        
        with open(self.temp_annotations_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate_id"], "CAND-0001")
        self.assertEqual(rows[0]["reviewer_maturity_label"], "underripe")
        self.assertEqual(rows[0]["review_notes"], "Very green test specimen")

    def test_04_original_manifest_unmodified(self):
        """Source manifest must retain exact identical SHA-256 hash before and after saves."""
        self.manager.save_annotation("CAND-0002", "partially_ripe", "medium")
        self.manager.save_annotation("CAND-0003", "fully_ripe", "high")
        
        current_manifest_hash = get_file_sha256(REVIEW_MANIFEST)
        self.assertEqual(
            self.initial_manifest_hash,
            current_manifest_hash,
            "CRITICAL ERROR: Original candidate manifest was modified!"
        )

    def test_05_metadata_and_group_id_preserved(self):
        """Saved annotation must preserve original group_id, rel_path, and dimensions."""
        record = self.manager.save_annotation("CAND-0001", "underripe", "high")
        cand = self.manager.candidate_map["CAND-0001"]

        self.assertEqual(record["group_id"], cand["group_id"])
        self.assertEqual(record["rel_path"], cand["rel_path"])
        self.assertEqual(record["width"], cand["width"])
        self.assertEqual(record["height"], cand["height"])
        self.assertEqual(record["sha256"], cand["sha256"])

    def test_06_resume_functionality(self):
        """A new manager instance must reload existing annotations safely."""
        self.manager.save_annotation("CAND-0001", "underripe", "high")
        self.manager.save_annotation("CAND-0005", "fully_ripe", "medium")

        # Create new manager pointing to the same file
        resumed_manager = AnnotationManager(
            manifest_path=REVIEW_MANIFEST,
            annotations_path=self.temp_annotations_csv
        )
        stats = resumed_manager.get_stats()
        self.assertEqual(stats["total_annotated"], 2)
        self.assertIn("CAND-0001", resumed_manager.annotations)
        self.assertIn("CAND-0005", resumed_manager.annotations)
        self.assertEqual(resumed_manager.annotations["CAND-0005"]["reviewer_maturity_label"], "fully_ripe")

    def test_07_revisiting_and_overwriting(self):
        """Revisiting a candidate and updating its label must overwrite in-place without duplicate rows."""
        self.manager.save_annotation("CAND-0010", "underripe", "low", "Initial guess")
        self.manager.save_annotation("CAND-0010", "partially_ripe", "high", "Corrected upon closer review")

        with open(self.temp_annotations_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        self.assertEqual(len(rows), 1, "There should be exactly one record for CAND-0010")
        self.assertEqual(rows[0]["reviewer_maturity_label"], "partially_ripe")
        self.assertEqual(rows[0]["review_confidence"], "high")
        self.assertEqual(rows[0]["review_notes"], "Corrected upon closer review")

    def test_08_skipping_logic(self):
        """Skipping should simply leave the candidate unannotated."""
        stats_before = self.manager.get_stats()
        # Pretend reviewer skipped CAND-0001 and only annotated CAND-0002
        self.manager.save_annotation("CAND-0002", "fully_ripe", "high")
        stats_after = self.manager.get_stats()

        self.assertEqual(stats_after["total_annotated"], stats_before["total_annotated"] + 1)
        self.assertNotIn("CAND-0001", self.manager.annotations)
        self.assertIn("CAND-0002", self.manager.annotations)

    def test_09_uncertain_quarantine_support(self):
        """Uncertain class must be supported for ambiguous/corrupted fruit."""
        record = self.manager.save_annotation(
            candidate_id="CAND-0004",
            label="uncertain",
            confidence="high",
            notes="Glare obscures 50% of fruit peel"
        )
        self.assertEqual(record["reviewer_maturity_label"], "uncertain")

    def test_10_primary_only_default_skips_defective(self):
        """get_first_unannotated_index() must default to primary_only=True and return the first primary candidate."""
        # Default call (primary_only=True)
        idx_default = self.manager.get_first_unannotated_index()
        self.assertEqual(idx_default, 1159)
        cand, _ = self.manager.get_candidate(idx_default)
        self.assertEqual(cand["candidate_id"], "CAND-1160")
        self.assertEqual(cand["candidate_suitability_flag"], "primary_candidate")

        # Explicit primary_only=False must return index 0
        idx_all = self.manager.get_first_unannotated_index(primary_only=False)
        self.assertEqual(idx_all, 0)
        cand0, _ = self.manager.get_candidate(idx_all)
        self.assertEqual(cand0["candidate_id"], "CAND-0001")
        self.assertEqual(cand0["candidate_suitability_flag"], "defective_rot_specimen")

    def test_11_stage2_training_filter_excludes_defective_and_uncertain(self):
        """get_stage2_training_annotations() must exclude defective_rot_specimen, [PILOT_QUARANTINE, and uncertain."""
        # 1. Defective rot specimen (CAND-0001)
        self.manager.save_annotation("CAND-0001", "fully_ripe", "high")
        # 2. Primary candidate with valid label (CAND-1160)
        self.manager.save_annotation("CAND-1160", "fully_ripe", "high")
        # 3. Primary candidate with uncertain label (CAND-1161)
        self.manager.save_annotation("CAND-1161", "uncertain", "low")
        # 4. Primary candidate with [PILOT_QUARANTINE in notes (CAND-1162)
        self.manager.save_annotation("CAND-1162", "fully_ripe", "high", notes="[PILOT_QUARANTINE: test flag]")

        stage2 = self.manager.get_stage2_training_annotations()
        self.assertEqual(len(stage2), 1)
        self.assertEqual(stage2[0]["candidate_id"], "CAND-1160")
        self.assertEqual(stage2[0]["reviewer_maturity_label"], "fully_ripe")

        stats = self.manager.get_stats()
        self.assertEqual(stats["primary_candidates_total"], 1341)
        self.assertEqual(stats["stage2_valid_annotated"], 1)
        self.assertEqual(stats["quarantined_or_defective_annotated"], 2)

    def test_12_pilot_records_preserved_and_quarantined(self):
        """Real citrus_annotations.csv must preserve CAND-0001..0004 with [PILOT_QUARANTINE notes, yielding 0 stage2 rows."""
        real_csv = WORKSPACE / "ml" / "data" / "processed" / "citrus_annotations.csv"
        self.assertTrue(real_csv.exists(), "citrus_annotations.csv must exist")

        real_manager = AnnotationManager(
            manifest_path=REVIEW_MANIFEST,
            annotations_path=real_csv
        )
        for cid in ["CAND-0001", "CAND-0002", "CAND-0003", "CAND-0004"]:
            self.assertIn(cid, real_manager.annotations)
            ann = real_manager.annotations[cid]
            self.assertIn("[PILOT_QUARANTINE", ann["review_notes"])
        
        self.assertEqual(real_manager.annotations["CAND-0001"]["reviewer_maturity_label"], "fully_ripe")
        self.assertEqual(real_manager.annotations["CAND-0002"]["reviewer_maturity_label"], "partially_ripe")
        self.assertEqual(real_manager.annotations["CAND-0003"]["reviewer_maturity_label"], "underripe")
        self.assertEqual(real_manager.annotations["CAND-0004"]["reviewer_maturity_label"], "uncertain")

        # Must yield 0 valid stage2 training annotations
        stage2 = real_manager.get_stage2_training_annotations()
        self.assertEqual(len(stage2), 0)

    def test_13_first_annotation_creates_history_event(self):
        """First annotation of a candidate must record an initial_annotation history event."""
        self.manager.save_annotation(
            candidate_id="CAND-1160",
            label="underripe",
            confidence="high",
            notes="First test event"
        )
        hist = self.manager.get_candidate_history("CAND-1160")
        self.assertEqual(len(hist), 1)
        ev = hist[0]
        self.assertEqual(ev["candidate_id"], "CAND-1160")
        self.assertEqual(ev["reviewer_maturity_label"], "underripe")
        self.assertEqual(ev["event_type"], "initial_annotation")
        self.assertEqual(ev["previous_event_id"], "none")
        self.assertEqual(ev["protocol_version"], "fruitnet_pilot_v1")

        # Verify on disk
        with open(self.temp_history_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_id"], ev["event_id"])

    def test_14_revising_label_preserves_original_event(self):
        """Revising a label must append a revision event with previous_event_id reference, never erasing the original."""
        # Initial
        self.manager.save_annotation(
            candidate_id="CAND-1161",
            label="underripe",
            confidence="low",
            notes="Preliminary observation"
        )
        # Revision
        self.manager.save_annotation(
            candidate_id="CAND-1161",
            label="partially_ripe",
            confidence="high",
            notes="Revised upon closer inspection of color break"
        )

        hist = self.manager.get_candidate_history("CAND-1161")
        self.assertEqual(len(hist), 2, "History must contain both original and revision events")
        ev1, ev2 = hist[0], hist[1]

        # Verify event 1 preserved intact
        self.assertEqual(ev1["reviewer_maturity_label"], "underripe")
        self.assertEqual(ev1["review_confidence"], "low")
        self.assertEqual(ev1["event_type"], "initial_annotation")
        self.assertEqual(ev1["previous_event_id"], "none")

        # Verify event 2 points back to event 1
        self.assertEqual(ev2["reviewer_maturity_label"], "partially_ripe")
        self.assertEqual(ev2["review_confidence"], "high")
        self.assertEqual(ev2["event_type"], "revision")
        self.assertEqual(ev2["previous_event_id"], ev1["event_id"])

        # Check raw history file has both rows
        with open(self.temp_history_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["reviewer_maturity_label"], "underripe")
        self.assertEqual(rows[1]["reviewer_maturity_label"], "partially_ripe")

    def test_15_current_view_reflects_latest_valid_annotation(self):
        """Current view CSV must reflect exactly one materialized row showing the latest revision."""
        self.manager.save_annotation("CAND-1162", "underripe", "low", "First")
        self.manager.save_annotation("CAND-1162", "partially_ripe", "medium", "Second")
        self.manager.save_annotation("CAND-1162", "fully_ripe", "high", "Third final")

        # History has 3 events
        hist = self.manager.get_candidate_history("CAND-1162")
        self.assertEqual(len(hist), 3)

        # Current view on disk has exactly 1 row
        with open(self.temp_annotations_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        c1162_rows = [r for r in rows if r["candidate_id"] == "CAND-1162"]
        self.assertEqual(len(c1162_rows), 1)
        self.assertEqual(c1162_rows[0]["reviewer_maturity_label"], "fully_ripe")
        self.assertEqual(c1162_rows[0]["review_notes"], "Third final")

    def test_16_uncertain_annotation_and_reassessment(self):
        """Uncertain quarantine annotations remain distinct, and later reassessment records reassessment event."""
        # Step 1: Initial uncertain quarantine
        self.manager.save_annotation("CAND-1163", "uncertain", "high", "Glare obscuring flavedo")
        curr = self.manager.annotations["CAND-1163"]
        self.assertEqual(curr["reviewer_maturity_label"], "uncertain")
        # Excluded from stage 2 training
        self.assertEqual(len(self.manager.get_stage2_training_annotations()), 0)

        # Step 2: Reassessment
        self.manager.save_annotation("CAND-1163", "fully_ripe", "high", "Reassessed with contrast adjustment")
        hist = self.manager.get_candidate_history("CAND-1163")
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["reviewer_maturity_label"], "uncertain")
        self.assertEqual(hist[0]["event_type"], "initial_annotation")
        self.assertEqual(hist[1]["reviewer_maturity_label"], "fully_ripe")
        self.assertEqual(hist[1]["event_type"], "reassessment")
        self.assertEqual(hist[1]["previous_event_id"], hist[0]["event_id"])

        # Now included in stage 2 training
        self.assertEqual(len(self.manager.get_stage2_training_annotations()), 1)

    def test_17_deduplication_retried_writes(self):
        """Repeated event IDs or retried writes must be idempotent and not create duplicate events."""
        custom_eid = "EVT-TEST-IDEMPOTENT-001"
        r1 = self.manager.save_annotation(
            candidate_id="CAND-1164",
            label="underripe",
            confidence="high",
            notes="Idempotent test",
            event_id=custom_eid
        )
        r2 = self.manager.save_annotation(
            candidate_id="CAND-1164",
            label="underripe",
            confidence="high",
            notes="Idempotent test duplicate retry",
            event_id=custom_eid
        )

        hist = self.manager.get_candidate_history("CAND-1164")
        self.assertEqual(len(hist), 1, "Retried write with identical event_id must not create duplicate history row")
        self.assertEqual(hist[0]["event_id"], custom_eid)

    def test_18_malformed_history_file_fails_safely(self):
        """A corrupt or malformed history file missing required schema headers must raise a descriptive ValueError."""
        bad_history_path = Path(self.temp_dir.name) / "bad_history.csv"
        bad_history_path.write_text("random_col1,random_col2\nval1,val2\n", encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            AnnotationManager(
                manifest_path=REVIEW_MANIFEST,
                annotations_path=self.temp_annotations_csv,
                history_path=bad_history_path
            )
        self.assertIn("missing required fields", str(ctx.exception))

    def test_19_crash_recovery_reconciles_missing_current_view(self):
        """If current view annotations CSV is lost or out-of-sync with history, AnnotationManager reconciles from history."""
        # Create a manager and write 2 annotations
        self.manager.save_annotation("CAND-1165", "underripe", "high", "Candidate 1165")
        self.manager.save_annotation("CAND-1166", "fully_ripe", "medium", "Candidate 1166")

        # Simulate a crash where current view was wiped or corrupted, but history ledger survived
        corrupted_annotations_csv = Path(self.temp_dir.name) / "corrupted_annotations.csv"
        # Start with empty file (or non-existent)
        if corrupted_annotations_csv.exists():
            corrupted_annotations_csv.unlink()

        # Reopen AnnotationManager pointing to the empty annotations and existing history
        recovered_manager = AnnotationManager(
            manifest_path=REVIEW_MANIFEST,
            annotations_path=corrupted_annotations_csv,
            history_path=self.temp_history_csv
        )

        # Both candidates must be recovered into current view
        self.assertIn("CAND-1165", recovered_manager.annotations)
        self.assertIn("CAND-1166", recovered_manager.annotations)
        self.assertEqual(recovered_manager.annotations["CAND-1165"]["reviewer_maturity_label"], "underripe")
        self.assertEqual(recovered_manager.annotations["CAND-1166"]["reviewer_maturity_label"], "fully_ripe")
        self.assertTrue(corrupted_annotations_csv.exists())

    def test_20_existing_pilot_records_in_real_history(self):
        """Real citrus_annotation_history.csv must preserve CAND-0001..0004 as historical_pilot events."""
        real_hist = WORKSPACE / "ml" / "data" / "processed" / "citrus_annotation_history.csv"
        self.assertTrue(real_hist.exists(), "Real citrus_annotation_history.csv must exist")

        with open(real_hist, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        hist_cids = [r["candidate_id"] for r in rows]
        for cid in ["CAND-0001", "CAND-0002", "CAND-0003", "CAND-0004"]:
            self.assertIn(cid, hist_cids)
            r = next(row for row in rows if row["candidate_id"] == cid)
            self.assertEqual(r["event_type"], "historical_pilot")
            self.assertEqual(r["previous_event_id"], "none")
            self.assertEqual(r["protocol_version"], "legacy_pilot_v0")
            self.assertIn("[PILOT_QUARANTINE", r["review_notes"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
