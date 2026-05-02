# Opus Rule Synthesis Validation — Sonnet 4.5 Critique

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`

# Opus Rule Synthesis Validation Critique

## 1. Failure Root Cause Categorization

**Bucketing/threshold mismatch (5 rules):** `rule_001`, `rule_002`, `rule_003`, `rule_004`, `rule_005`, `rule_012` all show dramatic count mismatches (65 vs 268, 0 vs 390, 0 vs 128, 0 vs 3374) while WR predictions remain close when data exists. This is **not** a logic bug—Opus correctly translated the playbook conditions. The Lab used different bucket thresholds (likely quintiles or custom splits for recovery_bull, or absolute thresholds like "vol_regime=Medium means 40-60 percentile"). Your tertile splits at 33/67 produce different populations. `rule_003` and `rule_004` hit zero because recovery_bull (n=199 in your data vs 972 in Lab) is sparse, and the vol=Medium/fvg_low intersection is empty at your thresholds.

**Missing sub-regime constraints (2 rules):** `rule_007` (Health×Bear UP_TRI) and `rule_008` (Health×Bear DN_TRI) match 311 and 1663 signals vs predicted 158 and 850. Lab findings were sub-regime specific (hot=32.4%, warm=30.7%) but Opus rules lack `sub_regime_constraint`. This is a **prompt ambiguity bug**—playbooks said "Bear hot" but Opus interpreted as regime=Bear without the sub-regime gate. WR drift (48.6% vs 32.4%, 30.7% vs 30.7%) confirms dilution across sub-regimes.

**Prediction overstatement (2 rules):** `win_003` and `win_006` show count±10% but WR outside band. `win_003` predicted 70% WR from 18/18 live signals, actual lifetime is 60.8%—classic small-sample overfit. `win_006` shows 72% vs 65% predicted, count 182 vs 150—this may be a legitimate regime shift or the playbook cherry-picked a hot period. These are **playbook prediction errors**, not Opus bugs.

---

## 2. Iterate Opus Prompt or Accept Current Rule Set?

**Current state assessment:** 38% PASS is below the 60-80% target, but 65% PASS+WARNING is borderline acceptable if WARNINGs are minor (count drift with WR intact). However, 9 FAILs include 3 zero-match rules and 2 rules missing critical sub-regime gates—these are **not cosmetic**. The session brief implicitly assumes rules will *fire* and produce usable signals; zero-match rules are dead weight.

**Recommendation: One focused iteration.** The failures cluster into two fixable categories: (a) missing sub-regime constraints (rule_007, rule_008), (b) bucket threshold ambiguity causing zero-matches (rule_003, rule_004, rule_012). A $2-3 Opus call with a targeted prompt can salvage 5+ rules. Specifically: "When playbook specifies 'Bear hot', emit `sub_regime_constraint='hot'`. When playbook uses 'low/medium/high' buckets, ask for explicit thresholds or default to tertiles with a comment flag." Manual fixes are faster for 2 rules but won't prevent the same bugs in future playbooks.

**Cost-benefit:** Spending $3 to rescue 5 high-priority rules (rule_003 is 74.1% WR, rule_012 is 63.3% WR) is justified. Manual fixing 9 rules costs 2-3 hours of eng time ($150-300 opportunity cost). Iterate once, then manual-fix stragglers.

---

## 3. Rule-by-Rule Action Recommendation

| Rule | Action | Rationale |
|------|--------|-----------|
| **win_003** | **(c) Accept with caveat** | Prediction error (70% from n=18 live overfitted). Document: "Live WR 70% not replicated in lifetime data (60.8%). Rule valid but expect 60-65% going forward." |
| **win_006** | **(c) Accept with caveat** | Count 182 vs 150 is +21%, WR 72% vs 65% is edge-case but within noise. Document: "Lifetime WR exceeds playbook by 7pp; monitor for regime drift." |
| **rule_002** | **(a) Regenerate** | Count mismatch 65 vs 268 suggests bucket threshold issue. Opus re-run with explicit tertile instruction may fix. If still broken, **(b) manual fix** to loosen fvg/vol thresholds. |
| **rule_003** | **(a) Regenerate + validate Lab data** | Zero-match is unacceptable for 74.1% WR prediction. Lab's n=390 recovery_bull signals vs your n=199 means different regime definitions. Request Lab's recovery_bull threshold (200d_return > X%, breadth > Y%) and hard-code in Opus prompt. |
| **rule_004** | **(a) Regenerate + validate Lab data** | Same as rule_003. Healthy_bull×swing_high=high×fvg_low is sparse. Verify Lab's swing_high="high" threshold (>=4 vs >=3?). |
| **rule_005** | **(b) Manual fix or (c) accept** | vol_climax_flag is rare (n=48). If Lab playbook was exploratory, document "Feature too sparse for production; archive rule." If high conviction, manually broaden to `vol_climax_flag OR atr_pct_20d > 80th percentile`. |
| **rule_007** | **(a) Regenerate** | Missing sub_regime=hot constraint. Trivial Opus fix: "emit sub_regime_constraint='hot' when playbook specifies Bear hot." High priority—this dilutes a 32% edge to 48%. |
| **rule_008** | **(a) Regenerate** | Same as rule_007. Missing sub_regime=warm constraint. |
| **rule_012** | **(a) Regenerate + investigate** | Zero-match for n=3374 prediction is catastrophic. Either (i) Lab used entirely different feature definitions (e.g., `fvg_unfilled_above_count` vs `fvg_gap_pct`), or (ii) bucketing mismatch. Opus re-run with explicit feature mapping + tertile bounds. If still zero, escalate to Lab for raw SQL. |

**Summary actions:** Regenerate 6 rules (rule_002, rule_003, rule_004, rule_007, rule_008, rule_012). Accept 2 with caveats (win_003, win_006). Manual-fix or archive 1 (rule_005).

---

## 4. Bucketing Threshold Mismatch: Resolution Strategy

**Root cause confirmed:** Lab playbooks use bucket labels ("low/medium/high", "recovery_bull") without embedding threshold definitions. Your validation harness defaulted to tertile splits (33/67 percentile), but Lab analyses likely used quintiles (20/40/60/80) or domain-specific cuts (e.g., recovery_bull = "200d_return > 15% AND breadth_ma50 > 60%"). This is a **data contract gap**, not an Opus bug.

**Recommended fix: Hybrid approach.** (1) **Short-term (this sprint):** Re-derive Lab thresholds by requesting the raw SQL or bucket definitions from the 9 playbooks. Hard-code these into the Opus prompt as examples: "recovery_bull means 200d_return > 12% AND breadth_ma50 > 55%". Opus will emit rules with inline comments documenting the thresholds. (2) **Medium-term:** Formalize a `bucket_registry.yaml` that maps feature→bucket_label→threshold. Validation harness reads this registry; Opus emits `bucket_id` references instead of raw thresholds. This prevents drift.

**Do not accept as "known precision gap."** The gap caused 5 of 9 failures and renders 3 rules useless (0 matches). Documenting it without fixing guarantees the next 10 playbooks will fail validation at 40% rate. The fix (request Lab thresholds, encode in prompt) costs 2 hours of coordination but prevents $50+ of wasted Opus calls and 10+ hours of debugging.

---

## 5. rule_003 + rule_004 Zero-Match Recovery Plan

**Diagnosis:** Lab reported n=390 for recovery_bull×vol=Med×fvg_low (74.1% WR) and n=128 for healthy_bull×swing_high=high×fvg_low (62.5% WR). Your validation found n=199 recovery_bull signals total and n=9,309 healthy_bull signals, yet the rule intersections produced 0 matches. This implies **feature intersection is empty at your bucket thresholds**, not that the features don't exist.

**Hypothesis testing:** (1) Check if Lab's "vol=Medium" means 40-60 percentile vs your 33-67 tertile. If Lab used quintiles, "Medium" = 40-60, and your "Medium" = 33-67 overlaps but shifts the population. (2) Verify `fvg_unfilled_above_count` bucket definition: your "low" is <=1, but Lab's may be <=2. (3) Confirm `swing_high_count_20d` "high" threshold: your >=4 vs Lab's >=3 could halve the population. Request Lab's raw SQL for these two rules.

**Recovery actions:** (a) **Immediate:** Run ad-hoc query on your 105,987 signals with Lab's exact thresholds (once received) to verify n=390 and n=128 are replicable. If not, Lab data may be from a different time window or symbol universe—escalate. (b) **Opus re-run:** Once thresholds confirmed, update prompt with explicit bounds: "recovery_bull = 200d_return > 12% AND breadth_ma50 > 55%; vol=Medium = atr_pct_20d between 35th-65th percentile." (c) **If still zero-match:** Archive rules with note "Lab findings not replicable in lifetime data; likely regime-specific or feature definition drift."

---

## 6. rule_007 Sub-Regime Constraint Fix

**Issue confirmed:** Lab finding was "Bear hot sub-regime, Health setup, UP_TRI → 32.4% WR (n=158)." Opus rule omitted `sub_regime_constraint='hot'`, so it matches all Bear signals (hot+warm+cold), producing n=311 at 48.6% WR. The 16pp WR inflation (48.6% vs 32.4%) and 2× count error proves the rule is firing on diluted population.

**Fix is trivial:** Add `sub_regime_constraint='hot'` to the rule dictionary. This is a one-line change: `rule_007['sub_regime_constraint'] = 'hot'`. Estimated impact: count drops to ~100-120 (your Bear hot sub-regime has 2,862 signals, Health setup is ~5% of setups, UP_TRI is ~60% of Health), WR drops toward 32-35%. This restores the edge.

**Recommendation: Manual fix now, Opus iteration for systemic prevention.** Manually patch rule_007 and rule_008 (same issue, Bear warm sub-regime) in the next 10 minutes. Then include in the Opus re-run prompt: "When playbook specifies regime + sub-regime (e.g., 'Bear hot'), emit both `regime_constraint` AND `sub_regime_constraint`. Example: regime_constraint='Bear', sub_regime_constraint='hot'." This prevents recurrence in future playbooks. Do not accept as gap—sub-regime gating is a core feature of the regime framework and omitting it breaks the strategy logic.

---

## 7. Iterate Opus Once: Go/No-Go Decision

**Go.** The failure analysis identifies **6 rules fixable by prompt clarification** (rule_002, rule_003, rule_004, rule_007, rule_008, rule_012) and **2 rules that are playbook prediction errors** (win_003, win_006). Manual fixing 6 rules costs 1-2 hours; iterating Opus with a focused prompt costs $2-3 and 20 minutes of eng time to prepare the prompt + validate output. The Opus iteration also **prevents the same bugs in future playbook batches**, which is worth 10× the cost.

**Focused prompt additions:** (1) "When playbook specifies regime + sub-regime (e.g., 'Bear hot'), emit both `regime_constraint='Bear'` AND `sub_regime_constraint='hot'`." (2) "When playbook uses bucket labels (low/medium/high), assume tertile splits (33/67 percentile) unless explicit thresholds provided. Emit inline comment: `# bucket: low = <=33rd percentile`." (3) "When playbook references recovery_bull or healthy_bull, use these definitions: recovery_bull = 200d_return > 12% AND breadth_ma50 > 55%; healthy_bull = 200d_return > 8% AND breadth_ma50 > 50%." (Hard-code after receiving Lab confirmation.)

**Iteration scope:** Re-run Opus on the 9 cell playbooks with the updated prompt. Validate only the 9 FAIL rules + 7 WARNING rules (16 total) to confirm fixes. Accept the 10 PASS rules as-is (no need to regenerate). Expected outcome: 6 FAIL→PASS, 2 FAIL→WARNING (win_003, win_006), 1 FAIL→manual (rule_005). This brings pass rate to 16/26 = 62%, within target. **Authorize the $3 spend.**
