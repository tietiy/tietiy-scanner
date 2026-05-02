"""S6 — Sonnet 4.5 critique of Step 1 Bull verification critique resolution."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_llm_critique.md"


def main():
    summary = """
# Step 1: Bull Verification Critique Resolution

## Context

Sonnet 4.5's V4 critique of Bull pipeline verification flagged 5
untested scenarios. Step 1 of Bull production-prep plan investigated
each to honest verdict (RESOLVED / GAP_DOCUMENTED / DEFERRED_TO_LIVE).
Documentation only — no scanner code changes.

## Verdict matrix

| # | Scenario | Verdict |
|---|---|---|
| S1 | State persistence Bear→Bull transition | RESOLVED |
| S2 | Volume filter absence case | RESOLVED w/ minor gap |
| S3 | Sector rotation edge cases | GAP_DOCUMENTED |
| S4 | Classifier jitter at boundaries | GAP_DOCUMENTED |
| S5 | BULL_PROXY first-Bull-day | RESOLVED |

3 RESOLVED, 2 GAP_DOCUMENTED, 0 DEFERRED_TO_LIVE.

## Synthesized findings

### S1 — Bear→Bull transitions structurally safe
Production classifier mathematics prevents direct Bear↔Bull single-day
transitions (slope can't flip ±0.01 in 1 bar). Empirically: 0 direct
in 12yr NIFTY. All transitions go through ≥30-day Choppy buffer
(detection age max 3 bars → all Bear-tagged context flushed).
Stateless-per-scan + fire-time regime tag = no state contamination.

### S2 — No hard volume filter exists
get_vol_rs() computes vol_q (High/Average/Thin) and vol_confirm tags
ONLY. Never gates emission. All signal types fire independent of
volume. Sonnet's "filter dropping legitimate breakouts" concern empty.

Soft scoring asymmetry: +1 vol_confirm bonus calibrated for Bear
(+6pp WR lift) but applied uniformly in Bull (+2pp WR lift). 62% of
Bull replay signals had vol_confirm=False, with 10% DEPLOY rate vs
63% for vol_confirm=True. Score-tier impact, not signal-emission.

### S3 — Sector rotation 3 calibration gaps
1. First-Bull-day stale ranking: 1-month sector_momentum window covers
   prior Bear/Choppy regime
2. Leadership inflation in broad Bull: 2023-06-15 had 7/8 sectors all
   "Leading" (+2% threshold); SecLead+1 bonus near-universal
3. Lab "SKIP Energy × Bull UP_TRI" (-2.9pp) NOT in production rules;
   Energy fired 12/112 (10.7%) of replay signals — most of any sector

### S4 — Classifier jitter quantified
- 17 single-day jitter (X-Y-X) in 12yr (~1.4/yr)
- 13 two-day jitter (X-Y-Y-X) (~1.1/yr)
- 21.6% of days within ±1% of EMA50 (boundary-grazing)
- 19.7% with |slope| in 0.003-0.007
- 0 direct Bull↔Bear jitters (consistent with S1)
- Worst-case: ~0.5-1 UP_TRI/yr demoted DEPLOY→WATCH on jitter Choppy
- Existing 10-day Bull activation gate already mitigates Day-1 risk

### S5 — BULL_PROXY first-day flood structurally impossible
5-condition conjunction gate (above own EMA50, near support, bullish
reversal candle, age≤1, valid stop). Per-stock EMA50 lag: most stocks
not BULL_PROXY-eligible on NIFTY Day-1 of Bull.
- Lifetime: 1.8/day across 188-stock universe
- V3 replay: 0.67% per stock-day, all WATCH bucket score 3-5
- First-Bull-day cohort = recovery_bull (highest WR sub-regime, 57.4%)

## Cross-scenario patterns

1. **Stateless-per-scan absorbs regime-transition concerns** (S1, S5):
   no carry-forward state from prior scan days; aging within today's
   df only; signal_history regime tag is fire-time stamp.

2. **Lab cell findings ≠ production scoring rules** (S3, S5):
   - Energy × Bull UP_TRI = SKIP NOT in rules
   - vol_climax × BULL_PROXY = REJECT NOT in rules
   - 0 Bull boost_patterns vs 7 Bear boost_patterns
   - Maps to PRODUCTION_POSTURE Gap 1

3. **Sub-regime detector gap blocks highest-impact filters** (S2, S3, S5):
   recovery_bull × vol=Med × fvg_low (74.1% WR) requires Gap 2 ship.

## Production-prep deliverables

### MUST DO before Bull activation (3)
1. Ship Bull rules to mini_scanner_rules.json (kill: Energy×Bull_UPTRI,
   vol_climax×BULL_PROXY; boost_patterns from cell playbooks)
2. First-Bull-day briefing: sector lag 15d, classifier jitter +
   10-day gate, BULL_PROXY rarity expectations
3. Sub-regime detector integration: 200d_return_pct +
   market_breadth_pct features → recovery/healthy/normal/late
   classification → cell-specific boost rules

### NICE TO HAVE post-activation (4)
4. Regime-aware vol_confirm scoring (Bear +1, Bull +0.5)
5. Breadth-adjusted SecLead (top-3 by 1m return vs absolute >+2%)
6. Classifier hysteresis (2-day confirmation before regime flip)
7. regime_confidence field in Telegram digest

## Honest limitations
1. No first-Bull-day live data exists. All conclusions inferred from
   classifier replay + Lab lifetime data + code inspection.
2. V3 replay used mid-Bull windows (2021-08, 2023-06), not first-day.
3. Sub-regime first-day classification is theoretical (Gap 2 not shipped).
4. Lab WR is lifetime; live inflation/compression unknown for Bull.
"""

    prompt = f"""You are doing the final critical review of Step 1 of
the Bull regime production-prep plan: investigation of 5 untested
scenarios from the prior V4 critique you wrote (Sonnet 4.5 yourself,
on 2026-05-03 same day). Step 1 was documentation-only with no scanner
code changes; 6 atomic commits.

{summary}

## Critique requested

1. **Verdict honesty.** 3 of 5 scenarios marked RESOLVED. Are these
   truly resolved or does the resolution depend on assumptions that
   could fail in live conditions? Specifically:
   - S1: "structurally impossible at daily level" — what if NIFTY has
     a >5% single-day move in unprecedented conditions? Does the
     argument still hold?
   - S5: "structurally low firing rate" — relies on per-stock EMA50
     lag. Could a coordinated news event override this lag (e.g.,
     Modi government stimulus → 50+ stocks all gap up above EMA50
     simultaneously)?
   - S2: "no hard filter exists" — is the soft scoring asymmetry
     understated? +1 bonus moving from score 5 to 6 IS DEPLOY/WATCH
     boundary; ~0.5x of Bull signals affected.

2. **Gap completeness.** Step 1 surfaced 1 new pre-activation item
   (vol_climax × BULL_PROXY kill rule). Are there gaps Step 1 missed
   that should have been flagged? Specifically: did the 5-scenario
   framing miss something a 6th scenario would have caught?

3. **Pre-activation prioritization.** Step 1 lists 3 MUST DO items.
   Of those 3, which is the highest-impact and which can be partially
   delivered (e.g., ship Energy×Bull_UPTRI kill rule today, defer
   boost_patterns until live data refines the WR estimates)?

4. **Step 2 readiness.** Step 1 declares Step 2 "unblocked." Given
   the 3 pre-activation MUST DOs are not yet shipped, is Step 2
   genuinely unblocked or should Step 2 wait for the rules-file work
   to land first?

5. **Cross-cell pattern: "Lab findings ≠ production rules" (Pattern 2).**
   This is now confirmed across 3 of 9 cells (Bull UP_TRI, Bull
   BULL_PROXY, plus the 2014-2026 Bear DOWN_TRI sector findings).
   Should this pattern trigger a dedicated workflow item to systematically
   port ALL Lab cell findings into mini_scanner_rules.json before any
   regime activation, rather than per-regime ad-hoc?

6. **Honest limitations.** Step 1 lists 4 limitations. The strongest
   is #1 (no live first-Bull-day data). Should the team plan a
   dedicated "first-Bull-day fire drill" exercise (paper-trade Day 1
   live, no real positions) before activating Bull cells with capital?
   Or is this overengineering?

7. **Atomic commit hygiene.** Step 1 produced 6 commits (S1-S5 +
   summary). The SUMMARY commit will be 7th. Is this commit count
   appropriate or excessive for the scope of work?

Format: markdown, ## sections per question. 3-5 short paragraphs each.
Be specific, ruthless, and where you can recommend a concrete action
or call something out as overconfident, do.
"""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Step 1 Bull Verification Critique Resolution — Sonnet 4.5 LLM Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** Critique of Step 1 (5 scenarios investigated to verdict)\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
