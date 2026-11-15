/**
 * AgriChain AI - Centralized Kinnow Mandarin CNN Ripeness & Quality Taxonomy
 *
 * Target Crop: Kinnow Mandarin (Citrus reticulata)
 * Production Architecture: 3-class CNN / ResNet18
 * Source of truth: Numeric class index:
 *   0 -> Underripe (Immature green / breaker stage)
 *   1 -> Partially Ripe (Transitional yellow-orange)
 *   2 -> Fully Ripe (Full golden-orange rind)
 */

/**
 * Verification state: Numeric mapping [0, 1, 2] is UNCONFIRMED against actual Kinnow
 * dataset metadata. It must not be assumed certified or used for training without
 * validated ground-truth annotations.
 */
export const CLASS_MAPPING_VERIFIED = false;
export const CLASS_MAPPING_STATUS = "UNCONFIRMED_PENDING_GROUND_TRUTH_VALIDATION";

/**
 * Single centralized class-label mapping for Kinnow ripeness classification.
 * Numeric index is preserved exactly for full backwards compatibility.
 *
 * @type {Record<number, string>}
 */
export const CLASS_LABELS = {
  0: "Underripe",
  1: "Partially Ripe",
  2: "Fully Ripe",
};

/**
 * Array of all supported numeric class indices for validation and iteration.
 */
export const RIPENESS_CLASSES = [0, 1, 2];

/**
 * Styling tokens for each ripeness class (badges, highlights, progress bars).
 */
export const CLASS_STYLES = {
  0: {
    name: "Underripe",
    badge: "bg-blue-500/15 text-blue-700",
    barColor: "bg-blue-500",
    text: "text-blue-600",
  },
  1: {
    name: "Partially Ripe",
    badge: "bg-amber-500/15 text-amber-800",
    barColor: "bg-amber-500",
    text: "text-amber-600",
  },
  2: {
    name: "Fully Ripe",
    badge: "bg-digital-mint/15 text-emerald-forest",
    barColor: "bg-digital-mint",
    text: "text-digital-mint",
  },
};

export const GUAVA_CLASS_LABELS = {
  0: "Green",
  1: "Mature Green",
  2: "Ripe",
};

export const BANANA_CLASS_LABELS = {
  0: "Unripe",
  1: "Half_Ripe",
  2: "Ripe",
  3: "Overripe",
};

export const SUPPORTED_FRUITS = [
  {
    id: "guava",
    name: "Guava",
    scientificName: "Psidium guajava L.",
    taskType: "classification",
    modelName: "ResNet18",
    version: "v2.0.0",
    status: "ready",
    statusLabel: "Certified Active",
    badgeClass: "bg-emerald-500/15 text-emerald-800 border-emerald-500/30",
    icon: "spa",
    description: "3-stage harvest intake maturity taxonomy (Green, Mature Green, Ripe).",
  },
  {
    id: "banana",
    name: "Banana",
    scientificName: "Musa acuminata",
    taskType: "classification",
    modelName: "ResNet18",
    version: "v1.0.0",
    status: "ready",
    statusLabel: "Baseline Verified",
    badgeClass: "bg-amber-500/15 text-amber-800 border-amber-500/30",
    icon: "eco",
    description: "4-stage peel degreening and senescence (Unripe, Half_Ripe, Ripe, Overripe).",
  },
  {
    id: "apple",
    name: "Apple",
    scientificName: "Malus domestica Borkh.",
    taskType: "object_detection",
    modelName: "YOLOv8n",
    version: "v1.0.0-exp",
    status: "ready",
    statusLabel: "Object Detection",
    badgeClass: "bg-purple-500/15 text-purple-800 border-purple-500/30",
    icon: "crop_free",
    description: "In-orchard apple detection and instance counting (Research CC BY-NC 4.0).",
  },
  {
    id: "mango",
    name: "Mango",
    scientificName: "Mangifera indica L.",
    taskType: "unavailable",
    modelName: "Awaiting Dataset",
    version: "N/A",
    status: "unavailable",
    statusLabel: "Gated Deficit",
    badgeClass: "bg-rose-500/15 text-rose-800 border-rose-500/30",
    icon: "block",
    description: "Harvest maturity model unavailable due to multi-stage training data deficit.",
  },
];

/**
 * Resolves the numeric class index (0 | 1 | 2) from an API response, string, or number.
 *
 * @param {any} input
 * @returns {0 | 1 | 2 | null}
 */
