"""BU4 follow-up: Sonnet 4.5 cross-regime synthesis after Bull UP_TRI."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "cross_regime_synthesis.md"


def main():
    prompt = """You are reviewing the cross-regime cell architecture
synthesis after completing Bull UP_TRI cell investigation.

## State of investigation (3 regimes, multiple cells)

CHOPPY regime (3 cells):
  • Choppy UP_TRI: F1 filter (ema_bull + coiled=medium); v2 sub-regime
    aware (tri-modal stress/balance/quiet)
  • Choppy DOWN_TRI: DEFERRED
  • Choppy BULL_PROXY: KILL (V3 confirmed at lifetime)

BEAR regime (3 cells):
  • Bear UP_TRI: HIGH confidence, lifetime-validated, sub-regime gated.
    Live 94.6% / lifetime 55.7% (gap +38.9pp from Phase 5 selection bias)
  • Bear DOWN_TRI: DEFERRED with provisional wk2/wk3 + Bank kill filter
  • Bear BULL_PROXY: DEFERRED with provisional HOT-only filter

BULL regime (1 of 3 cells):
  • Bull UP_TRI: PROVISIONAL_OFF. Lifetime-only (n=38,100, baseline 52.0%).
    Tri-modal sub-regime (recovery 2.6% / healthy 12.5% / normal 76.4% /
    late 7.1%). Best filter: recovery + vol=Med + fvg=low → 74.1% WR (n=390).
  • Bull DOWN_TRI: pending
  • Bull BULL_PROXY: pending

## Sub-regime detector design across regimes

| Regime | Primary axis | Secondary axis | Structure | Hot WR |
|---|---|---|---|---|
| Choppy | vol_percentile | market_breadth | tri-modal balanced | UP_TRI hot ~60% |
| Bear | vol_percentile | nifty_60d_return | tri-modal balanced | UP_TRI hot 68.3% |
| Bull | nifty_200d_return | market_breadth | tri-modal SKEWED | recovery 60.2% |

## Cross-regime architectural findings

1. **Sub-regime tri-modal structure is universal across all 3 regimes.**
   Bucket sizes vary: Choppy ~70% normal, Bear ~60%, Bull ~76%.
   Universal pattern: "two discriminative tails exist; bulk is baseline."

2. **Per-regime axes are different but related.**
   Choppy: state measures (vol percentile + breadth synchronicity)
   Bear: stress + capitulation (vol + 60d return)
   Bull: maturity + participation (200d return + breadth)
   Choppy uses real-time state; Bear and Bull use lookback returns.

3. **Direction-flip pattern (UP_TRI vs DOWN_TRI on regime anchor)
   confirmed in 2 of 3 regimes:**
   Bear: 60d=low UP_TRI +14.1pp vs DOWN_TRI -4.1pp
   Bull: 200d=high UP_TRI -2.1pp vs DOWN_TRI +1.5pp
   (Choppy direction-flip not yet tested)

4. **Cross-regime patterns DON'T transfer.**
   0/3 Bear UP_TRI top patterns qualify in Bull UP_TRI.
   Each cell needs its own filter design.
   The only universal-ish winner is wk4 calendar effect (Bear +7.5pp,
   Bull +2.6pp).

5. **Bull is architecturally distinct from Bear despite shared bullish
   direction.**
   - Bear UP_TRI loves compression (inside_bar=True +4.9pp)
   - Bull UP_TRI: NEUTRAL on inside_bar (no preference)
   - Bear UP_TRI hot is "vol=High + 60d=low" (capitulation reversal)
   - Bull UP_TRI hot is "low 200d + low breadth" (recovery breakout)
   - Different sectors lead in each regime

6. **Counterintuitive cells appear in 2 regimes:**
   Bear UP_TRI's "warm zone" (borderline cold sub-regime, live 95%)
   Bull UP_TRI's "recovery_bull" (low 200d + low breadth, 60.2%)
   Both involve regime classification during transitions where
   lagging indicators haven't caught up. May be a universal "transitional
   zone with quality leadership" pattern.

## Your task

Critique the cross-regime architecture findings and answer:

1. **Has the cross-regime meta-pattern proven valuable enough to use
   for Bull DOWN_TRI / Bull BULL_PROXY cell prediction?** What specific
   predictions can we make for Bull DOWN_TRI from the meta-pattern?

2. **Is "lifetime-only methodology" the right adaptation when live
   data is absent?** What's missing from the standard 5-step that
   could be salvaged or substituted?

3. **The "transitional zone with quality leadership" pattern** (Bear
   warm + Bull recovery_bull). Is this genuinely a universal phenomenon
   or two coincidences? How would we test if Choppy has an equivalent
   transitional cell?

4. **Production posture for PROVISIONAL_OFF cells.** When live data
   is absent, the calibrated WR equals lifetime baseline directly (no
   inflation to remove). But should we trust 74.1% lifetime expected
   WR as production WR, or should we still apply a "no-live-discount"
   (e.g., subtract 5pp for non-stationarity risk)?

5. **The wk4 calendar effect across regimes.** Bear UP_TRI +7.5pp,
   Bull UP_TRI +2.6pp, Choppy unclear. Is this real universal effect
   (institutional flow timing) or coincidence? Worth a dedicated
   cross-regime study?

6. **What's the minimum viable Bull regime cell coverage** to consider
   Bull regime "production-ready"? With Bull DOWN_TRI predicted DEFERRED
   and Bull BULL_PROXY untested, can we deploy Bull UP_TRI in production
   without the other 2 cells?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference actual numbers from above."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Cross-Regime Architecture Synthesis — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** post-Bull UP_TRI cell completion (BU4)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
