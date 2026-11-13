"""
AgriChain AI — Real-Road OSRM Routing & Distance Interpolation Service
=====================================================================
Fetches real highway geometries via OSRM (Open Source Routing Machine)
and provides distance-based road polyline interpolation for virtual vehicles.
Includes realistic multi-point highway fallbacks for offline/sandboxed operation.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from app.core.geo import is_network_available, validate_indian_coordinate

logger = logging.getLogger("agrichain.routing")

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates compass bearing in degrees (0° North, clockwise to 360°) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    initial_bearing = math.degrees(math.atan2(y, x))
    return (initial_bearing + 360.0) % 360.0


# High-resolution highway anchor corridors across Northern Indian agricultural belt
_CORRIDOR_ANCHORS: Dict[str, List[Tuple[float, float]]] = {
    # Abohar -> Azadpur APMC Mandi, Delhi via NH-7, NH-9 (Malout, Bathinda, Sirsa, Fatehabad, Hisar, Rohtak, Bahadurgarh)
    "abohar_to_delhi": [
        (30.1453, 74.1994),  # Abohar
        (30.1750, 74.3500),  # NH-7 Abohar-Malout Road
        (30.1915, 74.4989),  # Malout
        (30.2050, 74.7200),  # Giddarbaha NH-7
        (30.2110, 74.9455),  # Bathinda Ring Road
        (29.8500, 75.0100),  # Rama Mandi
        (29.5349, 75.0298),  # Sirsa NH-9
        (29.5144, 75.4549),  # Fatehabad NH-9
        (29.1492, 75.7217),  # Hisar NH-9
        (28.9800, 76.1500),  # Hansi
        (28.9100, 76.3800),  # Meham NH-9
        (28.8955, 76.6066),  # Rohtak Bypass
        (28.7900, 76.7600),  # Sampla
        (28.6924, 76.9240),  # Bahadurgarh Toll
        (28.7050, 77.0500),  # Peeragarhi, Delhi
        (28.7161, 77.1772),  # Azadpur APMC Mandi
    ],
    # Fazilka -> Ludhiana Agro via Muktsar, Kotkapura, Moga, Jagraon
    "fazilka_to_ludhiana": [
        (30.4037, 74.0254),  # Fazilka CA Store
        (30.4350, 74.2800),  # Fazilka-Muktsar Highway
        (30.4744, 74.5167),  # Sri Muktsar Sahib
        (30.5828, 74.8267),  # Kotkapura Bypass
        (30.8165, 75.1715),  # Moga Agri Terminal
        (30.7850, 75.4780),  # Jagraon Highway
        (30.8500, 75.6800),  # Mullanpur Dakha
        (30.9010, 75.8573),  # Ludhiana Agro Cold Chain
    ],
    # Hoshiarpur / Kangmai -> Azadpur Delhi via Phagwara, Ludhiana, Khanna, Ambala, Panipat, Sonipat (Grand Trunk / NH-44)
    "kangmai_to_delhi": [
        (31.6677, 75.7923),  # Kangmai Packhouse
        (31.5300, 75.9100),  # Hoshiarpur
        (31.2200, 75.7700),  # Phagwara NH-44
        (30.9010, 75.8573),  # Ludhiana Bypass
        (30.7000, 76.2200),  # Khanna Grain Market
        (30.6283, 76.3863),  # Sirhind (Bara Farm)
        (30.3800, 76.7800),  # Ambala Cantt
        (29.9700, 76.8800),  # Kurukshetra
        (29.6900, 76.9900),  # Karnal
        (29.3900, 76.9700),  # Panipat
        (28.9900, 77.0200),  # Sonipat
        (28.8500, 77.1000),  # Singhu Border
        (28.7161, 77.1772),  # Azadpur Mandi
    ],
    # Fazilka -> Amritsar via Jalalabad, Guru Har Sahai, Firozpur (NH-54), Talwandi Bhai, Zira, Makhu, Harike, Tarn Taran (~197 km)
    "fazilka_to_amritsar": [
        (30.4037, 74.0254),  # Fazilka CA Store
        (30.5050, 74.1450),  # Ladhuka Mandi NH-54
        (30.6050, 74.2550),  # Jalalabad NH-54
        (30.7100, 74.4000),  # Guru Har Sahai
        (30.8200, 74.5200),  # Mamdot / Firozpur South
        (30.9237, 74.6137),  # Firozpur Cantt Bypass
        (30.8650, 74.9450),  # Talwandi Bhai NH-54 Junction
        (30.9750, 74.9850),  # Zira Highway Junction
        (31.1000, 74.9900),  # Makhu NH-54
        (31.1700, 74.9700),  # Harike Pattan Wetland Bridge (NH-54)
        (31.3500, 74.9400),  # Naushehra Panwan Bypass
        (31.4520, 74.9280),  # Tarn Taran Sahib
        (31.5400, 74.8950),  # Amritsar Southern Bypass
        (31.6042, 74.8723),  # Amritsar Bhagtanwala APMC Mandi
    ],
    # Jaipur -> Agra via Bassi, Dausa, Sikandra, Mahwa, Bharatpur, Fatehpur Sikri (NH-21 Agra-Bikaner Expressway ~240 km)
    "jaipur_to_agra": [
        (26.7937, 75.7381),  # Jaipur Muhana Terminal Mandi
        (26.8300, 76.0400),  # Bassi NH-21
        (26.8900, 76.3400),  # Dausa Bypass
        (26.9600, 76.6000),  # Sikandra Junction
        (27.0400, 76.9300),  # Mahwa Toll Plaza
        (27.2200, 77.4900),  # Bharatpur City Bypass
        (27.0900, 77.6600),  # Fatehpur Sikri Historical Corridor
        (27.1767, 78.0081),  # Agra Integrated Cold Logistics Hub
    ],
    # Abohar -> Bathinda via Malout, Giddarbaha (NH-7 ~75 km)
    "abohar_to_bathinda": [
        (30.1453, 74.1994),  # Abohar Packhouse
        (30.1915, 74.4989),  # Malout Center
        (30.2050, 74.7200),  # Giddarbaha NH-7
        (30.1798, 74.9654),  # Bathinda PSWC CFS Complex
    ],
    # Abohar -> Ludhiana via Malout, Bathinda, Barnala, Raikot, Mullanpur (NH-7 & NH-64 ~225 km)
    "abohar_to_ludhiana": [
        (30.1453, 74.1994),  # Abohar
        (30.1915, 74.4989),  # Malout
        (30.2110, 74.9455),  # Bathinda Ring Road
        (30.3700, 75.5500),  # Barnala Grain Mandi
        (30.6500, 75.6000),  # Raikot Bypass
        (30.8500, 75.6800),  # Mullanpur Dakha
        (30.8492, 75.9868),  # Ludhiana Sahnewal Godown
    ],
}


class RoutingService:
    """Road routing service with OSRM driving integration, in-memory caching, and highway fallbacks."""

    def __init__(self):
        self._route_cache: Dict[str, Dict[str, Any]] = {}
        self._osrm_available: bool = True
        self._osrm_retry_after: float = 0.0

    def get_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> Dict[str, Any]:
        """
        Calculates a real-road driving route between origin and destination.
        Returns GeoJSON LineString (coordinates [[lon, lat], ...]), distance_km, and duration_s.
        """
        validate_indian_coordinate(origin_lat, origin_lon, "origin")
        validate_indian_coordinate(dest_lat, dest_lon, "destination")

        cache_key = f"{origin_lat:.3f},{origin_lon:.3f}->{dest_lat:.3f},{dest_lon:.3f}"
        if cache_key in self._route_cache:
            return dict(self._route_cache[cache_key])

        # 1. Attempt OSRM driving API call
        osrm_result = self._fetch_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon)
        if osrm_result is not None:
            self._route_cache[cache_key] = osrm_result
            return dict(osrm_result)

        # 2. Fallback to high-resolution highway corridor generator
        logger.info("OSRM unreachable or timed out; generating realistic highway corridor polyline.")
        fallback_result = self._generate_fallback_road_route(origin_lat, origin_lon, dest_lat, dest_lon)
        self._route_cache[cache_key] = fallback_result
        return dict(fallback_result)

    def _fetch_osrm_route(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> Optional[Dict[str, Any]]:
        """Queries the public OSRM driving routing engine."""
        import time
        if not is_network_available():
            return None
        if not self._osrm_available and time.time() < self._osrm_retry_after:
            return None

        # Note: OSRM URL format expects {lon},{lat};{lon},{lat}
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon1:.6f},{lat1:.6f};{lon2:.6f},{lat2:.6f}"
            f"?overview=full&geometries=geojson&steps=false"
        )
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AgriChain-AI-Simulator/1.0 (academic research)"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    routes = data.get("routes", [])
                    if routes:
                        best = routes[0]
                        geometry = best.get("geometry", {})
                        distance_m = float(best.get("distance", 0.0))
                        duration_s = float(best.get("duration", 0.0))
                        coords = geometry.get("coordinates", [])

                        if coords and len(coords) >= 2:
                            return {
                                "geometry": geometry,
                                "distance_km": round(distance_m / 1000.0, 2),
                                "duration_s": round(duration_s, 1),
                                "routing_source": "osrm_driving",
                                "waypoint_count": len(coords),
                            }
        except Exception as exc:
            self._osrm_available = False
            self._osrm_retry_after = time.time() + 120.0
            logger.info("OSRM route fetch unavailable: %s (cooloff active)", exc)

        return None

    def _generate_fallback_road_route(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> Dict[str, Any]:
        """
        Generates realistic highway-segmented road geometry when external OSRM is offline.
        Subdivides the path along Indian corridor anchor chains so the path curves along roads.
        """
        # Check if route matches or closely aligns with one of our known anchor corridors
        matched_anchors: Optional[List[Tuple[float, float]]] = None
        best_corridor_score = float("inf")

        for key, anchors in _CORRIDOR_ANCHORS.items():
            start_dist = haversine_distance_km(lat1, lon1, anchors[0][0], anchors[0][1])
            end_dist = haversine_distance_km(lat2, lon2, anchors[-1][0], anchors[-1][1])
            score = start_dist + end_dist
            if start_dist < 45.0 and end_dist < 45.0 and score < best_corridor_score:
                best_corridor_score = score
                matched_anchors = [(lat1, lon1)] + anchors[1:-1] + [(lat2, lon2)]

            # Reverse direction match
            rev_start = haversine_distance_km(lat1, lon1, anchors[-1][0], anchors[-1][1])
            rev_end = haversine_distance_km(lat2, lon2, anchors[0][0], anchors[0][1])
            rev_score = rev_start + rev_end
            if rev_start < 45.0 and rev_end < 45.0 and rev_score < best_corridor_score:
                best_corridor_score = rev_score
                matched_anchors = [(lat1, lon1)] + list(reversed(anchors))[1:-1] + [(lat2, lon2)]

        if not matched_anchors:
            # Build an interpolated multi-waypoint path with natural highway curvature
            straight_dist = haversine_distance_km(lat1, lon1, lat2, lon2)
            num_steps = max(8, int(straight_dist / 15.0))  # One waypoint roughly every 15 km
            matched_anchors = []
            matched_anchors.append((lat1, lon1))

            d_lat = lat2 - lat1
            d_lon = lon2 - lon1

            for step in range(1, num_steps):
                frac = step / float(num_steps)
                # Add natural subtle curve perpendicular to travel vector
                wave = math.sin(frac * math.pi) * 0.04
                step_lat = lat1 + d_lat * frac - d_lon * wave * 0.15
                step_lon = lon1 + d_lon * frac + d_lat * wave * 0.15
                matched_anchors.append((round(step_lat, 5), round(step_lon, 5)))

            matched_anchors.append((lat2, lon2))

        # Subdivide matched anchors into dense segments (approx every 1.5 - 2 km)
        dense_coords: List[List[float]] = []  # [[lon, lat], ...]
        total_dist_km = 0.0

        for i in range(len(matched_anchors) - 1):
            p1 = matched_anchors[i]
            p2 = matched_anchors[i + 1]
            seg_dist = haversine_distance_km(p1[0], p1[1], p2[0], p2[1])
            sub_count = max(1, int(seg_dist / 2.0))

            for s in range(sub_count):
                t = s / float(sub_count)
                interp_lat = p1[0] + t * (p2[0] - p1[0])
                interp_lon = p1[1] + t * (p2[1] - p1[1])
                dense_coords.append([round(interp_lon, 6), round(interp_lat, 6)])

        dense_coords.append([round(matched_anchors[-1][1], 6), round(matched_anchors[-1][0], 6)])

        # Calculate exact cumulative polyline distance
        for k in range(len(dense_coords) - 1):
            c1 = dense_coords[k]
            c2 = dense_coords[k + 1]
            total_dist_km += haversine_distance_km(c1[1], c1[0], c2[1], c2[0])

        # Average Indian commercial transit speed ~ 55 km/h
        duration_s = (total_dist_km / 55.0) * 3600.0

        return {
            "geometry": {
                "type": "LineString",
                "coordinates": dense_coords,
            },
            "distance_km": round(total_dist_km, 2),
            "duration_s": round(duration_s, 1),
            "routing_source": "fallback_corridor",
            "waypoint_count": len(dense_coords),
        }

    @staticmethod
    def interpolate_polyline_position(
        coordinates_lon_lat: List[List[float]],
        travelled_distance_km: float,
    ) -> Dict[str, Any]:
        """
        Interpolates the precise vehicle location along a road polyline given distance travelled.
        coordinates_lon_lat is a list of [lon, lat] pairs.
        Returns:
            latitude: float
            longitude: float
            heading_deg: float
            progress_pct: float (0.0 to 100.0)
            distance_remaining_km: float
            is_completed: bool
        """
        if not coordinates_lon_lat or len(coordinates_lon_lat) < 2:
            raise ValueError("Road polyline must have at least 2 coordinate pairs.")

        # Compute cumulative distance for each segment
        cumulative: List[float] = [0.0]
        running_total = 0.0
        for i in range(len(coordinates_lon_lat) - 1):
            p1 = coordinates_lon_lat[i]
            p2 = coordinates_lon_lat[i + 1]
            seg = haversine_distance_km(p1[1], p1[0], p2[1], p2[0])
            running_total += seg
            cumulative.append(running_total)

        total_route_km = cumulative[-1]

        # Clamp travelled distance
        effective_dist = max(0.0, min(travelled_distance_km, total_route_km))
        progress_pct = round((effective_dist / total_route_km * 100.0) if total_route_km > 0 else 100.0, 2)
        remaining_km = round(max(0.0, total_route_km - effective_dist), 2)

        # Handle boundary cases
        if effective_dist <= 0.0:
            first_pt = coordinates_lon_lat[0]
            second_pt = coordinates_lon_lat[1]
            heading = calculate_bearing_deg(first_pt[1], first_pt[0], second_pt[1], second_pt[0])
            return {
                "latitude": first_pt[1],
                "longitude": first_pt[0],
                "heading_deg": round(heading, 1),
                "progress_pct": 0.0,
                "distance_travelled_km": 0.0,
                "distance_remaining_km": round(total_route_km, 2),
                "total_distance_km": round(total_route_km, 2),
                "is_completed": False,
            }

        if effective_dist >= (total_route_km - 0.02):
            penult = coordinates_lon_lat[-2]
            last = coordinates_lon_lat[-1]
            heading = calculate_bearing_deg(penult[1], penult[0], last[1], last[0])
            return {
                "latitude": last[1],
                "longitude": last[0],
                "heading_deg": round(heading, 1),
                "progress_pct": 100.0,
                "distance_travelled_km": round(total_route_km, 2),
                "distance_remaining_km": 0.0,
                "total_distance_km": round(total_route_km, 2),
                "is_completed": True,
            }

        # Find the segment containing effective_dist
        idx = 0
        for i in range(len(cumulative) - 1):
            if cumulative[i] <= effective_dist <= cumulative[i + 1]:
                idx = i
                break

        seg_start_dist = cumulative[idx]
        seg_end_dist = cumulative[idx + 1]
        seg_len = seg_end_dist - seg_start_dist

        t = (effective_dist - seg_start_dist) / seg_len if seg_len > 0 else 0.0
        pt1 = coordinates_lon_lat[idx]
        pt2 = coordinates_lon_lat[idx + 1]

        lat = pt1[1] + t * (pt2[1] - pt1[1])
        lon = pt1[0] + t * (pt2[0] - pt1[0])
        heading = calculate_bearing_deg(pt1[1], pt1[0], pt2[1], pt2[0])

        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "heading_deg": round(heading, 1),
            "progress_pct": progress_pct,
            "distance_travelled_km": round(effective_dist, 2),
            "distance_remaining_km": remaining_km,
            "total_distance_km": round(total_route_km, 2),
            "is_completed": False,
        }


_routing_service: Optional[RoutingService] = None


def get_routing_service() -> RoutingService:
    global _routing_service
    if _routing_service is None:
        _routing_service = RoutingService()
    return _routing_service
