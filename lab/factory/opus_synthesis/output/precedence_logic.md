# Precedence Logic — v4 Rule Evaluation

This document defines how the v4 rule engine evaluates a signal against
the 23-rule corpus to produce a single verdict with a calibrated WR
estimate.

## Overview — 4-Layer Evaluation

Rules evaluate in strict order. Layer 1 is terminating; layers 2-4 are
non-terminating but compose pessimistically (most conservative wins).
Layer 4 is upgrade-only.

```
Signal arrives
  ↓
Layer 1: KILL / REJECT (terminating)
  ↓ (if no terminating match)
Layer 2: Sub-regime gate (establish baseline)
  ↓
Layer 3: Sector / Calendar pessimistic merge
  ↓
Layer 4: Phase-5 override (upgrade-only)
  ↓
Final verdict + calibrated WR
```

---

## Layer 1 — KILL/REJECT (terminating)

**Rule types:** `type=kill` with `verdict=REJECT` or `verdict=SKIP`
that are unconditional (no sub-regime gate, or sub-regime IS the kill).

**Behavior:** First match wins. No further evaluation. Output verdict
and stop.

**Examples in v4 corpus:**
- `kill_001` — Bank × DOWN_TRI × Bear → REJECT
- `rule_005` — vol_climax × BULL_PROXY × Bear → REJECT
- `rule_006` — vol_climax × BULL_PROXY × Bull-late_bull → REJECT
- `rule_007` — Health × UP_TRI × Bear → SKIP (32.4% lifetime; AVOID)
- `rule_008` — December × UP_TRI × Bear → SKIP (-25pp catastrophic)
- `rule_009` — February × UP_TRI × Choppy → SKIP (-16.2pp Budget vol)
- `rule_010` — BULL_PROXY × Choppy → REJECT (entire cell KILL)
- `rule_001` — late_bull × UP_TRI × Bull → SKIP
- `rule_002` — late_bull × BULL_PROXY × Bull → SKIP

**Implementation:** Iterate `kill` rules in priority order
(HIGH → MEDIUM → LOW). Match on `match_fields` AND all `conditions`.
First match terminates evaluation.

---

## Layer 2 — Sub-regime gate

**Rule types:** Implicit (the sub-regime classifier itself).

**Behavior:** Sub-regime classification establishes baseline verdict
eligibility. The classifier outputs a tier label which feeds into
Layer 3 matching:

| Sub-regime tier | Default verdict eligibility | Calibrated WR floor |
|---|---|---|
| Bear hot / boundary_hot | TAKE_FULL | 65-75% |
| Bear confident_hot | TAKE_FULL | 60-65% |
| Bear warm | TAKE_FULL | 70-90% (deferred until lifetime cohort accumulates) |
| Bear cold + Tier 1 cascade | TAKE_FULL | 60-65% |
| Bear cold (no cascade) | SKIP | 49-55% |
| Bull recovery_bull | TAKE_FULL eligible | 60-72% |
| Bull healthy_bull | TAKE_FULL eligible | 58-66% |
| Bull normal_bull | TAKE_SMALL eligible | 51-58% |
| Bull late_bull | SKIP (terminated at L1 via rule_001/002) | n/a |
| Choppy high_medium_flat | TAKE_FULL eligible | 58-65% |
| Choppy other 3-axis cells | TAKE_SMALL or SKIP per cell | varies |

**Boundary tier handling (per B1):**

The B1 finding states `boundary_hot` (just-into-hot) WR = 71.5% beats
`confident_hot` (deep-hot) WR = 64.2%. The 4-tier classifier exposes
this:

```
confident_hot:   TAKE_FULL @ 60-65%
boundary_hot:    TAKE_FULL @ 65-75% (highest WR — counterintuitive)
boundary_cold:   TAKE_SMALL @ 55-60% (transitional)
confident_cold:  SKIP / cascade @ ≤55%
```

**Hysteresis (Choppy):** N=2 composite confirmation prevents whipsaw.
First 2 days of new sub-regime label use previous CONFIRMED label (or
conservative fallback if NULL bootstrap).

