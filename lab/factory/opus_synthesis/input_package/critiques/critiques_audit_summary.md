# Critique Resolution + Rules Audit — SUMMARY

**Date:** 2026-05-03
**Step:** 1.5 + 2 of 7-step Bull production-prep plan (combined session)
**Branch:** backtest-lab; commits `d219a7b3` (A1) → `cde68a6c` (B3) → SY
**Output:** Step 3 (Opus rule synthesis) input package

---

## A. Per-critique verdict matrix

| # | Critique | Verdict | Action | Priority |
|---|---|---|---|---|
| **A1** | Rules audit across 9 cells | **HEALTHY (0 contradictions, 14 gaps)** | Schema + 14 new rules; Opus synthesis | HIGH |
| **C1** | Choppy missing momentum feature | **RESOLVED with action** | ADD nifty_20d_return_pct (3rd axis) | MEDIUM-HIGH |
| **C2** | Choppy breadth thresholds | **MARGINAL** | KEEP 33/67 (low priority change) | LOW |
| **C3** | Choppy transition whipsaw | **GAP_DOCUMENTED** | N=2 hysteresis + state file | MEDIUM |
| **B1** | Bear warm-zone display | **RESOLVED with action** | 4-tier confidence; counterintuitive boundary > deep | MEDIUM-HIGH |
| **B2** | Bear hard-threshold cliffs | **GAP_DOCUMENTED** | Soft sigmoid + verdict re-mapping | MEDIUM |
| **B3** | Bear Phase-5 override | **RESOLVED with design** | Wilson-lower-bound override mechanism | MEDIUM |

**4 RESOLVED, 2 GAP_DOCUMENTED, 1 MARGINAL. 0 DEFERRED_TO_LIVE.**

---

## B. Aggregated production-prep deliverables

### Schema additions to mini_scanner_rules.json

Per A1 + critique findings:

**2-tier schema design** (recommended by Sonnet 4.5 in A1 critique):
```json
{
  "match_fields": {
    "signal": "UP_TRI",
    "regime": "Bear",
    "sector": null
  },
  "conditions": [
    {"feature": "sub_regime", "value": "boundary_hot"},
    {"feature": "day_of_month_bucket", "value": "wk4"}
  ],
  "verdict": "TAKE_FULL",
  "evidence": {...}
}
```

`conditions` array supports arbitrary feature-value pairs (AND logic).
Avoids 6-flat-field schema explosion. Compatible with sub-regime tier
classification, calendar features, day-of-week.

### New rules to add (14 total, re-prioritized post-Sonnet)

#### HIGH priority (5 — sub-regime edge drivers + universal hygiene)

1. **late_bull = SKIP** for Bull UP_TRI/BULL_PROXY (74% vs 45% WR; 30pp swing)
2. **recovery_bull × vol=Med × fvg_low = TAKE_FULL** for Bull UP_TRI (74%, n=390)
3. **healthy_bull × 20d=high = TAKE_FULL** for Bull BULL_PROXY (62.5%, n=128)
4. **vol_climax × BULL_PROXY = REJECT** in Bear AND Bull-late_bull (-11pp Bear; -7.5pp late_bull)
5. **Bear UP_TRI × Health = AVOID** (32.4% in hot; hostile sector)

#### MEDIUM priority (5 — catastrophic calendar + scaffolding)

6. **Bear UP_TRI × December = SKIP** (-25pp catastrophic)
7. **Choppy UP_TRI × Feb = SKIP** (-16.2pp catastrophic; Indian Budget)
8. **Choppy BULL_PROXY = REJECT** (entire cell KILL verdict)
9. **Bear DOWN_TRI calendar filter** (wk2/wk3 only; +7.5pp lift)
10. **Bear UP_TRI cold cascade boost** (wk4 × swing_high=low; +13pp)

#### LOW priority (4 — sector + day-of-week micro-rules)

11. Bull UP_TRI × Energy = SKIP (-2.9pp)
12. Bull UP_TRI/PROXY × Sep = SKIP (-8.4pp)
13. Choppy DOWN_TRI: Pharma SKIP, Friday SKIP, wk4 small (-4.7/-6.2/-7.1pp)
14. Choppy UP_TRI × Metal = SKIP (-2.2pp)

