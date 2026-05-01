"""
Choppy regime — L3: comprehensive feature combination search at lifetime scale.

Per signal_type (UP_TRI / DOWN_TRI / BULL_PROXY) within Choppy:

A. Test all 2-feature combinations from Phase-2 lifetime-Choppy top-30 features.
   Filter: n_match ≥ 100, lift ≥ 5pp, p-value < 0.01.

B. For top 20 of (A) by lift × match_volume, test 3-feature extensions
   (add 3rd feature from same top-30).

Output: lifetime/comprehensive_combinations_top20.json (summary) +
        lifetime/comprehensive_combinations.parquet (full).

Compare against cell findings (F1 = ema_bull + coiled=medium):
  • Did F1 surface in this search? At what rank?
  • Are there higher-lift combinations the cells missed?
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse signal_matches_level + threshold parsing
_filter_path = (_LAB_ROOT / "factory" / "choppy_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("uptri_filter_l3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
OUTPUT_TOP20_PATH = _HERE / "comprehensive_combinations_top20.json"
OUTPUT_PARQUET = _HERE / "comprehensive_combinations.parquet"

TOP_K_FEATURES = 30
MIN_N_MATCH = 100
MIN_LIFT = 0.05
P_VALUE_THRESHOLD = 0.01


def _wlf(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _binomial_p(k: int, n: int, p_null: float) -> float:
    """Two-sided binomial test p-value."""
    if n == 0:
        return 1.0
    try:
        from scipy import stats
        try:
            return float(stats.binomtest(k, n, p=p_null,
                                              alternative="two-sided").pvalue)
        except AttributeError:
            return float(stats.binom_test(k, n, p=p_null,
                                                alternative="two-sided"))
    except ImportError:
        return 1.0


def _load_levels_for_feature(spec, signal_values: pd.Series) -> list[str]:
    """Derive applicable levels for a feature."""
    if spec.value_type == "bool":
        return ["True", "False"]
    if spec.value_type == "categorical":
        non_null = signal_values.dropna()
        if non_null.empty:
            return []
        return non_null.astype(str).value_counts().head(3).index.tolist()
    # numeric
    th = spec.level_thresholds
    if not isinstance(th, dict):
        return []
    if th.get("low") is None or th.get("high") is None:
        return []
    return ["low", "medium", "high"]


def _top_features_for(importance_data: dict, regime: str,
                          k: int = TOP_K_FEATURES) -> list[str]:
    cohort_key = f"lifetime-{regime}"
    cohort = importance_data.get("cohorts", {}).get(cohort_key, {})
    rf = cohort.get("ranked_features", [])
    return [f["feature_id"] for f in rf[:k]]


def _evaluate_combination(df: pd.DataFrame, baseline_wr: float,
                              combo: list[tuple[str, str]],
                              spec_by_id: dict, bounds_cache: dict
                              ) -> dict:
    """Evaluate a (feature, level) combination's WR vs baseline."""
    n = len(df)
    mask = pd.Series([True] * n, index=df.index)
    for fid, lvl in combo:
        spec = spec_by_id.get(fid)
        if spec is None:
            return None
        col = f"feat_{fid}"
        if col not in df.columns:
            return None
        m = df[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache))
        mask = mask & m.fillna(False)
    matched = df[mask]
    n_m = len(matched)
    if n_m < MIN_N_MATCH:
        return None
    n_w = (matched["wlf"] == "W").sum()
    n_l = (matched["wlf"] == "L").sum()
    n_wl = n_w + n_l
    if n_wl < MIN_N_MATCH:
        return None
    wr = n_w / n_wl
    lift = wr - baseline_wr
    if lift < MIN_LIFT:
        return None
    p = _binomial_p(n_w, n_wl, baseline_wr)
    if p > P_VALUE_THRESHOLD:
        return None
    return {
        "features": combo,
        "n_match": n_m, "n_match_wl": n_wl,
        "n_w": int(n_w), "n_l": int(n_l),
        "wr": float(wr), "lift_pp": float(lift),
        "p_value": float(p),
    }


