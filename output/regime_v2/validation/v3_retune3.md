# Validation 3 — Transition Reasonableness

**Design ref:** doc/regime_v2_design/05_validation.md §V3
**Window:** 2025-05-01 → 2026-05-05
**Outcome:** **FAIL**

## Criteria

### T1 — ❌ FAIL

  - **value**: 25
  - **range**: 6 ≤ x ≤ 20

### T2 — ✅ PASS

  - **n_inflections**: 2
  - **n_captured**: 2
  - **pct**: 100.0
  - **threshold**: ≥ 75%
  - **log**:
    - {'inflection': '2026-03-13', 'nearest_transition': '2026-03-13', 'days_off': 0, 'captured': True}
    - {'inflection': '2026-04-08', 'nearest_transition': '2026-04-06', 'days_off': 2, 'captured': True}

### T3 — ❌ FAIL

  - **n_false**: 10
  - **n_transitions**: 25
  - **pct**: 40.0
  - **threshold**: ≤ 20%

