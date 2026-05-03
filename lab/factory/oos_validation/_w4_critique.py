"""W4 Sonnet final review of DEPLOYMENT_DECISION + SHIP_LIST."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "_w4_critique.md"


def main():
    decision = (_HERE / "DEPLOYMENT_DECISION.md").read_text()
    ship = (_HERE / "SHIP_LIST.md").read_text()

    summary = f"""
# DEPLOYMENT_DECISION + SHIP_LIST (final)

## DEPLOYMENT_DECISION (excerpt)

{decision[:4500]}

## SHIP_LIST (excerpt)

{ship[:4000]}
"""

    prompt = f"""You are doing the FINAL REVIEW before the trader
deploys. Walk-forward validation produced a 2-rule SHIP_LIST.
Phase 1 specifies 25% capital with kill-switches and 60-day
evaluation.

{summary}

## Critique requested

1. **Are kill-switch thresholds defensible?** "Per-rule WR < 50%
   over 20 signals → halt" and "WR < 60% over 30 signals → reduce
   to 12.5%." You flagged in PB4 that Wilson lower bound on 13/20
   is 45%. Are these new thresholds noise-prone? What kill-switch
   would actually fire correctly?

2. **Is 25% capital position sizing honest?** Trader's 5% per trade
   max → 1.25% per Phase 1 signal. With 2 rules generating maybe
   5-15 signals per month, that's ~5-15% of capital cycling at any
   time. Is this too small to learn from? Too large for unvalidated
   rules?

3. **rule_019 hot sub-regime gating.** The walk-forward result
   (+17.2pp lift, n=191 mean per window) is genuinely strong. But
   it depends on Bear detector firing correctly. What happens if
   Bear detector mis-classifies on a transition day and rule_019
   fires when sub-regime is actually warm or cold? Is the trader
   protected?

4. **The "PHASE 1 EXPERIMENTAL" label in Telegram.** Sonnet
   recommended this in PB4. Is it actually behaviorally protective,
   or will trader just train their eye to ignore it after 30 days?
   Stronger alternatives?

5. **win_003 RECALL recommendation.** Already in production at full
   sizing (per existing kill_001 + win_007 logic). Walk-forward
   shows -14pp recent decay. Should the trader actually recall it
   tomorrow morning, or wait for next 5 signals to confirm decay
   pattern?

6. **What could break this in first 30 days that walk-forward
   couldn't catch?** Specifically — failure modes the walk-forward
   methodology has structural blindspots for.

7. **Honest probability that Phase 1 (2 rules at 25% cap, 60-day
   eval) produces meaningful positive return?** Compare to:
   - Full 8-rule Lab "READY_TO_SHIP" deployment (rejected by W3)
   - 5-rule deployment from Opus deep dive
   - Discretionary trading without rules
   - No deployment (continue paused)

Format: markdown, ## sections per question. 2-3 short paragraphs.
Be ruthless. Final review before deploy.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4500)
    OUT.write_text(
        f"# W4 Deployment — Sonnet 4.5 Final Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
