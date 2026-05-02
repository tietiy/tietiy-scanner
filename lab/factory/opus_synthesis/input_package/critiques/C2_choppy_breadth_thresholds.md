# C2 — Choppy Breadth Threshold Validation

**Date:** 2026-05-03
**Sonnet's concern:** "Choppy detector breadth thresholds (low/medium/
high) may not be data-validated. Could be arbitrary boundaries that
don't match actual edge concentration."

**Verdict: ⚠️ MARGINAL — current 33/67 is reasonable but not optimal; 25/75 produces +2pp span improvement; 20/80 maximizes discrimination at cost of cell stability.**

---

## A. Hypothesis

Tertile splits (33/67) on a continuous feature are conventional but
may not align with where actual WR variance concentrates. If a
different split produces materially higher discrimination (e.g., +5pp
span) while preserving meaningful cell sizes, the current detector
under-uses the breadth signal.

---

## B. Investigation

### Setup

Same dataset as C1: n=31,553 resolved Choppy signals, baseline WR
51.0%. `feat_market_breadth_pct` is continuous; tested 5 split options
+ fine-grained search.

### Threshold sweep

| Split | Thresholds | WR span | Smallest cell | % of total |
|---|---|---|---|---|
| 20/80 | [0.393, 0.652] | **19.37pp** | 1,472 | 4.7% |
| 25/75 | [0.418, 0.626] | 15.26pp | 1,746 | 5.5% |
| 30/70 | [0.441, 0.607] | 13.53pp | 2,130 | 6.8% |
| **33/67 (current)** | [0.456, 0.597] | 13.31pp | 1,943 | 6.2% |
| 40/60 | [0.490, 0.570] | 12.23pp | 1,091 | 3.5% |

### Fine-grained asymmetric search

Tested all (low_q, high_q) combos with low ∈ {0.20, 0.25, 0.30, 0.33,
0.40, 0.45} × high ∈ {0.55, 0.60, 0.67, 0.70, 0.75, 0.80}, requiring
all cells n ≥ 1,000:

**Best (maximum WR span):** split=(0.20, 0.55), span=**20.91pp**.

