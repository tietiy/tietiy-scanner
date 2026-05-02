# Step 4 Methodology Findings — Disciplined vs Trust-Opus

**Date:** 2026-05-03
**Branch:** backtest-lab; commits `e226ca74` (P1A) → ... → P3 merge

---

## A. Headline results

| Path | Rules | PASS | WARNING | FAIL | PASS rate | PASS+WARN |
|---|---|---|---|---|---|---|
| Step 3 (baseline) | 26 | 10 | 7 | 9 | 38.5% | 65.4% |
| Path 1 Disciplined | 27 | 9 | 9 | 9 | 33.3% | **66.7%** |
| Path 2 Trust-Opus | 31 | 10 | 8 | 13 | 32.3% | 58.1% |
| **Merged best-of-both** | **37** | **13** | **12** | **12** | **35.1%** | **67.6%** |

**Path 1 narrowly beats Path 2 on PASS+WARNING by 8.6pp.** Merged
set marginally beats Path 1 (+0.9pp). Step 3 baseline beat Path 1
on PASS rate alone but had lower PASS+WARNING.

The 80%+ PASS+WARNING target was NOT reached. The bottleneck is
existing rule predictions (win_* family) calibrated to live small-
sample data, not Opus synthesis quality.

---

## B. Methodology comparison

### What Path 1 (Disciplined) did better

1. **Per-rule fix instructions worked.** rule_007 had
   `sub_regime_constraint='hot'` added (Step 3 root cause fixed).
2. **Numeric thresholds beat bucket labels.** Rules using `feat_X
   lt 0.30` validated cleanly; Path 2 rules using `feat_X eq 'low'`
   required harness bucket-label support and were less reliable.
3. **Lifetime calibration of predictions improved.** Path 1 used
   honestly calibrated count bands (e.g., Bear UP_TRI Dec 1,200-1,900);
   Path 2 sometimes inherited Step 3 over-tight bands.
4. **Restored dropped rule (wk4 Choppy DOWN).** Path 1 emitted
   rule_018 explicitly as instructed.

### What Path 2 (Trust-Opus) did better

1. **Caught Path 1's kill_001 bug.** Original production rule has
   no explicit `regime` field; Path 1 preserved `regime=None`
   (matching all regimes → matched 3,695 signals). Path 2 inferred
   `regime=Bear` from source finding ("0/11 in Bear") and matched
   correctly at 653 signals.
2. **Surfaced new high-edge rule slot.** rule_020 (Bull DOWN_TRI
   late_bull × wk3 TAKE_SMALL at 65.2% lifetime, +21.8pp lift)
   was missed by Path 1's prescribed rule list. Path 2 read the Bull
   DOWN_TRI playbook and synthesized this rule from "open question"
   text.
3. **Added within-cell refinement.** rule_022 (Bear UP_TRI hot
   refinement at +9.5pp lift) — Path 1 didn't include this even
   though the playbook mentions it.
4. **More breadth of coverage.** 22 new rules vs Path 1's 18.

### What both paths got wrong

1. **win_* family predictions remain calibrated to live small-sample
   (90-100% WR), not lifetime baseline (53-60% WR).** All 6 sector
   boost rules (win_001-006) FAIL in both paths.
2. **Neither path added sub_regime_constraint to existing win_*
   rules.** Lab evidence is hot sub-regime specific; production rules
   match all Bear sub-regimes regardless.

---

## C. Per-slot merge analysis

Merge picked Path 1 for 25 logical rules; Path 2 for 12 (37 unique
slots after coarse signature dedup).

**Path 2 contributions to final merge:**
- `rule_019` (kill_001 with regime=Bear) — PASS
- `rule_002` (Bull BULL_PROXY late_bull SKIP) — PASS (Path 1 was WARNING)
- `rule_014` (Bull UP/PROXY Sep SKIP, n=3070) — PASS
- `rule_021` (Bear UP_TRI hot at boundary) — WARNING
- `rule_026` (Bull DOWN late_bull × wk3) — WARNING
- 7 others

**Path 1 dominated on:**
- HIGH priority Bull rules (recovery_bull, healthy_bull) with
  detailed conditions
- Calendar SKIP rules (Dec, Feb)
- LOW priority sector kills

---

## D. What does this teach about Opus prompting?

### Hypothesis test results

| Hypothesis | Verdict |
|---|---|
| Explicit constraints produce better Opus output | **MODESTLY TRUE** (+8.6pp PASS+WARN) |
| Trust-Opus produces better Opus output | FALSE (lower PASS+WARN) |
| Best-of-both produces meaningfully better output | **MARGINAL** (+0.9pp over best path) |
| Opus is robust to prompt variation | **TRUE for schema** (both produced compliant rules) |
| Opus catches existing-rule bugs with freedom | **TRUE** (Path 2 fixed kill_001 regime gap) |

