/**
 * AgriChain AI — Frontend Type Definitions
 * Typed contracts matching FastAPI schemas and PostGIS spatial entities.
 */

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface StorageFacility {
  id: string;
  name: string;
  facility_type: "packhouse" | "godown" | "warehouse" | "cold_storage" | "mandi" | string;
  address: string;
  village_or_city: string;
  district: string;
  state: string;
  postal_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  coordinates?: Coordinates | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  capacity?: number | null;
  capacity_unit?: string | null;
  current_utilization?: number | null;
  storage_temperature_min_c?: number | null;
  storage_temperature_max_c?: number | null;
  supported_commodities?: string[] | null;
  operational_status: "active" | "maintenance" | "inactive" | "full" | string;
  source_name?: string | null;
  source_url?: string | null;
  source_record?: string | null;
  verification_status: "verified" | "partially_verified" | "unverified" | string;
  verification_date?: string | null;
  last_source_check?: string | null;
  coordinate_source?: string | null;
  geocoding_confidence?: "rooftop" | "facility_campus" | "village_level" | "unverified" | string | null;
  data_provenance?: string | null;
  location_verification_status?: string;
  created_at: string;
  updated_at: string;
}

export interface Waypoint {
  id: string;
  shipment_id: string;
  longitude: number;
  latitude: number;
  srid: number;
  altitude_m?: number | null;
  speed_kmh?: number | null;
  heading_deg?: number | null;
  location_metadata?: Record<string, any>;
  recorded_at: string;
}

export interface Shipment {
  id: string;
  produce_type: string;
  produce: string;
  origin: string;
  destination: string;
  origin_facility_id?: string | null;
  destination_facility_id?: string | null;
  origin_facility?: StorageFacility | null;
  destination_facility?: StorageFacility | null;
  status: "created" | "in_transit" | "delivered" | "delayed" | "quarantined" | string;
  quantity: number;
  quantity_crates: number;
  temperature_c?: number | null;
  humidity_pct?: number | null;
  risk_index: number;
  created_at: string;
  last_update: string;
  current_coordinates?: Coordinates | null;
  latest_waypoint?: Waypoint | null;
}

export interface TelemetryRecord {
  id: string;
  shipment_id: string;
  temperature: number;
  humidity: number;
  sensor_id: string;
  location: string;
  timestamp: string;
}

export interface ShipmentRiskInfo {
  shipment_id: string;
  current_risk: number;
  predicted_arrival_risk: number;
  alert: boolean;
  telemetry_points_evaluated: number;
  avg_temperature_c: number;
  excursion_events: number;
}
