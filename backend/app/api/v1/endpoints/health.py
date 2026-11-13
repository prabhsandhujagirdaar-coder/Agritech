"""
AgriChain AI - Root Health & Liveness Endpoints
===============================================
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from app.core.config import settings
from app.db.session import probe_database_connection

router = APIRouter()


@router.get(
    "/health",
    summary="Application Health Probe",
    description="Returns backend liveness status, database connectivity, and active crop focus.",
)
async def system_health(request: Request) -> dict:
    service = getattr(request.app.state, "cnn_service", None)
    service_status = service.get_status() if service else None

    if settings.DATABASE_ENABLED:
        is_db_up, db_msg = probe_database_connection(timeout_seconds=1.5)
        db_status = {
            "enabled": True,
            "connected": is_db_up,
            "message": db_msg,
        }
    else:
        db_status = {
            "enabled": False,
            "connected": None,
            "message": "File-based ledger persistence active.",
        }

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "target_crop": settings.TARGET_CROP,
        "cnn_ready": service_status.model_available if service_status else False,
        "device": service_status.device if service_status else settings.MODEL_DEVICE,
        "database": db_status,
    }