### Practical recommendations for future Opus prompting

1. **Use disciplined prompts as default.** Explicit thresholds +
   per-rule fix instructions yield better validation rates.
2. **Reserve Trust-Opus for breadth discovery.** When you suspect
   the prompt may be missing rule slots (e.g., new playbook areas),
   Trust-Opus can surface them.
3. **Combine for best results:** start Disciplined; if validation
   shows missing rules, run a Trust-Opus pass to surface gaps.
4. **Numeric thresholds beat bucket labels.** Always prefer
   `{"feature": "X", "value": 0.30, "operator": "lt"}` over
   `{"feature": "X_bucket", "value": "low"}`. Validation harness
   compatibility is better.
5. **Prediction calibration is the real ceiling.** Both paths plateau
   at ~67% PASS+WARNING because predictions for existing rules
   reflect live small-sample (overfit). Calibrate predictions to
   lifetime data BEFORE running Opus.

### Cost-benefit of dual-path approach

- Cost: 2× Opus calls = $10.00 (one path = $5.00)
- Benefit: +0.9pp PASS+WARNING over best single path
- ROI: marginal for production output; **valuable for methodology
  insight** (we now know explicit prompting wins for Opus rule
  synthesis)

For future Step-3-equivalent synthesis tasks, **single Disciplined
Opus run** is recommended unless dual-path study is the explicit
goal.

---

## E. Why didn't either path reach 80%?

### The win_* prediction problem

Production rules `win_001` through `win_007` are seeded from live
small-sample data:
- `win_001`: 21/21 (100%) live → predicted 70-77% lifetime
- `win_002`: 19/19 (100%) → predicted 69-79%
- `win_003`: 18/18 (100%) → predicted 65-75%
- ... etc.

**Actual lifetime WR for these slots is ~55-60%** (regime+sector +
no sub-regime gate). The predictions are inflated by live small-n
selection bias. Both Opus paths inherited these inflated predictions
from Step 3 and didn't recalibrate.

**Fix:** Recalibrate win_* predictions to lifetime values OR add
`sub_regime_constraint='hot'` to win_* rules so they match the
narrower cohort their live evidence reflects. This is independent
of Opus output quality.

### The structural ceiling

Without fixing predictions:
- 9 existing rules × ~6 in failed prediction cohort → ~6 FAILs guaranteed
- 6/26 = 23% guaranteed FAIL rate
- Maximum achievable PASS+WARNING: 100% - 23% = 77%

So the 67-68% achieved is close to the structural ceiling given
prediction calibration issues. Reaching 80% requires Step 4
prediction recalibration as a separate task.

---

## F. Recommendations for production deployment

### Immediate (Step 4 closing)

1. **Use the merged final rule set** (`unified_rules_final.json`,
   37 rules) as the v4 deployment baseline
2. **Manually fix predictions for win_001-006** to lifetime calibration
3. **Add `sub_regime_constraint='hot'` to existing win_* rules** OR
   leave broad-match (current behavior) and accept lower expected_wr

### Step 5 (schema/barcode) input

The 37-rule merged set is ready for Step 5. Schema is v4 (2-tier).
All rules conform.

### Step 7 (production integration)

Use the merged set, with caveats:
- 13 PASS rules are deployment-ready
- 12 WARNING rules are deployment-ready with monitoring
- 12 FAIL rules: mostly existing win_* (recalibrate predictions) +
  some new rules with prediction inflation (recalibrate)

### Step 8+ (iteration)

Future Lab playbook updates will produce new rule synthesis tasks.
Lessons from Step 4:
- Default to Disciplined Opus prompting
- Validate against canonical Lab thresholds (not tertile splits)
- Recalibrate predictions to lifetime BEFORE Opus run

---

## G. Cumulative cost recap

| Step | Spend |
|---|---|
| Step 1 | $0.06 (Sonnet critique) |
| Step 2 | $0.12 (Sonnet critiques) |
| Step 3 | $5.05 (Opus + Sonnet validation) |
| Step 4 | $10.00 (2× Opus) — current |
| **Total** | **$15.23** |

Step 4 spent $10 to learn one methodology lesson (Disciplined > Trust)
and to gain marginal output improvement (+0.9pp). Cost-benefit was
moderate; future synthesis tasks should use single Disciplined run
to save $5/iteration.
