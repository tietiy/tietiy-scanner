# INV-006 — Exit timing optimization (12 variants × 3 signal types)

**Generated:** 2026-04-30T17:06:32.981909+00:00

**Branch:** backtest-lab

**Signal types tested:** UP_TRI, DOWN_TRI, BULL_PROXY

**Exit variants:** 13 (D2, D3, D4, D5, D6, D7, D8, D10, TRAIL_1.5xATR, TRAIL_2.0xATR, TRAIL_2.5xATR, LADDER_A_50at2R_50atD6, LADDER_B_33_33_34trailing)

**Baseline:** D6 (current scanner.config default)

---

## ⚠️ Caveats

**Caveat 2 (9.31% MS-2 miss-rate):** active. Variant cohorts share parent signal universe with INV-001/002/003 → same Caveat 2 vulnerability at margin.

**Caveat 5 (ATR-based variants):** ATR-14 computed on cached parquets via rolling mean of true range (Wilder approximation). For signals where ATR is NaN at entry (first 14 days of each stock's history), ATR-based variants report `n_atr_unavailable`.

**Caveat 6 (LONG-only outcomes):** Per signal_replayer, all signals (including DOWN_TRI) have LONG-direction outcomes. INV-006 inherits this; DOWN_TRI variant results are LONG-direction, not the natural SHORT trade. Inverting for SHORT interpretation is a separate analysis.

---

## Section 1 — Methodology

**Pipeline:** for each of 105987 backtest signals, compute outcomes across 12 exit variants. Per (signal_type × variant) cell: lifetime stats + train/test OOS split (train 2011-2022 / test 2023-2026) + hypothesis_tester evaluation. Compare each variant to D6 baseline.

**Variants tested:**
- **Fixed-day:** D2, D3, D4, D5, **D6 (baseline)**, D7, D8, D10 — exit at OPEN of N-th trading day post-entry.
- **Trailing-stop:** 1.5×ATR, 2.0×ATR, 2.5×ATR — initial stop = entry - mult×ATR_14_at_signal; daily update stop = max(prior, today_close - mult×today_ATR_14); exit at stop_price intraday on hit.
- **Ladder A:** 50% sold at entry+2R OR initial stop hit; 50% held to D6 OPEN. R = 1 ATR_14 unit.
- **Ladder B:** 33% at entry+1.5R; 33% at entry+2.5R; 34% trailing-2×ATR. Common initial stop = entry - 1×ATR for first two slices.

**W/L/F threshold:** ±0.5% from entry (matches signal_replayer FLAT semantics).

**Candidate threshold (vs D6 baseline):** Δ WR ≥ 3.0pp AND p < 0.05 AND n ≥ 100 → BEATS_BASELINE.

---

## Section 2 — UP_TRI variant results

**D6 baseline:** n_excl_flat=72059, WR=0.52, Wilson=0.5163, avg_pnl=0.4668

| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | p-value | Verdict |
|---------|-------------|-----|--------------|-------------|----------|---------|----------|----------|----------|--------------|---------|--------|
| D2 | 66392 | 0.5112 | 0.5074 | 0.2097 | 0.5165 | 0.4947 | 2.18 | REJECT | REJECT | -0.88 | 0.001065 | MARGINAL_OR_EQUIVALENT |
| D3 | 68657 | 0.5159 | 0.5121 | 0.2926 | 0.5229 | 0.4943 | 2.86 | REJECT | REJECT | -0.41000000000000003 | 0.123314 | MARGINAL_OR_EQUIVALENT |
| D4 | 70246 | 0.5179 | 0.5142 | 0.3517 | 0.5245 | 0.4976 | 2.69 | REJECT | REJECT | -0.21 | 0.425718 | MARGINAL_OR_EQUIVALENT |
| D5 | 71205 | 0.5186 | 0.515 | 0.4076 | 0.5231 | 0.5047 | 1.84 | REJECT | REJECT | -0.13999999999999999 | 0.595066 | MARGINAL_OR_EQUIVALENT |
| D6 | 72059 | 0.52 | 0.5163 | 0.4668 | 0.5236 | 0.5088 | 1.48 | REJECT | REJECT | 0.0 | — | BASELINE |
| D7 | 72814 | 0.5227 | 0.5191 | 0.5572 | 0.5245 | 0.5171 | 0.74 | REJECT | REJECT | 0.27 | 0.304161 | MARGINAL_OR_EQUIVALENT |
| D8 | 73203 | 0.5283 | 0.5247 | 0.6571 | 0.5302 | 0.5226 | 0.76 | REJECT | REJECT | 0.83 | 0.001553 | MARGINAL_OR_EQUIVALENT |
| D10 | 74149 | 0.534 | 0.5304 | 0.8529 | 0.5358 | 0.5282 | 0.76 | REJECT | REJECT | 1.4000000000000001 | 0.0 | MARGINAL_OR_EQUIVALENT |
| TRAIL_1.5xATR | 74797 | 0.4185 | 0.4149 | 0.4266 | 0.4265 | 0.3938 | 3.27 | REJECT | REJECT | -10.15 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.0xATR | 75041 | 0.4587 | 0.4551 | 0.4985 | 0.4664 | 0.4353 | 3.11 | REJECT | REJECT | -6.13 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.5xATR | 74906 | 0.4869 | 0.4834 | 0.5372 | 0.494 | 0.4654 | 2.86 | REJECT | REJECT | -3.3099999999999996 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_A_50at2R_50atD6 | 77863 | 0.3985 | 0.3951 | 0.0866 | 0.4083 | 0.369 | 3.93 | REJECT | REJECT | -12.15 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_B_33_33_34trailing | 74368 | 0.4318 | 0.4283 | 0.3707 | 0.4408 | 0.4044 | 3.64 | REJECT | REJECT | -8.82 | 0.0 | WORSE_THAN_BASELINE |

---

## Section 2 — DOWN_TRI variant results

**D6 baseline:** n_excl_flat=18097, WR=0.5347, Wilson=0.5274, avg_pnl=0.6072

| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | p-value | Verdict |
|---------|-------------|-----|--------------|-------------|----------|---------|----------|----------|----------|--------------|---------|--------|
| D2 | 16455 | 0.513 | 0.5054 | 0.2035 | 0.5057 | 0.537 | 3.13 | REJECT | REJECT | -2.17 | 5.5e-05 | MARGINAL_OR_EQUIVALENT |
| D3 | 17138 | 0.5158 | 0.5083 | 0.2687 | 0.5085 | 0.5388 | 3.03 | REJECT | REJECT | -1.8900000000000001 | 0.000394 | MARGINAL_OR_EQUIVALENT |
| D4 | 17516 | 0.524 | 0.5166 | 0.3757 | 0.516 | 0.5499 | 3.39 | REJECT | REJECT | -1.0699999999999998 | 0.043202 | MARGINAL_OR_EQUIVALENT |
| D5 | 17774 | 0.5299 | 0.5226 | 0.4961 | 0.5233 | 0.5508 | 2.75 | REJECT | REJECT | -0.48 | 0.362396 | MARGINAL_OR_EQUIVALENT |
| D6 | 18097 | 0.5347 | 0.5274 | 0.6072 | 0.5272 | 0.5582 | 3.1 | REJECT | REJECT | 0.0 | — | BASELINE |
| D7 | 18171 | 0.537 | 0.5297 | 0.6709 | 0.5302 | 0.5582 | 2.8 | REJECT | REJECT | 0.22999999999999998 | 0.655685 | MARGINAL_OR_EQUIVALENT |
| D8 | 18246 | 0.5426 | 0.5353 | 0.7663 | 0.5378 | 0.5575 | 1.97 | REJECT | REJECT | 0.79 | 0.130396 | MARGINAL_OR_EQUIVALENT |
| D10 | 18416 | 0.5442 | 0.537 | 0.9093 | 0.5432 | 0.5475 | 0.43 | REJECT | REJECT | 0.95 | 0.067853 | MARGINAL_OR_EQUIVALENT |
| TRAIL_1.5xATR | 18672 | 0.4366 | 0.4295 | 0.56 | 0.4321 | 0.4507 | 1.86 | REJECT | REJECT | -9.81 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.0xATR | 18738 | 0.4756 | 0.4685 | 0.6261 | 0.4743 | 0.4797 | 0.54 | REJECT | REJECT | -5.91 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.5xATR | 18689 | 0.5012 | 0.494 | 0.6516 | 0.5013 | 0.5009 | 0.04 | REJECT | REJECT | -3.35 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_A_50at2R_50atD6 | 19347 | 0.4167 | 0.4098 | 0.2288 | 0.4122 | 0.431 | 1.88 | REJECT | REJECT | -11.799999999999999 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_B_33_33_34trailing | 18606 | 0.4441 | 0.4369 | 0.4638 | 0.4401 | 0.4568 | 1.67 | REJECT | REJECT | -9.06 | 0.0 | WORSE_THAN_BASELINE |

---

## Section 2 — BULL_PROXY variant results

**D6 baseline:** n_excl_flat=4964, WR=0.5268, Wilson=0.5129, avg_pnl=0.5467

| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | p-value | Verdict |
|---------|-------------|-----|--------------|-------------|----------|---------|----------|----------|----------|--------------|---------|--------|
| D2 | 4526 | 0.515 | 0.5005 | 0.1683 | 0.512 | 0.5239 | 1.19 | REJECT | REJECT | -1.18 | 0.251686 | MARGINAL_OR_EQUIVALENT |
| D3 | 4738 | 0.5287 | 0.5145 | 0.2966 | 0.5281 | 0.5303 | 0.22 | REJECT | REJECT | 0.19 | 0.850494 | MARGINAL_OR_EQUIVALENT |
| D4 | 4817 | 0.5341 | 0.52 | 0.4172 | 0.5394 | 0.519 | 2.04 | REJECT | REJECT | 0.73 | 0.466084 | MARGINAL_OR_EQUIVALENT |
| D5 | 4889 | 0.5302 | 0.5162 | 0.4933 | 0.5358 | 0.5137 | 2.21 | REJECT | REJECT | 0.33999999999999997 | 0.737075 | MARGINAL_OR_EQUIVALENT |
| D6 | 4964 | 0.5268 | 0.5129 | 0.5467 | 0.5274 | 0.525 | 0.24 | REJECT | REJECT | 0.0 | — | BASELINE |
| D7 | 4992 | 0.5325 | 0.5186 | 0.6061 | 0.5325 | 0.5322 | 0.03 | REJECT | REJECT | 0.5700000000000001 | 0.571634 | MARGINAL_OR_EQUIVALENT |
| D8 | 4996 | 0.5364 | 0.5226 | 0.6506 | 0.5349 | 0.5408 | 0.59 | REJECT | REJECT | 0.96 | 0.335237 | MARGINAL_OR_EQUIVALENT |
| D10 | 5070 | 0.5351 | 0.5214 | 0.7854 | 0.5273 | 0.5575 | 3.02 | REJECT | REJECT | 0.83 | 0.403983 | MARGINAL_OR_EQUIVALENT |
| TRAIL_1.5xATR | 5170 | 0.4267 | 0.4133 | 0.443 | 0.4246 | 0.4327 | 0.81 | REJECT | REJECT | -10.01 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.0xATR | 5134 | 0.4657 | 0.4521 | 0.4346 | 0.4669 | 0.4622 | 0.47 | REJECT | REJECT | -6.11 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.5xATR | 5148 | 0.4922 | 0.4786 | 0.4352 | 0.4882 | 0.5038 | 1.56 | REJECT | REJECT | -3.46 | 0.00051 | WORSE_THAN_BASELINE |
| LADDER_A_50at2R_50atD6 | 5340 | 0.409 | 0.3959 | 0.1624 | 0.4109 | 0.4036 | 0.73 | REJECT | REJECT | -11.78 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_B_33_33_34trailing | 5099 | 0.4346 | 0.421 | 0.3364 | 0.4365 | 0.4293 | 0.72 | REJECT | REJECT | -9.22 | 0.0 | WORSE_THAN_BASELINE |

---

## Section 3 — Headline findings

### UP_TRI

- **D6 baseline WR:** 0.52 (n=72059, avg_pnl=0.4668)
- **Variants beating baseline:** 0
- **Variants worse than baseline:** 5
  - `TRAIL_1.5xATR` WR=0.4185 (Δ=-10.15 pp, p=0.0)
  - `TRAIL_2.0xATR` WR=0.4587 (Δ=-6.13 pp, p=0.0)
  - `TRAIL_2.5xATR` WR=0.4869 (Δ=-3.31 pp, p=0.0)
  - `LADDER_A_50at2R_50atD6` WR=0.3985 (Δ=-12.15 pp, p=0.0)
  - `LADDER_B_33_33_34trailing` WR=0.4318 (Δ=-8.82 pp, p=0.0)
- **Marginal / equivalent:** 7

### DOWN_TRI

- **D6 baseline WR:** 0.5347 (n=18097, avg_pnl=0.6072)
- **Variants beating baseline:** 0
- **Variants worse than baseline:** 5
  - `TRAIL_1.5xATR` WR=0.4366 (Δ=-9.81 pp, p=0.0)
  - `TRAIL_2.0xATR` WR=0.4756 (Δ=-5.91 pp, p=0.0)
  - `TRAIL_2.5xATR` WR=0.5012 (Δ=-3.35 pp, p=0.0)
  - `LADDER_A_50at2R_50atD6` WR=0.4167 (Δ=-11.80 pp, p=0.0)
  - `LADDER_B_33_33_34trailing` WR=0.4441 (Δ=-9.06 pp, p=0.0)
- **Marginal / equivalent:** 7

### BULL_PROXY

- **D6 baseline WR:** 0.5268 (n=4964, avg_pnl=0.5467)
- **Variants beating baseline:** 0
- **Variants worse than baseline:** 5
  - `TRAIL_1.5xATR` WR=0.4267 (Δ=-10.01 pp, p=0.0)
  - `TRAIL_2.0xATR` WR=0.4657 (Δ=-6.11 pp, p=0.0)
  - `TRAIL_2.5xATR` WR=0.4922 (Δ=-3.46 pp, p=0.00051)
  - `LADDER_A_50at2R_50atD6` WR=0.409 (Δ=-11.78 pp, p=0.0)
  - `LADDER_B_33_33_34trailing` WR=0.4346 (Δ=-9.22 pp, p=0.0)
- **Marginal / equivalent:** 7

### Universal best exit?

Avg WR across 3 signal types per variant (top 5):

| Variant | Avg WR (3 signals) |
|---------|--------------------|
| D10 | 0.5378 |
| D8 | 0.5358 |
| D7 | 0.5307 |
| D6 | 0.5272 |
| D5 | 0.5262 |

**Highest avg WR variant:** `D10` (avg WR 0.5378 across UP_TRI/DOWN_TRI/BULL_PROXY)

**D6 baseline avg WR:** 0.5272

---

## Section 4 — Open questions for user review

CC does NOT make promotion decisions. The following questions are surfaced for user judgment in a separate session.

1. **Per-signal optimal exit:** for each signal type, which variant (if any) shows BEATS_BASELINE? Decision: switch that signal's exit logic in scanner.config — separate main-branch session.

2. **Universal best exit candidate:** does Section 3's highest-avg-WR variant beat D6 across ALL signal types? If yes → unified exit migration; if only one or two signals → signal-specific exit rules.

3. **Risk-adjusted comparison:** WR improvement alone may not justify exit migration if avg_pnl_pct is materially worse (lower WR with bigger wins can outperform higher WR with smaller wins). User considers WR + avg_pnl jointly.

4. **Caveat 2 audit dependency:** any BEATS_BASELINE variant at marginal n needs Caveat 2 audit before promotion to scanner.config update.

5. **patterns.json INV-006 status:** PRE_REGISTERED → COMPLETED is user-only.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
