# INV-001 — UP_TRI × Bank × Choppy structural failure investigation

**Generated:** 2026-04-29T22:31:35.875736+00:00

**Branch:** backtest-lab

**Cohort filter:** signal=UP_TRI AND sector=Bank AND regime=Choppy

**Hypothesis type (Lab tier evaluation):** KILL

---

## ⚠️ Caveats carried forward

**Caveat 1 (sector indices missing):** 7 of 8 sector indices absent from MS-1 cache (only ^NSEBANK present). Affects Section 3b defensive-sector rotation analysis (per-cohort sector_momentum degraded; defensive UP_TRI signal generation itself is unaffected since per-stock OHLCV is present). Caveat 1 backfill deferred to future user/CC session.

**Caveat 2 (9.31% MS-2 miss-rate):** 23 of 247 live Apr 2026 signals did not regenerate in backtest. Findings at small n (<20) particularly susceptible. Tier B/A results at marginal n should be re-validated post-Caveat 2 audit before promotion. INV-001 cohort lifetime n is large (5146 resolved), so headline tier evaluation is robust to Caveat 2; per-mechanism sub-cohort findings are more vulnerable.

**Caveat 3 (score column null):** signal_replayer.py did not propagate live scoring; backtest_signals.score column is all-null. Section 2e signal-score quartile analysis returns DATA_UNAVAILABLE.



## Section 1 — Lifetime cohort baseline

**Total cohort signals:** 5186

**Lifetime stats (entire cohort):**

- n_total: 5186
- n_resolved: 5146
- n_open: 40
- n_win: 2410
- n_loss: 2212
- n_flat: 524
- wr_excl_flat: 0.5214
- wilson_lower_95: 0.507
- p_value_vs_50: 0.003587

**Train period (2011-01 → 2022-12):**

- n_total: 3437
- n_resolved: 3437
- n_open: 0
- n_win: 1672
- n_loss: 1406
- n_flat: 359
- wr_excl_flat: 0.5432
- wilson_lower_95: 0.5256
- p_value_vs_50: 2e-06

**Test period (2023-01 → 2026-04):**

- n_total: 1749
- n_resolved: 1709
- n_open: 40
- n_win: 738
- n_loss: 806
- n_flat: 165
- wr_excl_flat: 0.478
- wilson_lower_95: 0.4531
- p_value_vs_50: 0.083531

**Year-by-year breakdown:**

| Year | n_resolved | n_win | n_loss | n_flat | WR_excl_flat | Wilson_lower_95 |
|------|-----------|-------|--------|--------|--------------|------------------|
| 2011 | 231 | 100 | 115 | 16 | 0.4651 | 0.3996 |
| 2012 | 252 | 147 | 80 | 25 | 0.6476 | 0.5834 |
| 2013 | 272 | 102 | 145 | 25 | 0.413 | 0.3533 |
| 2014 | 155 | 105 | 42 | 8 | 0.7143 | 0.6365 |
| 2015 | 467 | 147 | 270 | 50 | 0.3525 | 0.3082 |
| 2016 | 164 | 87 | 67 | 10 | 0.5649 | 0.486 |
| 2017 | 316 | 161 | 100 | 55 | 0.6169 | 0.5566 |
| 2018 | 423 | 206 | 161 | 56 | 0.5613 | 0.5102 |
| 2019 | 338 | 191 | 111 | 36 | 0.6325 | 0.5767 |
| 2020 | 140 | 57 | 73 | 10 | 0.4385 | 0.3561 |
| 2021 | 180 | 104 | 63 | 13 | 0.6228 | 0.5473 |
| 2022 | 499 | 265 | 179 | 55 | 0.5968 | 0.5506 |
| 2023 | 610 | 286 | 263 | 61 | 0.5209 | 0.4792 |
| 2024 | 279 | 129 | 119 | 31 | 0.5202 | 0.4581 |
| 2025 | 529 | 218 | 263 | 48 | 0.4532 | 0.4093 |
| 2026 | 291 | 105 | 161 | 25 | 0.3947 | 0.3379 |


## Section 2 — Mechanism-candidate analysis

### 2a — PSU vs Private bank subsector

**Verdict:** `INCONCLUSIVE`

**Δ WR (subset A vs B):** 0.0244 (2.44 pp)

**p-value (2-prop z-test):** 0.314141

**Details:**

