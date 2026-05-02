"""SY — Sonnet 4.5 critique of Step 3 input package + Opus prompt structure."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_synthesis_llm.md"


def main():
    summary = """
# Step 1.5 + 2 Critique Resolution — SUMMARY

## Verdicts (7 critiques)

| # | Critique | Verdict | Action |
|---|---|---|---|
| A1 | Rules audit (9 cells) | HEALTHY (0 contradictions, 14 gaps) | Schema + 14 rules; Opus synthesis |
| C1 | Choppy missing momentum | RESOLVED with action | ADD nifty_20d_return_pct (3rd axis) |
| C2 | Choppy breadth thresholds | MARGINAL | KEEP 33/67 |
| C3 | Choppy transition whipsaw | GAP_DOCUMENTED | N=2 hysteresis + state file |
| B1 | Bear warm-zone display | RESOLVED — boundary > deep WR | 4-tier confidence display |
| B2 | Bear hard-threshold cliffs | GAP_DOCUMENTED — boundary > deep | Soft sigmoid + verdict re-mapping |
| B3 | Bear Phase-5 override | RESOLVED with design | Wilson-lower-bound override |

## Key findings consolidated

### Universal Bear UP_TRI insight (B1+B2)
- boundary_hot (just-into-hot) BEATS confident_hot (deep stress)
- Bear UP_TRI rewards INFLECTION-POINTS within stress, not depth
- Calibrated WR layers: baseline 53.5% → hot 67.8% → boundary 71.5%
  → Phase-5 override 76.6% (where applicable, ~3% of signals)

### Whipsaw findings (C3)
- 33% of Choppy days are sub-regime flip days
- 38% of episodes are 1-day duration
- N=2 hysteresis eliminates ALL 1-day jitter, halves total flips
- 9x more sub-regime jitter than regime-level jitter (S4 baseline)

### Detector improvements
- Choppy 2-axis → 3-axis (vol × breadth × momentum): 13.3pp → 27.1pp WR span
- Bear hard threshold → sigmoid: better boundary discrimination
- Bull sub-regime detector still pre-production (PRODUCTION_POSTURE Gap 2)

## 14 new rules to ship (priority-ranked post-Sonnet)

### HIGH (5 — sub-regime edge drivers + universal hygiene)
1. late_bull = SKIP (Bull UP_TRI/BULL_PROXY)
2. recovery_bull × vol=Med × fvg_low = TAKE_FULL (74% WR)
3. healthy_bull × 20d=high = TAKE_FULL (62.5%)
4. vol_climax × BULL_PROXY = REJECT (Bear AND Bull-late_bull)
5. Bear UP_TRI × Health = AVOID

### MEDIUM (5)
6. Bear UP_TRI × Dec = SKIP
7. Choppy UP_TRI × Feb = SKIP
8. Choppy BULL_PROXY = REJECT (entire cell)
9. Bear DOWN_TRI calendar filter (wk2/wk3)
10. Bear UP_TRI cold cascade boost

### LOW (4)
11-14. Various sector and day-of-week micro-rules

## Schema design (per A1 LLM critique)

2-tier: `match_fields = {signal, sector, regime}` +
        `conditions = [{feature: value}, ...]` (AND logic)

Rule precedence: KILL > sub-regime > sector/calendar > Phase-5 override

## Step 3 input package for Opus

1. 9 cell playbooks
2. 3 regime synthesis docs
3. 2 PRODUCTION_POSTURE docs
4. Bull production verification report
5. Bull critique resolution (Step 1: bull_critiques/SUMMARY.md)
6. Step 1.5+2 critique resolution (this directory)
7. mini_scanner_rules.json (current production)
8. Cross-regime architectural framework (in A1)

Plus:
- 5 worked examples (regime × signal × sub-regime cross-product)
- Calibrated WR expectations table (~12 cells)
- Schema spec (2-tier)
- Rule precedence model

## Step 3 (Opus) deliverables expected

