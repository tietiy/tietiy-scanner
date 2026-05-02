# Bull BULL_PROXY Cell — PROVISIONAL_OFF

## Status

- **Investigation date:** 2026-05-03
- **Cell classification:** **PROVISIONAL_OFF** (DEFERRED with provisional
  filter; lifetime-only methodology)
- **Confidence level:** LOW (no live validation possible)
- **Sessions completed:** 1 of 1
- **Production verdict:** DEFAULT SKIP; manual enable for provisional
  filter (`healthy_bull × nifty_20d_return=high`)

---

## Lifetime evidence

| Metric | Value |
|---|---|
| Lifetime n | 2,685 |
| Lifetime baseline WR | **51.1%** (best Bull-side baseline of 3 Bull cells) |
| Live n | 0 |
| Sub-regime structure | tri-modal (recovery / healthy / normal / late) |
| Direction-alignment with Bull UP_TRI | ✓ ALIGNED (3/4 sub-regimes) |

### Sub-regime distribution

| Sub-regime | n | % | WR | Lift vs baseline |
|---|---|---|---|---|
| recovery_bull | 70 | 2.6% | **57.4%** | +6.2pp |
| healthy_bull | 333 | 12.4% | 53.4% | +2.3pp |
| normal_bull | 2,011 | 74.9% | 51.5% | +0.4pp |
| late_bull | 268 | 10.0% | **43.6%** | −7.5pp |

Direction-alignment with Bull UP_TRI: recovery_bull and healthy_bull
are both bullish cells' best sub-regimes; late_bull is both cells'
worst. Confirms cross-cell directional alignment within Bull regime.

---

## Cross-cell prediction verdicts

| Test | Predicted | Actual | Verdict |
|---|---|---|---|
| `vol_climax_flag=True` | ANTI (Bear -11.0pp) | -4.4pp | ✓ CONFIRMED (universal pattern, weaker) |
| `nifty_20d_return=high` | WINNER (Bull UP_TRI anchor) | +5.8pp | ✓ CONFIRMED |
| `inside_bar_flag=True` | ANTI (Bear -9.4pp) | +1.4pp | ✗ DOESN'T TRANSFER |
| `nifty_60d_return=low` | WINNER (Bear +17.9pp) | (rare in Bull) | SKIPPED |
| `market_breadth_pct=high` | WINNER | +3.3pp | ✓ CONFIRMED |
| `52w_high_distance=high` | WINNER (Bear +14.4pp; far from highs) | +0.2pp | ✗ INVERTED |

**Verdicts confirmed**: vol_climax anti, 20d_return=high winner,
breadth=high winner.

**Pattern doesn't transfer**: inside_bar (Bear's range expansion
preference); 52w_high_distance (Bear: far-from-highs; Bull: NEAR-highs
+8.0pp WINNER — INVERTED across regimes).

### `vol_climax × BULL_PROXY` anti is universal

This is the strongest universal cross-regime BULL_PROXY anti-feature:
- Bear BULL_PROXY: −11.0pp
- Bull BULL_PROXY: −4.4pp
- Mechanism: capitulation events break the support structure that
  BULL_PROXY's reversal mechanism depends on.

### `52w_high_distance` direction INVERTS across regimes

| Regime | 52w_high_distance preference |
|---|---|
| Bear BULL_PROXY | =high WINNER (+14.4pp; far from highs = beaten down) |
| Bull BULL_PROXY | =low WINNER (+8.0pp; near highs = breakout-of-resistance) |

Different mechanism per regime: Bear = beaten-down support flip;
Bull = breakout-of-resistance support flip.

---

## Filter Conditions per sub-regime

### recovery_bull (highest precision; small sample)

Within recovery_bull (n=70, sub-regime baseline 57.4%):

| Filter | n | WR | Lift vs sub-regime |
|---|---|---|---|
| wk4 | 24 | **75.0%** | +29.1pp (small n caveat) |
| vol=Medium | 39 | 66.7% | +25.8pp |
| ROC=medium | 38 | 65.8% | +22.3pp |

### healthy_bull (broader sample)

Within healthy_bull (n=333, sub-regime baseline 53.4%):

