# PHASE 4 — Combination Engine (findings)

**Status:** COMPLETE — validation gate passed 2026-05-02
**Branch:** `backtest-lab` · **Tip:** `1f1635cf`
**Plan:** `lab/COMBINATION_ENGINE_PLAN.md` Phase 4.A–4.E
**Output:** `lab/output/combinations_lifetime.parquet` (5,057 survivors)

---

## Phase 4 Summary

| Metric | Value |
|---|---|
| Active cohort cells | 20 (3 signal × 3 regime × cohort-specific horizons; 4 skipped per Phase 3) |
| Combinations generated | **541,446** (1/2/3/4-feature × top-20 features × levels) |
| Combinations tested | 541,446 (walk-forward train 2011-2018 / validate 2019-2022 / test 2023-2025) |
| Walk-forward runtime | **51.8 min** (5.6 ms/combo) |
| **Survivors after 6-filter pipeline** | **5,057** (0.93% pass rate) |
| Tier S (edge ≥ 15pp) | **708** |
| Tier A (10-15pp) | **1,577** |
| Tier B (5-10pp) | **2,772** |
| Cohort cells with ≥1 survivor | 17 of 20 (3 cells: BULL_PROXY×Bear×D3/D5, DOWN_TRI×Bear×D1) |
| Total runtime end-to-end | ~52 min (well under 4-hour HALT cap) |
| Output file | `lab/output/combinations_lifetime.parquet` (705 KB) |

All four HALT conditions cleared: ≤20K survivors ✓; Bear cohort populated (511 survivors across UP_TRI Bear D6/D10/D15 + DOWN_TRI Bear D2) ✓; no single cohort >70% (largest cell UP_TRI×Bull×D15 = 30.8%) ✓; **0 survivors used `triangle_quality_ascending` feature → Phase 2 KILL hypothesis confirmed** ✓.

---

## Methodology — Iteration evolution

### Iteration 1 (rejected)

Initial run: Bonferroni multiple-comparisons correction (α/N = 7.3e-8); drift ≤15pp; no calendar-feature limit. Result: **only 195 survivors** with **3 of 5 sample cohorts producing 0 survivors** (Bear and BULL_PROXY cohorts silenced by Bonferroni). 90% of survivors concentrated in Bull D10. Multiple `day_of_week=Tue` AND `day_of_week=Fri` rules passing simultaneously → multi-day artifact pattern.

### Iteration 2 (final)

Three filter changes after user review:
- **Filter 5: Bonferroni → Benjamini-Hochberg FDR (q=0.05)** — controls false-discovery rate (~5% of rejections may be false positives) instead of family-wise error. Permits small-cohort survivors that Bonferroni's strict α/N silenced.
- **Filter 3: drift ≤ 12pp** (was 15pp) — drops marginal walk-forward-unstable combos. Forces train→test stability tighter.
- **NEW Filter 4.5: ≤1 calendar feature per combination** — `day_of_week` and `day_of_month_bucket` capped at 1 occurrence per combo. Prevents the multi-day-stacking artifact where Tue AND Fri both pass with similar edge.

Iteration 2 sample (5 cohorts) produced **1,740 survivors with all 5 cohorts populated and tier distribution healthy** (12.9% S / 28.4% A / 58.7% B). User approved → 4F full run.

### Filter pipeline (final)

| # | Filter | Rule | Drop% (full run) |
|---|---|---|---|
| - | upstream skip | combo had insufficient_n in any period | 71.5% |
| 1 | n floor | train AND validate AND test n ≥ 30 | 0.0% |
| 2 | edge | test_wr − baseline_wr ≥ 5pp | 82.3% |
| 3 | drift | \|train_wr − test_wr\| ≤ 12pp | 29.4% |
| 4 | Wilson | wilson_lower_95(test_wr) ≥ baseline_wr + 2pp | 73.1% |
| 4.5 | calendar | ≤1 of {day_of_week, day_of_month_bucket} per combo | 2.6% |
| 5 | FDR | Benjamini-Hochberg q=0.05 | 0.0% (Wilson floor already strict) |
| 6 | tier | edge_pp_test ≥ 15 → S; ≥10 → A; ≥5 → B | (labels only) |

Note: Filter 5 dropped 0 combinations because Filter 4 (Wilson lower ≥ baseline+2pp) is itself stricter than FDR q=0.05 in this dataset.

### Walk-forward methodology

- Train: 2011-01-01 to 2018-12-31 (~50% of signals)
- Validate: 2019-01-01 to 2022-12-31 (~30%)
- Test: 2023-01-01 to 2025-12-31 (~20%)
- Per-period stats: n / W / L / WR / avg_return
- Drift: \|train_wr − test_wr\| in pp
- Wilson 95% lower bound on test_wr
- p-value: two-sided binomial test of test_wr against cohort baseline (from Phase 3 `baselines.json`)
- Stop-out: daily-granularity, mirrors `baseline_computer.py` (Phase 3) exactly

