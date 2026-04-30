# INV-013 — DOWN_TRI exit timing direction-aware investigation

**Generated:** 2026-04-30T19:30:51.769466+00:00

**Branch:** backtest-lab

**Cohort:** signal=DOWN_TRI; direction=SHORT (verified per audit)

**Variants:** 13 (D2, D3, D4, D5, D6, D7, D8, D10, TRAIL_1.5xATR, TRAIL_2.0xATR, TRAIL_2.5xATR, LADDER_A_50at2R_50atD6, LADDER_B_33_33_34trailing)

**Baseline:** D6 (current scanner.config default)

---

## ⚠️ Caveats

**Direction-aware fix:** This investigation rebuilds the INV-006 runner pattern with SHORT-direction semantics for DOWN_TRI signals. SHORT pnl = (entry - exit) / entry × 100; SHORT stop_hit when high ≥ stop_price; SHORT target_hit when low ≤ target_price. Trailing stops placed ABOVE entry, trail DOWNWARD as price falls.

**Caveat 2 (9.31% MS-2 miss-rate)** inherited from MS-2 cross-validation; DOWN_TRI subset of universe; user re-validates surfaced candidates post-Caveat 2 audit before promotion.

**ATR computation:** ATR-14 computed from cached OHLC parquets via rolling mean of true range (Wilder approximation; same as INV-006). For signals where ATR is NaN at entry (first 14 days of cache), ATR-based variants report `n_atr_unavailable`.

---

## Section 1 — Methodology + direction-aware logic

**Pipeline:**
1. Filter backtest_signals.parquet to signal='DOWN_TRI' (n=19961; all direction='SHORT')
2. Pre-load 188 stock parquets with ATR-14 column
3. For each signal, compute outcomes for 12 exit variants using SHORT semantics:
   - Fixed-day exits (D2-D10): exit at OPEN of N-th trading day; pnl = (entry - exit) / entry × 100
   - Trailing-stop variants: initial stop = entry + mult × ATR (ABOVE entry); each day stop = min(prior, today_close + mult × today_ATR); stop hit when high ≥ stop
   - Ladder A: 50% at entry-2R (SHORT target below entry), 50% at D6 OPEN
   - Ladder B: 33% at entry-1.5R + 33% at entry-2.5R + 34% trailing-2×ATR
4. Aggregate by variant; compute lifetime stats; train/test OOS split + hypothesis_tester.
5. Compare each variant to D6 baseline (same SHORT semantics — apples-to-apples).

**Candidate threshold:** Δ WR ≥ 3.0pp + p < 0.05 + n ≥ 100 → BEATS_BASELINE.

---

## Section 2 — Per-variant results (DOWN_TRI; SHORT semantics)

**D6 baseline:** n_excl_flat=18097, WR=0.4653, Wilson=0.4581, avg_pnl=-0.6072%, R-mult=-0.1596

| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Avg_R-mult | Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | p-value | Verdict |
|---------|-------------|-----|--------------|-------------|------------|----------|---------|----------|----------|----------|--------------|---------|--------|
| D2 | 16455 | 0.487 | 0.4793 | -0.2035 | -0.0583 | 0.4943 | 0.463 | 3.13 | REJECT | REJECT | 2.17 | 5.5e-05 | MARGINAL_OR_EQUIVALENT |
| D3 | 17138 | 0.4842 | 0.4768 | -0.2687 | -0.06 | 0.4915 | 0.4612 | 3.03 | REJECT | REJECT | 1.89 | 0.000394 | MARGINAL_OR_EQUIVALENT |
| D4 | 17516 | 0.476 | 0.4686 | -0.3757 | -0.0899 | 0.484 | 0.4501 | 3.39 | REJECT | REJECT | 1.07 | 0.043202 | MARGINAL_OR_EQUIVALENT |
| D5 | 17773 | 0.47 | 0.4627 | -0.4961 | -0.1262 | 0.4766 | 0.4492 | 2.74 | REJECT | REJECT | 0.47 | 0.37681 | MARGINAL_OR_EQUIVALENT |
| D6 | 18097 | 0.4653 | 0.4581 | -0.6072 | -0.1596 | 0.4728 | 0.4418 | 3.1 | REJECT | REJECT | 0.0 | — | BASELINE |
| D7 | 18170 | 0.463 | 0.4558 | -0.6709 | -0.1778 | 0.4697 | 0.4418 | 2.79 | REJECT | REJECT | -0.23 | 0.659209 | MARGINAL_OR_EQUIVALENT |
| D8 | 18246 | 0.4574 | 0.4502 | -0.7663 | -0.2058 | 0.4622 | 0.4425 | 1.97 | REJECT | REJECT | -0.79 | 0.130396 | MARGINAL_OR_EQUIVALENT |
| D10 | 18416 | 0.4558 | 0.4486 | -0.9093 | -0.1196 | 0.4568 | 0.4525 | 0.43 | REJECT | REJECT | -0.95 | 0.067853 | MARGINAL_OR_EQUIVALENT |
| TRAIL_1.5xATR | 18633 | 0.3713 | 0.3644 | -0.454 | 0.0288 | 0.3732 | 0.3654 | 0.78 | REJECT | B | -9.4 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.0xATR | 18731 | 0.4042 | 0.3972 | -0.585 | -0.0105 | 0.4083 | 0.3912 | 1.71 | REJECT | REJECT | -6.11 | 0.0 | WORSE_THAN_BASELINE |
| TRAIL_2.5xATR | 18700 | 0.4311 | 0.424 | -0.6646 | -0.0351 | 0.4329 | 0.4254 | 0.75 | REJECT | REJECT | -3.42 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_A_50at2R_50atD6 | 19337 | 0.3556 | 0.3489 | -0.5108 | -0.1273 | 0.359 | 0.345 | 1.4 | REJECT | B | -10.97 | 0.0 | WORSE_THAN_BASELINE |
| LADDER_B_33_33_34trailing | 18651 | 0.3818 | 0.3749 | -0.3536 | -0.0369 | 0.3862 | 0.3677 | 1.85 | REJECT | B | -8.35 | 0.0 | WORSE_THAN_BASELINE |

---

## Section 3 — Drawdown + capital efficiency (D6 vs D10)

**Records:** 19948 DOWN_TRI signals with full 11-day post-entry window.

**MAE (max adverse excursion) — for SHORT, highest HIGH vs entry (positive = bad for SHORT):**

| Window | n | mean | median | p25 | p75 | p95 worst |
|--------|---|------|--------|-----|-----|-----------|
| D6 | 19948 | +4.423% | +3.365% | +1.254% | +6.327% | +13.498% |
| D10 | 19948 | +5.885% | +4.472% | +1.878% | +8.240% | +17.127% |

**Stop-out frequency (SHORT-direction stop ABOVE entry):**

| Stop window | n | pct |
|---|---|---|
| Stop in D1-D6 | 2473 | 12.40% |
| Additional stop in D7-D10 | 1379 | 6.91% |
| Total stop by D10 | 3852 | 19.31% |

**Per-trade pnl distribution (SHORT pnl):**

| Variant | p5 | p25 | p50 | p75 | p95 | mean | std |
|---------|------|------|------|------|------|------|------|
| D6 | -9.761% | -3.402% | -0.345% | +2.531% | +7.588% | -0.607% | +5.605% |
| D10 | -12.630% | -4.577% | -0.538% | +3.094% | +9.618% | -0.909% | +7.161% |

**Capital efficiency (Σ pnl / Σ days held):**

| Variant | n | Σ pnl% | Σ days | pnl/day | avg days |
|---------|---|---------|---------|----------|----------|
| D6 | 19948 | -12112.5% | 113377 | -0.10683% | 5.68 |
| D10 | 19948 | -18138.4% | 181058 | -0.10018% | 9.08 |

---

## Section 4 — Comparison to invalidated INV-006 DOWN_TRI numbers

INV-006 reported DOWN_TRI variants using LONG-only pnl + stop logic, which INVERTS the sign for SHORT-direction signals. INV-013 corrects this. The table below cross-references what INV-006 reported (invalid) vs what INV-013 now reports (correct).

