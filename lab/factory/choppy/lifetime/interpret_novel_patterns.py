"""
L3 follow-up: send the comprehensive-search novel combinations to Sonnet 4.5
for trading-mechanism interpretation.

The L3 search surfaced patterns NOT found in cell investigations:
  • UP_TRI:    market_breadth_pct=medium × nifty_vol_regime=High family
  • DOWN_TRI:  market_breadth_pct=medium × nifty_vol_regime=Medium family
  • BULL_PROXY: market_breadth_pct=high × multi_tf_alignment_score=high family

We collapse 3-feat extensions into their 2-feat seed to avoid prompt
redundancy, then ask Sonnet 4.5: are these novel mechanisms, or variants of
the compression-bull signature the cells previously surfaced?

Saves: lifetime/novel_patterns_interpretation.md (markdown, human-readable).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

INPUT_PATH = _HERE / "comprehensive_combinations_top20.json"
OUTPUT_PATH = _HERE / "novel_patterns_interpretation.md"


def _format_combo(features: list, n_wl: int, wr: float, lift: float) -> str:
    feats = " AND ".join(f"`{f}={l}`" for f, l in features)
    return f"{feats} → n={n_wl}, WR={wr*100:.1f}%, lift={lift*100:+.1f}pp"


def _consolidate(top20: list[dict]) -> list[dict]:
    """Keep one representative per unique 2-feat seed (best by lift × n)."""
    seen: dict[frozenset, dict] = {}
    for r in top20:
        # Coerce int-like fields (np.int64 → str on json dump)
        r["n_match_wl"] = int(r["n_match_wl"])
        r["n_match"] = int(r["n_match"])
        feats_2 = sorted(f"{f}={l}" for f, l in r["features"][:2])
        key = frozenset(feats_2[:2])
        score = r["lift_pp"] * r["n_match_wl"]
        if key not in seen or score > (
                seen[key]["lift_pp"] * seen[key]["n_match_wl"]):
            seen[key] = r
    return list(seen.values())


def main():
    print("─" * 80)
    print("L3 follow-up: novel-pattern interpretation via Sonnet 4.5")
    print("─" * 80)

    data = json.loads(INPUT_PATH.read_text())
    by_sig = data["by_signal_type"]

    sections = []
    for sig, payload in by_sig.items():
        baseline = payload["baseline_wr"]
        top20 = payload.get("top20_combinations", [])
        consolidated = _consolidate(top20)[:7]
        lines = [f"### {sig} × Choppy (baseline {baseline*100:.1f}% WR)"]
        for r in consolidated:
            lines.append("- " + _format_combo(
                r["features"], r["n_match_wl"], r["wr"], r["lift_pp"]))
        sections.append("\n".join(lines))

    cell_context = """## Cell-investigation findings (for comparison)

The Choppy regime cell investigations previously surfaced two families:

1. **F1 / F4 compression-bull** (UP_TRI cell):
   `ema_alignment=bull AND coiled_spring_score=medium`
   — held only +1.7pp lift at lifetime (live April 2026: +23pp; collapsed at scale).

2. **BULL_PROXY KILL family**: high market_breadth + extended-above-EMA20 patterns.
   All filters tested below +10pp lifetime lift → rejected.

Anti-features (`vix_level=high`, `feat_friday`, `coiled_spring=low`,
`market_breadth=high`) were 3-of-4 REFUTED at lifetime — directional inversion
from the live finding.
"""

    novel = "\n\n".join(sections)

    prompt = f"""You are interpreting a comprehensive 2-feature combination
search at lifetime scale (15-yr Indian equity backtest, ~35,000 Choppy-regime
signals). The patterns below MET our qualifying bar (n≥100, lift≥+5pp,
binomial p<0.01) but were NOT surfaced by prior single-cell investigations.

## Novel combinations qualifying at lifetime

{novel}

{cell_context}

## Your task

For each of the three signal types (UP_TRI / DOWN_TRI / BULL_PROXY), answer:

1. **Mechanism**: What trading mechanism does the dominant 2-feature family
   suggest? Reference established concepts (sector_rotation, mean_reversion,
   regime_transition, calendar_flow, smart_money_positioning,
   weak_hands_capitulation, institutional_accumulation, trend_continuation).

2. **Novel vs variant**: Is this a NEW pattern type the cells missed, or is
   it a variant of the compression-bull signature dressed in different
   features? Pay attention to whether `nifty_vol_regime=High`/`Medium` +
   `market_breadth_pct=medium` describes the same market state as
   "compression coil + bullish EMA stack" — or a fundamentally different
   regime sub-state.

3. **Production posture**: Given lifetime evidence (5-9pp lift on n=500-4500
   cohorts) but the F1 cell finding's collapse from +23pp live to +1.7pp
   lifetime, would you DEPLOY, INVESTIGATE FURTHER, or DEFER these patterns?

Format: markdown with `### UP_TRI`, `### DOWN_TRI`, `### BULL_PROXY`
sub-sections. Be specific and concise — 4-6 bullets per signal type.
End with a single `## Cross-signal synthesis` paragraph capturing the unifying
mechanism (or lack thereof)."""

    client = LLMClient()
    print(f"\nCost so far: ${client._total_cost:.3f} (cache loaded)")
    print("Calling Sonnet 4.5...")
    response = client.synthesize_findings(prompt, max_tokens=2500)

    md = f"""# Novel Pattern Interpretation — L3 Follow-up

**Source**: `comprehensive_combinations_top20.json`
**Model**: `claude-sonnet-4-5-20250929`
**Date**: 2026-05-02

## Patterns submitted

{novel}

## Sonnet 4.5 interpretation

{response}
"""
    OUTPUT_PATH.write_text(md)
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
