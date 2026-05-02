"""
Bull BULL_PROXY cell — BP2: differentiator analysis + cross-cell
prediction tests + LLM mechanism interpretation.

Tests 4 cross-cell predictions:
  1. vol_climax_flag=True → ANTI? (replicate Bear BULL_PROXY -11.0pp)
  2. nifty_20d_return=high → WINNER? (Bull UP_TRI primary anchor)
  3. inside_bar=True → ANTI? (Bear BULL_PROXY -9.4pp; range expansion)
  4. Sector preferences vs Bear BULL_PROXY (defensives) and Bull UP_TRI

Saves: lab/factory/bull_bullproxy/differentiators.json
       lab/factory/bull_bullproxy/differentiators_llm.md
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

_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bp2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bp2", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bp2"] = _detector_mod
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
        "n": len(grp), "n_w": nw, "n_l": nl, "n_wl": n_wl,
        "wr": (nw / n_wl) if n_wl > 0 else None,
    }


def lifetime_feature_differential(df, feature_panel, spec_by_id,
                                       bounds_cache, min_n=30):
    """Lower min_n=30 for thinner Bull BULL_PROXY cohort (n=2685)."""
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
            levels = df[col].dropna().astype(str).value_counts().head(4).index.tolist()
        else:
            levels = ["low", "medium", "high"]
        for lvl in levels:
            mask = df[col].apply(
                lambda v: matches_level(spec, v, lvl, bounds_cache)
            ).fillna(False)
            present = df[mask]
            absent = df[~mask]
            n_p = (present["wlf"] == "W").sum() + (present["wlf"] == "L").sum()
            n_a = (absent["wlf"] == "W").sum() + (absent["wlf"] == "L").sum()
            if n_p < min_n or n_a < min_n:
                continue
            wr_p = (present["wlf"] == "W").sum() / n_p if n_p > 0 else None
            wr_a = (absent["wlf"] == "W").sum() / n_a if n_a > 0 else None
            if wr_p is None or wr_a is None:
                continue
            results.append({
                "feature_id": fid, "level": lvl,
                "presence_n_wl": int(n_p),
                "presence_pct": float(n_p / n_total),
                "presence_wr": float(wr_p),
                "absence_wr": float(wr_a),
                "delta_pp": float((wr_p - wr_a) * 100),
            })
    results.sort(key=lambda r: -abs(r["delta_pp"]))
    return results


def main():
    print("─" * 80)
    print("BP2: Bull BULL_PROXY differentiators + cross-cell predictions")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bp = df[(df["regime"] == "Bull") & (df["signal"] == "BULL_PROXY")].copy()
    bp["wlf"] = bp["outcome"].apply(_wlf)
    bp_wl = bp[bp["wlf"].isin(["W", "L", "F"])].copy()

    baseline_wr = _wr(bp_wl)["wr"]
    print(f"\nLifetime n={len(bp_wl)}, baseline {baseline_wr*100:.1f}%")

    bp_wl["sub"] = bp_wl.apply(
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
        "cross_cell_predictions": {},
    }

    # ── A. Lifetime feature differential ────────────────────────────
    print(f"\n══ A. Lifetime feature differential ══")
    diff = lifetime_feature_differential(
        bp_wl, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=30)

    print(f"\n  Top 12 winner features:")
    print(f"  {'feature':<32}{'level':<10}{'pres_wr':>10}"
          f"{'abs_wr':>10}{'delta':>10}")
    print("  " + "─" * 72)
    top_winners = sorted(diff, key=lambda r: -r["delta_pp"])[:12]
    for r in top_winners:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    findings["top_winner_features"] = top_winners

    print(f"\n  Top 10 anti-features:")
    top_anti = sorted(diff, key=lambda r: r["delta_pp"])[:10]
    for r in top_anti:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    findings["top_anti_features"] = top_anti

    # ── B. Cross-cell prediction tests ──────────────────────────────
    print(f"\n══ B. Cross-cell prediction tests ══")

    test_cases = [
        ("vol_climax_flag", "True",
         "vol_climax=True ANTI? (Bear BULL_PROXY -11.0pp)",
         "anti", -2),
        ("nifty_20d_return_pct", "high",
         "nifty_20d=high WINNER? (Bull UP_TRI primary anchor)",
         "winner", 2),
        ("inside_bar_flag", "True",
         "inside_bar=True ANTI? (Bear BULL_PROXY -9.4pp; range expansion preferred)",
         "anti", -2),
        ("nifty_60d_return_pct", "low",
         "nifty_60d=low WINNER? (Bear BULL_PROXY +17.9pp anchor)",
         "winner", 2),
        ("market_breadth_pct", "high",
         "breadth=high WINNER? (broad participation in Bull bullish setups)",
         "winner", 2),
        ("52w_high_distance_pct", "high",
         "52w_high_distance=high WINNER? (Bear BULL_PROXY +14.4pp)",
         "winner", 2),
    ]

    for fid, lvl, desc, expected_dir, threshold in test_cases:
        matches = [r for r in diff
                   if r["feature_id"] == fid and r["level"] == lvl]
        if not matches:
            print(f"\n  {desc}")
            print(f"    SKIPPED — feature/level not in diff")
            continue
        r = matches[0]
        delta = r["delta_pp"]
        if expected_dir == "anti":
            verdict = ("✓ CONFIRMED" if delta < threshold else
                       ("✗ REFUTED" if delta > -threshold else "neutral"))
        else:
            verdict = ("✓ CONFIRMED" if delta > threshold else
                       ("✗ REFUTED" if delta < -threshold else "neutral"))
        print(f"\n  {desc}")
        print(f"    Actual: delta={delta:+.1f}pp on n={r['presence_n_wl']}  "
              f"→ {verdict}")
        findings["cross_cell_predictions"][f"{fid}={lvl}"] = {
            **r,
            "expected_direction": expected_dir,
            "verdict": verdict,
        }

    # ── C. Sub-regime within filters (recovery_bull) ────────────────
    print(f"\n══ C. Within-recovery_bull filters (n={(bp_wl['sub']=='recovery_bull').sum()}) ══")
    rec_grp = bp_wl[bp_wl["sub"] == "recovery_bull"]
    if len(rec_grp) >= 50:
        rec_baseline = _wr(rec_grp)["wr"]
        print(f"  recovery_bull baseline {rec_baseline*100:.1f}%")
        rec_diff = lifetime_feature_differential(
            rec_grp, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=20)
        rec_top = sorted(rec_diff, key=lambda r: -r["delta_pp"])[:5]
        print(f"\n  Top 5 within-recovery_bull winners:")
        for r in rec_top:
            print(f"    {r['feature_id']}={r['level']:<8} "
                  f"pres={r['presence_wr']*100:.1f}% (n={r['presence_n_wl']}) "
                  f"delta={r['delta_pp']:+.1f}pp")
        findings["recovery_bull_top_filters"] = rec_top

    # ── D. Sub-regime within healthy_bull ───────────────────────────
    print(f"\n══ D. Within-healthy_bull filters (n={(bp_wl['sub']=='healthy_bull').sum()}) ══")
    hth_grp = bp_wl[bp_wl["sub"] == "healthy_bull"]
    if len(hth_grp) >= 100:
        hth_baseline = _wr(hth_grp)["wr"]
        print(f"  healthy_bull baseline {hth_baseline*100:.1f}%")
        hth_diff = lifetime_feature_differential(
            hth_grp, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=30)
        hth_top = sorted(hth_diff, key=lambda r: -r["delta_pp"])[:5]
        print(f"\n  Top 5 within-healthy_bull winners:")
        for r in hth_top:
            print(f"    {r['feature_id']}={r['level']:<8} "
                  f"pres={r['presence_wr']*100:.1f}% (n={r['presence_n_wl']}) "
                  f"delta={r['delta_pp']:+.1f}pp")
        findings["healthy_bull_top_filters"] = hth_top

    OUTPUT_PATH.write_text(json.dumps(findings, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM analysis ────────────────────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for cross-cell mechanism interpretation...")
    print("─" * 80)

    from llm_client import LLMClient
    win_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}: "
        f"delta={r['delta_pp']:+.1f}pp (n={r['presence_n_wl']})"
        for r in top_winners[:8]
    )
    anti_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}: "
        f"delta={r['delta_pp']:+.1f}pp"
        for r in top_anti[:6]
    )
    pred_lines = "\n".join(
        f"  • {fid}: delta={r['delta_pp']:+.1f}pp → {r['verdict']}"
        for fid, r in findings["cross_cell_predictions"].items()
    )

    prompt = f"""You are interpreting Bull BULL_PROXY cell differentiator
