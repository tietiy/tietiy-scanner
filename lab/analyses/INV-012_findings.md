# INV-012 — BTST signal discovery (4 detectors × 3 hold variants)

**Generated:** 2026-04-30T20:06:48.906853+00:00

**Branch:** backtest-lab

**Detectors tested:** BTST_LAST_30MIN_STRENGTH, BTST_SECTOR_LEADER_ROTATION, BTST_POST_PULLBACK_RESUMPTION, BTST_INSIDE_DAY_BREAKOUT

**Hold variants:** HOLD_OPEN, HOLD_CLOSE, HOLD_D2

**Total cells:** 12 (4 × 3)

---

## ⚠️ Caveats

**Direction:** all BTST signals are LONG (entry at signal-day close, exit at next-day open / next-day close / D2 close). Outcome semantics use LONG D6-style logic adapted for BTST hold periods.

**Stop logic:** initial stop = entry × 0.97 (3% below; tighter than swing because shorter hold). Stop hit if any low ≤ stop_price during hold window. Gap-down through stop on T+1 open treated as STOP_HIT for HOLD_OPEN variant.

**FLAT threshold:** ±0.5% pnl_pct (matches signal_replayer convention).

**Caveat 2 (9.31% MS-2 miss-rate)** is INV-012-specific because this investigation builds detectors directly from cache. Cache miss-rate (yfinance gaps) may affect detection at margin.

**Detector 2 sector_momentum coverage:** only 8 sectors have sector_momentum data (Bank, IT, Pharma, Auto, Metal, Energy, FMCG, Infra). Stocks in non-indexed sectors (CapGoods, Consumer, Health, Other, Chem) are skipped for Detector 2.

**Detector 3 UP_TRI history dependency:** post-pullback resumption requires a prior UP_TRI W signal; depends on backtest_signals.parquet outcome integrity (Caveat 2 inheritance).

**Detector 4 inside-day breakout:** signal fires on inside-day; gap-up confirmation is embedded in HOLD_OPEN pnl rather than gating the signal. Pure inside-day breakouts (without next-day gap-up) produce HOLD_OPEN pnl ≈ 0 or negative.

---

## Section 1 — Methodology

**Detector 1 — BTST_LAST_30MIN_STRENGTH:** close_pos_in_range ≥ 0.75; close > prior 5-day high; volume > 1.5× prior 20-day avg volume.

**Detector 2 — BTST_SECTOR_LEADER_ROTATION:** today's sector_momentum = Leading; 5-trading-days-ago momentum = Lagging or Neutral; close_pos_in_range ≥ 0.7.

**Detector 3 — BTST_POST_PULLBACK_RESUMPTION:** UP_TRI W (DAY6_WIN or TARGET_HIT) within past 5 days; pullback 3.0-5.0% from highest close in window; today's close > prior 3-day high.

**Detector 4 — BTST_INSIDE_DAY_BREAKOUT:** today's range fully inside yesterday's range (today_high ≤ prev_high AND today_low ≥ prev_low). Gap-up confirmation embedded in HOLD_OPEN pnl, not gating the signal.

**Hold variants (entry = signal-day close):**
- HOLD_OPEN: exit at next-day open (T+1 open)
- HOLD_CLOSE: exit at next-day close (T+1 close)
- HOLD_D2: exit at T+2 close

**Stop:** entry × 0.97 (3% below). Stop hit if any low ≤ stop_price during hold.

---

## Section 2 — Detection diagnostics

**Total signal records:** 134848 across all 4 detectors

**Per-detector signal counts:**

| Detector | n |
|---|---|
| BTST_LAST_30MIN_STRENGTH | 16727 |
| BTST_SECTOR_LEADER_ROTATION | 15603 |
| BTST_POST_PULLBACK_RESUMPTION | 605 |
| BTST_INSIDE_DAY_BREAKOUT | 101913 |

**Distribution by year:**

| Year | Total | BTST_LAST_30MIN_STRENGTH | BTST_SECTOR_LEADER_ROTATION | BTST_POST_PULLBACK_RESUMPTION | BTST_INSIDE_DAY_BREAKOUT |
|---|---|---|---|---|---|
| 2011 | 7555 | 601 | 764 | 31 | 6159 |
| 2012 | 8155 | 928 | 925 | 24 | 6278 |
| 2013 | 7876 | 744 | 834 | 29 | 6269 |
| 2014 | 8204 | 1046 | 790 | 41 | 6327 |
| 2015 | 7889 | 805 | 894 | 45 | 6145 |
| 2016 | 7845 | 820 | 766 | 35 | 6224 |
| 2017 | 9423 | 1270 | 1118 | 32 | 7003 |
| 2018 | 8765 | 941 | 964 | 50 | 6810 |
| 2019 | 9367 | 973 | 1078 | 58 | 7258 |
| 2020 | 9809 | 1441 | 997 | 57 | 7314 |
| 2021 | 9744 | 1421 | 946 | 38 | 7339 |
| 2022 | 8983 | 1284 | 1211 | 33 | 6455 |
| 2023 | 9745 | 1580 | 1136 | 25 | 7004 |
| 2024 | 9436 | 1323 | 1215 | 49 | 6849 |
| 2025 | 9120 | 1159 | 1412 | 46 | 6503 |
| 2026 | 2932 | 391 | 553 | 12 | 1976 |