```json
{
  "psu": {
    "n_total": 666,
    "n_resolved": 660,
    "n_open": 6,
    "n_win": 327,
    "n_loss": 282,
    "n_flat": 51,
    "wr_excl_flat": 0.5369,
    "wr_excl_flat_excl_open": 0.5369,
    "wilson_lower_95": 0.4972,
    "p_value_vs_50": 0.068229
  },
  "private": {
    "n_total": 1576,
    "n_resolved": 1562,
    "n_open": 14,
    "n_win": 716,
    "n_loss": 681,
    "n_flat": 165,
    "wr_excl_flat": 0.5125,
    "wr_excl_flat_excl_open": 0.5125,
    "wilson_lower_95": 0.4863,
    "p_value_vs_50": 0.349058
  },
  "other": {
    "n_total": 2944,
    "n_resolved": 2924,
    "n_open": 20,
    "n_win": 1367,
    "n_loss": 1249,
    "n_flat": 308,
    "wr_excl_flat": 0.5226,
    "wr_excl_flat_excl_open": 0.5226,
    "wilson_lower_95": 0.5034,
    "p_value_vs_50": 0.02105
  },
  "verdict": "INCONCLUSIVE",
  "delta_wr": 0.0244,
  "p_value_2prop": 0.314141,
  "n_psu_resolved": 609,
  "n_private_resolved": 1397
}
```

### 2b — Volume profile (vol_q bucket)

**Verdict:** `INCONCLUSIVE`

**Δ WR (subset A vs B):** 0.0702 (7.02 pp)

**p-value (2-prop z-test):** 0.001429

**Details:**

```json
{
  "buckets": {
    "Average": {
      "n_total": 2786,
      "n_resolved": 2752,
      "n_open": 34,
      "n_win": 1318,
      "n_loss": 1149,
      "n_flat": 285,
      "wr_excl_flat": 0.5343,
      "wr_excl_flat_excl_open": 0.5343,
      "wilson_lower_95": 0.5145,
      "p_value_vs_50": 0.000668
    },
    "High": {
      "n_total": 1438,
      "n_resolved": 1436,
      "n_open": 2,
      "n_win": 621,
      "n_loss": 676,
      "n_flat": 139,
      "wr_excl_flat": 0.4788,
      "wr_excl_flat_excl_open": 0.4788,
      "wilson_lower_95": 0.4517,
      "p_value_vs_50": 0.126714
    },
    "Thin": {
      "n_total": 962,
      "n_resolved": 958,
      "n_open": 4,
      "n_win": 471,
      "n_loss": 387,
      "n_flat": 100,
      "wr_excl_flat": 0.549,
      "wr_excl_flat_excl_open": 0.549,
      "wilson_lower_95": 0.5155,
      "p_value_vs_50": 0.004135
    }
  },
  "comparison": "High vs Thin",
  "verdict": "INCONCLUSIVE",
  "delta_wr": 0.0702,
  "p_value_2prop": 0.001429,
  "n_high_resolved": 1297,
  "n_thin_resolved": 858
}
```

### 2c — Bank Nifty 20-day momentum at signal

**Verdict:** `INCONCLUSIVE`

**Δ WR (subset A vs B):** 0.0445 (4.45 pp)

**p-value (2-prop z-test):** 0.03235

**Details:**

```json
{
  "q1_lowest_momentum": {
    "n_total": 1300,
    "n_resolved": 1300,
    "n_open": 0,
    "n_win": 596,
    "n_loss": 575,
    "n_flat": 129,
    "wr_excl_flat": 0.509,
    "wr_excl_flat_excl_open": 0.509,
    "wilson_lower_95": 0.4804,
    "p_value_vs_50": 0.539428
  },
  "q4_highest_momentum": {
    "n_total": 1298,
    "n_resolved": 1258,
    "n_open": 40,
    "n_win": 626,
    "n_loss": 505,
    "n_flat": 127,
    "wr_excl_flat": 0.5535,
    "wr_excl_flat_excl_open": 0.5535,
    "wilson_lower_95": 0.5244,
    "p_value_vs_50": 0.000321
  },
  "q1_threshold": -0.0246,
  "q4_threshold": 0.0209,
  "verdict": "INCONCLUSIVE",
  "delta_wr": 0.0445,
  "p_value_2prop": 0.03235,
  "n_q1_resolved": 1171,
  "n_q4_resolved": 1131,
  "median_20d_return": -0.0019
}
```

### 2d — Day-of-month bucket (week 1/2/3/4)

**Verdict:** `INCONCLUSIVE`

**Δ WR (subset A vs B):** 0.0024 (0.24 pp)

**p-value (2-prop z-test):** 0.91321

**Details:**

