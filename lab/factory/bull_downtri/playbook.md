# Bull DOWN_TRI Cell — PROVISIONAL_OFF

## Status

- **Investigation date:** 2026-05-02 night
- **Cell classification:** **PROVISIONAL_OFF** (DEFERRED with provisional
  high-precision filter)
- **Confidence level:** LOW (lifetime-only; no live validation possible)
- **Sessions completed:** 1 of 1 (lifetime-only methodology)
- **Production verdict:** DEFAULT SKIP; manual enable for
  `late_bull × wk3` provisional filter

---

## Direction-flip prediction verdict — STRONGLY CONFIRMED

The cross-cell direction-flip pattern (predicted from Bull UP_TRI
findings) is the strongest cross-cell architectural finding to date.

### Sub-regime WR inversion (perfect mirror)

| Sub-regime | UP_TRI WR | DOWN_TRI WR | Inversion |
|---|---|---|---|
| recovery_bull | 60.2% (best) | 35.7% (worst) | ✓ |
| healthy_bull | 58.4% | 40.5% | ✓ |
| normal_bull | 51.3% | 42.6% | ✓ |
| late_bull | 45.1% (worst) | **53.0% (best)** ★ | ✓ |

**All 4 sub-regime cells inverted between Bull UP_TRI and Bull
DOWN_TRI.** Mechanism: late_bull (mid 200d × low breadth = topping
pattern) is exactly when DOWN_TRI shorts work; recovery_bull (low
200d × low breadth = early recovery) is exactly when DOWN_TRI shorts
get squeezed.

### Calendar inversion (mirror)

| Week | UP_TRI lift | DOWN_TRI lift | Inversion |
|---|---|---|---|
| wk1 | +0.5pp | −3.0pp | mild |
| wk2 | −0.5pp | +0.7pp | mild |
| wk3 | **−3.3pp** | **+8.4pp** | ✓ STRONG |
| wk4 | **+2.6pp** | **−5.6pp** | ✓ STRONG |

Calendar inversion across direction is now confirmed in 2 of 3
regimes (Bear and Bull). Mechanism: month-end institutional flows
favor longs; mid-month flows favor short-side rotations.

### Sector inversion (partial)

| Direction | Top sectors | Bottom sectors |
|---|---|---|
| Bull UP_TRI | IT, Health, Consumer, FMCG (growth/quality) | Energy |
| Bull DOWN_TRI | Metal, Bank, Health (cyclicals/financials) | FMCG, Auto |

Cyclicals (Metal, Bank) lead in DOWN_TRI; growth/defensives lead in
UP_TRI. Health appears in BOTH tops (rotation sector). FMCG cleanly
inverts (UP_TRI top → DOWN_TRI worst).

### Anchor inversion — PARTIAL

| Feature | UP_TRI | DOWN_TRI |
|---|---|---|
| nifty_20d_return=high | +5-8pp WINNER | -1.6pp (mild anti) |
| nifty_200d_return=high | -2.1pp ANTI | +1.5pp (mild winner) |

Anchor inversion is directional but weaker than expected — primary
inversions are at sub-regime + calendar levels, not single-feature
deltas.

---

## Sub-regime context

Bull regime sub-regime structure (per BU1 detector — `nifty_200d_return ×
market_breadth`):

| Sub-regime | Bull DOWN_TRI lifetime WR | Production action |
|---|---|---|
| recovery_bull | 35.7% (-7.7pp) | **SKIP** (worst cell) |
| healthy_bull | 40.5% (-2.9pp) | SKIP |
| normal_bull | 42.6% (-0.8pp) | SKIP (near baseline) |
| **late_bull** | **53.0% (+9.6pp)** | **PROVISIONAL TAKE_SMALL** |

late_bull is the ONLY sub-regime where Bull DOWN_TRI has positive
lifetime edge. All other sub-regimes are at-or-below baseline.

---

## Provisional filter (Verdict B from BD3)

| Component | Rule |
|---|---|
| Sub-regime | Must be `late_bull` (mid 200d × low breadth) |
| Calendar | Must be `wk3` (week 3 of month) |

### Lifetime evidence

| Cohort | n | WR | Lift over baseline |
|---|---|---|---|
| All Bull DOWN_TRI lifetime | 10,024 | 43.4% | — |
| late_bull subset | 945 | 53.0% | +9.6pp |
| **late_bull × wk3** | **253** | **65.2%** | **+21.8pp** ★ |
| late_bull × wk3 × Mon (within-cell) | (~165) | ~71% | (within-late_bull +18pp) |

The `late_bull × wk3` configuration is the strongest Bull DOWN_TRI
combination at lifetime — +21.8pp cumulative lift on n=253. Match
rate is low (2.9% of lifetime) but precision is high.

### Top within-late_bull features (sub-regime-internal filters)

| Feature / level | Δ within-late_bull | n |
|---|---|---|
| `day_of_week=Mon` | +18.0pp | 165 |
| `day_of_month_bucket=wk3` | +16.7pp | 253 |
| `inside_bar_flag=False` | +8.7pp | 792 |
| `nifty_vol_regime=Low` | +8.6pp | 721 |

