# AgriChain AI — FruitNet Citrus Ripeness Annotation Protocol Proposal

**Document**: `docs/deep-learning/fruitnet_annotation_protocol_proposal.md`  
**Status**: Proposal / Pre-Pilot Draft  
**Target Dataset**: FruitNet Indian Citrus Cohort (`Orange_Good` and `Orange_Mixed`, 1,341 primary candidates)  
**Task Domain**: Exploratory Citrus External Peel-Color Maturity Classification  
**Date**: October 15, 2026  

---

## 1. Scientific Disclaimer & Conceptual Distinctions

Before any human or automated annotation is performed, annotators and engineers must understand three distinct scientific tiers of maturity:

```
                            [ THREE TIERS OF MATURITY ]
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
[ Tier 1: Optical Flavedo ]    [ Tier 2: Visual Inferred ]     [ Tier 3: Biological Ground Truth ]
• Raw RGB pixel values         • Human expert evaluation       • Laboratory destructive testing
• Hue, saturation, value       • Multi-attribute visual rubric • Total Soluble Solids (°Brix)
• Surface color only           • Peel color + glands + button  • Titratable Acidity (TA) %
• Subject to lighting/camera   • Macroscopic proxy maturity    • Brix:TA ratio & Limonin content
```

### 1. Observed Peel Color $\ne$ Internal Biological Maturity
- Citrus fruits (*Citrus spp.*) are **non-climacteric**. Unlike bananas or tomatoes, citrus does not contain starch reserves to convert into sugars after harvest, and it does not exhibit a post-harvest ethylene and respiratory surge.
- Peel degreening (loss of chlorophyll and emergence of carotenoids in the flavedo) is triggered primarily by cool orchard night temperatures ($<15^\circ\text{C}$).
- In tropical and semi-tropical climates (such as central India where FruitNet was collected), fruit pulp may reach optimal eating quality ($>10^\circ$ Brix, balanced acidity) while the rind remains partially or completely green. Conversely, fruit exposed to excessive heat or degreened with ethylene gas may have an orange rind but poor internal quality.
- **Therefore, all labels in this protocol represent visual flavedo maturity stages, not verified internal biochemical maturity.**

### 2. Cultivar Disclaimer: Indian Citrus Proxy, Not Certified Kinnow
- The FruitNet orange images were collected in Indian wholesale markets and retail stalls. They represent domestic commercial cultivars, primarily **Nagpur Mandarin** (*Citrus reticulata* Blanco) and **Mosambi** (*Citrus sinensis* Osbeck).
- They are **not confirmed Punjab Kinnow Mandarin** (*Citrus nobilis* Loureiro $\times$ *Citrus deliciosa* Tenore).
- Any dataset or model developed from this cohort must be documented as an *exploratory Indian citrus visual maturity benchmark*, not a cultivar-specific Kinnow tool.

---

## 2. Target Classification Schema

The annotation protocol establishes three target visual maturity stages and a mandatory quarantine category:

| Label Key | Schema Name | Primary Color Definition | Gland & Calyx Morphology | Commercial Equivalent |
| :---: | :---: | :--- | :--- | :--- |
| **`1`** | **`underripe`** | $>60\%$ deep green or yellowish-green rind surface. | Dense, raised, pebble-like oil glands; calyx button tightly bound and pale green. | Immature / pre-harvest harvest reject. |
| **`2`** | **`partially_ripe`** | $25\%$ to $60\%$ yellow-orange breaker coloration. | Moderate gland stretching; button yellowish-green; clear color break. | Breaker stage / commercial long-transit maturity. |
| **`3`** | **`fully_ripe`** | $>80\%$ uniform golden-orange, deep orange, or amber rind. | Expanded, flattened, glossy oil glands; pliable rind; button dry-ringed. | Dessert mature / ready-to-eat retail. |
| **`4`** | **`uncertain`** | Ambiguous, conflicting, heavily occluded, or unresolvable. | Glare obscuring $>30\%$ of rind, heavy blur, or severe decomposition. | Quarantined from maturity training. |

---

## 3. Detailed Physical Evaluation Rubric

Annotators must synthesize three observable physical characteristics rather than checking color alone:

```
                      [ MULTI-ATTRIBUTE EVALUATION MATRIX ]
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
  [ 1. Flavedo Color ]          [ 2. Gland Morphology ]       [ 3. Button / Calyx ]
  • underripe: >60% green       • underripe: Raised, rough   • underripe: Green, tight
  • breaker: 25%–60% orange     • breaker: Intermediate       • breaker: Yellow-green
  • ripe: >80% golden-orange    • ripe: Smooth, glossy        • ripe: Tan ring, dry
```

### Stage 1: `underripe` (Immature Visual State)
- **Flavedo Color**: Predominantly dark forest green, olive green, or lime green covering $>60\%$ of the visible fruit surface. Yellow or pale orange breaker patches, if present, are localized to less than $25\%$ of the surface.
- **Gland Texture**: Oil glands are prominent, tightly packed, and raised, creating a pebbled, rough surface texture.
- **Calyx ("Button")**: If visible, the button is fresh, pale green, and firmly attached to the fruit shoulder with no separation ring.