analysis with cross-cell prediction tests.

## Cell context

• Lifetime n=2,685 Bull BULL_PROXY signals; baseline 51.1% WR
• 0 live Bull signals (lifetime-only methodology)
• Sub-regime distribution (Bull detector applied):
    recovery_bull n=70  (2.6%)  WR=57.4% (+6.2pp)  ← best
    healthy_bull  n=333 (12.4%) WR=53.4% (+2.3pp)
    normal_bull   n=2011 (74.9%) WR=51.5% (+0.4pp)
    late_bull     n=268 (10.0%)  WR=43.6% (-7.5pp)  ← worst
• Direction-alignment with Bull UP_TRI: ✓ ALIGNED (3/4 sub-regimes)

## Lifetime feature differential — top 8 winners

{win_lines}

## Lifetime top 6 anti-features

{anti_lines}

## Cross-cell prediction tests

{pred_lines}

## Cross-regime context

Bear BULL_PROXY (lifetime baseline 47.3%; HOT-only filter +17.9pp lift):
- Top winner: nifty_60d_return=low (+17.9pp; macro capitulation)
- Top winner: 52w_high_distance=high (+14.4pp; beaten down)
- Top anti: vol_climax=True (-11.0pp; capitulation breaks support)
- Top anti: inside_bar=True (-9.4pp; range expansion preferred)