**Top 8 sectors by total signal count:**

| Sector | Total |
|---|---|
| Bank | 25493 |
| Energy | 12761 |
| FMCG | 12643 |
| Pharma | 12187 |
| IT | 10697 |
| Chem | 10608 |
| Metal | 10433 |
| Auto | 10321 |

---

## Section 3 — Per-cell lifetime + tier evaluation (12 cells)

| Detector | Hold | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Train_WR | Test_WR | Drift_pp | BoostTier | KillTier |
|----------|------|-------------|-----|--------------|-------------|----------|---------|----------|----------|----------|
| BTST_LAST_30MIN_STRENGTH | HOLD_OPEN | 8597 | 0.7715 | 0.7626 | 0.3827 | 0.7678 | 0.7842 | 1.64 | S | REJECT |
| BTST_LAST_30MIN_STRENGTH | HOLD_CLOSE | 13261 | 0.481 | 0.4725 | 0.2075 | 0.4754 | 0.4979 | 2.25 | REJECT | REJECT |
| BTST_LAST_30MIN_STRENGTH | HOLD_D2 | 14365 | 0.4566 | 0.4485 | 0.2346 | 0.4483 | 0.4803 | 3.2 | REJECT | REJECT |
| BTST_SECTOR_LEADER_ROTATION | HOLD_OPEN | 6426 | 0.6948 | 0.6835 | 0.2228 | 0.6754 | 0.7602 | 8.48 | A | REJECT |
| BTST_SECTOR_LEADER_ROTATION | HOLD_CLOSE | 11564 | 0.5127 | 0.5036 | 0.197 | 0.504 | 0.5373 | 3.33 | REJECT | REJECT |
| BTST_SECTOR_LEADER_ROTATION | HOLD_D2 | 12951 | 0.5003 | 0.4917 | 0.2797 | 0.4889 | 0.5313 | 4.24 | REJECT | REJECT |
| BTST_POST_PULLBACK_RESUMPTION | HOLD_OPEN | 344 | 0.7297 | 0.6804 | 0.3678 | 0.6978 | 0.8636 | 16.58 | B | REJECT |
| BTST_POST_PULLBACK_RESUMPTION | HOLD_CLOSE | 491 | 0.5275 | 0.4833 | 0.2811 | 0.5274 | 0.5278 | 0.04 | REJECT | REJECT |
| BTST_POST_PULLBACK_RESUMPTION | HOLD_D2 | 521 | 0.476 | 0.4335 | 0.367 | 0.461 | 0.5315 | 7.05 | REJECT | REJECT |
| BTST_INSIDE_DAY_BREAKOUT | HOLD_OPEN | 42419 | 0.6689 | 0.6645 | 0.1851 | 0.6604 | 0.7109 | 5.05 | A | REJECT |
| BTST_INSIDE_DAY_BREAKOUT | HOLD_CLOSE | 74658 | 0.4901 | 0.4865 | 0.069 | 0.4873 | 0.5007 | 1.34 | REJECT | REJECT |
| BTST_INSIDE_DAY_BREAKOUT | HOLD_D2 | 84213 | 0.4793 | 0.4759 | 0.1467 | 0.4755 | 0.4932 | 1.77 | REJECT | REJECT |

**Cells earning Lab tier (S/A/B):** 4 of 12
- `BTST_LAST_30MIN_STRENGTH × HOLD_OPEN` (n=8597, WR=0.7715) → BOOST S
- `BTST_SECTOR_LEADER_ROTATION × HOLD_OPEN` (n=6426, WR=0.6948) → BOOST A
- `BTST_POST_PULLBACK_RESUMPTION × HOLD_OPEN` (n=344, WR=0.7297) → BOOST B
- `BTST_INSIDE_DAY_BREAKOUT × HOLD_OPEN` (n=42419, WR=0.6689) → BOOST A

---

## Section 4 — Sub-cohort breakdown (cells with n ≥ 200 only)

