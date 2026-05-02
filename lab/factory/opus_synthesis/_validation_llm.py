"""OP3 — Sonnet 4.5 critique of Opus rule synthesis validation report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_validation_llm.md"
REPORT_PATH = _HERE / "validation_report.json"


def main():
    report = json.loads(REPORT_PATH.read_text())

    # Build summary text for prompt
    summary_lines = []
    fail_lines = []
    warn_lines = []
    pass_lines = []
    for r in report["results"]:
        line = (
            f"  {r['rule_id']:14s} | {r['validation_verdict']:7s} | "
            f"actual n={r['actual_match_count']:5d} WR={(r['actual_match_wr'] or 0)*100:5.1f}% | "
            f"pred n={r['predicted_match_count']:5d} WR={(r['predicted_match_wr'] or 0)*100:5.1f}% | "
            f"{r['reason']}"
        )
        if r["validation_verdict"] == "FAIL":
            fail_lines.append(line)
        elif r["validation_verdict"] == "WARNING":
            warn_lines.append(line)
        else:
            pass_lines.append(line)

    s = report["summary"]
    summary_text = f"""
# Opus Rule Synthesis Validation Report

## Aggregate
- Total rules: {report['n_rules']}
- PASS: {s['PASS']} ({s['pass_rate']*100:.0f}%)
- WARNING: {s['WARNING']}
- FAIL: {s['FAIL']}
- Pass-or-warning rate: {s['pass_or_warning_rate']*100:.0f}%

## Per-rule results

### FAILED rules ({s['FAIL']})
{chr(10).join(fail_lines)}

### WARNING rules ({s['WARNING']})
{chr(10).join(warn_lines)}

### PASSED rules ({s['PASS']})
{chr(10).join(pass_lines)}

## Validation harness notes
- 105,987 total signals; 94,643 resolved (DAY6_WIN/LOSS/TARGET/STOP)
- Sub-regime computed per regime: Bull (200d × breadth), Bear (vol percentile × n60), Choppy (vol_regime × breadth_bucket)
- Bucketing uses tertile (33/67) splits for continuous features
- swing_high_count_20d bucketed as low(<=1), medium, high(>=4)
- fvg_unfilled_above_count bucketed as low(<=1), medium, high(>=5)

## Sub-regime distribution observed
- Bull: 50,809 total → recovery_bull 199, healthy_bull 9,309, late_bull 1,483, normal_bull 39,818
- Bear: 19,682 → hot 2,862, warm 8,343, cold 8,477
- Choppy: 35,496 → 9-cell distribution (vol × breadth)

## Failure analysis (preliminary categorization)
- Bucketing mismatch: Lab playbooks may have used different bucket thresholds
  (e.g., recovery_bull n=199 here vs 972 in Lab; Lab's 200d/breadth thresholds
  differ from my tertile splits)
- Prediction inaccuracy: some predictions overstated count/WR (e.g., win_003
  IT×Bear was based on 18/18 live, but lifetime WR is 60.8%)
- Rule too broad: rule_007 (Health×Bear UP_TRI) matches 311 signals across
  all sub-regimes; Lab's 32.4% finding was specifically in hot sub-regime —
  Opus rule didn't gate on sub-regime
- vol_climax sparse: rule_005, rule_006 match very few signals because
  feat_vol_climax_flag is rare
- 0 matches: rule_003, rule_004, rule_012 produce 0 matches due to
  feature combination rarity at my bucket thresholds
"""

    prompt = f"""You are reviewing the Opus rule synthesis validation
report. Step 3 ran Opus to produce 26 production rules from 9 cell
playbooks. Validation harness applied rules to 105,987 lifetime signals
to verify match counts + WRs against playbook predictions.

{summary_text}

## Critique requested

1. **Failure root cause categorization.** Are the 9 failures genuine
   rule logic bugs (Opus mis-translated playbooks) or prediction errors
   (playbook predictions imprecise / lifetime-vs-live confusion /
   bucketing-threshold mismatch)? Be specific per rule.

2. **Iterate Opus prompt or accept current rule set?** The pass rate
   is 38% PASS, 65% PASS+WARNING. Session brief expected 60-80% on
   first synthesis. Are we in acceptable range, or should we iterate?

3. **Rule-by-rule action recommendation.** For each FAIL: (a)
   regenerate via second Opus call with prompt fix, (b) manually fix
   the rule, or (c) accept as known limitation with documented
   caveat. Be concrete.

4. **Bucketing threshold mismatch is systemic.** The Lab playbooks
   reference categorical buckets (low/medium/high) but the playbooks
   don't always specify what threshold defines "low". My validation
   harness used 33/67 tertile splits. Lab analyses may have used
   different splits. Should this be:
   - Resolved by re-deriving Lab thresholds from raw data
   - Documented as known precision gap
   - Fixed via Opus iteration

5. **rule_003 + rule_004 0-match is concerning.** These are HIGH
   priority rules (recovery_bull × vol=Med × fvg_low at 74.1% lifetime,
   healthy_bull × 20d=high at 62.5%). My validation found 0 matches.
   But Lab said n=390 and n=128 respectively. What went wrong, and
   how do we recover the predictions?

6. **rule_007 (Health × Bear UP_TRI) should have sub_regime constraint.**
   Lab finding 32.4% WR was specifically in hot sub-regime. Opus rule
   has no sub_regime_constraint, so it matches across all Bear hot/warm/
   cold. Fix: add sub_regime_constraint=hot. Should this be a Step 3
   iteration or accepted gap?

7. **Should we iterate Opus once with a focused prompt addressing the
   FAIL rules?** Cost would be ~$2-3 for a focused re-run. Is the
   iteration worth the spend, or is manual fix faster?

Format: markdown, ## sections per question. 2-3 short paragraphs each.
Be specific, ruthless, where you can recommend a concrete action, do.
"""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Opus Rule Synthesis Validation — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
