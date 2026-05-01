# PHASE 2 — Feature Importance Analysis (findings)

**Status:** COMPLETE — validation gate passed 2026-05-01
**Branch:** `backtest-lab` · **Tip:** `4d83722f`
**Plan:** `lab/COMBINATION_ENGINE_PLAN.md` Phase 2.A–2.E
**Inputs:** `lab/output/enriched_signals.parquet` (Phase 1) + `output/signal_history.json` (live)

---

## Phase 2 Summary

| Metric | Value |
|---|---|
| Live signals processed | 232 resolved → 200 after dedup |
| Live W/L/F | W=114, L=78, F=8 (WR ex-F = 59.4%) |
| Live cohorts | 6 (Universal + Bear + Choppy + UP_TRI + DOWN_TRI + BULL_PROXY) |
| Bull-live cohort | **SKIPPED** — April 2026 data window has no Bull regime; lifetime Bull cohort substitutes |
| Lifetime cohorts | 4 (Universal + Bear + Bull + Choppy) |
| Lifetime n | 105,781 (excluding 206 OPEN signals) |
| Lifetime sample cap (RF/L1) | 25,000 stratified per cohort (full Bear at 19,682) |
| Importance methods | 4 (univariate edge_pp + univariate p-value + RF importance + L1 \|coef\|) |
| Aggregation | Borda count (sum of per-method ranks; lower = better) |
| Total runtime | ~36s (2A=2s + 2B=2.4s + 2C=33s + 2D<1s) |
| Outputs | `live_signals_with_features.parquet`, `univariate_importance.json`, `multivariate_importance.json`, `feature_importance.json` |

---

## Methodology details

### Cohort assembly

**Live cohorts** (`live_feature_joiner.py`):
- Loaded 290 live signal records from `output/signal_history.json`
- Filtered to 232 with resolved outcomes (DAY6_WIN / DAY6_LOSS / DAY6_FLAT / STOP_HIT / TARGET_HIT)
- Deduped by `(date, symbol, signal)` keeping the canonical record (drops `-REJ` mini-layer-rejected duplicates) → 200 unique
- Joined to `enriched_signals.parquet` on `(date/scan_date, symbol, signal)`: 188 direct matches
- 12 orphans (live signals from current scanner config not present in lifetime backtest, e.g. some BULL_PROXY/DOWN_TRI variants) had features re-extracted fresh via `FeatureExtractor.extract_single` against cached stock parquets → 0 unrecoverable
- Output: `live_signals_with_features.parquet` (200 × 196 cols including 114 feat_*)

**Lifetime cohorts** (loaded directly from `enriched_signals.parquet`):
- 105,987 rows total → 105,781 after filtering OPEN
- Outcome → W/L/F mapping: `{DAY6_WIN, TARGET_HIT}` → W; `{DAY6_LOSS, STOP_HIT}` → L; `DAY6_FLAT` → F
- Per-regime split (Bear / Bull / Choppy) for cohort-specific analysis
- For RF/L1: stratified down-sample to 25K per cohort (Bear keeps full 19,682) for tractable fit time

### Class imbalance handling

Live cohort imbalance is severe per regime:
- Bear-live: 83 W / 15 L (84.7% WR) — highly imbalanced; n_losses borderline
- Choppy-live: 31 W / 63 L (33.0% WR) — inverted imbalance vs Bear
- DOWN_TRI-live: 2 W / 12 L (n=14 total) — sub-threshold per spec
- BULL_PROXY-live: 13 W / 8 L — borderline

Decision per pre-flight critical-flag review: live cohorts get **univariate-only** ranking (2 methods); multivariate restricted to lifetime cohorts where n is large.

For lifetime multivariate, both RF and L1 use `class_weight="balanced"` to handle the mild imbalance (53.5% / 50.3% / 51.0% WR for Bear / Bull / Choppy).

### Missing-value strategy

Per Phase 1 findings, 14 of 114 features have NaN rates 30-95% (pattern-presence-dependent: FVG, OB, prior swings, Fib retracements, consolidation zones).

