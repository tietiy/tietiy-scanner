"""L5 Sonnet final review of LAB_PIPELINE_COMPLETE."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "L5_critique.md"


def main():
    summary_doc = (_LAB_ROOT / "LAB_PIPELINE_COMPLETE.md").read_text()

    prompt = f"""You are doing the FINAL REVIEW of the entire Lab
pipeline. The Lab analyzed 9 trading cells (3 regimes × 3 signal
types) over 5 steps, produced 37 production rules at schema v4.1,
designed a barcode format, and wrote a deployment plan.

Cumulative cost: $21.41. Pipeline duration: 5 steps + 30 sub-blocks.

# LAB_PIPELINE_COMPLETE.md

{summary_doc}

## Critical review

1. **Is the Lab work genuinely complete?** Are there gaps that the
   trader/team will discover in production that should have been
   caught here? Be specific — what's the most likely gap?

2. **Is the trader prepared for production deployment?** They've
   been seeing 95% live WR; production says 53-72%. The trader
   expectations document explains this. Realistic preparation, or
   under-preparation?

3. **Single biggest risk in first 30 days of live trading.** Be
   specific — what's the failure mode that's most likely to surface?

4. **What pre-deployment work is irreversibly missing?** Things that
   should have been done in Lab but weren't, that production
   couldn't easily fix.

5. **$21.41 spend on AI calls — value justification.** Was the
   spend worth it relative to alternative approaches (manual
   analysis, smaller-scope Lab, etc.)?

6. **Methodology lessons that generalize.** For future Lab work
   beyond TIE TIY (similar Lab pipelines on other strategies), what's
   the most transferable learning?

7. **Final verdict.** Lab work complete? Or "complete with caveats"?
   Or "needs Step 6 before Step 7"?

Format: markdown, ## sections per question. 2-3 short paragraphs each.
Be ruthless. This is the final review before production deployment.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4500)
    OUT.write_text(
        f"# L5 Lab Pipeline Complete — Sonnet 4.5 Final Review\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
