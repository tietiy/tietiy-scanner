# INV-007 — Volatility regime filter discovery

**Generated:** 2026-04-30T19:08:01.101509+00:00

**Branch:** backtest-lab

**Vol definition:** Nifty 20-day rolling realized vol (std of daily log returns × √252).

**Bucket thresholds:** Low <p30 (0.1082); Medium p30-p70; High >p70 (0.1604).

**Bucket day counts (15-year distribution):** {'Medium': 1494, 'High': 1121, 'Low': 1121}

---

## ⚠️ Caveats

**Vol warm-up exclusion:** First 20 trading days have NaN rolling vol; signals from those dates excluded from analysis. Total signals dropped: 761 of 105987 loaded.

**Caveat 2 (9.31% MS-2 miss-rate) inherited:** filtered cohorts at marginal n vulnerable to miss-rate; user re-validates surfaced candidates post-Caveat 2 audit before any promotion.

**Direction handling:** uses `hypothesis_tester.evaluate_hypothesis` exclusively which operates on `backtest_signals.outcome` column (correct SHORT semantics for DOWN_TRI per `signal_replayer.compute_d6_outcome`). No LONG-only manual pnl recomputation — explicitly avoids INV-006 runner bug pattern.

---

## Methodology

1. Load `^NSEI` close from cache; compute log returns; rolling 20-day std × √252 = annualized realized vol.
2. Compute percentile thresholds across full 15-year vol distribution: p30=0.1082, p70=0.1604.
3. Assign vol_bucket per date: Low (<p30), Medium (p30-p70), High (>p70).
4. Join vol_bucket to backtest signals via `scan_date`.
5. For each (signal × vol_bucket) of 9 cells: lifetime stats + train/test split + hypothesis_tester (BOOST + KILL).
6. Compare each cell to unfiltered baseline (full signal cohort, all buckets); classify CANDIDATE / MARGINAL / NO_EDGE per safe-default 2 (|Δ WR| ≥ 5pp + p < 0.05 + n ≥ 100 → CANDIDATE).

---

## Section 1 — Per-signal × per-bucket results

Unfiltered baselines (lifetime, full signal cohort across all buckets, vol-NaN signals excluded):

| Signal | n_excl_flat | Lifetime WR | Wilson_lower_95 |
|--------|-------------|-------------|------------------|
| UP_TRI | 71248 | 0.5283 | 0.5246 |
| DOWN_TRI | 17751 | 0.4474 | 0.4401 |
| BULL_PROXY | 4965 | 0.5003 | 0.4864 |

Per-cell results (signal × vol_bucket):

| Signal | Vol_bucket | n_excl_flat | WR | Wilson_lower | Δ vs base (pp) | p-value | BoostTier | KillTier | Verdict |
|--------|-----------|-------------|-----|--------------|----------------|---------|----------|----------|--------|
| UP_TRI | Low | 19573 | 0.5261 | 0.5191 | -0.22 | 0.582686 | REJECT | REJECT | NO_EDGE |
| UP_TRI | Medium | 29067 | 0.5199 | 0.5141 | -0.84 | 0.015729 | REJECT | REJECT | NO_EDGE |
| UP_TRI | High | 22608 | 0.5411 | 0.5346 | 1.28 | 0.000781 | REJECT | REJECT | NO_EDGE |
| DOWN_TRI | Low | 5667 | 0.4472 | 0.4342 | -0.02 | 0.972529 | REJECT | REJECT | NO_EDGE |
| DOWN_TRI | Medium | 7186 | 0.4538 | 0.4423 | 0.64 | 0.358387 | REJECT | REJECT | NO_EDGE |
| DOWN_TRI | High | 4898 | 0.4383 | 0.4245 | -0.91 | 0.258237 | REJECT | REJECT | NO_EDGE |
| BULL_PROXY | Low | 1572 | 0.5006 | 0.4759 | 0.03 | 0.981584 | REJECT | REJECT | NO_EDGE |
| BULL_PROXY | Medium | 2114 | 0.4801 | 0.4589 | -2.02 | 0.120328 | REJECT | REJECT | NO_EDGE |
| BULL_PROXY | High | 1279 | 0.5332 | 0.5058 | 3.29 | 0.035699 | REJECT | REJECT | MARGINAL |

---

## Section 2 — Surfaced filter candidates

**CANDIDATE cells (|Δ WR| ≥ 5pp + p < 0.05 + n ≥ 100):** 0

_No CANDIDATE cells surfaced._

**MARGINAL cells (|Δ WR| ≥ 2pp + p < 0.10 but below CANDIDATE threshold):** 1

