# Precedence Logic — Path 1 (Disciplined)

**Schema version:** 4
**Date:** 2026-05-03
**Scope:** 4-layer rule evaluation model for unified_rules_path1.json (24 rules).

---

## Overview

Rule evaluation is a 4-layer pipeline. Each signal traverses all layers in
order. Earlier layers can terminate; later layers modulate but don't
override sub-regime conservatism unless via explicit Phase-5 upgrade.

```
Layer 1: KILL/REJECT    (terminating; outputs SKIP/REJECT and stops)
Layer 2: Sub-regime gate (establishes baseline verdict)
Layer 3: Sector/Calendar (pessimistic merge — most conservative wins)
Layer 4: Phase-5 override (upgrade-only, gated by Wilson lower bound)
```

---

## Layer 1 — KILL/REJECT (terminating)

If ANY rule with type ∈ {kill} matches, evaluation stops and the rule's
verdict (SKIP or REJECT) is final.

Rules at this layer:
- `kill_001` — Bank × DOWN_TRI → REJECT
- `rule_001` — late_bull × Bull UP_TRI → SKIP
- `rule_002` — late_bull × Bull BULL_PROXY → SKIP
- `rule_005` — vol_climax × Bear BULL_PROXY → REJECT
- `rule_006` — vol_climax × late_bull × Bull BULL_PROXY → REJECT
- `rule_007` — Health × Bear UP_TRI × hot → SKIP
- `rule_008` — December × Bear UP_TRI → SKIP
- `rule_009` — February × Choppy UP_TRI → SKIP
- `rule_010` — Choppy BULL_PROXY (entire cell) → REJECT
- `rule_013` — Energy × Bull UP_TRI → SKIP (LOW priority; production_ready=false)
- `rule_014` — September × Bull UP_TRI → SKIP (LOW)
- `rule_015` — Pharma × Choppy DOWN_TRI → SKIP (LOW)
- `rule_016` — Friday × Choppy DOWN_TRI → SKIP (LOW)
- `rule_017` — Metal × Choppy UP_TRI → SKIP (LOW)
- `rule_018` — wk4 × Choppy DOWN_TRI → SKIP (LOW)

**Tie-breaking among multiple kill matches:** REJECT > SKIP. If
both REJECT and SKIP rules match, REJECT is final (stronger semantic).

---

## Layer 2 — Sub-regime gate

If no Layer 1 kill matches, evaluate sub-regime classification. Sub-regime
is computed at runtime from market state via per-regime detectors:

- **Bear detector** (`bear/subregime/detector.py`):
  - hot: vp > 0.70 AND n60 < -0.10
  - warm: vp > 0.70 AND -0.10 <= n60 < 0
  - cold: else

- **Bull detector** (`bull/subregime/detector.py`):
  - recovery_bull: 200d < 0.05 AND breadth < 0.60
  - healthy_bull: 200d in [0.05, 0.20] AND breadth > 0.80
  - late_bull: 200d in [0.05, 0.20] AND breadth < 0.60
  - normal_bull: else

If a rule has `sub_regime_constraint != null`, the rule only fires when
the runtime sub-regime matches.

Sub-regime gate establishes the baseline verdict for the signal:
- Boost rules with matching sub-regime → eligible for TAKE_FULL/TAKE_SMALL
- Sub-regime not matching any boost → eligible for default action per regime baseline

---

## Layer 3 — Sector/Calendar (pessimistic merge)

Sector and calendar rules are NON-terminating modulators. They modify
the Layer 2 baseline via pessimistic composition:

**Most conservative verdict wins**:
```
REJECT > SKIP > TAKE_SMALL > TAKE_FULL
```

Boost rules at this layer (e.g., `win_001` for Auto×Bear UP_TRI) confirm
TAKE_FULL but don't UPGRADE. If sub-regime gate already produced
TAKE_FULL, sector boost adds no lift. If sub-regime produced TAKE_SMALL
or SKIP, sector boost cannot override.

Boost rules can however MATCH at this layer to provide audit trail
("which boost rule confirms this verdict").

---

## Layer 4 — Phase-5 override (upgrade-only)

