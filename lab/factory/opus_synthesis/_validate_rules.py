"""OP3 — Validate Opus-generated rules against historical signal data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
_REPO_ROOT = _LAB_ROOT.parent

ENRICHED_PARQUET = _LAB_ROOT / "output" / "enriched_signals.parquet"
RULES_PATH = _HERE / "output" / "unified_rules_v4.json"
PREDICTIONS_PATH = _HERE / "output" / "validation_predictions.json"
REPORT_PATH = _HERE / "validation_report.json"


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add features the rules reference but raw data doesn't have."""
    df = df.copy()
    # Month from scan_date
    dt = pd.to_datetime(df["scan_date"])
    df["feat_month"] = dt.dt.month

    # Bucket continuous features (low/medium/high tertiles)
    def tertile(col):
        v = df[col]
        qs = v.quantile([0.33, 0.67]).values
        return v.apply(lambda x: "low" if x <= qs[0] else ("high" if x >= qs[1] else "medium"))

    df["feat_nifty_200d_return_bucket"] = tertile("feat_nifty_200d_return_pct")
    df["feat_nifty_60d_return_bucket"] = tertile("feat_nifty_60d_return_pct")
    df["feat_nifty_20d_return_bucket"] = tertile("feat_nifty_20d_return_pct")
    df["feat_breadth_bucket"] = tertile("feat_market_breadth_pct")

    # Counts → low/medium/high (small/large buckets)
    df["feat_swing_high_count_20d_bucket"] = df["feat_swing_high_count_20d"].apply(
        lambda x: "low" if x <= 1 else ("high" if x >= 4 else "medium")
    )
    df["feat_fvg_unfilled_above_count_bucket"] = df["feat_fvg_unfilled_above_count"].apply(
        lambda x: "low" if x <= 1 else ("high" if x >= 5 else "medium")
    )

    # Sub-regime — Bull (200d × breadth)
    def bull_subregime(row):
        s = row["feat_nifty_200d_return_bucket"]
        b = row["feat_breadth_bucket"]
        if s == "low" and b == "low":
            return "recovery_bull"
        if s == "medium" and b == "high":
            return "healthy_bull"
        if s == "medium" and b == "low":
            return "late_bull"
        return "normal_bull"

    # Sub-regime — Bear (vol percentile × 60d return)
    def bear_subregime(row):
        vp = row["feat_nifty_vol_percentile_20d"]
        n60 = row["feat_nifty_60d_return_pct"]
        if pd.isna(vp) or pd.isna(n60):
            return None
        if vp > 0.70:
            if n60 < -0.10:
                return "hot"
            elif n60 < 0:
                return "warm"
            else:
                return "cold"
        return "cold"

    # Sub-regime — Choppy (vol_regime × breadth_bucket)
    def choppy_subregime(row):
        v = row["feat_nifty_vol_regime"]
        b = row["feat_breadth_bucket"]
        return f"{v.lower()}_{b}" if pd.notna(v) and pd.notna(b) else None

    def compute_subregime(row):
        regime = row.get("regime")
        if regime == "Bull":
            return bull_subregime(row)
        if regime == "Bear":
            return bear_subregime(row)
        if regime == "Choppy":
            return choppy_subregime(row)
        return None

    df["sub_regime"] = df.apply(compute_subregime, axis=1)

    # Outcome → won
    def outcome_to_won(o):
        if o in ("DAY6_WIN", "TARGET_HIT"):
            return 1
        if o in ("DAY6_LOSS", "STOP_HIT"):
            return 0
        return None

    df["won"] = df["outcome"].map(outcome_to_won)
    return df


def apply_rule(df: pd.DataFrame, rule: dict) -> pd.DataFrame:
    """Filter signals matching this rule."""
    mask = pd.Series(True, index=df.index)

    # match_fields: signal, sector, regime
    mf = rule.get("match_fields", {})
    if mf.get("signal") is not None:
        mask &= df["signal"] == mf["signal"]
    if mf.get("sector") is not None:
        mask &= df["sector"] == mf["sector"]
    if mf.get("regime") is not None:
        mask &= df["regime"] == mf["regime"]

    # conditions: arbitrary feature-value pairs
    for cond in rule.get("conditions", []):
        feat = cond["feature"]
        val = cond["value"]
        op = cond.get("operator", "eq")
        if feat not in df.columns:
            # Unknown feature → no match
            return df.iloc[0:0]
        col = df[feat]
        if op == "eq":
            mask &= col == val
        elif op == "in":
            mask &= col.isin(val)
        elif op == "gt":
            mask &= col > val
        elif op == "lt":
            mask &= col < val
        elif op == "gte":
            mask &= col >= val
        elif op == "lte":
            mask &= col <= val

    # sub_regime_constraint
    sub_constraint = rule.get("sub_regime_constraint")
    if sub_constraint is not None:
        mask &= df["sub_regime"] == sub_constraint

    return df[mask]