export function getClassIndex(input) {
  if (input == null) return null;

  // Direct number check
  if (typeof input === "number") {
    if (input in CLASS_LABELS || input in GUAVA_CLASS_LABELS) return /** @type {0 | 1 | 2} */ (input);
    return null;
  }

  // Object checks (e.g. API response)
  if (typeof input === "object") {
    if (typeof input.class_index === "number" && (input.class_index in CLASS_LABELS || input.class_index in GUAVA_CLASS_LABELS)) {
      return /** @type {0 | 1 | 2} */ (input.class_index);
    }
    if (typeof input.class === "number" && (input.class in CLASS_LABELS || input.class in GUAVA_CLASS_LABELS)) {
      return /** @type {0 | 1 | 2} */ (input.class);
    }
    if (typeof input.predicted_class === "string") {
      return getClassIndex(input.predicted_class);
    }
  }

  // String check ("0", "1", "2" or "class0", "class1", "class2")
  if (typeof input === "string") {
    const trimmed = input.trim();
    const match = trimmed.match(/^class\s*([0-2])$/i);
    if (match) {
      return /** @type {0 | 1 | 2} */ (parseInt(match[1], 10));
    }
    const parsed = parseInt(trimmed, 10);
    if (!isNaN(parsed) && String(parsed) === trimmed && (parsed in CLASS_LABELS || parsed in GUAVA_CLASS_LABELS)) {
      return /** @type {0 | 1 | 2} */ (parsed);
    }
    // Reverse lookup from Kinnow or Guava labels
    for (const [idxStr, label] of Object.entries(CLASS_LABELS)) {
      if (label.toLowerCase() === trimmed.toLowerCase()) {
        return /** @type {0 | 1 | 2} */ (parseInt(idxStr, 10));
      }
    }
    for (const [idxStr, label] of Object.entries(GUAVA_CLASS_LABELS)) {
      if (label.toLowerCase() === trimmed.toLowerCase()) {
        return /** @type {0 | 1 | 2} */ (parseInt(idxStr, 10));
      }
    }
  }

  return null;
}

/**
 * Resolves the human-readable condition label for a given class index, key, or prediction result.
 * If backend already provides a valid human label, preserves it (Instruction 10).
 * Otherwise maps the numeric index to the standardized human-readable label (Instruction 6).
 *
 * @param {any} input
 * @param {string} [fallback]
 * @returns {string}
 */
export function getRipenessLabel(input, fallback = "Unknown") {
  // If input is an object with an explicit human-readable label
  if (typeof input === "object" && input !== null) {
    if (typeof input.label === "string" && input.label.trim()) {
      return input.label.trim();
    }
    const targetCrop = (input.target_crop || "").toLowerCase();
    const idx = getClassIndex(input);
    if (idx !== null) {
      if (targetCrop === "guava" && idx in GUAVA_CLASS_LABELS) {
        return GUAVA_CLASS_LABELS[idx];
      }
      if (idx in CLASS_LABELS) {
        return CLASS_LABELS[idx];
      }
    }
  }

  // If input is a string matching a known Guava label, preserve it directly
  if (typeof input === "string") {
    const trimmed = input.trim();
    for (const label of Object.values(GUAVA_CLASS_LABELS)) {
      if (label.toLowerCase() === trimmed.toLowerCase()) {
        return label;
      }
    }
  }

  const idx = getClassIndex(input);
  if (idx !== null && idx in CLASS_LABELS) {
    return CLASS_LABELS[idx];
  }

  return fallback;
}

/**
 * Formats a decimal confidence (e.g. 0.9718) into a percentage string (e.g. "97.18%").
 *
 * @param {number} confidence
 * @param {number} [decimals=2]
 * @returns {string}
 */
export function formatConfidence(confidence, decimals = 2) {
  if (typeof confidence !== "number" || isNaN(confidence)) {
    return "N/A";
  }
  return `${(confidence * 100).toFixed(decimals)}%`;
}

/**
 * Configurable UI Uncertainty Heuristic Thresholds (Phase 7)
 *
 * Operational UI heuristics to prompt manual review when class activation margin
 * or highest softmax score is low.
 *
 * IMPORTANT SCIENTIFIC DISCLAIMER:
 * These thresholds are heuristic presentation rules implemented in the frontend UI.
 * They are NOT calibrated Bayesian probabilities, statistical confidence intervals,
 * or clinical/agricultural certifications. They do NOT guarantee that the
 * model knows when it is wrong or right.
 */
export const UNCERTAINTY_THRESHOLDS = {
  // Flag as uncertain if top softmax score is below 60% (0.60)
  MIN_TOP_SCORE: 0.60,
  // Flag as uncertain if margin between top 2 class scores is below 15% (0.15)
  MIN_SCORE_MARGIN: 0.15,
};

/**
 * Checks whether a prediction result should be presented with a neutral uncertainty notice.
 *
 * Evaluates whether:
 * 1. Top softmax score < MIN_TOP_SCORE (e.g. < 0.60)
 * 2. Difference between 1st and 2nd highest class scores < MIN_SCORE_MARGIN (e.g. < 0.15)
 *
 * @param {any} result API response or object containing confidence and/or probabilities
 * @param {Partial<typeof UNCERTAINTY_THRESHOLDS>} [customThresholds] Optional override thresholds
 * @returns {{
 *   isUncertain: boolean,
 *   reason: "none" | "low_top_score" | "close_scores" | "both",
 *   topScore: number,
 *   secondScore: number,
 *   margin: number,
 *   message: string
 * }}
 */
