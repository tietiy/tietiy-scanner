# Path 1 (DISCIPLINED) — Opus Rule Synthesis Prompt — Step 4

## Role

You are iterating on the Step 3 Opus rule synthesis. Step 3 produced
26 rules with 38% PASS / 65% PASS+WARNING validation rate. Path 1 is
the **explicit-constraints iteration**: address each Step 3 failure
with hard-coded thresholds and specific instructions.

## Input package (provided as separate documents)

You receive 4 reference documents and the full Step 3 input package:

### Reference docs (CRITICAL — read first)
1. **`path1_thresholds_explicit.md`** — Lab's exact bucket thresholds
   (feature library + sub-regime detectors). NEVER infer; ALWAYS use these.
2. **`path1_step3_failure_analysis.md`** — categorized Step 3
   failures with root causes.
3. **`path1_specific_instructions.md`** — per-rule iteration
   directives. Each FAIL rule has a specific fix.
4. **`step3_validation_report.json`** — Step 3 actual vs predicted
   per rule.

### Step 3 input package (for reference, same as Step 3)
- 9 cell playbooks (`playbooks/`)
- 3 regime synthesis docs (`regime_synthesis/`)
- 14 critique resolution files (`critiques/`)
- 2 PRODUCTION_POSTURE docs (`posture/`)
- Existing production rules (`production/current_rules.json`)
- Bull verification report (`production/bull_verification.md`)

---

## YOUR TASK (Path 1 Disciplined)

Re-synthesize the Lab findings into 5 production deliverables, **using the
exact Lab thresholds documented in `path1_thresholds_explicit.md`** and
**addressing each failure documented in `path1_step3_failure_analysis.md`**.

The Path 1 mandate is **explicit constraints win over interpretive
freedom**. If your judgment differs from the documented thresholds or
specific instructions, follow the documents — your iteration is
constrained intentionally.

---

## DELIVERABLE 1 — `unified_rules_path1.json`

Same v4 schema as Step 3 (2-tier: match_fields + conditions array).

### Rule count target

**24 rules total** (15 NEW + 9 EXISTING):
- 14 priority-ranked rules (5 HIGH + 5 MEDIUM + 4 LOW) — same as Step 3 spec
- 1 NEW rule_018 (wk4 × Choppy DOWN_TRI = SKIP) — restoring dropped component
- 9 EXISTING rules (kill_001, watch_001, win_001-007) re-emitted compatibly

If logical rule has multiple natural parts (e.g., late_bull SKIP for
both UP_TRI and BULL_PROXY), you MAY split into multiple atomic rules
(Step 3 did this and it was acceptable). But you MUST NOT drop any
component (wk4 was dropped — restore it as rule_018).

### Mandatory adjustments per `path1_specific_instructions.md`

- **rule_002**: Bull detector breadth thresholds (0.60/0.80), realistic count prediction
- **rule_003**: recovery_bull definition + vol=Medium categorical + fvg<2 numeric
- **rule_004**: healthy_bull (200d in [0.05,0.20] AND breadth>0.80) + 20d>0.05
- **rule_005**: realistic prediction for sparse vol_climax_flag
- **rule_006**: realistic prediction for narrow late_bull × vol_climax intersection
- **rule_007**: ADD `sub_regime_constraint='hot'` (currently missing — root cause of FAIL)
- **rule_008**: Realistic count for Dec × Bear UP_TRI (1,200-1,900 not 850)
- **rule_012**: cold sub_regime + wk4 + swing_high<2 (numeric, not categorical bucket)
- **win_003**: expected_wr=0.61 (lifetime), not 0.70 (live small-n)
- **win_006**: expected_wr=0.65 (between live and lifetime drift)
- **rule_018** (NEW): wk4 × Choppy DOWN_TRI = SKIP

### Schema reminder