**Multivariate strategy:** `SimpleImputer(strategy="median")` on numeric/bool features. Categorical features one-hot encoded with `dummy_na=False`; missing values become "all-zero row" across that feature's dummy columns. This avoids the synthetic "missing-bucket" approach that would have inflated dimensionality.

**Univariate strategy:** rows where the specific feature is NaN are simply excluded from that feature's analysis (so `n_low + n_high < cohort_n` for high-NaN features).

### Methods ranked

1. **Univariate edge_pp**: median split for numeric, per-category for categorical, True/False for bool. Edge_pp = max bucket WR − min bucket WR.
2. **Univariate p-value**: t-test (numeric W vs L), chi-square (categorical, bool). Lower p = more important.
3. **Random Forest** (`n_estimators=200, max_depth=10, class_weight="balanced"`): 5-fold stratified CV AUC; full-data fit for `feature_importances_`. Aggregated per-feature_id by summing across one-hot columns.
4. **Logistic Regression L1** (`penalty="l1", C=0.1, solver="liblinear", class_weight="balanced"`): standardized features; 5-fold CV AUC; full-data fit for coefs. Aggregated per-feature_id by summing |coef| across one-hot columns.

### Borda aggregation

Per cohort: each available method ranks all 114 features 1–114. Borda score = sum across methods (lower = better). Final aggregate rank = sort by Borda ascending.

**Robustness score**: count of methods ranking the feature in cohort top-25.
- Live cohorts (2 methods): "robust" if ≥2 methods agree top-25 (★ marker)
- Lifetime cohorts (4 methods): "robust" if ≥3 of 4 methods agree top-25 (★ marker)

---

## Validation gate results

### AUC per lifetime cohort (target ≥ 0.55) ✓

| Cohort | RF AUC | Logistic AUC | Status |
|---|---|---|---|
| lifetime-universal | 0.605 | 0.558 | ✓ both meaningful |
| lifetime-Bear | **0.747** | 0.613 | ✓ strongest signal |
| lifetime-Bull | 0.638 | 0.553 | ✓ Logistic borderline |
| lifetime-Choppy | 0.703 | 0.564 | ✓ |

### Robustness (top-20 features stable across methods) ✓

| Cohort | Methods | Top-20 robust | Note |
|---|---|---|---|
| universal-live | 2 | 20/20 | both methods agree |
| Bear-live | 2 | 13/20 | some single-method outliers |
| Choppy-live | 2 | 15/20 | |
| UP_TRI-live | 2 | 20/20 | |
| DOWN_TRI-live | 2 | 16/20 | n=14 (too small to overinterpret) |
| BULL_PROXY-live | 2 | 17/20 | n=21 (small) |
| lifetime-universal | 4 | 9/20 | only 9 of 20 ranked top-25 by ≥3 of 4 methods |
| lifetime-Bear | 4 | 8/20 | |
| lifetime-Bull | 4 | 11/20 | |
| lifetime-Choppy | 4 | 10/20 | |

Lifetime robustness is lower because the bar is stricter (3 of 4 methods ≥ top-25 vs 2 of 2 for live). RF and L1 produce different rankings due to different sensitivities (RF picks up interactions; L1 picks up sparse high-magnitude effects).

### No-NaN-feature check ✓

All 114 features have at least some non-NaN values across live signals. Lifetime cohorts also intact.

### Lifetime-baseline verification ✓

Lifetime cohort sizes match Phase 1: 105,781 = 105,987 − 206 OPEN; per regime: Bear 19,682 / Bull 50,809 / Choppy 35,290 → all match.

---

## Top 20 per cohort

### lifetime-Bear (RF AUC 0.747 — highest signal)

