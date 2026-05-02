"""P3 — Sonnet 4.5 critique of Step 4 dual-Opus methodology results."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_methodology_llm.md"


def main():
    summary = """
# Step 4 Dual-Opus Methodology Comparison

## Aggregate validation results

| Path | Rules | PASS | WARNING | FAIL | PASS rate | PASS+WARN |
|---|---|---|---|---|---|---|
| Step 3 (baseline) | 26 | 10 | 7 | 9 | 38.5% | 65.4% |
| Path 1 Disciplined | 27 | 9 | 9 | 9 | 33.3% | **66.7%** |
| Path 2 Trust-Opus | 31 | 10 | 8 | 13 | 32.3% | 58.1% |
| Merged best-of-both | 37 | 13 | 12 | 12 | 35.1% | **67.6%** |

## Cost
- Path 1 Opus run: $5.07
- Path 2 Opus run: $4.93
- Total Step 4: $10.00
- Cumulative Lab: $15.23

## Key methodology findings

### Path 1 (Disciplined) wins on calibration
- Per-rule fix instructions worked (rule_007 sub_regime_constraint added)
- Numeric thresholds in conditions matched validation harness cleanly
- Lifetime-calibrated predictions improved validation pass rate

### Path 2 (Trust-Opus) wins on bug-catching + breadth
- Caught Path 1's kill_001 bug (regime=None vs regime='Bear')
- Surfaced rule_020 (Bull DOWN late_bull × wk3 +21.8pp lift) that Path 1 missed
- Added within-cell refinement (Bear UP_TRI hot +9.5pp from playbook open question)
- 22 new rules vs Path 1's 18

### Both paths fail on existing win_* rules
- 6/9 existing rules FAIL in BOTH paths
- Cause: predictions calibrated to live small-sample (90-100% WR) not lifetime (53-60%)
- This is a Step 4 prediction-calibration issue, NOT Opus output quality
- Fixing this would push PASS+WARNING from 67% to ~80%

### Structural ceiling explanation
Without fixing win_* predictions:
- 6 existing rules guaranteed FAIL
- 23% guaranteed FAIL rate
- Maximum PASS+WARNING: ~77%
- Both paths plateau at ~67% close to this ceiling

## Hypothesis test results
- Explicit constraints win: TRUE (modest, +8.6pp PASS+WARN)
- Trust-Opus wins: FALSE
- Best-of-both meaningfully better: MARGINAL (+0.9pp over best path)
- Opus robust to schema: TRUE
- Opus catches existing-rule bugs with freedom: TRUE (kill_001 fix)

## Recommendations
1. Default to Disciplined prompting for production synthesis
2. Reserve Trust-Opus for breadth discovery sessions
3. Numeric thresholds > bucket labels in conditions
4. Recalibrate win_* predictions to lifetime BEFORE next iteration
5. Combine: start Disciplined, run Trust-Opus when bug-catching needed

## Path-by-path FAIL examples for context

### Path 1 FAIL examples
- kill_001: regime=None preserves existing rule literally; matches 3,695 vs Lab 653
- win_001-006: Bear UP_TRI sector boosts; predictions inflated to 65-75% but lifetime ~55-60%
- rule_007: sub_regime_constraint='hot' added correctly, but prediction n=120-200 too tight (actual n=42 at 32.4% WR matches Lab perfectly)
- rule_011: Bear DOWN wk2/wk3 calendar; n=1748 vs predicted band

### Path 2 FAIL examples
- Same win_001-006 failures
- rule_006: Same as Path 1 rule_007 (Health × hot Bear) — strict prediction band again
- rule_010 (breadth=med × vol=Med × wk3 Choppy DOWN): bucket label issue
- rule_017: Bear DOWN wk2 only (without wk3 from Path 1)
"""

    prompt = f"""You are reviewing the Step 4 dual-Opus methodology
comparison. We ran two Opus paths in parallel — Path 1 (Disciplined,
explicit constraints) and Path 2 (Trust-Opus, freedom-first) — and
validated both against historical data + merged best-of-both.

{summary}

## Critique requested

1. **Headline verdict on methodology.** Path 1 wins on PASS+WARNING by
   8.6pp. Merged set marginally better. Is the conclusion ("Disciplined
   wins, default to it") sound? Or does the modest gap suggest both
   approaches are roughly equivalent and the choice should be based on
   other factors (cost, breadth, etc.)?

2. **Structural ceiling at 77%.** The win_* prediction-calibration
   issue caps PASS+WARNING at ~77% regardless of Opus prompt strategy.
   Should Step 4 close here, or should we recalibrate win_* predictions
   inline (manual fix) before declaring Step 4 complete? The
   recalibration is mechanical (replace 70-77% with 55-60%) but
   non-trivial since live data was 100% WR.

3. **Path 2's bug-catching value.** Path 2 caught the kill_001
   regime constraint bug that Path 1 missed. Is this a one-time win
   or a systematic pattern? Should production synthesis pipelines
   include a "Trust-Opus QA pass" specifically to catch such bugs
   in human-prescribed prompts?

4. **Merge complexity.** The merged set has 37 rules — more than
   either path alone. Some rules are functionally duplicated at
   different specificity levels (e.g., recovery_bull broad vs
   recovery_bull × vol=Med × fvg<2). Should production deploy 37
   rules with overlap, or aggressively deduplicate to ~25?

5. **$10 spend justification.** Step 4 cost $10 for +0.9pp gain over
   single best path. The session brief allowed up to $15. Was the
   methodology lesson worth $5 alone (the cost of the second Opus
   call)? Or should future iterations always run a single Disciplined
   path?

6. **Step 5 readiness.** With 67.6% PASS+WARNING, is the merged set
   ready for Step 5 (schema/barcode finalization), or does it need
   further iteration? Specifically: are the 12 FAIL rules acceptable
   to defer to Step 5 with documented caveats, or do they block
   Step 5?

7. **Cumulative spend trajectory.** Steps 1-4 spent $15.23. If
   Step 5+6 are lighter (per Step 3 STEP_3_REPORT projection), total
   Lab spend stays under $20. Is this trajectory acceptable for the
   value delivered (production-ready rule set + methodology
   insights), or should we cap further spending and accept current
   state?

Format: markdown, ## sections per question. 2-3 short paragraphs each.
Be specific, ruthless, and where you can recommend concrete action,
do.
"""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Step 4 Methodology — Sonnet 4.5 Final Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