```json
{
  "buckets": {
    "wk1": {
      "n_total": 1038,
      "n_resolved": 1038,
      "n_open": 0,
      "n_win": 533,
      "n_loss": 396,
      "n_flat": 109,
      "wr_excl_flat": 0.5737,
      "wr_excl_flat_excl_open": 0.5737,
      "wilson_lower_95": 0.5417,
      "p_value_vs_50": 7e-06
    },
    "wk2": {
      "n_total": 1368,
      "n_resolved": 1368,
      "n_open": 0,
      "n_win": 586,
      "n_loss": 611,
      "n_flat": 171,
      "wr_excl_flat": 0.4896,
      "wr_excl_flat_excl_open": 0.4896,
      "wilson_lower_95": 0.4613,
      "p_value_vs_50": 0.469931
    },
    "wk3": {
      "n_total": 1610,
      "n_resolved": 1610,
      "n_open": 0,
      "n_win": 710,
      "n_loss": 769,
      "n_flat": 131,
      "wr_excl_flat": 0.4801,
      "wr_excl_flat_excl_open": 0.4801,
      "wilson_lower_95": 0.4547,
      "p_value_vs_50": 0.124993
    },
    "wk4": {
      "n_total": 1170,
      "n_resolved": 1130,
      "n_open": 40,
      "n_win": 581,
      "n_loss": 436,
      "n_flat": 113,
      "wr_excl_flat": 0.5713,
      "wr_excl_flat_excl_open": 0.5713,
      "wilson_lower_95": 0.5407,
      "p_value_vs_50": 5e-06
    }
  },
  "comparison": "wk1 vs wk4",
  "verdict": "INCONCLUSIVE",
  "delta_wr": 0.0024,
  "p_value_2prop": 0.91321,
  "n_wk1_resolved": 929,
  "n_wk4_resolved": 1017
}
```

### 2e — Signal score quartile

**Verdict:** `DATA_UNAVAILABLE`

**Details:**

```json
{
  "verdict": "DATA_UNAVAILABLE",
  "reason": "score column is all-null in backtest_signals.parquet (live scoring not replayed in MS-2)"
}
```

### 2f — Calendar proximity (per safe-default 5)

**Verdict:** `SEE_SECTION_2D`

**Details:**

```json
{
  "approximation_note": "Per safe-default 5, day-of-month buckets used as proxy for monthly expiry / earnings windows. Cannot fetch RBI policy or earnings calendar (out of scope). Section 2d already provides this analysis with same bucketing scheme; flagging here for clarity.",
  "see_section": "2d (time of month)",
  "verdict": "SEE_SECTION_2D"
}
```



## Section 3 — Inverse pattern search

### 3a — DOWN_TRI Bank Choppy on INV-001 LOSER dates (SHORT-direction)

**Verdict:** `NO_INVERSE_SIGNAL`

**Details:**

```json
{
  "loser_dates_count": 621,
  "down_tri_entries_on_loser_dates": 491,
  "inverse_short_stats": {
    "wr_excl_flat": 0.4626,
    "n_win": 204,
    "n_loss": 237,
    "n_flat": 50,
    "n_open": 0,
    "wilson_lower_95": 0.4166,
    "p_value_vs_50": 0.116083
  },
  "verdict": "NO_INVERSE_SIGNAL",
  "method_note": "DOWN_TRI outcomes in backtest_signals.parquet are LONG-direction (per signal_replayer.compute_d6_outcome design). Inverted W\u2194L for SHORT-trade interpretation. STOP_HIT (LONG hit stop = price dropped sharply) maps to SHORT WIN; TARGET_HIT (price ran up) maps to SHORT LOSS."
}
```

### 3b — Defensive sector UP_TRI on same loser dates

**Verdict:** `NO_INVERSE_SIGNAL`

**Details:**

```json
{
  "loser_dates_count": 621,
  "defensive_signals_on_loser_dates": 5827,
  "defensive_stats": {
    "n_total": 5827,
    "n_resolved": 5827,
    "n_open": 0,
    "n_win": 2593,
    "n_loss": 2549,
    "n_flat": 685,
    "wr_excl_flat": 0.5043,
    "wr_excl_flat_excl_open": 0.5043,
    "wilson_lower_95": 0.4906,
    "p_value_vs_50": 0.539478
  },
  "verdict": "NO_INVERSE_SIGNAL",
  "by_sector_breakdown": {
    "Pharma": {
      "n_total": 1755,
      "n_resolved": 1755,
      "n_open": 0,
      "n_win": 776,
      "n_loss": 759,
      "n_flat": 220,
      "wr_excl_flat": 0.5055,
      "wr_excl_flat_excl_open": 0.5055,
      "wilson_lower_95": 0.4805,
      "p_value_vs_50": 0.664357
    },
    "Energy": {
      "n_total": 2173,
      "n_resolved": 2173,
      "n_open": 0,
      "n_win": 956,
      "n_loss": 991,
      "n_flat": 226,
      "wr_excl_flat": 0.491,
      "wr_excl_flat_excl_open": 0.491,
      "wilson_lower_95": 0.4688,
      "p_value_vs_50": 0.427659
    },
    "FMCG": {
      "n_total": 1899,
      "n_resolved": 1899,
      "n_open": 0,
      "n_win": 861,
      "n_loss": 799,
      "n_flat": 239,
      "wr_excl_flat": 0.5187,
      "wr_excl_flat_excl_open": 0.5187,
      "wilson_lower_95": 0.4946,
      "p_value_vs_50": 0.128077
    }
  },
  "caveat_note": "Caveat 1 (per safe-default 8): 7 sector indices absent from cache; sector_momentum falls back to Neutral for non-Bank sectors. Defensive-sector signal generation itself is unaffected (per-stock OHLCV present in cache); however per-cohort sector_momentum filter is degraded."
}
```