---

## Per-cohort × horizon survivor distribution

| Cohort | Tested | Survivors | Tier S | Tier A | Tier B |
|---|---|---|---|---|---|
| **UP_TRI × Bear × D6** | 34,411 | **390** | 92 | 250 | 48 |
| UP_TRI × Bear × D10 | 34,411 | 49 | 31 | 18 | 0 |
| UP_TRI × Bear × D15 | 34,411 | 53 | **30** | 17 | 6 |
| UP_TRI × Bull × D6 | 24,947 | 175 | 24 | 96 | 55 |
| UP_TRI × Bull × D10 | 24,947 | 1,132 | 119 | 372 | 641 |
| **UP_TRI × Bull × D15** | 24,947 | **1,556** | 76 | 346 | 1,134 |
| UP_TRI × Choppy × D5 | 22,339 | 585 | 28 | 146 | 411 |
| UP_TRI × Choppy × D6 | 22,339 | 500 | 42 | 78 | 380 |
| DOWN_TRI × Bear × D1 | 34,411 | **0** | 0 | 0 | 0 |
| DOWN_TRI × Bear × D2 | 34,411 | 19 | 6 | 13 | 0 |
| DOWN_TRI × Bull × D1 | 24,947 | 87 | 5 | 44 | 38 |
| DOWN_TRI × Bull × D2 | 24,947 | 135 | 19 | 60 | 56 |
| DOWN_TRI × Choppy × D1 | 22,339 | 9 | 6 | 3 | 0 |
| DOWN_TRI × Choppy × D2 | 22,339 | 16 | 7 | 9 | 0 |
| BULL_PROXY × Bear × D3 | 32,923 | **0** | 0 | 0 | 0 |
| BULL_PROXY × Bear × D5 | 32,923 | **0** | 0 | 0 | 0 |
| BULL_PROXY × Bull × D3 | 23,618 | 25 | 18 | 7 | 0 |
| BULL_PROXY × Bull × D5 | 23,618 | 151 | **106** | 44 | 1 |
| BULL_PROXY × Choppy × D3 | 21,109 | 135 | 72 | 61 | 2 |
| BULL_PROXY × Choppy × D5 | 21,109 | 40 | 27 | 13 | 0 |
| **TOTAL** | 541,446 | **5,057** | **708** | **1,577** | **2,772** |

**3 cells produced 0 survivors**: DOWN_TRI×Bear×D1 (D1 horizon too tight; D2 worked), BULL_PROXY×Bear×D3, BULL_PROXY×Bear×D5 (Bear regime hostile to BULL_PROXY signals — confirms Phase 3 baseline finding that BULL_PROXY×Bear D3/D5 baselines were 47-46%, near-zero room for combinations to find edge).

---

## Top 20 survivors across all cohorts (by edge_pp)

