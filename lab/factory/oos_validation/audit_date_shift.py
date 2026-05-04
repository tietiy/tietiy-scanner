"""Phase 3 Stage 2 — date_shift audit on rule_019.

Tests whether rule_019's recorded edge depends on STRICT temporal alignment of
(scan, won) pairs WITHIN each symbol's time-ordered signal sequence.

For each symbol, sort by scan_date_dt and shift `won` by +1 row (forward) and
-1 row (backward). If the rule's lift collapses into the Stage 1 shuffled-null
band, the rule's edge depends on correct date alignment (= no leakage).
If lift survives or grows, that's evidence of structural leakage / weak
temporal binding.

Reference distribution (DECIMAL form, NOT pp):
  output/label_randomization_audit.json
  stage_1_option_B_global_shuffle.shuffle_lift_distribution.mean ≈ -0.00969
  stage_1_option_B_global_shuffle.shuffle_lift_distribution.std  ≈  0.03632

Verdict per trial (all values in DECIMAL form):
  drop_pct  = (real_lift - shifted_lift) / real_lift
  shifted_z = (shifted_lift - shuffle_mean) / shuffle_std

  PASS:      drop_pct > 0.50 AND shifted_z < 2.0
  FAIL:      drop_pct < 0.10 OR  shifted_lift > real_lift
  AMBIGUOUS: otherwise

Overall:
  BOTH PASS    -> PASS
  EITHER FAIL  -> FAIL
  otherwise    -> AMBIGUOUS

Output: lab/factory/oos_validation/output/date_shift_audit.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # mirrors Stage 1 / _run_walkforward.py pattern

from walkforward import (  # noqa: E402
    walkforward, build_windows, aggregate_stability, load_data, RULES_PATH,
)

# ============================================================
# Constants
# ============================================================
RULE_ID = "rule_019_bear_uptri_hot_refinement"

RECORDED_MEAN_LIFT_PP = 17.2208   # rule_stability_summary: 0.1722080333296446 * 100
RECORDED_PCT_POSITIVE = 0.7826    # rule_stability_summary: 0.782608695652174

TOL_LIFT_PP = 0.5                 # mirrors Stage 1
TOL_POSITIVE = 0.02               # mirrors Stage 1

GROUP_COL = "symbol"              # shift within each symbol's time-ordered series
SORT_COL = "scan_date_dt"         # load_data() derives this datetime64 column

# Verdict thresholds (per spec)
DROP_PCT_PASS = 0.50              # shifted_lift dropped > 50% from real
DROP_PCT_FAIL = 0.10              # shifted_lift dropped < 10% (still near baseline)
Z_PASS = 2.0                      # shifted_z < this -> inside Stage 1 null band

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "date_shift_audit.json"
REFERENCE_FILE = OUTPUT_DIR / "label_randomization_audit.json"


# ============================================================
# Format helpers (avoid f-string conditional-format syntax)
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


def _fmt_z(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.3f}"


# ============================================================
# Loaders
# ============================================================
def load_rule_019() -> dict:
    """Load rule_019 spec from canonical RULES_PATH (mirrors Stage 1)."""
    rules = json.loads(RULES_PATH.read_text())["rules"]
    for r in rules:
        if r["id"] == RULE_ID:
            return r
    raise ValueError(f"{RULE_ID} not found in {RULES_PATH}")


def load_reference_shuffle_stats() -> dict:
    """Hard-coded keys — no auto-detection, no fallback.

    Returns shuffle_mean and shuffle_std in DECIMAL form (matching the form
    written by Stage 1's distribution_stats() into shuffle_lift_distribution).
    """
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
        "shuffle_min": float(dist["min"]),
        "shuffle_max": float(dist["max"]),
        "n_trials": int(payload["stage_1_option_B_global_shuffle"]["n_trials"]),
    }


# ============================================================
# Date-shift mechanics
# ============================================================
def shift_won_by_symbol(df: pd.DataFrame, shift: int, sort_col: str) -> tuple[pd.DataFrame, int]:
    """Shift `won` by `shift` rows within each symbol's time-ordered series.

    Tracks shift-induced NaN drops (rows that HAD a real label pre-shift but
    NaN post-shift) separately from pre-existing OPEN-signal NaNs via the
    `_had_real_won` mask. Only shift-induced NaN rows are dropped from the
    returned dataframe; original OPEN-signal NaN rows pass through unchanged
    so the harness handles them as it does in baseline.

    Returns (df_shifted, n_shift_induced_dropped).
    """
    df = df.copy()
    df["_had_real_won"] = df["won"].notna()

    df_sorted = df.sort_values([GROUP_COL, sort_col]).reset_index(drop=True)
    df_sorted["won"] = df_sorted.groupby(GROUP_COL)["won"].shift(shift)

    shift_induced_nan = df_sorted["_had_real_won"] & df_sorted["won"].isna()
    n_dropped = int(shift_induced_nan.sum())

    df_out = (
        df_sorted.loc[~shift_induced_nan]
        .drop(columns=["_had_real_won"])
        .reset_index(drop=True)
    )
    return df_out, n_dropped


# ============================================================
# Trial runner
# ============================================================
def run_walkforward_for_rule(rule: dict, df: pd.DataFrame, windows: list) -> dict:
    """Mirror Stage 1: walkforward + aggregate_stability for one rule."""
    results = walkforward(rule, df, windows)
    return aggregate_stability(rule, results)


def run_trial(rule: dict, df_full: pd.DataFrame, windows: list, shift: int) -> dict:
    """Build shifted df, run harness, return raw trial result (decimal form)."""
    df_shifted, n_dropped = shift_won_by_symbol(df_full, shift=shift, sort_col=SORT_COL)
    agg = run_walkforward_for_rule(rule, df_shifted, windows)
    return {
        "shift": shift,
        "n_shift_induced_dropped": n_dropped,
        "n_rows_post_shift": int(len(df_shifted)),
        "agg_mean_lift": agg.get("mean_lift"),  # decimal
        "agg_pct_positive_windows": agg.get("pct_positive_windows"),
        "agg_mean_match_n": agg.get("mean_match_n"),
    }


# ============================================================
# Verdict logic (per spec — all inputs DECIMAL)
# ============================================================
def trial_verdict(shifted_lift, real_lift: float, shuffle_mean: float, shuffle_std: float) -> dict:
    if shifted_lift is None or (isinstance(shifted_lift, float) and np.isnan(shifted_lift)):
        return {
            "shifted_lift": None,
            "real_lift": real_lift,
            "drop": float("nan"),
            "drop_pct": float("nan"),
            "shifted_z": float("nan"),
            "decision": "AMBIGUOUS",
            "decision_rationale": "shifted_lift is None/NaN — cannot compute verdict",
        }

    s = float(shifted_lift)
    drop = real_lift - s
    drop_pct = drop / real_lift if real_lift != 0 else float("nan")
    shifted_z = (s - shuffle_mean) / shuffle_std if shuffle_std > 0 else float("nan")

    # FAIL conditions (checked first — leakage signals)
    if s > real_lift:
        decision = "FAIL"
        rationale = (
            f"shifted_lift {_fmt_dec(s)} > real_lift {_fmt_dec(real_lift)} "
            f"(improvement under shift = structural leakage)"
        )
    elif (not np.isnan(drop_pct)) and drop_pct < DROP_PCT_FAIL:
        decision = "FAIL"
        rationale = (
            f"drop_pct {_fmt_dec(drop_pct)} < {DROP_PCT_FAIL} "
            f"(shifted_lift {_fmt_dec(s)} barely off real_lift {_fmt_dec(real_lift)})"
        )
    # PASS condition
    elif (not np.isnan(drop_pct)) and (not np.isnan(shifted_z)) \
            and drop_pct > DROP_PCT_PASS and shifted_z < Z_PASS:
        decision = "PASS"
        rationale = (
            f"drop_pct {_fmt_dec(drop_pct)} > {DROP_PCT_PASS} AND "
            f"shifted_z {_fmt_z(shifted_z)} < {Z_PASS} "
            f"(lift collapsed into Stage 1 null band)"
        )
    else:
        decision = "AMBIGUOUS"
        rationale = (
            f"drop_pct={_fmt_dec(drop_pct)} / shifted_z={_fmt_z(shifted_z)} "
            f"outside PASS band but no FAIL signal"
        )

    return {
        "shifted_lift": s,
        "real_lift": real_lift,
        "drop": drop,
        "drop_pct": drop_pct,
        "shifted_z": shifted_z,
        "decision": decision,
        "decision_rationale": rationale,
    }


def overall_verdict(t_plus: dict, t_minus: dict) -> dict:
    v1, v2 = t_plus["decision"], t_minus["decision"]
    if v1 == "PASS" and v2 == "PASS":
        d, r = "PASS", "both Trial +1 and Trial -1 PASS"
    elif v1 == "FAIL" or v2 == "FAIL":
        d, r = "FAIL", f"at least one trial FAIL (plus_1={v1}, minus_1={v2})"
    else:
        d, r = "AMBIGUOUS", f"plus_1={v1}, minus_1={v2}"
    return {"decision": d, "decision_rationale": r}


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print(f"date_shift audit on {RULE_ID}")
    print("=" * 60)
    t_total = time.time()

    print("\nLoading data + rule + windows + reference distribution...")
    df_full = load_data()
    rule_019 = load_rule_019()
    windows = build_windows(df_full)
    ref = load_reference_shuffle_stats()
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  windows: {len(windows)}")
    print(f"  rule_019: {rule_019['match_fields']} + sub_regime={rule_019.get('sub_regime_constraint')}")
    print(f"  group_col={GROUP_COL!r}  sort_col={SORT_COL!r}")
    print(
        f"  reference (Stage 1, decimal): mean={_fmt_dec(ref['shuffle_mean'])}, "
        f"std={_fmt_dec(ref['shuffle_std'])}, p95={_fmt_dec(ref['shuffle_p95'])}, "
        f"n_trials={ref['n_trials']}"
    )

    print("\nSANITY CHECK: reproduce baseline on REAL data")
    real_agg = run_walkforward_for_rule(rule_019, df_full, windows)
    real_lift = real_agg.get("mean_lift")  # decimal
    real_pct_positive = real_agg.get("pct_positive_windows")
    real_lift_pp = (real_lift * 100) if real_lift is not None else None

    real_lift_pp_s = _fmt_pp(real_lift_pp)
    real_pct_s = _fmt_dec(real_pct_positive)
    print(f"  reproduced mean_lift: {real_lift_pp_s} (recorded: {RECORDED_MEAN_LIFT_PP}pp; tol ±{TOL_LIFT_PP}pp)")
    print(f"  reproduced pct_positive: {real_pct_s} (recorded: {RECORDED_PCT_POSITIVE}; tol ±{TOL_POSITIVE})")

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
            "group_col": GROUP_COL,
            "sort_col": SORT_COL,
            "baseline": {
                "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
                "recorded_pct_positive": RECORDED_PCT_POSITIVE,
                "reproduced_mean_lift_pp": real_lift_pp,
                "reproduced_pct_positive": real_pct_positive,
                "reproduction_ok": False,
                "tolerance_lift_pp": TOL_LIFT_PP,
                "tolerance_positive": TOL_POSITIVE,
            },
            "trials": {"plus_1": None, "minus_1": None},
            "skipped_reason": "baseline reproduction failed",
        }, indent=2))
        sys.exit(1)
    print("  ✓ baseline reproduced within tolerance")

    # --- Trial +1 (forward shift)
    print("\nTRIAL +1: forward shift by 1 row per symbol")
    t0 = time.time()
    t_plus_raw = run_trial(rule_019, df_full, windows, shift=+1)
    t_plus_v = trial_verdict(t_plus_raw["agg_mean_lift"], real_lift, ref["shuffle_mean"], ref["shuffle_std"])
    print(
        f"  shifted_lift={_fmt_dec(t_plus_raw['agg_mean_lift'])} "
        f"({_fmt_pp((t_plus_raw['agg_mean_lift'] or 0) * 100)})  "
        f"n_dropped={t_plus_raw['n_shift_induced_dropped']:,}  "
        f"n_rows={t_plus_raw['n_rows_post_shift']:,}  "
        f"({time.time()-t0:.1f}s)"
    )
    print(f"  drop_pct={_fmt_dec(t_plus_v['drop_pct'])}  shifted_z={_fmt_z(t_plus_v['shifted_z'])}")
    print(f"  decision={t_plus_v['decision']} — {t_plus_v['decision_rationale']}")

    # --- Trial -1 (backward shift)
    print("\nTRIAL -1: backward shift by 1 row per symbol")
    t0 = time.time()
    t_minus_raw = run_trial(rule_019, df_full, windows, shift=-1)
    t_minus_v = trial_verdict(t_minus_raw["agg_mean_lift"], real_lift, ref["shuffle_mean"], ref["shuffle_std"])
    print(
        f"  shifted_lift={_fmt_dec(t_minus_raw['agg_mean_lift'])} "
        f"({_fmt_pp((t_minus_raw['agg_mean_lift'] or 0) * 100)})  "
        f"n_dropped={t_minus_raw['n_shift_induced_dropped']:,}  "
        f"n_rows={t_minus_raw['n_rows_post_shift']:,}  "
        f"({time.time()-t0:.1f}s)"
    )
    print(f"  drop_pct={_fmt_dec(t_minus_v['drop_pct'])}  shifted_z={_fmt_z(t_minus_v['shifted_z'])}")
    print(f"  decision={t_minus_v['decision']} — {t_minus_v['decision_rationale']}")

    # --- Overall
    overall = overall_verdict(t_plus_v, t_minus_v)
    print(f"\nOVERALL VERDICT: {overall['decision']} — {overall['decision_rationale']}")

    # --- Persist
    elapsed = round(time.time() - t_total, 2)
    out = {
        "rule_id": RULE_ID,
        "group_col": GROUP_COL,
        "sort_col": SORT_COL,
        "baseline": {
            "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
            "recorded_pct_positive": RECORDED_PCT_POSITIVE,
            "reproduced_mean_lift": real_lift,           # decimal
            "reproduced_mean_lift_pp": real_lift_pp,     # pp
            "reproduced_pct_positive": real_pct_positive,
            "reproduction_ok": True,
            "tolerance_lift_pp": TOL_LIFT_PP,
            "tolerance_positive": TOL_POSITIVE,
        },
        "reference_distribution": {
            "source": "label_randomization_audit.json:stage_1_option_B_global_shuffle.shuffle_lift_distribution",
            "form": "decimal",
            **ref,
        },
        "thresholds": {
            "drop_pct_pass": DROP_PCT_PASS,
            "drop_pct_fail": DROP_PCT_FAIL,
            "z_pass": Z_PASS,
        },
        "trials": {
            "plus_1": {**t_plus_raw, "verdict": t_plus_v},
            "minus_1": {**t_minus_raw, "verdict": t_minus_v},
        },
        "overall_verdict": overall,
        "elapsed_seconds": elapsed,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total elapsed: {elapsed}s")


if __name__ == "__main__":
    main()
