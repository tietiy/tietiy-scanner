# INV-002 — UP_TRI × Bank × Bear validation (small-sample hypothesis)

**Generated:** 2026-04-29T22:34:58.188288+00:00

**Branch:** backtest-lab

**Cohort filter:** signal=UP_TRI AND sector=Bank AND regime=Bear

**Hypothesis type (Lab tier evaluation):** BOOST

**Live evidence at registration:** n=8 W=8 L=0 → 100% WR

---

## ⚠️ Caveats carried forward

**Caveat 1 (sector indices missing):** Section 2b uses ^NSEBANK 60-day return as proxy for rate-cycle. Imperfect; actual RBI policy meeting calendar is out of scope.

**Caveat 2 (9.31% MS-2 miss-rate):** Lifetime cohort n is moderate (~2.6K resolved); per-sub-period n may be small (some Bear sub-periods <30 signals). Sub-period findings at small n vulnerable to Caveat 2.



## Section 1 — Lifetime cohort baseline + Bear sub-period analysis

**Total cohort signals:** 2689

**Lifetime stats:**

- n_total: 2689
- n_resolved: 2689
- n_open: 0
- n_win: 1299
- n_loss: 1160
- n_flat: 230
- wr_excl_flat: 0.5283
- wilson_lower_95: 0.5085
- p_value_vs_50: 0.005062

**Train period (2011-01 → 2022-12):**

- n_total: 2158
- n_resolved: 2158
- n_open: 0
- n_win: 1031
- n_loss: 943
- n_flat: 184
- wr_excl_flat: 0.5223
- wilson_lower_95: 0.5002
- p_value_vs_50: 0.04763

**Test period (2023-01 → 2026-04):**

- n_total: 531
- n_resolved: 531
- n_open: 0
- n_win: 268
- n_loss: 217
- n_flat: 46
- wr_excl_flat: 0.5526
- wilson_lower_95: 0.5081
- p_value_vs_50: 0.02057

**Bear sub-periods identified:** 29

**Year-by-year breakdown:**

| Year | n_resolved | n_win | n_loss | n_flat | WR_excl_flat | Wilson_lower_95 |
|------|-----------|-------|--------|--------|--------------|------------------|
| 2011 | 249 | 93 | 135 | 21 | 0.4079 | 0.3461 |
| 2012 | 131 | 95 | 29 | 7 | 0.7661 | 0.6843 |
| 2013 | 116 | 73 | 35 | 8 | 0.6759 | 0.5829 |
| 2014 | 50 | 25 | 18 | 7 | 0.5814 | 0.4333 |
| 2015 | 276 | 158 | 91 | 27 | 0.6345 | 0.5731 |
| 2016 | 236 | 89 | 127 | 20 | 0.412 | 0.3485 |
| 2017 | 5 | 4 | 0 | 1 | 1.0 | 0.5101 |
| 2018 | 294 | 190 | 76 | 28 | 0.7143 | 0.6572 |
| 2019 | 205 | 79 | 102 | 24 | 0.4365 | 0.3663 |
| 2020 | 176 | 86 | 82 | 8 | 0.5119 | 0.4369 |
| 2021 | 124 | 12 | 104 | 8 | 0.1034 | 0.0602 |
| 2022 | 296 | 127 | 144 | 25 | 0.4686 | 0.4101 |
| 2023 | 138 | 69 | 53 | 16 | 0.5656 | 0.4769 |
| 2024 | 113 | 47 | 59 | 7 | 0.4434 | 0.3524 |
| 2025 | 219 | 119 | 81 | 19 | 0.595 | 0.5258 |
| 2026 | 61 | 33 | 24 | 4 | 0.5789 | 0.4498 |

**Bear sub-period breakdown:**

