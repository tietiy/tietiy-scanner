"""P3 — Validate Path 1 and Path 2 rules against historical data.

Uses Lab-canonical bucket thresholds (per path1_thresholds_explicit.md):
- market_breadth_pct: low<0.30, medium 0.30-0.60, high>0.60
- nifty_200d/60d_return_pct: low<-0.10, medium -0.10 to 0.10, high>0.10
- nifty_20d_return_pct: low<-0.05, medium -0.05 to 0.05, high>0.05
- swing_high/low_count_20d: low<2, medium 2-3, high>3
- fvg_unfilled_above/below_count: low<2, medium 2-5, high>5

Sub-regime detector axes (separate from feature library):
- Bull: 200d at 0.05/0.20, breadth at 0.60/0.80
- Bear: vp at 0.70, n60 at -0.10
- Choppy: vp at 0.30/0.70, breadth at 0.30/0.60

Also creates bucket columns (e.g., feat_market_breadth_pct_bucket) so
rules that use bucket labels (Path 2 style) can match.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

ENRICHED_PARQUET = _LAB_ROOT / "output" / "enriched_signals.parquet"


# Lab feature library thresholds (canonical)
FEATURE_THRESHOLDS = {
    "feat_market_breadth_pct": {"low": 0.30, "high": 0.60},
    "feat_nifty_200d_return_pct": {"low": -0.10, "high": 0.10},
    "feat_nifty_60d_return_pct": {"low": -0.10, "high": 0.10},
    "feat_nifty_20d_return_pct": {"low": -0.05, "high": 0.05},
    "feat_nifty_vol_percentile_20d": {"low": 0.30, "high": 0.70},
    "feat_ROC_10": {"low": -0.03, "high": 0.03},
    "feat_RSI_14": {"low": 30, "high": 70},
    "feat_coiled_spring_score": {"low": 33, "high": 67},
    "feat_multi_tf_alignment_score": {"low": 1, "high": 2},
    "feat_range_compression_60d": {"low": 0.08, "high": 0.20},
    "feat_52w_high_distance_pct": {"low": 0.05, "high": 0.20},
    "feat_52w_low_distance_pct": {"low": 0.05, "high": 0.20},
    "feat_sector_index_20d_return_pct": {"low": -0.05, "high": 0.05},
    "feat_sector_index_60d_return_pct": {"low": -0.10, "high": 0.10},
    "feat_bank_nifty_20d_return_pct": {"low": -0.05, "high": 0.05},
    "feat_bank_nifty_60d_return_pct": {"low": -0.10, "high": 0.10},
    "feat_fvg_unfilled_above_count": {"low": 2, "high": 5},  # int: low<2, high>5
    "feat_fvg_unfilled_below_count": {"low": 2, "high": 5},
    "feat_swing_high_count_20d": {"low": 2, "high": 3},  # int: low<2, high>3
    "feat_swing_low_count_20d": {"low": 2, "high": 3},
}


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add bucket columns + sub_regime + month + won."""
    df = df.copy()
    dt = pd.to_datetime(df["scan_date"])
    df["feat_month"] = dt.dt.month

    # Bucket columns using Lab-canonical thresholds
    for feat, thresh in FEATURE_THRESHOLDS.items():
        if feat not in df.columns:
            continue
        low_t = thresh["low"]
        high_t = thresh["high"]
        col = df[feat]
        # For integer features, "low" is strict less than (e.g., <2 means 0,1)
        # For continuous, "low" is < threshold; "high" is > threshold; "medium" is between
        df[f"{feat}_bucket"] = col.apply(
            lambda x: ("low" if x < low_t else ("high" if x > high_t else "medium"))
            if pd.notna(x)
            else None
        )

    # Sub-regime — Bull (detector axes 0.05/0.20 for 200d, 0.60/0.80 for breadth)
    def bull_subregime(row):
        p = row.get("feat_nifty_200d_return_pct")
        s = row.get("feat_market_breadth_pct")
        if pd.isna(p) or pd.isna(s):
            return None
        p_level = "low" if p < 0.05 else ("high" if p > 0.20 else "mid")
        s_level = "low" if s < 0.60 else ("high" if s > 0.80 else "mid")
        if p_level == "low" and s_level == "low":
            return "recovery_bull"
        if p_level == "mid" and s_level == "high":
            return "healthy_bull"
        if p_level == "mid" and s_level == "low":
            return "late_bull"
        return "normal_bull"

    # Sub-regime — Bear (vp > 0.70, n60 < -0.10)
    def bear_subregime(row):
        vp = row.get("feat_nifty_vol_percentile_20d")
        n60 = row.get("feat_nifty_60d_return_pct")
        if pd.isna(vp) or pd.isna(n60):
            return None
        if vp > 0.70:
            if n60 < -0.10:
                return "hot"
            elif n60 < 0:
                return "warm"
            return "cold"
        return "cold"

    # Sub-regime — Choppy (vol_regime × breadth)
    def choppy_subregime(row):
        vp = row.get("feat_nifty_vol_percentile_20d")
        s = row.get("feat_market_breadth_pct")
        if pd.isna(vp) or pd.isna(s):
            return None
        vol_tier = "quiet" if vp < 0.30 else ("stress" if vp > 0.70 else "equilibrium")
        breadth_tier = "low" if s < 0.30 else ("high" if s > 0.60 else "mid")
        return f"{vol_tier}_{breadth_tier}"

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

    mf = rule.get("match_fields", {})
    if mf.get("signal") is not None:
        sig_val = mf["signal"]
        if isinstance(sig_val, list):
            mask &= df["signal"].isin(sig_val)
        else:
            mask &= df["signal"] == sig_val
    if mf.get("sector") is not None:
        sec_val = mf["sector"]
        if isinstance(sec_val, list):
            mask &= df["sector"].isin(sec_val)
        else:
            mask &= df["sector"] == sec_val
    if mf.get("regime") is not None:
        reg_val = mf["regime"]
        if isinstance(reg_val, list):
            mask &= df["regime"].isin(reg_val)
        else:
            mask &= df["regime"] == reg_val

    for cond in rule.get("conditions", []):
        feat = cond["feature"]
        val = cond["value"]
        op = cond.get("operator", "eq")

        # Auto-redirect to bucket column when value is a bucket label
        col_name = feat
        if isinstance(val, str) and val.lower() in ("low", "medium", "high"):
            bucket_col = f"{feat}_bucket"
            if bucket_col in df.columns:
                col_name = bucket_col
                val = val.lower()

        if col_name not in df.columns:
            return df.iloc[0:0]

        col = df[col_name]
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

    sub_constraint = rule.get("sub_regime_constraint")
    if sub_constraint is not None:
        mask &= df["sub_regime"] == sub_constraint

    return df[mask]