export function checkPredictionUncertainty(result, customThresholds) {
  const thresholds = {
    ...UNCERTAINTY_THRESHOLDS,
    ...(customThresholds || {}),
  };

  if (!result || typeof result !== "object") {
    return {
      isUncertain: false,
      reason: "none",
      topScore: 0,
      secondScore: 0,
      margin: 0,
      message: "",
    };
  }

  // Extract sorted numeric probability values
  let values = [];
  if (result.probabilities && typeof result.probabilities === "object") {
    values = Object.values(result.probabilities)
      .filter((v) => typeof v === "number" && !isNaN(v))
      .sort((a, b) => b - a);
  }

  // If no scores or probabilities are provided, there is no prediction to evaluate
  if (values.length === 0 && typeof result.confidence !== "number") {
    return {
      isUncertain: false,
      reason: "none",
      topScore: 0,
      secondScore: 0,
      margin: 0,
      message: "",
    };
  }

  const topScore =
    values.length > 0
      ? values[0]
      : typeof result.confidence === "number"
      ? result.confidence
      : 0;
  const secondScore = values.length > 1 ? values[1] : 0;
  const margin = Number((topScore - secondScore).toFixed(4));

  const isLowScore = topScore < thresholds.MIN_TOP_SCORE;
  const isCloseScores = values.length > 1 && margin < thresholds.MIN_SCORE_MARGIN;

  let reason = "none";
  if (isLowScore && isCloseScores) {
    reason = "both";
  } else if (isLowScore) {
    reason = "low_top_score";
  } else if (isCloseScores) {
    reason = "close_scores";
  }

  const isUncertain = isLowScore || isCloseScores;

  return {
    isUncertain,
    reason,
    topScore,
    secondScore,
    margin,
    message: isUncertain ? "Prediction uncertain — inspect the fruit manually." : "",
  };
}

/**
 * Supported Stakeholder Roles for Role-Based Experience & Routing.
 */
export const SUPPORTED_ROLES = [
  {
    id: "Farmer",
    title: "Farmer",
    subtitle: "Grower & Harvester",
    badge: "Field & Quality Intake",
    description: "Inspect guava harvest ripeness with ResNet18 AI, record harvested crates, and view post-harvest godown suitability.",
    icon: "agriculture",
    iconBg: "bg-emerald-100 text-emerald-800",
    borderHover: "hover:border-emerald-500",
    defaultTab: "analyze",
  },
  {
    id: "Dealer / Trader",
    title: "Dealer & Trader",
    subtitle: "Mandi Aggregator",
    badge: "Wholesale & Godowns",
    description: "Manage wholesale trading inventory, verify storage godown capacity, and coordinate transit batches across APMC mandis.",
    icon: "storefront",
    iconBg: "bg-teal-100 text-teal-800",
    borderHover: "hover:border-teal-500",
    defaultTab: "dealer",
  },
  {
    id: "Buyer",
    title: "Buyer (B2B)",
    badge: "Verified Marketplace",
    subtitle: "Retailer & Exporter",
    description: "Browse AI-audited guava batches, review ripeness confidence scores, calculate totals, and place demo purchase orders.",
    icon: "shopping_cart",
    iconBg: "bg-blue-100 text-blue-800",
    borderHover: "hover:border-blue-500",
    defaultTab: "marketplace",
  },
  {
    id: "Transporter / Logistics Partner",
    title: "Logistics Operator",
    subtitle: "Cold-Chain Fleet",
    badge: "Geospatial Tracking",
    description: "Monitor real-time PostGIS vehicle coordinates, thermal sensor telemetry, and transit checkpoint handover events.",
    icon: "local_shipping",
    iconBg: "bg-amber-100 text-amber-800",
    borderHover: "hover:border-amber-500",
    defaultTab: "tracking",
  },
  {
    id: "Admin / Platform Manager",
    title: "System Administrator",
    subtitle: "Platform Governance",
    badge: "System Diagnostics",
    description: "Inspect CNN PyTorch model health, REST API latency, audit logs, and cold-chain integrity controls.",
    icon: "admin_panel_settings",
    iconBg: "bg-slate-100 text-slate-800",
    borderHover: "hover:border-slate-500",
    defaultTab: "status",
  },
];

export const ROLE_DEFAULT_TABS = {
  "Farmer": "analyze",
  "Dealer / Trader": "dealer",
  "Buyer": "marketplace",
  "Transporter / Logistics Partner": "tracking",
  "Admin / Platform Manager": "status",
};

/**
 * Standardized Stacking Order & Z-Index Constants.
 * Ensures map panes, overlays, controls, and dialogs never conflict or obscure one another.
 */
export const Z_INDEX = {
  BASE: 0,
  MAP_CONTAINER: 0, // Stacking context isolated with CSS `isolation: isolate`
  MAP_CONTROLS: 20, // Internal controls inside map's local stacking context
  HEADER: 20,
  STICKY_NAV: 30,
  DROPDOWN: 40,
  DRAWER_BACKDROP: 40,
  DRAWER: 45,
  MAP_FULLSCREEN: 40, // Fullscreen map sits at 40, strictly below modals
  MODAL_BACKDROP: 50, // All modal overlays (role selector, orders, shipments) sit at 50
  MODAL_CONTENT: 50,
  TOAST_NOTIFICATIONS: 60,
};
