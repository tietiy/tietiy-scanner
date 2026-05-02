"""L3 — Opus barcode format design + Sonnet critique."""
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

OUTPUT_DIR = _HERE / "L3_opus_output"
RAW_PATH = _HERE / "_l3_opus_raw.md"
COST_LOG = _LAB_ROOT / "cache" / "llm" / "cost_log.jsonl"

OPUS_MODEL = "claude-opus-4-7"
DELIVERABLES = [
    "barcode_format_v1.md",
    "barcode_examples.json",
    "integration_spec.md",
    "validation_test_cases.json",
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
    schema_gap = (_HERE / "L2_schema_gap_analysis.md").read_text()
    integration_notes = (_LAB_ROOT / "factory" / "opus_iteration"
                         / "path1_disciplined" / "output"
                         / "integration_notes_path1.md").read_text()

    # Sample existing signal_history.json structure for backward-compat reference
    sig_hist = json.load((_LAB_ROOT.parent / "output" / "signal_history.json").open())
    sample_signal = sig_hist["history"][-1]
    sample_signal_str = json.dumps(sample_signal, indent=2)

    cell_playbooks_index = """
- bear_uptri (HIGH-confidence, hot/warm/cold sub-regime gated)
- bear_downtri (DEFERRED + provisional Verdict A)
- bear_bullproxy (DEFERRED + provisional hot-only)
- bull_uptri (PROVISIONAL_OFF, recovery/healthy/normal/late)
- bull_downtri (PROVISIONAL_OFF, late_bull × wk3)
- bull_bullproxy (PROVISIONAL_OFF, healthy_bull × 20d=high)
- choppy_uptri (CANDIDATE, breadth=medium × vol=High)
- choppy_downtri (CANDIDATE, breadth=medium × vol=Medium × wk3)
- choppy_bullproxy (KILL — entire cell rejected)
"""

    prompt = f"""# Production Barcode File Format Design

## Role

You are designing the production barcode JSON format for the TIE TIY
Scanner (Indian NSE F&O equity scanner). Production scanner generates
barcodes per signal at runtime, encoding regime/sub-regime
classification, matched rule IDs, verdict, confidence tier, calibrated
WR.

The barcode is the runtime equivalent of a Lab cell verdict — for
each signal that fires, it captures everything the scanner decided
about that signal, in a single JSON object that can be persisted,
displayed in Telegram, archived for replay, etc.

## Context

### Schema v4.1 (just finalized in L2)

The unified rules JSON at `unified_rules_v4_1_post_L2.json` has 37
rules across the 9 cells. Schema is 2-tier (match_fields + conditions
array). Each rule has expected_wr, confidence_tier, trade_mechanism,
sub_regime_constraint, etc.

### Existing signal_history.json (current schema v5)

Production scanner writes signals to signal_history.json with 67
fields per signal. Here's the most recent signal as a reference:

```json
{sample_signal_str}
```

Notable fields: action, age, attempt_number, date, direction, entry,
exit_date, generation, grade, id, layer, outcome, pivot_date,
pivot_price, regime, regime_score, result, scan_price, scan_time,
score, sector, signal, stop, symbol, target_price, vol_confirm, vol_q.

### Cell playbooks (reference)

{cell_playbooks_index}

### Rule schema v4.1 (relevant fields for barcode)

Rules have:
- id, type (kill/boost/warn/watch), match_fields, conditions[], verdict
- expected_wr, confidence_tier (HIGH/MEDIUM/LOW), trade_mechanism
- sub_regime_constraint
- production_ready, priority

## Constraints

- JSON structure with FIXED required fields + optional context fields
- Compact (production scanner produces 100s/day; archive size matters)
- Self-documenting (each barcode contains its own context — no
  external lookup required for trader to interpret)
- Backward-compatible with current signal_history.json structure
  (extends, not replaces)
- Must support these new concepts:
  - regime + sub_regime (computed at signal-fire-time)
  - matched_rule_ids[] (rules from v4.1 that fired)
  - verdict (TAKE_FULL / TAKE_SMALL / WATCH / SKIP / REJECT)
  - confidence_tier (B1's 4-tier: confident_hot, boundary_hot, etc.)
  - calibrated_wr (with band)
  - name_cap_status (e.g., "OK" / "REPEAT" — same name fired in 6 days)
  - date_cap_status ("OK" / "CORRELATED" — multiple signals same day)
  - sector_concentration_status ("OK" / "OVER" — too many in one sector)

## Deliverables

Produce 4 deliverables, each as a fenced code block tagged with the
deliverable filename.

### 1. `barcode_format_v1.md`

Format specification. Required sections:
- Barcode object structure (JSON schema-style)
- Required fields (with types + descriptions)
- Optional context fields
- Field ordering convention
- Self-documentation strategy (how each barcode explains itself)
- Backward compatibility notes (how barcode extends signal_history)

### 2. `barcode_examples.json`

8-10 worked examples covering all cell types:
- Bear UP_TRI hot — TAKE_FULL with sector boost
- Bear UP_TRI cold — TAKE_FULL via cascade rule
- Bull UP_TRI recovery_bull — TAKE_FULL with filter
- Bull DOWN_TRI late_bull × wk3 — TAKE_SMALL
- Bull BULL_PROXY healthy_bull × 20d=high — TAKE_FULL
- Choppy UP_TRI breadth=med × vol=High — TAKE_FULL
- Choppy BULL_PROXY — REJECT (entire cell killed)
- Choppy DOWN_TRI Friday — SKIP
- Optional: cap status edge cases (name repeat, sector concentration)

### 3. `integration_spec.md`

Production scanner integration approach:
- Where in scan flow does barcode get generated?
- What writes the barcode (which Python module)?
- How does barcode integrate with signal_history.json (append /
  augment / parallel file)?
- Performance considerations (latency budget per signal)
- Rollout plan (Phase A: shadow write; Phase B: replace; Phase C:
  remove old fields)

### 4. `validation_test_cases.json`

8-10 test inputs for verification:
- For each input: signal features + market state + expected matched
  rules + expected barcode output
- Format: list of {{input: {{...}}, expected: {{...}}}} objects
- Cover happy paths AND edge cases (no rules matched, multiple
  conflicting rules, cap statuses)

## Output format

Each deliverable in a fenced code block tagged with its filename:

```barcode_format_v1.md
# ...
```

```barcode_examples.json
{{...}}
```

```integration_spec.md
# ...
```

```validation_test_cases.json
{{...}}
```

The script will parse and save each to `L3_opus_output/`.

## Design constraints

- Field names: snake_case
- Booleans for status flags
- ISO-8601 dates
- Use `null` for missing optional fields, never empty string
- Numbers: floats for percentages (0.0-1.0), ints for counts
- Arrays for matched_rule_ids (typically 1-5 elements)
- Embed schema_version field for future migrations
"""

    print(f"  prompt: {len(prompt):,} chars")
    print(f"  approx input tokens: {len(prompt) // 4:,}")
    print(f"\n  calling {OPUS_MODEL} (max_tokens=24000, streaming)...")

    client = Anthropic()
    t0 = time.time()
    with client.messages.stream(
        model=OPUS_MODEL,
        max_tokens=24000,
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
            "caller": "step5_L3_barcode_design",
            "model": OPUS_MODEL,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": total,
        }) + "\n")

    parts = parse_deliverables(text, DELIVERABLES)
    for fname in DELIVERABLES:
        if fname in parts:
            (OUTPUT_DIR / fname).write_text(parts[fname])
            print(f"  ✓ {fname:30s} ({len(parts[fname]):,} chars)")
        else:
            print(f"  ✗ {fname:30s} MISSING")


if __name__ == "__main__":
    main()
