"""
Bull DOWN_TRI cell — BD2: differentiator analysis + direction-flip
predictions + cross-cell calendar inversion + LLM mechanism interpretation.

Lifetime-only methodology (no Phase 5 winners exist; 0 live Bull signals).

Tests architectural predictions inherited from Bull UP_TRI cell:

  Test 1 (regime anchor inversion):
    Bull UP_TRI: 20d_return=high WINNER (+5-8pp)
    Bull DOWN_TRI predicted: 20d_return=low WINNER (inversion)

  Test 2 (200d return for late-cycle short):
    Bull UP_TRI: 200d=high ANTI (-2.1pp)
    Bull DOWN_TRI predicted: 200d=high WINNER (mature trend reversal)
    Already partial-confirmed in BU2: +1.5pp

  Test 3 (calendar inversion):
    Bull UP_TRI: wk4 +2.6pp (mild winner)
    Bull DOWN_TRI predicted: wk2 winner / wk4 anti
    Parallel to Bear UP_TRI (+wk4) vs Bear DOWN_TRI (+wk2) inversion

  Test 4 (sector inversion):
    Bull UP_TRI: IT/Health/Consumer top (growth/quality)
    Bull DOWN_TRI: Metal/Bank top (cyclicals) — partially confirmed in BD1

Saves: lab/factory/bull_downtri/differentiators.json
       lab/factory/bull_downtri/differentiators_llm.md
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse matches_level
_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bd2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

# Reuse Bull sub-regime detector
_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bd2", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bd2"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "differentiators.json"
LLM_PATH = _HERE / "differentiators_llm.md"

FEATURE_PANEL = [
    ("nifty_60d_return_pct", "numeric"),
    ("nifty_20d_return_pct", "numeric"),
    ("nifty_200d_return_pct", "numeric"),
    ("nifty_vol_regime", "categorical"),
    ("nifty_vol_percentile_20d", "numeric"),
    ("market_breadth_pct", "numeric"),
    ("day_of_week", "categorical"),
    ("day_of_month_bucket", "categorical"),
    ("ema_alignment", "categorical"),
    ("MACD_signal", "categorical"),
    ("MACD_histogram_slope", "categorical"),
    ("RSI_14", "numeric"),
    ("ROC_10", "numeric"),
    ("higher_highs_intact_flag", "bool"),
    ("inside_bar_flag", "bool"),
    ("range_compression_60d", "numeric"),
    ("consolidation_quality", "categorical"),
    ("multi_tf_alignment_score", "numeric"),
    ("52w_high_distance_pct", "numeric"),
    ("52w_low_distance_pct", "numeric"),
    ("compression_duration", "numeric"),
    ("swing_high_count_20d", "numeric"),
    ("swing_low_count_20d", "numeric"),
    ("vol_climax_flag", "bool"),
    ("vol_dryup_flag", "bool"),
    ("ema50_slope_20d_pct", "numeric"),
    ("advance_decline_ratio_20d", "numeric"),
]


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _wr(grp: pd.DataFrame) -> dict:
    nw = int((grp["wlf"] == "W").sum())
    nl = int((grp["wlf"] == "L").sum())
    n_wl = nw + nl
    return {
        "n": len(grp), "n_w": nw, "n_l": nl,
        "n_wl": n_wl,
        "wr": (nw / n_wl) if n_wl > 0 else None,
    }


def lifetime_feature_differential(
    df: pd.DataFrame, feature_panel, spec_by_id, bounds_cache,
    min_n: int = 100,
) -> list[dict]:
    """For each (feature, level), compute presence_wr vs absence_wr."""
    results = []
    n_total = len(df)

    for fid, vtype in feature_panel:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue

        if vtype == "bool":
            levels = ["True", "False"]
        elif vtype == "categorical":
            top = df[col].dropna().astype(str).value_counts().head(4)
            levels = top.index.tolist()
        else:
            levels = ["low", "medium", "high"]

        for lvl in levels:
            mask = df[col].apply(
                lambda v: matches_level(spec, v, lvl, bounds_cache)
            ).fillna(False)
            present = df[mask]
            absent = df[~mask]
            n_p_wl = (present["wlf"] == "W").sum() + (present["wlf"] == "L").sum()
            n_a_wl = (absent["wlf"] == "W").sum() + (absent["wlf"] == "L").sum()
            if n_p_wl < min_n or n_a_wl < min_n:
                continue
            wr_p = (present["wlf"] == "W").sum() / n_p_wl if n_p_wl > 0 else None
            wr_a = (absent["wlf"] == "W").sum() / n_a_wl if n_a_wl > 0 else None
            if wr_p is None or wr_a is None:
                continue
            delta_pp = (wr_p - wr_a) * 100
            results.append({
                "feature_id": fid,
                "level": lvl,
                "presence_n_wl": int(n_p_wl),
                "presence_pct": float(n_p_wl / n_total),
                "presence_wr": float(wr_p),
                "absence_wr": float(wr_a),
                "delta_pp": float(delta_pp),
            })

    results.sort(key=lambda r: -abs(r["delta_pp"]))
    return results


def main():
    print("─" * 80)
    print("BD2: Bull DOWN_TRI differentiators + direction-flip + cross-cell tests")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bd = df[(df["regime"] == "Bull") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    bd_wl = bd[bd["wlf"].isin(["W", "L", "F"])].copy()

    baseline_wr = _wr(bd_wl)["wr"]
    print(f"\nLifetime n={len(bd_wl)}, baseline {baseline_wr*100:.1f}%")

    # Apply Bull sub-regime detector
    bd_wl["sub"] = bd_wl.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    findings = {
        "lifetime_baseline_wr": float(baseline_wr),
        "top_winner_features": [],
        "top_anti_features": [],
        "direction_flip_tests": {},
        "calendar_inversion": {},
        "subregime_within_filters": {},
    }

    # ── A. Lifetime feature differential ────────────────────────────
    print(f"\n══ A. Lifetime feature differential ══")
    diff = lifetime_feature_differential(
        bd_wl, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=100)

    print(f"\n  Top 10 winner features (positive delta):")
    print(f"  {'feature':<32}{'level':<10}{'pres_wr':>10}"
          f"{'abs_wr':>10}{'delta':>10}")
    print("  " + "─" * 72)
    top_winners = sorted(diff, key=lambda r: -r["delta_pp"])[:10]
    for r in top_winners:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    findings["top_winner_features"] = top_winners

    print(f"\n  Top 10 anti-features (negative delta):")
    top_anti = sorted(diff, key=lambda r: r["delta_pp"])[:10]
    for r in top_anti:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    findings["top_anti_features"] = top_anti

    # ── B. Direction-flip prediction tests ──────────────────────────
    print(f"\n══ B. Direction-flip prediction tests (vs Bull UP_TRI) ══")

    flip_tests = [
        ("nifty_20d_return_pct", "low",
         "Bull UP_TRI 20d=high WINNER → predicted DOWN_TRI 20d=low WINNER"),
        ("nifty_20d_return_pct", "high",
         "Bull UP_TRI 20d=high WINNER → predicted DOWN_TRI 20d=high ANTI"),
        ("nifty_200d_return_pct", "high",
         "Bull UP_TRI 200d=high ANTI → predicted DOWN_TRI 200d=high WINNER"),
        ("nifty_200d_return_pct", "low",
         "Bull UP_TRI 200d=low WINNER (recovery) → predicted DOWN_TRI 200d=low ANTI"),
        ("market_breadth_pct", "low",
         "Bull UP_TRI breadth=low ANTI → predicted DOWN_TRI breadth=low WINNER"),
        ("RSI_14", "high",
         "Bull UP_TRI RSI=high not specific → DOWN_TRI RSI=high may indicate overbought"),
    ]

    for fid, lvl, desc in flip_tests:
        # Find matching diff result
        matches = [r for r in diff
                   if r["feature_id"] == fid and r["level"] == lvl]
        if matches:
            r = matches[0]
            findings["direction_flip_tests"][f"{fid}={lvl}"] = r
            verdict = ("✓ CONFIRMED" if (r["delta_pp"] > 2 and "WINNER" in desc)
                       or (r["delta_pp"] < -2 and "ANTI" in desc)
                       else ("✗ REFUTED" if abs(r["delta_pp"]) > 2 else
                             "neutral"))
            print(f"\n  {desc}")
            print(f"    Actual: delta={r['delta_pp']:+.1f}pp "
                  f"(n_present={r['presence_n_wl']})  → {verdict}")

    # ── C. Cross-cell calendar inversion test ───────────────────────
    print(f"\n══ C. Cross-cell calendar inversion ══")
    print(f"  Predicted: Bull DOWN_TRI calendar profile inverted vs Bull UP_TRI")
    print(f"  Bull UP_TRI: wk4 +2.6pp WINNER, wk3 -3.3pp ANTI")
    print(f"  Bull DOWN_TRI predicted: wk2 winner / wk4 anti")
    cal_table = {}
    for wk in ("wk1", "wk2", "wk3", "wk4"):
        grp = bd_wl[bd_wl["feat_day_of_month_bucket"] == wk]
        st = _wr(grp)
        if st["wr"] is None or st["n_wl"] < 100:
            continue
        lift = (st["wr"] - baseline_wr) * 100
        cal_table[wk] = {
            "n": int(st["n_wl"]), "wr": float(st["wr"]),
            "lift_pp": float(lift),
        }
        print(f"    {wk}: n={st['n_wl']:>5} WR={st['wr']*100:.1f}% "
              f"lift={lift:+.1f}pp")
    findings["calendar_inversion"] = cal_table

    # ── D. Sub-regime within-cell filters ───────────────────────────
    print(f"\n══ D. Within-late_bull filters (best Bull DOWN_TRI sub-regime) ══")
    late_grp = bd_wl[bd_wl["sub"] == "late_bull"]
    late_baseline = _wr(late_grp)["wr"]
    print(f"  late_bull n={len(late_grp)}, sub-regime baseline {late_baseline*100:.1f}%")

    if len(late_grp) >= 200:
        late_diff = lifetime_feature_differential(
            late_grp, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=50)
        late_winners = sorted(late_diff, key=lambda r: -r["delta_pp"])[:5]
        print(f"\n  Top 5 winners within late_bull (vs late_bull baseline):")
        for r in late_winners:
            print(f"    {r['feature_id']}={r['level']:<8} "
                  f"pres={r['presence_wr']*100:.1f}% (n={r['presence_n_wl']}) "
                  f"delta={r['delta_pp']:+.1f}pp")
        findings["subregime_within_filters"]["late_bull"] = late_winners

    OUTPUT_PATH.write_text(json.dumps(findings, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM mechanism interpretation ────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for cross-cell mechanism interpretation...")
    print("─" * 80)

    from llm_client import LLMClient

    flip_summary = "\n".join(
        f"  • {fid}={r['level']}: "
        f"delta={r['delta_pp']:+.1f}pp (n={r['presence_n_wl']})"
        for fid, r in findings["direction_flip_tests"].items()
    )
    cal_summary = "\n".join(
        f"  • {wk}: WR={info['wr']*100:.1f}% lift={info['lift_pp']:+.1f}pp"
        for wk, info in findings["calendar_inversion"].items()
    )
    win_summary = "\n".join(
        f"  • {r['feature_id']}={r['level']}: "
        f"delta={r['delta_pp']:+.1f}pp (n={r['presence_n_wl']})"
        for r in top_winners[:8]
    )
    anti_summary = "\n".join(
        f"  • {r['feature_id']}={r['level']}: "
        f"delta={r['delta_pp']:+.1f}pp"
        for r in top_anti[:8]
    )

    prompt = f"""You are interpreting Bull DOWN_TRI cell differentiator