def validate_rule(df: pd.DataFrame, rule: dict, prediction: dict) -> dict:
    matched = apply_rule(df, rule)
    matched_resolved = matched[matched["won"].notna()]

    actual_count = len(matched)
    actual_resolved = len(matched_resolved)
    actual_wr = matched_resolved["won"].mean() if actual_resolved > 0 else None

    pred_count = prediction.get("predicted_match_count", 0) or 0
    pred_count_min = prediction.get("predicted_match_count_min", int(pred_count * 0.8))
    pred_count_max = prediction.get("predicted_match_count_max", int(pred_count * 1.2) or 1)
    pred_wr = prediction.get("predicted_match_wr")
    pred_wr_min = prediction.get("predicted_match_wr_min")
    pred_wr_max = prediction.get("predicted_match_wr_max")

    count_in = pred_count_min <= actual_count <= pred_count_max
    wr_in = (
        actual_wr is not None
        and pred_wr_min is not None
        and pred_wr_min - 0.001 <= actual_wr <= pred_wr_max + 0.001
    )

    if rule.get("type") == "kill" or rule.get("verdict") in ("REJECT", "SKIP"):
        if actual_wr is not None and actual_wr > 0.55:
            verdict = "WARNING"
            reason = f"Kill rule matches winners: n={actual_resolved} at {actual_wr:.1%}"
        elif actual_count == 0:
            verdict = "FAIL"
            reason = f"Zero matches; expected {pred_count_min}-{pred_count_max}"
        elif count_in:
            verdict = "PASS"
            reason = f"n={actual_count} in band [{pred_count_min}, {pred_count_max}]"
        else:
            wide_in = (pred_count_min * 0.5) <= actual_count <= (pred_count_max * 1.5)
            verdict = "WARNING" if wide_in else "FAIL"
            reason = f"n={actual_count} outside [{pred_count_min}, {pred_count_max}]"
    else:
        if actual_resolved == 0:
            verdict = "FAIL"
            reason = f"n={actual_count} but 0 resolved"
        elif count_in and wr_in:
            verdict = "PASS"
            reason = f"n={actual_count} (band {pred_count_min}-{pred_count_max}); WR={actual_wr:.1%} (band {pred_wr_min:.1%}-{pred_wr_max:.1%})"
        elif count_in or wr_in:
            verdict = "WARNING"
            reason = f"count={actual_count} ({'in' if count_in else 'OUT'}); WR={actual_wr:.1%} ({'in' if wr_in else 'OUT'})"
        else:
            verdict = "FAIL"
            reason = f"count={actual_count} (expected {pred_count_min}-{pred_count_max}); WR={actual_wr:.1%}"

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