This asymmetric split classifies 20% of days as low-breadth, 35% as
medium-breadth, 45% as high-breadth. Reflects the underlying
distribution where breadth tends to be skewed high (more "broad
participation" days than "narrow" days).

### Per-signal-type discrimination

Current 33/67 split, stratified by signal:

| Signal | WR span | Cells with n≥300 |
|---|---|---|
| UP_TRI | 19.66pp | 9/9 |
| DOWN_TRI | 20.49pp | 9/9 |
| BULL_PROXY | 21.71pp | 1/9 (sparse cell) |

Alternative 25/75 split:

| Signal | WR span | Cells with n≥300 |
|---|---|---|
| UP_TRI | **20.58pp** | 9/9 |
| DOWN_TRI | 15.41pp ↓ | 8/9 |
| BULL_PROXY | (insufficient n) | — |

Alternative 40/60 split:

| Signal | WR span | Cells with n≥300 |
|---|---|---|
| UP_TRI | 18.75pp | 9/9 |
| DOWN_TRI | **29.05pp** ★ | 8/9 |
| BULL_PROXY | (insufficient n) | — |

### Critical finding

**Different signal types prefer different splits:**
- UP_TRI: 25/75 (wider tails capture extreme breadth conditions)
- DOWN_TRI: 40/60 (tighter middle → DOWN_TRI sensitivity at the equilibrium boundary)
- BULL_PROXY: signal too sparse for stable threshold estimation

This suggests the optimal split is **signal-type-conditional**, not
a single Choppy-wide threshold.

---

## C. Decision criteria

From session brief:
- Maximize WR variance between cells
- Maintain meaningful cell sizes (no cell <5% of data)

| Split | WR span | Smallest cell % | Both criteria? |
|---|---|---|---|
| 20/80 | 19.37pp | 4.7% | NO (cell <5%) |
| 25/75 | 15.26pp | 5.5% | YES |
| 30/70 | 13.53pp | 6.8% | YES |
| **33/67 (current)** | 13.31pp | 6.2% | YES |
| 40/60 | 12.23pp | 3.5% | NO (cell <5%) |

**Best meeting both criteria: 25/75** — +2pp span improvement vs
current 33/67, all cells ≥5%.

But the per-signal analysis shows different optima per signal type.
Single-threshold approach is intrinsically a compromise.

---

## D. Mechanistic interpretation

### Why DOWN_TRI prefers 40/60 split

DOWN_TRI signals (descending triangle / short setups) work best when
breadth is decisively narrow OR decisively broad — the equilibrium
zone is where short setups fail (whipsawing). Tighter middle (40/60)
puts ~20% of days in the medium bucket, isolating extremes more
cleanly.

### Why UP_TRI prefers 25/75 split

UP_TRI signals (ascending triangle / long setups) work best when
breadth confirms via wide-or-narrow extremes. Wider tails (25/75) put
50% of days in extreme buckets, capturing more of the discriminating
variance.

### Why current 33/67 is a reasonable compromise

Tertile splits are mathematically clean (equal cell sizes) and
robust to small distributional shifts. They make WR comparison across
cells statistically meaningful. The 2pp gain from switching to 25/75
must be weighed against operational complexity.

---

## E. Recommendation

**Three options, in order of conservatism:**

### Option A: KEEP 33/67 (recommended)

**Rationale:** Marginal improvement from 25/75 doesn't justify
production change. Current detector works (13.3pp span). Other gaps
(C1 momentum addition, C3 hysteresis) have higher impact.

**Action:** Document in audit notes that 33/67 was tested vs alternatives
and confirmed as reasonable. No change to production.

### Option B: SHIP 25/75 split

**Rationale:** +2pp span improvement, all cells preserved at ≥5% of
data. Modest UX impact; cells re-stratify smoothly.

**Action:** Update Choppy sub-regime detector breadth thresholds to
(0.418, 0.626). Re-derive cell × signal × outcome lifetime tables.
Update mini_scanner_rules.json boost_patterns referencing breadth.

### Option C: SIGNAL-TYPE-CONDITIONAL THRESHOLDS

**Rationale:** Different signal types have meaningfully different
optimal splits. Single-threshold approach is intrinsically a compromise.

**Action:** Define per-signal-type breadth bucketing in the rule
schema. e.g., `breadth_bucket = compute_breadth_bucket(market_breadth_pct,
signal_type)`. UP_TRI uses (0.418, 0.626); DOWN_TRI uses (0.490, 0.570);
BULL_PROXY defers to UP_TRI for now.

**Risk:** complex; harder to reason about; production schema must
support per-signal feature transforms.

---

## F. Honest verdict

**MARGINAL — recommend Option A (keep current)** based on:
1. Current 33/67 is reasonable (passes both criteria)
2. +2pp improvement from 25/75 is below the threshold for production
   change risk
3. Bigger wins are available elsewhere:
   - C1 momentum addition: +13.8pp span improvement
   - Sub-regime tier integration (PRODUCTION_POSTURE Gap 2): unlocks 74% WR cells

**If breadth threshold change ships:** prefer 25/75 over 20/80
(better cell stability) and over signal-conditional (operational
complexity).

**Future work item (LOW priority):** revisit if/when production data
shows specific cells are underperforming due to threshold mismatch
(e.g., a "high breadth" cell consistently has 51% WR, suggesting it
should be re-bucketed).

---

## G. Investigation summary

| Aspect | Finding |
|---|---|
| Current 33/67 split discrimination | 13.31pp WR span across 9 cells |
| Optimal symmetric split (cells ≥5%) | 25/75 (15.26pp) |
| Maximum discrimination (asymmetric) | 20/55 split (20.91pp) — but skewed buckets |
| Per-signal optimum | UP_TRI: 25/75; DOWN_TRI: 40/60; BULL_PROXY: insufficient |
| Recommended action | KEEP 33/67 (Option A) |
| Margin for change | +2pp not enough to justify production update |
| Higher-priority wins available | C1 momentum (+13.8pp), Gap 2 sub-regime |

Sonnet's concern was valid — thresholds are conventional, not data-
optimized. But the magnitude of suboptimality is small enough that
priority sits with other gaps (momentum addition, sub-regime detector
ship).
