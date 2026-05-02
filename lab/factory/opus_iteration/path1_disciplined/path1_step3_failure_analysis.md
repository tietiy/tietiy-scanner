# Path 1 — Step 3 Validation Failure Analysis

**Date:** 2026-05-03
**Source:** Step 3 OP3 validation harness output + Sonnet 4.5 critique
**Purpose:** Provide Opus the exact failure modes to address in Path 1
iteration. Each failure is categorized by root cause + recommended fix.

---

## Step 3 results recap

- 26 rules generated (9 existing + 17 new)
- Validation: **10 PASS / 7 WARNING / 9 FAIL**
- Pass rate: 38.5%; Pass+Warning: 65.4%

## 9 FAIL rules — root cause categorization

### Category A: Bucket threshold mismatch (5 rules — primary fix)

| Rule | Predicted | Actual | Root cause |
|---|---|---|---|
| `rule_002` | n=268 (Bull late_bull BULL_PROXY) | n=65 | Wrong breadth threshold; Lab uses 0.60/0.80, harness used tertile |
| `rule_003` | n=390 (recovery_bull × vol=Med × fvg_low) | **n=0** | Zero match — bucket threshold catastrophic mismatch |
| `rule_004` | n=128 (healthy_bull × 20d=high) | **n=0** | Zero match — same |
| `rule_012` | n=3,374 (Bear UP_TRI cold cascade wk4 × swing_high=low) | **n=0** | swing_high_count_20d "low" was Lab `<2` not harness `<=1` |
| `rule_005` | n=139 (vol_climax × BULL_PROXY × Bear) | n=48 | vol_climax_flag is sparse (~0.05% of signals) |

**Fix applied in Path 1:**
- All thresholds explicitly documented in `path1_thresholds_explicit.md`
- Opus instructed to use exact numeric thresholds (e.g., `<0.30` not "low" without
  threshold)
- For Bull sub-regimes, USE Bull detector axes (0.05/0.20 for 200d, 0.60/0.80
  for breadth) — NOT feature library thresholds

### Category B: Missing sub_regime_constraint (1 rule)

| Rule | Issue | Lab finding |
|---|---|---|
| `rule_007` | Health × Bear UP_TRI matched all Bear (n=311 at 48.6% WR) | 32.4% WR specifically in HOT sub-regime; Opus omitted sub_regime_constraint='hot' |

**Fix applied in Path 1:**
- Path 1 prompt explicitly: "When playbook specifies regime + sub-regime
  (e.g., 'Bear hot, Health AVOID'), emit BOTH `regime_constraint` AND
  `sub_regime_constraint`."
- Specifically: rule_007 must include `sub_regime_constraint='hot'`

### Category C: Prediction overstatement (2 rules — accept with caveat)

| Rule | Prediction | Actual | Reason |
|---|---|---|---|
| `win_003` | 65-75% WR (IT × Bear UP_TRI) | 60.8% | Predicted from 18/18 live; lifetime is lower |
| `win_006` | 60-70% WR, n=120-180 | 72% WR, n=182 | Slight count + WR drift; not a bug |

**Fix applied in Path 1:**
- Path 1 prompt: "When existing rule has live small-sample evidence
  (e.g., 18/18), use LIFETIME baseline calibrated WR for `expected_wr`,
  not live observation. Document live observation in source_finding."
- Update predictions to use lifetime calibration

### Category D: Rule fragmentation cost dropped wk4 (1 rule slot)

Step 3 brief said: "Choppy DOWN_TRI: Pharma SKIP, Friday SKIP, **wk4 small**"
Opus produced rule_015 (Pharma) + rule_016 (Friday) but **dropped wk4**.

**Fix applied in Path 1:**
- Path 1 prompt: "If a logical rule has multiple components (e.g., 3
  separate sectors/calendars all with SKIP), emit one rule per
  component. Do not drop components."
- Specifically: include rule for `feat_day_of_month_bucket=wk4 ×
  Choppy DOWN_TRI = SKIP` (-7.1pp lift)

### Category E: Sparse-feature rules (rule_005 also Cat A)

`rule_005` and `rule_006` both depend on `feat_vol_climax_flag=True`,
which is rare (~0.05% of signals). Even with correct thresholds, these
rules match few signals. This is mechanism-specific and acceptable.

**Fix applied in Path 1:**
- Path 1 prompt: "For rules depending on rare features (e.g.,
  vol_climax_flag), set realistic `predicted_match_count` based on
  feature frequency, not on the protected cohort target. Add
  `evidence` notes about feature sparsity."

---

## Summary of Path 1 mandates

1. **Use exact Lab thresholds** from `path1_thresholds_explicit.md`. Numeric, not bucket labels.
2. **Always emit sub_regime_constraint** when playbook specifies sub-regime.
3. **Calibrate `expected_wr` to lifetime** (not live small-sample).
4. **Maintain rule fragmentation if needed** but **do not drop components**.
5. **Realistic predictions for sparse-feature rules.**
6. **Restore wk4 Choppy DOWN_TRI rule** that Step 3 dropped.

---

## Expected Path 1 outcome (Opus addressing these directly)

Per Sonnet 4.5 critique recommendation: "6 rules fixable by prompt
clarification" (rule_002, 003, 004, 007, 008, 012). Plus rule_018 for
dropped wk4. Plus calibrated predictions for win_003, win_006.

Target Path 1: **80%+ PASS+WARNING** rate after re-validation with
corrected thresholds.

If Path 1 fails to reach 80%, the failure is structural (Opus has
limits with explicit-constraint prompting), and Path 2 (Trust-Opus)
becomes the comparison baseline.
