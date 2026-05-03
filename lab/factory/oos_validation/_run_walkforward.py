"""W2 — Run walk-forward on Lab's 37 rules; produce per-rule time series."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from walkforward import (  # noqa: E402
    aggregate_stability,
    build_windows,
    load_data,
    walkforward,
)
from walkforward import RULES_PATH  # type: ignore  # noqa: E402

PER_RULE_PARQUET = _HERE / "per_rule_walkforward.parquet"
SUMMARY_JSON = _HERE / "rule_stability_summary.json"


def main():
    print("Loading data + rules...")
    df = load_data()
    rules = json.loads(RULES_PATH.read_text())["rules"]
    print(f"  signals: {len(df):,}")
    print(f"  rules: {len(rules)}")

    windows = build_windows(df)
    print(f"  windows: {len(windows)}")

    print("\nWalking forward 37 rules across 182 windows...")
    t0 = time.time()
    all_window_rows = []
    summaries = []
    for i, rule in enumerate(rules):
        rid = rule["id"]
        results = walkforward(rule, df, windows)
        # Tag with rule_id
        for r in results:
            r["rule_id"] = rid
            r["priority"] = rule.get("priority")
            r["verdict"] = rule.get("verdict")
            r["rule_type"] = rule.get("type")
        all_window_rows.extend(results)

        agg = aggregate_stability(rule, results)
        summaries.append(agg)

        # Progress
        if (i + 1) % 5 == 0 or i == len(rules) - 1:
            elapsed = time.time() - t0
            print(f"  {i+1}/{len(rules)} rules complete ({elapsed:.1f}s)")

    # Save per-window results
    df_windows = pd.DataFrame(all_window_rows)
    df_windows.to_parquet(PER_RULE_PARQUET, index=False)
    print(f"\nPer-window results: {PER_RULE_PARQUET} ({len(df_windows):,} rows)")

    # Save summary
    SUMMARY_JSON.write_text(json.dumps({
        "label": "Walk-forward stability summary",
        "n_rules": len(rules),
        "n_windows": len(windows),
        "window_days": 60,
        "step_days": 30,
        "rules": summaries,
    }, indent=2, default=str))
    print(f"Summary: {SUMMARY_JSON}")

    # Quick stability rollup
    print("\n=== STABILITY ROLLUP ===")
    print(f"{'rule_id':30s} {'priority':6s} {'wins':3s} {'pos%':5s} {'mean_lift':10s} {'recent_Δ':10s} {'n_match':7s}")
    for s in sorted(summaries, key=lambda x: -(x["mean_lift"] or -999)):
        rid = s["rule_id"][:30]
        prio = s["priority"] or "—"
        nw = s["n_windows_with_match"] or 0
        pos = s["pct_positive_windows"]
        pos_s = f"{pos*100:.0f}%" if pos is not None else "—"
        ml = s["mean_lift"]
        ml_s = f"{ml*100:+.2f}pp" if ml is not None else "—"
        rd = s["recent_vs_old_lift_delta"]
        rd_s = f"{rd*100:+.1f}pp" if rd is not None else "—"
        nm = s["mean_match_n"] or 0
        print(f"{rid:30s} {prio:6s} {nw:3d} {pos_s:5s} {ml_s:10s} {rd_s:10s} {nm:7.1f}")


if __name__ == "__main__":
    main()