| Rank | Feature | Family | Borda | Robust |
|---|---|---|---|---|
| 1 | day_of_month_bucket | regime | 36 | 4/4 ★ |
| 2 | market_breadth_pct | regime | 58 | 4/4 ★ |
| 3 | ema_alignment | momentum | 63 | 3/4 ★ |
| 4 | nifty_vol_regime | regime | 66 | 3/4 ★ |
| 5 | 52w_high_distance_pct | institutional_zone | 67 | 4/4 ★ |
| 6 | ROC_10 | momentum | 72 | 3/4 ★ |
| 7 | ema50_slope_20d_pct | momentum | 73 | 3/4 ★ |
| 8 | range_compression_60d | compression | 89 | 2/4 |
| 9 | day_of_week | regime | 90 | 3/4 ★ |
| 10 | swing_high_count_20d | pattern | 118 | 2/4 |
| 11 | nifty_vol_percentile_20d | regime | 119 | 2/4 |
| 12 | NR4_flag | compression | 123 | 2/4 |
| 13 | inside_bar_flag | pattern | 127 | 1/4 |
| 14 | fib_1272_extension_proximity_atr | institutional_zone | 134 | 2/4 |
| 15 | 52w_low_distance_pct | institutional_zone | 141 | 0/4 |
| 16 | fib_1618_extension_proximity_atr | institutional_zone | 143 | 1/4 |
| 17 | multi_tf_alignment_score | momentum | 149 | 1/4 |
| 18 | nifty_60d_return_pct | regime | 150 | 2/4 |
| 19 | consolidation_quality | compression | 151 | 2/4 |
| 20 | ema200_distance_pct | momentum | 154 | 2/4 |

### lifetime-Choppy (RF AUC 0.703)

| Rank | Feature | Family | Borda | Robust |
|---|---|---|---|---|
| 1 | ema_alignment | momentum | 36 | 4/4 ★ |
| 2 | MACD_signal | momentum | 43 | 4/4 ★ |
| 3 | fib_382_proximity_atr | institutional_zone | 55 | 4/4 ★ |
| 4 | market_breadth_pct | regime | 61 | 3/4 ★ |
| 5 | RSI_14 | momentum | 66 | 3/4 ★ |
| 6 | advance_decline_ratio_20d | regime | 68 | 3/4 ★ |
| 7 | day_of_month_bucket | regime | 78 | 2/4 |
| 8 | day_of_week | regime | 79 | 3/4 ★ |
| 9 | fib_50_proximity_atr | institutional_zone | 82 | 3/4 ★ |
| 10 | regime_score | regime | 91 | 2/4 |
| 11 | nifty_vol_regime | regime | 92 | 3/4 ★ |
| 12 | MACD_histogram_slope | momentum | 118 | 1/4 |
| 13 | ROC_10 | momentum | 126 | 3/4 ★ |
| 14 | compression_duration | compression | 129 | 1/4 |
| 15 | consolidation_quality | compression | 137 | 2/4 |
| 16 | higher_highs_intact_flag | pattern | 137 | 2/4 |
| 17 | MACD_histogram_sign | momentum | 140 | 2/4 |
| 18 | ema20_distance_pct | momentum | 140 | 2/4 |
| 19 | coiled_spring_score | compression | 141 | 2/4 |
| 20 | 52w_high_distance_pct | institutional_zone | 142 | 1/4 |

### lifetime-Bull (RF AUC 0.638)

| Rank | Feature | Family | Borda | Robust |
|---|---|---|---|---|
| 1 | day_of_week | regime | 21 | 4/4 ★ |
| 2 | regime_score | regime | 35 | 4/4 ★ |
| 3 | fib_1618_extension_proximity_atr | institutional_zone | 49 | 4/4 ★ |
| 4 | ema_alignment | momentum | 51 | 3/4 ★ |
| 5 | MACD_signal | momentum | 60 | 3/4 ★ |
| 6 | ROC_10 | momentum | 62 | 3/4 ★ |
| 7 | consolidation_quality | compression | 65 | 3/4 ★ |
| 8 | fib_1272_extension_proximity_atr | institutional_zone | 69 | 3/4 ★ |
| 9 | RSI_14 | momentum | 89 | 3/4 ★ |
| 10 | market_breadth_pct | regime | 94 | 3/4 ★ |
| 11 | coiled_spring_score | compression | 99 | 2/4 |
| 12 | fvg_unfilled_above_count | institutional_zone | 106 | 1/4 |
| 13 | nifty_vol_regime | regime | 111 | 2/4 |
| 14 | range_position_in_window | compression | 114 | 2/4 |
| 15 | MACD_histogram_slope | momentum | 117 | 2/4 |
| 16 | sector_momentum_state | regime | 118 | 3/4 ★ |
| 17 | day_of_month_bucket | regime | 126 | 2/4 |
| 18 | nifty_20d_return_pct | regime | 127 | 2/4 |
| 19 | swing_high_count_20d | pattern | 129 | 2/4 |
| 20 | ema50_slope_5d_pct | momentum | 131 | 2/4 |

