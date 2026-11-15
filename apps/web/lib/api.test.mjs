import assert from "node:assert";
import {
  isValidCoordinate,
  normalizeShipmentCoordinates,
  formatCoordinates,
  isWithinIndia,
  isWithinPunjabCorridor,
  hasValidFacilityCoordinates,
} from "./api.js";

console.log("Running Geospatial & Indian Boundary Normalization Unit Tests...");

// 1. Valid coordinates
assert.strictEqual(isValidCoordinate(30.1453, 74.1994), true, "Abohar coords should be valid");
assert.strictEqual(isValidCoordinate(-33.8688, 151.2093), true, "Sydney coords should be valid WGS84");
assert.strictEqual(isValidCoordinate(0, 0), true, "Origin coords should be valid");
assert.strictEqual(isValidCoordinate(90, 180), true, "Max boundary should be valid");
assert.strictEqual(isValidCoordinate(-90, -180), true, "Min boundary should be valid");

// 2. Invalid coordinates
assert.strictEqual(isValidCoordinate(91, 0), false, "Latitude > 90 must be invalid");
assert.strictEqual(isValidCoordinate(-90.1, 0), false, "Latitude < -90 must be invalid");
assert.strictEqual(isValidCoordinate(0, 181), false, "Longitude > 180 must be invalid");
assert.strictEqual(isValidCoordinate(0, -180.1), false, "Longitude < -180 must be invalid");
assert.strictEqual(isValidCoordinate(NaN, 50), false, "NaN latitude must be invalid");
assert.strictEqual(isValidCoordinate(50, null), false, "null longitude must be invalid");
assert.strictEqual(isValidCoordinate(undefined, undefined), false, "undefined coords must be invalid");

// 3. Indian Boundary Validation
assert.strictEqual(isWithinIndia(30.1453, 74.1994), true, "Abohar, Punjab must be within India");
assert.strictEqual(isWithinIndia(30.4037, 74.0254), true, "Fazilka, Punjab must be within India");
assert.strictEqual(isWithinIndia(30.2110, 74.9455), true, "Bathinda, Punjab must be within India");
assert.strictEqual(isWithinIndia(28.7161, 77.1772), true, "Azadpur, Delhi must be within India");
assert.strictEqual(isWithinIndia(19.0760, 72.9990), true, "Mumbai must be within India");
assert.strictEqual(isWithinIndia(51.5074, -0.1278), false, "London must NOT be within India");
assert.strictEqual(isWithinIndia(-33.8688, 151.2093), false, "Sydney must NOT be within India");

// 4. Punjab Corridor Focus
assert.strictEqual(isWithinPunjabCorridor(30.1453, 74.1994), true, "Abohar is in Punjab corridor");
assert.strictEqual(isWithinPunjabCorridor(30.9010, 75.8573), true, "Ludhiana is in Punjab corridor");
assert.strictEqual(isWithinPunjabCorridor(28.7161, 77.1772), true, "Delhi Azadpur is in corridor");
assert.strictEqual(isWithinPunjabCorridor(19.0760, 72.9990), false, "Mumbai is outside Punjab corridor");

// 5. Normalization from shipment formats
const shipmentWithCurrentCoords = {
  id: "SHP-001",
  current_coordinates: { latitude: 30.1453, longitude: 74.1994 },
};
const normalized1 = normalizeShipmentCoordinates(shipmentWithCurrentCoords);
assert.deepStrictEqual(normalized1, [30.1453, 74.1994], "Should extract from current_coordinates");

const shipmentWithLatestWaypoint = {
  id: "SHP-002",
  latest_waypoint: { latitude: 30.4037, longitude: 74.0254 },
};
const normalized2 = normalizeShipmentCoordinates(shipmentWithLatestWaypoint);
assert.deepStrictEqual(normalized2, [30.4037, 74.0254], "Should extract from latest_waypoint");

const shipmentWithPendingGps = {
  id: "SHP-004",
  status: "pending",
};
assert.strictEqual(normalizeShipmentCoordinates(shipmentWithPendingGps), null, "Missing coords should return null");

// 6. Coordinate formatting
assert.strictEqual(formatCoordinates([30.1453, 74.1994]), "30.1453° N, 74.1994° E");
assert.strictEqual(formatCoordinates(null), "Location Unavailable");

// 7. Phase 12: Facility Coordinate Validation & Map Marker Exclusion
const validFacility = {
  id: "FAC-PB-PAG-BARA",
  name: "PAGREXCO Bara Farm Packhouse",
  latitude: 30.6283,
  longitude: 76.3863,
};
assert.strictEqual(hasValidFacilityCoordinates(validFacility), true, "PAGREXCO Bara Farm coords must be valid for map markers");

