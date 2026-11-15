import assert from "node:assert/strict";
import { SUPPORTED_ROLES, ROLE_DEFAULT_TABS, GUAVA_CLASS_LABELS, getClassIndex, getRipenessLabel } from "./constants.js";

console.log("Running Phase 13.5 Frontend Unit & Regression Tests...\n");

// -----------------------------------------------------------------------------
// 1. Role-Based Stakeholder Mapping & Defaults
// -----------------------------------------------------------------------------
console.log("1. Validating Supported Roles & Routing Mapping...");

const expectedRoleIds = [
  "Farmer",
  "Dealer / Trader",
  "Buyer",
  "Transporter / Logistics Partner",
  "Admin / Platform Manager",
];

const actualRoleIds = SUPPORTED_ROLES.map((r) => r.id);
assert.deepEqual(actualRoleIds, expectedRoleIds, "Must support all 5 stakeholder roles");

// Check default tab mappings
assert.equal(ROLE_DEFAULT_TABS["Farmer"], "analyze", "Farmer maps to produce analysis");
assert.equal(ROLE_DEFAULT_TABS["Dealer / Trader"], "dealer", "Dealer maps to dealer & trader dashboard");
assert.equal(ROLE_DEFAULT_TABS["Buyer"], "marketplace", "Buyer maps to B2B marketplace");
assert.equal(ROLE_DEFAULT_TABS["Transporter / Logistics Partner"], "tracking", "Logistics maps to tracking");
assert.equal(ROLE_DEFAULT_TABS["Admin / Platform Manager"], "status", "Admin maps to status diagnostics");

for (const role of SUPPORTED_ROLES) {
  assert.ok(role.title, `Role ${role.id} must have title`);
  assert.ok(role.description, `Role ${role.id} must have description`);
  assert.ok(role.icon, `Role ${role.id} must have Material Symbol icon`);
  assert.equal(role.defaultTab, ROLE_DEFAULT_TABS[role.id], `Role defaultTab must match mapping`);
}

// -----------------------------------------------------------------------------
// 2. Guava Produce Ripeness Taxonomy
// -----------------------------------------------------------------------------
console.log("2. Validating Guava ResNet18 Harvest Ripeness Taxonomy...");

assert.equal(GUAVA_CLASS_LABELS[0], "Green");
assert.equal(GUAVA_CLASS_LABELS[1], "Mature Green");
assert.equal(GUAVA_CLASS_LABELS[2], "Ripe");

assert.equal(getClassIndex({ predicted_class: "Green", target_crop: "guava" }), 0);
assert.equal(getClassIndex({ predicted_class: "Mature Green", target_crop: "guava" }), 1);
assert.equal(getClassIndex({ predicted_class: "Ripe", target_crop: "guava" }), 2);

// Check that no fake or unverified categories exist
const validLabels = Object.values(GUAVA_CLASS_LABELS);
assert.ok(!validLabels.includes("Spoiled"));
assert.ok(!validLabels.includes("Grade A"));
assert.ok(!validLabels.includes("Pesticide Free"));

// -----------------------------------------------------------------------------
// 3. Buyer Marketplace Order Calculation & Validation Rules
// -----------------------------------------------------------------------------
console.log("3. Validating Buyer Marketplace Pricing & Validation Rules...");

function validateAndCalculateOrder({ listing, quantity, buyerName, buyerOrg, deliveryAddress }) {
  const errors = [];
  if (!listing) {
    errors.push("No listing selected.");
    return { valid: false, errors };
  }
  const qty = parseInt(quantity, 10);
  if (isNaN(qty) || qty <= 0) {
    errors.push("Order quantity must be at least 1 crate.");
  } else if (qty > listing.available_crates) {
    errors.push(`Order quantity (${qty}) exceeds available stock (${listing.available_crates}).`);
  }
  if (!buyerName || !buyerName.trim()) {
    errors.push("Buyer contact name is required.");
  }
  if (!buyerOrg || !buyerOrg.trim()) {
    errors.push("Buyer business / organization is required.");
  }
  if (!deliveryAddress || !deliveryAddress.trim()) {
    errors.push("Delivery address is required.");
  }

  const unitPrice = Number(listing.price_per_crate_inr) || 0;
  const totalPrice = qty > 0 ? qty * unitPrice : 0;
  const totalWeightKg = qty > 0 ? qty * (listing.crate_weight_kg || 20) : 0;

  return {
    valid: errors.length === 0,
    errors,
    qty,
    unitPrice,
    totalPrice,
    totalWeightKg,
  };
}

const mockListing = {
  id: "LST-GUA-001",
  title: "Guava Premium Crate (Ripe)",
  variety: "Allahabad Safeda",
  available_crates: 50,
  crate_weight_kg: 20,
  price_per_crate_inr: 1200,
};

// Valid calculation
const validCalc = validateAndCalculateOrder({
  listing: mockListing,
  quantity: 5,
  buyerName: "Rajesh Kumar",
  buyerOrg: "Punjab Retail Mart",
  deliveryAddress: "Mandi Road, Ludhiana",
});
assert.equal(validCalc.valid, true);
assert.equal(validCalc.totalPrice, 6000);
assert.equal(validCalc.totalWeightKg, 100);

// Quantity exceeding stock
const overStockCalc = validateAndCalculateOrder({
  listing: mockListing,
  quantity: 51,
  buyerName: "Rajesh Kumar",
  buyerOrg: "Punjab Retail Mart",
  deliveryAddress: "Mandi Road, Ludhiana",
});
assert.equal(overStockCalc.valid, false);
assert.ok(overStockCalc.errors[0].includes("exceeds available stock"));

// Zero or negative quantity
const zeroQtyCalc = validateAndCalculateOrder({
  listing: mockListing,
  quantity: 0,
  buyerName: "Rajesh Kumar",
  buyerOrg: "Punjab Retail Mart",
  deliveryAddress: "Mandi Road, Ludhiana",
});
assert.equal(zeroQtyCalc.valid, false);
assert.ok(zeroQtyCalc.errors[0].includes("at least 1 crate"));

// Missing buyer name
const missingNameCalc = validateAndCalculateOrder({
  listing: mockListing,
  quantity: 2,
  buyerName: "   ",
  buyerOrg: "Punjab Retail Mart",
  deliveryAddress: "Mandi Road, Ludhiana",
});
assert.equal(missingNameCalc.valid, false);
assert.ok(missingNameCalc.errors[0].includes("Buyer contact name is required"));

// -----------------------------------------------------------------------------
// 4. Role Navigation and Access Consistency
// -----------------------------------------------------------------------------
console.log("4. Validating Role Navigation Invariants...");

// Ensure each supported role has a matching dashboard tab
const ALLOWED_DASHBOARD_TABS = ["overview", "analyze", "tracking", "status", "facilities", "settings", "dealer", "marketplace"];

for (const [role, defaultTab] of Object.entries(ROLE_DEFAULT_TABS)) {
  assert.ok(
    ALLOWED_DASHBOARD_TABS.includes(defaultTab),
    `Default tab '${defaultTab}' for role '${role}' must be a known dashboard tab`
  );
}

console.log("\nAll Phase 13.5 Frontend Unit & Regression Tests Passed Successfully!");
