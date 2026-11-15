"""
AgriChain AI — Indian Agricultural Geocoding & Landmark Search Service
======================================================================
Provides verified search and geocoding across Indian mandis, cold stores,
APMCs, villages, and logistics hubs with Nominatim API and offline fallbacks.
"""

from __future__ import annotations

import logging
import time
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple
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
        "aliases": ["Azadpur APMC Mandi", "Azadpur Mandi", "Azadpur", "Delhi APMC Mandi", "Delhi Mandi"],
    },
    {
        "name": "Abohar Packhouse",
        "display_name": "Abohar Packhouse & Post-Harvest Center, Fazilka, Punjab 152116",
        "latitude": 30.1453,
        "longitude": 74.1994,
        "type": "packhouse",
        "state": "Punjab",
        "district": "Fazilka",
        "aliases": ["Abohar Post-Harvest Center", "Abohar Kinnow & Guava Packhouse", "Abohar Kinnow Packhouse", "Abohar Mandi", "Abohar"],
    },
    {
        "name": "Abohar Kinnow & Guava Packhouse",
        "display_name": "PAGREXCO Citrus & Guava Estate, Abohar, Fazilka, Punjab 152116",
        "latitude": 30.1453,
        "longitude": 74.1994,
        "type": "facility",
        "state": "Punjab",
        "district": "Fazilka",
        "aliases": ["Abohar Packhouse", "Abohar Post-Harvest Center", "Abohar Mandi", "Abohar Facility", "Abohar"],
    },
    {
        "name": "Fazilka CA Cold Store Hub",
        "display_name": "Fazilka Controlled Atmosphere Storage Hub, Fazilka, Punjab 152123",
        "latitude": 30.4037,
        "longitude": 74.0254,
        "type": "cold_storage",
        "state": "Punjab",
        "district": "Fazilka",
        "aliases": ["Fazilka Cold Store", "Fazilka CA Store", "Fazilka Mandi", "Fazilka Hub", "Fazilka"],
    },
    {
        "name": "Bathinda Multimodal Transit Hub",
        "display_name": "Bathinda Integrated Logistics Terminal, Bathinda, Punjab 151001",
        "latitude": 30.2110,
        "longitude": 74.9455,
        "type": "logistics_hub",
        "state": "Punjab",
        "district": "Bathinda",
        "aliases": ["Bathinda Central Agri Godown", "Bathinda Mandi", "Bathinda Logistics Hub", "Bathinda Godown", "Bathinda"],
    },
    {
        "name": "Ludhiana Agro Cold Chain Terminal",
        "display_name": "PAU Agricultural Cold Chain Hub, Ludhiana, Punjab 141004",
        "latitude": 30.9010,
        "longitude": 75.8573,
        "type": "cold_storage",
        "state": "Punjab",
        "district": "Ludhiana",
        "aliases": ["Ludhiana Agro Cold Chain Warehouse", "Ludhiana Mandi", "PAU Ludhiana", "Ludhiana Cold Storage", "Ludhiana"],
    },
    {
        "name": "Amritsar Mandi Logistics Center",
        "display_name": "Bhagtanwala Grain & Fruit Mandi, Amritsar, Punjab 143001",
        "latitude": 31.6340,
        "longitude": 74.8723,
        "type": "mandi",
        "state": "Punjab",
        "district": "Amritsar",
        "aliases": ["Amritsar Fruit & Produce Mandi Cold Terminal", "Amritsar Mandi", "Bhagtanwala Mandi", "Amritsar"],
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
        "name": "Jaipur Mandi",
        "display_name": "Jaipur APMC Muhana Fruit & Vegetable Terminal Mandi, Jaipur, Rajasthan 302029",
        "latitude": 26.7937,
        "longitude": 75.7381,
        "type": "mandi",
        "state": "Rajasthan",
        "district": "Jaipur",
        "aliases": ["Jaipur APMC Mandi", "Muhana Mandi", "Jaipur Wholesale Mandi", "Jaipur APMC", "Jaipur"],
    },
    {
        "name": "Jaipur Muhana APMC Terminal Mandi",
        "display_name": "Muhana Mandi Wholesale Terminal, Sanganer, Jaipur, Rajasthan 302029",
        "latitude": 26.7937,
        "longitude": 75.7381,
        "type": "mandi",
        "state": "Rajasthan",
        "district": "Jaipur",
        "aliases": ["Jaipur Mandi", "Muhana Mandi", "Jaipur Terminal Mandi", "Jaipur"],
    },
    {
        "name": "Agra Agro Cold Logistics Hub",
        "display_name": "Agra Integrated Cold Chain Terminal, NH-19 Corridor, Agra, Uttar Pradesh 282007",
        "latitude": 27.1767,
        "longitude": 78.0081,
        "type": "cold_storage",
        "state": "Uttar Pradesh",
        "district": "Agra",
        "aliases": ["Agra Mandi", "Agra Cold Storage", "Agra Cold Hub", "Agra"],
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


GENERIC_AGRI_KEYWORDS: Set[str] = {
    "punjab", "haryana", "rajasthan", "delhi", "uttar", "pradesh", "india",
    "mandi", "packhouse", "cold", "store", "storage", "hub", "terminal",
    "logistics", "center", "centre", "godown", "warehouse", "farm", "estate",
    "market", "wholesale", "apmc", "ca", "integrated", "post", "harvest",
    "checkpoint", "bypass", "road", "transit", "corridor", "depot", "complex",
}


def _score_place_relevance(
    q_clean: str,
    q_tokens: List[str],
    distinctive_tokens: List[str],
    place: Dict[str, Any],
) -> int:
    """Calculates relevance score for a place candidate against a query."""
    if not q_tokens:
        return 0

    name_lower = place.get("name", "").lower()
    disp_lower = place.get("display_name", "").lower()
    dist_lower = place.get("district", "").lower()
    state_lower = place.get("state", "").lower()
    aliases = [a.lower() for a in place.get("aliases", [])]

    # Exact match on name or any alias
    if q_clean == name_lower or any(q_clean == a for a in aliases):
        return 1000

    score = 0
    # Full substring match
    if q_clean in name_lower or name_lower in q_clean:
        score += 500
    for a in aliases:
        if q_clean in a or a in q_clean:
            score += 450
            break
    if q_clean in disp_lower:
        score += 300

    matched_distinctive = 0

    for token in q_tokens:
        is_distinctive = token in distinctive_tokens
        tok_matched = False

        if token in name_lower or any(token in a for a in aliases):
            score += 200 if is_distinctive else 20
            tok_matched = True

        if dist_lower and token in dist_lower:
            score += 150 if is_distinctive else 15
            tok_matched = True

        if disp_lower and token in disp_lower:
            score += 80 if is_distinctive else 10
            tok_matched = True

        if state_lower and token == state_lower:
            score += 10

        if is_distinctive and tok_matched:
            matched_distinctive += 1

    # If the query had distinctive location tokens (e.g. "bathinda"), but NONE matched this place,
    # discard this candidate so a state-only match ("punjab") does not pollute the results.
    if distinctive_tokens and matched_distinctive == 0:
        return 0

    return score


def _try_parse_coordinate_string(q: str) -> Optional[Tuple[float, float]]:
    """Attempts to parse a 'lat, lon' or 'lat lon' coordinate string."""
    parts = re.split(r"[,;\s]+", q.strip())
    if len(parts) == 2:
        try:
            lat = float(parts[0])
            lon = float(parts[1])
            if is_within_india(lat, lon):
                return lat, lon
        except (ValueError, TypeError):
            pass
    return None


class GeocodingService:
    """Geocoding service with local cache, repository facilities, and OSM Nominatim lookup."""

    def __init__(self):
        self._cache: Dict[str, List[Dict[str, Any]]] = {}
        self._single_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self._last_osm_call_time: float = 0.0
        self._nominatim_available: bool = True
        self._nominatim_retry_after: float = 0.0

    def clear_cache(self) -> None:
        """Clears in-memory search and geocoding caches."""
        self._cache.clear()
        self._single_cache.clear()

    def search_locations(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Searches Indian agricultural locations by name, district, or keyword.
        Prioritizes curated local mandis/facilities by relevance score and falls back to OSM Nominatim.
        """
        q = query.strip()
        if not q or len(q) < 2:
            return []

        q_lower = q.lower()
        if q_lower in self._cache:
            return self._cache[q_lower][:limit]

        # 0. Check if query is direct coordinates
        coord_pair = _try_parse_coordinate_string(q)
        if coord_pair is not None:
            c_lat, c_lon = coord_pair
            direct_coord_res = [{
                "name": f"Coordinate ({c_lat:.4f}, {c_lon:.4f})",
                "display_name": f"Coordinate Location ({c_lat:.4f}° N, {c_lon:.4f}° E)",
                "latitude": c_lat,
                "longitude": c_lon,
                "type": "coordinate",
                "state": "India",
                "source": "coordinate_input",
            }]
            self._cache[q_lower] = direct_coord_res
            return direct_coord_res

        q_clean = q_lower
        q_tokens = [w for w in re.split(r"[\s,._/\\-]+", q_clean) if len(w) >= 2]
        distinctive_tokens = [t for t in q_tokens if t not in GENERIC_AGRI_KEYWORDS]

        scored_candidates: List[Tuple[int, Dict[str, Any]]] = []
        seen_coords: Set[Tuple[float, float]] = set()

        # 1. Search in curated places
        for place in CURATED_AGRICULTURAL_PLACES:
            score = _score_place_relevance(q_clean, q_tokens, distinctive_tokens, place)
            if score > 0:
                lat = float(place["latitude"])
                lon = float(place["longitude"])
                coord_key = (round(lat, 3), round(lon, 3))
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    scored_candidates.append((score, {
                        "name": place["name"],
                        "display_name": place.get("display_name", place["name"]),
                        "latitude": lat,
                        "longitude": lon,
                        "type": place.get("type", "location"),
                        "state": place.get("state", "India"),
                        "source": "curated_agri_directory",
                    }))

        # 2. Search in repository facilities
        try:
            from app.db.repository import get_shipment_repository
            repo = get_shipment_repository()
            facilities = repo.list_facilities()
            for fac in facilities:
                fac_lat = fac.get("latitude")
                fac_lon = fac.get("longitude")
                if fac_lat is not None and fac_lon is not None:
                    try:
                        f_lat = float(fac_lat)
                        f_lon = float(fac_lon)
                    except (ValueError, TypeError):
                        continue

                    fac_place = {
                        "name": fac.get("name", ""),
                        "display_name": f"{fac.get('name', '')}, {fac.get('address', '')}",
                        "district": fac.get("district", ""),
                        "state": fac.get("state", "Punjab"),
                        "type": fac.get("facility_type", "facility"),
                    }
                    score = _score_place_relevance(q_clean, q_tokens, distinctive_tokens, fac_place)
                    if score > 0:
                        coord_key = (round(f_lat, 3), round(f_lon, 3))
                        if coord_key not in seen_coords:
                            seen_coords.add(coord_key)
                            scored_candidates.append((score, {
                                "name": fac.get("name", ""),
                                "display_name": fac_place["display_name"],
                                "latitude": f_lat,
                                "longitude": f_lon,
                                "type": fac.get("facility_type", "facility"),
                                "state": fac.get("state", "Punjab"),
                                "source": "facility_repository",
                            }))
        except Exception as exc:
            logger.debug("Facility repo lookup skipped: %s", exc)

        # Sort candidates descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        results = [cand[1] for cand in scored_candidates]

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

    def geocode_location(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes a location query into a single verified Indian geographic coordinate dict.
        Resolves coordinates from curated agricultural landmarks, facilities, or Nominatim.

        Returns:
            Dict with 'name', 'display_name', 'latitude', 'longitude', 'type', 'state', 'source'
            or None if unresolvable.
        """
        q = (query or "").strip()
        if not q or len(q) < 2:
            return None

        q_lower = q.lower()
        if q_lower in self._single_cache:
            return self._single_cache[q_lower]

        # 1. Check direct coordinates
        coord_pair = _try_parse_coordinate_string(q)
        if coord_pair is not None:
            c_lat, c_lon = coord_pair
            direct_res = {
                "name": f"Coordinate ({c_lat:.4f}, {c_lon:.4f})",
                "display_name": f"Coordinate Location ({c_lat:.4f}° N, {c_lon:.4f}° E)",
                "latitude": c_lat,
                "longitude": c_lon,
                "type": "coordinate",
                "state": "India",
                "source": "coordinate_input",
            }
            self._single_cache[q_lower] = direct_res
            return direct_res

        # 2. Search candidates via search_locations
        candidates = self.search_locations(q, limit=5)
        for cand in candidates:
            lat = cand.get("latitude")
            lon = cand.get("longitude")
            if lat is not None and lon is not None:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    if is_within_india(f_lat, f_lon):
                        resolved = {
                            "name": cand.get("name") or q,
                            "display_name": cand.get("display_name") or cand.get("name") or q,
                            "latitude": f_lat,
                            "longitude": f_lon,
                            "type": cand.get("type", "location"),
                            "state": cand.get("state", "India"),
                            "source": cand.get("source", "curated_agri_directory"),
                        }
                        self._single_cache[q_lower] = resolved
                        return resolved
                except (ValueError, TypeError):
                    continue

        # 3. Direct Nominatim fallback if search_locations yielded nothing
        osm_matches = self._query_osm_nominatim(q, limit=3)
        for item in osm_matches:
            lat = item.get("latitude")
            lon = item.get("longitude")
            if lat is not None and lon is not None:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    if is_within_india(f_lat, f_lon):
                        self._single_cache[q_lower] = item
                        return item
                except (ValueError, TypeError):
                    continue

        self._single_cache[q_lower] = None
        return None

    # Backward compatibility alias
    geocode = geocode_location

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
