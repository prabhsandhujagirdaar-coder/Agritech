import assert from "node:assert/strict";
import {
  CLASS_LABELS,
  RIPENESS_CLASSES,
  getClassIndex,
  getRipenessLabel,
  formatConfidence,
  UNCERTAINTY_THRESHOLDS,
  checkPredictionUncertainty,
} from "./constants.js";

console.log("Running Guava & Produce CNN Class Labels & Ripeness Taxonomy Tests...\n");

// Test 1: Centralized Mapping has exactly 3 classes
assert.equal(Object.keys(CLASS_LABELS).length, 3, "CLASS_LABELS must contain exactly 3 classes");
assert.deepEqual(RIPENESS_CLASSES, [0, 1, 2], "RIPENESS_CLASSES must contain exactly [0, 1, 2]");

// Guava Specific Taxonomy Verification
import { GUAVA_CLASS_LABELS } from "./constants.js";
assert.equal(GUAVA_CLASS_LABELS[0], "Green", "Guava index 0 must be Green");
assert.equal(GUAVA_CLASS_LABELS[1], "Mature Green", "Guava index 1 must be Mature Green");
assert.equal(GUAVA_CLASS_LABELS[2], "Ripe", "Guava index 2 must be Ripe");

// Test 2: Required test cases from specification
// Class 0 -> Underripe
assert.equal(CLASS_LABELS[0], "Underripe", "Class 0 must map to Underripe");
assert.equal(getRipenessLabel(0), "Underripe", "getRipenessLabel(0) must return Underripe");
assert.equal(getRipenessLabel("class0"), "Underripe", "getRipenessLabel('class0') must return Underripe");
assert.equal(getRipenessLabel("0"), "Underripe", "getRipenessLabel('0') must return Underripe");

// Class 1 -> Partially Ripe
assert.equal(CLASS_LABELS[1], "Partially Ripe", "Class 1 must map to Partially Ripe");
assert.equal(getRipenessLabel(1), "Partially Ripe", "getRipenessLabel(1) must return Partially Ripe");
assert.equal(getRipenessLabel("class1"), "Partially Ripe", "getRipenessLabel('class1') must return Partially Ripe");
assert.equal(getRipenessLabel("1"), "Partially Ripe", "getRipenessLabel('1') must return Partially Ripe");

// Class 2 -> Fully Ripe
assert.equal(CLASS_LABELS[2], "Fully Ripe", "Class 2 must map to Fully Ripe");
assert.equal(getRipenessLabel(2), "Fully Ripe", "getRipenessLabel(2) must return Fully Ripe");
assert.equal(getRipenessLabel("class2"), "Fully Ripe", "getRipenessLabel('class2') must return Fully Ripe");
assert.equal(getRipenessLabel("2"), "Fully Ripe", "getRipenessLabel('2') must return Fully Ripe");

// Confidence formatting test: 0.9718 -> 97.18%
assert.equal(formatConfidence(0.9718), "97.18%", "Confidence 0.9718 must format to 97.18%");

// Test 3: API payload parsing
const apiPayload1 = { class: 2, confidence: 0.9718 };
assert.equal(getClassIndex(apiPayload1), 2, "Payload class: 2 should resolve to index 2");
assert.equal(getRipenessLabel(apiPayload1), "Fully Ripe", "Payload class: 2 should resolve to Fully Ripe");

const apiPayload2 = { class_index: 0, predicted_class: "class0", confidence: 0.95 };
assert.equal(getClassIndex(apiPayload2), 0, "Payload class_index: 0 should resolve to index 0");
assert.equal(getRipenessLabel(apiPayload2), "Underripe", "Payload class_index: 0 should resolve to Underripe");

const apiPayload3 = { class_index: 1, predicted_class: "class1", confidence: 0.884 };
assert.equal(getClassIndex(apiPayload3), 1, "Payload class_index: 1 should resolve to index 1");
assert.equal(getRipenessLabel(apiPayload3), "Partially Ripe", "Payload class_index: 1 should resolve to Partially Ripe");

// Test 4: Preserves backend label if already provided
const apiPayloadWithLabel = { class_index: 1, label: "Partially Ripe Custom", confidence: 0.9 };
assert.equal(getRipenessLabel(apiPayloadWithLabel), "Partially Ripe Custom", "Backend label should be preserved when provided");

