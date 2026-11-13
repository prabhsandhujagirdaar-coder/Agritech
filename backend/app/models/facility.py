"""
AgriChain AI — Storage Facility Model Declarations
==================================================
Entity models for agricultural godowns, packhouses, warehouses, and mandis.
Compatible with SQLAlchemy ORM and standard dataclasses for universal execution.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class StorageFacilityModel:
    """Relational entity representing an agricultural storage facility or godown."""
    id: str
    name: str
    facility_type: str  # packhouse, godown, warehouse, cold_storage, mandi
    address: str
    village_or_city: str
    district: str
    state: str = "Punjab"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    capacity: Optional[float] = None
    capacity_unit: Optional[str] = None
    current_utilization: Optional[float] = None
    storage_temperature_min_c: Optional[float] = None
    storage_temperature_max_c: Optional[float] = None
    supported_commodities: Optional[list[str]] = None
    operational_status: Optional[str] = None  # active, maintenance, inactive, full, unconfirmed
    guava_suitability_category: Optional[str] = None  # guava_confirmed, horticulture_unconfirmed, ambient_grain, cold_store_unknown, wholesale_market
    source_citation_type: Optional[str] = None  # direct_document, facility_page, official_portal, committee_proceeding, directory_level_reference
    legal_entity_verification: Optional[str] = None  # verified, unverified
    physical_facility_verification: Optional[str] = None  # verified, partially_verified, unverified
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_record: Optional[str] = None
    verification_status: str = "verified"  # verified, partially_verified, unverified
    verification_date: Optional[str] = None
    last_source_check: Optional[str] = None
    coordinate_source: Optional[str] = None
    geocoding_confidence: Optional[str] = None
    data_provenance: Optional[str] = None
    location_verification_status: str = "verified"
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        coords = None
        if self.latitude is not None and self.longitude is not None:
            coords = {
                "latitude": float(self.latitude),
                "longitude": float(self.longitude),
            }
        return {
            "id": self.id,
            "name": self.name,
            "facility_type": self.facility_type,
            "address": self.address,
            "village_or_city": self.village_or_city,
            "district": self.district,
            "state": self.state,
            "postal_code": self.postal_code,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "coordinates": coords,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "capacity": float(self.capacity) if self.capacity is not None else None,
            "capacity_unit": self.capacity_unit,
            "current_utilization": float(self.current_utilization) if self.current_utilization is not None else None,
            "storage_temperature_min_c": float(self.storage_temperature_min_c) if self.storage_temperature_min_c is not None else None,
            "storage_temperature_max_c": float(self.storage_temperature_max_c) if self.storage_temperature_max_c is not None else None,
            "supported_commodities": list(self.supported_commodities) if self.supported_commodities else None,
            "operational_status": self.operational_status,
            "guava_suitability_category": self.guava_suitability_category,
            "source_citation_type": self.source_citation_type,
            "legal_entity_verification": self.legal_entity_verification,
            "physical_facility_verification": self.physical_facility_verification,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_record": self.source_record,
            "verification_status": self.verification_status,
            "verification_date": self.verification_date,
            "last_source_check": self.last_source_check,
            "coordinate_source": self.coordinate_source,
            "geocoding_confidence": self.geocoding_confidence,
            "data_provenance": self.data_provenance,
            "location_verification_status": self.location_verification_status or self.verification_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
