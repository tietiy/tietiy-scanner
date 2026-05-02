# LAB PIPELINE COMPLETE

**Date:** 2026-05-03
**Branch:** backtest-lab; HEAD `4c335e43` (post-L4) + this commit (L5)
**Pipeline duration:** ~10 sessions across Steps 1-5
**Cumulative API spend:** $21.41

---

## Executive summary

The Lab pipeline analyzed **9 cells** (3 regimes × 3 signal types)
across **lifetime (15-year) data** plus April-May 2026 live data,
investigated **14 critique scenarios** raised by Sonnet 4.5,
synthesized **37 production rules** via dual-Opus methodology
(Path 1 Disciplined + Path 2 Trust-Opus), and produced a
production-ready **schema v4.1** rule set plus barcode format
plus deployment plan plus trader expectations document.

The closing artifacts (`lab/factory/step5_finalization/L4_opus_output/`)
are ready for **Step 7 production integration**:
- `unified_rules_v4_1_FINAL.json` — 37-rule production ruleset
- `integration_notes_FINAL.md` — phased deployment plan
- `KNOWN_ISSUES.md` — documented limitations + mitigations
- `trader_expectations.md` — emotional + analytical preparation

Validation: **35/37 PASS, 2 WARNING, 0 FAIL** (94.6% PASS, 100% PASS+WARN).

---

## Pipeline trajectory

| Step | Sub-blocks | Atomic commits | API spend | Outcome |
|---|---|---|---|---|
| Step 1: Bull critiques | S1-S6 | 6 | $0.06 | 5 RESOLVED + SUMMARY |
| Step 2: Critique resolution | A1, C1-C3, B1-B3, SY | 8 | $0.12 | 7 RESOLVED + SUMMARY |
| Step 3: Opus synthesis | OP1-OP4 | 4 | $5.05 | 26 rules at 65% PASS+WARN |
| Step 4: Dual-path Opus | P1A-P3 | 5 | $10.04 | 37 rules at 67.6% PASS+WARN; methodology insight |
| Step 5: Finalization | L1-L5 | 5 | $3.66 | 37 rules at 100% PASS+WARN; barcode + plan |
| **Total** | **30 sub-blocks** | **28 commits** | **$21.41** | **Production-ready** |

---

## Architectural insights consolidated

### Cross-regime universal patterns (3)

1. **Sub-regime tri-modal structure**: Every regime (Bear/Bull/Choppy)
   has tri-modal (or quad-modal for Bull) sub-regime structure with
   regime-specific axes:
   - Choppy: vol × breadth (+ momentum from C1)
   - Bear: vol_percentile × 60d_return
   - Bull: 200d_return × breadth
2. **Calendar inversion across direction**: UP_TRI vs DOWN_TRI prefer
   opposite calendar weeks within the same regime. Confirmed in 3/3
   regimes (Bear wk4↔wk2, Bull wk4↔wk3, Choppy wk4↔wk3).
3. **vol_climax × BULL_PROXY anti-pattern**: Universal across
   regimes — vol_climax breaks support reversal mechanism that
   BULL_PROXY depends on.

### Direction-flip pattern (universal within regime)

Bull regime exhibits **PERFECT 4-cell sub-regime inversion** between
UP_TRI and DOWN_TRI:
- recovery_bull: UP_TRI 60.2%, DOWN_TRI 35.7%
- healthy_bull: UP_TRI 58.4%, DOWN_TRI 40.5%
- normal_bull: UP_TRI 51.3%, DOWN_TRI 42.6%
- late_bull: UP_TRI 45.1%, DOWN_TRI 53.0%

This is the strongest cross-cell architectural finding in the Lab.

### Counterintuitive Bear UP_TRI finding (B1)

**boundary_hot tier (71.5% WR) > confident_hot tier (64.2% WR).**
Bear UP_TRI rewards inflection-points within stress, not depth-of-
stress. This was discovered during B1 critique investigation — the
Bear UP_TRI playbook was updated post-investigation.

### Methodology lessons (Step 4)

- **Disciplined Opus prompting** modestly outperforms Trust-Opus
  (+8.6pp PASS+WARN)
- **Trust-Opus catches existing-rule bugs** (kill_001 regime fix)
  that Disciplined preserves literally
- **Dual-path produces breadth** beyond either path alone
- **Numeric thresholds beat bucket labels** for harness compatibility
- **Prediction calibration is the real ceiling** — Opus produces
  good rules; predictions need lifetime-calibrated input data

---

## 37 production rules — by priority

### HIGH priority (13 rules; production_ready=true)

Core edge-driver rules:
- Bull sub-regime gating (recovery_bull, late_bull SKIPs and TAKE_FULLs)
- Bear UP_TRI hot Health AVOID
- vol_climax × BULL_PROXY universal REJECT
- Existing 7 win_* sector boosts (recalibrated to lifetime in L1)

### MEDIUM priority (18 rules; production_ready=true)