// Test 5: Verify NO fourth class exists
assert.equal(CLASS_LABELS[3], undefined, "Class 3 must not exist");
assert.equal(CLASS_LABELS[4], undefined, "Class 4 must not exist");
assert.equal(getClassIndex("class3"), null, "class3 must return null");

// Test 6: Verify old 4-class terminology is NOT in CLASS_LABELS
const labelValues = Object.values(CLASS_LABELS);
const prohibited = [
  "Fresh", "fresh",
  "Early Decline", "early decline",
  "Moderate Spoilage", "moderate spoilage",
  "Spoiled", "spoiled",
  "damaged", "early_spoilage", "rotten"
];
for (const term of prohibited) {
  assert.ok(!labelValues.includes(term), `Prohibited term '${term}' must not be in CLASS_LABELS`);
}

// Test 7: Guava CNN Class Labels & Ripeness Mapping (Phase 4 Integration)
assert.equal(getClassIndex("Green"), 0, "'Green' should resolve to class index 0");
assert.equal(getClassIndex("Mature Green"), 1, "'Mature Green' should resolve to class index 1");
assert.equal(getClassIndex("Ripe"), 2, "'Ripe' should resolve to class index 2");

const guavaPayload = {
  predicted_class: "Mature Green",
  class_index: 1,
  label: "Mature Green",
  confidence: 0.9310,
  probabilities: { "Green": 0.0412, "Mature Green": 0.9310, "Ripe": 0.0278 },
  target_crop: "guava",
  model_version: "2.0.0",
};
assert.equal(getClassIndex(guavaPayload), 1, "Guava payload should resolve to index 1");
assert.equal(getRipenessLabel("Green"), "Green", "getRipenessLabel('Green') must return 'Green'");
assert.equal(getRipenessLabel("Mature Green"), "Mature Green", "getRipenessLabel('Mature Green') must return 'Mature Green'");
assert.equal(getRipenessLabel("Ripe"), "Ripe", "getRipenessLabel('Ripe') must return 'Ripe'");
assert.equal(getRipenessLabel({ class_index: 0, target_crop: "guava" }), "Green", "Guava class 0 should resolve to 'Green'");
assert.equal(getRipenessLabel({ class_index: 1, target_crop: "guava" }), "Mature Green", "Guava class 1 should resolve to 'Mature Green'");
assert.equal(getRipenessLabel({ class_index: 2, target_crop: "guava" }), "Ripe", "Guava class 2 should resolve to 'Ripe'");

// Test 8: Prediction Uncertainty Heuristic (Phase 7)
assert.equal(UNCERTAINTY_THRESHOLDS.MIN_TOP_SCORE, 0.60, "Default MIN_TOP_SCORE should be 0.60");
assert.equal(UNCERTAINTY_THRESHOLDS.MIN_SCORE_MARGIN, 0.15, "Default MIN_SCORE_MARGIN should be 0.15");

// Low top score example 1 (e.g. 47.36%)
const lowScoreResult1 = {
  predicted_class: "Green",
  class_index: 0,
  label: "Green",
  confidence: 0.4736,
  probabilities: { "Green": 0.4736, "Mature Green": 0.4510, "Ripe": 0.0754 },
};
const u1 = checkPredictionUncertainty(lowScoreResult1);
assert.equal(u1.isUncertain, true, "Top score 47.36% must be flagged as uncertain");
assert.equal(u1.message, "Prediction uncertain — inspect the fruit manually.");
assert.equal(u1.reason, "both", "47.36% has both low top score (<0.60) and small margin (<0.15)");
// Predicted class remains visible
assert.equal(lowScoreResult1.label, "Green");

// Low top score example 2 (e.g. 50.72%)
const lowScoreResult2 = {
  predicted_class: "Mature Green",
  class_index: 1,
  label: "Mature Green",
  confidence: 0.5072,
  probabilities: { "Green": 0.0428, "Mature Green": 0.5072, "Ripe": 0.4500 },
};
const u2 = checkPredictionUncertainty(lowScoreResult2);
assert.equal(u2.isUncertain, true, "Top score 50.72% must be flagged as uncertain");
assert.equal(u2.message, "Prediction uncertain — inspect the fruit manually.");
assert.equal(lowScoreResult2.label, "Mature Green");

