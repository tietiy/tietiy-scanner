"""LS3 helper: Sonnet 4.5 critique of full Bull regime production posture."""
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
# Bull Regime Production Posture Summary

## Cell status

| Cell | Status | Best filter | Filter WR / lift |
|---|---|---|---|
| Bull UP_TRI | PROVISIONAL_OFF | recovery × vol=Med × fvg_low | 74.1% / +22pp (n=390) |
| Bull DOWN_TRI | PROVISIONAL_OFF | late × wk3 | 65.2% / +21.8pp (n=253) |
| Bull BULL_PROXY | PROVISIONAL_OFF | healthy × 20d=high | 62.5% / +11.4pp (n=128) |

All 3 cells: lifetime-only methodology (0 live Bull signals). All
PROVISIONAL_OFF default. Bull production scanner pipeline VERIFIED
(no bugs, no blockers).

## Sub-regime detector (Bull)

Tri-modal SKEWED:
  recovery_bull: ~2.6% (low 200d AND low breadth — early-cycle quality leadership)
  healthy_bull:  ~12.5% (mid 200d AND high breadth — broad sustained Bull)
  normal_bull:   ~76.4% (everything else — bulk basin)
  late_bull:     ~7.1% (mid 200d AND low breadth — narrowing leadership topping)

## Calibrated WR expectations table

| Sub-regime | UP_TRI | BULL_PROXY | DOWN_TRI |
|---|---|---|---|
| Recovery | 60-74% (filter) | 58-65% (filter) | SKIP (35.7% — worst) |
| Healthy  | TAKE_FULL (~58%) | 62.5% (filter) | SKIP (40.5%) |
| Normal   | TAKE_SMALL (~51%) | SKIP | SKIP (42.6%) |
| Late     | SKIP (45.1% — worst) | SKIP | 65.2% (late × wk3) |

## KILL rules (sparse for Bull)

  vol_climax × BULL_PROXY → REJECT (universal anti, replicates Bear -11pp)

## Activation triggers

  Bull regime active ≥10 days + ≥30 live signals + matched-WR ≥ 50%

## Documented gaps (must address pre-activation)

  Gap 1: 0 Bull-specific boost_patterns in mini_scanner_rules.json
  Gap 2: Bull sub-regime detector not in production scanner
  Gap 3: target_price=None (by design)
  Gap 4: Sonnet's 5 untested Bull verification scenarios
  Gap 5: Bull cells need live validation gating (different from Bear UP_TRI)

## Pre-activation action list (10 items)

  Items 1-5 are pre-activation prep (Bull sub-regime detector
  integration, tests for Sonnet's scenarios, provisional
  boost_patterns, trader briefing).

  Items 6-10 are activation-day work (decision flow integration,
  Telegram digest, first-Bull-day brief, activation triggers
  documented, shadow-mode test).
"""

    prompt = f"""You are doing the final review of the Bull regime
production posture, before Bull regime activates live (Bull regime
hasn't been the active regime during the scanner's operational period;
all Bull cell findings are lifetime-only).

{summary}

## Critique requested

1. **Sub-regime gating defensibility.** Tri-modal SKEWED structure
   (76% normal, 23% edges) with hard thresholds. The trader has been
   trained on Bear's 94.6% live WR; Bull's calibrated 60-74% is much
   lower. What's the strongest argument FOR this design? What breaks
   first?

2. **WR calibration honesty.** Bull cells are lifetime-only, no live
   data inflation to remove. Calibrated WR equals lifetime baseline
   directly. Should we trust 74.1% lifetime as production WR, or apply
   a "no-live-discount" (e.g., subtract 5pp for non-stationarity risk)?

3. **First-Bull-day failure mode.** Bull regime activates live after
   months of Bear/Choppy. Trader sees first Bull signals in Telegram.
   What's the most likely failure cascade? (E.g., trader emotional
   shift from Bear's 94.6% to Bull's 65% triggers system override or
   scanner dismissal.)

4. **PROVISIONAL_OFF default vs Bear UP_TRI shadow-deployment-ready.**
   Bear UP_TRI's posture was "shadow-deployment-ready" with live
   evidence + lifetime caveats. Bull cells are PROVISIONAL_OFF. Is
   the more conservative posture appropriate for Bull, or
   over-conservative?

5. **The 5 untested scenarios from Bull verification critique** —
   state persistence across regime transitions, volume filter absence,
   sector rotation edges, classifier jitter, BULL_PROXY first-Bull-day.
   Of these 5, which 2-3 are the highest priority to test before Bull
   regime activates live? Which can wait?

6. **Production deployment risk ranking.** Of the 5 documented gaps,
   which 3 are the highest priority? Which can wait until post-Bull-
   activation?

7. **Cross-regime synthesis future work** — should we do dedicated
   cross-regime synthesis NOW (consolidate 9 cells into universal vs
   regime-specific architectural framework) OR wait for Bull regime
   to return live + activate cells first?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, ruthless, reference actual numbers. Where you can
recommend a concrete next step, do."""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# Bull Production Posture — Sonnet 4.5 Final Critique (LS3)\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
