# Opus Rule Synthesis Prompt — Step 3

## Role

You are translating Lab investigation findings into production trading
rules for the TIE TIY Scanner (Indian NSE F&O equity scanner, daily
rhythm). The Lab has investigated 9 cells across 3 market regimes
(Bull/Bear/Choppy × UP_TRI/DOWN_TRI/BULL_PROXY) and produced lifetime-
validated playbooks with sub-regime gating.

## Input package (provided as separate documents)

You have access to these documents:

### Cell playbooks (9 files, in `playbooks/`)
- `bear_uptri.md` — HIGH-confidence sub-regime gated (hot/warm/cold)
- `bear_downtri.md` — DEFERRED + provisional Verdict A (kill_001 + wk2/wk3)
- `bear_bullproxy.md` — DEFERRED + provisional hot-only filter
- `bull_uptri.md` — PROVISIONAL_OFF, recovery/healthy/normal/late
- `bull_downtri.md` — PROVISIONAL_OFF, late_bull × wk3 (perfect inversion)
- `bull_bullproxy.md` — PROVISIONAL_OFF, healthy_bull × 20d=high
- `choppy_uptri.md` — CANDIDATE, breadth=medium × vol=High × MACD=bull
- `choppy_downtri.md` — CANDIDATE (upgraded from DEFERRED via L3 search)
- `choppy_bullproxy.md` — KILL (entire cell rejected)

### Regime synthesis docs (3 files, in `regime_synthesis/`)
- `bear.md` — Bear cross-cell + sub-regime axes (vol × 60d_return)
- `bull.md` — Bull cross-cell + sub-regime axes (200d_return × breadth)
- `choppy.md` — Choppy cross-cell + sub-regime axes (vol × breadth)

### Production posture docs (2 files, in `posture/`)
- `bear_posture.md` — Bear regime activation criteria
- `bull_posture.md` — Bull regime activation gates + 5 known gaps

### Critique resolutions (14 files, in `critiques/`)
- `bull_critiques_summary.md` — Step 1 (5 Bull critique resolutions)
- `S1`-`S5` — individual Bull critique investigations
- `critiques_audit_summary.md` — Step 1.5+2 SUMMARY (CRITICAL CONTEXT)
- `A1_rules_audit.md` — cross-cell rule consistency analysis
- `C1`-`C3` — Choppy critique resolutions
- `B1`-`B3` — Bear critique resolutions

### Existing production state (in `production/`)
- `current_rules.json` — `mini_scanner_rules.json` schema v3 with
  1 kill_pattern + 1 watch_pattern + 7 boost_patterns (all regime=Bear)
- `bull_verification.md` — Bull pipeline verification report

---

## YOUR TASK

Synthesize the Lab findings into 5 production deliverables. **Do not
skip any deliverable. Do not invent rules beyond what the playbooks
support. Do not invent features outside the existing scanner pipeline.**

---

## DELIVERABLE 1 — `unified_rules_v4.json`

Production rules in **2-tier schema** (designed in
`critiques/critiques_audit_summary.md` section H — read it carefully).

### Schema specification (v4)

```json
{
  "schema_version": 4,
  "generated_at": "ISO-8601",
  "description": "Step 3 Opus synthesis: 14 new rules + 9 existing rules harmonized",
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
        {"feature": "<feature_name>", "value": "<value>", "operator": "eq"|"in"|"gt"|"lt"|null}
      ],
      "verdict": "TAKE_FULL" | "TAKE_SMALL" | "WATCH" | "SKIP" | "REJECT",
      "expected_wr": 0.65,
      "confidence_tier": "HIGH" | "MEDIUM" | "LOW",
      "trade_mechanism": "mean_reversion" | "breakout_continuation" | "regime_transition" | "trend_fade" | "support_bounce_reversal" | "counter_trend",
      "regime_constraint": "Bear" | "Bull" | "Choppy" | "any",
      "sub_regime_constraint": "hot" | "boundary_hot" | "recovery_bull" | ... | null,
      "production_ready": true | false,
      "priority": "HIGH" | "MEDIUM" | "LOW",
      "source_playbook": "bear_uptri" | "bull_uptri" | ...,
      "source_finding": "Brief description of the Lab finding",
      "evidence": {
        "n": 1234,
        "wr": 0.65,
        "lift_pp": 7.5,
        "tier": "validated" | "preliminary" | "lifetime"
      }
    }
  ],
  "notes": {...}
}
```

### Rule generation requirements

**Total: 14 NEW rules + 9 EXISTING rules verified compatible = 23 rules**

The 14 new rules are explicitly priority-ranked in
`critiques/critiques_audit_summary.md` section B and the post-LLM
adjustments. Do NOT add more, do NOT add fewer.

#### HIGH priority (5 — must produce all 5)

1. **late_bull = SKIP for Bull UP_TRI/BULL_PROXY** — sub-regime gate;
   30pp swing (74% recovery_bull vs 45% late_bull)
