"""
AgriChain AI - CNN Schemas
===========================
Pydantic v2 validation models for CNN inference, model health, and validation status.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CNNPredictionResponse(BaseModel):
    """
    Standardized, strongly-typed response returned by the CNN prediction route.
    Maintains backwards compatibility with legacy client properties while providing
    full auditability for the produce quality inspection pipeline.
    """
    predicted_class: str = Field(
        ...,
        description="Internal model class identifier (e.g., 'Green', 'Mature Green', 'Ripe').",
    )
    class_index: int = Field(
        ...,
        ge=0,
        description="Zero-indexed classification label.",
    )
    label: str = Field(
        ...,
        description="Human-readable ripeness / quality stage label.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Softmax output score associated with the predicted class (uncalibrated heuristic score, not a calibrated probability).",
    )
    probabilities: Dict[str, float] = Field(
        ...,
        description="Softmax output distribution across all evaluated classes.",
    )
    target_crop: str = Field(
        default="guava",
        description="Validated target crop name (e.g., 'guava', 'kinnow').",
    )
    model_name: str = Field(
        ...,
        description="Identifier of the active frozen model checkpoint.",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Semantic version of the loaded model checkpoint artifact.",
    )
    device: str = Field(
        ...,
        description="Execution compute device ('cuda' or 'cpu').",
    )
    inference_ms: Optional[float] = Field(
        default=None,
        description="Wall-clock inference latency in milliseconds.",
    )

    # Multi-Fruit Architecture Extensions (Phase 14A, backwards-compatible)
    detected_fruit: Optional[str] = Field(
        default=None,
        description="Stage 1 detected fruit commodity species (e.g., 'guava', 'mango', 'banana', 'apple').",
    )
    fruit_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Softmax activation score of the Stage 1 fruit identifier.",
    )
    fruit_probabilities: Optional[Dict[str, float]] = Field(
        default=None,
        description="Class probability distribution across supported commodities from Stage 1.",
    )
    ripeness: Optional[str] = Field(
        default=None,
        description="Semantic alias for predicted_class corresponding to native fruit maturity stages.",
    )
    status: Optional[str] = Field(
        default=None,
        description="Operational prediction status ('ready', 'fruit_unsupported', 'model_unavailable', 'uncertain').",
    )
    is_validated: Optional[bool] = Field(
        default=None,
        description="Whether the active checkpoint for this specific fruit has passed certified statistical evaluation.",
    )
    warnings: Optional[list[str]] = Field(
        default=None,
        description="Diagnostic warnings, such as low identification confidence or transitional boundaries.",
    )


class CNNModelStatusResponse(BaseModel):
    """
    Inspection status response detailing model availability and validation state.
    """
    status: str = Field(
        ...,
        description="High-level status: 'ready' when a validated model is loaded, 'unavailable' otherwise.",
    )
    target_crop: str = Field(
        default="guava",
        description="Target agricultural crop.",
    )
    model_available: bool = Field(
        ...,
        description="Whether a valid, certified model is loaded and accepting inference requests.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Name of the model architecture.",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Semantic version of the model checkpoint if loaded.",
    )
    weights_path: str = Field(
        ...,
        description="Configured weights filepath.",
    )
    weights_exist: bool = Field(
        ...,
        description="Whether the weights file is physically present on disk.",
    )
    device: str = Field(
        ...,
        description="Compute device target.",
    )
    class_mapping_verified: bool = Field(
        default=False,
        description="Whether numeric class indices 0, 1, 2 have been verified against ground truth.",
    )
    class_mapping_status: str = Field(
        default="UNCONFIRMED_PENDING_GROUND_TRUTH_VALIDATION",
        description="Class mapping verification status.",
    )
    message: str = Field(
        ...,
        description="Detailed diagnostic or availability message.",
    )


class FruitRegistryItemSchema(BaseModel):
    """Schema representing one registered fruit commodity in the model registry."""
    fruit: str
    common_name: str
    scientific_name: str
    cultivar: str
    supported: bool
    available: bool
    is_validated: bool
    status: str
    architecture: str
    task_type: str = "classification"
    model_version: Optional[str] = None
    classes: list[str]
    class_labels: Dict[int, str]
    num_classes: int
    weights_path: str
    weights_exist: bool
    message: str


class MultiFruitRegistryStatusResponse(BaseModel):
    """Overall multi-fruit registry status response."""
    supported_fruits: list[str]
    available_fruits: list[str]
    production_crop: str = "guava"
    fruits: Dict[str, FruitRegistryItemSchema]
    stage1_identifier: Dict[str, Any]


class BoundingBox(BaseModel):
    """Normalized or pixel coordinates of a single detected produce instance."""
    x1: float = Field(..., description="Top-left X coordinate.")
    y1: float = Field(..., description="Top-left Y coordinate.")
    x2: float = Field(..., description="Bottom-right X coordinate.")
    y2: float = Field(..., description="Bottom-right Y coordinate.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score.")
    class_id: int = Field(default=0, description="Class index (0 for apple).")
    class_name: str = Field(default="apple", description="Detected commodity class name.")


class AppleDetectionResult(BaseModel):
    """Orchard object detection result for Apple specimens (YOLOv8n)."""
    task: str = Field(default="object_detection", description="Model task type.")
    detected_apples_count: int = Field(..., ge=0, description="Total count of apple instances detected.")
    boxes: List[BoundingBox] = Field(default_factory=list, description="List of bounding boxes with confidences.")
    average_confidence: Optional[float] = Field(default=None, description="Mean confidence across all detected bounding boxes.")
    model_name: str = Field(default="yolov8n", description="Detection architecture.")
    model_version: str = Field(default="1.0.0-experimental", description="Checkpoint version.")
    license: str = Field(
        default="Academic / Non-Commercial Research Only (CC BY-NC 4.0)",
        description="Dataset and model usage terms.",
    )
    scope_disclaimer: str = Field(
        default=(
            "This experimental model performs orchard object detection and instance counting only. "
            "It does NOT evaluate maturity stages, ripeness, sweetness, disease, or commercial market grade."
        ),
        description="Explicit agronomic and capabilities boundary.",
    )


class FruitIdentificationResult(BaseModel):
    """Stage 1 species recognition and canopy/background rejection output."""
    predicted_fruit: str = Field(..., description="Predicted commodity ('guava', 'banana', 'apple', 'mango', 'negative_background').")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Top-1 softmax probability.")
    probabilities: Dict[str, float] = Field(..., description="Softmax distribution across all 5 Stage 1 classes.")
    is_uncertain: bool = Field(..., description="True if top confidence is below threshold (< 0.80), low margin (< 0.15), or negative_background.")
    uncertainty_reason: Optional[str] = Field(default=None, description="Explanation when identification is ambiguous.")
    model_name: str = Field(default="mobilenet_v3_large", description="Identifier architecture.")
    model_version: str = Field(default="2.0.0", description="Identifier version.")


class FruitInspectionResponse(BaseModel):
    """Unified response envelope for multi-fruit inspection in both manual and automatic modes."""
    mode: str = Field(..., description="Execution mode: 'manual' or 'auto'.")
    target_fruit: str = Field(..., description="Target fruit commodity ('guava', 'banana', 'apple', 'mango', 'negative_background', 'unknown').")
    task_type: str = Field(..., description="Task type: 'classification', 'object_detection', or 'unavailable'.")
    status: str = Field(..., description="Execution status: 'ready', 'unavailable', 'uncertain', or 'unknown_fruit'.")
    identified_fruit: Optional[str] = Field(default=None, description="Stage 1 detected fruit if auto mode was invoked.")
    identification: Optional[FruitIdentificationResult] = Field(default=None, description="Detailed Stage 1 identification diagnostics.")
    classification: Optional[CNNPredictionResponse] = Field(default=None, description="Maturity/ripeness classification output (Guava / Banana).")
    detection: Optional[AppleDetectionResult] = Field(default=None, description="Object detection output (Apple YOLOv8n).")
    unavailable_reason: Optional[str] = Field(default=None, description="Detailed explanation if commodity model is unavailable / data-deficit.")
    warnings: List[str] = Field(default_factory=list, description="Diagnostic warnings or user guidance.")
    device: str = Field(..., description="Compute execution device ('cuda' or 'cpu').")
    inference_ms: float = Field(..., description="Total wall-clock inference duration in milliseconds.")

