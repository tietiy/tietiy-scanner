"""Phase 3 — label_randomization audit on rule_019.

Two-stage harness audit per consultant Round 8 directive:

STAGE 1 (always): Option B — global won-column shuffle, 100 trials
STAGE 2 (conditional): Option A — rule_019-matching-only shuffle, 100 trials
                       runs only if Stage 1 verdict is AMBIGUOUS

Pass criterion: real lift (+17.22pp) far above shuffled-null
distribution. Under H0 (no edge), shuffled-lift mean ≈ 0pp,
pct_positive ≈ 50%.

Output: lab/factory/oos_validation/output/label_randomization_audit.json

Verdict per stage:
  PASS:      real_lift > p95(shuffle) AND z_score > 3
  FAIL:      real_lift <= mean(shuffle) OR z_score < 1.5
  AMBIGUOUS: 1.5 <= z_score <= 3, OR z>3 but real_lift not above p95
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # already-established project pattern (mirrors _run_walkforward.py)

from walkforward import (  # noqa: E402
    walkforward, build_windows, aggregate_stability, load_data,
    matches_rule, add_derived_features, RULES_PATH,
)

# Constants
RULE_ID = "rule_019_bear_uptri_hot_refinement"
N_TRIALS_STAGE1 = 100
N_TRIALS_STAGE2 = 100
TOL_LIFT_PP = 0.5
TOL_POSITIVE = 0.02
RECORDED_MEAN_LIFT_PP = 17.2208   # from rule_stability_summary: 0.1722080333296446 * 100
RECORDED_PCT_POSITIVE = 0.7826    # from summary: 0.782608695652174

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "label_randomization_audit.json"


def load_rule_019() -> dict:
    """Load rule_019 spec from canonical RULES_PATH."""
    rules = json.loads(RULES_PATH.read_text())["rules"]
    for r in rules:
        if r["id"] == RULE_ID:
            return r
    raise ValueError(f"{RULE_ID} not found in {RULES_PATH}")


def run_walkforward_for_rule(rule: dict, df: pd.DataFrame, windows: list) -> dict:
    """Run walkforward + aggregate_stability for one rule. Returns aggregate dict."""
    results = walkforward(rule, df, windows)
    return aggregate_stability(rule, results)


def distribution_stats(values: list[float]) -> dict:
    """Compute summary stats of a list of floats."""
    arr = np.array(values, dtype=float)
    return {
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr, ddof=1)),
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "p05": float(np.nanpercentile(arr, 5)),
        "p50": float(np.nanpercentile(arr, 50)),
        "p95": float(np.nanpercentile(arr, 95)),
        "all_values": [float(x) if not np.isnan(x) else None for x in arr.tolist()],
    }


def verdict_for_stage(real_lift: float, shuffle_lifts: list[float]) -> dict:
    """Compute z-score, p95 comparison, and PASS/FAIL/AMBIGUOUS decision."""
    arr = np.array([v for v in shuffle_lifts if v is not None and not np.isnan(v)], dtype=float)
    if len(arr) < 5:
        return {
            "z_score_lift": None,
            "real_lift_above_shuffle_p95": False,
            "decision": "FAIL",
            "decision_rationale": f"insufficient valid trials ({len(arr)}); cannot compute null distribution",
        }
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    p95 = float(np.percentile(arr, 95))
    z = (real_lift - mu) / sd if sd > 0 else None

    above_p95 = real_lift > p95

    if z is not None and z > 3 and above_p95:
        decision = "PASS"
        rationale = f"real_lift {real_lift:.4f} > shuffle p95 {p95:.4f}; z={z:.2f}"
    elif z is not None and z < 1.5:
        decision = "FAIL"
        rationale = f"z={z:.2f} < 1.5; real_lift {real_lift:.4f} not distinguishable from null mean {mu:.4f}"
    elif real_lift <= mu:
        decision = "FAIL"
        rationale = f"real_lift {real_lift:.4f} <= shuffle mean {mu:.4f}; rule no better than chance"
    elif z is not None and z > 3 and not above_p95:
        decision = "AMBIGUOUS"
        rationale = f"z={z:.2f} high but real_lift {real_lift:.4f} not above shuffle p95 {p95:.4f}"
    else:
        decision = "AMBIGUOUS"
        rationale = f"z={z:.2f} in 1.5-3 grey zone"

    return {
        "z_score_lift": z,
        "real_lift_above_shuffle_p95": above_p95,
        "decision": decision,
        "decision_rationale": rationale,
    }


def stage_1_global_shuffle(rule_019: dict, df_full: pd.DataFrame, windows: list, n_trials: int) -> dict:
    """Shuffle won column globally, n_trials times."""
    won_original = df_full["won"].values.copy()
    lifts = []
    pct_positives = []
    match_ns = []
    t0 = time.time()
    for seed in range(n_trials):
        np.random.seed(seed)
        df_full["won"] = np.random.permutation(won_original)
        agg = run_walkforward_for_rule(rule_019, df_full, windows)
        lifts.append(agg.get("mean_lift") if agg.get("mean_lift") is not None else float("nan"))
        pct_positives.append(agg.get("pct_positive_windows") if agg.get("pct_positive_windows") is not None else float("nan"))
        match_ns.append(agg.get("mean_match_n", 0))
        if (seed + 1) % 20 == 0:
            print(f"  Stage 1 progress: {seed+1}/{n_trials} ({time.time()-t0:.1f}s)")
    df_full["won"] = won_original  # restore (defensive)
    elapsed = time.time() - t0
    return {
        "n_trials": n_trials,
        "shuffle_lift_distribution": distribution_stats(lifts),
        "shuffle_pct_positive_distribution": distribution_stats(pct_positives),
        "elapsed_seconds": round(elapsed, 2),
        "mean_match_n_avg": float(np.mean(match_ns)),
    }


def stage_2_rule_matching_shuffle(rule_019: dict, df_full: pd.DataFrame, windows: list, n_trials: int) -> dict:
    """Shuffle won within rows that match rule_019 only.

    Per audit spec: identify rows where matches_rule(row, rule_019) is True,
    shuffle the won values WITHIN that subset, leave the rest untouched.
    """
    print("  Stage 2 setup: identifying rule_019-matching rows (one-time)...")
    t0 = time.time()
    mask = df_full.apply(lambda row: matches_rule(row, rule_019), axis=1)
    matching_idx = df_full.index[mask].tolist()
    print(f"    {len(matching_idx)} rows match rule_019; setup took {time.time()-t0:.1f}s")

    won_original = df_full["won"].values.copy()
    matching_won_original = df_full.loc[matching_idx, "won"].values.copy()
    lifts = []
    pct_positives = []
    match_ns = []
    t0 = time.time()
    for seed in range(n_trials):
        np.random.seed(seed)
        df_full["won"] = won_original
        shuffled = np.random.permutation(matching_won_original)
        df_full.loc[matching_idx, "won"] = shuffled
        agg = run_walkforward_for_rule(rule_019, df_full, windows)
        lifts.append(agg.get("mean_lift") if agg.get("mean_lift") is not None else float("nan"))
        pct_positives.append(agg.get("pct_positive_windows") if agg.get("pct_positive_windows") is not None else float("nan"))
        match_ns.append(agg.get("mean_match_n", 0))
        if (seed + 1) % 20 == 0:
            print(f"  Stage 2 progress: {seed+1}/{n_trials} ({time.time()-t0:.1f}s)")
    df_full["won"] = won_original  # restore
    elapsed = time.time() - t0
    return {
        "n_trials": n_trials,
        "n_matching_rows": int(len(matching_idx)),
        "shuffle_lift_distribution": distribution_stats(lifts),
        "shuffle_pct_positive_distribution": distribution_stats(pct_positives),
        "elapsed_seconds": round(elapsed, 2),
        "mean_match_n_avg": float(np.mean(match_ns)),
    }


def main():
    print("=" * 60)
    print(f"label_randomization audit on {RULE_ID}")
    print("=" * 60)

    print("\nLoading data + rule + windows...")
    df_full = load_data()  # add_derived_features incl. won, sub_regime
    rule_019 = load_rule_019()
    windows = build_windows(df_full)
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  windows: {len(windows)}")
    print(f"  rule_019: {rule_019['match_fields']} + sub_regime={rule_019.get('sub_regime_constraint')}")

    print("\nSANITY CHECK #1: reproduce baseline on REAL data")
    real_agg = run_walkforward_for_rule(rule_019, df_full, windows)
    real_mean_lift_pp = real_agg["mean_lift"] * 100 if real_agg["mean_lift"] is not None else None
    real_pct_positive = real_agg["pct_positive_windows"]
    print(f"  reproduced mean_lift: {real_mean_lift_pp:.4f}pp (recorded: {RECORDED_MEAN_LIFT_PP}pp; tol ±{TOL_LIFT_PP}pp)")
    print(f"  reproduced pct_positive: {real_pct_positive:.4f} (recorded: {RECORDED_PCT_POSITIVE}; tol ±{TOL_POSITIVE})")

    reproduction_ok = (
        real_mean_lift_pp is not None
        and abs(real_mean_lift_pp - RECORDED_MEAN_LIFT_PP) <= TOL_LIFT_PP
        and real_pct_positive is not None
        and abs(real_pct_positive - RECORDED_PCT_POSITIVE) <= TOL_POSITIVE
    )

    if not reproduction_ok:
        print("\n  ✗ baseline reproduction FAILED — STOPPING")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps({
            "rule_id": RULE_ID,
            "baseline": {
                "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
                "recorded_pct_positive": RECORDED_PCT_POSITIVE,
                "reproduced_mean_lift_pp": real_mean_lift_pp,
                "reproduced_pct_positive": real_pct_positive,
                "reproduction_ok": False,
                "tolerance_lift_pp": TOL_LIFT_PP,
                "tolerance_positive": TOL_POSITIVE,
            },
            "stage_1_option_B_global_shuffle": {"ran": False, "skipped_reason": "baseline reproduction failed"},
            "stage_2_option_A_rule_matching_shuffle": {"ran": False, "skipped_reason": "baseline reproduction failed"},
        }, indent=2))
        sys.exit(1)
    print("  ✓ baseline reproduced within tolerance")

    print(f"\nSTAGE 1: Option B — global won-shuffle, {N_TRIALS_STAGE1} trials")
    stage1 = stage_1_global_shuffle(rule_019, df_full, windows, N_TRIALS_STAGE1)
    real_lift = real_agg["mean_lift"]  # decimal form, e.g. 0.172
    stage1_verdict = verdict_for_stage(real_lift, stage1["shuffle_lift_distribution"]["all_values"])
    pct_pos_verdict = verdict_for_stage(real_pct_positive, stage1["shuffle_pct_positive_distribution"]["all_values"])
    stage1["verdict"] = {
        **stage1_verdict,
        "z_score_positive": pct_pos_verdict["z_score_lift"],
    }
    print(f"  Stage 1 decision: {stage1['verdict']['decision']}")
    print(f"  rationale: {stage1['verdict']['decision_rationale']}")

    stage2_block = {"ran": False, "skipped_reason": f"stage 1 {stage1['verdict']['decision']}"}
    if stage1["verdict"]["decision"] == "AMBIGUOUS":
        stage2_block = {"ran": False, "skipped_reason": "stage 1 AMBIGUOUS — awaiting explicit user approval before Stage 2"}

    out = {
        "rule_id": RULE_ID,
        "baseline": {
            "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
            "recorded_pct_positive": RECORDED_PCT_POSITIVE,
            "reproduced_mean_lift_pp": real_mean_lift_pp,
            "reproduced_pct_positive": real_pct_positive,
            "reproduction_ok": True,
            "tolerance_lift_pp": TOL_LIFT_PP,
            "tolerance_positive": TOL_POSITIVE,
        },
        "stage_1_option_B_global_shuffle": stage1,
        "stage_2_option_A_rule_matching_shuffle": stage2_block,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, indent=2))
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"\nFinal Stage 1 decision: {stage1['verdict']['decision']}")


if __name__ == "__main__":
    main()
