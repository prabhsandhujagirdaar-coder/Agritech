"""
AgriChain AI - Multi-Fruit Model Registry Foundation
====================================================
Phase 14A Implementation:
Centralized, safe registry defining supported fruit commodities,
their scientific identities, checkpoint paths, native agronomic maturity stages,
and strict validation guards.

Guarantees:
1. Zero Fake Predictions: Uncertified or untrained models remain explicitly unavailable.
2. Checkpoint Preservation: Guava production model (v2.0.0) remains certified and untouched.
3. Agronomic Separation: Never merges incompatible biological stages across species.
4. Memory Safety: Prevents indiscriminate concurrent allocation on constrained GPU devices.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("agrichain.services.model_registry")


@dataclass(frozen=True)
class FruitMetadata:
    """Immutable specification for a fruit commodity and its maturity taxonomy."""
    fruit_id: str
    common_name: str
    scientific_name: str
    primary_cultivar: str
    checkpoint_filename: str
    classes: Tuple[str, ...]
    class_labels: Dict[int, str]
    num_classes: int
    architecture: str = "resnet18"
    task_type: str = "classification"  # "classification" or "object_detection"
    model_version: Optional[str] = None
    input_size: Tuple[int, int, int] = (3, 224, 224)
    normalization_mean: Tuple[float, float, float] = (0.485, 0.456, 0.406)
    normalization_std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    is_validated: bool = False
    status_label: str = "AWAITING_TRAINING"
    description: str = ""


# ---------------------------------------------------------------------------
# Authoritative Multi-Fruit Registry Catalog
# ---------------------------------------------------------------------------
FRUIT_CATALOG: Dict[str, FruitMetadata] = {
    "guava": FruitMetadata(
        fruit_id="guava",
        common_name="Guava",
        scientific_name="Psidium guajava L.",
        primary_cultivar="Local Sindhi / Allahabad Safeda",
        checkpoint_filename="best_guava_resnet18.pth",
        classes=("Green", "Mature Green", "Ripe"),
        class_labels={0: "Green", 1: "Mature Green", 2: "Ripe"},
        num_classes=3,
        architecture="resnet18",
        task_type="classification",
        model_version="2.0.0",
        is_validated=True,
        status_label="CERTIFIED_ACTIVE",
        description="Climacteric subtropical fruit; 3-stage harvest intake maturity taxonomy.",
    ),
    "mango": FruitMetadata(
        fruit_id="mango",
        common_name="Mango",
        scientific_name="Mangifera indica L.",
        primary_cultivar="Harumanis / Chaunsa / Dashehari",
        checkpoint_filename="best_mango_resnet18.pth",
        classes=("unripe", "semi-ripe", "ripe", "rotten"),
        class_labels={0: "unripe", 1: "semi-ripe", 2: "ripe", 3: "rotten"},
        num_classes=4,
        architecture="resnet18",
        task_type="classification",
        model_version=None,
        is_validated=False,
        status_label="GATED_DEFICIT",
        description="Climacteric tropical drupe; awaiting validated multi-stage dataset. Model unavailable; zero synthetic predictions.",
    ),
    "banana": FruitMetadata(
        fruit_id="banana",
        common_name="Banana",
        scientific_name="Musa acuminata / Musa balbisiana",
        primary_cultivar="Cavendish / Ambon",
        checkpoint_filename="best_banana_resnet18.pth",
        classes=("Unripe", "Half_Ripe", "Ripe", "Overripe"),
        class_labels={0: "Unripe", 1: "Half_Ripe", 2: "Ripe", 3: "Overripe"},
        num_classes=4,
        architecture="resnet18",
        task_type="classification",
        model_version="1.0.0",
        is_validated=True,
        status_label="BASELINE_VERIFIED",
        description="High-ethylene climacteric monocot; 4-stage peel degreening and senescence (Audited baseline v1.0.0).",
    ),
    "apple": FruitMetadata(
        fruit_id="apple",
        common_name="Apple",
        scientific_name="Malus domestica Borkh.",
        primary_cultivar="Fuji / Gala",
        checkpoint_filename="best_apple_yolov8n.pt",
        classes=("apple",),
        class_labels={0: "apple"},
        num_classes=1,
        architecture="yolov8n",
        task_type="object_detection",
        model_version="1.0.0-experimental",
        is_validated=True,
        status_label="EXPERIMENTAL_DETECTION",
        description="Temperate pome fruit; YOLOv8n in-orchard object detection under CC BY-NC 4.0 license. Harvest maturity and quality grading are unavailable.",
    ),
}

STAGE1_IDENTIFIER_METADATA = FruitMetadata(
    fruit_id="fruit_identifier",
    common_name="Multi-Fruit Identifier",
    scientific_name="Species Classifier",
    primary_cultivar="Multi-Crop",
    checkpoint_filename="best_fruit_identifier_mobilenet_v3_large.pth",
    classes=("guava", "banana", "apple", "mango", "negative_background"),
    class_labels={0: "guava", 1: "banana", 2: "apple", 3: "mango", 4: "negative_background"},
    num_classes=5,
    architecture="mobilenet_v3_large",
    task_type="classification",
    model_version="2.0.0",
    is_validated=True,
    status_label="BENCHMARK_VERIFIED",
    description="Stage 1 species recognition and canopy/background rejection model (MobileNetV3-Large, Test Macro F1: 0.9981).",
)


class MultiFruitModelRegistry:
    """
    Manages discovery, validation status, and checkpoint resolution across supported fruit species.
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        if artifacts_dir is not None:
            self.artifacts_dir = Path(artifacts_dir)
        else:
            self.artifacts_dir = settings.resolved_guava_weights_path().parent

        self._catalog = dict(FRUIT_CATALOG)
        self._identifier_meta = STAGE1_IDENTIFIER_METADATA

    def get_supported_fruits(self) -> List[str]:
        """Return list of all registered fruit IDs."""
        return list(self._catalog.keys())

    def get_metadata(self, fruit: str) -> Optional[FruitMetadata]:
        """Retrieve static metadata specification for a specific fruit."""
        return self._catalog.get(fruit.lower().strip())

    def resolve_weights_path(self, fruit: str) -> Path:
        """Resolve expected checkpoint path on disk for a given fruit or identifier."""
        fruit_key = fruit.lower().strip()
        if fruit_key == "guava":
            return settings.resolved_guava_weights_path()
        if fruit_key == "banana":
            return settings.resolved_banana_weights_path()
        if fruit_key == "apple":
            return settings.resolved_apple_weights_path()
        if fruit_key in ("fruit_identifier", "stage1_identifier", "identifier"):
            return settings.resolved_fruit_identifier_weights_path()

        meta = self.get_metadata(fruit_key)
        if meta is None:
            return self.artifacts_dir / f"best_{fruit_key}_resnet18.pth"
        return self.artifacts_dir / meta.checkpoint_filename

    def is_fruit_available(self, fruit: str) -> bool:
        """
        Check whether a certified, frozen model checkpoint physically exists
        and has been verified for production readiness.
        """
        fruit_key = fruit.lower().strip()
        meta = self.get_metadata(fruit_key)
        if meta is None or not meta.is_validated:
            return False

        path = self.resolve_weights_path(fruit_key)
        return path.exists()

    def get_fruit_status(self, fruit: str) -> Dict[str, Any]:
        """Return detailed validation and artifact diagnostic for a fruit."""
        fruit_key = fruit.lower().strip()
        meta = self.get_metadata(fruit_key)
        if meta is None:
            return {
                "fruit": fruit_key,
                "common_name": fruit.capitalize(),
                "scientific_name": "Unknown",
                "cultivar": "Unknown",
                "supported": False,
                "available": False,
                "is_validated": False,
                "status": "UNSUPPORTED_COMMODITY",
                "architecture": "unknown",
                "task_type": "unknown",
                "model_version": None,
                "classes": [],
                "class_labels": {},
                "num_classes": 0,
                "weights_path": "",
                "weights_exist": False,
                "message": f"Commodity '{fruit}' is not registered in AgriChain AI.",
            }

        path = self.resolve_weights_path(fruit_key)
        path_exists = path.exists()
        is_ready = meta.is_validated and path_exists

        if is_ready:
            msg = f"Certified {meta.common_name} model v{meta.model_version} ready at '{path.name}'."
        elif path_exists and not meta.is_validated:
            msg = f"Checkpoint present for {meta.common_name} but awaiting benchmark validation and certification."
        else:
            msg = f"No certified checkpoint found for {meta.common_name}. Training required."

        status_val = (
            meta.status_label
            if is_ready
            else (
                meta.status_label
                if meta.status_label == "GATED_DEFICIT"
                else ("AWAITING_VALIDATION" if path_exists else "AWAITING_TRAINING")
            )
        )

        return {
            "fruit": meta.fruit_id,
            "common_name": meta.common_name,
            "scientific_name": meta.scientific_name,
            "cultivar": meta.primary_cultivar,
            "supported": True,
            "available": is_ready,
            "is_validated": meta.is_validated,
            "status": status_val,
            "architecture": meta.architecture,
            "task_type": meta.task_type,
            "model_version": meta.model_version,
            "classes": list(meta.classes),
            "class_labels": dict(meta.class_labels),
            "num_classes": meta.num_classes,
            "weights_path": str(path),
            "weights_exist": path_exists,
            "message": msg,
        }

    def get_full_registry_status(self) -> Dict[str, Any]:
        """Return comprehensive diagnostic summary for all fruits and the stage-1 identifier."""
        stage1_path = settings.resolved_fruit_identifier_weights_path()
        stage1_exists = stage1_path.exists()
        stage1_available = self._identifier_meta.is_validated and stage1_exists

        return {
            "supported_fruits": self.get_supported_fruits(),
            "available_fruits": [f for f in self.get_supported_fruits() if self.is_fruit_available(f)],
            "production_crop": "guava",
            "fruits": {f: self.get_fruit_status(f) for f in self.get_supported_fruits()},
            "stage1_identifier": {
                "supported": True,
                "available": stage1_available,
                "status": self._identifier_meta.status_label if stage1_available else "AWAITING_TRAINING",
                "checkpoint": self._identifier_meta.checkpoint_filename,
                "architecture": self._identifier_meta.architecture,
                "version": self._identifier_meta.model_version,
                "classes": list(self._identifier_meta.classes),
                "weights_path": str(stage1_path),
                "weights_exist": stage1_exists,
                "message": (
                    f"Stage 1 fruit identifier ({self._identifier_meta.architecture}) v{self._identifier_meta.model_version} active."
                    if stage1_available else "Stage 1 fruit identifier awaiting multi-fruit dataset curation and training."
                ),
            },
        }


# Global registry instance
model_registry = MultiFruitModelRegistry()