analysis with cross-cell direction-flip predictions tested.

## Cell context

• Lifetime: n=10,024 Bull DOWN_TRI signals; baseline 43.4% WR
• 0 live Bull signals (lifetime-only methodology)
• Bull regime sub-regime structure (per BU1 detector):
    recovery_bull WR=35.7% (worst — INVERTS UP_TRI's 60.2% best)
    healthy_bull  WR=40.5%
    normal_bull   WR=42.6%
    late_bull     WR=53.0% ★ (best — INVERTS UP_TRI's 45.1% worst)

## Direction-flip prediction tests

{flip_summary}

## Calendar pattern (cross-cell inversion test)

{cal_summary}

## Lifetime top winner features

{win_summary}

## Lifetime top anti-features

{anti_summary}

## Bull UP_TRI architecture (for comparison)

• Lifetime baseline 52.0%
• Top winner: nifty_20d_return=high (recency)
• 200d_return=high ANTI (-2.1pp)
• Calendar: wk4 winner (+2.6pp), wk3 anti (-3.3pp)
• Sectors: IT/Health/Consumer top (growth/quality)
• Best sub-regime: recovery_bull 60.2% (low 200d × low breadth)

## Bear DOWN_TRI architecture (for comparison)

• Lifetime baseline 46.1%
• 0 Phase 5 winners; all 19 combos WATCH
• Top winners: wk2 +15pp, higher_highs_intact +4pp
• Sectors: defensives top (Pharma, Health, Other)
• kill_001: Bank × Bear DOWN_TRI

## Your task

1. **Direction-flip pattern verdict.** Did the cross-cell direction
   inversion hold for Bull DOWN_TRI? Quote specific deltas. Is the
   pattern stronger or weaker than predicted?

2. **Bull DOWN_TRI mechanism.** What does this cell represent
   mechanically? Trend exhaustion shorts in late-stage Bull?
   Rotation out of leaders into laggards? Mean-reversion against
   momentum?

3. **late_bull sub-regime as primary edge zone.** late_bull is the
   ONLY sub-regime where Bull DOWN_TRI has positive WR (53%, +9.6pp
   over baseline). Is this a deployable filter, or fragile small
   sample?

4. **Cross-cell vs Bear DOWN_TRI.** Bear DOWN_TRI was DEFERRED
   (lifetime baseline 46.1%, 0 Phase 5 winners). Bull DOWN_TRI
   lifetime baseline is LOWER (43.4%) but has a clean sub-regime
   edge (late_bull 53%). Does this make Bull DOWN_TRI more deployable
   than Bear DOWN_TRI when Bull regime returns?

5. **Both DOWN_TRI cells contrarian-short hostility.** Bear DOWN_TRI
   live 18.2%, Bull DOWN_TRI no live data. Is contrarian short
   fundamentally harder than contrarian long across all regimes?
   What architectural truth does this expose?

6. **Production verdict for Bull DOWN_TRI.** PROVISIONAL_OFF default.
   Manual enable: late_bull only? Or just SKIP all?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference deltas and sample sizes."""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    LLM_PATH.write_text(
        f"# Bull DOWN_TRI Differentiator Analysis — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"Saved: {LLM_PATH}")


if __name__ == "__main__":
    main()
