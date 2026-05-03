"""D2 — Opus 4.7 deep dive synthesis call."""
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

CONTEXT_DIR = _HERE / "opus_context_package"
OUTPUT_DIR = _HERE / "output"
RAW_PATH = _HERE / "_d2_opus_raw.md"
COST_LOG = _LAB_ROOT / "cache" / "llm" / "cost_log.jsonl"

OPUS_MODEL = "claude-opus-4-7"

DELIVERABLES = [
    "independent_diagnosis.md",
    "path_critique.md",
    "unconventional_alternatives.md",
    "recommended_combination.md",
    "brutal_assessment.md",
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


def collect_context() -> str:
    parts = ["# Context Package — TIE TIY Quantitative Trading System Decision Point\n\n"]
    for p in sorted(CONTEXT_DIR.iterdir()):
        if not p.is_file():
            continue
        parts.append(f"\n\n---\n\n## FILE: {p.name}\n\n")
        try:
            parts.append(p.read_text())
        except UnicodeDecodeError:
            parts.append(f"<binary; skipped>")
    return "".join(parts)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    context = collect_context()
    print(f"  context: {len(context):,} chars (~{len(context)//4:,} tokens)")

    system_prompt = (
        "You are an independent expert reviewing a quantitative trading "
        "system at decision point. Provide critical analysis. Surface what's "
        "missing. Challenge assumptions. The trader has paused live trading "
        "to do this Lab work and is at risk of perfectionism, sunk-cost, "
        "premature deployment, and AI-tool dependency. Your job is to be "
        "useful, not polite. If your conclusion is 'this system is over-"
        "engineered relative to expected returns,' say so. If your conclusion "
        "is 'the trader should trade simpler systems and abandon Lab work,' "
        "say so. This is the trader's last AI deep dive before deployment. "
        "Make it count. Take time. Use adaptive thinking high effort."
    )

    user_prompt = (
        "TIE TIY systematic trading system at decision point. Lab pipeline\n"
        "complete with 37 production-ready rules. Production backtest reveals\n"
        "8 READY_TO_SHIP, 29 NEEDS_LIVE_DATA — data-starvation diagnosed.\n\n"
        "Read the context package thoroughly:\n"
        "- Lab pipeline summary (file 01)\n"
        "- 37 final rules (file 02)\n"
        "- Production backtest results (file 06)\n"
        "- Operator constraints (file 50)\n"
        "- My 10-path out-of-box analysis with recommended combination (file 51)\n"
        "- Plus production data, brain decisions, trader expectations,\n"
        "  known issues, methodology findings\n\n"
        "Produce 5 deliverables. Each in a fenced code block tagged with\n"
        "the deliverable filename:\n\n"
        "## 1. `independent_diagnosis.md`\n"
        "- Your independent analysis of the core problem\n"
        "- Do you agree with the data-starvation framing?\n"
        "- Are there other diagnoses I missed (over-fitting, regime drift,\n"
        "  validation methodology flaw, etc.)?\n"
        "- What's the SINGLE biggest risk that could break this system in\n"
        "  first 6 months?\n\n"
        "## 2. `path_critique.md`\n"
        "- Critique each of my 10 paths\n"
        "- Which paths am I overrating?\n"
        "- Which paths am I underrating?\n"
        "- Are there paths I missed entirely?\n"
        "- Specifically: critique paper trading (Path 9) — is 60 days enough?\n"
        "  Are there hidden risks?\n\n"
        "## 3. `unconventional_alternatives.md`\n"
        "- At least 3 paths I didn't consider\n"
        "- For each: what problem it solves, what it requires, realistic outcome\n"
        "- Be willing to propose unusual ideas\n"
        "- Honest about feasibility\n\n"
        "## 4. `recommended_combination.md`\n"
        "- Your recommended path combination (may differ from mine)\n"
        "- Sequencing rationale\n"
        "- Realistic timeline estimate\n"
        "- Key risks per phase\n"
        "- Decision criteria at each gate\n\n"
        "## 5. `brutal_assessment.md`\n"
        "- What does the trader need to hear that they don't want to hear?\n"
        "- Are they at risk of perfectionism preventing deployment?\n"
        "- Are they at risk of premature deployment due to trading-restart\n"
        "  pressure?\n"
        "- What's the honest probability this system produces meaningful\n"
        "  returns in first 12 months?\n"
        "- What single decision should they NOT delegate to AI tools, including\n"
        "  you?\n\n"
        "CONSTRAINTS:\n"
        "- Be willing to disagree with my analysis\n"
        "- Don't be polite at the expense of accuracy\n"
        "- Identify cognitive biases in my framing\n"
        "- Distinguish what's actually addressable vs irreducible uncertainty\n"
        "- This is the trader's last AI deep dive before deployment. Make it count.\n\n"
        "Output format — exactly 5 fenced blocks tagged with filename:\n\n"
        "```independent_diagnosis.md\n# ...\n```\n\n"
        "```path_critique.md\n# ...\n```\n\n"
        "```unconventional_alternatives.md\n# ...\n```\n\n"
        "```recommended_combination.md\n# ...\n```\n\n"
        "```brutal_assessment.md\n# ...\n```\n\n"
        "Context package follows.\n\n"
    ) + context

    print(f"  total user prompt: {len(user_prompt):,} chars")
    print(f"  approx input tokens: {len(user_prompt) // 4:,}")
    print(f"\n  calling {OPUS_MODEL} (max_tokens=32000, streaming)...")

    client = Anthropic()
    t0 = time.time()
    with client.messages.stream(
        model=OPUS_MODEL,
        max_tokens=32000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
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

    print(f"\n  === USAGE + COST ===")
    print(f"  input tokens:  {in_tok:,} (${cost_in:.3f})")
    print(f"  output tokens: {out_tok:,} (${cost_out:.3f})")
    print(f"  TOTAL: ${total:.3f}")

    with COST_LOG.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "caller": "out_of_box_deep_dive_D2",
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


if __name__ == "__main__":
    main()
