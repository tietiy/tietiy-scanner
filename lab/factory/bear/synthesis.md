# Bear Regime Synthesis — Cross-Cell Consolidation

**Status:** Bear regime cell investigation complete (3 of 3 cells).
**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Scope:** Consolidate findings from Bear UP_TRI, Bear DOWN_TRI, and
Bear BULL_PROXY cells into unified Bear regime understanding.

---

## A. Cell summary

| Cell | Status | Confidence | Sessions | Production verdict |
|---|---|---|---|---|
| **Bear UP_TRI** | ✅ COMPLETE | HIGH (lifetime-validated) | 3 | Sub-regime gated; shadow-deployment-ready |
| **Bear DOWN_TRI** | DEFERRED | LOW | 1 | kill_001 (Bank) + provisional wk2/wk3 timing filter |
| **Bear BULL_PROXY** | DEFERRED | LOW | 1 | Provisional HOT-only filter (manual enable; default SKIP) |

**Headline:** 1 of 3 Bear cells reached HIGH confidence. The two DEFERRED
cells lack Phase 5 winners (DOWN_TRI: 0 V/P, all 19 WATCH; BULL_PROXY:
0 combinations at all) — standard winners-vs-rejected differentiator
analysis was not feasible. Both fell back to lifetime-only methodology.

---

## B. Cross-cell feature behavior matrix

The single most important finding from this synthesis: **the same feature
predicts opposite outcomes across cells**, and the pattern is
mechanistically explainable.

### Feature × cell direction matrix

| Feature / level | Bear UP_TRI | Bear DOWN_TRI | Bear BULL_PROXY | Pattern |
|---|---|---|---|---|
| `nifty_60d_return_pct=low` | **+14.1pp** | **−4.1pp** | **+17.9pp** | Bullish setups share anchor; bearish inverts |
| `day_of_month_bucket=wk4` | **+7.5pp** | **−17.5pp** | +2.3pp (mild) | Bullish setups prefer wk4; bearish prefers wk2 |
| `day_of_month_bucket=wk2` | −6.4pp | **+15.0pp** | −5.5pp | Mirror inversion of wk4 |
| `inside_bar_flag=True` | **+4.9pp** (compression) | n/a | **−9.4pp** (range expansion needed) | Same regime, both bullish, OPPOSITE preferences |
| `vol_climax_flag=True` | n/a | n/a | **−11.0pp** | Capitulation kills BULL_PROXY (breaks support) |
| `nifty_vol_regime=High` | +2.1pp (sub-regime) | weak +2.1pp | +5.1pp | Hot vol favors all 3 cells; magnitude varies |
| `nifty_vol_regime=Low` | (within stress only) | n/a | **+7.9pp** | BULL_PROXY's U-shaped vol response (Low + High both win) |
| `52w_high_distance_pct=high` | +6.6pp (top-10 winner) | n/a | **+14.4pp** | Both bullish setups want stocks near 52w lows |
| `swing_high_count_20d=low` | **+23.3pp** (#1 winner) | n/a | weak | UP_TRI-specific: low overhead resistance for breakout |
| `higher_highs_intact_flag=True` | weak | **+4.0pp** | n/a | DOWN_TRI: HHs + descending triangle = distribution top |

### Patterns observable in the matrix

1. **Bullish anchor universal**: `nifty_60d_return_pct=low` is the strongest
   winner anchor for both bullish cells (UP_TRI +14.1pp, BULL_PROXY +17.9pp).
   Bearish DOWN_TRI inverts (−4.1pp).

2. **Calendar inversion is real and clean**: Bullish setups (UP_TRI,
   BULL_PROXY) prefer wk4. Bearish DOWN_TRI prefers wk2 with wk4 strongly
   anti. Mechanism: month-end institutional rebalancing creates buy-side
   pressure (helps bullish; hurts bearish continuation).

3. **Same-feature direction-flips between bullish cells**: UP_TRI loves
   `inside_bar=True` (compression coil); BULL_PROXY hates it (needs range
   expansion for reversal candle). Cells should NOT share filter logic
   on inside_bar despite shared bullish direction.

4. **Setup-specific anti-features**: BULL_PROXY's `vol_climax=True` anti
   (−11.0pp) doesn't appear in UP_TRI. Capitulation breaks support
   (kills BULL_PROXY) but doesn't damage triangle structure (neutral
   for UP_TRI).