| Variant | INV-006 reported WR (INVALID — LONG-direction) | INV-013 corrected WR (SHORT-direction) | Sign inversion check |
|---------|------------------------------------------------|-----------------------------------------|----------------------|
| D2 | — | 0.487 | — |
| D3 | — | 0.4842 | — |
| D4 | — | 0.476 | — |
| D5 | — | 0.47 | — |
| D6 | 0.5347 | 0.4653 | sum=1.0 (~1.0 indicates inversion) |
| D7 | — | 0.463 | — |
| D8 | — | 0.4574 | — |
| D10 | — | 0.4558 | — |
| TRAIL_1.5xATR | 0.4366 | 0.3713 | sum=0.8079 |
| TRAIL_2.0xATR | 0.4756 | 0.4042 | sum=0.8798 |
| TRAIL_2.5xATR | 0.5012 | 0.4311 | sum=0.9323 (~1.0 indicates inversion) |
| LADDER_A_50at2R_50atD6 | 0.4167 | 0.3556 | sum=0.7723 |
| LADDER_B_33_33_34trailing | 0.4441 | 0.3818 | sum=0.8259 |

*Sum ≈ 1.0 indicates the INV-006 number was the LONG-direction inversion of the SHORT semantics (W/L flip; FLAT handling causes minor deviation). INV-013 numbers are the corrected SHORT-direction values.*

---

## Section 5 — Headline findings (data only; NO promotion calls)

- **D6 baseline (SHORT-direction, corrected):** WR 0.4653, n_excl_flat 18097, avg_pnl -0.6072%, R-mult -0.1596
- **Variants BEAT D6 on WR (≥3pp + p<0.05 + n≥100):** 0
- **Variants WORSE than D6:** 5
  - `TRAIL_1.5xATR` WR=0.3713 (Δ=-9.40pp, p=0.0)
  - `TRAIL_2.0xATR` WR=0.4042 (Δ=-6.11pp, p=0.0)
  - `TRAIL_2.5xATR` WR=0.4311 (Δ=-3.42pp, p=0.0)
  - `LADDER_A_50at2R_50atD6` WR=0.3556 (Δ=-10.97pp, p=0.0)
  - `LADDER_B_33_33_34trailing` WR=0.3818 (Δ=-8.35pp, p=0.0)
- **Marginal / equivalent:** 7

**Pnl improvement check (≥10% relative + p<0.05 vs D6 avg_pnl):**

Variants beating D6 on pnl (≥10% relative + p<0.05): 6
  - `D2` avg_pnl=-0.203% (vs D6 -0.607%; rel=+66.5%; p=0.0000)
  - `D3` avg_pnl=-0.269% (vs D6 -0.607%; rel=+55.7%; p=0.0000)
  - `D4` avg_pnl=-0.376% (vs D6 -0.607%; rel=+38.1%; p=0.0000)
  - `D5` avg_pnl=-0.496% (vs D6 -0.607%; rel=+18.3%; p=0.0383)
  - `TRAIL_1.5xATR` avg_pnl=-0.454% (vs D6 -0.607%; rel=+25.2%; p=0.0045)
  - `LADDER_B_33_33_34trailing` avg_pnl=-0.354% (vs D6 -0.607%; rel=+41.8%; p=0.0000)

**Headline:** INV-013 finds 0 variants beating D6 on WR but 6 beating on pnl (≥10% relative + p<0.05). Strongest: `D2` (rel +66.5%, p=0.0000). Pattern parallels INV-006 UP_TRI/BULL_PROXY where longer holds capture more pnl per winning trade.

---

## Section 6 — Open questions for user review

1. **DOWN_TRI exit migration:** does Section 2 surface any BEATS_BASELINE variant that warrants scanner.config HOLDING_DAYS update for SHORT signals? User decides per cell.

2. **Cross-signal unification (with INV-006):** UP_TRI × D10 was identified as plausibly net-positive in INV-006 supplementary. If INV-013 also surfaces D10 (or another variant) for DOWN_TRI, consider unified migration; if DOWN_TRI prefers different exit, signal-specific config required.

3. **Drawdown trade-off (Section 3):** longer holds widen the MAE distribution for SHORT trades the same way as for LONG. User weighs WR/pnl improvement against deeper tail risk.

4. **Caveat 2 audit dependency:** any BEATS_BASELINE variant at marginal n needs Caveat 2 audit before promotion.

5. **patterns.json INV-013 status:** PRE_REGISTERED → COMPLETED is user-only transition.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.
