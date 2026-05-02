# Bull UP_TRI Cell — PROVISIONAL

## Status

- **Investigation date:** 2026-05-02 night
- **Cell classification:** **PROVISIONAL** (lifetime-only methodology)
- **Confidence level:** MEDIUM (lifetime evidence robust on n=38,100;
  no live validation possible — 0 Bull signals in current data)
- **Sessions completed:** 1 of 1 (lifetime-only methodology adapts the
  Bear/Choppy 5-step pipeline; Phase 5 cell investigation skipped because
  no live winners exist to differentiate)
- **Production verdict:** **PROVISIONAL_OFF default** — cell findings
  documented for future activation when Bull regime returns + live
  signals accumulate

---

## Why PROVISIONAL

### Layer 1 — Zero live Bull data

April-May 2026 has 0 Bull-classified live signals. Production scanner's
regime classifier outputs Choppy/Bear during current window. Bull regime
has not been triggered for the entire live tracking period.

### Layer 2 — Phase 5 doesn't apply

Standard 5-step methodology requires Phase 5 winners-vs-rejected
differentiation. With 0 live signals, Phase 5 produces 0 winners.
Adapted methodology: lifetime-only feature differentiation + sub-regime
stratification + comprehensive search.

### Layer 3 — No live-vs-lifetime gap to remove

Bear UP_TRI cell decomposed its +38.9pp gap as ~13pp sub-regime + 26pp
Phase 5 selection bias. Bull UP_TRI has no live data → no inflation to
remove → calibrated WR equals lifetime WR directly. Honest baseline:
**~52% baseline / 60-65% on best filtered subsets**.

---

## Sub-regime structure (Bull is TRI-MODAL)

Per BU1 axis discovery — the predicted axes (`trend_persistence ×
leadership_concentration`) work, but interpretation refines: best Bull
detector uses `nifty_200d_return × market_breadth_pct`.

| Sub-regime | Definition | n | % | WR |
|---|---|---|---|---|
| **recovery_bull** | low 200d AND low breadth | 972 | 2.6% | **60.2%** (+8.2pp) ★ counterintuitive |
| **healthy_bull** | mid 200d AND high breadth | 4,764 | 12.5% | **58.4%** (+6.3pp) |
| normal_bull | (everything else) | 29,110 | 76.4% | 51.3% |
| late_bull | mid 200d AND low breadth | 2,699 | 7.1% | **45.1%** (−6.9pp) ← AVOID |

Sub-regime span: 15.1pp (recovery_bull − late_bull). Sub-regime
gating produces meaningful precision lift.

### Counterintuitive recovery_bull cell

The `low 200d AND low breadth` cell is the **highest-WR Bull UP_TRI cell
(60.2% on n=972)**. Mechanism:
- Bull regime classified after Bear-to-Bull transition while 200d return
  still catching up (lagging indicator)
- Quality stocks reverting first (narrow leadership)
- Narrow breadth is feature-of-recovery, not bug

---

## Filter Conditions per sub-regime

### recovery_bull (highest precision)

Within recovery_bull (n=972, sub-regime baseline 60.2%):

| Filter | n | WR | Lift vs sub-regime |
|---|---|---|---|
| `vol=Medium AND fvg_unfilled_above_count=low` | 390 | **74.1%** | +13.9pp |
| `vol=Medium AND nifty_20d_return=medium` | 438 | 72.8% | +12.6pp |
| `breadth=med AND vol=Medium` | 494 | 69.6% | +9.4pp |

These are the **highest-WR Bull UP_TRI configurations** discovered.
Cumulative lift from 52% baseline: ~22pp.

### healthy_bull (broad-and-clean)

Within healthy_bull (n=4,764, sub-regime baseline 58.4%):

| Filter | n | WR | Lift vs sub-regime |
|---|---|---|---|
| `RSI=medium AND wk4` | 574 | **68.1%** | +9.8pp |
| `wk4 AND swing_high_count_20d=low` | 893 | 65.2% | +6.8pp |
| `breadth=high AND wk4` | 900 | 65.0% | +6.6pp |

### Full-Bull lifetime patterns (no sub-regime gating)

