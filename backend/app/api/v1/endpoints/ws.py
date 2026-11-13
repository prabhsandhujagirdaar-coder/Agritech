"""
AgriChain AI — WebSocket Real-Time Gateway
===========================================
Provides real-time event streaming for shipment lifecycle transitions,
cold-chain sensor telemetry updates, and geospatial waypoint tracking.
Supports keepalive ping/pong across container networks and proxies.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Dict, List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("agrichain.ws")
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts real-time events."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total clients: %d", len(self.active_connections))

    async def broadcast(self, event: str, data: Dict[str, Any]) -> None:
        """Broadcast an event payload to all connected WebSocket clients."""
        if not self.active_connections:
            return

        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        text_message = json.dumps(payload)
        dead_connections: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_message)
            except Exception as exc:
                logger.warning("Error broadcasting to client (%s), queuing for removal", exc)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


# Global singleton ConnectionManager
_global_ws_manager: ConnectionManager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return _global_ws_manager


@router.websocket("/ws/shipments")
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint accepting telemetry consumers, web dashboards, and mobile clients.
    Supports keep-alive ping/pong frames and initial greeting.
    """
    manager = get_ws_manager()
    await manager.connect(websocket)

    try:
        # Send initial connection handshake
        await websocket.send_json({
            "event": "connected",
            "message": "AgriChain AI WebSocket Stream Active",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        while True:
            # Await client messages (e.g. heartbeat pings)
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                msg_type = data.get("type", "").lower()
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})
            except json.JSONDecodeError:
                if message.strip().lower() == "ping":
                    await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("Unhandled WebSocket exception: %s", exc)
        manager.disconnect(websocket)
