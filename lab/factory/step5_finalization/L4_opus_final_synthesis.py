"""L4 — Opus final integration synthesis."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from llm_client import _load_dotenv_if_needed  # noqa: E402

_load_dotenv_if_needed()
from anthropic import Anthropic  # noqa: E402

OUTPUT_DIR = _HERE / "L4_opus_output"
RAW_PATH = _HERE / "_l4_opus_raw.md"
COST_LOG = _LAB_ROOT / "cache" / "llm" / "cost_log.jsonl"

OPUS_MODEL = "claude-opus-4-7"
DELIVERABLES = [
    "unified_rules_v4_1_FINAL.json",
    "integration_notes_FINAL.md",
    "KNOWN_ISSUES.md",
    "trader_expectations.md",
]


def parse_deliverables(text: str, deliverables: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    starts = []
    for fname in deliverables:
        idx = text.find(f"```{fname}\n")
        if idx >= 0:
            starts.append((idx, fname))
    starts.sort()
    for i, (start, fname) in enumerate(starts):
        cs = start + len(f"```{fname}\n")
        ce = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        block = text[cs:ce]
        block = re.sub(r"\n```\s*\n*$", "", block.rstrip()) + "\n"
        out[fname] = block
    return out


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rules_v4_1 = (_HERE / "unified_rules_v4_1_post_L2.json").read_text()
    preds_v4_1 = (_HERE / "validation_predictions_post_L2.json").read_text()
    val_post_l2 = (_HERE / "validation_post_L2.json").read_text()
    schema_gap = (_HERE / "L2_schema_gap_analysis.md").read_text()
    barcode_format = (_HERE / "L3_opus_output" / "barcode_format_v1.md").read_text()
    barcode_integration = (_HERE / "L3_opus_output" / "integration_spec.md").read_text()
    methodology = (_LAB_ROOT / "factory" / "opus_iteration"
                   / "methodology_findings.md").read_text()

    prompt = f"""# Final Lab Pipeline Integration — Opus Synthesis

## Role

You are producing the FINAL production-ready Lab pipeline output. This
is the closing synthesis after Steps 1-5. You receive:

- 37-rule v4.1 ruleset (post-L1 win_* recalibration + post-L2 schema
  refinement; 100% PASS+WARN)
- Validation report showing 35 PASS / 2 WARN / 0 FAIL
- Schema v4.1 gap analysis
- Barcode format design (L3)
- Step 4 methodology findings

Produce 4 deliverables that close the Lab pipeline and hand off to
Step 7 (production integration).

## Inputs

### Current rules v4.1 ({len(rules_v4_1):,} chars)

```json
{rules_v4_1[:8000]}...[truncated]
```

### Predictions v4.1 ({len(preds_v4_1):,} chars)

```json
{preds_v4_1[:3000]}...[truncated]
```

### Post-L2 validation summary
{val_post_l2[:1500]}

### L2 schema gap analysis (excerpt)
{schema_gap[:2500]}

### L3 barcode format design (excerpt)
{barcode_format[:2500]}

### L3 integration spec (excerpt)
{barcode_integration[:2500]}

### Step 4 methodology findings (excerpt)
{methodology[:2500]}

---

## Your task

Synthesize the closing Lab artifacts. **Do not skip any deliverable. Do
not change rule logic — your job is integration not rule generation.**

## Deliverable 1: `unified_rules_v4_1_FINAL.json`

Re-emit the v4.1 ruleset with:
- All 37 rules from L2 output (no logic changes)
- `production_ready` flag accurately set per rule (HIGH/MEDIUM = true,
  LOW = deferred = false)
- `deferred_reason` for production_ready=false rules
- `known_issue` reference for the 2 WARNING rules
- `barcode_compatibility` field per rule (does this rule emit a
  barcode field? what value?)
- Updated `description` field at top: closing the Lab pipeline

The output must remain schema v4.1 compliant.

## Deliverable 2: `integration_notes_FINAL.md`

Step 7 production deployment plan. Sections:

1. **Pre-deployment checklist** (8-10 items)
2. **Phase 1 — HIGH priority rules deployment** (week 1-2)
   - Which rules ship; which detector dependencies; which cells
3. **Phase 2 — MEDIUM priority rules** (week 3-4)
4. **Phase 3 — LOW priority rules** (deferred to month 2+)
5. **Detector integration order**:
   - Bull sub-regime (200d × breadth) — required for Phase 1
   - Bear 4-tier classifier (B1) — required for Phase 1
   - Choppy 3-axis + N=2 hysteresis (C1+C3) — required for Phase 2
   - Phase-5 override (B3) — required for Phase 1
6. **2-week parallel validation period**:
   - v3 (current) + v4.1 (new) running concurrently
   - Discrepancy logging
   - Trader sees both verdicts; selects which to follow
7. **Cutover criteria**:
   - Discrepancy rate < 5%
   - WR delta < 3pp
   - Trader confidence affirmed
   - Rollback procedure if criteria fail
8. **Schema migration v3 → v4.1**:
   - mini_scanner_rules.json bump
   - Backward-compat shim during parallel period
