# Bear UP_TRI Lifetime Sub-Regime Analysis

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bear UP_TRI Feature Combination Analysis

## 1. Bear Regime Structure

The Bear UP_TRI cell shows a **bimodal rather than tri-modal** structure, fundamentally different from Choppy. The regime splits into **stress-bear** (high vol + negative returns, 43% of signals via stress__low_breadth + stress__med_breadth) and **balance-bear** (moderate conditions, 34% via balance sub-regimes). The "quiet" category is essentially absent (1%), which makes sense—quiet markets don't generate many Bear reversal setups.

The **dominant axis is volatility regime crossed with breadth**, not returns alone. The hot sub-regime marker `nifty_vol_regime=High` combined with `nifty_60d_return_pct=low` captures 15% of lifetime at 68.3% WR, while everything else (the "cold" 85%) sits at 53.4%. This is a clean binary split: stressed Bear markets vs. everything else.

Notably, **week-4 timing (day_of_month_bucket=wk4) dominates the top combinations** but appears to be a universal calendar lift (+7.6pp) rather than a hot sub-regime marker. It affects all Bear conditions equally, suggesting month-end portfolio rebalancing creates better UP_TRI reversal opportunities regardless of vol/breadth state.

The structure is simpler than Choppy: **Bear = stress + low breadth works, everything else struggles**. There's no "quiet high-breadth Bear" regime of meaningful size because those aren't Bear conditions—they're recovery transitions.

## 2. Hot Sub-Regime Characterization

**Hot Bear UP_TRI occurs when:**
1. **Volatility regime = High** (nifty_vol_percentile_20d above ~70th percentile)
2. **60-day returns deeply negative** (nifty_60d_return_pct = low, typically < -10%)
3. **Breadth compressed but not catastrophic** (low/medium, not extreme panic)
4. **Low swing complexity** (swing_high_count_20d=low, swing_low_count_20d=low)

This describes **late-stage capitulation or deep drawdown phases** where the market has been falling steadily, volatility is elevated but not spiking intraday (hence clean tri-pattern formation), and price action shows exhaustion rather than chaotic whipsaws. The "hot sub-regime markers" table confirms this: week-2 signals in low-vol environments (87.7% WR) are outliers, but the robust hot regime is the stressed condition.

In market terms, this feels like **"the third or fourth leg down"**—not initial panic (too choppy for clean patterns), but the grinding phase where participants capitulate, compression builds, and mechanical reversals gain edge. The low swing counts indicate clean directional movement exhausted, prime for triangle breakout reversal.

The **quiet__high_breadth** sub-regime (87.2% WR, 1% occurrence) represents rare Bear-labeled signals in recovering markets—likely false Bear classifications or transitional setups that work precisely because they're not really Bear conditions.

## 3. The 94.6% vs 68.3% Gap Explanation

The **26.3pp residual gap** after accounting for hot sub-regime location has three probable contributors:

**Phase-5 selection bias is primary**. April 2026's 74 signals represent a filtered subset where Phase-5 structure quality, momentum alignment, and exit timing were all optimal. The lifetime hot sub-regime (68.3%) includes every messy, marginal, poorly-formed triangle that happened to occur during high-vol/negative-return periods. April's signals likely had tighter compression, cleaner breakouts, and better post-pattern follow-through—all Phase-5 selection criteria.

**April 2026 may represent "extra hot within hot"**: a particularly clean capitulation phase where volatility was high but *stable* (not spiking), breadth deteriorated *uniformly* (not whipsawing), and the 60-day return was deeply negative but with *recent stabilization* (creating reversal setup). The binary hot/cold split at L1 doesn't capture within-regime gradients.

**Calendar concentration is real but secondary**. 74 signals in one month implies 2-3 per trading day—this density suggests a persistent regime, not random luck. However, if 40% occurred in week-4 (matching the lifetime pattern), that's ~30 signals with week-4 lift already baked into the 94.6%, which still leaves 20pp+ unexplained. The gap is too large for calendar alone.

**Conclusion**: The 94.6% reflects Phase-5's ability to cherry-pick the *best* Bear UP_TRI setups within an already-favorable hot sub-regime. Lifetime hot (68.3%) is the realistic expectation when the macro regime is right but individual signal quality varies.

## 4. Production Behavior Shift Upon Exiting Hot

When **nifty_vol_percentile_20d drops below 70th percentile OR nifty_60d_return_pct rises above -10%**, the trader should expect **WR to collapse to the 53-54% range**—the "cold sub-regime" baseline that represents 85% of lifetime history.

Concretely:
- **If vol regime shifts to Medium/Low while returns stay negative**: Expect 54-56% WR. The market is still bearish but compression quality degrades without volatility to fuel clean triangle formations.
- **If 60-day returns recover to flat/positive while vol stays elevated**: Expect 50-53% WR. High volatility in a recovering market creates false Bear labels—these are actually Choppy or early Bull conditions misclassified.
- **If both degrade together** (vol drops + returns improve): Expect 50-52% WR, approaching coin-flip. The Bear regime itself is ending.

The **stress__med_breadth sub-regime at 50.7% WR** is the warning flag—it represents 28% of lifetime and occurs when volatility is present but breadth hasn't fully compressed, creating noisy Bear signals. If breadth starts expanding (moving toward medium/high) while exiting hot, that's the worst configuration.

**Operational guidance**: When hot sub-regime conditions break, immediately implement one of the gating filters from section 5. Don't trade Bear UP_TRI unfiltered in cold regime—the edge disappears.

## 5. Filter Recommendations for Non-Hot Sub-Regimes

When **NOT in hot sub-regime** (vol < 70th percentile OR 60d_return > -10%), gate signals using these lifetime combination filters:

### Primary Filter: Week-4 + Low Swing Complexity
**`day_of_month_bucket=wk4 AND swing_high_count_20d=low`** (n=3,845, 63.3% WR, +7.6pp lift)

This captures 25% of lifetime Bear signals and works across all vol/breadth states. The combination of month-end timing (institutional rebalancing) plus clean price action (low swing counts) identifies the highest-quality Bear reversals even in moderate conditions. Add `swing_low_count_20d=low` for slightly tighter filter (63.1% WR, n=3,791).

### Secondary Filter: Low Breadth + Negative Momentum + Low Swings
**`market_breadth_pct=low AND ema50_slope_20d_pct=low AND swing_high_count_20d=low`** (n=4,555, 61.8% WR, +6.2pp lift)

This is the largest single combination (30% of lifetime) and defines "Bear conditions lite"—breadth compressed, trend negative, but without requiring high volatility. Use this when vol regime is Medium and you need a broader gate than week-4 timing alone. It won't match hot sub-regime performance but provides 62% WR with substantial volume.

### Tertiary Filter: Week-4 Timing Alone
**`day_of_month_bucket=wk4`** (any combination from top 7 entries)

If the above are too restrictive, simply requiring week-4 timing captures ~25-26% of lifetime at 63%+ WR. The lift is consistent across multiple feature combinations (compression_duration=low, swing counts, etc.), indicating week-4 is a robust standalone edge. In cold sub-regime, this provides minimal acceptable performance.

**Avoid trading Bear UP_TRI entirely** during week-1/2/3 in cold sub-regime unless breadth is extremely low AND ema50_slope is sharply negative—otherwise you're in the 50-53% WR zone where transaction costs erase edge.