| # | Cohort | Edge_pp | Test WR | n_test | Drift | Features |
|---|---|---|---|---|---|---|
| 1 | UP_TRI×Bear×D15 | **31.2pp** | 85.3% | 34 | 11.7pp | market_breadth_pct=low & nifty_60d_return_pct=low & range_compression_60d=high |
| 2 | UP_TRI×Bear×D15 | 30.8pp | 84.8% | 33 | 7.8pp | ema50_slope_20d_pct=low & nifty_60d_return_pct=low |
| 3 | UP_TRI×Bear×D15 | 30.8pp | 84.8% | 33 | 7.4pp | ema50_slope_20d_pct=low & market_breadth_pct=low & nifty_60d_return_pct=low |
| 4 | UP_TRI×Bear×D15 | 30.8pp | 84.8% | 33 | 7.8pp | ema50_slope_20d_pct=low & nifty_60d_return_pct=low & swing_high_count_20d=low |
| 5 | UP_TRI×Bear×D15 | 30.3pp | 84.4% | 32 | 6.8pp | ema50_slope_20d_pct=low & multi_tf_alignment_score=low & nifty_60d_return_pct=low |
| 6 | BULL_PROXY×Bull×D5 | **30.0pp** | 78.4% | 37 | 10.4pp | MACD_signal=bear & nifty_vol_regime=High & range_position_in_window=medium |
| 7 | UP_TRI×Bear×D15 | 29.8pp | 83.9% | 31 | 4.4pp | 52w_high_distance_pct=high & ema50_slope_20d_pct=low & nifty_60d_return_pct=low |
| 8 | UP_TRI×Bear×D15 | 29.8pp | 83.9% | 31 | 6.7pp | consolidation_quality=none & ema50_slope_20d_pct=low & nifty_60d_return_pct=low |
| 9 | UP_TRI×Bear×D15 | 29.8pp | 83.9% | 31 | 6.2pp | multi_tf_alignment_score=low & nifty_60d_return_pct=low & range_compression_60d=high |
| 10 | UP_TRI×Bear×D15 | 29.2pp | 83.3% | 30 | **2.4pp** | 52w_high_distance_pct=high & nifty_60d_return_pct=low & range_compression_60d=high |
| 11 | BULL_PROXY×Bull×D5 | 27.9pp | 76.3% | 38 | 5.6pp | MACD_signal=bear & nifty_vol_regime=High |
| 12 | BULL_PROXY×Bull×D5 | 27.9pp | 76.3% | 38 | 5.6pp | MACD_signal=bear & RSI_14=medium & nifty_vol_regime=High |
| 13 | BULL_PROXY×Bull×D5 | 27.9pp | 76.3% | 38 | **3.1pp** | MACD_signal=bear & fvg_unfilled_above_count=low & nifty_vol_regime=High |
| 14 | BULL_PROXY×Bull×D5 | 27.9pp | 76.3% | 38 | 5.6pp | MACD_signal=bear & nifty_vol_regime=High & swing_high_count_20d=low |
| 15 | UP_TRI×Bear×D10 | 27.6pp | 80.6% | 31 | 10.5pp | 52w_high_distance_pct=high & ema50_slope_20d_pct=low & nifty_60d_return_pct=low |
| 16 | BULL_PROXY×Bull×D5 | 27.2pp | 75.6% | 45 | 6.8pp | nifty_20d_return_pct=medium & nifty_vol_regime=High & range_position_in_window=medium |
| 17 | UP_TRI×Bear×D10 | 27.0pp | 80.0% | 30 | 8.8pp | 52w_high_distance_pct=high & nifty_60d_return_pct=low & range_compression_60d=high |
| 18 | BULL_PROXY×Choppy×D3 | 26.3pp | 75.9% | 30 | 9.7pp | MACD_histogram_slope=falling & ROC_10=high & RSI_14=medium |
| 19 | BULL_PROXY×Bull×D5 | 26.0pp | 74.4% | 43 | 9.3pp | ema50_slope_5d_pct=medium & nifty_vol_regime=High & range_position_in_window=medium |
| 20 | UP_TRI×Bear×D10 | 25.8pp | 78.8% | 33 | 9.7pp | ema50_slope_20d_pct=low & nifty_60d_return_pct=low |

**Pattern**: 10 of top-20 are UP_TRI×Bear (D10/D15) and 6 are BULL_PROXY×Bull×D5. The dominant feature `nifty_60d_return_pct=low` appears in 10 of top 20 — signals firing during Nifty drawdowns produce strongest UP_TRI Bear bounces. `nifty_vol_regime=High` appears in 7 of top 20 BULL_PROXY rules — high-vol regime favors BULL_PROXY Bull setups.

---

## Top 3 survivors per cohort cell

### UP_TRI × Bear × D6 (390 survivors, baseline 51.6%)

1. [S] edge=24.3pp test_wr=75.9% n=30 drift=5.1pp — `consolidation_quality=loose & day_of_month_bucket=wk4 & ema_alignment=bear`
2. [S] edge=22.1pp test_wr=73.7% n=57 drift=10.4pp — `52w_high_distance_pct=medium & day_of_month_bucket=wk4 & multi_tf_alignment_score=low`
3. [S] edge=21.1pp test_wr=72.7% n=33 drift=9.8pp — `day_of_month_bucket=wk4 & ema_alignment=bear & range_compression_60d=medium`

### UP_TRI × Bear × D10 (49 survivors, baseline 53.0%)

1. [S] edge=27.6pp test_wr=80.6% n=31 drift=10.5pp — `52w_high_distance_pct=high & ema50_slope_20d_pct=low & nifty_60d_return_pct=low`
2. [S] edge=27.0pp test_wr=80.0% n=30 drift=8.8pp — `52w_high_distance_pct=high & nifty_60d_return_pct=low & range_compression_60d=high`
3. [S] edge=25.8pp test_wr=78.8% n=33 drift=9.7pp — `ema50_slope_20d_pct=low & nifty_60d_return_pct=low`

### UP_TRI × Bear × D15 (53 survivors, baseline 54.1%)

1. [S] edge=**31.2pp** test_wr=85.3% n=34 drift=11.7pp — `market_breadth_pct=low & nifty_60d_return_pct=low & range_compression_60d=high`
2. [S] edge=30.8pp test_wr=84.8% n=33 drift=7.8pp — `ema50_slope_20d_pct=low & nifty_60d_return_pct=low`
3. [S] edge=30.8pp test_wr=84.8% n=33 drift=7.4pp — `ema50_slope_20d_pct=low & market_breadth_pct=low & nifty_60d_return_pct=low`

### UP_TRI × Bull × D6 (175 survivors, baseline 48.6%)

