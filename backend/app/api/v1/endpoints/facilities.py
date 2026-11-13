"""
AgriChain AI — Storage Facility Management Endpoints
====================================================
Exposes CRUD and query operations for agricultural storage facilities,
godowns, packhouses, cold-storage terminals, and mandis across Punjab and Northern India.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.db.repository import get_shipment_repository
from app.db.session import DatabaseConnectionError
from app.schemas.facility import FacilityCreateRequest, FacilityRecord

router = APIRouter()


@router.get("", summary="List Storage Facilities & Godowns", response_model=List[FacilityRecord])
async def list_facilities(
    facility_type: Optional[str] = Query(None, description="Filter by facility type (packhouse, godown, warehouse, cold_storage, mandi)."),
    district: Optional[str] = Query(None, description="Filter by administrative district (e.g. Fazilka, Bathinda, Hoshiarpur)."),
    state: Optional[str] = Query(None, description="Filter by Indian state (e.g. Punjab, Delhi)."),
    operational_status: Optional[str] = Query(None, description="Filter by operational status (active, maintenance, inactive, full)."),
    verification_status: Optional[str] = Query(None, description="Filter by verification status (verified, partially_verified, unverified)."),
    guava_suitability: Optional[str] = Query(None, description="Filter by guava supply chain suitability (guava_confirmed, horticulture_unconfirmed, ambient_grain, cold_store_unknown, wholesale_market)."),
    q: Optional[str] = Query(None, description="Search term matching facility name, address, village, district, or commodities."),
) -> List[Dict[str, Any]]:
    """
    Returns registered agricultural storage facilities and godowns.
    All facilities include source references, verification status, and verified geographic coordinates.
    """
    try:
        repo = get_shipment_repository()
        return repo.list_facilities(
            facility_type=facility_type,
            district=district,
            state=state,
            operational_status=operational_status,
            verification_status=verification_status,
            guava_suitability_category=guava_suitability,
            q=q,
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{facility_id}", summary="Get Storage Facility Details", response_model=FacilityRecord)
async def get_facility(facility_id: str) -> Dict[str, Any]:
    """Retrieves a single storage facility or godown by its unique identifier."""
    try:
        repo = get_shipment_repository()
        facility = repo.get_facility(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Storage facility '{facility_id}' not found.",
            )
        return facility
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{facility_id}/suitability", summary="Validate Facility Guava Supply-Chain Suitability")
async def get_facility_suitability(
    facility_id: str,
    operation: Optional[str] = Query(None, description="Intended operation: packhouse_cooling, cold_storage, market_auction, transit_hub, harvesting_aggregation."),
    crop: str = Query("guava", description="Target crop (Default: guava)."),
) -> Dict[str, Any]:
    """
    Evaluates facility readiness and suitability with strict truthfulness per Phase 13 requirements.
    Distinguishes guava trading, guava handling, guava cold chain, and current operational availability.
    """
    try:
        repo = get_shipment_repository()
        facility = repo.get_facility(facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Storage facility '{facility_id}' not found.",
            )
        return repo.evaluate_facility_suitability(facility_id, operation=operation, crop=crop)
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.post("", summary="Register Storage Facility", status_code=status.HTTP_201_CREATED, response_model=FacilityRecord)
async def create_facility(payload: FacilityCreateRequest) -> Dict[str, Any]:
    """
    Registers a new storage facility or godown with strict Indian geographic boundary validation.
    """
    try:
        repo = get_shipment_repository()
        return repo.create_facility(payload.model_dump())
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
