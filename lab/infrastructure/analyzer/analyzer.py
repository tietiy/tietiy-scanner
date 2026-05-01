"""
Analyzer orchestrator — full pipeline:
  Phase 1-5 outputs → unified patterns → evidence vectors → scored patterns
  → tier classifications → barcodes.json + patterns_full.json + findings.md

Used by inv_analyzer_first_run.py.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from llm_client import LLMClient  # noqa: E402
from pattern_unifier import unify_combinations, UnifiedPattern  # noqa: E402
from evidence_aggregator import aggregate_evidence  # noqa: E402
from pattern_scorer import score_all_patterns  # noqa: E402
from tier_classifier import classify_all  # noqa: E402
from emission import (  # noqa: E402
    emit_barcodes_json, emit_patterns_full_json, emit_findings_synthesis,
)


def run_analyzer(
        survivors_path: Path,
        combos_pending_path: Path,
        live_validated_path: Path,
        importance_path: Path,
        baselines_path: Path,
        out_barcodes_path: Path,
        out_patterns_full_path: Path,
        out_findings_path: Path,
        llm_client: Optional[LLMClient] = None,
        verbose: bool = True) -> dict:
    """End-to-end analyzer pipeline. Returns run summary dict."""
    t_total = time.time()
    if llm_client is None:
        llm_client = LLMClient()

    if verbose:
        print("─" * 72)
        print("Analyzer pipeline")
        print("─" * 72)

    # ── Step 1: Load inputs ──────────────────────────────────────────
    if verbose:
        print(f"\n[1/8] Loading Phase 1-5 outputs...")
    survivors = pd.read_parquet(survivors_path)
    combos_def = pd.read_parquet(combos_pending_path)
    feat_cols = ["feature_a_id", "feature_a_level", "feature_b_id",
                  "feature_b_level", "feature_c_id", "feature_c_level",
                  "feature_d_id", "feature_d_level"]
    survivors = survivors.merge(combos_def[["combo_id"] + feat_cols],
                                    on="combo_id", how="left")
    live_p5 = pd.read_parquet(live_validated_path)
    with open(importance_path) as fh:
        importance = json.load(fh)
    with open(baselines_path) as fh:
        baselines = json.load(fh)
    if verbose:
        print(f"  Phase 4 survivors: {len(survivors)}")
        print(f"  Phase 5 entries: {len(live_p5)}")

    # ── Step 2: Unify patterns ───────────────────────────────────────
    if verbose:
        print(f"\n[2/8] Unifying combinations into patterns...")
    t0 = time.time()
    unified = unify_combinations(survivors)
    if verbose:
        print(f"  unified patterns: {len(unified)} "
              f"(compression {len(survivors)/max(1,len(unified)):.1f}x, "
              f"{time.time()-t0:.1f}s)")

    # ── Step 3: Aggregate evidence ──────────────────────────────────
    if verbose:
        print(f"\n[3/8] Aggregating evidence per pattern...")
    t0 = time.time()
    evidences = aggregate_evidence(unified, survivors, live_p5,
                                       importance, baselines)
    if verbose:
        print(f"  evidence vectors: {len(evidences)} "
              f"({time.time()-t0:.1f}s)")

    # ── Step 4: Score patterns (LLM mechanism calls) ─────────────────
    if verbose:
        print(f"\n[4/8] Scoring patterns (LLM mechanism evaluation)...")
        # Cost projection check after first 50
        n_total = len(evidences)
        # We don't know cost until we run — surface periodic updates instead
    t0 = time.time()
    scored = score_all_patterns(evidences, llm_client, progress_every=20)
    if verbose:
        print(f"  scored: {len(scored)} ({time.time()-t0:.1f}s)")
        print(f"  LLM calls: {llm_client.total_calls} "
              f"(cache hits: {llm_client.cache_hits}, "
              f"cost: ${llm_client.total_cost:.3f})")

    # ── Step 5: Classify tiers ───────────────────────────────────────
    if verbose:
        print(f"\n[5/8] Classifying tiers...")
    t0 = time.time()
    classified = classify_all(scored)
    tier_dist: dict[str, int] = {}
    for p in classified:
        t = p["tier_classification"]["tier"]
        tier_dist[t] = tier_dist.get(t, 0) + 1
    if verbose:
        print(f"  tier distribution: {tier_dist}")

    # ── Step 6: Emit barcodes.json ───────────────────────────────────
    if verbose:
        print(f"\n[6/8] Emitting barcodes.json (production-facing)...")
    metadata = {
        "phase_1_input": str(survivors_path),
        "phase_5_input": str(live_validated_path),
        "tier_distribution": tier_dist,
    }
    barcodes_payload = emit_barcodes_json(classified, out_barcodes_path,
                                              metadata)
    if verbose:
        print(f"  saved: {out_barcodes_path} "
              f"({len(barcodes_payload['barcodes'])} barcodes)")

    # ── Step 7: Emit patterns_full.json ──────────────────────────────
    if verbose:
        print(f"\n[7/8] Emitting patterns_full.json (analyzer-internal)...")
    pf_payload = emit_patterns_full_json(classified, out_patterns_full_path,
                                              metadata)
    if verbose:
        print(f"  saved: {out_patterns_full_path}")

    # ── Step 8: Emit findings synthesis ──────────────────────────────
    if verbose:
        print(f"\n[8/8] Emitting findings synthesis (LLM single-shot)...")
    fs_summary = emit_findings_synthesis(classified, out_findings_path,
                                              llm_client, metadata)
    if verbose:
        print(f"  saved: {out_findings_path}")

    total_runtime = time.time() - t_total
    summary = {
        "n_unified_patterns": len(classified),
        "tier_distribution": tier_dist,
        "n_barcodes_emitted": len(barcodes_payload["barcodes"]),
        "llm_total_calls": llm_client.total_calls,
        "llm_cache_hits": llm_client.cache_hits,
        "llm_total_cost_usd": llm_client.total_cost,
        "total_runtime_seconds": total_runtime,
    }
    if verbose:
        print()
        print("═" * 72)
        print("ANALYZER RUN SUMMARY")
        print("═" * 72)
        for k, v in summary.items():
            print(f"  {k}: {v}")
    return summary