Catastrophe avoidance + calendar filters + cold cascade boosts:
- Bear UP_TRI Dec SKIP (-25pp)
- Choppy UP_TRI Feb SKIP (-16pp)
- Choppy BULL_PROXY entire-cell REJECT
- Bear DOWN_TRI wk2/wk3 calendar
- Bear UP_TRI cold cascade boost
- Bull DOWN_TRI late_bull × wk3 (Path 2 contribution)
- Bull cell rules (recovery_bull × vol=Med × fvg<2)
- Plus 11 other rules covering edge cases

### LOW priority (6 rules; production_ready=false; deferred to Phase 2+)

Sector + day-of-week micro-rules:
- Bull UP_TRI × Energy SKIP
- Bull UP_TRI/PROXY × Sep SKIP
- Choppy DOWN_TRI: Pharma, Friday, wk4 SKIPs
- Choppy UP_TRI × Metal SKIP

---

## Schema v4.1 (final)

2-tier structure:
- `match_fields`: signal × sector × regime
- `conditions`: array of `{feature, value, operator}` AND-gated

Plus per-rule fields:
- `verdict`: TAKE_FULL / TAKE_SMALL / WATCH / SKIP / REJECT
- `expected_wr`: calibrated WR
- `confidence_tier`: HIGH / MEDIUM / LOW
- `trade_mechanism`: mean_reversion / breakout_continuation / etc.
- `regime_constraint` + `sub_regime_constraint`
- `production_ready` + `deferred_reason` + `known_issue`
- `barcode_compatibility`
- `evidence`: {n, wr, lift_pp, tier}

Predictions schema v4.1 makes tolerance bands first-class:
- `predicted_match_count_min/max` (was implied ±20%)
- `predicted_match_wr_min/max` (was implied ±5pp)
- `calibration_basis`: lifetime_observation / live_observation / predicted

Rule precedence model (4-layer):
1. KILL/REJECT terminating
2. Sub-regime gate
3. Sector / Calendar pessimistic merge
4. Phase-5 override (upgrade-only, Wilson lower bound > base + 5pp)

---

## Barcode format v1 (L3)

Production runtime emits barcode JSON per signal capturing:
- `regime_state`: regime + sub_regime + classifier_confidence
- `rule_match`: matched_rule_ids[] + primary_verdict + kill_overrides
- `confidence`: tier + calibrated_wr + calibrated_wr_band
- `caps`: name_cap + date_cap + sector_concentration statuses
- `execution`: action + sizing_recommendation
- `context`: trade_mechanism + expected_hold_days + source_playbook

Backward-compatible with signal_history.json (schema v5). Phase A
shadow-write → Phase B replace → Phase C clean.

---

## Step 7 production integration handoff

### Pre-conditions (must complete first)

| Pre-condition | Status |
|---|---|
| Schema v4.1 finalized | ✅ Done (L2) |
| 37-rule v4.1 ruleset validated | ✅ Done (94.6% PASS) |
| Barcode format designed | ✅ Done (L3) |
| Production deployment plan | ✅ Done (L4 integration_notes_FINAL.md) |
| KNOWN_ISSUES catalogued | ✅ Done (L4) |
| Trader expectations document | ✅ Done (L4) |
| Bull sub-regime detector in production | ❌ Step 7 ship |
| Bear 4-tier classifier in production | ❌ Step 7 ship |
| Choppy 3-axis detector + N=2 hysteresis | ❌ Step 7 ship |
| Phase-5 override mechanism | ❌ Step 7 ship |
| Bucket registry (Lab thresholds) persisted | ❌ Step 7 ship |
| 2-week parallel validation infra | ❌ Step 7 ship |

### Step 7 phased rollout (per L4 integration_notes_FINAL)

- **Week 1-2**: Phase 1 — HIGH priority rules + Bull sub-regime
  detector + Bear 4-tier classifier + Phase-5 override
- **Week 3-4**: Phase 2 — MEDIUM priority rules + Choppy 3-axis
  detector + N=2 hysteresis
- **Week 4-5**: 2-week parallel validation (v3 vs v4.1)
- **Week 5+**: Cutover decision (criteria: discrepancy <5%, WR delta
  <3pp); rollback procedure documented
- **Month 2+**: Phase 3 — LOW priority rules incremental activation
- **Month 6+**: B2 sigmoid Phase-2 evaluation

### Estimated Step 7 timeline: 4-6 weeks to live trading

---

## Deliverables index

### Production-ready (lab/factory/step5_finalization/L4_opus_output/)

- `unified_rules_v4_1_FINAL.json` — production ruleset
- `integration_notes_FINAL.md` — Step 7 deployment plan
- `KNOWN_ISSUES.md` — documented limitations + mitigations
- `trader_expectations.md` — trader emotional + analytical preparation

### Supporting (lab/factory/step5_finalization/)

- `unified_rules_v4_1_post_L2.json` — input to L4 (37 rules at 100% PASS+WARN)
- `validation_predictions_post_L2.json` — calibrated predictions
- `validation_post_L2.json` — final validation report
- `L1_recalibration_results.json` — win_* lifetime recalibration
- `L2_schema_gap_analysis.md` — v4.0 → v4.1 evolution
- `L3_opus_output/barcode_format_v1.md` — barcode design

