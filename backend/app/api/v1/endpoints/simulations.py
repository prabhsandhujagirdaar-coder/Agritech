"""
AgriChain AI — Dynamic Real-Road Vehicle Simulation API Endpoints
================================================================
Provides endpoints for Indian agricultural geocoding search, OSRM road route previews,
authoritative simulation lifecycle control, live telemetry, and historical replay.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.db.repository import get_shipment_repository
from app.schemas.simulation import (
    CreateSimulationRequest,
    LocationSearchQuery,
    LocationSearchResult,
    RoutePreviewRequest,
    RoutePreviewResponse,
    SimulationControlRequest,
    SimulationSessionResponse,
    SimulationTelemetryPoint,
)
from app.services.geocoding_service import get_geocoding_service
from app.services.routing_service import get_routing_service
from app.services.simulation_engine import get_simulation_engine

router = APIRouter()


@router.post(
    "/geocoding/search",
    response_model=List[LocationSearchResult],
    summary="Search Indian Agricultural Mandis, Cold Stores & Landmarks",
)
async def search_locations(payload: LocationSearchQuery) -> List[LocationSearchResult]:
    """
    Searches Indian mandis, facilities, villages, and logistics hubs with
    in-memory cache, repository lookup, and OSM Nominatim fallback.
    """
    service = get_geocoding_service()
    results = service.search_locations(payload.query, limit=payload.limit)
    return [LocationSearchResult(**item) for item in results]


@router.post(
    "/routes/preview",
    response_model=RoutePreviewResponse,
    summary="Preview Real-Road Highway Driving Route (OSRM)",
)
async def preview_route(payload: RoutePreviewRequest) -> RoutePreviewResponse:
    """
    Calculates a real-road highway driving route between coordinates using OSRM.
    Returns GeoJSON LineString coordinates [[lon, lat], ...], road distance, and duration.
    """
    try:
        routing = get_routing_service()
        route_data = routing.get_route(
            payload.origin_lat,
            payload.origin_lon,
            payload.destination_lat,
            payload.destination_lon,
        )
        return RoutePreviewResponse(
            origin={
                "name": payload.origin_name or "Origin Point",
                "latitude": payload.origin_lat,
                "longitude": payload.origin_lon,
            },
            destination={
                "name": payload.destination_name or "Destination Point",
                "latitude": payload.destination_lat,
                "longitude": payload.destination_lon,
            },
            distance_km=route_data["distance_km"],
            duration_s=route_data["duration_s"],
            geometry=route_data["geometry"],
            routing_source=route_data["routing_source"],
            waypoint_count=route_data["waypoint_count"],
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Route calculation failed: {exc}",
        )


@router.post(
    "/",
    response_model=SimulationSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dynamic Real-Road Simulation Session",
)
async def create_simulation(payload: CreateSimulationRequest) -> SimulationSessionResponse:
    """
    Creates an authoritative simulation session along a real road polyline.
    Strictly synchronizes with the authoritative route for the associated shipment if provided.
    """
    repo = get_shipment_repository()
    routing = get_routing_service()
    engine = get_simulation_engine()

    # Safely stop any running background tasks to prevent competing simulation loops
    for running_id in list(engine._running_tasks.keys()):
        try:
            await engine.stop_simulation(running_id)
        except Exception:
            pass

    origin_name = payload.origin_name
    dest_name = payload.destination_name
    origin_lat = payload.origin_lat
    origin_lon = payload.origin_lon
    dest_lat = payload.destination_lat
    dest_lon = payload.destination_lon
    route_identifier = payload.route_identifier

    # Case 1: Session associated with a registered shipment
    if payload.shipment_id:
        shipment = repo.get_shipment(payload.shipment_id)
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registered shipment '{payload.shipment_id}' does not exist.",
            )

        from app.api.v1.endpoints.shipments import get_shipment_route
        auth_route = get_shipment_route(payload.shipment_id)

        route_geojson = auth_route["geometry"]
        total_dist_km = float(auth_route["distance_km"])
        duration_s = float(auth_route["duration_s"])
        origin_name = auth_route["origin_name"]
        dest_name = auth_route["destination_name"]
        origin_lat = float(auth_route["origin"]["latitude"])
        origin_lon = float(auth_route["origin"]["longitude"])
        dest_lat = float(auth_route["destination"]["latitude"])
        dest_lon = float(auth_route["destination"]["longitude"])
        route_identifier = f"ROUTE-{payload.shipment_id}-{round(total_dist_km, 2)}"

    # Case 2: Custom simulation route
    else:
        if payload.route_geometry and payload.route_geometry.get("coordinates"):
            route_geojson = payload.route_geometry
            coords = route_geojson.get("coordinates", [])
            if len(coords) < 2:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Supplied road geometry must contain at least 2 coordinate points.",
                )
            if payload.total_distance_km and payload.total_distance_km > 0:
                total_dist_km = float(payload.total_distance_km)
            else:
                from app.services.routing_service import haversine_distance_km
                total_dist_km = sum(
                    haversine_distance_km(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
                    for i in range(len(coords) - 1)
                )
            duration_s = (total_dist_km / 55.0) * 3600.0
            route_identifier = payload.route_identifier or f"ROUTE-CUSTOM-{round(total_dist_km, 2)}"
        else:
            try:
                route_data = routing.get_route(origin_lat, origin_lon, dest_lat, dest_lon)
                route_geojson = route_data["geometry"]
                total_dist_km = float(route_data["distance_km"])
                duration_s = float(route_data["duration_s"])
                route_identifier = f"ROUTE-CUSTOM-{round(total_dist_km, 2)}"
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to calculate road route: {exc}",
                )

    coords = route_geojson["coordinates"]
    start_pt = coords[0]

    session_data = {
        "shipment_id": payload.shipment_id,
        "route_identifier": route_identifier,
        "origin_name": origin_name,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
        "destination_name": dest_name,
        "destination_lat": dest_lat,
        "destination_lon": dest_lon,
        "route_geojson": route_geojson,
        "total_distance_km": round(total_dist_km, 2),
        "estimated_duration_s": round(duration_s, 1),
        "current_distance_km": 0.0,
        "current_lat": start_pt[1],
        "current_lon": start_pt[0],
        "current_heading_deg": 0.0,
        "current_speed_kmh": 0.0,
        "speed_multiplier": payload.speed_multiplier,
        "status": "READY",
        "scenario": payload.scenario,
        "step_count": 0,
    }

    created = repo.create_simulation_session(session_data)
    return SimulationSessionResponse(**created)


@router.get(
    "/",
    response_model=List[SimulationSessionResponse],
    summary="List Simulation Sessions",
)
async def list_simulations(
    shipment_id: Optional[str] = Query(None, description="Filter by associated shipment ID"),
    limit: int = Query(50, ge=1, le=100),
) -> List[SimulationSessionResponse]:
    """Returns recent simulation sessions, newest first."""
    repo = get_shipment_repository()
    sessions = repo.list_simulation_sessions(shipment_id=shipment_id, limit=limit)
    return [SimulationSessionResponse(**s) for s in sessions]


@router.get(
    "/{simulation_id}",
    response_model=SimulationSessionResponse,
    summary="Get Simulation Session Details",
)
async def get_simulation(simulation_id: str) -> SimulationSessionResponse:
    repo = get_shipment_repository()
    session = repo.get_simulation_session(simulation_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )
    return SimulationSessionResponse(**session)


@router.post(
    "/{simulation_id}/start",
    response_model=SimulationSessionResponse,
    summary="Start Continuous Real-Road Simulation",
)
async def start_simulation(simulation_id: str) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.start_simulation(simulation_id)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.post(
    "/{simulation_id}/pause",
    response_model=SimulationSessionResponse,
    summary="Pause Running Simulation",
)
async def pause_simulation(simulation_id: str) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.pause_simulation(simulation_id)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.post(
    "/{simulation_id}/resume",
    response_model=SimulationSessionResponse,
    summary="Resume Paused Simulation",
)
async def resume_simulation(simulation_id: str) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.resume_simulation(simulation_id)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.post(
    "/{simulation_id}/stop",
    response_model=SimulationSessionResponse,
    summary="Stop Simulation",
)
async def stop_simulation(simulation_id: str) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.stop_simulation(simulation_id)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.post(
    "/{simulation_id}/reset",
    response_model=SimulationSessionResponse,
    summary="Reset Simulation to Origin (0 km)",
)
async def reset_simulation(simulation_id: str) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.reset_simulation(simulation_id)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.post(
    "/{simulation_id}/step",
    response_model=SimulationSessionResponse,
    summary="Advance Simulation One Discrete Step (Manual Mode)",
)
async def step_simulation(
    simulation_id: str,
    advance_km: Optional[float] = Query(None, description="Optional distance in km to advance"),
) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        session = await engine.step_simulation(simulation_id, advance_km=advance_km)
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.patch(
    "/{simulation_id}/controls",
    response_model=SimulationSessionResponse,
    summary="Update Simulation Controls (Speed Multiplier, Scenario)",
)
async def update_simulation_controls(
    simulation_id: str,
    payload: SimulationControlRequest,
) -> SimulationSessionResponse:
    try:
        engine = get_simulation_engine()
        if payload.action == "start":
            session = await engine.start_simulation(simulation_id)
        elif payload.action == "pause":
            session = await engine.pause_simulation(simulation_id)
        elif payload.action == "resume":
            session = await engine.resume_simulation(simulation_id)
        elif payload.action == "stop":
            session = await engine.stop_simulation(simulation_id)
        elif payload.action == "reset":
            session = await engine.reset_simulation(simulation_id)
        elif payload.action == "step":
            session = await engine.step_simulation(simulation_id)
        else:
            session = await engine.update_controls(
                simulation_id,
                speed_multiplier=payload.speed_multiplier,
                scenario=payload.scenario,
            )
        return SimulationSessionResponse(**session)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )


@router.get(
    "/{simulation_id}/telemetry",
    response_model=List[SimulationTelemetryPoint],
    summary="Get Simulation Recorded Sensor Telemetry",
)
async def get_simulation_telemetry(
    simulation_id: str,
    limit: int = Query(200, ge=1, le=1000),
) -> List[SimulationTelemetryPoint]:
    repo = get_shipment_repository()
    if not repo.get_simulation_session(simulation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )
    readings = repo.get_simulation_telemetry(simulation_id, limit=limit)
    return [SimulationTelemetryPoint(**r) for r in readings]


@router.get(
    "/{simulation_id}/history",
    summary="Get Full Simulation History for Playback and Replay",
)
async def get_simulation_history(
    simulation_id: str,
    limit: int = Query(500, ge=1, le=2000),
) -> Dict[str, Any]:
    """
    Returns full road route geometry, waypoints, and recorded time-series telemetry
    suitable for historical scrubbing and playback visualization.
    """
    repo = get_shipment_repository()
    session = repo.get_simulation_session(simulation_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation session '{simulation_id}' not found.",
        )
    telemetry = repo.get_simulation_telemetry(simulation_id, limit=limit)
    return {
        "session": session,
        "route_geojson": session["route_geojson"],
        "telemetry_points": telemetry,
        "total_steps": len(telemetry),
        "total_distance_km": session["total_distance_km"],
    }
