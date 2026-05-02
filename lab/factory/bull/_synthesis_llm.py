"""LS1 helper: Sonnet 4.5 cross-cell synthesis after Bull cell trio."""
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
in Bull regime trading (Indian NSE F&O equity scanner).

## Bull regime cell trio status

| Cell | Status | Lifetime baseline | Provisional filter | Filter WR / lift |
|---|---|---|---|---|
| Bull UP_TRI | PROVISIONAL_OFF | 52.0% | recovery × vol=Med × fvg_low | 74.1% / +22pp (n=390) |
| Bull DOWN_TRI | PROVISIONAL_OFF | 43.4% | late × wk3 | 65.2% / +21.8pp (n=253) |
| Bull BULL_PROXY | PROVISIONAL_OFF | 51.1% | healthy × 20d=high | 62.5% / +11.4pp (n=128) |

All 3 cells: lifetime-only methodology (0 live Bull signals during
current operational window). All PROVISIONAL_OFF default.

## STRONGEST architectural finding: sub-regime PERFECT inversion

Bull's 4 sub-regime cells flip cleanly between UP_TRI and DOWN_TRI:

| Sub-regime | Bull UP_TRI WR | Bull DOWN_TRI WR |
|---|---|---|
| recovery_bull | 60.2% (best) | 35.7% (worst) |
| healthy_bull | 58.4% | 40.5% |
| normal_bull | 51.3% | 42.6% |
| late_bull | 45.1% (worst) | 53.0% (best) |

UP_TRI's BEST cell is DOWN_TRI's WORST. UP_TRI's WORST is DOWN_TRI's
BEST. All 4 cells flip cleanly. This is the strongest cross-cell
architectural finding in the Lab.

## Cross-cell findings

1. Sub-regime axes: nifty_200d_return × market_breadth (different from
   Bear's vol × 60d_return; different from Choppy's vol × breadth)
2. Direction-alignment between bullish cells (UP_TRI + BULL_PROXY both
   prefer recovery > healthy > normal > late)
3. Calendar inversion: bullish cells prefer wk4 (+13.7pp BULL_PROXY,
   +2.6pp UP_TRI); bearish DOWN_TRI prefers wk3 (+8.4pp)
4. Universal vol_climax × BULL_PROXY anti (Bear -11pp, Bull -4.4pp)
5. 0/3 Bear UP_TRI top patterns qualify in Bull UP_TRI (architecturally
   distinct despite shared signal type)
6. recovery_bull is "transitional quality" cell — analog to Bear's
   "warm" zone (low 200d + low breadth = early-cycle quality leadership
   concentration)

## Cross-regime context (now 9 cells across 3 regimes)

| Regime | Sub-regime axes | Bullish baseline | Bearish baseline |
|---|---|---|---|
| Choppy | vol × breadth | UP_TRI 52.3% | DOWN_TRI 46.1% |
| Bear | vol × 60d_return | UP_TRI 55.7%, BULL_PROXY 47.3% | DOWN_TRI 46.1% |
| Bull | 200d_return × breadth | UP_TRI 52.0%, BULL_PROXY 51.1% | DOWN_TRI 43.4% |

DOWN_TRI is below 50% baseline in Bear (46.1%) and Bull (43.4%).
Universal contrarian-short hostility outside narrow exhaustion zones.

## Bull production scanner verification

Separate verification session (NOT a cell investigation) confirmed Bull
pipeline works end-to-end: regime classifier outputs Bull, signal
generators fire, scoring assigns Bull-specific scores. 0 bugs. 0
blockers. All 10 verification checks passed across 2 historical Bull
windows (2021-08, 2023-06).

## Your task

5 architectural questions, 3-4 short paragraphs each:

1. **Trader mental model for Bull regime trading.** When Bull regime
   activates live (after months of Bear/Choppy), how is Bull-trading
   psychologically different from Bear-trading? The Bear UP_TRI cell
   produced 94.6% live WR; Bull UP_TRI calibrated 60-74% on best
   filter. The trader has been trained on Bear's 94% — what's the
   right framing for Bull's 65% production reality?

2. **Lifetime-only methodology limitations.** All 3 Bull cells closed
   PROVISIONAL_OFF without live validation. What CANNOT be known about
   Bull cells until live data accumulates? Be specific about which
   Lab findings might fail to replicate live (which provisional filters
   are most fragile?).

3. **Cross-regime universal patterns confirmed.** Three universals
   identified: tri-modal sub-regime structure (3/3 regimes),
   vol_climax × BULL_PROXY anti (2/3 regimes), bullish-cell
   direction-alignment (UP_TRI + BULL_PROXY same sub-regime preferences
   in 2/2 regimes tested). Are these robust enough to use as production
   architectural principles? Or are they artifact patterns?

4. **The "recovery_bull as transitional quality" cell** — analogous to
   Bear's "warm" zone. Is this a genuine universal pattern (every
   regime has a transitional quality sub-regime) or coincidence? Worth
   dedicated cross-regime test? What would the test look like?

5. **Production deployment for Bull regime when it returns** — given
   all 3 cells are PROVISIONAL_OFF and need 30+ live signals + 50%
   match-WR to upgrade. What's the activation playbook for Bull cells?
   Order of operations: which cell activates first, how is sub-regime
   detector deployed, what's the trader experience on Day 1 of live
   Bull?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference the actual numbers above, and where you can
recommend a concrete next step, do."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bull Regime Synthesis — Sonnet 4.5 Cross-Cell Analysis\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Companion:** [`synthesis.md`](synthesis.md)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
