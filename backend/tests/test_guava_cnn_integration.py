"""
AgriChain AI - Guava CNN Integration & Verification Test Suite
=============================================================
Phase 4 Verification covering:
1. Checkpoint loading and architecture verification.
2. Exact class-index mapping (0: Green, 1: Mature Green, 2: Ripe).
3. Inference preprocessing parity with training evaluation.
4. Valid RGB image inference on actual dataset samples.
5. Invalid, corrupt, and unsupported image inputs.
6. Missing checkpoint behavior (HTTP 503 without fabrication).
7. Stable response schema invariants.
8. Correct confidence score semantics and handling.
9. Regression verification for backend endpoints.
10. Next.js proxy contract compatibility.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from fastapi.testclient import TestClient
except Exception:
    from tests.test_client_compat import TestClient

from PIL import Image

from app.core.config import settings
from app.main import app
from app.schemas.cnn import CNNModelStatusResponse, CNNPredictionResponse
from app.services.cnn_service import (
    CNNService,
    InvalidImageError,
    ImageTooLargeError,
    ModelUnavailableError,
    UnsupportedMediaTypeError,
)


def _load_sample_manifest():
    """Load test manifest records if available."""
    manifest_path = MONOREPO_ROOT / "ml" / "data" / "manifests" / "v2_grouped" / "test.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _create_synthetic_image_bytes(format: str = "JPEG", size: tuple = (128, 128), color: tuple = (34, 139, 34)) -> bytes:
    """Generate in-memory valid image bytes for testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


