# Validation 5 — Cohort-Wise Predictive Power

**Design ref:** doc/regime_v2_design/05_validation.md §V5

**Outcome:** **FAIL**

### P1 — ❌ FAIL

  - **v1_weighted_std_pnl**: 4.36
  - **v2_weighted_std_pnl**: 4.79
  - **threshold**: V2 < V1

### P2 — ✅ PASS

  - **UP_TRI_bear_family_wr_v2**: 92.9
  - **UP_TRI_bear_family_n_v2**: 42
  - **BULL_PROXY_bear_family_wr_v2**: 90.0
  - **BULL_PROXY_bear_family_n_v2**: 10
  - **UP_TRI_bear_v1_baseline_wr**: 94.7
  - **thresholds**: UP_TRI Bear-family ≥85%, BULL_PROXY Bear-family ≥75%
  - **details**: {'UP_TRI_bear_pass': np.True_, 'BULL_PROXY_bear_pass': np.True_}

### P3 — ❌ FAIL

  - **count**: 0
  - **cohorts**: []
  - **threshold**: ≥ 1 (bonus)

### P4 — ✅ PASS

  - **n_v2_cohorts_with_wr_ge_50**: 0
  - **violators**: []
  - **threshold**: 0 V2 sub-cohorts with WR ≥ 50%

## V1 cohorts (resolved-only)

| signal | v1_regime | n | wr% | avg_pnl | std_pnl |
|---|---|---:|---:|---:|---:|
| BULL_PROXY | Bear | 16 | 87.5 | 7.03 | 4.96 |
| BULL_PROXY | Choppy | 15 | 26.7 | -1.53 | 3.67 |
| DOWN_TRI | Bear | 20 | 20.0 | -7.28 | 6.03 |
| DOWN_TRI | Choppy | 34 | 38.2 | -1.95 | 4.93 |
| UP_TRI | Bear | 94 | 94.7 | 5.99 | 3.79 |
| UP_TRI | Choppy | 107 | 34.6 | -0.51 | 4.37 |

## V2 cohorts (resolved-only)

| signal | v2_regime | n | wr% | avg_pnl | std_pnl |
|---|---|---:|---:|---:|---:|
| BULL_PROXY | BEAR | 9 | 88.9 | 9.84 | 4.65 |
| BULL_PROXY | BEAR_RECOVERY | 1 | 100.0 | 4.1 | nan |
| BULL_PROXY | CHOPPY | 17 | 52.9 | 0.72 | 3.95 |
| BULL_PROXY | nan | 4 | 0.0 | -3.86 | 1.19 |
| DOWN_TRI | BEAR | 18 | 22.2 | -7.36 | 6.31 |
| DOWN_TRI | BEAR_RECOVERY | 17 | 35.3 | -2.26 | 5.22 |
| DOWN_TRI | CHOPPY | 16 | 43.8 | -1.31 | 4.76 |
| DOWN_TRI | nan | 3 | 0.0 | -6.65 | 1.98 |
| UP_TRI | BEAR | 40 | 95.0 | 7.16 | 4.11 |
| UP_TRI | BEAR_RECOVERY | 2 | 50.0 | 2.8 | 7.45 |
| UP_TRI | CHOPPY | 159 | 54.7 | 1.36 | 4.83 |