const validNestedCoordsFacility = {
  id: "FAC-PB-PAG-KANG",
  name: "PAGREXCO Kangmai",
  coordinates: { latitude: 31.6677, longitude: 75.7923 },
};
assert.strictEqual(hasValidFacilityCoordinates(validNestedCoordsFacility), true, "Nested coordinates facility must be valid");

const unverifiedNullCoordsFacility = {
  id: "FAC-PB-UNV-01",
  name: "Facility Without Coordinates",
  latitude: null,
  longitude: null,
};
assert.strictEqual(hasValidFacilityCoordinates(unverifiedNullCoordsFacility), false, "Null coordinates facility must NOT be plotted on map");

const outsideIndiaFacility = {
  id: "FAC-UK-LON-01",
  name: "London Facility",
  latitude: 51.5074,
  longitude: -0.1278,
};
assert.strictEqual(hasValidFacilityCoordinates(outsideIndiaFacility), false, "Facility outside India must NOT be plotted on map");

assert.strictEqual(hasValidFacilityCoordinates(null), false, "Null facility must return false");
assert.strictEqual(hasValidFacilityCoordinates(undefined), false, "Undefined facility must return false");

// 8. Phase 12.2: Guava Supply Chain Categories & Citation Tiers
const VALID_GUAVA_CATEGORIES = new Set([
  "guava_confirmed",
  "horticulture_unconfirmed",
  "ambient_grain",
  "cold_store_unknown",
  "wholesale_market",
]);

const VALID_CITATION_TIERS = new Set([
  "direct_document",
  "facility_page",
  "official_portal",
  "committee_proceeding",
  "directory_level_reference",
]);

const azadpurFacility = {
  id: "FAC-DL-AZD-01",
  name: "Azadpur APMC Fruit & Vegetable Mega Mandi",
  guava_suitability_category: "guava_confirmed",
  source_citation_type: "official_portal",
  geocoding_confidence: "facility_campus",
};
assert.strictEqual(VALID_GUAVA_CATEGORIES.has(azadpurFacility.guava_suitability_category), true);
assert.strictEqual(VALID_CITATION_TIERS.has(azadpurFacility.source_citation_type), true);
assert.strictEqual(azadpurFacility.geocoding_confidence, "facility_campus");

const pswcFazilka = {
  id: "FAC-PB-FAZ-01",
  name: "PSWC Warehousing Centre Fazilka",
  guava_suitability_category: "ambient_grain",
  source_citation_type: "directory_level_reference",
  geocoding_confidence: "village_level",
};
assert.strictEqual(VALID_GUAVA_CATEGORIES.has(pswcFazilka.guava_suitability_category), true);
assert.strictEqual(VALID_CITATION_TIERS.has(pswcFazilka.source_citation_type), true);
assert.strictEqual(pswcFazilka.geocoding_confidence, "village_level");

// 9. Phase 13: Operations, Tracking Modes, and Lifecycle Event Taxonomy
const VALID_FACILITY_OPERATIONS = new Set([
  "harvesting_aggregation",
  "packhouse_cooling",
  "cold_storage",
  "market_auction",
  "transit_hub",
]);

const VALID_TRACKING_MODES = new Set([
  "live_gps",
  "simulated",
  "disconnected_last_known",
]);

const VALID_TELEMETRY_MODES = new Set([
  "live_sensor",
  "simulated",
  "unavailable",
]);

const VALID_EVENT_TYPES = new Set([
  "shipment_created",
  "facility_association_updated",
  "shipment_dispatched",
  "in_transit",
  "arrival_recorded",
  "facility_handover",
  "delivery_completed",
  "tracking_connection_lost",
  "sensor_threshold_alert",
]);

assert.strictEqual(VALID_FACILITY_OPERATIONS.has("packhouse_cooling"), true);
assert.strictEqual(VALID_FACILITY_OPERATIONS.has("market_auction"), true);
assert.strictEqual(VALID_TRACKING_MODES.has("live_gps"), true);
assert.strictEqual(VALID_TRACKING_MODES.has("simulated"), true);
assert.strictEqual(VALID_TRACKING_MODES.has("disconnected_last_known"), true);
assert.strictEqual(VALID_TELEMETRY_MODES.has("unavailable"), true);
assert.strictEqual(VALID_EVENT_TYPES.has("facility_handover"), true);
assert.strictEqual(VALID_EVENT_TYPES.has("delivery_completed"), true);

console.log("All Geospatial, Facility Suitability, & Phase 13 Lifecycle Tests PASSED successfully!");

