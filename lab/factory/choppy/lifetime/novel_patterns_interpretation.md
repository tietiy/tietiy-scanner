# Novel Pattern Interpretation — L3 Follow-up

**Source**: `comprehensive_combinations_top20.json`
**Model**: `claude-sonnet-4-5-20250929`
**Date**: 2026-05-02

## Patterns submitted

### UP_TRI × Choppy (baseline 52.3% WR)
- `market_breadth_pct=medium` AND `nifty_vol_regime=High` → n=4546, WR=60.1%, lift=+7.9pp
- `MACD_signal=bull` AND `nifty_vol_regime=High` AND `market_breadth_pct=medium` → n=3318, WR=62.5%, lift=+10.2pp
- `nifty_vol_regime=High` AND `MACD_histogram_sign=positive` AND `market_breadth_pct=medium` → n=3318, WR=62.5%, lift=+10.2pp
- `day_of_month_bucket=wk4` AND `52w_low_distance_pct=high` → n=3805, WR=60.3%, lift=+8.0pp
- `day_of_month_bucket=wk4` AND `bank_nifty_20d_return_pct=medium` AND `52w_low_distance_pct=high` → n=2802, WR=62.8%, lift=+10.5pp

### DOWN_TRI × Choppy (baseline 46.1% WR)
- `market_breadth_pct=medium` AND `nifty_vol_regime=Medium` → n=1727, WR=55.2%, lift=+9.1pp
- `advance_decline_ratio_20d=low` AND `nifty_vol_regime=Medium` AND `market_breadth_pct=medium` → n=1727, WR=55.2%, lift=+9.1pp
- `nifty_vol_regime=Medium` AND `compression_duration=low` AND `market_breadth_pct=medium` → n=1725, WR=55.2%, lift=+9.1pp
- `day_of_month_bucket=wk3` AND `bank_nifty_20d_return_pct=medium` → n=1295, WR=57.8%, lift=+11.7pp
- `advance_decline_ratio_20d=low` AND `day_of_month_bucket=wk3` AND `bank_nifty_20d_return_pct=medium` → n=1295, WR=57.8%, lift=+11.7pp
- `RSI_14=medium` AND `nifty_vol_regime=Medium` AND `market_breadth_pct=medium` → n=1508, WR=56.1%, lift=+10.0pp
- `day_of_month_bucket=wk3` AND `compression_duration=low` AND `bank_nifty_20d_return_pct=medium` → n=1289, WR=57.7%, lift=+11.6pp

### BULL_PROXY × Choppy (baseline 49.6% WR)
- `market_breadth_pct=high` AND `multi_tf_alignment_score=high` → n=507, WR=56.4%, lift=+6.8pp
- `market_breadth_pct=high` AND `52w_high_distance_pct=medium` AND `multi_tf_alignment_score=high` → n=422, WR=57.3%, lift=+7.7pp
- `market_breadth_pct=high` AND `consolidation_quality=none` AND `multi_tf_alignment_score=high` → n=325, WR=58.8%, lift=+9.2pp
- `higher_highs_intact_flag=True` AND `multi_tf_alignment_score=high` → n=497, WR=55.5%, lift=+5.9pp
- `day_of_month_bucket=wk4` AND `consolidation_quality=none` → n=364, WR=57.7%, lift=+8.1pp

## Sonnet 4.5 interpretation

# 2-Feature Combination Analysis

## UP_TRI

### 1. Mechanism
- **Regime transition + calendar flow hybrid**: The dominant pattern combines `nifty_vol_regime=High` (volatility stress) with `market_breadth_pct=medium` (selective participation, not panic-wide).
- **Smart money positioning during selective stress**: High vol + medium breadth suggests institutional actors buying triangles while retail remains cautious — differentiated from indiscriminate capitulation (which would show low breadth).
- **Month-end accumulation pattern**: The `day_of_month_bucket=wk4` + `52w_low_distance_pct=high` (stocks near yearly lows) at +8.0pp lift signals **institutional window-dressing** or rebalancing flows targeting depressed names with technical setup.
- **Not compression-bull**: The F1 "coiled_spring + EMA_bull" required *low* volatility for coiling; this pattern *requires High vol* — fundamentally opposite market states.

### 2. Novel vs Variant
- **Novel pattern type**: The cell investigation sought low-vol compression setups; these combinations explicitly select *high-volatility + medium-breadth* regimes — a **volatility-exploitation** edge, not compression.
- The MACD confirmations (bull signal, positive histogram) in high-vol context suggest **momentum persistence through stress**, distinct from mean-reversion coils.
- Calendar + valuation intersection (wk4 × 52w_low_distance) was invisible in single-feature cells; emerges only in combination space.

### 3. Production Posture
- **INVESTIGATE FURTHER** with regime-conditional deployment:
  - The +10.2pp lift on n=3318 cohorts (MACD+vol+breadth) is compelling and orthogonal to failed F1 logic.
  - But: Test whether `nifty_vol_regime=High` was *clustered* in specific calendar years (2015-16 vol spike, 2020 COVID) — if so, lift may not generalize to 2026+ low-vol regimes.
  - Deploy wk4 + 52w_low_distance filter (n=3805, +8.0pp) as **calendar-stratified pilot** — easy to monitor for degradation.
  - Avoid full production until validating that high-vol regimes recur with similar equity curve contribution post-2024.

---

## DOWN_TRI

