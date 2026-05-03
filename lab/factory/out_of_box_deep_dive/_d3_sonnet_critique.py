"""D3 — Sonnet 4.5 critique of Opus deep dive output."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "sonnet_critique.md"


def main():
    diag = (_HERE / "output" / "independent_diagnosis.md").read_text()
    paths = (_HERE / "output" / "path_critique.md").read_text()
    alts = (_HERE / "output" / "unconventional_alternatives.md").read_text()
    rec = (_HERE / "output" / "recommended_combination.md").read_text()
    brutal = (_HERE / "output" / "brutal_assessment.md").read_text()

    summary = f"""
# Opus Deep Dive Output (5 deliverables)

## Headline conclusions Opus produced

1. **Disagrees with my data-starvation framing.** Identifies 4
   deeper problems: circular validation, win_*/Path B anomaly
   papered over, methodology overfit, complexity-without-evidence.

2. **Path 9 (paper trading 60 days) SIGNIFICANTLY OVERRATED.**
   N math doesn't work for narrow rules.

3. **My missing path: "Delete 32 rules, deploy 5."**

4. **Walk-forward OOS test (Day 1-3) is "single highest-value
   action you skipped."**

5. **Hire human quant for $300-500 / 4 hours** — claims this is
   best feedback per dollar; LLMs cannot give what human with
   skin-in-game can.

6. **AI-tool dependency is primary risk** (not perfectionism).
   "Your last advisory should be a human quant, not me."

7. **Honest 12-month return probabilities:**
   - 37-rule path: 25% meaningful win / 25% meaningful loss
   - 5-rule path: 35% / 20%
   - Walk-forward OOS first path: 40% / 15%

8. **Recommendation:** Phase 0 (Week 1: walk-forward OOS + ablation
   + hire quant + decision gate) → Phase 1 (Week 2: 5-10 rules at
   half size) → 6 months trade + accumulate → revisit Lab v2.

## Excerpt from Opus brutal_assessment

{brutal[:4500]}

---

## Excerpt from Opus path_critique (subset)

{paths[:3500]}

---

## Excerpt from Opus recommended_combination

{rec[:2500]}
"""

    prompt = f"""You are critiquing Claude Opus 4.7's "deep dive" on
a quantitative trading system at deployment decision point. The
trader's analysis suggested paper trading + multi-detector + regime
tolerance + Opus advisory. Opus produced this output (excerpts
above).

The trader needs an honest second opinion BEFORE morning. Opus's
output is harsh (correctly?) and pushes the trader toward simpler
deployment + walk-forward OOS test + hiring a human quant.

## Your critique

1. **Did Opus genuinely engage with the problem or produce confident-
   sounding generic advice?** Be specific. Distinguish "engagement"
   from "pattern-matching from training data."

2. **Are Opus's unconventional alternatives genuinely unconventional
   or just rebranded standard ideas?** Specifically: "delete 32
   rules", "hire quant", "trade simple system 6 months first" —
   are these insights or obvious-in-retrospect?

3. **Did Opus identify the trader's cognitive biases honestly?**
   It identified: AI-tool dependency, completeness (not
   perfectionism), sunk cost. Did it miss any? Did it manufacture
   any?

4. **Did Opus's brutal_assessment.md actually pull punches or land
   truthfully?** Read the excerpt. Is "you wrote me a document
   asking me to confirm conclusions you'd already reached" a
   genuine insight or rhetorical posturing?

5. **What's the strongest single recommendation across both my
   analysis and Opus's?** If you had to combine the best of both,
   what would emerge?

6. **What's the trader most likely to misinterpret or skip from
   Opus's output?** Specifically watch for: trader rationalizing
   "Opus is just being LLM-pessimistic" and dismissing it.

7. **If you had to pick ONE thing for the trader to do tomorrow
   morning, what would it be?** Single concrete next action.

Format: markdown, ## sections per question. Be specific. Be ruthless.
This is final review before trader deployment decision.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4500)
    OUT.write_text(
        f"# D3 Sonnet 4.5 Critique of Opus Deep Dive\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
