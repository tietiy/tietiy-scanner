# Bull UP_TRI Cell — COMPLETE (PROVISIONAL)

**Status:** ✅ COMPLETE at PROVISIONAL_OFF (Session 1 of 1).
**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** 4 atomic commits across BU1-BU4

This document is the cross-session summary of the Bull UP_TRI cell
investigation — the first Bull regime cell, conducted with adapted
lifetime-only methodology (no live Bull data exists in current
trading window).

---

## Cell scope and outcome

| Metric | Value |
|---|---|
| Cell signal × regime | UP_TRI × Bull |
| Live signals | **0** (Bull regime not classified live during current period) |
| Lifetime signals | 38,100 (LARGEST single-cell cohort in Lab) |
| Lifetime baseline WR | 52.0% |
| Sub-regime structure | tri-modal: recovery / healthy / normal / late |
| Best sub-regime cell | recovery_bull (60.2% WR on n=972) |
| Best filter (sub-regime + filter) | recovery_bull + vol=Med + fvg_low → 74.1% WR (n=390) |
| Confidence (lifetime-validated) | MEDIUM (robust lifetime; no live validation) |
| Production posture | **PROVISIONAL_OFF default** |

---

## Methodology applied (lifetime-only adaptation)

The validated 5-step factory methodology was adapted for this cell:

| Step | Standard | Bull UP_TRI adaptation |
|---|---|---|
| 1. Live cell investigation | extract / differentiators / filter_test / playbook | **SKIPPED** (no live data) |
| 2. Lifetime validation | Test live findings at scale | **SKIPPED** (no live findings to validate) |
| 3. Comprehensive lifetime search | 2-feat + 3-feat combinatorial | ✓ BU3 |
| 4. Sub-regime stratification | sector × calendar × vol | ✓ BU2 + BU3 |
| 5. Synthesis + sub-regime gating | detector + production posture | ✓ BU1 (detector) + BU4 (playbook) |

This collapses to a **3-step lifetime-only methodology**:
- BU1: extract + sub-regime detector + axis discovery
- BU2: stratification + cross-cell prediction tests
- BU3: comprehensive feature search
- BU4: PROVISIONAL playbook + cross-regime synthesis

This is the reference template for **lifetime-only cell methodology**
when live data is absent — applies to future Bull cells (DOWN_TRI,
BULL_PROXY) and any cell where live signals don't exist.

---

## Findings hierarchy

### Architectural insights (top-level — apply to all Bull cells + future regimes)

1. **Bull is genuinely architecturally distinct from Bear UP_TRI.**
   0/3 Bear UP_TRI top patterns qualify in Bull. Each cell needs its
   own filter design. Cross-cell inheritance does not work even within
   the same signal type across regimes.

2. **Sub-regime meta-pattern HOLDS but with bucket-size variance.**
   Bull tri-modal with 76% normal + 23% edges (skewed). Bear tri-modal
   with 60% normal + 40% edges (distributed). Choppy similar to Bull.
   Universal: "two discriminative tails exist; bulk is baseline."

3. **Per-regime sub-regime axes are correct.** Bull's best axes
   (`nifty_200d_return × market_breadth`) differ from Bear's
   (`vol_percentile × nifty_60d_return`) and Choppy's
   (`vol_percentile × market_breadth`). The "primary axis = regime
   definition" meta-pattern from Bear synthesis is confirmed.

4. **Direction-flip prediction CONFIRMED in Bull regime.** UP_TRI vs
   DOWN_TRI inversion on the regime anchor (200d_return) holds. Bull
   UP_TRI: -2.1pp on high 200d; Bull DOWN_TRI: +1.5pp on high 200d.
   This pattern is now confirmed in 2 of 3 regimes (Bear, Bull).

5. **Sub-regime detector axis discovery methodology validated.** When
   predicted axes don't work cleanly, testing 4 candidate axis pairs
   identifies the actual best discriminator. Use lifetime WR span as
   selection metric. predicted_v2 (200d × breadth) won at 15.1pp span;
   predicted_v1 (multi_tf × breadth) was 12.7pp.