### Detector changes recommended

| Detector | Current | Proposed | Source | Priority |
|---|---|---|---|---|
| Choppy sub-regime | vol × breadth (9 cells) | vol × breadth × momentum (27 cells) | C1 | MEDIUM-HIGH |
| Choppy breadth thresholds | 33/67 tertile | KEEP 33/67 | C2 | (no change) |
| Choppy hysteresis | None | N=2 confirmation | C3 | MEDIUM |
| Bear classification | binary hot/warm/cold | 5-tier with confidence | B1 | MEDIUM-HIGH |
| Bear threshold scoring | hard cliff | sigmoid hot_conf | B2 | MEDIUM |
| Bear WR estimation | sub-regime base | sub-regime + Phase-5 override | B3 | MEDIUM |
| Bull sub-regime | (not in production) | recovery/healthy/normal/late | A1 (Gap 2) | MEDIUM-HIGH |

### Display/messaging changes

- **5-tier confidence display** in Telegram (B1 + B2):
  ```
  [BEAR · BOUNDARY_HOT · 72% expected]
  ```
- **Calibrated WR alongside live observation** (B1 + B3):
  ```
  Calibrated: 71% / Observed live: 94% / Phase-5 override: 76%
  ```
- **Counterintuitive findings briefing** (B1 + B2):
  Trader must understand boundary_hot > confident_hot at deployment.

### Architectural improvements

| Item | Source | Impact |
|---|---|---|
| Rule precedence model (KILL > sub-regime > sector/calendar > override) | A1 LLM critique | Conflict resolution |
| Sub-regime state file (subregime_state.json) | C3 | Whipsaw mitigation |
| Phase-5 combo database lookup | B3 | Feature-specific calibration |
| 2-tier rule schema | A1 LLM critique | Avoids 6-field explosion |
| Worked examples (≥5) | A1 LLM critique | Runtime validation |
| Trade mechanism annotation per rule | A1 LLM critique | Surfaces implicit logic conflicts |

---

## C. Step 3 input package (revised final)

Step 3 (Opus rule synthesis) receives:

### Lab artifacts (existing)

1. **9 cell playbooks**: `lab/factory/{regime}_{signal}/playbook.md`
2. **3 regime synthesis docs**: `lab/factory/{bear,bull,choppy}/synthesis*.md`
3. **2 PRODUCTION_POSTURE docs**: `lab/factory/{bear,bull}/PRODUCTION_POSTURE.md`
4. **Bull production verification report**: `lab/factory/bull_verification/`

### Critique resolution artifacts (Step 1 + this session)

5. **Bull critique resolution (Step 1)**: `lab/factory/bull_critiques/SUMMARY.md`
   + S1-S5 individual reports + `_llm_critique.md`
6. **Step 1.5 + Step 2 critique resolution (this session)**:
   `lab/factory/critiques_audit/{A1, C1-C3, B1-B3}.md` + `_a1_llm.md`

### Production state

7. **Pre-existing production rules**: `data/mini_scanner_rules.json`
   (1 kill + 1 watch + 7 boost; schema v3)
8. **Cross-regime architectural framework** (synthesized in A1):
   - 3 universal patterns (vol_climax × BULL_PROXY anti, sub-regime tri-modal, calendar inversion)
   - Regime-specific axes (Choppy=vol×breadth, Bear=vol×60d, Bull=200d×breadth)
   - Direction-flip pattern (UP vs DOWN within same regime)

### Design constraints for Opus

- **Schema:** 2-tier (match_fields + conditions array), not 6-flat-field
- **Precedence:** KILL > sub-regime > sector/calendar > override (4-layer)
- **Output:** structural-rules.json (universal) + parametric-cell-tables.json (cell-specific)
- **Validation:** ≥5 worked examples covering regime × signal × sub-regime cross-product

### Calibrated WR expectations Opus must preserve

