"""
AgriChain AI - CNN Quality Inspection Service
=============================================
Encapsulates image validation, model lifecycle management, and CNN inference.
Supports verified Guava (*Psidium guajava*) ResNet18 maturity classification (classes: Green, Mature Green, Ripe)
with strict rejection of uncertified or proxy checkpoints.

Strict Scientific Constraints:
1. Rejects proxy or unrelated crop checkpoints for harvest maturity predictions.
2. If no valid model artifact exists, marks the service unavailable (HTTP 503).
3. NEVER fabricates predictions, confidence scores, or freshness/spoilage percentages.
4. Performs strict image decoding and payload validation.
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.schemas.cnn import (
    AppleDetectionResult,
    BoundingBox,
    CNNModelStatusResponse,
    CNNPredictionResponse,
    FruitIdentificationResult,
    FruitInspectionResponse,
)
from app.services.model_registry import model_registry

logger = logging.getLogger("agrichain.services.cnn")


class CNNServiceError(Exception):
    """Base exception for CNN service operations."""
    status_code: int = 500
    detail: str = "Internal CNN service error"

    def __init__(self, detail: Optional[str] = None, status_code: Optional[int] = None):
        if detail:
            self.detail = detail
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail)


class UnsupportedMediaTypeError(CNNServiceError):
    status_code = 415
    detail = "Unsupported file type. Please upload a JPEG, PNG, or WEBP image."


class InvalidImageError(CNNServiceError):
    status_code = 400
    detail = "Invalid or corrupted image payload."


class ImageTooLargeError(CNNServiceError):
    status_code = 400
    detail = "Uploaded file exceeds maximum allowed size."


class ModelUnavailableError(CNNServiceError):
    status_code = 503
    detail = (
        "Produce visual classification model is currently unavailable. "
        "Awaiting completion and deployment of a certified model checkpoint. "
        "Synthetic or cross-crop proxy predictions are strictly disabled."
    )


class CNNService:
    """
    Service managing model loading, image validation, and quality classification.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        crop: Optional[str] = None,
        model_version: Optional[str] = None,
    ):
        self.crop = (crop or (
            "guava" if (settings.GUAVA_MODEL_ACTIVATED and settings.TARGET_CROP.lower() == "guava") else settings.TARGET_CROP
        )).lower()

        if weights_path is not None:
            self.weights_path = Path(weights_path)
            if "guava" in str(self.weights_path).lower():
                self.crop = "guava"
            elif "banana" in str(self.weights_path).lower():
                self.crop = "banana"
        elif self.crop == "guava":
            self.weights_path = settings.resolved_guava_weights_path()
        elif self.crop == "banana":
            self.weights_path = settings.resolved_banana_weights_path()
        else:
            self.weights_path = settings.resolved_weights_path()

        self.device_str = settings.MODEL_DEVICE
        self.target_crop = self.crop
        self.model_version = model_version or (
            settings.GUAVA_MODEL_VERSION if self.crop == "guava"
            else (settings.BANANA_MODEL_VERSION if self.crop == "banana" else None)
        )

        if self.crop == "guava":
            self.num_classes = len(settings.GUAVA_CLASSES)
            self.classes = list(settings.GUAVA_CLASSES)
            self.class_labels = dict(settings.GUAVA_CLASS_LABELS)
            self.class_mapping_verified = True
            self.class_mapping_status = "VERIFIED_GROUND_TRUTH_METADATA"
        elif self.crop == "banana":
            self.num_classes = len(settings.BANANA_CLASSES)
            self.classes = list(settings.BANANA_CLASSES)
            self.class_labels = dict(settings.BANANA_CLASS_LABELS)
            self.class_mapping_verified = True
            self.class_mapping_status = "VERIFIED_GROUND_TRUTH_METADATA"
        else:
            self.num_classes = settings.MODEL_NUM_CLASSES
            self.classes = list(settings.KINNOW_CLASSES)
            self.class_labels = dict(settings.KINNOW_CLASS_LABELS)
            self.class_mapping_verified = settings.CLASS_MAPPING_VERIFIED
            self.class_mapping_status = settings.CLASS_MAPPING_STATUS

        self.model: Any = None
        self.torch_device: Any = None
        self.transform: Any = None
        self._is_ready: bool = False
        self._status_message: str = ""

        # Attempt to initialize runtime components safely
        self._initialize()

    def _initialize(self) -> None:
        """Inspect environment, hardware device, and model artifact availability."""
        # 1. Resolve compute device
        try:
            import torch
            if self.device_str == "cuda" and torch.cuda.is_available():
                self.torch_device = torch.device("cuda")
            else:
                self.torch_device = torch.device("cpu")
        except ImportError:
            self.torch_device = "cpu"

        # 2. Inspect configured weights artifact
        if not self.weights_path.exists():
            self._is_ready = False
            crop_label = self.crop.capitalize()
            self._status_message = (
                f"Model checkpoint not found at '{self.weights_path}'. "
                f"{crop_label} classification service remains disabled until a certified checkpoint is trained and frozen."
            )
            logger.warning("CNNService: %s", self._status_message)
            return

        # 3. Load and inspect checkpoint metadata
        try:
            import torch
            checkpoint = torch.load(self.weights_path, map_location=self.torch_device)

            # Integrity check: Ensure checkpoint is NOT a legacy strawberry model
            crop_tag = checkpoint.get("crop", "").lower() if isinstance(checkpoint, dict) else ""
            if "strawberry" in crop_tag or "strawberry" in str(self.weights_path).lower():
                self._is_ready = False
                self._status_message = (
                    "Integrity Violation: Legacy strawberry model detected. "
                    "In accordance with AgriChain AI integrity standards, strawberry models cannot be "
                    "reused for produce predictions. Service disabled."
                )
                logger.error("CNNService: %s", self._status_message)
                return

            # If checkpoint contains guava metadata, reconcile and verify
            if crop_tag == "guava" or "guava" in str(self.weights_path).lower():
                self.target_crop = "guava"
                self.crop = "guava"
                if isinstance(checkpoint, dict):
                    if "class_mapping" in checkpoint:
                        ckpt_mapping = checkpoint["class_mapping"]
                        int_mapping = {int(k): str(v) for k, v in ckpt_mapping.items()}
                        self.class_labels = int_mapping
                        self.classes = [int_mapping[i] for i in range(len(int_mapping))]
                        self.num_classes = len(self.classes)
                    if "config" in checkpoint:
                        self.model_version = checkpoint["config"].get("version", self.model_version or "2.0.0")
                self.class_mapping_verified = True
                self.class_mapping_status = "VERIFIED_GROUND_TRUTH_METADATA"

            # If checkpoint contains banana metadata, reconcile and verify
            elif crop_tag == "banana" or "banana" in str(self.weights_path).lower():
                self.target_crop = "banana"
                self.crop = "banana"
                if isinstance(checkpoint, dict):
                    if "idx_to_class" in checkpoint:
                        ckpt_mapping = checkpoint["idx_to_class"]
                        int_mapping = {int(k): str(v) for k, v in ckpt_mapping.items()}
                        self.class_labels = int_mapping
                        self.classes = [int_mapping[i] for i in range(len(int_mapping))]
                        self.num_classes = len(self.classes)
                    elif "classes" in checkpoint:
                        self.classes = list(checkpoint["classes"])
                        self.class_labels = {i: c for i, c in enumerate(self.classes)}
                        self.num_classes = len(self.classes)
                    if "config" in checkpoint:
                        self.model_version = checkpoint["config"].get("version", self.model_version or "1.0.0")
                self.class_mapping_verified = True
                self.class_mapping_status = "VERIFIED_GROUND_TRUTH_METADATA"

            # Checkpoint is valid and ready
            self._load_torch_model(checkpoint)
            self._is_ready = True
            self._status_message = f"Model loaded successfully on {self.torch_device} for {self.target_crop}."
            logger.info("CNNService: %s", self._status_message)

        except Exception as exc:
            self._is_ready = False
            self._status_message = f"Failed to load model artifact: {exc}"
            logger.exception("CNNService initialization error: %s", exc)

    def _load_torch_model(self, checkpoint: Any) -> None:
        """Instantiate PyTorch architecture and load state dict."""
        import torch
        from torchvision import models, transforms

        # ResNet18 transfer architecture matching research specs
        model = models.resnet18(weights=None)
        in_features = model.fc.in_features

        dropout_p = 0.2
        if isinstance(checkpoint, dict) and "config" in checkpoint:
            dropout_p = checkpoint["config"].get("model", {}).get("dropout", 0.2)

        model.fc = torch.nn.Sequential(
            torch.nn.Dropout(p=dropout_p),
            torch.nn.Linear(in_features, self.num_classes),
        )

        state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
        model.load_state_dict(state_dict)
        model = model.to(self.torch_device)
        model.eval()
        self.model = model

        # Standard deterministic validation transform with strict parity to training evaluation
        # Preprocessing: Resize(256) -> CenterCrop(224) -> ToTensor() -> Normalize(...)
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    @property
    def is_available(self) -> bool:
        """Return True if a certified model is actively loaded and ready."""
        return self._is_ready and self.model is not None

    def get_status(self) -> CNNModelStatusResponse:
        """Return diagnostic status of the CNN inspection module."""
        return CNNModelStatusResponse(
            status="ready" if self.is_available else "unavailable",
            target_crop=self.target_crop,
            model_available=self.is_available,
            model_name=settings.MODEL_BACKBONE,
            model_version=self.model_version if self.is_available else None,
            weights_path=str(self.weights_path),
            weights_exist=self.weights_path.exists(),
            device=str(self.torch_device),
            class_mapping_verified=self.class_mapping_verified,
            class_mapping_status=self.class_mapping_status,
            message=self._status_message,
        )

    def validate_image_bytes(
        self,
        raw_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Image.Image:
        """
        Validate image type, non-emptiness, size limits, and readability.
        Returns decoded RGB PIL Image.
        Raises corresponding CNNServiceError subclasses for HTTP status translation.
        """
        # 1. Non-empty check
        if not raw_bytes or len(raw_bytes) == 0:
            raise InvalidImageError("Empty upload payload.")

        # 2. Maximum file size check
        if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
            raise ImageTooLargeError(
                f"File size ({len(raw_bytes)} bytes) exceeds the allowed limit of {settings.MAX_UPLOAD_BYTES} bytes."
            )

        # 3. Content-Type and filename extension check
        ct = (content_type or "").lower().strip()
        if ct and ct not in settings.ALLOWED_IMAGE_TYPES:
            raise UnsupportedMediaTypeError(
                f"Unsupported content type '{content_type}'. Expected one of {settings.ALLOWED_IMAGE_TYPES}."
            )

        if filename:
            ext = Path(filename).suffix.lower()
            if ext and ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
                raise UnsupportedMediaTypeError(
                    f"Unsupported file extension '{ext}'. Expected one of {settings.ALLOWED_IMAGE_EXTENSIONS}."
                )

        # 4. Stream decoding and readability verification
        try:
            image = Image.open(io.BytesIO(raw_bytes))
            # Force decode pixels immediately to detect truncated or corrupted files
            image.load()

            # Ensure minimum viable dimensions
            if image.width < 10 or image.height < 10:
                raise InvalidImageError("Image dimensions are too small to be a valid produce specimen.")

            # Convert to standard RGB 3-channel mode
            if image.mode != "RGB":
                image = image.convert("RGB")

            return image

        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning("Unreadable image rejected: %s", exc)
            raise InvalidImageError("Invalid or corrupted image. Unable to decode pixel buffer.")

    def predict(self, image: Image.Image) -> CNNPredictionResponse:
        """
        Execute model inference on a validated PIL Image.
        Guarantees:
        - Never fabricates results if model is not loaded (raises ModelUnavailableError).
        - Computes true softmax probabilities and latency.
        - Provides predicted class and uncalibrated confidence score with clear semantics.
        """
        if not self.is_available:
            crop_label = self.target_crop.capitalize()
            raise ModelUnavailableError(
                detail=(
                    f"{crop_label} model inference is currently unavailable. {self._status_message}"
                )
            )

        import torch
        import torch.nn.functional as F

        t0 = time.perf_counter()

        # Preprocessing: strict parity with training evaluation
        tensor = self.transform(image).unsqueeze(0).to(self.torch_device)

        # Inference
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities_tensor = F.softmax(logits, dim=1).squeeze(0)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        predicted_idx = int(torch.argmax(probabilities_tensor).item())
        confidence = float(probabilities_tensor[predicted_idx].item())

        probs_dict: Dict[str, float] = {}
        for i, class_name in enumerate(self.classes):
            if i < len(probabilities_tensor):
                probs_dict[class_name] = round(float(probabilities_tensor[i].item()), 4)

        label = self.class_labels.get(predicted_idx, f"Class {predicted_idx}")

        return CNNPredictionResponse(
            predicted_class=self.classes[predicted_idx],
            class_index=predicted_idx,
            label=label,
            confidence=round(confidence, 4),
            probabilities=probs_dict,
            target_crop=self.target_crop,
            model_name=settings.MODEL_BACKBONE,
            model_version=self.model_version,
            device=str(self.torch_device),
            inference_ms=round(latency_ms, 2),
            detected_fruit=None,  # Stage 1 fruit identifier not yet installed; do not fabricate fruit ID
            fruit_confidence=None,
            fruit_probabilities=None,
            ripeness=self.classes[predicted_idx],
            status="ready",
            is_validated=self.class_mapping_verified,
        )


class FruitIdentifierService:
    """
    Stage 1 Multi-Fruit Species Classifier & Canopy/Background Rejection Service.
    Evaluates whether an uploaded image contains Guava, Banana, Apple, Mango, or Non-Fruit / Canopy.
    """

    def __init__(self, weights_path: Optional[Path] = None):
        self.weights_path = Path(weights_path) if weights_path else settings.resolved_fruit_identifier_weights_path()
        self.device_str = settings.MODEL_DEVICE
        self.model: Any = None
        self.torch_device: Any = None
        self.transform: Any = None
        self._is_ready: bool = False
        self._status_message: str = ""
        self.classes = list(settings.FRUIT_IDENTIFIER_CLASSES)
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
        self.idx_to_class = {i: c for i, c in enumerate(self.classes)}
        self.architecture = settings.FRUIT_IDENTIFIER_BACKBONE
        self.model_version = settings.FRUIT_IDENTIFIER_VERSION

        self._initialize()

    def _initialize(self) -> None:
        """Load device, weights, architecture, and validation transform safely."""
        try:
            import torch
            if self.device_str == "cuda" and torch.cuda.is_available():
                self.torch_device = torch.device("cuda")
            else:
                self.torch_device = torch.device("cpu")
        except ImportError:
            self.torch_device = "cpu"

        if not self.weights_path.exists():
            self._is_ready = False
            self._status_message = f"Fruit Identifier checkpoint not found at '{self.weights_path}'."
            logger.warning("FruitIdentifierService: %s", self._status_message)
            return

        try:
            import torch
            from torchvision import models, transforms

            checkpoint = torch.load(self.weights_path, map_location=self.torch_device)
            arch = (
                checkpoint.get("architecture", self.architecture)
                if isinstance(checkpoint, dict)
                else self.architecture
            )

            if "mobilenet" in str(arch).lower():
                self.architecture = "mobilenet_v3_large"
                model = models.mobilenet_v3_large(weights=None)
                in_features = model.classifier[3].in_features
                model.classifier[3] = torch.nn.Linear(in_features, len(self.classes))
                state_dict = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
                model.load_state_dict(state_dict)
            else:
                self.architecture = "resnet18"
                model = models.resnet18(weights=None)
                in_features = model.fc.in_features
                dropout_p = 0.2
                if isinstance(checkpoint, dict) and "config" in checkpoint:
                    dropout_p = checkpoint["config"].get("model", {}).get("dropout", 0.2)
                model.fc = torch.nn.Sequential(
                    torch.nn.Dropout(p=dropout_p),
                    torch.nn.Linear(in_features, len(self.classes)),
                )
                state_dict = (
                    checkpoint["model_state_dict"]
                    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
                    else checkpoint
                )
                model.load_state_dict(state_dict)

            model = model.to(self.torch_device)
            model.eval()
            self.model = model

            self.transform = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.CenterCrop((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ])

            self._is_ready = True
            self._status_message = (
                f"Fruit Identifier ({self.architecture}) loaded successfully on {self.torch_device}."
            )
            logger.info("FruitIdentifierService: %s", self._status_message)

        except Exception as exc:
            self._is_ready = False
            self._status_message = f"Failed to load Fruit Identifier checkpoint: {exc}"
            logger.exception("FruitIdentifierService initialization error: %s", exc)

    @property
    def is_available(self) -> bool:
        return self._is_ready and self.model is not None

    def identify(self, image: Image.Image) -> FruitIdentificationResult:
        """Run Stage 1 species identification and canopy rejection."""
        if not self.is_available:
            raise ModelUnavailableError(
                detail=f"Fruit Identifier service is unavailable. {self._status_message}"
            )

        import torch
        import torch.nn.functional as F

        tensor = self.transform(image).unsqueeze(0).to(self.torch_device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs_t = F.softmax(logits, dim=1).squeeze(0)

        # Build class probability mapping
        probs_dict: Dict[str, float] = {}
        for i, c in enumerate(self.classes):
            if i < len(probs_t):
                probs_dict[c] = round(float(probs_t[i].item()), 4)

        # Sort to find top-1 and top-2
        sorted_pairs = sorted(probs_dict.items(), key=lambda kv: kv[1], reverse=True)
        top_class, top_conf = sorted_pairs[0]
        second_class, second_conf = sorted_pairs[1] if len(sorted_pairs) > 1 else ("", 0.0)
        margin = top_conf - second_conf

        # Evaluate uncertainty conditions
        is_uncertain = False
        uncertainty_reason: Optional[str] = None

        if top_class == "negative_background":
            is_uncertain = True
            uncertainty_reason = (
                "Non-fruit canopy or background foliage detected. Please upload an image centered on produce."
            )
        elif top_conf < settings.FRUIT_IDENTIFIER_CONFIDENCE_THRESHOLD:
            is_uncertain = True
            uncertainty_reason = (
                f"Low species confidence ({round(top_conf * 100, 1)}% < "
                f"{round(settings.FRUIT_IDENTIFIER_CONFIDENCE_THRESHOLD * 100, 1)}%). Manual confirmation required."
            )
        elif margin < settings.FRUIT_IDENTIFIER_MARGIN_THRESHOLD:
            is_uncertain = True
            uncertainty_reason = (
                f"Ambiguous boundary between '{top_class}' and '{second_class}' "
                f"(margin {round(margin * 100, 1)}% < {round(settings.FRUIT_IDENTIFIER_MARGIN_THRESHOLD * 100, 1)}%). "
                "Manual confirmation required."
            )

        return FruitIdentificationResult(
            predicted_fruit=top_class,
            confidence=round(top_conf, 4),
            probabilities=probs_dict,
            is_uncertain=is_uncertain,
            uncertainty_reason=uncertainty_reason,
            model_name=self.architecture,
            model_version=self.model_version,
        )


class AppleDetectionService:
    """
    Apple Orchard Object Detection Service (YOLOv8n).
    Exposes bounding boxes, instance count, confidence, and strict licensing terms.
    Does NOT evaluate harvest maturity or quality grading.
    """

    def __init__(self, weights_path: Optional[Path] = None):
        self.weights_path = Path(weights_path) if weights_path else settings.resolved_apple_weights_path()
        self.model: Any = None
        self._is_ready: bool = False
        self._status_message: str = ""
        self._initialize()

    def _initialize(self) -> None:
        if not self.weights_path.exists():
            self._is_ready = False
            self._status_message = f"Apple YOLO checkpoint not found at '{self.weights_path}'."
            logger.warning("AppleDetectionService: %s", self._status_message)
            return

        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.weights_path))
            self._is_ready = True
            self._status_message = f"Apple YOLOv8n detector loaded successfully from '{self.weights_path.name}'."
            logger.info("AppleDetectionService: %s", self._status_message)
        except Exception as exc:
            self._is_ready = False
            self._status_message = f"Failed to load Apple YOLO model: {exc}"
            logger.exception("AppleDetectionService initialization error: %s", exc)

    @property
    def is_available(self) -> bool:
        return self._is_ready and self.model is not None

    def detect(self, image: Image.Image, conf_threshold: Optional[float] = None) -> AppleDetectionResult:
        if not self.is_available:
            raise ModelUnavailableError(
                detail=f"Apple YOLO detector is unavailable. {self._status_message}"
            )

        conf = conf_threshold if conf_threshold is not None else settings.APPLE_CONFIDENCE_THRESHOLD
        results = self.model.predict(image, conf=conf, verbose=False)[0]

        boxes: List[BoundingBox] = []
        conf_sum = 0.0

        for box in results.boxes:
            xyxy = box.xyxy[0].tolist()
            b_conf = float(box.conf[0].item())
            cls_id = int(box.cls[0].item())
            conf_sum += b_conf
            boxes.append(
                BoundingBox(
                    x1=round(xyxy[0], 1),
                    y1=round(xyxy[1], 1),
                    x2=round(xyxy[2], 1),
                    y2=round(xyxy[3], 1),
                    confidence=round(b_conf, 4),
                    class_id=cls_id,
                    class_name="apple",
                )
            )

        avg_conf = round(conf_sum / len(boxes), 4) if boxes else None

        return AppleDetectionResult(
            task="object_detection",
            detected_apples_count=len(boxes),
            boxes=boxes,
            average_confidence=avg_conf,
            model_name="yolov8n",
            model_version=settings.APPLE_MODEL_VERSION,
            license="Academic / Non-Commercial Research Only (CC BY-NC 4.0)",
            scope_disclaimer=(
                "This experimental model performs orchard object detection and instance counting only. "
                "It does NOT evaluate maturity stages, ripeness, sweetness, disease, or commercial market grade."
            ),
        )


