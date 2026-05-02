# C1 — Choppy Missing Momentum Feature

**Date:** 2026-05-03
**Sonnet's concern:** "Choppy sub-regime detector (vol × breadth)
doesn't capture momentum. Choppy with rising momentum is structurally
different from Choppy with falling momentum, but current detector
treats them the same."

**Verdict: ✅ RESOLVED with action — momentum produces 11.8pp avg within-cell variance; ADD `nifty_20d_return_pct` as 3rd detector axis.**

---

## A. Hypothesis

If momentum is redundant with vol × breadth, adding it would not
produce meaningful WR variance within existing cells. If momentum
captures distinct structure, within-cell WR would split cleanly across
momentum buckets.

Decision criteria from session brief:
- Variance > 5pp → ADD to detector
- Variance < 3pp → REJECT (redundant)
- Variance 3-5pp → MARGINAL (recommend production test)

---

## B. Investigation

### Setup

Ran on `lab/output/enriched_signals.parquet` (105,987 enriched signals
across all regimes, 141 features). Filtered to:
- regime=Choppy
- outcome ∈ {DAY6_WIN, TARGET_HIT, DAY6_LOSS, STOP_HIT} (resolved only)

Result: **n=31,553 resolved Choppy signals, baseline WR=51.0%**.

Bucketed `feat_market_breadth_pct` by tertiles (33/67 splits):
- low ≤ 0.456
- medium 0.456-0.597
- high ≥ 0.597

### Current detector (vol × breadth) — baseline

| vol | breadth | n | WR |
|---|---|---|---|
| High | medium | 3365 | **59.0%** ★ best |
| Low | high | 2600 | 53.5% |
| Low | medium | 1943 | 52.1% |
| Medium | high | 5306 | 51.6% |
| High | high | 2612 | 51.3% |
| Medium | medium | 5311 | 51.1% |
| Low | low | 2400 | 49.5% |
| High | low | 2954 | 48.1% |
| Medium | low | 5062 | **45.7%** ← worst |

**Current detector WR span (max - min): 13.3pp.**

### 3-axis detector (vol × breadth × mom_20d)

Added `feat_nifty_20d_return_pct` bucketed by tertile:
- falling (≤ -1.32%)
- flat (-1.32% to +0.72%)
- rising (≥ +0.72%)

Top + bottom cells of 3-axis (n ≥ 200):

| vol | breadth | mom | n | WR |
|---|---|---|---|---|
| High | medium | flat | 938 | **64.3%** ★ |
| High | low | rising | 916 | 61.9% |
| Medium | high | rising | 2658 | 60.8% |
| High | medium | rising | 1416 | 60.1% |
| ... | ... | ... | ... | ... |
| Medium | high | flat | 1792 | 42.0% |
| Medium | low | flat | 1456 | 38.9% |
| Low | low | rising | 279 | 39.8% |

**3-axis detector WR span: 27.1pp.** Doubles the current detector's
discriminating power.

### Within-cell momentum variance (per (vol × breadth) cell)

| Cell | n | base WR | momentum span | Verdict |
|---|---|---|---|---|
| **High × low** | 2954 | 48.1% | **24.7pp** (rising 61.9% vs falling 37.2%) | strongest signal |
| **Medium × high** | 5306 | 51.6% | **18.9pp** (rising 60.8% vs flat 42.0%) | strong |
| Medium × medium | 5311 | 51.1% | 11.8pp (falling 56.5% vs flat 44.7%) | inverted! |
| High × medium | 3365 | 59.0% | 11.7pp (flat 64.3% vs falling 52.6%) | strong |
| Low × low | 2400 | 49.5% | 11.1pp (flat 50.9% vs **rising 39.8%**) | inverted! |
| Medium × low | 5062 | 45.7% | 9.8pp | strong |
| Low × medium | 1943 | 52.1% | 9.1pp | strong |
| Low × high | 2600 | 53.5% | 5.1pp | marginal |
| High × high | 2612 | 51.3% | 4.2pp | redundant |

**Average within-cell span: 11.8pp** — well above 5pp threshold.

**6 of 9 cells show >9pp within-cell variance.** 2 marginal/redundant
cells (Low × high, High × high). 1 inverted cell (Medium × medium —
where falling momentum is winner; mean-reversion logic).

### Comparison: candidate momentum features

| Feature | Type | Avg within-cell span |
|---|---|---|
| `feat_nifty_20d_return_pct` | continuous (tertiled) | **11.8pp** ★★★ |
| `feat_ROC_10` | continuous (tertiled) | 10.0pp ★★ |
| `feat_MACD_signal` | categorical (bull/bear) | 6.1pp ★ |
| `feat_ema50_slope_20d_pct` | continuous (tertiled) | 4.3pp BELOW threshold |

**`nifty_20d_return_pct` wins** as the momentum axis. ROC_10 is a
close second.

---

## C. Mechanistic interpretation

### Cell-by-cell momentum stories

**High × low × rising: 61.9% (vs 37.2% falling)** — high vol +
narrow breadth + rising momentum = early-Bull-like recovery within
Choppy. Recovery setup, momentum confirms.

**Medium × high × rising: 60.8% (vs 42.0% flat)** — equilibrium vol
+ broad participation + rising momentum = trend-of-Choppy continuation
working.

