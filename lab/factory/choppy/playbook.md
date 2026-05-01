# Choppy Regime Playbook

Unified guidance for trading any Choppy-regime signal across all 3 signal types.

## Status

- **Investigation date:** 2026-05-02
- **Cells complete:** 3 of 3 (UP_TRI, DOWN_TRI, BULL_PROXY)
- **Overall regime confidence:** **MEDIUM** — driven by Choppy UP_TRI cell (the only cell with sufficient live data for filter articulation). Both other cells contribute structural verdicts (DEFERRED for DOWN_TRI, KILL for BULL_PROXY) that simplify the decision flow.
- **Live data window:** April 2026 (uniformly `nifty_vol_regime=High`)
- **Aggregate live universe:** 91 + 3 + 8 = **102 Choppy signals**
- **Aggregate live WR**: (29 + 0 + 2) / (54 + 3 + 6 + 29 + 0 + 2 excluding flats) = **31 wins / 102 = 30.4%** unfiltered

---

## Decision Flow at Signal Time

For any Choppy stock signal, branch by signal_type:

### UP_TRI signals → see [Choppy UP_TRI cell](../choppy_uptri/playbook.md)

```
IF ema_alignment == "bull" AND coiled_spring_score == "medium":
    IF MACD_histogram_slope != "falling" AND higher_highs_intact_flag != True:
        → TAKE_FULL (F1 + F4 match)  [conviction tier; n=6, 67% WR]
    ELSE:
        → TAKE_SMALL (F1 match only)  [n=20, 58% WR]
ELSE:
    → SKIP
```

Filter F1 lift: +23pp over 35% baseline. Skipped WR: 28%. **30pp matched-vs-skipped gap**.

### DOWN_TRI signals → see [Choppy DOWN_TRI cell](../choppy_downtri/playbook.md)

```
→ TAKE_SMALL or SKIP (default)
```

Cell is **DEFERRED**. Live universe = 3 signals, all losses. Phase 4 produced 25 surviving patterns at lifetime test_wr 68% but none have enough live matches to validate. Trader judgment call until quarterly re-run.

**Conservative production recommendation**: SKIP unless trader has a strong context-based reason to take. The 3 observed live signals went 0/3.

### BULL_PROXY signals → see [Choppy BULL_PROXY cell](../choppy_bullproxy/playbook.md)

```
→ REJECT (always)
```

Cell verdict is **KILL**. 0/175 Phase-4 patterns validated; 8 live signals at 25% WR; 2 winners feature-indistinguishable from 6 losers. Production should suppress all Choppy BULL_PROXY signals at the bridge layer.

**Narrow exception** (compression-coil BULL_PROXY) is documented but UNTESTED — scanner doesn't currently fire that variant. Re-evaluate cell verdict only when ≥5 such signals accumulate with WR ≥50%.

---

## What Choppy Regime Feels Like Mechanically

Choppy regime punishes momentum-extended stocks and rewards compressed, bullish-aligned setups attempting their first break. The regime oscillates inside a high-volatility range — price swings feel large but reversals come fast, so trend-continuation patterns (higher highs intact, extended rallies) fail reliably because the market lacks follow-through conviction. You want stocks **coiling at support with EMA alignment confirming underlying bullish structure**, not stocks already stretched or in mixed alignment grinding sideways. Ascending triangle breakouts work when the spring is wound (medium coiled_spring_score) and the trend is intact (bull EMA alignment); descending triangles and support bounces on mixed-trend stocks are traps. Default posture is **SKIP** — only 20 of 91 triangle signals met the narrow filter, and that selectivity is the edge. When the compression-bull signature fires, size small but trust it; when it doesn't, the regime will chop you apart.

*— Mechanism narrative synthesized via Claude Sonnet 4.5 from cell findings*

---

## No-Match Default Behavior

When a Choppy signal does NOT match any cell's filter:

