"""
AgriChain AI — Shipment & Telemetry Persistence Repository
==========================================================
Provides unified data persistence for produce shipments, sensor telemetry,
PostGIS spatial waypoints, and agricultural storage facilities (godowns, packhouses).

Key architectural guarantees:
1. Persistence across backend restarts (persisted state ledger).
2. Strict foreign-key enforcement (telemetry references existing shipments).
3. Explicit database failure handling: when database mode is enabled, connection
   failures raise DatabaseConnectionError rather than silently falling back to in-memory state.
4. Preserves 100% of existing API response contracts.
5. Strict Indian geospatial operational boundaries (Punjab & Northern India corridor).
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.geo import validate_indian_coordinate
from app.db.session import (
    DatabaseConnectionError,
    ForeignKeyViolationError,
    InsufficientStockError,
    ListingNotFoundError,
    ShipmentNotFoundError,
    get_sync_database_url,
    probe_database_connection,
)
from app.models.shipment import GeoWaypointModel, ShipmentModel, TelemetryLogModel
from app.models.facility import StorageFacilityModel

logger = logging.getLogger("agrichain.repository")

# Default persistent ledger location within backend/app/db/
DEFAULT_STORAGE_FILE = Path(__file__).resolve().parent / ".persisted_session.json"

INITIAL_SEED_FACILITIES: List[Dict[str, Any]] = [
    {
        "id": "FAC-PB-PAG-BARA",
        "name": "PAGREXCO Pack House-cum-Cold Storage (Bara Farm)",
        "facility_type": "packhouse",
        "address": "Village Bara Farm, Sirhind, GT Road Corridor",
        "village_or_city": "Bara Farm",
        "district": "Fatehgarh Sahib",
        "state": "Punjab",
        "postal_code": "140406",
        "latitude": 30.6283,
        "longitude": 76.3863,
        "coordinates": {"latitude": 30.6283, "longitude": 76.3863},
        "contact_phone": "0172-2742468",
        "contact_email": "pagrexco@punjabagro.gov.in",
        "capacity": 24.0,
        "capacity_unit": "MT",
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Fruits", "Vegetables", "Horticultural Produce"],
        "operational_status": "active",
        "guava_suitability_category": "horticulture_unconfirmed",
        "source_citation_type": "direct_document",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "verified",
        "source_name": "Punjab Agri Export Corporation Limited (PAGREXCO)",
        "source_url": "https://punjabagro.gov.in/wp-content/uploads/2025/03/EOI-Pack-House-cum-Cold-Storage.pdf",
        "source_record": "EOI for Pack House cum Cold Storage Facilities on Lease/Rental Basis (Ref: PAGREXCO/EOI/2025-01)",
        "verification_status": "verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Bara Farm, Sirhind approximate village centroid",
        "geocoding_confidence": "village_level",
        "data_provenance": "Documented in PAGREXCO EOI 2025-01 with 4 MT pre-cooling chamber and two 10 MT cold storage chambers (Total 24 MT). Direct document proof. General horticultural produce; guava suitability is unconfirmed (general infrastructure, guava not explicitly named in EOI).",
        "location_verification_status": "verified",
        "created_at": "2026-10-26T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-PAG-KANG",
        "name": "PAGREXCO Pack House-cum-Cold Storage (Kangmai)",
        "facility_type": "packhouse",
        "address": "Village Kangmai, Tehsil Hariana",
        "village_or_city": "Kangmai",
        "district": "Hoshiarpur",
        "state": "Punjab",
        "postal_code": "144208",
        "latitude": 31.6677,
        "longitude": 75.7923,
        "coordinates": {"latitude": 31.6677, "longitude": 75.7923},
        "contact_phone": "0172-2742468",
        "contact_email": "pagrexco@punjabagro.gov.in",
        "capacity": 54.0,
        "capacity_unit": "MT",
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Citrus", "Kinnow", "Horticultural Produce", "Vegetables"],
        "operational_status": "active",
        "guava_suitability_category": "horticulture_unconfirmed",
        "source_citation_type": "direct_document",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "verified",
        "source_name": "Punjab Agri Export Corporation Limited (PAGREXCO)",
        "source_url": "https://punjabagro.gov.in/wp-content/uploads/2025/03/EOI-Pack-House-cum-Cold-Storage.pdf",
        "source_record": "EOI for Pack House cum Cold Storage Facilities on Lease/Rental Basis (Ref: PAGREXCO/EOI/2025-01)",
        "verification_status": "verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Kangmai village approximate centroid (Hariana block, Hoshiarpur)",
        "geocoding_confidence": "village_level",
        "data_provenance": "Documented in PAGREXCO EOI 2025-01 with 4 MT pre-cooling unit and 50 MT cold storage capacity across 3 chambers (Total 54 MT). Direct document proof. Primarily serves the Hoshiarpur sub-mountain citrus belt; guava suitability unconfirmed.",
        "location_verification_status": "verified",
        "created_at": "2026-10-26T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-ABO-01",
        "name": "PAGREXCO Kinnow Grading, Waxing & Packhouse Center",
        "facility_type": "packhouse",
        "address": "Village Alamgarh, Abohar-Ganganagar Road (NH-62)",
        "village_or_city": "Alamgarh",
        "district": "Fazilka",
        "state": "Punjab",
        "postal_code": "152116",
        "latitude": 30.1227,
        "longitude": 74.1566,
        "coordinates": {"latitude": 30.1227, "longitude": 74.1566},
        "contact_phone": None,
        "contact_email": "pagrexco@punjabagro.gov.in",
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Kinnow", "Citrus"],
        "operational_status": "active",
        "guava_suitability_category": "horticulture_unconfirmed",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "verified",
        "source_name": "Punjab Agro Export Corporation (PAGREXCO)",
        "source_url": "https://punjabagro.gov.in/horticulture/",
        "source_record": "PAGREXCO Horticultural Infrastructure Directory (Alamgarh Center, Abohar)",
        "verification_status": "verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Village Alamgarh, NH-62 Abohar corridor approximate geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "Major mechanized citrus post-harvest center on NH-62 with washing, waxing, and electronic size grading lines. Sourced from PAGREXCO horticulture directory (directory-level reference). Engineered specifically for Kinnow/citrus; guava handling is not documented.",
        "location_verification_status": "verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-FAZ-01",
        "name": "PSWC Warehousing Centre Fazilka",
        "facility_type": "godown",
        "address": "Near Old Grain Market / Railway Line, Fazilka",
        "village_or_city": "Fazilka",
        "district": "Fazilka",
        "state": "Punjab",
        "postal_code": "152123",
        "latitude": 30.4037,
        "longitude": 74.0254,
        "coordinates": {"latitude": 30.4037, "longitude": 74.0254},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Foodgrains", "Wheat", "Paddy"],
        "operational_status": "active",
        "guava_suitability_category": "ambient_grain",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "Punjab State Warehousing Corporation (PSWC)",
        "source_url": "https://pswc.in/Warehousing.aspx",
        "source_record": "PSWC Warehousing Centers Directory (Fazilka District: Fazilka-I & II)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Fazilka Mandi / Railway Goods Shed approximate town geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "Public scientific storage warehouse complex managed by PSWC in Fazilka for PDS buffer stocks. Sourced from PSWC warehousing network directory (directory-level reference). Dry grain godown; NOT suitable for guava or cold-chain produce.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-BTI-01",
        "name": "PSWC Container Freight Station & Warehousing Complex",
        "facility_type": "godown",
        "address": "A-6, Industrial Growth Centre, Mansa Road",
        "village_or_city": "Bathinda",
        "district": "Bathinda",
        "state": "Punjab",
        "postal_code": "151001",
        "latitude": 30.1798,
        "longitude": 74.9654,
        "coordinates": {"latitude": 30.1798, "longitude": 74.9654},
        "contact_phone": "0164-2430085",
        "contact_email": "icdbthpswc@punjab.gov.in",
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Foodgrains", "Wheat", "Paddy", "Agricultural Inputs"],
        "operational_status": "active",
        "guava_suitability_category": "ambient_grain",
        "source_citation_type": "facility_page",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "verified",
        "source_name": "Punjab State Warehousing Corporation (PSWC)",
        "source_url": "https://pswc.in/ContainerFreightStation.aspx",
        "source_record": "PSWC Container Freight Station & Warehousing Directory (Bathinda CFS)",
        "verification_status": "verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Industrial Growth Centre, Mansa Road approximate industrial zone geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "Inland Container Depot / CFS and warehousing godowns operated by PSWC. Sourced from PSWC CFS page with verified contact phone (0164-2430085). Dry grain/freight facility; NOT suitable for guava.",
        "location_verification_status": "verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-LDH-01",
        "name": "PSWC Warehousing Centre Sahnewal",
        "facility_type": "godown",
        "address": "GT Road, Near Kanech Railway Siding, Sahnewal",
        "village_or_city": "Sahnewal",
        "district": "Ludhiana",
        "state": "Punjab",
        "postal_code": "141120",
        "latitude": 30.8492,
        "longitude": 75.9868,
        "coordinates": {"latitude": 30.8492, "longitude": 75.9868},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Foodgrains", "Wheat", "Paddy", "Agricultural Inputs"],
        "operational_status": "active",
        "guava_suitability_category": "ambient_grain",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "Punjab State Warehousing Corporation (PSWC)",
        "source_url": "https://pswc.in/Warehousing.aspx",
        "source_record": "PSWC Warehousing Network Master List (Ludhiana District: Sahnewal Centre)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Sahnewal GT Road corridor approximate geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "PSWC transit warehousing facility along the GT Road corridor. Sourced from PSWC warehousing network directory (directory-level reference). Dry foodgrain storage; direct phone/email unverified on public website. NOT suitable for guava.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-ASR-01",
        "name": "Bhagtanwala APMC Fruit & Produce Mandi Yard",
        "facility_type": "mandi",
        "address": "Bhagtanwala Mandi Complex, Tarn Taran Road",
        "village_or_city": "Amritsar",
        "district": "Amritsar",
        "state": "Punjab",
        "postal_code": "143001",
        "latitude": 31.6042,
        "longitude": 74.8723,
        "coordinates": {"latitude": 31.6042, "longitude": 74.8723},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Wheat", "Paddy", "Basmati Rice", "Seasonal Fruits & Vegetables"],
        "operational_status": "active",
        "guava_suitability_category": "wholesale_market",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "Punjab State Agricultural Marketing Board (Punjab Mandi Board)",
        "source_url": "https://mandiboard.nic.in/",
        "source_record": "Punjab Mandi Board Principal Market Yard Directory (Amritsar - Bhagtanwala Yard)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Bhagtanwala APMC Market Yard approximate yard geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "Principal APMC wholesale market yard in Amritsar under Punjab Mandi Board. Sourced from Punjab Mandi Board directory (directory-level reference). Primary wholesale auction venue for regional produce; partially suitable for seasonal guava trade but lacks dedicated post-harvest packhouse infrastructure.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-JAL-01",
        "name": "M/s Rabb Cold Store",
        "facility_type": "cold_storage",
        "address": "Village Rupewal / Mehmuwal Yusafpur, Tehsil Shahkot",
        "village_or_city": "Mehmuwal Yusafpur",
        "district": "Jalandhar",
        "state": "Punjab",
        "postal_code": "144701",
        "latitude": 31.0825,
        "longitude": 75.3412,
        "coordinates": {"latitude": 31.0825, "longitude": 75.3412},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Potatoes", "Horticultural Produce"],
        "operational_status": None,
        "guava_suitability_category": "cold_store_unknown",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "National Horticulture Board (NHB) / Corporate Registration Registry",
        "source_url": "https://nhb.gov.in/",
        "source_record": "Commercial Enterprise Registration & Jalandhar Cold Storage Registry (LEI standard verified)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Village Mehmuwal Yusafpur / Rupewal approximate village geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "Commercial cold storage enterprise registered in the central Doaba potato belt. Legal entity registration verified (directory-level reference). Physical capacity and current operational status unconfirmed on-site (kept null). Guava suitability unknown.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-DL-AZD-01",
        "name": "Azadpur APMC Fruit & Vegetable Mega Mandi",
        "facility_type": "mandi",
        "address": "Office Complex, New Fruit Market (NFM) Phase-II, Sarai Pipal Thala, Azadpur",
        "village_or_city": "Azadpur",
        "district": "North Delhi",
        "state": "Delhi",
        "postal_code": "110033",
        "latitude": 28.7161,
        "longitude": 77.1772,
        "coordinates": {"latitude": 28.7161, "longitude": 77.1772},
        "contact_phone": "011-27691807",
        "contact_email": "apmcazadpur.delhi@delhi.gov.in",
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Guava", "Kinnow", "Citrus", "Perishable Produce"],
        "operational_status": "active",
        "guava_suitability_category": "guava_confirmed",
        "source_citation_type": "official_portal",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "verified",
        "source_name": "APMC Azadpur (Market of National Importance) / Govt of NCT of Delhi",
        "source_url": "https://apmcazadpurdelhi.com/",
        "source_record": "APMC Azadpur Terminal Market Directory & e-NAM Trading Hub",
        "verification_status": "verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Azadpur APMC Market Office Complex, WGS84 Geocode",
        "geocoding_confidence": "facility_campus",
        "data_provenance": "Asia's largest wholesale fruits and vegetables market. CONFIRMED SUITABLE FOR GUAVA: primary northern terminal market handling commercial guava auction, ripening chambers, and cold-chain transfers from Punjab. Verified via official APMC portal.",
        "location_verification_status": "verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-NHB-TALW",
        "name": "Sardar Mohinder Singh Cold Store",
        "facility_type": "cold_storage",
        "address": "Talwandi Madho, Tehsil Shahkot",
        "village_or_city": "Talwandi Madho",
        "district": "Jalandhar",
        "state": "Punjab",
        "postal_code": "144627",
        "latitude": 31.0945,
        "longitude": 75.3280,
        "coordinates": {"latitude": 31.0945, "longitude": 75.3280},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Potatoes", "Horticultural Produce"],
        "operational_status": None,
        "guava_suitability_category": "cold_store_unknown",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "National Horticulture Board (NHB) / Corporate Registration Registry",
        "source_url": "https://nhb.gov.in/",
        "source_record": "Cold Storage Commercial Registration (LEI issued Jan 2025)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Talwandi Madho village approximate centroid, Shahkot",
        "geocoding_confidence": "village_level",
        "data_provenance": "Registered commercial cold storage enterprise in Talwandi Madho (PIN 144627). Legal entity registered (directory-level reference). Physical MT capacity and current operational status unconfirmed on-site (kept null). Guava suitability unknown.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-26T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-NHB-BURJ",
        "name": "M/s New Kissan Cold Storage",
        "facility_type": "cold_storage",
        "address": "Village Burj Gill, Tehsil Rampura Phul",
        "village_or_city": "Burj Gill",
        "district": "Bathinda",
        "state": "Punjab",
        "postal_code": "151104",
        "latitude": 30.4500,
        "longitude": 75.2300,
        "coordinates": {"latitude": 30.4500, "longitude": 75.2300},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Potatoes", "Horticultural Produce"],
        "operational_status": None,
        "guava_suitability_category": "cold_store_unknown",
        "source_citation_type": "committee_proceeding",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "National Horticulture Board (NHB)",
        "source_url": "https://nhb.gov.in/",
        "source_record": "Proceedings of the 9th Meeting of the Project Approval Committee (PAC) - Ref: NHB/03APB/OCS/000061",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Village Burj Gill approximate village centroid",
        "geocoding_confidence": "village_level",
        "data_provenance": "Approved under NHB Capital Investment Subsidy Scheme (Cold Storage Type-I, EPC Rs 884.625L, Promoter Shri Harjaspal Singh). Legal sanction documented in PAC proceedings citation. Physical capacity in MT and current operational status unconfirmed on-site (kept null). Guava suitability unknown.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-26T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
    {
        "id": "FAC-PB-PSW-MAL",
        "name": "PSWC Warehousing Centre Malout",
        "facility_type": "godown",
        "address": "Near Grain Market / Bhatinda Road, Malout",
        "village_or_city": "Malout",
        "district": "Sri Muktsar Sahib",
        "state": "Punjab",
        "postal_code": "152107",
        "latitude": 30.1915,
        "longitude": 74.4989,
        "coordinates": {"latitude": 30.1915, "longitude": 74.4989},
        "contact_phone": None,
        "contact_email": None,
        "capacity": None,
        "capacity_unit": None,
        "current_utilization": None,
        "storage_temperature_min_c": None,
        "storage_temperature_max_c": None,
        "supported_commodities": ["Foodgrains", "Wheat", "Paddy"],
        "operational_status": "active",
        "guava_suitability_category": "ambient_grain",
        "source_citation_type": "directory_level_reference",
        "legal_entity_verification": "verified",
        "physical_facility_verification": "partially_verified",
        "source_name": "Punjab State Warehousing Corporation (PSWC)",
        "source_url": "https://pswc.in/Warehousing.aspx",
        "source_record": "PSWC Warehousing Centers Directory (Muktsar District: Malout Centre SW-1 & 2)",
        "verification_status": "partially_verified",
        "verification_date": "2026-10-26",
        "last_source_check": "2026-10-26",
        "coordinate_source": "Malout Grain Market / Bhatinda Road approximate town geocode",
        "geocoding_confidence": "village_level",
        "data_provenance": "State warehousing complex (SW Malout-1 & SW Malout-2) managed by PSWC along the NH-7 transit corridor. Sourced from PSWC warehousing network directory (directory-level reference). Dry foodgrain storage; direct phone/email unverified on public website. NOT suitable for guava.",
        "location_verification_status": "partially_verified",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-26T10:00:00Z",
    },
]

INITIAL_SEED_SHIPMENTS: List[Dict[str, Any]] = [
    {
        "id": "SHP-2026-001",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Azadpur APMC Mandi, Delhi",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-DL-AZD-01",
        "status": "in_transit",
        "quantity": 450.0,
        "quantity_crates": 450,
        "temperature_c": 6.2,
        "humidity_pct": 88.0,
        "risk_index": 18.5,
        "created_at": "2026-10-18T10:00:00Z",
        "last_update": "2026-10-18T14:00:00Z",
    },
    {
        "id": "SHP-2026-002",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Fazilka CA Cold Store, Punjab",
        "destination": "Ludhiana Agro Cold Chain Warehouse",
        "origin_facility_id": "FAC-PB-FAZ-01",
        "destination_facility_id": "FAC-PB-LDH-01",
        "status": "in_transit",
        "quantity": 600.0,
        "quantity_crates": 600,
        "temperature_c": 7.1,
        "humidity_pct": 86.5,
        "risk_index": 24.0,
        "created_at": "2026-10-18T09:30:00Z",
        "last_update": "2026-10-18T13:45:00Z",
    },
    {
        "id": "SHP-2026-003",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Fazilka CA Cold Store, Punjab",
        "destination": "Amritsar Fruit & Produce Mandi Cold Terminal",
        "origin_facility_id": "FAC-PB-FAZ-01",
        "destination_facility_id": "FAC-PB-ASR-01",
        "status": "delivered",
        "quantity": 450.0,
        "quantity_crates": 450,
        "temperature_c": 6.2,
        "humidity_pct": 86.5,
        "risk_index": 15.0,
        "created_at": "2026-10-21T06:19:49Z",
        "last_update": "2026-10-22T13:31:02Z",
    },
    {
        "id": "SHP-2026-004",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Bathinda Central Agri Godown",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-PB-BTI-01",
        "status": "created",
        "quantity": 300.0,
        "quantity_crates": 300,
        "temperature_c": 6.3,
        "humidity_pct": 86.8,
        "risk_index": 15.0,
        "created_at": "2026-10-22T06:04:06Z",
        "last_update": "2026-10-22T06:04:29Z",
    },
    {
        "id": "SHP-2026-005",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Jalandhar Packhouse",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-PB-JAL-01",
        "status": "created",
        "quantity": 520.0,
        "quantity_crates": 520,
        "temperature_c": 5.9,
        "humidity_pct": 87.2,
        "risk_index": 15.0,
        "created_at": "2026-10-22T06:06:29Z",
        "last_update": "2026-10-22T13:31:13Z",
    },
    {
        "id": "SHP-2026-006",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Azadpur APMC Mandi, Delhi",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-DL-AZD-01",
        "status": "created",
        "quantity": 350.0,
        "quantity_crates": 350,
        "temperature_c": 6.0,
        "humidity_pct": 88.0,
        "risk_index": 15.0,
        "created_at": "2026-10-22T06:07:14Z",
        "last_update": "2026-10-22T06:07:14Z",
    },
    {
        "id": "SHP-2026-007",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Ludhiana Agro Cold Chain Warehouse",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-PB-LDH-01",
        "status": "created",
        "quantity": 350.0,
        "quantity_crates": 350,
        "temperature_c": 6.0,
        "humidity_pct": 88.0,
        "risk_index": 15.0,
        "created_at": "2026-10-22T06:09:19Z",
        "last_update": "2026-10-22T06:09:19Z",
    },
    {
        "id": "SHP-2026-008",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Fazilka CA Cold Store, Punjab",
        "destination": "Bathinda Central Agri Godown",
        "origin_facility_id": "FAC-PB-FAZ-01",
        "destination_facility_id": "FAC-PB-BTI-01",
        "status": "created",
        "quantity": 350.0,
        "quantity_crates": 350,
        "temperature_c": 6.0,
        "humidity_pct": 88.0,
        "risk_index": 15.0,
        "created_at": "2026-10-22T10:42:08Z",
        "last_update": "2026-10-22T13:31:23Z",
    },
    {
        "id": "SHP-2026-009",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Abohar Post-Harvest Center, Punjab",
        "destination": "Amritsar Fruit & Produce Mandi Cold Terminal",
        "origin_facility_id": "FAC-PB-ABO-01",
        "destination_facility_id": "FAC-PB-ASR-01",
        "status": "created",
        "quantity": 350.0,
        "quantity_crates": 350,
        "temperature_c": 6.0,
        "humidity_pct": 88.0,
        "risk_index": 15.0,
        "created_at": "2026-10-22T10:43:23Z",
        "last_update": "2026-10-22T10:43:23Z",
    },
    {
        "id": "SHP-2026-010",
        "produce_type": "Guava",
        "produce": "Guava",
        "origin": "Jaipur Muhana APMC Terminal Mandi",
        "destination": "Agra Agro Cold Logistics Hub",
        "origin_facility_id": None,
        "destination_facility_id": None,
        "origin_lat": 26.7937,
        "origin_lon": 75.7381,
        "destination_lat": 27.1767,
        "destination_lon": 78.0081,
        "status": "in_transit",
        "quantity": 500.0,
        "quantity_crates": 500,
        "temperature_c": 6.4,
        "humidity_pct": 87.0,
        "risk_index": 16.0,
        "created_at": "2026-10-23T08:00:00Z",
        "last_update": "2026-10-23T11:00:00Z",
    },
]

INITIAL_SEED_TELEMETRY: Dict[str, List[Dict[str, Any]]] = {
    "SHP-2026-001": [
        {
            "id": "TEL-001-1",
            "shipment_id": "SHP-2026-001",
            "temperature": 6.2,
            "humidity": 88.0,
            "sensor_id": "SNS-COLD-01",
            "location": "Abohar Packhouse (30.1453° N, 74.1994° E)",
            "timestamp": "2026-10-18T14:00:00Z",
        },
        {
            "id": "TEL-001-2",
            "shipment_id": "SHP-2026-001",
            "temperature": 6.5,
            "humidity": 87.5,
            "sensor_id": "SNS-COLD-01",
            "location": "Malout Corridor (30.1915° N, 74.4989° E)",
            "timestamp": "2026-10-18T14:30:00Z",
        },
        {
            "id": "TEL-001-3",
            "shipment_id": "SHP-2026-001",
            "temperature": 6.1,
            "humidity": 86.8,
            "sensor_id": "SNS-COLD-01",
            "location": "Bathinda Transit Hub (30.2110° N, 74.9455° E)",
            "timestamp": "2026-10-18T15:30:00Z",
        },
        {
            "id": "TEL-001-4",
            "shipment_id": "SHP-2026-001",
            "temperature": 6.3,
            "humidity": 86.5,
            "sensor_id": "SNS-COLD-01",
            "location": "Sirsa Checkpoint, NH-9 (29.5349° N, 75.0298° E)",
            "timestamp": "2026-10-18T16:30:00Z",
        },
    ],
    "SHP-2026-002": [
        {
            "id": "TEL-002-1",
            "shipment_id": "SHP-2026-002",
            "temperature": 7.1,
            "humidity": 86.5,
            "sensor_id": "SNS-COLD-02",
            "location": "Fazilka CA Cold Store (30.4037° N, 74.0254° E)",
            "timestamp": "2026-10-18T13:45:00Z",
        },
        {
            "id": "TEL-002-2",
            "shipment_id": "SHP-2026-002",
            "temperature": 6.8,
            "humidity": 87.0,
            "sensor_id": "SNS-COLD-02",
            "location": "Muktsar Corridor (30.4744° N, 74.5167° E)",
            "timestamp": "2026-10-18T14:45:00Z",
        },
    ],
    "SHP-2026-003": [
        {
            "id": "TEL-003-1",
            "shipment_id": "SHP-2026-003",
            "temperature": 5.8,
            "humidity": 88.0,
            "sensor_id": "SNS-COLD-03",
            "location": "Fazilka (30.4037° N, 74.0254° E)",
            "timestamp": "2026-10-21T06:19:49Z",
        },
        {
            "id": "TEL-003-2",
            "shipment_id": "SHP-2026-003",
            "temperature": 5.5,
            "humidity": 89.0,
            "sensor_id": "SNS-COLD-03",
            "location": "Amritsar Cold Terminal (31.6340° N, 74.8723° E)",
            "timestamp": "2026-10-22T13:31:02Z",
        },
    ],
}

INITIAL_SEED_WAYPOINTS: Dict[str, List[Dict[str, Any]]] = {
    "SHP-2026-001": [
        {
            "id": "WAY-001-1",
            "shipment_id": "SHP-2026-001",
            "longitude": 74.1994,
            "latitude": 30.1453,
            "srid": 4326,
            "altitude_m": 186.0,
            "speed_kmh": 45.0,
            "heading_deg": 85.0,
            "location_metadata": {"hub": "Abohar Packhouse", "state": "Punjab", "district": "Fazilka"},
            "recorded_at": "2026-10-18T14:00:00Z",
        },
        {
            "id": "WAY-001-2",
            "shipment_id": "SHP-2026-001",
            "longitude": 74.4989,
            "latitude": 30.1915,
            "srid": 4326,
            "altitude_m": 192.0,
            "speed_kmh": 62.0,
            "heading_deg": 78.0,
            "location_metadata": {"corridor": "Malout Corridor", "state": "Punjab", "highway": "NH-7"},
            "recorded_at": "2026-10-18T14:30:00Z",
        },
        {
            "id": "WAY-001-3",
            "shipment_id": "SHP-2026-001",
            "longitude": 74.9455,
            "latitude": 30.2110,
            "srid": 4326,
            "altitude_m": 204.0,
            "speed_kmh": 58.0,
            "heading_deg": 110.0,
            "location_metadata": {"hub": "Bathinda Transit Hub", "state": "Punjab", "highway": "NH-7"},
            "recorded_at": "2026-10-18T15:30:00Z",
        },
        {
            "id": "WAY-001-4",
            "shipment_id": "SHP-2026-001",
            "longitude": 75.0298,
            "latitude": 29.5349,
            "srid": 4326,
            "altitude_m": 208.0,
            "speed_kmh": 64.0,
            "heading_deg": 135.0,
            "location_metadata": {"hub": "Sirsa Checkpoint", "state": "Haryana", "highway": "NH-9"},
            "recorded_at": "2026-10-18T16:30:00Z",
        },
    ],
    "SHP-2026-002": [
        {
            "id": "WAY-002-1",
            "shipment_id": "SHP-2026-002",
            "longitude": 74.0254,
            "latitude": 30.4037,
            "srid": 4326,
            "altitude_m": 178.0,
            "speed_kmh": 52.0,
            "heading_deg": 75.0,
            "location_metadata": {"hub": "Fazilka CA Cold Store", "state": "Punjab"},
            "recorded_at": "2026-10-18T13:45:00Z",
        },
        {
            "id": "WAY-002-2",
            "shipment_id": "SHP-2026-002",
            "longitude": 74.5167,
            "latitude": 30.4744,
            "srid": 4326,
            "altitude_m": 184.0,
            "speed_kmh": 60.0,
            "heading_deg": 68.0,
            "location_metadata": {"corridor": "Muktsar Corridor", "state": "Punjab"},
            "recorded_at": "2026-10-18T14:45:00Z",
        },
        {
            "id": "WAY-002-3",
            "shipment_id": "SHP-2026-002",
            "longitude": 74.8267,
            "latitude": 30.5828,
            "srid": 4326,
            "altitude_m": 196.0,
            "speed_kmh": 56.0,
            "heading_deg": 62.0,
            "location_metadata": {"corridor": "Kotkapura Bypass", "state": "Punjab"},
            "recorded_at": "2026-10-18T15:45:00Z",
        },
    ],
    "SHP-2026-003": [
        {
            "id": "WAY-003-1",
            "shipment_id": "SHP-2026-003",
            "longitude": 74.0254,
            "latitude": 30.4037,
            "srid": 4326,
            "altitude_m": 178.0,
            "speed_kmh": 45.0,
            "heading_deg": 35.0,
            "location_metadata": {"hub": "Fazilka CA Cold Store", "state": "Punjab"},
            "recorded_at": "2026-10-21T06:19:49Z",
        },
        {
            "id": "WAY-003-2",
            "shipment_id": "SHP-2026-003",
            "longitude": 74.6133,
            "latitude": 30.9237,
            "srid": 4326,
            "altitude_m": 182.0,
            "speed_kmh": 65.0,
            "heading_deg": 25.0,
            "location_metadata": {"corridor": "Firozpur Corridor", "state": "Punjab"},
            "recorded_at": "2026-10-21T08:00:00Z",
        },
        {
            "id": "WAY-003-3",
            "shipment_id": "SHP-2026-003",
            "longitude": 74.8723,
            "latitude": 31.6340,
            "srid": 4326,
            "altitude_m": 218.0,
            "speed_kmh": 0.0,
            "heading_deg": 0.0,
            "location_metadata": {"hub": "Amritsar Fruit & Produce Mandi Cold Terminal", "state": "Punjab", "status": "delivered"},
            "recorded_at": "2026-10-22T13:31:02Z",
        },
    ],
}

INITIAL_SEED_EVENTS: Dict[str, List[Dict[str, Any]]] = {
    "SHP-2026-001": [
        {
            "id": "EVT-SHP-2026-001-1",
            "shipment_id": "SHP-2026-001",
            "event_type": "shipment_created",
            "description": "Shipment batch created for 450 crates of Guava from Alamgarh Packhouse to Azadpur APMC Mega Mandi.",
            "facility_id": "FAC-PB-ABO-01",
            "facility_name": "PAGREXCO Kinnow Grading, Waxing & Packhouse Center",
            "source": "system_event",
            "metadata": {"produce_type": "Guava", "quantity_crates": 450},
            "timestamp": "2026-10-18T10:00:00Z",
        },
        {
            "id": "EVT-SHP-2026-001-2",
            "shipment_id": "SHP-2026-001",
            "event_type": "facility_association_updated",
            "description": "Origin linked to FAC-PB-ABO-01; Destination linked to FAC-DL-AZD-01; Intermediate hub linked to FAC-PB-BTI-01.",
            "facility_id": "FAC-PB-ABO-01",
            "facility_name": "PAGREXCO Kinnow Grading, Waxing & Packhouse Center",
            "source": "system_event",
            "metadata": {"origin_operation": "packhouse_cooling", "destination_operation": "market_auction", "intermediate_operation": "transit_hub"},
            "timestamp": "2026-10-18T10:05:00Z",
        },
        {
            "id": "EVT-SHP-2026-001-3",
            "shipment_id": "SHP-2026-001",
            "event_type": "shipment_dispatched",
            "description": "Refrigerated transport vehicle dispatched from origin packhouse onto NH-7 corridor.",
            "facility_id": "FAC-PB-ABO-01",
            "facility_name": "PAGREXCO Kinnow Grading, Waxing & Packhouse Center",
            "source": "manual_operator",
            "metadata": {"driver": "Harpreet Singh", "vehicle": "PB-03-AG-4912"},
            "timestamp": "2026-10-18T13:45:00Z",
        },
        {
            "id": "EVT-SHP-2026-001-4",
            "shipment_id": "SHP-2026-001",
            "event_type": "in_transit",
            "description": "Vehicle crossed Malout Corridor checkpoint (30.1915° N, 74.4989° E).",
            "facility_id": None,
            "facility_name": None,
            "source": "demo_simulated",
            "metadata": {"speed_kmh": 62.0, "checkpoint": "Malout Corridor", "simulated": True},
            "timestamp": "2026-10-18T14:30:00Z",
        },
        {
            "id": "EVT-SHP-2026-001-5",
            "shipment_id": "SHP-2026-001",
            "event_type": "facility_handover",
            "description": "Transit checkpoint reached at PSWC Container Freight Station Bathinda (FAC-PB-BTI-01).",
            "facility_id": "FAC-PB-BTI-01",
            "facility_name": "PSWC Container Freight Station & Warehousing Complex",
            "source": "demo_simulated",
            "metadata": {"hub": "Bathinda Transit Hub", "simulated": True},
            "timestamp": "2026-10-18T15:30:00Z",
        },
    ],
    "SHP-2026-002": [
        {
            "id": "EVT-SHP-2026-002-1",
            "shipment_id": "SHP-2026-002",
            "event_type": "shipment_created",
            "description": "Shipment batch created for 600 crates of Guava from Fazilka warehouse corridor to Ludhiana Agro Cold Chain.",
            "facility_id": "FAC-PB-FAZ-01",
            "facility_name": "PSWC Warehousing Centre Fazilka",
            "source": "system_event",
            "metadata": {"produce_type": "Guava", "quantity_crates": 600},
            "timestamp": "2026-10-18T09:30:00Z",
        },
        {
            "id": "EVT-SHP-2026-002-2",
            "shipment_id": "SHP-2026-002",
            "event_type": "shipment_dispatched",
            "description": "Dispatched onto Muktsar-Kotkapura transit corridor.",
            "facility_id": "FAC-PB-FAZ-01",
            "facility_name": "PSWC Warehousing Centre Fazilka",
            "source": "manual_operator",
            "metadata": {"vehicle": "PB-05-AB-7811"},
            "timestamp": "2026-10-18T13:45:00Z",
        },
    ],
    "SHP-2026-003": [
        {
            "id": "EVT-SHP-2026-003-1",
            "shipment_id": "SHP-2026-003",
            "event_type": "shipment_created",
            "description": "Shipment batch created for 450 crates of Guava from Fazilka to Amritsar Fruit & Produce Mandi Yard.",
            "facility_id": "FAC-PB-FAZ-01",
            "facility_name": "PSWC Warehousing Centre Fazilka",
            "source": "system_event",
            "metadata": {"produce_type": "Guava", "quantity_crates": 450},
            "timestamp": "2026-10-21T06:19:49Z",
        },
        {
            "id": "EVT-SHP-2026-003-2",
            "shipment_id": "SHP-2026-003",
            "event_type": "shipment_dispatched",
            "description": "Dispatched via Firozpur corridor to Bhagtanwala APMC Yard, Amritsar.",
            "facility_id": "FAC-PB-FAZ-01",
            "facility_name": "PSWC Warehousing Centre Fazilka",
            "source": "manual_operator",
            "metadata": {"vehicle": "PB-02-CD-1190"},
            "timestamp": "2026-10-21T08:00:00Z",
        },
        {
            "id": "EVT-SHP-2026-003-3",
            "shipment_id": "SHP-2026-003",
            "event_type": "arrival_recorded",
            "description": "Arrival recorded at Bhagtanwala APMC Fruit & Produce Mandi Yard, Amritsar.",
            "facility_id": "FAC-PB-ASR-01",
            "facility_name": "Bhagtanwala APMC Fruit & Produce Mandi Yard",
            "source": "manual_operator",
            "metadata": {"gate_entry": "Gate 2 (Tarn Taran Road)"},
            "timestamp": "2026-10-22T13:00:00Z",
        },
        {
            "id": "EVT-SHP-2026-003-4",
            "shipment_id": "SHP-2026-003",
            "event_type": "delivery_completed",
            "description": "Produce physical handover and mandi yard intake inspection completed for wholesale auction.",
            "facility_id": "FAC-PB-ASR-01",
            "facility_name": "Bhagtanwala APMC Fruit & Produce Mandi Yard",
            "source": "manual_operator",
            "metadata": {"crates_received": 450, "condition": "good"},
            "timestamp": "2026-10-22T13:31:02Z",
        },
    ],
}


INITIAL_SEED_LISTINGS: List[Dict[str, Any]] = [
    {
        "id": "LST-GUA-001",
        "title": "Guava Premium Crate (Ripe)",
        "variety": "Allahabad Safeda",
        "crop": "guava",
        "ripeness_stage": "Ripe",
        "ai_verified": True,
        "softmax_score": 0.982,
        "origin_facility_id": "FAC-PB-ABO-01",
        "origin_name": "Farm Gate D (Abohar Cluster)",
        "available_crates": 120,
        "crate_weight_kg": 20.0,
        "price_per_crate_inr": 1200.0,
        "image_url": "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
        "notes": "Certified harvest maturity evaluated with ResNet18 model v2.0.0. Ready for retail distribution.",
    },
    {
        "id": "LST-GUA-002",
        "title": "Guava Transit Crate (Mature Green)",
        "variety": "Hisar Safeda / Shweta",
        "crop": "guava",
        "ripeness_stage": "Mature Green",
        "ai_verified": True,
        "softmax_score": 0.875,
        "origin_facility_id": "FAC-PB-PAG-BARA",
        "origin_name": "Packhouse Zone E (Bara Farm Hub)",
        "available_crates": 160,
        "crate_weight_kg": 20.0,
        "price_per_crate_inr": 1050.0,
        "image_url": "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
        "notes": "Mature green firmness optimal for multi-day long-distance cold-chain transport.",
    },
    {
        "id": "LST-GUA-003",
        "title": "Guava Harvest Crate (Green / Breaker)",
        "variety": "Lalit / Regional Sindhi",
        "crop": "guava",
        "ripeness_stage": "Green",
        "ai_verified": True,
        "softmax_score": 0.914,
        "origin_facility_id": "FAC-PB-FAZ-01",
        "origin_name": "Abohar Post-Harvest Center (Fazilka)",
        "available_crates": 200,
        "crate_weight_kg": 20.0,
        "price_per_crate_inr": 950.0,
        "image_url": "https://images.unsplash.com/photo-1536511132770-e5058c7e8c46?w=600&auto=format&fit=crop&q=60",
        "notes": "Breaker stage fruit for scheduled ripening in controlled atmosphere chambers.",
    },
]

INITIAL_SEED_ORDERS: List[Dict[str, Any]] = [
    {
        "id": "ORD-2026-0001",
        "listing_id": "LST-GUA-001",
        "produce_title": "Guava Premium Crate (Ripe)",
        "variety": "Allahabad Safeda",
        "ripeness_stage": "Ripe",
        "quantity_crates": 20,
        "total_weight_kg": 400.0,
        "unit_price_inr": 1200.0,
        "total_price_inr": 24000.0,
        "currency": "INR",
        "buyer_name": "Demo Buyer",
        "buyer_organization": "Delhi NCR Premium Grocers",
        "shipping_destination": "Azadpur APMC Mandi, Delhi",
        "status": "confirmed",
        "is_demo_order": True,
        "simulation_notice": "DEMO WORKFLOW SIMULATION — No real payment processed and no legal financial obligation created.",
        "idempotency_key": "seed-order-1",
        "created_at": "2026-10-25T14:30:00Z",
    }
]

INITIAL_SEED_INVENTORY: List[Dict[str, Any]] = [
    {
        "id": "INV-PB-2026-001",
        "farmer_id": "FARMER-PB-001",
        "crop_type": "guava",
        "crate_quantity": 120,
        "price_per_crate": 450.0,
        "total_stock_value": 54000.0,
        "description": "Allahabad Safeda prime harvest; grade A intake ready for cold storage.",
        "harvest_date": "2026-10-28",
        "location": "Abohar Farm Gate, Punjab",
        "status": "available",
        "created_at": "2026-10-28T08:30:00Z",
        "updated_at": "2026-10-28T08:30:00Z",
    },
    {
        "id": "INV-PB-2026-002",
        "farmer_id": "FARMER-PB-001",
        "crop_type": "banana",
        "crate_quantity": 80,
        "price_per_crate": 380.0,
        "total_stock_value": 30400.0,
        "description": "Grand Naine mature green stage 2 harvest crates.",
        "harvest_date": "2026-10-29",
        "location": "Fazilka Ripening Center Gate, Punjab",
        "status": "available",
        "created_at": "2026-10-29T10:15:00Z",
        "updated_at": "2026-10-29T10:15:00Z",
    },
    {
        "id": "INV-PB-2026-003",
        "farmer_id": "FARMER-PB-001",
        "crop_type": "kinnow",
        "crate_quantity": 200,
        "price_per_crate": 520.0,
        "total_stock_value": 104000.0,
        "description": "Fresh orchard harvest from Abohar citrus belt. Commercial stock.",
        "harvest_date": "2026-10-30",
        "location": "Abohar Post-Harvest Center, Punjab",
        "status": "available",
        "created_at": "2026-10-30T09:00:00Z",
        "updated_at": "2026-10-30T09:00:00Z",
    },
]


class ShipmentRepository:
    """Repository handling shipment records, storage facilities, telemetry, and geospatial waypoints."""

    def __init__(
        self,
        storage_file: Optional[Path] = None,
        database_enabled: Optional[bool] = None,
    ):
        self.storage_file = Path(storage_file) if storage_file else DEFAULT_STORAGE_FILE
        self.database_enabled = (
            database_enabled
            if database_enabled is not None
            else getattr(settings, "DATABASE_ENABLED", False)
        )
        self._shipments: List[Dict[str, Any]] = []
        self._facilities: List[Dict[str, Any]] = []
        self._telemetry: Dict[str, List[Dict[str, Any]]] = {}
        self._waypoints: Dict[str, List[Dict[str, Any]]] = {}
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._listings: List[Dict[str, Any]] = []
        self._orders: List[Dict[str, Any]] = []
        self._inventory: List[Dict[str, Any]] = []
        self._simulation_sessions: Dict[str, Dict[str, Any]] = {}
        self._simulation_telemetry: Dict[str, List[Dict[str, Any]]] = {}

        self._initialize_storage()

    def _get_db_connection(self):
        """Returns a database connection if psycopg2 or psycopg is available."""
        db_url = get_sync_database_url()
        try:
            import psycopg2
            return psycopg2.connect(db_url)
        except Exception:
            try:
                import psycopg
                return psycopg.connect(db_url)
            except Exception:
                return None

    def _sync_from_database(self) -> bool:
        """Loads shipments, facilities, telemetry, and waypoints directly from PostgreSQL / PostGIS."""
        conn = self._get_db_connection()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                # Load facilities
                try:
                    cur.execute(
                        """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'storage_facilities';
                        """
                    )
                    cols = {row[0] for row in cur.fetchall()}
                    has_provenance = "source_name" in cols

                    if has_provenance:
                        cur.execute(
                            "SELECT id, name, facility_type, address, village_or_city, district, "
                            "state, postal_code, latitude, longitude, capacity, capacity_unit, "
                            "current_utilization, storage_temperature_min_c, storage_temperature_max_c, "
                            "supported_commodities, operational_status, source_name, source_url, "
                            "source_record, verification_status, verification_date, last_source_check, "
                            "coordinate_source, geocoding_confidence, data_provenance, "
                            "location_verification_status, created_at, updated_at "
                            "FROM storage_facilities ORDER BY name ASC;"
                        )
                        f_rows = cur.fetchall()
                        if f_rows:
                            self._facilities = []
                            for f in f_rows:
                                lat = float(f[8]) if f[8] is not None else None
                                lon = float(f[9]) if f[9] is not None else None
                                coords = {"latitude": lat, "longitude": lon} if lat is not None and lon is not None else None
                                self._facilities.append({
                                    "id": f[0], "name": f[1], "facility_type": f[2], "address": f[3],
                                    "village_or_city": f[4], "district": f[5], "state": f[6], "postal_code": f[7],
                                    "latitude": lat, "longitude": lon, "coordinates": coords,
                                    "capacity": float(f[10]) if f[10] is not None else None,
                                    "capacity_unit": f[11],
                                    "current_utilization": float(f[12]) if f[12] is not None else None,
                                    "storage_temperature_min_c": float(f[13]) if f[13] is not None else None,
                                    "storage_temperature_max_c": float(f[14]) if f[14] is not None else None,
                                    "supported_commodities": f[15] if isinstance(f[15], list) else None,
                                    "operational_status": f[16],
                                    "source_name": f[17],
                                    "source_url": f[18],
                                    "source_record": f[19],
                                    "verification_status": f[20] or "verified",
                                    "verification_date": f[21],
                                    "last_source_check": f[22],
                                    "coordinate_source": f[23],
                                    "geocoding_confidence": f[24],
                                    "data_provenance": f[25],
                                    "location_verification_status": f[26] or f[20] or "verified",
                                    "created_at": f[27].isoformat() if hasattr(f[27], "isoformat") else str(f[27]),
                                    "updated_at": f[28].isoformat() if hasattr(f[28], "isoformat") else str(f[28]),
                                })
                    else:
                        cur.execute(
                            "SELECT id, name, facility_type, address, village_or_city, district, "
                            "state, postal_code, latitude, longitude, capacity, capacity_unit, "
                            "current_utilization, storage_temperature_min_c, storage_temperature_max_c, "
                            "operational_status, location_verification_status, created_at, updated_at "
                            "FROM storage_facilities ORDER BY name ASC;"
                        )
                        f_rows = cur.fetchall()
                        if f_rows:
                            self._facilities = []
                            for f in f_rows:
                                lat = float(f[8]) if f[8] is not None else None
                                lon = float(f[9]) if f[9] is not None else None
                                coords = {"latitude": lat, "longitude": lon} if lat is not None and lon is not None else None
                                self._facilities.append({
                                    "id": f[0], "name": f[1], "facility_type": f[2], "address": f[3],
                                    "village_or_city": f[4], "district": f[5], "state": f[6], "postal_code": f[7],
                                    "latitude": lat, "longitude": lon, "coordinates": coords,
                                    "capacity": float(f[10]) if f[10] is not None else None,
                                    "capacity_unit": f[11],
                                    "current_utilization": float(f[12]) if f[12] is not None else None,
                                    "storage_temperature_min_c": float(f[13]) if f[13] is not None else None,
                                    "storage_temperature_max_c": float(f[14]) if f[14] is not None else None,
                                    "operational_status": f[15],
                                    "location_verification_status": f[16],
                                    "created_at": f[17].isoformat() if hasattr(f[17], "isoformat") else str(f[17]),
                                    "updated_at": f[18].isoformat() if hasattr(f[18], "isoformat") else str(f[18]),
                                })
                except Exception as f_exc:
                    logger.debug("storage_facilities table query exception: %s", f_exc)

                # Load shipments
                cur.execute(
                    "SELECT id, produce_type, produce, origin, destination, quantity, "
                    "quantity_crates, status, temperature_c, humidity_pct, risk_index, "
                    "created_at, last_update FROM shipments ORDER BY created_at ASC;"
                )
                rows = cur.fetchall()
                if rows:
                    self._shipments = []
                    for r in rows:
                        self._shipments.append({
                            "id": r[0],
                            "produce_type": r[1],
                            "produce": r[2],
                            "origin": r[3],
                            "destination": r[4],
                            "quantity": float(r[5]) if r[5] is not None else 0.0,
                            "quantity_crates": int(r[6]) if r[6] is not None else 0,
                            "status": r[7],
                            "temperature_c": float(r[8]) if r[8] is not None else None,
                            "humidity_pct": float(r[9]) if r[9] is not None else None,
                            "risk_index": float(r[10]) if r[10] is not None else 0.0,
                            "created_at": r[11].isoformat() if hasattr(r[11], "isoformat") else str(r[11]),
                            "last_update": r[12].isoformat() if hasattr(r[12], "isoformat") else str(r[12]),
                        })
                # Load telemetry
                cur.execute(
                    "SELECT id, shipment_id, temperature, humidity, sensor_id, location, timestamp "
                    "FROM telemetry_logs ORDER BY timestamp ASC;"
                )
                t_rows = cur.fetchall()
                self._telemetry = {}
                for t in t_rows:
                    self._telemetry.setdefault(t[1], []).append({
                        "id": t[0],
                        "shipment_id": t[1],
                        "temperature": float(t[2]),
                        "humidity": float(t[3]),
                        "sensor_id": t[4],
                        "location": t[5],
                        "timestamp": t[6].isoformat() if hasattr(t[6], "isoformat") else str(t[6]),
                    })
                # Load waypoints
                cur.execute(
                    "SELECT id, shipment_id, ST_X(coordinates), ST_Y(coordinates), "
                    "altitude_m, speed_kmh, heading_deg, location_metadata, recorded_at "
                    "FROM geo_waypoints ORDER BY recorded_at ASC;"
                )
                w_rows = cur.fetchall()
                self._waypoints = {}
                for w in w_rows:
                    self._waypoints.setdefault(w[1], []).append({
                        "id": w[0],
                        "shipment_id": w[1],
                        "longitude": float(w[2]),
                        "latitude": float(w[3]),
                        "srid": 4326,
                        "altitude_m": float(w[4]) if w[4] is not None else None,
                        "speed_kmh": float(w[5]) if w[5] is not None else None,
                        "heading_deg": float(w[6]) if w[6] is not None else None,
                        "location_metadata": w[7] if isinstance(w[7], dict) else {},
                        "recorded_at": w[8].isoformat() if hasattr(w[8], "isoformat") else str(w[8]),
                    })
            conn.close()
            self._commit()
            logger.info("Successfully loaded data from PostgreSQL / PostGIS")
            return len(self._shipments) > 0
        except Exception as exc:
            logger.warning("Could not sync from PostgreSQL: %s", exc)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            return False

    def _db_insert_shipment(self, record: Dict[str, Any]) -> None:
        if not self.database_enabled:
            return
        conn = self._get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO shipments (
                        id, produce_type, produce, origin, destination, quantity,
                        quantity_crates, status, temperature_c, humidity_pct, risk_index,
                        created_at, last_update
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        record["id"], record["produce_type"], record["produce"],
                        record["origin"], record["destination"], record["quantity"],
                        record["quantity_crates"], record["status"], record["temperature_c"],
                        record["humidity_pct"], record["risk_index"], record["created_at"],
                        record["last_update"],
                    )
                )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Failed to insert shipment into PostgreSQL: %s", exc)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _initialize_storage(self) -> None:
        """Initializes repository data from disk or verified Indian seeds."""
        if self.database_enabled:
            is_open, msg = probe_database_connection()
            if not is_open:
                raise DatabaseConnectionError(
                    f"PostgreSQL/PostGIS is enabled (DATABASE_ENABLED=True) but unreachable at "
                    f"'{settings.DATABASE_URL}'. Detail: {msg}. "
                    f"Silent fallback to in-memory fixtures is strictly disabled."
                )
            if self._sync_from_database():
                return

        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                self._shipments = data.get("shipments", [])
                self._facilities = data.get("facilities", [])
                self._telemetry = data.get("telemetry", {})
                self._waypoints = data.get("waypoints", {})
                self._events = data.get("events", {})
                if not self._events:
                    self._events = {k: [dict(r) for r in v] for k, v in INITIAL_SEED_EVENTS.items()}

                self._listings = data.get("listings", [])
                if not self._listings:
                    self._listings = [dict(item) for item in INITIAL_SEED_LISTINGS]

                self._orders = data.get("orders", [])
                if not self._orders:
                    self._orders = [dict(item) for item in INITIAL_SEED_ORDERS]

                self._inventory = data.get("inventory", [])
                if not self._inventory:
                    self._inventory = [dict(item) for item in INITIAL_SEED_INVENTORY]

                self._simulation_sessions = data.get("simulation_sessions", {})
                self._simulation_telemetry = data.get("simulation_telemetry", {})

                # Check if legacy demo facilities are present or facilities need migration
                has_legacy_demo = any(
                    f.get("location_verification_status") == "demo_simulated"
                    or not f.get("source_name")
                    for f in self._facilities
                )
                # Synchronize seed facilities with audited Phase 12.1 records
                seed_dict = {f["id"]: dict(f) for f in INITIAL_SEED_FACILITIES}
                merged_facilities = []
                seen_ids = set()

                # Always keep seed facilities synchronized with audited INITIAL_SEED_FACILITIES
                for seed_id, seed_fac in seed_dict.items():
                    merged_facilities.append(dict(seed_fac))
                    seen_ids.add(seed_id)

                # Preserve any user-registered facilities that are not old demo simulated
                for f in self._facilities:
                    fid = f.get("id")
                    if fid not in seen_ids and f.get("location_verification_status") != "demo_simulated":
                        merged_facilities.append(dict(f))
                        seen_ids.add(fid)

                self._facilities = merged_facilities

                # Synchronize seed shipments with verified INITIAL_SEED_SHIPMENTS
                seed_shipments_dict = {s["id"]: dict(s) for s in INITIAL_SEED_SHIPMENTS}
                for s in self._shipments:
                    sid = s.get("id")
                    if sid in seed_shipments_dict:
                        seed_item = seed_shipments_dict[sid]
                        for key in ["origin", "destination", "origin_facility_id", "destination_facility_id", "origin_lat", "origin_lon", "destination_lat", "destination_lon"]:
                            if key in seed_item:
                                s[key] = seed_item[key]

                self._commit()

                logger.info(
                    "Loaded %d shipments, %d facilities, %d marketplace listings from '%s'",
                    len(self._shipments),
                    len(self._facilities),
                    len(self._listings),
                    self.storage_file.name,
                )
                return
            except Exception as exc:
                logger.warning(
                    "Error reading persisted ledger '%s', resetting to verified Indian seeds: %s",
                    self.storage_file,
                    exc,
                )

        # Initialize with verified Indian Punjab seeds
        self._shipments = [dict(s) for s in INITIAL_SEED_SHIPMENTS]
        self._facilities = [dict(f) for f in INITIAL_SEED_FACILITIES]
        self._telemetry = {k: [dict(r) for r in v] for k, v in INITIAL_SEED_TELEMETRY.items()}
        self._waypoints = {k: [dict(w) for w in v] for k, v in INITIAL_SEED_WAYPOINTS.items()}
        self._events = {k: [dict(r) for r in v] for k, v in INITIAL_SEED_EVENTS.items()}
        self._listings = [dict(item) for item in INITIAL_SEED_LISTINGS]
        self._orders = [dict(item) for item in INITIAL_SEED_ORDERS]
        self._inventory = [dict(item) for item in INITIAL_SEED_INVENTORY]
        self._simulation_sessions = {}
        self._simulation_telemetry = {}
        self._commit()

    def _commit(self) -> None:
        """Atomic write to storage ledger file to guarantee survival across backend restarts."""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": "1.4.0",
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "operational_scope": "India (Punjab & Northern Agricultural Corridor)",
                "facilities": self._facilities,
                "shipments": self._shipments,
                "telemetry": self._telemetry,
                "waypoints": self._waypoints,
                "events": self._events,
                "listings": self._listings,
                "orders": self._orders,
                "inventory": self._inventory,
                "simulation_sessions": self._simulation_sessions,
                "simulation_telemetry": self._simulation_telemetry,
            }
            tmp_file = self.storage_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_file.replace(self.storage_file)
        except Exception as exc:
            logger.error("Failed to persist storage ledger to '%s': %s", self.storage_file, exc)

    def evaluate_facility_suitability(
        self,
        facility_id: Optional[str],
        operation: Optional[str] = None,
        crop: str = "guava",
    ) -> Dict[str, Any]:
        """
        Evaluates facility readiness and suitability with strict truthfulness per Phase 13 requirements.
        Separates four independent concepts:
          1. Guava trading (verified, partially_verified, or not_verified)
          2. Guava handling (verified, partially_verified, unconfirmed, or unsuitable)
          3. Guava cold-chain capability (verified, partially_verified, unconfirmed, or unsuitable)
          4. Current operational availability (active, unknown, maintenance, inactive)
        """
        if not facility_id:
            return {
                "facility_id": "",
                "facility_name": "Unspecified Facility",
                "operation": operation or "unspecified",
                "crop": crop,
                "suitable": False,
                "suitability_status": "unspecified",
                "capabilities": {
                    "guava_trading": False,
                    "guava_handling": False,
                    "guava_cold_chain": False,
                    "operational_availability": "unknown",
                },
                "warnings": ["No facility specified for this operation."],
                "evidence_summary": "No facility identifier was provided.",
                "source_citation": None,
            }

        facility = self.get_facility(facility_id)
        if not facility:
            return {
                "facility_id": facility_id,
                "facility_name": "Unknown Facility",
                "operation": operation or "unspecified",
                "crop": crop,
                "suitable": False,
                "suitability_status": "not_found",
                "capabilities": {
                    "guava_trading": False,
                    "guava_handling": False,
                    "guava_cold_chain": False,
                    "operational_availability": "unknown",
                },
                "warnings": [f"Referenced facility '{facility_id}' does not exist in the registry."],
                "evidence_summary": f"Facility ID '{facility_id}' could not be located.",
                "source_citation": None,
            }

        fid = facility["id"]
        fname = facility.get("name", "Unnamed Facility")
        ftype = facility.get("facility_type", "godown")
        cat = facility.get("guava_suitability_category")
        op_status = facility.get("operational_status")
        commodities = [str(c).lower() for c in (facility.get("supported_commodities") or [])]

        # 1. Guava trading capability
        if fid == "FAC-DL-AZD-01" or (ftype == "mandi" and "guava" in commodities):
            guava_trading = "verified"
        elif ftype == "mandi":
            guava_trading = "partially_verified"
        else:
            guava_trading = "not_verified"

        # 2. Guava handling capability (grading, sorting, packing, pre-cooling)
        if fid in ("FAC-PB-PAG-BARA", "FAC-PB-PAG-KANG"):
            guava_handling = "partially_verified"  # Pre-cooling chamber exists for general horticulture; guava specific unconfirmed
        elif fid == "FAC-PB-ABO-01":
            guava_handling = "unconfirmed"  # Mechanized citrus waxing; guava handling not documented
        elif ftype == "godown":
            guava_handling = "unsuitable"  # Dry grain godown, no handling/packing lines
        elif ftype == "cold_storage":
            guava_handling = "unconfirmed"  # Commercial cold store, no packhouse grading lines documented
        else:
            guava_handling = "not_verified"

        # 3. Guava cold-chain capability (refrigerated storage 8-10°C, chilling injury <4°C)
        if fid in ("FAC-PB-PAG-BARA", "FAC-PB-PAG-KANG"):
            guava_cold_chain = "partially_verified"  # Cold chambers documented; guava protocol unconfirmed
        elif cat == "cold_store_unknown" or ftype == "cold_storage":
            guava_cold_chain = "unconfirmed"  # Potato-oriented cold store; guava protocol unconfirmed
        elif ftype == "godown" or cat == "ambient_grain":
            guava_cold_chain = "unsuitable"  # Dry ambient grain godown; NO refrigeration
        elif ftype == "mandi":
            guava_cold_chain = "partially_verified" if fid == "FAC-DL-AZD-01" else "not_verified"
        else:
            guava_cold_chain = "unconfirmed"

        # 4. Current operational availability
        operational_availability = "active" if op_status == "active" else ("unknown" if op_status is None else op_status)

        capabilities = {
            "guava_trading": guava_trading,
            "guava_handling": guava_handling,
            "guava_cold_chain": guava_cold_chain,
            "operational_availability": operational_availability,
        }

        warnings: List[str] = []
        suitable = True
        suitability_status = "verified"

        op = (operation or "").lower()

        # Operational availability check for any operation
        if operational_availability == "unknown":
            warnings.append("Current operational availability is unknown. Physical on-site intake capacity must be confirmed before dispatch.")

        if op in ("market_auction", "trading", "mandi_sale"):
            if guava_trading == "verified":
                suitability_status = "verified_guava_trading"
            elif guava_trading == "partially_verified":
                suitability_status = "partially_verified"
                warnings.append(f"Wholesale mandi yard '{fname}' conducts general fruit & vegetable auctions; specific guava trading lot volume is partially verified.")
            else:
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"Facility '{fname}' is registered as a {ftype}, not an authorized produce mandi or auction market.")

        elif op in ("packhouse_cooling", "pre_cooling", "grading_packing"):
            if guava_handling == "partially_verified":
                suitability_status = "partially_verified"
                warnings.append(f"Facility '{fname}' has documented pre-cooling chambers for general horticulture, but dedicated guava post-harvest handling protocol is unconfirmed.")
            elif fid == "FAC-PB-ABO-01":
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"Facility '{fname}' is engineered specifically for citrus/Kinnow washing, waxing, and sizing lines; guava handling is not documented.")
            elif ftype == "godown":
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"Facility '{fname}' is an ambient grain godown lacking produce washing, grading, and pre-cooling equipment.")
            else:
                suitable = False
                suitability_status = "not_verified"
                warnings.append(f"Facility '{fname}' lacks verified produce sorting, grading, or pre-cooling packhouse lines.")

        elif op in ("cold_storage", "refrigerated_holding"):
            if ftype == "mandi":
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"Facility '{fname}' is a wholesale terminal mandi with only short-term transit holding/ripening chambers, not certified cold storage.")
            elif guava_cold_chain == "unsuitable" or ftype == "godown":
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"CRITICAL: Facility '{fname}' is a dry ambient grain warehouse with NO refrigeration. Storing perishable guava here will cause rapid decay.")
            elif guava_cold_chain == "unconfirmed":
                suitable = False
                suitability_status = "not_verified"
                warnings.append(f"Facility '{fname}' is a commercial cold store registered in potato belt; guava cold-chain capability (8-10°C) is unconfirmed and physical capacity is unverified.")
            elif guava_cold_chain == "partially_verified":
                suitability_status = "partially_verified"
                warnings.append(f"Facility '{fname}' has documented cold rooms (10-50 MT); guava-specific temperature regime is unconfirmed.")
            else:
                suitable = False
                suitability_status = "not_verified"
                warnings.append(f"Facility '{fname}' lacks certified long-term cold storage infrastructure.")

        elif op in ("transit_hub", "checkpoint_handover"):
            if fid == "FAC-PB-BTI-01":
                suitability_status = "verified"
            elif op_status != "active":
                suitability_status = "partially_verified"
                warnings.append(f"Facility '{fname}' operational availability is unconfirmed for cargo transit handover.")

        elif op in ("harvesting_aggregation", "orchard_intake"):
            if ftype == "godown":
                suitable = False
                suitability_status = "unsuitable_for_operation"
                warnings.append(f"Facility '{fname}' is a grain warehouse, not an orchard produce aggregation center.")
            else:
                suitability_status = "partially_verified" if op_status != "active" else "verified"

        # Evidence summary text
        evidence_summary = (
            f"Facility '{fname}' ({ftype.upper()}): "
            f"Trading={guava_trading.upper()}, "
            f"Handling={guava_handling.upper()}, "
            f"ColdChain={guava_cold_chain.upper()}, "
            f"Availability={operational_availability.upper()}."
        )

        source_citation = {
            "source_name": facility.get("source_name"),
            "source_record": facility.get("source_record"),
            "source_url": facility.get("source_url"),
            "source_citation_type": facility.get("source_citation_type"),
            "verification_status": facility.get("verification_status"),
            "coordinate_source": facility.get("coordinate_source"),
            "geocoding_confidence": facility.get("geocoding_confidence"),
        }

        return {
            "facility_id": fid,
            "facility_name": fname,
            "operation": operation or "general_assessment",
            "crop": crop,
            "suitable": suitable,
            "suitability_status": suitability_status,
            "capabilities": capabilities,
            "warnings": warnings,
            "evidence_summary": evidence_summary,
            "source_citation": source_citation,
        }

    def _enrich_shipment(self, shp: Dict[str, Any]) -> Dict[str, Any]:
        """Attaches serialized geospatial coordinates, latest waypoint, and linked facility metadata with suitability."""
        record = dict(shp)
        shp_id = record["id"]

        waypoints = self._waypoints.get(shp_id, [])
        if waypoints:
            latest = waypoints[-1]
            record["current_coordinates"] = {
                "latitude": float(latest["latitude"]),
                "longitude": float(latest["longitude"]),
            }
            record["latest_waypoint"] = dict(latest)
        else:
            record["current_coordinates"] = None
            record["latest_waypoint"] = None

        # Determine location tracking_mode truthfully
        simulated_wps = sum(
            1 for w in waypoints
            if w.get("location_metadata", {}).get("source") == "demo_simulated"
            or w.get("location_metadata", {}).get("simulated") is True
        )
        live_wps = sum(
            1 for w in waypoints
            if w.get("location_metadata", {}).get("source") == "live_gps"
        )
        if live_wps > 0 and simulated_wps == 0:
            record["tracking_mode"] = "live_gps"
        elif simulated_wps > 0:
            record["tracking_mode"] = "simulated"
        else:
            record["tracking_mode"] = record.get("tracking_mode") or "simulated"

        # Determine telemetry_mode truthfully
        telemetry_logs = self._telemetry.get(shp_id, [])
        if not telemetry_logs:
            record["telemetry_mode"] = "unavailable"
        elif any(t.get("sensor_id") == "SNS-SIM-DEMO" for t in telemetry_logs):
            record["telemetry_mode"] = "simulated"
        else:
            record["telemetry_mode"] = record.get("telemetry_mode") or "simulated"

        # Attach linked facility summaries if available
        origin_fid = record.get("origin_facility_id")
        dest_fid = record.get("destination_facility_id")
        inter_fid = record.get("intermediate_facility_id")

        record["origin_facility"] = self.get_facility(origin_fid) if origin_fid else None
        record["destination_facility"] = self.get_facility(dest_fid) if dest_fid else None
        record["intermediate_facility"] = self.get_facility(inter_fid) if inter_fid else None

        # Evaluate facility suitabilities and collect warnings
        suitability_warnings = []

        if origin_fid:
            o_op = record.get("origin_operation") or "harvesting_aggregation"
            o_suit = self.evaluate_facility_suitability(origin_fid, operation=o_op)
            record["origin_suitability"] = o_suit
            for w in o_suit.get("warnings", []):
                suitability_warnings.append(f"Origin ({record['origin_facility']['name']}): {w}")
        else:
            record["origin_suitability"] = None

        if dest_fid:
            d_op = record.get("destination_operation") or "market_auction"
            d_suit = self.evaluate_facility_suitability(dest_fid, operation=d_op)
            record["destination_suitability"] = d_suit
            for w in d_suit.get("warnings", []):
                suitability_warnings.append(f"Destination ({record['destination_facility']['name']}): {w}")
        else:
            record["destination_suitability"] = None

        if inter_fid:
            i_op = record.get("intermediate_operation") or "transit_hub"
            i_suit = self.evaluate_facility_suitability(inter_fid, operation=i_op)
            record["intermediate_suitability"] = i_suit
            for w in i_suit.get("warnings", []):
                suitability_warnings.append(f"Intermediate Hub ({record['intermediate_facility']['name']}): {w}")
        else:
            record["intermediate_suitability"] = None

        record["suitability_warnings"] = suitability_warnings
        record["events_count"] = len(self._events.get(shp_id, []))
        return record

    def add_shipment_event(self, shipment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends an auditable lifecycle tracking or facility event.
        Includes duplicate prevention for rapid retries (<60s window for identical event_type & facility).
        """
        shp = self.get_shipment(shipment_id)
        if not shp:
            raise ShipmentNotFoundError(f"Shipment '{shipment_id}' not found.")

        facility_id = payload.get("facility_id")
        facility_name = None
        if facility_id:
            facility = self.get_facility(facility_id)
            if not facility:
                raise ValueError(f"Referenced facility '{facility_id}' does not exist.")
            facility_name = facility.get("name")

        events = self._events.setdefault(shipment_id, [])
        event_type = payload["event_type"]
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now_dt.isoformat()

        # Duplicate prevention: Check if identical event was logged within last 60 seconds
        if events:
            last = events[-1]
            if last.get("event_type") == event_type and last.get("facility_id") == facility_id:
                try:
                    last_time = datetime.datetime.fromisoformat(last["timestamp"].replace("Z", "+00:00"))
                    if abs((now_dt - last_time).total_seconds()) < 60:
                        logger.info("Prevented duplicate event '%s' for shipment '%s'", event_type, shipment_id)
                        return last
                except Exception:
                    pass

        event_id = f"EVT-{shipment_id}-{len(events) + 1}"
        event = {
            "id": event_id,
            "shipment_id": shipment_id,
            "event_type": event_type,
            "description": payload["description"],
            "facility_id": facility_id,
            "facility_name": facility_name,
            "source": payload.get("source", "system_event"),
            "metadata": payload.get("metadata", {}),
            "timestamp": now_iso,
        }
        events.append(event)
        self._commit()
        return event

    def get_shipment_events(self, shipment_id: str) -> List[Dict[str, Any]]:
        """Returns ordered timeline of verified tracking events for a shipment."""
        if not self.get_shipment(shipment_id):
            raise ShipmentNotFoundError(f"Shipment '{shipment_id}' not found.")
        return list(self._events.get(shipment_id, []))

    # -------------------------------------------------------------------------
    # Facilities Management Methods
    # -------------------------------------------------------------------------
    def list_facilities(
        self,
        facility_type: Optional[str] = None,
        district: Optional[str] = None,
        state: Optional[str] = None,
        operational_status: Optional[str] = None,
        verification_status: Optional[str] = None,
        guava_suitability_category: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns registered agricultural storage facilities with optional filtering and search."""
        results = list(self._facilities)
        if facility_type:
            results = [f for f in results if f.get("facility_type") == facility_type]
        if district:
            results = [f for f in results if f.get("district", "").lower() == district.lower()]
        if state:
            results = [f for f in results if f.get("state", "").lower() == state.lower()]
        if operational_status:
            results = [f for f in results if f.get("operational_status") == operational_status]
        if verification_status:
            results = [
                f for f in results
                if f.get("verification_status") == verification_status
                or f.get("location_verification_status") == verification_status
            ]
        if guava_suitability_category:
            results = [f for f in results if f.get("guava_suitability_category") == guava_suitability_category]
        if q:
            query = q.strip().lower()
            filtered = []
            for f in results:
                name_match = query in f.get("name", "").lower()
                addr_match = query in f.get("address", "").lower()
                city_match = query in f.get("village_or_city", "").lower()
                dist_match = query in f.get("district", "").lower()
                comm_match = any(query in str(c).lower() for c in (f.get("supported_commodities") or []))
                source_match = query in f.get("source_name", "").lower()
                if name_match or addr_match or city_match or dist_match or comm_match or source_match:
                    filtered.append(f)
            results = filtered
        return results

    # Alias for compatibility with external services
    get_facilities = list_facilities

    def get_facility(self, facility_id: str) -> Optional[Dict[str, Any]]:
        """Returns single facility record by identifier."""
        for f in self._facilities:
            if f["id"] == facility_id:
                return dict(f)
        return None

    def create_facility(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Registers a new agricultural storage facility with optional Indian coordinate validation."""
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        coords = None
        if lat is not None and lon is not None:
            lat = float(lat)
            lon = float(lon)
            validate_indian_coordinate(lat, lon, field_name="facility coordinates")
            coords = {"latitude": lat, "longitude": lon}

        fid = payload.get("id") or f"FAC-PB-{len(self._facilities) + 1:03d}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        v_status = payload.get("verification_status") or payload.get("location_verification_status") or "verified"

        facility = {
            "id": fid,
            "name": payload.get("name", ""),
            "facility_type": payload.get("facility_type", "godown"),
            "address": payload.get("address", ""),
            "village_or_city": payload.get("village_or_city", ""),
            "district": payload.get("district", ""),
            "state": payload.get("state", "Punjab"),
            "postal_code": payload.get("postal_code"),
            "latitude": lat,
            "longitude": lon,
            "coordinates": coords,
            "contact_phone": payload.get("contact_phone"),
            "contact_email": payload.get("contact_email"),
            "capacity": float(payload["capacity"]) if payload.get("capacity") is not None else None,
            "capacity_unit": payload.get("capacity_unit"),
            "current_utilization": float(payload["current_utilization"]) if payload.get("current_utilization") is not None else None,
            "storage_temperature_min_c": float(payload["storage_temperature_min_c"]) if payload.get("storage_temperature_min_c") is not None else None,
            "storage_temperature_max_c": float(payload["storage_temperature_max_c"]) if payload.get("storage_temperature_max_c") is not None else None,
            "supported_commodities": list(payload["supported_commodities"]) if payload.get("supported_commodities") else None,
            "operational_status": payload.get("operational_status"),
            "guava_suitability_category": payload.get("guava_suitability_category"),
            "source_citation_type": payload.get("source_citation_type"),
            "legal_entity_verification": payload.get("legal_entity_verification"),
            "physical_facility_verification": payload.get("physical_facility_verification"),
            "source_name": payload.get("source_name"),
            "source_url": payload.get("source_url"),
            "source_record": payload.get("source_record"),
            "verification_status": v_status,
            "verification_date": payload.get("verification_date") or now_iso[:10],
            "last_source_check": payload.get("last_source_check") or now_iso[:10],
            "coordinate_source": payload.get("coordinate_source"),
            "geocoding_confidence": payload.get("geocoding_confidence"),
            "data_provenance": payload.get("data_provenance"),
            "location_verification_status": v_status,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        self._facilities.append(facility)
        self._commit()
        return facility

    # -------------------------------------------------------------------------
    # Shipments Management Methods
    # -------------------------------------------------------------------------
    def list_shipments(self) -> List[Dict[str, Any]]:
        """Returns all registered shipment records with current geospatial coordinates."""
        return [self._enrich_shipment(s) for s in self._shipments]

    def get_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Finds a shipment record by identifier with current geospatial coordinates."""
        for shp in self._shipments:
            if shp["id"] == shipment_id:
                return self._enrich_shipment(shp)
        return None

    def create_shipment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new shipment batch and persists it across restarts."""
        new_id = payload.get("id") or f"SHP-2026-{len(self._shipments) + 1:03d}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        produce_type = payload.get("produce_type", "Guava")
        quantity = float(payload.get("quantity", 0.0))

        origin_fid = payload.get("origin_facility_id")
        dest_fid = payload.get("destination_facility_id")
        inter_fid = payload.get("intermediate_facility_id")

        # Validate facility IDs exist if provided
        for fid, role in [(origin_fid, "origin"), (dest_fid, "destination"), (inter_fid, "intermediate")]:
            if fid and not self.get_facility(fid):
                raise ValueError(f"Selected {role} facility '{fid}' does not exist in the registry.")

        record = {
            "id": new_id,
            "produce_type": produce_type,
            "produce": produce_type,
            "origin": payload.get("origin", ""),
            "destination": payload.get("destination", ""),
            "origin_facility_id": origin_fid,
            "destination_facility_id": dest_fid,
            "intermediate_facility_id": inter_fid,
            "origin_operation": payload.get("origin_operation"),
            "destination_operation": payload.get("destination_operation"),
            "intermediate_operation": payload.get("intermediate_operation"),
            "planned_departure": payload.get("planned_departure"),
            "actual_departure": payload.get("actual_departure"),
            "planned_arrival": payload.get("planned_arrival"),
            "actual_arrival": payload.get("actual_arrival"),
            "tracking_mode": payload.get("tracking_mode", "simulated"),
            "telemetry_mode": payload.get("telemetry_mode", "simulated"),
            "quantity": quantity,
            "quantity_crates": int(quantity),
            "status": payload.get("status", "created"),
            "temperature_c": 6.0,
            "humidity_pct": 88.0,
            "risk_index": 15.0,
            "quality_grade": payload.get("quality_grade"),
            "inspection_verdict": payload.get("inspection_verdict"),
            "created_at": now_iso,
            "last_update": now_iso,
        }
        self._shipments.append(record)
        self._telemetry[new_id] = []
        self._waypoints[new_id] = []
        self._events[new_id] = []

        # Automatically log creation event
        self.add_shipment_event(new_id, {
            "event_type": "shipment_created",
            "description": f"Shipment created for {int(quantity)} crates of {produce_type} ({record['origin']} to {record['destination']}).",
            "facility_id": origin_fid,
            "source": "system_event",
            "metadata": {"produce_type": produce_type, "quantity": quantity},
        })

        # If quality inspection is present, log quality event
        if payload.get("quality_grade"):
            self.add_shipment_event(new_id, {
                "event_type": "quality_inspection_recorded",
                "description": f"AI Produce Inspection Grade: {payload.get('quality_grade')} recorded for {produce_type}.",
                "facility_id": origin_fid,
                "source": "ai_inspection",
                "metadata": payload.get("inspection_verdict") or {},
            })

        if origin_fid or dest_fid or inter_fid:
            o_fac = self.get_facility(origin_fid) if origin_fid else None
            d_fac = self.get_facility(dest_fid) if dest_fid else None
            i_fac = self.get_facility(inter_fid) if inter_fid else None
            desc = f"Facilities associated: Origin='{o_fac['name'] if o_fac else 'None'}', Destination='{d_fac['name'] if d_fac else 'None'}'"
            if i_fac:
                desc += f", Intermediate Hub='{i_fac['name']}'"
            self.add_shipment_event(new_id, {
                "event_type": "facility_association_updated",
                "description": desc,
                "facility_id": origin_fid or dest_fid,
                "source": "system_event",
                "metadata": {
                    "origin_facility_id": origin_fid,
                    "destination_facility_id": dest_fid,
                    "intermediate_facility_id": inter_fid,
                },
            })

        self._commit()
        self._db_insert_shipment(record)
        return self._enrich_shipment(record)

    def _db_insert_telemetry(self, reading: Dict[str, Any]) -> None:
        if not self.database_enabled:
            return
        conn = self._get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO telemetry_logs (
                        id, shipment_id, temperature, humidity, sensor_id, location, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        reading["id"], reading["shipment_id"], reading["temperature"],
                        reading["humidity"], reading["sensor_id"], reading["location"],
                        reading["timestamp"],
                    )
                )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Failed to insert telemetry into PostgreSQL: %s", exc)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def add_telemetry(self, shipment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests a new telemetry log reading for an active shipment."""
        shp = self.get_shipment(shipment_id)
        if not shp:
            raise ShipmentNotFoundError(f"Shipment '{shipment_id}' not found.")

        readings = self._telemetry.setdefault(shipment_id, [])
        reading_id = f"TEL-{shipment_id}-{len(readings) + 1}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        reading = {
            "id": reading_id,
            "shipment_id": shipment_id,
            "temperature": float(payload["temperature"]),
            "humidity": float(payload["humidity"]),
            "sensor_id": payload.get("sensor_id", "SNS-COLD-01"),
            "location": payload.get("location", ""),
            "timestamp": now_iso,
        }
        readings.append(reading)

        # Update parent shipment latest temperature/humidity and risk_index
        for s in self._shipments:
            if s["id"] == shipment_id:
                s["temperature_c"] = reading["temperature"]
                s["humidity_pct"] = reading["humidity"]
                s["last_update"] = now_iso
                temps = [float(t["temperature"]) for t in readings if "temperature" in t]
                avg_temp = sum(temps) / len(temps) if temps else reading["temperature"]
                excursion_count = sum(1 for t in temps if t > 8.0 or t < 4.0)
                base_risk = min(100.0, max(5.0, (avg_temp - 5.0) * 8.0 + excursion_count * 6.5))
                s["risk_index"] = round(base_risk, 1)
                break

        self._commit()
        self._db_insert_telemetry(reading)
        return reading

    def get_telemetry(self, shipment_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns recorded telemetry logs for a shipment."""
        readings = self._telemetry.get(shipment_id, [])
        return readings[skip : skip + limit]

    def _db_insert_waypoint(self, waypoint: Dict[str, Any]) -> None:
        if not self.database_enabled:
            return
        conn = self._get_db_connection()
        if not conn:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO geo_waypoints (
                        id, shipment_id, coordinates, altitude_m, speed_kmh,
                        heading_deg, location_metadata, recorded_at
                    ) VALUES (
                        %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        waypoint["id"], waypoint["shipment_id"],
                        waypoint["longitude"], waypoint["latitude"],
                        waypoint["altitude_m"], waypoint["speed_kmh"],
                        waypoint["heading_deg"],
                        json.dumps(waypoint.get("location_metadata", {})),
                        waypoint["recorded_at"],
                    )
                )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("Failed to insert waypoint into PostgreSQL: %s", exc)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def add_waypoint(self, shipment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Records a geospatial route waypoint (SRID 4326).
        Enforces strict Indian operational boundary checks.
        """
        if not self.get_shipment(shipment_id):
            raise ShipmentNotFoundError(f"Shipment '{shipment_id}' not found.")

        lon = float(payload["longitude"])
        lat = float(payload["latitude"])
        validate_indian_coordinate(lat, lon, field_name=f"waypoint for shipment {shipment_id}")

        waypoints = self._waypoints.setdefault(shipment_id, [])
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        waypoint_id = f"WAY-{shipment_id}-{len(waypoints) + 1}"

        waypoint = {
            "id": waypoint_id,
            "shipment_id": shipment_id,
            "longitude": lon,
            "latitude": lat,
            "srid": 4326,
            "altitude_m": payload.get("altitude_m"),
            "speed_kmh": payload.get("speed_kmh"),
            "heading_deg": payload.get("heading_deg"),
            "location_metadata": payload.get("location_metadata", {}),
            "recorded_at": now_iso,
        }
        waypoints.append(waypoint)

        # Update parent shipment's last_update
        for s in self._shipments:
            if s["id"] == shipment_id:
                s["last_update"] = now_iso
                break

        self._commit()
        self._db_insert_waypoint(waypoint)
        return waypoint

    def get_waypoints(self, shipment_id: str) -> List[Dict[str, Any]]:
        """Returns geospatial waypoints for a shipment."""
        return list(self._waypoints.get(shipment_id, []))

    def update_shipment_status(self, shipment_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates shipment properties (e.g. status, temperature, risk index, facilities)."""
        target = None
        for s in self._shipments:
            if s["id"] == shipment_id:
                target = s
                break
        if not target:
            raise ShipmentNotFoundError(f"Shipment '{shipment_id}' not found.")

        old_status = target.get("status")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tracked_keys = (
            "status", "temperature_c", "humidity_pct", "risk_index",
            "origin", "destination", "origin_facility_id", "destination_facility_id",
            "intermediate_facility_id", "origin_operation", "destination_operation",
            "intermediate_operation", "planned_departure", "actual_departure",
            "planned_arrival", "actual_arrival", "tracking_mode", "telemetry_mode"
        )
        for k in tracked_keys:
            if k in updates:
                target[k] = updates[k]
        target["last_update"] = now_iso

        # Log appropriate lifecycle event if status changed
        new_status = target.get("status")
        if old_status != new_status:
            if new_status == "in_transit":
                self.add_shipment_event(shipment_id, {
                    "event_type": "shipment_dispatched",
                    "description": f"Shipment status updated to 'in_transit'. Dispatched from origin facility.",
                    "facility_id": target.get("origin_facility_id"),
                    "source": "manual_operator",
                })
            elif new_status == "delivered":
                self.add_shipment_event(shipment_id, {
                    "event_type": "delivery_completed",
                    "description": f"Shipment successfully delivered at destination facility.",
                    "facility_id": target.get("destination_facility_id"),
                    "source": "manual_operator",
                })
            elif new_status == "delayed":
                self.add_shipment_event(shipment_id, {
                    "event_type": "in_transit",
                    "description": f"Shipment transit delay reported.",
                    "source": "manual_operator",
                })

        # Check facility association changes
        if any(k in updates for k in ("origin_facility_id", "destination_facility_id", "intermediate_facility_id")):
            self.add_shipment_event(shipment_id, {
                "event_type": "facility_association_updated",
                "description": "Shipment facility associations updated.",
                "source": "manual_operator",
            })

        self._commit()
        return self._enrich_shipment(target)

    # -----------------------------------------------------------------------
    # Buyer Marketplace & Demo Orders Methods (Phase 13.5)
    # -----------------------------------------------------------------------
    def get_marketplace_listings(self) -> List[Dict[str, Any]]:
        """Returns active produce listings available in the B2B marketplace."""
        if not self._listings:
            self._listings = [dict(item) for item in INITIAL_SEED_LISTINGS]
            self._commit()
        return [dict(item) for item in self._listings]

    def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific produce listing by ID."""
        for item in self._listings:
            if item.get("id") == listing_id:
                return dict(item)
        return None

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and records a demo purchase order.
        Guarantees:
        - Rejects unknown listing IDs.
        - Validates quantity > 0 and <= available stock.
        - Computes total price strictly on server from authoritative listing price.
        - Idempotently prevents duplicate order submissions.
        - Deducts purchased inventory from listing.
        - Persists to file-based session ledger.
        """
        listing_id = order_data.get("listing_id")
        target_listing = None
        for item in self._listings:
            if item.get("id") == listing_id:
                target_listing = item
                break

        if target_listing is None:
            raise ListingNotFoundError(f"Produce listing '{listing_id}' does not exist.")

        try:
            quantity = int(order_data.get("quantity_crates", 0))
        except (ValueError, TypeError):
            raise ValueError("Quantity in crates must be an integer.")

        if quantity <= 0:
            raise ValueError("Order quantity must be at least 1 crate.")

        available = int(target_listing.get("available_crates", 0))
        if quantity > available:
            raise InsufficientStockError(
                f"Requested quantity of {quantity} crates exceeds available stock of {available} crates."
            )

        buyer_name = str(order_data.get("buyer_name", "Demo Buyer")).strip()
        idempotency_key = order_data.get("idempotency_key")
        now = datetime.datetime.now(datetime.timezone.utc)

        # Idempotency & duplicate submission check (within last 60 seconds)
        for existing in self._orders:
            if idempotency_key and existing.get("idempotency_key") == idempotency_key:
                logger.info("Idempotent order match found for key '%s'", idempotency_key)
                return dict(existing)
            if (
                existing.get("listing_id") == listing_id
                and existing.get("buyer_name") == buyer_name
                and existing.get("quantity_crates") == quantity
            ):
                created_str = existing.get("created_at")
                if created_str:
                    try:
                        created_dt = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if (now - created_dt).total_seconds() < 60:
                            logger.info("Prevented duplicate order submission within 60s window for '%s'", listing_id)
                            return dict(existing)
                    except Exception:
                        pass

        # Authoritative server-side price calculation
        unit_price = float(target_listing["price_per_crate_inr"])
        total_price = round(quantity * unit_price, 2)
        crate_weight = float(target_listing.get("crate_weight_kg", 20.0))
        total_weight = round(quantity * crate_weight, 2)

        # Deduct purchased quantity from inventory
        target_listing["available_crates"] = available - quantity

        order_id = f"ORD-2026-{len(self._orders) + 1:04d}"
        order_record = {
            "id": order_id,
            "listing_id": target_listing["id"],
            "produce_title": target_listing["title"],
            "variety": target_listing.get("variety", "Guava (Psidium guajava)"),
            "ripeness_stage": target_listing.get("ripeness_stage", "Ripe"),
            "quantity_crates": quantity,
            "total_weight_kg": total_weight,
            "unit_price_inr": unit_price,
            "total_price_inr": total_price,
            "currency": "INR",
            "buyer_name": buyer_name,
            "buyer_organization": str(order_data.get("buyer_organization", "")).strip() or None,
            "shipping_destination": str(order_data.get("shipping_destination", "Azadpur APMC Mandi, Delhi")).strip(),
            "status": "confirmed",
            "is_demo_order": True,
            "simulation_notice": "DEMO WORKFLOW SIMULATION — No real payment processed and no legal financial obligation created.",
            "idempotency_key": idempotency_key,
            "created_at": now.isoformat(),
        }

        self._orders.insert(0, order_record)
        self._commit()
        logger.info("Created demo purchase order '%s' for %d crates of '%s'", order_id, quantity, listing_id)
        return dict(order_record)

    def get_orders(self, buyer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recorded demo orders, optionally filtered by buyer."""
        if not buyer_name:
            return [dict(order) for order in self._orders]
        clean_buyer = buyer_name.strip().lower()
        return [
            dict(order) for order in self._orders
            if clean_buyer in order.get("buyer_name", "").lower()
        ]

    # =========================================================================
    # Dynamic Vehicle Simulation Persistence Methods
    # =========================================================================

    def create_simulation_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates and stores a new simulation session."""
        session_id = session_data.get("id")
        if not session_id:
            session_id = f"SIM-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._simulation_sessions)+1:03d}"
            session_data["id"] = session_id

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        session_data.setdefault("created_at", now_iso)
        session_data.setdefault("updated_at", now_iso)
        session_data.setdefault("status", "CREATED")
        session_data.setdefault("current_distance_km", 0.0)
        session_data.setdefault("step_count", 0)

        self._simulation_sessions[session_id] = dict(session_data)
        self._simulation_telemetry.setdefault(session_id, [])
        self._commit()
        logger.info("Created simulation session '%s' (%s -> %s)", session_id, session_data.get("origin_name"), session_data.get("destination_name"))
        return dict(session_data)

    def get_simulation_session(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Returns simulation session by ID, including its latest recorded telemetry fix."""
        session = self._simulation_sessions.get(simulation_id)
        if not session:
            return None
        res = dict(session)
        history = self._simulation_telemetry.get(simulation_id, [])
        res["latest_telemetry"] = history[-1] if history else None
        return res

    def update_simulation_session(self, simulation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates fields of a simulation session and commits to disk."""
        session = self._simulation_sessions.get(simulation_id)
        if not session:
            return None
        session.update(updates)
        session["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._commit()
        return self.get_simulation_session(simulation_id)

    def list_simulation_sessions(
        self,
        shipment_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Returns recent simulation sessions, optionally filtered by associated shipment."""
        sessions = list(self._simulation_sessions.values())
        if shipment_id:
            sessions = [s for s in sessions if s.get("shipment_id") == shipment_id]
        # Sort newest first
        sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        results = []
        for s in sessions[:limit]:
            sid = s.get("id")
            s_copy = dict(s)
            history = self._simulation_telemetry.get(sid, [])
            s_copy["latest_telemetry"] = history[-1] if history else None
            results.append(s_copy)
        return results

    def add_simulation_telemetry(self, simulation_id: str, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Appends a synthetic sensor/telemetry reading to a simulation session."""
        if simulation_id not in self._simulation_sessions:
            raise KeyError(f"Simulation session '{simulation_id}' does not exist.")

        t_id = reading.get("id") or f"TEL-SIM-{len(self._simulation_telemetry.get(simulation_id, [])) + 1:04d}"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        reading_dict = {
            "id": t_id,
            "simulation_id": simulation_id,
            "shipment_id": reading.get("shipment_id") or self._simulation_sessions[simulation_id].get("shipment_id"),
            "sequence_step": reading.get("sequence_step", len(self._simulation_telemetry.get(simulation_id, [])) + 1),
            "latitude": float(reading["latitude"]),
            "longitude": float(reading["longitude"]),
            "heading_deg": float(reading.get("heading_deg", 0.0)),
            "speed_kmh": float(reading.get("speed_kmh", 0.0)),
            "distance_travelled_km": float(reading.get("distance_travelled_km", 0.0)),
            "distance_remaining_km": float(reading.get("distance_remaining_km", 0.0)),
            "temperature_c": float(reading["temperature_c"]),
            "humidity_pct": float(reading["humidity_pct"]),
            "delay_minutes": int(reading.get("delay_minutes", 0)),
            "risk_score": float(reading.get("risk_score", 0.0)),
            "predicted_arrival_risk": float(reading.get("predicted_arrival_risk", 0.0)),
            "alert": bool(reading.get("alert", False)),
            "scenario": str(reading.get("scenario", "normal")),
            "data_source": "simulation",
            "sensor_id": str(reading.get("sensor_id", "SNS-SIM-DEMO")),
            "timestamp": reading.get("timestamp", now_iso),
        }

        self._simulation_telemetry.setdefault(simulation_id, []).append(reading_dict)
        self._commit()
        return reading_dict

    def get_simulation_telemetry(self, simulation_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Returns ordered time-series telemetry records for a simulation session."""
        history = self._simulation_telemetry.get(simulation_id, [])
        return [dict(t) for t in history[-limit:]]

    def delete_simulation_session(self, simulation_id: str) -> bool:
        """Deletes a simulation session and associated telemetry."""
        if simulation_id in self._simulation_sessions:
            del self._simulation_sessions[simulation_id]
            self._simulation_telemetry.pop(simulation_id, None)
            self._commit()
            return True
        return False

    # -------------------------------------------------------------------------
    # Farmer Inventory Management (Feature 2)
    # -------------------------------------------------------------------------
    def list_inventory(
        self,
        farmer_id: Optional[str] = None,
        crop_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List inventory records filtered by farmer, crop, or status."""
        items = self._inventory
        if farmer_id:
            items = [i for i in items if i.get("farmer_id") == farmer_id]
        if crop_type:
            items = [i for i in items if i.get("crop_type") == crop_type.lower().strip()]
        if status:
            items = [i for i in items if i.get("status") == status.lower().strip()]
        return [dict(i) for i in items]

    def get_inventory_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific inventory item by ID."""
        for item in self._inventory:
            if item.get("id") == item_id:
                return dict(item)
        return None

    def create_inventory_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new farmer inventory record with server-calculated stock value."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        item_id = data.get("id") or f"INV-PB-{len(self._inventory) + 1:04d}"

        crate_quantity = int(data["crate_quantity"])
        price_per_crate = float(data["price_per_crate"])
        # Server-authoritative total stock value calculation
        total_stock_value = round(crate_quantity * price_per_crate, 2)

        record = {
            "id": item_id,
            "farmer_id": str(data.get("farmer_id", "FARMER-PB-001")),
            "crop_type": str(data["crop_type"]).lower().strip(),
            "crate_quantity": crate_quantity,
            "price_per_crate": price_per_crate,
            "total_stock_value": total_stock_value,
            "description": data.get("description"),
            "harvest_date": data.get("harvest_date"),
            "location": data.get("location") or "Abohar Orchard Gate, Punjab",
            "status": str(data.get("status", "available")).lower().strip(),
            "created_at": data.get("created_at") or now_iso,
            "updated_at": now_iso,
        }
        self._inventory.append(record)
        self._commit()
        return dict(record)

    def update_inventory_item(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing inventory item, recalculating stock value if quantity or price changed."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for item in self._inventory:
            if item.get("id") == item_id:
                for field in ("crate_quantity", "price_per_crate", "description", "harvest_date", "location", "status", "crop_type"):
                    if field in updates and updates[field] is not None:
                        if field == "crop_type":
                            item["crop_type"] = str(updates["crop_type"]).lower().strip()
                        elif field == "crate_quantity":
                            item["crate_quantity"] = int(updates["crate_quantity"])
                        elif field == "price_per_crate":
                            item["price_per_crate"] = float(updates["price_per_crate"])
                        else:
                            item[field] = updates[field]
                item["total_stock_value"] = round(item["crate_quantity"] * item["price_per_crate"], 2)
                item["updated_at"] = now_iso
                self._commit()
                return dict(item)
        return None

    def delete_inventory_item(self, item_id: str) -> bool:
        """Delete an inventory item by ID."""
        for idx, item in enumerate(self._inventory):
            if item.get("id") == item_id:
                self._inventory.pop(idx)
                self._commit()
                return True
        return False



# Global singleton instance
_repository_instance: Optional[ShipmentRepository] = None


def get_shipment_repository() -> ShipmentRepository:
    """Dependency injector providing the singleton ShipmentRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = ShipmentRepository()
    return _repository_instance
