"""
AgriChain AI — Database Model Declarations
==========================================
PostgreSQL / PostGIS entity models for shipments, telemetry logs, and spatial waypoints.
Compatible with SQLAlchemy ORM when available, and standard dataclasses for universal execution.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ShipmentModel:
    """Relational entity representing a produce shipment batch."""
    id: str
    produce_type: str = "Guava"
    produce: str = "Guava"
    origin: str = ""
    destination: str = ""
    quantity: float = 0.0
    quantity_crates: int = 0
    status: str = "created"
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    risk_index: float = 0.0
    origin_facility_id: Optional[str] = None
    destination_facility_id: Optional[str] = None
    intermediate_facility_id: Optional[str] = None
    origin_operation: Optional[str] = None
    destination_operation: Optional[str] = None
    intermediate_operation: Optional[str] = None
    planned_departure: Optional[str] = None
    actual_departure: Optional[str] = None
    planned_arrival: Optional[str] = None
    actual_arrival: Optional[str] = None
    tracking_mode: str = "simulated"
    telemetry_mode: str = "simulated"
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    last_update: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "produce_type": self.produce_type,
            "produce": self.produce,
            "origin": self.origin,
            "destination": self.destination,
            "status": self.status,
            "quantity": float(self.quantity),
            "quantity_crates": int(self.quantity_crates),
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "risk_index": float(self.risk_index),
            "origin_facility_id": self.origin_facility_id,
            "destination_facility_id": self.destination_facility_id,
            "intermediate_facility_id": self.intermediate_facility_id,
            "origin_operation": self.origin_operation,
            "destination_operation": self.destination_operation,
            "intermediate_operation": self.intermediate_operation,
            "planned_departure": self.planned_departure,
            "actual_departure": self.actual_departure,
            "planned_arrival": self.planned_arrival,
            "actual_arrival": self.actual_arrival,
            "tracking_mode": self.tracking_mode,
            "telemetry_mode": self.telemetry_mode,
            "created_at": self.created_at,
            "last_update": self.last_update,
        }


@dataclass
class ShipmentEventModel:
    """Relational entity representing an auditable shipment tracking or facility event."""
    id: str
    shipment_id: str
    event_type: str
    description: str
    facility_id: Optional[str] = None
    source: str = "system_event"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "event_type": self.event_type,
            "description": self.description,
            "facility_id": self.facility_id,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class TelemetryLogModel:
    """Relational entity representing a single cold-chain sensor log reading."""
    id: str
    shipment_id: str
    temperature: float
    humidity: float
    sensor_id: str = "SNS-COLD-01"
    location: str = ""
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "temperature": float(self.temperature),
            "humidity": float(self.humidity),
            "sensor_id": self.sensor_id,
            "location": self.location,
            "timestamp": self.timestamp,
        }


@dataclass
class GeoWaypointModel:
    """
    Spatial entity representing a GPS route waypoint (Point SRID 4326).
    Only populated with verified geographic coordinates; never fabricated from free text.
    """
    id: str
    shipment_id: str
    longitude: float
    latitude: float
    srid: int = 4326
    altitude_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    location_metadata: Dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "longitude": float(self.longitude),
            "latitude": float(self.latitude),
            "srid": self.srid,
            "altitude_m": self.altitude_m,
            "speed_kmh": self.speed_kmh,
            "heading_deg": self.heading_deg,
            "location_metadata": self.location_metadata,
            "recorded_at": self.recorded_at,
        }
