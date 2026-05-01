"""
Phase 2 SUB-BLOCK 2D — Rank aggregation (Borda count) across importance methods.

For each cohort, combines available ranking methods into a single robust
ranking via Borda count (sum of ranks; lower = more important).

Method availability per cohort:
  Live cohorts (6): univariate edge_pp + univariate p_value (2 methods)
  Lifetime cohorts (4): edge_pp + p_value + RF importance + L1 |coef| (4 methods)

Robustness score: number of methods that rank a feature in the cohort's
top-25 (max = number of methods available for that cohort).

Output: lab/output/feature_importance.json — one entry per feature per
cohort, sorted by Borda score ascending; top-20 flagged.

Run:
    .venv/bin/python lab/analyses/inv_phase2_rank_aggregation.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────
UNIVARIATE_PATH = _LAB_ROOT / "output" / "univariate_importance.json"
MULTIVARIATE_PATH = _LAB_ROOT / "output" / "multivariate_importance.json"
OUTPUT_PATH = _LAB_ROOT / "output" / "feature_importance.json"

TOP_K_FOR_ROBUSTNESS = 25  # features ranked top-25 by N methods → robust


def _rank_dict(method_results: list[dict],
                  key: str,
                  ascending: bool = False) -> dict:
    """Convert a list of {feature_id, ...} into {feature_id: rank} (1=best).
    For p_value, ascending=True (lower p_value = more important).
    For everything else (edge_pp, RF importance, L1 |coef|), ascending=False."""
    sorted_list = sorted(method_results,
                            key=lambda r: r.get(key, 0),
                            reverse=not ascending)
    return {r["feature_id"]: i + 1 for i, r in enumerate(sorted_list)}


def aggregate_cohort(cohort_name: str,
                       univariate_data: dict,
                       multivariate_data: dict,
                       all_feature_ids: list[str]) -> dict:
    """Build Borda ranking for one cohort. Returns aggregated cohort entry."""
    uni = univariate_data["cohorts"].get(cohort_name)
    if uni is None or not uni.get("ranked_features"):
        return None

    uni_features = uni["ranked_features"]

    # Method 1: edge_pp (higher = more important)
    rank_edge = _rank_dict(uni_features, "edge_pp", ascending=False)
    # Method 2: p_value (lower = more important)
    rank_p = _rank_dict(uni_features, "p_value", ascending=True)

    methods_available = ["univariate_edge_pp", "univariate_p_value"]
    method_ranks = {"univariate_edge_pp": rank_edge,
                       "univariate_p_value": rank_p}

    # Multivariate ranks if available (lifetime cohorts only)
    multi = multivariate_data["cohorts"].get(cohort_name) if multivariate_data else None
    if multi:
        rank_rf = {r["feature_id"]: r["rank"] for r in multi["rf"]}
        rank_l1 = {r["feature_id"]: r["rank"] for r in multi["logistic"]}
        method_ranks["rf_importance"] = rank_rf
        method_ranks["logistic_l1_magnitude"] = rank_l1
        methods_available.extend(["rf_importance", "logistic_l1_magnitude"])

    # Build per-feature aggregated stats
    n_methods = len(methods_available)
    feature_stats = []

    # Build quick lookups
    uni_lookup = {r["feature_id"]: r for r in uni_features}
    rf_lookup = ({r["feature_id"]: r for r in multi["rf"]}
                  if multi else {})
    l1_lookup = ({r["feature_id"]: r for r in multi["logistic"]}
                  if multi else {})

    for fid in all_feature_ids:
        # Get rank from each method (default = worst possible if missing)
        ranks_per_method = {}
        for mname in methods_available:
            mr = method_ranks[mname]
            if fid in mr:
                ranks_per_method[mname] = mr[fid]
            else:
                ranks_per_method[mname] = len(all_feature_ids)  # worst rank

        # Borda score = sum of ranks (lower = better)
        borda_score = sum(ranks_per_method.values())

        # Robustness: how many methods rank this feature in top-K
        robustness = sum(1 for r in ranks_per_method.values()
                            if r <= TOP_K_FOR_ROBUSTNESS)

        # Pull underlying stats
        u = uni_lookup.get(fid, {})
        rf_r = rf_lookup.get(fid)
        l1_r = l1_lookup.get(fid)

        stats = {
            "feature_id": fid,
            "family": u.get("family", "?"),
            "value_type": u.get("value_type", "?"),
            "borda_score": borda_score,
            "robustness": robustness,
            "n_methods": n_methods,
            "method_ranks": ranks_per_method,
            "univariate_edge_pp": u.get("edge_pp"),
            "univariate_p_value": u.get("p_value"),
            "univariate_effect_size": u.get("effect_size"),
        }
        if rf_r:
            stats["rf_importance"] = rf_r["importance"]
            stats["rf_rank"] = rf_r["rank"]
        if l1_r:
            stats["logistic_coef_magnitude"] = l1_r["coef_magnitude"]
            stats["logistic_coef_sign"] = l1_r["coef_sign"]
            stats["logistic_rank"] = l1_r["rank"]

        feature_stats.append(stats)

    # Sort by Borda score (ascending)
    feature_stats.sort(key=lambda s: s["borda_score"])
    # Mark top-20
    for i, s in enumerate(feature_stats):
        s["aggregate_rank"] = i + 1
        s["top_20"] = i < 20

    return {
        "n": uni.get("n"),
        "n_w": uni.get("n_w"),
        "n_l": uni.get("n_l"),
        "methods_available": methods_available,
        "auc_rf": multi.get("auc_rf") if multi else None,
        "auc_logistic": multi.get("auc_logistic") if multi else None,
        "ranked_features": feature_stats,
    }


def main():
    print("─" * 72)
    print("Phase 2 SUB-BLOCK 2D — Rank aggregation (Borda count)")
    print("─" * 72)

    t0 = time.time()
    registry = FeatureRegistry.load_all()
    all_feature_ids = sorted(s.feature_id for s in registry.list_all())

    print(f"\nLoading univariate ({UNIVARIATE_PATH.name})...")
    with open(UNIVARIATE_PATH) as fh:
        uni = json.load(fh)
    print(f"Loading multivariate ({MULTIVARIATE_PATH.name})...")
    with open(MULTIVARIATE_PATH) as fh:
        multi = json.load(fh)

    # Process all cohorts
    output = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "top_k_robustness_threshold": TOP_K_FOR_ROBUSTNESS,
        "cohorts": {},
    }

    cohort_order = [
        "universal-live", "Bear-live", "Choppy-live",
        "UP_TRI-live", "DOWN_TRI-live", "BULL_PROXY-live",
        "lifetime-universal", "lifetime-Bear", "lifetime-Bull",
        "lifetime-Choppy",
    ]

    for cohort_name in cohort_order:
        print(f"\nAggregating {cohort_name}...")
        agg = aggregate_cohort(cohort_name, uni, multi, all_feature_ids)
        if agg is None:
            print(f"  no data; skipping")
            continue
        output["cohorts"][cohort_name] = agg
        n_methods = len(agg["methods_available"])
        # Robust top-20: rank ≤ 20 by Borda + robustness ≥ ceil(n_methods * 0.75)
        threshold = max(2, int(n_methods * 0.75))
        robust = sum(1 for f in agg["ranked_features"][:20]
                       if f["robustness"] >= threshold)
        print(f"  methods={n_methods}, AUC_rf={agg['auc_rf']}, "
              f"top-20 robust (≥{threshold}/{n_methods} methods agree top-25): "
              f"{robust}/20")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as fh:
        json.dump(output, fh, indent=2, default=str)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    print(f"Total runtime: {time.time() - t0:.1f}s")

    # Surface top-20 per cohort
    print()
    print("═" * 72)
    print("TOP 20 PER COHORT (Borda-aggregated)")
    print("═" * 72)
    for name, c in output["cohorts"].items():
        nm = len(c["methods_available"])
        threshold = max(2, int(nm * 0.75))
        n_w, n_l = c["n_w"], c["n_l"]
        warn = " ⚠" if n_l < 20 else ""
        auc_str = (f"AUC_rf={c['auc_rf']:.3f}"
                     if c["auc_rf"] is not None else "AUC_rf=N/A (univariate-only)")
        print(f"\n{name} (n_w={n_w}, n_l={n_l}, methods={nm}, {auc_str}){warn}")
        print(f"  {'rk':<3}{'feature_id':<40}{'family':<22}"
              f"{'borda':>7}{'robust':>8}")
        for f in c["ranked_features"][:20]:
            mark = "★" if f["robustness"] >= threshold else " "
            print(f"  {f['aggregate_rank']:<3}{f['feature_id']:<40}"
                  f"{f['family']:<22}{f['borda_score']:>7}"
                  f"{f['robustness']}/{nm}{mark}")


if __name__ == "__main__":
    main()