### BTST_LAST_30MIN_STRENGTH × HOLD_OPEN

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| CapGoods | Bull | 370 | 0.8703 | 0.8322 | S | REJECT |
| Pharma | Bull | 316 | 0.8418 | 0.7975 | S | REJECT |
| Chem | Bull | 459 | 0.8344 | 0.7977 | A | REJECT |
| Health | Choppy | 36 | 0.8333 | 0.6811 | REJECT | REJECT |
| Energy | Bull | 554 | 0.8159 | 0.7815 | S | REJECT |
| CapGoods | Choppy | 181 | 0.8066 | 0.743 | B | REJECT |
| Other | Bull | 346 | 0.8064 | 0.7614 | S | REJECT |
| Bank | Bull | 1020 | 0.8049 | 0.7795 | S | REJECT |
| Health | Bull | 106 | 0.8019 | 0.716 | A | REJECT |
| Pharma | Choppy | 181 | 0.8011 | 0.737 | S | REJECT |
| Auto | Bull | 361 | 0.8006 | 0.7563 | S | REJECT |
| Metal | Bull | 456 | 0.7982 | 0.759 | S | REJECT |
| Energy | Choppy | 223 | 0.7892 | 0.731 | A | REJECT |
| IT | Bull | 319 | 0.7774 | 0.7286 | S | REJECT |
| CapGoods | Bear | 92 | 0.7717 | 0.6761 | A | REJECT |
| Bank | Choppy | 496 | 0.7581 | 0.7185 | A | REJECT |
| Chem | Choppy | 237 | 0.7553 | 0.6968 | A | REJECT |
| FMCG | Bull | 310 | 0.7548 | 0.704 | S | REJECT |
| Other | Choppy | 134 | 0.7537 | 0.6744 | A | REJECT |
| Infra | Bull | 307 | 0.7524 | 0.7012 | B | REJECT |
| Metal | Choppy | 253 | 0.751 | 0.6942 | A | REJECT |
| IT | Choppy | 176 | 0.7273 | 0.6571 | A | REJECT |
| Pharma | Bear | 103 | 0.7087 | 0.6148 | REJECT | REJECT |
| Auto | Choppy | 212 | 0.6887 | 0.6235 | REJECT | REJECT |
| FMCG | Choppy | 201 | 0.6866 | 0.6194 | A | REJECT |
| Other | Bear | 59 | 0.678 | 0.551 | REJECT | REJECT |
| Energy | Bear | 128 | 0.6719 | 0.5866 | REJECT | REJECT |
| Infra | Choppy | 143 | 0.6713 | 0.5907 | A | REJECT |
| Metal | Bear | 128 | 0.6641 | 0.5785 | A | REJECT |
| Chem | Bear | 100 | 0.66 | 0.5628 | REJECT | REJECT |
| FMCG | Bear | 94 | 0.6596 | 0.5592 | B | REJECT |
| Auto | Bear | 86 | 0.6512 | 0.5459 | REJECT | REJECT |
| Infra | Bear | 45 | 0.6444 | 0.4984 | REJECT | REJECT |
| Bank | Bear | 199 | 0.6432 | 0.5745 | A | REJECT |
| IT | Bear | 78 | 0.641 | 0.5303 | B | REJECT |

**Sub-cohort tier hits in this cell:** 27 of 35

### BTST_LAST_30MIN_STRENGTH × HOLD_CLOSE

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Pharma | Bear | 162 | 0.5617 | 0.4848 | REJECT | REJECT |
| Bank | Choppy | 747 | 0.5355 | 0.4996 | REJECT | REJECT |
| Other | Bear | 83 | 0.5301 | 0.4238 | REJECT | REJECT |
| IT | Bear | 117 | 0.5299 | 0.44 | REJECT | REJECT |
| Auto | Bear | 143 | 0.5245 | 0.4431 | REJECT | REJECT |
| Health | Bull | 158 | 0.519 | 0.4416 | REJECT | REJECT |
| Energy | Choppy | 357 | 0.5126 | 0.4609 | REJECT | REJECT |
| Other | Choppy | 225 | 0.5067 | 0.4418 | REJECT | REJECT |
| Infra | Bull | 527 | 0.5028 | 0.4603 | REJECT | REJECT |
| Infra | Choppy | 238 | 0.5 | 0.437 | REJECT | REJECT |
| Metal | Choppy | 375 | 0.4987 | 0.4483 | REJECT | REJECT |
| CapGoods | Bull | 571 | 0.4956 | 0.4548 | REJECT | REJECT |
| Pharma | Bull | 563 | 0.4938 | 0.4527 | REJECT | REJECT |
| Pharma | Choppy | 302 | 0.4934 | 0.4374 | REJECT | REJECT |
| Metal | Bull | 624 | 0.4904 | 0.4513 | REJECT | REJECT |
| Chem | Bull | 619 | 0.4895 | 0.4503 | REJECT | REJECT |
| Energy | Bear | 186 | 0.4892 | 0.4184 | REJECT | REJECT |
| CapGoods | Bear | 127 | 0.4882 | 0.4029 | REJECT | REJECT |
| Energy | Bull | 777 | 0.4878 | 0.4528 | REJECT | REJECT |
| Chem | Choppy | 345 | 0.487 | 0.4346 | REJECT | REJECT |
| Bank | Bull | 1549 | 0.4835 | 0.4587 | REJECT | REJECT |
| IT | Bull | 505 | 0.4772 | 0.434 | REJECT | REJECT |
| CapGoods | Choppy | 278 | 0.4748 | 0.4169 | REJECT | REJECT |
| Auto | Bull | 610 | 0.4705 | 0.4312 | REJECT | REJECT |
| FMCG | Choppy | 337 | 0.4599 | 0.4075 | REJECT | REJECT |
| Bank | Bear | 286 | 0.451 | 0.3944 | REJECT | REJECT |
| FMCG | Bear | 162 | 0.4506 | 0.376 | REJECT | REJECT |
| Auto | Choppy | 318 | 0.4497 | 0.3959 | REJECT | REJECT |
| Other | Bull | 478 | 0.4414 | 0.3975 | REJECT | REJECT |
| IT | Choppy | 298 | 0.4362 | 0.3811 | REJECT | REJECT |
| Health | Choppy | 85 | 0.4353 | 0.335 | REJECT | REJECT |
| Health | Bear | 33 | 0.4242 | 0.2724 | REJECT | REJECT |
| Metal | Bear | 175 | 0.4229 | 0.3521 | REJECT | REJECT |
| Chem | Bear | 142 | 0.4155 | 0.3377 | REJECT | REJECT |
| FMCG | Bull | 570 | 0.4088 | 0.3692 | REJECT | REJECT |
| Infra | Bear | 84 | 0.381 | 0.2845 | REJECT | REJECT |
| Consumer | Bull | 36 | 0.3611 | 0.2248 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 37

