"""
AgriChain AI - Backend Core Configuration
=========================================
Central configuration settings module loading environment variables
with strict defaults aligning with backend/.env.example.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

# Locate the root backend and monorepo root
BACKEND_DIR = Path(__file__).resolve().parents[2]
MONOREPO_ROOT = BACKEND_DIR.parent


class Settings(BaseModel):
    PROJECT_NAME: str = Field(
        default_factory=lambda: os.getenv("PROJECT_NAME", "AgriChain AI Backend")
    )
    API_V1_STR: str = Field(
        default_factory=lambda: os.getenv("API_V1_STR", "/api/v1")
    )
    DEBUG: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    )

    # Server Bindings
    HOST: str = Field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0")
    )
    PORT: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000"))
    )

    # CORS Allowed Origins
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: (
            json.loads(os.getenv("BACKEND_CORS_ORIGINS"))
            if os.getenv("BACKEND_CORS_ORIGINS")
            else ["http://localhost:3000", "http://127.0.0.1:3000"]
        )
    )

    # Relational & Spatial Database
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db",
        )
    )
    SYNC_DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "SYNC_DATABASE_URL",
            "postgresql://agrichain_user:your_secure_password_here@localhost:5432/agrichain_db",
        )
    )
    DATABASE_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("DATABASE_ENABLED", "false").lower() in ("true", "1", "yes")
    )

    # ML Inference Configuration
    MODEL_DEVICE: str = Field(
        default_factory=lambda: os.getenv("MODEL_DEVICE", "cuda")
    )
    MODEL_BACKBONE: str = Field(
        default_factory=lambda: os.getenv("MODEL_BACKBONE", "resnet18")
    )
    MODEL_NUM_CLASSES: int = Field(
        default_factory=lambda: int(os.getenv("MODEL_NUM_CLASSES", "3"))
    )
    MODEL_WEIGHTS_PATH: str = Field(
        default_factory=lambda: os.getenv(
            "MODEL_WEIGHTS_PATH", "ml/artifacts/best_kinnow_resnet18.pth"
        )
    )
    CONFIDENCE_THRESHOLD: float = Field(
        default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
    )

    # Crop and Scientific Integrity Guard
    TARGET_CROP: str = Field(
        default_factory=lambda: os.getenv("TARGET_CROP", "guava")
    )
    # Class mapping verification guard (Guava classes: Green, Mature Green, Ripe)
    CLASS_MAPPING_VERIFIED: bool = True
    CLASS_MAPPING_STATUS: str = "VERIFIED_GROUND_TRUTH_METADATA"
    KINNOW_CLASSES: List[str] = ["class0", "class1", "class2"]
    KINNOW_CLASS_LABELS: dict[int, str] = {
        0: "Underripe",
        1: "Partially Ripe",
        2: "Fully Ripe",
    }

    # Guava CNN Configuration (Phase 4 Integration)
    GUAVA_MODEL_WEIGHTS_PATH: str = Field(
        default_factory=lambda: os.getenv(
            "GUAVA_MODEL_WEIGHTS_PATH", "ml/artifacts/best_guava_resnet18.pth"
        )
    )
    GUAVA_MODEL_VERSION: str = Field(
        default_factory=lambda: os.getenv("GUAVA_MODEL_VERSION", "2.0.0")
    )
    GUAVA_CLASSES: List[str] = ["Green", "Mature Green", "Ripe"]
    GUAVA_CLASS_LABELS: dict[int, str] = {
        0: "Green",
        1: "Mature Green",
        2: "Ripe",
    }
    # Controlled Activation Guard (Activated for Guava primary crop)
    GUAVA_MODEL_ACTIVATED: bool = Field(
        default_factory=lambda: os.getenv("GUAVA_MODEL_ACTIVATED", "true").lower() in ("true", "1", "yes")
    )

    # Banana CNN Configuration (Phase 14 Baseline)
    BANANA_MODEL_WEIGHTS_PATH: str = Field(
        default_factory=lambda: os.getenv(
            "BANANA_MODEL_WEIGHTS_PATH", "ml/artifacts/best_banana_resnet18.pth"
        )
    )
    BANANA_MODEL_VERSION: str = Field(
        default_factory=lambda: os.getenv("BANANA_MODEL_VERSION", "1.0.0")
    )
    BANANA_CLASSES: List[str] = ["Unripe", "Half_Ripe", "Ripe", "Overripe"]
    BANANA_CLASS_LABELS: dict[int, str] = {
        0: "Unripe",
        1: "Half_Ripe",
        2: "Ripe",
        3: "Overripe",
    }

    # Apple YOLOv8n Object Detection Configuration (Phase 16B Workstream B)
    APPLE_MODEL_WEIGHTS_PATH: str = Field(
        default_factory=lambda: os.getenv(
            "APPLE_MODEL_WEIGHTS_PATH", "ml/artifacts/best_apple_yolov8n.pt"
        )
    )
    APPLE_MODEL_VERSION: str = Field(
        default_factory=lambda: os.getenv("APPLE_MODEL_VERSION", "1.0.0-experimental")
    )
    APPLE_CONFIDENCE_THRESHOLD: float = Field(
        default_factory=lambda: float(os.getenv("APPLE_CONFIDENCE_THRESHOLD", "0.25"))
    )

    # Stage 1 Multi-Fruit Identifier V2 Configuration (Phase 16B Workstream A)
    FRUIT_IDENTIFIER_WEIGHTS_PATH: str = Field(
        default_factory=lambda: os.getenv(
            "FRUIT_IDENTIFIER_WEIGHTS_PATH", "ml/artifacts/best_fruit_identifier_mobilenet_v3_large.pth"
        )
    )
    FRUIT_IDENTIFIER_BACKBONE: str = Field(
        default_factory=lambda: os.getenv("FRUIT_IDENTIFIER_BACKBONE", "mobilenet_v3_large")
    )
    FRUIT_IDENTIFIER_VERSION: str = Field(
        default_factory=lambda: os.getenv("FRUIT_IDENTIFIER_VERSION", "2.0.0")
    )
    FRUIT_IDENTIFIER_CLASSES: List[str] = ["guava", "banana", "apple", "mango", "negative_background"]
    FRUIT_IDENTIFIER_CONFIDENCE_THRESHOLD: float = Field(
        default_factory=lambda: float(os.getenv("FRUIT_IDENTIFIER_CONFIDENCE_THRESHOLD", "0.80"))
    )
    FRUIT_IDENTIFIER_MARGIN_THRESHOLD: float = Field(
        default_factory=lambda: float(os.getenv("FRUIT_IDENTIFIER_MARGIN_THRESHOLD", "0.15"))
    )

    # Image upload constraints
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB cap
    ALLOWED_IMAGE_TYPES: List[str] = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    ]
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    def resolved_weights_path(self, crop: Optional[str] = None) -> Path:
        """Resolve model weights path relative to backend or monorepo root."""
        # Use banana path if explicitly requested
        if crop == "banana":
            raw_path = self.BANANA_MODEL_WEIGHTS_PATH
        # Use apple path if explicitly requested
        elif crop == "apple":
            raw_path = self.APPLE_MODEL_WEIGHTS_PATH
        # Use fruit identifier path if explicitly requested
        elif crop in ("fruit_identifier", "identifier"):
            raw_path = self.FRUIT_IDENTIFIER_WEIGHTS_PATH
        # Use guava path if explicitly requested or if guava is activated as the target crop
        elif crop == "guava" or (crop is None and self.GUAVA_MODEL_ACTIVATED and self.TARGET_CROP.lower() == "guava"):
            raw_path = self.GUAVA_MODEL_WEIGHTS_PATH
        else:
            raw_path = self.MODEL_WEIGHTS_PATH

        p = Path(raw_path)
        if p.is_absolute():
            return p
        # Check relative to backend dir first
        candidate1 = (BACKEND_DIR / p).resolve()
        if candidate1.exists():
            return candidate1
        # Check relative to monorepo root
        candidate2 = (MONOREPO_ROOT / p).resolve()
        if candidate2.exists():
            return candidate2
        # Return candidate2 as canonical reference path
        return candidate2

    def resolved_guava_weights_path(self) -> Path:
        """Explicitly resolve guava model weights path."""
        return self.resolved_weights_path(crop="guava")

    def resolved_banana_weights_path(self) -> Path:
        """Explicitly resolve banana model weights path."""
        return self.resolved_weights_path(crop="banana")

    def resolved_apple_weights_path(self) -> Path:
        """Explicitly resolve apple YOLOv8n weights path."""
        p = self.resolved_weights_path(crop="apple")
        if p.exists():
            return p
        fallback = (MONOREPO_ROOT / "ml/experiments/phase16b/apple_yolo/best_apple_yolov8n.pt").resolve()
        if fallback.exists():
            return fallback
        return p

    def resolved_fruit_identifier_weights_path(self) -> Path:
        """Explicitly resolve Stage 1 Fruit Identifier weights path."""
        p = self.resolved_weights_path(crop="fruit_identifier")
        if p.exists():
            return p
        fallback_mb = (MONOREPO_ROOT / "ml/experiments/phase16b/fruit_identifier_v2/mobilenet_v3_large/best_mobilenet_v3_large.pth").resolve()
        if fallback_mb.exists():
            return fallback_mb
        fallback_rn = (MONOREPO_ROOT / "ml/artifacts/best_fruit_identifier_resnet18.pth").resolve()
        if fallback_rn.exists():
            return fallback_rn
        return p


settings = Settings()