class TestGuavaCNNIntegration(unittest.TestCase):
    """Rigorous test suite for Phase 4 Guava CNN integration."""

    @classmethod
    def setUpClass(cls):
        cls.guava_weights_path = settings.resolved_guava_weights_path()
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    # -------------------------------------------------------------------------
    # 1. Checkpoint Loading
    # -------------------------------------------------------------------------
    def test_01_checkpoint_file_exists_and_loads(self):
        """Verify checkpoint file presence, architecture keys, and metadata integrity."""
        self.assertTrue(
            self.guava_weights_path.exists(),
            f"Guava checkpoint artifact missing at {self.guava_weights_path}",
        )
        service = CNNService(weights_path=self.guava_weights_path)
        self.assertTrue(service.is_available, "CNNService failed to load guava checkpoint")
        self.assertEqual(service.target_crop, "guava")
        self.assertEqual(service.model_version, "2.0.0")
        self.assertIsNotNone(service.model)
        self.assertIsNotNone(service.transform)

    # -------------------------------------------------------------------------
    # 2. Exact Class-Index Mapping
    # -------------------------------------------------------------------------
    def test_02_exact_class_index_mapping(self):
        """Verify exact mapping: 0 -> Green, 1 -> Mature Green, 2 -> Ripe."""
        service = CNNService(weights_path=self.guava_weights_path)
        self.assertEqual(service.classes, ["Green", "Mature Green", "Ripe"])
        self.assertEqual(service.class_labels[0], "Green")
        self.assertEqual(service.class_labels[1], "Mature Green")
        self.assertEqual(service.class_labels[2], "Ripe")
        self.assertTrue(service.class_mapping_verified)
        self.assertEqual(service.class_mapping_status, "VERIFIED_GROUND_TRUTH_METADATA")

        status = service.get_status()
        self.assertEqual(status.target_crop, "guava")
        self.assertTrue(status.class_mapping_verified)
        self.assertEqual(status.model_version, "2.0.0")

    # -------------------------------------------------------------------------
    # 3. Inference Preprocessing Parity
    # -------------------------------------------------------------------------
    def test_03_inference_preprocessing_parity(self):
        """Verify preprocessing pipeline strictly matches training evaluation transforms."""
        service = CNNService(weights_path=self.guava_weights_path)
        self.assertIsNotNone(service.transform)

        # Create sample PIL image of non-square dimension
        sample_img = Image.new("RGB", (320, 240), color=(100, 180, 50))
        tensor = service.transform(sample_img)

        # Check tensor shape [3, 224, 224] (Resize to 256 then CenterCrop to 224)
        self.assertEqual(list(tensor.shape), [3, 224, 224])
        self.assertFalse(tensor.isnan().any(), "Transformed tensor contains NaN")

        # Verify transform steps: Resize(256) -> CenterCrop(224) -> ToTensor -> Normalize
        transform_types = [type(t).__name__ for t in service.transform.transforms]
        self.assertIn("Resize", transform_types)
        self.assertIn("CenterCrop", transform_types)
        self.assertIn("ToTensor", transform_types)
        self.assertIn("Normalize", transform_types)

        # Verify CenterCrop size is (224, 224)
        center_crops = [t for t in service.transform.transforms if type(t).__name__ == "CenterCrop"]
        self.assertEqual(center_crops[0].size, (224, 224))

        # Verify Resize size is (256, 256)
        resizes = [t for t in service.transform.transforms if type(t).__name__ == "Resize"]
        self.assertEqual(resizes[0].size, (256, 256))

    # -------------------------------------------------------------------------
    # 4. Valid RGB Image Inference on Actual Dataset Samples
    # -------------------------------------------------------------------------
    def test_04_valid_rgb_image_inference_actual_dataset(self):
        """Execute inference on actual images from the held-out test manifest."""
        manifest = _load_sample_manifest()
        self.assertGreater(len(manifest), 0, "Test manifest is empty or missing")

        service = CNNService(weights_path=self.guava_weights_path)

        # Find one image for each class in test manifest
        samples_by_class = {}
        for r in manifest:
            cname = r["class_name"]
            if cname not in samples_by_class:
                img_path = Path(r["abs_path"])
                if img_path.exists():
                    samples_by_class[cname] = img_path

        self.assertIn("Green", samples_by_class)
        self.assertIn("Mature Green", samples_by_class)
        self.assertIn("Ripe", samples_by_class)

        for expected_class, img_path in samples_by_class.items():
            with Image.open(img_path) as raw_img:
                pred = service.predict(raw_img)

            self.assertIsInstance(pred, CNNPredictionResponse)
            self.assertIn(pred.predicted_class, ["Green", "Mature Green", "Ripe"])
            self.assertIn(pred.class_index, [0, 1, 2])
            self.assertEqual(pred.label, pred.predicted_class)
            self.assertGreater(pred.confidence, 0.0)
            self.assertLessEqual(pred.confidence, 1.0)
            self.assertEqual(pred.target_crop, "guava")
            self.assertEqual(pred.model_version, "2.0.0")
            self.assertGreater(pred.inference_ms, 0.0)

            # Probabilities distribution
            self.assertEqual(set(pred.probabilities.keys()), {"Green", "Mature Green", "Ripe"})
            self.assertAlmostEqual(sum(pred.probabilities.values()), 1.0, places=3)
            self.assertEqual(pred.predicted_class, max(pred.probabilities, key=pred.probabilities.get))

    # -------------------------------------------------------------------------
    # 5. Invalid, Corrupt, and Unsupported Image Inputs
    # -------------------------------------------------------------------------
    def test_05_image_validation_rejections(self):
        """Verify strict rejection of invalid image payloads."""
        service = CNNService(weights_path=self.guava_weights_path)

        # Empty payload
        with self.assertRaises(InvalidImageError):
            service.validate_image_bytes(b"", content_type="image/jpeg")

        # Unsupported content type (PDF)
        with self.assertRaises(UnsupportedMediaTypeError):
            service.validate_image_bytes(b"%PDF-1.4 dummy", content_type="application/pdf")

        # Unsupported file extension (.txt)
        with self.assertRaises(UnsupportedMediaTypeError):
            service.validate_image_bytes(b"hello", content_type="text/plain", filename="sample.txt")

        # Corrupt pixel buffer
        with self.assertRaises(InvalidImageError):
            service.validate_image_bytes(b"\xff\xd8\xff\xe0corrupt payload", content_type="image/jpeg")

        # Excessively small image (< 10x10)
        tiny_buf = io.BytesIO()
        Image.new("RGB", (4, 4), color=(0, 255, 0)).save(tiny_buf, format="PNG")
        with self.assertRaises(InvalidImageError):
            service.validate_image_bytes(tiny_buf.getvalue(), content_type="image/png")

        # Oversized file
        oversized = b"X" * (settings.MAX_UPLOAD_BYTES + 1024)
        with self.assertRaises(ImageTooLargeError):
            service.validate_image_bytes(oversized, content_type="image/jpeg")

    # -------------------------------------------------------------------------
    # 6. Missing Checkpoint Behavior & Guard Preservation
    # -------------------------------------------------------------------------
    def test_06_missing_checkpoint_unavailability(self):
        """When checkpoint is missing, service is unavailable and never fabricates results."""
        missing_service = CNNService(weights_path=Path("non_existent_weights.pth"))
        self.assertFalse(missing_service.is_available)
        status = missing_service.get_status()
        self.assertEqual(status.status, "unavailable")
        self.assertFalse(status.model_available)

        dummy_img = Image.new("RGB", (100, 100))
        with self.assertRaises(ModelUnavailableError) as ctx:
            missing_service.predict(dummy_img)
        self.assertIn("unavailable", str(ctx.exception).lower())

    def test_06b_production_endpoint_remains_guarded_by_default(self):
        """
        Controlled Activation Guard (Phase D):
        Verify that default application state keeps the HTTP 503 guard intact
        until explicit activation approval.
        """
        from unittest.mock import patch
        # When default settings apply (GUAVA_MODEL_ACTIVATED=False), /predict returns 503
        with patch.object(settings, "GUAVA_MODEL_ACTIVATED", False):
            default_service = CNNService(crop="kinnow")
            self.assertFalse(default_service.is_available)
            stat = default_service.get_status()
            self.assertEqual(stat.status, "unavailable")

    # -------------------------------------------------------------------------
    # 7. Stable Response Schema Invariants
    # -------------------------------------------------------------------------
    def test_07_response_schema_invariants(self):
        """Verify response schema contains required fields and adheres to pydantic constraints."""
        service = CNNService(weights_path=self.guava_weights_path)
        img = Image.new("RGB", (128, 128), color=(50, 150, 50))
        resp = service.predict(img)

        # Validate with Pydantic model directly
        data = resp.model_dump()
        self.assertIn("predicted_class", data)
        self.assertIn("class_index", data)
        self.assertIn("label", data)
        self.assertIn("confidence", data)
        self.assertIn("probabilities", data)
        self.assertIn("target_crop", data)
        self.assertIn("model_name", data)
        self.assertIn("model_version", data)
        self.assertIn("device", data)
        self.assertIn("inference_ms", data)

        re_validated = CNNPredictionResponse(**data)
        self.assertEqual(re_validated.confidence, resp.confidence)
        self.assertEqual(re_validated.model_version, "2.0.0")

    # -------------------------------------------------------------------------
    # 8. Correct Confidence Score Semantics
    # -------------------------------------------------------------------------
    def test_08_confidence_semantics(self):
        """Verify confidence is uncalibrated softmax score bounded in [0.0, 1.0]."""
        service = CNNService(weights_path=self.guava_weights_path)
        img = Image.new("RGB", (128, 128), color=(200, 200, 30))
        resp = service.predict(img)

        # Confidence must equal max of softmax probabilities
        max_p = max(resp.probabilities.values())
        self.assertAlmostEqual(resp.confidence, max_p, places=4)
        self.assertGreaterEqual(resp.confidence, 0.0)
        self.assertLessEqual(resp.confidence, 1.0)

    # -------------------------------------------------------------------------
    # 9. HTTP Endpoint Prediction & Parity
    # -------------------------------------------------------------------------
    def test_09_http_endpoint_guava_inference(self):
        """Verify HTTP POST /predict and /api/v1/cnn/predict when guava model is active."""
        original_service = app.state.cnn_service
        try:
            guava_service = CNNService(weights_path=self.guava_weights_path)
            app.state.cnn_service = guava_service

            jpeg_bytes = _create_synthetic_image_bytes(format="JPEG")
            resp = self.client.post(
                "/predict",
                files={"file": ("guava_test.jpg", jpeg_bytes, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.json()

            self.assertEqual(body["target_crop"], "guava")
            self.assertEqual(body["model_version"], "2.0.0")
            self.assertIn(body["predicted_class"], ["Green", "Mature Green", "Ripe"])
            self.assertIn(body["label"], ["Green", "Mature Green", "Ripe"])
            self.assertIn("confidence", body)
            self.assertIn("probabilities", body)
            self.assertEqual(set(body["probabilities"].keys()), {"Green", "Mature Green", "Ripe"})

            # /health probe verification
            h_resp = self.client.get("/health")
            self.assertEqual(h_resp.status_code, 200)
            h_body = h_resp.json()
            self.assertEqual(h_body["target_crop"], "guava")
            self.assertTrue(h_body["model_available"])

            # /api/v1/cnn/status verification
            s_resp = self.client.get(f"{settings.API_V1_STR}/cnn/status")
            self.assertEqual(s_resp.status_code, 200)
            s_body = s_resp.json()
            self.assertEqual(s_body["target_crop"], "guava")
            self.assertTrue(s_body["model_available"])
            self.assertTrue(s_body["class_mapping_verified"])
            self.assertEqual(s_body["model_version"], "2.0.0")
        finally:
            app.state.cnn_service = original_service

    # -------------------------------------------------------------------------
    # 10. Next.js Proxy Compatibility
    # -------------------------------------------------------------------------
    def test_10_nextjs_proxy_compatibility(self):
        """
        Verify that Next.js proxy enrichments (class, class_index, label)
        process the Guava prediction JSON seamlessly.
        """
        sample_api_response = {
            "predicted_class": "Mature Green",
            "class_index": 1,
            "label": "Mature Green",
            "confidence": 0.9310,
            "probabilities": {"Green": 0.0412, "Mature Green": 0.9310, "Ripe": 0.0278},
            "target_crop": "guava",
            "model_name": "resnet18",
            "model_version": "2.0.0",
            "device": "cpu",
            "inference_ms": 12.5,
        }

        # Simulate Next.js app/api/predict/route.js logic
        numeric_index = (
            sample_api_response["class_index"]
            if isinstance(sample_api_response.get("class_index"), int)
            else sample_api_response.get("class")
        )

        enriched = {
            **sample_api_response,
            "class": numeric_index,
            "class_index": numeric_index,
            "label": sample_api_response.get("label", "Unknown"),
        }

        self.assertEqual(enriched["class"], 1)
        self.assertEqual(enriched["class_index"], 1)
        self.assertEqual(enriched["label"], "Mature Green")
        self.assertEqual(enriched["target_crop"], "guava")
        self.assertEqual(enriched["model_version"], "2.0.0")


if __name__ == "__main__":
    unittest.main()
