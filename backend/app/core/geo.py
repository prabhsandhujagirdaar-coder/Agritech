"""
AgriChain AI — Geospatial Validation & Operational Boundaries
============================================================
Enforces Indian agricultural supply chain geographical boundaries (WGS84 / SRID 4326).
Ensures vehicle waypoints and storage facilities remain within verified Indian corridors.
"""

from typing import Tuple, Dict, Any, Optional

# India Geographical Bounding Box (Mainland)
# Latitude: 8.0689° N to 37.0900° N
# Longitude: 68.1166° E to 97.4116° E
INDIA_LAT_MIN = 8.0
INDIA_LAT_MAX = 37.5
INDIA_LON_MIN = 68.0
INDIA_LON_MAX = 97.5

# Punjab & Northern Agricultural Corridor Focus Area (Punjab, Haryana, Delhi NCR, Northern Rajasthan)
PUNJAB_CORRIDOR_LAT_MIN = 28.0
PUNJAB_CORRIDOR_LAT_MAX = 32.6
PUNJAB_CORRIDOR_LON_MIN = 73.5
PUNJAB_CORRIDOR_LON_MAX = 77.8


def is_valid_wgs84(latitude: float, longitude: float) -> bool:
    """Validates global WGS84 coordinate boundary constraints."""
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return False
    return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0


def is_within_india(latitude: float, longitude: float) -> bool:
    """
    Checks if coordinates fall within the general geographic boundaries of India.
    Prevents synthetic or rogue GPS coordinates outside India from corrupting map bounds.
    """
    if not is_valid_wgs84(latitude, longitude):
        return False
    return (
        INDIA_LAT_MIN <= latitude <= INDIA_LAT_MAX
        and INDIA_LON_MIN <= longitude <= INDIA_LON_MAX
    )


def is_within_punjab_corridor(latitude: float, longitude: float) -> bool:
    """
    Checks if coordinates fall within the Punjab agricultural corridor (Punjab, Haryana, Delhi NCR).
    """
    if not is_within_india(latitude, longitude):
        return False
    return (
        PUNJAB_CORRIDOR_LAT_MIN <= latitude <= PUNJAB_CORRIDOR_LAT_MAX
        and PUNJAB_CORRIDOR_LON_MIN <= longitude <= PUNJAB_CORRIDOR_LON_MAX
    )


def validate_indian_coordinate(latitude: float, longitude: float, field_name: str = "coordinates") -> None:
    """
    Raises ValueError if coordinates fall outside India.
    """
    if not is_valid_wgs84(latitude, longitude):
        raise ValueError(
            f"Invalid WGS84 coordinates for {field_name}: latitude {latitude} must be in [-90, 90], longitude {longitude} must be in [-180, 180]"
        )
    if not is_within_india(latitude, longitude):
        raise ValueError(
            f"Coordinates for {field_name} ({latitude:.4f}° N, {longitude:.4f}° E) fall outside India operational boundaries. "
            f"Allowed range: Lat [{INDIA_LAT_MIN}, {INDIA_LAT_MAX}], Lon [{INDIA_LON_MIN}, {INDIA_LON_MAX}]."
        )


import socket
import time

_last_network_check: float = 0.0
_is_online: bool = False


def is_network_available() -> bool:
    """
    Fast, non-blocking check (<200ms) to verify internet egress availability.
    Prevents prolonged 30s DNS timeouts in sandboxed or offline environments.
    """
    global _last_network_check, _is_online
    now = time.time()
    if now - _last_network_check < 30.0:
        return _is_online
    _last_network_check = now
    try:
        orig_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(0.2)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("1.1.1.1", 53))
            socket.gethostbyname("router.project-osrm.org")
            _is_online = True
        finally:
            socket.setdefaulttimeout(orig_timeout)
    except Exception:
        _is_online = False
    return _is_online

