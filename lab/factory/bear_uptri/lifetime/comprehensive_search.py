"""
Bear UP_TRI cell — L2: comprehensive feature combination search at lifetime.

Within lifetime Bear UP_TRI (n=15,151, baseline 55.7%):

A. Test all 2-feature combinations from Phase-2 lifetime-Bear top-30 features.
   Filter: n ≥ 100, lift ≥ 5pp, p_value < 0.01.

B. For top 20 of (A) by lift × match_volume, test 3-feature extensions.

C. Identify "hot sub-regime markers" — combinations producing live-like
   90%+ WR at lifetime scale. When current data matches these, expect
   live-like behavior. When current data doesn't match, expect baseline.

D. Compare to Session 1 broad-band finding: did the cell investigation
   miss higher-lift lifetime patterns?

Output: lifetime/comprehensive_combinations_top20.json (summary) +
        lifetime/comprehensive_combinations.parquet (full).

Saves: lifetime/sub_regime_llm_analysis.md (Sonnet 4.5 interpretation)
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

# Reuse this cell's matches_level
_filter_path = _HERE.parent / "filter_test.py"
_spec = _ilu.spec_from_file_location("bear_uptri_filter_l2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
OUTPUT_TOP20_PATH = _HERE / "comprehensive_combinations_top20.json"
OUTPUT_PARQUET = _HERE / "comprehensive_combinations.parquet"
OUTPUT_LLM_PATH = _HERE / "sub_regime_llm_analysis.md"

TOP_K_FEATURES = 30
MIN_N_MATCH = 100
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
                              spec_by_id: dict, bounds_cache: dict
                              ) -> dict | None:
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
        "n_match": n_m, "n_match_wl": int(n_wl),
        "n_w": int(n_w), "n_l": int(n_l),
        "wr": float(wr), "lift_pp": float(lift),
        "p_value": float(p),
    }


def search_2feature(df: pd.DataFrame, baseline_wr: float,
                        feature_ids: list[str],
                        spec_by_id: dict,
                        bounds_cache: dict) -> list[dict]:
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


def llm_subregime_analysis(top_combos: list[dict], hot_markers: list[dict],
                                baseline_wr: float) -> str:
    from llm_client import LLMClient

    top_lines = "\n".join(
        f"  • {' AND '.join(f'{f}={l}' for f, l in r['features'])}  "
        f"→ n={r['n_match_wl']}, WR={r['wr']*100:.1f}%, "
        f"lift={r['lift_pp']*100:+.1f}pp"
        for r in top_combos[:10]
    )
    hot_lines = "\n".join(
        f"  • {' AND '.join(f'{f}={l}' for f, l in r['features'])}  "
        f"→ n={r['n_match_wl']}, WR={r['wr']*100:.1f}%, "
        f"lift={r['lift_pp']*100:+.1f}pp"
        for r in hot_markers[:10]
    ) if hot_markers else "(none ≥85% WR with n≥100)"

    prompt = f"""You are interpreting comprehensive lifetime feature
combination search results for the Bear UP_TRI trading cell.

## Context

• Lifetime universe: 15,151 Bear UP_TRI signals (15-yr backtest)
• Lifetime baseline: {baseline_wr*100:.1f}% WR
• Live April 2026: 74 signals, **94.6% WR** (broad-band, no filter improves)
• Live-vs-lifetime gap: +38.9pp — LARGEST in Lab

## Top 10 lifetime combinations (by lift × match_volume)

{top_lines}

## "Hot sub-regime markers" (combinations with WR ≥ 85% at lifetime)

{hot_lines}

## Hot sub-regime structural confirmation (from L1)

• `nifty_60d_return_pct=low × nifty_vol_regime=High`: 15% of lifetime,
  68.3% WR (cold 53.4%, Δ +14.9pp)
• Live April 2026 is 100% in hot sub-regime, but live's 94.6% is still
  +26.3pp above lifetime hot (68.3%). Either April 2026 is "extra hot"
  even within hot, OR Phase-5 picked the best patterns within hot.

## Sub-regime distribution per T1 detector

• stress__low_breadth     35%  60.0%
• stress__med_breadth     28%  50.7%  (hostile)
• balance__low_breadth    17%  54.6%
• balance__med_breadth    17%  53.9%
• quiet__high_breadth      1%  87.2%  (strongest, small)

## Your task

1. **Bear regime structure**: Is Bear tri-modal like Choppy (stress /
   balance / quiet), or is the structure different? What's the dominant
   axis — vol percentile, 60d return, breadth, or something else?

2. **Hot sub-regime characterization**: When are we in "hot Bear UP_TRI"
   conditions? List 3-4 features that mark it. What does it feel like
   in market terms (capitulation? early Bear? late Bear?).

3. **The 94.6% live vs 68.3% lifetime hot gap**: 26pp residual gap even
   within the same sub-regime cell. What explains it? Phase 5 selection
   bias? "Extra hot" sub-regime? Calendar luck?

4. **Production behavior shift**: When current sub-regime exits "hot"
   (vol_percentile drops below 0.70 OR nifty_60d_return rises above
   −0.10), what should the trader expect? Concrete WR estimate.

5. **Filter recommendation for non-hot sub-regimes**: When NOT in hot
   sub-regime, which lifetime combinations should be the gating filter?
   Pick 2-3 from the top combos list.