| Filter | n | WR | Lift vs sub-regime |
|---|---|---|---|
| vol=High | 41 | **78.0%** | +28.6pp (small n) |
| day_of_week=Tue | 71 | 70.4% | +22.4pp |
| nifty_60d=high | 93 | 64.5% | +16.3pp |
| **nifty_20d=high** | **128** | **62.5%** | **+16.1pp** ★ |

### Universal anchors (no sub-regime gating)

| Filter | n | WR | Lift |
|---|---|---|---|
| `wk4` alone | 707 | **60.8%** | +9.7pp ★ (broadest coverage) |
| `nifty_20d_return=high` | 593 | 55.5% | +5.8pp |
| `nifty_vol_regime=High` | (~700) | 62.1% | +13.1pp |

---

## Disqualifying conditions

Hard SKIPs:

| Condition | WR | Reason |
|---|---|---|
| sub-regime = late_bull | 43.6% | -7.5pp anti; late-cycle exhaustion |
| `day_of_month_bucket=wk3` | 42.8% | -10.7pp anti |
| `day_of_month_bucket=wk1` | 45.2% | -7.8pp anti |
| `nifty_200d_return=high` | 48.8% | -6.8pp (late-cycle) |
| `vol_climax_flag=True` | 47.0% | -4.4pp (universal anti) |
| Sector = Bank | 45.6% | -5.5pp lifetime |
| Sector = Metal | 46.8% | -4.3pp lifetime |

---

## Production Verdict (PROVISIONAL_OFF)

### Default behavior

| Condition | Action |
|---|---|
| Live Bull BULL_PROXY signal (currently 0) | **DEFAULT: SKIP** |
| Activation requires | Bull regime active + ≥30 live signals + provisional filter match-WR ≥ 50% |
| Manual enable for testing | Settings flag `bull_bullproxy_provisional_enabled=true` |

### When manually enabled (provisional rules)

```python
def bull_bullproxy_action_provisional(signal, market_state):
    sub = detect_bull_subregime(
        market_state.nifty_200d_return_pct,
        market_state.market_breadth_pct,
    )

    # Universal hard SKIPs
    if signal.feat_vol_climax_flag is True:
        return "SKIP"  # universal BULL_PROXY anti
    if sub == "late_bull":
        return "SKIP"  # -7.5pp lifetime
    if signal.feat_day_of_month_bucket in ("wk1", "wk3"):
        return "SKIP"  # -7.8 to -10.7pp anti
    if signal.sector in ("Bank", "Metal"):
        return "SKIP"  # -4 to -5.5pp lifetime

    # Highest precision: healthy_bull × 20d=high
    if (sub == "healthy_bull"
            and signal.feat_nifty_20d_return_pct == "high"):
        return "TAKE_FULL"  # 62.5% lifetime expected (n=128)

    # Recovery_bull broad (sub-regime baseline 57.4%)
    if sub == "recovery_bull":
        if signal.feat_day_of_month_bucket == "wk4":
            return "TAKE_FULL"  # ~75% (small n=24)
        return "TAKE_SMALL"  # 57% baseline

    # wk4 universal winner (broader coverage fallback)
    if signal.feat_day_of_month_bucket == "wk4":
        return "TAKE_SMALL"  # 60.8% lifetime, +9.7pp

    return "SKIP"  # default conservative
```

### Calibrated WR expectations (HONEST)

| Filter | Lifetime WR | Calibrated production |
|---|---|---|
| recovery_bull + wk4 | ~75% (n=24) | 60-72% (small sample caveat) |
| healthy_bull + 20d=high | 62.5% (n=128) | **58-66%** ★ |
| wk4 alone | 60.8% (n=707) | 56-64% (broadest evidence) |
| recovery_bull broad | 57.4% (n=70) | 54-60% |
| Unfiltered | 51.1% | ~51% (≈ coin flip + 1pp) |

---

## Comparison vs Bear BULL_PROXY