2. **recovery_bull × vol=Med × fvg_low = TAKE_FULL for Bull UP_TRI** —
   74.1% lifetime, n=390
3. **healthy_bull × nifty_20d=high = TAKE_FULL for Bull BULL_PROXY** —
   62.5% lifetime, n=128
4. **vol_climax × BULL_PROXY = REJECT in Bear AND Bull-late_bull** —
   universal anti-pattern (-11pp Bear; -7.5pp late_bull)
5. **Bear UP_TRI × Health = AVOID** (32.4% in hot; hostile sector)

#### MEDIUM priority (5 — must produce all 5)

6. **Bear UP_TRI × December = SKIP** (-25pp catastrophic)
7. **Choppy UP_TRI × Feb = SKIP** (-16.2pp catastrophic; Indian Budget)
8. **Choppy BULL_PROXY = REJECT** (entire cell KILL verdict)
9. **Bear DOWN_TRI calendar filter** (wk2/wk3 only; +7.5pp lift)
10. **Bear UP_TRI cold cascade boost** (wk4 × swing_high=low; +13pp)

#### LOW priority (4 — produce with `production_ready: false`)

11. Bull UP_TRI × Energy = SKIP (-2.9pp)
12. Bull UP_TRI/PROXY × Sep = SKIP (-8.4pp)
13. Choppy DOWN_TRI: Pharma SKIP, Friday SKIP, wk4 small (-4.7/-6.2/-7.1pp)
14. Choppy UP_TRI × Metal = SKIP (-2.2pp)

#### Existing 9 rules — verify compatible

Re-emit existing rules (kill_001, watch_001, win_001 through win_007)
in v4 schema. Add `production_ready: true` and inherit `priority`
based on Lab evidence.

### Field generation rules

- **`source_playbook`**: cite the EXACT playbook filename (e.g.,
  `bull_uptri`)
- **`source_finding`**: 1-line description with the lift/WR data point
- **`evidence`**: pull n, wr, lift_pp from the playbook
- **`expected_wr`**: use the calibrated WR (NOT live observed; use
  lifetime baseline + sub-regime tier from B1)
- **`trade_mechanism`**: per cell, not per rule. Use:
  - Bear UP_TRI = `mean_reversion`
  - Bull UP_TRI = `breakout_continuation`
  - Choppy UP_TRI = `regime_transition`
  - Bear DOWN_TRI = `trend_fade`
  - Bull DOWN_TRI = `counter_trend`
  - Choppy DOWN_TRI = `regime_transition`
  - Bear BULL_PROXY = `support_bounce_reversal`
  - Bull BULL_PROXY = `support_bounce_reversal`
  - Choppy BULL_PROXY = (KILL — no mechanism)

### Schema compliance constraints

- All `match_fields` keys are exactly one of: `signal`, `sector`, `regime`
- All `conditions` array items are objects with `feature`, `value`,
  optionally `operator` (default `eq`)
- All `feature` names MUST exist in scanner data (`feat_*` prefix or
  signal-level fields like `regime`, `sector`)
- Use null for "any" matches (e.g., `"sector": null` matches all sectors)

---

## DELIVERABLE 2 — `precedence_logic.md`

Document the 4-layer rule evaluation order and conflict resolution.

### Required sections

1. **Layer 1 — KILL/REJECT (terminating)**
   - kill_pattern + REJECT-verdict rules fire first
   - First match wins; no further evaluation
   - Examples from generated rules

2. **Layer 2 — Sub-regime gate**
   - Sub-regime classification establishes baseline verdict eligibility
   - Hot/recovery_bull → TAKE eligible
   - Cold/late_bull → SKIP fallback
   - Boundary tier handling (per B1)

3. **Layer 3 — Sector / Calendar pessimistic merge**
   - Sector and calendar rules are NON-terminating
   - Pessimistic composition: `SKIP > TAKE_HALF > TAKE_FULL` (most conservative wins)
   - Boost rules CONFIRM but don't UPGRADE

4. **Layer 4 — Phase-5 override (upgrade-only)**
   - Wilson 95% lower bound > sub-regime base + 5pp triggers upgrade
   - VALIDATED tier only; recency check (90 days)
   - Upgrade-only: cannot downgrade verdict

5. **3 worked conflict examples** (from `critiques/critiques_audit_summary.md` section I)

---

## DELIVERABLE 3 — `b1_b2_coupling_analysis.md`

Per session brief, B1 (4-tier display) ships now; B2 (sigmoid) deferred
to Phase-2. Address explicitly:

1. **Production gap acknowledgment:** Without B2's continuous scoring,
   production still has cliff effect at sub-regime boundaries (vp=0.70,
   n60=-0.10).

2. **Trade-off:** B1's 4-tier labels uncertainty visibly to trader
   but verdicts remain binary at sub-regime boundaries. Counter:
   B2's sigmoid would smooth verdicts but requires features
   not yet in production.