### BTST_LAST_30MIN_STRENGTH × HOLD_D2

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Pharma | Bear | 180 | 0.5556 | 0.4826 | REJECT | REJECT |
| Bank | Choppy | 828 | 0.5072 | 0.4732 | REJECT | REJECT |
| Infra | Choppy | 265 | 0.4943 | 0.4347 | REJECT | REJECT |
| Metal | Choppy | 397 | 0.4937 | 0.4448 | REJECT | REJECT |
| CapGoods | Choppy | 304 | 0.4934 | 0.4377 | REJECT | REJECT |
| FMCG | Bear | 175 | 0.4857 | 0.4128 | REJECT | REJECT |
| Auto | Bear | 160 | 0.4813 | 0.4052 | REJECT | REJECT |
| Infra | Bull | 562 | 0.4786 | 0.4376 | REJECT | REJECT |
| Auto | Bull | 658 | 0.4757 | 0.4378 | REJECT | REJECT |
| Chem | Bull | 660 | 0.4742 | 0.4364 | REJECT | REJECT |
| Health | Choppy | 89 | 0.4719 | 0.3715 | REJECT | REJECT |
| Energy | Bear | 191 | 0.4712 | 0.4017 | REJECT | REJECT |
| Auto | Choppy | 346 | 0.4711 | 0.4191 | REJECT | REJECT |
| Health | Bull | 175 | 0.4686 | 0.3961 | REJECT | REJECT |
| CapGoods | Bear | 131 | 0.4656 | 0.3824 | REJECT | REJECT |
| Other | Choppy | 243 | 0.465 | 0.4033 | REJECT | REJECT |
| Pharma | Bull | 611 | 0.4615 | 0.4224 | REJECT | REJECT |
| Chem | Bear | 146 | 0.4589 | 0.3802 | REJECT | REJECT |
| Bank | Bull | 1667 | 0.4577 | 0.4339 | REJECT | REJECT |
| IT | Bull | 557 | 0.456 | 0.4151 | REJECT | REJECT |
| Energy | Choppy | 372 | 0.4543 | 0.4044 | REJECT | REJECT |
| Bank | Bear | 307 | 0.4528 | 0.398 | REJECT | REJECT |
| Metal | Bull | 681 | 0.4523 | 0.4153 | REJECT | REJECT |
| Energy | Bull | 856 | 0.4498 | 0.4167 | REJECT | REJECT |
| Other | Bear | 96 | 0.4479 | 0.3524 | REJECT | REJECT |
| Pharma | Choppy | 340 | 0.4412 | 0.3893 | REJECT | REJECT |
| Other | Bull | 515 | 0.435 | 0.3928 | REJECT | REJECT |
| CapGoods | Bull | 615 | 0.4309 | 0.3923 | REJECT | REJECT |
| FMCG | Choppy | 363 | 0.4298 | 0.3798 | REJECT | REJECT |
| Chem | Choppy | 400 | 0.4275 | 0.3799 | REJECT | REJECT |
| IT | Bear | 121 | 0.4215 | 0.3372 | REJECT | REJECT |
| IT | Choppy | 315 | 0.4063 | 0.3536 | REJECT | REJECT |
| FMCG | Bull | 607 | 0.402 | 0.3637 | REJECT | REJECT |
| Infra | Bear | 94 | 0.3723 | 0.2814 | REJECT | B |
| Metal | Bear | 188 | 0.3723 | 0.3064 | REJECT | B |
| Consumer | Bull | 42 | 0.3571 | 0.2299 | REJECT | REJECT |
| Health | Bear | 36 | 0.3056 | 0.18 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 2 of 37

### BTST_SECTOR_LEADER_ROTATION × HOLD_OPEN

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Pharma | Bull | 309 | 0.7961 | 0.7477 | S | REJECT |
| Pharma | Choppy | 241 | 0.7759 | 0.7192 | S | REJECT |
| Energy | Bull | 396 | 0.7576 | 0.713 | B | REJECT |
| Metal | Choppy | 263 | 0.7529 | 0.6973 | A | REJECT |
| Bank | Bull | 916 | 0.7511 | 0.7221 | A | REJECT |
| Energy | Choppy | 303 | 0.7426 | 0.6905 | A | REJECT |
| Metal | Bear | 148 | 0.7365 | 0.6602 | S | REJECT |
| Auto | Choppy | 254 | 0.7323 | 0.6747 | A | REJECT |
| FMCG | Bear | 92 | 0.7174 | 0.6181 | REJECT | REJECT |
| Infra | Bull | 268 | 0.7164 | 0.6597 | REJECT | REJECT |
| Auto | Bull | 279 | 0.6918 | 0.6353 | A | REJECT |
| Pharma | Bear | 74 | 0.6892 | 0.5766 | REJECT | REJECT |
| FMCG | Choppy | 220 | 0.6682 | 0.6035 | A | REJECT |
| Metal | Bull | 349 | 0.6619 | 0.6107 | REJECT | REJECT |
| IT | Bear | 168 | 0.6607 | 0.5862 | B | REJECT |
| Bank | Choppy | 695 | 0.6403 | 0.6039 | B | REJECT |
| IT | Bull | 260 | 0.6308 | 0.5706 | B | REJECT |
| Energy | Bear | 146 | 0.6301 | 0.5494 | REJECT | REJECT |
| FMCG | Bull | 302 | 0.6291 | 0.5734 | B | REJECT |
| Infra | Choppy | 269 | 0.6171 | 0.5577 | B | REJECT |
| Bank | Bear | 150 | 0.6067 | 0.5268 | REJECT | REJECT |
| IT | Choppy | 159 | 0.6038 | 0.5262 | REJECT | REJECT |
| Infra | Bear | 37 | 0.5676 | 0.4091 | REJECT | REJECT |
| Auto | Bear | 115 | 0.5304 | 0.4397 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 15 of 24

