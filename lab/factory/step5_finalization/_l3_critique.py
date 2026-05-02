"""L3 Sonnet critique of Opus barcode design."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "L3_critique.md"


def main():
    fmt = (_HERE / "L3_opus_output" / "barcode_format_v1.md").read_text()
    examples = (_HERE / "L3_opus_output" / "barcode_examples.json").read_text()
    integration = (_HERE / "L3_opus_output" / "integration_spec.md").read_text()

    summary = f"""
# L3 Opus Barcode Format Design

## barcode_format_v1.md (excerpt)
{fmt[:3500]}

## Sample example structure
{examples[:2500]}

## integration_spec.md (excerpt)
{integration[:2500]}
"""

    prompt = f"""You are reviewing the Opus-designed production barcode
format for the TIE TIY Scanner. The barcode encodes per-signal regime
classification, matched rules, verdict, calibrated WR, cap statuses,
etc. Production scanner generates 100s/day; archives must be compact
and self-documenting.

{summary}

## Critique requested

1. **Format compactness.** Production scanner generates ~50-300 signals
   per scan day. Each barcode persists to archive. Is the proposed
   format compact enough for daily volume? Are there fields that could
   be reference-by-id instead of inline?

2. **Field naming clarity.** Production traders + future maintenance
   need to read these. Are field names clear / consistent? Any
   ambiguous names?

3. **Edge cases that might break.** What scenarios would produce
   malformed barcodes? Multiple matched rules with conflicting
   verdicts? No matched rules? Corrupt sub-regime classification?
   Missing optional fields?

4. **Production performance.** Generating barcode per signal: is the
   structure realistic for ~50ms latency budget? Any nested lookups
   or computations that could blow up?

5. **Backward compatibility.** Barcode is supposed to extend
   signal_history.json (current schema v5). Does the Opus design
   preserve compatibility, or does it implicitly require v6 migration?

6. **Self-documentation.** Each barcode contains its own context.
   Does the format actually achieve this? Specifically: can a trader
   look at one barcode and understand WHY the verdict was generated
   without consulting external rule files?

7. **Concrete fix list.** If production deployment is the goal, what
   2-3 changes would you mandate before this format is locked?

Format: markdown, ## sections per question. 2-3 short paragraphs.
Be specific.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    OUT.write_text(
        f"# L3 Opus Barcode Design — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
