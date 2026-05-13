# Validation 5 — Cohort-Wise Predictive Power

**Design ref:** doc/regime_v2_design/05_validation.md §V5

**Outcome:** **FAIL**

### P1 — ❌ FAIL

  - **v1_weighted_std_pnl**: 4.36
  - **v2_weighted_std_pnl**: 5.45
  - **threshold**: V2 < V1

### P2 — ❌ FAIL

  - **UP_TRI_bear_family_wr_v2**: 100.0
  - **UP_TRI_bear_family_n_v2**: 1
  - **BULL_PROXY_bear_family_wr_v2**: 0.0
  - **BULL_PROXY_bear_family_n_v2**: 0
  - **UP_TRI_bear_v1_baseline_wr**: 94.7
  - **thresholds**: UP_TRI Bear-family ≥85%, BULL_PROXY Bear-family ≥75%
  - **details**: {'UP_TRI_bear_pass': np.True_, 'BULL_PROXY_bear_pass': False}

### P3 — ✅ PASS

  - **count**: 2
  - **cohorts**:
    - {'signal_type': 'BULL_PROXY', 'v2_regime': 'CHOPPY', 'n': 27, 'wins': 18, 'avg_pnl': 3.89, 'std_pnl': 5.92, 'wr_pct': 66.7}
    - {'signal_type': 'UP_TRI', 'v2_regime': 'CHOPPY', 'n': 200, 'wins': 125, 'avg_pnl': 2.52, 'std_pnl': 5.24, 'wr_pct': 62.5}
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
| BULL_PROXY | CHOPPY | 27 | 66.7 | 3.89 | 5.92 |
| BULL_PROXY | nan | 4 | 0.0 | -3.86 | 1.19 |
| DOWN_TRI | CHOPPY | 51 | 33.3 | -3.76 | 6.03 |
| DOWN_TRI | nan | 3 | 0.0 | -6.65 | 1.98 |
| UP_TRI | BEAR_RECOVERY | 1 | 100.0 | 5.23 | nan |
| UP_TRI | CHOPPY | 200 | 62.5 | 2.52 | 5.24 |
