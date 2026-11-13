"""
AgriChain AI - FastAPI Application
===================================
Main application entry point for the AgriChain AI platform.
Exposes Guava quality inspection, cold-chain telemetry risk analysis,
and geospatial shipment tracking.

Maintains 100% backwards compatibility with legacy /predict and /health roots
while exposing the structured /api/v1 architecture.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.api.v1.endpoints.cnn import (
    inspect_fruit_produce,
    predict_guava_quality,
    predict_kinnow_quality,
)
from app.core.config import settings
from app.schemas.cnn import CNNPredictionResponse, FruitInspectionResponse
from app.services.cnn_service import CNNService, CNNServiceError, MultiFruitInspectionService

logger = logging.getLogger("agrichain.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    Initializes CNNService once at startup on application state.
    """
    logger.info("Initializing AgriChain AI Backend services...")
    cnn_service = CNNService()
    app.state.cnn_service = cnn_service

    multi_fruit_service = MultiFruitInspectionService(guava_service=cnn_service)
    app.state.multi_fruit_service = multi_fruit_service

    status_obj = cnn_service.get_status()
    logger.info(
        "CNN Inspection Service initialized: crop='%s', available=%s, device=%s",
        status_obj.target_crop,
        status_obj.model_available,
        status_obj.device,
    )
    if not status_obj.model_available:
        logger.warning(
            "CNN Guava Model Status: %s. Rejection of uncertified or proxy models is active.",
            status_obj.message,
        )

    try:
        yield
    finally:
        logger.info("Releasing backend service resources...")
        app.state.cnn_service = None
        app.state.multi_fruit_service = None


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AgriChain AI Backend Platform — AI-Powered Guava Quality Inspection "
        "& Cold-Chain Management Platform for Punjab, India."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(CNNServiceError)
async def cnn_service_exception_handler(request: Request, exc: CNNServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ---------------------------------------------------------------------------
# Versioned API Router (/api/v1) & Next.js Proxy Compatibility Routes
# ---------------------------------------------------------------------------
from app.api.v1.endpoints import facilities, inventory, orders, shipments, simulations, telemetry, ws
from app.db.session import probe_database_connection

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(facilities.router, prefix="/api/facilities", tags=["Facilities Proxy Compatibility"])
app.include_router(shipments.router, prefix="/api/shipments", tags=["Shipments Proxy Compatibility"])
app.include_router(simulations.router, prefix="/api/simulations", tags=["Simulations Proxy Compatibility"])
app.include_router(telemetry.router, prefix="/api/telemetry", tags=["Telemetry Proxy Compatibility"])
app.include_router(telemetry.router, prefix="/api/v1/lstm", tags=["LSTM Contract Parity"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders Proxy Compatibility"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory Proxy Compatibility"])
app.include_router(ws.router, tags=["WebSocket Real-Time Gateway"])


# ---------------------------------------------------------------------------
# Root Compatibility Routes (Legacy Next.js Proxy & Direct Client Support)
# ---------------------------------------------------------------------------
@app.get("/health", summary="Root Health Probe", tags=["Compatibility"])
async def root_health(request: Request) -> dict:
    service: CNNService = getattr(request.app.state, "cnn_service", None)
    if service is None:
        return {"status": "unavailable", "api_status": "offline", "message": "Service uninitialized."}

    stat = service.get_status()

    if settings.DATABASE_ENABLED:
        is_db_up, db_msg = probe_database_connection(timeout_seconds=1.5)
        db_status = {"enabled": True, "connected": is_db_up, "message": db_msg}
    else:
        db_status = {"enabled": False, "connected": None, "message": "File-based ledger persistence active."}

    return {
        "status": "healthy",
        "api_status": "online",
        "target_crop": stat.target_crop,
        "model": stat.model_name,
        "model_version": stat.model_version,
        "device": stat.device,
        "model_available": stat.model_available,
        "model_status": "ready" if stat.model_available else "unavailable",
        "message": stat.message,
        "database": db_status,
    }


@app.post(
    "/predict",
    response_model=CNNPredictionResponse,
    summary="Root Predict Alias",
    tags=["Compatibility"],
    responses={
        400: {"description": "Invalid image payload or corrupted byte stream."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Guava model unavailable or awaiting certified checkpoint."},
    },
)
async def root_predict(
    request: Request,
    file: UploadFile = File(..., description="Image file of the Guava fruit."),
) -> CNNPredictionResponse:
    """Root alias delegating to the unified CNN prediction handler."""
    return await predict_guava_quality(request=request, file=file)


@app.post(
    "/inspect",
    response_model=FruitInspectionResponse,
    summary="Root Inspect Alias",
    tags=["Compatibility"],
    responses={
        400: {"description": "Invalid image payload or corrupted byte stream."},
        415: {"description": "Unsupported media type (accepts JPEG, PNG, WEBP)."},
        422: {"description": "Missing file upload parameter."},
        503: {"description": "Model unavailable."},
    },
)
async def root_inspect(
    request: Request,
    file: UploadFile = File(..., description="Image file of produce specimen."),
    mode: str = "manual",
    fruit: str = "guava",
) -> FruitInspectionResponse:
    """Root alias delegating to the unified multi-fruit inspection endpoint."""
    return await inspect_fruit_produce(request=request, file=file, mode=mode, fruit=fruit)
