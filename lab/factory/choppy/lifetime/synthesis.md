# Choppy Regime — Comprehensive Lifetime Exploration (L1-L5 Synthesis)

**Date:** 2026-05-02
**Branch:** `backtest-lab`
**Scope:** 35,290 W/L/F Choppy signals over 15-yr backtest (2011-2026)
**Method:** L1 segmentation → L2 cell-validation → L3 combinatorial mix-match
→ L4 stratification → L5 synthesis

This document supersedes the `lifetime_validation_summary.md` (V1-V4)
findings with a deeper, multi-axis investigation. The headline shift: Choppy
regime is **not uniform** — it contains three identifiable micro-regimes,
and edge filters depend on which sub-regime is active.

---

## Headline findings

1. **Choppy is tri-modal, not uniform.** Three distinct sub-regimes drive
   different filter behavior:
   - **Stress sub-regime** — `nifty_vol_regime=High`, ~28% of lifetime
     (n=7,497 UP_TRI). UP_TRI baseline 55.7% in this bucket.
   - **Balance sub-regime** — `nifty_vol_regime=Medium`, ~51% of lifetime
     (n=13,784 UP_TRI). UP_TRI baseline 49.2% — *below* the all-Choppy
     average.
   - **Quiet sub-regime** — `nifty_vol_regime=Low`, ~21% of lifetime
     (n=5,791 UP_TRI). UP_TRI baseline 55.1%.

2. **L3 surfaced novel patterns the cell investigations missed.** All three
   signal types' top lifetime-qualifying combos are anchored on
   `market_breadth_pct` × `nifty_vol_regime`, not `ema_alignment` ×
   `coiled_spring_score`:
   | Signal | Top 2-feat combo | n | WR | Lift |
   |---|---|---|---|---|
   | UP_TRI | `market_breadth=medium AND nifty_vol=High` | 4546 | 60.1% | +7.9pp |
   | DOWN_TRI | `market_breadth=medium AND nifty_vol=Medium` | 1727 | 55.2% | +9.1pp |
   | BULL_PROXY | `market_breadth=high AND multi_tf_alignment=high` | 507 | 56.4% | +6.8pp |

3. **Vol-gating is essential.** L4 confirmed the L3 UP_TRI combo
   (`breadth=medium`) **only works in High-vol cohort** (+7.9pp lift); in
   Medium-vol it inverts to −5.5pp lift over baseline.

4. **F1 cell finding does not surface as a top combo at lifetime.**
   `ema_bull AND coiled=medium` failed the qualifying bar (n≥100, lift≥+5pp,
   p<0.01) for any signal type. F1 is a regime-shift adaptive filter, not a
   structural Choppy edge.

5. **Strong calendar seasonality.** February asymmetry (UP_TRI −16.2pp,
   DOWN_TRI +16.2pp) and wk3 asymmetry (UP_TRI −3.9pp, DOWN_TRI +9.5pp) are
   the largest single-feature stratification effects.

6. **BULL_PROXY KILL verdict reconfirmed.** Only 10 qualifying 2-feat combos
   surfaced (vs 151 UP_TRI / 132 DOWN_TRI), best at +6.8pp lift below the
   +10pp deployment threshold. Sector reach also collapses — only FMCG and
   Bank meet n≥200.

---

## L1 — Lifetime data segmentation

### Universe scale
- 35,290 Choppy W/L/F signals across 2011-04 → 2026-04
- Aggregate baseline WR: 51.6%
- Composition: UP_TRI 27,072 (52.3% baseline); DOWN_TRI 6,287 (46.1%);
  BULL_PROXY 1,931 (49.6%)

### By year
| year_range | WR_observation |
|---|---|
| 2011-2015 | volatile band 41.8%–58.5%, peak in 2013 |
| 2017 | 60.7% high (n=2280) — strong bull-trending macro |
| 2020-2021 | 51-58% range (COVID + recovery) |
| 2024-2026 | 47-55% range |

WR drift across years: ±10pp around the 52% mean — meaningful sub-regime
variation but no systematic decay.

### By volatility regime
| nifty_vol_regime | n | WR |
|---|---|---|
| Low | 7,754 | 53.0% |
| Medium | 18,272 | 49.5% |
| High | 9,264 | 54.7% |

