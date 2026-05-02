"""Step 4 — Generic Opus runner for either Path (1 disciplined or 2 trust).

Usage: python _run_opus_path.py path1   OR   python _run_opus_path.py path2

Inputs (path1 example):
  - lab/factory/opus_iteration/path1_disciplined/path1_opus_prompt.md
  - lab/factory/opus_iteration/path1_disciplined/path1_*.md (reference docs)
  - lab/factory/opus_iteration/path1_disciplined/step3_validation_report.json
  - lab/factory/opus_synthesis/input_package/  (shared base inputs)

Outputs (path1 example):
  - lab/factory/opus_iteration/path1_disciplined/output/<5 deliverables>
  - lab/factory/opus_iteration/path1_disciplined/_opus_raw.md
"""
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


SHARED_INPUT_DIR = _LAB_ROOT / "factory" / "opus_synthesis" / "input_package"
COST_LOG_PATH = _LAB_ROOT / "cache" / "llm" / "cost_log.jsonl"

OPUS_MODEL = "claude-opus-4-7"
OPUS_INPUT_RATE = 15.0
OPUS_OUTPUT_RATE = 75.0


PATH_CONFIGS = {
    "path1": {
        "label": "Path 1 Disciplined",
        "dir": "path1_disciplined",
        "prompt_file": "path1_opus_prompt.md",
        "deliverables": [
            "unified_rules_path1.json",
            "precedence_logic_path1.md",
            "b1_b2_coupling_path1.md",
            "validation_predictions_path1.json",
            "integration_notes_path1.md",
        ],
    },
    "path2": {
        "label": "Path 2 Trust-Opus",
        "dir": "path2_trust",
        "prompt_file": "path2_opus_prompt.md",
        "deliverables": [
            "unified_rules_path2.json",
            "precedence_logic_path2.md",
            "b1_b2_coupling_path2.md",
            "validation_predictions_path2.json",
            "integration_notes_path2.md",
        ],
    },
}


def collect_path_specific_inputs(path_dir: Path) -> str:
    """Read all path-specific reference docs (path1_*.md, etc.)."""
    parts = []
    for f in sorted(path_dir.iterdir()):
        if f.is_file() and (f.suffix == ".md" or f.suffix == ".json") and f.stem != "_opus_raw":
            # Skip the prompt file itself (handled separately)
            if f.name.endswith("_opus_prompt.md"):
                continue
            parts.append(f"\n\n---\n\n## REFERENCE DOC: {f.name}\n\n")
            parts.append(f.read_text())
    return "".join(parts)


def collect_shared_inputs() -> str:
    """Collect the shared Step 3 input package."""
    parts = ["\n\n---\n\n# SHARED STEP 3 INPUT PACKAGE\n\n"]
    for path in sorted(SHARED_INPUT_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SHARED_INPUT_DIR)
        parts.append(f"\n\n---\n\n## FILE: {rel}\n\n")
        try:
            parts.append(path.read_text())
        except UnicodeDecodeError:
            parts.append(f"<binary file {rel}; skipped>")
    return "".join(parts)


def parse_deliverables(text: str, deliverables: list[str]) -> dict[str, str]:
    """Extract content between deliverable tags. Handles nested code fences."""
    out: dict[str, str] = {}
    starts: list[tuple[int, str]] = []
    for fname in deliverables:
        marker = f"```{fname}\n"
        idx = text.find(marker)
        if idx >= 0:
            starts.append((idx, fname))
    starts.sort()

    for i, (start, fname) in enumerate(starts):
        content_start = start + len(f"```{fname}\n")
        if i + 1 < len(starts):
            content_end = starts[i + 1][0]
        else:
            content_end = len(text)
        block = text[content_start:content_end]
        block = re.sub(r"\n```\s*\n*$", "", block.rstrip()) + "\n"
        out[fname] = block
    return out


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in PATH_CONFIGS:
        print("usage: _run_opus_path.py {path1|path2}")
        sys.exit(1)

    path_key = sys.argv[1]
    cfg = PATH_CONFIGS[path_key]
    path_dir = _HERE / cfg["dir"]
    output_dir = path_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = path_dir / "_opus_raw.md"

    prompt_path = path_dir / cfg["prompt_file"]
    if not prompt_path.exists():
        print(f"ERROR: prompt not found: {prompt_path}")
        sys.exit(1)

    prompt = prompt_path.read_text()
    path_specific = collect_path_specific_inputs(path_dir)
    shared = collect_shared_inputs()

    full_user = f"{prompt}\n\n---\n\n# PATH-SPECIFIC REFERENCE DOCS\n\n{path_specific}\n\n{shared}"

    print(f"=== {cfg['label']} ===")
    print(f"  prompt: {prompt_path.name} ({len(prompt):,} chars)")
    print(f"  path-specific docs: {len(path_specific):,} chars")
    print(f"  shared input package: {len(shared):,} chars")
    print(f"  combined user message: {len(full_user):,} chars")
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
    raw_path.write_text(text)
    print(f"  raw response: {raw_path} ({len(text):,} chars)")

    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    cost_in = in_tok / 1e6 * OPUS_INPUT_RATE
    cost_out = out_tok / 1e6 * OPUS_OUTPUT_RATE
    total_cost = cost_in + cost_out

    print(f"\n  === USAGE + COST ===")
    print(f"  input tokens:  {in_tok:,} (${cost_in:.3f})")
    print(f"  output tokens: {out_tok:,} (${cost_out:.3f})")
    print(f"  TOTAL: ${total_cost:.3f}")

    with COST_LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "caller": f"opus_iteration_step4_{path_key}",
            "model": OPUS_MODEL,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cost_usd": total_cost,
        }) + "\n")

    print(f"\n  === PARSING DELIVERABLES ===")
    parts = parse_deliverables(text, cfg["deliverables"])
    for fname in cfg["deliverables"]:
        if fname in parts:
            (output_dir / fname).write_text(parts[fname])
            print(f"  ✓ {fname:40s} ({len(parts[fname]):,} chars)")
        else:
            print(f"  ✗ {fname:40s} MISSING")

    rules_path = output_dir / cfg["deliverables"][0]
    if rules_path.exists():
        try:
            data = json.loads(rules_path.read_text())
            n_rules = len(data.get("rules", []))
            print(f"\n  rules JSON parses OK: {n_rules} rules, schema v{data.get('schema_version')}")
        except json.JSONDecodeError as e:
            print(f"\n  ⚠ rules JSON fails to parse: {e}")

    print("\n  done.")


if __name__ == "__main__":
    main()