| Label | Start | End | Days | Signals | n_resolved | WR_excl_flat | Wilson_lower_95 |
|-------|-------|-----|------|---------|-----------|--------------|------------------|
| 2011_Bear_05 | 2011-05-11 | 2011-06-24 | 45 | 62 | 62 | 0.5472 | 0.4145 |
| 2011_Bear_08 | 2011-08-05 | 2011-10-18 | 75 | 113 | 113 | 0.5577 | 0.4619 |
| 2011_Bear_11 | 2011-11-22 | 2012-01-12 | 52 | 123 | 123 | 0.4444 | 0.3576 |
| 2012_Bear_05 | 2012-05-08 | 2012-06-11 | 35 | 82 | 82 | 0.6282 | 0.5173 |
| 2013_Bear_03 | 2013-03-01 | 2013-03-07 | 7 | 60 | 60 | 0.7963 | 0.671 |
| 2013_Bear_03 | 2013-03-25 | 2013-04-17 | 24 | 60 | 60 | 0.7963 | 0.671 |
| 2013_Bear_06 | 2013-06-14 | 2013-07-04 | 21 | 6 | 6 | 0.8333 | 0.4365 |
| 2013_Bear_08 | 2013-08-06 | 2013-09-05 | 31 | 50 | 50 | 0.5208 | 0.3833 |
| 2014_Bear_02 | 2014-02-05 | 2014-02-20 | 16 | 50 | 50 | 0.5814 | 0.4333 |
| 2015_Bear_03 | 2015-03-30 | 2015-04-01 | 3 | 0 | 0 | None | None |
| 2015_Bear_04 | 2015-04-27 | 2015-06-19 | 54 | 74 | 74 | 0.746 | 0.6266 |
| 2015_Bear_08 | 2015-08-25 | 2015-10-01 | 38 | 104 | 104 | 0.7396 | 0.6438 |
| 2015_Bear_11 | 2015-11-13 | 2015-12-24 | 42 | 98 | 98 | 0.4444 | 0.3462 |
| 2016_Bear_01 | 2016-01-11 | 2016-03-02 | 52 | 127 | 127 | 0.459 | 0.3732 |
| 2016_Bear_11 | 2016-11-10 | 2017-01-04 | 56 | 114 | 114 | 0.3776 | 0.2879 |
| 2018_Bear_02 | 2018-02-22 | 2018-04-06 | 44 | 118 | 118 | 0.717 | 0.6248 |
| 2018_Bear_09 | 2018-09-28 | 2018-11-15 | 49 | 176 | 176 | 0.7125 | 0.638 |
| 2019_Bear_07 | 2019-07-23 | 2019-09-19 | 59 | 205 | 205 | 0.4365 | 0.3663 |
| 2020_Bear_02 | 2020-02-28 | 2020-05-27 | 90 | 176 | 176 | 0.5119 | 0.4369 |
| 2021_Bear_11 | 2021-11-30 | 2021-12-30 | 31 | 124 | 124 | 0.1034 | 0.0602 |
| 2022_Bear_02 | 2022-02-23 | 2022-03-16 | 22 | 48 | 48 | 0.4048 | 0.2704 |
| 2022_Bear_05 | 2022-05-06 | 2022-07-12 | 68 | 248 | 248 | 0.4803 | 0.4165 |
| 2023_Bear_02 | 2023-02-02 | 2023-02-13 | 12 | 115 | 115 | 0.54 | 0.4426 |
| 2023_Bear_02 | 2023-02-28 | 2023-04-03 | 35 | 115 | 115 | 0.54 | 0.4426 |
| 2023_Bear_10 | 2023-10-31 | 2023-11-09 | 10 | 23 | 23 | 0.6818 | 0.4732 |
| 2024_Bear_10 | 2024-10-28 | 2024-12-02 | 36 | 113 | 113 | 0.4434 | 0.3524 |
| 2024_Bear_12 | 2024-12-27 | 2025-03-19 | 83 | 219 | 219 | 0.595 | 0.5258 |
| 2026_Bear_01 | 2026-01-23 | 2026-02-05 | 14 | 20 | 20 | 0.4444 | 0.2456 |
| 2026_Bear_03 | 2026-03-04 | 2026-04-13 | 41 | 41 | 41 | 0.641 | 0.4842 |


## Section 2 — Mechanism-candidate analysis

### 2a — Oversold rebound (Bank Nifty RSI-14 < 30)

**Verdict:** `INCONCLUSIVE`

**Δ WR (subset A vs B):** 0.0585 (5.85 pp)

**p-value (2-prop z-test):** 0.061928

**Details:**

```json
{
  "oversold_rsi_lt_30": {
    "n_total": 317,
    "n_resolved": 317,
    "n_open": 0,
    "n_win": 167,
    "n_loss": 121,
    "n_flat": 29,
    "wr_excl_flat": 0.5799,
    "wr_excl_flat_excl_open": 0.5799,
    "wilson_lower_95": 0.5222,
    "p_value_vs_50": 0.006717
  },
  "not_oversold_rsi_gte_30": {
    "n_total": 2372,
    "n_resolved": 2372,
    "n_open": 0,
    "n_win": 1132,
    "n_loss": 1039,
    "n_flat": 201,
    "wr_excl_flat": 0.5214,
    "wr_excl_flat_excl_open": 0.5214,
    "wilson_lower_95": 0.5004,
    "p_value_vs_50": 0.045938
  },
  "verdict": "INCONCLUSIVE",
  "delta_wr": 0.0585,
  "p_value_2prop": 0.061928,
  "n_oversold_resolved": 288,
  "n_not_oversold_resolved": 2171,
  "median_rsi_at_signal": 46.98
}
```

