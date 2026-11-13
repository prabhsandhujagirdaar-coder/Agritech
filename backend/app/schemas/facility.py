"""
AgriChain AI — Storage Facility & Godown Schemas
================================================
Defines strongly-typed request and response contracts for Indian agricultural
godowns, packhouses, cold-storage facilities, and mandis.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class FacilityType(str, Enum):
    PACKHOUSE = "packhouse"
    GODOWN = "godown"
    WAREHOUSE = "warehouse"
    COLD_STORAGE = "cold_storage"
    MANDI = "mandi"


class FacilityStatus(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"
    FULL = "full"


class FacilityVerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    DEMO_SIMULATED = "demo_simulated"


class FacilityRecord(BaseModel):
    id: str = Field(..., description="Unique facility identifier (e.g. FAC-PB-PAG-BARA, FAC-PB-ABO-01).")
    name: str = Field(..., description="Official/listed facility name from public sources.")
    facility_type: str = Field(..., description="Facility classification (packhouse, godown, warehouse, cold_storage, mandi).")
    address: str = Field(..., description="Physical street address or industrial sector.")
    village_or_city: str = Field(..., description="City or village name.")
    district: str = Field(..., description="Administrative district (e.g. Fazilka, Hoshiarpur, Fatehgarh Sahib).")
    state: str = Field(default="Punjab", description="Indian state name.")
    postal_code: Optional[str] = Field(default=None, description="6-digit Indian PIN code where available.")
    latitude: Optional[float] = Field(default=None, ge=8.0, le=37.5, description="WGS84 Latitude within India (null if unknown).")
    longitude: Optional[float] = Field(default=None, ge=68.0, le=97.5, description="WGS84 Longitude within India (null if unknown).")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="Standardized {latitude, longitude} pair or None.")
    contact_phone: Optional[str] = Field(default=None, description="Public telephone or mobile contact if documented.")
    contact_email: Optional[str] = Field(default=None, description="Public administrative email if documented.")
    capacity: Optional[float] = Field(default=None, ge=0.0, description="Published storage capacity (null if not officially documented).")
    capacity_unit: Optional[str] = Field(default=None, description="Capacity measurement unit (e.g. MT, crates).")
    current_utilization: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Current occupancy percentage (null unless real feed exists).")
    storage_temperature_min_c: Optional[float] = Field(default=None, description="Recommended min storage temp (°C) if documented.")
    storage_temperature_max_c: Optional[float] = Field(default=None, description="Recommended max storage temp (°C) if documented.")
    supported_commodities: Optional[list[str]] = Field(default=None, description="Supported commodities only where documented.")
    operational_status: Optional[str] = Field(default=None, description="Operational availability status (active, maintenance, inactive, unconfirmed).")
    guava_suitability_category: Optional[str] = Field(default=None, description="Guava supply chain suitability: guava_confirmed, horticulture_unconfirmed, ambient_grain, cold_store_unknown, wholesale_market.")
    source_citation_type: Optional[str] = Field(default=None, description="Citation tier: direct_document, facility_page, official_portal, committee_proceeding, directory_level_reference.")
    legal_entity_verification: Optional[str] = Field(default=None, description="Legal entity registration status: verified, unverified.")
    physical_facility_verification: Optional[str] = Field(default=None, description="Physical site existence verification status: verified, partially_verified, unverified.")
    source_name: Optional[str] = Field(default=None, description="Official publishing authority or agency (e.g. PAGREXCO, NHB, PSWC).")
    source_url: Optional[str] = Field(default=None, description="Official public source URL or document reference.")
    source_record: Optional[str] = Field(default=None, description="Source record, gazette notice, or EOI identifier.")
    verification_status: str = Field(default="verified", description="Pedigree status: verified, partially_verified, unverified.")
    verification_date: Optional[str] = Field(default=None, description="ISO date of source verification.")
    last_source_check: Optional[str] = Field(default=None, description="ISO date when source URL/record was last audited.")
    coordinate_source: Optional[str] = Field(default=None, description="Provenance of geographic coordinates.")
    geocoding_confidence: Optional[str] = Field(default=None, description="Geocoding accuracy level: rooftop, facility_campus, village_level, unverified.")
    data_provenance: Optional[str] = Field(default=None, description="Detailed provenance notes and sourcing history.")
    location_verification_status: str = Field(default="verified", description="Backward-compatible pedigree status.")
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp.")


class FacilityCreateRequest(BaseModel):
    id: Optional[str] = Field(default=None, description="Optional custom ID; auto-assigned if omitted.")
    name: str = Field(..., min_length=3, max_length=255)
    facility_type: FacilityType = Field(default=FacilityType.GODOWN)
    address: str = Field(..., min_length=3, max_length=255)
    village_or_city: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    state: str = Field(default="Punjab", min_length=2, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    latitude: Optional[float] = Field(default=None, ge=8.0, le=37.5, description="Latitude within India.")
    longitude: Optional[float] = Field(default=None, ge=68.0, le=97.5, description="Longitude within India.")
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    contact_email: Optional[str] = Field(default=None, max_length=120)
    capacity: Optional[float] = Field(default=None, ge=0.0)
    capacity_unit: Optional[str] = Field(default=None, max_length=20)
    current_utilization: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    storage_temperature_min_c: Optional[float] = Field(default=None)
    storage_temperature_max_c: Optional[float] = Field(default=None)
    supported_commodities: Optional[list[str]] = Field(default=None)
    operational_status: Optional[str] = Field(default=None)
    guava_suitability_category: Optional[str] = Field(default=None)
    source_citation_type: Optional[str] = Field(default=None)
    legal_entity_verification: Optional[str] = Field(default=None)
    physical_facility_verification: Optional[str] = Field(default=None)
    source_name: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[str] = Field(default=None, max_length=1000)
    source_record: Optional[str] = Field(default=None, max_length=255)
    verification_status: FacilityVerificationStatus = Field(default=FacilityVerificationStatus.VERIFIED)
    verification_date: Optional[str] = Field(default=None)
    last_source_check: Optional[str] = Field(default=None)
    coordinate_source: Optional[str] = Field(default=None, max_length=255)
    geocoding_confidence: Optional[str] = Field(default=None, max_length=50)
    data_provenance: Optional[str] = Field(default=None)
    location_verification_status: Optional[FacilityVerificationStatus] = Field(default=None)

