# Path 2 (TRUST-OPUS) — Opus Rule Synthesis Prompt — Step 4

## Role

You are iterating on the Step 3 Opus rule synthesis. Step 3 produced
26 rules with 38% PASS / 65% PASS+WARNING validation rate. Path 2 is
the **freedom-first iteration**: I'm giving you all the same Step 3
inputs, plus the Step 3 validation results and Sonnet 4.5's
critique, and asking you to iterate using your own judgment.

This is a methodology comparison study. Path 1 (a separate iteration)
prescribes specific fixes with hard-coded thresholds. Path 2 trusts
your interpretive synthesis. We will validate both empirically and
compare.

## Input package (provided as separate documents)

### Step 3 inputs (same as before)
- 9 cell playbooks (`playbooks/`)
- 3 regime synthesis docs (`regime_synthesis/`)
- 14 critique resolution files (`critiques/`)
- 2 PRODUCTION_POSTURE docs (`posture/`)
- Existing production rules (`production/current_rules.json`)
- Bull verification report (`production/bull_verification.md`)

### NEW for Path 2 — Step 3 validation feedback
- `step3_validation_report.json` — Step 3 actual vs predicted per rule
  (10 PASS / 7 WARNING / 9 FAIL)
- `step3_sonnet_critique.md` — Sonnet 4.5's analysis of Step 3 failures
  with categorization (bucket mismatch / missing sub_regime constraint /
  prediction overstatement / sparse features / dropped components)

---

## YOUR TASK (Path 2 Trust-Opus)

Re-synthesize the Lab findings into the same 5 production deliverables
as Step 3. **Use your judgment to address the validation failures.**

You have full freedom to:
- Interpret playbook findings as you see fit
- Choose appropriate thresholds (you may use playbook-implied or
  your own judgment from raw data)
- Decide rule fragmentation strategy (split vs combine)
- Adjust predictions based on your reading of evidence
- Fix or ignore the Step 3 failures however seems most appropriate

The mandate is **produce better rules than Step 3, using your
synthesis judgment**. There are no hard-coded threshold mandates;
no per-rule fix instructions; no fragmentation rules. Just: read
the playbooks + critiques + Step 3 results, and iterate.

### What we're measuring (Path 2 vs Path 1)

After both paths run, validation harness applies both rule sets to
historical data. We compare:
- PASS rates
- Coverage (do all cell verdicts have representation?)
- Schema compliance
- Per-rule quality

If Path 2 outperforms Path 1, the lesson is "Opus is better with
freedom than constraints." If Path 1 wins, the lesson is "explicit
constraints help Opus." Either outcome teaches us how to prompt
Opus for future synthesis tasks.

---

## DELIVERABLES (5 — same structure as Step 3)

### `unified_rules_path2.json`

Production rules in v4 schema (2-tier: match_fields + conditions
array). Same schema as Step 3.

### `precedence_logic_path2.md`

4-layer rule evaluation order (KILL > sub-regime > sector/calendar >
override) with conflict examples.

### `b1_b2_coupling_path2.md`

B1 4-tier display ships now; B2 sigmoid deferred. Mapping spec.

### `validation_predictions_path2.json`

Per-rule quantitative predictions (count + WR + tolerance bands).

### `integration_notes_path2.md`

Production deployment plan.

---

## SCHEMA REMINDER

```json
{
  "schema_version": 4,
  "rules": [
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
      "trade_mechanism": "mean_reversion" | "breakout_continuation" | ...,
      "regime_constraint": "Bear" | "Bull" | "Choppy" | "any",
      "sub_regime_constraint": "hot" | "boundary_hot" | "recovery_bull" | ... | null,
      "production_ready": true | false,
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "source_playbook": "...",
      "source_finding": "...",
      "evidence": {"n": 0, "wr": 0.0, "lift_pp": 0.0, "tier": "..."}
    }
  ]
}
```

---

## CONSTRAINTS (LIGHT — Path 2 has freedom but boundaries)

- Schema MUST be v4 2-tier (match_fields + conditions array)
- Features MUST exist in scanner pipeline (use `feat_*` names from
  enriched_signals.parquet — see playbooks for examples)
- DO NOT contradict critique findings (e.g., "boundary_hot beats
  confident_hot" must not be reversed)
- DO produce all 5 deliverables (skipping = failure)
- DO produce predictions for every rule (1:1 coverage)
- DO cite source_playbook per rule

You have freedom on:
- Number of rules (any count is acceptable; balance coverage vs noise)
- Threshold choice (use any reasonable interpretation of playbooks)
- Rule fragmentation strategy
- Confidence tier assignment
- Production_ready field assignment
- Predictions methodology

---

## Step 3 failure context (for your judgment, not prescriptive)

Step 3 produced 9 FAIL rules. Sonnet 4.5 categorized them:
- 5 had bucket threshold mismatch (predictions used different thresholds than validation harness)
- 1 (rule_007 Health × Bear UP_TRI) was missing sub_regime_constraint
- 2 had prediction overstatement (live small-sample inflated)
- 1 was a dropped component (Choppy DOWN wk4)
- rule_005 + rule_006 were sparse-feature edge cases

How you address these is your choice. Possibilities:
- Use feature library threshold conventions (look at playbook syntax)
- Use sub-regime detector axes when relevant
- Calibrate predictions from playbook lifetime data
- Restore dropped components as needed
- Tighten or loosen sub-regime gates as you see fit

---

## OUTPUT FORMAT

Same as Step 3: 5 fenced code blocks tagged with deliverable filenames.

```unified_rules_path2.json
{...}
```

```precedence_logic_path2.md
# ...
```

```b1_b2_coupling_path2.md
# ...
```

```validation_predictions_path2.json
{...}
```

```integration_notes_path2.md
# ...
```

---

## Closing note

Path 2 is the freedom-first iteration. Use your judgment. The point of
this comparison is to learn whether Opus does better with explicit
constraints (Path 1) or with interpretive freedom (Path 2). Don't
mimic Path 1; produce your own synthesis.

Step 3 and the validation results give you context on what worked
and what didn't. Build on that intelligently.