### 2b — Rate-cycle correlation (Bank Nifty 60-day return proxy per Caveat 1)

**Verdict:** `CANDIDATE`

**Δ WR (subset A vs B):** 0.2826 (28.26 pp)

**p-value (2-prop z-test):** 0.0

**Details:**

```json
{
  "negative_60d_ret_subset": {
    "n_total": 2419,
    "n_resolved": 2419,
    "n_open": 0,
    "n_win": 1231,
    "n_loss": 980,
    "n_flat": 208,
    "wr_excl_flat": 0.5568,
    "wr_excl_flat_excl_open": 0.5568,
    "wilson_lower_95": 0.536,
    "p_value_vs_50": 0.0
  },
  "positive_60d_ret_subset": {
    "n_total": 270,
    "n_resolved": 270,
    "n_open": 0,
    "n_win": 68,
    "n_loss": 180,
    "n_flat": 22,
    "wr_excl_flat": 0.2742,
    "wr_excl_flat_excl_open": 0.2742,
    "wilson_lower_95": 0.2224,
    "p_value_vs_50": 0.0
  },
  "verdict": "CANDIDATE",
  "delta_wr": 0.2826,
  "p_value_2prop": 0.0,
  "n_negative_resolved": 2211,
  "n_positive_resolved": 248,
  "approximation_note": "Per Caveat 1, RBI rate cycle data unavailable; using ^NSEBANK 60-day return as proxy. Negative 60-day return \u2248 bear-leaning macro \u2248 rate-cut expectation window. Imperfect proxy; actual rate-cycle data is policy-meeting calendar."
}
```

### 2c — Sample-window bias (Bear sub-period WR variance)

**Verdict:** `HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT`

**Details:**

