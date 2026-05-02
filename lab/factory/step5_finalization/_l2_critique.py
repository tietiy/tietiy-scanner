"""L2 Sonnet critique."""
from __future__ import annotations
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import LLMClient  # noqa: E402

OUT = _HERE / "L2_critique.md"


def main():
    gap = (_HERE / "L2_schema_gap_analysis.md").read_text()
    val = json.loads((_HERE / "validation_post_L2.json").read_text())
    summary = f"""
# L2 Schema Gap Analysis

{gap[:6000]}

## Validation post-L2
- Total: {val['n_rules']}
- PASS: {val['summary']['PASS']} ({val['summary']['pass_rate']*100:.1f}%)
- WARNING: {val['summary']['WARNING']}
- FAIL: {val['summary']['FAIL']}
- PASS+WARN: {val['summary']['pass_or_warning_rate']*100:.1f}%

## Remaining 2 WARNINGs
"""
    for r in val['results']:
        if r['validation_verdict'] == 'WARNING':
            wr = r.get('actual_match_wr')
            wr_str = f"{wr*100:.1f}%" if wr else "—"
            summary += f"- {r['rule_id']}: n={r['actual_match_count']} WR={wr_str} | {r['reason'][:120]}\n"

    prompt = f"""You are reviewing L2 schema validation + v4.1 design
for the Lab pipeline. We extended schema to make prediction tolerances
first-class fields and recalibrated 16 rules' predictions.

{summary}

## Critique

1. **94.6% PASS / 100% PASS+WARN.** Is this real progress or did we
   just loosen bands until everything passes? Prediction recalibration
   used actual observed values — risk of overfitting validation
   harness to lifetime data, not generalizing.

2. **Schema v4.1 extensions sufficient?** We added explicit
   tolerance bands + production_ready/deferred_reason/known_issue
   fields. Are there other production-readiness gaps the schema
   should cover (e.g., rule deprecation tracking, rule conflict
   resolution metadata)?

3. **2 remaining WARNINGs** are kill-rules-matching-winners. rule_027
   says SKIP Pharma×Choppy DOWN_TRI but actual matched signals win at
   66%. Either Lab finding doesn't generalize OR rule logic is wrong.
   Should we DELETE these rules instead of accepting WARNING?

4. **Risk of v4.1 schema as production deployment baseline.** With
   100% PASS+WARN, the temptation is to ship immediately. What
   second-order issues might surface in 30 days of live trading
   that validation can't catch?

Format: markdown, ## sections per question. 2-3 short paragraphs.
"""
    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    OUT.write_text(
        f"# L2 Schema Validation — Sonnet 4.5 Critique\n\n"
        f"**Date:** 2026-05-03\n\n{response}\n"
    )
    print(f"  saved: {OUT}; cost: ${client._total_cost:.3f}")


if __name__ == "__main__":
    main()
