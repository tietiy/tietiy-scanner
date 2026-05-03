"""Walk-forward harness for OOS validation of Lab's 37 rules.

For each rule, walk a 60-day rolling window across 2011-2026 with
30-day step. Per window: compute rule match count, match WR, baseline
WR (signal-type WR within that window), and lift.

Aggregate stability metrics per rule across all windows:
- mean_lift, std_lift
- pct_positive_windows (% windows with lift > 0)
- pct_significant_windows (Wilson lower bound > baseline)
- recent_vs_old_trend (last 12 months vs older)

Validation tests:
- kill_001 (Bear × Bank × DOWN_TRI = REJECT): expect consistent
  negative or near-zero matched WR
- random rule (signal=UP_TRI no other constraints): expect lift ≈ 0
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "factory" / "production_backtest"))

from harness import (  # noqa: E402
    RULES_PATH,
    add_derived_features,
    matches_rule,
    load_rules,
)

ENRICHED = _LAB_ROOT / "output" / "enriched_signals.parquet"

WINDOW_DAYS = 60
STEP_DAYS = 30


def wilson_lower_95(wins: int, total: int) -> Optional[float]:
    if total == 0:
        return None
    p = wins / total
    z = 1.96
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    spread = (z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return centre - spread


def build_windows(df: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Construct list of (window_start, window_end) tuples."""
    df = df.copy()
    df["scan_date_dt"] = pd.to_datetime(df["scan_date"])
    start = df["scan_date_dt"].min()
    end = df["scan_date_dt"].max()
    windows = []
    cur = start
    while cur + pd.Timedelta(days=WINDOW_DAYS) <= end:
        w_end = cur + pd.Timedelta(days=WINDOW_DAYS)
        windows.append((cur, w_end))
        cur += pd.Timedelta(days=STEP_DAYS)
    return windows


def evaluate_rule_in_window(rule: dict, window_df: pd.DataFrame) -> dict:
    """Evaluate one rule against signals in this window.

    Returns: dict with match_n, match_resolved, match_w, match_l,
    match_wr, baseline_n, baseline_wr, lift, wilson_lower
    """
    # Apply rule.matches_rule per row (vectorize via apply)
    if window_df.empty:
        return {
            "match_n": 0, "match_resolved": 0, "match_w": 0, "match_l": 0,
            "match_wr": None, "baseline_n": 0, "baseline_wr": None,
            "lift": None, "wilson_lower": None,
        }

    # Vectorized match: build mask
    mask = pd.Series(True, index=window_df.index)
    mf = rule.get("match_fields", {})
    if mf.get("signal") is not None:
        sig_v = mf["signal"]
        if isinstance(sig_v, list):
            mask &= window_df["signal"].isin(sig_v)
        else:
            mask &= window_df["signal"] == sig_v
    if mf.get("sector") is not None:
        sec_v = mf["sector"]
        if isinstance(sec_v, list):
            mask &= window_df["sector"].isin(sec_v)
        else:
            mask &= window_df["sector"] == sec_v
    if mf.get("regime") is not None:
        reg_v = mf["regime"]
        if isinstance(reg_v, list):
            mask &= window_df["regime"].isin(reg_v)
        else:
            mask &= window_df["regime"] == reg_v

    sub = rule.get("sub_regime_constraint")
    if sub is not None:
        mask &= window_df["sub_regime"] == sub

    for cond in rule.get("conditions", []):
        feat = cond["feature"]
        val = cond["value"]
        op = cond.get("operator", "eq")

        col_name = feat
        if isinstance(val, str) and val.lower() in ("low", "medium", "high"):
            bucket_col = f"{feat}_bucket"
            if bucket_col in window_df.columns:
                col_name = bucket_col
                val = val.lower()

        if col_name not in window_df.columns:
            return {
                "match_n": 0, "match_resolved": 0, "match_w": 0, "match_l": 0,
                "match_wr": None, "baseline_n": 0, "baseline_wr": None,
                "lift": None, "wilson_lower": None,
            }
        col = window_df[col_name]
        if op == "eq":
            mask &= col == val
        elif op == "in":
            if isinstance(val, list):
                mask &= col.isin(val)
            else:
                mask &= col == val
        elif op == "gt":
            mask &= col > val
        elif op == "lt":
            mask &= col < val
        elif op == "gte":
            mask &= col >= val
        elif op == "lte":
            mask &= col <= val

    matched = window_df[mask]
    matched_resolved = matched[matched["won"].notna()]
    match_w = int((matched_resolved["won"] == 1).sum())
    match_l = int((matched_resolved["won"] == 0).sum())
    match_resolved = match_w + match_l
    match_wr = match_w / match_resolved if match_resolved > 0 else None

    # Baseline cohort: same signal type within window (or all if signal=null)
    baseline_signal = mf.get("signal")
    if baseline_signal is None:
        baseline_df = window_df[window_df["won"].notna()]
    else:
        if isinstance(baseline_signal, list):
            baseline_df = window_df[
                window_df["signal"].isin(baseline_signal) & window_df["won"].notna()
            ]
        else:
            baseline_df = window_df[
                (window_df["signal"] == baseline_signal) & window_df["won"].notna()
            ]
    baseline_n = len(baseline_df)
    baseline_w = int((baseline_df["won"] == 1).sum())
    baseline_wr = baseline_w / baseline_n if baseline_n > 0 else None

    lift = None
    if match_wr is not None and baseline_wr is not None:
        lift = match_wr - baseline_wr

    wilson = wilson_lower_95(match_w, match_resolved) if match_resolved > 0 else None

    return {
        "match_n": int(len(matched)),
        "match_resolved": match_resolved,
        "match_w": match_w,
        "match_l": match_l,
        "match_wr": float(match_wr) if match_wr is not None else None,
        "baseline_n": baseline_n,
        "baseline_wr": float(baseline_wr) if baseline_wr is not None else None,
        "lift": float(lift) if lift is not None else None,
        "wilson_lower": float(wilson) if wilson is not None else None,
    }


