"""
AgriChain AI — Marketplace & Demo Orders Endpoints
===================================================
Provides B2B produce lot catalog and demo order placement.
Strictly verifies available stock, computes pricing server-side,
and transparently identifies all transactions as demo simulations.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.repository import ShipmentRepository, get_shipment_repository
from app.db.session import InsufficientStockError, ListingNotFoundError
from app.schemas.order import CreateOrderRequest, OrderResponse, ProduceListingResponse

logger = logging.getLogger("agrichain.api.orders")
router = APIRouter()


@router.get(
    "/listings",
    response_model=List[ProduceListingResponse],
    summary="Get Marketplace Produce Listings",
    description="List available verified produce lots for B2B buyers.",
)
async def list_marketplace_listings(
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> List[ProduceListingResponse]:
    listings = repo.get_marketplace_listings()
    return [ProduceListingResponse(**item) for item in listings]


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Demo Purchase Order",
    description=(
        "Places a demo order for a verified produce lot. Validates available stock, "
        "calculates total price strictly server-side, and records order in persistent storage."
    ),
)
async def create_demo_order(
    payload: CreateOrderRequest,
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> OrderResponse:
    try:
        order_dict = repo.create_order(payload.model_dump())
        return OrderResponse(**order_dict)
    except ListingNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Failed to process demo order: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order processing failed: {exc}",
        )


@router.get(
    "",
    response_model=List[OrderResponse],
    summary="List Recorded Demo Orders",
    description="Retrieve recorded purchase orders, optionally filtered by buyer name.",
)
async def list_demo_orders(
    buyer_name: Optional[str] = Query(None, description="Filter orders by buyer name"),
    repo: ShipmentRepository = Depends(get_shipment_repository),
) -> List[OrderResponse]:
    orders = repo.get_orders(buyer_name=buyer_name)
    return [OrderResponse(**item) for item in orders]