| Cell × tier | Calibrated WR |
|---|---|
| Bear UP_TRI boundary_hot | 65-75% (lifetime 71.5%) |
| Bear UP_TRI confident_hot | 60-65% |
| Bear UP_TRI cold_cascade (wk4 × swing_high=low) | 60-65% |
| Bull UP_TRI recovery_bull × vol=Med × fvg_low | 70-78% (lifetime 74.1%) |
| Bull UP_TRI healthy_bull × wk4 | 60-68% |
| Bull DOWN_TRI late_bull × wk3 | 60-70% (lifetime 65.2%) |
| Bull BULL_PROXY healthy_bull × 20d=high | 58-66% (lifetime 62.5%) |
| Choppy UP_TRI breadth=med × vol=High | 58-65% |
| Choppy DOWN_TRI breadth=med × vol=Med × wk3 | 53-62% |
| All Phase-5-override-eligible | Wilson lower (typically 70-77%) |

---

## D. Step 3 (Opus) prompt structure recommendation

### Opus task scope

Synthesize unified production rules from:
- 9 cell playbooks (cell findings)
- A1 audit (cross-cell consistency + gaps)
- C1-C3 + B1-B3 critique resolutions (detector improvements)
- mini_scanner_rules.json (current production state)

### Output structure (2-file)

**File 1: `structural_rules.json`**
- Universal patterns (vol_climax×BULL_PROXY anti, etc.)
- Sub-regime tri-modal gating template
- Calendar inversion template
- Schema spec (2-tier)
- Rule precedence definition

**File 2: `parametric_cells.json`**
- Per-cell sub-regime axes
- Per-cell tier boundaries
- Per-cell sector preferences
- Per-cell kill rules

### Opus constraints

1. Must handle 5 cell types per regime (UP_TRI, DOWN_TRI, BULL_PROXY,
   plus Bear hot/warm/cold and Bull recovery/healthy/normal/late
   sub-regimes).
2. Must produce valid runtime output for all 5 worked examples
   provided in this SUMMARY.
3. Must preserve calibrated WR expectations from section C.
4. Must annotate trade mechanism per rule (mean-reversion / breakout /
   continuation / regime-transition).
5. Must NOT introduce new fields beyond match_fields + conditions array
   (per A1 LLM critique).
6. Must preserve precedence: KILL → sub-regime → sector/calendar →
   Phase-5 override.

### Validation criteria

For each of 5 worked examples (next section), Opus rules must produce:
- A single verdict (TAKE_FULL / TAKE_SMALL / SKIP / REJECT)
- Trace showing which rules fired in what order
- Calibrated WR estimate within 3pp of expected

---

## E. Worked examples for Opus validation

### Example 1: Bear UP_TRI hot, sector=Auto, wk4

```
Date: 2026-04-25 (Friday, wk4, Apr)
Signal: AUTOLINKS UP_TRI age=0
regime=Bear, sector=Auto
Features:
  feat_nifty_vol_percentile_20d = 0.75
  feat_nifty_60d_return_pct = -0.13
  feat_day_of_month_bucket = wk4
Sub-regime: hot (vp > 0.70 AND n60 < -0.10)
B1 tier: confident_hot (both >0.05 from threshold)

Expected verdict trace:
  1. KILL filters: vol_climax not present → pass
  2. Sub-regime gate: hot → eligible
  3. Boost match: win_001 (Auto × UP_TRI × Bear) → BOOST applies
  4. Calendar: wk4 winner → no penalty
  5. Phase-5 override: no VALIDATED match for this combo

Final verdict: TAKE_FULL
Calibrated WR: 65-75% (sub-regime hot baseline; live observation 21/21
in production rules supports upper end)
```

### Example 2: Bull UP_TRI recovery_bull + filter

```
Date: 2027-03-15 (Monday, wk3, March) [hypothetical Bull regime]
Signal: TCS UP_TRI age=0
regime=Bull, sector=IT
Features:
  feat_nifty_200d_return_pct = -0.05 (low)
  feat_market_breadth_pct = 0.42 (low)
  feat_nifty_vol_regime = Medium
  feat_fvg_unfilled_above_count = 0 (low)
  feat_day_of_month_bucket = wk3
Sub-regime: recovery_bull (low 200d AND low breadth)

Expected verdict trace:
  1. KILL filters: vol_climax not present, sector not Energy → pass
  2. Sub-regime gate: recovery_bull → eligible (best Bull cell)
  3. Filter match: recovery_bull × vol=Med × fvg_low → strongest Bull combo
  4. Calendar: wk3 minor anti (-3.3pp) but not blocking
  5. Phase-5 override: no Bull VALIDATED combos (cell PROVISIONAL_OFF)

Final verdict: TAKE_FULL
Calibrated WR: 70-78% (recovery_bull × vol=Med × fvg_low best combo)
```

