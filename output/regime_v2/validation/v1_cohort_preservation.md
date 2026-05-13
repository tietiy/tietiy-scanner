# Validation 1 — Cohort Preservation

**Design ref:** doc/regime_v2_design/05_validation.md §V1

**Outcome:** **FAIL**

## Setup

- Total signals: 372
- Resolved signals: 286
- UP_TRI × Bear (V1, resolved): n=94

## Criteria

### C1 — ❌ FAIL

  - **pct**: 11.7
  - **count_preserved**: 11
  - **count_original**: 94
  - **threshold**: ≥ 80%

### C2 — ✅ PASS

  - **wr_pct**: 90.9
  - **threshold**: ≥ 85%

### C3 — ✅ PASS

  - **pct_adjacent**: 100.0
  - **out_distribution**: {'CHOPPY': 83}
  - **threshold**: ≥ 80% in CHOPPY or BEAR_RECOVERY

### C4 — ✅ PASS

  - **n_resolved**: 0
  - **wr_pct**: None
  - **threshold**: n<5 (no false attribution) OR WR>60%

### C5 — ❌ FAIL

  - **pct**: 83.9
  - **threshold**: = 100%

