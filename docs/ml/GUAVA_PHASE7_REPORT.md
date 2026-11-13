# AgriChain AI — Phase 7: Prediction Uncertainty & Farmer-Friendly Results Report

**Document Version:** 1.0.0  
**Target Crop:** Guava (*Psidium guajava* L.)  
**Model Architecture:** ResNet18 Transfer Learning Baseline (v2.0.0, frozen weights)  
**Backend:** FastAPI + Uvicorn (`http://127.0.0.1:8000`)  
**Frontend:** Next.js 14 (`http://localhost:3000`)  
**Implementation Date:** October 2026  
**Status:** Completed & Verified  

---

## Executive Summary

Phase 7 enhances the user presentation and operational transparency of the Guava CNN maturity prediction service without modifying model weights, retuning hyperparameters, retraining, or altering backend database schemas. 

During Phase 5 and Phase 6, test inferences on diverse guava specimens yielded uncalibrated softmax scores ranging from high certainty (e.g., 97.06% on unambiguous Green fruit) to intermediate or contested distributions (e.g., 75.18%, 50.72%, and 47.36% on transitional or mixed fruit). In raw deployment, high-confidence numbers can mislead growers into over-trusting borderline classifications, while ambiguous scores can leave farmers without actionable guidance.

To resolve these presentation challenges with scientific integrity:
1. **Uncertainty-Aware Presentation:** A transparent UI heuristic was implemented in the frontend. When the top softmax score is low (< 0.60) or the top two class scores are closely contested (margin < 0.15), a neutral guidance banner is displayed: `“Prediction uncertain — inspect the fruit manually.”` The predicted class remains visible at all times.
2. **Image-Quality Guidance:** Practical field advice was added to the upload interface, guiding farmers to capture one fruit per photo under good lighting with a clear view, and explicitly noting that the model predicts one overall class for the image rather than detecting individual fruits.
3. **Maturity Decoupled from "Quality Grading":** The UI terminology was audited and revised from ambiguous "Quality Grading" to precise "Maturity Stage Evaluation". Disclaimers make clear that the model only evaluates surface maturity (Green, Mature Green, Ripe) and does not inspect for disease, internal rot, pests, food safety, or market grade.
4. **Uncalibrated Score Semantics Preserved:** The metric continues to be labeled as "Softmax Score" with an explicit "Uncalibrated score" descriptor.
5. **Rigorous Test Validation:** Frontend test suites were added to cover low scores, close margins, clear scores, custom overrides, and all three classes. Zero regression was confirmed across backend tests and Next.js linting.

---

## 1. Exact Uncertainty Thresholds & Scientific Rationale

### Threshold Configuration (`apps/web/lib/constants.js`)

```javascript
export const UNCERTAINTY_THRESHOLDS = {
  // Flag as uncertain if top softmax score is below 60% (0.60)
  MIN_TOP_SCORE: 0.60,
  // Flag as uncertain if margin between top 2 class scores is below 15% (0.15)
  MIN_SCORE_MARGIN: 0.15,
};
```

### Heuristic Evaluation Logic

The function `checkPredictionUncertainty(result, customThresholds)` evaluates the probability distribution returned by the CNN:
- **Low Top Score Rule:** If the highest softmax score is below `0.60` (`60.0%`), the model lacks strong class activation dominance. Example: A specimen predicting 47.36% Green and 45.10% Mature Green triggers `low_top_score`.
- **Close Margin Rule:** If the difference between the 1st and 2nd highest class scores is below `0.15` (`15.0%`), the prediction is closely contested across adjacent maturity categories. Example: A specimen predicting 52.0% Mature Green and 46.0% Ripe (margin = 6.0%) triggers `close_scores`.
- **Compound Rule:** If both conditions are met, the reason is flagged as `both`.
- **Configurability:** Thresholds can be dynamically overridden per invocation (e.g. `{ MIN_TOP_SCORE: 0.70 }`), ensuring flexibility as deployment parameters evolve.

### Crucial Scientific & Operational Disclaimers
- **UI Heuristic, Not Calibrated Probability:** These thresholds are operational presentation rules implemented in the UI layer. They are **not** Bayesian credible intervals, conformal prediction sets, or statistically calibrated probabilities.
- **No Claim of Self-Awareness:** The interface does **not** claim the model "knows when it is wrong." Neural networks with uncalibrated softmax heads can produce high overconfidence on out-of-distribution inputs. The heuristic serves strictly as an operational prompt for human-in-the-loop inspection.
- **Preservation of Prediction:** When the uncertainty banner appears, the predicted class is never suppressed or hidden. The farmer sees both the model's top guess and the recommendation to verify manually.

---

## 2. Image-Quality Guidance for Field Use

To assist farmers and field technicians in obtaining reliable inputs, the upload component now includes prominent image guidance:

1. **One fruit per photo:** Frame a single guava centered in the image where practical, ensuring natural, even lighting and a clear, focused view without heavy shadows or obstructions.
2. **Multiple fruits in frame:** The CNN evaluates a single overall class for the entire uploaded image. It does **not** perform object detection, spatial segmentation, or individual fruit classification.
3. **Maturity scope:** Explicitly reminds the user that the model evaluates surface maturity stage only (Green, Mature Green, Ripe) and does not perform internal or commercial quality grading.

---

## 3. Separation of Maturity from "Quality Grading"

In agricultural science and commerce, "quality" includes physical integrity, blemish presence, pest damage, internal rot, brix level, and market export specifications. A 3-class surface vision classifier cannot assess these attributes.