- **Default action: SKIP**
- Rationale: Choppy regime's edge is structurally narrow. Aggregate baseline WR is ~30%; without the filter, expected outcome is loss-skewed.
- **Override conditions:** None routine. If trader sees compelling context outside our 114-feature library (e.g., earnings catalyst, sector rotation news, options flow), trader judgment applies — but at SMALLER position size always.

This default is more conservative than Bear or (future) Bull regime defaults. Choppy = highest selectivity required.

---

## Aggregate Evidence

| Metric | Value |
|---|---|
| Total Choppy signals (live, deduped) | 102 |
| Aggregate live WR (unfiltered) | ~30% |
| F1-matched UP_TRI subset | 20 signals, 58% WR (+23pp lift) |
| TOTAL "TAKE" signals across all 3 cells | **20** (only UP_TRI F1 matches) |
| Match rate (signals that get a TAKE verdict) | 20 / 102 = **19.6%** |
| Cells producing tradeable filter | 1 of 3 (UP_TRI only) |
| Cells DEFERRED | 1 (DOWN_TRI) |
| Cells KILLED | 1 (BULL_PROXY) |

**80% of Choppy signals get a SKIP or REJECT verdict.** This is the regime's character — filter narrow, skip default.

---

## Cross-Cell Insights

### The compression-bull signature dominates winning patterns

`ema_alignment=bull AND coiled_spring_score=medium` is the **single most important feature combo** in Choppy regime:
- Choppy UP_TRI cell: F1 winning filter
- Choppy BULL_PROXY cell: WATCH-cluster signature (untested narrow exception)
- Both point to same trade archetype: bullish-trend stock with moderate compression breaks out in Choppy

If a Choppy stock has this signature and any UP_TRI / BULL_PROXY-style signal fires, trader should pay attention. Across cells, this is the unified "compression-coil break" pattern.

### Universal anti-features (across cells)

Features that appear as kill conditions or losing-cluster markers across Choppy cells:

- **`higher_highs_intact_flag = True`** (Choppy UP_TRI anti-feature, Choppy BULL_PROXY rejected-cluster) — counter-intuitive: trend-continuation flag KILLS in Choppy because Choppy means continuation breaks.
- **`ema20_distance_pct = high`** (Choppy BULL_PROXY rejected-cluster) — already-extended momentum dies in Choppy.
- **`market_breadth_pct = high`** in lifetime backtest = anti-feature in Choppy live (high-breadth signals attracted Choppy market reversion).
- **`MACD_histogram_slope = falling`** (Choppy UP_TRI anti-feature) — momentum already deteriorating doesn't recover in Choppy.

Production rule of thumb: **if the chart looks like a clean uptrend with momentum extension, Choppy regime will probably kill it.**

### Default horizon by signal type

| Signal | Recommended hold | Rationale |
|---|---|---|
| UP_TRI | **D5** | All 18 Phase 5 VALIDATED were D5; D6 had zero VALIDATED |
| DOWN_TRI | **D2** (provisional) | INV-013 confirmed D2 > D6 across regimes; 16 of 25 Phase-4 survivors were D2 |
| BULL_PROXY | N/A (REJECT) | — |

---

## Production Integration Notes

### Scanner consumption pseudocode

```python
def choppy_signal_action(signal):
    if signal.regime != "Choppy":
        return None  # not this playbook's domain

    if signal.signal_type == "BULL_PROXY":
        return "REJECT"

    if signal.signal_type == "DOWN_TRI":
        # Cell DEFERRED; conservative default
        return "TAKE_SMALL" if trader_override_present else "SKIP"

    if signal.signal_type == "UP_TRI":
        ema_bull = signal.feat_ema_alignment == "bull"
        coiled_med = (33 <= signal.feat_coiled_spring_score <= 67)
        if not (ema_bull and coiled_med):
            return "SKIP"
        # F4 confirmation
        macd_falling = signal.feat_MACD_histogram_slope == "falling"
        hhs_intact = signal.feat_higher_highs_intact_flag is True
        if macd_falling or hhs_intact:
            return "TAKE_SMALL"
        return "TAKE_FULL"

    return "SKIP"
```

### Telegram message format (suggested)