### BTST_SECTOR_LEADER_ROTATION × HOLD_CLOSE

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Metal | Choppy | 435 | 0.5908 | 0.544 | REJECT | REJECT |
| Bank | Bear | 243 | 0.5638 | 0.5009 | REJECT | REJECT |
| Metal | Bear | 213 | 0.5587 | 0.4915 | REJECT | REJECT |
| Energy | Choppy | 521 | 0.5566 | 0.5137 | REJECT | REJECT |
| Bank | Choppy | 1222 | 0.5466 | 0.5186 | REJECT | REJECT |
| Infra | Bull | 531 | 0.5461 | 0.5036 | REJECT | REJECT |
| FMCG | Bear | 159 | 0.5409 | 0.4634 | REJECT | REJECT |
| Energy | Bull | 710 | 0.5394 | 0.5027 | REJECT | REJECT |
| Auto | Choppy | 460 | 0.5326 | 0.4869 | REJECT | REJECT |
| Pharma | Bull | 665 | 0.5308 | 0.4928 | REJECT | REJECT |
| IT | Choppy | 289 | 0.5294 | 0.4719 | REJECT | REJECT |
| IT | Bear | 248 | 0.5202 | 0.4581 | REJECT | REJECT |
| Infra | Choppy | 492 | 0.5163 | 0.4721 | REJECT | REJECT |
| Pharma | Bear | 133 | 0.4962 | 0.4126 | REJECT | REJECT |
| Bank | Bull | 1616 | 0.495 | 0.4707 | REJECT | REJECT |
| FMCG | Choppy | 459 | 0.488 | 0.4426 | REJECT | REJECT |
| Energy | Bear | 200 | 0.485 | 0.4167 | REJECT | REJECT |
| Auto | Bull | 547 | 0.4808 | 0.4392 | REJECT | REJECT |
| Auto | Bear | 186 | 0.4785 | 0.4079 | REJECT | REJECT |
| FMCG | Bull | 644 | 0.4783 | 0.4399 | REJECT | REJECT |
| Pharma | Choppy | 453 | 0.4724 | 0.4269 | REJECT | REJECT |
| Metal | Bull | 564 | 0.4574 | 0.4168 | REJECT | REJECT |
| IT | Bull | 478 | 0.454 | 0.4099 | REJECT | REJECT |
| Infra | Bear | 68 | 0.3088 | 0.2117 | REJECT | B |

**Sub-cohort tier hits in this cell:** 1 of 24

### BTST_SECTOR_LEADER_ROTATION × HOLD_D2

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| FMCG | Bear | 173 | 0.578 | 0.5035 | REJECT | REJECT |
| IT | Choppy | 336 | 0.5714 | 0.518 | REJECT | REJECT |
| Infra | Choppy | 554 | 0.556 | 0.5143 | REJECT | REJECT |
| Metal | Choppy | 483 | 0.5342 | 0.4896 | REJECT | REJECT |
| Auto | Choppy | 527 | 0.5313 | 0.4886 | REJECT | REJECT |
| Bank | Choppy | 1324 | 0.5287 | 0.5018 | REJECT | REJECT |
| Energy | Bull | 792 | 0.5164 | 0.4816 | REJECT | REJECT |
| Pharma | Bull | 740 | 0.5162 | 0.4802 | REJECT | REJECT |
| Auto | Bear | 212 | 0.5094 | 0.4426 | REJECT | REJECT |
| Energy | Choppy | 597 | 0.5092 | 0.4692 | REJECT | REJECT |
| Infra | Bull | 594 | 0.5067 | 0.4666 | REJECT | REJECT |
| FMCG | Choppy | 508 | 0.5039 | 0.4606 | REJECT | REJECT |
| Bank | Bull | 1826 | 0.5 | 0.4771 | REJECT | REJECT |
| Energy | Bear | 240 | 0.5 | 0.4372 | REJECT | REJECT |
| Metal | Bear | 220 | 0.5 | 0.4345 | REJECT | REJECT |
| IT | Bull | 555 | 0.4937 | 0.4523 | REJECT | REJECT |
| Pharma | Choppy | 527 | 0.4915 | 0.449 | REJECT | REJECT |
| IT | Bear | 263 | 0.4791 | 0.4194 | REJECT | REJECT |
| Bank | Bear | 270 | 0.4667 | 0.408 | REJECT | REJECT |
| Pharma | Bear | 149 | 0.4497 | 0.3721 | REJECT | REJECT |
| Metal | Bull | 613 | 0.4421 | 0.4033 | REJECT | REJECT |
| Auto | Bull | 613 | 0.4372 | 0.3984 | REJECT | REJECT |
| FMCG | Bull | 734 | 0.4319 | 0.3965 | REJECT | REJECT |
| Infra | Bear | 69 | 0.3043 | 0.2085 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 24

