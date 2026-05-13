# Validation 5 — Cohort-Wise Predictive Power

**Design ref:** doc/regime_v2_design/05_validation.md §V5

**Outcome:** **FAIL**

### P1 — ❌ FAIL

  - **v1_weighted_std_pnl**: 4.36
  - **v2_weighted_std_pnl**: 5.42
  - **threshold**: V2 < V1

### P2 — ❌ FAIL

  - **UP_TRI_bear_family_wr_v2**: 84.6
  - **UP_TRI_bear_family_n_v2**: 13
  - **BULL_PROXY_bear_family_wr_v2**: 100.0
  - **BULL_PROXY_bear_family_n_v2**: 1
  - **UP_TRI_bear_v1_baseline_wr**: 94.7
  - **thresholds**: UP_TRI Bear-family ≥85%, BULL_PROXY Bear-family ≥75%
  - **details**: {'UP_TRI_bear_pass': np.False_, 'BULL_PROXY_bear_pass': np.True_}

### P3 — ✅ PASS

  - **count**: 2
  - **cohorts**:
    - {'signal_type': 'BULL_PROXY', 'v2_regime': 'CHOPPY', 'n': 26, 'wins': 17, 'avg_pnl': 3.88, 'std_pnl': 6.04, 'wr_pct': 65.4}
    - {'signal_type': 'UP_TRI', 'v2_regime': 'CHOPPY', 'n': 188, 'wins': 115, 'avg_pnl': 2.41, 'std_pnl': 5.32, 'wr_pct': 61.2}
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
| BULL_PROXY | BEAR_RECOVERY | 1 | 100.0 | 4.1 | nan |
| BULL_PROXY | CHOPPY | 26 | 65.4 | 3.88 | 6.04 |
| BULL_PROXY | nan | 4 | 0.0 | -3.86 | 1.19 |
| DOWN_TRI | BEAR_RECOVERY | 17 | 35.3 | -2.26 | 5.22 |
| DOWN_TRI | CHOPPY | 34 | 32.4 | -4.51 | 6.34 |
| DOWN_TRI | nan | 3 | 0.0 | -6.65 | 1.98 |
| UP_TRI | BEAR_RECOVERY | 13 | 84.6 | 4.32 | 3.54 |
| UP_TRI | CHOPPY | 188 | 61.2 | 2.41 | 5.32 |
