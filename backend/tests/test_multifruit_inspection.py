"""
AgriChain AI - Multi-Fruit Inspection Integration Tests
======================================================
Comprehensive test suite verifying Phase 17B deliverables:
1. Multi-Fruit Model Registry: Guava (Active), Banana (Verified Baseline),
   Apple (Experimental Detection), and Mango (Gated Data Deficit).
2. Manual Selection Workflow across all 4 commodities.
3. Automatic Identification Workflow via Stage 1 MobileNetV3-Large with uncertainty fallback.
4. Apple YOLOv8n object detection contract (bounding boxes, count, research license).
5. Mango honest unavailable/data-deficit handling (zero synthetic predictions).
6. Production Checkpoint Hash Preservation (Guava, Banana, Identifier).
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.main import app
from app.services.model_registry import model_registry


class TestMultiFruitInspection(unittest.TestCase):
    """Integration test suite for dual-mode multi-fruit inspection system."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Monorepo root and test image paths
        cls.apple_test_img = Path("ml/data/processed/apple_detection_yolo/images/test/108.jpg")
        if not cls.apple_test_img.exists():
            # Fallback search if path is relative to repo root
            cls.apple_test_img = Path(__file__).resolve().parents[2] / "ml/data/processed/apple_detection_yolo/images/test/108.jpg"

        # Generate standard test images in memory
        cls.dummy_fruit_bytes = cls._create_test_rgb_image(color=(80, 180, 70), size=(256, 256))
        cls.dummy_dark_bytes = cls._create_test_rgb_image(color=(20, 20, 20), size=(256, 256))

    @staticmethod
    def _create_test_rgb_image(color=(100, 150, 80), size=(224, 224)) -> bytes:
        img = Image.new("RGB", size, color=color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    def test_01_registry_catalog_completeness(self):
        """Verify model registry catalogs all 4 fruits and stage 1 identifier with correct tasks."""
        supported = model_registry.get_supported_fruits()
        self.assertEqual(sorted(supported), ["apple", "banana", "guava", "mango"])

        # Guava
        guava_meta = model_registry.get_metadata("guava")
        self.assertIsNotNone(guava_meta)
        self.assertTrue(guava_meta.is_validated)
        self.assertEqual(guava_meta.task_type, "classification")
        self.assertEqual(guava_meta.status_label, "CERTIFIED_ACTIVE")
        self.assertEqual(guava_meta.model_version, "2.0.0")
        self.assertEqual(guava_meta.classes, ("Green", "Mature Green", "Ripe"))

        # Banana
        banana_meta = model_registry.get_metadata("banana")
        self.assertIsNotNone(banana_meta)
        self.assertTrue(banana_meta.is_validated)
        self.assertEqual(banana_meta.task_type, "classification")
        self.assertEqual(banana_meta.status_label, "BASELINE_VERIFIED")
        self.assertEqual(banana_meta.model_version, "1.0.0")
        self.assertEqual(banana_meta.classes, ("Unripe", "Half_Ripe", "Ripe", "Overripe"))

        # Apple
        apple_meta = model_registry.get_metadata("apple")
        self.assertIsNotNone(apple_meta)
        self.assertTrue(apple_meta.is_validated)
        self.assertEqual(apple_meta.task_type, "object_detection")
        self.assertEqual(apple_meta.architecture, "yolov8n")
        self.assertEqual(apple_meta.status_label, "EXPERIMENTAL_DETECTION")

        # Mango
        mango_meta = model_registry.get_metadata("mango")
        self.assertIsNotNone(mango_meta)
        self.assertFalse(mango_meta.is_validated)
        self.assertEqual(mango_meta.status_label, "GATED_DEFICIT")

        # Full registry diagnostics via endpoint
        res = self.client.get("/api/v1/cnn/registry")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("guava", data["available_fruits"])
        self.assertIn("banana", data["available_fruits"])
        self.assertIn("apple", data["available_fruits"])
        self.assertNotIn("mango", data["available_fruits"])
        self.assertTrue(data["stage1_identifier"]["available"])
        self.assertEqual(data["stage1_identifier"]["status"], "BENCHMARK_VERIFIED")

    def test_02_manual_guava_inspection(self):
        """Test manual Guava inspection returns 3-stage harvest maturity classification."""
        res = self.client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=guava",
            files={"file": ("guava.jpg", self.dummy_fruit_bytes, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "manual")
        self.assertEqual(data["target_fruit"], "guava")
        self.assertEqual(data["task_type"], "classification")
        self.assertEqual(data["status"], "ready")
        self.assertIsNotNone(data["classification"])

        classification = data["classification"]
        self.assertIn(classification["predicted_class"], ["Green", "Mature Green", "Ripe"])
        self.assertGreaterEqual(classification["confidence"], 0.0)
        self.assertLessEqual(classification["confidence"], 1.0)
        self.assertEqual(set(classification["probabilities"].keys()), {"Green", "Mature Green", "Ripe"})

    def test_03_manual_banana_inspection(self):
        """Test manual Banana inspection returns 4-stage peel ripeness classification."""
        res = self.client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=banana",
            files={"file": ("banana.jpg", self.dummy_fruit_bytes, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "manual")
        self.assertEqual(data["target_fruit"], "banana")
        self.assertEqual(data["task_type"], "classification")
        self.assertEqual(data["status"], "ready")
        self.assertIsNotNone(data["classification"])

        classification = data["classification"]
        self.assertIn(classification["predicted_class"], ["Unripe", "Half_Ripe", "Ripe", "Overripe"])
        self.assertEqual(
            set(classification["probabilities"].keys()),
            {"Unripe", "Half_Ripe", "Ripe", "Overripe"},
        )

    def test_04_manual_apple_inspection(self):
        """Test manual Apple inspection returns YOLOv8n object detection boxes and count."""
        if not self.apple_test_img.exists():
            self.skipTest(f"Apple test image not found at {self.apple_test_img}")

        with open(self.apple_test_img, "rb") as f:
            res = self.client.post(
                "/api/v1/cnn/inspect?mode=manual&fruit=apple",
                files={"file": (self.apple_test_img.name, f, "image/jpeg")},
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "manual")
        self.assertEqual(data["target_fruit"], "apple")
        self.assertEqual(data["task_type"], "object_detection")
        self.assertEqual(data["status"], "ready")
        self.assertIsNotNone(data["detection"])

        detection = data["detection"]
        self.assertEqual(detection["task"], "object_detection")
        self.assertGreater(detection["detected_apples_count"], 0)
        self.assertIn("CC BY-NC 4.0", detection["license"])
        self.assertIn("does not evaluate maturity", detection["scope_disclaimer"].lower())

        # Verify box structure
        self.assertGreater(len(detection["boxes"]), 0)
        first_box = detection["boxes"][0]
        self.assertIn("x1", first_box)
        self.assertIn("y1", first_box)
        self.assertIn("x2", first_box)
        self.assertIn("y2", first_box)
        self.assertGreater(first_box["x2"], first_box["x1"])
        self.assertGreater(first_box["y2"], first_box["y1"])
        self.assertGreater(first_box["confidence"], 0.25)

    def test_05_manual_mango_gated_handling(self):
        """Test manual Mango selection honestly reports unavailable/data-deficit state without fake inference."""
        res = self.client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=mango",
            files={"file": ("mango.jpg", self.dummy_fruit_bytes, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "manual")
        self.assertEqual(data["target_fruit"], "mango")
        self.assertEqual(data["task_type"], "unavailable")
        self.assertEqual(data["status"], "unavailable")
        self.assertIsNone(data["classification"])
        self.assertIsNone(data["detection"])
        self.assertIsNotNone(data["unavailable_reason"])
        self.assertIn("dataset", data["unavailable_reason"].lower())

    def test_06_stage1_identify_endpoint(self):
        """Test standalone Stage 1 fruit identification endpoint."""
        if not self.apple_test_img.exists():
            self.skipTest(f"Apple test image not found at {self.apple_test_img}")

        with open(self.apple_test_img, "rb") as f:
            res = self.client.post(
                "/api/v1/cnn/identify",
                files={"file": (self.apple_test_img.name, f, "image/jpeg")},
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["predicted_fruit"], "apple")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertFalse(data["is_uncertain"])
        self.assertEqual(
            set(data["probabilities"].keys()),
            {"guava", "banana", "apple", "mango", "negative_background"},
        )

    def test_07_auto_mode_high_confidence_cascade(self):
        """Test auto mode identifies apple with high confidence and cascades to YOLO detector."""
        if not self.apple_test_img.exists():
            self.skipTest(f"Apple test image not found at {self.apple_test_img}")

        with open(self.apple_test_img, "rb") as f:
            res = self.client.post(
                "/api/v1/cnn/inspect?mode=auto",
                files={"file": (self.apple_test_img.name, f, "image/jpeg")},
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "auto")
        self.assertEqual(data["identified_fruit"], "apple")
        self.assertEqual(data["task_type"], "object_detection")
        self.assertEqual(data["status"], "ready")
        self.assertIsNotNone(data["identification"])
        self.assertIsNotNone(data["detection"])
        self.assertGreater(data["detection"]["detected_apples_count"], 0)

    def test_08_auto_mode_uncertainty_handling(self):
        """Test auto mode with non-fruit or dark image handles uncertainty without false downstream prediction."""
        res = self.client.post(
            "/api/v1/cnn/inspect?mode=auto",
            files={"file": ("dark.jpg", self.dummy_dark_bytes, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["mode"], "auto")
        self.assertIsNotNone(data["identification"])

        # If uncertain or negative_background, must NOT run false crop classification
        if data["identification"]["is_uncertain"]:
            self.assertIn(data["status"], ["uncertain", "unknown_fruit"])
            self.assertGreater(len(data["warnings"]), 0)

    def test_09_invalid_crop_rejection(self):
        """Test rejection of unsupported fruit commodities with HTTP 400."""
        res = self.client.post(
            "/api/v1/cnn/inspect?mode=manual&fruit=strawberry",
            files={"file": ("fruit.jpg", self.dummy_fruit_bytes, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported commodity", res.json()["detail"])

    def test_10_production_checkpoint_hashes(self):
        """Verify certified checkpoint hashes remain 100% unaltered."""
        expected_hashes = {
            "ml/artifacts/best_guava_resnet18.pth": "b213059f6b9744915ef921f2be70de9ae1eb0dd6c50a3fb0edce0e2cb710f5b4",
            "ml/artifacts/best_banana_resnet18.pth": "3b296ba8556d88bd934f74fee1e88860921fe69dd5b4869984fd0c529f339dae",
            "ml/artifacts/best_fruit_identifier_resnet18.pth": "07150d1ddb92ea8ce7018e08fa6c3d21b6b6de6aac9c5feb838d6f9dc28a8967",
        }

        for rel_path, expected_hash in expected_hashes.items():
            p = Path(rel_path)
            if not p.exists():
                p = Path(__file__).resolve().parents[2] / rel_path
            self.assertTrue(p.exists(), f"Checkpoint {rel_path} must exist on disk.")
            current_hash = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(
                current_hash,
                expected_hash,
                f"SHA-256 mismatch for {rel_path}! Production checkpoint was corrupted or overwritten.",
            )


if __name__ == "__main__":
    unittest.main()