---

## Layer 3 — Sector / Calendar pessimistic merge

**Rule types:** `type=boost` with `verdict=TAKE_FULL/TAKE_SMALL`,
`type=kill` with `verdict=SKIP` that are NOT sub-regime-only kills.

**Behavior:** Non-terminating. All matching rules collected.
Pessimistic composition rule:

```
SKIP > TAKE_SMALL > TAKE_FULL
```

The MOST CONSERVATIVE verdict among all matching rules wins.

**Boost rules CONFIRM but do NOT UPGRADE.** A TAKE_FULL boost rule
matching a sub-regime that's already eligible for TAKE_FULL produces
TAKE_FULL (no change). A TAKE_FULL boost matching a TAKE_SMALL
sub-regime eligibility STAYS at TAKE_SMALL (boost does not upgrade).

**Composition table:**

| Sub-regime baseline | Sector/Cal rule | Final |
|---|---|---|
| TAKE_FULL | (no rule) | TAKE_FULL |
| TAKE_FULL | TAKE_FULL boost | TAKE_FULL (confirmed) |
| TAKE_FULL | TAKE_SMALL | TAKE_SMALL (downgrade) |
| TAKE_FULL | SKIP | SKIP (downgrade) |
| TAKE_SMALL | TAKE_FULL boost | TAKE_SMALL (NO upgrade — Layer 3 cannot upgrade) |
| TAKE_SMALL | SKIP | SKIP |
| SKIP | (any) | SKIP |

---

## Layer 4 — Phase-5 override (upgrade-only)

**Rule types:** Not in v4 rule corpus directly; lookup in
`combinations_live_validated.parquet`.

**Behavior:** Phase-5 override CAN upgrade verdict (e.g.,
TAKE_SMALL → TAKE_FULL) when feature-specific live evidence exceeds
sub-regime base rate. Cannot downgrade.

**Trigger conditions (ALL required):**
1. `live_n >= 10`
2. `live_tier == "VALIDATED"`
3. Wilson 95% lower bound > Layer-3 verdict's calibrated WR + 5pp
4. Combo data within last 90 days (recency check)

**Selection (multiple matches):** Pick combo with highest Wilson
lower bound.

**Output:** Final verdict + override-aware calibrated WR. Telegram
should display both:
```
Calibrated WR: 76% (Phase-5 override on inside_bar=True, n=27, Wilson 76.6%)
Sub-regime base: 71.5% (boundary_hot)
```

---

## Worked Conflict Examples

### Example 1: Bear UP_TRI × Health (Layer 1 termination)

```
Signal: HDFC.NS UP_TRI in Bear regime, Health sector, vp=0.78, n60=-0.13

Layer 1 evaluation:
  - rule_007 (Health × UP_TRI × Bear) MATCHES → SKIP
  - TERMINATE

Final verdict: SKIP
Calibrated WR: 32% (n/a; signal blocked)
Reason: "Health sector hostile in Bear UP_TRI (32.4% lifetime in hot)"
```

### Example 2: Bull UP_TRI recovery_bull × Sep (pessimistic merge)

```
Signal: TCS.NS UP_TRI in Bull regime, IT sector, recovery_bull sub-regime,
        vol=Medium, fvg_low=true, month=September, wk4

Layer 1: No KILL match (rule_001 late_bull doesn't apply; rule_014 Sep
         is production_ready=false in initial deployment)

Layer 2: recovery_bull → TAKE_FULL eligible (60-72%)

Layer 3:
  - rule_003 (recovery_bull × vol=Med × fvg_low) → TAKE_FULL boost
  - rule_014 (Sep Bull UP_TRI) → SKIP (if active)
  Pessimistic merge:
    - If rule_014 active: SKIP wins
    - If rule_014 inactive (initial Phase B deployment): TAKE_FULL

Layer 4: No Bull VALIDATED combos (cell PROVISIONAL_OFF) → no override

Final verdict (Phase B): TAKE_FULL @ 72% calibrated
Final verdict (Phase D, after rule_014 active): SKIP
Reason (Phase D): "September Bull catastrophic month (-8.4pp); pessimistic merge"
```

