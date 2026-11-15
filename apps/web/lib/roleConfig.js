/**
 * AgriChain AI — Centralized Role-Based Access & Workspace Configuration
 * ======================================================================
 * Single source of truth for:
 * 1. Role identification and alias normalization (Farmer, Logistics, Dealer, Buyer, Admin).
 * 2. Role-specific navigation items and permitted dashboard tabs.
 * 3. Strict access boundaries: users only see and navigate to features permitted for their role.
 * 4. Role-specific header titles, descriptions, and quick metric overviews.
 */

export const ROLE_KEYS = {
  FARMER: "Farmer",
  LOGISTICS: "Logistics",
  DEALER: "Dealer",
  BUYER: "Buyer",
  ADMIN: "Admin",
};

export const ROLES_CONFIG = {
  [ROLE_KEYS.FARMER]: {
    id: "Farmer",
    legacyId: "Farmer",
    title: "Farmer",
    displayTitle: "Farmer (Grower & Harvester)",
    subtitle: "Orchard Management & Quality Intake",
    badge: "Field & Harvest",
    icon: "agriculture",
    iconBg: "bg-emerald-100 text-emerald-800",
    borderHover: "hover:border-emerald-500",
    borderActive: "border-emerald-500 bg-emerald-50/50",
    description: "Inspect produce harvest ripeness, manage crop yields, and track packhouse dispatches.",
    defaultTab: "analyze",
    allowedTabs: ["analyze", "farmer", "tracking"],
    headerTitle: "Farmer Workspace",
    headerSubtitle: "Multi-fruit harvest maturity inspection, crop yield planner & packhouse intake",
    quickStats: [
      { label: "AI Produce Inspection", value: "Dual-Mode Active", icon: "biotech", subtext: "Guava, Banana, Apple, Mango" },
      { label: "Active Harvest Lots", value: "3 Clustered Blocks", icon: "potted_plant", subtext: "Allahabad Safeda & Sindhi" },
      { label: "Regional Packhouse", value: "FAC-PB-ABO-01", icon: "warehouse", subtext: "PAGREXCO Alamgarh Packhouse" },
    ],
    navItems: [
      {
        id: "analyze",
        label: "Produce Inspection",
        icon: "biotech",
        badge: "Dual-Mode AI",
        description: "Manual selection & automatic fruit identification",
      },
      {
        id: "farmer",
        label: "Farmer Overview & Harvest",
        icon: "agriculture",
        badge: "Harvests",
        description: "Farm yields, soil sensors & packhouse intake",
      },
      {
        id: "tracking",
        label: "My Shipments",
        icon: "local_shipping",
        description: "Track harvest dispatches & PostGIS routes",
      },
    ],
  },

  [ROLE_KEYS.LOGISTICS]: {
    id: "Logistics",
    legacyId: "Transporter / Logistics Partner",
    title: "Logistics",
    displayTitle: "Logistics (Cold-Chain Fleet)",
    subtitle: "PostGIS Fleet Tracking & Corridor Telemetry",
    badge: "Cold-Chain Fleet",
    icon: "local_shipping",
    iconBg: "bg-amber-100 text-amber-800",
    borderHover: "hover:border-amber-500",
    borderActive: "border-amber-500 bg-amber-50/50",
    description: "Monitor PostGIS route corridors, vehicle coordinates, and cold-chain telemetry.",
    defaultTab: "tracking",
    allowedTabs: ["tracking", "warehouse"],
    headerTitle: "Logistics & Fleet Workspace",
    headerSubtitle: "PostGIS GPS corridor tracking, cold-chain thermal telemetry & transit simulation",
    quickStats: [
      { label: "Active Corridor", value: "NH-7 / NH-9 Fleet", icon: "route", subtext: "Abohar to Azadpur Mega Mandi" },
      { label: "Thermal Envelope", value: "4°C – 8°C (Optimal)", icon: "thermostat", subtext: "Cold-chain spoilage risk < 15%" },
      { label: "Telemetry Stream", value: "PostGIS SRID 4326", icon: "satellite_alt", subtext: "Live GPS & simulated waypoints" },
    ],
    navItems: [
      {
        id: "tracking",
        label: "Shipment Tracking & Map",
        icon: "local_shipping",
        badge: "PostGIS",
        description: "Corridor routes, telemetry stream & checkpoints",
      },
      {
        id: "warehouse",
        label: "Storage Facility Directory",
        icon: "warehouse",
        description: "APMC mandis, cold stores & transit hubs",
      },
    ],
  },

  [ROLE_KEYS.DEALER]: {
    id: "Dealer",
    legacyId: "Dealer / Trader",
    title: "Dealer",
    displayTitle: "Dealer (Mandi Aggregator)",
    subtitle: "Wholesale Auctions & Mandi Intake",
    badge: "Mandi Aggregator",
    icon: "storefront",
    iconBg: "bg-teal-100 text-teal-800",
    borderHover: "hover:border-teal-500",
    borderActive: "border-teal-500 bg-teal-50/50",
    description: "Manage wholesale lot auctions, mandi intake verification, and warehouse receipts.",
    defaultTab: "dealer",
    allowedTabs: ["dealer", "marketplace", "tracking"],
    headerTitle: "Dealer & Mandi Workspace",
    headerSubtitle: "Mandi arrival intake, wholesale lot auctions & cold-chain warehouse receipts",
    quickStats: [
      { label: "APMC Trading Mandi", value: "Azadpur APMC", icon: "domain", subtext: "FAC-DL-AZD-01 (MNI Hub)" },
      { label: "Verified Produce Lots", value: "Active Auction Pool", icon: "verified", subtext: "ResNet18 Audited Harvest Batches" },
      { label: "Mandi Intake Capacity", value: "8,500 MT / Day", icon: "inventory", subtext: "Cold storage & auction chambers" },
    ],
    navItems: [
      {
        id: "dealer",
        label: "Dealer Overview & Intake",
        icon: "storefront",
        badge: "Mandi",
        description: "Auction lots, intake verification & receipts",
      },
      {
        id: "marketplace",
        label: "Available Produce Lots",
        icon: "inventory_2",
        description: "Browse verified harvest lots across packhouses",
      },
      {
        id: "tracking",
        label: "Inbound Consignments",
        icon: "local_shipping",
        description: "Cold-chain shipments arriving at mandi",
      },
    ],
  },

  [ROLE_KEYS.BUYER]: {
    id: "Buyer",
    legacyId: "Buyer",
    title: "Buyer",
    displayTitle: "Buyer (B2B Retailer & Exporter)",
    subtitle: "Verified B2B Produce Sourcing",
    badge: "Verified Marketplace",
    icon: "shopping_cart",
    iconBg: "bg-blue-100 text-blue-800",
    borderHover: "hover:border-blue-500",
    borderActive: "border-blue-500 bg-blue-50/50",
    description: "Browse AI-audited produce batches, review ripeness grades, and place purchase orders.",
    defaultTab: "marketplace",
    allowedTabs: ["marketplace", "tracking"],
    headerTitle: "B2B Buyer Workspace",
    headerSubtitle: "Verified produce lot catalog, AI ripeness audit & purchase order ledger",
    quickStats: [
      { label: "B2B Marketplace", value: "Verified Lots Open", icon: "shopping_bag", subtext: "Audited Guava & Produce" },
      { label: "AI Quality Standard", value: "ResNet18 Verified", icon: "verified_user", subtext: "Certified Harvest Ripeness" },
      { label: "Purchase Protection", value: "Cold-Chain Monitored", icon: "shield", subtext: "Temperature-guaranteed transit" },
    ],
    navItems: [
      {
        id: "marketplace",
        label: "B2B Marketplace & Catalog",
        icon: "shopping_cart",
        badge: "Live Catalog",
        description: "Browse verified lots & place purchase orders",
      },
      {
        id: "tracking",
        label: "Track Inbound Orders",
        icon: "local_shipping",
        description: "Monitor cold-chain transit of purchased lots",
      },
    ],
  },

  [ROLE_KEYS.ADMIN]: {
    id: "Admin",
    legacyId: "Admin / Platform Manager",
    title: "Admin",
    displayTitle: "Admin (Platform Governance)",
    subtitle: "AI Model Diagnostics & Platform Infrastructure",
    badge: "Platform Governance",
    icon: "admin_panel_settings",
    iconBg: "bg-slate-100 text-slate-800",
    borderHover: "hover:border-slate-500",
    borderActive: "border-slate-500 bg-slate-50/50",
    description: "Inspect PyTorch CUDA GPU health, REST API latency, and model registry.",
    defaultTab: "status",
    allowedTabs: ["status", "analytics", "warehouse"],
    headerTitle: "System Administration Workspace",
    headerSubtitle: "PyTorch CUDA RTX 4050 diagnostics, FastAPI health & model registry",
    quickStats: [
      { label: "Inference Engine", value: "CUDA 12.8 Active", icon: "memory", subtext: "NVIDIA RTX 4050 (6GB VRAM)" },
      { label: "Model Registry", value: "5 Models Loaded", icon: "psychology", subtext: "Guava, Banana, Apple, Stage 1 ID" },
      { label: "API Health", value: "FastAPI Online", icon: "check_circle", subtext: "Uvicorn Port 8000 | Latency < 10ms" },
    ],
    navItems: [
      {
        id: "status",
        label: "System Status & Hardware",
        icon: "dns",
        badge: "CUDA Active",
        description: "PyTorch GPU diagnostics, API health & latency",
      },
      {
        id: "analytics",
        label: "Model Registry & Benchmarks",
        icon: "monitoring",
        description: "Evaluation curves, F1 scores & model matrices",
      },
      {
        id: "warehouse",
        label: "Infrastructure Directory",
        icon: "warehouse",
        description: "PostGIS facility management & geocoding audit",
      },
    ],
  },
};

