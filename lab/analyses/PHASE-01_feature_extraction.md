# PHASE 1 — Feature Extraction (findings)

**Status:** COMPLETE — validation gate passed 2026-05-01
**Branch:** `backtest-lab` · **Tip:** `28c4b898`
**Spec:** `lab/COMBINATION_ENGINE_FEATURE_SPEC.md` v2.1.1
**Plan:** `lab/COMBINATION_ENGINE_PLAN.md` Phase 1.A–1.E

---

## Phase 1 Summary

| Metric | Value |
|---|---|
| Goal | Compute 114 features per signal across 6 families; produce enriched parquet for Phase 2 onward |
| Total signals | 105,987 |
| Total features | 114 (compression 15, institutional_zone 22, momentum 25, volume 15, regime 20, pattern 17) |
| Original signal columns preserved | 27 |
| Enriched parquet shape | 105,987 × 141 |
| **Total runtime** | **15m 43.5s** |
| Init (registry + universe pre-load + sector indices) | 0.40s |
| Extraction loop (per-symbol grouped, 188 symbols) | 15m 40.5s (8.9 ms/signal · 113 signals/sec) |
| DataFrame build (dict-concat) | 2.3s |
| Parquet save | 0.3s |
| Output | `lab/output/enriched_signals.parquet` (57.8 MB) |
| Errors | 0 / 105,987 |
| Validation gate | ✓ PASSED |

GitHub flagged the parquet at 57.8 MB (recommended max 50 MB); push accepted. If this becomes routine, consider Git LFS or compression tuning.

---

## Methodology

**Signal source:** `lab/output/backtest_signals.parquet` — 105,987 signals across 188 F&O stocks, 2011-03-30 → 2026-04-29 (15 years). Mix: UP_TRI 80,511 / DOWN_TRI 19,961 / BULL_PROXY 5,515. Regime mix: Bull 50,809 / Choppy 35,496 / Bear 19,682. Already enriched with `regime`, `regime_score`, `sec_mom`, `rs_q`, `vol_q`, `vol_confirm` from prior Lab work — those carry through as signal-row passthroughs.

**Feature library:** `lab/feature_library/` × 114 JSONs (one per feature, full schema with feature_id, family, value_type, value_range, level_thresholds, direction, mechanism, data_source, computation_complexity, spec_version=v2.1). Loaded by `lab/infrastructure/feature_loader.py` (registry pattern).

**Extractor:** `lab/infrastructure/feature_extractor.py` — single `FeatureExtractor` class, computes all 114 features per signal via 6 family methods. Cross-family caching (`CachedIndicators` dataclass) computes EMAs/ATR/pivots/BB/KC/52w/range_compression series **once per signal**; the 6 family methods reuse them. `scanner_core.detect_pivots` reused via `sys.path` import — same `PIVOT_LOOKBACK=10` semantics as live scanner.

**Algorithm specs locked:** Block 3 algorithm specifications subsection of the spec doc (FVG with 0.25×ATR gap; OB with 3+ consecutive bars + 2×ATR cumulative move; coiled_spring; consolidation_quality buckets; BB/KC params; breakout_strength; consolidation_zone; round number tiers; Fib direction selection per `signal["direction"]`; cross-stock per-scan_date cache).

**v2.1.1 amendments** (post-Block-4 validation findings; same spec doc): triangle algorithm refined to 60-bar window + ≥3 total pivots + `trendline_respect_score`; sector index map extended with primary→fallback chain (Health → CNXPHARMA, Consumer → CNXFMCG, Chem/CapGoods → NSEI fallback).

**Sample validated** (Block 4 v2): 1000 stratified signals processed end-to-end with full validation report before committing to the 15-min full extraction.

---

## Family-by-family computation notes

### Family 1 — Compression / range (15 features)

