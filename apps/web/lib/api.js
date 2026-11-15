/**
 * AgriChain AI — Centralized REST API Client
 * Wraps all Next.js proxy route handlers connected to FastAPI backend.
 * Provides geospatial validation for Indian agricultural supply chains.
 */

// India mainland geographical bounding box
export const INDIA_BOUNDS = {
  latMin: 8.0,
  latMax: 37.5,
  lonMin: 68.0,
  lonMax: 97.5,
};

// Punjab & Northern India corridor focus area
export const PUNJAB_CORRIDOR_BOUNDS = {
  latMin: 28.0,
  latMax: 32.6,
  lonMin: 73.5,
  lonMax: 77.8,
};

/**
 * Validates WGS84 geographic coordinate bounds.
 * Latitude must be in [-90, 90], Longitude must be in [-180, 180].
 */
export function isValidCoordinate(lat, lng) {
  if (typeof lat !== "number" || typeof lng !== "number") return false;
  if (Number.isNaN(lat) || Number.isNaN(lng)) return false;
  return lat >= -90.0 && lat <= 90.0 && lng >= -180.0 && lng <= 180.0;
}

/**
 * Checks if coordinates fall within Indian geographic boundaries.
 */
export function isWithinIndia(lat, lng) {
  if (!isValidCoordinate(lat, lng)) return false;
  return (
    lat >= INDIA_BOUNDS.latMin &&
    lat <= INDIA_BOUNDS.latMax &&
    lng >= INDIA_BOUNDS.lonMin &&
    lng <= INDIA_BOUNDS.lonMax
  );
}

/**
 * Checks if coordinates fall within Punjab and northern agricultural corridor.
 */
export function isWithinPunjabCorridor(lat, lng) {
  if (!isValidCoordinate(lat, lng)) return false;
  return (
    lat >= PUNJAB_CORRIDOR_BOUNDS.latMin &&
    lat <= PUNJAB_CORRIDOR_BOUNDS.latMax &&
    lng >= PUNJAB_CORRIDOR_BOUNDS.lonMin &&
    lng <= PUNJAB_CORRIDOR_BOUNDS.lonMax
  );
}

/**
 * Extracts and normalizes valid [latitude, longitude] from shipment object.
 * Returns null if no valid coordinates exist (never fabricates default locations).
 */
export function normalizeShipmentCoordinates(shipment) {
  if (!shipment) return null;

  // 1. Check current_coordinates field
  if (shipment.current_coordinates) {
    const { latitude, longitude } = shipment.current_coordinates;
    if (isValidCoordinate(latitude, longitude)) {
      return [latitude, longitude];
    }
  }

  // 2. Fallback to latest_waypoint
  if (shipment.latest_waypoint) {
    const { latitude, longitude } = shipment.latest_waypoint;
    if (isValidCoordinate(latitude, longitude)) {
      return [latitude, longitude];
    }
  }

  // 3. Fallback to top-level latitude/longitude if present
  if (typeof shipment.latitude === "number" && typeof shipment.longitude === "number") {
    if (isValidCoordinate(shipment.latitude, shipment.longitude)) {
      return [shipment.latitude, shipment.longitude];
    }
  }

  return null;
}

/**
 * Formats a [latitude, longitude] array into human-readable cardinal string.
 */
export function formatCoordinates(coords) {
  if (!coords || !Array.isArray(coords) || coords.length !== 2) {
    return "Location Unavailable";
  }
  const [lat, lon] = coords;
  if (!isValidCoordinate(lat, lon)) {
    return "Location Unavailable";
  }
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(4)}° ${latDir}, ${Math.abs(lon).toFixed(4)}° ${lonDir}`;
}

// ----------------------------------------------------------------------------
// Shipments API
// ----------------------------------------------------------------------------
export async function fetchShipments() {
  const res = await fetch("/api/shipments", { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server returned ${res.status}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchShipment(id) {
  const res = await fetch(`/api/shipments/${id}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch shipment ${id}`);
  }
  return res.json();
}

export async function fetchShipmentWaypoints(id) {
  const res = await fetch(`/api/shipments/${id}/waypoints`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch waypoints for ${id}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchShipmentRisk(id) {
  const res = await fetch(`/api/shipments/${id}/risk`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch risk for ${id}`);
  }
  return res.json();
}

/**
 * Fetches dynamic, real-road highway route geometry and distance for a specific shipment.
 * Origin and destination coordinates are calculated strictly from the selected shipment's endpoints.
 */
