"""
AgriChain AI — Shipment Pydantic Schemas
========================================
Defines strongly-typed request and response contracts for produce shipment lifecycles,
including PostGIS coordinates, facility associations, suitability validation,
and auditable event logging.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    CREATED = "created"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    QUARANTINED = "quarantined"


class FacilityOperationType(str, Enum):
    HARVESTING_AGGREGATION = "harvesting_aggregation"
    PACKHOUSE_COOLING = "packhouse_cooling"
    COLD_STORAGE = "cold_storage"
    MARKET_AUCTION = "market_auction"
    TRANSIT_HUB = "transit_hub"


class TrackingMode(str, Enum):
    LIVE_GPS = "live_gps"
    SIMULATED = "simulated"
    DISCONNECTED_LAST_KNOWN = "disconnected_last_known"


class TelemetryMode(str, Enum):
    LIVE_SENSOR = "live_sensor"
    SIMULATED = "simulated"
    UNAVAILABLE = "unavailable"


class TrackingEventType(str, Enum):
    SHIPMENT_CREATED = "shipment_created"
    FACILITY_ASSOCIATION_UPDATED = "facility_association_updated"
    SHIPMENT_DISPATCHED = "shipment_dispatched"
    IN_TRANSIT = "in_transit"
    ARRIVAL_RECORDED = "arrival_recorded"
    FACILITY_HANDOVER = "facility_handover"
    DELIVERY_COMPLETED = "delivery_completed"
    TRACKING_CONNECTION_LOST = "tracking_connection_lost"
    SENSOR_THRESHOLD_ALERT = "sensor_threshold_alert"


class CreateShipmentRequest(BaseModel):
    produce_type: str = Field(default="Guava", description="Target crop or produce type (Default: Guava).")
    origin: str = Field(..., min_length=2, max_length=255, description="Origin packhouse, godown, or farm.")
    destination: str = Field(..., min_length=2, max_length=255, description="Destination mandi, warehouse, or cold hub.")
    quantity: float = Field(..., ge=0.0, description="Volume in standard units or kilograms.")
    status: ShipmentStatus = Field(default=ShipmentStatus.CREATED, description="Initial lifecycle status.")
    origin_facility_id: Optional[str] = Field(default=None, description="Optional foreign key referencing origin storage_facilities(id).")
    destination_facility_id: Optional[str] = Field(default=None, description="Optional foreign key referencing destination storage_facilities(id).")
    intermediate_facility_id: Optional[str] = Field(default=None, description="Optional intermediate transit hub or pre-cooling station.")
    origin_operation: Optional[str] = Field(default=None, description="Operation at origin (e.g. harvesting_aggregation, packhouse_cooling).")
    destination_operation: Optional[str] = Field(default=None, description="Operation at destination (e.g. market_auction, cold_storage).")
    intermediate_operation: Optional[str] = Field(default=None, description="Operation at intermediate hub (e.g. transit_hub, inspection).")
    planned_departure: Optional[str] = Field(default=None, description="Planned departure timestamp ISO 8601.")
    actual_departure: Optional[str] = Field(default=None, description="Actual departure timestamp ISO 8601.")
    planned_arrival: Optional[str] = Field(default=None, description="Planned arrival timestamp ISO 8601.")
    actual_arrival: Optional[str] = Field(default=None, description="Actual arrival timestamp ISO 8601.")
    tracking_mode: Optional[str] = Field(default="simulated", description="Location telemetry source: live_gps, simulated, or disconnected_last_known.")
    telemetry_mode: Optional[str] = Field(default="simulated", description="Atmospheric sensor stream source: live_sensor, simulated, or unavailable.")
    quality_grade: Optional[str] = Field(default=None, description="Verified AI harvest maturity / ripeness grade.")
    inspection_verdict: Optional[Dict[str, Any]] = Field(default=None, description="Detailed AI inspection result.")


class ShipmentRecord(BaseModel):
    id: str = Field(..., description="Unique shipment identifier (e.g. SHP-2026-001).")
    produce_type: str = Field(..., description="Target crop (e.g. Guava).")
    produce: str = Field(..., description="Backwards compatibility alias for produce_type.")
    origin: str = Field(..., description="Origin location.")
    destination: str = Field(..., description="Destination location.")
    status: str = Field(..., description="Shipment lifecycle status.")
    quantity: float = Field(..., description="Total volume / units.")
    quantity_crates: int = Field(..., description="Standardized crate count.")
    temperature_c: Optional[float] = Field(default=None, description="Latest cold-chain temperature reading (°C).")
    humidity_pct: Optional[float] = Field(default=None, description="Latest relative humidity (%).")
    risk_index: float = Field(default=0.0, description="Cold-chain spoilage risk index (0.0 - 100.0).")
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
    last_update: str = Field(..., description="ISO 8601 last update timestamp.")
    current_coordinates: Optional[Dict[str, float]] = Field(default=None, description="Latest verified GPS coordinates {latitude, longitude}.")
    latest_waypoint: Optional[Dict[str, Any]] = Field(default=None, description="Latest PostGIS waypoint record.")
    origin_facility_id: Optional[str] = Field(default=None, description="Linked origin facility identifier.")
    destination_facility_id: Optional[str] = Field(default=None, description="Linked destination facility identifier.")
    intermediate_facility_id: Optional[str] = Field(default=None, description="Linked intermediate facility identifier.")
    origin_facility: Optional[Dict[str, Any]] = Field(default=None, description="Enriched origin facility summary.")
    destination_facility: Optional[Dict[str, Any]] = Field(default=None, description="Enriched destination facility summary.")
    intermediate_facility: Optional[Dict[str, Any]] = Field(default=None, description="Enriched intermediate facility summary.")
    origin_operation: Optional[str] = Field(default=None, description="Operation at origin facility.")
    destination_operation: Optional[str] = Field(default=None, description="Operation at destination facility.")
    intermediate_operation: Optional[str] = Field(default=None, description="Operation at intermediate facility.")
    planned_departure: Optional[str] = Field(default=None, description="Planned departure timestamp.")
    actual_departure: Optional[str] = Field(default=None, description="Actual departure timestamp.")
    planned_arrival: Optional[str] = Field(default=None, description="Planned arrival timestamp.")
    actual_arrival: Optional[str] = Field(default=None, description="Actual arrival timestamp.")
    tracking_mode: str = Field(default="simulated", description="Location telemetry source (live_gps, simulated, disconnected_last_known).")
    telemetry_mode: str = Field(default="simulated", description="Cold-chain sensor telemetry source (live_sensor, simulated, unavailable).")
    suitability_warnings: List[str] = Field(default_factory=list, description="Truthful warnings if any facility operation is unverified or unsuitable.")
    origin_suitability: Optional[Dict[str, Any]] = Field(default=None, description="Detailed suitability assessment for origin facility.")
    destination_suitability: Optional[Dict[str, Any]] = Field(default=None, description="Detailed suitability assessment for destination facility.")
    intermediate_suitability: Optional[Dict[str, Any]] = Field(default=None, description="Detailed suitability assessment for intermediate facility.")
    events_count: int = Field(default=0, description="Total number of logged lifecycle tracking events.")
    quality_grade: Optional[str] = Field(default=None, description="Associated AI produce quality / ripeness grade.")
    inspection_verdict: Optional[Dict[str, Any]] = Field(default=None, description="Detailed produce inspection result payload.")


class ShipmentEventRecord(BaseModel):
    id: str = Field(..., description="Unique event identifier (e.g. EVT-SHP-2026-001-1).")
    shipment_id: str = Field(..., description="Referenced shipment identifier.")
    event_type: str = Field(..., description="Lifecycle event type.")
    description: str = Field(..., description="Truthful human-readable event description.")
    facility_id: Optional[str] = Field(default=None, description="Referenced facility identifier if event occurred at a facility.")
    facility_name: Optional[str] = Field(default=None, description="Referenced facility name.")
    source: str = Field(default="system_event", description="Event source: system_event, manual_operator, demo_simulated, sensor_gateway.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured event metadata.")
    timestamp: str = Field(..., description="ISO 8601 event timestamp.")


class CreateShipmentEventRequest(BaseModel):
    event_type: str = Field(..., description="Lifecycle event type.")
    description: str = Field(..., min_length=2, max_length=500, description="Event description.")
    facility_id: Optional[str] = Field(default=None, description="Optional referenced facility identifier.")
    source: str = Field(default="manual_operator", description="Event origin source.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata.")


class FacilitySuitabilityResponse(BaseModel):
    facility_id: str
    facility_name: str
    operation: str
    crop: str = "guava"
    suitable: bool
    suitability_status: str
    capabilities: Dict[str, Any]
    warnings: List[str]
    evidence_summary: str
    source_citation: Optional[Dict[str, Any]] = None