```json
{
  "n_subperiods_total": 29,
  "n_subperiods_with_signals": 28,
  "single_window_flag": false,
  "wr_min_across_subperiods": 0.1034,
  "wr_max_across_subperiods": 0.8333,
  "wr_range_across_subperiods": 0.7299,
  "subperiod_breakdown": [
    {
      "label": "2011_Bear_05",
      "n_signals": 62,
      "n_resolved": 62,
      "wr_excl_flat": 0.5472,
      "n_resolved_excl_flat": 53,
      "wilson_lower_95": 0.4145
    },
    {
      "label": "2011_Bear_08",
      "n_signals": 113,
      "n_resolved": 113,
      "wr_excl_flat": 0.5577,
      "n_resolved_excl_flat": 104,
      "wilson_lower_95": 0.4619
    },
    {
      "label": "2011_Bear_11",
      "n_signals": 123,
      "n_resolved": 123,
      "wr_excl_flat": 0.4444,
      "n_resolved_excl_flat": 117,
      "wilson_lower_95": 0.3576
    },
    {
      "label": "2012_Bear_05",
      "n_signals": 82,
      "n_resolved": 82,
      "wr_excl_flat": 0.6282,
      "n_resolved_excl_flat": 78,
      "wilson_lower_95": 0.5173
    },
    {
      "label": "2013_Bear_03",
      "n_signals": 60,
      "n_resolved": 60,
      "wr_excl_flat": 0.7963,
      "n_resolved_excl_flat": 54,
      "wilson_lower_95": 0.671
    },
    {
      "label": "2013_Bear_03",
      "n_signals": 60,
      "n_resolved": 60,
      "wr_excl_flat": 0.7963,
      "n_resolved_excl_flat": 54,
      "wilson_lower_95": 0.671
    },
    {
      "label": "2013_Bear_06",
      "n_signals": 6,
      "n_resolved": 6,
      "wr_excl_flat": 0.8333,
      "n_resolved_excl_flat": 6,
      "wilson_lower_95": 0.4365
    },
    {
      "label": "2013_Bear_08",
      "n_signals": 50,
      "n_resolved": 50,
      "wr_excl_flat": 0.5208,
      "n_resolved_excl_flat": 48,
      "wilson_lower_95": 0.3833
    },
    {
      "label": "2014_Bear_02",
      "n_signals": 50,
      "n_resolved": 50,
      "wr_excl_flat": 0.5814,
      "n_resolved_excl_flat": 43,
      "wilson_lower_95": 0.4333
    },
    {
      "label": "2015_Bear_03",
      "n_signals": 0,
      "n_resolved": 0,
      "wr_excl_flat": null,
      "n_resolved_excl_flat": 0,
      "wilson_lower_95": null
    },
    {
      "label": "2015_Bear_04",
      "n_signals": 74,
      "n_resolved": 74,
      "wr_excl_flat": 0.746,
      "n_resolved_excl_flat": 63,
      "wilson_lower_95": 0.6266
    },
    {
      "label": "2015_Bear_08",
      "n_signals": 104,
      "n_resolved": 104,
      "wr_excl_flat": 0.7396,
      "n_resolved_excl_flat": 96,
      "wilson_lower_95": 0.6438
    },
    {
      "label": "2015_Bear_11",
      "n_signals": 98,
      "n_resolved": 98,
      "wr_excl_flat": 0.4444,
      "n_resolved_excl_flat": 90,
      "wilson_lower_95": 0.3462
    },
    {
      "label": "2016_Bear_01",
      "n_signals": 127,
      "n_resolved": 127,
      "wr_excl_flat": 0.459,
      "n_resolved_excl_flat": 122,
      "wilson_lower_95": 0.3732
    },
    {
      "label": "2016_Bear_11",
      "n_signals": 114,
      "n_resolved": 114,
      "wr_excl_flat": 0.3776,
      "n_resolved_excl_flat": 98,
      "wilson_lower_95": 0.2879
    },
    {
      "label": "2018_Bear_02",
      "n_signals": 118,
      "n_resolved": 118,
      "wr_excl_flat": 0.717,
      "n_resolved_excl_flat": 106,
      "wilson_lower_95": 0.6248
    },
    {
      "label": "2018_Bear_09",
      "n_signals": 176,
      "n_resolved": 176,
      "wr_excl_flat": 0.7125,
      "n_resolved_excl_flat": 160,
      "wilson_lower_95": 0.638
    },
    {
      "label": "2019_Bear_07",
      "n_signals": 205,
      "n_resolved": 205,
      "wr_excl_flat": 0.4365,
      "n_resolved_excl_flat": 181,
      "wilson_lower_95": 0.3663
    },
    {
      "label": "2020_Bear_02",
      "n_signals": 176,
      "n_resolved": 176,
      "wr_excl_flat": 0.5119,
      "n_resolved_excl_flat": 168,
      "wilson_lower_95": 0.4369
    },
    {
      "label": "2021_Bear_11",
      "n_signals": 124,
      "n_resolved": 124,
      "wr_excl_flat": 0.1034,
      "n_resolved_excl_flat": 116,
      "wilson_lower_95": 0.0602
    },
    {
      "label": "2022_Bear_02",
      "n_signals": 48,
      "n_resolved": 48,
      "wr_excl_flat": 0.4048,
      "n_resolved_excl_flat": 42,
      "wilson_lower_95": 0.2704
    },
    {
      "label": "2022_Bear_05",
      "n_signals": 248,
      "n_resolved": 248,
      "wr_excl_flat": 0.4803,
      "n_resolved_excl_flat": 229,
      "wilson_lower_95": 0.4165
    },
    {
      "label": "2023_Bear_02",
      "n_signals": 115,
      "n_resolved": 115,
      "wr_excl_flat": 0.54,
      "n_resolved_excl_flat": 100,
      "wilson_lower_95": 0.4426
    },
    {
      "label": "2023_Bear_02",
      "n_signals": 115,
      "n_resolved": 115,
      "wr_excl_flat": 0.54,
      "n_resolved_excl_flat": 100,
      "wilson_lower_95": 0.4426
    },
    {
      "label": "2023_Bear_10",
      "n_signals": 23,
      "n_resolved": 23,
      "wr_excl_flat": 0.6818,
      "n_resolved_excl_flat": 22,
      "wilson_lower_95": 0.4732
    },
    {
      "label": "2024_Bear_10",
      "n_signals": 113,
      "n_resolved": 113,
      "wr_excl_flat": 0.4434,
      "n_resolved_excl_flat": 106,
      "wilson_lower_95": 0.3524
    },
    {
      "label": "2024_Bear_12",
      "n_signals": 219,
      "n_resolved": 219,
      "wr_excl_flat": 0.595,
      "n_resolved_excl_flat": 200,
      "wilson_lower_95": 0.5258
    },
    {
      "label": "2026_Bear_01",
      "n_signals": 20,
      "n_resolved": 20,
      "wr_excl_flat": 0.4444,
      "n_resolved_excl_flat": 18,
      "wilson_lower_95": 0.2456
    },
    {
      "label": "2026_Bear_03",
      "n_signals": 41,
      "n_resolved": 41,
      "wr_excl_flat": 0.641,
      "n_resolved_excl_flat": 39,
      "wilson_lower_95": 0.4842
    }
  ],
  "verdict": "HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT"
}
```



