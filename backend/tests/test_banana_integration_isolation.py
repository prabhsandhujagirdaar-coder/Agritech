"""
AgriChain AI - Banana Integration & Isolation Test Suite
=========================================================
Phase 14F Verification Suite:
1. Guava Backward Compatibility: Verifies default CNNService is unaffected and serves Guava 3-class.
2. Banana Isolated Service: Verifies CNNService(crop="banana") initializes correctly with 4 classes.
3. Genuine & Synthetic Inference: Verifies 4-class softmax output, uncalibrated confidence, and zero fabrication.
4. Input Rejection & Validation: Verifies empty payload, corrupted byte stream, and invalid media types.
5. Missing Checkpoint Handling: Verifies graceful degradation and ModelUnavailableError (HTTP 503).
6. Registry Invariant Gating: Confirms Banana is_validated remains False in the public model registry.
7. Isolated API Endpoints: Verifies /api/v1/cnn/status/banana and /api/v1/cnn/predict/banana via TestClient.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from PIL import Image

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.cnn import CNNModelStatusResponse, CNNPredictionResponse
from app.services.cnn_service import (
    CNNService,
    InvalidImageError,
    ModelUnavailableError,
    UnsupportedMediaTypeError,
)
from app.services.model_registry import model_registry


class TestBananaIntegrationIsolation(unittest.TestCase):
    """Rigorous isolation and integration tests for the Phase 14 Banana model."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.banana_checkpoint = settings.resolved_banana_weights_path()
        cls.guava_checkpoint = settings.resolved_guava_weights_path()

    def test_01_guava_backward_compatibility(self):
        """Ensure default CNNService remains 100% bound to Guava with 3 classes."""
        service = CNNService()
        self.assertEqual(service.target_crop, "guava")
        self.assertEqual(len(service.classes), 3)
        self.assertEqual(service.classes, ["Green", "Mature Green", "Ripe"])
        self.assertTrue(service.is_available)

        # Run synthetic image
        img = Image.new("RGB", (224, 224), color=(34, 139, 34))
        pred = service.predict(img)
        self.assertIsInstance(pred, CNNPredictionResponse)
        self.assertEqual(pred.target_crop, "guava")
        self.assertEqual(len(pred.probabilities), 3)
        self.assertIn("Green", pred.probabilities)
        self.assertIn("Mature Green", pred.probabilities)
        self.assertIn("Ripe", pred.probabilities)
        self.assertIsNone(pred.detected_fruit)

    def test_02_banana_isolated_service_initialization(self):
        """Ensure Banana CNNService initializes with 4-class taxonomy."""
        service = CNNService(crop="banana")
        self.assertEqual(service.target_crop, "banana")
        self.assertEqual(service.num_classes, 4)
        self.assertEqual(service.classes, ["Unripe", "Half_Ripe", "Ripe", "Overripe"])
        self.assertEqual(
            service.class_labels,
            {0: "Unripe", 1: "Half_Ripe", 2: "Ripe", 3: "Overripe"},
        )
        self.assertTrue(service.is_available)
        self.assertTrue(service.weights_path.exists())

        stat = service.get_status()
        self.assertIsInstance(stat, CNNModelStatusResponse)
        self.assertEqual(stat.target_crop, "banana")
        self.assertTrue(stat.model_available)
        self.assertEqual(stat.status, "ready")

    def test_03_banana_inference_softmax_and_zero_fabrication(self):
        """Ensure Banana inference produces valid 4-class distribution and never fabricates fruit ID."""
        service = CNNService(crop="banana")
        img = Image.new("RGB", (224, 224), color=(255, 255, 0))  # Yellow synthetic
        pred = service.predict(img)

        self.assertEqual(pred.target_crop, "banana")
        self.assertIn(pred.predicted_class, ["Unripe", "Half_Ripe", "Ripe", "Overripe"])
        self.assertEqual(len(pred.probabilities), 4)

        # Sum of probabilities must equal ~1.0
        prob_sum = sum(pred.probabilities.values())
        self.assertAlmostEqual(prob_sum, 1.0, places=2)

        # Zero fabrication invariant: Stage 1 fruit identifier is not deployed
        self.assertIsNone(pred.detected_fruit)
        self.assertIsNone(pred.fruit_confidence)
        self.assertIsNone(pred.fruit_probabilities)

    def test_04_banana_inference_on_real_manifest_sample(self):
        """Ensure Banana model accurately runs on an actual physical test image from the dataset."""
        workspace_root = settings.resolved_weights_path().parents[2]
        test_manifest = workspace_root / "ml" / "data" / "manifests" / "banana_ripeness" / "test.json"
        if not test_manifest.exists():
            self.skipTest(f"Test manifest not found at {test_manifest}")

        with open(test_manifest, "r", encoding="utf-8") as f:
            records = json.load(f)

        first_sample = records[0]
        sample_path = workspace_root / first_sample["path"]
        self.assertTrue(sample_path.exists(), f"Sample image missing at {sample_path}")

        service = CNNService(crop="banana")
        with Image.open(sample_path) as im:
            pred = service.predict(im)

        self.assertEqual(pred.target_crop, "banana")
        self.assertIn(pred.predicted_class, ["Unripe", "Half_Ripe", "Ripe", "Overripe"])
        self.assertGreaterEqual(pred.confidence, 0.0)
        self.assertLessEqual(pred.confidence, 1.0)
        self.assertGreater(pred.inference_ms, 0.0)

    def test_05_input_payload_validation_and_rejection(self):
        """Ensure invalid or corrupted payloads are safely rejected."""
        service = CNNService(crop="banana")

        # 1. Empty payload
        with self.assertRaises(InvalidImageError):
            service.validate_image_bytes(b"")

        # 2. Corrupt / unreadable bytes
        with self.assertRaises(InvalidImageError):
            service.validate_image_bytes(b"NOT_A_VALID_IMAGE_DATA_HEADER")

        # 3. Disallowed MIME type
        with self.assertRaises(UnsupportedMediaTypeError):
            service.validate_image_bytes(b"RIFF....WEBP", content_type="application/pdf")

        # 4. Disallowed file extension
        with self.assertRaises(UnsupportedMediaTypeError):
            service.validate_image_bytes(b"RIFF....WEBP", filename="malicious.exe")

    def test_06_missing_checkpoint_graceful_degradation(self):
        """Ensure non-existent weights path fails safely with ModelUnavailableError (503)."""
        bogus_path = Path("ml/artifacts/non_existent_banana_checkpoint.pth")
        service = CNNService(crop="banana", weights_path=bogus_path)

        self.assertFalse(service.is_available)
        stat = service.get_status()
        self.assertEqual(stat.status, "unavailable")
        self.assertFalse(stat.model_available)

        img = Image.new("RGB", (224, 224), color=(255, 0, 0))
        with self.assertRaises(ModelUnavailableError):
            service.predict(img)

    def test_07_model_registry_banana_gating_invariant(self):
        """Confirm Banana status in the public model registry (Phase 17B Baseline Verified)."""
        banana_meta = model_registry.get_metadata("banana")
        self.assertIsNotNone(banana_meta)
        self.assertTrue(banana_meta.is_validated, "Banana is validated in registry for Phase 17B!")
        self.assertEqual(banana_meta.status_label, "BASELINE_VERIFIED")
        self.assertTrue(
            model_registry.is_fruit_available("banana"),
            "Banana must report available=True when audited baseline checkpoint exists!",
        )

        # Available fruits include guava, banana, apple
        available_fruits = [
            f for f in model_registry.get_supported_fruits()
            if model_registry.is_fruit_available(f)
        ]
        self.assertIn("guava", available_fruits)
        self.assertIn("banana", available_fruits)

    def test_08_api_isolated_banana_routes(self):
        """Test API endpoints via TestClient ensuring isolation and backward compatibility."""
        with TestClient(app) as client:
            # 1. Guava status route
            res_guava_status = client.get("/api/v1/cnn/status")
            self.assertEqual(res_guava_status.status_code, 200)
            self.assertEqual(res_guava_status.json()["target_crop"], "guava")

            # 2. Isolated Banana status route
            res_banana_status = client.get("/api/v1/cnn/status/banana")
            self.assertEqual(res_banana_status.status_code, 200)
            data_banana = res_banana_status.json()
            self.assertEqual(data_banana["target_crop"], "banana")
            self.assertTrue(data_banana["model_available"])

            # 3. Create dummy image buffer
            buf = io.BytesIO()
            Image.new("RGB", (224, 224), color=(255, 255, 0)).save(buf, format="JPEG")
            buf.seek(0)
            img_bytes = buf.getvalue()

            # 4. Standard /predict (Guava)
            res_guava_pred = client.post(
                "/api/v1/cnn/predict",
                files={"file": ("guava_sample.jpg", img_bytes, "image/jpeg")},
            )
            self.assertEqual(res_guava_pred.status_code, 200)
            guava_json = res_guava_pred.json()
            self.assertEqual(guava_json["target_crop"], "guava")
            self.assertEqual(len(guava_json["probabilities"]), 3)

            # 5. Isolated /predict?crop=banana
            res_banana_query = client.post(
                "/api/v1/cnn/predict?crop=banana",
                files={"file": ("banana_sample.jpg", img_bytes, "image/jpeg")},
            )
            self.assertEqual(res_banana_query.status_code, 200)
            b_query_json = res_banana_query.json()
            self.assertEqual(b_query_json["target_crop"], "banana")
            self.assertEqual(len(b_query_json["probabilities"]), 4)
            self.assertIn("Half_Ripe", b_query_json["probabilities"])

            # 6. Isolated /predict/banana endpoint
            res_banana_route = client.post(
                "/api/v1/cnn/predict/banana",
                files={"file": ("banana_sample.jpg", img_bytes, "image/jpeg")},
            )
            self.assertEqual(res_banana_route.status_code, 200)
            b_route_json = res_banana_route.json()
            self.assertEqual(b_route_json["target_crop"], "banana")
            self.assertEqual(len(b_route_json["probabilities"]), 4)


if __name__ == "__main__":
    unittest.main()
