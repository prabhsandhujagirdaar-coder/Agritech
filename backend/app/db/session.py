"""
AgriChain AI — Database Session & Connection Management
=======================================================
Safely manages PostgreSQL / PostGIS database connections using credentials
provided via environment variables (DATABASE_URL / SYNC_DATABASE_URL).
"""

from __future__ import annotations

import logging
import os
import socket
from typing import Tuple
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger("agrichain.db")


class DatabaseConnectionError(Exception):
    """Raised when PostgreSQL/PostGIS connectivity is required but fails."""
    pass


class ShipmentNotFoundError(Exception):
    """Raised when a queried shipment does not exist."""
    pass


class ForeignKeyViolationError(Exception):
    """Raised when a foreign key constraint is violated (e.g. telemetry on unknown shipment)."""
    pass


class ListingNotFoundError(Exception):
    """Raised when a queried marketplace produce listing is not found."""
    pass


class InsufficientStockError(Exception):
    """Raised when an order quantity exceeds available stock."""
    pass


def get_sync_database_url() -> str:
    """Retrieve synchronous PostgreSQL URL from environment or configuration."""
    raw = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or settings.SYNC_DATABASE_URL
    if raw.startswith("postgresql+asyncpg://"):
        raw = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw


def get_async_database_url() -> str:
    """Retrieve asynchronous PostgreSQL URL from environment or configuration."""
    raw = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    return raw


def probe_database_connection(timeout_seconds: float = 2.0) -> Tuple[bool, str]:
    """
    Probes whether the configured PostgreSQL host and port are reachable.
    Does not require external database drivers to perform connection testing.
    """
    db_url = get_sync_database_url()
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
    except Exception as exc:
        return False, f"Invalid database URL format: {exc}"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout_seconds)
    try:
        res = s.connect_ex((host, port))
        if res == 0:
            return True, f"PostgreSQL port {port} on '{host}' is reachable."
        return False, f"PostgreSQL port {port} on '{host}' is unreachable (code {res})."
    except Exception as exc:
        return False, f"Socket error reaching '{host}:{port}': {exc}"
    finally:
        s.close()
