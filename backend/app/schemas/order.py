"""
AgriChain AI — Marketplace & Demo Orders Schemas
=================================================
Pydantic schemas for buyer marketplace produce listings, demo order submissions,
server-side price validation, and order history auditing.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProduceListingResponse(BaseModel):
    """Authoritative produce lot listing in the B2B marketplace."""
    id: str = Field(..., description="Unique listing identifier (e.g. LST-GUA-001).")
    title: str = Field(..., description="Display title for the produce lot.")
    variety: str = Field(default="Guava (Psidium guajava)", description="Guava variety/cultivar.")
    crop: str = Field(default="guava", description="Target agricultural crop.")
    ripeness_stage: str = Field(..., description="Maturity/ripeness classification stage (e.g. 'Ripe', 'Mature Green', 'Green').")
    ai_verified: bool = Field(default=True, description="Whether batch was evaluated with real neural network inference.")
    softmax_score: float = Field(..., description="Softmax confidence output score (uncalibrated heuristic score, not a safety certification).")
    origin_facility_id: Optional[str] = Field(None, description="Origin warehouse or packhouse facility ID.")
    origin_name: str = Field(..., description="Origin location name.")
    available_crates: int = Field(..., ge=0, description="Available inventory stock in crates.")
    crate_weight_kg: float = Field(default=20.0, description="Nominal weight per crate in kilograms.")
    price_per_crate_inr: float = Field(..., gt=0.0, description="Authoritative wholesale price per crate in INR (₹).")
    image_url: str = Field(..., description="Produce batch visual preview URL.")
    notes: Optional[str] = Field(None, description="Harvest and intake notes.")


class CreateOrderRequest(BaseModel):
    """
    Demo order submission payload.
    Total price is strictly calculated server-side from authoritative listing data.
    Client-submitted totals or prices are discarded to prevent client tampering.
    """
    listing_id: str = Field(..., description="ID of the listing being ordered.")
    quantity_crates: int = Field(..., gt=0, description="Number of crates to order (must be <= available stock).")
    buyer_name: str = Field(default="Demo Buyer", min_length=2, max_length=100, description="Name of purchasing buyer.")
    buyer_organization: Optional[str] = Field(default="Punjab Agro Traders", max_length=150, description="Buyer organization or firm.")
    shipping_destination: str = Field(default="Azadpur Mandi, Delhi", min_length=3, max_length=200, description="Destination warehouse or terminal.")
    contact_phone: Optional[str] = Field(default=None, description="Contact phone for shipment coordination.")
    idempotency_key: Optional[str] = Field(default=None, description="Client-provided idempotency token to prevent duplicate submissions.")


class OrderResponse(BaseModel):
    """Confirmed demo order record."""
    id: str = Field(..., description="Order confirmation reference ID (e.g. ORD-2026-0042).")
    listing_id: str = Field(..., description="Reference to the ordered marketplace listing.")
    produce_title: str = Field(..., description="Title of the ordered produce lot.")
    variety: str = Field(..., description="Guava cultivar/variety.")
    ripeness_stage: str = Field(..., description="Ripeness classification.")
    quantity_crates: int = Field(..., description="Confirmed quantity in crates.")
    total_weight_kg: float = Field(..., description="Total weight in kg.")
    unit_price_inr: float = Field(..., description="Authoritative unit price per crate in INR.")
    total_price_inr: float = Field(..., description="Server-computed total order price in INR.")
    currency: str = Field(default="INR", description="Currency code.")
    buyer_name: str = Field(..., description="Purchaser name.")
    buyer_organization: Optional[str] = Field(None, description="Purchaser firm.")
    shipping_destination: str = Field(..., description="Delivery location.")
    status: str = Field(default="confirmed", description="Order status ('confirmed', 'processing', 'dispatched').")
    is_demo_order: bool = Field(default=True, description="Explicit flag indicating simulated demo transaction.")
    simulation_notice: str = Field(
        default="DEMO WORKFLOW SIMULATION — No real payment processed and no legal financial obligation created.",
        description="Legal and commercial transparency disclaimer.",
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