Bull UP_TRI (lifetime baseline 52.0%):
- Top winner: nifty_20d_return=high (+5-8pp; recent strength)
- Best sub-regime: recovery_bull 60.2% (low 200d × low breadth)

## Your task

1. **Mechanism — what does Bull BULL_PROXY represent?** Support
   rejection in Bull regime — unlike Bear BULL_PROXY (capitulation
   reversal at extreme oversold), Bull BULL_PROXY is "support holds
   in sustained uptrend". What does this mean for institutional
   behavior? Why does it work?

2. **vol_climax replication test verdict.** Was vol_climax=True ANTI
   in Bull regime as predicted? If yes, this is a universal
   BULL_PROXY anti-feature (capitulation breaks support across regimes).
   If no, what changes in Bull regime?

3. **inside_bar=True direction across regimes.** Bear BULL_PROXY
   prefers range expansion (inside_bar=True is -9.4pp anti). Did Bull
   BULL_PROXY show same preference?

4. **20d_return alignment with Bull UP_TRI.** Both bullish Bull cells
   should share the recency anchor (nifty_20d=high). Was this
   confirmed? What's the production implication?

5. **Sector preferences vs Bear BULL_PROXY.** Bear BULL_PROXY had
   defensives top (Pharma 67%, Energy 64%). Bull BULL_PROXY's top
   sectors? Same pattern or different?

6. **Production verdict.** Bull BULL_PROXY baseline 51.1% (above 50%).
   Best sub-regime recovery_bull 57.4% on n=70 (small). Healthy_bull
   53.4% on n=333 (broader). What's the right production filter, and
   when should it activate?

Format: markdown, ## sections per question, 3-4 paragraphs each.
Be specific, reference deltas and sample sizes."""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    LLM_PATH.write_text(
        f"# Bull BULL_PROXY Differentiator Analysis — Sonnet 4.5\n\n"
        f"**Date:** 2026-05-03\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"Saved: {LLM_PATH}")


if __name__ == "__main__":
    main()