```json
{
  "id": "rule_NNN",
  "active": true,
  "type": "kill" | "boost" | "warn" | "watch",
  "match_fields": {
    "signal": "UP_TRI" | "DOWN_TRI" | "BULL_PROXY" | null,
    "sector": "Bank" | ... | null,
    "regime": "Bear" | "Bull" | "Choppy" | null
  },
  "conditions": [
    {"feature": "<feature_name>", "value": <value>, "operator": "eq"|"in"|"gt"|"lt"|"gte"|"lte"}
  ],
  "verdict": "TAKE_FULL" | "TAKE_SMALL" | "WATCH" | "SKIP" | "REJECT",
  "expected_wr": 0.65,
  "confidence_tier": "HIGH" | "MEDIUM" | "LOW",
  "trade_mechanism": "mean_reversion" | "breakout_continuation" | "regime_transition" | "trend_fade" | "support_bounce_reversal" | "counter_trend",
  "regime_constraint": "Bear" | "Bull" | "Choppy" | "any",
  "sub_regime_constraint": "hot" | "warm" | "cold" | "recovery_bull" | "healthy_bull" | "late_bull" | "normal_bull" | null,
  "production_ready": true | false,
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "source_playbook": "...",
  "source_finding": "...",
  "evidence": {"n": 0, "wr": 0.0, "lift_pp": 0.0, "tier": "..."}
}
```

---

## DELIVERABLE 2 — `precedence_logic_path1.md`

Same 4-layer model as Step 3:
1. KILL/REJECT terminating
2. Sub-regime gate
3. Sector / Calendar pessimistic merge
4. Phase-5 override (upgrade-only)

Include 3 worked conflict examples, with at least one example
showing how sub_regime_constraint correctly gates rule_007 (Health ×
Bear UP_TRI = AVOID only in HOT, not in WARM/COLD).

---

## DELIVERABLE 3 — `b1_b2_coupling_path1.md`

Same as Step 3: B1 (4-tier display) ships now; B2 (sigmoid) deferred.

In Path 1, additionally specify:
- Tier-to-verdict mapping uses sub_regime_constraint (e.g., boundary_hot
  is a sub-regime, not a separate field)
- The 4-tier system maps to sub_regime values: confident_hot, boundary_hot,
  boundary_cold, confident_cold

---

## DELIVERABLE 4 — `validation_predictions_path1.json`

For each rule, predict expected behavior using the **CORRECTED Lab
thresholds**. Specifically:
- recovery_bull: ~972 lifetime / 38,100 = 2.6% population baseline
- healthy_bull: ~4,764 / 38,100 = 12.5% population baseline
- late_bull: ~2,699 / 38,100 = 7.1% population baseline
- hot Bear: ~15% of Bear lifetime
- vol_climax_flag=True: ~0.5% population overall (sparse feature)

Tolerance bands:
- count: ±20% of point prediction
- WR: ±5pp of point prediction

If a rule's prediction is uncertain (e.g., new rule_018 wk4 Choppy DOWN),
widen the band (count: ±30%; WR: ±7pp).

---

## DELIVERABLE 5 — `integration_notes_path1.md`

Same as Step 3: 8-week deployment plan, schema migration, cutover
criteria.

In Path 1, additionally document:
- Why bucket threshold registry is required (path1_thresholds_explicit.md
  is the authoritative source — must be persisted in production)
- Why sub_regime_constraint is critical (Step 3 rule_007 failure case)
- Phase-5 override mechanism (B3) integration

---

## CONSTRAINTS (HARD — Path 1 specific)

- USE EXACT THRESHOLDS from `path1_thresholds_explicit.md`. Numeric
  comparisons preferred. Do not infer; do not substitute.
- ADDRESS EACH FAILURE in `path1_step3_failure_analysis.md`. Don't
  paper over.
- DON'T DROP COMPONENTS — restore wk4 as rule_018.
- ADD `sub_regime_constraint` for ALL sub-regime-gated rules.
- 24 RULES TOTAL (15 NEW + 9 EXISTING). Not 26 (Step 3). Not 22.
- LIFETIME-CALIBRATED expected_wr (NOT live small-sample inflated).
- VALIDATE before output: every condition references a Lab feature
  with documented thresholds.

---

## OUTPUT FORMAT

Same as Step 3: 5 fenced code blocks tagged with deliverable filenames.

```unified_rules_path1.json
{...}
```

```precedence_logic_path1.md
# ...
```

```b1_b2_coupling_path1.md
# ...
```

```validation_predictions_path1.json
{...}
```

```integration_notes_path1.md
# ...
```

The script will parse each by language tag and save to
`output/<deliverable>`.

---

## Closing reminder

Path 1 is the disciplined iteration. If you're tempted to add interpretive nuance, **don't** — Path 2 is doing that separately. Path 1 should produce rules that mechanically satisfy the documented Lab thresholds and address every Step 3 failure.

If your iteration produces fewer than 24 rules, fewer than 15 NEW rules, or any unexplained deviation, the iteration has failed Path 1's mandate. Re-emit.
