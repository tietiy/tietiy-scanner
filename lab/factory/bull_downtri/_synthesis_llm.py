"""BD4 follow-up: Sonnet 4.5 cross-cell synthesis after Bull DOWN_TRI."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "cross_cell_synthesis.md"


def main():
    prompt = """You are reviewing the cross-cell synthesis after
completing Bull DOWN_TRI cell investigation.

## Both DOWN_TRI cells now investigated

### Bear DOWN_TRI (DEFERRED with provisional filter)
- Live: n=11, 2W/9L = 18.2% WR (catastrophic in current sub-regime)
- Lifetime: n=3,640, 46.1% baseline
- 0 Phase 5 winners (all 19 combos WATCH)
- Provisional filter: kill_001 (Bank) + wk2/wk3 timing → 53.6% WR
  on n=1,446 (+7.5pp lift)
- Live-vs-lifetime gap: -28pp (DEFLATED — opposite of bullish cells)

### Bull DOWN_TRI (PROVISIONAL_OFF with provisional filter)
- Live: n=0 (Bull regime not active during current period)
- Lifetime: n=10,024, 43.4% baseline
- Provisional filter: late_bull × wk3 → 65.2% WR on n=253 (+21.8pp lift)
- 4 sub-regime PERFECT INVERSION between Bull UP_TRI and Bull DOWN_TRI
  (recovery 60.2%/35.7%, healthy 58.4%/40.5%, normal 51.3%/42.6%,
   late 45.1%/53.0%)
- Calendar inversion confirmed (wk3 +8.4pp DOWN_TRI; wk4 +2.6pp UP_TRI)

## Cross-regime DOWN_TRI architectural pattern

Universal observations:
1. Both DOWN_TRI cells lifetime baseline BELOW 50% (43.4% / 46.1%)
2. Both cells DEFERRED — neither produces a deployable filter from
   live data alone
3. Both have provisional sub-regime-gated filters with positive lift
4. Both rely on calendar effects (Bear: wk2; Bull: wk3) for primary
   timing edge
5. Both have hostile sectors that should be excluded
6. The cells that produce positive WR for DOWN_TRI are the EXACT
   inversions of cells that produce positive WR for UP_TRI:
     • Bear UP_TRI hot (capitulation reversal) → Bear DOWN_TRI hostile
     • Bull UP_TRI recovery (early-cycle quality) → Bull DOWN_TRI hostile
     • Bull UP_TRI late_bull (topping) → Bull DOWN_TRI BEST CELL

## Architectural questions

1. **"Contrarian short fundamentally harder than long across all
   regimes"** — true based on the data?
   - Bear DOWN_TRI live: 18.2% (with-direction but losing to
     bear-rallies)
   - Bull DOWN_TRI lifetime: 43.4% (counter-direction;
     structurally <50%)

   Is this a market-microstructure truth (institutional bias toward
   long; short squeezes; index drift up over time) or just a sample
   artifact?

2. **Sub-regime perfect inversion** (Bull UP_TRI vs Bull DOWN_TRI all
   4 cells flip). Is this a generalizable pattern that should hold in
   Choppy regime too? What's the simplest test?

3. **Calendar inversion across regimes** (Bear wk2/wk4; Bull wk3/wk4).
   Both bullish setups prefer wk4. Bearish setups prefer mid-month
   (wk2 in Bear; wk3 in Bull). What institutional flow mechanism
   explains the regime-specific mid-month preference?

4. **Provisional filter precision tradeoff:**
   - Bear DOWN_TRI: +7.5pp lift on n=1,446 (broad, low precision)
   - Bull DOWN_TRI: +21.8pp lift on n=253 (narrow, high precision)
   What's the right production posture for each? Different default
   sizing per cell?

5. **Both cells rely on sub-regime gating to find positive WR.**
   The architectural truth: DOWN_TRI is NOT a universal short signal
   but a "narrow-sub-regime exhaustion bet". Should this change how
   we communicate the cell to traders — frame as exhaustion-bet
   rather than as a "short setup"?

6. **Production deployment for both DOWN_TRI cells when their regimes
   return.** What's the activation criteria + minimum live n for
   upgrading PROVISIONAL → CANDIDATE → VALIDATED?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific about the actual numbers."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4000)

    OUTPUT_PATH.write_text(
        f"# Cross-Cell DOWN_TRI Synthesis — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** post-Bull DOWN_TRI cell completion (BD4)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