To prevent deceptive marketing or misleading growers:
- **Button Label Updated:** Renamed from `"Analyze Guava Quality"` to `"Evaluate Guava Maturity"`.
- **Inspection Service Scope:** Added a persistent disclaimer banner directly beneath the score card:
  > *"Maturity Assessment Scope: This CNN evaluates surface harvest maturity stage (Green, Mature Green, Ripe) only. It does not inspect for pest infestation, fungal disease, internal decay, freshness, food safety, or commercial market grade."*
- **No Inferred Attributes:** No downstream safety or market grading certifications are generated or implied from maturity predictions.

---

## 4. Score Semantics

The model output score is formally presented as:
- **Card Title:** `Softmax Score`
- **Numerical Value:** Formatted to two decimal places (e.g., `47.36%`, `75.18%`, `97.06%`)
- **Subtitle Descriptor:** `Uncalibrated score`
- **Explanatory Tooltip / Context:** Explicit documentation that the value represents the normalized exponential logit magnitude, not a guaranteed likelihood of accuracy or statistical reliability.

---

## 5. Verification & Test Results

### Frontend Unit Tests (`apps/web/lib/constants.test.mjs`)

Added comprehensive test suites (Test 8 and Test 9) executing under Node.js:
- **Low Top Score Tests:** Validated with specimen scores `47.36%` and `50.72%` $\to$ correctly flags `isUncertain = true` with message `"Prediction uncertain — inspect the fruit manually."`
- **Near-Tied Score Tests:** Validated closely contested distributions (e.g., 0.52 vs 0.46) $\to$ correctly flags uncertainty due to `close_scores`.
- **Clear High Score Tests:** Validated high certainty scores (`75.18%`, `97.06%`, `67.70%`) $\to$ flags `isUncertain = false` and `message = ""`.
- **Configurable Overrides:** Validated custom threshold overrides (`MIN_SCORE_MARGIN: 0.35`).
- **All Three Classes Covered:** Both certain and uncertain scenarios tested for `Green`, `Mature Green`, and `Ripe`.
- **Layout & Identity Preservation:** Verified `predicted_class` and `label` are preserved without mutation.
- **Null & Empty Safety:** Verified `checkPredictionUncertainty(null)` and `checkPredictionUncertainty({})` return safe non-crashing defaults (`isUncertain = false`).

**Test Execution Output:**
```
> agrichain-web@0.1.0 test
> node lib/constants.test.mjs

Running Strawberry CNN Class Labels & Ripeness Taxonomy Tests...
All CNN Class Labels, Produce Taxonomy, & Phase 7 Uncertainty Tests PASSED successfully!
```

### Frontend Code Quality (`npm run lint` in `apps/web`)
```
> agrichain-web@0.1.0 lint
> next lint

Exit Code: 0 (0 errors, 4 non-blocking pre-existing Next.js image warnings)
```

### Backend Regression Tests (`python -m unittest`)
- `backend/tests/test_guava_cnn_integration.py`: **11 of 11 tests passed** (100% pass rate).
- `backend/tests/test_cnn_api.py`: **15 of 15 tests passed** (100% pass rate).
- Total backend tests passing: **39 of 39**.

---

## 6. Files Changed and Technical Modifications

| File | Change Type | Summary of Changes |
| :--- | :--- | :--- |
| [`apps/web/lib/constants.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.js) | Edit | Defined `UNCERTAINTY_THRESHOLDS` (`MIN_TOP_SCORE: 0.60`, `MIN_SCORE_MARGIN: 0.15`) and implemented `checkPredictionUncertainty()` with null-safety and configurable overrides. |
| [`apps/web/app/dashboard/page.js`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/app/dashboard/page.js) | Edit | Integrated field image-quality guidance card; updated action button to "Evaluate Guava Maturity"; inserted the uncertainty warning banner; added the explicit maturity assessment scope disclaimer; preserved predicted class visibility and uncalibrated score tags. |
| [`apps/web/lib/constants.test.mjs`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/apps/web/lib/constants.test.mjs) | Edit | Added unit tests covering low scores (47.36%, 50.72%), confident scores (75.18%, 97.06%, 67.70%), near-tied margins, custom overrides, and all three maturity classes. |
| [`docs/ml/GUAVA_PHASE7_REPORT.md`](file:///c:/Users/PrabSandhu/Documents/codes/Agritech_/docs/ml/GUAVA_PHASE7_REPORT.md) | Create | Comprehensive Phase 7 report detailing uncertainty heuristics, guidance, scope distinctions, test suites, and remaining limitations. |

---

## 7. Remaining Limitations & Boundaries

1. **Absence of Temperature Scaling or Platt Scaling:** The model's softmax outputs remain mathematically uncalibrated. A future calibration phase utilizing held-out validation logits to fit an optimal temperature parameter $T$ is recommended before making probabilistic assertions.
2. **Single-Fruit Assumption:** The classification model operates on whole-image RGB features. When multiple guavas or busy foliage appear in an image, the model cannot distinguish between fruits or classify them separately. An object-detection model (e.g., YOLO or Faster R-CNN) would be required for multi-fruit localization.
3. **Transitional Maturity Ambiguity:** In biological reality, ripening is a continuous physiological continuum rather than discrete bins. Specimens transitioning between Mature Green and Ripe naturally exhibit overlapping visual features that produce balanced softmax logits.
4. **No Agricultural or Clinical Certification:** This system has not undergone clinical, legal, or regulatory agricultural grading certification. It is an experimental decision-support tool and must not be used as the sole determinant for commercial contracts, export grading, food safety validation, or phytosanitary compliance.
