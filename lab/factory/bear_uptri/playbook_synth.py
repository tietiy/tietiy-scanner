"""
B4 helper: ask Sonnet 4.5 for a trader-facing narrative for the
Bear UP_TRI cell, given the cell evidence + filter findings.

Output: lab/factory/bear_uptri/_playbook_narrative.md (interim, used to
enrich playbook.md hand-written sections).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "_playbook_narrative.md"


def main():
    print("Calling Sonnet 4.5 for Bear UP_TRI playbook narrative...")
    diff = json.loads((_HERE / "differentiators.json").read_text())
    filt = json.loads((_HERE / "filter_test_results.json").read_text())

    top_winners = diff["top_winner_features_vs_watch"][:5]
    top_anti = diff["top_anti_features_vs_watch"][:5]
    win_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}  diff={r['differentiator_score']*100:+.0f}pp"
        for r in top_winners)
    anti_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}  diff={r['differentiator_score']*100:+.0f}pp"
        for r in top_anti)
    cands = filt["candidate_filters"]
    cand_lines = "\n".join(
        f"  • {c['name']}: matched WR={c['matched_wr']*100:.0f}%, "
        f"match_rate={c['match_rate']*100:.0f}%"
        for c in cands if c['matched_wr'] is not None
    )

    prompt = f"""You are writing the trader-facing narrative section of a
production playbook for the Bear UP_TRI trading cell. The cell is the
strongest cohort across the entire investigation pipeline.

## Cell evidence
• Live signals: 74 in April 2026 — 70 wins / 4 losses → 94.6% WR
• Lifetime baseline: 55.7% WR over 15,151 historical Bear UP_TRI signals
• Live-vs-lifetime gap: +38.9pp (largest regime-shift artifact in Lab)
• Phase 5: 100% validation rate (87/87 evaluable patterns)
• Vol regime in live: 100% High (uniform stress sub-regime)

## Top winner features (vs WATCH baseline)
{win_lines}

## Top anti-features (over-represented in WATCH)
{anti_lines}

## Filter back-test results (all candidates)
{cand_lines}

Headline: NO filter improves on the 94.6% baseline. The 4 losses scatter
evenly across all candidate filter splits. Bear UP_TRI in current sub-
regime is broad-band edge, not narrow-band.

## The 4 losses (for context)
• OIL.NS 2026-04-01 (Energy)  — ema_alignment=mixed, wk1
• OIL.NS 2026-04-06 (Energy)  — ema_alignment=mixed, wk1
• COROMANDEL.NS 2026-04-09 (Chem) — ema_alignment=mixed, wk2
• JKCEMENT.NS 2026-04-09 (Infra) — ema_alignment=mixed, wk2

3 of 4 losses occurred on just two date clusters (2026-04-01, 2026-04-09);
all 4 had ema_alignment=mixed; none in wk4 (so the wk4 anti-feature is
NOT validated by losses).

## Your task — write a trader-facing narrative

Cover these sub-sections with one short paragraph each. Be terse, concrete,
trader-like. Reference established concepts (oversold mean reversion, bear
rally, capitulation, regime transition, etc.) where appropriate.

1. **What this cell feels like mechanically** — When does Bear UP_TRI
   work? What's the market state that produces winners?

2. **When to take the trade** — What does the trader watch for at signal
   time? Setup / trigger / confirmation framing.

3. **When to be cautious / size down** — Even in a 94.6% cohort, what
   warrants reduced size? Not filter rules, just trader judgment cues.

4. **Risk: regime-shift fragility** — Why the 94.6% is unlikely to
   sustain in lifetime. What macro shift would invalidate it.

5. **Exit discipline** — When to close. Default hold horizon. Stop placement.

Output as markdown — five `### ` sub-sections. No preamble or wrap-up
paragraph; just the five sections. Each section 3-5 sentences max."""

    client = LLMClient()
    md = client.synthesize_findings(prompt, max_tokens=2000)
    OUT.write_text(md)
    print(f"Saved interim narrative: {OUT}")
    print(f"Cost this call: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
