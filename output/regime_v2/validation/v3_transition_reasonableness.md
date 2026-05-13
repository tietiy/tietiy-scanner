# Validation 3 — Transition Reasonableness

**Design ref:** doc/regime_v2_design/05_validation.md §V3
**Window:** 2025-05-01 → 2026-05-05
**Outcome:** **FAIL**

## Criteria

### T1 — ❌ FAIL

  - **value**: 21
  - **range**: 6 ≤ x ≤ 20

### T2 — ❌ FAIL

  - **n_inflections**: 2
  - **n_captured**: 1
  - **pct**: 50.0
  - **threshold**: ≥ 75%
  - **log**:
    - {'inflection': '2026-03-13', 'nearest_transition': '2026-03-09', 'days_off': 4, 'captured': True}
    - {'inflection': '2026-04-08', 'nearest_transition': '2026-04-02', 'days_off': 6, 'captured': False}

### T3 — ❌ FAIL

  - **n_false**: 5
  - **n_transitions**: 21
  - **pct**: 23.8
  - **threshold**: ≤ 20%