9. **Barcode rollout** (per L3 integration spec):
   - Phase A shadow → Phase B replace → Phase C clean

## Deliverable 3: `KNOWN_ISSUES.md`

Document the 2 WARNINGs + LOW priority deferred items. Sections:

1. **Active WARNINGs** (2 items):
   - rule_027 (Choppy DOWN Pharma SKIP, WR=66.1%): document why
     observed WR contradicts Lab finding; mitigation
   - watch_001 (Choppy UP_TRI broad informational): WR slightly out of
     band; deferral
2. **LOW priority deferred** (LOW priority rules with
   production_ready=false): list each, why deferred, when revisit
3. **Methodology limitations**:
   - No live first-Bull-day data
   - Bucket threshold registry not yet formalized
   - Phase-5 override database needs quarterly refresh
4. **Future iteration items**:
   - Re-derive Lab thresholds from raw data (Step 1.5+2 SY
     recommendation)
   - B2 sigmoid soft thresholds (deferred to Phase 2 in B1+B2)
   - Choppy 3-axis detector with composite hysteresis (C1+C3)
5. **Operational risks**:
   - Live small-sample inflation (if early production data shows
     90%+ WR, it's selection bias not edge)
   - Sub-regime detector classification on transition days

## Deliverable 4: `trader_expectations.md`

Trader-facing emotional + analytical preparation. Sections:

1. **The honest WR shift**:
   - Live observed: 95% (Bear UP_TRI hot, n=74)
   - Production calibrated: ~57-71% (lifetime baseline + sub-regime tier)
   - Why the 30pp drop is honest, not the system "getting worse"
2. **First 30 days expectations**:
   - Day 1-7: shadow mode; no real capital
   - Day 8-15: Phase 1 HIGH rules live; small position sizes
   - Day 16-30: Phase 2 ramp; full sizing on validated cohorts
   - Realistic outcome distributions per phase
3. **Failure modes and recovery**:
   - "First-day BULL_PROXY flood" (S5 finding) — actually rare
   - "Sub-regime jitter on classification day" (S4) — 10-day gate
   - "Phase-5 override fires on stale combo" — 90-day recency check
4. **When to escalate concerns**:
   - WR < 50% over 30+ signals → review sub-regime classification
   - Sector mismatch from Lab playbook → check kill_pattern integrity
   - Multiple kill rules firing simultaneously → review precedence
5. **Calibrated WR table** (per cell, per tier):
   - Show all 37 rules' calibrated_wr ranges
   - Highlight HIGH/MEDIUM priority rules
6. **Trader's mental model**:
   - This is NOT a "system that wins 95%"; this is a "system with
     edge cells" producing 55-75% WR
   - Edge is real but narrow; size discipline matters more than rule
     quality
   - Phase-5 override is a precision boost, not a magic wand

## Constraints

- All 4 deliverables required; do not skip any
- Output MUST conform to schema v4.1
- Do not change rule logic from v4.1 input
- Use plain English in Markdown deliverables (no jargon without
  explanation)
- Be honest about limitations — Lab work is real but bounded

## Output format

```unified_rules_v4_1_FINAL.json
{{...}}
```

```integration_notes_FINAL.md
# ...
```

```KNOWN_ISSUES.md
# ...
```

```trader_expectations.md
# ...
```
"""

    print(f"  prompt: {len(prompt):,} chars")
    print(f"  approx input tokens: {len(prompt) // 4:,}")
    print(f"\n  calling {OPUS_MODEL} (max_tokens=32000, streaming)...")

    client = Anthropic()
    t0 = time.time()
    with client.messages.stream(
        model=OPUS_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        text_parts = []
        for chunk in stream.text_stream:
            text_parts.append(chunk)
        response = stream.get_final_message()
    text = "".join(text_parts)
    elapsed = time.time() - t0
    RAW_PATH.write_text(text)
    print(f"  elapsed: {elapsed:.1f}s; raw: {len(text):,} chars")

    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    cost_in = in_tok / 1e6 * 15.0
    cost_out = out_tok / 1e6 * 75.0
    total = cost_in + cost_out
    print(f"  tokens: input {in_tok:,} (${cost_in:.3f}), output {out_tok:,} (${cost_out:.3f})")
    print(f"  TOTAL: ${total:.3f}")

    with COST_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "caller": "step5_L4_final_synthesis",
            "model": OPUS_MODEL,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": total,
        }) + "\n")

    parts = parse_deliverables(text, DELIVERABLES)
    for fname in DELIVERABLES:
        if fname in parts:
            (OUTPUT_DIR / fname).write_text(parts[fname])
            print(f"  ✓ {fname:40s} ({len(parts[fname]):,} chars)")
        else:
            print(f"  ✗ {fname:40s} MISSING")

    # Quick sanity check
    rules_path = OUTPUT_DIR / "unified_rules_v4_1_FINAL.json"
    if rules_path.exists():
        try:
            data = json.loads(rules_path.read_text())
            print(f"\n  FINAL rules JSON: {len(data.get('rules', []))} rules, schema {data.get('schema_version')}")
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON parse error: {e}")


if __name__ == "__main__":
    main()