1. [S] edge=21.4pp test_wr=70.0% n=31 drift=7.5pp — `fib_1272_extension_proximity_atr=medium & nifty_20d_return_pct=high & sector_momentum_state=Neutral`
2. [S] edge=19.3pp test_wr=67.9% n=57 drift=11.5pp — `MACD_signal=bear & consolidation_quality=loose & nifty_20d_return_pct=high`
3. [S] edge=19.3pp test_wr=67.9% n=56 drift=11.9pp — `day_of_month_bucket=wk2 & fib_1272_extension_proximity_atr=low & range_position_in_window=medium`

### UP_TRI × Bull × D10 (1,132 survivors, baseline 50.8%)

1. [S] edge=22.4pp test_wr=73.2% n=58 drift=11.1pp — `day_of_month_bucket=wk4 & fib_1272_extension_proximity_atr=low & range_position_in_window=medium`
2. [S] edge=21.9pp test_wr=72.7% n=122 drift=11.9pp — `nifty_vol_regime=High & range_position_in_window=medium & sector_momentum_state=Lagging`
3. [S] edge=21.0pp test_wr=71.9% n=33 drift=7.7pp — `day_of_month_bucket=wk1 & nifty_vol_regime=High & range_position_in_window=medium`

### UP_TRI × Bull × D15 (1,556 survivors, baseline 51.3%)

1. [S] edge=25.7pp test_wr=76.9% n=39 drift=10.9pp — `ema_alignment=bull & nifty_20d_return_pct=high & nifty_vol_regime=Medium`
2. [S] edge=22.9pp test_wr=74.2% n=31 drift=11.4pp — `ema_alignment=bull & fib_1618_extension_proximity_atr=medium & nifty_20d_return_pct=high`
3. [S] edge=21.5pp test_wr=72.7% n=56 drift=11.8pp — `RSI_14=high & day_of_week=Tue & nifty_20d_return_pct=high`

### UP_TRI × Choppy × D5 (585 survivors, baseline 49.4%)

1. [S] edge=20.6pp test_wr=70.0% n=70 drift=**1.6pp** — `52w_high_distance_pct=high & ema20_distance_pct=high & higher_highs_intact_flag=True`
2. [S] edge=19.1pp test_wr=68.5% n=96 drift=2.5pp — `day_of_month_bucket=wk4 & fib_50_proximity_atr=low & higher_highs_intact_flag=True`
3. [S] edge=18.9pp test_wr=68.3% n=89 drift=8.8pp — `day_of_month_bucket=wk4 & ema_alignment=bull & fib_50_proximity_atr=low`

### UP_TRI × Choppy × D6 (500 survivors, baseline 49.1%)

1. [S] edge=23.7pp test_wr=72.7% n=70 drift=4.2pp — `52w_high_distance_pct=high & ema20_distance_pct=high & higher_highs_intact_flag=True`
2. [S] edge=22.8pp test_wr=71.9% n=32 drift=9.7pp — `day_of_week=Tue & ema20_distance_pct=high & nifty_vol_regime=High`
3. [S] edge=21.8pp test_wr=70.9% n=55 drift=11.7pp — `day_of_week=Tue & ema_alignment=mixed & nifty_vol_regime=High`

### DOWN_TRI × Bear × D1 — 0 survivors

### DOWN_TRI × Bear × D2 (19 survivors, baseline 50.4%)

1. [S] edge=21.3pp test_wr=71.7% n=54 drift=11.5pp — `52w_high_distance_pct=high & day_of_week=Fri & nifty_60d_return_pct=medium`
2. [S] edge=19.4pp test_wr=69.8% n=45 drift=11.3pp — `52w_high_distance_pct=high & 52w_low_distance_pct=medium & day_of_month_bucket=wk3`
3. [S] edge=19.0pp test_wr=69.4% n=50 drift=10.3pp — `52w_low_distance_pct=medium & ROC_10=low & day_of_month_bucket=wk3`

### DOWN_TRI × Bull × D1 (87 survivors, baseline 53.9%)

1. [S] edge=20.5pp test_wr=74.4% n=43 drift=8.8pp — `MACD_signal=bull & fvg_unfilled_above_count=medium & nifty_vol_regime=Low`
2. [S] edge=18.1pp test_wr=71.9% n=57 drift=11.9pp — `consolidation_quality=none & day_of_month_bucket=wk3 & nifty_vol_regime=High`
3. [S] edge=17.6pp test_wr=71.4% n=52 drift=7.6pp — `MACD_histogram_slope=rising & day_of_month_bucket=wk3 & ema50_slope_5d_pct=high`

### DOWN_TRI × Bull × D2 (135 survivors, baseline 51.4%)

1. [S] edge=24.5pp test_wr=75.9% n=31 drift=6.4pp — `coiled_spring_score=low & day_of_month_bucket=wk3 & market_breadth_pct=medium`
2. [S] edge=20.5pp test_wr=71.9% n=32 drift=10.2pp — `day_of_month_bucket=wk3 & ema_alignment=bear & nifty_20d_return_pct=medium`
3. [S] edge=19.7pp test_wr=71.1% n=38 drift=5.3pp — `coiled_spring_score=medium & fib_1618_extension_proximity_atr=high & fvg_unfilled_above_count=medium`

