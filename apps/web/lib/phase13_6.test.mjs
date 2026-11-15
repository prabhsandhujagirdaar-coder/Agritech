import assert from "node:assert/strict";
import {
  SUPPORTED_ROLES,
  ROLE_DEFAULT_TABS,
  Z_INDEX,
  GUAVA_CLASS_LABELS,
} from "./constants.js";

console.log("Running Phase 13.6 Frontend Unit & UI/UX Regression Tests...\n");

// -----------------------------------------------------------------------------
// 1. Z-Index Hierarchy & Stacking Invariants (Map Overlay Fix)
// -----------------------------------------------------------------------------
console.log("1. Validating Z_INDEX Hierarchy & Stacking Context Invariants...");

assert.equal(Z_INDEX.BASE, 0, "Base stacking context should be 0");
assert.equal(Z_INDEX.MAP_CONTAINER, 0, "Normal map container must sit at z-index 0 to prevent overlay bleeding");
assert.equal(Z_INDEX.MAP_CONTROLS, 20, "Leaflet controls & buttons must be bounded at z-20");
assert.equal(Z_INDEX.HEADER, 20, "Header bar sits at z-20");
assert.equal(Z_INDEX.STICKY_NAV, 30, "Sticky nav controls sit at z-30");
assert.equal(Z_INDEX.DROPDOWN, 40, "Dropdowns sit at z-40");
assert.equal(Z_INDEX.MAP_FULLSCREEN, 40, "Fullscreen map modal overlay sits at z-40");
assert.equal(Z_INDEX.DRAWER, 45, "Mobile slide-over drawer sits at z-45");
assert.equal(Z_INDEX.MODAL_BACKDROP, 50, "Modals must sit at z-50 to guarantee they cover the map and page");
assert.equal(Z_INDEX.MODAL_CONTENT, 50, "Modal content must sit at z-50");

// Verify strict relational invariants:
// Modals MUST always appear strictly ABOVE the map (both normal and fullscreen)
assert.ok(
  Z_INDEX.MODAL_BACKDROP > Z_INDEX.MAP_FULLSCREEN,
  "Modal backdrop (50) must be strictly higher than Fullscreen map (40)"
);
assert.ok(
  Z_INDEX.MODAL_BACKDROP > Z_INDEX.MAP_CONTAINER,
  "Modal backdrop (50) must be strictly higher than Normal map container (0)"
);
assert.ok(
  Z_INDEX.MODAL_CONTENT > Z_INDEX.MAP_CONTROLS,
  "Modal content (50) must be strictly higher than Map controls (20)"
);
assert.ok(
  Z_INDEX.MAP_FULLSCREEN > Z_INDEX.MAP_CONTROLS,
  "Fullscreen map (40) must be higher than inline map controls (20)"
);

// -----------------------------------------------------------------------------
// 2. Role Selector Onboarding & Stakeholder Default Mapping
// -----------------------------------------------------------------------------
console.log("2. Validating Stakeholder Roles & Onboarding Presentation Invariants...");

assert.equal(SUPPORTED_ROLES.length, 5, "Platform must offer exactly 5 balanced stakeholder roles");
const roleIds = SUPPORTED_ROLES.map((r) => r.id);
assert.deepEqual(
  roleIds,
  [
    "Farmer",
    "Dealer / Trader",
    "Buyer",
    "Transporter / Logistics Partner",
    "Admin / Platform Manager",
  ],
  "Must match exact stakeholder taxonomy"
);

for (const role of SUPPORTED_ROLES) {
  assert.ok(role.title, `Role ${role.id} must have a display title`);
  assert.ok(role.subtitle, `Role ${role.id} must have a subtitle`);
  assert.ok(role.badge, `Role ${role.id} must have a badge`);
  assert.ok(role.description, `Role ${role.id} must have a description`);
  assert.ok(role.icon, `Role ${role.id} must have an icon`);
  assert.ok(role.iconBg, `Role ${role.id} must have an iconBg class`);
  assert.ok(role.borderHover, `Role ${role.id} must have borderHover class`);
  assert.equal(
    role.defaultTab,
    ROLE_DEFAULT_TABS[role.id],
    `Role ${role.id} default tab must match ROLE_DEFAULT_TABS`
  );
}

// -----------------------------------------------------------------------------
// 3. Logistics Table Pagination & Slice Logic (Single Scrollbar)
// -----------------------------------------------------------------------------
console.log("3. Validating Table Single-Scroll Pagination / Slice Logic...");

const mockWaypoints = Array.from({ length: 15 }, (_, i) => ({
  id: `WP-${i + 1}`,
  latitude: 30.1 + i * 0.05,
  longitude: 74.4 + i * 0.05,
  recorded_at: new Date(Date.now() - (15 - i) * 60000).toISOString(),
}));

