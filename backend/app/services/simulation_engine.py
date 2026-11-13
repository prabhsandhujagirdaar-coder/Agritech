"""
AgriChain AI — Authoritative Server-Side Vehicle Movement & Cold-Chain Simulation Engine
=======================================================================================
Orchestrates vehicle traversal strictly along road polylines, generates bounded synthetic
cold-chain sensor telemetry, evaluates rolling 24-step LSTM risk, and broadcasts live updates.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import math
import random
from typing import Any, Dict, List, Optional

from app.api.v1.endpoints.ws import get_ws_manager
from app.db.repository import get_shipment_repository
from app.schemas.telemetry import TelemetryPoint
from app.services.routing_service import get_routing_service

logger = logging.getLogger("agrichain.simulation_engine")


class SimulationEngine:
    """Singleton server-authoritative simulation runner with concurrency management."""

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._rolling_buffers: Dict[str, List[TelemetryPoint]] = {}
        self._lock: Optional[asyncio.Lock] = None
        self._tick_interval_s: float = 1.0
        self._base_advance_km_per_tick: float = 2.0  # Scaled for responsive UI demonstration

    def _get_lock(self) -> asyncio.Lock:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if self._lock is None or (loop is not None and getattr(self._lock, "_loop", None) is not None and self._lock._loop is not loop):
            self._lock = asyncio.Lock()
        return self._lock

    async def start_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Starts continuous simulation loop for a session."""
        repo = get_shipment_repository()
        session = repo.get_simulation_session(simulation_id)
        if not session:
            raise KeyError(f"Simulation session '{simulation_id}' not found.")

        current_status = session.get("status")
        if current_status == "COMPLETED":
            # Reset to start if already completed
            await self.reset_simulation(simulation_id)
            session = repo.get_simulation_session(simulation_id)

        async with self._get_lock():
            # Cancel any existing loop for this session
            if simulation_id in self._running_tasks:
                self._running_tasks[simulation_id].cancel()
                self._running_tasks.pop(simulation_id, None)

            repo.update_simulation_session(simulation_id, {"status": "RUNNING"})
            task = asyncio.create_task(self._run_loop(simulation_id))
            self._running_tasks[simulation_id] = task

        updated = repo.get_simulation_session(simulation_id)
        await self._broadcast_status(updated)
        return updated

    async def pause_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Pauses a running simulation loop."""
        async with self._get_lock():
            if simulation_id in self._running_tasks:
                self._running_tasks[simulation_id].cancel()
                self._running_tasks.pop(simulation_id, None)

        repo = get_shipment_repository()
        repo.update_simulation_session(simulation_id, {"status": "PAUSED"})
        updated = repo.get_simulation_session(simulation_id)
        await self._broadcast_status(updated)
        return updated

    async def resume_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Resumes a paused simulation."""
        return await self.start_simulation(simulation_id)

    async def stop_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Stops and cancels a simulation."""
        async with self._get_lock():
            if simulation_id in self._running_tasks:
                self._running_tasks[simulation_id].cancel()
                self._running_tasks.pop(simulation_id, None)

        repo = get_shipment_repository()
        repo.update_simulation_session(simulation_id, {"status": "STOPPED"})
        updated = repo.get_simulation_session(simulation_id)
        await self._broadcast_status(updated)
        return updated

    async def reset_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """Resets vehicle position back to origin (0 km)."""
        async with self._get_lock():
            if simulation_id in self._running_tasks:
                self._running_tasks[simulation_id].cancel()
                self._running_tasks.pop(simulation_id, None)

        self._rolling_buffers.pop(simulation_id, None)
        repo = get_shipment_repository()
        session = repo.get_simulation_session(simulation_id)
        if not session:
            raise KeyError(f"Simulation session '{simulation_id}' not found.")

        coords = session["route_geojson"]["coordinates"]
        start_pt = coords[0]
        updates = {
            "status": "READY",
            "current_distance_km": 0.0,
            "current_lat": start_pt[1],
            "current_lon": start_pt[0],
            "current_heading_deg": 0.0,
            "current_speed_kmh": 0.0,
            "step_count": 0,
        }
        repo.update_simulation_session(simulation_id, updates)
        updated = repo.get_simulation_session(simulation_id)
        await self._broadcast_status(updated)
        return updated

    async def step_simulation(self, simulation_id: str, advance_km: Optional[float] = None) -> Dict[str, Any]:
        """Advances simulation by one discrete checkpoint step."""
        repo = get_shipment_repository()
        session = repo.get_simulation_session(simulation_id)
        if not session:
            raise KeyError(f"Simulation session '{simulation_id}' not found.")

        speed_multiplier = float(session.get("speed_multiplier", 1.0))
        delta_km = advance_km if advance_km is not None else (self._base_advance_km_per_tick * speed_multiplier * 2.5)

        return await self._advance_step(simulation_id, delta_km)

    async def update_controls(
        self,
        simulation_id: str,
        speed_multiplier: Optional[float] = None,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates speed multiplier or active scenario on the fly."""
        repo = get_shipment_repository()
        updates: Dict[str, Any] = {}
        if speed_multiplier is not None:
            updates["speed_multiplier"] = max(0.1, min(20.0, float(speed_multiplier)))
        if scenario is not None:
            updates["scenario"] = str(scenario).strip()

        if updates:
            repo.update_simulation_session(simulation_id, updates)

        updated = repo.get_simulation_session(simulation_id)
        await self._broadcast_status(updated)
        return updated

    async def _run_loop(self, simulation_id: str):
        """Asynchronous execution loop for running sessions."""
        try:
            while True:
                repo = get_shipment_repository()
                session = repo.get_simulation_session(simulation_id)
                if not session or session.get("status") != "RUNNING":
                    break

                multiplier = float(session.get("speed_multiplier", 1.0))
                delta_km = self._base_advance_km_per_tick * multiplier

                res = await self._advance_step(simulation_id, delta_km)
                if res.get("status") == "COMPLETED":
                    logger.info("Simulation session '%s' arrived at destination.", simulation_id)
                    break

                await asyncio.sleep(self._tick_interval_s)
        except asyncio.CancelledError:
            logger.debug("Simulation loop '%s' cancelled.", simulation_id)
        except Exception as exc:
            logger.error("Simulation loop '%s' encountered error: %s", simulation_id, exc)
            repo = get_shipment_repository()
            repo.update_simulation_session(simulation_id, {"status": "FAILED"})

    async def _advance_step(self, simulation_id: str, delta_km: float) -> Dict[str, Any]:
        """Calculates road interpolation, generates synthetic telemetry, runs LSTM risk, and broadcasts."""
        repo = get_shipment_repository()
        session = repo.get_simulation_session(simulation_id)
        if not session:
            raise KeyError(f"Simulation session '{simulation_id}' not found.")

        coords = session["route_geojson"]["coordinates"]
        total_dist_km = float(session.get("total_distance_km", 0.0))
        current_dist_km = float(session.get("current_distance_km", 0.0))
        new_dist_km = min(total_dist_km, current_dist_km + delta_km)
        scenario = session.get("scenario", "normal")
        step_count = int(session.get("step_count", 0)) + 1
        shipment_id = session.get("shipment_id")

        # 1. Exact Road Polyline Interpolation
        router = get_routing_service()
        fix = router.interpolate_polyline_position(coords, new_dist_km)
        is_completed = fix["is_completed"] or (total_dist_km > 0 and (total_dist_km - new_dist_km) <= 0.05) or (new_dist_km >= total_dist_km)

        if is_completed:
            fix["latitude"] = coords[-1][1]
            fix["longitude"] = coords[-1][0]
            fix["distance_travelled_km"] = round(total_dist_km, 2)
            fix["distance_remaining_km"] = 0.0
            fix["progress_pct"] = 100.0
        else:
            fix["distance_travelled_km"] = round(new_dist_km, 2)
            fix["distance_remaining_km"] = round(max(0.0, total_dist_km - new_dist_km), 2)
            fix["progress_pct"] = round(min(100.0, max(0.0, (new_dist_km / (total_dist_km or 1.0)) * 100.0)), 1)

        # 2. Synthetic Telemetry Generation
        telemetry = self._generate_telemetry(scenario, step_count, fix["distance_remaining_km"])
        telemetry["latitude"] = fix["latitude"]
        telemetry["longitude"] = fix["longitude"]
        telemetry["heading_deg"] = fix["heading_deg"]
        telemetry["distance_travelled_km"] = fix["distance_travelled_km"]
        telemetry["distance_remaining_km"] = fix["distance_remaining_km"]
        telemetry["sequence_step"] = step_count
        telemetry["shipment_id"] = shipment_id

        # 3. Rolling 24-step LSTM Risk Sequence
        point = TelemetryPoint(
            hour=step_count,
            temperature=telemetry["temperature_c"],
            humidity=telemetry["humidity_pct"],
            delay_minutes=telemetry["delay_minutes"],
            speed_kmh=telemetry["speed_kmh"],
            distance_remaining_km=fix["distance_remaining_km"],
        )
        buffer = self._rolling_buffers.setdefault(simulation_id, [])
        buffer.append(point)
        if len(buffer) > 24:
            buffer.pop(0)

        risk_eval = self._evaluate_lstm_risk(buffer)
        telemetry["risk_score"] = risk_eval["current_risk"]
        telemetry["predicted_arrival_risk"] = risk_eval["predicted_arrival_risk"]
        telemetry["alert"] = risk_eval["alert"]

        # 4. Record to repository
        t_record = repo.add_simulation_telemetry(simulation_id, telemetry)

        # Update session status
        new_status = "COMPLETED" if is_completed else "RUNNING"
        session_updates = {
            "status": new_status,
            "current_distance_km": fix["distance_travelled_km"],
            "current_lat": fix["latitude"],
            "current_lon": fix["longitude"],
            "current_heading_deg": fix["heading_deg"],
            "current_speed_kmh": telemetry["speed_kmh"],
            "step_count": step_count,
        }
        repo.update_simulation_session(simulation_id, session_updates)
        updated_session = repo.get_simulation_session(simulation_id)

        # 5. Broadcast live events
        await self._broadcast_telemetry(updated_session, t_record, risk_eval)

        # If linked to a real shipment, mirror updates to shipment waypoints & telemetry
        if shipment_id:
            try:
                # Add waypoint
                wp_data = {
                    "latitude": fix["latitude"],
                    "longitude": fix["longitude"],
                    "altitude_m": 200.0,
                    "speed_kmh": telemetry["speed_kmh"],
                    "heading_deg": fix["heading_deg"],
                    "location_metadata": {
                        "source": "simulation",
                        "simulation_id": simulation_id,
                        "data_source": "simulation",
                        "sensor_id": "SNS-SIM-DEMO",
                    },
                }
                repo.add_waypoint(shipment_id, wp_data)
                # Mirror telemetry
                tel_data = {
                    "temperature": telemetry["temperature_c"],
                    "humidity": telemetry["humidity_pct"],
                    "sensor_id": "SNS-SIM-DEMO",
                    "location": f"Simulated Road Fix (Step {step_count})",
                }
                repo.add_telemetry(shipment_id, tel_data)
                # Broadcast shipment location & telemetry updates
                ws = get_ws_manager()
                await ws.broadcast("location_update", {
                    "shipment_id": shipment_id,
                    "latitude": fix["latitude"],
                    "longitude": fix["longitude"],
                    "speed_kmh": telemetry["speed_kmh"],
                    "heading_deg": fix["heading_deg"],
                    "simulation_id": simulation_id,
                })
                await ws.broadcast("telemetry_update", {
                    "shipment_id": shipment_id,
                    "temperature": telemetry["temperature_c"],
                    "humidity": telemetry["humidity_pct"],
                    "sensor_id": "SNS-SIM-DEMO",
                })
                await ws.broadcast("risk_update", {
                    "shipment_id": shipment_id,
                    "current_risk": risk_eval["current_risk"],
                    "predicted_arrival_risk": risk_eval["predicted_arrival_risk"],
                    "alert": risk_eval["alert"],
                })
            except Exception as e:
                logger.debug("Shipment mirror broadcast error: %s", e)

        return updated_session

    def _generate_telemetry(
        self,
        scenario: str,
        step: int,
        remaining_km: float,
    ) -> Dict[str, Any]:
        """Generates realistic synthetic sensor readings strictly constrained to scenario profiles."""
        base_speed = 55.0
        # Scenario variations
        if scenario == "temperature_excursion":
            # Compressor failure: temperature climbs progressively above 8°C
            temp = round(min(16.0, 5.0 + max(0, step - 2) * 1.25 + random.uniform(-0.2, 0.2)), 1)
            humidity = round(min(92.0, 85.0 + random.uniform(-2.0, 2.0)), 1)
            speed = round(max(30.0, base_speed + random.uniform(-5.0, 5.0)), 1)
            delay = max(0, (step - 5) * 5)
        elif scenario == "delay":
            # Traffic congestion or highway roadblock: speed drops, delay escalates
            speed = round(max(0.0, 10.0 - min(8.0, step * 1.5) + random.uniform(-2.0, 2.0)), 1)
            temp = round(min(9.5, 6.0 + step * 0.4 + random.uniform(-0.1, 0.1)), 1)
            humidity = round(88.0 + random.uniform(-1.0, 1.0), 1)
            delay = min(180, step * 12)
        elif scenario == "high_humidity":
            # Condensation risk: relative humidity climbs above 95%
            temp = round(5.2 + random.uniform(-0.3, 0.3), 1)
            humidity = round(min(99.0, 92.0 + min(6.0, step * 0.8) + random.uniform(-0.5, 0.5)), 1)
            speed = round(base_speed + random.uniform(-4.0, 4.0), 1)
            delay = 0
        else:
            # Normal optimal cold chain (4°C - 7°C, 85-90% RH, speed 50-65 km/h)
            temp = round(5.5 + math.sin(step * 0.4) * 0.6 + random.uniform(-0.2, 0.2), 1)
            humidity = round(87.0 + math.cos(step * 0.3) * 2.0 + random.uniform(-0.5, 0.5), 1)
            speed = round(base_speed + random.uniform(-5.0, 8.0), 1) if remaining_km > 5.0 else 25.0
            delay = 0

        return {
            "temperature_c": temp,
            "humidity_pct": humidity,
            "speed_kmh": speed,
            "delay_minutes": delay,
            "scenario": scenario,
            "data_source": "simulation",
            "sensor_id": "SNS-SIM-DEMO",
        }

    def _evaluate_lstm_risk(self, sequence: List[TelemetryPoint]) -> Dict[str, Any]:
        """Evaluates transit risk across the 24-step sequence using domain-rule heuristic.
        Note: Evaluated against thermal window (4°C-8°C); trained PyTorch LSTM checkpoint pending."""
        if not sequence:
            return {"current_risk": 10.0, "predicted_arrival_risk": 11.5, "alert": False}

        temps = [pt.temperature for pt in sequence]
        avg_temp = sum(temps) / len(temps)
        excursion_hours = sum(1 for t in temps if t > 8.0 or t < 4.0)
        max_delay = max(pt.delay_minutes for pt in sequence)

        # Baseline formula: excursion count + temp rise + delay impact
        risk = min(100.0, max(5.0, (avg_temp - 5.0) * 8.0 + excursion_hours * 7.5 + (max_delay * 0.3)))
        predicted = min(100.0, risk * 1.15)

        return {
            "current_risk": round(risk, 1),
            "predicted_arrival_risk": round(predicted, 1),
            "alert": predicted > 50.0,
        }

    async def _broadcast_status(self, session: Dict[str, Any]):
        """Broadcasts simulation session status change."""
        try:
            ws = get_ws_manager()
            await ws.broadcast("simulation_status_update", {
                "simulation_id": session["id"],
                "status": session["status"],
                "speed_multiplier": session["speed_multiplier"],
                "scenario": session["scenario"],
                "current_distance_km": session["current_distance_km"],
                "total_distance_km": session["total_distance_km"],
            })
        except Exception:
            pass

    async def _broadcast_telemetry(
        self,
        session: Dict[str, Any],
        telemetry: Dict[str, Any],
        risk: Dict[str, Any],
    ):
        """Broadcasts simulation position, sensor telemetry, and LSTM risk updates."""
        try:
            ws = get_ws_manager()
            await ws.broadcast("simulation_telemetry_update", {
                "simulation_id": session["id"],
                "telemetry": telemetry,
                "risk": risk,
                "status": session["status"],
            })
            if session["status"] == "COMPLETED":
                await ws.broadcast("simulation_completed", {
                    "simulation_id": session["id"],
                    "total_distance_km": session["total_distance_km"],
                    "final_risk": risk["current_risk"],
                })
        except Exception:
            pass


_simulation_engine: Optional[SimulationEngine] = None


def get_simulation_engine() -> SimulationEngine:
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = SimulationEngine()
    return _simulation_engine