### Cell-specific findings (apply to Bull UP_TRI production only)

#### Sub-regime structure

| Sub-regime | Definition | n | % | WR |
|---|---|---|---|---|
| **recovery_bull** ★ | low 200d AND low breadth | 972 | 2.6% | 60.2% (+8.2pp) |
| **healthy_bull** | mid 200d AND high breadth | 4,764 | 12.5% | 58.4% (+6.3pp) |
| normal_bull | (everything else) | 29,110 | 76.4% | 51.3% |
| **late_bull** | mid 200d AND low breadth | 2,699 | 7.1% | 45.1% (−6.9pp) |

#### Top winner features (lifetime, n=38,100)

Universal anchor (full Bull): `nifty_20d_return_pct=high` (+5.5 to
+7.8pp lift across multiple combos)

Within recovery_bull (sub-regime baseline 60.2%):
- `vol=Medium AND fvg_unfilled_above_count=low`: 74.1% WR (+13.9pp)
- `vol=Medium AND nifty_20d_return=medium`: 72.8% WR (+12.6pp)

Within healthy_bull (sub-regime baseline 58.4%):
- `RSI=medium AND wk4`: 68.1% WR (+9.8pp)
- `wk4 AND swing_high_count_20d=low`: 65.2% WR (+6.8pp)

#### Hard SKIPs (universal)

- late_bull sub-regime → 45.1% topping risk
- nifty_vol_regime=High → -2.0pp anti (Bull is stable regime)
- Sector = Energy → -2.9pp lifetime
- Month = September → -8.4pp catastrophic
- Week = wk3 → -3.3pp

---

## Comparison to Bear UP_TRI cell

| Property | Bear UP_TRI | Bull UP_TRI |
|---|---|---|
| Lifetime n | 15,151 | 38,100 |
| Live n | 74 (94.6% WR) | 0 |
| Lifetime baseline | 55.7% | 52.0% |
| Live-vs-lifetime gap | +38.9pp (live inflated) | n/a (no live) |
| Sub-regime axes | vol × 60d_return | 200d × breadth |
| Sub-regime structure | hot/warm/cold (~20%/?%/?%) | recovery/healthy/normal/late (2.6%/12.5%/76.4%/7.1%) |
| Best sub-regime | hot 68.3% WR (n=2,275) | recovery 60.2% WR (n=972) |
| Best filter | wk4 × swing_high=low: 63.3% on 3,374 | recovery + vol=Med + fvg=low: 74.1% on 390 |
| Primary anchor | 60d_return=low (oversold) | 20d_return=high (recent strength) |
| Inside_bar | True (compression, +4.9pp) | NEUTRAL (no preference) |
| Sector top | CapGoods, Auto, Other (defensive industrial) | IT, Health, Consumer (growth/quality) |
| Confidence | HIGH (live + lifetime) | MEDIUM (lifetime only) |
| Production | Shadow-deployment-ready | PROVISIONAL_OFF |

**Key difference:** Bull's best filter cell is **higher precision but
narrower sample** than Bear UP_TRI's. Bear UP_TRI's hot sub-regime is
~15% of lifetime; Bull's recovery_bull is only 2.6%. Production will
get fewer high-confidence Bull signals per regime period.

---

## What's deferred or pending

### Within Bull UP_TRI cell

- **Live validation** — entirely pending. Needs Bull regime to return
  + ≥30 live Bull UP_TRI signals before activation possible.
- **Recovery_bull cell sample size validation** — n=972 lifetime is
  meaningful but the +13.9pp lift on the n=390 best subset is from a
  small sample. Quarterly Phase-5 re-runs as Bull regime returns
  should populate.
- **Phase-5 selection bias check** — Bear UP_TRI/BULL_PROXY showed
  +25-30pp Phase-5 inflation. Will Bull show same pattern? Cannot
  test until Bull regime + Phase 5 produce winners.

### Bull regime broader

