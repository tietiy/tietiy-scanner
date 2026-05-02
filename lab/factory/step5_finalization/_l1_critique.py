"""L1 — Sonnet critique of win_* recalibration."""
from __future__ import annotations
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "L1_critique.md"


def main():
    results = json.loads((_HERE / "L1_recalibration_results.json").read_text())
    summary = f"""
# L1 Win_* Recalibration Results

## Aggregate
- Total rules: {results['n_rules']}
- PASS: {results['summary']['PASS']} ({results['summary']['pass_rate']*100:.1f}%)
- WARNING: {results['summary']['WARNING']}
- FAIL: {results['summary']['FAIL']}
- Pass+Warning: {results['summary']['pass_or_warning_rate']*100:.1f}%

## Step 4 baseline → L1 post-recalibration
- PASS: 13 (35.1%) → 20 (54.1%) [+19pp]
- WARNING: 12 → 12
- FAIL: 12 → 5 [-58%]
- Pass+Warning: 67.6% → 86.5% [+19pp; exceeded 80% target]

## Changes applied
{chr(10).join('- ' + c for c in results['changes_applied'])}

## Win_* recalibration values

| Rule | Sector | Old expected_wr | New expected_wr | Lifetime n | Lifetime WR |
|---|---|---|---|---|---|
| win_001 | Auto | 0.72 (live 21/21) | 0.59 | 1009 | 59.5% |
| win_002 | FMCG | 0.74 (live 19/19) | 0.58 | 1274 | 57.6% |
| win_003 | IT | 0.61 (live 18/18) | 0.53 | 1046 | 53.3% |
| win_004 | Metal | 0.68 (live 15/15) | 0.57 | 1147 | 57.1% |
| win_005 | Pharma | 0.72 (live 13/13) | 0.58 | 1142 | 57.7% |
| win_006 | Infra | 0.65 (live 10.5/12) | 0.54 | 1039 | 53.8% |

kill_001 fix: regime=None → regime='Bear'; n 3,695 → 595 at 45% WR

## Remaining 5 FAILs (post-L1)
- rule_011 (Bear DOWN_TRI calendar): n=1748 vs predicted 700-1100
- rule_007 (Health × Bear UP_TRI hot): n=42 actual vs 120-200 predicted (rule WR 32.4% perfect; prediction band too tight)
- rule_020 (Path 2): structural issue
- rule_022 (Path 2): structural issue
- rule_025 (Path 2): structural issue
"""

    prompt = f"""You are reviewing the L1 win_* recalibration step
of the Lab pipeline. We mechanically replaced 6 win_* rules' predictions
with lifetime baselines. Validation jumped from 67.6% → 86.5%
PASS+WARNING.

{summary}

## Critique requested

1. **Are recalibrated values defensible?** The win_* rules were seeded
   from live small-sample (90-100% WR). Lifetime WR is 53-60%. Trader
   expectations need to shift dramatically. Is this calibration honest,
   or are we under-calibrating because lifetime data spans 15 years
   including regimes very different from current?

2. **Should any rules NOT have been recalibrated?** The win_* rules
   represent strong live performance in a specific sub-regime (April
   2026 hot Bear). Recalibrating to broad lifetime drops expected WR
   by 13-19pp. An alternative was to ADD sub_regime_constraint='hot'
   to keep the rules narrow and high-confidence. Is broad-match +
   recalibration the right choice, or should we have kept narrow
   match + high WR?

3. **Production trader expectation shift.** Trader has been seeing 95%
   live WR. Production rules now claim 53-59% WR. This is a 30-40pp
   downgrade. Is this honest reporting, or will the trader view it as
   "the system got worse" and lose confidence? How to communicate the
   shift?

4. **5 remaining FAILs.** All are prediction-band tightness issues
   (rule_007 has perfect 32.4% match WR but band was 120-200; actual
   was 42). Should L2 loosen prediction bands schema-wide, or
   per-rule?

5. **86.5% PASS+WARNING.** Above the 80% target. Is the Lab pipeline
   essentially done at the rule-quality level, or are there
   second-order issues (e.g., rule interaction, deployment risk) that
   the validation harness can't catch?

Format: markdown, ## sections per question. 2-3 short paragraphs each.
Be specific, ruthless.
"""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    OUT.write_text(
        f"# L1 Win_* Recalibration — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