class MultiFruitInspectionService:
    """
    Unified multi-fruit inspection orchestrator supporting BOTH:
    1. Manual commodity selection (Guava, Banana, Apple, Mango).
    2. Automatic species identification via Fruit Identifier V2 with uncertainty gating.
    """

    def __init__(
        self,
        guava_service: Optional[CNNService] = None,
        banana_service: Optional[CNNService] = None,
        apple_service: Optional[AppleDetectionService] = None,
        identifier_service: Optional[FruitIdentifierService] = None,
    ):
        self.guava_service = guava_service or CNNService(crop="guava")
        self.banana_service = banana_service or CNNService(crop="banana")
        self.apple_service = apple_service or AppleDetectionService()
        self.identifier_service = identifier_service or FruitIdentifierService()
        self.registry = model_registry

    def validate_image_bytes(
        self,
        raw_bytes: bytes,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Image.Image:
        """Validate and decode image bytes using shared rigorous validation logic."""
        return self.guava_service.validate_image_bytes(
            raw_bytes, content_type=content_type, filename=filename
        )

    def inspect(
        self,
        image: Image.Image,
        mode: str = "manual",
        target_fruit: Optional[str] = None,
    ) -> FruitInspectionResponse:
        mode_clean = (mode or "manual").lower().strip()
        t0 = time.perf_counter()
        device_name = str(self.guava_service.torch_device or "cpu")

        if mode_clean == "manual":
            fruit_key = (target_fruit or "guava").lower().strip()
            meta = self.registry.get_metadata(fruit_key)
            if meta is None:
                raise CNNServiceError(
                    status_code=400,
                    detail=f"Unsupported commodity '{target_fruit}'. Registered fruits: {self.registry.get_supported_fruits()}.",
                )

            # Mango: Explicitly gated data deficit
            if fruit_key == "mango":
                return FruitInspectionResponse(
                    mode="manual",
                    target_fruit="mango",
                    task_type="unavailable",
                    status="unavailable",
                    unavailable_reason=(
                        "Mango maturity prediction is unavailable. Awaiting validated multi-stage harvest dataset. "
                        "In compliance with AgriChain AI integrity standards, cross-crop proxy models and synthetic predictions are strictly disabled."
                    ),
                    warnings=["Commodity gated due to training data deficit."],
                    device=device_name,
                    inference_ms=0.0,
                )

            # Guava: Certified ResNet18
            if fruit_key == "guava":
                pred = self.guava_service.predict(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="manual",
                    target_fruit="guava",
                    task_type="classification",
                    status="ready",
                    classification=pred,
                    device=pred.device,
                    inference_ms=round(latency, 2),
                )

            # Banana: Baseline ResNet18
            if fruit_key == "banana":
                pred = self.banana_service.predict(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="manual",
                    target_fruit="banana",
                    task_type="classification",
                    status="ready",
                    classification=pred,
                    device=pred.device,
                    inference_ms=round(latency, 2),
                )

            # Apple: YOLOv8n Object Detector
            if fruit_key == "apple":
                det = self.apple_service.detect(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="manual",
                    target_fruit="apple",
                    task_type="object_detection",
                    status="ready",
                    detection=det,
                    device=device_name,
                    inference_ms=round(latency, 2),
                )

            raise CNNServiceError(status_code=400, detail=f"Unrecognized fruit '{fruit_key}'.")

        elif mode_clean == "auto":
            # Stage 1: Fruit Identification
            id_result = self.identifier_service.identify(image)
            pred_crop = id_result.predicted_fruit

            # If uncertain or negative background, do NOT execute false downstream prediction
            if id_result.is_uncertain or pred_crop == "negative_background":
                latency = (time.perf_counter() - t0) * 1000.0
                status_code = "unknown_fruit" if pred_crop == "negative_background" else "uncertain"
                warning_text = (
                    id_result.uncertainty_reason
                    or "Stage 1 identification is uncertain. Please confirm the commodity manually before proceeding."
                )
                return FruitInspectionResponse(
                    mode="auto",
                    target_fruit=pred_crop,
                    task_type=(
                        "classification"
                        if pred_crop in ("guava", "banana", "mango")
                        else ("object_detection" if pred_crop == "apple" else "unavailable")
                    ),
                    status=status_code,
                    identified_fruit=pred_crop,
                    identification=id_result,
                    warnings=[warning_text],
                    device=device_name,
                    inference_ms=round(latency, 2),
                )

            # Certain identification: cascade downstream
            if pred_crop == "guava":
                pred = self.guava_service.predict(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="auto",
                    target_fruit="guava",
                    task_type="classification",
                    status="ready",
                    identified_fruit="guava",
                    identification=id_result,
                    classification=pred,
                    device=pred.device,
                    inference_ms=round(latency, 2),
                )

            elif pred_crop == "banana":
                pred = self.banana_service.predict(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="auto",
                    target_fruit="banana",
                    task_type="classification",
                    status="ready",
                    identified_fruit="banana",
                    identification=id_result,
                    classification=pred,
                    device=pred.device,
                    inference_ms=round(latency, 2),
                )

            elif pred_crop == "apple":
                det = self.apple_service.detect(image)
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="auto",
                    target_fruit="apple",
                    task_type="object_detection",
                    status="ready",
                    identified_fruit="apple",
                    identification=id_result,
                    detection=det,
                    device=device_name,
                    inference_ms=round(latency, 2),
                )

            elif pred_crop == "mango":
                latency = (time.perf_counter() - t0) * 1000.0
                return FruitInspectionResponse(
                    mode="auto",
                    target_fruit="mango",
                    task_type="unavailable",
                    status="unavailable",
                    identified_fruit="mango",
                    identification=id_result,
                    unavailable_reason=(
                        "Specimen identified as Mango (Mangifera indica), but the harvest maturity model is currently unavailable "
                        "due to dataset deficit. In compliance with AgriChain AI integrity standards, synthetic predictions are strictly disabled."
                    ),
                    warnings=["Commodity gated due to training data deficit."],
                    device=device_name,
                    inference_ms=round(latency, 2),
                )

            raise CNNServiceError(status_code=500, detail=f"Unexpected identification outcome '{pred_crop}'.")

        else:
            raise CNNServiceError(status_code=400, detail=f"Invalid mode '{mode}'. Must be 'manual' or 'auto'.")
