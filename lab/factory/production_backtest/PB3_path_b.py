"""PB3 — Path B: backtest 37 rules against enriched_signals
filtered to operational window (broader academic universe).

Path A used signal_history (production-scanner-promoted signals only).
Path B uses enriched_signals — including signals that production
scanner's filters dropped or didn't trigger. Wider universe to
cross-validate Path A findings.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from harness import (
    RULES_PATH,
    add_derived_features,
    evaluate_signal,
    hypothetical_pnl,
    load_enriched_op,
    load_rules,
    load_signal_history,
    operational_window,
)

OUTPUT_PATH = _HERE / "path_b_enriched_signals.json"


def main():
    print("Loading rules + datasets...")
    rules = load_rules(RULES_PATH)
    df_sh = load_signal_history()
    op_start, op_end = operational_window(df_sh)

    df_en = load_enriched_op()
    df_en = add_derived_features(df_en)
    df_en_op = df_en[(df_en["scan_date"] >= op_start) & (df_en["scan_date"] <= op_end)].copy()
    print(f"  enriched op-window: n={len(df_en_op)} signals")
    print(f"  signal types: {df_en_op['signal'].value_counts().to_dict()}")
    print(f"  regimes: {df_en_op['regime'].value_counts().to_dict()}")
    print(f"  resolved: {df_en_op['won'].notna().sum()}")
    print(f"  rules: {len(rules)}")

    # Apply rules per signal
    print("\nApplying rules to each signal...")
    results = []
    for _, row in df_en_op.iterrows():
        ev = evaluate_signal(row, rules)
        won = row.get("won")
        # Cast to native int if not nan
        won_actual = int(won) if pd.notna(won) else None
        pnl = hypothetical_pnl(ev["winning_verdict"], won_actual)
        results.append({
            "scan_date": str(row.get("scan_date")),
            "symbol": row.get("symbol"),
            "signal": row.get("signal"),
            "sector": row.get("sector"),
            "regime": row.get("regime"),
            "sub_regime": row.get("sub_regime"),
            "outcome": row.get("outcome"),
            "won_actual": won_actual,
            "matched_rule_ids": ev["matched_rule_ids"],
            "winning_rule_id": ev["winning_rule_id"],
            "winning_verdict": ev["winning_verdict"],
            "calibrated_wr": ev["calibrated_wr"],
            "rule_layer": ev["rule_layer"],
            "hypothetical_pnl_units": pnl,
        })

    df_results = pd.DataFrame(results)

    # Per-rule aggregate
    rule_stats = defaultdict(lambda: {"matched_count": 0, "winners": 0, "losers": 0,
                                       "winning_count": 0, "winning_winners": 0,
                                       "winning_losers": 0})
    for r in results:
        for rid in r["matched_rule_ids"]:
            rule_stats[rid]["matched_count"] += 1
            if r["won_actual"] == 1:
                rule_stats[rid]["winners"] += 1
            elif r["won_actual"] == 0:
                rule_stats[rid]["losers"] += 1
        if r["winning_rule_id"]:
            wid = r["winning_rule_id"]
            rule_stats[wid]["winning_count"] += 1
            if r["won_actual"] == 1:
                rule_stats[wid]["winning_winners"] += 1
            elif r["won_actual"] == 0:
                rule_stats[wid]["winning_losers"] += 1

    rule_summary = {}
    for rule in rules:
        rid = rule["id"]
        st = rule_stats.get(rid, {})
        m_n = st.get("matched_count", 0)
        m_w = st.get("winners", 0)
        m_l = st.get("losers", 0)
        m_wr = m_w / (m_w + m_l) if (m_w + m_l) > 0 else None
        win_n = st.get("winning_count", 0)
        win_w = st.get("winning_winners", 0)
        win_l = st.get("winning_losers", 0)
        win_wr = win_w / (win_w + win_l) if (win_w + win_l) > 0 else None
        rule_summary[rid] = {
            "rule_id": rid,
            "priority": rule.get("priority"),
            "verdict": rule.get("verdict"),
            "type": rule.get("type"),
            "expected_wr": rule.get("expected_wr"),
            "matched_count": m_n,
            "matched_resolved": m_w + m_l,
            "matched_wr": round(m_wr, 4) if m_wr is not None else None,
            "winning_count": win_n,
            "winning_resolved": win_w + win_l,
            "winning_wr": round(win_wr, 4) if win_wr is not None else None,
        }

    # Aggregate
    n_total = len(df_results)
    n_resolved = df_results["won_actual"].notna().sum()
    n_matched = (df_results["winning_rule_id"].notna()).sum()
    n_unmatched = (df_results["winning_rule_id"].isna()).sum()
    take_signals = df_results[df_results["winning_verdict"].isin(["TAKE_FULL", "TAKE_SMALL"])]
    take_resolved = take_signals[take_signals["won_actual"].notna()]
    take_wr = take_resolved["won_actual"].mean() if len(take_resolved) > 0 else None
    skip_signals = df_results[df_results["winning_verdict"].isin(["SKIP", "REJECT", "WATCH"])]
    skip_resolved = skip_signals[skip_signals["won_actual"].notna()]
    skip_wr = skip_resolved["won_actual"].mean() if len(skip_resolved) > 0 else None

    pnl_total = df_results["hypothetical_pnl_units"].dropna().sum()
    pnl_n = df_results["hypothetical_pnl_units"].dropna().shape[0]

    actual_resolved = df_results[df_results["won_actual"].notna()]
    baseline_wr = actual_resolved["won_actual"].mean() if len(actual_resolved) > 0 else None

    summary = {
        "label": "Path B — enriched_signals operational window backtest",
        "operational_window": [str(op_start), str(op_end)],
        "n_signals_total": n_total,
        "n_signals_resolved": int(n_resolved),
        "n_matched_by_any_rule": int(n_matched),
        "n_unmatched_default_skip": int(n_unmatched),
        "baseline_wr_resolved": round(baseline_wr, 4) if baseline_wr else None,
        "rule_take_signals": len(take_signals),
        "rule_take_resolved": len(take_resolved),
        "rule_take_wr": round(take_wr, 4) if take_wr else None,
        "rule_skip_signals": len(skip_signals),
        "rule_skip_resolved": len(skip_resolved),
        "rule_skip_wr": round(skip_wr, 4) if skip_wr else None,
        "hypothetical_pnl_units_sum": round(pnl_total, 3),
        "hypothetical_pnl_n_signals": int(pnl_n),
        "verdict_distribution": df_results["winning_verdict"].value_counts().to_dict(),
        "rule_layer_distribution": df_results["rule_layer"].value_counts().to_dict(),
        "per_rule_stats": rule_summary,
    }

    print(f"\n=== Verdict distribution ===")
    print(df_results["winning_verdict"].value_counts().to_string())

    print(f"\n=== AGGREGATE ===")
    print(f"  Total signals: {n_total}")
    print(f"  Resolved: {n_resolved}")
    print(f"  Matched by any rule: {n_matched}; unmatched: {n_unmatched}")
    print(f"  Baseline WR (resolved): {baseline_wr*100:.1f}%" if baseline_wr else "  Baseline: —")
    print(f"  Rule TAKE: {len(take_signals)}; resolved {len(take_resolved)}; WR={take_wr*100:.1f}%" if take_wr else "  TAKE WR: —")
    print(f"  Rule SKIP/REJECT/WATCH: {len(skip_signals)}; resolved {len(skip_resolved)}; WR={skip_wr*100:.1f}%" if skip_wr else "  SKIP WR: —")
    print(f"  Hypothetical PnL: {pnl_total:+.2f} units on {pnl_n} signals")

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
