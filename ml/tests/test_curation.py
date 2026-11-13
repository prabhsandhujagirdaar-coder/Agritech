#!/usr/bin/env python3
"""
AgriChain AI - Unit Tests for Citrus Candidate Review Manifest
==============================================================
Validates schema compliance, zero-automated-label invariant,
path integrity, duplicate prevention, and group_id preservation.
"""

import unittest
import csv
from pathlib import Path

WORKSPACE = Path(r"C:\Users\PrabSandhu\Documents\codes\Agritech_")
RAW_DIR = WORKSPACE / "ml" / "data" / "raw"
PROCESSED_DIR = WORKSPACE / "ml" / "data" / "processed"
REVIEW_CSV = PROCESSED_DIR / "citrus_candidate_review.csv"

REQUIRED_FIELDS = [
    "candidate_id", "rel_path", "dataset_source", "original_quality_label",
    "quality_category", "width", "height", "format", "size_bytes",
    "sha256", "dhash", "group_id", "candidate_suitability_flag",
    "reviewer_maturity_label", "reviewer_id", "review_confidence",
    "review_notes", "cultivar_verified", "ground_truth_method"
]

EXPECTED_CATEGORIES = {
    "Good Quality_Fruits/Orange_Good",
    "Bad Quality_Fruits/Orange_Bad",
    "Mixed Qualit_Fruits/Orange"
}

class TestCitrusCandidateReview(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not REVIEW_CSV.exists():
            raise FileNotFoundError(f"Review manifest missing: {REVIEW_CSV}")
        cls.rows = []
        with open(REVIEW_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cls.fieldnames = reader.fieldnames
            cls.rows = list(reader)

    def test_01_manifest_exists_and_row_count(self):
        """Manifest must exist and contain exactly 2,500 candidate images."""
        self.assertEqual(len(self.rows), 2500, "Manifest row count should be exactly 2500")

    def test_02_required_fieldnames_present(self):
        """Manifest header must contain all required schema columns."""
        for field in REQUIRED_FIELDS:
            self.assertIn(field, self.fieldnames, f"Missing required column: {field}")

    def test_03_zero_automated_ripeness_labels(self):
        """Crucial invariant: reviewer_maturity_label must be completely empty (no auto-guessing)."""
        prefilled = [r["candidate_id"] for r in self.rows if r["reviewer_maturity_label"].strip() != ""]
        self.assertEqual(len(prefilled), 0, f"Found pre-filled ripeness labels in {len(prefilled)} rows!")

    def test_04_human_review_fields_empty(self):
        """All human review fields must be empty pending expert inspection."""
        for r in self.rows:
            self.assertEqual(r["reviewer_id"].strip(), "")
            self.assertEqual(r["review_confidence"].strip(), "")
            self.assertEqual(r["cultivar_verified"].strip(), "")
            self.assertEqual(r["ground_truth_method"].strip(), "")

    def test_05_candidate_paths_exist_on_disk(self):
        """Sample and verify that candidate files physically exist on disk."""
        # Verify first 100 and last 100 files
        samples = self.rows[:100] + self.rows[-100:]
        for r in samples:
            full_path = RAW_DIR / r["rel_path"]
            self.assertTrue(full_path.exists(), f"Image path does not exist on disk: {full_path}")

    def test_06_no_duplicate_rel_paths(self):
        """All candidate filepaths in the manifest must be strictly unique."""
        paths = [r["rel_path"] for r in self.rows]
        self.assertEqual(len(paths), len(set(paths)), "Found duplicate relative file paths in review manifest!")

    def test_07_group_ids_preserved(self):
        """Every candidate must possess a non-empty group_id for zero-leakage splitting."""
        missing_group = [r["candidate_id"] for r in self.rows if not r["group_id"].strip()]
        self.assertEqual(len(missing_group), 0, f"Found {len(missing_group)} candidates missing group_id!")

    def test_08_original_quality_categories_valid(self):
        """Original labels must strictly match verified FruitNet orange categories."""
        labels = set(r["original_quality_label"] for r in self.rows)
        self.assertEqual(labels, EXPECTED_CATEGORIES, f"Unexpected categories in manifest: {labels - EXPECTED_CATEGORIES}")

    def test_09_suitability_flag_counts(self):
        """Validate candidate suitability flag distribution."""
        primary = sum(1 for r in self.rows if r["candidate_suitability_flag"] == "primary_candidate")
        rot = sum(1 for r in self.rows if r["candidate_suitability_flag"] == "defective_rot_specimen")
        self.assertEqual(primary, 1341, "Expected 1341 primary candidates (Good + Mixed)")
        self.assertEqual(rot, 1159, "Expected 1159 defective rot specimens (Bad)")

if __name__ == "__main__":
    unittest.main(verbosity=2)