### Stage 2: `partially_ripe` (Color-Break / Turning State)
- **Flavedo Color**: Distinct color break. Between $25\%$ and $60\%$ of the surface has transitioned to yellow, pale orange, or orange. Significant green pigmentation persists, especially around the stem end, shoulders, or calyx button.
- **Gland Texture**: Oil glands around the equatorial band have flattened and expanded, while glands near the stem end remain tight and raised.
- **Calyx ("Button")**: Button shows a pale yellowish-green tint; pedicel attachment is firm.

### Stage 3: `fully_ripe` (Mature Orange State)
- **Flavedo Color**: $>80\%$ rich golden-orange, deep orange, or reddish-orange pigmentation. Residual green, if any, is restricted to a minor halo ($<10\%$) immediately adjacent to the calyx button.
- **Gland Texture**: Flavedo surface is smooth, glossy, and pliable. Oil glands are expanded and flush with the rind surface.
- **Calyx ("Button")**: Button has turned tan, pale brown, or straw-colored with a distinct dry abscission ring.

---

## 4. Handling Challenging & Ambiguous Conditions

### 1. Mixed Coloration & Transitional Boundaries
- **Rule**: If an orange has approximately 50% green and 50% orange surface, it is firmly classified as **`partially_ripe`**.
- **Boundary Threshold**:
  - If orange coverage is estimated between $20\%$ and $25\%$, the annotator must inspect gland morphology. If glands are rough and pebbled, label as `underripe`. If glands have flattened, label as `partially_ripe`.
  - If orange coverage is estimated between $75\%$ and $80\%$, inspect whether the remaining green is a localized stem ring (label as `fully_ripe`) or extends in broad streaks down the fruit flanks (label as `partially_ripe`).
  - If confidence remains low, mark as **`uncertain`** with confidence `low`.

### 2. Adverse Lighting & Camera Glare
- **Specular Flash Highlights**: Direct camera flash produces bright white glare spots.
  - If glare covers $<20\%$ of the fruit surface and the surrounding rind provides clear chromaticity, ignore the glare spot and annotate the visible rind.
  - If glare covers $>30\%$ of the central fruit area and washes out the flavedo hue, mark as **`uncertain`**.
- **Deep Shadows**: If half the fruit is in deep shadow ($V < 0.20$), base the assessment only on the well-illuminated hemisphere. Note in comments: `illumination_uneven`.

### 3. Surface Defects, Damage, and Rot (Quality vs Maturity)
> [!IMPORTANT]
> **DEFECT SCREENING MUST PRECEDENT MATURITY EVALUATION**:
> Physical decay, mold, and damage are **quality defects**, NOT stages of ripeness.
- **Severe Fungal Rot / Decomposition**: Fruit exhibiting blue/green mold (*Penicillium digitatum/italicum*), black rot (*Alternaria*), or soft watery breakdown must be marked as **`uncertain`** if the decay obscures $>25\%$ of the rind. These specimens belong in Stage 1 defect screening, not Stage 2 maturity classification.
- **Superficial Blemishes (Thrips Scarring, Sooty Mold, Sunscald)**:
  - If the blemish is superficial (e.g. gray scarring or corky tissue) and the underlying rind color is clearly visible across the majority of the fruit, annotate the maturity stage according to the healthy flavedo and record the defect in `review_notes` (e.g., `thrips_scarring_present`).
  - Do not treat cosmetic scarring as green flavedo or color break.

### 4. Multiple Fruit and Occlusions
- In frames containing multiple oranges (common in `Orange_Mixed`):
  - If one orange is clearly central and foregrounded, annotate that specific orange.
  - If multiple oranges of differing maturity stages occupy the center equally, mark as **`uncertain`** and note: `multiple_conflicting_fruits`.

---

## 5. Reviewer Metadata & Auditable Workflow

Each annotation must record:
1. `candidate_id`: Permanent ID from `citrus_candidate_review.csv` (e.g., `CAND-1160`).
2. `reviewer_id`: Unique identifier for the human evaluator (e.g., `reviewer_01`).
3. `reviewer_maturity_label`: One of `underripe`, `partially_ripe`, `fully_ripe`, `uncertain`.
4. `review_confidence`: `high`, `medium`, or `low`.
5. `review_notes`: Structured text for defects or edge cases (e.g., `flash_glare_severe`, `stem_button_green`).
6. `cultivar_verified`: Boolean `false` for all FruitNet images.
7. `ground_truth_method`: `human_visual_review`.
8. `annotated_at`: UTC ISO-8601 timestamp.

---

## 6. Pilot Implementation Plan (60 Images)

1. **Selection**: Extract 60 stratified candidates:
   - 20 Predominantly Green (sampled from distinct burst clusters)
   - 20 Color-Break / Turning (sampled from distinct burst clusters)
   - 20 Predominantly Orange (sampled from distinct burst clusters)
2. **Blinded Dual-Annotation**: Two independent reviewers evaluate the identical 60 candidates without conferring.
3. **Statistical Acceptance**:
   - Compute Cohen's Kappa ($\kappa$). Minimum threshold: $\kappa \ge 0.75$.
   - Compute raw percentage agreement. Minimum threshold: $\ge 85\%$.
4. **Resolution Conference**: Review all discordant cases to calibrate boundaries before proceeding to the broader candidate pool.