def search_2feature(df: pd.DataFrame, baseline_wr: float,
                        feature_ids: list[str],
                        spec_by_id: dict,
                        bounds_cache: dict) -> list[dict]:
    """Test all 2-feature combinations from feature_ids list."""
    feature_levels: dict[str, list[str]] = {}
    for fid in feature_ids:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue
        levels = _load_levels_for_feature(spec, df[col])
        if levels:
            feature_levels[fid] = levels

    results = []
    n_tested = 0
    for fid_a, fid_b in combinations(feature_levels.keys(), 2):
        for la in feature_levels[fid_a]:
            for lb in feature_levels[fid_b]:
                combo = [(fid_a, la), (fid_b, lb)]
                r = _evaluate_combination(df, baseline_wr, combo,
                                              spec_by_id, bounds_cache)
                n_tested += 1
                if r is not None:
                    results.append(r)
    print(f"    {n_tested} 2-feat combos tested, {len(results)} qualifying")
    results.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    return results


def search_3feature(df: pd.DataFrame, baseline_wr: float,
                        top_2feat: list[dict], feature_ids: list[str],
                        spec_by_id: dict, bounds_cache: dict,
                        max_seeds: int = 20) -> list[dict]:
    """For top 2-feat combos, try adding a 3rd feature from feature_ids."""
    feature_levels: dict[str, list[str]] = {}
    for fid in feature_ids:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue
        levels = _load_levels_for_feature(spec, df[col])
        if levels:
            feature_levels[fid] = levels

    results = []
    n_tested = 0
    for seed in top_2feat[:max_seeds]:
        seed_features = {f for f, _ in seed["features"]}
        for fid_c in feature_levels.keys():
            if fid_c in seed_features:
                continue
            for lc in feature_levels[fid_c]:
                combo = list(seed["features"]) + [(fid_c, lc)]
                r = _evaluate_combination(df, baseline_wr, combo,
                                              spec_by_id, bounds_cache)
                n_tested += 1
                if r is not None:
                    results.append(r)
    print(f"    {n_tested} 3-feat combos tested, {len(results)} qualifying")
    results.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    return results


