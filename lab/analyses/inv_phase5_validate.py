"""
Phase 5 SUB-BLOCK 5B — Run live validation on Phase 4 survivors.

Pipeline:
  1. Load combinations_lifetime.parquet (5,057 Phase 4 survivors)
  2. Load live_signals_with_features.parquet (200 deduped live signals)
  3. Pre-compute live outcomes for all Phase-4 horizons (D1, D2, D3, D5, D6, D10, D15)
  4. For each survivor: match live signals + classify tier
  5. Save lab/output/combinations_live_validated.parquet

Tier rules per Phase 5 spec:
  VALIDATED   live_n≥10, live_wr ≥ test_wr−5pp AND ≥ baseline+5pp
  PRELIMINARY live_n≥5,  live_wr ≥ test_wr−10pp AND ≥ baseline+3pp
  WATCH       live_n<5, or Bull cohort, or falls through
  REJECTED    live_n≥5 AND (live_wr < baseline OR live_wr < test_wr−15pp)

Run:
    .venv/bin/python lab/analyses/inv_phase5_validate.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402
from live_signal_matcher import (  # noqa: E402
    LiveSignalMatcher, precompute_live_outcomes,
)
from live_validation_engine import (  # noqa: E402
    classify_tier, get_baseline_wr,
)

SURVIVORS_PATH = _LAB_ROOT / "output" / "combinations_lifetime.parquet"
COMBOS_PENDING_PATH = _LAB_ROOT / "output" / "combinations_pending.parquet"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
BASELINES_PATH = _LAB_ROOT / "output" / "baselines.json"
CACHE_DIR = _LAB_ROOT / "cache"
OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_live_validated.parquet"

MAX_RUNTIME_SEC = 30 * 60


def main():
    print("─" * 72)
    print("Phase 5 SUB-BLOCK 5B — Live validation of Phase 4 survivors")
    print("─" * 72)

    t_total = time.time()

    print(f"\nLoading: {SURVIVORS_PATH}")
    survivors = pd.read_parquet(SURVIVORS_PATH)
    print(f"  Phase 4 survivors: {len(survivors)}")

    print(f"Loading: {COMBOS_PENDING_PATH}")
    combos_def = pd.read_parquet(COMBOS_PENDING_PATH)
    # Merge feature_*_id/level into survivors so matcher can read them
    feat_cols = ["feature_a_id", "feature_a_level",
                  "feature_b_id", "feature_b_level",
                  "feature_c_id", "feature_c_level",
                  "feature_d_id", "feature_d_level"]
    survivors = survivors.merge(combos_def[["combo_id"] + feat_cols],
                                    on="combo_id", how="left")

    print(f"Loading: {LIVE_PATH}")
    live = pd.read_parquet(LIVE_PATH)
    print(f"  live signals: {len(live)}")

    print(f"Loading: {BASELINES_PATH}")
    with open(BASELINES_PATH) as fh:
        baselines = json.load(fh)

    # Determine horizons needed
    horizons_needed = sorted({int(h[1:]) for h in survivors["horizon"].unique()})
    print(f"\nPre-computing live outcomes for horizons {horizons_needed}...")
    t0 = time.time()
    outcomes_by_h = precompute_live_outcomes(live, CACHE_DIR, horizons_needed)
    print(f"  done in {time.time() - t0:.1f}s")

    # Build matcher
    registry = FeatureRegistry.load_all()
    matcher = LiveSignalMatcher(live, outcomes_by_h, registry)

    # Iterate combinations
    print(f"\nValidating {len(survivors)} combinations...")
    t0 = time.time()
    rows = []
    for i, (_, combo) in enumerate(survivors.iterrows(), 1):
        elapsed = time.time() - t_total
        if elapsed > MAX_RUNTIME_SEC:
            print(f"\n⚠ HALT: runtime {elapsed/60:.0f}min exceeds "
                  f"{MAX_RUNTIME_SEC/60}min")
            sys.exit(1)
        match = matcher.match_combination(combo.to_dict())
        baseline_wr = get_baseline_wr(baselines, combo["signal_type"],
                                          combo["regime"], combo["horizon"])
        verdict = classify_tier(combo.to_dict(),
                                    {"live_n": match.live_n,
                                     "live_wr": match.live_wr},
                                    baseline_wr)
        rows.append({
            "combo_id": combo["combo_id"],
            "live_n": match.live_n,
            "live_n_wins": match.live_n_wins,
            "live_n_losses": match.live_n_losses,
            "live_n_flat": match.live_n_flat,
            "live_wr": match.live_wr,
            "live_drift_vs_test": verdict.live_drift_vs_test,
            "live_edge_pp": verdict.live_edge_pp,
            "live_tier": verdict.live_tier,
            "cohort_blocked": verdict.cohort_blocked,
            "cohort_match_count": match.cohort_match_count,
            "matched_sample_ids": match.matched_sample_ids,
        })
        if i % 1000 == 0:
            print(f"  {i}/{len(survivors)} validated "
                  f"({time.time() - t0:.1f}s elapsed)")

    print(f"  Validation: {time.time() - t0:.1f}s")
    live_df = pd.DataFrame(rows)
    final = survivors.merge(live_df, on="combo_id", how="left")

    # ── Tier distribution ────────────────────────────────────────────
    print()
    print("═" * 72)
    print("TIER DISTRIBUTION")
    print("═" * 72)
    tier_dist = final["live_tier"].value_counts(dropna=False)
    print(tier_dist.to_string())
    print()
    blocked = int(final["cohort_blocked"].sum())
    print(f"Bull cohort blocked: {blocked}")

    # Per-cohort tier breakdown
    print()
    print("Per-cohort × horizon tier distribution:")
    print(f"{'cohort':<32}{'tier':<14}{'n':>5}")
    for (s, r, h), grp in final.groupby(["signal_type", "regime", "horizon"]):
        cohort_str = f"{s}×{r}×{h}"
        tier_counts = grp["live_tier"].value_counts()
        for tier in ("VALIDATED", "PRELIMINARY", "WATCH", "REJECTED"):
            n = tier_counts.get(tier, 0)
            if n > 0:
                print(f"  {cohort_str:<30}{tier:<14}{n:>5}")

    # ── Save ─────────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Drop matched_sample_ids list-typed col before parquet (or convert)
    final.to_parquet(OUTPUT_PATH, index=False)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_kb:.1f} KB, {len(final)} rows)")

    total_runtime = time.time() - t_total
    print(f"\nTotal Phase 5 runtime: {total_runtime/60:.1f} min")


if __name__ == "__main__":
    main()