def validate_rule(df: pd.DataFrame, rule: dict, prediction: dict) -> dict:
    """Apply rule, compute actual stats, compare to prediction."""
    matched = apply_rule(df, rule)
    matched_resolved = matched[matched["won"].notna()]

    actual_count = len(matched)
    actual_resolved = len(matched_resolved)
    actual_wr = matched_resolved["won"].mean() if actual_resolved > 0 else None

    pred_count = prediction.get("predicted_match_count", 0)
    pred_count_min = prediction.get("predicted_match_count_min", 0)
    pred_count_max = prediction.get("predicted_match_count_max", 0)
    pred_wr = prediction.get("predicted_match_wr")
    pred_wr_min = prediction.get("predicted_match_wr_min")
    pred_wr_max = prediction.get("predicted_match_wr_max")

    # Verdict
    count_in = pred_count_min <= actual_count <= pred_count_max
    wr_in = (
        actual_wr is not None
        and pred_wr_min is not None
        and pred_wr_min - 0.001 <= actual_wr <= pred_wr_max + 0.001
    )

    if rule.get("type") == "kill" or rule.get("verdict") in ("REJECT", "SKIP"):
        # Kill rules: WR for matched should be LOW (otherwise we're killing winners)
        if actual_wr is not None and actual_wr > 0.55:
            verdict = "WARNING"  # kill rule matches winning signals
            reason = (
                f"Kill rule matches {actual_resolved} signals at {actual_wr:.1%} WR "
                f"(suggests rule may be too broad)"
            )
        else:
            if count_in:
                verdict = "PASS"
                reason = f"Match count {actual_count} within band [{pred_count_min}, {pred_count_max}]"
            else:
                verdict = "WARNING" if pred_count_min * 0.5 <= actual_count <= pred_count_max * 1.5 else "FAIL"
                reason = f"Match count {actual_count} outside band [{pred_count_min}, {pred_count_max}]"
    else:
        # Boost rules: check both count and WR
        if actual_resolved == 0:
            verdict = "FAIL"
            reason = f"Rule matches {actual_count} signals but 0 resolved (no WR data)"
        elif count_in and wr_in:
            verdict = "PASS"
            reason = f"count={actual_count} (band {pred_count_min}-{pred_count_max}); WR={actual_wr:.1%} (band {pred_wr_min:.1%}-{pred_wr_max:.1%})"
        elif count_in or wr_in:
            verdict = "WARNING"
            reason = f"count={actual_count} ({'in' if count_in else 'OUT'}); WR={actual_wr:.1%} ({'in' if wr_in else 'OUT'} of {pred_wr_min:.1%}-{pred_wr_max:.1%})"
        else:
            verdict = "FAIL"
            reason = f"count={actual_count} (expected {pred_count_min}-{pred_count_max}); WR={actual_wr:.1%} (expected {pred_wr_min:.1%}-{pred_wr_max:.1%})"

    return {
        "rule_id": rule["id"],
        "priority": rule.get("priority"),
        "type": rule.get("type"),
        "verdict": rule.get("verdict"),
        "actual_match_count": actual_count,
        "actual_resolved_count": actual_resolved,
        "actual_match_wr": float(actual_wr) if actual_wr is not None else None,
        "predicted_match_count": pred_count,
        "predicted_match_wr": pred_wr,
        "validation_verdict": verdict,
        "reason": reason,
    }


def main():
    print(f"Loading enriched signals: {ENRICHED_PARQUET}")
    df = pd.read_parquet(ENRICHED_PARQUET)
    print(f"  shape: {df.shape}")

    print("Computing derived features (sub_regime, buckets, month, won)...")
    df = add_derived_features(df)
    print(f"  resolved (won not null): {df['won'].notna().sum()}")
    print(f"  sub_regime distribution: {df['sub_regime'].value_counts().to_dict()}")

    print(f"\nLoading rules + predictions...")
    rules = json.loads(RULES_PATH.read_text())["rules"]
    preds = {p["rule_id"]: p for p in json.loads(PREDICTIONS_PATH.read_text())["predictions"]}

    print(f"  rules: {len(rules)}")
    print(f"  predictions: {len(preds)}")

    print("\n=== Per-rule validation ===")
    results = []
    for rule in rules:
        rid = rule["id"]
        pred = preds.get(rid, {})
        if not pred:
            print(f"  ⚠ {rid}: no prediction available")
            continue
        result = validate_rule(df, rule, pred)
        results.append(result)
        v = result["validation_verdict"]
        emoji = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(v, "?")
        n = result["actual_match_count"]
        wr = result["actual_match_wr"]
        wr_str = f"{wr:.1%}" if wr is not None else "—"
        print(f"  {emoji} {rid:14s} | {v:7s} | n={n:5d} WR={wr_str:5s} | {result['reason']}")

    # Aggregate
    pass_n = sum(r["validation_verdict"] == "PASS" for r in results)
    warn_n = sum(r["validation_verdict"] == "WARNING" for r in results)
    fail_n = sum(r["validation_verdict"] == "FAIL" for r in results)

    print(f"\n=== AGGREGATE ===")
    print(f"  PASS: {pass_n}/{len(results)}")
    print(f"  WARNING: {warn_n}/{len(results)}")
    print(f"  FAIL: {fail_n}/{len(results)}")
    print(f"  Pass rate: {pass_n/len(results)*100:.1f}%")
    print(f"  Pass+Warning rate: {(pass_n+warn_n)/len(results)*100:.1f}%")

    # Save
    report = {
        "schema_version": 4,
        "n_rules": len(rules),
        "n_predictions": len(preds),
        "n_results": len(results),
        "summary": {
            "PASS": pass_n,
            "WARNING": warn_n,
            "FAIL": fail_n,
            "pass_rate": pass_n / len(results) if results else 0,
            "pass_or_warning_rate": (pass_n + warn_n) / len(results) if results else 0,
        },
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved: {REPORT_PATH}")


if __name__ == "__main__":
    main()
