# COMBINATION ENGINE — Phase 1 Feature Library Spec (v2.1)

**Authored:** 2026-05-XX (v1) → refined v2 (post 7-question review) → refined v2.1 (post-section-verification Fib enhancement)
**Status:** v2.1 — refinements applied; ready for Phase 1 implementation
**Scope:** Phase 1 of `lab/COMBINATION_ENGINE_PLAN.md` — defines **114 features** across 6 families (was 110 in v1; 112 in v2).
**Branch:** backtest-lab

**v2 changes summary:** added `close_pos_in_range` (BTST primitive) to Family 4; replaced 2 wave-count features with 4 swing-structure features in Family 6; collapsed accumulation/distribution mirror; specified triangle/swing algorithms; corrected 2 source attributions.

**v2.1 changes summary:** added 2 Fib extension features (`fib_1272_extension_proximity_atr`, `fib_1618_extension_proximity_atr`) to Family 2; added Fib algorithm specification subsection within Family 2.

See "Resolved Decisions" section at bottom for per-Q rationale and v2.1 addendum.

---

## Schema (per feature)

Each feature definition will be stored as `lab/feature_library/<feature_id>.json` with these fields:

| Field | Description |
|---|---|
| `feature_id` | snake_case unique identifier |
| `family` | one of: compression / institutional_zone / momentum / volume / regime / pattern |
| `value_type` | float / int / categorical / bool |
| `value_range` | numeric range or list of categorical values |
| `level_thresholds` | bucketing for combination engine: `{"low": "<X", "medium": "X-Y", "high": ">Y"}` (or per type) |
| `direction` | bullish / bearish / neutral / regime-dependent / both |
| `mechanism` | 1-2 sentences plain English: why might this predict outcomes |
| `data_source` | signal-row field / OHLCV computation / cross-stock / external |
| `computation_complexity` | cheap / medium / expensive |

---

## Family 1 — Compression / range features (15 features)

Detect price consolidation states preceding breakouts. Compression is widely associated with high-conviction breakout follow-through.