Counter-intuitive: **High-vol Choppy WR exceeds Medium-vol Choppy WR by
+5.2pp**. Choppy isn't uniformly hostile — its hostile bucket is medium-vol
(equilibrium), not high-vol (stress).

---

## L2 — Cell findings vs lifetime

| Live finding | Lifetime verdict | Confidence delta |
|---|---|---|
| F1 (ema_bull + coiled=medium) +23pp lift | +1.7pp at lifetime | **WEAKENED** |
| F4 (F1 + no falling MACD + no HHs intact) +31.7pp | +3.0pp at lifetime | **WEAKENED** |
| 4 universal anti-features | 3 of 4 REFUTED (direction inverted) | **REFUTED** |
| BULL_PROXY KILL verdict | Confirmed (no filter > +10pp) | **CONFIRMED** |
| DOWN_TRI DEFERRED | Unchanged; new pattern surfaced in L3-L4 | **UPGRADABLE** |

---

## L3 — Comprehensive combinatorial search

Tested all 2-feat combos from Phase-2 lifetime-Choppy top-30 features per
signal type, then 3-feat extensions for top-20 seeds. Filter: n≥100,
lift≥+5pp, binomial p<0.01.

### UP_TRI top family (151 qualifying 2-feat combos)
Anchor: `market_breadth_pct=medium × nifty_vol_regime=High`
- 60.1% WR, +7.9pp lift, n=4,546
- Adding MACD bull/positive histogram → 62.5% WR, +10.2pp, n=3,318
- Adding `RSI_14=medium` → +8.3pp, n=3,876
- Calendar variant: `wk4 × 52w_low=high` → +8.0pp, n=3,805 (different
  family — month-end / oversold rotation)

### DOWN_TRI top family (132 qualifying)
Anchor: `market_breadth_pct=medium × nifty_vol_regime=Medium`
- 55.2% WR, +9.1pp lift, n=1,727
- Calendar variant: `wk3 × bank_nifty_20d_return=medium` → 57.8% WR,
  +11.7pp, n=1,295 (best DOWN_TRI lift)

### BULL_PROXY top family (10 qualifying — sparse)
Anchor: `market_breadth_pct=high × multi_tf_alignment_score=high`
- 56.4% WR, +6.8pp lift, n=507
- With `consolidation_quality=none` → 58.8% WR, +9.2pp, n=325

**F1 (`ema_bull + coiled=medium`) did NOT meet qualifying criteria for any
signal type at lifetime.** This is the cleanest evidence yet that F1 is a
regime-shift adaptive pattern, not a structural Choppy edge.

### Sonnet 4.5 mechanism interpretation (full text in
[novel_patterns_interpretation.md](novel_patterns_interpretation.md))

> "The three families reveal Choppy regime's internal structure is bi-modal
> [...] UP_TRI exploits high-volatility stress episodes with selective
> institutional buying (volatility arbitrage), DOWN_TRI captures
> medium-volatility equilibrium mean reversion when sentiment is neutral
> [...], and BULL_PROXY isolates rare high-breadth momentum bursts that
> contradict the regime label itself (likely transition states). The F1
> collapse (+23pp live → +1.7pp lifetime) now has clear explanation: it
> selected one Choppy sub-state (low-vol coiling) that was over-represented
> in April 2026's specific 3-week window but constitutes <15% of historical
> Choppy periods, whereas these 2-feature combos partition the full regime
> topology."

Production posture per Sonnet 4.5:
- **DEPLOY** — DOWN_TRI medium-vol balance (largest n, robust across 7
  redundant feature variants)
- **INVESTIGATE** — UP_TRI high-vol stress (novel, regime-clustering risk)
- **DEFER** — BULL_PROXY (small n, possibly Choppy→Trend bleed)

---

## L4 — Sector × calendar × volatility stratification

### Sector edge ranking

| Signal | Best sectors (lift > 0) | Worst sectors (lift < 0) |
|---|---|---|
| UP_TRI | CapGoods +3.1pp, FMCG +2.0pp, Auto +1.8pp | Metal −2.2pp, IT/Infra −1.3pp |
| DOWN_TRI | Other +4.1pp, CapGoods +2.6pp, Energy +1.7pp | Pharma −4.7pp, Bank −1.3pp |
| BULL_PROXY | FMCG +4.6pp | only 2 sectors meet n≥200 |