1. structural_rules.json (universal patterns)
2. parametric_cells.json (cell-specific axes/thresholds)
3. Rule precedence documentation
4. Test vectors validating against worked examples

## Honest limitations
1. No live first-Bull-day data
2. Choppy 3-axis detector untested in production
3. C3 hysteresis adds state (current scanner is stateless-per-scan)
4. B1 + B2 produce same finding via different mechanisms — ship one
5. B3 needs quarterly refresh cadence
6. Trade mechanism annotation TBD per-rule

API spend Step 1.5 + 2: $0.054 (A1 LLM only)
"""

    prompt = f"""You are doing FINAL critical review before Step 3
(Opus rule synthesis). Step 1.5 (rules audit) + Step 2 (6 critiques)
both ran. Output below. Step 3 will produce unified production rules
informed by all critique resolutions.

{summary}

## Critique requested

1. **Step 3 readiness verification.** The summary declares "Step 3
   READY." Are there missing pieces Opus needs that aren't in the
   input package? Specifically: do the 5 worked examples cover enough
   of the regime × signal × sub-regime cross-product, or are there
   common production scenarios missing?

2. **B1 vs B2 conflict.** Both produce same finding (boundary_hot >
   confident_hot) via different mechanisms (5-tier display vs sigmoid).
   The summary recommends "ship one." Which one? B1's tiered display
   is simpler operationally; B2's sigmoid is more flexible. Which
   serves trader expectation management better?

3. **C1 + C3 sequencing.** C1 recommends adding momentum axis
   (9 cells → 27 cells), which will INCREASE whipsaw. C3 recommends
   N=2 hysteresis to reduce whipsaw. Should these ship together,
   or sequentially? If together, how does hysteresis apply across
   3 axes (each axis independently, or to the composite sub-regime)?

4. **Rule precedence model.** Summary defines KILL > sub-regime >
   sector/calendar > override. But A1 also surfaced rule
   *interactions* (e.g., Bear UP_TRI hot AND Health AVOID — which
   wins?). Is the 4-layer hierarchy sufficient, or are there
   conflicts that need explicit resolution?

5. **Trade mechanism annotation.** A1 LLM critique #1 said rules
   should annotate trade mechanism (mean-reversion / breakout-
   continuation / regime-transition). This was deferred to Opus.
   Should Opus annotate per-rule, or per-cell, or per-regime?

6. **Schema versioning.** Current mini_scanner_rules.json is schema
   v3. Step 3 outputs new 2-tier schema. Migration path:
   forward-compat (v3 rules continue to work) or breaking change?
   What's the safe deployment approach?

7. **Production capacity vs Lab fidelity.** Lab findings show
   ~70 cell × sub-regime × filter combinations with calibrated WR.
   Production scanner currently has 9 boost_patterns. Going from 9
   to ~70 rules is 8x complexity growth. Is that operationally
   safe, or should Step 3 prune to a smaller HIGH-confidence subset
   first?

8. **Worked examples coverage gap.** The 5 worked examples cover
   Bear UP_TRI hot/boundary_hot, Bull UP_TRI recovery_bull,
   Choppy UP_TRI breadth=medium, Choppy BULL_PROXY KILL, Bear UP_TRI
   override-doesn't-trigger. What's missing? Specifically:
   - Bull DOWN_TRI late_bull × wk3 (the strongest provisional Bull DOWN combo)
   - Bear DOWN_TRI Verdict A (calendar filter)
   - Choppy DOWN_TRI breadth=medium × vol=Medium × wk3 (CANDIDATE)
   - All Bull cells together when Bull regime activates

   Should we author 3-5 more worked examples for Step 3?

Format: markdown, ## sections per question. 2-4 short paragraphs each.
Be specific, ruthless, and where you can recommend a concrete action,
do.
"""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# SY Synthesis — Sonnet 4.5 Final Critique (Step 3 Readiness)\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n"
        f"**Context:** Critique of Step 1.5 + Step 2 output package before Opus rule synthesis\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