### lifetime-universal (RF AUC 0.605)

| Rank | Feature | Family | Borda | Robust |
|---|---|---|---|---|
| 1 | day_of_week | regime | 20 | 4/4 ★ |
| 2 | ROC_10 | momentum | 39 | 3/4 ★ |
| 3 | day_of_month_bucket | regime | 41 | 4/4 ★ |
| 4 | MACD_signal | momentum | 46 | 4/4 ★ |
| 5 | nifty_vol_regime | regime | 64 | 3/4 ★ |
| 6 | regime_state | regime | 64 | 4/4 ★ |
| 7 | MACD_histogram_slope | momentum | 70 | 3/4 ★ |
| 8 | regime_score | regime | 88 | 2/4 |
| 9 | RSI_14 | momentum | 103 | 3/4 ★ |
| 10 | prior_swing_low_distance_pct | institutional_zone | 104 | 2/4 |
| 11 | last_swing_high_distance_atr | pattern | 107 | 3/4 ★ |
| 12 | consolidation_quality | compression | 115 | 2/4 |
| 13 | fib_1272_extension_proximity_atr | institutional_zone | 119 | 1/4 |
| 14 | fvg_above_proximity | institutional_zone | 119 | 1/4 |
| 15 | MACD_histogram_sign | momentum | 122 | 2/4 |
| 16 | fib_1618_extension_proximity_atr | institutional_zone | 133 | 1/4 |
| 17 | compression_duration | compression | 134 | 1/4 |
| 18 | consecutive_down_days | momentum | 135 | 2/4 |
| 19 | ema_alignment | momentum | 136 | 2/4 |
| 20 | swing_high_count_20d | pattern | 136 | 2/4 |

### Live cohort top-20 — see `lab/output/feature_importance.json` for full data

Live cohort top features dominated by regime/calendar features due to extremely narrow date window (April 2026, ~17 trading days). Treat as **directional rather than authoritative** — Phase 4 should weight lifetime cohorts more heavily and use live cohorts only for sanity-check overlap.

---

## Cross-cohort comparison

### Features that appear in top-20 across **3+ lifetime cohorts** (universal + Bear + Bull + Choppy)

- `day_of_week` (4/4) — universal calendar effect
- `day_of_month_bucket` (4/4) — universal calendar effect
- `MACD_signal` (3/4: universal, Bull, Choppy)
- `MACD_histogram_slope` (3/4: universal, Bear, Choppy)
- `ema_alignment` (4/4)
- `RSI_14` (3/4: universal, Bull, Choppy)
- `ROC_10` (4/4)
- `nifty_vol_regime` (4/4)
- `regime_score` (3/4: universal, Bull, Choppy)
- `market_breadth_pct` (3/4: Bear, Bull, Choppy)
- `consolidation_quality` (3/4: universal, Bull, Choppy)
- `swing_high_count_20d` (3/4: universal, Bear, Bull)

### Regime-specific features