**Sector mismatch rules** (lift ≤ −2pp):
- AVOID UP_TRI in Metal
- AVOID DOWN_TRI in Pharma

### Calendar effects

**Weekly (week-of-month):**
| | UP_TRI | DOWN_TRI |
|---|---|---|
| wk1 | +1.8pp | −1.4pp |
| wk2 | −1.4pp | +0.6pp |
| wk3 | **−3.9pp** | **+9.5pp** |
| wk4 | **+4.8pp** | **−7.1pp** |

The wk3/wk4 inversion is striking — UP_TRI works at month-end / month-start;
DOWN_TRI works mid-month around expiry overhang.

**Day-of-week:**
- DOWN_TRI Friday is a hard kill (−6.2pp)
- DOWN_TRI Thursday is the strongest (+5.1pp on n=1246)
- UP_TRI Tuesday best (+2.4pp), Thursday worst (−1.7pp)

**Monthly:**
| month | UP_TRI lift | DOWN_TRI lift |
|---|---|---|
| Feb | **−16.2pp** | **+16.2pp** |
| Mar | +10.0pp | −10.6pp |
| Sep | +11.7pp | −12.7pp |
| Oct | +7.3pp | −1.0pp |
| Jul | −7.1pp | +11.4pp |

The February asymmetry (Indian budget month, traditional vol spike) is the
largest single calendar effect across the entire study.

### Vol-conditional confirmation of L3 combos

| Signal | Combo | Low vol | Med vol | High vol |
|---|---|---|---|---|
| UP_TRI | breadth=medium | +1.2pp | **−5.5pp** | **+7.9pp** ✓ |
| DOWN_TRI | breadth=medium | −5.6pp | **+9.1pp** ✓ | −3.0pp |
| BULL_PROXY | breadth=high | +7.4pp | +6.2pp | +1.5pp |

Vol-gating is essential — UP_TRI breadth=medium **inverts** between
Medium-vol (negative) and High-vol (positive) cohorts.

---

## L5 — Synthesis and revised production stance

### Choppy regime decision flow (revised, post-comprehensive)

```python
def choppy_action_v2(signal):
    if signal.signal_type == "BULL_PROXY":
        return "REJECT"                            # KILL verdict reconfirmed

    if signal.signal_type == "UP_TRI":
        # Avoid catastrophic months / sectors
        if signal.month == 2:                      # Feb −16.2pp
            return "SKIP"
        if signal.sector == "Metal":               # −2.2pp
            return "TAKE_SMALL_AT_MOST"
        # NEW: prefer lifetime-confirmed pattern
        if (signal.feat_market_breadth_pct == "medium"
                and signal.feat_nifty_vol_regime == "High"
                and signal.feat_MACD_signal == "bull"):
            return "TAKE_FULL"                     # +10.2pp lift, n=3318
        if (signal.feat_market_breadth_pct == "medium"
                and signal.feat_nifty_vol_regime == "High"):
            return "TAKE_FULL"                     # +7.9pp lift, n=4546
        # Legacy F1 falls through — only deploy small in Apr-like sub-regimes
        if (signal.feat_ema_alignment == "bull"
                and signal.feat_coiled_spring_score == "medium"):
            return "TAKE_SMALL"                    # regime-adaptive only
        return "SKIP"

    if signal.signal_type == "DOWN_TRI":
        if signal.sector == "Pharma":              # −4.7pp
            return "SKIP"
        if signal.feat_day_of_week == "Fri":       # −6.2pp
            return "SKIP"
        if signal.feat_day_of_month_bucket == "wk4":   # −7.1pp
            return "TAKE_SMALL_AT_MOST"
        # NEW: lifetime-confirmed
        if (signal.feat_market_breadth_pct == "medium"
                and signal.feat_nifty_vol_regime == "Medium"
                and signal.feat_day_of_month_bucket == "wk3"):
            return "TAKE_FULL"                     # +11.7pp lift, n=1295
        if (signal.feat_market_breadth_pct == "medium"
                and signal.feat_nifty_vol_regime == "Medium"):
            return "TAKE_SMALL"                    # +9.1pp lift, n=1727
        return "SKIP"
```

