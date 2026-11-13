"""
AgriChain AI — Telemetry & Geospatial Waypoints Schemas
=======================================================
Defines schemas for cold-chain sensor streams, transit risk evaluation,
and PostGIS geospatial waypoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AddTelemetryRequest(BaseModel):
    temperature: float = Field(..., description="Cold-chain temperature reading (°C).")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage (%).")
    sensor_id: str = Field(default="SNS-COLD-01", description="Telemetry sensor hardware identifier.")
    location: str = Field(default="", description="Free-text or landmark description of current location.")


class TelemetryRecord(BaseModel):
    id: str = Field(..., description="Unique telemetry reading identifier.")
    shipment_id: str = Field(..., description="Foreign key referencing the parent shipment ID.")
    temperature: float = Field(..., description="Temperature (°C).")
    humidity: float = Field(..., description="Humidity (%).")
    sensor_id: str = Field(..., description="Sensor hardware identifier.")
    location: str = Field(default="", description="Free-text location.")
    timestamp: str = Field(..., description="ISO 8601 recorded timestamp.")


class GeoWaypointCreate(BaseModel):
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude.")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude.")
    altitude_m: Optional[float] = Field(default=None, description="Altitude in meters above sea level.")
    speed_kmh: Optional[float] = Field(default=None, ge=0.0, description="Vehicle ground speed (km/h).")
    heading_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Compass heading in degrees.")
    location_metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary corridor metadata.")


class GeoWaypointRecord(BaseModel):
    id: str = Field(..., description="Unique waypoint identifier.")
    shipment_id: str = Field(..., description="Foreign key referencing the parent shipment ID.")
    longitude: float = Field(..., description="Longitude (ST_X).")
    latitude: float = Field(..., description="Latitude (ST_Y).")
    srid: int = Field(default=4326, description="Spatial reference system identifier (WGS84).")
    altitude_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    location_metadata: Dict[str, Any] = Field(default_factory=dict)
    recorded_at: str = Field(..., description="ISO 8601 recorded timestamp.")


class TelemetryPoint(BaseModel):
    hour: int = 0
    temperature: float = Field(..., description="Cold-chain temperature reading (°C).")
    humidity: float = Field(default=85.0, description="Relative humidity percentage (%).")
    delay_minutes: int = Field(default=0, description="Transit delay duration in minutes.")
    speed_kmh: float = Field(default=50.0, description="Transit speed in km/h.")
    distance_remaining_km: float = Field(default=0.0, description="Remaining distance in km.")


class LSTMPredictionRequest(BaseModel):
    shipment_id: str
    sequence: List[TelemetryPoint]


class LSTMPredictionResponse(BaseModel):
    shipment_id: str
    current_risk: float
    predicted_arrival_risk: float
    alert: bool
    inference_ms: float