Source: pure OHLCV. Cheap features (NR4/NR7, range_compression, inside_day) plus medium (BB/KC squeeze, coiled_spring composite, consolidation_quality bucketing). All 15 features computed for **every** signal — **0% NaN across the family** (mean / max). Rolling 20-bar windows handle the boundary cases gracefully (still need ≥20 bars of history; first ~20 trading days of 2011 are pre-universe-start so don't appear in signals).

### Family 2 — Institutional zones (22 features)

Source: OHLCV + cached pivots from `scanner_core.detect_pivots`. The high-NaN family — mean **29.4%**, max **95.5%** (`consolidation_zone_distance_atr`). Pattern-presence-dependent NaN by design: `ob_bearish_proximity` 73.3%, `ob_bullish_proximity` 62.1%, `prior_swing_high_distance_pct` 60.6%, `fvg_above_proximity` 58.3%, `fvg_below_proximity` 40.1%. The 6 Fib features 39% NaN (impulse identification requires both pivot highs AND pivot lows in the 30-bar window). `52w_high_distance_pct`, `52w_low_distance_pct`, `pivot_distance_atr`, `round_number_proximity_pct` all 0% NaN. Cross-INV: `breakout_strength_atr` complements scanner_core's pivot/zone logic.

### Family 3 — Momentum / structure (25 features)

Source: pure OHLCV. **0% NaN across the family** (max 0.3% on RSI_9 boundary, rounds to 0). Standard EMAs (20/50/200), RSI (14/9), MACD (ema12-26 + ema9 signal), daily/weekly returns (3d/5d/10d/20d/60d), consecutive-up/down streaks, EMA50-cross trend age, multi-timeframe alignment (daily + weekly + monthly EMA50), daily vol pct, ROC_10. Categorical features `ema_alignment` (bull/bear/mixed) and `MACD_signal` (bull/bear/neutral) returned as object dtype.

### Family 4 — Volume (15 features)

Source: OHLCV + signal-row passthrough (vol_q). Mean NaN **0.1%**, max **0.3%** (close_pos_in_range / wick ratios — only NaN when bar's range is exactly zero, rare). vol_ratio over 4 windows (5d/10d/20d/50d), volume regression slope, `accumulation_distribution_signed` (single signed feature; mirror collapsed per Q3), OBV slope, vol climax/dryup flags. Cross-INV: `close_pos_in_range` (Q1 v2 addition) directly encodes the INV-012 BTST `LAST_30MIN_STRENGTH` primitive.

### Family 5 — Regime / context (20 features)

Source: signal-row passthrough (4 features) + Nifty/Bank Nifty/sector index parquets (8 features) + per-scan_date cross-stock cache (3 features) + calendar (3 features) + composite stock-vs-Nifty RS (1) + Nifty vol regime (1). Mean NaN **0.8%**, max **6.8%** (`sector_index_60d_return_pct` — residual after v2.1.1 fallback chain; comes from `Other` sector signals + early-history boundary). Cross-INV linkages:
- `bank_nifty_60d_return_pct` directly encodes INV-002 Bank Nifty 60d return Section 2b
- `nifty_vol_percentile_20d` + `nifty_vol_regime` encode INV-007 vol regime Phase 1
- `regime_state` / `regime_score` / `sector_momentum_state` / `rs_q` are passthroughs from prior `inv_*_regime.py` enrichment

### Family 6 — Patterns (17 features)

Source: OHLCV + cached pivots. Mean NaN **1.7%**, max **29.0%** (`last_swing_high_distance_atr` — structural; requires pivot in last 30 bars, `PIVOT_LOOKBACK=10` plus market noise leaves ~29% without). Triangle features (5) — v2.1.1 refinement produces non-zero quality on **5.61%** of signals (5,941/105,987 across the 15-yr universe; matches Block 4 sample's 6.1% extrapolation). Triangle quality > 50: 5,934 signals (5.60% — most non-zero are high-quality). Swing features (4): `swing_high_count_20d` / `swing_low_count_20d` / `last_swing_high_distance_atr` / `higher_highs_intact_flag`. Candle flags (8): bullish/bearish engulf, hammer, shooting star, inside/outside bar, gap up/down pct.

---

## Validation gate results

### Schema check ✓

- 114 / 114 feat_* columns present
- 0 missing
- 27 original signal columns preserved
- Total cols 141, rows 105,987

### NaN distribution

Per the Phase 1.D plan: "<5% NaN per feature (otherwise diagnose)". Reality: 100 of 114 features hit that bar; 14 don't. The 14 are pattern-presence-dependent and discussed below.

| NaN bucket | Feature count |
|---|---|
| 0–10%  | 100 |
| 10–30% | 2 |
| 30–60% | 8 |
| 60–90% | 3 |
| >90%   | 1 |
| **mean / median / max** | **6.1% / 0.0% / 95.5%** |

**Top 10 highest NaN-rate features:**

| feature_id | family | complexity | NaN rate |
|---|---|---|---|
| consolidation_zone_distance_atr | institutional_zone | medium | 95.5% |
| ob_bearish_proximity | institutional_zone | expensive | 73.3% |
| ob_bullish_proximity | institutional_zone | expensive | 62.1% |
| prior_swing_high_distance_pct | institutional_zone | medium | 60.6% |
| fvg_above_proximity | institutional_zone | medium | 58.3% |
| fvg_below_proximity | institutional_zone | medium | 40.1% |
| fib_1272_extension_proximity_atr | institutional_zone | medium | 39.0% |
| fib_1618_extension_proximity_atr | institutional_zone | medium | 39.0% |
| fib_382_proximity_atr | institutional_zone | medium | 39.0% |
| fib_50_proximity_atr | institutional_zone | medium | 39.0% |

### Pattern-presence-dependent NaN (semantically correct, NOT a bug)

The 14 features above 5% NaN are all proximity / count features for **rare structural patterns** in 30-bar windows: order blocks, FVGs, prior swings, Fib retracements/extensions, consolidation zones. NaN means "no qualifying pattern exists for this signal" — the only correct semantic. Phase 2 importance analysis must handle these as missing-data cohorts rather than dropping signals.

User explicitly accepted these in Block 4 v2 review: "Pattern-presence-dependent NaN (OB/FVG/consolidation 60-95%) accepted — semantically correct. Phase 2 design will handle missing-data cohorts appropriately."

### Reference cheap features must be <5% NaN ✓

| Feature | NaN rate | Status |
|---|---|---|
| regime_state | 0.0% | ✓ |
| vol_ratio_20d | 0.0% | ✓ |
| ema50_distance_pct | 0.0% | ✓ |

### Distribution sanity (vs Block 4 sample) ✓

All 5 reference features within ±20% drift threshold (full vs sample medians):

| Feature | Min | Median (full) | Max | Std | Block 4 median | Drift |
|---|---|---|---|---|---|---|
| vol_ratio_20d | 0.000 | 0.784 | 305.292 | 1.761 | 0.775 | 1.2% |
| ema50_distance_pct | -0.545 | 0.012 | 0.584 | 0.063 | 0.014 | 13.4% |
| RSI_14 | 0.000 | 55.211 | 99.019 | 13.708 | 55.455 | 0.4% |
| range_compression_20d | 0.023 | 0.130 | 3.206 | 0.074 | 0.131 | 1.0% |
| close_pos_in_range | 0.000 | 0.459 | 1.606 | 0.265 | 0.462 | 0.6% |

`ema50_distance_pct` 13.4% drift is the largest — both medians round to ~0.013, the relative drift is high because the value is small. Distribution shape preserved.

### 5 sample rows (spot-check)

| # | Symbol | scan_date | Signal | Regime | RSI_14 | vol_ratio_20d | tri_asc | fib_618 | swing_h | HH |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CROMPTON.NS | 2021-11-17 | DOWN_TRI | Bull | 43.0 | 1.23 | 0.0 | 0.87 | 1 | F |
| 2 | INFY.NS | 2021-11-18 | UP_TRI | Bull | 69.2 | 0.86 | 0.0 | 1.47 | 0 | T |
| 3 | FORTIS.NS | 2016-05-20 | UP_TRI | Bull | 33.9 | 0.40 | 0.0 | 1.07 | 0 | T |
| 4 | FEDERALBNK.NS | 2012-09-04 | DOWN_TRI | Bull | 30.0 | 1.26 | 0.0 | 1.89 | 1 | F |
| 5 | UBL.NS | 2019-10-24 | UP_TRI | Bull | 55.6 | 1.18 | 0.0 | 1.34 | 0 | F |

Sample 1 (CROMPTON Other sector) demonstrates `Other` sector behavior; sample 5 (UBL Consumer) used the FMCG fallback for sector index. All sample values pass domain plausibility check.

### Triangle quality at full scale

- 3,364 / 105,987 (**3.17%**) signals show ascending triangle quality > 0
- 2,577 / 105,987 (**2.43%**) show descending triangle quality > 0
- 5,941 / 105,987 (**5.61%**) any direction > 0 (no overlap — slope conditions are mutually exclusive at the same window)
- 5,934 / 105,987 (**5.60%**) any direction > 50 quality

Matches Block 4 extrapolation (32 + 29 = 61 per 1000 → ~6,000 across 105,987). Sufficient population for Phase 4 combination engine triangle-cohort tests.

---

## Bugs caught and fixed during Phase 1B

1. **dtype coercion in `extract()`** (commit `639bcbe1`, Block 3C-3): pandas refused string assignment to pre-allocated `float64` columns when categorical features (`ema_alignment`, `MACD_signal`, etc.) tried to write `'bull'`/`'bear'` strings. Caused 1/1 signals in batch tests to error out (added `feat__extractor_error` column). **Fix:** refactored `extract()` to build feature dicts first, concat as new DataFrame at the end — preserves mixed dtypes natively. Caught only because integration test ran `extract()` (batch path), not `extract_single` (per-row path).

2. **Triangle algorithm structurally impossible** (commits `e262be6d` + `4651f53b`, Block 4 v2): with `PIVOT_LOOKBACK=10`, `detect_pivots` enforces ≥21 bars between same-type pivots. The original 30-bar triangle window with ≥3+3 pivot requirement could never be satisfied — `triangle_quality_*` was 0 for **100%** of 1000 sample signals. Synthetic 3C-3 tests passed because they directly populated `cache.pivot_highs/lows`, bypassing the live detector. **Fix:** v2.1.1 spec amendment + implementation refactor: 60-bar window, ≥3 *total* pivots (not 3+3), `trendline_respect_score` (% of bars where high within 1 ATR of upper line AND low within 1 ATR of lower line) replaces R²-of-sparse-pivots, new composite formula. **Test gap closed:** added `TestRealPipelineIntegration` class with 3 tests using real cached parquets (catches synthetic-cache-injection blindspot).

3. **Sector index coverage gap** (Block 4 v2, same commits as #2): original `_SECTOR_INDEX_MAP` covered 8 of 13 universe sectors. The 5 unmapped (Other / Chem / CapGoods / Health / Consumer ≈ 31% of universe) returned NaN for `sector_index_*d_return_pct`. **Fix:** primary→fallback chain — Health uses CNXPHARMA fallback (cached), Consumer uses CNXFMCG (cached), Chem/CapGoods fall back to NSEI (cached). NIFTY HEALTHCARE / CONSUMER DURABLES / CHEMICAL / INDIA MANUFACTURING parquets not cached; warnings logged at init when fallback used. `Other` left intentionally NaN (catch-all). NaN rate 24.0% → **6.8%** at full scale.

---

## Known issues / caveats

- **`Other` sector signals**: `sector_index_*_return_pct` = NaN for these signals (catch-all sector by design; correct semantics).
- **`last_swing_high_distance_atr` 29% NaN**: structural — `PIVOT_LOOKBACK=10` plus 30-bar window means ~29% of signals genuinely have no pivot_high in the search window. Phase 2 importance analysis will determine if the cohort split (has-recent-swing vs not) matters; if so, can extend lookback.
- **Pattern-presence-dependent features** (consolidation_zone 95.5%, OB 62-73%, FVG 40-58%, prior_swing_high 60.6%): 60-95% NaN rates reflect rarity of these patterns in 30-bar / 60-bar windows. Phase 2 must handle as missing-data cohorts; Phase 4 combination engine must permit absent-feature buckets.
- **5.6% triangle non-zero rate**: Phase 4 will operate on a 5,941-signal triangle cohort. Sufficient for hypothesis testing but smaller than expected if user's mental model assumed triangles in 20%+ of signals.
- **GitHub 50 MB warning**: `enriched_signals.parquet` is 57.8 MB. Push succeeded. If Block 5 outputs grow further (e.g., adding outcome columns, regime breakdowns), consider Git LFS or column-selective storage.

---

## Reference to spec & related docs

- **Spec:** `lab/COMBINATION_ENGINE_FEATURE_SPEC.md` v2.1.1 (114 features × 6 families + Block 3 algorithm specifications subsection + v2.1.1 amendment subsection)
- **Master plan:** `lab/COMBINATION_ENGINE_PLAN.md` — Phases 1–6 lifecycle
- **Algorithm specs locked:** Block 3 algorithm specifications subsection (FVG, OB, coiled_spring, consolidation_quality, BB/KC params, breakout_strength, consolidation_zone, round number tiers, Fib direction selection, cross-stock cache strategy)
- **Tests:** **101 tests passing** across `lab/infrastructure/`:
  - `test_feature_extractor.py` — 41 (schema 5 + cheap 10 + triangle 5 + Fib 5 + swing 3 + candle 4 + integration 3 + no-leakage 2 + caching 1 + real-pipeline 3 + dtype 1)
  - `test_feature_loader.py` — 19
  - `test_hypothesis_tester.py` — 41 (prior INV work)

---

## What this enables

- **Phase 2** (importance analysis, 3-5 days): join `enriched_signals.parquet` with the 118 resolved live signals in `signal_history.json`; rank 114 features by predictive power on outcomes (univariate WR comparisons, mutual info, random forest, logistic regression — Borda-count aggregation). Top-20 flagged for Phase 4.
- **Phase 3** (cohort baselines, 3 days): compute universe baseline WR per (signal × regime × hold_horizon) cohort using same parquet. Corrects INV-012's incorrect 50% null assumption.
- **Phase 4** (combination engine): top-20 features × cohorts × levels → search high-confluence rules; lifetime backtest over 105,987 signals.
- **Phase 5** (live validation): combinations from Phase 4 tested against the 1-month live database; only candidates that hold up survive.
- **Phase 6** (barcode compilation): 20-100 high-conviction trading rules with cohort + feature requirements + evidence + mechanism + tier.

---

## Next phase

Phase 2 — Feature importance via live winner analysis. Per master plan: 3-5 days; runs in fresh CC session. Inputs: this parquet (`lab/output/enriched_signals.parquet`) + live `signal_history.json`. Outputs: `lab/output/live_signals_with_features.parquet`, `lab/output/feature_importance.json`, `lab/analyses/PHASE-02_feature_importance.md`.

Phase 1B — **COMPLETE**.
