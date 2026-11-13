"""
AgriChain AI — Shipment Management Endpoints
============================================
Preserves shipment lifecycle, PostGIS geospatial route references, and intake records.
Satisfies the API contracts invoked by Next.js /api/shipments and ShipmentsTracking component.
Persisted via ShipmentRepository with PostgreSQL / PostGIS migration support.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.api.v1.endpoints.ws import get_ws_manager
from app.core.geo import validate_indian_coordinate, is_within_india
from app.db.repository import get_shipment_repository
from app.db.session import DatabaseConnectionError, ShipmentNotFoundError
from app.schemas.shipment import CreateShipmentEventRequest, CreateShipmentRequest
from app.schemas.telemetry import AddTelemetryRequest, GeoWaypointCreate
from app.services.geocoding_service import get_geocoding_service
from app.services.routing_service import get_routing_service

router = APIRouter()


class _StoreProxyList(list):
    """Backwards compatibility proxy for SHIPMENTS_STORE."""
    def __iter__(self):
        return iter(get_shipment_repository().list_shipments())

    def __len__(self):
        return len(get_shipment_repository().list_shipments())

    def __getitem__(self, item):
        return get_shipment_repository().list_shipments()[item]


class _StoreProxyDict(dict):
    """Backwards compatibility proxy for TELEMETRY_STORE."""
    def values(self):
        repo = get_shipment_repository()
        return [repo.get_telemetry(s["id"]) for s in repo.list_shipments()]

    def get(self, k, default=None):
        repo = get_shipment_repository()
        res = repo.get_telemetry(k)
        return res if res else (default or [])


# Module-level backwards-compatibility proxies
SHIPMENTS_STORE = _StoreProxyList()
TELEMETRY_STORE = _StoreProxyDict()


@router.get("", summary="List Shipments")
async def list_shipments() -> List[Dict[str, Any]]:
    try:
        repo = get_shipment_repository()
        return repo.list_shipments()
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create Shipment")
async def create_shipment(payload: CreateShipmentRequest) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        record = repo.create_shipment(payload.model_dump())
        try:
            await get_ws_manager().broadcast("shipment_created", record)
        except Exception:
            pass
        return record
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}", summary="Get Shipment by ID")
async def get_shipment(shipment_id: str) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        shp = repo.get_shipment(shipment_id)
        if shp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment '{shipment_id}' not found.",
            )
        return shp
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}/route", summary="Get Dynamic Real-Road Route for Selected Shipment")
def get_shipment_route(shipment_id: str) -> Dict[str, Any]:
    """
    Computes dynamic, real-road highway routing geometry and distance for a specific shipment.
    Origin and destination coordinates are authoritatively resolved from facility references,
    direct shipment coordinates, or geocoding of origin/destination locations.
    Never reuses stale corridors or static hardcoded coordinates.
    """
    try:
        repo = get_shipment_repository()
        shp = repo.get_shipment(shipment_id)
        if shp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment '{shipment_id}' not found.",
            )

        origin_name = shp.get("origin") or "Origin"
        dest_name = shp.get("destination") or "Destination"
        o_lat = shp.get("origin_lat")
        o_lon = shp.get("origin_lon")
        d_lat = shp.get("destination_lat")
        d_lon = shp.get("destination_lon")

        # 1. Resolve Origin coordinates from facility
        if o_lat is None or o_lon is None:
            o_fac = shp.get("origin_facility")
            if not o_fac and shp.get("origin_facility_id"):
                o_fac = repo.get_facility(shp.get("origin_facility_id"))
            if o_fac and o_fac.get("latitude") is not None and o_fac.get("longitude") is not None:
                o_lat = float(o_fac["latitude"])
                o_lon = float(o_fac["longitude"])
                if not origin_name or origin_name == "Origin":
                    origin_name = o_fac.get("name", origin_name)

        # 2. Resolve Destination coordinates from facility
        if d_lat is None or d_lon is None:
            d_fac = shp.get("destination_facility")
            if not d_fac and shp.get("destination_facility_id"):
                d_fac = repo.get_facility(shp.get("destination_facility_id"))
            if d_fac and d_fac.get("latitude") is not None and d_fac.get("longitude") is not None:
                d_lat = float(d_fac["latitude"])
                d_lon = float(d_fac["longitude"])
                if not dest_name or dest_name == "Destination":
                    dest_name = d_fac.get("name", dest_name)

        # 3. Geocode fallback if coordinates still missing
        geo = get_geocoding_service()
        if (o_lat is None or o_lon is None) and origin_name:
            res = geo.geocode_location(origin_name)
            if res:
                o_lat = float(res["latitude"])
                o_lon = float(res["longitude"])
                if res.get("name") and origin_name == "Origin":
                    origin_name = res["name"]

        if (d_lat is None or d_lon is None) and dest_name:
            res = geo.geocode_location(dest_name)
            if res:
                d_lat = float(res["latitude"])
                d_lon = float(res["longitude"])
                if res.get("name") and dest_name == "Destination":
                    dest_name = res["name"]

        if o_lat is None or o_lon is None or d_lat is None or d_lon is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to resolve valid geographic coordinates for shipment '{shipment_id}' (Origin: '{origin_name}', Destination: '{dest_name}').",
            )

        validate_indian_coordinate(o_lat, o_lon, "origin")
        validate_indian_coordinate(d_lat, d_lon, "destination")

        routing = get_routing_service()
        route_data = routing.get_route(o_lat, o_lon, d_lat, d_lon)

        return {
            "shipment_id": shipment_id,
            "origin_name": origin_name,
            "destination_name": dest_name,
            "origin": {
                "latitude": round(o_lat, 6),
                "longitude": round(o_lon, 6),
            },
            "destination": {
                "latitude": round(d_lat, 6),
                "longitude": round(d_lon, 6),
            },
            "geometry": route_data.get("geometry", {}),
            "distance_km": route_data.get("distance_km", 0.0),
            "duration_s": route_data.get("duration_s", 0.0),
            "routing_source": route_data.get("routing_source", "road_network"),
            "waypoint_count": route_data.get("waypoint_count", len(route_data.get("geometry", {}).get("coordinates", []))),
        }
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Routing service error: {exc}",
        )


@router.patch("/{shipment_id}", summary="Update Shipment Status / Properties")
async def update_shipment_status(shipment_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        updated = repo.update_shipment_status(shipment_id, updates)
        try:
            await get_ws_manager().broadcast("shipment_update", updated)
        except Exception:
            pass
        return updated
    except ShipmentNotFoundError as not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}/risk", summary="Get Shipment Cold-Chain Spoilage Risk")
async def get_shipment_risk(shipment_id: str) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        shp = repo.get_shipment(shipment_id)
        if shp is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment '{shipment_id}' not found.",
            )
        telemetry_list = repo.get_telemetry(shipment_id, limit=50)
        temps = [float(t["temperature"]) for t in telemetry_list if "temperature" in t]
        avg_temp = sum(temps) / len(temps) if temps else float(shp.get("temperature_c") or 6.5)
        excursion_count = sum(1 for t in temps if t > 8.0 or t < 4.0)
        base_risk = min(100.0, max(5.0, (avg_temp - 5.0) * 8.0 + excursion_count * 6.5))
        predicted_arrival_risk = min(100.0, base_risk * 1.15)
        return {
            "shipment_id": shipment_id,
            "current_risk": round(base_risk, 1),
            "predicted_arrival_risk": round(predicted_arrival_risk, 1),
            "alert": predicted_arrival_risk > 50.0,
            "telemetry_points_evaluated": len(temps),
            "avg_temperature_c": round(avg_temp, 2),
            "excursion_events": excursion_count,
        }
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}/telemetry", summary="Get Shipment Telemetry Sequence")
async def get_shipment_telemetry(
    shipment_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    try:
        repo = get_shipment_repository()
        return repo.get_telemetry(shipment_id, skip=skip, limit=limit)
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.post(
    "/{shipment_id}/telemetry",
    status_code=status.HTTP_201_CREATED,
    summary="Add Telemetry Reading",
)
async def add_shipment_telemetry(
    shipment_id: str,
    payload: AddTelemetryRequest,
) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        reading = repo.add_telemetry(shipment_id, payload.model_dump())
        try:
            await get_ws_manager().broadcast("telemetry_update", reading)
            # Recompute and broadcast risk update for live dashboard gauges
            telemetry_list = repo.get_telemetry(shipment_id, limit=50)
            temps = [float(t["temperature"]) for t in telemetry_list if "temperature" in t]
            shp = repo.get_shipment(shipment_id)
            avg_temp = sum(temps) / len(temps) if temps else float((shp or {}).get("temperature_c") or 6.5)
            excursion_count = sum(1 for t in temps if t > 8.0 or t < 4.0)
            base_risk = min(100.0, max(5.0, (avg_temp - 5.0) * 8.0 + excursion_count * 6.5))
            predicted_arrival_risk = min(100.0, base_risk * 1.15)
            risk_payload = {
                "shipment_id": shipment_id,
                "current_risk": round(base_risk, 1),
                "predicted_arrival_risk": round(predicted_arrival_risk, 1),
                "alert": predicted_arrival_risk > 50.0,
                "telemetry_points_evaluated": len(temps),
                "avg_temperature_c": round(avg_temp, 2),
                "excursion_events": excursion_count,
            }
            await get_ws_manager().broadcast("risk_update", risk_payload)
        except Exception:
            pass
        return reading
    except ShipmentNotFoundError as not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}/waypoints", summary="Get Geospatial Waypoints (PostGIS SRID 4326)")
async def get_shipment_waypoints(shipment_id: str) -> List[Dict[str, Any]]:
    try:
        repo = get_shipment_repository()
        if not repo.get_shipment(shipment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment '{shipment_id}' not found.",
            )
        return repo.get_waypoints(shipment_id)
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.post(
    "/{shipment_id}/waypoints",
    status_code=status.HTTP_201_CREATED,
    summary="Add Geospatial Waypoint (PostGIS SRID 4326)",
)
async def add_shipment_waypoint(
    shipment_id: str,
    payload: GeoWaypointCreate,
) -> Dict[str, Any]:
    try:
        repo = get_shipment_repository()
        waypoint = repo.add_waypoint(shipment_id, payload.model_dump())
        try:
            await get_ws_manager().broadcast("waypoint_update", waypoint)
            location_payload = {
                "shipment_id": shipment_id,
                "latitude": waypoint["latitude"],
                "longitude": waypoint["longitude"],
                "speed_kmh": waypoint.get("speed_kmh"),
                "heading_deg": waypoint.get("heading_deg"),
                "altitude_m": waypoint.get("altitude_m"),
                "location_metadata": waypoint.get("location_metadata", {}),
                "recorded_at": waypoint["recorded_at"],
            }
            await get_ws_manager().broadcast("location_update", location_payload)
        except Exception:
            pass
        return waypoint
    except ShipmentNotFoundError as not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.get("/{shipment_id}/events", summary="Get Auditable Shipment Lifecycle Events Timeline")
async def get_shipment_events(shipment_id: str) -> List[Dict[str, Any]]:
    """
    Returns the verified chronological timeline of lifecycle events for a shipment,
    including creations, dispatches, facility handovers, and alerts.
    """
    try:
        repo = get_shipment_repository()
        return repo.get_shipment_events(shipment_id)
    except ShipmentNotFoundError as not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@router.post(
    "/{shipment_id}/events",
    status_code=status.HTTP_201_CREATED,
    summary="Record Auditable Shipment Lifecycle Event",
)
async def add_shipment_event(
    shipment_id: str,
    payload: CreateShipmentEventRequest,
) -> Dict[str, Any]:
    """
    Records an auditable lifecycle or facility association event with duplicate prevention.
    """
    try:
        repo = get_shipment_repository()
        event = repo.add_shipment_event(shipment_id, payload.model_dump())
        try:
            await get_ws_manager().broadcast("event_update", event)
        except Exception:
            pass
        return event
    except ShipmentNotFoundError as not_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment '{shipment_id}' not found.",
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


# Corridor definitions for demo/simulated movement testing
_DEMO_CORRIDORS: Dict[str, List[Dict[str, Any]]] = {
    "SHP-2026-001": [
        {"lat": 30.1453, "lon": 74.1994, "name": "Abohar Packhouse", "speed": 45.0, "heading": 85.0},
        {"lat": 30.1915, "lon": 74.4989, "name": "Malout Corridor", "speed": 62.0, "heading": 78.0},
        {"lat": 30.2110, "lon": 74.9455, "name": "Bathinda Transit Hub", "speed": 58.0, "heading": 110.0},
        {"lat": 29.5349, "lon": 75.0298, "name": "Sirsa Checkpoint (NH-9)", "speed": 64.0, "heading": 135.0},
        {"lat": 29.5144, "lon": 75.4549, "name": "Fatehabad Corridor", "speed": 60.0, "heading": 125.0},
        {"lat": 29.1492, "lon": 75.7217, "name": "Hisar Logistics Hub", "speed": 55.0, "heading": 130.0},
        {"lat": 28.8955, "lon": 76.6066, "name": "Rohtak Bypass", "speed": 65.0, "heading": 115.0},
        {"lat": 28.6924, "lon": 76.9240, "name": "Bahadurgarh Toll", "speed": 48.0, "heading": 100.0},
        {"lat": 28.7161, "lon": 77.1772, "name": "Azadpur APMC Mandi, Delhi", "speed": 20.0, "heading": 80.0},
    ],
    "SHP-2026-002": [
        {"lat": 30.4037, "lon": 74.0254, "name": "Fazilka CA Cold Store", "speed": 45.0, "heading": 75.0},
        {"lat": 30.4744, "lon": 74.5167, "name": "Muktsar Corridor", "speed": 60.0, "heading": 68.0},
        {"lat": 30.5828, "lon": 74.8267, "name": "Kotkapura Bypass", "speed": 56.0, "heading": 62.0},
        {"lat": 30.8165, "lon": 75.1715, "name": "Moga Agri Terminal", "speed": 58.0, "heading": 55.0},
        {"lat": 30.7850, "lon": 75.4780, "name": "Jagraon Highway", "speed": 60.0, "heading": 65.0},
        {"lat": 30.9010, "lon": 75.8573, "name": "Ludhiana Agro Cold Chain", "speed": 35.0, "heading": 70.0},
    ],
    "SHP-2026-003": [
        {"lat": 30.4037, "lon": 74.0254, "name": "Fazilka CA Cold Store", "speed": 45.0, "heading": 35.0},
        {"lat": 30.9237, "lon": 74.6133, "name": "Firozpur Corridor", "speed": 65.0, "heading": 25.0},
        {"lat": 31.0667, "lon": 74.9833, "name": "Zira Checkpoint", "speed": 55.0, "heading": 30.0},
        {"lat": 31.1500, "lon": 74.9600, "name": "Harike Barrage", "speed": 40.0, "heading": 15.0},
        {"lat": 31.4520, "lon": 74.9250, "name": "Tarn Taran Bypass", "speed": 58.0, "heading": 10.0},
        {"lat": 31.6340, "lon": 74.8723, "name": "Amritsar Mandi Terminal", "speed": 0.0, "heading": 0.0},
    ],
}


@router.post(
    "/{shipment_id}/simulate-step",
    summary="Advance Simulated Movement Checkpoint (Opt-in Demo Mode)",
    tags=["Simulation & Demo"],
)
async def simulate_shipment_step(shipment_id: str) -> Dict[str, Any]:
    """
    Opt-in demo movement simulator for environments without physical vehicle GPS transponders.
    Records a clearly-marked 'demo_simulated' waypoint fix, cold-chain telemetry reading, and audit event.
    Updates PostGIS location, recalculates risk, and broadcasts to connected WebSocket clients.
    """
    try:
        repo = get_shipment_repository()
        shp = repo.get_shipment(shipment_id)
        if not shp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shipment '{shipment_id}' not found.",
            )

        existing_wps = repo.get_waypoints(shipment_id)
        corridor = _DEMO_CORRIDORS.get(shipment_id)

        if corridor:
            next_idx = len(existing_wps) % len(corridor)
            next_pt = corridor[next_idx]
            lat = next_pt["lat"]
            lon = next_pt["lon"]
            name = next_pt["name"]
            speed = next_pt["speed"]
            heading = next_pt["heading"]
        else:
            # Interpolate between origin and destination coordinates
            o_fac = shp.get("origin_facility")
            d_fac = shp.get("destination_facility")
            o_lat = o_fac["latitude"] if o_fac else 30.1453
            o_lon = o_fac["longitude"] if o_fac else 74.1994
            d_lat = d_fac["latitude"] if d_fac else 28.7161
            d_lon = d_fac["longitude"] if d_fac else 77.1772

            progress = min(1.0, ((len(existing_wps) + 1) * 0.15) % 1.05)
            lat = round(o_lat + (d_lat - o_lat) * progress, 4)
            lon = round(o_lon + (d_lon - o_lon) * progress, 4)
            name = f"Corridor Step {len(existing_wps) + 1}"
            speed = 52.0 if progress < 1.0 else 0.0
            heading = 85.0

        # 1. Record simulated waypoint with strict demo labelling
        waypoint_payload = {
            "latitude": lat,
            "longitude": lon,
            "altitude_m": 195.0,
            "speed_kmh": speed,
            "heading_deg": heading,
            "location_metadata": {
                "source": "demo_simulated",
                "simulated": True,
                "checkpoint": name,
                "label": "DEMO_SIMULATED_TRANSIT_FIX",
            },
        }
        waypoint = repo.add_waypoint(shipment_id, waypoint_payload)

        # 2. Record simulated cold-chain telemetry
        temp = round(5.8 + (len(existing_wps) % 5) * 0.3, 1)
        humidity = round(86.5 + (len(existing_wps) % 3) * 0.5, 1)
        telemetry_payload = {
            "temperature": temp,
            "humidity": humidity,
            "sensor_id": "SNS-SIM-DEMO",
            "location": f"{name} (Simulated Demo)",
        }
        telemetry = repo.add_telemetry(shipment_id, telemetry_payload)

        # 3. Record auditable simulation event
        event_payload = {
            "event_type": "in_transit",
            "description": f"Simulated transit fix recorded at {name} (Demo Mode).",
            "source": "demo_simulated",
            "metadata": {
                "checkpoint": name,
                "speed_kmh": speed,
                "latitude": lat,
                "longitude": lon,
                "simulated": True,
            },
        }
        event = repo.add_shipment_event(shipment_id, event_payload)

        # 4. Broadcast updates over WebSocket
        try:
            await get_ws_manager().broadcast("waypoint_update", waypoint)
            await get_ws_manager().broadcast("telemetry_update", telemetry)
            await get_ws_manager().broadcast("event_update", event)
            await get_ws_manager().broadcast("location_update", {
                "shipment_id": shipment_id,
                "latitude": lat,
                "longitude": lon,
                "speed_kmh": speed,
                "heading_deg": heading,
                "recorded_at": waypoint["recorded_at"],
                "simulated": True,
            })
        except Exception:
            pass

        return {
            "status": "success",
            "simulated": True,
            "shipment_id": shipment_id,
            "waypoint": waypoint,
            "telemetry": telemetry,
            "event": event,
        }
    except DatabaseConnectionError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