def walkforward(rule: dict, df: pd.DataFrame, windows: list) -> list[dict]:
    """Apply rule across all windows."""
    results = []
    for w_start, w_end in windows:
        win_df = df[(df["scan_date_dt"] >= w_start) & (df["scan_date_dt"] < w_end)]
        r = evaluate_rule_in_window(rule, win_df)
        r["window_start"] = w_start.strftime("%Y-%m-%d")
        r["window_end"] = w_end.strftime("%Y-%m-%d")
        results.append(r)
    return results


def aggregate_stability(rule: dict, results: list[dict]) -> dict:
    """Aggregate per-rule stability metrics."""
    res_df = pd.DataFrame(results)
    # Only consider windows where rule matched at least one resolved signal
    valid = res_df[res_df["match_resolved"] >= 1]
    if valid.empty:
        return {
            "rule_id": rule.get("id"),
            "n_windows_total": len(res_df),
            "n_windows_with_match": 0,
            "mean_lift": None,
            "std_lift": None,
            "pct_positive_windows": None,
            "pct_significant_windows": None,
            "min_match_n": 0,
            "max_match_n": 0,
            "mean_match_n": 0,
            "recent_lift_12m": None,
            "older_lift": None,
            "recent_vs_old_lift_delta": None,
            "expected_wr": rule.get("expected_wr"),
            "priority": rule.get("priority"),
            "verdict": rule.get("verdict"),
        }

    lifts = valid["lift"].dropna()
    pos_lift = (lifts > 0).sum()
    sig_lift = (
        (valid["wilson_lower"].fillna(-1) > valid["baseline_wr"].fillna(0)).sum()
    )

    # Recent 12 months vs older
    valid_dt = valid.copy()
    valid_dt["window_end_dt"] = pd.to_datetime(valid_dt["window_end"])
    cutoff = valid_dt["window_end_dt"].max() - pd.Timedelta(days=365)
    recent = valid_dt[valid_dt["window_end_dt"] > cutoff]
    older = valid_dt[valid_dt["window_end_dt"] <= cutoff]
    recent_lift = recent["lift"].dropna().mean() if not recent.empty else None
    older_lift = older["lift"].dropna().mean() if not older.empty else None
    delta = (recent_lift - older_lift) if recent_lift is not None and older_lift is not None else None

    return {
        "rule_id": rule.get("id"),
        "n_windows_total": int(len(res_df)),
        "n_windows_with_match": int(len(valid)),
        "mean_lift": float(lifts.mean()) if not lifts.empty else None,
        "std_lift": float(lifts.std()) if len(lifts) >= 2 else None,
        "pct_positive_windows": float(pos_lift / len(valid)) if len(valid) > 0 else None,
        "pct_significant_windows": float(sig_lift / len(valid)) if len(valid) > 0 else None,
        "min_match_n": int(valid["match_n"].min()),
        "max_match_n": int(valid["match_n"].max()),
        "mean_match_n": float(valid["match_n"].mean()),
        "recent_lift_12m": float(recent_lift) if recent_lift is not None else None,
        "older_lift": float(older_lift) if older_lift is not None else None,
        "recent_vs_old_lift_delta": float(delta) if delta is not None else None,
        "expected_wr": rule.get("expected_wr"),
        "priority": rule.get("priority"),
        "verdict": rule.get("verdict"),
    }