## Section 3 — Tier evaluation (parent BOOST)

**Parent cohort BOOST tier verdict:** `REJECT`

**Train→Test drift (pp):** 3.03

**Train stats:**

- n_total: 2158
- n_resolved: 2158
- n_open: 0
- n_win: 1031
- n_loss: 943
- n_flat: 184
- wr_excl_flat: 0.5223
- wilson_lower_95: 0.5002
- p_value_vs_50: 0.04763

**Test stats:**

- n_total: 531
- n_resolved: 531
- n_open: 0
- n_win: 268
- n_loss: 217
- n_flat: 46
- wr_excl_flat: 0.5526
- wilson_lower_95: 0.5081
- p_value_vs_50: 0.02057

**Decision log:**

- Hypothesis type: BOOST
- Train: WR=0.5223 n=1974 (W=1031 L=943)
- Test:  WR=0.5526 n=485 (W=268 L=217)
- Drift: 0.0303
- Wilson lower (train): 0.5002
- Wilson lower (test):  0.5081
- p-value vs 50% (train): 0.04763
- p-value vs 50% (test):  0.02057
- Tier verdict: REJECT
- --- Per-tier gate evaluation ---
- Tier S BOOST [FAIL]:
-   ✗ train_wr 0.5223 >= 0.75
-   ✓ train_n 1974 >= 100
-   ✗ test_wr 0.5526 >= 0.65
-   ✓ test_n 485 >= 30
-   ✓ drift 0.0303 < 0.1
-   ✗ train_wilson_lower 0.5002 >= 0.6
-   ✓ train_p_value 0.04763 < 0.05
- Tier A BOOST [FAIL]:
-   ✗ train_wr 0.5223 >= 0.65
-   ✓ train_n 1974 >= 50
-   ✓ test_wr 0.5526 >= 0.55
-   ✓ test_n 485 >= 20
-   ✓ drift 0.0303 < 0.15
-   ✓ train_wilson_lower 0.5002 >= 0.5
-   ✓ train_p_value 0.04763 < 0.05
- Tier B BOOST [FAIL]:
-   ✗ train_wr 0.5223 >= 0.6
-   ✓ train_n 1974 >= 30
-   ✓ test_wr 0.5526 >= 0.5
-   ✓ test_n 485 >= 15
-   ✓ drift 0.0303 < 0.2



## Section 4 — Headline findings (data only; NO promotion calls)

Verdicts surfaced by section:

| Section | Verdict |
|---------|--------|
| 1 - Lifetime baseline + Bear sub-period | `29 sub-periods identified` |
| 2a - Oversold rebound | `INCONCLUSIVE` |
| 2b - Rate-cycle proxy | `CANDIDATE` |
| 2c - Sample-window bias | `HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT` |
| 3 - Tier evaluation | `REJECT` |

## Open questions for next investigation (deferred to user review)

- Section 2c sub-period variance verdict drives sample-window-bias decision:
  - LOW_VARIANCE_STABLE → cohort genuinely profits across multiple Bear regimes (Tier S/A boost candidate per Section 3)
  - MODERATE_VARIANCE → some sub-period instability; lower confidence promotion
  - HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT → live n=8 likely Apr 2026-specific artifact; reject
  - INSUFFICIENT_SUBPERIODS → not enough independent Bear regimes to validate
- Section 3 BOOST tier verdict drives tier promotion candidate level (S/A/B/REJECT)
- If Section 2a Oversold CANDIDATE → consider RSI<30 as filter sub-cohort
- If Section 2b Rate-cycle CANDIDATE → flag for INV-NN with proper rate calendar (out of scope)
- Caveat 2 audit before promotion of any sub-period finding at marginal n

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change
or main-branch promotion.