### BTST_POST_PULLBACK_RESUMPTION × HOLD_CLOSE

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Bank | Bull | 38 | 0.5789 | 0.4219 | REJECT | REJECT |
| Bank | Bear | 31 | 0.5484 | 0.3777 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 2

### BTST_POST_PULLBACK_RESUMPTION × HOLD_D2

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Bank | Bear | 32 | 0.5 | 0.3363 | REJECT | REJECT |
| Bank | Bull | 41 | 0.4878 | 0.3425 | REJECT | REJECT |
| Bank | Choppy | 30 | 0.4667 | 0.3023 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 3

### BTST_INSIDE_DAY_BREAKOUT × HOLD_OPEN

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Other | Bull | 1385 | 0.7321 | 0.7082 | A | REJECT |
| CapGoods | Bull | 1311 | 0.7246 | 0.6998 | A | REJECT |
| Pharma | Bull | 1480 | 0.7142 | 0.6906 | A | REJECT |
| Metal | Bull | 1640 | 0.7055 | 0.683 | A | REJECT |
| Auto | Bull | 1332 | 0.705 | 0.6799 | A | REJECT |
| Bank | Bull | 3465 | 0.703 | 0.6876 | A | REJECT |
| Consumer | Choppy | 101 | 0.703 | 0.6077 | B | REJECT |
| Energy | Bull | 1761 | 0.7024 | 0.6807 | A | REJECT |
| FMCG | Bull | 1465 | 0.6983 | 0.6743 | A | REJECT |
| Health | Bull | 418 | 0.6962 | 0.6505 | A | REJECT |
| Chem | Bull | 1820 | 0.6951 | 0.6735 | A | REJECT |
| Pharma | Choppy | 1053 | 0.6885 | 0.6599 | A | REJECT |
| Consumer | Bull | 108 | 0.6852 | 0.5925 | REJECT | REJECT |
| IT | Bull | 1543 | 0.6818 | 0.6581 | A | REJECT |
| Health | Choppy | 307 | 0.6743 | 0.62 | A | REJECT |
| Energy | Bear | 873 | 0.6735 | 0.6417 | A | REJECT |
| CapGoods | Choppy | 879 | 0.6724 | 0.6406 | A | REJECT |
| Infra | Bull | 1487 | 0.6718 | 0.6475 | A | REJECT |
| Pharma | Bear | 808 | 0.6708 | 0.6376 | A | REJECT |
| CapGoods | Bear | 628 | 0.664 | 0.6262 | A | REJECT |
| Other | Choppy | 906 | 0.6611 | 0.6297 | B | REJECT |
| Consumer | Bear | 67 | 0.6567 | 0.5373 | REJECT | REJECT |
| Metal | Bear | 808 | 0.6498 | 0.6162 | B | REJECT |
| FMCG | Bear | 779 | 0.647 | 0.6128 | B | REJECT |
| IT | Bear | 781 | 0.6466 | 0.6124 | A | REJECT |
| Metal | Choppy | 1094 | 0.6463 | 0.6175 | B | REJECT |
| Health | Bear | 186 | 0.6452 | 0.5741 | B | REJECT |
| Chem | Choppy | 1256 | 0.6449 | 0.618 | B | REJECT |
| Energy | Choppy | 1156 | 0.6445 | 0.6164 | B | REJECT |
| FMCG | Choppy | 1005 | 0.6428 | 0.6127 | B | REJECT |
| Bank | Bear | 1690 | 0.6408 | 0.6177 | B | REJECT |
| Chem | Bear | 955 | 0.6408 | 0.6099 | B | REJECT |
| Auto | Choppy | 906 | 0.6391 | 0.6073 | B | REJECT |
| Other | Bear | 636 | 0.6352 | 0.5971 | B | REJECT |
| Bank | Choppy | 2283 | 0.6351 | 0.6152 | B | REJECT |
| Auto | Bear | 683 | 0.6135 | 0.5764 | B | REJECT |
| IT | Choppy | 1044 | 0.6015 | 0.5715 | REJECT | REJECT |
| Infra | Bear | 765 | 0.5961 | 0.5609 | REJECT | REJECT |
| Infra | Choppy | 1070 | 0.5935 | 0.5637 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 34 of 39