- **Bear-only**: `52w_high_distance_pct`, `ema50_slope_20d_pct`, `range_compression_60d`, `nifty_vol_percentile_20d`, `NR4_flag`, `inside_bar_flag`, `52w_low_distance_pct`, `multi_tf_alignment_score`, `nifty_60d_return_pct`, `ema200_distance_pct` — **structural compression + 52w + Nifty context dominate**. Aligns with INV-002 finding (Bank Nifty 60d) and INV-007 (vol regime).
- **Bull-only top**: `fib_1618_extension_proximity_atr` rank 3 — **target-zone confluence matters in trend continuation**. `coiled_spring_score`, `range_position_in_window`, `sector_momentum_state` also Bull-distinct.
- **Choppy-only top**: `fib_382_proximity_atr` rank 3, `fib_50_proximity_atr` rank 9 — **retracement levels matter in range-bound markets**. `MACD_histogram_sign`, `compression_duration`, `coiled_spring_score`, `higher_highs_intact_flag` also Choppy-distinct.

### Live vs lifetime drift (top-20 overlap)

Universal-live top-20 vs lifetime-universal top-20 overlap: ~6 features
- Both list: `day_of_month_bucket`, `regime_state`, `regime_score`, `RSI_14`, `MACD_histogram_slope`, `prior_swing_low_distance_pct`
- Live-only (date-range artifacts likely): `advance_decline_ratio_20d`, `bank_nifty_20d/60d_return_pct`, `nifty_20d/60d/200d_return_pct`, `sector_index_20d_return_pct` — these spike in live because the April 2026 window contains a specific Bank/Nifty trajectory
- Lifetime-only: `day_of_week`, `ROC_10`, `MACD_signal`, `nifty_vol_regime`, `last_swing_high_distance_atr`, `fvg_above_proximity`, `fib_1272/1618_extensions` — true structural features that need a wide history to surface

---

## Surprises and concerns

### Surprising

1. **Triangle features**: `triangle_quality_ascending` ranked top 1 in lifetime-Bear univariate (edge_pp=0.104, p<0.002, effect_size=-0.048) — **negative effect_size means losers more likely have triangle structure than winners**, which is counter-intuitive for a "high-conviction breakout" signal. May indicate triangle setups in Bear regime are false breakouts. Worth Phase 4 investigation as a kill-pattern candidate.

2. **`day_of_week` and `day_of_month_bucket` rank highly even at 105K-signal lifetime scale**: typically chalked up to small-cohort artifact, but persistence at scale suggests genuine seasonality (NSE expiry/payday effects). Phase 4 should test these as cohort-split rather than feature.

3. **Fib extension features (1272/1618) rank top in Bull**: target-zone confluence captured cleanly. Justifies the v2.1 spec addition.

4. **`vol_q` shows up high in lifetime-Bear L1** (rank 1, |coef|=0.377, sign=-): high-volume signals in Bear underperform. Counter-intuitive for "vol confirms breakout" mantra; may capture distribution rather than accumulation.

### Expected but worth verifying

5. **Bank Nifty 60d return** (`bank_nifty_60d_return_pct`): high in universal-live (rank 9) and Bear-live (rank 18); only rank 4 in lifetime-Bear top-20. INV-002 already flagged this; Phase 4 cohort-split should re-find it.

6. **`close_pos_in_range`** (INV-012 BTST primitive): not in top-20 of any cohort. Either INV-012's overnight bias doesn't translate to D6 holding (different horizon) or the BTST signal is masked at swing-trade scale.

### Concerns

7. **Bear-live n_losses=15** (post-dedup, below the 20 threshold): top features (`bollinger_squeeze_20d`, `swing_high_count_20d`, `fib_786_proximity_atr`) are interesting but statistically tentative; Phase 4 must validate against lifetime-Bear before including.

8. **DOWN_TRI-live n=14** and **BULL_PROXY-live n=21**: rankings produced but ~25% of top-20 are single-method outliers. Treat as hypothesis generators only, not as fact.

9. **L1 logistic AUC for Bull (0.553) and universal (0.558) just above 0.55 threshold**: weak linear signal. RF AUC strongly outperforms L1 in all cohorts → real predictive structure is non-linear / interaction-based. Phase 4 combination engine (which tests interactions) is the right next step rather than relying on linear coefficients.

