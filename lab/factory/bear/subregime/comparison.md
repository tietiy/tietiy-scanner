# Bear vs Choppy Sub-Regime Detector — Cross-Cell Architecture Comparison

**Date:** 2026-05-02
**Scope:** Compare the Bear sub-regime detector (S2) with the Choppy
sub-regime detector (T1) and surface architectural patterns.
**Authoritative companions:**
[Choppy detector design](../../choppy/subregime/detector_design.md) and
[Bear detector module](detector.py).

---

## Detector specs side-by-side

| Property | Choppy (T1) | Bear (S2) |
|---|---|---|
| Investigation date | 2026-05-02 | 2026-05-02 |
| Structure | **tri-modal** | **bimodal** |
| Sub-regimes | quiet / balance / stress | hot / cold |
| Primary axis | `nifty_vol_percentile_20d` | `nifty_vol_percentile_20d` |
| Secondary axis | `market_breadth_pct` | `nifty_60d_return_pct` |
| Subtype dim | breadth qualifier (low/med/high) | (none) |
| Thresholds | < 0.30 quiet, > 0.70 stress | > 0.70 AND < −0.10 hot |
| Lifetime classification agreement | 100% (same as categorical) | 100% (perfect L1 reproduction) |

**Key shared property:** Both detectors use `nifty_vol_percentile_20d` as
their primary axis, but with different threshold interpretations:
- Choppy partitions volatility into 3 zones (quiet / balance / stress)
- Bear collapses to 2 zones (hot if vol > 0.70 AND 60d_return < −0.10)

**Different secondary axes:** Choppy uses cross-sectional breadth; Bear
uses longitudinal 60-day return. This is the **architectural distinction**
between regimes — different secondary axes capture different regime
mechanics.

---

## Why the axes differ per regime

### Choppy regime mechanics → breadth-secondary

In Choppy regime (oscillating, range-bound markets), the question is
**how broadly is the universe participating in moves?** Cross-sectional
breadth (`market_breadth_pct`) discriminates:
- High breadth in Choppy = synchronized churn (failed continuation)
- Medium breadth in stress = selective stress (institutional buying
  while retail is cautious — the L3 winning combo)
- Low breadth = panic capitulation

Secondary axis is a **synchronicity** measure.

### Bear regime mechanics → 60d-return-secondary

In Bear regime (sustained downtrend), the question is **how deep into
drawdown are we?** Longitudinal 60-day return discriminates:
- Sustained negative (< −10%) + high vol = late-stage capitulation
  (the "hot" cell — 68.3% WR; the +14.9pp lift sub-regime)
- Shallow negative or recovering = transitional / mid-Bear
  (the "cold" cell — 53.4% WR)

Secondary axis is a **depth-of-drawdown** measure.

### Why these aren't the same axis

Bear's `nifty_60d_return_pct` does NOT discriminate Choppy edges;
Choppy's `market_breadth_pct` doesn't define Bear hot/cold cells.

This was tested in Session 2:
- L3 search for Bear surfaced patterns anchored on `wk4 × swing_high=low`
  and `breadth=low × ema50=low × swing_high=low`
- But these are **internal-cold patterns**, not the hot/cold gate itself
- The hot/cold gate IS the structural division, and it requires
  longitudinal context (60d return) that breadth doesn't provide.

---

## Architectural pattern (proposed)

### Universal primary, regime-specific secondary

| Regime | Primary axis | Secondary axis | Structure |
|---|---|---|---|
| Choppy | vol_percentile | breadth (synchronicity) | tri-modal |
| Bear | vol_percentile | 60d_return (depth) | bimodal |
| Bull (future) | vol_percentile | sector momentum or 60d_return positive | bimodal? |

**Hypothesis:** vol_percentile is the universal primary axis across
regimes (high vol = stress, low vol = quiet), but the secondary axis
captures regime-specific edge. The number of sub-regime cells (2 or 3)
is determined by how many distinct edge regions exist in the
secondary-axis space.

### Why bimodal in Bear vs tri-modal in Choppy?

**Choppy is tri-modal** because Choppy contains genuinely 3 distinct
market characters:
- Quiet (low vol = no oscillation; rare; transitional)
- Balance (med vol = mid-Choppy; the hostile bucket)
- Stress (high vol = volatile Choppy; the favorable F1 cohort)

**Bear is bimodal** because Bear's "quiet" sub-regime is essentially
absent (1% of lifetime — quiet markets don't generate Bear setups; if
vol is genuinely low, the market is recovering or never was Bear).
Bear collapses to: hot (capitulation) and cold (everything else).

### Implications for Bull regime

If the universal primary stays vol_percentile, what is Bull's secondary
axis? Hypotheses:
1. **`nifty_60d_return_pct=high` (positive)** — symmetric to Bear's
   negative-deep gate; identifies "hot Bull" as accelerating uptrend
2. **Sector momentum dispersion** — Bull may need cross-sectional info
   like Choppy did
3. **Volatility-of-volatility** — Bull "hot" may be smooth-trend-low-vol
   rather than vol-extreme

These are speculative; will validate when Bull live data accumulates.

---

## Live data classification — surprise finding from S2