### BTST_INSIDE_DAY_BREAKOUT × HOLD_CLOSE

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Auto | Choppy | 1648 | 0.5243 | 0.5001 | REJECT | REJECT |
| Consumer | Choppy | 161 | 0.5217 | 0.445 | REJECT | REJECT |
| FMCG | Bear | 1380 | 0.5167 | 0.4903 | REJECT | REJECT |
| Other | Bear | 973 | 0.5149 | 0.4835 | REJECT | REJECT |
| IT | Choppy | 1750 | 0.5143 | 0.4909 | REJECT | REJECT |
| IT | Bull | 2713 | 0.5068 | 0.488 | REJECT | REJECT |
| Pharma | Bear | 1254 | 0.5032 | 0.4755 | REJECT | REJECT |
| FMCG | Bull | 3198 | 0.5031 | 0.4858 | REJECT | REJECT |
| Energy | Choppy | 2068 | 0.5015 | 0.4799 | REJECT | REJECT |
| Consumer | Bear | 106 | 0.5 | 0.4065 | REJECT | REJECT |
| Auto | Bull | 2564 | 0.4996 | 0.4803 | REJECT | REJECT |
| Pharma | Bull | 3096 | 0.4987 | 0.4811 | REJECT | REJECT |
| Energy | Bear | 1372 | 0.4978 | 0.4714 | REJECT | REJECT |
| Infra | Bear | 1157 | 0.4978 | 0.4691 | REJECT | REJECT |
| Infra | Bull | 2771 | 0.494 | 0.4755 | REJECT | REJECT |
| Bank | Bull | 6648 | 0.4931 | 0.4811 | REJECT | REJECT |
| Metal | Bull | 2835 | 0.4921 | 0.4737 | REJECT | REJECT |
| Pharma | Choppy | 1937 | 0.4915 | 0.4693 | REJECT | REJECT |
| IT | Bear | 1132 | 0.4903 | 0.4612 | REJECT | REJECT |
| FMCG | Choppy | 2031 | 0.4889 | 0.4672 | REJECT | REJECT |
| Infra | Choppy | 1746 | 0.4885 | 0.4651 | REJECT | REJECT |
| Auto | Bear | 1112 | 0.4883 | 0.459 | REJECT | REJECT |
| Chem | Bear | 1309 | 0.4874 | 0.4604 | REJECT | REJECT |
| Metal | Choppy | 1749 | 0.4871 | 0.4638 | REJECT | REJECT |
| Bank | Bear | 2564 | 0.4848 | 0.4655 | REJECT | REJECT |
| Bank | Choppy | 4007 | 0.4827 | 0.4672 | REJECT | REJECT |
| Chem | Bull | 3121 | 0.4816 | 0.4641 | REJECT | REJECT |
| Other | Choppy | 1522 | 0.4816 | 0.4566 | REJECT | REJECT |
| CapGoods | Bull | 2490 | 0.4807 | 0.4611 | REJECT | REJECT |
| Health | Choppy | 543 | 0.4807 | 0.4389 | REJECT | REJECT |
| Other | Bull | 2437 | 0.4805 | 0.4607 | REJECT | REJECT |
| Energy | Bull | 3368 | 0.4795 | 0.4627 | REJECT | REJECT |
| CapGoods | Choppy | 1532 | 0.4758 | 0.4509 | REJECT | REJECT |
| Chem | Choppy | 2012 | 0.4747 | 0.4529 | REJECT | REJECT |
| CapGoods | Bear | 991 | 0.4672 | 0.4363 | REJECT | REJECT |
| Metal | Bear | 1152 | 0.4644 | 0.4358 | REJECT | REJECT |
| Health | Bull | 837 | 0.4624 | 0.4288 | REJECT | REJECT |
| Consumer | Bull | 222 | 0.4595 | 0.3951 | REJECT | REJECT |
| Health | Bear | 312 | 0.4583 | 0.4039 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 39

### BTST_INSIDE_DAY_BREAKOUT × HOLD_D2

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Consumer | Bull | 269 | 0.5204 | 0.4609 | REJECT | REJECT |
| Pharma | Bear | 1410 | 0.5113 | 0.4853 | REJECT | REJECT |
| Auto | Bull | 2918 | 0.5096 | 0.4915 | REJECT | REJECT |
| IT | Choppy | 1960 | 0.5071 | 0.485 | REJECT | REJECT |
| IT | Bull | 3122 | 0.5035 | 0.486 | REJECT | REJECT |
| Auto | Choppy | 1837 | 0.4976 | 0.4747 | REJECT | REJECT |
| Health | Choppy | 613 | 0.4959 | 0.4565 | REJECT | REJECT |
| FMCG | Bull | 3685 | 0.4955 | 0.4794 | REJECT | REJECT |
| Pharma | Choppy | 2247 | 0.4953 | 0.4747 | REJECT | REJECT |
| FMCG | Bear | 1537 | 0.4945 | 0.4695 | REJECT | REJECT |
| Pharma | Bull | 3515 | 0.4919 | 0.4754 | REJECT | REJECT |
| Energy | Choppy | 2320 | 0.4888 | 0.4685 | REJECT | REJECT |
| FMCG | Choppy | 2281 | 0.484 | 0.4635 | REJECT | REJECT |
| Bank | Choppy | 4548 | 0.4824 | 0.4679 | REJECT | REJECT |
| Infra | Bull | 3075 | 0.481 | 0.4634 | REJECT | REJECT |
| Bank | Bull | 7547 | 0.4806 | 0.4693 | REJECT | REJECT |
| Other | Choppy | 1716 | 0.4802 | 0.4566 | REJECT | REJECT |
| Other | Bear | 1082 | 0.4787 | 0.4491 | REJECT | REJECT |
| Health | Bull | 922 | 0.4761 | 0.4441 | REJECT | REJECT |
| Chem | Bull | 3549 | 0.4756 | 0.4592 | REJECT | REJECT |
| IT | Bear | 1286 | 0.4751 | 0.4479 | REJECT | REJECT |
| Metal | Bull | 3125 | 0.4739 | 0.4565 | REJECT | REJECT |
| Metal | Choppy | 1994 | 0.4734 | 0.4516 | REJECT | REJECT |
| Auto | Bear | 1215 | 0.4733 | 0.4453 | REJECT | REJECT |
| Other | Bull | 2809 | 0.4721 | 0.4536 | REJECT | REJECT |
| Chem | Bear | 1476 | 0.4702 | 0.4448 | REJECT | REJECT |
| Chem | Choppy | 2299 | 0.4693 | 0.449 | REJECT | REJECT |
| CapGoods | Choppy | 1728 | 0.4664 | 0.443 | REJECT | REJECT |
| Consumer | Bear | 118 | 0.4661 | 0.3786 | REJECT | REJECT |
| Energy | Bull | 3778 | 0.4659 | 0.45 | REJECT | REJECT |
| CapGoods | Bull | 2765 | 0.4658 | 0.4473 | REJECT | REJECT |
| Bank | Bear | 2856 | 0.4639 | 0.4457 | REJECT | REJECT |
| Infra | Bear | 1268 | 0.4629 | 0.4356 | REJECT | REJECT |
| Infra | Choppy | 1983 | 0.4624 | 0.4406 | REJECT | REJECT |
| Energy | Bear | 1544 | 0.4618 | 0.437 | REJECT | REJECT |
| CapGoods | Bear | 1108 | 0.4486 | 0.4195 | REJECT | REJECT |
| Consumer | Choppy | 181 | 0.4365 | 0.3663 | REJECT | REJECT |
| Metal | Bear | 1270 | 0.4362 | 0.4092 | REJECT | REJECT |
| Health | Bear | 332 | 0.4096 | 0.3581 | REJECT | REJECT |