export async function fetchShipmentRoute(id, options = {}) {
  const { signal } = options;
  const res = await fetch(`/api/shipments/${id}/route`, {
    cache: "no-store",
    signal,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch dynamic road route for shipment ${id}`);
  }
  return res.json();
}

export async function fetchShipmentTelemetry(id, skip = 0, limit = 100) {
  const res = await fetch(`/api/shipments/${id}/telemetry?skip=${skip}&limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch telemetry for ${id}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function createShipment(payload) {
  const res = await fetch("/api/shipments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create shipment");
  }
  return res.json();
}

export async function addShipmentWaypoint(id, waypointData) {
  const res = await fetch(`/api/shipments/${id}/waypoints`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(waypointData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to record waypoint");
  }
  return res.json();
}

export async function addShipmentTelemetry(id, telemetryData) {
  const res = await fetch(`/api/shipments/${id}/telemetry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(telemetryData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to log telemetry");
  }
  return res.json();
}

export async function simulateShipmentStep(id) {
  const res = await fetch(`/api/shipments/${id}/simulate-step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to simulate shipment step");
  }
  return res.json();
}

export async function evaluateLstmRisk(shipmentId, sequence) {
  const res = await fetch("/api/telemetry/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shipment_id: shipmentId, sequence }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to evaluate LSTM risk sequence");
  }
  return res.json();
}

/**
 * Checks if a facility record possesses valid, plottable WGS84 geographic coordinates within India.
 * Prevents map errors and guarantees invalid/missing coordinates are never rendered on the map.
 */
export function hasValidFacilityCoordinates(facility) {
  if (!facility) return false;
  const lat = facility.latitude != null ? facility.latitude : facility.coordinates?.latitude;
  const lon = facility.longitude != null ? facility.longitude : facility.coordinates?.longitude;
  return isValidCoordinate(lat, lon) && isWithinIndia(lat, lon);
}

// ----------------------------------------------------------------------------
// Storage Facilities & Godowns API
// ----------------------------------------------------------------------------
export async function fetchFacilities(filters = {}) {
  const query = new URLSearchParams();
  if (filters.facility_type && filters.facility_type !== "all") query.set("facility_type", filters.facility_type);
  if (filters.district && filters.district !== "all") query.set("district", filters.district);
  if (filters.state && filters.state !== "all") query.set("state", filters.state);
  if (filters.operational_status && filters.operational_status !== "all") query.set("operational_status", filters.operational_status);
  if (filters.verification_status && filters.verification_status !== "all") query.set("verification_status", filters.verification_status);
  if (filters.guava_suitability && filters.guava_suitability !== "all") query.set("guava_suitability", filters.guava_suitability);
  if (filters.q && filters.q.trim()) query.set("q", filters.q.trim());

  const queryString = query.toString() ? `?${query.toString()}` : "";
  const res = await fetch(`/api/facilities${queryString}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch facilities (${res.status})`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchFacility(id) {
  const res = await fetch(`/api/facilities/${id}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch facility ${id}`);
  }
  return res.json();
}

export async function createFacility(payload) {
  const res = await fetch("/api/facilities", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to register storage facility");
  }
  return res.json();
}

export async function fetchFacilitySuitability(id, operation = null, crop = "guava") {
  const query = new URLSearchParams();
  if (operation) query.set("operation", operation);
  if (crop) query.set("crop", crop);
  const queryString = query.toString() ? `?${query.toString()}` : "";
  const res = await fetch(`/api/facilities/${id}/suitability${queryString}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to evaluate suitability for facility ${id}`);
  }
  return res.json();
}

export async function fetchShipmentEvents(id) {
  const res = await fetch(`/api/shipments/${id}/events`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch events for shipment ${id}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function addShipmentEvent(id, eventData) {
  const res = await fetch(`/api/shipments/${id}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(eventData),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to record event for shipment ${id}`);
  }
  return res.json();
}

/**
 * Fetch available produce listings in the B2B marketplace.
 */
export async function fetchMarketplaceListings() {
  const res = await fetch("/api/orders/listings", { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch marketplace listings");
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/**
 * Submit a demo purchase order for a verified produce lot.
 */
export async function createDemoOrder(orderPayload) {
  const res = await fetch("/api/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(orderPayload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Failed to place demo purchase order");
  }
  return data;
}

/**
 * Fetch recorded demo orders, optionally filtered by buyer.
 */
export async function fetchDemoOrders(buyerName = null) {
  const query = buyerName ? `?buyer_name=${encodeURIComponent(buyerName)}` : "";
  const res = await fetch(`/api/orders${query}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch demo orders");
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/**
 * Check backend health status.
 */
export async function fetchBackendHealth() {
  const res = await fetch("/api/health", { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  return {
    ok: res.ok,
    status: res.status,
    data,
  };
}

// ============================================================================
// Dynamic Real-Road Vehicle Simulation API Client Methods
// ============================================================================

/**
 * Searches Indian mandis, facilities, villages, and logistics hubs.
 */
export async function searchSimulationLocations(query, limit = 8) {
  if (!query || query.trim().length < 2) return [];
  const res = await fetch("/api/simulations/geocoding/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: query.trim(), limit }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Location search failed");
  }
  return res.json();
}

/**
 * Previews real-road highway driving route between coordinates via OSRM.
 */
export async function previewSimulationRoute(routeParams) {
  const res = await fetch("/api/simulations/routes/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(routeParams),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Route preview calculation failed");
  }
  return res.json();
}

/**
 * Creates an authoritative server-side simulation session along real road polyline.
 */
export async function createSimulationSession(sessionPayload) {
  const res = await fetch("/api/simulations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sessionPayload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create simulation session");
  }
  return res.json();
}

/**
 * Retrieves details and latest state of a simulation session.
 */
export async function fetchSimulationSession(id) {
  const res = await fetch(`/api/simulations/${id}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch simulation session ${id}`);
  }
  return res.json();
}

/**
 * Lists simulation sessions, optionally filtered by shipment.
 */
export async function fetchSimulationSessions(shipmentId = null) {
  const query = shipmentId ? `?shipment_id=${encodeURIComponent(shipmentId)}` : "";
  const res = await fetch(`/api/simulations${query}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch simulation sessions");
  }
  return res.json();
}

/**
 * Dispatches control actions (start, pause, resume, stop, reset, step) to simulation.
 */
export async function controlSimulation(id, action, advanceKm = null) {
  const query = advanceKm != null ? `?advance_km=${encodeURIComponent(advanceKm)}` : "";
  const res = await fetch(`/api/simulations/${id}/${action}${query}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Simulation control '${action}' failed`);
  }
  return res.json();
}

/**
 * Updates simulation speed multiplier or cold-chain scenario dynamically.
 */
export async function updateSimulationControls(id, { speed_multiplier, scenario }) {
  const res = await fetch(`/api/simulations/${id}/controls`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "update", speed_multiplier, scenario }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update simulation controls");
  }
  return res.json();
}

/**
 * Fetches time-series telemetry records for a simulation session.
 */
export async function fetchSimulationTelemetry(id, limit = 200) {
  const res = await fetch(`/api/simulations/${id}/telemetry?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch simulation telemetry");
  }
  return res.json();
}

/**
 * Fetches full route and telemetry track history for historical replay.
 */
export async function fetchSimulationHistory(id, limit = 500) {
  const res = await fetch(`/api/simulations/${id}/history?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch simulation history");
  }
  return res.json();
}

/**
 * ============================================================================
 * Farmer Stock & Inventory Management APIs (Feature 2)
 * ============================================================================
 */

/**
 * Fetches the supported marketplace crops catalogue.
 */
export async function fetchCropCatalogue() {
  const res = await fetch("/api/inventory/crops", { cache: "no-store" });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch crop catalogue");
  }
  return res.json();
}

/**
 * Fetches inventory items for a farmer or platform view.
 */
export async function fetchFarmerInventory(params = {}, headers = {}) {
  const query = new URLSearchParams();
  if (params.farmer_id) query.set("farmer_id", params.farmer_id);
  if (params.crop_type) query.set("crop_type", params.crop_type);
  if (params.status) query.set("status", params.status);

  const url = `/api/inventory${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "GET",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch farmer inventory");
  }
  return res.json();
}

/**
 * Creates a new farmer stock item.
 */
export async function createInventoryItem(payload, headers = {}) {
  const res = await fetch("/api/inventory", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create inventory item");
  }
  return res.json();
}

/**
 * Updates an existing stock item.
 */
export async function updateInventoryItem(id, updates, headers = {}) {
  const res = await fetch(`/api/inventory/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: JSON.stringify(updates),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update inventory item");
  }
  return res.json();
}

/**
 * Deletes an inventory record.
 */
export async function deleteInventoryItem(id, headers = {}) {
  const res = await fetch(`/api/inventory/${id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete inventory item");
  }
  return res.json();
}