def validate_path(df: pd.DataFrame, rules_path: Path, preds_path: Path, label: str) -> dict:
    rules = json.loads(rules_path.read_text())["rules"]
    preds = {p["rule_id"]: p for p in json.loads(preds_path.read_text())["predictions"]}

    print(f"\n=== {label} ===")
    print(f"  rules: {len(rules)}; predictions: {len(preds)}")

    results = []
    for rule in rules:
        rid = rule["id"]
        pred = preds.get(rid, {})
        if not pred:
            print(f"  ⚠ {rid}: no prediction")
            continue
        result = validate_rule(df, rule, pred)
        results.append(result)
        v = result["validation_verdict"]
        emoji = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(v, "?")
        n = result["actual_match_count"]
        wr = result["actual_match_wr"]
        wr_str = f"{wr:.1%}" if wr is not None else "—"
        print(f"  {emoji} {rid:14s} | {v:7s} | n={n:5d} WR={wr_str:5s}")

    pass_n = sum(r["validation_verdict"] == "PASS" for r in results)
    warn_n = sum(r["validation_verdict"] == "WARNING" for r in results)
    fail_n = sum(r["validation_verdict"] == "FAIL" for r in results)
    print(f"\n  PASS: {pass_n}/{len(results)} ({pass_n/len(results)*100:.1f}%)")
    print(f"  WARNING: {warn_n}/{len(results)}")
    print(f"  FAIL: {fail_n}/{len(results)}")
    print(f"  Pass+Warning rate: {(pass_n+warn_n)/len(results)*100:.1f}%")

    return {
        "label": label,
        "n_rules": len(rules),
        "summary": {
            "PASS": pass_n,
            "WARNING": warn_n,
            "FAIL": fail_n,
            "pass_rate": pass_n / len(results) if results else 0,
            "pass_or_warning_rate": (pass_n + warn_n) / len(results) if results else 0,
        },
        "results": results,
    }


def main():
    print(f"Loading enriched signals: {ENRICHED_PARQUET}")
    df = pd.read_parquet(ENRICHED_PARQUET)
    print(f"  shape: {df.shape}")
    df = add_derived_features(df)
    print(f"  resolved: {df['won'].notna().sum()}")
    print(f"  sub_regime distribution:")
    sd = df['sub_regime'].value_counts().head(15).to_dict()
    for k, v in sd.items():
        print(f"    {k}: {v}")

    # Path 1
    p1_dir = _HERE / "path1_disciplined" / "output"
    p1_report = validate_path(
        df,
        p1_dir / "unified_rules_path1.json",
        p1_dir / "validation_predictions_path1.json",
        "Path 1 Disciplined",
    )
    (_HERE / "validation_path1.json").write_text(json.dumps(p1_report, indent=2))

    # Path 2
    p2_dir = _HERE / "path2_trust" / "output"
    p2_report = validate_path(
        df,
        p2_dir / "unified_rules_path2.json",
        p2_dir / "validation_predictions_path2.json",
        "Path 2 Trust-Opus",
    )
    (_HERE / "validation_path2.json").write_text(json.dumps(p2_report, indent=2))

    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"{'Metric':30s} | {'Path 1':>15s} | {'Path 2':>15s}")
    print("-" * 60)
    print(f"{'Total rules':30s} | {p1_report['n_rules']:>15} | {p2_report['n_rules']:>15}")
    p1s = p1_report["summary"]
    p2s = p2_report["summary"]
    print(f"{'PASS count':30s} | {p1s['PASS']:>15} | {p2s['PASS']:>15}")
    print(f"{'WARNING count':30s} | {p1s['WARNING']:>15} | {p2s['WARNING']:>15}")
    print(f"{'FAIL count':30s} | {p1s['FAIL']:>15} | {p2s['FAIL']:>15}")
    print(f"{'Pass rate':30s} | {p1s['pass_rate']*100:>13.1f}% | {p2s['pass_rate']*100:>13.1f}%")
    print(f"{'Pass+Warning rate':30s} | {p1s['pass_or_warning_rate']*100:>13.1f}% | {p2s['pass_or_warning_rate']*100:>13.1f}%")

    print("\n  done.")


if __name__ == "__main__":
    main()
