"""
AgriChain AI - API v1 Router Aggregator
=======================================
Combines all v1 endpoint routers.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import cnn, facilities, health, inventory, orders, shipments, simulations, telemetry, ws

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(cnn.router, prefix="/cnn", tags=["CNN Guava Quality"])
api_router.include_router(facilities.router, prefix="/facilities", tags=["Storage Facilities & Godowns"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["Shipments"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry & LSTM Risk"])
api_router.include_router(orders.router, prefix="/orders", tags=["Marketplace & Orders"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Farmer Stock & Inventory"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["Dynamic Vehicle Simulation"])
api_router.include_router(ws.router, tags=["WebSocket Real-Time Gateway"])