### Top lifetime winner features (full Bull DOWN_TRI)

| Feature / level | Δ presence−absence | n |
|---|---|---|
| `day_of_month_bucket=wk3` | +11.5pp | 2,404 |
| `52w_low_distance_pct=low` | +7.3pp | (~1,300) |
| `nifty_vol_regime=Low` | +5.9pp | (~1,800) |
| `ema_alignment=bear` | +3.9pp | (~1,500) |
| `52w_high_distance_pct=high` | +3.8pp | (~1,500) |

---

## Disqualifying conditions

Hard SKIPs (lifetime evidence):

| Condition | WR | Reason |
|---|---|---|
| sub-regime = recovery_bull | 35.7% | -7.7pp anti; rally just starting |
| sub-regime = healthy_bull | 40.5% | -2.9pp anti |
| `day_of_month_bucket=wk4` | 37.8% | -8.2pp anti (mirror of UP_TRI) |
| `nifty_vol_regime=Medium` | 40.6% | -4.4pp anti |
| `RSI_14=high` | 40.4% | -3.1pp anti (counter-intuitive — high RSI is BULLISH continuation) |
| Sector = FMCG | 39.3% | -4.0pp lifetime |
| Sector = Auto | 39.4% | -4.0pp lifetime |

---

## Production Verdict (PROVISIONAL_OFF)

### Default behavior

| Condition | Action |
|---|---|
| Live Bull DOWN_TRI signal (currently 0) | **DEFAULT: SKIP** until activation |
| Activation requires | Bull regime active + ≥30 live signals + provisional filter match-WR ≥ 50% |
| Manual enable for testing | Settings flag `bull_downtri_provisional_enabled=true` |

### When manually enabled (provisional rules)

```python
def bull_downtri_action_provisional(signal, market_state):
    sub = detect_bull_subregime(
        market_state.nifty_200d_return_pct,
        market_state.market_breadth_pct,
    )
    if sub != "late_bull":
        return "SKIP"  # only late_bull works
    # Disqualifying conditions
    if signal.sector in ("FMCG", "Auto"):
        return "SKIP"  # -4pp lifetime
    if signal.feat_nifty_vol_regime != "Low":
        return "SKIP"  # late_bull DOWN_TRI works in Low vol
    if signal.feat_RSI_14 == "high":
        return "SKIP"  # high RSI = sustained Bull momentum (anti)
    # Highest-precision filter
    if signal.feat_day_of_month_bucket == "wk3":
        return "TAKE_SMALL"  # ~65% lifetime expected (calibrated 60-70%)
    if signal.feat_day_of_week == "Mon":
        return "TAKE_SMALL"  # within-late_bull +18pp
    # Lower-precision late_bull match
    return "TAKE_SMALL"  # 53% lifetime baseline
```

### Calibrated WR expectations (HONEST — no live inflation)

| Filter | Lifetime WR | Calibrated production |
|---|---|---|
| late_bull + wk3 | 65.2% | **60-70%** |
| late_bull + Mon | ~71% (n=165) | 62-72% (provisional) |
| late_bull broad | 53.0% | 50-58% |
| Unfiltered Bull DOWN_TRI | 43.4% | ~43% (≈ losing) |

---

## Sample lifetime trades (top 5 cohort years for late_bull × wk3)

(Lifetime-only — no live trades possible)

late_bull × wk3 cohort distributes across years where Bull regime
showed late-cycle topping characteristics. Strong cohorts include
2018 (Bull DOWN_TRI overall +15.5pp lift) and 2022 (+7.7pp). These
years had narrowing leadership / topping mid-Bull periods.

---

## Cross-cell findings

### Bull DOWN_TRI vs Bear DOWN_TRI

| Property | Bear DOWN_TRI | Bull DOWN_TRI |
|---|---|---|
| Lifetime baseline | 46.1% | 43.4% |
| Live signals | 11 (18.2% WR) | 0 |
| Phase 5 winners | 0 | n/a |
| Provisional filter | wk2/wk3 + non-Bank | **late_bull × wk3** |
| Filter WR | 53.6% (+7.5pp) | **65.2% (+21.8pp)** ★ |
| Filter n | 1,446 | 253 |
| Filter match rate | 39.7% | 2.9% |

Bull DOWN_TRI's provisional filter has **higher precision but
narrower sample** than Bear DOWN_TRI's. Bull = high-conviction sparse
filter; Bear = lower-conviction broader filter. Both are DEFERRED
pending live validation.

### Universal contrarian-short hostility

Both DOWN_TRI cells show structural weakness:
- Bear DOWN_TRI: live 18.2% (catastrophic in current sub-regime)
- Bull DOWN_TRI: lifetime 43.4% (below 50% — losing baseline)

DOWN_TRI is **contrarian short** in both regimes. Bear regime: shorts
are with-direction but get squeezed by bear-rallies. Bull regime:
shorts are counter-direction. Both produce <50% baseline.