| Signal | Vol_bucket | n | WR | Δ vs base (pp) | p-value |
|--------|-----------|---|-----|---------------|---------|
| BULL_PROXY | High | 1279 | 0.5332 | 3.29 | 0.035699 |

---

## Section 3 — Tier evaluation per cell

Train/test OOS split (2011-2022 / 2023-2026); tier per PROMOTION_PROTOCOL.md Gate 3.

| Signal | Vol_bucket | Boost_train_WR | Boost_test_WR | Boost_drift_pp | BoostTier | Kill_train_WR | Kill_test_WR | Kill_drift_pp | KillTier |
|--------|-----------|----------------|----------------|----------------|----------|---------------|--------------|----------------|----------|
| UP_TRI | Low | 0.5271 | 0.5248 | 0.23 | REJECT | 0.5271 | 0.5248 | 0.23 | REJECT |
| UP_TRI | Medium | 0.5281 | 0.4937 | 3.44 | REJECT | 0.5281 | 0.4937 | 3.44 | REJECT |
| UP_TRI | High | 0.5418 | 0.5351 | 0.67 | REJECT | 0.5418 | 0.5351 | 0.67 | REJECT |
| DOWN_TRI | Low | 0.4576 | 0.4313 | 2.63 | REJECT | 0.4576 | 0.4313 | 2.63 | REJECT |
| DOWN_TRI | Medium | 0.4504 | 0.4661 | 1.57 | REJECT | 0.4504 | 0.4661 | 1.57 | REJECT |
| DOWN_TRI | High | 0.4543 | 0.298 | 15.63 | REJECT | 0.4543 | 0.298 | 15.63 | REJECT |
| BULL_PROXY | Low | 0.5167 | 0.4792 | 3.75 | REJECT | 0.5167 | 0.4792 | 3.75 | REJECT |
| BULL_PROXY | Medium | 0.4869 | 0.4568 | 3.01 | REJECT | 0.4869 | 0.4568 | 3.01 | REJECT |
| BULL_PROXY | High | 0.5166 | 0.6741 | 15.75 | REJECT | 0.5166 | 0.6741 | 15.75 | REJECT |

**Cells earning Lab tier (S/A/B) on either BOOST or KILL hypothesis:** 0


---

## Section 4 — Cross-signal patterns

Per-bucket Δ WR averaged across signal types:

| Vol_bucket | Avg Δ WR (pp) | n_signals_evaluated |
|-----------|---------------|----------------------|
| Low | -0.07 | 3 |
| Medium | -0.74 | 3 |
| High | +1.22 | 3 |

Universal direction interpretation:
- **Low vol regime: signal-specific** (avg -0.07 pp; signs vary OR magnitude below 2pp).
- **Medium vol regime: signal-specific** (avg -0.74 pp; signs vary OR magnitude below 2pp).
- **High vol regime: signal-specific** (avg +1.22 pp; signs vary OR magnitude below 2pp).

---

## Section 5 — Headline findings (data only; NO promotion calls)

- **Cells evaluated:** 9 (3 signals × 3 vol buckets)
- **INSUFFICIENT_N cells:** 0
- **ERROR cells:** 0
- **CANDIDATE filter cells:** 0
- **MARGINAL cells:** 1
- **Tier-earning cells (BOOST or KILL S/A/B):** 0

**Headline:** No CANDIDATE filters surfaced at the 5pp+0.05 threshold; 1 MARGINAL cells suggest directional patterns but below promotion-grade significance. Vol regime filter does not yield clear edge in current universe.

---

## Section 6 — Open questions for user review

1. **CANDIDATE filter promotion:** for each CANDIDATE cell in Section 2, does sub-cohort tier-eligibility (Section 3) clear PROMOTION_PROTOCOL Gate 3? User decides per cell whether to add filter to mini_scanner_rules.

2. **Cross-signal universal patterns (Section 4):** if any vol regime universally improves or degrades WR across all 3 signal types, consider global filter (single config flag) vs signal-specific (per-signal filter).

3. **Caveat 2 audit dependency:** any CANDIDATE filter at marginal n (say n_filtered < 200) needs Caveat 2 audit before promotion.

4. **Vol bucket boundary sensitivity:** current p30 / p70 are arbitrary; user could request sensitivity analysis (p25/p75 or p20/p80) if findings depend strongly on bucket definition.

5. **patterns.json INV-007 status:** PRE_REGISTERED → COMPLETED is user-only transition.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC. User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change or main-branch promotion.