3. **B1-only production behavior recommendation:**
   - Show 4 tiers in Telegram: confident_hot / boundary_hot / boundary_cold / confident_cold
   - Map to verdicts:
     - boundary_hot → TAKE_FULL (highest WR 71.5% — counterintuitive)
     - confident_hot → TAKE_FULL (60-65%)
     - boundary_cold → TAKE_SMALL (transitional 55-60%)
     - confident_cold → SKIP (apply cold cascade if available)
   - Document calibrated WR alongside live observed (per B3 framework)

4. **Phase-2 trigger:** When should B2 sigmoid be promoted from
   Phase-2 to production? (Recommend criteria, e.g., "after 6 months
   live operation showing verdict-tier mismatch frequency >X%").

---

## DELIVERABLE 4 — `validation_predictions.json`

For each rule generated in Deliverable 1, predict expected behavior
when applied to historical lifetime data (`enriched_signals.parquet`,
105,987 enriched signals).

### Format

```json
{
  "schema_version": 4,
  "predictions": [
    {
      "rule_id": "rule_001",
      "predicted_match_count": 2400,
      "predicted_match_count_min": 1920,
      "predicted_match_count_max": 2880,
      "predicted_match_wr": 0.65,
      "predicted_match_wr_min": 0.60,
      "predicted_match_wr_max": 0.70,
      "predicted_lift_vs_baseline": 0.075,
      "source_playbook": "bear_uptri",
      "source_evidence": "n=1,446 lifetime matches at 53.6% WR per Verdict A"
    }
  ]
}
```

### Tolerance bands

- `predicted_match_count_min` = 80% of point prediction
- `predicted_match_count_max` = 120% of point prediction
- `predicted_match_wr_min` = point - 5pp
- `predicted_match_wr_max` = point + 5pp

These tolerances come directly from the session brief's validation
criteria (±20% count, ±5pp WR).

### Coverage requirement

Every rule in Deliverable 1 must have a corresponding entry in
Deliverable 4. Use playbook evidence as point predictions.

---

## DELIVERABLE 5 — `integration_notes.md`

Production deployment plan for the v4 ruleset.

### Required sections

1. **Ship order**
   - Phase A (week 1): existing 9 rules continue; v4 schema published
   - Phase B (weeks 1-3): HIGH priority rules (5) deployed in parallel
     (v3 + v4 evaluator both run; discrepancies logged)
   - Phase C (weeks 3-5): MEDIUM priority rules (5) added
   - Phase D (months 2+): LOW priority rules (4) after live validation

2. **Sub-regime detector requirements**
   - Choppy 3-axis detector (vol × breadth × momentum) per C1
   - N=2 composite hysteresis per C3
   - Bull sub-regime detector (PRODUCTION_POSTURE Gap 2) — required
     for HIGH rules 1-3
   - Bear 4-tier classifier (B1) — required for sector mismatch refinement

3. **Phase-5 override mechanism**
   - Wilson lower bound calculation pre-cached
   - VALIDATED combo database at
     `lab/output/combinations_live_validated.parquet`
   - 90-day recency check
   - ~10ms lookup per signal

4. **Schema migration plan (v3 → v4)**
   - 2-week parallel evaluation window
   - Cutover criteria: discrepancy rate <5% AND WR delta <3pp
   - Rollback procedure if cutover fails

5. **Cutover criteria** (specific go/no-go gates)

6. **Open production gaps** that may block any of HIGH/MEDIUM rules
   (e.g., Bull rules 1-3 require sub-regime detector ship first)

---

## CONSTRAINTS (HARD)

- Rules MUST conform to v4 2-tier schema EXACTLY. Do not add new top-level fields.
- Rules MUST reference features that exist in the scanner data pipeline. Use the `feat_*` naming convention from `enriched_signals.parquet` (you'll see these used in playbooks).
- Rules MUST be derived from playbook findings. Cite source playbook + evidence per rule.
- Rules MUST handle 5 cell types (HIGH/MEDIUM/LOW filter, KILL/REJECT, DEFERRED/PROVISIONAL_OFF).
- Rules MUST be testable: validation predictions must be quantitative.
- DO NOT skip any of the 5 deliverables.
- DO NOT generate >14 new rules or <14 new rules. Priority ranking is final.
- DO NOT invent features that don't appear in playbooks.
- DO NOT contradict critique findings (e.g., do NOT reverse "boundary_hot beats confident_hot").
- DO NOT change schema design (2-tier was decided in Step 1.5+2).

## OUTPUT FORMAT

Produce 5 separate documents. Output each in a single fenced code block
with the deliverable filename as the language tag, in this order:

```unified_rules_v4.json
{...}
```

```precedence_logic.md
# Precedence Logic
...
```

```b1_b2_coupling_analysis.md
# B1+B2 Coupling Analysis
...
```

```validation_predictions.json
{...}
```

```integration_notes.md
# Integration Notes
...
```

The script will parse each fenced block by its language tag and save
to the corresponding file in `output/`.