| feature_id | type | range | level_thresholds (low / med / high) | direction | source | cost |
|---|---|---|---|---|---|---|
| range_compression_5d | float | 0-1 | `<0.02 / 0.02-0.05 / >0.05` (range/avg_close) | bullish (low) | OHLCV | cheap |
| range_compression_10d | float | 0-1 | `<0.03 / 0.03-0.07 / >0.07` | bullish (low) | OHLCV | cheap |
| range_compression_20d | float | 0-1 | `<0.05 / 0.05-0.12 / >0.12` | bullish (low) | OHLCV | cheap |
| range_compression_60d | float | 0-1 | `<0.08 / 0.08-0.20 / >0.20` | bullish (low) | OHLCV | cheap |
| compression_duration | int | 0-60 | `<5 / 5-15 / >15` (days inside <5% range) | bullish (high) | OHLCV | medium |
| inside_day_flag | bool | 0/1 | n/a (binary) | both | OHLCV | cheap |
| inside_day_streak | int | 0-10 | `<2 / 2-3 / >3` (consecutive inside days) | bullish (high) | OHLCV | cheap |
| NR4_flag | bool | 0/1 | n/a (today's range = narrowest of 4) | both | OHLCV | cheap |
| NR7_flag | bool | 0/1 | n/a (today's range = narrowest of 7) | both | OHLCV | cheap |
| bollinger_squeeze_20d | bool | 0/1 | n/a (BB width / KC width <1) | bullish | OHLCV | medium |
| bollinger_band_width_pct | float | 0-1 | `<0.04 / 0.04-0.10 / >0.10` (BB width / mid) | bullish (low) | OHLCV | medium |
| atr_compression_pct | float | 0-1 | `<0.5 / 0.5-1.0 / >1.0` (current ATR / 60d avg ATR) | bullish (low) | OHLCV | cheap |
| range_position_in_window | float | 0-1 | `<0.25 / 0.25-0.75 / >0.75` (close position in 20d range) | both (regime-dep) | OHLCV | cheap |
| coiled_spring_score | float | 0-100 | `<33 / 33-67 / >67` (composite of compression + uptrend) | bullish (high) | OHLCV | medium |
| consolidation_quality | categorical | tight / loose / none | n/a | bullish (tight) | OHLCV | medium |

**Mechanism notes:**
- Range compression (5/10/20/60d): tighter range = more accumulation/distribution; breakout follow-through statistically higher post-compression. Different lookbacks capture different timeframes.
- compression_duration: longer compression = more pent-up energy; explosive moves more likely.
- inside_day_flag / streak / NR4 / NR7: classical narrow-range patterns that precede expansion days.
- bollinger_squeeze: low BB width relative to Keltner width = volatility contraction; classical breakout setup.
- coiled_spring_score: composite of compression + favorable trend; designed to capture prime breakout setups.
- consolidation_quality: human-readable bucket combining range tightness + parallel/wedge geometry.

---

## Family 2 — Institutional zone features (22 features)

Distance/proximity to historically-significant price zones (FVGs, order blocks, swing highs/lows, fib retracements + extensions). Mechanism: institutional positioning concentrates at these levels. v2.1 added 2 Fib extension features (`fib_1272_extension_proximity_atr`, `fib_1618_extension_proximity_atr`) for target-zone confluence testing in Phase 4.

| feature_id | type | range | level_thresholds | direction | source | cost |
|---|---|---|---|---|---|---|
| fvg_above_proximity | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs to nearest above-FVG) | regime-dep | OHLCV | medium |
| fvg_below_proximity | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs to nearest below-FVG) | regime-dep | OHLCV | medium |
| fvg_unfilled_above_count | int | 0-20 | `<2 / 2-5 / >5` (unfilled FVGs above current price within 60d) | bullish (high; targets) | OHLCV | medium |
| fvg_unfilled_below_count | int | 0-20 | `<2 / 2-5 / >5` (unfilled FVGs below within 60d) | bearish (high; targets) | OHLCV | medium |
| ob_bullish_proximity | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs to nearest bullish order block) | bullish (low) | OHLCV | expensive |
| ob_bearish_proximity | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs to nearest bearish order block) | bearish (low) | OHLCV | expensive |
| support_zone_distance_atr | float | 0-20 | `<1 / 1-3 / >3` (ATRs to nearest support per scanner_core zones) | bullish (low) | signal-row | cheap |
| resistance_zone_distance_atr | float | 0-20 | `<1 / 1-3 / >3` (ATRs to nearest resistance) | bearish (low) | signal-row | cheap |
| prior_swing_high_distance_pct | float | 0-1 | `<0.02 / 0.02-0.10 / >0.10` (% to last 20d swing high) | bullish (low — about to break) | OHLCV | medium |
| prior_swing_low_distance_pct | float | 0-1 | `<0.02 / 0.02-0.10 / >0.10` (% to last 20d swing low) | bearish (low) | OHLCV | medium |
| 52w_high_distance_pct | float | 0-1 | `<0.05 / 0.05-0.20 / >0.20` | bullish (low) | OHLCV | cheap |
| 52w_low_distance_pct | float | 0-1 | `<0.05 / 0.05-0.20 / >0.20` | bearish (low) | OHLCV | cheap |
| fib_382_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (38.2% retracement of last impulse) | both (bounce zone) | OHLCV | medium |
| fib_50_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (50% retracement) | both | OHLCV | medium |
| fib_618_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (61.8% — golden ratio bounce zone) | both | OHLCV | medium |
| fib_786_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (78.6% — deep retrace) | both | OHLCV | medium |
| fib_1272_extension_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (1.272× extension target zone) | both | OHLCV | medium |
| fib_1618_extension_proximity_atr | float | 0-10 | `<0.5 / 0.5-1.5 / >1.5` (1.618× golden extension target) | both | OHLCV | medium |
| pivot_distance_atr | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs to scanner-detected pivot) | bullish (low) | signal-row | cheap |
| breakout_strength_atr | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs above nearest resistance, if bullish breakout) | bullish (high) | OHLCV | medium |
| consolidation_zone_distance_atr | float | 0-10 | `<0.5 / 0.5-2 / >2` (ATRs from base of recent consolidation) | bullish (low — early breakout) | OHLCV | medium |
| round_number_proximity_pct | float | 0-1 | `<0.005 / 0.005-0.02 / >0.02` (% to nearest round-number price) | both | OHLCV | cheap |

**Mechanism notes:**
- FVG (fair value gap) features: imbalance zones that price often revisits; proximity matters for entry quality.
- Order blocks (bullish/bearish): institutional accumulation/distribution candles; price often respects these on retest.
- Support/resistance zone distance: existing scanner_core has these via detect_pivots; reuse signal-row fields.
- Swing high/low distance: psychological levels; close to swing high = potential breakout setup.
- 52w_high/low distance: classical screener filter; near-52w-high signals momentum strength.
- Fibonacci retracement levels: 38.2/50/61.8/78.6 are widely used; bounce zones for trend continuation.
- fib_1272_extension_proximity_atr: 1.272 extension of last impulse acts as first target zone; price reaching this level often pauses or reverses.
- fib_1618_extension_proximity_atr: 1.618 (golden ratio) extension acts as classical target; institutional profit-taking zone often clusters here.
- Pivot distance: scanner already computes pivot points; ATR-relative distance is the relevant feature.
- Breakout strength: how far above resistance has price moved in ATRs — separates true breakouts from false ones.
- Round number proximity: psychological levels like ₹100, ₹500, ₹1000 often act as magnets/barriers.

