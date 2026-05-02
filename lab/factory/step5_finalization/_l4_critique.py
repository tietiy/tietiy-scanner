"""L4 Sonnet critique of Opus final synthesis."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "L4_critique.md"


def main():
    integration = (_HERE / "L4_opus_output" / "integration_notes_FINAL.md").read_text()
    known_issues = (_HERE / "L4_opus_output" / "KNOWN_ISSUES.md").read_text()
    trader_exp = (_HERE / "L4_opus_output" / "trader_expectations.md").read_text()

    summary = f"""
# L4 Opus Final Synthesis

## integration_notes_FINAL.md (excerpt)
{integration[:3000]}

## KNOWN_ISSUES.md (excerpt)
{known_issues[:3000]}

## trader_expectations.md (excerpt)
{trader_exp[:3500]}
"""

    prompt = f"""You are reviewing the L4 Opus FINAL synthesis — the
closing artifacts for the Lab pipeline. We have 37-rule v4.1 ruleset,
production deployment plan, KNOWN_ISSUES catalogue, and trader
expectations document.

{summary}

## Critique requested

1. **Production deployment plan defensibility.** Is the Phase 1 → 2 →
   3 sequence realistic? Are pre-deployment checklist items
   sufficient? What's missing?

2. **Calibrated WR honesty.** Trader has been seeing 95% live WR.
   Production calibrated is 53-72%. Trader expectations doc explains
   this — is the explanation honest enough? Does it under-prepare
   the trader for the emotional shift?

3. **Trader emotional preparation realistic?** First 30 days plan,
   failure modes, escalation criteria — does this set the trader up
   for success or for disappointment?

4. **KNOWN_ISSUES coverage.** 2 active WARNINGs + 6 LOW deferred + 4
   methodology limitations + 5 future iteration items. Are there
   risks NOT documented that production would surface?

5. **What's the SINGLE BIGGEST RISK in first 30 days of live
   trading?** Be specific.

6. **Step 7 (production integration) handoff complete?** Can a
   production engineer take these 4 deliverables and ship a working
   system, or are critical pieces missing?

Format: markdown, ## sections per question. 2-3 short paragraphs.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4000)
    OUT.write_text(
        f"# L4 Opus Final Synthesis — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