// Clear, high score example (e.g. 75.18%)
const confidentResult1 = {
  predicted_class: "Mature Green",
  class_index: 1,
  label: "Mature Green",
  confidence: 0.7518,
  probabilities: { "Green": 0.2266, "Mature Green": 0.7518, "Ripe": 0.0216 },
};
const u3 = checkPredictionUncertainty(confidentResult1);
assert.equal(u3.isUncertain, false, "Score 75.18% with large margin must not be flagged uncertain");
assert.equal(u3.reason, "none");
assert.equal(u3.message, "");

// Clear high score (e.g. 97.06% Green)
const confidentResult2 = {
  predicted_class: "Green",
  class_index: 0,
  label: "Green",
  confidence: 0.9706,
  probabilities: { "Green": 0.9706, "Mature Green": 0.0289, "Ripe": 0.0006 },
};
const u4 = checkPredictionUncertainty(confidentResult2);
assert.equal(u4.isUncertain, false);

// Clear high score (e.g. 67.70% Ripe)
const confidentResult3 = {
  predicted_class: "Ripe",
  class_index: 2,
  label: "Ripe",
  confidence: 0.6770,
  probabilities: { "Green": 0.0597, "Mature Green": 0.2633, "Ripe": 0.6770 },
};
const u5 = checkPredictionUncertainty(confidentResult3);
assert.equal(u5.isUncertain, false, "Ripe 67.70% with margin 0.4137 should not be uncertain");

// Independent condition: Low score ONLY under default thresholds (top < 0.60, margin >= 0.15)
const lowScoreOnlyResult = {
  predicted_class: "Green",
  confidence: 0.58,
  probabilities: { "Green": 0.58, "Mature Green": 0.25, "Ripe": 0.17 },
};
const uLowOnly = checkPredictionUncertainty(lowScoreOnlyResult);
assert.equal(uLowOnly.isUncertain, true, "Top score 58% (<0.60) with 33% margin must be uncertain");
assert.equal(uLowOnly.reason, "low_top_score", "Should trigger low_top_score specifically");

// Independent condition: Close margin ONLY under default thresholds (top >= 0.60, margin < 0.15)
const closeMarginOnlyResult = {
  predicted_class: "Ripe",
  confidence: 0.62,
  probabilities: { "Green": 0.05, "Mature Green": 0.52, "Ripe": 0.62 },
};
const uCloseOnly = checkPredictionUncertainty(closeMarginOnlyResult);
assert.equal(uCloseOnly.isUncertain, true, "Top score 62% with 10% margin (<0.15) must be uncertain");
assert.equal(uCloseOnly.reason, "close_scores", "Should trigger close_scores specifically");

// Close scores with custom configurable threshold override
const customCheck = checkPredictionUncertainty(closeMarginOnlyResult, { MIN_SCORE_MARGIN: 0.05 });
assert.equal(customCheck.isUncertain, false, "Margin 0.10 is >= overridden MIN_SCORE_MARGIN 0.05, so not uncertain");
assert.equal(customCheck.reason, "none");

// Test 9: Verify All 3 Classes with Uncertain and Certain Scenarios
const classScenarios = [
  { class_name: "Green", top: 0.45, second: 0.43, expectedUncertain: true },
  { class_name: "Green", top: 0.95, second: 0.04, expectedUncertain: false },
  { class_name: "Mature Green", top: 0.49, second: 0.46, expectedUncertain: true },
  { class_name: "Mature Green", top: 0.85, second: 0.12, expectedUncertain: false },
  { class_name: "Ripe", top: 0.48, second: 0.47, expectedUncertain: true },
  { class_name: "Ripe", top: 0.88, second: 0.10, expectedUncertain: false },
];

for (const sc of classScenarios) {
  const mockPayload = {
    predicted_class: sc.class_name,
    label: sc.class_name,
    confidence: sc.top,
    probabilities: {
      [sc.class_name]: sc.top,
      "Competitor": sc.second,
      "Third": Math.max(0, 1.0 - sc.top - sc.second),
    },
  };
  const res = checkPredictionUncertainty(mockPayload);
  assert.equal(
    res.isUncertain,
    sc.expectedUncertain,
    `Class ${sc.class_name} with top ${sc.top} should have isUncertain=${sc.expectedUncertain}`
  );
  // Ensure predicted class and label remain intact
  assert.equal(mockPayload.label, sc.class_name);
}

// Null/empty input handling
assert.equal(checkPredictionUncertainty(null).isUncertain, false);
assert.equal(checkPredictionUncertainty({}).isUncertain, false);

console.log("All CNN Class Labels, Produce Taxonomy, & Phase 7 Uncertainty Tests PASSED successfully!");
