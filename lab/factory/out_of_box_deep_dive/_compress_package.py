"""Compress context package to fit Opus 200K context window."""
import json
from pathlib import Path

DST = Path("lab/factory/out_of_box_deep_dive/opus_context_package")

# 1. signal_history → essential fields only
sh = json.load((DST / "11_signal_history.json").open())
hist = sh.get("history", [])
keep_fields = [
    "id", "date", "symbol", "sector", "signal", "direction",
    "regime", "stock_regime", "regime_score", "score",
    "vol_q", "vol_confirm", "sec_mom", "sec_leading", "rs_q",
    "action", "user_action", "result", "outcome",
    "entry", "exit_price", "stop", "target_price",
    "pnl_pct", "mae_pct", "mfe_pct", "days_to_outcome",
    "grade", "grade_A", "is_sa", "attempt_number",
]
compact_hist = [{k: row.get(k) for k in keep_fields if k in row} for row in hist]
(DST / "11_signal_history.json").write_text(
    json.dumps({"schema": 5, "n": len(compact_hist), "history": compact_hist}, default=str)
)

# 2. Brain files — keep only key sections, drop nested signal repetitions
def compact_brain(path):
    b = json.load(path.open())
    out = {
        "schema_version": b.get("schema_version"),
        "phase": b.get("phase"),
        "phase_status": b.get("phase_status"),
        "phase_timestamp": b.get("phase_timestamp"),
        "market_date": b.get("market_date"),
        "banner": b.get("banner"),
        "summary": b.get("summary"),
        "alerts": b.get("alerts"),
        "self_queries": b.get("self_queries"),
        "upstream_health": b.get("upstream_health"),
        "should_send_telegram": b.get("should_send_telegram"),
    }
    # signals: keep essential fields only
    sigs = b.get("signals", [])
    if isinstance(sigs, list):
        out["signals_compact"] = [
            {
                "id": s.get("id"),
                "symbol": s.get("symbol"),
                "signal": s.get("signal"),
                "regime": s.get("regime"),
                "sector": s.get("sector"),
                "score": s.get("score"),
                "action": s.get("action"),
                "bucket": s.get("bucket"),
            }
            for s in sigs[:50]
        ]
        out["signals_total_count"] = len(sigs)
    elif isinstance(sigs, dict):
        out["signals_buckets"] = {k: len(v) if isinstance(v, list) else v for k, v in sigs.items()}
    # open_positions: count only
    pos = b.get("open_positions", [])
    out["open_positions_count"] = len(pos) if isinstance(pos, list) else None
    out["open_positions_summary"] = (
        [{"id": p.get("id"), "symbol": p.get("symbol"), "signal": p.get("signal"),
          "result": p.get("result"), "score": p.get("score")}
         for p in pos[:20]] if isinstance(pos, list) else None
    )
    return out

for f in DST.iterdir():
    if f.name.startswith(("20_", "21_", "22_", "23_", "24_", "25_", "26_")) and f.suffix == ".json":
        compact = compact_brain(f)
        f.write_text(json.dumps(compact, indent=1, default=str))

# 3. patterns.json — keep top 30 by lift, plus baselines + summary
pat = json.load((DST / "40_patterns.json").open())
patterns = pat.get("patterns", [])
# sort by absolute lift (assume lift_pp or wr-baseline)
def sort_key(p):
    return p.get("n_resolved", 0)
top_patterns = sorted(patterns, key=sort_key, reverse=True)[:30]
compact = {
    "schema_version": pat.get("schema_version"),
    "total_resolved_signals": pat.get("total_resolved_signals"),
    "feature_set": pat.get("feature_set", [])[:20] if isinstance(pat.get("feature_set"), list) else pat.get("feature_set"),
    "tier_thresholds": pat.get("tier_thresholds"),
    "baselines": pat.get("baselines"),
    "summary": pat.get("summary"),
    "top_30_patterns_by_resolved": top_patterns,
    "total_patterns_in_full_file": len(patterns),
}
(DST / "40_patterns.json").write_text(json.dumps(compact, indent=1, default=str))

# 4. unified_rules_v4_1_FINAL — keep summary + top fields per rule
rules = json.load((DST / "02_unified_rules_v4_1_FINAL.json").open())
compact_rules = {
    "schema_version": rules.get("schema_version"),
    "n_rules": rules.get("n_rules", len(rules.get("rules", []))),
    "rules": [
        {
            "id": r.get("id"),
            "type": r.get("type"),
            "priority": r.get("priority"),
            "verdict": r.get("verdict"),
            "production_ready": r.get("production_ready"),
            "match_fields": r.get("match_fields"),
            "conditions": r.get("conditions"),
            "sub_regime_constraint": r.get("sub_regime_constraint"),
            "expected_wr": r.get("expected_wr"),
            "trade_mechanism": r.get("trade_mechanism"),
            "source_finding": (r.get("source_finding") or "")[:200],
        }
        for r in rules.get("rules", [])
    ],
}
(DST / "02_unified_rules_v4_1_FINAL.json").write_text(json.dumps(compact_rules, indent=1, default=str))

# 5. deployment_readiness — keep essentials
dr = json.load((DST / "07_deployment_readiness.json").open())
compact_dr = {
    "label": dr.get("label"),
    "operational_window": dr.get("operational_window"),
    "n_rules": dr.get("n_rules"),
    "rules": [
        {
            "rule_id": r.get("rule_id"),
            "priority": r.get("priority"),
            "verdict": r.get("verdict"),
            "regime": r.get("regime"),
            "sub_regime": r.get("sub_regime"),
            "lab_expected_wr": r.get("lab_expected_wr"),
            "path_a_resolved_n": r.get("path_a_resolved_n"),
            "path_a_wr": r.get("path_a_wr"),
            "path_b_resolved_n": r.get("path_b_resolved_n"),
            "path_b_wr": r.get("path_b_wr"),
            "readiness": r.get("readiness"),
        }
        for r in dr.get("rules", [])
    ],
}
(DST / "07_deployment_readiness.json").write_text(json.dumps(compact_dr, indent=1, default=str))

# Print sizes
import os
total = 0
for f in sorted(DST.iterdir()):
    s = f.stat().st_size
    total += s
    print(f"{f.name:50s} {s/1024:8.1f} KB")
print(f"TOTAL: {total/1024:.1f} KB ({total//4} approx tokens)")