def main():
    print("─" * 80)
    print("L3: Choppy comprehensive feature combination search at lifetime scale")
    print("─" * 80)
    t_total = time.time()

    df = pd.read_parquet(ENRICHED_PATH)
    ch = df[df["regime"] == "Choppy"].copy()
    ch["wlf"] = ch["outcome"].apply(_wlf)
    ch_wl = ch[ch["wlf"].isin(["W", "L", "F"])].copy()

    importance_data = json.loads(IMPORTANCE_PATH.read_text())
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    feature_ids = _top_features_for(importance_data, "Choppy", TOP_K_FEATURES)
    print(f"\nTop-{TOP_K_FEATURES} lifetime-Choppy features (Phase 2):")
    print("  " + ", ".join(feature_ids[:15]))

    out: dict = {"by_signal_type": {}}
    parquet_rows = []

    for sig_type in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub = ch_wl[ch_wl["signal"] == sig_type]
        n = len(sub)
        nw = (sub["wlf"] == "W").sum()
        nl = (sub["wlf"] == "L").sum()
        baseline_wr = nw / (nw + nl)
        print(f"\n── {sig_type} × Choppy (n={n}, baseline={baseline_wr*100:.1f}%) ──")

        t0 = time.time()
        top_2feat = search_2feature(sub, baseline_wr, feature_ids,
                                          spec_by_id, bounds_cache)
        print(f"    2-feat search: {time.time() - t0:.1f}s")

        t0 = time.time()
        top_3feat = search_3feature(sub, baseline_wr, top_2feat,
                                          feature_ids, spec_by_id,
                                          bounds_cache)
        print(f"    3-feat search: {time.time() - t0:.1f}s")

        # Compile top-20 with cell-comparison
        all_combos = top_2feat + top_3feat
        all_combos.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
        top20 = all_combos[:20]

        # Check if F1 (ema_bull + coiled=medium) appears
        f1_match = None
        for r in top_2feat:
            features_set = {f"{f}={l}" for f, l in r["features"]}
            if features_set == {"ema_alignment=bull",
                                    "coiled_spring_score=medium"}:
                f1_match = r
                break
        f1_rank_in_2feat = next(
            (i + 1 for i, r in enumerate(top_2feat)
             if {f"{f}={l}" for f, l in r["features"]}
                == {"ema_alignment=bull", "coiled_spring_score=medium"}),
            None)

        out["by_signal_type"][sig_type] = {
            "n": n, "baseline_wr": float(baseline_wr),
            "n_qualifying_2feat": len(top_2feat),
            "n_qualifying_3feat": len(top_3feat),
            "f1_appearance": f1_match,
            "f1_rank_in_2feat": f1_rank_in_2feat,
            "top20_combinations": top20,
        }

        # Surface
        print(f"\n    Top 10 combinations by lift × volume:")
        print(f"    {'rank':<5}{'features':<60}{'n':>6}{'wr':>7}{'lift':>8}")
        print("    " + "─" * 88)
        for i, r in enumerate(top20[:10], 1):
            feats = " & ".join(f"{f}={l}" for f, l in r["features"])
            print(f"    {i:<5}{feats[:58]:<60}{r['n_match_wl']:>6}"
                  f"{r['wr']*100:>6.1f}%{r['lift_pp']*100:>+7.1f}pp")

        if f1_match:
            print(f"\n    F1 (ema_bull + coiled=medium) found at rank {f1_rank_in_2feat}: "
                  f"WR={f1_match['wr']*100:.1f}%, lift {f1_match['lift_pp']*100:+.1f}pp")
        else:
            print(f"\n    F1 (ema_bull + coiled=medium) did NOT meet "
                  f"qualifying criteria (n>=100 + lift>=5pp + p<0.01) at lifetime")

        # Build parquet rows
        for r in top20:
            parquet_rows.append({
                "signal_type": sig_type,
                "features": json.dumps([{"feature_id": f, "level": l}
                                              for f, l in r["features"]]),
                "n_match": r["n_match"],
                "n_match_wl": r["n_match_wl"],
                "n_w": r["n_w"], "n_l": r["n_l"],
                "wr": r["wr"], "lift_pp": r["lift_pp"],
                "p_value": r["p_value"],
                "feature_count": len(r["features"]),
            })

    # Save
    OUTPUT_TOP20_PATH.write_text(json.dumps(out, indent=2, default=str))
    if parquet_rows:
        pd.DataFrame(parquet_rows).to_parquet(OUTPUT_PARQUET, index=False)
    print(f"\nSaved: {OUTPUT_TOP20_PATH}")
    if parquet_rows:
        print(f"Saved: {OUTPUT_PARQUET}")

    # Summary
    print()
    print("═" * 80)
    print("L3 SUMMARY")
    print("═" * 80)
    for sig_type, data in out["by_signal_type"].items():
        n_combos = data["n_qualifying_2feat"] + data["n_qualifying_3feat"]
        print(f"\n  {sig_type}: {n_combos} qualifying combos "
              f"(2-feat: {data['n_qualifying_2feat']}, "
              f"3-feat: {data['n_qualifying_3feat']})")
        if data["f1_appearance"]:
            print(f"    F1 cell finding present at rank "
                  f"{data['f1_rank_in_2feat']}/{data['n_qualifying_2feat']} "
                  f"by 2-feat lift × volume")
        else:
            print(f"    F1 cell finding NOT in qualifying combos")

    print(f"\nTotal runtime: {time.time() - t_total:.1f}s")


if __name__ == "__main__":
    main()
