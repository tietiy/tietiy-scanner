"""W3 — Classify rules into SURVIVOR/WEAK/UNSTABLE/DEGRADER/REJECT.

Classification logic:
- SURVIVOR: mean_lift > 5pp AND pct_positive > 70% AND no degradation trend
  AND mean_match_n >= 5 (real sample)
- WEAK_SURVIVOR: mean_lift > 3pp AND pct_positive > 60% AND mean_match_n >= 3
- DEGRADER: mean_lift > 0 BUT recent_lift_12m < older_lift by > 10pp
- UNSTABLE: high std_lift, no clear positive trend
- REJECT: mean_lift <= 0 (when expecting positive)
- INSUFFICIENT_DATA: n_windows_with_match < 5

Boost rules (verdict TAKE_FULL/TAKE_SMALL): expect POSITIVE lift
Kill rules (verdict REJECT/SKIP): expect NEGATIVE lift
Watch rules (verdict WATCH): expect ~0 lift

Cross-reference with production backtest's 8 READY_TO_SHIP rules.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

SUMMARY_JSON = _HERE / "rule_stability_summary.json"
DEPLOYMENT_READINESS = (
    _LAB_ROOT / "factory" / "production_backtest" / "deployment_readiness.json"
)
OUT = _HERE / "stability_analysis.json"


def classify(rule: dict) -> tuple[str, str]:
    """Classify rule. Returns (category, rationale)."""
    rid = rule["rule_id"]
    verdict = rule.get("verdict")
    nw = rule.get("n_windows_with_match", 0) or 0
    ml = rule.get("mean_lift")
    pp = rule.get("pct_positive_windows")
    delta = rule.get("recent_vs_old_lift_delta")
    nmean = rule.get("mean_match_n", 0) or 0

    if nw < 5:
        return ("INSUFFICIENT_DATA",
                f"only {nw} windows with match across 15yr lifetime")

    # Kill rules expect NEGATIVE lift (matches losers)
    if verdict in ("REJECT", "SKIP"):
        if ml is None:
            return ("INSUFFICIENT_DATA", f"no lift data, n_windows={nw}")
        if ml <= -0.03:
            return ("SURVIVOR_KILL",
                    f"kill rule consistently matches losers: mean lift {ml*100:+.1f}pp")
        if ml <= 0.02:
            return ("WEAK_SURVIVOR_KILL",
                    f"kill rule mild anti: mean lift {ml*100:+.1f}pp")
        return ("REJECT_KILL_NOT_KILLING",
                f"kill rule matches winners: mean lift {ml*100:+.1f}pp — should not deploy as kill")

    # Watch rules expect ~0 lift (informational)
    if verdict == "WATCH":
        return ("WATCH_INFORMATIONAL", f"watch rule, mean lift {ml*100:+.1f}pp" if ml else "watch rule, no lift data")

    # Boost rules (TAKE_FULL / TAKE_SMALL) expect POSITIVE lift
    if verdict in ("TAKE_FULL", "TAKE_SMALL"):
        if ml is None:
            return ("INSUFFICIENT_DATA", f"no lift data, n_windows={nw}")

        # Degradation detection
        if delta is not None and delta < -0.10 and ml > 0:
            return ("DEGRADER",
                    f"mean lift {ml*100:+.1f}pp BUT recent_Δ {delta*100:+.1f}pp — fading edge")

        if ml > 0.05 and (pp or 0) > 0.70 and nmean >= 5:
            return ("SURVIVOR",
                    f"mean lift {ml*100:+.1f}pp, {(pp or 0)*100:.0f}% pos windows, n={nmean:.0f}")

        if ml > 0.03 and (pp or 0) > 0.60 and nmean >= 3:
            return ("WEAK_SURVIVOR",
                    f"mean lift {ml*100:+.1f}pp, {(pp or 0)*100:.0f}% pos windows")

        if ml > 0:
            return ("UNSTABLE_POSITIVE",
                    f"positive but inconsistent: lift {ml*100:+.1f}pp, {(pp or 0)*100:.0f}% pos")

        return ("REJECT_NEGATIVE_LIFT",
                f"boost rule shows negative lift: {ml*100:+.1f}pp — would underperform baseline")

    return ("UNCLASSIFIED", f"verdict={verdict}, lift={ml}")


def main():
    summary = json.loads(SUMMARY_JSON.read_text())
    deployment = json.loads(DEPLOYMENT_READINESS.read_text())

    # Index deployment readiness by rule_id
    deployment_by_id = {r["rule_id"]: r for r in deployment["rules"]}

    classifications = []
    for rule in summary["rules"]:
        category, rationale = classify(rule)
        backtest_readiness = deployment_by_id.get(rule["rule_id"], {}).get("readiness")
        classifications.append({
            **rule,
            "category": category,
            "rationale": rationale,
            "backtest_readiness": backtest_readiness,
        })

    # Counts per category
    import collections
    cat_count = collections.Counter(c["category"] for c in classifications)

    # Cross-reference: which rules are SURVIVOR in walk-forward AND READY_TO_SHIP in backtest?
    overlap_high_confidence = [
        c for c in classifications
        if c["category"] in ("SURVIVOR", "SURVIVOR_KILL")
        and c["backtest_readiness"] == "READY_TO_SHIP"
    ]

    # Walk-forward survivors
    wf_survivors = [
        c for c in classifications
        if c["category"] in ("SURVIVOR", "SURVIVOR_KILL")
    ]

    # Sort by mean_lift (positive first)
    classifications.sort(
        key=lambda x: -(x.get("mean_lift") or -999)
    )

    print("=" * 80)
    print("STABILITY CLASSIFICATION (37 rules)")
    print("=" * 80)
    for c in cat_count.most_common():
        print(f"  {c[0]}: {c[1]}")
    print()

    print(f"Walk-forward SURVIVORS: {len(wf_survivors)}")
    for s in wf_survivors:
        print(f"  ✓ {s['rule_id']:40s} | {s['category']:18s} | {s['rationale']}")
    print()

    print(f"Walk-forward × Production backtest INTERSECTION (highest confidence): {len(overlap_high_confidence)}")
    for o in overlap_high_confidence:
        print(f"  ★ {o['rule_id']:40s} | wf:{o['category']:15s} backtest:{o['backtest_readiness']}")
    print()

    print("DEGRADERS (concerning):")
    degraders = [c for c in classifications if c["category"] == "DEGRADER"]
    for d in degraders:
        print(f"  ⚠ {d['rule_id']:40s} | {d['rationale']}")
    print()

    print("REJECT_NEGATIVE_LIFT (boost rule shows negative lift):")
    rejects = [c for c in classifications if c["category"] == "REJECT_NEGATIVE_LIFT"]
    for r in rejects:
        print(f"  ✗ {r['rule_id']:40s} | {r['rationale']}")
    print()

    out = {
        "label": "Walk-forward stability analysis",
        "n_rules": len(classifications),
        "category_counts": dict(cat_count),
        "wf_survivors": [s["rule_id"] for s in wf_survivors],
        "wf_x_backtest_high_confidence": [o["rule_id"] for o in overlap_high_confidence],
        "degraders": [d["rule_id"] for d in degraders],
        "rejects": [r["rule_id"] for r in rejects],
        "classifications": classifications,
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
