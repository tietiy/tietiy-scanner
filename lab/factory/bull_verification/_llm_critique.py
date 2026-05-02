"""V4 follow-up: Sonnet 4.5 critique of Bull pipeline verification."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "bull_verification_critique.md"


def main():
    prompt = """You are doing the final architectural critique of the
Bull production scanner verification (TIE TIY trading system, Indian
NSE F&O equity scanner, runs daily on yfinance data).

## Verification context

Bull regime hasn't been the active regime during the scanner's
operational period (April 2026 onwards). All 3 Bull cell investigations
in the Lab were lifetime-only methodology because no live Bull data
exists. This verification session tested: does the Bull pipeline work
functionally if it activates live tomorrow?

## Method

Replay 2 historical Bull windows through unmodified production functions:
  • 2021-08-02 → 2021-08-13 (5 days, post-COVID rally)
  • 2023-06-12 → 2023-06-23 (5 days, broad uptrend)

For each day:
  • Fetch NIFTY data ending that date; run regime classifier logic
    (replicated inline from main.py:get_nifty_info)
  • Fetch each of 60 sample stocks (188 universe stratified by sector)
  • Invoke production scanner_core.detect_signals() unchanged
  • Invoke production scorer.enrich_signal() unchanged

## Verification results (all 10 checks passed)

| Check | Primary 2021-08 | Secondary 2023-06 |
|-------|----------------|-------------------|
| Regime classifier outputs Bull | ✓ 5/5 | ✓ 5/5 |
| Days with signals | ✓ 5/5 | ✓ 5/5 |
| Signal counts sane | ✓ avg 14/day | ✓ avg 8.4/day |
| Signal types observed | ✓ all 3 (UP_TRI/DOWN_TRI/BULL_PROXY) | ⚠ 2/3 (no BULL_PROXY) |
| Scoring errors | ✓ 0 | ✓ 0 |

70 + 42 = 112 total signals generated. Spot-checked 10 for correctness.
Scoring math verified manually. Sector ranking consistent with Lab's
Bull UP_TRI cell findings (IT, Health, Pharma, CapGoods all firing).

## Documented gaps (not blocking)

1. NO Bull-specific boost_patterns in mini_scanner_rules.json (all 7
   entries are regime=Bear; expected since no Bull live data to
   populate from)

2. target_price=None on all Bull signals (production design: only
   UP_TRI×Bear gets Target2x; everything else is Day6 exit; same
   behavior for Choppy)

3. Lab built Bull sub-regime detector
   (recovery/healthy/normal/late per nifty_200d × breadth) but
   production scanner has no sub-regime detection layer (Wave 5 brain
   integration item)

## What verification CANNOT catch

- Bugs only manifesting in future data conditions different from
  historical Bull
- Performance issues (functional verification only)
- Integration issues with Telegram/PWA downstream layers
- Concurrent/race-condition issues (single-threaded replay)
- State-mutation bugs (each replay day was independent; production
  uses persistent signal_history.json state)

## Sample signals (spot-check)

Primary window (2021-08-05): LALPATHLAB UP_TRI age=0
  pivot ₹1658 → entry ₹1978 (+19% above pivot, valid breakout)
  stop ₹1612 (below pivot)
  score 6 = Age0(3) + Bull(2) + Vol(1)
  action DEPLOY

Secondary window (2023-06-21): IPCALAB DOWN_TRI age=0
  pivot ₹761 → entry ₹737 (below pivot, valid breakdown)
  stop ₹779 (above pivot)
  score 7 = Age0(3) + DownAll(2) + Vol(1) + SecLead(1)
  action DEPLOY

All scoring math correct. All trigger conditions correct.

## Your task — critique

1. **Hidden gaps in Bull handling that this verification didn't catch.**
   What's NOT verified that should be? Be specific about additional
   tests.

2. **Architectural concerns about Bull readiness.** Are there
   non-obvious risks in activating Bull live deployment? What could
   surface unexpectedly?

3. **The "live data inflates production WR" problem from Lab's Bear
   UP_TRI cell.** Bear UP_TRI showed +38.9pp live-vs-lifetime gap
   (94.6% live / 55.7% lifetime). If Bull regime activates and
   immediately hits Phase-5-equivalent selection bias, will Bull
   live signals look impossibly good (90%+ WR) for a few weeks
   before mean-reverting? Should the trader be warned?

4. **What's the right "first Bull day" trader experience?** Bull
   regime activates after months of Bear/Choppy. Trader sees Bull
   signals in Telegram for the first time. What should the system
   communicate to manage expectations?

5. **The "no BULL_PROXY in 2023-06 secondary window" finding** —
   real (low-vol Bull doesn't generate BULL_PROXY) or weakness in
   verification (only 5 days, only 60 stocks)?

6. **Pre-activation checklist.** Given verification passes but
   gaps exist, what's the minimal pre-activation checklist before
   Bull regime can run with full production confidence?

Format: markdown, ## sections per question. 3-5 short paragraphs each.
Be specific, ruthless, and where you can recommend a concrete action,
do."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bull Verification — Sonnet 4.5 Architectural Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** post-V3 replay verification (10/10 checks passed)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