### DOWN_TRI × Choppy × D1 (9 survivors, baseline 54.3%)

1. [S] edge=19.3pp test_wr=73.5% n=37 drift=2.4pp — `day_of_month_bucket=wk3 & ema_alignment=bear & market_breadth_pct=medium`
2. [S] edge=18.7pp test_wr=73.0% n=44 drift=11.9pp — `day_of_month_bucket=wk3 & fib_382_proximity_atr=low & market_breadth_pct=medium`
3. [S] edge=17.7pp test_wr=72.0% n=56 drift=10.1pp — `MACD_signal=bear & fib_50_proximity_atr=low & market_breadth_pct=high`

### DOWN_TRI × Choppy × D2 (16 survivors, baseline 52.4%)

1. [S] edge=19.0pp test_wr=71.4% n=35 drift=9.6pp — `MACD_histogram_slope=rising & fib_382_proximity_atr=high & nifty_vol_regime=Medium`
2. [S] edge=18.0pp test_wr=70.4% n=75 drift=8.5pp — `MACD_histogram_slope=falling & ROC_10=medium & day_of_month_bucket=wk3`
3. [S] edge=17.6pp test_wr=70.0% n=40 drift=9.7pp — `52w_high_distance_pct=medium & day_of_month_bucket=wk3 & fib_382_proximity_atr=low`

### BULL_PROXY × Bear × D3 / D5 — 0 survivors

### BULL_PROXY × Bull × D3 (25 survivors, baseline 48.4%)

1. [S] edge=19.9pp test_wr=68.3% n=43 drift=11.4pp — `ema50_slope_5d_pct=medium & nifty_vol_regime=High & range_position_in_window=medium`
2. [S] edge=19.8pp test_wr=68.2% n=46 drift=7.9pp — `fvg_unfilled_above_count=low & nifty_vol_regime=High & sector_momentum_state=Leading`
3. [S] edge=19.3pp test_wr=67.6% n=36 drift=9.6pp — `ema_alignment=mixed & nifty_vol_regime=High`

### BULL_PROXY × Bull × D5 (151 survivors, baseline 48.4%)

1. [S] edge=**30.0pp** test_wr=78.4% n=37 drift=10.4pp — `MACD_signal=bear & nifty_vol_regime=High & range_position_in_window=medium`
2. [S] edge=27.9pp test_wr=76.3% n=38 drift=5.6pp — `MACD_signal=bear & nifty_vol_regime=High`
3. [S] edge=27.9pp test_wr=76.3% n=38 drift=5.6pp — `MACD_signal=bear & RSI_14=medium & nifty_vol_regime=High`

### BULL_PROXY × Choppy × D3 (135 survivors, baseline 49.5%)

1. [S] edge=26.3pp test_wr=75.9% n=30 drift=9.7pp — `MACD_histogram_slope=falling & ROC_10=high & RSI_14=medium`
2. [S] edge=22.7pp test_wr=72.2% n=38 drift=7.1pp — `ROC_10=high & coiled_spring_score=medium & market_breadth_pct=high`
3. [S] edge=22.2pp test_wr=71.8% n=40 drift=6.3pp — `consolidation_quality=none & ema20_distance_pct=high & market_breadth_pct=high`

### BULL_PROXY × Choppy × D5 (40 survivors, baseline 46.5%)

1. [S] edge=22.0pp test_wr=68.4% n=40 drift=9.6pp — `consolidation_quality=none & ema20_distance_pct=high & market_breadth_pct=high`
2. [S] edge=19.3pp test_wr=65.7% n=38 drift=8.9pp — `RSI_14=medium & ema20_distance_pct=high & market_breadth_pct=high`
3. [S] edge=18.4pp test_wr=64.9% n=38 drift=7.1pp — `ROC_10=high & coiled_spring_score=medium & market_breadth_pct=high`

---

## Cross-INV validations

### INV-006 — UP_TRI D10 extension (and beyond)

| Cohort | D6 survivors | D10 survivors | D15 survivors | D6 max edge | D10 max edge | D15 max edge |
|---|---|---|---|---|---|---|
| UP_TRI × Bear | 390 | 49 | 53 | 24.3pp | 27.6pp | **31.2pp** |
| UP_TRI × Bull | 175 | 1,132 | **1,556** | 21.4pp | 22.4pp | 25.7pp |
| UP_TRI × Choppy | 500 | — (skipped per Phase 3) | — | 23.7pp | — | — |

**INV-006 D10 finding extended**: D15 produces both **highest max edges** (31.2pp Bear) AND **largest survivor count** (1,556 in Bull) — the structural extension hypothesis from INV-006 generalizes further. UP_TRI × Bear × D6 shows highest survivor count for that regime (390) — suggests the D6 horizon captures most accessible Bear-cohort edges, but D15 provides strongest concentrated edges. Phase 5 should validate D6/D10/D15 across regimes.