**Computation Algorithm specifications (Family 2):**

**Fibonacci proximity features algorithm:**

"Last impulse" identification — within last 30 bars, find the most recent significant swing using existing scanner pivot detection (`PIVOT_LOOKBACK` from `scanner/config.py`).
- For uptrend retracement context: identify highest pivot high in window → most recent pivot low after that high. Impulse range = high - low.
- For downtrend retracement context: identify lowest pivot low in window → most recent pivot high after that low. Impulse range = high - low.
- If no clean swing found in 30 bars (no pivot high+low pair), all `fib_*_proximity_atr` features = NaN.

Fib levels computed at: 0.382, 0.50, 0.618, 0.786 (retracements within impulse) + 1.272, 1.618 (extensions beyond impulse).

Proximity formula: `abs(current_price - fib_level_price) / current_atr`.

Feature direction interpretation:
- Retracements (0.382-0.786): bounce zones for trend continuation; bullish if price approaching upward retracement zone in established uptrend (low proximity = strong bounce candidate); symmetric for downtrend.
- Extensions (1.272, 1.618): target zones beyond impulse; bullish/bearish depending on impulse direction; low proximity = price reaching projected target.

---

## Family 3 — Momentum / structure features (25 features)

Rate-of-change and trend-state indicators across multiple timeframes. Captures signal entry conditions and broader trend alignment.

