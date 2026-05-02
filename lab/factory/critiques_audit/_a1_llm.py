"""A1 — Sonnet 4.5 critique of rules audit across 9 cells."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUTPUT_PATH = _HERE / "_a1_llm.md"


def main():
    summary = """
# A1 Rules Audit Across 9 Cells

## Cells covered (3 regimes × 3 signal types)
- Bear UP_TRI (HIGH-confidence sub-regime gated, hot/warm/cold)
- Bear DOWN_TRI (DEFERRED + provisional Verdict A: kill_001 + wk2/wk3)
- Bear BULL_PROXY (DEFERRED + provisional hot-only)
- Bull UP_TRI (PROVISIONAL_OFF, recovery/healthy/normal/late)
- Bull DOWN_TRI (PROVISIONAL_OFF, late_bull × wk3 only)
- Bull BULL_PROXY (PROVISIONAL_OFF, healthy_bull × 20d=high best)
- Choppy UP_TRI (CANDIDATE, breadth=medium × vol=High)
- Choppy DOWN_TRI (CANDIDATE, breadth=medium × vol=Medium × wk3)
- Choppy BULL_PROXY (KILL — entire cell rejected)

## Production rules.json current state
- 1 kill_pattern (Bank × DOWN_TRI; live 0/11)
- 1 watch_pattern (UP_TRI × Choppy; informational)
- 7 boost_patterns (all regime=Bear; 6 sector-specific UP_TRI + 1 BULL_PROXY)
- Schema v3 supports: signal, sector, regime, conviction_tag

## Cross-cell consistency findings

### Universal patterns (consistent)
- vol_climax × BULL_PROXY = anti (Bear -11pp, Bull -4.4pp; UNIVERSAL)
- Sub-regime tri-modal structure (all 9 cells)
- Calendar inversion across direction (3/3 regimes confirmed)
- Direction-flip pattern UP vs DOWN (perfect 4-cell inversion in Bull)

### Regime-specific (don't transfer)
- Sub-regime axes vary: Choppy=vol×breadth, Bear=vol×60d, Bull=200d×breadth
- Anchor features vary: Bear=60d_low, Bull=20d_high, Choppy=breadth_med
- High vol: Bear=hot tier (winner), Bull=ANTI, Choppy=required

### Direct contradictions: ZERO
Production rules are strict SUBSET of Lab findings. Gap is missing
rules, not wrong rules.

## Recommended new rules (12 total)
HIGH priority (5):
1. Universal vol_climax × BULL_PROXY = REJECT (cross-regime)
2. Choppy BULL_PROXY = REJECT (entire cell)
3. Bear UP_TRI × Health = AVOID (32.4% hot, hostile sector)
4. Bear UP_TRI × Dec = SKIP (-25pp catastrophic)
5. Choppy UP_TRI × Feb = SKIP (-16.2pp catastrophic; Budget month)

MEDIUM priority (5):
6. Bull UP_TRI × Energy = SKIP (-2.9pp)
7. Bear DOWN_TRI calendar filter (wk2/wk3 only; +7.5pp)
8. Choppy DOWN_TRI wk3 × breadth=med × vol=Med = TAKE_FULL (+11.7pp, n=1295)
9. Bear UP_TRI cold cascade (wk4 × swing_high=low; +13pp)
10. late_bull = SKIP for Bull UP_TRI/BULL_PROXY (requires sub-regime detector)

LOW priority (4):
11. Choppy DOWN_TRI × Pharma = SKIP (-4.7pp)
12. Choppy DOWN_TRI × Friday = SKIP (-6.2pp)
13. Choppy UP_TRI × Metal = SKIP (-2.2pp)
14. Bull UP_TRI/PROXY × Sep = SKIP (-8.4pp)

## Schema gaps for Opus to address
- Production rules.json supports: signal, sector, regime
- Lab rules need: month, day_of_month_bucket, day_of_week, sub_regime,
  nifty_vol_regime, nifty_60d_return_bucket
- Schema extension required as part of Step 3 synthesis output

## Verdict
- Methodology consistency: HEALTHY (0 contradictions)
- Production rules consistency: HEALTHY (strict subset)
- Rule completeness: 12 gaps, all documented
- Step 3 readiness: READY
"""

    prompt = f"""You are doing critical review of a rules audit
across 9 trading-system cells (3 regimes × 3 signal types). The audit
output feeds Step 3 (Opus rule synthesis) which will produce unified
production rules.

{summary}

## Critique requested

1. **Methodology consistency claim.** The audit declares "0
   contradictions" between cells and "0 contradictions" between Lab
   and production. Is this honest, or did the audit miss conflicts
   by framing them as "regime-specific" or "direction-specific"
   variations? Specifically test: are there cases where the same
   feature × signal × regime context produces opposite verdicts
   across cell investigations?

2. **Universal pattern claim.** The audit says vol_climax × BULL_PROXY
   = anti is universal (-11pp Bear, -4.4pp Bull). The Bull number is
   weaker. Should this be classified universal-with-strength-variance
   or are these actually different mechanisms with similar surface
   manifestation?

3. **Schema extension scope.** Audit recommends adding month,
   day_of_month, day_of_week, sub_regime, vol_regime, 60d_return_bucket
   to mini_scanner_rules.json. That's 6 new fields. Is this the right
   schema design, or should some of these (like sub_regime) be runtime
   computed fields rather than rule-matchable fields? What's the
   architectural tradeoff?

4. **Priority ranking.** HIGH priority list has 5 items, mostly
   catastrophic cells (Choppy BULL_PROXY KILL, Dec/Feb calendar
   catastrophes). Are these priorities well-calibrated, or is anything
   misranked? Specifically: should sub-regime gating rules
   (recovery/healthy/late_bull) be HIGH priority since they unlock
   the highest WR cells (74% recovery_bull × vol=Med × fvg_low)?

5. **Missing gap detection.** Audit found 12 missing rules. Did the
   audit framework catch all gaps or are there entire categories
   missing? Specifically: did it consider cross-cell rule
   *interactions* (e.g., what if a signal triggers both Bear UP_TRI
   hot AND Bear UP_TRI Health AVOID — which wins)? Did it consider
   *temporal* rules (rule-of-the-day-of-week within month)?

6. **Step 3 (Opus) readiness.** The audit declares "Step 3 ready."
   What's the single most important thing Opus needs that's NOT
   in this audit? Be specific.

7. **Cross-cell architectural patterns vs cell-specific findings.**
   The audit emphasizes universal patterns (sub-regime tri-modal,
   calendar inversion, direction-flip). At what point does the
   universal-pattern abstraction become unhelpful — i.e., when do
   we need cell-specific rules that don't conform to the framework?

Format: markdown, ## sections per question. 2-4 short paragraphs each.
Be specific, ruthless, and where you can recommend a concrete action,
do.
"""

    client = LLMClient()
    print(f"  cost so far: ${client._total_cost:.3f}")
    response = client.synthesize_findings(prompt, max_tokens=4500)

    OUTPUT_PATH.write_text(
        f"# A1 Rules Audit — Sonnet 4.5 LLM Critique\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"  saved: {OUTPUT_PATH}")
    print(f"  cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