For TAKE_FULL:
```
🟢 [Choppy F1+F4] BULLISH SETUP
Symbol: <SYMBOL> | Date: <DATE>
Filter: ema_bull + coiled_medium + (no falling MACD/HHs)
Evidence: Choppy UP_TRI F4 — 67% WR (n=6 live)
Size: FULL | Hold: D5 default
```

For TAKE_SMALL:
```
🟡 [Choppy F1] CAUTION SIZING
Symbol: <SYMBOL> | Date: <DATE>
Filter: ema_bull + coiled_medium (F1 only — anti-feature triggered)
Evidence: Choppy UP_TRI F1 — 58% WR (n=20 live)
Size: HALF | Hold: D5 default
```

For REJECT (BULL_PROXY):
```
⛔ [Choppy KILL] BULL_PROXY SUPPRESSED
Symbol: <SYMBOL> | Date: <DATE>
Reason: Choppy BULL_PROXY 0/175 Phase 5 validated; 25% live WR
Action: NO TRADE
```

For SKIP (any cell, no match):
- Suppress Telegram alert entirely OR
- Daily digest format only (not realtime push)

### Risk management notes

- **Choppy = smaller size always** — even on TAKE_FULL, target half of normal Bear or Bull position size. Choppy's 30% baseline WR is structurally worse than Bear/Bull baselines.
- **Stop discipline tighter** — Choppy reversals are fast; a stop intended for Bear regime should be tightened for Choppy.
- **D5 hold is hard cap** — Choppy UP_TRI evidence specifically said D6 doesn't validate; trader should not extend hold past D5 hoping for recovery.

---

## Limitations + Future Work

### Where confidence is weak

1. **DOWN_TRI cell DEFERRED** — 3 live signals is too sparse to articulate a filter. Quarterly re-runs needed.
2. **BULL_PROXY exception untested** — compression-coil variant could exist but scanner doesn't fire it; can't validate without scanner config change.
3. **Single-window data** — all live signals are April 2026 within a uniform high-vol Choppy. Filters may behave differently in Choppy with different vol sub-character (low-vol Choppy, post-Bear Choppy, post-Bull Choppy).
4. **F1's 58% WR has wide CI** (Wilson 95% on 11W/19WL ≈ [37%, 76%]). Point estimate is real but bands are loose.

### What more data would resolve

| Data need | Resolves |
|---|---|
| 30+ more Choppy DOWN_TRI signals | DOWN_TRI cell filter articulation |
| 50+ more Choppy UP_TRI signals | F1 WR confidence interval narrowing |
| Scanner produces compression-coil BULL_PROXY signals | BULL_PROXY narrow exception test |
| Choppy data spanning multiple vol sub-characters | Filter generalization across vol regimes |
| Sector-level analysis (8 sectors × 3 signal_types) | Sector-conditional refinements |

### Pending cells

- **BEAR_PROXY** (when scanner detects it; signal type not currently in production)
- **Compression-coil BULL_PROXY variant** (if scanner config adjusted)
- **Choppy×D6 patterns** (currently SKIP; investigate if D6 has standalone edge for any sub-case)

### Quarterly re-validation triggers

- Live Choppy signal count grows by ≥30 → re-run all 3 cells
- F1 matched WR drops below 50% on next 20 signals → relegate F1 to PRELIMINARY, investigate
- DOWN_TRI live WR exceeds 40% on next 15 signals → upgrade DEFERRED → CANDIDATE filter
- BULL_PROXY 5+ compression-coil variants accumulate → test narrow-exception hypothesis

---

## Update Log

- **v1 (2026-05-02):** Initial Choppy regime synthesis from 3 cell investigations:
  - UP_TRI cell: MEDIUM confidence, F1 filter (58% WR on 20/91 matched, +23pp lift)
  - DOWN_TRI cell: DEFERRED (live n=3, all losses)
  - BULL_PROXY cell: KILL (0/175 Phase-4 patterns validated, 25% live WR)
  - Aggregate match rate 19.6%; default action SKIP for unmatched
