"""P3 — Validate merged final rule set."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _validate_paths import add_derived_features, validate_rule, ENRICHED_PARQUET  # noqa: E402

FINAL_RULES = _HERE / "unified_rules_final.json"
FINAL_PREDS = _HERE / "validation_predictions_final.json"
FINAL_REPORT = _HERE / "validation_final.json"


def main():
    print(f"Loading enriched signals + computing features...")
    df = pd.read_parquet(ENRICHED_PARQUET)
    df = add_derived_features(df)
    print(f"  resolved: {df['won'].notna().sum()}")

    rules = json.loads(FINAL_RULES.read_text())["rules"]
    preds = {p["rule_id"]: p for p in json.loads(FINAL_PREDS.read_text())["predictions"]}
    print(f"\n=== Merged final rule set ===")
    print(f"  rules: {len(rules)}; predictions: {len(preds)}")

    results = []
    for rule in rules:
        rid = rule["id"]
        pred = preds.get(rid, {})
        if not pred:
            continue
        result = validate_rule(df, rule, pred)
        results.append(result)
        v = result["validation_verdict"]
        emoji = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(v, "?")
        n = result["actual_match_count"]
        wr = result["actual_match_wr"]
        wr_str = f"{wr:.1%}" if wr is not None else "—"
        origin = rule.get("_merge_origin", "?")
        print(f"  {emoji} {rid:12s} ({origin}) | {v:7s} | n={n:5d} WR={wr_str:5s}")

    pass_n = sum(r["validation_verdict"] == "PASS" for r in results)
    warn_n = sum(r["validation_verdict"] == "WARNING" for r in results)
    fail_n = sum(r["validation_verdict"] == "FAIL" for r in results)
    print(f"\n  PASS: {pass_n}/{len(results)} ({pass_n/len(results)*100:.1f}%)")
    print(f"  WARNING: {warn_n}/{len(results)}")
    print(f"  FAIL: {fail_n}/{len(results)}")
    print(f"  Pass+Warning: {(pass_n+warn_n)/len(results)*100:.1f}%")

    report = {
        "schema_version": 4,
        "label": "Merged final (best-of-both)",
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
    FINAL_REPORT.write_text(json.dumps(report, indent=2))
    print(f"\nSaved: {FINAL_REPORT}")


if __name__ == "__main__":
    main()