**Medium × medium × falling: 56.5% (vs 44.7% flat)** — equilibrium
across all axes + falling momentum = mean-reversion working
(counter-trend buy).

**Low × low × rising: 39.8% (vs flat/falling)** — low vol + narrow
breadth + rising momentum = late-trend exhaustion in Choppy. Rising
momentum is a TRAP here.

This is exactly the pattern Sonnet flagged: Choppy is not uniform on
momentum. Different momentum × cell combinations produce different
trade logic.

### Cross-cell architectural alignment

The 3-axis detector aligns with the cross-regime synthesis already
documented:
- **Bull** sub-regime detector uses `nifty_200d_return × breadth`
- **Bear** sub-regime detector uses `vol × nifty_60d_return`
- **Choppy** (proposed) sub-regime detector: `vol × breadth × nifty_20d_return`

Each regime uses **2 momentum-related axes** + 1 distinct axis (Bull:
breadth; Bear: vol; Choppy: vol AND breadth). The current Choppy
detector under-uses momentum compared to the other regimes.

---

## D. New detector spec (recommended for production integration)

```python
def detect_choppy_subregime(
    nifty_vol_regime: str,           # Low / Medium / High
    market_breadth_pct: float,        # continuous → tertile bucket
    nifty_20d_return_pct: float,      # continuous → tertile bucket
):
    breadth_tertiles = [0.456, 0.597]
    mom_tertiles = [-0.0132, 0.0072]

    breadth = (
        "low" if market_breadth_pct <= breadth_tertiles[0]
        else "high" if market_breadth_pct >= breadth_tertiles[1]
        else "medium"
    )
    mom = (
        "falling" if nifty_20d_return_pct <= mom_tertiles[0]
        else "rising" if nifty_20d_return_pct >= mom_tertiles[1]
        else "flat"
    )
    return f"{nifty_vol_regime.lower()}_{breadth}_{mom}"
```

Output is one of 27 sub-regime cells (3 × 3 × 3). Top WR cells
(high_med_flat 64%, high_low_rising 62%, med_high_rising 61%) become
TAKE_FULL candidates. Bottom cells (med_high_flat 42%, med_low_flat 39%)
become SKIP.

---

## E. Production integration approach

**Pre-activation work:**
1. Add `nifty_20d_return_pct` feature to production scanner data
   pipeline (likely already computable from existing data — just need
   to surface as enrichment field).
2. Compute and persist tertile thresholds (-1.32% / +0.72%) — these
   should be lifetime-derived, not rolling.
3. Update Choppy sub-regime detector function to 3-axis version.
4. Re-stratify all 3 Choppy cells (UP_TRI / DOWN_TRI / BULL_PROXY)
   on new sub-regime cells; identify TAKE_FULL / TAKE_SMALL / SKIP
   cells per signal type.

**Note:** This is the same upstream work as Bull's Gap 2 (sub-regime
detector integration). Bundling Choppy + Bull sub-regime detector
shipment makes sense as a single architectural delivery.

**Risk:** 27 sub-regime cells × 3 signal types = 81 cell × signal
combinations to validate. Many will have small lifetime n. Production
should use a fallback: if cell × signal n < 200, defer to 2-axis
(vol × breadth) verdict.

---

## F. Caveats

1. **Feature-engineering dependency.** Production must compute
   `nifty_20d_return_pct` daily — this is a NIFTY-level feature, not
   per-stock. Already available in NIFTY data; just needs surfacing.

2. **Tertile thresholds are lifetime-fitted.** -1.32% / +0.72% are
   tertile boundaries from lifetime data; these may not generalize
   if future Choppy market structure shifts. Alternative: rolling
   12-month tertile recomputation.

3. **Doesn't address C2 (breadth threshold) or C3 (whipsaw)** — those
   are separate critique sub-blocks.

4. **3 of 9 cells show inverted momentum behavior** (rising = anti
   in Low×low; falling = winner in Medium×medium). Production must
   apply per-cell rules, not a universal "rising = good" heuristic.

---

## G. Verdict

**RESOLVED with action.** Momentum produces meaningful WR variance
(11.8pp avg, well above 5pp threshold). ADD `nifty_20d_return_pct`
as 3rd axis to Choppy sub-regime detector.

| Decision criterion | Result |
|---|---|
| Within-cell WR variance | 11.8pp avg (>5pp threshold) |
| Cell coverage | 6 of 9 cells >9pp variance |
| Best alternative momentum feature | nifty_20d_return_pct (vs ROC_10 10.0pp, MACD 6.1pp, ema50_slope 4.3pp) |
| Detector span improvement | 13.3pp → 27.1pp (2x discriminating power) |

**Action:** ADD momentum to Choppy sub-regime detector. Spec drafted
in section D. Production integration bundles with Bull Gap 2.

**Pre-activation work item:** **Add to A1 priority list as MEDIUM-HIGH:**
"Choppy sub-regime detector V2 (add nifty_20d_return_pct as 3rd axis;
27-cell tri-modal classification)."

This is a NEW gap not surfaced in A1 audit. A1 listed Choppy as
working with current vol × breadth detector; C1 reveals that detector
is under-powered.
