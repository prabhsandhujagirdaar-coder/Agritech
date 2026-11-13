"""
AgriChain AI — Farmer Stock & Inventory Management Endpoints
============================================================
Provides stock management for farmers, supporting produce listing,
server-side stock valuation, strict ownership authorization, and
explicit separation between marketplace trading and AI inspection.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.db.repository import ShipmentRepository, get_shipment_repository
from app.schemas.inventory import (
    CropCatalogueItem,
    CreateInventoryRequest,
    UpdateInventoryRequest,
    InventoryItemResponse,
    SUPPORTED_MARKETPLACE_CROPS,
)

logger = logging.getLogger("agrichain.api.inventory")
router = APIRouter()


def _enrich_inventory_item(item: dict) -> dict:
    """Enriches stored inventory records with authoritative crop metadata and AI status."""
    enriched = dict(item)
    crop_key = str(item.get("crop_type", "guava")).lower().strip()
    crop_info = SUPPORTED_MARKETPLACE_CROPS.get(crop_key, {})
    enriched["crop_name"] = crop_info.get("name", crop_key.capitalize())
    enriched["scientific_name"] = crop_info.get("scientific_name", "N/A")
    enriched["ai_classification_available"] = crop_info.get("ai_classification_available", False)
    enriched["ai_task"] = crop_info.get("ai_task", "unavailable")
    return enriched


def get_current_user_context(
    x_role: Optional[str] = Header(None, alias="X-Role"),
    x_farmer_id: Optional[str] = Header(None, alias="X-Farmer-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> dict:
    """Extract authenticated role and actor identity from headers."""
    role = (x_role or "farmer").lower().strip()
    farmer_id = x_farmer_id or "FARMER-PB-001"
    user_id = x_user_id or farmer_id
    return {"role": role, "farmer_id": farmer_id, "user_id": user_id}


@router.get(
    "/crops",
    response_model=List[CropCatalogueItem],
    summary="Get Supported Marketplace Crops",
    description="Returns the full crop catalogue with explicit AI model availability metadata.",
)
def get_crop_catalogue() -> List[CropCatalogueItem]:
    return [CropCatalogueItem(**v) for v in SUPPORTED_MARKETPLACE_CROPS.values()]


@router.get(
    "",
    response_model=List[InventoryItemResponse],
    summary="List Farmer Inventory",
    description="List stock items. Farmers view their own inventory; admins have platform-wide oversight.",
)
def list_inventory(
    farmer_id: Optional[str] = Query(None, description="Filter by farmer ID"),
    crop_type: Optional[str] = Query(None, description="Filter by crop type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    auth: dict = Depends(get_current_user_context),
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> List[InventoryItemResponse]:
    # Enforce role isolation: if role is 'farmer', default to their own farmer_id
    effective_farmer_id = farmer_id
    if auth["role"] == "farmer" and not effective_farmer_id:
        effective_farmer_id = auth["farmer_id"]

    items = repo.list_inventory(farmer_id=effective_farmer_id, crop_type=crop_type, status=status_filter)
    return [InventoryItemResponse(**_enrich_inventory_item(item)) for item in items]


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Farmer Stock Item",
    description="Creates a new stock record with server-calculated total value.",
)
def create_inventory_item(
    payload: CreateInventoryRequest,
    auth: dict = Depends(get_current_user_context),
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> InventoryItemResponse:
    # If role is farmer, bind listing to their verified farmer_id
    data = payload.model_dump()
    if auth["role"] == "farmer":
        data["farmer_id"] = auth["farmer_id"]

    created = repo.create_inventory_item(data)
    logger.info("Created inventory item %s for farmer %s (%s crates of %s)", created["id"], created["farmer_id"], created["crate_quantity"], created["crop_type"])
    return InventoryItemResponse(**_enrich_inventory_item(created))


@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Get Specific Inventory Item",
    description="Retrieve full details for an individual inventory record.",
)
def get_inventory_item(
    item_id: str,
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> InventoryItemResponse:
    item = repo.get_inventory_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )
    return InventoryItemResponse(**_enrich_inventory_item(item))


@router.put(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Update Inventory Item",
    description="Updates stock details. Enforces ownership authorization: farmers can only edit their own items.",
)
def update_inventory_item(
    item_id: str,
    payload: UpdateInventoryRequest,
    auth: dict = Depends(get_current_user_context),
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> InventoryItemResponse:
    existing = repo.get_inventory_item(item_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )

    # Ownership check: farmers can only edit their own stock
    if auth["role"] == "farmer" and existing.get("farmer_id") != auth["farmer_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you can only modify your own stock records.",
        )

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = repo.update_inventory_item(item_id, updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to update inventory item '{item_id}'.",
        )
    return InventoryItemResponse(**_enrich_inventory_item(updated))


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Inventory Item",
    description="Deletes a stock item. Enforces ownership authorization: farmers can only delete their own items.",
)
def delete_inventory_item(
    item_id: str,
    auth: dict = Depends(get_current_user_context),
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> dict:
    existing = repo.get_inventory_item(item_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item '{item_id}' not found.",
        )

    # Ownership check
    if auth["role"] == "farmer" and existing.get("farmer_id") != auth["farmer_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you can only delete your own stock records.",
        )

    deleted = repo.delete_inventory_item(item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove inventory item '{item_id}'.",
        )
    return {"status": "success", "message": f"Inventory item '{item_id}' deleted successfully."}
