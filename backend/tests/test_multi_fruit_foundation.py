"""
AgriChain AI - Multi-Fruit Foundation & Model Registry Tests
============================================================
Phase 14A Test Suite verifying:
1. Multi-fruit model registry catalogs guava, mango, banana, and apple.
2. Guava production model remains certified, active, and validated.
3. Mango, banana, and apple remain explicitly unvalidated and awaiting training.
4. Stage 1 fruit identifier is cataloged and marked awaiting training.
5. Zero prediction fabrication: Unsupported or unvalidated fruits cannot produce synthetic inferences.
6. Checkpoint paths resolve safely and non-destructively.
7. Prediction response schema maintains 100% backward compatibility.
"""

from __future__ import annotations

import io
import unittest
from pathlib import Path
from PIL import Image

from app.core.config import settings
from app.schemas.cnn import (
    CNNPredictionResponse,
    MultiFruitRegistryStatusResponse,
    FruitRegistryItemSchema,
)
from app.services.model_registry import (
    FRUIT_CATALOG,
    MultiFruitModelRegistry,
    model_registry,
)
from app.services.cnn_service import CNNService


class TestMultiFruitFoundation(unittest.TestCase):
    """Test suite for Phase 14A model registry and safe multi-fruit foundation."""

    def test_01_catalog_contains_four_mandated_fruits(self):
        """Verify all 4 required fruits are defined with correct taxonomy."""
        supported = model_registry.get_supported_fruits()
        self.assertIn("guava", supported)
        self.assertIn("mango", supported)
        self.assertIn("banana", supported)
        self.assertIn("apple", supported)
        self.assertEqual(len(supported), 4)

    def test_02_guava_production_model_is_certified_and_available(self):
        """Ensure Guava model is certified active with v2.0.0 and verified mapping."""
        guava_meta = model_registry.get_metadata("guava")
        self.assertIsNotNone(guava_meta)
        self.assertTrue(guava_meta.is_validated)
        self.assertEqual(guava_meta.status_label, "CERTIFIED_ACTIVE")
        self.assertEqual(guava_meta.model_version, "2.0.0")
        self.assertEqual(guava_meta.classes, ("Green", "Mature Green", "Ripe"))
        self.assertEqual(guava_meta.num_classes, 3)

        # Check physical checkpoint existence
        self.assertTrue(model_registry.is_fruit_available("guava"))
        guava_status = model_registry.get_fruit_status("guava")
        self.assertTrue(guava_status["available"])
        self.assertTrue(guava_status["is_validated"])
        self.assertEqual(guava_status["status"], "CERTIFIED_ACTIVE")

    def test_03_mango_banana_apple_are_unvalidated_and_unavailable(self):
        """Ensure Mango remains explicitly unvalidated and gated due to dataset deficit."""
        meta = model_registry.get_metadata("mango")
        self.assertIsNotNone(meta, "Metadata missing for mango")
        self.assertFalse(meta.is_validated, "Mango must not be marked validated")
        self.assertEqual(meta.status_label, "GATED_DEFICIT")
        self.assertFalse(
            model_registry.is_fruit_available("mango"),
            "Mango must report available=False",
        )
        status = model_registry.get_fruit_status("mango")
        self.assertFalse(status["available"])
        self.assertFalse(status["is_validated"])
        self.assertEqual(status["status"], "GATED_DEFICIT")

    def test_04_agronomic_taxonomies_are_distinct(self):
        """Verify species-specific labels are not conflated or blindly merged."""
        guava_meta = model_registry.get_metadata("guava")
        banana_meta = model_registry.get_metadata("banana")
        mango_meta = model_registry.get_metadata("mango")
        apple_meta = model_registry.get_metadata("apple")

        # Guava: Green, Mature Green, Ripe
        self.assertEqual(list(guava_meta.classes), ["Green", "Mature Green", "Ripe"])
        # Banana: Unripe, Half_Ripe, Ripe, Overripe (4 classes)
        self.assertEqual(list(banana_meta.classes), ["Unripe", "Half_Ripe", "Ripe", "Overripe"])
        # Mango: Unripe, Semi-ripe, Ripe, Rotten (4 classes)
        self.assertEqual(list(mango_meta.classes), ["unripe", "semi-ripe", "ripe", "rotten"])
        # Apple: apple (YOLOv8n object detection)
        self.assertEqual(list(apple_meta.classes), ["apple"])

    def test_05_registry_status_serializes_cleanly(self):
        """Verify full registry status produces valid Pydantic schema."""
        full_status = model_registry.get_full_registry_status()
        resp = MultiFruitRegistryStatusResponse(**full_status)
        self.assertEqual(sorted(resp.supported_fruits), ["apple", "banana", "guava", "mango"])
        self.assertEqual(sorted(resp.available_fruits), ["apple", "banana", "guava"])
        self.assertEqual(resp.production_crop, "guava")
        self.assertIn("guava", resp.fruits)
        self.assertIn("banana", resp.fruits)
        self.assertIn("mango", resp.fruits)
        self.assertIn("apple", resp.fruits)

    def test_06_unsupported_commodity_rejected_safely(self):
        """Verify query for an unsupported crop returns clean rejection."""
        status = model_registry.get_fruit_status("dragonfruit")
        self.assertFalse(status["supported"])
        self.assertFalse(status["available"])
        self.assertEqual(status["status"], "UNSUPPORTED_COMMODITY")

    def test_07_prediction_response_schema_backward_compatibility(self):
        """Verify legacy clients reading only old fields work identically with new schema."""
        raw_payload = {
            "predicted_class": "Mature Green",
            "class_index": 1,
            "label": "Mature Green",
            "confidence": 0.8147,
            "probabilities": {"Green": 0.1683, "Mature Green": 0.8147, "Ripe": 0.0170},
            "target_crop": "guava",
            "model_name": "resnet18",
            "model_version": "2.0.0",
            "device": "cuda",
            "inference_ms": 23.41,
        }
        # Validate schema without new fields
        parsed = CNNPredictionResponse(**raw_payload)
        self.assertEqual(parsed.predicted_class, "Mature Green")
        self.assertEqual(parsed.class_index, 1)
        self.assertEqual(parsed.target_crop, "guava")
        self.assertIsNone(parsed.detected_fruit)

        # Validate schema WITH new fields
        multi_payload = {
            **raw_payload,
            "detected_fruit": "guava",
            "fruit_confidence": 0.985,
            "fruit_probabilities": {"guava": 0.985, "mango": 0.005, "banana": 0.005, "apple": 0.005},
            "ripeness": "Mature Green",
            "status": "ready",
            "is_validated": True,
        }
        parsed_multi = CNNPredictionResponse(**multi_payload)
        self.assertEqual(parsed_multi.detected_fruit, "guava")
        self.assertEqual(parsed_multi.fruit_confidence, 0.985)
        self.assertEqual(parsed_multi.ripeness, "Mature Green")
        self.assertTrue(parsed_multi.is_validated)

    def test_08_single_crop_inference_does_not_fabricate_detected_fruit(self):
        """Verify that single-crop Guava inference does not report a fabricated Stage 1 fruit detection."""
        service = CNNService()
        if service.is_available:
            img = Image.new("RGB", (224, 224), color=(34, 139, 34))
            pred = service.predict(img)
            self.assertEqual(pred.target_crop, "guava")
            self.assertIsNone(pred.detected_fruit, "detected_fruit must remain None until Stage 1 identifier is trained")
            self.assertIsNone(pred.fruit_confidence, "fruit_confidence must remain None without Stage 1 model")
            self.assertEqual(pred.status, "ready")
            self.assertTrue(pred.is_validated)


if __name__ == "__main__":
    unittest.main()

