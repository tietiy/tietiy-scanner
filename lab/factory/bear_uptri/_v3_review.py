"""S3 final review: Sonnet 4.5 critique of playbook v3 + production posture."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_v3_review.md"


def main():
    # Build a compact summary for the prompt
    posture_summary = """
# Bear UP_TRI v3 — Production Posture Summary

## Sub-regime gating (TRI-modal)
- hot:  vol > 0.70 AND 60d_return < -0.10  (15% lifetime, 68.3% WR)
- warm: vol > 0.70 AND -0.10 ≤ 60d_return < 0  (NEW; live 95.2% on n=42)
- cold: vol ≤ 0.70 OR 60d_return ≥ 0  (85% lifetime, 53.4% WR)

## Per sub-regime action
- hot/warm: TAKE_FULL on signals (with day/name correlation caps)
- cold + Tier 1 (wk4 × swing_high=low): TAKE_FULL (61.4% lifetime)
- cold no Tier 1: SKIP

## Mismatch rules (universal)
- AVOID Health UP_TRI in Bear (lifetime hot 32.4%)
- AVOID December (-25pp lifetime)

## Phase-5 hierarchy override
Phase-5 validated signals execute regardless of sub-regime; sub-regime
informs sizing/stops only. Detector outputs are unconditional priors.

## Calibrated WR expectations (NOT live 94.6%)
- hot: 65-75% (lifetime 68.3% + some Phase-5 bias)
- warm: 70-90% (single-window n=42; lifetime untested)
- cold + Tier 1: 58-65%
- cold no match: SKIP (~50%)

## Risk management
- Max 5 concurrent Bear UP_TRI positions
- Day-correlation cap: 80% sizing if 3+ signals same day
- Repeat-name cap: TAKE_SMALL if same stock fires within 6 days

## Trader emotional preparation
At 70% production WR (vs 94.6% live), expect:
- 2-loss streaks: ~9% of streaks (vs 0.3% at 94%)
- 3-loss streaks: ~2.7% (vs <0.1% at 94%)
- 3-4 consecutive losing trades will be normal
"""

    prompt = f"""You are doing the final review of Bear UP_TRI cell v3
production posture, before Wave 5 brain integration.

{posture_summary}

## Critique requested

1. **Are the sub-regime gating rules defensible?**
   Hot/warm/cold tri-modal structure with hard thresholds. Concrete
   trade-offs. What's the strongest argument FOR this design? What's
   the strongest argument AGAINST?

2. **Is the WR calibration honest?**
   Calibrated expectation: 65-75% in hot Bear UP_TRI, vs live 94.6%.
   Is this calibration too conservative, too aggressive, or right?
   What evidence would change your view?

3. **Edge cases that might break in production?**
   3-5 specific scenarios where v3 logic produces wrong action.

4. **Trader emotional preparation — what should they actually expect?**
   When 30 trades go from 28W/2L (94% WR window) to 21W/9L (70% WR
   window), what does that feel like emotionally? Concrete behavioral
   guidance.

5. **What's missing or under-specified?**
   Production posture has gaps. Name 2-3 most important.

Format: markdown, ## sections per question. 3-4 paragraphs each.
Be specific and ruthless — this is final review before deployment."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    print("  calling Sonnet 4.5 for v3 final review...")
    response = client.synthesize_findings(prompt, max_tokens=3500)
    OUTPUT_PATH.write_text(
        f"# Bear UP_TRI v3 Final Review — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