---

## C. Architectural patterns identified

### Pattern 1: Bullish vs bearish direction is the primary divider

The largest behavioral splits in the matrix track signal direction
(long vs short), not specific signal type. Bear UP_TRI and Bear
BULL_PROXY share more feature signatures with each other than either
shares with Bear DOWN_TRI.

This means production decision logic should branch first on direction,
then on signal-type-specific filters.

### Pattern 2: Within bullish, mechanism divides the cells

UP_TRI is breakout from compression (loves `inside_bar=True`,
`swing_high_count_20d=low`, `range_compression_60d=high`).

BULL_PROXY is reversal from range expansion (loves
`inside_bar=False`, `52w_high_distance=high`, `vol_climax=False`).

Both bullish; both fire in Bear regime; but **mechanically different**.
Filters should not be shared.

### Pattern 3: Calendar inversion across direction

| Direction | wk2 | wk4 |
|---|---|---|
| Bullish (UP_TRI, BULL_PROXY) | anti | preferred |
| Bearish (DOWN_TRI) | preferred | anti |

Mechanism (per Sonnet 4.5 in earlier sessions): month-end institutional
rebalancing creates buy-side pressure that helps bullish setups and
hurts bearish continuation. Mid-month flow is the opposite.

### Pattern 4: Hot Bear sub-regime favors LONG positions universally

| Cell | Hot lifetime WR | Cold lifetime WR | Δ |
|---|---|---|---|
| Bear UP_TRI | 68.3% (n=2275) | 53.4% (n=12876) | +14.9pp |
| Bear BULL_PROXY | 63.7% (n=86) | 45.5% (n=805) | +18.2pp |
| Bear DOWN_TRI | 47.0% (n=556) | 45.7% (n=3084) | +1.3pp (no edge) |

Hot Bear (high vol + deep 60d drawdown) is the favorable sub-regime
for bullish setups. DOWN_TRI doesn't get a sub-regime lift — descending
triangles in capitulation often get squeezed by short-cover bounces.

### Pattern 5: vol_climax kills BULL_PROXY but not UP_TRI

Capitulation events break the support structure that BULL_PROXY's
reversal mechanism depends on. UP_TRI's compression triangle is more
robust to vol spikes (the triangle itself absorbs the volatility
without breaking).

This is a clean architectural finding for Bull regime BULL_PROXY work
later: expect vol_climax to remain anti for BULL_PROXY across regimes.

---

## D. Sub-regime distribution across cells

Bear regime sub-regime structure (from Bear UP_TRI Session 2 detector):

```
Bear sub-regime: TRI-modal (proposed for UP_TRI per S2 critique)
  hot:  vol_percentile > 0.70 AND nifty_60d_return < -0.10
        ~15% of lifetime in Bear UP_TRI
        ~9.7% of lifetime in Bear BULL_PROXY
        Highest WR in both bullish cells

  warm: vol > 0.70 AND -0.10 ≤ nifty_60d_return < 0
        Discovered in Bear UP_TRI S2 (live April 2026 data)
        Lifetime cohort untested (need quarterly Phase-5 re-runs)
        Live evidence: behaves like hot

  cold: vol ≤ 0.70 OR nifty_60d_return ≥ 0
        ~85% of lifetime
        Low edge for bullish; near-baseline for bearish
```

**Bear DOWN_TRI does NOT follow the same sub-regime axes.** Its winner
features are calendar-driven (wk2/wk3) not vol/return-driven. The
detector reuse from UP_TRI doesn't help DOWN_TRI. Different mechanism;
different sub-regime structure.

---

## E. Live-vs-lifetime gap pattern

| Cell | Live WR | Lifetime WR | Gap | Direction |
|---|---|---|---|---|
| Bear UP_TRI | 94.6% (n=74) | 55.7% (n=15151) | **+38.9pp** | Inflated |
| Bear BULL_PROXY | 84.6% (n=13) | 47.3% (n=891) | **+37.3pp** | Inflated |
| Bear DOWN_TRI | 18.2% (n=11) | 46.1% (n=3640) | **−28.0pp** | Deflated |

