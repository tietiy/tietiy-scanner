# Bull Regime Cell Trio — Preview for Synthesis

**Status:** All 3 Bull regime cells investigated (PROVISIONAL methodology).
**Date:** 2026-05-03
**Cells:**
- Bull UP_TRI: PROVISIONAL_OFF (commit `5d6c5506`)
- Bull DOWN_TRI: PROVISIONAL_OFF (commit `f819c9cf`)
- Bull BULL_PROXY: PROVISIONAL_OFF (commit `4dc7b1a0`)

This document previews findings for the upcoming Bull regime synthesis
session. It is structured to mirror the Bear synthesis (BS1-BS3) layout
that will follow.

---

## A. Cell summary table (Bull regime)

| Cell | Status | Confidence | Sessions | Provisional filter | Filter WR / lift |
|---|---|---|---|---|---|
| Bull UP_TRI | PROVISIONAL_OFF | MEDIUM | 1 | `recovery_bull × vol=Med × fvg_low` | 74.1% / +22pp (n=390) |
| Bull DOWN_TRI | PROVISIONAL_OFF | LOW | 1 | `late_bull × wk3` | 65.2% / +21.8pp (n=253) |
| Bull BULL_PROXY | PROVISIONAL_OFF | LOW | 1 | `healthy_bull × 20d=high` | 62.5% / +11.4pp (n=128) |

All 3 Bull cells:
- Used **lifetime-only methodology** (no live data exists)
- Are PROVISIONAL_OFF default (manual enable required)
- Have provisional filters with meaningful lifetime evidence
- Await Bull regime return + 30+ live signals for activation

---

## B. Cross-cell feature behavior matrix (Bull regime)

| Feature | UP_TRI | BULL_PROXY | DOWN_TRI | Pattern |
|---|---|---|---|---|
| `nifty_20d_return_pct=high` | +5-8pp WIN | +5.8pp WIN | -1.6pp anti | Bullish cells share anchor; bearish inverts |
| `nifty_200d_return_pct=high` | -2.1pp ANTI | -6.8pp ANTI | +1.5pp mild winner | High 200d = late-cycle = anti for bullish, mild winner for shorts |
| `day_of_month_bucket=wk4` | +2.6pp WIN | **+13.7pp WIN** | -5.6pp ANTI | Calendar inversion confirmed (parallel to Bear) |
| `day_of_month_bucket=wk3` | -3.3pp anti | -10.7pp anti | **+8.4pp WIN** | Mid-month winner for bearish cell |
| `vol_climax_flag=True` | n/a | -4.4pp ANTI | n/a | Universal BULL_PROXY anti (Bear -11.0pp; same direction) |
| `nifty_vol_regime=High` | -2.0pp anti | **+13.1pp WIN** | -3.1pp anti | UNIVERSAL ANTI for non-BULL_PROXY; BULL_PROXY uses high vol |
| `market_breadth_pct=high` | +3.4pp WIN | +3.3pp WIN | n/a | Both bullish Bull cells share breadth=high winner |
| `inside_bar_flag=True` | -0.1pp NEUTRAL | +1.4pp neutral | n/a | Bear's compression preference doesn't transfer to Bull |
| `52w_high_distance=high` | +6.6pp WIN | +0.2pp neutral | n/a | Bear BULL_PROXY +14.4pp; Bull BULL_PROXY INVERTS to prefer NEAR highs |

---

## C. Architectural patterns within Bull regime

### Pattern 1: Direction-flip pattern (UP_TRI vs DOWN_TRI) STRONGLY CONFIRMED

The strongest cross-cell finding in the Bull regime work.

**Sub-regime PERFECT 4-cell inversion:**

| Sub-regime | UP_TRI WR | DOWN_TRI WR |
|---|---|---|
| recovery_bull | 60.2% (best) | 35.7% (worst) |
| healthy_bull | 58.4% | 40.5% |
| normal_bull | 51.3% | 42.6% |
| late_bull | 45.1% (worst) | 53.0% (best) |

**Calendar inversion:**

| Week | UP_TRI lift | DOWN_TRI lift |
|---|---|---|
| wk3 | -3.3pp | +8.4pp |
| wk4 | +2.6pp | -5.6pp |

**Sector inversion:**
- UP_TRI top: IT, Health, Consumer (growth/quality)
- DOWN_TRI top: Metal, Bank (cyclicals/financials)

### Pattern 2: Direction-alignment (UP_TRI vs BULL_PROXY) confirmed

Both bullish Bull cells share architecture:
- Sub-regime preference: recovery > healthy > normal > late
- Anchor: `nifty_20d_return=high`
- Calendar: wk4 winner
- Breadth=high winner

### Pattern 3: BULL_PROXY-specific universal pattern across regimes

`vol_climax_flag=True` is anti for BULL_PROXY in BOTH Bear and Bull.
Different magnitudes (Bear -11pp; Bull -4.4pp) but same direction.
Mechanism: capitulation breaks support that BULL_PROXY's reversal
mechanism depends on.

