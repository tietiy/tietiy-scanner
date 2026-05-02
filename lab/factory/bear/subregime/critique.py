"""
S2 follow-up: send Bear vs Choppy detector architecture comparison to
Sonnet 4.5 for cross-cell architecture critique.

Saves: lab/factory/bear/subregime/architecture_critique.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

DETECTOR_JSON = _HERE / "detector.json"
OUTPUT_PATH = _HERE / "architecture_critique.md"


def main():
    detector = json.loads(DETECTOR_JSON.read_text())

    prompt = f"""You are reviewing the architecture of per-regime sub-
regime detectors for an Indian equity Bear/Choppy/Bull trading system.

## Choppy detector (T1, already built)
Structure: TRI-MODAL (quiet / balance / stress)
Primary axis: nifty_vol_percentile_20d
  • < 0.30 → quiet
  • 0.30-0.70 → balance
  • > 0.70 → stress
Secondary axis: market_breadth_pct (synchronicity, cross-section)
  • Subtypes: low_breadth / med_breadth / high_breadth (9-cell)

## Bear detector (S2, just built)
Structure: BIMODAL (hot / cold)
Primary axis: nifty_vol_percentile_20d (same as Choppy)
Secondary axis: nifty_60d_return_pct (depth, longitudinal)
Hot definition: vol > 0.70 AND 60d_return < -0.10
Lifetime classification: 100% agreement with L1 hot/cold split
  hot 15% (n=2275, 68.3% WR)
  cold 85% (n=12876, 53.4% WR)

## SURPRISE FINDING — Live data classification

April 2026 live Bear UP_TRI (74 signals):
  Hot: 32 signals (43%) — fired April 1-7, vol > 0.70 AND 60d < -0.10
  Cold: 42 signals (57%) — fired April 9-10, vol > 0.70 BUT 60d -0.07 to -0.09

The 42 "cold" signals are BORDERLINE — 60d_return JUST above the -0.10
threshold. Yet they printed:
  W=40, L=2, F=0 → 95.2% WR

The cold cascade Tier 1 (wk4 × swing_high=low) captured 0 of the 42
borderline-cold signals. Yet 95% won. The cold cascade was calibrated to
lifetime cold (53.4% baseline) but borderline-cold-with-Phase-5-selection-
bias is at 95%.

## Architectural questions

1. **Universal primary axis (vol_percentile) — is this correct?**
   Both Choppy and Bear use vol_percentile as primary. Should Bull?
   Or is vol_percentile actually a confound that masks regime-specific
   primaries?

2. **Secondary axis specificity — fundamental or convenient?**
   Choppy uses breadth (cross-section); Bear uses 60d_return
   (longitudinal). Are these capturing fundamentally different regime
   mechanics, or are they alternative coordinates over the same
   underlying market state?

3. **Bimodal vs tri-modal — what determines sub-regime count?**
   Choppy = 3 cells, Bear = 2 cells. Is this real (Bear genuinely
   bimodal) or an artifact of binary threshold choice?

4. **Borderline classification problem — how should we handle it?**
   The Bear detector produces "cold" for signals that behave like hot
   in live data. Options:
   (a) Add "warm" zone (vol > 0.70 AND -0.10 ≤ 60d ≤ 0)
   (b) Use confidence score to surface low-confidence boundary cases
   (c) Soften threshold to bands (e.g., 60d < -0.05 = hot probability 0.7)
   (d) Accept hard threshold and trust lifetime predictions over live

5. **Phase-5 selection bias — handle within detector or outside?**
   The 42 cold signals printed 95% WR partly because they were Phase-5
   winners. Should the detector have a "Phase-5 validated" override
   that suppresses the cold cascade for known-good patterns?

6. **Bull regime axes — what would you predict?**
   Vol_percentile + ??? for Bull. Symmetric inverse of Bear (high
   60d_return positive) or different axis entirely (sector dispersion,
   trend persistence)?

Format: markdown, ## sections per question. 3-4 short paragraphs each.
Be specific about trade-offs. Where you can recommend a concrete next
step, do."""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=4500)

    md = f"""# Bear vs Choppy Detector Architecture — Sonnet 4.5 Critique

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

{response}
"""
    OUTPUT_PATH.write_text(md)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
