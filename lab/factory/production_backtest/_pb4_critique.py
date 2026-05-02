"""PB4 Sonnet critique of production backtest report."""
from __future__ import annotations
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "_pb4_critique.md"


def main():
    report = (_HERE / "BACKTEST_REPORT.md").read_text()
    readiness = json.loads((_HERE / "deployment_readiness.json").read_text())

    # Build summary for prompt
    import collections
    by_r = collections.Counter(r["readiness"] for r in readiness["rules"])

    summary = f"""
# Production Backtest — Headline + Per-Rule Readiness

## Headline (Path A signal_history; Path B enriched op-window)

Path A (290 production-promoted signals, 224 resolved):
- Actual production WR: 61.6%
- Rule TAKE: 71 signals, 60 resolved → 93.3% WR
- Rule SKIP/REJECT/WATCH: 219, 164 resolved → 50.0% WR
- Hypothetical PnL: +41 units / 290 signals

Path B (816 academic op-window, 566 resolved):
- Baseline WR: 64.1%
- Rule TAKE: 88 signals, 80 resolved → 91.2% WR
- Rule SKIP/REJECT/WATCH: 728, 486 resolved → 59.7%
- Hypothetical PnL: +66 units / 566 resolved

Cross-validation: TAKE WR Δ = 2.1pp (Path A 93.3% vs Path B 91.2%)

## Deployment readiness (37 rules)

- READY_TO_SHIP: {by_r['READY_TO_SHIP']}
- NEEDS_REVIEW: {by_r['NEEDS_REVIEW']}
- NEEDS_LIVE_DATA: {by_r['NEEDS_LIVE_DATA']}
- DEFER: {by_r.get('DEFER', 0)}
- DEPLOY_WITH_CAUTION: {by_r.get('DEPLOY_WITH_CAUTION', 0)}

By priority:
- HIGH (13 rules): 6 READY_TO_SHIP, 4 NEEDS_REVIEW, 3 NEEDS_LIVE_DATA
- MEDIUM (18 rules): 2 READY_TO_SHIP, 1 NEEDS_REVIEW, 15 NEEDS_LIVE_DATA
- LOW (6 rules): 0 READY_TO_SHIP, 6 NEEDS_LIVE_DATA

## NEEDS_REVIEW rules (Path A vs Path B divergence > 10pp)

- win_003 (IT×Bear UP_TRI): Δ=28pp (Path A 100% vs Path B 72%)
- win_005 (Pharma×Bear UP_TRI): Δ=33pp (Path A 100% vs Path B 67%)
- win_006 (Infra×Bear UP_TRI): Δ=12.5pp
- watch_001 (Choppy UP_TRI broad): Δ=14.4pp (Path A 35% vs Path B 49%)
- rule_031 (Bear UP_TRI IT hot): Δ=17.6pp

## NEEDS_LIVE_DATA breakdown

- 7 Bull rules (no Bull regime in Apr 2026)
- ~17 rules with n<5 in operational window (mostly calendar-
  conditional like Dec/Sep/Feb SKIPs that don't fire in April,
  or Choppy sub-regime rules with rare April matches)

## April 2026 = hot Bear sub-regime

The 90%+ TAKE WRs reflect April's hot Bear conditions. Lab calibrated
WRs (53-72%) are LIFETIME baselines integrated across hot/warm/cold.
Hot Bear cells expected to produce 85-95% WR; cold Bear 50-58%.
"""

    prompt = f"""You are reviewing the production backtest report
for the TIE TIY Scanner. We applied 37 v4.1 rules to (A) production
signal_history (290 signals) and (B) enriched_signals same window
(816 signals). Cross-validation Δ = 2.1pp.

{summary}

## Critique requested

1. **Are deployment recommendations honest?** 8 READY_TO_SHIP feels
   small. Many rules NEEDS_LIVE_DATA because of small operational
   window (April 2026 alone). Should we lower the n>=5 threshold to
   include more rules, or is conservative deferral correct?

2. **NEEDS_REVIEW rules — should they ship despite Path A vs Path B
   divergence?** win_003/005/006 (Bear UP_TRI sector boosts) show
   Path A 100% but Path B 70%. Production filter selects high-WR
   subset; broader universe is closer to Lab-calibrated. The current
   production rule (win_003) is ALREADY shipped (kill_001 + win_007
   are existing production rules). Recalling them isn't an option;
   the question is whether they should be flagged in production logs.

3. **TAKE WR 91-93% in Path A and B — credible or too good?** The
   Bear UP_TRI cell finding documented 94.6% live observed with
   Phase-5 selection bias. Backtest reproduces 93.3% (Path A) and
   91.2% (Path B). Is this honest evidence the rules work, or
   circular validation (rules tested on data they were derived from)?

4. **Production deployment risk in Step 7.** With 8 READY_TO_SHIP
   and 24 NEEDS_LIVE_DATA, Phase 1 deployment is essentially the
   8 READY rules + existing production rules. That's defensible
   but narrow. Should Step 7 wait until more sub-regime windows
   accumulate, or is Phase 1 enough to start?

5. **Single biggest risk for Step 7 deployment NOT surfaced by this
   backtest.** Be specific.

6. **Should the 5 NEEDS_REVIEW rules be DOWNGRADED to NEEDS_LIVE_DATA
   instead?** The Path A vs B divergence is real. Could justify
   "we don't trust these enough to ship until more data."

Format: markdown, ## sections per question. 2-3 short paragraphs.
Be ruthless.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4000)
    OUT.write_text(
        f"# PB4 Production Backtest — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