| feature_id | type | range | level_thresholds | direction | source | cost |
|---|---|---|---|---|---|---|
| ema20_distance_pct | float | -1 to 1 | `<-0.02 / -0.02 to 0.02 / >0.02` | bullish (high+) | OHLCV | cheap |
| ema50_distance_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` | bullish (high+) | OHLCV | cheap |
| ema200_distance_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | bullish (high+) | OHLCV | cheap |
| ema_alignment | categorical | bull / mixed / bear | n/a (price>20>50>200 / etc.) | bullish (bull) | OHLCV | cheap |
| ema20_slope_5d_pct | float | -1 to 1 | `<-0.01 / -0.01 to 0.01 / >0.01` | bullish (high+) | OHLCV | cheap |
| ema50_slope_5d_pct | float | -1 to 1 | `<-0.01 / -0.01 to 0.01 / >0.01` | bullish (high+) | OHLCV | cheap |
| ema50_slope_20d_pct | float | -1 to 1 | `<-0.02 / -0.02 to 0.02 / >0.02` | bullish (high+) | OHLCV | cheap |
| daily_3d_return_pct | float | -0.5 to 0.5 | `<-0.02 / -0.02 to 0.02 / >0.02` | both (regime-dep) | OHLCV | cheap |
| daily_5d_return_pct | float | -0.5 to 0.5 | `<-0.03 / -0.03 to 0.03 / >0.03` | both | OHLCV | cheap |
| daily_20d_return_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` | bullish (high+) | OHLCV | cheap |
| daily_60d_return_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | bullish (high+) | OHLCV | cheap |
| weekly_2w_return_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` | bullish (high+) | OHLCV | cheap |
| weekly_4w_return_pct | float | -1 to 1 | `<-0.08 / -0.08 to 0.08 / >0.08` | bullish (high+) | OHLCV | cheap |
| RSI_14 | float | 0-100 | `<30 / 30-70 / >70` | both (oversold/overbought) | OHLCV | cheap |
| RSI_9 | float | 0-100 | `<30 / 30-70 / >70` | both | OHLCV | cheap |
| MACD_signal | categorical | bull / bear / neutral | n/a (MACD vs signal-line state) | bullish (bull) | OHLCV | cheap |
| MACD_histogram_sign | categorical | positive / negative | n/a | bullish (positive) | OHLCV | cheap |
| MACD_histogram_slope | categorical | rising / falling / flat | n/a | bullish (rising) | OHLCV | medium |
| consecutive_up_days | int | 0-20 | `<2 / 2-4 / >4` | bullish (high) | OHLCV | cheap |
| consecutive_down_days | int | 0-20 | `<2 / 2-4 / >4` | bearish (high) | OHLCV | cheap |
| uptrend_age_days | int | 0-200 | `<20 / 20-60 / >60` (bars since last EMA50 cross-up) | bullish (medium — not too mature) | OHLCV | medium |
| downtrend_age_days | int | 0-200 | `<20 / 20-60 / >60` (bars since last EMA50 cross-down) | bearish (medium) | OHLCV | medium |
| multi_tf_alignment_score | float | 0-3 | `<1 / 1-2 / >2` (count of aligned daily/weekly/monthly trends) | bullish (high) | OHLCV | medium |
| daily_volatility_pct | float | 0-1 | `<0.015 / 0.015-0.04 / >0.04` (20d std-dev of returns) | regime-dep | OHLCV | cheap |
| ROC_10 | float | -0.5 to 0.5 | `<-0.03 / -0.03 to 0.03 / >0.03` (10-day rate of change) | bullish (high+) | OHLCV | cheap |

**Mechanism notes:**
- EMA distance pct (20/50/200): price relative to moving averages; near or above EMA = trend-with strength.
- EMA alignment: classical "bullish stack" (price > EMA20 > EMA50 > EMA200) or "bearish stack"; captures multi-timeframe trend.
- EMA slope (5d/20d): rate of EMA change; rising EMA = healthy uptrend.
- Daily return windows (3/5/20/60d): rate-of-change at different timeframes; captures momentum at different lookbacks.
- Weekly return windows (2w/4w): smooths daily noise; institutional swing-trader timeframe.
- RSI 14/9: classical momentum oscillator; RSI < 30 oversold rebound vs >70 overbought.
- MACD signal/histogram/slope: classical momentum convergence indicator with multiple readings.
- Consecutive up/down days: streaks; longer streaks may signal exhaustion (mean reversion) or strength (continuation).
- Trend age: balances "new trend may not have legs" vs "old trend may be exhausted."
- Multi-TF alignment score: composite count of aligned timeframes; higher = stronger conviction.
- Daily volatility pct: 20d std-dev of returns; complements range_compression with vol-of-vol perspective.
- ROC_10: simple rate-of-change; close at T vs close at T-10.

---

## Family 4 — Volume features (15 features)

Volume signature relative to recent history + intraday close-position. Volume confirms or contradicts price moves; close-position-in-range captures end-of-day buying or selling pressure.

| feature_id | type | range | level_thresholds | direction | source | cost |
|---|---|---|---|---|---|---|
| vol_ratio_5d | float | 0-10 | `<0.7 / 0.7-1.5 / >1.5` (today_vol / 5d_avg) | bullish (high) | OHLCV | cheap |
| vol_ratio_10d | float | 0-10 | `<0.7 / 0.7-1.5 / >1.5` | bullish (high) | OHLCV | cheap |
| vol_ratio_20d | float | 0-10 | `<0.7 / 0.7-1.5 / >1.5` | bullish (high) | OHLCV | cheap |
| vol_ratio_50d | float | 0-10 | `<0.7 / 0.7-1.5 / >1.5` | bullish (high) | OHLCV | cheap |
| vol_q | categorical | Thin / Average / High | n/a (existing scanner field) | bullish (High) | signal-row | cheap |
| vol_trend_slope_20d | float | -1 to 1 | `<-0.02 / -0.02 to 0.02 / >0.02` (20d vol regression slope) | bullish (high+) | OHLCV | medium |
| body_to_range_ratio | float | 0-1 | `<0.3 / 0.3-0.7 / >0.7` (body / total range today) | bullish (high) | OHLCV | cheap |
| upper_wick_ratio | float | 0-1 | `<0.2 / 0.2-0.5 / >0.5` (upper wick / range) | bearish (high — selling pressure) | OHLCV | cheap |
| lower_wick_ratio | float | 0-1 | `<0.2 / 0.2-0.5 / >0.5` (lower wick / range) | bullish (high — buying support) | OHLCV | cheap |
| close_pos_in_range | float | 0-1 | `<0.3 weak / 0.3-0.7 mid / >0.7 strong` ((close - low) / (high - low)) | bullish (high) | OHLCV | cheap |
| vol_climax_flag | bool | 0/1 | n/a (vol > 2.5× 20d avg) | both (regime-dep) | OHLCV | cheap |
| vol_dryup_flag | bool | 0/1 | n/a (vol < 0.5× 20d avg) | bullish (post-pullback dryup) | OHLCV | cheap |
| accumulation_distribution_signed | float | -1 to 1 | `<-0.3 distribution / -0.3 to 0.3 neutral / >0.3 accumulation` (sum of price-vol product over 20d, normalized) | bullish (high — positive = accumulation) | OHLCV | medium |
| volume_at_pivot_ratio | float | 0-10 | `<1.0 / 1.0-2.0 / >2.0` (vol on pivot day / 20d avg) | bullish (high) | signal-row + OHLCV | medium |
| obv_slope_20d_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` (OBV regression slope normalized) | bullish (high+) | OHLCV | medium |

