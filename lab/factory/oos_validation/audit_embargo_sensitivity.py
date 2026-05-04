"""Phase 3 Step 3.6 — embargo_sensitivity audit on rule_019.

NAMING CAVEAT (read this carefully):
The consultant's framework calls this "embargo sensitivity" — testing whether
walk-forward results depend on a temporal gap between training and test
windows. That framing presumes a train/test methodology that DOES NOT EXIST
in this harness. walkforward.py evaluates each 60-day window independently,
computing rule lift = (rule_match_wr - same-signal-baseline_wr) entirely
within the window. There is no train segment, no test segment, and no
expected_wr fitted on training data.

What this audit ACTUALLY tests, mapped from the consultant's frame:
  Window-overlap sensitivity. The current harness uses 60d windows with 30d
  step, so consecutive windows share 30d of signal data (50% overlap). If
  aggregate stability metrics (mean_lift, pct_positive_windows) are inflated
  by autocorrelation between overlapping windows, subsampling to widen the
  effective stride should expose that.

Trial sequence (window stride in days):
  step=30  (baseline, full overlap, 182 windows, all original)
  step=60  (zero overlap, ~91 windows)
  step=90  (30d gap, ~61 windows)
  step=120 (60d gap, ~46 windows)
  step=150 (90d gap, ~37 windows)
  step=180 (120d gap / yearly stride, ~31 windows)

Per-trial decision (per Phase 3.6 spec):
  PASS:       |drift| <= 0.03 (decimal, ~3pp) AND lift > shuffle_p95
  FAIL:       lift < shuffle_p95 (collapsed into null band)
  AMBIGUOUS:  drift > 0.03 but lift > shuffle_p95

Drift tolerance loosened from 2pp → 3pp because high-step trials have only
6-12 matched windows, where natural sampling variance can produce 1-3pp
drift even with stable underlying edge.

Low-window override at OVERALL level (per Phase 3.4 pattern):
  - If a CORE trial (step in {60, 90, 120}) trips low_window_count_warning
    (n_windows_with_match < 5), force overall AMBIGUOUS even if per-trial
    decisions are PASS.
  - Extended trials (step=150, 180) tripping low_window are noted but do
    NOT auto-demote.

Overall verdict (across step=60..180, the 5 non-baseline trials):
  PASS:      all 5 non-baseline trials PASS, AND no core trial low-window
  FAIL:      any non-baseline trial FAIL
  AMBIGUOUS: any non-baseline trial AMBIGUOUS, OR core trials tripped low-window

Output: lab/factory/oos_validation/output/embargo_sensitivity_audit.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # mirrors Stage 1 / Step 3.3-3.5 pattern

from walkforward import (  # noqa: E402
    walkforward, build_windows, aggregate_stability, load_data, RULES_PATH,
)

# ============================================================
# Constants
# ============================================================
RULE_ID = "rule_019_bear_uptri_hot_refinement"

RECORDED_MEAN_LIFT_PP = 17.2208
RECORDED_PCT_POSITIVE = 0.7826
TOL_LIFT_PP = 0.5
TOL_POSITIVE = 0.02

BASELINE_STEP = 30                  # walkforward.py STEP_DAYS — full-overlap baseline
BASE_STRIDE_DAYS = 30               # build_windows step granularity
STEP_VALUES = [30, 60, 90, 120, 150, 180]
NON_BASELINE_STEPS = [60, 90, 120, 150, 180]
CORE_STEPS = [60, 90, 120]

LIFT_DRIFT_TOLERANCE = 0.03         # decimal — ~3pp on the lift scale
LOW_WINDOW_THRESHOLD = 5

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "embargo_sensitivity_audit.json"
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
# Walk-forward helper
# ============================================================
def run_walkforward_for_rule(rule: dict, df: pd.DataFrame, windows: list) -> dict:
    results = walkforward(rule, df, windows)
    return aggregate_stability(rule, results)


# ============================================================
# Per-trial decision
# ============================================================
def trial_decision(trial_lift, baseline_lift: float, shuffle_p95: float) -> dict:
    """PASS / FAIL / AMBIGUOUS per spec. Returns dict with decision + drift + rationale."""
    if trial_lift is None or (isinstance(trial_lift, float) and np.isnan(trial_lift)):
        return {
            "decision": "AMBIGUOUS",
            "rationale": "trial_lift is None/NaN — cannot compute decision",
            "lift_drift_from_baseline": None,
        }

    s = float(trial_lift)
    drift = abs(s - baseline_lift)

    if s < shuffle_p95:
        return {
            "decision": "FAIL",
            "rationale": (
                f"trial_lift {_fmt_dec(s)} < shuffle_p95 {_fmt_dec(shuffle_p95)} "
                f"(lift fell into shuffle null band)"
            ),
            "lift_drift_from_baseline": drift,
        }
    if drift <= LIFT_DRIFT_TOLERANCE:
        return {
            "decision": "PASS",
            "rationale": (
                f"|drift| {_fmt_dec(drift)} <= {LIFT_DRIFT_TOLERANCE} AND "
                f"lift {_fmt_dec(s)} > shuffle_p95 {_fmt_dec(shuffle_p95)}"
            ),
            "lift_drift_from_baseline": drift,
        }
    return {
        "decision": "AMBIGUOUS",
        "rationale": (
            f"|drift| {_fmt_dec(drift)} > {LIFT_DRIFT_TOLERANCE} "
            f"(lift {_fmt_dec(s)} drifted from baseline) but "
            f"lift > shuffle_p95 {_fmt_dec(shuffle_p95)}"
        ),
        "lift_drift_from_baseline": drift,
    }


def trial_summary(step_size: int, windows_used: list, agg: dict,
                  baseline_lift: float, shuffle_p95: float) -> dict:
    """Build per-trial summary dict (matches Phase 3.4 pattern)."""
    n_windows = int(len(windows_used))
    n_windows_with_match = int(agg.get("n_windows_with_match", 0))
    mean_lift = agg.get("mean_lift")
    mean_lift_pp = (mean_lift * 100) if mean_lift is not None else None
    pct_pos = agg.get("pct_positive_windows")

    above_p95 = bool(
        mean_lift is not None
        and not (isinstance(mean_lift, float) and np.isnan(mean_lift))
        and float(mean_lift) > shuffle_p95
    )
    low_warning = n_windows_with_match < LOW_WINDOW_THRESHOLD

    decision_dict = trial_decision(mean_lift, baseline_lift, shuffle_p95)

    return {
        "step_size_days": step_size,
        "n_windows": n_windows,
        "n_windows_with_match": n_windows_with_match,
        "mean_lift": mean_lift,
        "mean_lift_pp": mean_lift_pp,
        "pct_positive_windows": pct_pos,
        "lift_above_shuffle_p95": above_p95,
        "low_window_count_warning": low_warning,
        "lift_drift_from_baseline": decision_dict["lift_drift_from_baseline"],
        "decision": decision_dict["decision"],
        "rationale": decision_dict["rationale"],
    }


# ============================================================
# Overall verdict
# ============================================================
def overall_verdict(trials: dict) -> dict:
    non_baseline_keys = [f"step_{s}" for s in NON_BASELINE_STEPS]
    core_keys = [f"step_{s}" for s in CORE_STEPS]

    non_baseline = [trials[k] for k in non_baseline_keys if k in trials]
    core_trials = [trials[k] for k in core_keys if k in trials]

    decisions = [t["decision"] for t in non_baseline]
    per_trial_summary = ", ".join(
        f"{k}={trials[k]['decision']}" for k in non_baseline_keys if k in trials
    )

    # FAIL precedence
    if "FAIL" in decisions:
        return {
            "decision": "FAIL",
            "rationale": (
                f"At least one non-baseline trial FAIL (lift fell into shuffle null band). "
                f"Per-trial: {per_trial_summary}"
            ),
        }

    # AMBIGUOUS from per-trial drift
    if "AMBIGUOUS" in decisions:
        return {
            "decision": "AMBIGUOUS",
            "rationale": (
                f"At least one non-baseline trial AMBIGUOUS "
                f"(|drift| > {LIFT_DRIFT_TOLERANCE} but lift > shuffle_p95). "
                f"Per-trial: {per_trial_summary}"
            ),
        }

    # All non-baseline trials PASS — check core low-window override
    core_low = [t["step_size_days"] for t in core_trials if t.get("low_window_count_warning", False)]
    if core_low:
        return {
            "decision": "AMBIGUOUS",
            "rationale": (
                f"All non-baseline per-trial PASS, but core trial(s) at step={core_low} "
                f"tripped low_window_count_warning (< {LOW_WINDOW_THRESHOLD} windows with "
                f"rule_019 match) — lift may not be statistically meaningful at those strides. "
                f"Per-trial: {per_trial_summary}"
            ),
        }

    # Note any extended-trial low-window tripping (informational, doesn't demote)
    extended_low = [
        t["step_size_days"] for t in non_baseline
        if t.get("low_window_count_warning", False) and t["step_size_days"] not in CORE_STEPS
    ]
    extended_note = (
        f" (extended trials at step={extended_low} tripped low_window_count_warning expectedly; "
        f"informational, not auto-demoting)"
        if extended_low else ""
    )

    return {
        "decision": "PASS",
        "rationale": (
            f"All 5 non-baseline trials PASS, core trials (step={CORE_STEPS}) did not trip "
            f"low_window_count_warning. Per-trial: {per_trial_summary}{extended_note}"
        ),
    }


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print(f"embargo_sensitivity audit on {RULE_ID}")
    print("(window-overlap sensitivity — see docstring for naming caveat)")
    print("=" * 60)
    t_total = time.time()

    print("\nLoading data + rule + windows + reference...")
    df_full = load_data()
    rule_019 = load_rule_019()
    full_windows = build_windows(df_full)
    ref = load_reference_shuffle_stats()
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  baseline windows: {len(full_windows)} (60d windows, 30d step, 50% overlap)")
    print(f"  rule_019: {rule_019['match_fields']} + sub_regime={rule_019.get('sub_regime_constraint')}")
    print(
        f"  reference (Stage 1, decimal): mean={_fmt_dec(ref['shuffle_mean'])}, "
        f"std={_fmt_dec(ref['shuffle_std'])}, p95={_fmt_dec(ref['shuffle_p95'])}, "
        f"max={_fmt_dec(ref['shuffle_max'])}"
    )

    # --- Sanity check (= step=30 trial baseline, reused below)
    print("\nSANITY CHECK: reproduce baseline on REAL data (= step=30 trial)")
    real_agg = run_walkforward_for_rule(rule_019, df_full, full_windows)
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
            "test_name": "embargo_sensitivity",
            "baseline": {"reproduction_ok": False},
            "skipped_reason": "baseline reproduction failed",
        }, indent=2))
        sys.exit(1)
    print("  ✓ baseline reproduced within tolerance")

    # --- Trials
    print("\nEMBARGO TRIALS (window-overlap sensitivity)")
    trials: dict = {}
    for step_size in STEP_VALUES:
        t0 = time.time()
        stride = step_size // BASE_STRIDE_DAYS  # 30→1, 60→2, 90→3, 120→4, 150→5, 180→6
        windows_sub = full_windows[::stride]
        # Reuse the sanity-check agg for the baseline step=30; otherwise re-run
        if step_size == BASELINE_STEP:
            agg = real_agg
        else:
            agg = run_walkforward_for_rule(rule_019, df_full, windows_sub)
        summary = trial_summary(step_size, windows_sub, agg, real_lift, ref["shuffle_p95"])
        trials[f"step_{step_size}"] = summary

        baseline_marker = " (baseline)" if step_size == BASELINE_STEP else ""
        print(
            f"  step={step_size:>3}  n_windows={summary['n_windows']:>3}  "
            f"n_win_match={summary['n_windows_with_match']:>3}  "
            f"lift={_fmt_pp(summary['mean_lift_pp'])}  "
            f"drift={_fmt_dec(summary['lift_drift_from_baseline'])}  "
            f"above_p95={summary['lift_above_shuffle_p95']}  "
            f"decision={summary['decision']}{baseline_marker}  "
            f"({time.time()-t0:.1f}s)"
        )
        if summary["low_window_count_warning"]:
            print(
                f"  ⚠ WARNING step={step_size}: only {summary['n_windows_with_match']} window(s) "
                f"with any rule_019 match (< {LOW_WINDOW_THRESHOLD}); lift may not be "
                f"statistically meaningful"
            )

    # --- Overall verdict
    overall = overall_verdict(trials)
    print(f"\nOVERALL VERDICT: {overall['decision']} — {overall['rationale']}")

    # --- Persist
    elapsed = round(time.time() - t_total, 2)
    out = {
        "rule_id": RULE_ID,
        "test_name": "embargo_sensitivity",
        "test_description": (
            "Window-overlap sensitivity (mapped from consultant's 'embargo' framing, "
            "which doesn't apply directly to walkforward — no train/test split). "
            "Subsamples baseline windows[::N] to widen effective stride; tests whether "
            "aggregate stability metrics are inflated by 50% overlap of consecutive "
            "60d-windows / 30d-step harness."
        ),
        "configuration": {
            "baseline_step_days": BASELINE_STEP,
            "step_values_days": STEP_VALUES,
            "non_baseline_steps": NON_BASELINE_STEPS,
            "core_steps": CORE_STEPS,
            "lift_drift_tolerance_decimal": LIFT_DRIFT_TOLERANCE,
            "low_window_threshold": LOW_WINDOW_THRESHOLD,
        },
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