def load_data() -> pd.DataFrame:
    """Load enriched signals + add derived features + window date column."""
    df = pd.read_parquet(ENRICHED)
    df = add_derived_features(df)
    df["scan_date_dt"] = pd.to_datetime(df["scan_date"])
    return df


def validation_tests(df: pd.DataFrame, windows: list) -> dict:
    """Run sanity tests:
    1. kill_001 should consistently match losers (negative or zero lift)
    2. A trivially broad rule (signal=UP_TRI only) should have lift ≈ 0
    """
    # Test 1: kill_001 from current production rules (Bear × Bank × DOWN_TRI)
    kill_test = {
        "id": "test_kill",
        "type": "kill",
        "match_fields": {"signal": "DOWN_TRI", "sector": "Bank", "regime": "Bear"},
        "conditions": [],
        "sub_regime_constraint": None,
        "verdict": "REJECT",
    }
    results = walkforward(kill_test, df, windows)
    agg = aggregate_stability(kill_test, results)
    test1 = {
        "test": "kill_001 (Bear × Bank × DOWN_TRI)",
        "expectation": "matched WR <= baseline (kill rule should match losers)",
        "actual_mean_lift": agg["mean_lift"],
        "actual_pct_positive": agg["pct_positive_windows"],
        "n_windows_with_match": agg["n_windows_with_match"],
        "passed": (agg["mean_lift"] is None or agg["mean_lift"] <= 0.02),
    }

    # Test 2: trivial rule (UP_TRI only, no constraints)
    trivial = {
        "id": "test_trivial",
        "type": "boost",
        "match_fields": {"signal": "UP_TRI", "sector": None, "regime": None},
        "conditions": [],
        "sub_regime_constraint": None,
        "verdict": "TAKE_FULL",
    }
    results = walkforward(trivial, df, windows)
    agg = aggregate_stability(trivial, results)
    test2 = {
        "test": "trivial UP_TRI-only (no constraints)",
        "expectation": "lift ≈ 0 (matched cohort = baseline cohort)",
        "actual_mean_lift": agg["mean_lift"],
        "actual_pct_positive": agg["pct_positive_windows"],
        "n_windows_with_match": agg["n_windows_with_match"],
        "passed": (agg["mean_lift"] is None or abs(agg["mean_lift"]) < 0.01),
    }

    return {"validation_tests": [test1, test2]}


__all__ = [
    "WINDOW_DAYS", "STEP_DAYS",
    "build_windows", "evaluate_rule_in_window",
    "walkforward", "aggregate_stability",
    "load_data", "validation_tests",
    "wilson_lower_95",
]


if __name__ == "__main__":
    print("Loading data...")
    df = load_data()
    print(f"  shape: {df.shape}")
    print(f"  date range: {df['scan_date'].min()} → {df['scan_date'].max()}")

    print("\nBuilding windows...")
    windows = build_windows(df)
    print(f"  {len(windows)} windows ({WINDOW_DAYS}d windows, {STEP_DAYS}d step)")
    print(f"  first: {windows[0][0].strftime('%Y-%m-%d')} → {windows[0][1].strftime('%Y-%m-%d')}")
    print(f"  last:  {windows[-1][0].strftime('%Y-%m-%d')} → {windows[-1][1].strftime('%Y-%m-%d')}")

    print("\nValidation tests...")
    tests = validation_tests(df, windows)
    for t in tests["validation_tests"]:
        emoji = "✓" if t["passed"] else "✗"
        ml = t["actual_mean_lift"]
        ml_s = f"{ml*100:+.2f}pp" if ml is not None else "—"
        print(f"  {emoji} {t['test']}")
        print(f"    expectation: {t['expectation']}")
        print(f"    actual mean lift: {ml_s}; positive windows: {(t['actual_pct_positive'] or 0)*100:.0f}%")
        print(f"    windows with match: {t['n_windows_with_match']}")
