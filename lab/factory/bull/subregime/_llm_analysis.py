"""BU1 follow-up: Sonnet 4.5 cross-regime meta-pattern verdict."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "meta_pattern_verdict.md"


def main():
    prompt = """You are reviewing the cross-regime sub-regime
architecture meta-pattern after testing it on Bull regime data.

## Meta-pattern (from Bear synthesis BS1 LLM analysis)

> "Primary axis = regime definition, secondary axis = risk flavor"

| Regime | Primary axis | Secondary axis | Structure | Hot WR (lift) |
|---|---|---|---|---|
| Choppy | vol_percentile (chop) | breadth (sync vs rotation) | tri-modal | UP_TRI hot 60% (+8pp) |
| Bear | vol_percentile (panic vs grind) | nifty_60d_return (oversold vs capitulation) | tri-modal | UP_TRI hot 68% (+15pp) |
| Bull (predicted) | trend_persistence | leadership_concentration | predicted tri-modal | TBD |

## Bull regime test results (n=38,100 lifetime UP_TRI signals)

Tested 4 axis configurations:
1. **predicted_v1** (multi_tf_alignment × breadth): 12.7pp WR range
2. **predicted_v2** (nifty_200d_return × breadth): **15.1pp WR range — BEST**
3. alt_60d_breadth (60d_return × breadth): 13.3pp range
4. alt_vol_breadth (vol × breadth, Choppy-style): 9.7pp range

predicted_v2 chosen as final detector. Bull is tri-modal:

| Sub-regime | Definition | n | % | WR |
|---|---|---|---|---|
| recovery_bull | low 200d AND low breadth | 972 | 2.6% | **60.2%** (+8.2pp) ★ counterintuitive |
| healthy_bull | mid 200d AND high breadth | 4,764 | 12.5% | **58.4%** (+6.3pp) |
| normal_bull | (everything else) | 29,110 | 76.4% | 51.3% |
| late_bull | mid 200d AND low breadth | 2,699 | 7.1% | **45.1%** (−6.9pp) |

## Counterintuitive findings

1. **recovery_bull is the highest-WR cell** (60.2% on n=972). Definition:
   nifty_200d_return < 0.05 AND market_breadth_pct < 0.60. This is
   Bull regime classified AFTER long lookback still mildly negative,
   AND narrow leadership. Mechanically: stocks emerging from Bear
   first, quality leaders driving recovery, narrow breadth is
   feature-of-recovery not a bug.

2. **late_bull is the worst-WR cell** (45.1% on n=2,699). Definition:
   mid 200d AND low breadth. Classic "narrowing leadership topping"
   pattern.

3. **healthy_bull is the bulk-edge cell** (58.4% on n=4,764). Mid 200d
   AND broad breadth = sustained healthy Bull. This is what most
   traders intuitively call "Bull market".

## Architectural questions

1. **Meta-pattern verdict.** Predicted "trend_persistence × leadership_
   concentration" axes — were they correct? Or does the actual best
   axis (`nifty_200d_return_pct`) measure something different than
   "persistence"? What's the right way to characterize Bull's primary
   axis?

2. **Tri-modal but DIFFERENT structure.** Choppy and Bear are tri-
   modal with hot/balance/cold (or hot/warm/cold). Bull is tri-modal
   with recovery/healthy/late + dominant "normal" bucket. The
   structure shape differs. Is the tri-modal META-pattern still
   universal, or is it really just "extremes matter; 70%+ of regime
   is normal"?

3. **The recovery_bull surprise.** Counterintuitive cell (low 200d +
   narrow breadth = highest WR). Does this generalize to Bear's
   "warm zone" and Choppy's stress sub-regime as similar
   "transitional zones with quality leadership"? Or is recovery_bull
   genuinely Bull-specific?

4. **Production implications.** Bull UP_TRI in recovery_bull would
   produce ~60% WR, healthy_bull 58%, late_bull 45%. Most signals
   (76%) land in normal_bull (~51%, near baseline). For production
   filter design:
     a) Apply recovery + healthy as TAKE_FULL?
     b) SKIP late_bull explicitly?
     c) Cascade for normal_bull?

5. **Cross-cell predictions for Bull DOWN_TRI / BULL_PROXY.** Based
   on Bear's pattern (DOWN_TRI inverts UP_TRI's anchor), what should
   we expect for:
     a) Bull DOWN_TRI: contrarian short in Bull. Predicted weak
        edge; primary anchor inverts (high 200d should help DOWN_TRI?)
     b) Bull BULL_PROXY: support rejection in Bull. Should align with
        Bull UP_TRI direction; recovery_bull may be its sweet spot too.

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference the WR numbers, and where you can recommend a
concrete production filter, do."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4000)

    OUTPUT_PATH.write_text(
        f"# Bull Regime Meta-Pattern Verdict — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