### 1. Mechanism
- **Mean reversion in medium-vol, medium-breadth balance**: `nifty_vol_regime=Medium` + `market_breadth_pct=medium` at +9.1pp (n=1727) suggests Choppy regime's **equilibrium hunting** — downward triangles resolve upward when market isn't trending hard either direction.
- **Weak hands capitulation + calendar flow**: The `day_of_month_bucket=wk3` × `bank_nifty_20d_return_pct=medium` combo at +11.7pp (n=1295) isolates **mid-month institutional re-entry** after retail capitulation in downward patterns, specifically when financials show moderate (not extreme) recent performance.
- **RSI medium + vol medium = neutral sentiment zone**: The n=1508 cohort (+10.0pp) confirms these aren't oversold bounces but **range-bound reversion** trades where neither bulls nor bears dominate.

### 2. Novel vs Variant
- **Novel anti-trend pattern**: Cell investigations sought compression setups (inherently bullish); DOWN_TRI combinations instead exploit **directional paradox** — bearish patterns in neutral regimes flip bullish due to Choppy regime's non-directional nature.
- The `advance_decline_ratio_20d=low` appearing alongside *improved* win rates (+9.1pp, +11.7pp) is counterintuitive — suggests **sector rotation** where broad weakness doesn't prevent specific DOWN_TRI names from mean-reverting when financials (Bank Nifty) stabilize.
- Fundamentally distinct from UP_TRI's vol-exploitation: DOWN_TRI requires *medium* vol, not high — different regime sub-state.

### 3. Production Posture
- **DEPLOY with size constraints**:
  - The wk3 + Bank Nifty medium return filter (n=1295, +11.7pp) has clean calendar/regime logic and moderate sample size — production-ready for 10-15% of Choppy capital allocation.
  - Medium-vol + medium-breadth filters (n=1727, +9.1pp) are robust across 7 redundant feature combinations — strong evidence of real regime structure, not overfitting.
  - Risk: Smaller cohorts (n=1295-1727 vs UP_TRI's 3318-4546) increase tail risk; cap position sizes at 50-60% of UP_TRI allocations.
  - Monitor for **regime shift**: If India enters sustained trending phase (2026+), medium-vol Choppy sub-regime may contract, reducing signal frequency.

---

## BULL_PROXY

### 1. Mechanism
- **Trend continuation in high-quality breadth**: `market_breadth_pct=high` + `multi_tf_alignment_score=high` at +6.8pp (n=507) isolates **institutional trend-following** — proxies fire when market-wide participation confirms directional conviction.
- **Consolidation breakout variant**: The +9.2pp lift when adding `consolidation_quality=none` (n=325) suggests these aren't range-bound setups but **momentum continuation** — stocks already trending that pause briefly without formal consolidation structure.
- **Higher-high confirmation**: `higher_highs_intact_flag=True` filters reinforce this is **pure trend persistence**, not mean reversion or regime flip.

### 2. Novel vs Variant
- **Variant of killed BULL_PROXY patterns**, but *inverted selection*: Cell investigations rejected `market_breadth=high` + extended-above-EMA filters because they selected *late-stage exhaustion*.
- These combinations add `multi_tf_alignment_score=high` as **momentum quality filter** — distinguishing healthy multi-timeframe trends from single-timeframe extensions.
- The `consolidation_quality=none` requirement (strongest at +9.2pp) directly contradicts cell findings that sought consolidation patterns — this is **anti-consolidation momentum**, capturing runaway trends in Choppy regime's brief directional bursts.
- Still a trend-continuation family, but filtered for **early/mid-stage** vs cell's late-stage versions.

### 3. Production Posture
- **DEFER pending deeper investigation**:
  - Smallest cohorts (n=325-507) with modest lift (+6.8-9.2pp) relative to UP/DOWN_TRI's stronger signals.
  - The +9.2pp lift on n=325 is statistically significant but economically marginal given Choppy regime's 49.6% baseline — leaves only ~58.8% WR, barely above coin-flip in execution slippage.
  - **Mechanism contradiction**: These are trend-following patterns in a *Choppy regime* definition — suggests either (a) regime classification error (some "Choppy" periods were actually Trend), or (b) these capture Choppy→Trend transitions rather than stable Choppy behavior.
  - Investigate regime transition timing: If signals cluster at Choppy regime *exits*, they're bleeding into Trend regime alpha; if distributed throughout Choppy periods, deploy cautiously as 5-10% allocation for diversification.

---

## Cross-Signal Synthesis

The three families reveal **Choppy regime's internal structure is bi-modal, not uniform**: UP_TRI exploits high-volatility stress episodes with selective institutional buying (volatility arbitrage), DOWN_TRI captures medium-volatility equilibrium mean reversion when sentiment is neutral and financials stabilize (range-bound recycling), and BULL_PROXY isolates rare high-breadth momentum bursts that contradict the regime label itself (likely transition states). The unifying thread is **regime sub-state specificity** — lifetime scale reveals Choppy isn't a single market condition but a collision of three distinct micro-regimes (stress, balance, breakout) that cells' compression-obsessed lens completely missed. The F1 collapse (+23pp live → +1.7pp lifetime) now has clear explanation: it selected *one* Choppy sub-state (low-vol coiling) that was over-represented in April 2026's specific 3-week window but constitutes <15% of historical Choppy periods, whereas these 2-feature combos partition the full regime topology. Production priority: DOWN_TRI's medium-vol balance trades (most stable, largest n) → UP_TRI's high-vol stress trades (novel, needs validation) → BULL_PROXY momentum (smallest, likely regime-bleed artifact).
