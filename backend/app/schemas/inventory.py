"""
AgriChain AI — Farmer Stock & Inventory Management Schemas
==========================================================
Defines validation schemas for produce inventory, marketplace crop catalogue,
and server-authoritative stock value computation.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


SUPPORTED_MARKETPLACE_CROPS: Dict[str, Dict[str, Any]] = {
    "guava": {
        "crop_id": "guava",
        "name": "Guava",
        "scientific_name": "Psidium guajava L.",
        "primary_variety": "Allahabad Safeda / Shweta",
        "ai_classification_available": True,
        "ai_task": "classification",
        "ai_model": "ResNet18 v2.0.0",
        "description": "3-stage harvest intake maturity taxonomy (Green, Mature Green, Ripe).",
    },
    "banana": {
        "crop_id": "banana",
        "name": "Banana",
        "scientific_name": "Musa acuminata / balbisiana",
        "primary_variety": "Grand Naine (G9)",
        "ai_classification_available": True,
        "ai_task": "classification",
        "ai_model": "ResNet18 v1.0.0",
        "description": "4-stage degreening and ripeness classification.",
    },
    "apple": {
        "crop_id": "apple",
        "name": "Apple",
        "scientific_name": "Malus domestica Borkh.",
        "primary_variety": "Royal Delicious / Shimla",
        "ai_classification_available": False,
        "ai_task": "detection_only",
        "ai_model": "YOLOv8n (CC BY-NC 4.0)",
        "description": "In-orchard detection under CC BY-NC 4.0; harvest maturity classification unavailable.",
    },
    "mango": {
        "crop_id": "mango",
        "name": "Mango",
        "scientific_name": "Mangifera indica L.",
        "primary_variety": "Chaunsa / Dasheri",
        "ai_classification_available": False,
        "ai_task": "unavailable",
        "ai_model": None,
        "description": "Commercial marketplace trading supported; AI harvest classification explicitly unavailable.",
    },
    "kinnow": {
        "crop_id": "kinnow",
        "name": "Kinnow Mandarin",
        "scientific_name": "Citrus nobilis x C. deliciosa",
        "primary_variety": "Punjab Regional Citrus",
        "ai_classification_available": False,
        "ai_task": "unavailable",
        "ai_model": None,
        "description": "Abohar & Fazilka citrus belt staple; commercial listing supported without active AI model.",
    },
}

ALLOWED_STOCK_STATUSES = ("available", "reserved", "sold", "unavailable")


class CropCatalogueItem(BaseModel):
    """Metadata specification for a supported marketplace crop."""
    crop_id: str
    name: str
    scientific_name: str
    primary_variety: str
    ai_classification_available: bool
    ai_task: str
    ai_model: Optional[str] = None
    description: str


class CreateInventoryRequest(BaseModel):
    """Payload to create a new farmer stock record."""
    farmer_id: str = Field(default="FARMER-PB-001", min_length=2, max_length=64, description="ID of the listing farmer.")
    crop_type: str = Field(..., description="Target crop key (e.g. guava, banana, apple, mango, kinnow).")
    crate_quantity: int = Field(..., gt=0, description="Available crates of produce (must be a positive integer).")
    price_per_crate: float = Field(..., gt=0.0, description="Price per crate in INR (must be positive).")
    description: Optional[str] = Field(default=None, max_length=500, description="Optional produce batch description.")
    harvest_date: Optional[str] = Field(default=None, description="ISO or date string of harvest.")
    location: Optional[str] = Field(default="Abohar Orchard Gate, Punjab", max_length=200, description="Farm or packhouse storage location.")
    status: str = Field(default="available", description="Stock availability status.")

    @field_validator("crop_type")
    @classmethod
    def validate_crop_type(cls, v: str) -> str:
        key = v.lower().strip()
        if key not in SUPPORTED_MARKETPLACE_CROPS:
            supported = ", ".join(SUPPORTED_MARKETPLACE_CROPS.keys())
            raise ValueError(f"Crop '{v}' is not supported. Supported marketplace crops: {supported}")
        return key

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        val = v.lower().strip()
        if val not in ALLOWED_STOCK_STATUSES:
            allowed = ", ".join(ALLOWED_STOCK_STATUSES)
            raise ValueError(f"Status '{v}' is invalid. Allowed statuses: {allowed}")
        return val


class UpdateInventoryRequest(BaseModel):
    """Payload to update an existing farmer stock record."""
    crate_quantity: Optional[int] = Field(default=None, gt=0, description="Updated crate quantity.")
    price_per_crate: Optional[float] = Field(default=None, gt=0.0, description="Updated price per crate in INR.")
    description: Optional[str] = Field(default=None, max_length=500)
    harvest_date: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        val = v.lower().strip()
        if val not in ALLOWED_STOCK_STATUSES:
            allowed = ", ".join(ALLOWED_STOCK_STATUSES)
            raise ValueError(f"Status '{v}' is invalid. Allowed statuses: {allowed}")
        return val


class InventoryItemResponse(BaseModel):
    """Authoritative farmer inventory item record."""
    id: str = Field(..., description="Unique inventory stock identifier (e.g. STK-2026-0001).")
    farmer_id: str = Field(..., description="Farmer identity owning this stock.")
    crop_type: str = Field(..., description="Crop identifier.")
    crop_name: str = Field(..., description="Common display name of crop.")
    scientific_name: str = Field(..., description="Scientific binomial name.")
    crate_quantity: int = Field(..., description="Available crates.")
    price_per_crate: float = Field(..., description="Unit price per crate in INR.")
    total_stock_value: float = Field(..., description="Authoritative total value = crate_quantity * price_per_crate.")
    description: Optional[str] = None
    harvest_date: Optional[str] = None
    location: str
    status: str
    ai_classification_available: bool = Field(..., description="Whether real AI classification is active for this crop.")
    ai_task: str = Field(..., description="AI inspection capability tier.")
    created_at: str
    updated_at: str