### Example 3: Bear UP_TRI hot × Phase-5 override

```
Signal: TATA.NS UP_TRI in Bear regime, Metal sector, hot sub-regime
        (vp=0.73, n60=-0.12), feat_inside_bar=True

Layer 1: No KILL match (Metal not Health; not December)

Layer 2: hot → boundary_hot tier (vp 0.73 just-inside; n60 -0.12 just-inside)
         Calibrated baseline 71.5% (boundary_hot per B1)

Layer 3:
  - win_004 (Metal × UP_TRI × Bear) → TAKE_FULL boost
  Final after L3: TAKE_FULL @ 71.5%

Layer 4: Phase-5 override search
  - Combo (inside_bar_flag=True, Bear UP_TRI) VALIDATED, n=13, live_wr=92.3%,
    Wilson lower=66.7%
  - Override trigger check: 66.7% < 71.5% + 5pp = 76.5%? YES, 66.7% is
    BELOW 76.5%, so override does NOT trigger.
  - Sub-regime base wins.

Final verdict: TAKE_FULL @ 71.5% (boundary_hot)
WR source: sub_regime_boundary_hot (NOT phase5_override)
Reason: "Bear UP_TRI boundary_hot tier; Metal sector confirms; Phase-5 base
         insufficient to upgrade beyond sub-regime"
```

---

## Implementation pseudocode

```python
def evaluate_signal(signal, market_state, combo_db):
    # Layer 1: KILL terminating
    for rule in kill_rules_by_priority(active=True):
        if matches(signal, rule):
            return Verdict(rule.verdict, rule.expected_wr, "kill", rule.id)

    # Layer 2: Sub-regime gate
    sub_regime = detect_subregime(signal.regime, market_state)
    base_verdict, base_wr = sub_regime_baseline(sub_regime, signal.signal)

    if base_verdict == "SKIP":
        return Verdict("SKIP", base_wr, "sub_regime_skip", sub_regime)

    # Layer 3: Sector / Calendar pessimistic merge
    matched_rules = [r for r in non_kill_rules(active=True) if matches(signal, r)]
    final_verdict = base_verdict
    final_wr = base_wr
    triggered_ids = []

    for rule in matched_rules:
        if rule.verdict == "SKIP":
            return Verdict("SKIP", rule.expected_wr, "pessimistic_skip", rule.id)
        if rule.verdict == "TAKE_SMALL" and final_verdict == "TAKE_FULL":
            final_verdict = "TAKE_SMALL"
            final_wr = min(final_wr, rule.expected_wr)
        # TAKE_FULL boost: confirms, no upgrade
        triggered_ids.append(rule.id)

    # Layer 4: Phase-5 override (upgrade-only)
    override = find_phase5_override(signal, combo_db, base_wr)
    if override and override.wilson_lower > final_wr + 0.05:
        final_verdict = "TAKE_FULL"  # upgrade
        final_wr = override.wilson_lower
        return Verdict(final_verdict, final_wr, "phase5_override",
                       override.combo_id)

    return Verdict(final_verdict, final_wr, "composed", triggered_ids)
```

---

## Edge cases and tie-breaking

1. **Multiple Layer 1 matches:** Iterate by priority HIGH → MEDIUM → LOW.
   First match wins. Within same priority, by `id` lexicographic order.

2. **Multiple Layer 3 matches with same verdict:** Confirms the verdict;
   pick highest `expected_wr` for display.

3. **Sub-regime "unknown" (missing features):** Fail-closed → SKIP with
   reason="sub_regime_unknown".

4. **Conflicting Phase-5 overrides:** Pick max(Wilson_lower).

5. **Activation gate (first 10 days of regime change):** Shadow mode
   per Bull/Bear PRODUCTION_POSTURE; signals logged but not promoted.
   Verdicts shown as "SHADOW" in Telegram.