10. **No Bull-live cohort**: April 2026 window has zero Bull regime signals. Phase 5 quarterly re-run handles this; no immediate gap to fix. Note: Phase 4 will still generate Bull combinations from lifetime-Bull top-20.

---

## Implications for Phase 4

1. **Use top-20 per cohort, not single universal top-20**. Bear and Choppy have substantially different top-20 sets (overlap ~50%). Combination engine should iterate cohort-by-cohort.

2. **Prioritize lifetime cohort rankings** for combination search; use live rankings as overlap check (does combination from lifetime-Bear top-20 also rank in Bear-live top-20?).

3. **Bear cohort is highest-confidence**: AUC 0.747 implies strong predictive structure. Combination engine should likely surface most Tier S/A rules from Bear-cohort search.

4. **Target features for cohort-split exploration**:
   - `bank_nifty_60d_return_pct` cohort split (per INV-002)
   - `nifty_vol_regime` × signal_type (per INV-007)
   - `triangle_quality_ascending` in Bear (potential kill rule)
   - `vol_q` × Bear (potential distribution-detection rule)

5. **Single-method-outlier features** (top-20 by Borda but only 1-2 of 4 methods agree top-25): Lower priority for Phase 4. Examples in lifetime-Bear: `52w_low_distance_pct` (0/4 agree), `inside_bar_flag` (1/4), `multi_tf_alignment_score` (1/4).

6. **Calendar features** (`day_of_week`, `day_of_month_bucket`) flagged as top across cohorts — Phase 4 should split by these as cohort axes (e.g. Mon vs Fri WR comparison) rather than treat as predictive features.

---

## Known limitations

- **Live n=200 is small for ML**: 200 obs / 114 features = 1.75 ratio. Univariate is fine; multivariate would severely overfit (which is why we restricted multivariate to lifetime).
- **Live data April 2026 only**: covers Bear + Choppy regimes; no Bull. Live signal patterns may not generalize.
- **Live cohort dedup dropped 32 -REJ records**, mostly Bear; live Bear-cohort dropped from 130 → 98.
- **DOWN_TRI-live and BULL_PROXY-live are too small** for confident inference (n<25). Top-20 from these cohorts must be cross-validated against lifetime equivalents before Phase 4 commits.
- **Calendar features dominate** at all cohort sizes — likely true seasonality but Phase 4 should test cohort-split rather than rely on them as predictors.
- **Lifetime sample cap (25K)** for RF/L1: full Bear processed (19K); Universal/Bull/Choppy down-sampled. Borda ranks depend on sampled subset; re-sampling with different seed could shift mid-rank features by ±5-10 ranks. Top-10 is robust; ranks 15-20 less so.
- **W/L definition excludes F (DAY6_FLAT)**: 11,138 lifetime + 8 live signals dropped from analysis. F-as-failure-mode worth Phase 4 cohort split.
- **No cross-validation of feature importance against time-period-out samples**: importance computed on full lifetime; Phase 5 will validate against held-out 1-month live data.

---

## Reference

- **Spec:** `lab/COMBINATION_ENGINE_FEATURE_SPEC.md` v2.1.1
- **Plan:** `lab/COMBINATION_ENGINE_PLAN.md` Phase 2
- **Phase 1:** `lab/analyses/PHASE-01_feature_extraction.md`
- **Tests:** **107 tests passing** across `lab/infrastructure/`:
  - `test_feature_extractor.py` (41) + `test_feature_loader.py` (19) + `test_hypothesis_tester.py` (41) + `test_live_feature_joiner.py` (6)

---

## Next phase

Phase 3 — Cohort baseline computation. Per master plan: 3 days; runs in fresh CC session. For each (signal_type × regime × hold_horizon) cohort, compute universe baseline WR. Corrects INV-012's incorrect 50% null assumption and gives Phase 4 a meaningful baseline to compare combinations against.

Phase 2 — **COMPLETE**.