The Bear detector classifies April 2026 live Bear UP_TRI signals as:
- **Hot: 32 signals (43.2%)** — fired 2026-04-01 / 04-06 / 04-07
- **Cold: 42 signals (56.8%)** — fired 2026-04-09 / 04-10

This contradicts Session 2's assumption that "all 74 live signals are in
hot sub-regime". The reality is more nuanced:

### What actually happened

The 42 "cold" signals are **borderline cold** — they fail the hot gate
because `nifty_60d_return_pct` is between −0.071 and −0.090, JUST above
the −0.10 threshold. Vol_percentile is 0.971-0.972 (clearly hot), but
60d return had recovered slightly by April 9-10.

### What the data shows (live cold subset, n=42)

| Metric | Value |
|---|---|
| n | 42 |
| W / L / F | 40 / 2 / 0 |
| Live WR | **95.2%** |
| Cold cascade Tier 1 matches | **0 of 42** |
| Cold cascade SKIP | 42 of 42 (95.2% WR) |

**The cold cascade Tier 1 captures 0 of the 42 live cold signals**, yet
95.2% of them won. The cold cascade predicts these should be at ~53%
WR, but they're at 95%.

### Implications for the detector

1. **The hot threshold is brittle.** A small change in `nifty_60d_return`
   (from −0.09 to −0.11) flips classification. The 42 borderline-cold
   signals behave like hot signals at lifetime would, except even better.

2. **There's a "warm" sub-regime not captured.** Hot/cold is too binary.
   A "warm" zone might be: vol > 0.70 AND −0.10 ≤ 60d_return ≤ 0
   (high vol, mild drawdown). This zone is NOT in lifetime cold's 53.4%
   profile — it's behaving more like hot.

3. **Phase-5 selection bias is enormous.** The 42 cold signals were
   Phase-5 winners; their ability to print 95% in a "borderline" sub-
   regime confirms the +26.3pp residual gap from L2 is largely
   selection-driven, not sub-regime-driven.

4. **Production posture needs to NOT use the cold cascade in borderline-
   cold conditions.** The cascade is calibrated to lifetime cold (53.4%
   baseline) but live borderline-cold is operating at 95% — applying the
   cascade SKIP rule would have skipped 42 wins.

### Recommended update to Bear detector

Add a third "warm" classification:
```
hot   : vol > 0.70 AND 60d_return < -0.10
warm  : vol > 0.70 AND -0.10 ≤ 60d_return ≤ 0     ← NEW
cold  : vol ≤ 0.70 OR 60d_return > 0
```

In warm zone, default to TAKE_FULL (matching live evidence). At lifetime
scale this needs validation — quarterly Phase 5 re-run will populate.

---

## Confidence scoring

Both detectors output a 0-100 confidence score, but the calibration is
**geometric, not statistical**:
- Choppy: distance from 0.30 / 0.70 boundary, normalized
- Bear: minimum of (vol distance, return distance) past hot boundaries

Neither is a "probability of correct sub-regime classification" in a
calibrated sense. Future enhancement: fit logistic models predicting WR
from features and use predicted-WR as confidence.

---

## Production deployment notes

### Where each detector runs

Both detectors are **per-day-once** functions. They take universe-level
features (NIFTY vol, 60d return, market breadth) and emit a label for
the trading day. The label is shared across all signals fired that day.

### Output format

`output/current_subregime.json`:
```json
{
  "scan_date": "2026-05-02",
  "regime": "Bear",
  "subregime": "hot",
  "vol_percentile": 0.825,
  "nifty_60d_return": -0.142,
  "expected_wr_range": "68-95%",
  "filter_recommendation": "TAKE_FULL"
}
```

### Integration with bridge composer

The pre_market composer (8:55 IST) computes the day's sub-regime label
once, before per-signal feature joining. Bear UP_TRI signals during the
day inherit the label via state.

### Failure modes

| Failure | Handling |
|---|---|
| Vol percentile or 60d return missing | label = "unknown"; default to most conservative posture (cold cascade) |
| Vol_percentile exactly 0.70 | strict `>` comparison → cold (boundary case favors safety) |
| 60d_return between −0.10 and 0 (warm zone) | currently labeled "cold" but per S2 finding deserves "warm" (TAKE_FULL) — pending v2 detector |

---

## Final architectural recommendations

1. **Per-regime sub-regime detectors are the right design** (vs single
   universal detector). Each regime's edge mechanics differ; the
   secondary axes need to be regime-specific.

2. **Vol_percentile as universal primary** appears to work. Adopt for
   future Bull / Bear DOWN_TRI / BULL_PROXY cells unless evidence
   contradicts.

3. **Bear detector v2 should add "warm" zone** based on S2 surprise.
   Defer to quarterly re-validation; do not deploy v2 until lifetime
   data supports the warm zone (currently warm zone is single-window
   April 2026 evidence only).

4. **Production posture should respect detector confidence.** Low-
   confidence borderline classifications (close to threshold) should
   either default to most conservative (SKIP) or surface as
   "uncertain" for trader review.

5. **Phase-5 selection bias is large enough to warrant separate
   tracking.** When detector says "cold" but signal is Phase-5
   validated, the WR floor may be much higher than lifetime cold
   baseline suggests.
