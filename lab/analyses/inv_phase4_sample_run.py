"""
Phase 4 SUB-BLOCK 4E — Sample run on 5 cohorts for user validation gate.

Runs combination_generator → walk_forward_tester → inv_phase4_filter pipeline
on a 5-cohort subset (UP_TRI×Bear×D10, UP_TRI×Bull×D10, UP_TRI×Choppy×D6,
DOWN_TRI×Bear×D2, BULL_PROXY×Choppy×D5).

Surfaces per-cohort funnel + top 5 survivors per cohort + tier distribution.

User reviews:
  • Are surviving combinations mechanically sensible?
  • Is the tier distribution reasonable (not all-S which would suggest leakage)?
  • Is walk-forward stability OK (drift mostly < 10pp on survivors)?

If gate passes → user approves Phase 4F full run.
If gate fails → diagnose before full run.

Run:
    .venv/bin/python lab/analyses/inv_phase4_sample_run.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402
from combination_generator import generate_combinations  # noqa: E402
from walk_forward_tester import (  # noqa: E402
    run_walk_forward, precompute_outcomes,
)
from inv_phase4_filter import apply_filters, print_funnel  # noqa: E402

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
BASELINES_PATH = _LAB_ROOT / "output" / "baselines.json"
CACHE_DIR = _LAB_ROOT / "cache"
OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_sample.parquet"
TESTED_OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_sample_tested.parquet"

# Five cohort cells for the sample
SAMPLE_CELLS = [
    ("UP_TRI", "Bear", "D10"),
    ("UP_TRI", "Bull", "D10"),
    ("UP_TRI", "Choppy", "D6"),
    ("DOWN_TRI", "Bear", "D2"),
    ("BULL_PROXY", "Choppy", "D5"),
]


def main():
    print("─" * 72)
    print("Phase 4 SUB-BLOCK 4E — Sample run on 5 cohorts")
    print("─" * 72)

    t_total = time.time()

    print(f"\nLoading: {ENRICHED_PATH}")
    signals = pd.read_parquet(ENRICHED_PATH)
    signals["scan_date"] = pd.to_datetime(signals["scan_date"])

    print(f"Loading: {IMPORTANCE_PATH}")
    with open(IMPORTANCE_PATH) as fh:
        importance = json.load(fh)

    print(f"Loading: {BASELINES_PATH}")
    with open(BASELINES_PATH) as fh:
        baselines = json.load(fh)

    registry = FeatureRegistry.load_all()

    # Generate combinations for sample cells only
    print(f"\nGenerating combinations for {len(SAMPLE_CELLS)} sample cells:")
    combos = generate_combinations(signals, importance, registry,
                                       SAMPLE_CELLS, verbose=False)
    print(f"  Total: {len(combos)} combinations across sample cells")
    print(f"  Per-cell breakdown:")
    for (s, r, h) in SAMPLE_CELLS:
        n = len(combos[(combos["signal_type"] == s)
                          & (combos["regime"] == r)
                          & (combos["horizon"] == h)])
        print(f"    {s:<12} × {r:<8} × {h:<3}: {n:>6}")

    # Pre-compute outcomes for all needed horizons
    needed_horizons = sorted({int(h[1:]) for _, _, h in SAMPLE_CELLS})
    print(f"\nPre-computing outcomes for horizons {needed_horizons}...")
    t0 = time.time()
    outcomes_by_h = precompute_outcomes(signals, needed_horizons, CACHE_DIR)
    print(f"  Outcome compute: {time.time()-t0:.1f}s")

    # Walk-forward test all sample combinations
    print(f"\nWalk-forward testing {len(combos)} combinations...")
    t0 = time.time()
    tested = run_walk_forward(combos, signals, outcomes_by_h, baselines,
                                  registry, progress_every=10_000)
    print(f"  Walk-forward: {time.time()-t0:.1f}s")

    # Save walk-forward output BEFORE filtering (so filter iterations are fast)
    TESTED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tested.to_parquet(TESTED_OUTPUT_PATH, index=False)
    print(f"  saved {TESTED_OUTPUT_PATH} ({len(tested)} rows)")

    # Apply iter-2 filter pipeline (FDR + drift 12pp + calendar limit)
    print(f"\nApplying 6-filter pipeline (iteration 2)...")
    survivors, funnel = apply_filters(tested, len(tested),
                                          combos_definitions=combos)
    print_funnel(funnel)

    # Per-cohort breakdown of survivors
    print(f"\nPer-cohort survivor distribution:")
    print(f"  {'cohort':<32} {'tested':>7}  {'survivors':>9}  {'tier_S':>7}  {'tier_A':>7}  {'tier_B':>7}")
    for (s, r, h) in SAMPLE_CELLS:
        cell_tested = len(tested[(tested["signal_type"] == s)
                                     & (tested["regime"] == r)
                                     & (tested["horizon"] == h)])
        cell_surv = survivors[(survivors["signal_type"] == s)
                                  & (survivors["regime"] == r)
                                  & (survivors["horizon"] == h)]
        s_count = (cell_surv["tier"] == "S").sum()
        a_count = (cell_surv["tier"] == "A").sum()
        b_count = (cell_surv["tier"] == "B").sum()
        print(f"  {s + ' × ' + r + ' × ' + h:<32} {cell_tested:>7}  "
              f"{len(cell_surv):>9}  {s_count:>7}  {a_count:>7}  {b_count:>7}")

    # Merge with original combo definitions to get feature_a..d info for display
    survivors_with_features = survivors.merge(
        combos[["combo_id", "feature_a_id", "feature_a_level",
                  "feature_b_id", "feature_b_level",
                  "feature_c_id", "feature_c_level",
                  "feature_d_id", "feature_d_level"]],
        on="combo_id", how="left")

    # Top 5 per cell
    print()
    print("═" * 72)
    print("TOP 5 SURVIVORS PER COHORT (by edge_pp_test descending)")
    print("═" * 72)
    for (s, r, h) in SAMPLE_CELLS:
        cell = survivors_with_features[
            (survivors_with_features["signal_type"] == s)
            & (survivors_with_features["regime"] == r)
            & (survivors_with_features["horizon"] == h)
        ].nlargest(5, "edge_pp_test")
        print(f"\n--- {s} × {r} × {h} ---")
        if len(cell) == 0:
            print("  (no survivors)")
            continue
        for _, row in cell.iterrows():
            features = []
            for slot in ("a", "b", "c", "d"):
                fid = row.get(f"feature_{slot}_id")
                lvl = row.get(f"feature_{slot}_level")
                if pd.notna(fid) and pd.notna(lvl):
                    features.append(f"{fid}={lvl}")
            tier = row["tier"]
            print(f"  [{tier}] edge={row['edge_pp_test']*100:.1f}pp  "
                  f"test_wr={row['test_wr']*100:.1f}%  "
                  f"baseline={row['baseline_wr']*100:.1f}%  "
                  f"drift={row['drift_train_test_pp']*100:.1f}pp  "
                  f"n_test={row['test_n']}  "
                  f"wilson_lo={row['test_wilson_lower_95']*100:.1f}%")
            print(f"       features: {' & '.join(features)}")

    # Drift histogram among survivors (verify 12pp ceiling holds)
    if len(survivors) > 0:
        drift_pp = survivors["drift_train_test_pp"].abs() * 100
        print()
        print(f"Drift distribution among {len(survivors)} survivors (test_wr "
              f"vs train_wr):")
        for lo, hi, label in [
            (0.0, 2.0, "0-2pp"), (2.0, 5.0, "2-5pp"),
            (5.0, 8.0, "5-8pp"), (8.0, 10.0, "8-10pp"),
            (10.0, 12.0, "10-12pp"),
        ]:
            n = ((drift_pp >= lo) & (drift_pp < hi)).sum()
            pct = n / len(survivors) * 100
            print(f"  {label:>10}: {n:>4} ({pct:>5.1f}%)")
        max_drift = drift_pp.max()
        print(f"  max drift: {max_drift:.1f}pp (ceiling 12pp)")

    # Calendar feature audit
    if len(survivors) > 0:
        merged = survivors.merge(
            combos[["combo_id", "feature_a_id", "feature_b_id",
                      "feature_c_id", "feature_d_id"]],
            on="combo_id", how="left")
        cal_counts = merged.apply(
            lambda r: sum(1 for slot in "abcd"
                            if pd.notna(r.get(f"feature_{slot}_id"))
                            and r[f"feature_{slot}_id"] in
                            ("day_of_week", "day_of_month_bucket")),
            axis=1)
        print()
        print(f"Calendar features per survivor:")
        for k in (0, 1, 2, 3, 4):
            n = (cal_counts == k).sum()
            if n > 0:
                print(f"  {k} calendar features: {n}")
        print(f"  max per combo: {cal_counts.max()} (ceiling: 1)")

    # Save sample output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    survivors.to_parquet(OUTPUT_PATH, index=False)
    print(f"\nSaved: {OUTPUT_PATH} ({len(survivors)} survivors)")
    total_runtime = time.time() - t_total
    print(f"Total Phase 4E runtime: {total_runtime / 60:.1f} min")

    print()
    print("═" * 72)
    print("USER REVIEW GATE")
    print("═" * 72)
    print("""
Inspect the per-cohort funnel + top 5 survivors above. Verify:

  • Combinations look mechanically plausible (not curve-fit garbage)
  • Tier distribution is reasonable (not 100% Tier S; not 0% Tier B)
  • Walk-forward stability: drift mostly < 10pp on survivors
  • Features cited match the cohort's mechanism intuition
  • Cohorts where 0 survivors emerged: surface for diagnosis

If gate passes → reply 'PHASE 4 SAMPLE APPROVED, proceed to 4F full run'
If gate fails → reply with specific concerns; iterate before 4F""")


if __name__ == "__main__":
    main()