### 3c — BULL_PROXY Bank 2-3 days after failed UP_TRI

**Verdict:** `NO_INVERSE_SIGNAL`

**Details:**

```json
{
  "loser_dates_count": 621,
  "target_followup_dates_count": 632,
  "bull_proxy_signals_on_followup": 182,
  "bull_proxy_stats": {
    "n_total": 182,
    "n_resolved": 180,
    "n_open": 2,
    "n_win": 79,
    "n_loss": 94,
    "n_flat": 7,
    "wr_excl_flat": 0.4566,
    "wr_excl_flat_excl_open": 0.4566,
    "wilson_lower_95": 0.3842,
    "p_value_vs_50": 0.254108
  },
  "verdict": "NO_INVERSE_SIGNAL"
}
```



## Section 4 — Tier evaluation (parent KILL + sub-cohort FILTER)

**Parent cohort KILL tier verdict:** `REJECT`

**Train→Test drift (pp):** 6.52

**Train stats:**

- n_total: 3437
- n_resolved: 3437
- n_open: 0
- n_win: 1672
- n_loss: 1406
- n_flat: 359
- wr_excl_flat: 0.5432
- wilson_lower_95: 0.5256
- p_value_vs_50: 2e-06

**Test stats:**

- n_total: 1749
- n_resolved: 1709
- n_open: 40
- n_win: 738
- n_loss: 806
- n_flat: 165
- wr_excl_flat: 0.478
- wilson_lower_95: 0.4531
- p_value_vs_50: 0.083531

**Decision log:**

- Hypothesis type: KILL
- Train: WR=0.5432 n=3078 (W=1672 L=1406)
- Test:  WR=0.478 n=1544 (W=738 L=806)
- Drift: 0.0652
- Wilson lower (train): 0.5256
- Wilson lower (test):  0.4531
- p-value vs 50% (train): 2e-06
- p-value vs 50% (test):  0.083531
- Tier verdict: REJECT



## Section 5 — Ground-truth validation (GTB-002)

**Verdict:** `GATE_4_PASS`

**Prevented losses:** 14 | **Suppressed winners:** 2 | **Flat:** 1

**Ratio (prevented/suppressed):** 7.0

**Counterfactual P&L delta (pct):** 46.56

**P&L prevented (sum, pct):** -54.21

**P&L suppressed (sum, pct):** 7.65



## Section 6 — Headline findings (data only; NO promotion calls)

Verdicts surfaced by section (per safe-default thresholds):

| Section | Verdict |
|---------|--------|
| 1 - Lifetime baseline | `see lifetime stats` |
| 2a - PSU vs Private | `INCONCLUSIVE` |
| 2b - Volume profile | `INCONCLUSIVE` |
| 2c - Bank Nifty momentum | `INCONCLUSIVE` |
| 2d - Time of month | `INCONCLUSIVE` |
| 2e - Signal score (DATA_UNAVAILABLE) | `DATA_UNAVAILABLE` |
| 2f - Calendar proximity | `SEE_SECTION_2D` |
| 3a - DOWN_TRI inverse | `NO_INVERSE_SIGNAL` |
| 3b - Defensive sector rotation | `NO_INVERSE_SIGNAL` |
| 3c - BULL_PROXY post-failure | `NO_INVERSE_SIGNAL` |
| 4 - Tier evaluation | `REJECT` |
| 5 - GTB-002 validation | `GATE_4_PASS` |

## Open questions for next investigation (deferred to user review)

- Section 4 parent KILL tier verdict drives kill_002 conviction-tag decision
- Section 5 GTB-002 verdict drives Gate 4 pass/fail for kill_002
- If 2a PSU vs Private CANDIDATE → consider sub-cohort kill rather than parent kill
- If 3a DOWN_TRI shows PROFITABLE_INVERSE → boost-pattern candidate worth INV-NN follow-up
- Caveat 1 backfill before INV-003 (matrix scan) regardless of INV-001 outcome
- Caveat 2 audit before promotion of any sub-cohort tier B/A finding at marginal n
- Bank Nifty momentum at signal time (Section 2c) may be the dominant differentiator;
  cross-check with Volume profile (2b) for compound filter candidates in INV-NN

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change
or main-branch promotion.