| Property | Bear BULL_PROXY | Bull BULL_PROXY |
|---|---|---|
| Lifetime n | 891 | 2,685 |
| Lifetime baseline | 47.3% | 51.1% |
| Best sub-regime | hot 63.7% (n=86) | recovery_bull 57.4% (n=70) |
| Best filter | hot-only +16.4pp | healthy_bull × 20d=high +11.4pp |
| Top winner anchor | nifty_60d=low (oversold; +17.9pp) | nifty_20d=high (recency; +5.8pp) |
| Top anti | vol_climax=True (-11.0pp) | vol_climax=True (-4.4pp; same direction) |
| Compression | inside_bar=False winner (range expansion) | inside_bar=True neutral |
| Sectors | Pharma + defensives top | Pharma + IT + FMCG top |

Both share: vol_climax anti, support-rejection mechanism, sub-regime
specificity, defensive sector concentration. Different: anchor (Bear
oversold vs Bull recency), candle pattern preference (Bear range
expansion; Bull no preference), 52w_high_distance preference INVERTED.

---

## Investigation Notes

### What worked

1. **Direction-alignment with Bull UP_TRI confirmed** (3/4 sub-regimes).
   recovery_bull and healthy_bull are best for both bullish cells;
   late_bull is worst for both. Sub-regime structure works similarly
   across the two Bull bullish cells.

2. **Cross-cell predictions mostly confirmed**: vol_climax anti
   (universal), 20d_return=high winner (Bull bullish anchor), breadth=high
   winner (Bull bullish-cell pattern).

3. **High vol is GOOD for Bull BULL_PROXY** (+13.1pp on n≈700) —
   different from Bull UP_TRI which had vol=High as -2pp anti. Bull
   BULL_PROXY captures intra-trend volatility spikes that test
   support, distinct from UP_TRI's preference for moderate vol.

4. **wk4 calendar effect strongest for Bull BULL_PROXY** (+13.7pp; vs
   Bull UP_TRI +2.6pp). Calendar effect is direction-aligned across
   bullish Bull cells.

### What was unexpected

1. **52w_high_distance INVERTS across regimes** for BULL_PROXY:
   Bear prefers far from highs (beaten-down); Bull prefers NEAR
   highs (breakout-of-resistance). Different mechanisms per regime.

2. **inside_bar pattern doesn't transfer** from Bear BULL_PROXY's
   range-expansion preference. Bull BULL_PROXY is neutral on
   inside_bar (+1.4pp).

3. **vol=High is winner for Bull BULL_PROXY** despite being anti for
   Bull UP_TRI. Different mechanisms per cell within the same regime.

4. **Verdict A (high precision) and Verdict C (broad calendar) are
   nearly equivalent in WR**: 62.5% vs 60.8%. C has 5.5x larger
   sample. Production might prefer C for coverage; A for precision.

### Open questions (require Bull regime to resolve)

1. **Live validation of Verdict A** (n=128): does 62.5% WR sustain?
2. **Verdict C broader coverage**: is wk4 calendar effect alone
   enough, or does 20d_return gating matter?
3. **High vol as winner**: is this a real Bull BULL_PROXY mechanism
   or sample artifact?
4. **Within-cell small-sample finds** (75% on n=24, 78% on n=41):
   real or fragile?

---

## Re-evaluation triggers

| Trigger | Action |
|---|---|
| Bull regime classified for ≥10 trading days | Begin live signal accumulation |
| ≥30 Bull BULL_PROXY live signals | Re-run methodology with Phase 5 step |
| Provisional filter match-WR ≥ 55% on live | Upgrade PROVISIONAL → CANDIDATE |
| Bull regime ends without sufficient signals | Maintain PROVISIONAL; log gap |

---

## Update Log

- **v1 (2026-05-03, BP1-BP4):** Cell PROVISIONAL_OFF with lifetime-only
  methodology. n=2,685 lifetime evidence (baseline 51.1%). Direction-
  alignment with Bull UP_TRI confirmed (3/4 sub-regimes). Provisional
  Verdict A filter (`healthy_bull × nifty_20d=high`) shows 62.5% WR
  on n=128 (+11.4pp lift). Verdict C (`wk4` alone) shows 60.8% WR on
  n=707 — broader fallback. Cross-cell predictions: vol_climax anti
  CONFIRMED (universal); 20d_return=high anchor CONFIRMED; inside_bar
  pattern DOESN'T transfer; 52w_high_distance INVERTS direction across
  regimes.

  Production: DEFAULT SKIP; manual enable for Verdict A or C.
  Activation pending Bull regime return + 30+ live signals.