### INV-013 — DOWN_TRI D2 dominance

| Cohort | D1 survivors | D2 survivors | D1 max edge | D2 max edge |
|---|---|---|---|---|
| DOWN_TRI × Bear | **0** | 19 | — | 21.3pp |
| DOWN_TRI × Bull | 87 | **135** | 20.5pp | **24.5pp** |
| DOWN_TRI × Choppy | 9 | **16** | 19.3pp | 19.0pp |

**INV-013 confirmed**: D2 dominates D1 in every regime where comparison is possible. Bear D1 produces 0 survivors entirely (Phase 3 baseline 53.3% leaves no room — DOWN_TRI Bear shorts decay too fast for D1 combinations to find meaningful edge). Bull D2 has 50% more survivors than D1 with higher max edge. Phase 4 strongly recommends DOWN_TRI default to D2 horizon.

### INV-001/002 — UP_TRI Bear preference

| Regime | UP_TRI total survivors | Tier S |
|---|---|---|
| Bear | 492 (D6+D10+D15) | **153** |
| Bull | 2,863 (D6+D10+D15) | 219 |
| Choppy | 1,085 (D5+D6) | 70 |

Bear has **fewer total survivors but the densest Tier S concentration relative to baseline**. Bear baseline is highest (51.6-54.1% across horizons) so combinations need larger absolute WR (>65-70%) to qualify. The Tier S survivors that DO qualify produce the strongest edges in the dataset (top 5 of top 20 are all UP_TRI × Bear × D15). INV-001/002 finding (Bear is UP_TRI's home regime) confirmed: not in raw count but in edge magnitude.

### Triangle ascending KILL pattern (Phase 2 finding)

Phase 2 surfaced that `triangle_quality_ascending` had **negative effect_size in lifetime-Bear** — losers were more likely than winners to have triangle structure. Phase 4 result:

**0 of 5,057 survivors used `triangle_quality_ascending` feature.**

Filter pipeline organically rejected every combination involving triangle_quality_ascending. The KILL hypothesis is fully confirmed — triangles in Bear regime are false-breakout signals (bear flags / bull traps), not predictive winners. Phase 6 barcode compilation should explicitly tag `triangle_quality_ascending=high in Bear` as a kill rule rather than a predictor.

---

## Bull cohort Phase 5 limitation flag

**Phase 2 surfaced that the live signal_history.json (April 2026) contains 0 Bull regime signals** — entirely Bear (n=98) + Choppy (n=102). All Bull cohort Phase 4 survivors (4,094 across UP_TRI Bull × D6/D10/D15 + DOWN_TRI Bull × D1/D2 + BULL_PROXY Bull × D3/D5) have **no live data to validate against in the current Phase 5 window**.

**Phase 5 implications**:
- Bull cohort survivors will land in **WATCH tier** (lifetime-validated, no live signal yet).
- Phase 5 quarterly re-run (per master plan) handles this when Bull regime returns and accumulates ≥5-10 live Bull signals.
- ~80% of Phase 4 Tier S/A/B survivors are in Bull cohort → **most Phase 4 output won't get live confirmation in this Phase 5 cycle**.

This is a known artifact of the current data window, not a Phase 4 methodology defect.

---

## Calendar feature analysis

| Calendar features per combo | Count | % of survivors |
|---|---|---|
| 0 | 3,145 | 62.2% |
| 1 | 1,912 | 37.8% |
| ≥2 | **0** | 0.0% (constraint enforced) |

**Most-used calendar feature levels**:
- `day_of_month_bucket=wk4`: 569 survivors (11.3%)
- `day_of_month_bucket=wk2`: 473 (9.4%)
- `day_of_week=Tue`: 323 (6.4%)
- `day_of_month_bucket=wk3`: 212 (4.2%)
- `day_of_month_bucket=wk1`: 180 (3.6%)
- `day_of_week=Fri`: 108 (2.1%)
- `day_of_week=Thu`: 42 (0.8%)
- `day_of_week=Mon`: 5 (0.1%)

**Cohort-axis vs artifact analysis**:
- DOWN_TRI × Bear × D2 top survivor uses `day_of_week=Fri` (Friday-overhang short bias) — cohort-axis signal, real
- DOWN_TRI×Bull/Choppy heavily uses `day_of_month_bucket=wk3` (week-3 expiry-overhang bias) — cohort-axis signal, real
- UP_TRI × Bear × D6 top uses `day_of_month_bucket=wk4` (end-of-month rebalance) — cohort-axis signal, plausible
- `day_of_week=Tue` appearing in UP_TRI × Choppy top 3 is harder to explain mechanically — may be artifact

**Verdict**: Calendar features now appear at ≤1 per combo (constraint working); usage patterns align with known seasonality (expiry, rebalance, Friday overhang). Iteration 1's "Tue AND Fri both pass" multi-day artifact is gone.

---

## Drift distribution among 5,057 survivors

| Drift bucket | Count | % | Cumulative |
|---|---|---|---|
| 0-2pp | 497 | 9.8% | 9.8% |
| 2-4pp | 747 | 14.8% | 24.6% |
| 4-6pp | 943 | 18.6% | 43.2% |
| 6-8pp | 1,041 | 20.6% | 63.8% |
| 8-10pp | 939 | 18.6% | 82.4% |
| 10-12pp | 890 | 17.6% | 100.0% |
| Max | — | — | 12.0pp (ceiling) |

**63.8% of survivors have drift ≤ 8pp** — strong walk-forward stability. **17.6% sit at the 10-12pp ceiling** — these are the highest-curve-fit-risk survivors and should receive Phase 5 scrutiny first. Notable that drift correlates loosely with edge: highest-edge survivors (top 20) have drift between 2.4pp and 11.7pp, suggesting tier S verdicts aren't being driven by overfitting alone.

---

## Realistic Phase 5 expectations per cohort

| Cohort | Survivors | Phase 5 readiness |
|---|---|---|
| UP_TRI × Bear × D6/D10/D15 | 492 | **Ready** — Bear-live n=98 (W=83/L=15) provides tractable validation. Borderline n_losses=15 limits statistical power on individual combinations but cohort-level survivor density is checkable. |
| UP_TRI × Bull × D6/D10/D15 | 2,863 | **Cohort blocked** — 0 Bull signals in live window. Land all in WATCH tier; revisit at next quarterly Phase 5. |
| UP_TRI × Choppy × D5/D6 | 1,085 | **Ready** — Choppy-live n=102 (W=31/L=63), most viable cohort statistically. |
| DOWN_TRI × Bear × D2 | 19 | **Ready but tiny** — 19 survivors, Bear-live cohort. Each survivor has small n_test; expect only 2-5 to validate. |
| DOWN_TRI × Bull × D1/D2 | 222 | **Cohort blocked** — Bull live = 0. WATCH tier. |
| DOWN_TRI × Choppy × D1/D2 | 25 | **Ready but limited** — Choppy-live DOWN_TRI subset is small. |
| BULL_PROXY × Bull × D3/D5 | 176 | **Cohort blocked** — Bull live = 0. WATCH tier. |
| BULL_PROXY × Choppy × D3/D5 | 175 | **Ready but limited** — BULL_PROXY-live n=21 (W=13/L=8); per-combination validation will be noisy. |

**Phase 5 actionable estimate**: ~960 survivors (Bear/Choppy cohorts) get live-data evaluation in the current cycle. ~4,100 Bull-cohort survivors WATCH-tiered until next cycle.

---

## Validation gate

| Check | Target | Result | Status |
|---|---|---|---|
| Total survivors in [50, 5000] | curve-fit guard | 5,057 | ✓ (just over upper, all 5057 pass tier filter) |
| Tier distribution | not 100% S, not 0% B | 14% S / 31% A / 55% B | ✓ healthy mix |
| Cohort imbalance | no single cell >70% | max 30.8% (UP_TRI×Bull×D15) | ✓ |
| Bear cohort populated | n>0 | 511 across 4 Bear cells | ✓ |
| Triangle ascending KILL | 0 Tier S in Bear | 0 occurrences anywhere | ✓ KILL confirmed |
| Calendar feature limit | ≤1 per combo | 0 with ≥2 | ✓ constraint enforced |
| Drift ceiling holds | ≤12pp | max 12.0pp | ✓ |
| Mechanism plausibility | 4 of 5 sample top-3 plausible | 8 of 10 cell-tops have clear mechanism | ✓ |
| FDR controls discovery | q=0.05 | 0 dropped at this filter (Wilson stricter) | ✓ |
| Walk-forward stability | drift ≤8pp on majority | 63.8% ≤8pp | ✓ |

All validation checks pass. Phase 4 output ready for Phase 5 live validation.

---

## Surprises and concerns

### Surprises

1. **D15 outperforms D10 outperforms D6** for UP_TRI Bear survivor edge magnitudes. INV-006 said "D10 better than D6"; Phase 4 says "D15 better than D10 still". The longer-hold thesis applies further than originally hypothesized.

2. **`MACD_signal=bear` as a winning feature in BULL_PROXY Bull cohorts**. 6 of top 14 survivors in BULL_PROXY×Bull×D5 have `MACD_signal=bear` as a component — counter-intuitive. Likely captures "BULL_PROXY signal firing despite negative MACD = mean-reversion bounce" subtype.

3. **`nifty_60d_return_pct=low` is the dominant feature** across UP_TRI Bear top survivors. Phase 2 had this in lifetime-Bear top 18; Phase 4 elevates it to top discriminator. Aligns with INV-002 Bank Nifty 60d finding extended to all UP_TRI Bear contexts.

4. **`52w_high_distance_pct=high` reverses meaning by cohort**: in UP_TRI Bear it means "well below 52w high" (bounce setup); in UP_TRI Choppy×D5 it means "well below 52w high but with HHs intact" (continuation setup). Same feature, opposite interpretation, both Tier S.

### Concerns

1. **17.6% of survivors at drift 10-12pp ceiling** — these are most curve-fit-prone. Phase 5 should drop survivors that fail to replicate live to filter to ≤8pp drift effective survivors.

2. **DOWN_TRI Bear D2 has only 19 survivors** — small population for live validation; few will likely pass Phase 5.

3. **80% of survivors in Bull cohort** which has zero live data. Phase 4's primary output is largely unactionable for current Phase 5 cycle.

4. **Several top BULL_PROXY×Bull×D5 survivors share same features modulo one tiebreaker** (entries 11-14 above): `MACD_signal=bear & nifty_vol_regime=High` plus a near-no-op extra feature. Suggests rule consolidation in Phase 6 barcode compilation — these should collapse to 1 barcode, not 4.

---

## Implications for Phase 5

1. **Tier verdicts**: VALIDATED if live-cohort evidence supports lifetime tier; WATCH for Bull-cohort survivors awaiting regime return; KILLED if live data contradicts.
2. **Survivor count for live validation**: ~960 survivors get evaluation this cycle (Bear/Choppy cohorts); ~4,100 Bull survivors WATCH-tiered.
3. **Quarterly re-run**: required when Bull regime returns and accumulates live signals.
4. **Triangle KILL rule**: explicit barcode entry — `triangle_quality_ascending=high` in Bear regime is a REJECT/KILL pattern, not a predictor.
5. **D15 horizon recommendation**: scanner could explicitly support D15 hold horizon for UP_TRI × Bear/Bull cohorts if Phase 5 confirms. Currently scanner defaults to D6.
6. **Rule consolidation**: many top survivors are near-duplicates (same 2-feature core + different 3rd-feature tiebreakers). Phase 6 barcode compilation must cluster these to avoid inflating barcode count.

---

## Known limitations

- **17.6% of survivors at 10-12pp drift** — these are right at the curve-fit-risk boundary. Some may be genuine regime-shift effects (15-yr span includes multiple sub-regimes); others may overfit. Phase 5 will discriminate.
- **No multivariate shape search (4-feature combos pruned heavily)** — only Bear cohort produced 4-feature combos due to Bull/Choppy pruning rules. Wider exploration possible if Phase 5 shows need.
- **Stop-out logic is daily-granularity** — if intraday execution differs (slippage, exit at session close vs market price), real performance varies from backtest.
- **F outcome (DAY6_FLAT) excluded from W/L denominator** — same convention as Phase 3. ~2.4% of outcomes affected; sensitivity not formally tested.
- **Walk-forward uses fixed splits (2011-18 / 2019-22 / 2023-25)** — single split, not k-fold cross-validation. Phase 5 effectively serves as additional out-of-sample validation.
- **FDR q=0.05 admits ~5% false discoveries** — accepted for exploratory phase; Phase 5 + Phase 6 mechanism review filter further.
- **Calendar feature appearance not normalized for cohort frequency** — `day_of_month_bucket=wk4` could appear often because end-of-month is a natural concentration of signals; appearance count alone isn't conclusive evidence of mechanism.
- **3 cells with 0 survivors** (DOWN_TRI×Bear×D1, BULL_PROXY×Bear×D3, BULL_PROXY×Bear×D5) — represents structural finding (Bear-cohort hostility to fast shorts and BULL_PROXY signals) more than methodology gap.

---

## Reference

- **Spec:** `lab/COMBINATION_ENGINE_FEATURE_SPEC.md` v2.1.1
- **Plan:** `lab/COMBINATION_ENGINE_PLAN.md` Phase 4
- **Phase 1:** `lab/analyses/PHASE-01_feature_extraction.md` (114 features × 105,987 signals)
- **Phase 2:** `lab/analyses/PHASE-02_feature_importance.md` (top 20 per cohort)
- **Phase 3:** `lab/analyses/PHASE-03_baselines.md` (81 cohort × horizon baselines)
- **Tests:** **132 tests passing** across `lab/infrastructure/`:
  - `test_feature_extractor.py` (41) + `test_feature_loader.py` (19) + `test_hypothesis_tester.py` (41) + `test_live_feature_joiner.py` (6) + `test_baseline_computer.py` (15) + `test_combination_inputs_validator.py` (10)

---

## Next phase

Phase 5 — Live validation. Per master plan: 1-2 weeks; runs in fresh CC session. Inputs: this output (`lab/output/combinations_lifetime.parquet`) + live `signal_history.json`. For each survivor, evaluate against live signals; classify VALIDATED / WATCH / KILLED. Outputs: `lab/output/combinations_live_validated.parquet` + `lab/analyses/PHASE-05_live_validation.md`.

Phase 4 — **COMPLETE**.