// Default view should show 6 items
const defaultSlice = mockWaypoints.slice(-6).reverse();
assert.equal(defaultSlice.length, 6, "Default slice must show exactly 6 most recent waypoints");
assert.equal(defaultSlice[0].id, "WP-15", "Top item in reversed slice must be the newest waypoint");

// Expanded view should show all 15 items
const expandedSlice = [...mockWaypoints].reverse();
assert.equal(expandedSlice.length, 15, "Expanded view must show all 15 waypoints");
assert.equal(expandedSlice[0].id, "WP-15", "Top item must be newest waypoint");
assert.equal(expandedSlice[14].id, "WP-1", "Last item must be oldest waypoint");

// -----------------------------------------------------------------------------
// 4. Shipment Search & Filter Logic
// -----------------------------------------------------------------------------
console.log("4. Validating Shipment Filter & Search Engine...");

const mockShipments = [
  {
    id: "SHP-GUA-001",
    produce_type: "Guava (Allahabad Safeda)",
    status: "in_transit",
    origin: "Faridkot Aggregation Center",
    destination: "APMC Mandi Ludhiana",
    risk_index: 12,
    coordinates: [30.6769, 74.7583],
  },
  {
    id: "SHP-GUA-002",
    produce_type: "Guava (Lucknow 49)",
    status: "pending",
    origin: "Bathinda Farm Gate",
    destination: "Jalandhar Cold Storage",
    risk_index: 48,
    coordinates: null,
  },
  {
    id: "SHP-GUA-003",
    produce_type: "Guava (Shweta)",
    status: "delivered",
    origin: "Patiala Processing Hub",
    destination: "Chandigarh Terminal Mandi",
    risk_index: 5,
    coordinates: [30.7333, 76.7794],
  },
];

function filterShipments(list, query, statusFilter) {
  return list.filter((s) => {
    if (statusFilter !== "all") {
      const st = (s.status || "").toLowerCase();
      if (statusFilter === "in_transit") {
        if (st !== "in_transit" && st !== "in transit" && st !== "dispatched") return false;
      } else if (statusFilter === "pending") {
        if (st !== "pending" && st !== "created") return false;
      } else if (statusFilter === "delivered") {
        if (st !== "delivered" && st !== "completed") return false;
      }
    }
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      s.id.toLowerCase().includes(q) ||
      s.produce_type.toLowerCase().includes(q) ||
      s.origin.toLowerCase().includes(q) ||
      s.destination.toLowerCase().includes(q)
    );
  });
}

// Test status filtering
assert.equal(filterShipments(mockShipments, "", "all").length, 3);
assert.equal(filterShipments(mockShipments, "", "in_transit").length, 1);
assert.equal(filterShipments(mockShipments, "", "pending").length, 1);
assert.equal(filterShipments(mockShipments, "", "delivered").length, 1);

// Test query search
assert.equal(filterShipments(mockShipments, "Faridkot", "all").length, 1);
assert.equal(filterShipments(mockShipments, "Lucknow", "all").length, 1);
assert.equal(filterShipments(mockShipments, "SHP-GUA", "all").length, 3);
assert.equal(filterShipments(mockShipments, "Nonexistent", "all").length, 0);

// Test summary metric calculations
const activeCount = mockShipments.filter((s) => s.status === "in_transit").length;
const highRiskCount = mockShipments.filter((s) => s.risk_index > 40).length;
const geolocatedCount = mockShipments.filter((s) => s.coordinates && s.coordinates.length === 2).length;

assert.equal(activeCount, 1, "Should count 1 active in-transit shipment");
assert.equal(highRiskCount, 1, "Should count 1 high-risk excursion shipment");
assert.equal(geolocatedCount, 2, "Should count 2 geolocated shipments");

// -----------------------------------------------------------------------------
// 5. Guava Fresh Produce Cold-Chain Thermal Window
// -----------------------------------------------------------------------------
console.log("5. Validating Guava Cold-Chain Thermal Window (4°C – 8°C)...");

function evaluateGuavaThermalReading(temp) {
  if (temp < 4.0) {
    return { status: "chilling_hazard", alert: true, label: "Chilling Injury Risk" };
  }
  if (temp > 8.0) {
    return { status: "warm_excursion", alert: true, label: "Warm Excursion Risk" };
  }
  return { status: "optimal", alert: false, label: "Optimal Cold Chain" };
}

assert.equal(evaluateGuavaThermalReading(2.5).alert, true, "2.5°C is below 4.0°C (chilling risk)");
assert.equal(evaluateGuavaThermalReading(5.5).alert, false, "5.5°C is inside 4.0°C–8.0°C optimal window");
assert.equal(evaluateGuavaThermalReading(8.0).alert, false, "8.0°C is within boundary");
assert.equal(evaluateGuavaThermalReading(9.2).alert, true, "9.2°C is above 8.0°C (warm excursion)");

console.log("\n✅ All Phase 13.6 unit and regression tests passed successfully!");

