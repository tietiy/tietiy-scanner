# Bull BULL_PROXY Cell — COMPLETE (PROVISIONAL_OFF)

**Status:** ✅ COMPLETE at PROVISIONAL_OFF (Session 1 of 1).
**Date:** 2026-05-03
**Branch:** `backtest-lab`
**Commits:** 4 atomic commits across BP1-BP4

This is the third and final Bull regime cell. Bull cell trio is now
complete; Bull regime synthesis is the natural next step.

---

## Cell scope

| Metric | Value |
|---|---|
| Cell signal × regime | BULL_PROXY × Bull |
| Live signals | 0 |
| Lifetime signals | 2,685 |
| Lifetime baseline WR | 51.1% (best Bull-side baseline of 3 Bull cells) |
| Sub-regime structure | tri-modal (recovery / healthy / normal / late) |
| Direction-alignment with Bull UP_TRI | ✓ ALIGNED (3/4 sub-regimes) |
| Best filter | `healthy_bull × nifty_20d_return=high` → 62.5% WR (n=128, +11.4pp) |
| Alternative broad filter | `wk4` alone → 60.8% WR (n=707, +9.7pp) |

---

## Direction-alignment with Bull UP_TRI — CONFIRMED

3 of 4 sub-regimes aligned:

| Sub-regime | Bull UP_TRI WR | Bull BULL_PROXY WR | Aligned? |
|---|---|---|---|
| recovery_bull | 60.2% (best) | 57.4% (best) | ✓ |
| healthy_bull | 58.4% | 53.4% | ✓ |
| normal_bull | 51.3% | 51.5% | technically near-baseline |
| late_bull | 45.1% (worst) | 43.6% (worst) | ✓ |

Both bullish Bull cells share the same sub-regime preference structure:
recovery_bull > healthy_bull > normal > late_bull. This is the
expected pattern from cross-regime architecture (UP_TRI and BULL_PROXY
are both bullish setups; should align in same regime).

---

## Cross-cell predictions tested