### Methodology + critique (lab/factory/)

- `bull_critiques/` — 5 Bull verification critiques (S1-S5)
- `critiques_audit/` — A1 rules audit + 6 Choppy/Bear critiques + SY synthesis
- `opus_synthesis/` — Step 3 first Opus pass + validation
- `opus_iteration/` — Step 4 dual-path comparison + methodology findings

### Cell-level Lab work (lab/factory/{regime}_{signal}/)

- 9 playbook.md files
- Per-cell extract.py + lifetime/ subdir
- Per-cell synthesis docs

---

## Lessons documented for future Lab work

1. **Always recalibrate predictions to lifetime BEFORE Opus run.**
   Live small-sample predictions cause systematic FAIL rate.
2. **Build bucket registry for Lab thresholds** — eliminate
   "categorical bucket label" ambiguity that broke Step 3 validation.
3. **Default to Disciplined Opus prompts** for production synthesis.
   Reserve Trust-Opus for QA passes that catch literal-preservation
   bugs.
4. **Per-rule prediction tolerance is essential**. Implicit ±20% /
   ±5pp doesn't work for sub-regime narrow rules.
5. **Two-stage methodology**: Disciplined synthesis → Trust-Opus QA
   pass costs $10/iteration but catches semantic bugs the constrained
   pass misses.
6. **Counterintuitive findings are real**. Bear UP_TRI boundary_hot >
   confident_hot was discovered via B1 critique; the playbook was
   wrong before this investigation.

---

## Sonnet 4.5 final review (full critique: `lab/factory/step5_finalization/L5_critique.md`)

### Verdict

**"Lab work is complete with two caveats: operational gaps exist, but they're fixable in Step 7 Week 1."**

### 3 gaps Sonnet identified

1. **Sub-regime detectors never validated on Apr-May 2026 live data** —
   architectural completeness is real, but operational confirmation
   that detectors don't misclassify on the trader's actual market
   conditions is missing.
2. **Phase-5 override mechanism has no live-data dry run** — no
   estimate of how many signals/week trigger override (1-2 in
   bull, 0-1 in bear); trader has no mental model.
3. **Sector concentration cap × rule precedence untested** —
   barcode v1 has `sector_concentration` status field but no
   documented behavior for "TAKE_FULL fires while sector cap
   already hit."

### Most likely production surprise

Week 2 of Phase 1, Bull sub-regime detector classifies as
`recovery_bull` but trader feels like `healthy_bull`; 3 UP_TRI
signals get SKIPed that trader would have taken manually.
Trader loses confidence — not because detector is wrong, but
because they weren't shown a live dry run during April-May 2026.

### Week 0 pre-deployment recommendation (added to plan)

Add a **5-day Week 0** before Step 7 Phase 1 that does:
1. **Day 1-2**: Run sub-regime detectors on Apr-May 2026 live data;
   compare to trader's manual regime log; document discrepancies.
2. **Day 3**: Run Phase-5 override on Apr-May 2026 signals; output
   upgrade count + WR deltas; add to trader_expectations.md.
3. **Day 4**: Unit-test sector cap × rule precedence interaction.
4. **Day 5**: Trader paper-trades 10 historical signals (5 SKIP +
   5 TAKE_FULL) to calibrate emotional override criteria.

**Cost of Week 0**: ~$50-100 engineering time (no AI spend).
**Value**: Converts the 3 gaps from "trader discovers in Week 2"
to "trader is pre-calibrated before Day 1." Lifts first-30-day
success probability from estimated 70% → 90%.

### Spend justification (Sonnet)

> "$21.41 was under-spend if anything. You could've justified
> $30-40 to do the missing live dry-runs. The 37 rules are a
> byproduct — the actual deliverable is the methodology for
> doing this again."

### Most generalizable methodology lessons (Sonnet ranked)

1. **Recalibrate predictions to lifetime BEFORE synthesis**, not
   after. Step 3 → L1 sequence was inefficient because predictions
   were calibrated to live small-sample first.
2. **Bucket registry is first-class schema requirement, not
   documentation**. Step 3 validation failed because bucket
   labels were implicit; L2 retrofitted; should have been in
   schema v1.
3. **Counterintuitive findings require Lab investigation, not
   production deferral**. B1 discovered `boundary_hot >
   confident_hot` — playbook was wrong before this. Stop and
   investigate when synthesis surfaces logic-violating patterns.
4. **Disciplined prompting + Trust-Opus QA pass** beats either
   alone for high-stakes rule synthesis. Costs $10/iteration but
   catches semantic bugs.

---

## Final disposition

**LAB PIPELINE: COMPLETE.**

37 production rules. Schema v4.1. Barcode format v1. Phased
deployment plan. KNOWN_ISSUES catalogued. Trader expectations
documented. Methodology lessons captured.

**Recommended next step:** Week 0 pre-deployment (5 days, no
AI spend) → Step 7 Phase 1 deployment (Week 1-2).

**Cumulative AI spend:** $21.41. Sonnet's verdict: under-spent
if anything; another $50-100 in engineering Week 0 work would
materially de-risk first 30 days.