### Pattern 4: Cross-regime patterns DON'T fully transfer

Bear UP_TRI patterns refuse to qualify in Bull UP_TRI (0 of 3 tested).
Bear BULL_PROXY's `52w_high_distance=high` winner INVERTS to
Bull BULL_PROXY's `52w_high_distance=low` winner. Bear BULL_PROXY's
`inside_bar=False` winner becomes neutral in Bull.

Each cell + regime combination has its own architectural signature
beyond shared anchors. Cross-regime synthesis must respect this.

---

## D. Bull regime sub-regime detector summary

Built in Bull UP_TRI Session 1 (BU1); reused unchanged across
DOWN_TRI and BULL_PROXY:

```python
def detect_bull_subregime(nifty_200d_return_pct, market_breadth_pct):
    """Tri-modal Bull sub-regime."""
    p = nifty_200d_return_pct  # 200d return = trend maturity
    s = market_breadth_pct      # breadth = participation quality

    if p < 0.05:  # low 200d
        if s < 0.60:  # low breadth
            return "recovery_bull"  # early cycle, narrow leadership
    if 0.05 <= p <= 0.20:  # mid 200d
        if s > 0.80:  # high breadth
            return "healthy_bull"   # broad sustained Bull
        if s < 0.60:  # low breadth
            return "late_bull"      # narrowing leadership topping
    return "normal_bull"             # everything else
```

**Distribution across Bull cells:**

| Cell | recovery | healthy | normal | late |
|---|---|---|---|---|
| Bull UP_TRI | 2.6% | 12.5% | 76.4% | 7.1% |
| Bull DOWN_TRI | 3.2% | 11.6% | 73.0% | 10.8% |
| Bull BULL_PROXY | 2.6% | 12.4% | 74.9% | 10.0% |

Distribution is consistent across cells (same regime → same sub-regime
distribution). Detector reuse validated.

---

## E. Lifetime baselines comparison (3 Bull cells)

| Cell | Lifetime baseline | vs Bear cell parallel |
|---|---|---|
| Bull UP_TRI | 52.0% | Bear UP_TRI 55.7% (Bear higher) |
| Bull BULL_PROXY | 51.1% | Bear BULL_PROXY 47.3% (Bull higher) |
| Bull DOWN_TRI | 43.4% | Bear DOWN_TRI 46.1% (Bear higher) |

Pattern: Bullish cells (UP_TRI, BULL_PROXY) have similar baselines
within ~1pp; bearish DOWN_TRI is ~9pp lower. Cross-regime: Bear UP_TRI
+3.7pp above Bull UP_TRI; Bull BULL_PROXY +3.8pp above Bear BULL_PROXY;
Bear DOWN_TRI +2.7pp above Bull DOWN_TRI. No consistent direction.

---

## F. Open items for Bull regime synthesis (next session)

1. **BS1-style cross-cell consolidation document** — formal synthesis
   parallel to Bear BS1.

2. **BS2-style unified Bull decision flow** — production-ready
   pseudo-code that gates by sub-regime + applies cell-specific
   filters per signal type.

3. **BS3-style production posture document** — Bull regime production
   readiness assessment + activation criteria.

4. **Cross-regime synthesis** — the layer above. With Choppy + Bear +
   Bull all investigated, the architectural meta-pattern can be
   finalized:
   - Universal: tri-modal sub-regime structure (with regime-specific
     bucket size variance)
   - Universal: `vol_climax × BULL_PROXY` anti
   - Universal: direction-flip pattern (UP_TRI vs DOWN_TRI inversion)
   - Universal: bullish cell direction-alignment within regime
   - Regime-specific: axes (Choppy vol×breadth, Bear vol×60d, Bull
     200d×breadth)
   - Regime-specific: most filter anchors, sector preferences

5. **Production deployment plan for ALL provisional filters** —
   activation criteria, monitoring, rollback procedures across
   Bear UP_TRI (only HIGH-confidence), Bear DOWN_TRI/BULL_PROXY
   (DEFERRED), all 3 Bull cells (PROVISIONAL_OFF).

---

## Cell trio status (final)

| Cell | Verdict | Filter | Activation |
|---|---|---|---|
| Bull UP_TRI | PROVISIONAL_OFF | recovery × vol=Med × fvg=low → 74% (n=390) | Bull regime + 30+ live |
| Bull DOWN_TRI | PROVISIONAL_OFF | late × wk3 → 65% (n=253) | Bull regime + 30+ live |
| Bull BULL_PROXY | PROVISIONAL_OFF | healthy × 20d=high → 62.5% (n=128) | Bull regime + 30+ live |

All 3 cells produced provisional filters with positive lifetime
evidence. None has live validation.

**Next session:** Bull regime synthesis (3 atomic commits, parallel to
Bear synthesis BS1-BS3).