| Filter | n | WR | Lift |
|---|---|---|---|
| `RSI=medium × nifty_20d=high × breadth=high` | 4,794 | 59.3% | +7.2pp |
| `RSI=medium × nifty_20d=high` | 5,096 | 58.8% | +6.7pp |
| `nifty_vol=Medium × nifty_20d=high × breadth=med` | 3,365 | 59.9% | +7.8pp |

**Bull UP_TRI's strongest universal anchor is `nifty_20d_return_pct=high`**
(recent positive NIFTY return) — NOT 200d (which is the sub-regime
detector axis but not the cell's filter anchor).

---

## Disqualifying conditions

Hard SKIPs based on lifetime evidence:

| Condition | WR | Reason |
|---|---|---|
| late_bull sub-regime (mid 200d × low breadth) | 45.1% | -6.9pp anti; topping risk |
| `nifty_vol_regime=High` | 50.4% | -2.0pp anti (Bull works in moderate vol; high vol = late-Bull instability) |
| Sector = Energy | 49.2% | -2.9pp lifetime; worst Bull UP_TRI sector |
| Month = Sep | 43.6% | -8.4pp lifetime catastrophic month |
| Month = Apr | 46.4% | -5.6pp |
| Week = wk3 | 48.7% | -3.3pp anti |

---

## Evidence

| Metric | Lifetime |
|---|---|
| n total | 38,100 (largest cell in Lab) |
| W / L / F | 17,667 / 16,284 / 4,149 |
| Baseline WR | **52.0%** |
| Best sub-regime cell (recovery_bull) | 60.2% (+8.2pp) |
| Best sub-regime + filter | 74.1% (recovery + vol=Medium + fvg_low) |
| 2-feat qualifying combos (full Bull) | 40 |
| 3-feat qualifying combos | 866 |

**No live evidence.** All numbers are pure lifetime — calibrated WR
expectations apply directly.

---

## Cross-regime architectural findings

### Bull UP_TRI is genuinely DISTINCT from Bear UP_TRI

| Property | Bear UP_TRI | Bull UP_TRI |
|---|---|---|
| Lifetime baseline | 55.7% | 52.0% |
| Sub-regime axes | vol × 60d_return | 200d × breadth |
| Sub-regime structure | hot/warm/cold (evenly distributed) | recovery/healthy/normal/late (skewed) |
| Primary filter anchor | 60d_return=low (oversold) | 20d_return=high (recent strength) |
| Secondary anchor | swing_high_count_20d=low | RSI_14=medium |
| Inside_bar preference | True (compression) | NEUTRAL (no preference) |
| Calendar winner | wk4 (+7.5pp) | wk4 (+2.6pp; weaker) |
| Calendar loser | wk2 (-6.4pp) | wk3 (-3.3pp) |
| High vol preference | tier in hot sub-regime | -2.0pp ANTI |
| Sector top | CapGoods, Auto (defensive industrial) | IT, Health (growth/quality) |
| Sector bottom | Health (32% in hot!) | Energy |

**Cross-regime patterns DO NOT transfer**: 0 of 3 Bear UP_TRI top
patterns qualify in Bull UP_TRI. Each cell needs its own filter design.

### Direction-flip prediction CONFIRMED

H2 (cross-cell direction inversion on regime anchor) tested:
- Bull UP_TRI: high 200d_return delta = **−2.1pp** (anti)
- Bull DOWN_TRI: high 200d_return delta = **+1.5pp** (mild winner)

Inversion holds. Same mechanism as Bear's `nifty_60d_return=low`
inversion across UP_TRI vs DOWN_TRI.

### Meta-pattern verdict (from BU1 LLM)

PARTIAL CONFIRMED with revised interpretation:
- Sub-regime structure is universal (every regime has tri-modal
  hot/baseline/cold structure)
- Bucket sizes vary by regime stability (Bull: 76% normal vs Bear: 60%
  normal vs Choppy: 70% normal)
- Universal pattern: "two discriminative tails exist; bulk is baseline"
- Per-regime axes are correct; don't unify

---

## Production Verdict (PROVISIONAL_OFF)

| Condition | Action |
|---|---|
| Live Bull signal fires (currently none — 0 Bull live signals) | **DEFAULT: SKIP** until activation |
| Activation requires | Bull regime present + ≥30 live Bull signals + matched-WR ≥ 50% under provisional filter |
| Manual enable for testing | Settings flag `bull_uptri_provisional_enabled=true` |

### When manually enabled (provisional production rules)

```python
def bull_uptri_action_provisional(signal, market_state):
    sub = detect_bull_subregime(
        market_state.nifty_200d_return_pct,
        market_state.market_breadth_pct,
    )
    # sub ∈ {recovery_bull, healthy_bull, normal_bull, late_bull}

    # Hard SKIPs
    if sub == "late_bull":
        return "SKIP"  # 45.1% lifetime, topping risk
    if signal.month == 9:
        return "SKIP"  # -8.4pp lifetime
    if signal.sector == "Energy":
        return "SKIP"  # -2.9pp lifetime
    if signal.feat_nifty_vol_regime == "High":
        return "SKIP"  # late-Bull instability proxy

    # Best precision: recovery_bull + filter
    if sub == "recovery_bull":
        if (signal.feat_nifty_vol_regime == "Medium"
                and signal.feat_fvg_unfilled_above_count == "low"):
            return "TAKE_FULL"  # 74.1% lifetime expected
        if signal.feat_nifty_vol_regime == "Medium":
            return "TAKE_FULL"  # 69.6%-72.8% expected
        return "TAKE_SMALL"  # baseline recovery 60.2%

    # healthy_bull: prefer wk4
    if sub == "healthy_bull":
        if (signal.feat_RSI_14 == "medium"
                and signal.feat_day_of_month_bucket == "wk4"):
            return "TAKE_FULL"  # 68.1% expected
        if signal.feat_day_of_month_bucket == "wk4":
            return "TAKE_FULL"  # 65% expected
        return "TAKE_SMALL"  # baseline healthy 58.4%

    # normal_bull: apply universal anchor
    if sub == "normal_bull":
        if (signal.feat_RSI_14 == "medium"
                and signal.feat_nifty_20d_return_pct == "high"):
            return "TAKE_SMALL"  # 58.8% expected
        return "SKIP"  # below baseline edge

    return "SKIP"
```

### Calibrated WR expectations (HONEST — no inflation to remove)

| Sub-regime + filter | Lifetime WR | Expected production WR |
|---|---|---|
| recovery_bull + vol=Med + fvg=low | 74.1% | **70-78%** |
| recovery_bull + vol=Med | 69.6-72.8% | 65-75% |
| healthy_bull + RSI=med + wk4 | 68.1% | 63-72% |
| healthy_bull + wk4 | 65.0-65.2% | 60-68% |
| normal_bull + RSI=med + 20d=high | 58.8% | 54-62% |
| Unfiltered Bull UP_TRI | 52.0% | ~52% (≈ coin flip + 2pp) |

**Honest comparison vs Bear UP_TRI's 65-75% calibrated**: Bull UP_TRI's
top filters reach similar WR in best cells (recovery_bull + vol=Med +
fvg=low at 74%), but the top cells are **narrower** (n=390 vs Bear hot
n=2,275). Bull production produces ~5-10× fewer high-confidence signals
per regime period.

---

## Sample lifetime trades (top 5 per category)

(Note: lifetime-only — no live trade examples possible)

### recovery_bull cell (top patterns)

Lifetime n=972 signals with WR 60.2%. Best subset: vol=Medium AND
fvg_unfilled_above_count=low produced 290 wins on 390 W/L signals (74.1%).
Sample lifetime years where recovery_bull was active: 2009 (post-2008
recovery), 2014 (post-2011-13 sluggish), 2020 (post-COVID), 2023
(post-2022).

### healthy_bull cell (top patterns)

Lifetime n=4,764 signals with WR 58.4%. Best subset: RSI=medium AND
wk4 produced 391 wins on 574 W/L (68.1%). Active in 2014 (sustained
broad rally), 2017, 2021 mid-year.

---

## Investigation Notes

### What worked

1. **Lifetime-only methodology adapted cleanly.** Pure lifetime
   analysis on n=38,100 produces robust statistical evidence. No live
   validation needed for Phase 5 selection bias decomposition (none
   exists to remove).

2. **Predicted axes worked partially.** Sonnet 4.5's prediction
   (`trend_persistence × leadership_concentration`) was directionally
   correct. Best detector uses `nifty_200d_return × market_breadth`,
   refined as "trend MATURITY × participation quality".

3. **Sub-regime structure confirmed** (15.1pp top-vs-bottom span).
   Tri-modal pattern holds across 3 regimes (Choppy, Bear, Bull) with
   regime-specific axes.

4. **recovery_bull counterintuitive finding** (60.2% WR on
   `low 200d × low breadth`). Mechanism is mechanically clean:
   Bear-to-Bull transition while lagging indicators catch up.

### What was unexpected

1. **Bull UP_TRI's primary filter anchor is `nifty_20d_return=high`**
   (recent strength), NOT 200d_return (which is the sub-regime axis).
   Two different axes for two different purposes within the cell.

2. **Inside_bar=True preference doesn't transfer from Bear UP_TRI.**
   Bull doesn't show compression preference. Different mechanism even
   though both are bullish setups.

3. **High vol is ANTI for Bull UP_TRI (-2.0pp).** Bear UP_TRI's hot
   sub-regime tier (high vol favorable) inverts here. Bull is stable
   regime; high vol = late-Bull instability.

4. **0/3 Bear UP_TRI top patterns qualify in Bull.** Strongest
   evidence that bullish setups are NOT universal across regimes.

5. **Sector ranking very different.** Bear UP_TRI top: industrial
   defensives (CapGoods, Auto). Bull UP_TRI top: growth/quality (IT,
   Health). Bull regime favors growth; Bear favors defense.

### Open questions (require Bull regime to resolve)

1. **Live activation threshold:** how many live Bull signals + what
   match-WR is sufficient to upgrade PROVISIONAL → CANDIDATE?
   Recommendation: ≥30 live Bull signals with provisional filter
   match-WR ≥ 50% (lifetime baseline).

2. **recovery_bull sustainability:** the 74.1% WR cell has only n=390
   lifetime. Is this real edge or fragile small-sample? Need ≥10 more
   recovery_bull live observations to validate.

3. **Phase 5 selection bias in Bull:** when Bull regime returns and
   Phase 5 produces winners, will Bull's live-vs-lifetime gap show
   the same +30pp pattern as Bear UP_TRI/BULL_PROXY (bullish cells
   inflate)? Or is Bull's stability suppressing selection bias?

4. **20d-vs-200d return tension:** sub-regime detector uses 200d
   (cycle position); filter anchor uses 20d (recency). Are these
   genuinely capturing different things, or is there a unified axis
   we're missing?

5. **Cross-regime universal patterns:** the only consistent winner
   across all 3 regimes' UP_TRI cells is **wk4 calendar effect**
   (Bear +7.5pp, Bull +2.6pp, Choppy unclear). Is this genuinely
   universal? Worth dedicated investigation.

---

## Next-steps

This cell is **complete** at PROVISIONAL_OFF until Bull regime returns
to live data. Re-evaluation triggers:

| Trigger | Action |
|---|---|
| Bull regime classified live for ≥10 trading days | Begin live signal accumulation tracking |
| ≥30 Bull UP_TRI live signals accumulated | Re-run methodology with Phase 5 cell investigation step |
| Provisional filter match-WR ≥ 50% on live | Upgrade PROVISIONAL → CANDIDATE; consider production deployment |
| Bull regime ends without ≥30 signals | Maintain PROVISIONAL; log gap for next Bull cycle |

---

## Update Log

- **v1 (2026-05-02 night, BU1-BU4):** Cell PROVISIONAL with
  lifetime-only methodology. n=38,100 lifetime evidence. Bull tri-modal
  sub-regime structure confirmed (recovery/healthy/normal/late) with
  axes `nifty_200d_return × market_breadth_pct`. Bull UP_TRI's primary
  filter anchor differs from Bear UP_TRI (`20d=high` vs `60d=low`).
  Cross-regime patterns DON'T transfer (0/3 Bear patterns qualify).
  Direction-flip prediction CONFIRMED on 200d_return inversion across
  UP_TRI vs DOWN_TRI. Production: PROVISIONAL_OFF default; manual
  enable available with calibrated 65-75% WR expectations on best
  filters (recovery_bull + vol=Medium + fvg_low).
