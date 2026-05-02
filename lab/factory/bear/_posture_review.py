"""BS3 helper: Sonnet 4.5 critique of full Bear regime production posture."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_posture_review.md"


def main():
    summary = """
# Bear Regime Production Posture Summary

## Cell status (final, post-3-cell investigation)

| Cell | Status | Confidence | Production action |
|---|---|---|---|
| Bear UP_TRI | COMPLETE | HIGH | Shadow-deployment-ready with sub-regime gating |
| Bear DOWN_TRI | DEFERRED | LOW | kill_001 + provisional wk2/wk3 (default OFF) |
| Bear BULL_PROXY | DEFERRED | LOW | Provisional HOT-only (default OFF) |

## Sub-regime detector (Bear)

  hot:  vol_percentile > 0.70 AND nifty_60d_return < -0.10
  warm: vol > 0.70 AND -0.10 ≤ nifty_60d_return < 0
  cold: vol ≤ 0.70 OR nifty_60d_return ≥ 0

## Calibrated WR expectations table

| Sub-regime | UP_TRI | BULL_PROXY | DOWN_TRI |
|---|---|---|---|
| Hot | 65-75% (NOT live 94.6%) | 65-75% (NOT live 84.6%) | SKIP |
| Warm | TAKE_FULL (live evidence) | SKIP | SKIP |
| Cold | filter cascade ~63% | SKIP | provisional ~50-55% |

## KILL rules (universal, apply BEFORE sub-regime check)

- kill_001: Bank × Bear DOWN_TRI (already in production)
- vol_climax × Bear BULL_PROXY (new)
- December × Bear UP_TRI (-25pp lifetime)
- Health × Bear UP_TRI (lifetime hot 32.4%)

## Trader heuristics

- Repeat-name cap: same stock fires within 6 days → TAKE_SMALL
- Day-correlation cap: 3+ same-day signals → 80% sizing
- Max 5 concurrent Bear positions

## Known gaps (must close before live deployment)

GAP 1: Warm zone WR calibration is statistically dishonest (n=42 CI
       is 84-99%, not 70-90%). Recommendation: collapse warm to hot
       65-75% pending lifetime warm cohort accumulation.
GAP 2: Rule precedence ambiguity (Phase-5 vs Health × UP_TRI; cap
       stacking; max position cap)
GAP 3: Exit rules + stops not specified per sub-regime
GAP 4: Signal strength tiering within sub-regime missing
GAP 5: Performance monitoring + pause triggers missing
GAP 6: Warm zone boundary dead zone (60d_return near 0) undefined
GAP 7: Regime stability filter (3-day persistence requirement)

## Pre-deployment action list (15 items)

8 minimum for shadow mode; 6 more for live mode; 1 final shadow-mode
verification gate.
"""

    prompt = f"""You are doing the final review of the Bear regime
production posture document, before Wave 5 brain integration.

{summary}

## Critique requested

1. **Sub-regime gating defensibility.** Hot/warm/cold tri-modal with
   hard thresholds + 5% ambiguity filter. The trader has been operating
   at 94.6% live WR; production calibration is 65-75%. What's the
   strongest argument FOR this design? What breaks first?

2. **WR calibration honesty.** GAP 1 flags warm zone calibration as
   statistically dishonest. Production posture currently shows
   "TAKE_FULL (live evidence)" for warm. Should warm be displayed as
   65-75% (collapsed to hot) or 80-95% (trust the data)?

3. **Trader emotional preparation.** When live runs at 94.6% and
   production runs at 70%, what does the trader feel emotionally
   during the first 30-trade window? At what point does emotional
   reaction compound with regime misclassification to break the
   system?

4. **Failure mode prediction.** Sub-regime detector misclassifies
   (boundary whipsaw or warm/cold ambiguity). What's the most likely
   failure cascade? (E.g., trader sees 3 losses in a row, manually
   overrides to skip remaining signals, then misses the regime
   recovery.)

5. **Production deployment risk ranking.** Of the 7 known gaps, which
   3 are the highest priority to close before live deployment? Which
   can wait?

6. **Bull regime preparation adequacy.** Predicted Bull axes are
   trend_persistence × leadership_concentration. Plan is 6-9 sessions
   total. Is this adequate? Anything missing?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, ruthless, reference actual numbers above. Where you can
recommend a concrete next step, do."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bear Production Posture — Sonnet 4.5 Final Critique (BS3)\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