- **Bull DOWN_TRI cell** — apply 5-step methodology (lifetime-only
  adaptation). Direction-flip prediction CONFIRMED at high level
  (200d_return inverts). Cell investigation should refine.
- **Bull BULL_PROXY cell** — apply 5-step methodology. Predicted to
  show similar mechanism to Bull UP_TRI but with different filter
  anchor (likely sector momentum dispersion).
- **Bull regime synthesis** — once all 3 cells complete (or DEFERRED),
  build cross-cell consolidation similar to Bear synthesis.

### Architectural

- **Cross-regime universal patterns** — only consistent finding so
  far is wk4 calendar effect (Bear +7.5pp, Bull +2.6pp, Choppy
  unclear). Worth dedicated investigation.
- **Phase-5-equivalent in lifetime** — when no live data exists, what
  is the methodological equivalent of Phase-5 selection bias check?
  Currently no answer.

---

## Lessons for Bull DOWN_TRI cell (next session)

When investigating Bull DOWN_TRI:

1. **Apply lifetime-only methodology** (3-step adaptation validated
   here).

2. **Expect lifetime baseline ~43.4%** (already confirmed in BU2 H2
   test). Below 50% — DOWN_TRI is contrarian short in Bull regime.

3. **Direction-flip predicts:** primary anchor for Bull DOWN_TRI
   should INVERT Bull UP_TRI's:
   - Bull UP_TRI anchor: `nifty_20d_return_pct=high`
   - Bull DOWN_TRI anchor (predicted): `nifty_20d_return_pct=low` or
     `200d_return=high` (per H2 confirmation: high 200d helps Bull
     DOWN_TRI)

4. **Expected outcome:** likely DEFERRED or KILL given baseline 43.4%
   suggests structural weakness. Bear DOWN_TRI was DEFERRED for the
   same reason (live worse than lifetime, baseline 46.1%).

5. **Bull sub-regime detector reuses cleanly** for Bull DOWN_TRI
   (same regime, same market state classification).

---

## File outputs

| File | Purpose |
|---|---|
| `lab/factory/bull_uptri/extract.py` + `data_summary.json` | BU1a: lifetime extraction |
| `lab/factory/bull/subregime/detector.py` + `detector.json` | BU1b: tri-modal Bull detector |
| `lab/factory/bull/subregime/axis_discovery.json` | BU1: 4-config axis comparison |
| `lab/factory/bull/subregime/meta_pattern_verdict.md` | BU1 LLM cross-regime meta-pattern analysis |
| `lab/factory/bull_uptri/lifetime/stratification.py` + `stratification.json` | BU2: cross-cell prediction tests |
| `lab/factory/bull_uptri/lifetime/stratification_llm.md` | BU2 LLM architectural analysis |
| `lab/factory/bull_uptri/lifetime/comprehensive_search.py` + outputs | BU3: 2-feat + 3-feat search |
| `lab/factory/bull_uptri/playbook.md` | BU4: PROVISIONAL_OFF playbook |
| `lab/factory/bull_uptri/CELL_COMPLETE.md` | BU4: This document |

---

## Summary

Bull UP_TRI cell is **complete at PROVISIONAL_OFF** with lifetime-only
methodology. Cross-regime meta-pattern PARTIAL CONFIRMED with revised
interpretation. Bull is architecturally distinct from Bear UP_TRI:
different sub-regime axes, different filter anchors, different sector
preferences, different sub-regime structure (skewed not distributed).

The cell's best lifetime configuration (`recovery_bull` + `vol=Medium`
+ `fvg_unfilled_above_count=low`) shows 74.1% WR on n=390 — the
**highest-WR Bull UP_TRI configuration in lifetime data**. But this is
a narrow cell (1% of total lifetime signals).

Production posture: **PROVISIONAL_OFF default** until Bull regime
returns. Activation requires ≥30 live Bull signals with provisional
filter match-WR ≥ 50%.

**Next session:** Bull DOWN_TRI cell (Session 1 of 1, lifetime-only).
Apply same 3-step adaptation. Expect DEFERRED outcome given lifetime
baseline 43.4%.
