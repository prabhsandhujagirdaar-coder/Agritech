"""
AgriChain AI — Indian Agricultural Geocoding & Landmark Search Service
======================================================================
Provides verified search and geocoding across Indian mandis, cold stores,
APMCs, villages, and logistics hubs with Nominatim API and offline fallbacks.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any, Dict, List, Optional
import urllib.request
import json

from app.core.geo import is_network_available, is_within_india, validate_indian_coordinate

logger = logging.getLogger("agrichain.geocoding")

# Curated Indian agricultural mandis, cold chains, and logistical centers
CURATED_AGRICULTURAL_PLACES: List[Dict[str, Any]] = [
    {
        "name": "Azadpur APMC Mega Mandi",
        "display_name": "Azadpur APMC Fruit & Vegetable Market, North Delhi, Delhi 110033",
        "latitude": 28.7161,
        "longitude": 77.1772,
        "type": "mandi",
        "state": "Delhi",
        "district": "North Delhi",
    },
    {
        "name": "Abohar Kinnow & Guava Packhouse",
        "display_name": "PAGREXCO Citrus & Guava Estate, Abohar, Fazilka, Punjab 152116",
        "latitude": 30.1453,
        "longitude": 74.1994,
        "type": "facility",
        "state": "Punjab",
        "district": "Fazilka",
    },
    {
        "name": "Fazilka CA Cold Store Hub",
        "display_name": "Fazilka Controlled Atmosphere Storage Hub, Fazilka, Punjab 152123",
        "latitude": 30.4037,
        "longitude": 74.0254,
        "type": "cold_storage",
        "state": "Punjab",
        "district": "Fazilka",
    },
    {
        "name": "Bathinda Multimodal Transit Hub",
        "display_name": "Bathinda Integrated Logistics Terminal, Bathinda, Punjab 151001",
        "latitude": 30.2110,
        "longitude": 74.9455,
        "type": "logistics_hub",
        "state": "Punjab",
        "district": "Bathinda",
    },
    {
        "name": "Ludhiana Agro Cold Chain Terminal",
        "display_name": "PAU Agricultural Cold Chain Hub, Ludhiana, Punjab 141004",
        "latitude": 30.9010,
        "longitude": 75.8573,
        "type": "cold_storage",
        "state": "Punjab",
        "district": "Ludhiana",
    },
    {
        "name": "Amritsar Mandi Logistics Center",
        "display_name": "Bhagtanwala Grain & Fruit Mandi, Amritsar, Punjab 143001",
        "latitude": 31.6340,
        "longitude": 74.8723,
        "type": "mandi",
        "state": "Punjab",
        "district": "Amritsar",
    },
    {
        "name": "Jalandhar Maqsudan Mandi",
        "display_name": "Maqsudan APMC Fruit & Vegetable Mandi, Jalandhar, Punjab 144008",
        "latitude": 31.3489,
        "longitude": 75.5786,
        "type": "mandi",
        "state": "Punjab",
        "district": "Jalandhar",
    },
    {
        "name": "PAGREXCO Bara Farm Packhouse",
        "display_name": "Village Bara Farm Packhouse & Cold Store, Sirhind, Fatehgarh Sahib, Punjab",
        "latitude": 30.6283,
        "longitude": 76.3863,
        "type": "packhouse",
        "state": "Punjab",
        "district": "Fatehgarh Sahib",
    },
    {
        "name": "PAGREXCO Kangmai Cold Storage",
        "display_name": "Village Kangmai Packhouse, Tehsil Hariana, Hoshiarpur, Punjab",
        "latitude": 31.6677,
        "longitude": 75.7923,
        "type": "packhouse",
        "state": "Punjab",
        "district": "Hoshiarpur",
    },
    {
        "name": "Sirsa APMC Checkpoint & Mandi",
        "display_name": "Sirsa Grain & Cotton Market, NH-9 Corridor, Sirsa, Haryana 125055",
        "latitude": 29.5349,
        "longitude": 75.0298,
        "type": "mandi",
        "state": "Haryana",
        "district": "Sirsa",
    },
    {
        "name": "Hisar Logistics Hub",
        "display_name": "Hisar Agro Logistics Center, Hisar, Haryana 125001",
        "latitude": 29.1492,
        "longitude": 75.7217,
        "type": "logistics_hub",
        "state": "Haryana",
        "district": "Hisar",
    },
    {
        "name": "Rohtak Bypass Food Logistics Hub",
        "display_name": "Rohtak Cold Chain Logistics Park, Rohtak, Haryana 124001",
        "latitude": 28.8955,
        "longitude": 76.6066,
        "type": "logistics_hub",
        "state": "Haryana",
        "district": "Rohtak",
    },
    {
        "name": "Bahadurgarh NCR Cold Transit Hub",
        "display_name": "Bahadurgarh Delhi-Border Cold Logistics Hub, Jhajjar, Haryana 124507",
        "latitude": 28.6924,
        "longitude": 76.9240,
        "type": "logistics_hub",
        "state": "Haryana",
        "district": "Jhajjar",
    },
    {
        "name": "Chandigarh Grain Market Sector 26",
        "display_name": "Sector 26 APMC Fruit & Grain Mandi, Chandigarh UT 160019",
        "latitude": 30.7280,
        "longitude": 76.8040,
        "type": "mandi",
        "state": "Chandigarh",
        "district": "Chandigarh",
    },
    {
        "name": "Patiala Agri Wholesale Market",
        "display_name": "Sanauri Gate APMC Mandi, Patiala, Punjab 147001",
        "latitude": 30.3398,
        "longitude": 76.3869,
        "type": "mandi",
        "state": "Punjab",
        "district": "Patiala",
    },
    {
        "name": "Moga Agri Terminal",
        "display_name": "GT Road Agri Terminal, Moga, Punjab 142001",
        "latitude": 30.8165,
        "longitude": 75.1715,
        "type": "mandi",
        "state": "Punjab",
        "district": "Moga",
    },
    {
        "name": "Jaipur Muhana APMC Terminal Mandi",
        "display_name": "Muhana Mandi Wholesale Terminal, Sanganer, Jaipur, Rajasthan 302029",
        "latitude": 26.7937,
        "longitude": 75.7381,
        "type": "mandi",
        "state": "Rajasthan",
        "district": "Jaipur",
    },
    {
        "name": "Agra Agro Cold Logistics Hub",
        "display_name": "Agra Integrated Cold Chain Terminal, NH-19 Corridor, Agra, Uttar Pradesh 282007",
        "latitude": 27.1767,
        "longitude": 78.0081,
        "type": "cold_storage",
        "state": "Uttar Pradesh",
        "district": "Agra",
    },
    {
        "name": "Malout Corridor Transit Center",
        "display_name": "Malout Agri Transport Hub, Sri Muktsar Sahib, Punjab 152107",
        "latitude": 30.1915,
        "longitude": 74.4989,
        "type": "transit_hub",
        "state": "Punjab",
        "district": "Sri Muktsar Sahib",
    },
    {
        "name": "Fatehabad Agri Hub",
        "display_name": "Fatehabad Mandi Center, Fatehabad, Haryana 125050",
        "latitude": 29.5144,
        "longitude": 75.4549,
        "type": "mandi",
        "state": "Haryana",
        "district": "Fatehabad",
    },
]


class GeocodingService:
    """Geocoding service with local cache, repository facilities, and OSM Nominatim lookup."""

    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._last_osm_call_time: float = 0.0
        self._nominatim_available: bool = True
        self._nominatim_retry_after: float = 0.0

    def search_locations(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Searches Indian agricultural locations by name, district, or keyword.
        Prioritizes curated local mandis/facilities and falls back to OSM Nominatim.
        """
        q = query.strip()
        if not q or len(q) < 2:
            return []

        q_lower = q.lower()
        if q_lower in self._cache:
            return self._cache[q_lower][:limit]

        results: List[Dict[str, Any]] = []
        seen_coords = set()

        # 1. Search in curated places
        for place in CURATED_AGRICULTURAL_PLACES:
            name_match = q_lower in place["name"].lower()
            display_match = q_lower in place["display_name"].lower()
            district_match = place.get("district", "").lower() in q_lower or q_lower in place.get("district", "").lower()
            state_match = place.get("state", "").lower() in q_lower or q_lower in place.get("state", "").lower()

            if name_match or display_match or district_match or state_match:
                coord_key = (round(place["latitude"], 3), round(place["longitude"], 3))
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    results.append({
                        "name": place["name"],
                        "display_name": place["display_name"],
                        "latitude": place["latitude"],
                        "longitude": place["longitude"],
                        "type": place.get("type", "location"),
                        "state": place.get("state", "Punjab"),
                        "source": "curated_agri_directory",
                    })

        # 2. Search in repository facilities
        try:
            from app.db.repository import get_shipment_repository
            repo = get_shipment_repository()
            facilities = repo.list_facilities()
            for fac in facilities:
                fac_name = fac.get("name", "")
                fac_dist = fac.get("district", "")
                fac_addr = fac.get("address", "")
                fac_lat = fac.get("latitude")
                fac_lon = fac.get("longitude")

                if fac_lat is not None and fac_lon is not None:
                    if (
                        q_lower in fac_name.lower()
                        or q_lower in fac_dist.lower()
                        or q_lower in fac_addr.lower()
                    ):
                        coord_key = (round(float(fac_lat), 3), round(float(fac_lon), 3))
                        if coord_key not in seen_coords:
                            seen_coords.add(coord_key)
                            results.append({
                                "name": fac_name,
                                "display_name": f"{fac_name}, {fac_addr}",
                                "latitude": float(fac_lat),
                                "longitude": float(fac_lon),
                                "type": fac.get("facility_type", "facility"),
                                "state": fac.get("state", "Punjab"),
                                "source": "facility_repository",
                            })
        except Exception as exc:
            logger.debug("Facility repo lookup skipped: %s", exc)

        # 3. Only query OSM Nominatim if no local matches found
        if len(results) == 0:
            osm_matches = self._query_osm_nominatim(q, limit=limit)
            for item in osm_matches:
                coord_key = (round(item["latitude"], 3), round(item["longitude"], 3))
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    results.append(item)

        trimmed = results[:limit]
        self._cache[q_lower] = trimmed
        return trimmed

    def _query_osm_nominatim(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries OpenStreetMap Nominatim with rate limiting (1 call / sec) and timeout."""
        if not is_network_available():
            return []
        if not self._nominatim_available and time.time() < self._nominatim_retry_after:
            return []

        now = time.time()
        elapsed = now - self._last_osm_call_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_osm_call_time = time.time()

        encoded = urllib.parse.quote(f"{query}, India")
        url = (
            f"https://nominatim.openstreetmap.org/search?"
            f"q={encoded}&format=json&countrycodes=in&limit={limit}&addressdetails=1"
        )
        headers = {
            "User-Agent": "AgriChain-AI-Simulator/1.0 (academic cold-chain research; contact@agrichain-ai.org)"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.status == 200:
                    raw = json.loads(response.read().decode("utf-8"))
                    osm_results = []
                    for entry in raw:
                        try:
                            lat = float(entry.get("lat"))
                            lon = float(entry.get("lon"))
                            if is_within_india(lat, lon):
                                display = entry.get("display_name", "")
                                name = entry.get("name") or display.split(",")[0]
                                addr = entry.get("address", {})
                                state = addr.get("state") or addr.get("state_district") or "India"
                                osm_results.append({
                                    "name": name,
                                    "display_name": display,
                                    "latitude": lat,
                                    "longitude": lon,
                                    "type": entry.get("type", "location"),
                                    "state": state,
                                    "source": "osm_nominatim",
                                })
                        except (ValueError, TypeError):
                            continue
                    return osm_results
        except Exception as exc:
            self._nominatim_available = False
            self._nominatim_retry_after = time.time() + 120.0
            logger.info("Nominatim lookup offline/unavailable for '%s': %s (cooloff active)", query, exc)
            return []

        return []


_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
