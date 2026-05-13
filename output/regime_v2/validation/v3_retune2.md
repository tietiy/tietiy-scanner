# Validation 3 — Transition Reasonableness

**Design ref:** doc/regime_v2_design/05_validation.md §V3
**Window:** 2025-05-01 → 2026-05-05
**Outcome:** **FAIL**

## Criteria

### T1 — ✅ PASS

  - **value**: 19
  - **range**: 6 ≤ x ≤ 20

### T2 — ✅ PASS

  - **n_inflections**: 2
  - **n_captured**: 2
  - **pct**: 100.0
  - **threshold**: ≥ 75%
  - **log**:
    - {'inflection': '2026-03-13', 'nearest_transition': '2026-03-16', 'days_off': 3, 'captured': True}
    - {'inflection': '2026-04-08', 'nearest_transition': '2026-04-07', 'days_off': 1, 'captured': True}

### T3 — ❌ FAIL

  - **n_false**: 5
  - **n_transitions**: 19
  - **pct**: 26.3
  - **threshold**: ≤ 20%