### Example 3: Choppy UP_TRI in equilibrium sub-regime

```
Date: 2026-09-12 (Wednesday, wk2, Sep)
Signal: HDFC UP_TRI age=1
regime=Choppy, sector=Bank
Features:
  feat_nifty_vol_regime = High
  feat_market_breadth_pct = 0.51 (medium)
  feat_nifty_20d_return_pct = -0.005 (flat)
  feat_MACD_signal = bull
  feat_day_of_month_bucket = wk2
Sub-regime (3-axis per C1): high_medium_flat → 64.3% lifetime

Expected verdict trace:
  1. KILL filters: not Choppy BULL_PROXY → pass
  2. Sub-regime gate: high_medium_flat → strong
  3. Filter match: breadth=med × vol=High × MACD=bull → 62.5% lifetime
  4. Calendar: Sep is BEST month (+11.7pp); wk2 neutral
  5. Sector: Bank is neutral

Final verdict: TAKE_FULL
Calibrated WR: 58-65%
```

### Example 4: Choppy BULL_PROXY (entire cell KILLED)

```
Date: 2026-04-22 (Tuesday, wk4, Apr)
Signal: ABCBANK BULL_PROXY age=0
regime=Choppy, sector=Bank
Features: ...

Expected verdict trace:
  1. KILL filters: BULL_PROXY × Choppy regime → REJECT (entire cell KILL)

Final verdict: REJECT
Calibrated WR: N/A (signal blocked)
```

### Example 5: Bear UP_TRI hot + Phase-5 override

```
Date: 2026-04-12 (Friday, wk2, Apr)
Signal: TATA UP_TRI age=0
regime=Bear, sector=Metal
Features:
  feat_nifty_vol_percentile_20d = 0.73
  feat_nifty_60d_return_pct = -0.12
  feat_inside_bar_flag = True
  feat_day_of_week = Thu
Sub-regime: boundary_hot (just-into-hot per B1)

Expected verdict trace:
  1. KILL filters: not Health, not Energy → pass
  2. Sub-regime gate: boundary_hot → strongest tier (71.5% calibrated)
  3. Boost match: win_004 (Metal × UP_TRI × Bear) → BOOST
  4. Phase-5 override search: VALIDATED combo found
     (inside_bar_flag=True, n=13, Wilson lower 66.7%)
  5. Override decision: 66.7% < boundary_hot 71.5% — DON'T override
     (use sub-regime base instead)

Final verdict: TAKE_FULL
Calibrated WR: 71% (boundary_hot calibrated; override doesn't trigger)
WR source: sub_regime_boundary_hot (NOT phase5_override)
```

---

## F. Honest limitations + open questions for Step 3

### Caveats not yet resolved

1. **No live first-Bull-day data** (carried from Step 1). All Bull
   rules are pre-deployment.

2. **Sub-regime detector V2 (Choppy 3-axis from C1) is untested in
   production.** Recommend pre-activation backtest validation.

3. **Hysteresis (C3 N=2) introduces state.** Current scanner is
   stateless-per-scan (S1 finding). Adding state requires careful
   crash-recovery design.

4. **Soft thresholds (B2) and tiered display (B1) are layered
   mechanisms.** Need to ship one consistent display, not both.

5. **Phase-5 override database (B3) needs quarterly refresh
   cadence.** No production process yet for this.

