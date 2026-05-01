"""
Phase 4 SUB-BLOCK 4D — Filter pipeline (iteration 2) + tier classification.

Iteration 2 changes (post-Phase 4E sample review):
  • Filter 5 changed from Bonferroni to Benjamini-Hochberg FDR (q=0.05) —
    populates small cohorts (Bear/DOWN_TRI/BULL_PROXY) that Bonferroni
    silenced; 5% false-discovery-rate is acceptable for exploratory phase.
  • Filter 3 tightened: drift ≤ 12pp (was 15pp) — drops marginal
    walk-forward-unstable combinations.
  • New Filter 4.5: max 1 calendar feature per combination
    ({day_of_week, day_of_month_bucket}) — prevents multi-day artifact rules
    where Tue AND Fri both pass.
  • Tier classification stays edge-based (edge_pp_test = test_wr −
    baseline_wr already cohort-specific via Phase 3 baselines.json).

Filter order:
  Filter 1 (n floor):    train AND validate AND test n ≥ 30
  Filter 2 (edge):       test_wr − baseline_wr ≥ 5pp
  Filter 3 (drift):      |train_wr − test_wr| ≤ 12pp        ← tightened
  Filter 4 (Wilson):     wilson_lower_95(test_wr) ≥ baseline_wr + 2pp
  Filter 4.5 (calendar): ≤ 1 of {day_of_week, day_of_month_bucket}  ← NEW
  Filter 5 (FDR):        Benjamini-Hochberg q=0.05            ← swapped
  Filter 6 (tier):       edge_pp ≥ 15pp → S; ≥10 → A; ≥5 → B

Surfaces filter funnel statistics. Output: lab/output/combinations_lifetime.parquet
(survivors only).

Run-mode:
    .venv/bin/python lab/analyses/inv_phase4_filter.py <input.parquet>
        [--combos <combos_def.parquet>] [--out <output.parquet>]
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

# Filter thresholds (iteration 2)
N_FLOOR = 30
EDGE_FLOOR_PP = 0.05
DRIFT_CEIL_PP = 0.12  # tightened from 0.15
WILSON_FLOOR_PP_OVER_BASELINE = 0.02
FDR_Q = 0.05  # Benjamini-Hochberg false-discovery-rate cap

# Calendar features (iteration 2 constraint: max 1 per combo)
CALENDAR_FEATURE_IDS = frozenset({"day_of_week", "day_of_month_bucket"})
MAX_CALENDAR_PER_COMBO = 1

# Tier thresholds (edge_pp = test_wr - baseline_wr; cohort-specific via baselines.json)
TIER_S_PP = 0.15
TIER_A_PP = 0.10
TIER_B_PP = 0.05


def _benjamini_hochberg(p_values: np.ndarray, q: float = FDR_Q) -> np.ndarray:
    """Benjamini-Hochberg FDR procedure. Returns boolean mask of accepted
    (rejected-null = significant) hypotheses.

    Procedure: sort p-values ascending; find largest k where p[k] ≤ (k/m)·q.
    All hypotheses with rank ≤ k are accepted (significant)."""
    m = len(p_values)
    if m == 0:
        return np.zeros(0, dtype=bool)
    order = np.argsort(p_values)
    sorted_p = p_values[order]
    critical = (np.arange(1, m + 1) / m) * q
    below = sorted_p <= critical
    if not below.any():
        return np.zeros(m, dtype=bool)
    largest_k = int(np.where(below)[0].max())
    accept = np.zeros(m, dtype=bool)
    accept[order[: largest_k + 1]] = True
    return accept


def _count_calendar_features_per_row(row: pd.Series) -> int:
    """Count calendar features (day_of_week, day_of_month_bucket) used in
    a combination row. Inspects feature_a..d_id slots."""
    count = 0
    for slot in ("a", "b", "c", "d"):
        fid = row.get(f"feature_{slot}_id")
        if pd.notna(fid) and fid in CALENDAR_FEATURE_IDS:
            count += 1
    return count


def apply_filters(tested: pd.DataFrame,
                    n_total_combos_tested: int,
                    combos_definitions: pd.DataFrame = None
                    ) -> tuple[pd.DataFrame, dict]:
    """Apply iteration-2 filter pipeline. Returns (survivors_df, funnel_stats).

    `combos_definitions`: optional DataFrame with combo_id + feature_a..d_id;
    used by Filter 4.5 (calendar feature limit). If None, calendar filter
    is skipped (with a warning in the funnel).
    """
    funnel = {"input": len(tested)}

    df = tested.copy()
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

    # Filter 3: drift bound |train_wr - test_wr| ≤ 12pp (iter-2 tightened)
    f3_mask = df["drift_train_test_pp"].abs() <= DRIFT_CEIL_PP
    df = df[f3_mask].copy()
    funnel["after_filter_3_drift"] = len(df)

    # Filter 4: Wilson lower bound ≥ baseline_wr + 2pp
    f4_mask = (df["test_wilson_lower_95"]
                 >= df["baseline_wr"] + WILSON_FLOOR_PP_OVER_BASELINE)
    df = df[f4_mask].copy()
    funnel["after_filter_4_wilson"] = len(df)

    # Filter 4.5: calendar feature limit (iter-2 NEW)
    if combos_definitions is not None and len(df) > 0:
        feat_cols = [c for c in (
            "feature_a_id", "feature_b_id",
            "feature_c_id", "feature_d_id"
        ) if c in combos_definitions.columns]
        df = df.merge(combos_definitions[["combo_id"] + feat_cols],
                        on="combo_id", how="left")
        cal_counts = df.apply(_count_calendar_features_per_row, axis=1)
        df = df[cal_counts <= MAX_CALENDAR_PER_COMBO].copy()
        df = df.drop(columns=feat_cols, errors="ignore")
        funnel["after_filter_4_5_calendar"] = len(df)
    else:
        funnel["after_filter_4_5_calendar"] = len(df)
        funnel["calendar_filter_skipped"] = True

    # Filter 5: Benjamini-Hochberg FDR (iter-2 swapped from Bonferroni)
    if len(df) > 0:
        p_vals = df["test_p_value_vs_baseline"].fillna(1.0).values
        accept = _benjamini_hochberg(p_vals, q=FDR_Q)
        df = df[accept].copy()
    funnel["after_filter_5_fdr"] = len(df)
    funnel["fdr_q"] = float(FDR_Q)

    # Filter 6: tier classification (cohort-specific via edge_pp baseline-relative)
    df["tier"] = "B"
    df.loc[df["edge_pp_test"] >= TIER_A_PP, "tier"] = "A"
    df.loc[df["edge_pp_test"] >= TIER_S_PP, "tier"] = "S"
    funnel["tier_S"] = int((df["tier"] == "S").sum())
    funnel["tier_A"] = int((df["tier"] == "A").sum())
    funnel["tier_B"] = int((df["tier"] == "B").sum())

    return df, funnel


def print_funnel(funnel: dict) -> None:
    print("\n" + "═" * 72)
    print("FILTER FUNNEL (iteration 2)")
    print("═" * 72)
    rows = [
        ("Input combinations", funnel["input"]),
        ("(upstream skipped)", funnel["upstream_skipped"]),
        ("After upstream skip filter", funnel["after_skip_filter"]),
        ("After Filter 1 (n ≥ 30 per period)", funnel["after_filter_1_n_floor"]),
        ("After Filter 2 (edge_pp ≥ 5pp)", funnel["after_filter_2_edge"]),
        ("After Filter 3 (|drift| ≤ 12pp)", funnel["after_filter_3_drift"]),
        ("After Filter 4 (Wilson lower ≥ baseline + 2pp)",
         funnel["after_filter_4_wilson"]),
        ("After Filter 4.5 (≤1 calendar feature per combo)",
         funnel["after_filter_4_5_calendar"]),
        ("After Filter 5 (Benjamini-Hochberg FDR q=0.05)",
         funnel["after_filter_5_fdr"]),
    ]
    prev = None
    for label, count in rows:
        if prev is None or "skip" in label.lower():
            print(f"  {label:<55} {count:>10}")
        else:
            drop = prev - count
            drop_pct = drop / prev * 100 if prev > 0 else 0
            print(f"  {label:<55} {count:>10}  (−{drop} / {drop_pct:.1f}%)")
        prev = count
    print(f"  FDR q: {funnel['fdr_q']}")
    if funnel.get("calendar_filter_skipped"):
        print("  ⚠ calendar filter skipped (no combos_definitions provided)")
    print(f"\nTier distribution among survivors:")
    print(f"  Tier S (edge ≥ 15pp): {funnel['tier_S']}")
    print(f"  Tier A (10-15pp):     {funnel['tier_A']}")
    print(f"  Tier B (5-10pp):      {funnel['tier_B']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT),
                      help="walk-forward tested combinations parquet")
    ap.add_argument("--combos",
                      default=str(_LAB_ROOT / "output" / "combinations_pending.parquet"),
                      help="combinations_pending.parquet (for calendar filter)")
    ap.add_argument("--out", default=str(DEFAULT_OUTPUT),
                      help="output survivors parquet")
    args = ap.parse_args()

    in_path = Path(args.input_path)
    out_path = Path(args.out)
    combos_path = Path(args.combos)

    print(f"Loading: {in_path}")
    tested = pd.read_parquet(in_path)
    n_total = len(tested)
    print(f"  {n_total} combinations tested")

    combos_def = None
    if combos_path.exists():
        print(f"Loading combos definitions: {combos_path}")
        combos_def = pd.read_parquet(combos_path)
    else:
        print(f"  ⚠ {combos_path} not found; calendar filter will skip")

    t0 = time.time()
    survivors, funnel = apply_filters(tested, n_total, combos_def)
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
