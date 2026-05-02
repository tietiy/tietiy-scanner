"""BS1 helper: Sonnet 4.5 cross-cell architectural analysis."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "synthesis_llm_analysis.md"


def main():
    prompt = """You are reviewing the synthesis of a 3-cell investigation
in Bear regime trading. The cells are:

• Bear UP_TRI (ascending triangle breakout in Bear): COMPLETE 3 sessions,
  HIGH confidence, lifetime-validated, sub-regime gated.
  Live 94.6% WR / lifetime 55.7% (gap +38.9pp).
  Sub-regime: tri-modal (hot 15% / warm / cold 85%).

• Bear DOWN_TRI (descending triangle breakdown in Bear): DEFERRED with
  provisional filter. 0 Phase 5 winners; 19 WATCH combos.
  Live 18.2% WR / lifetime 46.1% (gap -28pp INVERTED).
  Provisional filter: kill_001 (Bank exclusion) + wk2/wk3 timing.

• Bear BULL_PROXY (support rejection in Bear): DEFERRED with
  provisional HOT-only filter. ZERO Phase 5 combinations at all.
  Live 84.6% WR / lifetime 47.3% (gap +37.3pp).
  Provisional filter: HOT sub-regime only.

## Cross-cell feature behavior matrix (lifetime data)

| Feature | UP_TRI | DOWN_TRI | BULL_PROXY |
|---|---|---|---|
| nifty_60d_return_pct=low | +14.1pp WIN | −4.1pp ANTI | +17.9pp WIN |
| day_of_month_bucket=wk4 | +7.5pp WIN | −17.5pp ANTI | +2.3pp (mild) |
| day_of_month_bucket=wk2 | −6.4pp anti | +15.0pp WIN | −5.5pp anti |
| inside_bar_flag=True | +4.9pp (compression) | n/a | −9.4pp (range expansion) |
| vol_climax_flag=True | n/a | n/a | −11.0pp ANTI |
| nifty_vol_regime=Low | n/a | n/a | +7.9pp WIN (U-shape) |
| 52w_high_distance_pct=high | +6.6pp | n/a | +14.4pp WIN |

## Architectural patterns identified

1. Bullish vs bearish direction is the primary divider
2. Within bullish: compression (UP_TRI) vs range expansion (BULL_PROXY)
3. Calendar inversion: bullish prefers wk4; bearish prefers wk2
4. Hot Bear sub-regime favors LONG positions (UP_TRI/BULL_PROXY); not DOWN_TRI
5. vol_climax kills BULL_PROXY (breaks support) but not UP_TRI (triangle absorbs)

## Live-vs-lifetime gap pattern

- Bullish cells INFLATE (UP_TRI +38.9pp, BULL_PROXY +37.3pp) — Phase 5
  selection bias + sub-regime tailwind
- Bearish DOWN_TRI DEFLATES (-28pp) — no Phase 5 winners, current
  sub-regime hostile to short setups

## Sub-regime structure

Bear sub-regime detector built (vol > 0.70 AND nifty_60d_return < -0.10
= hot). Reused across UP_TRI (S2) and BULL_PROXY (P1) cleanly.
DOWN_TRI doesn't follow same axes (calendar-driven instead).

## Your task

5 questions, each requires 3-4 short paragraphs:

1. **Is the directional asymmetry (long works, short doesn't in Bear)
   typical of all Bear regimes or specific to current sub-regime?**
   This matters for production calibration: should we expect Bear
   DOWN_TRI to remain hostile or recover when sub-regime shifts?
   Reference established market microstructure or empirical evidence.

2. **Architectural pattern across cells: 'same feature, opposite
   directions across cells'.** UP_TRI compression vs BULL_PROXY
   expansion on inside_bar_flag is one example. Is this a feature
   of the Bear regime specifically, or is this how trading edge
   ALWAYS works across mechanism-distinct cells? Predict whether
   Bull regime will show similar same-feature-opposite-direction
   behavior.

3. **Phase 5 thinness as a methodology limit.** 2 of 3 Bear cells
   couldn't run standard methodology (DOWN_TRI: 19 WATCH/no winners;
   BULL_PROXY: 0 combos). Is this a Phase 4 walk-forward issue (filter
   too strict?), a fundamental thinness of these cells, or something
   else? What should change in the Lab pipeline before Bull regime
   work?

4. **Bear vs Choppy comparison.** Choppy is tri-modal on vol × breadth
   axes. Bear is tri-modal on vol × 60d_return axes. Same architecture
   (tri-modal regime), different secondary axis. Bull regime predicted
   to use trend_persistence × leadership_concentration. Is the
   per-regime sub-regime detector approach correct, or is there a
   universal axis hiding in here that we're missing?

5. **Production deployment risk.** When trader's Bear UP_TRI live WR
   has been 94.6% and production WR drops to calibrated 65-75%, what's
   the most likely failure mode? How does the trader's emotional
   response to the WR shift compound with technical sub-regime
   misclassification? What's the early warning signal that should
   pause production?

Format: markdown, ## sections per question, 3-4 paragraphs each.
Be specific, ruthless, and reference the actual feature data above
where applicable."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bear Regime Synthesis — Sonnet 4.5 Cross-Cell Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Companion:** [`synthesis.md`](synthesis.md)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
