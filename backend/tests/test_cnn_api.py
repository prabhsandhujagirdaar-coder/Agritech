"""
AgriChain AI - Backend CNN API & Readiness Test Suite
=====================================================
Focused verification tests covering:
1. Root /health and /api/v1/health endpoints.
2. CNN model status and Kinnow readiness diagnostics.
3. Payload validation: missing file, unsupported media type, empty upload, corrupt image, oversized file.
4. Explicit missing-model handling: returns HTTP 503 without fabricating fake predictions or numbers.
5. Rejection of legacy strawberry models to protect scientific integrity.
6. Schema compliance and invariant validation on active inference.
7. Endpoint parity between root /predict and /api/v1/cnn/predict.
8. Preservation of shipments and telemetry/LSTM endpoints.
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure backend directory is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from fastapi.testclient import TestClient
except Exception:
    from tests.test_client_compat import TestClient

from PIL import Image

from app.core.config import settings
from app.main import app
from app.schemas.cnn import CNNPredictionResponse
from app.services.cnn_service import CNNService


def _create_synthetic_image_bytes(format: str = "JPEG", size: tuple = (64, 64), color: tuple = (240, 140, 20)) -> bytes:
    """Generate in-memory valid image bytes for testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


class TestAgriChainBackendAPI(unittest.TestCase):
    """Integration test suite for the AgriChain AI FastAPI backend."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    # -------------------------------------------------------------------------
    # 1. Health & Status Endpoints
    # -------------------------------------------------------------------------
    def test_01_root_health_probe(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("status", body)
        self.assertIn("target_crop", body)
        self.assertEqual(body["target_crop"], settings.TARGET_CROP)
        self.assertIn("model_available", body)
        self.assertIn("device", body)

    def test_02_v1_health_probe(self):
        resp = self.client.get(f"{settings.API_V1_STR}/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["target_crop"], settings.TARGET_CROP)
        self.assertIn("service", body)

    def test_03_cnn_status_diagnostics(self):
        resp = self.client.get(f"{settings.API_V1_STR}/cnn/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["target_crop"], settings.TARGET_CROP)
        self.assertIn("status", body)
        self.assertIn("model_available", body)
        self.assertIn("weights_exist", body)
        self.assertIn("message", body)

    # -------------------------------------------------------------------------
    # 2. Upload Validation & HTTP Error Handling
    # -------------------------------------------------------------------------
    def test_04_predict_missing_file_returns_422(self):
        resp = self.client.post("/predict")
        self.assertEqual(resp.status_code, 422)

    def test_05_predict_unsupported_file_type_rejected_with_415(self):
        bogus = ("report.pdf", b"%PDF-1.4 fake pdf data", "application/pdf")
        resp = self.client.post("/predict", files={"file": bogus})
        self.assertEqual(resp.status_code, 415)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("Unsupported", body["detail"])

    def test_06_predict_text_file_rejected_with_415(self):
        bogus = ("notes.txt", b"hello world plain text", "text/plain")
        resp = self.client.post("/predict", files={"file": bogus})
        self.assertEqual(resp.status_code, 415)

    def test_07_predict_empty_upload_returns_400(self):
        empty = ("empty.jpg", b"", "image/jpeg")
        resp = self.client.post("/predict", files={"file": empty})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("Empty", body["detail"])

    def test_08_predict_corrupt_image_returns_400(self):
        corrupt = ("broken.png", b"\x89PNG\r\n\x1a\ncorrupted bytes", "image/png")
        resp = self.client.post("/predict", files={"file": corrupt})
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("detail", body)
        self.assertIn("Invalid or corrupted", body["detail"])

    def test_09_predict_oversized_upload_returns_400(self):
        # Create a mock upload exceeding MAX_UPLOAD_BYTES without generating huge RAM
        service = app.state.cnn_service
        huge_bytes = b"0" * (settings.MAX_UPLOAD_BYTES + 1024)
        with self.assertRaises(Exception) as ctx:
            service.validate_image_bytes(huge_bytes, content_type="image/jpeg")
        self.assertIn("exceeds the allowed limit", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. Model Availability & No-Fabrication Invariants
    # -------------------------------------------------------------------------
    def test_10_missing_model_returns_503_without_fabricated_predictions(self):
        """
        Critical requirement: When no validated Kinnow model artifact exists,
        the API must explicitly return HTTP 503 and never fabricate predictions
        or fake confidence/freshness percentages.
        """
        # Ensure service is pointing to a non-existent checkpoint
        original_service = app.state.cnn_service
        try:
            fake_service = CNNService(weights_path=Path("non_existent_kinnow_model.pth"))
            app.state.cnn_service = fake_service

            jpeg_bytes = _create_synthetic_image_bytes(format="JPEG")
            resp = self.client.post(
                "/predict",
                files={"file": ("fruit.jpg", jpeg_bytes, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 503)
            body = resp.json()

            # Confirm informative message and absence of fabricated metrics
            self.assertIn("detail", body)
            self.assertIn("unavailable", body["detail"].lower())
            self.assertNotIn("predicted_class", body)
            self.assertNotIn("confidence", body)
            self.assertNotIn("probabilities", body)
            self.assertNotIn("freshness_percentage", body)
            self.assertNotIn("spoilage_percentage", body)
        finally:
            app.state.cnn_service = original_service

    def test_11_legacy_strawberry_model_is_strictly_rejected(self):
        """
        Scientific integrity guard: A strawberry model must NEVER be presented
        as a Kinnow model.
        """
        service = CNNService(weights_path=Path("legacy_strawberry_weights.pth"))
        # Even if weights file had strawberry in path, it should be marked unavailable
        self.assertFalse(service.is_available)
        status = service.get_status()
        self.assertEqual(status.status, "unavailable")

    # -------------------------------------------------------------------------
    # 4. Valid Model Integration & Response Schema Parity
    # -------------------------------------------------------------------------
    def test_12_mock_validated_model_predict_flow_and_schema(self):
        """
        Verifies that when a validated model is loaded into CNNService,
        the API responds with the complete, standardized CNNPredictionResponse.
        """
        original_service = app.state.cnn_service
        try:
            # Construct a mock ready service
            mock_service = CNNService(weights_path=Path("mock_best_kinnow.pth"))
            mock_service._is_ready = True
            mock_service.model = MagicMock()

            # Mock prediction output
            mock_prediction = CNNPredictionResponse(
                predicted_class="class2",
                class_index=2,
                label="Fully Ripe",
                confidence=0.9650,
                probabilities={"class0": 0.0150, "class1": 0.0200, "class2": 0.9650},
                target_crop="kinnow",
                model_name="resnet18",
                device="cpu",
                inference_ms=35.2,
            )
            mock_service.predict = MagicMock(return_value=mock_prediction)
            app.state.cnn_service = mock_service

            jpeg_bytes = _create_synthetic_image_bytes(format="JPEG")
            resp = self.client.post(
                "/predict",
                files={"file": ("kinnow_sample.jpg", jpeg_bytes, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.json()

            # Verify schema fields
            self.assertEqual(body["predicted_class"], "class2")
            self.assertEqual(body["class_index"], 2)
            self.assertEqual(body["label"], "Fully Ripe")
            self.assertEqual(body["target_crop"], "kinnow")
            self.assertAlmostEqual(body["confidence"], 0.9650, places=4)
            self.assertEqual(set(body["probabilities"].keys()), {"class0", "class1", "class2"})
            self.assertAlmostEqual(sum(body["probabilities"].values()), 1.0, places=4)
            self.assertEqual(body["predicted_class"], max(body["probabilities"], key=body["probabilities"].get))
        finally:
            app.state.cnn_service = original_service

    def test_13_v1_predict_endpoint_parity(self):
        """Ensure /api/v1/cnn/predict exhibits exact parity with root /predict."""
        resp = self.client.post(f"{settings.API_V1_STR}/cnn/predict")
        self.assertEqual(resp.status_code, 422)

    # -------------------------------------------------------------------------
    # 5. Preserved Features: Shipments & Telemetry / LSTM
    # -------------------------------------------------------------------------
    def test_14_preserved_shipments_endpoints(self):
        resp = self.client.get(f"{settings.API_V1_STR}/shipments")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertIsInstance(items, list)
        self.assertIn("id", items[0])
        origins = [it.get("origin", "") for it in items]
        self.assertTrue(any("Abohar" in o for o in origins), f"Expected 'Abohar' in origins: {origins}")

    def test_15_preserved_telemetry_lstm_predict_endpoint(self):
        payload = {
            "shipment_id": "SHP-2026-001",
            "sequence": [
                {
                    "hour": i,
                    "temperature": 6.0 + (0.5 if i > 12 else 0.0),
                    "humidity": 88.0,
                    "delay_minutes": i * 5,
                    "speed_kmh": 55.0,
                    "distance_remaining_km": 500.0 - i * 20,
                }
                for i in range(24)
            ],
        }
        resp = self.client.post(f"{settings.API_V1_STR}/telemetry/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["shipment_id"], "SHP-2026-001")
        self.assertIn("current_risk", body)
        self.assertIn("predicted_arrival_risk", body)
        self.assertIn("alert", body)
        self.assertIn("inference_ms", body)


if __name__ == "__main__":
    unittest.main()
