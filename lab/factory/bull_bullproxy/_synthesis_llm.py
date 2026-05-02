"""BP4 follow-up: Sonnet 4.5 cross-cell synthesis after Bull cell trio."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "cross_cell_synthesis.md"


def main():
    prompt = """You are reviewing the Bull regime cell trio after
completing all 3 cells investigation.

## Bull regime cell trio status

| Cell | Status | Lifetime baseline | Filter | Filter WR / lift |
|---|---|---|---|---|
| Bull UP_TRI | PROVISIONAL_OFF | 52.0% | recovery × vol=Med × fvg_low | 74.1% / +22pp (n=390) |
| Bull DOWN_TRI | PROVISIONAL_OFF | 43.4% | late × wk3 | 65.2% / +21.8pp (n=253) |
| Bull BULL_PROXY | PROVISIONAL_OFF | 51.1% | healthy × 20d=high | 62.5% / +11.4pp (n=128) |

All 3 cells lifetime-only methodology (0 live Bull signals).
All 3 PROVISIONAL_OFF default; manual enable available.

## Bull sub-regime structure (universal across Bull cells)

Built in BU1 with axes nifty_200d_return × market_breadth.
Tri-modal: recovery / healthy / normal / late.

Sub-regime distribution consistent across all 3 Bull cells:
  recovery_bull: 2.6-3.2%
  healthy_bull: 11.6-12.5%
  normal_bull: 73.0-76.4%
  late_bull: 7.1-10.8%

## Cross-cell findings within Bull regime

1. **Sub-regime PERFECT inversion** (UP_TRI vs DOWN_TRI):
   recovery_bull: UP_TRI 60.2% (best) vs DOWN_TRI 35.7% (worst)
   late_bull: UP_TRI 45.1% (worst) vs DOWN_TRI 53.0% (best)
   All 4 sub-regime cells flip cleanly.

2. **Sub-regime alignment** (UP_TRI vs BULL_PROXY):
   Both bullish cells share recovery > healthy > normal > late
   structure. 3/4 sub-regimes aligned.

3. **Calendar inversion within Bull**:
   UP_TRI:    wk4 +2.6pp WIN; wk3 -3.3pp anti
   BULL_PROXY: wk4 +13.7pp WIN; wk3 -10.7pp anti
   DOWN_TRI:  wk4 -5.6pp anti; wk3 +8.4pp WIN

4. **Universal Bull bullish-cell anchor**: nifty_20d_return=high
   wins for both UP_TRI (+5-8pp) and BULL_PROXY (+5.8pp); inverts
   for DOWN_TRI (-1.6pp).

5. **vol_climax × BULL_PROXY anti is UNIVERSAL across regimes**
   (Bear -11.0pp, Bull -4.4pp). Same direction; capitulation
   breaks support.

6. **52w_high_distance INVERTS across Bear vs Bull BULL_PROXY**:
   Bear: high WINNER (+14.4pp; far from highs = beaten down)
   Bull: low WINNER (+8.0pp; near highs = breakout-of-resistance)

## Cross-regime context (now 9 cells across 3 regimes)

| Regime | Cells investigated | High-confidence | DEFERRED/PROVISIONAL_OFF | Sub-regime axes |
|---|---|---|---|---|
| Choppy | 3 | 1 (UP_TRI v2) | 2 | vol × breadth |
| Bear | 3 | 1 (UP_TRI v3, shadow-deploy-ready) | 2 | vol × 60d_return |
| Bull | 3 | 0 (all PROVISIONAL_OFF) | 3 | 200d × breadth |

Bear UP_TRI is the only cell with live data validation.
Bull cells await Bull regime return.

## Your task — Bull regime cell trio synthesis

1. **Unified Bull regime architectural pattern.** With all 3 Bull
   cells investigated, what's the trader-narrative for "Bull regime
   trading"? How does Bull regime trade differently from Bear/Choppy
   in operational terms?

2. **Why Bull bullish cells (UP_TRI + BULL_PROXY) share architecture
   but Bear bullish cells (UP_TRI + BULL_PROXY) don't.**
   Bear UP_TRI prefers compression (inside_bar=True); Bear BULL_PROXY
   prefers range expansion. Bull UP_TRI is neutral; Bull BULL_PROXY
   is also neutral. Why does Bear show within-direction divergence
   but Bull shows alignment?

3. **Production deployment for Bull regime when it returns.**
   When Bull regime classifies live for ≥10 days, what's the
   activation playbook for Bull cells? Order of operations for
   activating Bull UP_TRI (recovery × vol=Med × fvg=low) vs Bull
   DOWN_TRI (late × wk3) vs Bull BULL_PROXY (healthy × 20d=high)?

4. **The 4-cell sub-regime PERFECT inversion** (Bull UP_TRI vs Bull
   DOWN_TRI) is the strongest cross-cell finding in the Lab.
   Universal pattern (should hold for Choppy and Bear DOWN_TRI vs
   UP_TRI too)? Worth dedicated cross-regime test?

5. **`52w_high_distance` REGIME-INVERSION** for BULL_PROXY (Bear
   far-from-highs; Bull near-highs). What does this say about the
   different mechanisms BULL_PROXY captures per regime? Does this
   generalize to other features that might invert across regimes?

6. **Cross-regime synthesis preview.** With 9 cells across 3 regimes,
   what are the 3-5 universal patterns vs 3-5 regime-specific
   patterns? Frame this as the foundation for the cross-regime
   synthesis that will follow.

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference actual numbers from above."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bull Cell Trio Cross-Cell Synthesis — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** post-Bull BULL_PROXY cell completion (BP4)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