Format: markdown, ## sections per question. 3-5 short paragraphs each.
Be specific and concrete."""

    client = LLMClient()
    return client.synthesize_findings(prompt, max_tokens=2800)


def main():
    print("─" * 80)
    print("L2: Bear UP_TRI comprehensive feature combination search")
    print("─" * 80)
    t_total = time.time()

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bear") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()

    n = len(bu_wl)
    nw = (bu_wl["wlf"] == "W").sum()
    nl = (bu_wl["wlf"] == "L").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLifetime Bear UP_TRI: n={n}, baseline_wr={baseline_wr*100:.1f}%")

    importance_data = json.loads(IMPORTANCE_PATH.read_text())
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    feature_ids = _top_features_for(importance_data, "Bear", TOP_K_FEATURES)
    print(f"\nTop-{TOP_K_FEATURES} lifetime-Bear features (Phase 2):")
    print("  " + ", ".join(feature_ids[:15]))

    # 2-feat search
    print(f"\n── 2-feat combinatorial search ──")
    t0 = time.time()
    top_2feat = search_2feature(bu_wl, baseline_wr, feature_ids,
                                      spec_by_id, bounds_cache)
    print(f"    runtime: {time.time() - t0:.1f}s")

    # 3-feat extension
    print(f"\n── 3-feat extension (top 20 seeds) ──")
    t0 = time.time()
    top_3feat = search_3feature(bu_wl, baseline_wr, top_2feat,
                                      feature_ids, spec_by_id,
                                      bounds_cache)
    print(f"    runtime: {time.time() - t0:.1f}s")

    # Compile + sort
    all_combos = top_2feat + top_3feat
    all_combos.sort(key=lambda r: -(r["lift_pp"] * r["n_match_wl"]))
    top20 = all_combos[:20]

    # Hot sub-regime markers (≥85% WR)
    hot_markers = [r for r in all_combos if r["wr"] >= 0.85]
    hot_markers.sort(key=lambda r: -(r["wr"] * r["n_match_wl"]))

    # Surface
    print(f"\n── Top 15 combinations by lift × match_volume ──")
    print(f"  {'rank':<5}{'features':<60}{'n':>6}{'wr':>7}{'lift':>9}")
    print("  " + "─" * 90)
    for i, r in enumerate(top20[:15], 1):
        feats = " & ".join(f"{f}={l}" for f, l in r["features"])
        print(f"  {i:<5}{feats[:58]:<60}{r['n_match_wl']:>6}"
              f"{r['wr']*100:>6.1f}%{r['lift_pp']*100:>+8.1f}pp")

    print(f"\n── Hot sub-regime markers (lifetime WR ≥ 85%, n ≥ 100) ──")
    if hot_markers:
        print(f"  {'rank':<5}{'features':<60}{'n':>6}{'wr':>7}")
        print("  " + "─" * 80)
        for i, r in enumerate(hot_markers[:10], 1):
            feats = " & ".join(f"{f}={l}" for f, l in r["features"])
            print(f"  {i:<5}{feats[:58]:<60}{r['n_match_wl']:>6}"
                  f"{r['wr']*100:>6.1f}%")
    else:
        print(f"  None: no combination produces ≥85% lifetime WR on n≥100")
        print(f"  → Live's 94.6% WR is NOT reproducible by any 2-3 feature")
        print(f"    combination at lifetime scale. Bear UP_TRI's broad-band")
        print(f"    edge in current sub-regime is genuinely a sub-regime")
        print(f"    artifact, not a stable filterable structure.")

    out = {
        "lifetime_universe": {
            "n": int(n), "baseline_wr": float(baseline_wr),
        },
        "n_qualifying_2feat": len(top_2feat),
        "n_qualifying_3feat": len(top_3feat),
        "top20_combinations": top20,
        "hot_subregime_markers": hot_markers[:10],
    }
    OUTPUT_TOP20_PATH.write_text(json.dumps(out, indent=2, default=str))

    if all_combos:
        rows = []
        for r in all_combos[:200]:
            rows.append({
                "features": json.dumps(
                    [{"feature_id": f, "level": l}
                     for f, l in r["features"]]),
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
        print(f"Saved: {OUTPUT_PARQUET} (top 200)")

    # LLM analysis
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for sub-regime analysis...")
    print("─" * 80)
    md = llm_subregime_analysis(top20, hot_markers, baseline_wr)
    OUTPUT_LLM_PATH.write_text(
        f"# Bear UP_TRI Lifetime Sub-Regime Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{md}\n"
    )
    print(f"Saved: {OUTPUT_LLM_PATH}")

    # Summary
    print()
    print("═" * 80)
    print("L2 SUMMARY")
    print("═" * 80)
    print(f"  Qualifying 2-feat combos: {len(top_2feat)}")
    print(f"  Qualifying 3-feat combos: {len(top_3feat)}")
    print(f"  Hot sub-regime markers (≥85% lifetime WR): {len(hot_markers)}")
    if top20:
        best = top20[0]
        feats = " & ".join(f"{f}={l}" for f, l in best["features"])
        print(f"  Best lifetime pattern: {feats}")
        print(f"    n={best['n_match_wl']}, WR={best['wr']*100:.1f}%, "
              f"lift={best['lift_pp']*100:+.1f}pp")
    print(f"\nTotal runtime: {time.time() - t_total:.1f}s")


if __name__ == "__main__":
    main()
