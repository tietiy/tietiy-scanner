"""Phase 3 Step 3.4 — universe_perturbation audit on rule_019.

Tests whether rule_019's edge is broad-based or concentrated in a few symbols.
For N in [1, 3, 5, 10, 20], drop rule_019 matches from the top-N symbols by
pnl contribution, re-run walkforward, observe lift trajectory.

Reference distribution (DECIMAL form): Stage 1 shuffle_lift_distribution.

Verdict (overall):
  PASS:                  lift at N=20 > 0.5 * real_lift AND > shuffle_p95
  FAIL:                  lift at N=3  < shuffle_p95 (edge gone in 3 symbols)
  LOW-WINDOW-AMBIGUOUS:  N=20 has < 5 windows with any rule_019 match
                          (suppresses PASS — not statistically meaningful)
  AMBIGUOUS:             otherwise

Verdict precedence: FAIL > LOW-WINDOW-AMBIGUOUS > PASS > AMBIGUOUS.

Output: lab/factory/oos_validation/output/universe_perturbation_audit.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # mirrors Stage 1 / Step 3.3 pattern

from walkforward import (  # noqa: E402
    walkforward, build_windows, aggregate_stability, load_data, matches_rule, RULES_PATH,
)

# ============================================================
# Constants
# ============================================================
RULE_ID = "rule_019_bear_uptri_hot_refinement"

RECORDED_MEAN_LIFT_PP = 17.2208
RECORDED_PCT_POSITIVE = 0.7826
TOL_LIFT_PP = 0.5
TOL_POSITIVE = 0.02

PROFIT_COL = "pnl_pct"
N_TRIALS_LIST = [1, 3, 5, 10, 20]
SCOPE = "option_A_drop_rule_matches_only"
LOW_WINDOW_THRESHOLD = 5  # n_windows_with_match below this → statistical-meaningfulness warning

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "universe_perturbation_audit.json"
REFERENCE_FILE = OUTPUT_DIR / "label_randomization_audit.json"


# ============================================================
# Format helpers
# ============================================================
def _fmt_pp(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.4f}pp"


def _fmt_dec(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.6f}"


def _fmt_pct(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val) * 100:.2f}%"


# ============================================================
# Loaders
# ============================================================
def load_rule_019() -> dict:
    rules = json.loads(RULES_PATH.read_text())["rules"]
    for r in rules:
        if r["id"] == RULE_ID:
            return r
    raise ValueError(f"{RULE_ID} not found in {RULES_PATH}")


def load_reference_shuffle_stats() -> dict:
    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Reference distribution not found at {REFERENCE_FILE}. "
            "Run audit_label_randomization.py first (Stage 1)."
        )
    payload = json.loads(REFERENCE_FILE.read_text())
    dist = payload["stage_1_option_B_global_shuffle"]["shuffle_lift_distribution"]
    return {
        "shuffle_mean": float(dist["mean"]),
        "shuffle_std": float(dist["std"]),
        "shuffle_p95": float(dist["p95"]),
        "shuffle_max": float(dist["max"]),
        "n_trials": int(payload["stage_1_option_B_global_shuffle"]["n_trials"]),
    }


# ============================================================
# Symbol contribution ranking
# ============================================================
def compute_symbol_contributions(df: pd.DataFrame, rule: dict) -> tuple[pd.DataFrame, pd.Series]:
    """For each symbol, compute rule_019 contribution metrics.

    NaN-handling (EXPLICIT — no implicit pandas NaN→0 reliance):
      - pnl_sum:        sum over rows with pnl_pct notna (excludes OPEN only).
                        Includes DAY6_FLAT outcomes since they have meaningful pnl.
      - n_matches:      count of rule_019 matches with pnl_pct notna
                        (= same denominator as pnl_sum).
      - won_sum:        sum over rows with won notna (excludes OPEN + DAY6_FLAT).
                        DAY6_FLAT does NOT contribute since `won` is NaN there.
      - n_won_resolved: count of rule_019 matches with won notna
                        (subset of n_matches; n_matches - n_won_resolved = DAY6_FLAT count).

    Symbols with zero rule_019 matches are excluded.
    Returns (contrib_df, match_mask). contrib_df sorted desc by pnl_sum.
    """
    print("  applying matches_rule (one-time)...")
    match_mask = df.apply(lambda row: matches_rule(row, rule), axis=1)
    df_matches = df[match_mask]

    # pnl-resolved subset (excludes OPEN only)
    df_pnl = df_matches[df_matches[PROFIT_COL].notna()]
    pnl_sum = df_pnl.groupby("symbol")[PROFIT_COL].sum().rename("pnl_sum")
    n_matches = df_pnl.groupby("symbol").size().rename("n_matches")

    # won-resolved subset (excludes OPEN + DAY6_FLAT)
    df_won = df_matches[df_matches["won"].notna()]
    won_sum = df_won.groupby("symbol")["won"].sum().rename("won_sum")
    n_won_resolved = df_won.groupby("symbol").size().rename("n_won_resolved")

    contrib = (
        pd.concat([pnl_sum, won_sum, n_won_resolved, n_matches], axis=1)
        .fillna({"won_sum": 0, "n_won_resolved": 0})  # symbol with all-DAY6_FLAT matches
        .sort_values("pnl_sum", ascending=False)
    )
    contrib["n_won_resolved"] = contrib["n_won_resolved"].astype(int)
    contrib["n_matches"] = contrib["n_matches"].astype(int)
    return contrib, match_mask


# ============================================================
# Trial mechanics
# ============================================================
def drop_top_n_matches(df: pd.DataFrame, match_mask: pd.Series,
                        top_symbols: list[str]) -> tuple[pd.DataFrame, int]:
    """Drop rows where rule_019 matches AND symbol is in top_symbols. Other rows untouched."""
    drop_mask = match_mask & df["symbol"].isin(top_symbols)
    return df[~drop_mask].copy(), int(drop_mask.sum())


def run_walkforward_for_rule(rule: dict, df: pd.DataFrame, windows: list) -> dict:
    results = walkforward(rule, df, windows)
    return aggregate_stability(rule, results)


# ============================================================
# Per-trial summary
# ============================================================
def trial_summary(N: int, dropped_symbols: list[str], n_dropped_rows: int, agg: dict,
                  real_lift: float, shuffle_p95: float) -> dict:
    lift = agg.get("mean_lift")
    pct_pos = agg.get("pct_positive_windows")
    n_windows_with_match = int(agg.get("n_windows_with_match", 0))
    mean_match_n = agg.get("mean_match_n")

    if lift is None or (isinstance(lift, float) and np.isnan(lift)):
        ratio = None
        above_p95 = False
    else:
        ratio = float(lift) / real_lift if real_lift != 0 else None
        above_p95 = float(lift) > shuffle_p95

    low_window_warning = n_windows_with_match < LOW_WINDOW_THRESHOLD

    return {
        "N": N,
        "dropped_symbols": dropped_symbols,
        "n_rule_019_matches_dropped": n_dropped_rows,
        "remaining_lift": lift,
        "remaining_lift_pp": (lift * 100) if lift is not None else None,
        "remaining_pct_positive_windows": pct_pos,
        "n_windows_with_match": n_windows_with_match,
        "mean_match_n": mean_match_n,
        "lift_ratio_vs_real": ratio,
        "lift_above_shuffle_p95": above_p95,
        "low_window_count_warning": low_window_warning,
    }


# ============================================================
# Overall verdict
# ============================================================
def overall_verdict(trials: dict, real_lift: float, shuffle_p95: float) -> dict:
    t3 = trials.get("N_3", {})
    t20 = trials.get("N_20", {})
    n3_lift = t3.get("remaining_lift")
    n20_lift = t20.get("remaining_lift")
    n20_low_window = bool(t20.get("low_window_count_warning", False))
    n20_windows = int(t20.get("n_windows_with_match", 0))

    # FAIL check first
    if n3_lift is not None and not (isinstance(n3_lift, float) and np.isnan(n3_lift)) \
            and float(n3_lift) < shuffle_p95:
        return {
            "decision": "FAIL",
            "rationale": (
                f"lift at N=3 ({_fmt_dec(n3_lift)}) < shuffle_p95 ({_fmt_dec(shuffle_p95)}) "
                f"— edge gone after dropping just 3 symbols"
            ),
        }

    # Low-window-count override at N=20: blocks PASS, demotes to AMBIGUOUS
    if n20_low_window:
        # Identify all trials that tripped the warning, for diagnostic context
        tripped_Ns = [
            int(k.split("_")[1]) for k in trials.keys()
            if trials[k].get("low_window_count_warning", False)
        ]
        tripped_Ns_sorted = sorted(tripped_Ns)
        return {
            "decision": "AMBIGUOUS",
            "rationale": (
                f"N=20 has only {n20_windows} window(s) with any rule_019 match "
                f"(< {LOW_WINDOW_THRESHOLD}); lift {_fmt_dec(n20_lift)} not "
                f"statistically meaningful enough to call PASS. "
                f"Trials with low_window_count_warning: N={tripped_Ns_sorted}"
            ),
        }

    # PASS check
    if (n20_lift is not None
            and not (isinstance(n20_lift, float) and np.isnan(n20_lift))
            and float(n20_lift) > 0.5 * real_lift
            and float(n20_lift) > shuffle_p95):
        return {
            "decision": "PASS",
            "rationale": (
                f"lift at N=20 ({_fmt_dec(n20_lift)}) > 0.5 * real_lift "
                f"({_fmt_dec(0.5 * real_lift)}) AND > shuffle_p95 "
                f"({_fmt_dec(shuffle_p95)})"
            ),
        }

    return {
        "decision": "AMBIGUOUS",
        "rationale": (
            f"N=3 above shuffle_p95 (no FAIL) but N=20 ({_fmt_dec(n20_lift)}) "
            f"below 0.5*real_lift ({_fmt_dec(0.5 * real_lift)}) or shuffle_p95 "
            f"({_fmt_dec(shuffle_p95)})"
        ),
    }


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print(f"universe_perturbation audit on {RULE_ID}")
    print(f"scope: {SCOPE}")
    print(f"rank_metric: sum({PROFIT_COL})")
    print("=" * 60)
    t_total = time.time()

    print("\nLoading data + rule + windows + reference...")
    df_full = load_data()
    rule_019 = load_rule_019()
    windows = build_windows(df_full)
    ref = load_reference_shuffle_stats()
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  windows: {len(windows)}")
    print(f"  rule_019: {rule_019['match_fields']} + sub_regime={rule_019.get('sub_regime_constraint')}")
    print(
        f"  reference (Stage 1, decimal): mean={_fmt_dec(ref['shuffle_mean'])}, "
        f"std={_fmt_dec(ref['shuffle_std'])}, p95={_fmt_dec(ref['shuffle_p95'])}, "
        f"max={_fmt_dec(ref['shuffle_max'])}"
    )

    # --- Sanity check
    print("\nSANITY CHECK: reproduce baseline on REAL data")
    real_agg = run_walkforward_for_rule(rule_019, df_full, windows)
    real_lift = real_agg.get("mean_lift")
    real_pct_positive = real_agg.get("pct_positive_windows")
    real_lift_pp = (real_lift * 100) if real_lift is not None else None
    print(f"  reproduced mean_lift: {_fmt_pp(real_lift_pp)} (recorded: {RECORDED_MEAN_LIFT_PP}pp; tol ±{TOL_LIFT_PP}pp)")
    print(f"  reproduced pct_positive: {_fmt_dec(real_pct_positive)} (recorded: {RECORDED_PCT_POSITIVE}; tol ±{TOL_POSITIVE})")
    reproduction_ok = (
        real_lift_pp is not None
        and abs(real_lift_pp - RECORDED_MEAN_LIFT_PP) <= TOL_LIFT_PP
        and real_pct_positive is not None
        and abs(real_pct_positive - RECORDED_PCT_POSITIVE) <= TOL_POSITIVE
    )
    if not reproduction_ok:
        print("\n  ✗ baseline reproduction FAILED — STOPPING")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps({
            "rule_id": RULE_ID,
            "scope": SCOPE,
            "baseline": {
                "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
                "recorded_pct_positive": RECORDED_PCT_POSITIVE,
                "reproduced_mean_lift_pp": real_lift_pp,
                "reproduced_pct_positive": real_pct_positive,
                "reproduction_ok": False,
            },
            "skipped_reason": "baseline reproduction failed",
        }, indent=2))
        sys.exit(1)
    print("  ✓ baseline reproduced within tolerance")

    # --- Symbol contributions (top 20)
    print("\nSYMBOL CONTRIBUTIONS — rule_019 matches, ranked by sum(pnl_pct)")
    t0 = time.time()
    contrib, match_mask = compute_symbol_contributions(df_full, rule_019)
    print(f"  total symbols with rule_019 matches: {len(contrib):,}")
    print(f"  total rule_019 matches in df: {int(match_mask.sum()):,}")
    print(f"  ({time.time()-t0:.1f}s)")

    top20 = contrib.head(20)
    print("\n  Top 20 symbols by pnl contribution:")
    print(f"  {'rank':>4}  {'symbol':<14}  {'pnl_sum':>10}  {'won_sum':>8}  {'n_won_res':>9}  {'n_matches':>9}")
    for i, (sym, row) in enumerate(top20.iterrows(), start=1):
        print(
            f"  {i:>4}  {sym:<14}  {row['pnl_sum']:>10.4f}  "
            f"{row['won_sum']:>8.0f}  {int(row['n_won_resolved']):>9d}  {int(row['n_matches']):>9d}"
        )

    top_symbols_ranked = top20.index.tolist()
    top20_records = [
        {
            "rank": i + 1,
            "symbol": sym,
            "pnl_sum": float(row["pnl_sum"]),
            "won_sum": float(row["won_sum"]),
            "n_won_resolved": int(row["n_won_resolved"]),
            "n_matches": int(row["n_matches"]),
        }
        for i, (sym, row) in enumerate(top20.iterrows())
    ]

    # --- Trials
    print("\nPERTURBATION TRIALS")
    trials: dict = {}
    for N in N_TRIALS_LIST:
        t0 = time.time()
        symbols_to_drop = top_symbols_ranked[:N]
        df_filtered, n_dropped_rows = drop_top_n_matches(df_full, match_mask, symbols_to_drop)
        agg = run_walkforward_for_rule(rule_019, df_filtered, windows)
        summary = trial_summary(N, symbols_to_drop, n_dropped_rows, agg, real_lift, ref["shuffle_p95"])
        trials[f"N_{N}"] = summary
        print(
            f"  N={N:>2}  dropped={n_dropped_rows:>4} matches  "
            f"lift={_fmt_pp(summary['remaining_lift_pp'])}  "
            f"ratio={_fmt_dec(summary['lift_ratio_vs_real'])}  "
            f"above_p95={summary['lift_above_shuffle_p95']}  "
            f"n_win_match={summary['n_windows_with_match']}  "
            f"({time.time()-t0:.1f}s)"
        )
        if summary["low_window_count_warning"]:
            print(
                f"  ⚠ WARNING N={N}: only {summary['n_windows_with_match']} window(s) "
                f"with any rule_019 match (< {LOW_WINDOW_THRESHOLD}); lift may not be "
                f"statistically meaningful"
            )

    # --- Overall verdict
    overall = overall_verdict(trials, real_lift, ref["shuffle_p95"])
    print(f"\nOVERALL VERDICT: {overall['decision']} — {overall['rationale']}")

    # --- Persist
    elapsed = round(time.time() - t_total, 2)
    out = {
        "rule_id": RULE_ID,
        "scope": SCOPE,
        "rank_metric": f"sum({PROFIT_COL})",
        "n_trials_list": N_TRIALS_LIST,
        "low_window_threshold": LOW_WINDOW_THRESHOLD,
        "baseline": {
            "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
            "recorded_pct_positive": RECORDED_PCT_POSITIVE,
            "reproduced_mean_lift": real_lift,
            "reproduced_mean_lift_pp": real_lift_pp,
            "reproduced_pct_positive": real_pct_positive,
            "reproduction_ok": True,
            "tolerance_lift_pp": TOL_LIFT_PP,
            "tolerance_positive": TOL_POSITIVE,
        },
        "shuffle_reference": {
            "source": "label_randomization_audit.json:stage_1_option_B_global_shuffle.shuffle_lift_distribution",
            "form": "decimal",
            **ref,
        },
        "top_20_symbols": top20_records,
        "trials": trials,
        "overall_verdict": overall,
        "elapsed_seconds": elapsed,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total elapsed: {elapsed}s")


if __name__ == "__main__":
    main()
