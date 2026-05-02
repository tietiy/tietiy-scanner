"""
Bull UP_TRI cell — BU3: comprehensive lifetime feature combination search.

n=38,100 lifetime Bull UP_TRI signals (largest cell). Tests all 2-feat
combinations from Phase-2 lifetime-Bull top features, then 3-feat
extensions for top-20 seeds.

Filter criteria: n_match ≥ 200, lift ≥ +5pp, p < 0.01.

Plus:
  • Sub-regime stratified search (within recovery_bull and healthy_bull
    cells) — find filters that work specifically in those favorable cells
  • Cross-regime pattern check — do Bear UP_TRI top patterns appear in
    Bull UP_TRI?

Saves:
  lab/factory/bull_uptri/lifetime/comprehensive_combinations_top20.json
  lab/factory/bull_uptri/lifetime/comprehensive_combinations.parquet
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
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from feature_loader import FeatureRegistry  # noqa: E402

_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bu3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bu3", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bu3"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
OUTPUT_TOP20_PATH = _HERE / "comprehensive_combinations_top20.json"
OUTPUT_PARQUET = _HERE / "comprehensive_combinations.parquet"

TOP_K_FEATURES = 30
MIN_N_MATCH = 200
MIN_LIFT = 0.05
P_VALUE_THRESHOLD = 0.01


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _binomial_p(k: int, n: int, p_null: float) -> float:
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
    if spec.value_type == "bool":
        return ["True", "False"]
    if spec.value_type == "categorical":
        non_null = signal_values.dropna()
        if non_null.empty:
            return []
        return non_null.astype(str).value_counts().head(3).index.tolist()
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
                              spec_by_id: dict, bounds_cache: dict,
                              min_n: int = MIN_N_MATCH) -> dict | None:
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
    if n_m < min_n:
        return None
    n_w = (matched["wlf"] == "W").sum()
    n_l = (matched["wlf"] == "L").sum()
    n_wl = n_w + n_l
    if n_wl < min_n:
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
        "n_match": n_m, "n_match_wl": int(n_wl),
        "n_w": int(n_w), "n_l": int(n_l),
        "wr": float(wr), "lift_pp": float(lift),
        "p_value": float(p),
    }


def search_2feature(df: pd.DataFrame, baseline_wr: float,
                        feature_ids: list[str],
                        spec_by_id: dict, bounds_cache: dict,
                        min_n: int = MIN_N_MATCH) -> list[dict]:
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
                                              spec_by_id, bounds_cache, min_n)
                n_tested += 1
                if r is not None:
                    results.append(r)
    print(f"    {n_tested} 2-feat combos tested, {len(results)} qualifying")
    results.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    return results


def search_3feature(df: pd.DataFrame, baseline_wr: float,
                        top_2feat: list[dict], feature_ids: list[str],
                        spec_by_id: dict, bounds_cache: dict,
                        max_seeds: int = 20,
                        min_n: int = MIN_N_MATCH) -> list[dict]:
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
                                              spec_by_id, bounds_cache, min_n)
                n_tested += 1
                if r is not None:
                    results.append(r)
    print(f"    {n_tested} 3-feat combos tested, {len(results)} qualifying")
    results.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    return results


def main():
    print("─" * 80)
    print("BU3: Bull UP_TRI comprehensive lifetime feature search")
    print("─" * 80)
    t_total = time.time()

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bull") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()

    # Apply Bull sub-regime detector
    bu_wl["sub"] = bu_wl.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    n = len(bu_wl)
    nw = (bu_wl["wlf"] == "W").sum()
    nl = (bu_wl["wlf"] == "L").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLifetime Bull UP_TRI: n={n}, baseline_wr={baseline_wr*100:.1f}%")

    importance_data = json.loads(IMPORTANCE_PATH.read_text())
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # Try Bull-specific feature importance; fall back to universal if missing
    feature_ids = _top_features_for(importance_data, "Bull", TOP_K_FEATURES)
    if not feature_ids:
        # Use universal (across all regimes) top features
        universal = importance_data.get("ranked_features",
                                              importance_data.get("universal", []))
        feature_ids = [f["feature_id"] for f in universal[:TOP_K_FEATURES]]
        if not feature_ids:
            # Final fallback — manually-curated list
            feature_ids = [
                "ema_alignment", "MACD_signal", "ROC_10",
                "nifty_vol_regime", "market_breadth_pct",
                "nifty_60d_return_pct", "nifty_200d_return_pct",
                "day_of_week", "day_of_month_bucket",
                "swing_high_count_20d", "swing_low_count_20d",
                "inside_bar_flag", "range_compression_60d",
                "consolidation_quality", "multi_tf_alignment_score",
                "52w_high_distance_pct", "52w_low_distance_pct",
                "compression_duration", "RSI_14",
                "ema50_slope_20d_pct", "ema200_distance_pct",
                "vol_climax_flag", "vol_dryup_flag",
                "higher_highs_intact_flag", "advance_decline_ratio_20d",
                "sector_rank_within_universe", "MACD_histogram_slope",
                "regime_score", "fib_50_proximity_atr",
                "fib_382_proximity_atr",
            ]
    print(f"\nTop-{len(feature_ids)} Bull lifetime features:")
    print("  " + ", ".join(feature_ids[:15]))

    # Run search on full Bull UP_TRI
    print(f"\n── Full lifetime 2-feat search (n={n}) ──")
    t0 = time.time()
    top_2feat = search_2feature(bu_wl, baseline_wr, feature_ids,
                                      spec_by_id, bounds_cache,
                                      min_n=MIN_N_MATCH)
    print(f"    runtime: {time.time() - t0:.1f}s")

    print(f"\n── Full lifetime 3-feat extension (top 20 seeds) ──")
    t0 = time.time()
    top_3feat = search_3feature(bu_wl, baseline_wr, top_2feat,
                                      feature_ids, spec_by_id, bounds_cache)
    print(f"    runtime: {time.time() - t0:.1f}s")

    all_combos = top_2feat + top_3feat
    all_combos.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    top20 = all_combos[:20]

    # Sub-regime stratified search — within recovery_bull
    print(f"\n── Sub-regime stratified: within recovery_bull (n={(bu_wl['sub']=='recovery_bull').sum()}) ──")
    rec_grp = bu_wl[bu_wl["sub"] == "recovery_bull"]
    rec_baseline = (rec_grp["wlf"] == "W").sum() / max(1, ((rec_grp["wlf"] == "W").sum()
                                                              + (rec_grp["wlf"] == "L").sum()))
    rec_2feat = []
    if len(rec_grp) > 200:
        rec_2feat = search_2feature(rec_grp, rec_baseline, feature_ids,
                                          spec_by_id, bounds_cache, min_n=50)
        print(f"    recovery_bull baseline {rec_baseline*100:.1f}%")

    # Sub-regime stratified — within healthy_bull
    print(f"\n── Sub-regime stratified: within healthy_bull (n={(bu_wl['sub']=='healthy_bull').sum()}) ──")
    hth_grp = bu_wl[bu_wl["sub"] == "healthy_bull"]
    hth_baseline = (hth_grp["wlf"] == "W").sum() / max(1, ((hth_grp["wlf"] == "W").sum()
                                                              + (hth_grp["wlf"] == "L").sum()))
    hth_2feat = []
    if len(hth_grp) > 200:
        hth_2feat = search_2feature(hth_grp, hth_baseline, feature_ids,
                                          spec_by_id, bounds_cache, min_n=100)
        print(f"    healthy_bull baseline {hth_baseline*100:.1f}%")

    # Surface
    print(f"\n── Top 15 full-Bull lifetime patterns ──")
    print(f"  {'rank':<5}{'features':<60}{'n':>6}{'wr':>7}{'lift':>9}")
    print("  " + "─" * 90)
    for i, r in enumerate(top20[:15], 1):
        feats = " & ".join(f"{f}={l}" for f, l in r["features"])
        print(f"  {i:<5}{feats[:58]:<60}{r['n_match_wl']:>6}"
              f"{r['wr']*100:>6.1f}%{r['lift_pp']*100:>+8.1f}pp")

    if rec_2feat:
        print(f"\n── Top 5 recovery_bull patterns (within sub-regime) ──")
        for i, r in enumerate(rec_2feat[:5], 1):
            feats = " & ".join(f"{f}={l}" for f, l in r["features"])
            print(f"  {i}. {feats}: n={r['n_match_wl']}, "
                  f"WR={r['wr']*100:.1f}%, lift={r['lift_pp']*100:+.1f}pp "
                  f"vs sub-regime baseline {rec_baseline*100:.1f}%")

    if hth_2feat:
        print(f"\n── Top 5 healthy_bull patterns (within sub-regime) ──")
        for i, r in enumerate(hth_2feat[:5], 1):
            feats = " & ".join(f"{f}={l}" for f, l in r["features"])
            print(f"  {i}. {feats}: n={r['n_match_wl']}, "
                  f"WR={r['wr']*100:.1f}%, lift={r['lift_pp']*100:+.1f}pp "
                  f"vs sub-regime baseline {hth_baseline*100:.1f}%")

    # Cross-regime pattern check — Bear UP_TRI's top patterns in Bull UP_TRI
    print(f"\n── Cross-regime pattern check: Bear UP_TRI patterns in Bull UP_TRI ──")
    bear_patterns = [
        [("nifty_60d_return_pct", "low"), ("swing_high_count_20d", "low")],
        [("day_of_month_bucket", "wk4"), ("swing_high_count_20d", "low")],
        [("market_breadth_pct", "low"), ("ema50_slope_20d_pct", "low")],
    ]
    cross_results = []
    for combo in bear_patterns:
        r = _evaluate_combination(bu_wl, baseline_wr, combo,
                                        spec_by_id, bounds_cache, min_n=100)
        feats = " & ".join(f"{f}={l}" for f, l in combo)
        if r is None:
            # Manual evaluation to surface even if doesn't pass filter
            mask = pd.Series([True] * len(bu_wl), index=bu_wl.index)
            for fid, lvl in combo:
                spec = spec_by_id.get(fid)
                col = f"feat_{fid}"
                if col not in bu_wl.columns:
                    continue
                m = bu_wl[col].apply(
                    lambda v: matches_level(spec, v, lvl, bounds_cache)
                ).fillna(False)
                mask = mask & m
            grp = bu_wl[mask]
            nw = (grp["wlf"] == "W").sum()
            nl = (grp["wlf"] == "L").sum()
            wr = nw / (nw + nl) if (nw + nl) > 0 else None
            lift = (wr - baseline_wr) * 100 if wr else None
            cross_results.append({
                "pattern": feats,
                "n": int(nw + nl), "wr": wr,
                "lift_pp": lift,
                "qualifies_in_bull": False,
            })
            print(f"  {feats[:60]}: n={nw+nl}, "
                  f"WR={(wr or 0)*100:.1f}%, lift={(lift or 0):+.1f}pp "
                  f"(does NOT qualify in Bull, lift<5pp)")
        else:
            cross_results.append({
                "pattern": feats, "n": r["n_match_wl"],
                "wr": r["wr"], "lift_pp": r["lift_pp"],
                "qualifies_in_bull": True,
            })
            print(f"  {feats[:60]}: n={r['n_match_wl']}, "
                  f"WR={r['wr']*100:.1f}%, lift={r['lift_pp']*100:+.1f}pp "
                  f"✓ qualifies in Bull")

    # Save
    out = {
        "lifetime_universe": {"n": int(n), "baseline_wr": float(baseline_wr)},
        "n_qualifying_2feat_full": len(top_2feat),
        "n_qualifying_3feat_full": len(top_3feat),
        "top20_combinations_full": top20,
        "recovery_bull_top5": rec_2feat[:5],
        "healthy_bull_top5": hth_2feat[:5],
        "recovery_bull_baseline_wr": float(rec_baseline) if len(rec_grp) else None,
        "healthy_bull_baseline_wr": float(hth_baseline) if len(hth_grp) else None,
        "cross_regime_pattern_check": cross_results,
    }
    OUTPUT_TOP20_PATH.write_text(json.dumps(out, indent=2, default=str))

    # Save full parquet
    if all_combos:
        rows = []
        for r in all_combos[:300]:
            rows.append({
                "features": json.dumps(
                    [{"feature_id": f, "level": l} for f, l in r["features"]]),
                "n_match": int(r["n_match"]),
                "n_match_wl": int(r["n_match_wl"]),
                "n_w": int(r["n_w"]), "n_l": int(r["n_l"]),
                "wr": float(r["wr"]),
                "lift_pp": float(r["lift_pp"]),
                "p_value": float(r["p_value"]),
                "feature_count": len(r["features"]),
            })
        pd.DataFrame(rows).to_parquet(OUTPUT_PARQUET, index=False)

    print(f"\nSaved: {OUTPUT_TOP20_PATH}")
    if all_combos:
        print(f"Saved: {OUTPUT_PARQUET} (top 300)")

    print(f"\nTotal runtime: {time.time() - t_total:.1f}s")
    print()
    print("═" * 80)
    print("BU3 SUMMARY")
    print("═" * 80)
    print(f"  Full lifetime: {len(top_2feat)} qualifying 2-feat, "
          f"{len(top_3feat)} qualifying 3-feat")
    print(f"  recovery_bull (n={len(rec_grp)}): "
          f"{len(rec_2feat)} qualifying 2-feat")
    print(f"  healthy_bull (n={len(hth_grp)}): "
          f"{len(hth_2feat)} qualifying 2-feat")
    print(f"  Cross-regime check: {sum(1 for r in cross_results if r['qualifies_in_bull'])}/3 "
          f"Bear UP_TRI patterns qualify in Bull")


if __name__ == "__main__":
    main()