**Mechanism notes:**
- vol_ratio (5/10/20/50d): vol relative to recent baselines; high ratio = institutional participation.
- vol_q (existing): scanner's 3-bucket vol classification; reuse for combination filter.
- vol_trend_slope_20d: is vol rising or falling over 20d window — distributing or accumulating?
- body_to_range_ratio: large body = decisive move; small body = indecision (doji-like).
- upper/lower wick ratios: tell story of intraday rejection; high upper wick = sellers stepped in at highs.
- close_pos_in_range: INV-012 BTST primitive — close in top 30% of range with volume signature predicts overnight gap-up follow-through above universe baseline; close in bottom 30% predicts overnight reversal pressure.
- vol_climax: extreme volume often signals reversal (capitulation low or distribution high).
- vol_dryup: volume contraction during pullback often precedes resumption of trend.
- accumulation_distribution_signed: sum of (close - open) × vol over 20d window, normalized; positive value = net accumulation; negative = net distribution. Single signed feature replaces v1 mirrored pair (collapsed per Q3 resolution).
- volume_at_pivot: volume on the pivot bar relative to background; high pivot vol = stronger pivot.
- OBV slope: on-balance volume regression slope; rising OBV = accumulation.

---

## Family 5 — Regime / context features (20 features)

Market and sector context surrounding the signal. Captures the "weather" the signal fires in.

