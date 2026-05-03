"""W3 Sonnet critique of stability analysis."""
from __future__ import annotations
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "_w3_critique.md"


def main():
    sa = json.loads((_HERE / "stability_analysis.json").read_text())

    summary_lines = []
    for c in sa["classifications"][:30]:
        ml = c.get("mean_lift")
        ml_s = f"{ml*100:+.1f}pp" if ml is not None else "—"
        delta = c.get("recent_vs_old_lift_delta")
        d_s = f"{delta*100:+.1f}pp" if delta is not None else "—"
        nm = c.get("mean_match_n", 0) or 0
        summary_lines.append(
            f"  {c['rule_id']:40s} | {c['category']:25s} | "
            f"lift={ml_s:>7s} pos={(c.get('pct_positive_windows') or 0)*100:.0f}% "
            f"recent_Δ={d_s:>7s} n={nm:.0f}"
        )

    summary = f"""
# Walk-Forward Stability Analysis on Lab's 37 Rules

## Setup
- 60-day rolling windows, 30-day step
- 182 windows spanning 2011-03-30 → 2026-04-10 (15 years)
- Each window: rule match WR vs same-window baseline WR for cohort
- Lift = match_wr - baseline_wr
- Validation tests passed (kill_001 -7.1pp, trivial UP_TRI 0.0pp)

## Category counts
{json.dumps(sa['category_counts'], indent=2)}

## 5 SURVIVORS (mean_lift > 5pp, pct_positive > 70%, n>=5)
{chr(10).join('  ' + s for s in sa['wf_survivors'])}

## 3 INTERSECTION (walk-forward SURVIVOR + backtest READY_TO_SHIP)
{chr(10).join('  ★ ' + s for s in sa['wf_x_backtest_high_confidence'])}

## 3 DEGRADERS (high mean lift but fading recent windows)
{chr(10).join('  ⚠ ' + s for s in sa['degraders'])}

## 4 REJECT_NEGATIVE_LIFT (boost rule with negative lift)
{chr(10).join('  ✗ ' + s for s in sa['rejects'])}

## Top 30 rules sorted by mean lift
{chr(10).join(summary_lines)}

## Detail on key findings

- **rule_019_bear_uptri_hot_refinement** is the strongest survivor:
  +17.2pp mean lift across 23 windows with match, 78% positive,
  mean n=191 per window. This is the broadest-sample HIGH rule.

- **kill_001** (Bear × Bank × DOWN_TRI = REJECT) consistently kills:
  -7.1pp mean across 80 windows with match, 39% positive (matches losers
  61% of windows). Clean kill rule.

- **rule_029 (Bear UP_TRI Pharma hot)** is alarming:
  +18pp mean BUT recent_Δ -57.7pp — Lab playbook said Pharma is top
  hot Bear sector; recent windows show the opposite.

- **win_007 (Bear BULL_PROXY hot)** has +32.5pp mean (highest of all rules)
  but recent_Δ -10.5pp — degradation trend.

- **All 4 Bull rules tested** show negative lift (Bull UP_TRI healthy/
  late and BULL_PROXY recovery). Bull rules need Bull regime activation;
  cannot be validated in primarily Bear/Choppy data.

- **11 rules INSUFFICIENT_DATA**: narrow Choppy sub-regime + Bull
  rules + specific calendar combos that don't accumulate matches across
  15-year lifetime.

## Decision case (per session brief)

- INTERSECTION count: 3 rules
- Falls in CASE 2: "DEPLOY high-confidence survivors only" (2-4 rules
  with 25% capital, kill-switches, 60-day evaluation)
"""

    prompt = f"""You are reviewing a walk-forward stability analysis
on a quantitative trading system's 37 rules. Walk-forward is the
honest OOS test (Opus's deep dive flagged Lab's prior backtest as
circular).

{summary}

## Critique requested

1. **Are SURVIVOR thresholds defensible?** mean_lift > 5pp AND
   pct_positive > 70% AND n>=5. Should we tighten (e.g., mean_lift
   > 7pp) to weed out marginal performers? Loosen to capture more?

2. **The 3 INTERSECTION rules** (kill_001, win_001, rule_019). Are
   these genuinely high-confidence or is the intersection
   compromised because both backtest and walk-forward use overlapping
   data? rule_019 has n=191 mean per window — strong sample. win_001
   is Bear×Auto×UP_TRI, exact same logic as Lab's win_001 already
   in production.

3. **DEGRADERS specifically**:
   - rule_029 Pharma hot: mean +18pp, recent -57.7pp. Should we
     SKIP this entirely or document it as "regime shift discovery"?
   - win_003 IT×Bear: mean +5pp, recent -14pp. Already in production.
     Should we recommend recall?

4. **All Bull rules show negative lift** (rule_010/011/012/023).
   Is this real data deficiency or genuine refutation of Lab's Bull
   work? Can we tell which from these windows?

5. **rule_031 IT hot** is in SURVIVOR (+16pp mean, 79% pos, n=18)
   but rule_029 Pharma hot is DEGRADER (+18pp mean, recent -57.7pp).
   Same cell type (Bear UP_TRI hot), different sectors. Is one
   Sector real edge and the other regime artifact?

6. **Are there rules we're rejecting that should pass with different
   criteria?** Specifically: 11 INSUFFICIENT_DATA rules — should
   we relax sample threshold for Bull rules (no Bull regime)?

7. **Lab work over-fit verdict.** Per Opus deep dive: "rules derived
   from + tested on April 2026 = circular." Walk-forward gives 3
   rules that survive across 15 years. Does this confirm or refute
   Lab's overall validity? Specifically: would 5 rules be
   appropriate Phase 1, or does this evidence support all of
   Lab's "8 READY_TO_SHIP from backtest"?

Format: markdown, ## sections per question. 2-3 short paragraphs.
Be ruthless.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4500)
    OUT.write_text(
        f"# W3 Walk-Forward Stability — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