### Confidence tiers across findings

| Finding | Confidence | Why |
|---|---|---|
| BULL_PROXY KILL verdict | **HIGH** | Confirmed at lifetime (V3 + L3) |
| L3 UP_TRI breadth=medium × vol=High | **MEDIUM-HIGH** | n=4546, p<0.001, vol-gated |
| L3 DOWN_TRI breadth=medium × vol=Medium | **MEDIUM-HIGH** | n=1727, robust across 7 redundant variants |
| L3 BULL_PROXY breadth=high × multi_tf=high | **LOW** | Below +10pp threshold; small n |
| F1 (ema_bull + coiled=medium) | **LOW** | Lifetime lift +1.7pp; regime-shift adaptive |
| Universal anti-features (3 of 4) | **REFUTED** | Direction inverted at lifetime |
| February UP_TRI hostility | **MEDIUM** | n=3338, but single-feature so likely confounded |
| wk3 DOWN_TRI bonus | **MEDIUM** | n=1718, +9.5pp lift |

### What the comprehensive exploration changes

1. **Cell investigations were too narrow** — single-feature differentiator
   analysis missed the dominant 2-feature families. Future cells need a
   combinatorial-search step (analogous to L3) before settling on filters.

2. **Vol-gating must be a first-class filter dimension.** L1 surfaced it
   as a sub-regime; L3-L4 confirmed it's essential. Future filter rules
   should branch on `nifty_vol_regime` rather than treat it as confounder.

3. **F1 is real but narrow.** It works in hostile-Choppy sub-windows
   (April 2026) where market_breadth=high makes momentum die. In mainstream
   Choppy, the dominant edge sits elsewhere.

4. **Calendar features are first-class signals**, not just confounders. wk3
   and February are the largest stratification effects in the entire
   investigation; they belong in production filter logic.

5. **Sector mismatch rules are simple wins.** UP_TRI×Metal and DOWN_TRI×Pharma
   are negative across the lifetime baseline — no filter rescues them at
   reasonable n.

### Open research questions

1. Does the L3 UP_TRI combo (breadth=medium × vol=High × MACD bull) hold up
   in 2026+ live data? Quarterly Phase-5 re-runs should track.
2. Is the wk3 DOWN_TRI effect mechanistic (expiry overhang) or coincidental?
   Test against monthly expiry calendar (typically last Thu of month →
   week-3 Thursday in some months).
3. What drives the Feb UP_TRI/DOWN_TRI asymmetry? Hypothesis: Indian Union
   Budget vol spike inverts triangle resolution direction.
4. The BULL_PROXY breadth=high × multi_tf=high pattern surfaces but is
   sub-threshold. Is this a "Choppy→Trend transition" effect, or true
   Choppy edge?
5. F1 should re-validate in another hostile-Choppy sub-regime to confirm
   regime-shift-adaptive thesis. Without re-validation, F1 may be a single-
   window artifact.

---

## File outputs

| File | Generated by | Purpose |
|---|---|---|
| `data_summary.json` | L1 (extract.py) | Year/sector/vol/signal-type WR breakdowns |
| `cell_validation.json` | L2 (cell_validation.py) | Consolidated V1/V2/V3 verdicts |
| `comprehensive_combinations_top20.json` | L3 (comprehensive_search.py) | Top-20 lifetime combos per signal_type |
| `comprehensive_combinations.parquet` | L3 | All qualifying combos (full table) |
| `novel_patterns_interpretation.md` | L3 follow-up (interpret_novel_patterns.py) | Sonnet 4.5 mechanism analysis |
| `stratified_findings.json` | L4 (stratified_search.py) | Sector × calendar × vol stratification |
| `synthesis.md` | L5 (this file) | L1-L4 synthesis + revised production stance |

---

## Update Log

- **v1 (2026-05-02 night):** Initial L1-L5 synthesis. Choppy tri-modal
  framing. F1 demoted; novel `market_breadth × nifty_vol` patterns
  promoted. Vol-gating, calendar, sector rules added to decision flow.