| feature_id | type | range | level_thresholds | direction | source | cost |
|---|---|---|---|---|---|---|
| nifty_20d_return_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` | both (regime-dep) | external | cheap |
| nifty_60d_return_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | both | external | cheap |
| nifty_200d_return_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | both | external | cheap |
| bank_nifty_20d_return_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` | both | external | cheap |
| bank_nifty_60d_return_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | both (per INV-002 finding) | external | cheap |
| sector_index_20d_return_pct | float | -1 to 1 | `<-0.05 / -0.05 to 0.05 / >0.05` (stock's sector index) | bullish (high+) | external | cheap |
| sector_index_60d_return_pct | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` | bullish (high+) | external | cheap |
| nifty_vol_percentile_20d | float | 0-1 | `<0.30 / 0.30-0.70 / >0.70` (vol percentile across 15-yr) | both (regime-dep) | external | cheap |
| nifty_vol_regime | categorical | Low / Medium / High | n/a (per INV-007 buckets) | both | external | cheap |
| regime_state | categorical | Bear / Bull / Choppy | n/a (existing) | regime-dep | signal-row | cheap |
| regime_score | int | -1 to 2 | n/a | regime-dep | signal-row | cheap |
| sector_momentum_state | categorical | Lagging / Neutral / Leading | n/a (existing) | bullish (Leading) | signal-row | cheap |
| sector_rank_within_universe | int | 1-13 | `<5 / 5-9 / >9` (rank by 20d return) | bullish (low rank = top) | cross-stock | medium |
| stock_rs_vs_nifty_60d | float | -1 to 1 | `<-0.10 / -0.10 to 0.10 / >0.10` (stock 60d − nifty 60d) | bullish (high+) | OHLCV + external | medium |
| rs_q | categorical | Weak / Neutral / Strong | n/a (existing scanner field) | bullish (Strong) | signal-row | cheap |
| market_breadth_pct | float | 0-1 | `<0.30 / 0.30-0.60 / >0.60` (% F&O stocks above 50d EMA) | bullish (high+) | cross-stock | expensive |
| advance_decline_ratio_20d | float | 0-3 | `<0.5 / 0.5-1.5 / >1.5` (20d cumulative AD ratio) | bullish (high+) | cross-stock | expensive |
| day_of_month_bucket | categorical | wk1 / wk2 / wk3 / wk4 | n/a (1-7, 8-14, 15-21, 22-31) | both (regime-dep) | signal-row | cheap |
| day_of_week | categorical | Mon-Fri | n/a | both | signal-row | cheap |
| days_to_monthly_expiry | int | 0-30 | `<5 / 5-15 / >15` | both | signal-row | cheap |

**Mechanism notes:**
- Nifty returns (20/60/200d): broad market context; signals fired in different macro regimes behave differently.
- Bank Nifty returns: per INV-002 Section 2b, 60d Bank Nifty return materially differentiates Bank-cohort UP_TRI WR.
- Sector index returns: stock's own sector momentum at multiple timeframes.
- Nifty vol percentile / regime: per INV-007 — vol bucket is signal-specific (no universal edge surfaced; included for combination engine to test).
- Regime state / score: existing scanner classification; foundational context.
- Sector_momentum_state: existing scanner field; complement to sector_index returns.
- Sector rank: stock's sector ranking among all sectors by recent return.
- Stock RS vs Nifty: relative strength vs broad market (60d).
- rs_q: existing scanner 3-bucket classification.
- Market breadth / AD ratio: cross-stock features capturing universe-wide momentum.
- Day of month / week / expiry: calendar-event proxies; INV-005 was scoped around this but never executed.

---

## Family 6 — Pattern features (17 features)

Discrete chart-pattern flags + structural swing features + quality scores. Mostly bool/categorical for clean combination engine bucketing. v2 dropped wave-count features (per Q2; expensive + noisy) in favor of 4 swing-structure features that capture similar pattern-quality information at lower computation cost.

| feature_id | type | range | level_thresholds | direction | source | cost |
|---|---|---|---|---|---|---|
| triangle_quality_ascending | float | 0-100 | `<33 / 33-67 / >67` (composite quality score) | bullish (high) | OHLCV | expensive |
| triangle_quality_descending | float | 0-100 | `<33 / 33-67 / >67` | bearish (high) | OHLCV | expensive |
| triangle_compression_pct | float | 0-1 | `<0.05 / 0.05-0.10 / >0.10` (current range / triangle base width) | bullish (low) | OHLCV | medium |
| triangle_touches_count | int | 0-10 | `<3 / 3-5 / >5` (number of trendline touches) | bullish (high) | OHLCV | medium |
| triangle_age_bars | int | 0-100 | `<10 / 10-30 / >30` | bullish (medium — not too old) | OHLCV | medium |
| swing_high_count_20d | int | 0-10 | `<2 / 2-3 / >3` (count of pivot highs in last 20 bars) | bullish (low — fewer recent highs = breakout potential) | OHLCV | medium |
| swing_low_count_20d | int | 0-10 | `<2 / 2-3 / >3` (count of pivot lows in last 20 bars) | bullish (high — multiple support touches) | OHLCV | medium |
| last_swing_high_distance_atr | float | 0-20 | `<1 / 1-3 / >3` (ATRs to most recent pivot high) | bullish (low — near breakout) | OHLCV | cheap |
| higher_highs_intact_flag | bool | 0/1 | n/a (last 3 swing highs in monotonic-increasing sequence) | bullish (1 — sequence maintained) | OHLCV | medium |
| gap_up_pct | float | -0.1 to 0.1 | `<0.005 / 0.005-0.02 / >0.02` (today_open / prev_close - 1) | bullish (high+) | OHLCV | cheap |
| gap_down_pct | float | -0.1 to 0.1 | `<-0.02 / -0.02 to -0.005 / >-0.005` | bearish (high+ | abs) | OHLCV | cheap |
| bullish_engulf_flag | bool | 0/1 | n/a (today engulfs prior red candle) | bullish (1) | OHLCV | cheap |
| bearish_engulf_flag | bool | 0/1 | n/a | bearish (1) | OHLCV | cheap |
| hammer_flag | bool | 0/1 | n/a (small body + long lower wick at lows) | bullish (1) | OHLCV | cheap |
| shooting_star_flag | bool | 0/1 | n/a (small body + long upper wick at highs) | bearish (1) | OHLCV | cheap |
| inside_bar_flag | bool | 0/1 | n/a (today's range inside prior; complement to Family 1) | both | OHLCV | cheap |
| outside_bar_flag | bool | 0/1 | n/a (today's range engulfs prior) | both (volatility expansion) | OHLCV | cheap |

**Mechanism notes:**
- Triangle quality (asc/desc): composite of trendline fit + touches + symmetry; classical breakout pattern.
- Triangle compression / touches / age: granular triangle features; interaction with quality score informs strength.
- Swing high/low counts (20d): structural pattern-quality proxies. Few swing highs in 20d = price compressing toward breakout; many swing lows = repeated support tests = strengthening floor.
- last_swing_high_distance_atr: how far below the most recent pivot high price currently sits (ATR-normalized); near = breakout pending.
- higher_highs_intact_flag: simple monotonic check on last 3 pivot highs; intact uptrend structure.
- Gap up/down pct: reuse from existing GAP_BREAKOUT detector logic; already validated as feature.
- Engulfing / hammer / shooting star: classical reversal candle patterns; complement triangle continuation patterns.
- Inside bar / outside bar: range relationship; inside = compression candidate; outside = volatility expansion.

**Computation Algorithm specifications (Family 6):**

**triangle_quality_ascending / triangle_quality_descending:**
- Algorithm: scan last 30 bars. Identify pivot highs (need ≥3) and pivot lows (need ≥3) using existing `detect_pivots` logic with `PIVOT_LOOKBACK`.
- Fit linear regression to pivot highs → for ascending triangle expect flat slope (`|slope_norm| < 0.005`); for descending expect negative slope < -0.005.
- Fit linear regression to pivot lows → for ascending expect positive slope > 0.005; for descending expect flat.
- Compute R² of both fits (line-fit quality).
- Composite score: `(touch_count × 10) + (R²_lows × 30) + (R²_highs × 30) + (compression_factor × 30)`. Cap at 100.
- `compression_factor = 1 - (current_range / 30d_high_range)`.
- If <3 pivots in either direction → score = 0.

**triangle_compression_pct:**
- Computed as: `today's high-low / (highest pivot high in last 30 bars - lowest pivot low in last 30 bars)`. Lower = more compressed.

**triangle_touches_count:**
- Count of pivot highs + pivot lows in last 30 bars that fall within 1 ATR of the regression-fit trendlines. Higher = more confirmation.

**swing_high_count_20d / swing_low_count_20d:**
- Apply existing `detect_pivots` logic with `PIVOT_LOOKBACK` over last 20 bars. Count pivot highs / pivot lows respectively.

**last_swing_high_distance_atr:**
- `(most_recent_pivot_high_price - today_close) / today_atr14`. Returns 0 if no pivot high in last 20 bars.

**higher_highs_intact_flag:**
- Take last 3 pivot highs from last 60 bars (need ≥3). Return 1 if `pivot[i] > pivot[i-1] > pivot[i-2]`; else 0. Returns 0 if fewer than 3 pivot highs available.

---

## Cross-family notes

- **Total features:** 15 + 22 + 25 + 15 + 20 + 17 = **114** (v1 had 110; v2 had 112; v2.1 net +2 from Fib extensions).
- **Reuse from signal-row:** ~21 features (vol_q, rs_q, sec_mom, regime, regime_score, atr, score, support/resistance distances, pivot info, days_to_monthly_expiry per Q-correction #2) — cheap, computed by existing scanner.
- **OHLCV-derived:** ~78 features — computed in Phase 1 feature_extractor from cached parquets (v2.1 added 2 Fib extension features).
- **External (Nifty / Bank Nifty / sector indices):** ~10 features — computed from `_index_*.parquet` files.
- **OHLCV + external composite:** 1 feature (`stock_rs_vs_nifty_60d` per Q-correction #1) — needs both stock data and Nifty index.
- **Cross-stock:** ~5 features (sector rank, market breadth, AD ratio) — require iterating across full universe.

**Computation cost summary:** 67 cheap / 36 medium / 11 expensive features. Phase 1 feature_extractor will need batch processing; expensive features may be deferred to follow-up if Phase 2 importance ranking deprioritizes them. Cost shifted vs v1 (was 65/32/13) due to v2 changes (wave-count expensive×2 dropped, swing-structure 1 cheap + 3 medium added, +1 cheap close_pos, -1 medium distribution collapsed) plus v2.1 (+2 medium Fib extensions). Net distribution: 65→67 cheap, 32→36 medium, 13→11 expensive.

**Combination-engine readiness:** All features have `level_thresholds` defined for low/medium/high bucketing. Combination engine (Phase 4) will iterate over these levels rather than raw values.

**Prior-INV cross-references:**
- **INV-007** (vol regime): `nifty_vol_percentile_20d` + `nifty_vol_regime` directly capture Phase 1 of that finding.
- **INV-002** (Bank Nifty 60d return Section 2b): `bank_nifty_60d_return_pct` directly encodes that filter.
- **INV-006** (D6 vs D10 exits): outside Phase 1 scope; lives in hold_horizon dimension of combination engine (Phase 4).
- **INV-010** (GAP_BREAKOUT): `gap_up_pct` + `range_compression_10d` jointly encode the detector; Phase 4 can re-discover the combination.
- **INV-012** (BTST): `close_pos_in_range` (Family 4 v2 addition per Q1) directly encodes the LAST_30MIN_STRENGTH primitive — Phase 4 can re-discover the BTST signal as a feature combination.

---

## Resolved Decisions (v1 → v2)

User reviewed the 7 open questions surfaced in v1. Decisions documented here for audit trail; corresponding spec edits applied above.

### Q1 — close_pos_in_range (BTST primitive)
- **Decision:** YES — added to Family 4 (Volume).
- **Rationale:** Directly encodes INV-012 BTST_LAST_30MIN_STRENGTH primitive (the only BTST detector confirmed REAL_EDGE +10pp over universe baseline). Cheap to compute; high re-discovery value for Phase 4 combination engine.
- **Implementation:** `(close - low) / (high - low)`; thresholds `<0.3 weak / 0.3-0.7 mid / >0.7 strong`; bullish (high); cheap.

### Q2 — Wave-count features (Family 6)
- **Decision:** DROP both `wave_count_estimate` + `wave_4_complete_flag`. REPLACE with 4 swing-structure features.
- **Rationale:** Elliott wave counting is expensive + noisy + subjective. Swing-structure features (pivot counts, monotonic-sequence flag, distance-to-last-pivot) capture similar pattern-quality information at lower cost using existing `detect_pivots` infrastructure.
- **Net change to Family 6:** -2 + 4 = +2 features (15 → 17).
- **Added features:** `swing_high_count_20d`, `swing_low_count_20d`, `last_swing_high_distance_atr`, `higher_highs_intact_flag`.

### Q3 — Accumulation/distribution mirror
- **Decision:** COLLAPSE. Drop `distribution_score_20d`; rename `accumulation_score_20d` → `accumulation_distribution_signed`.
- **Rationale:** Mirror features double the dimensionality without adding information. Single signed feature with explicit threshold semantics (`<-0.3 distribution / -0.3 to 0.3 neutral / >0.3 accumulation`) is cleaner for combination engine bucketing.
- **Net change to Family 4:** -1 feature; offset by Q1 +1 → Family 4 stays at 15.

### Q4 — Categorical exhaustive enums
- **Decision:** APPROVE. Document enum values in feature_library JSON when implementing in Phase 1B build.
- **Rationale:** No structural change needed; v1 schema already supports `value_range` as enum list for categorical features. Phase 1B will populate these explicitly in `lab/feature_library/<feature_id>.json` files.

### Q5 — Regime-specific level_thresholds
- **Decision:** REJECT for v1 (this spec). Universal thresholds throughout.
- **Rationale:** Adding regime-specific thresholds doubles or triples the feature space (one threshold set per regime) without empirical evidence that thresholds should vary. Phase 2 importance analysis will surface whether regime-dependent calibration is needed; refine post-Phase-2 if so.

### Q6 — Family 7 for outcome-derived features
- **Decision:** REJECT.
- **Rationale:** Outcome-derived features (e.g., signal's prior-trade-outcome streak) carry significant leakage risk if mishandled — features computed at signal time would inadvertently use post-signal-time information. Discipline-violating; not worth the implementation complexity to gate properly.

### Q7 — 110-feature target
- **Decision (v2):** NEW TARGET ~112. Acceptable drift from v1's 110 given net effect of Q1/Q2/Q3.
- **Counts (v2):** Family 1 = 15 / Family 2 = 20 / Family 3 = 25 / Family 4 = 15 / Family 5 = 20 / Family 6 = 17. Total **112**.
- **Update (v2.1):** Total moved to **114** after Fib extension addition. Family 2 = 22; all others unchanged. See v2.1 subsection below.

### Additional corrections (not from numbered Q list)

**Source attribution corrections:**
- `stock_rs_vs_nifty_60d` (Family 5): source changed from `OHLCV` → `OHLCV + external` (needs both stock parquet AND Nifty index parquet).
- `days_to_monthly_expiry` (Family 5): source changed from `external` → `signal-row` (computable from signal date + NSE expiry calendar; no external data fetch required).

**Algorithm specifications added:**
- Family 6: explicit algorithms for `triangle_quality_*`, `triangle_compression_pct`, `triangle_touches_count`, all 4 swing-structure features.
- Other families: existing mechanism notes plus inline thresholds are sufficient; no separate algorithm subsection needed for Families 1-5 in v2.

### v2.1 (post-section-verification): Fib enhancement
- Added algorithm specification for all 6 Fib levels (4 retracement + 2 extension)
- Added 2 Fib extension features: `fib_1272_extension_proximity_atr`, `fib_1618_extension_proximity_atr`
- Total feature count: 112 → 114
- Family 2 count: 20 → 22
- Rationale: classical Fib targets (1.272, 1.618) complement retracement entry zones; without extensions, combination engine cannot test target-confluence patterns.

---

## Next step (post user review)

Once user approves v2.1 spec contents:
1. Generate `lab/feature_library/<feature_id>.json` × 114 (one file per feature with full schema; Q4 enum values populated explicitly).
2. Build `lab/infrastructure/feature_loader.py` (registry pattern).
3. Build `lab/infrastructure/feature_extractor.py` (computation engine; uses algorithms specified in Family 2 for Fib features and Family 6 for triangle/swing features).
4. Run Phase 1 validation gate per `lab/COMBINATION_ENGINE_PLAN.md` Phase 1.D.
5. Commit `lab/output/enriched_signals.parquet` + `lab/analyses/PHASE-01_feature_extraction.md`.
6. End Phase 1 session; move to Phase 2 separately.
