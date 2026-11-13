"""
AgriChain AI - CNN Quality Prediction & Status Endpoints
========================================================
Versioned REST endpoints for Kinnow Mandarin image quality classification.
Enforces rigorous validation on uploaded payloads and handles missing model
checkpoints with explicit HTTP 503 errors without fabricating results.
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.schemas.cnn import (
    CNNModelStatusResponse,
    CNNPredictionResponse,
    FruitIdentificationResult,
    FruitInspectionResponse,
    MultiFruitRegistryStatusResponse,
)
from app.services.cnn_service import (
    CNNService,
    CNNServiceError,
    FruitIdentifierService,
    InvalidImageError,
    ModelUnavailableError,
    MultiFruitInspectionService,
    UnsupportedMediaTypeError,
)

logger = logging.getLogger("agrichain.api.cnn")
router = APIRouter()


def get_cnn_service(request: Request, crop: Optional[str] = None) -> CNNService:
    """Retrieve the initialized CNNService instance from application state."""
    if isinstance(crop, str) and crop.lower() == "banana":
        service: Optional[CNNService] = getattr(request.app.state, "banana_service", None)
        if service is None:
            service = CNNService(crop="banana")
            request.app.state.banana_service = service
        return service

    service: Optional[CNNService] = getattr(request.app.state, "cnn_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CNN inspection service has not been initialized on the application state.",
        )
    return service


def get_multi_fruit_service(request: Request) -> MultiFruitInspectionService:
    """Retrieve or initialize the MultiFruitInspectionService instance."""
    service: Optional[MultiFruitInspectionService] = getattr(request.app.state, "multi_fruit_service", None)
    if service is None:
        cnn_srv = getattr(request.app.state, "cnn_service", None) or CNNService(crop="guava")
        banana_srv = getattr(request.app.state, "banana_service", None) or CNNService(crop="banana")
        service = MultiFruitInspectionService(guava_service=cnn_srv, banana_service=banana_srv)
        request.app.state.multi_fruit_service = service
    return service


def get_identifier_service(request: Request) -> FruitIdentifierService:
    """Retrieve or initialize Stage 1 Fruit Identifier Service."""
    multi_service = get_multi_fruit_service(request)
    return multi_service.identifier_service


@router.get(
    "/status",
    response_model=CNNModelStatusResponse,
    summary="Get CNN Model Status & Guava Readiness",
    description="Inspect whether a certified Guava checkpoint is actively loaded.",
)
async def get_status(request: Request) -> CNNModelStatusResponse:
    service = get_cnn_service(request)
    return service.get_status()


@router.get(
    "/status/banana",
    response_model=CNNModelStatusResponse,
    summary="Get Banana CNN Model Status & Readiness",
    description="Inspect whether the Banana ResNet18 baseline checkpoint is loaded in isolation.",
)
async def get_banana_status(request: Request) -> CNNModelStatusResponse:
    service = get_cnn_service(request, crop="banana")
    return service.get_status()


@router.get(
    "/health",
    summary="CNN Module Health Check",
    description="Lightweight health probe reporting device and model availability.",
)
async def cnn_health(request: Request) -> dict:
    service = get_cnn_service(request)
    stat = service.get_status()
    return {
        "status": "healthy" if stat.model_available else "unavailable",
        "target_crop": stat.target_crop,
        "model": stat.model_name,
        "model_version": stat.model_version,
        "device": stat.device,
        "model_available": stat.model_available,
        "message": stat.message,
    }


@router.get(
    "/registry",
    response_model=MultiFruitRegistryStatusResponse,
    summary="Get Multi-Fruit Model Registry Status",
    description="Inspect supported fruit commodities, checkpoint validation states, and readiness.",
)
async def get_multi_fruit_registry(request: Request) -> MultiFruitRegistryStatusResponse:
    from app.services.model_registry import model_registry
    return MultiFruitRegistryStatusResponse(**model_registry.get_full_registry_status())


@router.post(
    "/predict",
    response_model=CNNPredictionResponse,
    responses={
        400: {"description": "Invalid image payload or corrupted byte stream."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Produce model unavailable or awaiting certified checkpoint."},
    },
    summary="Predict Produce Quality / Ripeness",
    description=(
        "Upload a produce image for quality classification. "
        "Returns verified softmax distribution and quality grade. "
        "Returns HTTP 503 if no validated model artifact is present."
    ),
)
async def predict_guava_quality(
    request: Request,
    file: UploadFile = File(..., description="Image file of the produce specimen (JPEG/PNG/WEBP)."),
    crop: Optional[str] = None,
) -> CNNPredictionResponse:
    # 1. Validate file part is present
    if file is None or file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded.",
        )

    # 2. Read file bytes
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        logger.exception("Error reading uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content.",
        )

    # 3. Process through Service Layer
    service = get_cnn_service(request, crop=crop)
    try:
        image = service.validate_image_bytes(
            raw_bytes=raw_bytes,
            content_type=file.content_type,
            filename=file.filename,
        )
        return service.predict(image)

    except CNNServiceError as cnn_err:
        raise HTTPException(
            status_code=cnn_err.status_code,
            detail=cnn_err.detail,
        )
    except Exception as exc:
        logger.exception("Unhandled error during prediction: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected failure during produce quality evaluation.",
        )


@router.post(
    "/predict/banana",
    response_model=CNNPredictionResponse,
    responses={
        400: {"description": "Invalid image payload or corrupted byte stream."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Banana model unavailable or checkpoint missing."},
    },
    summary="Predict Banana Ripeness (Isolated Baseline Path)",
    description=(
        "Upload a Banana image for 4-class ripeness evaluation (Unripe, Half_Ripe, Ripe, Overripe). "
        "Provides isolated inference path for Phase 14F benchmarking without mutating production registry."
    ),
)
async def predict_banana_quality(
    request: Request,
    file: UploadFile = File(..., description="Image file of the Banana specimen (JPEG/PNG/WEBP)."),
) -> CNNPredictionResponse:
    return await predict_guava_quality(request, file=file, crop="banana")


# Backward-compatible alias for existing tests and routes
predict_kinnow_quality = predict_guava_quality


@router.post(
    "/inspect",
    response_model=FruitInspectionResponse,
    responses={
        400: {"description": "Invalid image payload, unsupported file format, or invalid parameters."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Produce model unavailable or checkpoint missing."},
    },
    summary="Unified Multi-Fruit Inspection (Dual-Mode)",
    description=(
        "Unified produce inspection endpoint supporting BOTH:\n"
        "1. Manual Fruit Selection across 4 commodities: Guava, Banana, Apple, and Mango.\n"
        "2. Automatic Fruit Identification via Stage 1 MobileNetV3-Large with uncertainty fallback.\n\n"
        "Guarantees:\n"
        "- Guava: 3-stage harvest maturity (Green, Mature Green, Ripe).\n"
        "- Banana: 4-stage peel ripeness (Unripe, Half_Ripe, Ripe, Overripe).\n"
        "- Apple: YOLOv8n object detection (bounding boxes & apple count; research CC BY-NC 4.0; no fake maturity).\n"
        "- Mango: Honest gated state (returns data deficit explanation; zero fake predictions)."
    ),
)
async def inspect_fruit_produce(
    request: Request,
    file: UploadFile = File(..., description="Image file of the produce specimen (JPEG/PNG/WEBP)."),
    mode: str = Query("manual", pattern="^(manual|auto)$", description="Inspection mode ('manual' | 'auto')."),
    fruit: Optional[str] = Query(None, description="Target commodity for manual mode ('guava', 'banana', 'apple', 'mango')."),
) -> FruitInspectionResponse:
    # 1. Validate file part is present
    if file is None or file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded.",
        )

    # 2. Read file bytes
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        logger.exception("Error reading uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content.",
        )

    # 3. Process through unified MultiFruitInspectionService
    service = get_multi_fruit_service(request)
    try:
        image = service.validate_image_bytes(
            raw_bytes=raw_bytes,
            content_type=file.content_type,
            filename=file.filename,
        )
        return service.inspect(image=image, mode=mode, target_fruit=fruit)

    except CNNServiceError as cnn_err:
        raise HTTPException(
            status_code=cnn_err.status_code,
            detail=cnn_err.detail,
        )
    except Exception as exc:
        logger.exception("Unhandled error during multi-fruit inspection: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected failure during produce inspection: {exc}",
        )


@router.post(
    "/identify",
    response_model=FruitIdentificationResult,
    responses={
        400: {"description": "Invalid image payload or corrupted byte stream."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Stage 1 fruit identifier model unavailable."},
    },
    summary="Stage 1 Fruit Species Identification",
    description=(
        "Standalone species classifier evaluating produce among Guava, Banana, Apple, Mango, "
        "or Non-Fruit / Canopy. Returns top predicted class, confidence, softmax distribution, "
        "and uncertainty flags."
    ),
)
async def identify_fruit_species(
    request: Request,
    file: UploadFile = File(..., description="Image file to identify (JPEG/PNG/WEBP)."),
) -> FruitIdentificationResult:
    # 1. Validate file part is present
    if file is None or file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded.",
        )

    # 2. Read file bytes
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        logger.exception("Error reading uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content.",
        )

    # 3. Process through Stage 1 FruitIdentifierService
    multi_service = get_multi_fruit_service(request)
    try:
        image = multi_service.validate_image_bytes(
            raw_bytes=raw_bytes,
            content_type=file.content_type,
            filename=file.filename,
        )
        return multi_service.identifier_service.identify(image)

    except CNNServiceError as cnn_err:
        raise HTTPException(
            status_code=cnn_err.status_code,
            detail=cnn_err.detail,
        )
    except Exception as exc:
        logger.exception("Unhandled error during fruit identification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected failure during fruit identification: {exc}",
        )
