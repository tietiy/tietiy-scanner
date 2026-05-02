"""OP2 — Run Opus 4.7 rule synthesis on the Step 3 input package."""
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


INPUT_PACKAGE_DIR = _HERE / "input_package"
PROMPT_PATH = _HERE / "opus_prompt.md"
OUTPUT_DIR = _HERE / "output"
RAW_RESPONSE_PATH = _HERE / "_opus_raw_response.md"
COST_LOG_PATH = _LAB_ROOT / "cache" / "llm" / "cost_log.jsonl"

OPUS_MODEL = "claude-opus-4-7"
OPUS_INPUT_RATE = 15.0   # $/M tokens
OPUS_OUTPUT_RATE = 75.0  # $/M tokens

DELIVERABLES = [
    "unified_rules_v4.json",
    "precedence_logic.md",
    "b1_b2_coupling_analysis.md",
    "validation_predictions.json",
    "integration_notes.md",
]


def collect_input_package() -> str:
    """Concatenate all input package files into a single context block."""
    parts = ["# Input Package — Step 3\n\n"]
    for path in sorted(INPUT_PACKAGE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(INPUT_PACKAGE_DIR)
        parts.append(f"\n\n---\n\n## FILE: {rel}\n\n")
        try:
            parts.append(path.read_text())
        except UnicodeDecodeError:
            parts.append(f"<binary file {rel}; skipped>")
    return "".join(parts)


def parse_deliverables(text: str) -> dict[str, str]:
    """Extract content between deliverable tags.

    Each deliverable starts with ```<filename>\n and ends just before the
    next deliverable tag (or end of text). The closing ``` is found by
    looking for the LAST ``` before the next deliverable starts —
    handles nested code fences inside markdown content.
    """
    out: dict[str, str] = {}
    starts: list[tuple[int, str]] = []
    for fname in DELIVERABLES:
        marker = f"```{fname}\n"
        idx = text.find(marker)
        if idx >= 0:
            starts.append((idx, fname))
    starts.sort()

    for i, (start, fname) in enumerate(starts):
        content_start = start + len(f"```{fname}\n")
        # Find end: just before the next deliverable's opening tag, or
        # end of text. Then strip trailing closing ``` line.
        if i + 1 < len(starts):
            content_end = starts[i + 1][0]
        else:
            content_end = len(text)
        block = text[content_start:content_end]
        # Strip trailing ``` line + whitespace
        block = re.sub(r"\n```\s*\n*$", "", block.rstrip()) + "\n"
        out[fname] = block
    return out


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    package = collect_input_package()
    prompt = PROMPT_PATH.read_text()

    full_user = f"{prompt}\n\n---\n\n# INPUT PACKAGE BELOW\n\n{package}"

    print(f"  input package chars: {len(package):,}")
    print(f"  prompt chars: {len(prompt):,}")
    print(f"  combined chars: {len(full_user):,}")
    print(f"  approx input tokens: {len(full_user) // 4:,}")

    client = Anthropic()
    print(f"\n  calling {OPUS_MODEL} (max_tokens=32000, streaming)...")
    t0 = time.time()
    with client.messages.stream(
        model=OPUS_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": full_user}],
    ) as stream:
        text_parts = []
        for chunk in stream.text_stream:
            text_parts.append(chunk)
        response = stream.get_final_message()
    text = "".join(text_parts)
    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s")
    RAW_RESPONSE_PATH.write_text(text)
    print(f"  raw response saved: {RAW_RESPONSE_PATH} ({len(text):,} chars)")

    # Cost tracking
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    cost_in = in_tok / 1e6 * OPUS_INPUT_RATE
    cost_out = out_tok / 1e6 * OPUS_OUTPUT_RATE
    total_cost = cost_in + cost_out

    print("\n  === USAGE + COST ===")
    print(f"  input tokens:  {in_tok:,} (${cost_in:.3f})")
    print(f"  output tokens: {out_tok:,} (${cost_out:.3f})")
    print(f"  TOTAL: ${total_cost:.3f}")

    # Append to cost log
    COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "caller": "opus_synthesis_step3",
            "model": OPUS_MODEL,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": total_cost,
        }) + "\n")

    # Parse deliverables
    print("\n  === PARSING DELIVERABLES ===")
    parts = parse_deliverables(text)
    for fname in DELIVERABLES:
        if fname in parts:
            (OUTPUT_DIR / fname).write_text(parts[fname])
            n = len(parts[fname])
            print(f"  ✓ {fname:38s} ({n:,} chars)")
        else:
            print(f"  ✗ {fname:38s} MISSING")

    # Spot check on unified_rules_v4.json
    rules_path = OUTPUT_DIR / "unified_rules_v4.json"
    if rules_path.exists():
        try:
            data = json.loads(rules_path.read_text())
            n_rules = len(data.get("rules", []))
            print(f"\n  unified_rules_v4.json parses OK: {n_rules} rules")
            print(f"  schema_version: {data.get('schema_version')}")
        except json.JSONDecodeError as e:
            print(f"\n  ⚠ unified_rules_v4.json fails to parse: {e}")

    print("\n  done.")


if __name__ == "__main__":
    main()