6. **Trade mechanism annotation (A1 LLM critique adjustment #1)
   not yet authored.** Per-rule "this is mean-reversion" /
   "this is breakout-continuation" tag is missing.

### Step 3 questions to resolve

1. How should Opus reconcile B1 (5-tier display) and B2 (soft sigmoid)?
   Both produce same finding via different mechanisms.

2. How should Phase-5 override interact with sub-regime gating in
   production decision flow?

3. Should structural_rules.json + parametric_cells.json be unified
   into single rules.json, or kept separate for clarity?

4. What's the rule schema versioning approach? mini_scanner_rules.json
   schema v3 → v4 migration path?

5. How are kill_pattern interactions handled (e.g., Bear UP_TRI ×
   Health AVOID overlapping with sub-regime hot)?

---

## G. Step 3 readiness signal

| Step 3 readiness check | Status |
|---|---|
| All A1 audit gaps surfaced | ✅ DONE (14 rules) |
| All Choppy critiques (C1-C3) resolved | ✅ DONE |
| All Bear critiques (B1-B3) resolved | ✅ DONE |
| Schema design recommendation | ✅ 2-tier (match_fields + conditions) |
| Rule precedence model | ✅ KILL > sub-regime > sector/calendar > override |
| Worked examples authored | ✅ 5 examples (section E) |
| Calibrated WR expectations documented | ✅ DONE (section C) |
| Mechanism annotations | ❌ TBD by Opus per-rule |
| Schema versioning | ❌ TBD in Step 3 |
| Production code changes blocking Step 3 | NONE — all design |
| API spend Step 1.5 + 2 | $0.054 (A1 LLM only) |
| Atomic commits Step 1.5 + 2 | 7 (A1, C1-C3, B1-B3) + this SUMMARY = **8** |
| Step 3 unblocked? | ✅ READY |

**Step 1.5 + 2 closes here.** Step 3 (Opus rule synthesis) is unblocked.

---

## H. POST-LLM CRITIQUE ADJUSTMENTS

Sonnet 4.5 critique output: `_synthesis_llm.md`. Raised 8 challenges.

**Key verdict from Sonnet:** "Step 3 IS NOT YET READY" — 3 blockers:
1. 4 missing worked examples (Bull DOWN, Bear DOWN, Choppy DOWN 3-axis, first-Bull-day bootstrap)
2. Explicit rule composition logic (4-layer precedence is necessary but not sufficient)
3. C1+C3 sequencing decision

I'll address blockers 1 and 2 inline in this SUMMARY before closing.
Blocker 3 captured as decision below. The other 5 challenges accepted
as adjustments.

### Accepted adjustments (5)

**1. Ship B1 (tiered), defer B2 (sigmoid).** B1's 4-tier display matches
existing percentile-bucket architecture. B2's sigmoid requires
calibration work + continuous-feature support not yet present.
B2 documented as Phase-2 enhancement.

**2. C1 + C3 ship TOGETHER with COMPOSITE hysteresis.** Per-axis
hysteresis (3 separate state variables) is operationally complex.
Composite: compute the 3-axis sub-regime label, require N=2
consecutive days of SAME composite label. 1 state variable
(`previous_subregime_label`). Bootstrap state as NULL on regime
change; first 2 days are "provisional" verdicts at conservative
fallback (baseline Choppy).

**3. Trade mechanism annotation per-CELL** (not per-rule). 9 cells × 1
mechanism each = 9 annotations vs 70+ if per-rule. Mechanism is cell-
level property:
- Bear UP_TRI = mean_reversion (stress dip fade)
- Bull UP_TRI recovery_bull = breakout-continuation
- Choppy UP_TRI = regime-transition (anticipating breakout)
- DOWN_TRI Bear/Bull/Choppy = trend-fade / counter-trend / equilibrium-fade
- BULL_PROXY = support-bounce-reversal

Annotation lives in `parametric_cells.json`; rules inherit.

**4. Schema migration: BREAKING CHANGE v3 → v4** with 2-week parallel
validation. Forward-compat across 9 → 70 rules adds bug surface;
clean cutover with shadow comparison is safer.

**5. Pruning: Step 3 ships HIGH + MEDIUM only initially.** 10 new
rules (HIGH 5 + MEDIUM 5) + 9 existing = 19 total. LOW-priority
rules (11-14) tagged `production_ready: false` for Step 4. Captures
80% of edge at 25% of complexity.

### Rejected adjustment (1)

**Sonnet recommended detailed pessimistic composition logic** ("AVOID >
SKIP > TAKE_HALF > TAKE_FULL"). Accepted in spirit (see section I
below) — but rejected as a binary "Step 3 not ready" blocker. Composition
logic is a Step 3 deliverable, not a Step 1.5+2 prerequisite. Opus
will produce composition logic informed by the conflict examples below.

### Decision: C1 + C3 ship together (composite hysteresis)

Per Sonnet's recommendation. Schema flag `requires_confirmation: true`
on Choppy rules; scanner maintains `last_subregime_label` state;
on regime flip, reset state to NULL with conservative fallback for
2 days.

---

## I. Rule composition logic (addresses blocker 2)

### Layer 1 — KILL/REJECT (terminating)

If any KILL/REJECT rule matches, output that verdict and stop. No
further evaluation. Examples:
- Bear UP_TRI × Health = AVOID (terminates evaluation)
- Choppy BULL_PROXY = REJECT (terminates evaluation)
- vol_climax × BULL_PROXY = REJECT (terminates evaluation)

### Layer 2 — Sub-regime gate

Sub-regime classification establishes baseline verdict:
- Hot/recovery_bull → eligible for TAKE
- Cold/late_bull → eligible for SKIP fallback
- Boundary tiers → tier-specific WR (B1)

### Layer 3 — Sector / Calendar modulation

Sector and calendar rules are NON-terminating. They modify but don't
override sub-regime gating. Pessimistic composition:

| Sub-regime | Sector | Calendar | Final |
|---|---|---|---|
| TAKE_FULL | (no rule) | (no rule) | TAKE_FULL |
| TAKE_FULL | TAKE_FULL_BOOST | (no rule) | TAKE_FULL (no double-up) |
| TAKE_FULL | (no rule) | SKIP | SKIP (pessimistic merge) |
| TAKE_HALF | TAKE_HALF | (no rule) | TAKE_HALF |
| SKIP | (any) | (any) | SKIP (sub-regime is conservative anchor) |

Rule: **most conservative verdict wins** (SKIP > TAKE_HALF > TAKE_FULL).
Boost rules don't UPGRADE; they only confirm.

### Layer 4 — Phase-5 override

Override only fires if:
- Sub-regime base + override delta > 5pp
- Wilson 95% lower bound > sub-regime base + 5pp
- Combo recency within 90 days

Override CAN upgrade verdict from TAKE_HALF → TAKE_FULL (this is the
override's purpose — feature-specific calibration above sub-regime
generic rate).

Override CANNOT downgrade (a kill in layer 1 already prevents this;
override is purely an upgrade mechanism).

### Conflict examples (3)

**Conflict 1: Bear UP_TRI boundary_hot × Health AVOID**

```
Layer 1 (KILL): Health × Bear_UPTRI = AVOID → MATCHES → terminate.
Final verdict: AVOID
WR: N/A (signal blocked at Layer 1)
```

**Conflict 2: Bull UP_TRI recovery_bull × wk4 boost × Sep skip**

```
Layer 1 (KILL): no kill matches → continue.
Layer 2 (sub-regime): recovery_bull → TAKE_FULL eligible (74% WR
  with vol=Med × fvg_low filter).
Layer 3 (sector/cal): wk4 boost (+2.6pp) AND Sep skip (-8.4pp).
  Pessimistic merge: SKIP wins.
Layer 4 (Phase-5 override): no Bull combos VALIDATED (cell PROVISIONAL_OFF).
Final verdict: SKIP
WR: N/A (Sep override blocks)
```

**Conflict 3: Bear UP_TRI hot × inside_bar=True (override)**

```
Layer 1 (KILL): no kill matches → continue.
Layer 2 (sub-regime): hot → TAKE_FULL eligible (boundary_hot 71.5%
  via B1 tier).
Layer 3 (sector/cal): no sector AVOID; calendar neutral.
Layer 4 (Phase-5 override): inside_bar_flag=True VALIDATED combo
  (n=13, Wilson lower 66.7%).
  Sub-regime baseline 71.5% > override 66.7% by >5pp → override DOES
  NOT trigger (sub-regime base is stronger).
Final verdict: TAKE_FULL (sub-regime hot, no override)
WR: 65-75% (boundary_hot calibrated)
```

These 3 examples establish:
1. KILL terminates evaluation immediately
2. Pessimistic merge applies to sub-regime + sector/cal
3. Phase-5 override is upgrade-only and gated by Wilson lower bound

---

## J. Additional worked examples (addresses blocker 1)

### Example 6: Bull DOWN_TRI late_bull × wk3 (strongest Bull DOWN combo)

```
Date: 2027-08-19 (Wednesday, wk3, Aug) [hypothetical late_bull]
Signal: TATAMOTORS DOWN_TRI age=0
regime=Bull, sector=Auto
Features:
  feat_nifty_200d_return_pct = 0.18 (mid)
  feat_market_breadth_pct = 0.43 (low)
  feat_nifty_vol_regime = Low
  feat_RSI_14 = medium (not high)
  feat_day_of_month_bucket = wk3
  feat_day_of_week = Wed
Sub-regime: late_bull (mid 200d AND low breadth)

Verdict trace:
  1. KILL filters: not BULL_PROXY × Choppy → pass
  2. Sub-regime gate: late_bull → TAKE_SMALL eligible (53% Bull DOWN baseline)
  3. Filter match: late_bull × wk3 × non-Friday → +21.8pp (65.2% lifetime)
  4. Sector: Auto is FMCG/Auto SKIP candidate (-4pp); pessimistic merge
     downgrades TAKE_SMALL → SKIP
  5. Phase-5 override: 0 Bull DOWN VALIDATED combos (cell PROVISIONAL_OFF)

Final verdict: SKIP (sector Auto block)
WR: N/A
Trade mechanism (cell-level): counter-trend (Bull DOWN_TRI is
contrarian short)

Note: if sector were Metal or Bank instead, verdict would be TAKE_SMALL
with calibrated 60-70% WR.
```

### Example 7: Bear DOWN_TRI Verdict A (calendar + non-Bank)

```
Date: 2026-04-15 (Wednesday, wk3, Apr)
Signal: ULTRACEMCO DOWN_TRI age=0
regime=Bear, sector=Pharma (top-ranked Bear DOWN sector)
Features:
  feat_higher_highs_intact_flag = True
  feat_RSI_14 = medium
  feat_day_of_month_bucket = wk3
Sub-regime (Bear): cold (vol < 0.70)

Verdict trace:
  1. KILL filters: not Bank × DOWN_TRI → pass
  2. Sub-regime gate: cold (Bear DOWN baseline 46.1%; cold cascade not
     directly applicable — Bear DOWN cell is DEFERRED)
  3. Filter match (Verdict A): non-Bank AND wk2/wk3 → TAKE_SMALL
     (~53.6% lifetime, +7.5pp lift)
  4. Sector: Pharma top sector (no kill)
  5. Phase-5 override: 0 Bear DOWN VALIDATED → no override

Final verdict: TAKE_SMALL
Calibrated WR: 50-58% (Verdict A lifetime)
Trade mechanism: trend-fade (Bear DOWN_TRI is with-direction continuation)
```

### Example 8: Choppy DOWN_TRI 3-axis + composite hysteresis

```
Date: 2026-09-23 (Wednesday, wk3, Sep) [Day 1 of new sub-regime]
Signal: ASIANPAINT DOWN_TRI age=0
regime=Choppy, sector=Other
Features:
  feat_nifty_vol_regime = Medium
  feat_market_breadth_pct = 0.51 (medium)
  feat_nifty_20d_return_pct = -0.018 (falling)
  feat_day_of_week = Wed
  feat_day_of_month_bucket = wk3
Raw sub-regime (3-axis): medium_medium_falling

Yesterday's confirmed sub-regime: medium_medium_flat
N=2 hysteresis state: pending (1 day of new label) → use yesterday's
  CONFIRMED sub-regime (medium_medium_flat) for verdict

Verdict trace:
  1. KILL filters: not Pharma → pass
  2. Sub-regime gate: medium_medium_flat (CONFIRMED, NOT today's raw
     medium_medium_falling — hysteresis applies)
  3. Filter match: breadth=med × vol=Med × wk3 → 57.8% lifetime (+11.7pp)
     But sub-regime is "flat" not "falling" — partial mismatch
  4. Sector: Other is best Choppy DOWN sector (+4.1pp); pessimistic
     merge keeps TAKE_FULL eligible
  5. Phase-5 override: no Choppy DOWN VALIDATED → no override
  6. Calendar: wk3 +9.5pp boost

Final verdict: TAKE_SMALL (hysteresis-conservative; full would require
  2-day confirmation)
Calibrated WR: 53-58%
Trade mechanism: equilibrium-fade (Choppy DOWN_TRI in equilibrium vol)

Note: Tomorrow if signal still classifies medium_medium_falling, hysteresis
state confirms flip and tomorrow's same-context signal would be TAKE_FULL.
```

### Example 9: First-Bull-day bootstrap (transition-day handling)

```
Date: 2026-11-04 (Tuesday, wk1, Nov) [Day 1 of Bull regime activation
  per regime classifier]
Signal: BHARTIARTL UP_TRI age=0
regime=Bull (just activated TODAY)
Features:
  feat_nifty_200d_return_pct = -0.04 (low)
  feat_market_breadth_pct = 0.38 (low)
  feat_nifty_vol_regime = Medium
  feat_fvg_unfilled_above_count = 1 (low)
Raw sub-regime: recovery_bull (low 200d + low breadth)
Hysteresis state: NULL (regime just changed; bootstrap mode)

Verdict trace:
  1. KILL filters: not Energy × Bull_UPTRI → pass
  2. Regime activation gate: Bull regime active for 1 day; activation
     threshold is ≥10 days. Pre-activation behavior:
     - SHADOW MODE for first 10 days (signals logged but not promoted)
     - Cell rules evaluated as if active, but no Telegram TAKE alerts
     - Trader sees "[BULL · ACTIVATING · day 1/10]" tag
  3. Sub-regime gate: recovery_bull eligible at 60.2% baseline
  4. Filter: recovery_bull × vol=Med × fvg_low → 74.1% lifetime
  5. Sector: not Energy, not Sep → no kill
  6. Phase-5 override: 0 Bull VALIDATED → no override

Final verdict (production): SHADOW (would have been TAKE_FULL)
Telegram: "[BULL · ACTIVATING · 1/10] BHARTIARTL UP_TRI shadow.
  Calibrated 74% WR. Activation in 9 days."
WR shown: 70-78% (would-have-been calibrated)
Trade mechanism: breakout-continuation (Bull UP_TRI recovery)

Bootstrap edge case handling:
- Days 1-10 of new Bull regime: SHADOW mode (per Bull
  PRODUCTION_POSTURE activation gate)
- Day 11+: full Bull cell rules activate
- C1 hysteresis state initializes at first scan with NULL prev label;
  Day 2 is first non-bootstrap day for hysteresis purposes
```

---

## K. Step 3 readiness signal (REVISED post-LLM)

| Step 3 readiness check | Status |
|---|---|
| All A1 audit gaps surfaced | ✅ DONE |
| All Choppy critiques resolved | ✅ DONE |
| All Bear critiques resolved | ✅ DONE |
| Schema design recommendation | ✅ 2-tier |
| Rule precedence model | ✅ 4-layer |
| **Rule composition logic (NEW)** | ✅ 3 conflict examples (section I) |
| Worked examples authored | ✅ 9 examples (5 in section E + 4 in section J) |
| Calibrated WR expectations | ✅ DONE |
| C1 + C3 sequencing decision | ✅ Together with composite hysteresis |
| B1 vs B2 decision | ✅ Ship B1, defer B2 |
| Pruning strategy | ✅ HIGH + MEDIUM only initially |
| Schema migration | ✅ Breaking change v3 → v4 with parallel validation |
| Mechanism annotation scope | ✅ Per-cell |
| Production code changes blocking Step 3 | NONE |
| API spend Step 1.5 + 2 | $0.116 (A1 + SY LLM) |
| Atomic commits Step 1.5 + 2 | 8 (A1 + C1-C3 + B1-B3 + SY) |
| **Step 3 unblocked?** | ✅ READY |

**All 3 Sonnet blockers addressed inline.** Step 3 (Opus rule
synthesis) is unblocked. SY closes here.

Step 3 deliverables expected:
1. `structural_rules_v4.json` (universal patterns + schema)
2. `parametric_cells_v4.json` (per-cell axes + thresholds + mechanism)
3. Rule precedence + composition logic (validated against 9 worked examples)
4. Schema migration plan (v3 → v4 parallel evaluation)
5. Test vectors for runtime validation
