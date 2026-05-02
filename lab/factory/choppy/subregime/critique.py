"""
T1 follow-up: send the proposed Choppy sub-regime detector design to
Sonnet 4.5 for critique. Are the features chosen sufficient? Are the
thresholds defensible? What edge cases might break it?

Saves: lab/factory/choppy/subregime/detector_critique.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

VALIDATION_PATH = _HERE / "detector_validation.json"
DESIGN_MD_PATH = _HERE / "detector_design.md"
OUTPUT_PATH = _HERE / "detector_critique.md"


def main():
    print("─" * 80)
    print("T1 follow-up: Sonnet 4.5 critique of sub-regime detector")
    print("─" * 80)

    validation = json.loads(VALIDATION_PATH.read_text())
    design_md = DESIGN_MD_PATH.read_text()

    # Excerpt the most decision-relevant parts of the design doc to keep
    # the prompt compact (under ~3000 tokens of context).
    summary_excerpt = f"""
## Detector design summary

PRIMARY axis: nifty_vol_percentile_20d (continuous 0-1)
  Thresholds: < 0.30 → quiet, 0.30-0.70 → balance, > 0.70 → stress
  These thresholds come from the existing feature_loader categorical
  definition (feat_nifty_vol_regime: Low/Medium/High).

SECONDARY axis: market_breadth_pct (% universe stocks above 50d SMA)
  Subtype qualifier: < 0.30 → low_breadth, 0.30-0.60 → med_breadth,
                     > 0.60 → high_breadth

OUTPUT:
  subregime ∈ {{quiet, balance, stress}}
  subtype = "{{sub}}__{{breadth_qual}}"  (9 cells)
  confidence: 0-100 (geometric distance from boundary, not calibrated)

## Lifetime validation results (35,290 Choppy signals)

Distribution match: 100% agreement with categorical feat_nifty_vol_regime
(detector is essentially a continuous re-derivation of the same boundaries).

WR by subregime × signal_type (validates tri-modal hypothesis):
{json.dumps(validation['wr_by_subregime_x_signal'], indent=2, default=str)[:1500]}

## Subtype WR (most important — confirms / refines L3 findings)

UP_TRI:
  stress__med_breadth: 60.1% on n=4954  (L3 winner — confirmed)
  stress__low_breadth: 20.2% on n=372   (CATASTROPHIC — new finding)
  stress__high_breadth: 51.7% on n=2171
  balance__med_breadth: 46.8% on n=7762 (the actual hostile cell)
  balance__high_breadth: 54.0% on n=4760
  quiet__low_breadth: 65.1% on n=359    (surprisingly strong — new finding)
  quiet__med_breadth: 53.4% on n=3218
  quiet__high_breadth: 55.8% on n=2214

DOWN_TRI:
  balance__med_breadth: 55.2% on n=1903 (L3 DOWN_TRI winner)
  balance__low_breadth: 44.4% on n=361
  All other cells: 35-45% range

BULL_PROXY:
  quiet__high_breadth: 57.1% on n=178   (best, but small)
  All other cells: 46-56% range

## Live April 2026 classification

100% stress sub-regime; 87% stress__high_breadth, 13% stress__med_breadth.
0 signals classified as balance__med_breadth (the L3 DOWN_TRI winner cell)
or quiet__* (surprising 65% UP_TRI cell).

## Limitations explicitly known
1. No transition-state detection (sudden flip on a single day)
2. Breadth thresholds inherited from feature spec, not optimized
3. Confidence is geometric (distance) not statistically calibrated
4. Single-day classification, no smoothing
"""

    prompt = f"""You are reviewing the design of a market sub-regime
detector for an Indian-equity Choppy-regime trading system. The detector
classifies daily market state into one of three sub-regimes (stress /
balance / quiet) plus a breadth-qualifier subtype, to gate which
historical filter to apply per signal.

{summary_excerpt}

## Critique requested

1. **Feature sufficiency**: Are `nifty_vol_percentile_20d` (primary) and
   `market_breadth_pct` (secondary) sufficient to capture meaningful Choppy
   sub-regime structure? What is the strongest *missing* feature, and why
   does its absence matter? Be specific.

2. **Threshold defensibility**: The 0.30 / 0.70 vol-percentile cutoffs were
   inherited from an existing categorical feature, not optimized for
   sub-regime separation. Is this defensible at face value, or is the
   detector likely to be sub-optimal? If sub-optimal, suggest a principled
   way to choose thresholds.

3. **Edge cases that break it**: List 3-5 concrete market scenarios where
   this detector would mis-classify in a way that produces wrong filter
   selection. Be specific (e.g., "post-Budget Feb 2024-style scenario where
   X happens").

4. **The `quiet__low_breadth` 65.1% UP_TRI surprise** (n=359). Is this
   likely a real edge or a survivor-bias artifact? What test would
   discriminate?

5. **The `stress__low_breadth` 20.2% UP_TRI catastrophe** (n=372). Is the
   small n credible enough to act on as a hard SKIP rule, or do we need
   more evidence?

6. **Production deployment risk**: If this detector ships TODAY without
   transition-state handling, what is the most likely failure mode in the
   first 6 months of production?

Format: markdown, ## sections per question. Be terse — 2-4 short paragraphs
per section, not exhaustive. Where you can hedge with confidence
qualifiers, do so honestly."""

    client = LLMClient()
    print(f"\nCost so far: ${client._total_cost:.3f}")
    print("Calling Sonnet 4.5 for critique...")
    response = client.synthesize_findings(prompt, max_tokens=2800)

    md = f"""# Choppy Sub-Regime Detector — Sonnet 4.5 Critique

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`
**Source:** `detector_design.md` + `detector_validation.json`

## Critique

{response}
"""
    OUTPUT_PATH.write_text(md)
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
