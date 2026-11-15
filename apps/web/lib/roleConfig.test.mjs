import assert from "node:assert/strict";
import {
  ROLE_KEYS,
  ROLES_CONFIG,
  normalizeRoleId,
  getRoleConfig,
  isTabAllowedForRole,
} from "./roleConfig.js";
import { SUPPORTED_ROLES, ROLE_DEFAULT_TABS } from "./constants.js";

console.log("Running Phase 19 Role Configuration & Access Control Unit Tests...\n");

// 1. All 5 roles exist with complete metadata
console.log("1. Validating Canonical Role Configurations...");
const expectedKeys = ["Farmer", "Logistics", "Dealer", "Buyer", "Admin"];
assert.deepEqual(Object.keys(ROLES_CONFIG), expectedKeys);

for (const key of expectedKeys) {
  const cfg = ROLES_CONFIG[key];
  assert.ok(cfg.id, `Role ${key} must have id`);
  assert.ok(cfg.title, `Role ${key} must have title`);
  assert.ok(cfg.description, `Role ${key} must have description`);
  assert.ok(cfg.icon, `Role ${key} must have icon`);
  assert.ok(Array.isArray(cfg.allowedTabs), `Role ${key} must have allowedTabs`);
  assert.ok(cfg.allowedTabs.length >= 2, `Role ${key} must have at least 2 allowed tabs`);
  assert.ok(cfg.allowedTabs.includes(cfg.defaultTab), `Role ${key} defaultTab must be in allowedTabs`);
  assert.ok(Array.isArray(cfg.navItems), `Role ${key} must have navItems`);
  assert.ok(cfg.navItems.length >= 2, `Role ${key} must have at least 2 navItems`);
}

// 2. Normalization handles aliases and legacy constants
console.log("2. Validating Normalization & Alias Mapping...");
assert.equal(normalizeRoleId("Farmer"), "Farmer");
assert.equal(normalizeRoleId("farmer"), "Farmer");
assert.equal(normalizeRoleId("Logistics"), "Logistics");
assert.equal(normalizeRoleId("Transporter / Logistics Partner"), "Logistics");
assert.equal(normalizeRoleId("transporter"), "Logistics");
assert.equal(normalizeRoleId("Dealer"), "Dealer");
assert.equal(normalizeRoleId("Dealer / Trader"), "Dealer");
assert.equal(normalizeRoleId("Buyer"), "Buyer");
assert.equal(normalizeRoleId("Admin"), "Admin");
assert.equal(normalizeRoleId("Admin / Platform Manager"), "Admin");
assert.equal(normalizeRoleId("unknown_role"), "Farmer"); // safe fallback

// 3. Strict Tab Access Enforcement
console.log("3. Validating Strict Tab Access Enforcement...");

// Farmer: allowed = ["analyze", "farmer", "tracking"]
assert.equal(isTabAllowedForRole("Farmer", "analyze"), true);
assert.equal(isTabAllowedForRole("Farmer", "farmer"), true);
assert.equal(isTabAllowedForRole("Farmer", "tracking"), true);
assert.equal(isTabAllowedForRole("Farmer", "dealer"), false, "Farmer must NOT access dealer tab");
assert.equal(isTabAllowedForRole("Farmer", "status"), false, "Farmer must NOT access status tab");
assert.equal(isTabAllowedForRole("Farmer", "marketplace"), false, "Farmer must NOT access marketplace tab");

// Logistics: allowed = ["tracking", "warehouse"]
assert.equal(isTabAllowedForRole("Logistics", "tracking"), true);
assert.equal(isTabAllowedForRole("Logistics", "warehouse"), true);
assert.equal(isTabAllowedForRole("Logistics", "analyze"), false, "Logistics must NOT access analyze tab");
assert.equal(isTabAllowedForRole("Logistics", "dealer"), false, "Logistics must NOT access dealer tab");
assert.equal(isTabAllowedForRole("Logistics", "status"), false, "Logistics must NOT access status tab");

// Dealer: allowed = ["dealer", "marketplace", "tracking"]
assert.equal(isTabAllowedForRole("Dealer", "dealer"), true);
assert.equal(isTabAllowedForRole("Dealer", "analyze"), false, "Dealer must NOT access analyze tab");
assert.equal(isTabAllowedForRole("Dealer", "status"), false, "Dealer must NOT access status tab");

// Buyer: allowed = ["marketplace", "tracking"]
assert.equal(isTabAllowedForRole("Buyer", "marketplace"), true);
assert.equal(isTabAllowedForRole("Buyer", "dealer"), false, "Buyer must NOT access dealer tab");
assert.equal(isTabAllowedForRole("Buyer", "analyze"), false, "Buyer must NOT access analyze tab");
assert.equal(isTabAllowedForRole("Buyer", "status"), false, "Buyer must NOT access status tab");

// Admin: allowed = ["status", "analytics", "warehouse"]
assert.equal(isTabAllowedForRole("Admin", "status"), true);
assert.equal(isTabAllowedForRole("Admin", "analytics"), true);
assert.equal(isTabAllowedForRole("Admin", "dealer"), false, "Admin must NOT access dealer tab");
assert.equal(isTabAllowedForRole("Admin", "marketplace"), false, "Admin must NOT access marketplace tab");

console.log("All Phase 19 Role Configuration Unit Tests PASSED successfully!\n");