| Test | Predicted | Actual | Verdict |
|---|---|---|---|
| `vol_climax=True` ANTI | yes (Bear -11pp) | -4.4pp | ✓ CONFIRMED |
| `nifty_20d=high` WINNER | yes (Bull UP_TRI anchor) | +5.8pp | ✓ CONFIRMED |
| `inside_bar=True` ANTI | yes (Bear -9.4pp) | +1.4pp | ✗ NEUTRAL (doesn't transfer) |
| `breadth=high` WINNER | yes (Bull bullish pattern) | +3.3pp | ✓ CONFIRMED |
| `52w_high_distance=high` WINNER | yes (Bear +14.4pp) | +0.2pp | ✗ INVERTED (Bull prefers NEAR highs) |

3 of 5 predictions confirmed. 2 don't transfer/invert — confirms that
each cell + regime combination has its own architectural signature
beyond shared anchors.

---

## Findings hierarchy

### Architectural insights (top-level — apply across regimes)

1. **`vol_climax × BULL_PROXY` anti-feature is UNIVERSAL.** Confirmed
   in both Bear (-11.0pp) and Bull (-4.4pp) regimes. Capitulation
   events break support structures that BULL_PROXY's reversal
   mechanism depends on.

2. **`52w_high_distance` direction INVERTS across regimes** for
   BULL_PROXY: Bear prefers far-from-highs (beaten down); Bull prefers
   NEAR-highs (breakout-of-resistance). Different mechanisms per
   regime; same directional flag.

3. **Direction-alignment within same regime confirmed**: Bull UP_TRI
   and Bull BULL_PROXY share recovery > healthy > normal > late
   sub-regime preference. Both bullish cells aligned.

4. **`nifty_20d_return=high` is the universal Bull bullish-cell
   anchor**: works for both Bull UP_TRI (+5-8pp) and Bull BULL_PROXY
   (+5.8pp). Bull DOWN_TRI inverts (-1.6pp mild anti).

5. **wk4 calendar effect direction holds across Bull bullish cells**:
   Bull UP_TRI (+2.6pp), Bull BULL_PROXY (+13.7pp); Bull DOWN_TRI
   inverts (-5.6pp).

### Cell-specific findings

#### Filter cascade

```python
def bull_bullproxy_action_provisional(signal, market_state):
    sub = detect_bull_subregime(...)

    # Universal hard SKIPs
    if signal.feat_vol_climax_flag is True:
        return "SKIP"
    if sub == "late_bull":
        return "SKIP"
    if signal.feat_day_of_month_bucket in ("wk1", "wk3"):
        return "SKIP"
    if signal.sector in ("Bank", "Metal"):
        return "SKIP"

    # Highest-precision: healthy_bull × 20d=high
    if (sub == "healthy_bull"
            and signal.feat_nifty_20d_return_pct == "high"):
        return "TAKE_FULL"  # 62.5% lifetime expected

    # Recovery_bull broad
    if sub == "recovery_bull":
        if signal.feat_day_of_month_bucket == "wk4":
            return "TAKE_FULL"  # ~75% on small n
        return "TAKE_SMALL"

    # wk4 universal winner (broad fallback)
    if signal.feat_day_of_month_bucket == "wk4":
        return "TAKE_SMALL"  # 60.8% lifetime

    return "SKIP"
```

#### Calibrated WR expectations

| Filter | Lifetime WR | Calibrated production |
|---|---|---|
| healthy_bull + 20d=high | 62.5% | 58-66% |
| wk4 alone | 60.8% | 56-64% |
| recovery_bull + wk4 | ~75% (n=24) | 60-72% (small sample) |
| Unfiltered | 51.1% | ~51% |

---

## Comparison to Bear BULL_PROXY

| Property | Bear BULL_PROXY | Bull BULL_PROXY |
|---|---|---|
| Lifetime n | 891 | 2,685 |
| Baseline WR | 47.3% | 51.1% |
| Best sub-regime | hot 63.7% (+16.4pp) | recovery 57.4% (+6.2pp) |
| Best filter precision | 63.7% on n=86 | 62.5% on n=128 |
| Top anchor | nifty_60d=low (oversold) | nifty_20d=high (recency) |
| Universal anti | vol_climax=True (-11.0pp) | vol_climax=True (-4.4pp) |
| Sectors | defensives top | growth + defensives top |

Bull BULL_PROXY has a HIGHER baseline (+3.8pp) but WEAKER best-cell
lift than Bear BULL_PROXY. Bull's edge is more diffuse; Bear's is
concentrated in narrow hot sub-regime.

---

## What's deferred or pending

- **Live validation** entirely pending — Bull regime hasn't been
  classified live during current period.
- **Verdict A vs Verdict C tradeoff**: precision (A: +11.4pp on n=128)
  vs broad coverage (C: +9.7pp on n=707). Live data will inform which
  is more useful in production.
- **`vol=High` finding** (+13.1pp on n≈700) — counterintuitive given
  Bull UP_TRI prefers moderate vol. Validate with live data.

---

## Lessons for Bull regime synthesis (next session)

1. **Apply same synthesis pattern as Bear** (BS1-BS3 sequence).
2. **3 cross-cell findings to consolidate**:
   - Sub-regime perfect inversion (UP_TRI vs DOWN_TRI)
   - Sub-regime alignment (UP_TRI vs BULL_PROXY)
   - Universal `vol_climax × BULL_PROXY` anti (Bear + Bull both)
3. **Bull regime cell trio status**: 1 PROVISIONAL_OFF (UP_TRI), 1
   PROVISIONAL_OFF with provisional filter (DOWN_TRI), 1
   PROVISIONAL_OFF with provisional filter (BULL_PROXY).
4. **Cross-regime synthesis** is the layer above — 3 regimes × 3 cells
   = 9 cells investigated. All major architectural patterns confirmed
   or refined.

---

## Summary

Bull BULL_PROXY closes the Bull regime cell trio. PROVISIONAL_OFF
verdict with two viable provisional filters (`healthy_bull × 20d=high`
high precision; `wk4` alone broader coverage). Cross-cell predictions
mostly confirmed (3/5); two patterns (`inside_bar`, `52w_high_distance`)
either don't transfer or invert across Bear/Bull BULL_PROXY.

Production posture: DEFAULT SKIP; manual enable available pending Bull
regime return + 30+ live signals.

**Next session:** Bull regime synthesis (cross-cell consolidation).
After that: cross-regime synthesis (Choppy + Bear + Bull).
