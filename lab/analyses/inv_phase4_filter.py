"""
Phase 4 SUB-BLOCK 4D — 6-filter pipeline + tier classification.

Applies filters in order to walk-forward-tested combinations:
  Filter 1 (n floor):    train AND validate AND test n ≥ 30
  Filter 2 (edge):       test_wr − baseline_wr ≥ 5pp (Tier B floor)
  Filter 3 (drift):      |train_wr − test_wr| ≤ 15pp
  Filter 4 (Wilson):     wilson_lower_95(test_wr) ≥ baseline_wr + 2pp
  Filter 5 (significance): p-value < 0.01 / N_combos_tested  (Bonferroni)
  Filter 6 (tier):       edge_pp ≥ 15pp → S; ≥10 → A; ≥5 → B

Surfaces filter funnel statistics. Output: lab/output/combinations_lifetime.parquet
(survivors only).

Run-mode:
    .venv/bin/python lab/analyses/inv_phase4_filter.py <input.parquet> [--out <output.parquet>]
where input.parquet is walk-forward output (combinations_tested.parquet).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent

DEFAULT_INPUT = _LAB_ROOT / "output" / "combinations_tested.parquet"
DEFAULT_OUTPUT = _LAB_ROOT / "output" / "combinations_lifetime.parquet"

# Filter thresholds
N_FLOOR = 30
EDGE_FLOOR_PP = 0.05
DRIFT_CEIL_PP = 0.15
WILSON_FLOOR_PP_OVER_BASELINE = 0.02
ALPHA = 0.01

# Tier thresholds
TIER_S_PP = 0.15
TIER_A_PP = 0.10
TIER_B_PP = 0.05


def apply_filters(tested: pd.DataFrame,
                    n_total_combos_tested: int) -> tuple[pd.DataFrame, dict]:
    """Apply 6-filter pipeline. Returns (survivors_df, funnel_stats)."""
    funnel = {"input": len(tested)}

    df = tested.copy()
    # Strip out skip_reason rows immediately — they failed an upstream check
    skipped = df["skip_reason"].notna()
    funnel["upstream_skipped"] = int(skipped.sum())
    df = df[~skipped].copy()
    funnel["after_skip_filter"] = len(df)

    # Filter 1: n floor in train AND validate AND test
    f1_mask = ((df["train_n"] >= N_FLOOR)
                 & (df["validate_n"] >= N_FLOOR)
                 & (df["test_n"] >= N_FLOOR))
    df = df[f1_mask].copy()
    funnel["after_filter_1_n_floor"] = len(df)

    # Filter 2: edge magnitude ≥ 5pp
    f2_mask = df["edge_pp_test"] >= EDGE_FLOOR_PP
    df = df[f2_mask].copy()
    funnel["after_filter_2_edge"] = len(df)

    # Filter 3: drift bound |train_wr - test_wr| ≤ 15pp
    f3_mask = df["drift_train_test_pp"].abs() <= DRIFT_CEIL_PP
    df = df[f3_mask].copy()
    funnel["after_filter_3_drift"] = len(df)

    # Filter 4: Wilson lower bound ≥ baseline_wr + 2pp
    f4_mask = (df["test_wilson_lower_95"]
                 >= df["baseline_wr"] + WILSON_FLOOR_PP_OVER_BASELINE)
    df = df[f4_mask].copy()
    funnel["after_filter_4_wilson"] = len(df)

    # Filter 5: Bonferroni-corrected p-value
    bonferroni_threshold = ALPHA / max(1, n_total_combos_tested)
    f5_mask = df["test_p_value_vs_baseline"] < bonferroni_threshold
    df = df[f5_mask].copy()
    funnel["after_filter_5_bonferroni"] = len(df)
    funnel["bonferroni_threshold"] = float(bonferroni_threshold)

    # Filter 6: tier classification (just labels, no removal)
    df["tier"] = "B"  # default
    df.loc[df["edge_pp_test"] >= TIER_A_PP, "tier"] = "A"
    df.loc[df["edge_pp_test"] >= TIER_S_PP, "tier"] = "S"
    funnel["tier_S"] = int((df["tier"] == "S").sum())
    funnel["tier_A"] = int((df["tier"] == "A").sum())
    funnel["tier_B"] = int((df["tier"] == "B").sum())

    return df, funnel


def print_funnel(funnel: dict) -> None:
    print("\n" + "═" * 72)
    print("FILTER FUNNEL")
    print("═" * 72)
    rows = [
        ("Input combinations", funnel["input"]),
        ("(upstream skipped)", funnel["upstream_skipped"]),
        ("After upstream skip filter", funnel["after_skip_filter"]),
        ("After Filter 1 (n ≥ 30 per period)", funnel["after_filter_1_n_floor"]),
        ("After Filter 2 (edge_pp ≥ 5pp)", funnel["after_filter_2_edge"]),
        ("After Filter 3 (|drift| ≤ 15pp)", funnel["after_filter_3_drift"]),
        ("After Filter 4 (Wilson lower ≥ baseline + 2pp)",
         funnel["after_filter_4_wilson"]),
        ("After Filter 5 (Bonferroni p < α/N)",
         funnel["after_filter_5_bonferroni"]),
    ]
    prev = None
    for label, count in rows:
        if prev is None or "skip" in label.lower():
            print(f"  {label:<50} {count:>10}")
        else:
            drop = prev - count
            drop_pct = drop / prev * 100 if prev > 0 else 0
            print(f"  {label:<50} {count:>10}  (−{drop} / {drop_pct:.1f}%)")
        prev = count
    print(f"  Bonferroni α / N: {funnel['bonferroni_threshold']:.2e}")
    print(f"\nTier distribution among survivors:")
    print(f"  Tier S (edge ≥ 15pp): {funnel['tier_S']}")
    print(f"  Tier A (10-15pp):     {funnel['tier_A']}")
    print(f"  Tier B (5-10pp):      {funnel['tier_B']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT),
                      help="walk-forward tested combinations parquet")
    ap.add_argument("--out", default=str(DEFAULT_OUTPUT),
                      help="output survivors parquet")
    args = ap.parse_args()

    in_path = Path(args.input_path)
    out_path = Path(args.out)

    print(f"Loading: {in_path}")
    tested = pd.read_parquet(in_path)
    n_total = len(tested)
    print(f"  {n_total} combinations tested")

    t0 = time.time()
    survivors, funnel = apply_filters(tested, n_total)
    elapsed = time.time() - t0
    print(f"\nFiltered in {elapsed:.2f}s")

    print_funnel(funnel)

    if len(survivors) == 0:
        print("\n⚠ HALT: 0 survivors — filter thresholds too aggressive?")
        sys.exit(1)
    if len(survivors) > 5_000:
        print(f"\n⚠ NOTE: {len(survivors)} survivors > 5K (insufficient pruning?)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    survivors.to_parquet(out_path, index=False)
    print(f"\nSaved: {out_path} ({len(survivors)} survivors)")


if __name__ == "__main__":
    main()
