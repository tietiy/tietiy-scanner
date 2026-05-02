"""PB2 — Path A: backtest 37 rules against signal_history.json signals.

For each production signal:
- Join to enriched_signals on (date, symbol, signal) for feat_* fields
- Apply rule precedence; compute matched rules + verdict
- Compare to actual production behavior
- Aggregate per-rule

Output: path_a_signal_history.json with aggregate + per-rule stats.
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
    join_signal_history_to_enriched,
    load_enriched_op,
    load_rules,
    load_signal_history,
    operational_window,
    outcome_to_won,
)

OUTPUT_PATH = _HERE / "path_a_signal_history.json"


def main():
    print("Loading rules + datasets...")
    rules = load_rules(RULES_PATH)
    df_sh = load_signal_history()
    df_en = load_enriched_op()
    df_en = add_derived_features(df_en)
    op_start, op_end = operational_window(df_sh)
    print(f"  signal_history: n={len(df_sh)}; window {op_start} → {op_end}")
    print(f"  rules: {len(rules)}")

    # Join: signal_history rows get feat_* + sub_regime + won from enriched
    print("\nJoining signal_history to enriched_signals...")
    df = join_signal_history_to_enriched(df_sh, df_en)
    matched_to_enriched = df["sub_regime"].notna().sum()
    print(f"  joined rows with enriched feat_* data: {matched_to_enriched}/{len(df)}")

    # Outcome
    df["won_actual"] = df["outcome"].map(outcome_to_won)

    # Apply rules per signal
    print("\nApplying rules to each signal...")
    results = []
    for _, row in df.iterrows():
        ev = evaluate_signal(row, rules)
        won = row.get("won_actual")
        pnl = hypothetical_pnl(ev["winning_verdict"], won)
        results.append({
            "signal_id": row.get("id"),
            "date": row.get("date"),
            "symbol": row.get("symbol"),
            "signal": row.get("signal"),
            "sector": row.get("sector"),
            "regime": row.get("regime"),
            "sub_regime": row.get("sub_regime"),
            "outcome_actual": row.get("outcome"),
            "won_actual": won,
            "production_action": row.get("action"),  # what production did
            "production_score": row.get("score"),
            "matched_rule_ids": ev["matched_rule_ids"],
            "winning_rule_id": ev["winning_rule_id"],
            "winning_verdict": ev["winning_verdict"],
            "calibrated_wr": ev["calibrated_wr"],
            "rule_layer": ev["rule_layer"],
            "hypothetical_pnl_units": pnl,
            "matched_to_enriched": pd.notna(row.get("sub_regime")),
        })

    # Aggregate
    df_results = pd.DataFrame(results)

    # Verdict distribution
    print("\n=== Verdict distribution ===")
    print(df_results["winning_verdict"].value_counts().to_string())

    # Per-rule aggregate
    print("\n=== Per-rule aggregate ===")
    rule_stats = defaultdict(lambda: {"matched_count": 0, "winners": 0, "losers": 0,
                                       "winning_count": 0, "winning_winners": 0,
                                       "winning_losers": 0, "verdicts": defaultdict(int)})

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
            rule_stats[wid]["verdicts"][r["winning_verdict"]] += 1

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

    # Production baseline: what was the actual WR over resolved signal_history?
    actual_resolved = df_results[df_results["won_actual"].notna()]
    actual_wr = actual_resolved["won_actual"].mean() if len(actual_resolved) > 0 else None

    summary = {
        "label": "Path A — signal_history.json backtest",
        "operational_window": [str(op_start), str(op_end)],
        "n_signals_total": n_total,
        "n_signals_resolved": int(n_resolved),
        "n_matched_by_any_rule": int(n_matched),
        "n_unmatched_default_skip": int(n_unmatched),
        "n_joined_to_enriched": int(matched_to_enriched),
        "actual_production_wr_resolved": round(actual_wr, 4) if actual_wr else None,
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

    print("\n=== AGGREGATE ===")
    print(f"  Total signals: {n_total}")
    print(f"  Resolved: {n_resolved}")
    print(f"  Matched by any rule: {n_matched}")
    print(f"  Unmatched (default SKIP): {n_unmatched}")
    print(f"  Joined to enriched (have feat_* data): {matched_to_enriched}")
    print(f"\n  Actual production WR (resolved signals): {actual_wr*100:.1f}%" if actual_wr else "  Actual WR: —")
    print(f"  Rule-decided TAKE: {len(take_signals)} signals; {len(take_resolved)} resolved; WR={take_wr*100:.1f}%" if take_wr else "  TAKE WR: —")
    print(f"  Rule-decided SKIP/REJECT/WATCH: {len(skip_signals)} signals; {len(skip_resolved)} resolved; WR={skip_wr*100:.1f}%" if skip_wr else "  SKIP WR: —")
    print(f"\n  Hypothetical PnL (units): {pnl_total:+.2f} on {pnl_n} signals")
    print(f"  PnL per signal: {pnl_total/pnl_n:+.3f}" if pnl_n else "  PnL per: —")

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    (_HERE / "path_a_per_signal.json").write_text(
        json.dumps([{**r, "matched_rule_ids": list(r["matched_rule_ids"])} for r in results], indent=2, default=str)
    )
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Saved: {_HERE / 'path_a_per_signal.json'}")


if __name__ == "__main__":
    main()