**Sub-cohort tier hits in this cell:** 0 of 39

---

## Section 5 — UP_TRI baseline + cross-detector synthesis

**UP_TRI baseline (D6 hold):** WR 0.5281, n_excl_flat 71865

**Cross-detector pattern by hold variant:**

| Detector | HOLD_OPEN WR | HOLD_CLOSE WR | HOLD_D2 WR | Best Hold |
|----------|--------------|---------------|-------------|-----------|
| BTST_LAST_30MIN_STRENGTH | 0.7715 | 0.481 | 0.4566 | HOLD_OPEN |
| BTST_SECTOR_LEADER_ROTATION | 0.6948 | 0.5127 | 0.5003 | HOLD_OPEN |
| BTST_POST_PULLBACK_RESUMPTION | 0.7297 | 0.5275 | 0.476 | HOLD_OPEN |
| BTST_INSIDE_DAY_BREAKOUT | 0.6689 | 0.4901 | 0.4793 | HOLD_OPEN |

**Highest-WR cell:** `BTST_LAST_30MIN_STRENGTH × HOLD_OPEN` — WR 0.7715 (n_excl_flat 8597; BoostTier S)

---

## Section 6 — Headline findings (data only; NO promotion calls)

- **Total signal records:** 134848 across 4 detectors × 15 years
- **Cells evaluated:** 12 (4 × 3)
- **Cells with sufficient n for tier eval:** 12
- **Cells with INSUFFICIENT_N:** 0
- **Cells earning Tier S/A/B:** 4 of 12
- **UP_TRI baseline WR:** 0.5281 (n 71865)

**Headline:** INV-012 surfaces 4 BTST cells earning Lab tier (S/A/B). Top: BTST_LAST_30MIN_STRENGTH×HOLD_OPEN (WR 0.7715, n 8597), BTST_SECTOR_LEADER_ROTATION×HOLD_OPEN (WR 0.6948, n 6426), BTST_POST_PULLBACK_RESUMPTION×HOLD_OPEN (WR 0.7297, n 344). User reviews per-cell tier eligibility + Caveat 2 audit before any scanner integration.

---

## Section 7 — Open questions for user review

1. **BTST viability:** if any cell earns Lab tier, decide whether to integrate as new BTST signal type in scanner_core.py. Note BTST has different time horizon than swing signals — may require bridge L1 PRE_MARKET composer extension to surface BTST entries before market open + bridge L2 POST_OPEN composer for next-day exits.

2. **Sub-cohort tier hits (Section 4):** if any (sector × regime) sub-cohort earns tier even though parent cell REJECT, consider conditional BTST signal restricted to specific cohorts. n at margin (30-200) — Caveat 2 audit critical.

3. **Detector design improvement:** if 0 cells earn tier, BTST may still work with refined detector logic (different thresholds; additional filters). User decides whether to register INV-NN follow-up with refined definitions.

4. **HOLD variant best practice:** Section 5 cross-detector table shows which HOLD variant maximizes WR per detector. Consistent HOLD_OPEN dominance would inform single-config BTST exit; detector-specific best-hold would require per-detector exit config.

5. **Caveat 2 audit dependency:** any tier-eligible cell at marginal n needs Caveat 2 audit before promotion (parallel to INV-003 / INV-010 candidates).

6. **patterns.json INV-012 status:** PRE_REGISTERED → COMPLETED is user-only transition.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
