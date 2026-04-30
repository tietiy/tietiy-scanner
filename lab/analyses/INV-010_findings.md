# INV-010 — GAP_BREAKOUT new entry signal discovery

**Generated:** 2026-04-30T19:48:46.649902+00:00

**Branch:** backtest-lab

**Signal:** GAP_BREAKOUT (LONG; gap-up + 10-day consolidation + 5-day high break + volume confirmation)

**Universe:** 188 F&O stocks × 15-year backtest (2011-2026)

---

## ⚠️ Caveats

**Signal direction:** LONG (consistent with UP_TRI/BULL_PROXY family). Outcome computation uses LONG D6 semantics: stop_hit if low ≤ stop_price; target_hit if high ≥ target_price; pnl = (exit - entry) / entry × 100.

**Caveat 2 (9.31% MS-2 miss-rate)** is INV-010-specific because this investigation builds a NEW detector from cache parquets directly; not subject to the original signal_replayer regen miss-rate. However, miss-rate in cache itself (yfinance gaps, missing volume bars) may affect detection.

**Adoption requires production work:** any GAP_BREAKOUT promotion to scanner.scanner_core would be a separate main-branch session (per INV-010 patterns.json note); INV-010 is data + structured analysis only.

---

## Section 1 — Methodology

**Signal definition (all 4 rules required):**
1. `today_open > prev_close × 1.005` (gap up >0.5%)
2. `today_high > prior_5d_high` (5-day high break)
3. `prior_10d_range / prior_10d_avg_close < 0.05` (consolidation: 10-day range <5.0%)
4. `today_volume > 1.2 × prior_20d_avg_volume` (volume confirmation)

**Entry/exit:**
- entry_close = today's close
- stop_price = entry × 0.95 (5% below)
- target_price = entry × 1.1 (10% above; 2:1 RR)
- Hold period: D6 default
- Direction: LONG; D6 close exit if neither stop nor target hit

**Pipeline:** for each stock parquet, build rolling features (prev_close, prior_5d_high, prior_10d_range, prior_10d_avg_close, prior_20d_avg_volume); detect signals where all 4 rules fire; emit signal records; compute LONG D6 outcomes; join regime + sector; tier evaluation.

---

## Section 2 — Detection diagnostics

**Total signals detected:** 1827

**Stocks with at least one signal:** 183 of 188

**Date range:** 2011-02-28 → 2026-04-23

**Outcome distribution:**

| Outcome | Count | Pct |
|---|---|---|
| DAY6_WIN | 743 | 40.67% |
| DAY6_LOSS | 495 | 27.09% |
| STOP_HIT | 248 | 13.57% |
| DAY6_FLAT | 221 | 12.10% |
| TARGET_HIT | 119 | 6.51% |
| OPEN | 1 | 0.05% |

**Signals by year:**

| Year | Count |
|---|---|
| 2011 | 43 |
| 2012 | 86 |
| 2013 | 74 |
| 2014 | 62 |
| 2015 | 56 |
| 2016 | 96 |
| 2017 | 199 |
| 2018 | 100 |
| 2019 | 81 |
| 2020 | 84 |
| 2021 | 111 |
| 2022 | 117 |
| 2023 | 342 |
| 2024 | 126 |
| 2025 | 225 |
| 2026 | 25 |

**Signals by sector:**

| Sector | Count |
|---|---|
| Bank | 301 |
| FMCG | 245 |
| Pharma | 206 |
| IT | 200 |
| Energy | 168 |
| Auto | 135 |
| Chem | 124 |
| Infra | 105 |
| Other | 103 |
| CapGoods | 97 |
| Metal | 86 |
| Health | 36 |
| Consumer | 21 |

---

## Section 3 — Lifetime cohort + tier evaluation

**Lifetime stats:**
- n_total: 1827
- n_resolved: 1826
- n_excl_flat: 1605
- n_win: 862 | n_loss: 743 | n_flat: 221 | n_open: 1
- WR (excl flat): 0.5371
- Wilson lower 95: 0.5126
- p-value vs 50%: 0.002974

**Tier evaluation (train 2011-2022 / test 2023-2026):**

| Hypothesis | Train_WR | Test_WR | Drift_pp | Train_n | Test_n | Tier |
|---|---|---|---|---|---|---|
| BOOST | 0.5411 | 0.5309 | 1.02 | 974 | 631 | **REJECT** |
| KILL  | 0.5411 | 0.5309 | 1.02 | — | — | **REJECT** |

**Per-trade pnl distribution (LONG semantics):**

| Stat | Value |
|---|---|
| n | 1826 |
| Mean | +0.682% |
| Median | +0.280% |
| Std | +4.039% |
| p5 | -5.000% |
| p25 | -2.117% |
| p75 | +2.925% |
| p95 | +10.000% |

---

## Section 4 — Sector × regime sub-cohort breakdown

**Cells evaluated:** 39 (18 OK, 21 INSUFFICIENT_N)

| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |
|--------|--------|-------------|-----|--------------|----------|----------|
| Other | Bull | 65 | 0.6462 | 0.5247 | B | REJECT |
| Chem | Choppy | 30 | 0.6333 | 0.4551 | REJECT | REJECT |
| FMCG | Bull | 128 | 0.6172 | 0.5307 | B | REJECT |
| FMCG | Choppy | 67 | 0.5821 | 0.4627 | B | REJECT |
| Bank | Choppy | 74 | 0.5811 | 0.4674 | B | REJECT |
| Metal | Bull | 48 | 0.5625 | 0.4227 | REJECT | REJECT |
| Auto | Choppy | 34 | 0.5588 | 0.3945 | REJECT | REJECT |
| Energy | Bull | 86 | 0.5581 | 0.4529 | REJECT | REJECT |
| Bank | Bull | 172 | 0.5523 | 0.4777 | REJECT | REJECT |
| IT | Choppy | 52 | 0.5192 | 0.3869 | REJECT | REJECT |
| IT | Bull | 106 | 0.5189 | 0.4248 | REJECT | REJECT |
| Infra | Bull | 64 | 0.5156 | 0.3958 | REJECT | REJECT |
| CapGoods | Bull | 63 | 0.5079 | 0.3876 | REJECT | REJECT |
| Chem | Bull | 73 | 0.4932 | 0.3817 | REJECT | REJECT |
| Energy | Choppy | 47 | 0.4894 | 0.3528 | REJECT | REJECT |
| Pharma | Bull | 115 | 0.487 | 0.3975 | REJECT | REJECT |
| Auto | Bull | 82 | 0.4634 | 0.3595 | REJECT | REJECT |
| Pharma | Choppy | 55 | 0.4545 | 0.3303 | REJECT | REJECT |

**Sub-cohorts earning Lab tier (S/A/B):** 4
- `Bank × Choppy` → BOOST B (n=74, WR=0.5811)
- `FMCG × Choppy` → BOOST B (n=67, WR=0.5821)
- `FMCG × Bull` → BOOST B (n=128, WR=0.6172)
- `Other × Bull` → BOOST B (n=65, WR=0.6462)

---

## Section 5 — Comparison to UP_TRI baseline

**UP_TRI baseline (lifetime, all sectors/regimes):**
- n_excl_flat: 71865, WR=0.5281, Wilson=0.5244, p=0.0
- BoostTier: REJECT | KillTier: REJECT

**Comparison vs UP_TRI baseline:**
- Δ WR: +0.0090 (+0.90 pp)
- 2-prop z-test p-value: 0.476468
- **Verdict: GAP_BREAKOUT marginal/equivalent vs UP_TRI on lifetime WR**

**Per-sector lifetime WR comparison (sectors with both ≥30 signals):**

| Sector | UP_TRI n | UP_TRI WR | GAP_BREAKOUT n | GAP_BREAKOUT WR | Δ WR pp |
|--------|----------|-----------|----------------|------------------|----------|
| Auto | 5445 | 0.5414 | 120 | 0.5 | -4.14 |
| Bank | 13383 | 0.5197 | 259 | 0.5483 | +2.86 |
| CapGoods | 4684 | 0.5433 | 90 | 0.5222 | -2.11 |
| Chem | 5723 | 0.5378 | 110 | 0.5273 | -1.05 |
| Energy | 7016 | 0.5021 | 146 | 0.5205 | +1.84 |
| FMCG | 6447 | 0.5458 | 216 | 0.5972 | +5.14 |
| Health | 1518 | 0.5349 | 30 | 0.5333 | -0.16 |
| IT | 5359 | 0.5432 | 172 | 0.5116 | -3.16 |
| Infra | 5422 | 0.5168 | 91 | 0.5055 | -1.13 |
| Metal | 5787 | 0.5205 | 74 | 0.527 | +0.65 |
| Other | 4485 | 0.5242 | 95 | 0.6316 | +10.74 |
| Pharma | 6083 | 0.5289 | 185 | 0.4757 | -5.32 |

---

## Section 6 — Headline findings (data only; NO promotion calls)

- **Total signals detected:** 1827 across 188 stocks × 15 years
- **Lifetime WR:** 0.5371 (n_excl_flat=1605)
- **Lifetime BOOST tier:** **REJECT**
- **Lifetime KILL tier:** **REJECT**
- **Sub-cohort tier hits (S/A/B):** 4 of 18 OK cells
- **UP_TRI baseline WR:** 0.5281 (n=71865)

**Headline:** GAP_BREAKOUT lifetime cohort REJECTs at parent tier but 4 sub-cohorts earn Tier S/A/B. User reviews per-cohort tier eligibility.

---

## Section 7 — Open questions for user review

1. **Lifetime tier eligibility:** Does Section 3 BOOST or KILL tier verdict warrant adding GAP_BREAKOUT to scanner.scanner_core as new signal type? If no tier earned, decision is to archive new signal definition.

2. **Sub-cohort tier hits (Section 4):** if any (sector × regime) cell earns tier even though lifetime REJECT, consider conditional GAP_BREAKOUT signal (only fires for specific cohorts). Same n + Caveat 2 vulnerability check as INV-003 surfaced candidates.

3. **GAP_BREAKOUT vs UP_TRI (Section 5):** does new signal materially beat existing UP_TRI base case on lifetime WR? If marginal, no incremental value from adding new signal type.

4. **Caveat 2 audit dependency:** any tier-eligible cell at marginal n needs Caveat 2 audit before promotion (same standard as INV-003 candidates).

5. **Detector parameter sensitivity:** thresholds (0.5% gap, 5% range, 1.2× vol) are arbitrary; could request sensitivity analysis (different thresholds) if findings sit near boundaries.

6. **patterns.json INV-010 status:** PRE_REGISTERED → COMPLETED is user-only transition.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