Phase-5 override is upgrade-only. It can promote TAKE_SMALL → TAKE_FULL
when:
1. live_n >= 10
2. Wilson 95% lower bound > sub-regime base + 5pp
3. live_tier == VALIDATED
4. Combo recency within 90 days

Override CANNOT downgrade. Layer 1 kills are unchallengeable by override.

---

## Worked Conflict Examples

### Example 1: Bear UP_TRI Health hot — Layer 1 terminates

```
Signal: HCLTECH UP_TRI, sector=Health, regime=Bear
Sub-regime detected: hot (vp=0.78, n60=-0.13)

Layer 1: rule_007 (Health × Bear UP_TRI × hot) MATCHES → SKIP, terminate.

Final verdict: SKIP
WR: N/A
Audit: kill rule_007 fired; Health is the one Bear sector where hot fails (32.4%).

Note: Without sub_regime_constraint='hot' on rule_007, the rule would
match all 311 lifetime Bear Health UP_TRI signals at 48.6% (Bear Health
baseline). With the constraint, it only matches the ~158 hot subset at
32.4% — the actual hostile cohort. This was Step 3's primary FAIL fix.
```

### Example 2: Bear UP_TRI Auto warm — Layer 2 + Layer 3 confirm

```
Signal: TATAMOTORS UP_TRI, sector=Auto, regime=Bear
Sub-regime detected: warm (vp=0.72, n60=-0.05)
Calendar: April

Layer 1: No kill matches. (Health constraint doesn't apply; no December.)
Layer 2: Sub-regime warm → eligible for TAKE_FULL (per Bear UP_TRI playbook).
Layer 3: win_001 (Auto × Bear UP_TRI) MATCHES → TAKE_FULL boost confirms.
         No calendar mismatch (April is favorable for Bear UP_TRI per playbook).
Layer 4: Check Phase-5 override database. No VALIDATED combo at Wilson lower
         bound > 70% + 5pp = 75%. Override does not trigger.

Final verdict: TAKE_FULL
WR: 65-75% (boundary_hot/warm calibrated; lifetime hot baseline 68.3%)
Audit: win_001 boost confirms; sub-regime warm gates entry.
```

### Example 3: Bull UP_TRI recovery_bull with September skip — Layer 3 pessimistic merge

```
Signal: TCS UP_TRI, sector=IT, regime=Bull
Sub-regime detected: recovery_bull (200d=-0.02, breadth=0.45)
Features: vol_regime=Medium, fvg_unfilled_above_count=1
Calendar: September

Layer 1: rule_014 (September × Bull UP_TRI) MATCHES → SKIP, terminate.

Final verdict: SKIP
WR: N/A (September block at Layer 1)
Audit: Even though rule_003 (recovery_bull × vol=Med × fvg_low) would
       have produced 74% WR TAKE_FULL at Layer 2/3, Layer 1 calendar
       kill terminates first.

Note: rule_014 is currently production_ready=false (LOW priority). When
production_ready is enforced, this rule does NOT fire and the signal
proceeds to Layer 2 producing TAKE_FULL. This demonstrates the
production_ready flag's gating effect on Layer 1 evaluation.
```

---

## Production_ready gating

Rules with `production_ready=false` are evaluated in shadow mode only —
they log matches for audit but do not affect the final verdict. This
applies to all LOW priority rules in Path 1 initial deployment
(rule_013, rule_014, rule_015, rule_016, rule_017, rule_018) plus
rule_006 (sparse Bull late_bull vol_climax intersection).

When LOW rules are promoted to production_ready=true (Phase 2 of
deployment), they integrate into Layer 1 evaluation per the precedence
above.

---

## Schema migration note (v3 → v4)

Schema v3 used flat fields (signal, sector, regime). Schema v4 introduces
the 2-tier model:

- `match_fields`: top-level matchers (signal, sector, regime)
- `conditions`: array of feature-value-operator triples (AND-gated)
- `sub_regime_constraint`: explicit sub-regime gate (null if not gated)

All Path 1 rules carry the v4 schema. Existing v3 rules (kill_001,
watch_001, win_001-007) are re-emitted with empty `conditions` arrays
and `sub_regime_constraint: null` (except win_007 which gates on hot).