/**
 * Normalizes any input role string (canonical ID, legacy ID, or lowercase alias)
 * into a canonical ROLE_KEYS string.
 */
export function normalizeRoleId(roleInput) {
  if (!roleInput || typeof roleInput !== "string") {
    return ROLE_KEYS.FARMER;
  }
  const clean = roleInput.trim().toLowerCase();

  if (clean.includes("farmer")) {
    return ROLE_KEYS.FARMER;
  }
  if (clean.includes("logistics") || clean.includes("transport")) {
    return ROLE_KEYS.LOGISTICS;
  }
  if (clean.includes("dealer") || clean.includes("trader")) {
    return ROLE_KEYS.DEALER;
  }
  if (clean.includes("buyer")) {
    return ROLE_KEYS.BUYER;
  }
  if (clean.includes("admin")) {
    return ROLE_KEYS.ADMIN;
  }

  return ROLE_KEYS.FARMER;
}

/**
 * Retrieves the full configuration for a given role identifier.
 */
export function getRoleConfig(roleInput) {
  const canonical = normalizeRoleId(roleInput);
  return ROLES_CONFIG[canonical] || ROLES_CONFIG[ROLE_KEYS.FARMER];
}

/**
 * Checks whether a tab ID is permitted for the active role.
 */
export function isTabAllowedForRole(roleInput, tabId) {
  const config = getRoleConfig(roleInput);
  return config.allowedTabs.includes(tabId);
}