### Decomposition (Bear UP_TRI — most thoroughly investigated)

Live 94.6% = lifetime 55.7% baseline + 12.6pp hot sub-regime structure
+ 26.3pp Phase 5 selection bias

The +26.3pp Phase 5 selection bias is significant — it represents the
system's pattern-validation pipeline cherry-picking high-quality
patterns. This bias is NOT reproducible in production (cell deploys to
unfiltered live signals).

### Pattern across cells

- **Bullish cells inflate above lifetime** (Phase 5 selection bias +
  current sub-regime tailwind).
- **Bearish cells deflate below lifetime** (no Phase 5 winners means
  no selection bias to inflate; current sub-regime is hostile to
  short setups in transitional Bear).

This pattern is consistent across all 3 cells investigated. Future
cells should expect:
- Phase 5 winners → inflated live (Bear UP_TRI / BULL_PROXY pattern)
- 0 Phase 5 winners → deflated live (Bear DOWN_TRI pattern)

---

## F. Methodology lessons surfaced from Bear regime

### Lesson 1: Phase 5 thinness limits methodology

Standard 5-step methodology (validated through Bear UP_TRI's 3 sessions)
requires Phase 5 winners to drive winners-vs-rejected differentiator
analysis. When Phase 5 produces 0 winners (Bear DOWN_TRI) or 0 combos
(Bear BULL_PROXY), the methodology stalls at Step 1.

**Fallback:** lifetime-only differentiator analysis on enriched_signals
parquet. Less powerful than winners-vs-rejected but still meaningful.

### Lesson 2: Cross-cell synthesis surfaces patterns single cells can't see

Bear UP_TRI's `wk4` winner is just a calendar effect when viewed alone.
Bear DOWN_TRI's `wk4` anti is also just a calendar effect alone. Together
they reveal the **bullish/bearish direction inversion architectural
pattern** that informs Bull regime preparation.

Future cells should be synthesized at the regime level after individual
cell investigation completes.

### Lesson 3: Sub-regime detector built once is reusable

Bear sub-regime detector (vol > 0.70 AND 60d_return < −0.10) was built
in Bear UP_TRI Session 2. It applied unchanged to Bear BULL_PROXY P1
and reproduced sub-regime structure cleanly (+18.2pp delta). Bear
DOWN_TRI doesn't follow these axes (different mechanism), but the
detector cost was paid once.

For Bull regime work: build Bull sub-regime detector once (predicted
axes per Bear UP_TRI S2 critique: trend_persistence × leadership_
concentration), reuse across all Bull cells.

### Lesson 4: DEFERRED is a valid outcome with provisional filters

Both Bear DOWN_TRI and Bear BULL_PROXY closed at DEFERRED with
provisional filters. This is more useful than KILL (preserves real
lifetime structure) and more honest than FILTER (live data can't
support full validation).

Production posture for DEFERRED cells: default SKIP, manual enable
for provisional filter, preserve optionality without committing
capital.

### Lesson 5: 0 Phase 5 combos is a signal, not noise

Bear BULL_PROXY had literally 0 Phase 5 combinations (worse than
DOWN_TRI's 19 WATCH). This suggests Phase 4 walk-forward filtering
became progressively hostile to BULL_PROXY × Bear cohort. Worth
investigating whether Phase 4 selection criteria can be adjusted to
include more BULL_PROXY combinations in future runs.

---

## G. Sonnet 4.5 cross-cell architectural analysis

See [`bear/synthesis_llm_analysis.md`](synthesis_llm_analysis.md) for
the full cross-cell architectural critique generated by Sonnet 4.5
during BS1.

---

## Decision flow

See [`bear/decision_flow.md`](decision_flow.md) for the full unified
production decision flow with sub-regime gating, KILL rules, and
calibrated WR expectations per signal-type × sub-regime.

---

## Update Log

- **v1 (2026-05-02 night, BS1):** Initial cross-cell consolidation.
  3 Bear cells investigated; 1 HIGH confidence + 2 DEFERRED.
  Architectural patterns identified: bullish/bearish direction is
  primary divider; calendar inversion across direction; sub-regime
  detector reusable for bullish cells; Phase 5 thinness limits
  methodology for 2 of 3 cells.
