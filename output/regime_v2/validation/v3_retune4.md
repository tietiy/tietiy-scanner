# Validation 3 — Transition Reasonableness

**Design ref:** doc/regime_v2_design/05_validation.md §V3
**Window:** 2025-05-01 → 2026-05-05
**Outcome:** **FAIL**

## Criteria

### T1 — ❌ FAIL

  - **value**: 33
  - **range**: 6 ≤ x ≤ 20

### T2 — ❌ FAIL

  - **n_inflections**: 2
  - **n_captured**: 1
  - **pct**: 50.0
  - **threshold**: ≥ 75%
  - **log**:
    - {'inflection': '2026-03-13', 'nearest_transition': '2026-03-11', 'days_off': 2, 'captured': True}
    - {'inflection': '2026-04-08', 'nearest_transition': '2026-04-20', 'days_off': 12, 'captured': False}

### T3 — ❌ FAIL

  - **n_false**: 15
  - **n_transitions**: 33
  - **pct**: 45.5
  - **threshold**: ≤ 20%

