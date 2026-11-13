"""
AgriChain AI — Dynamic Real-Road Vehicle Simulation Schemas
============================================================
Defines Pydantic models for location search/geocoding, OSRM route previews,
authoritative simulation sessions, telemetry, and control commands.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LocationSearchQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=150, description="Location search query (mandi, city, village, facility).")
    limit: int = Field(default=8, ge=1, le=25, description="Maximum number of location results to return.")


class LocationSearchResult(BaseModel):
    display_name: str = Field(..., description="Human-readable location title including district and state.")
    name: str = Field(..., description="Short name of facility, mandi, or city.")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude.")
    type: str = Field(default="facility", description="Location type (facility, mandi, city, landmark).")
    state: Optional[str] = Field(default="Punjab", description="State or territory.")
    source: str = Field(default="verified_seed", description="Origin of record: verified_seed, osm_nominatim, or facility_repo.")


class RoutePreviewRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90.0, le=90.0, description="Origin WGS84 Latitude.")
    origin_lon: float = Field(..., ge=-180.0, le=180.0, description="Origin WGS84 Longitude.")
    destination_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination WGS84 Latitude.")
    destination_lon: float = Field(..., ge=-180.0, le=180.0, description="Destination WGS84 Longitude.")
    origin_name: Optional[str] = Field(default="Origin Point", description="Display name for origin.")
    destination_name: Optional[str] = Field(default="Destination Point", description="Display name for destination.")


class RoutePreviewResponse(BaseModel):
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    distance_km: float = Field(..., description="Total road distance in kilometers.")
    duration_s: float = Field(..., description="Estimated travel duration in seconds under normal conditions.")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON LineString geometry with road coordinates [[lon, lat], ...].")
    routing_source: str = Field(..., description="Source of route geometry: 'osrm_driving' or 'fallback_corridor'.")
    waypoint_count: int = Field(..., description="Total coordinate points along the road polyline.")


class CreateSimulationRequest(BaseModel):
    shipment_id: Optional[str] = Field(default=None, description="Optional existing shipment to associate with.")
    route_identifier: Optional[str] = Field(default=None, description="Optional canonical route identifier or fingerprint.")
    origin_name: str = Field(..., description="Source address or landmark.")
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lon: float = Field(..., ge=-180.0, le=180.0)
    destination_name: str = Field(..., description="Destination address or landmark.")
    destination_lat: float = Field(..., ge=-90.0, le=90.0)
    destination_lon: float = Field(..., ge=-180.0, le=180.0)
    total_distance_km: Optional[float] = Field(default=None, ge=0.0, description="Authoritative total road distance in kilometers.")
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=20.0, description="Simulation speed factor (e.g. 1.0, 2.0, 5.0).")
    scenario: str = Field(default="normal", description="Cold-chain simulation scenario: normal, temperature_excursion, delay, high_humidity.")
    route_geometry: Optional[Dict[str, Any]] = Field(default=None, description="Optional pre-calculated route GeoJSON.")


class SimulationControlRequest(BaseModel):
    action: str = Field(..., description="Action: start, pause, resume, stop, reset, step.")
    speed_multiplier: Optional[float] = Field(default=None, ge=0.1, le=20.0, description="Updated speed factor.")
    scenario: Optional[str] = Field(default=None, description="Updated cold-chain condition scenario.")


class SimulationTelemetryPoint(BaseModel):
    id: str
    simulation_id: str
    shipment_id: Optional[str] = None
    sequence_step: int
    latitude: float
    longitude: float
    heading_deg: float = 0.0
    speed_kmh: float = 0.0
    distance_travelled_km: float = 0.0
    distance_remaining_km: float = 0.0
    temperature_c: float
    humidity_pct: float
    delay_minutes: int = 0
    risk_score: float = 0.0
    predicted_arrival_risk: float = 0.0
    alert: bool = False
    scenario: str = "normal"
    data_source: str = "simulation"
    sensor_id: str = "SNS-SIM-DEMO"
    timestamp: str


class SimulationSessionResponse(BaseModel):
    id: str
    shipment_id: Optional[str] = None
    route_identifier: Optional[str] = None
    origin_name: str
    origin_lat: float
    origin_lon: float
    destination_name: str
    destination_lat: float
    destination_lon: float
    route_geojson: Dict[str, Any]
    total_distance_km: float
    estimated_duration_s: float
    current_distance_km: float
    current_lat: float
    current_lon: float
    current_heading_deg: float
    current_speed_kmh: float
    speed_multiplier: float
    status: str
    scenario: str
    step_count: int
    latest_telemetry: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

