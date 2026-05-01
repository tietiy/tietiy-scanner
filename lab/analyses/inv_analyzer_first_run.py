"""
Analyzer first run — execute full pipeline on Phase 1-5 outputs.

Outputs:
  • lab/output/barcodes.json (production-facing)
  • lab/output/patterns_full.json (analyzer-internal)
  • lab/analyses/ANALYZER_findings.md (human digest, LLM-synthesized)

Cost projection: ~544 patterns × ~$0.0014/call ≈ $0.75 estimated.
HALT cap: $30 cost / 2hr runtime.

Run:
    .venv/bin/python lab/analyses/inv_analyzer_first_run.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from analyzer import run_analyzer  # noqa: E402
from llm_client import LLMClient  # noqa: E402

SURVIVORS_PATH = _LAB_ROOT / "output" / "combinations_lifetime.parquet"
COMBOS_PENDING_PATH = _LAB_ROOT / "output" / "combinations_pending.parquet"
LIVE_VALIDATED_PATH = _LAB_ROOT / "output" / "combinations_live_validated.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
BASELINES_PATH = _LAB_ROOT / "output" / "baselines.json"

OUT_BARCODES = _LAB_ROOT / "output" / "barcodes.json"
OUT_PATTERNS_FULL = _LAB_ROOT / "output" / "patterns_full.json"
OUT_FINDINGS = _LAB_ROOT / "analyses" / "ANALYZER_findings.md"

COST_HALT_USD = 30.0
RUNTIME_HALT_SEC = 2 * 60 * 60


def main():
    print("Analyzer FIRST RUN")
    print(f"  inputs:")
    for p in (SURVIVORS_PATH, COMBOS_PENDING_PATH, LIVE_VALIDATED_PATH,
                IMPORTANCE_PATH, BASELINES_PATH):
        if not p.exists():
            sys.exit(f"FATAL: missing input {p}")
        print(f"    {p}")

    llm = LLMClient()
    summary = run_analyzer(
        survivors_path=SURVIVORS_PATH,
        combos_pending_path=COMBOS_PENDING_PATH,
        live_validated_path=LIVE_VALIDATED_PATH,
        importance_path=IMPORTANCE_PATH,
        baselines_path=BASELINES_PATH,
        out_barcodes_path=OUT_BARCODES,
        out_patterns_full_path=OUT_PATTERNS_FULL,
        out_findings_path=OUT_FINDINGS,
        llm_client=llm,
    )

    # Cost guardrail check
    if summary["llm_total_cost_usd"] > COST_HALT_USD:
        print(f"\n⚠ COST CHECK: total cost "
              f"${summary['llm_total_cost_usd']:.2f} > "
              f"${COST_HALT_USD:.2f} HALT threshold")


if __name__ == "__main__":
    main()