The only way DOWN_TRI works is in **late-cycle exhaustion sub-regimes**
(Bear: capitulation; Bull: late_bull topping). Outside those narrow
zones, contrarian shorts fail.

### Cross-regime calendar inversion CONFIRMED 2/3 regimes

| Regime | UP_TRI prefers | DOWN_TRI prefers | Inversion? |
|---|---|---|---|
| Bear | wk4 (+7.5pp) | wk2 (+15pp) | ✓ STRONG |
| Bull | wk4 (+2.6pp) | wk3 (+8.4pp) | ✓ CONFIRMED |
| Choppy | (untested) | (untested) | TBD |

Bear used wk2 winner; Bull uses wk3 winner. Both inversions are
clean. Different mid-month winner per regime (institutional flow
timing differs by regime structure).

---

## Investigation Notes

### What worked

1. **Bull sub-regime detector reused cleanly** — built once for Bull
   UP_TRI, applied without modification to Bull DOWN_TRI. Sub-regime
   structure produces a CLEAN 4-cell INVERSION (UP_TRI's best cell =
   DOWN_TRI's worst, vice versa).

2. **Direction-flip pattern strongly confirmed** at sub-regime
   level. Strongest cross-cell architectural finding to date —
   sub-regime structure mirrors perfectly across direction.

3. **Calendar inversion confirmed** (wk3 winner vs wk4 anti, mirror
   of UP_TRI's wk4 winner vs wk3 anti). Cross-regime pattern now
   confirmed in 2 of 3 regimes.

4. **Lifetime data is robust** (n=10,024) and supports a
   high-precision provisional filter (+21.8pp lift on n=253). Bull
   DOWN_TRI's filter is actually STRONGER than Bear DOWN_TRI's despite
   no live validation.

### What was unexpected

1. **Sub-regime inversion is PERFECT across all 4 cells**, not just
   directional. UP_TRI and DOWN_TRI sub-regime cells mirror exactly:
   recovery_bull (60.2% / 35.7%), healthy_bull (58.4% / 40.5%),
   normal_bull (51.3% / 42.6%), late_bull (45.1% / 53.0%).

2. **Anchor (200d/20d) inversion is WEAK at single-feature level.**
   Bull UP_TRI's 20d=high winner (+5-8pp) maps to DOWN_TRI's 20d=high
   only -1.6pp. Sub-regime + calendar inversions are stronger than
   feature-level deltas.

3. **RSI=high is ANTI for Bull DOWN_TRI** (-3.1pp). Counter-intuitive
   for a "short overbought" thesis. Mechanism: high RSI in Bull regime
   = sustained momentum = bullish continuation, NOT topping signal.
   RSI overbought is regime-dependent.

4. **wk3 effect is the strongest** in Bull DOWN_TRI — not wk2 like
   Bear DOWN_TRI. Different mid-month winner per regime.

### Open questions (require Bull regime to resolve)

1. **Live validation:** when Bull regime returns and produces ≥30
   Bull DOWN_TRI signals, does the late_bull × wk3 filter sustain
   60-70% live WR?

2. **n=253 sample size:** the provisional filter cohort is
   meaningful but narrow. Will quarterly Phase-5 re-runs as Bull
   regime accumulates produce more late_bull × wk3 observations to
   tighten confidence?

3. **late_bull × Mon (n=165):** the day-of-week effect (+18pp within
   late_bull on Mondays) is striking. Real or noise? Test against
   other regimes' Mon effect.

4. **Sub-regime inversion universality:** does this 4-cell perfect
   inversion (UP_TRI vs DOWN_TRI) replicate in Choppy regime? Worth
   running same analysis on Choppy DOWN_TRI vs UP_TRI to test.

---

## Re-evaluation triggers

| Trigger | Action |
|---|---|
| Bull regime classified for ≥10 trading days | Begin live signal accumulation tracking |
| ≥30 Bull DOWN_TRI live signals | Re-run methodology with Phase 5 step |
| Provisional filter match-WR ≥ 60% on live | Upgrade PROVISIONAL_OFF → CANDIDATE |
| Bull regime ends without sufficient signals | Maintain PROVISIONAL_OFF; log for next cycle |

---

## Update Log

- **v1 (2026-05-02 night, BD1-BD4):** Cell PROVISIONAL_OFF with
  lifetime-only methodology. n=10,024 lifetime evidence (baseline
  43.4%). Strongest cross-cell architectural finding: sub-regime
  perfect inversion (all 4 Bull sub-regime cells flip WR direction
  between UP_TRI and DOWN_TRI). Calendar inversion confirmed (wk3 +
  for DOWN_TRI; wk4 + for UP_TRI). Provisional Verdict B
  (`late_bull × wk3`) shows +21.8pp lift on n=253 — strongest Bull
  DOWN_TRI configuration. Production: DEFAULT SKIP; manual enable
  available pending Bull regime return + live validation.
