"""
Bear BULL_PROXY cell — P2: feature differentiator analysis with thin-data
caveat (lifetime-only fallback methodology).

Standard winners-vs-rejected analysis NOT FEASIBLE (0 Phase 5 combos at
all). Falling back to 4 alternative approaches (parallel to Bear DOWN_TRI):

  A. LIFETIME differentiator analysis — features in lifetime winners (W)
     vs losers (L) within n=891 Bear BULL_PROXY signals.
  B. Sub-regime stratification within lifetime — sector × hot/cold WR.
  C. Cross-cell comparison with Bear UP_TRI — same features, opposite
     directions?
  D. BULL_PROXY-specific feature check — support proximity, prior_lows,
     accumulation patterns (mechanism-specific to bull-rejection setup).

After analysis, send to Sonnet 4.5 for cross-cell mechanism interpretation.
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
_spec = _ilu.spec_from_file_location("bear_uptri_filter_p2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

# Reuse Bear sub-regime detector
_detector_path = (_LAB_ROOT / "factory" / "bear" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bear_subregime_p2", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bear_subregime_p2"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bear_subregime = _detector_mod.detect_bear_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
LIVE_FEATURES_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "differentiators.json"
LLM_OUTPUT_PATH = _HERE / "differentiators_llm_interpretation.md"

FEATURE_PANEL = [
    ("nifty_60d_return_pct", "numeric"),
    ("nifty_vol_regime", "categorical"),
    ("nifty_vol_percentile_20d", "numeric"),
    ("market_breadth_pct", "numeric"),
    ("day_of_week", "categorical"),
    ("day_of_month_bucket", "categorical"),
    ("ema_alignment", "categorical"),
    ("ema50_slope_20d_pct", "numeric"),
    ("MACD_signal", "categorical"),
    ("MACD_histogram_slope", "categorical"),
    ("higher_highs_intact_flag", "bool"),
    ("RSI_14", "numeric"),
    ("ROC_10", "numeric"),
    ("swing_high_count_20d", "numeric"),
    ("swing_low_count_20d", "numeric"),
    ("inside_bar_flag", "bool"),
    ("range_compression_60d", "numeric"),
    ("consolidation_quality", "categorical"),
    ("multi_tf_alignment_score", "numeric"),
    ("52w_high_distance_pct", "numeric"),
    ("52w_low_distance_pct", "numeric"),
    ("compression_duration", "numeric"),
    # BULL_PROXY-specific features (support / accumulation)
    ("vol_dryup_flag", "bool"),
    ("vol_climax_flag", "bool"),
]


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def lifetime_feature_differential(
    df: pd.DataFrame,
    feature_panel: list[tuple[str, str]],
    spec_by_id: dict,
    bounds_cache: dict,
    min_n: int = 30,
) -> list[dict]:
    """For each (feature, level), compute presence_wr vs absence_wr.

    Lower min_n=30 due to thinner lifetime cohort (n=891 vs Bear UP_TRI 15k).
    """
    results = []
    n_total = len(df)

    for fid, vtype in feature_panel:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue

        levels = []
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


def llm_mechanism_interpretation(
    top_winners: list[dict], top_anti: list[dict],
    sector_lt: dict, hot_wr: float, cold_wr: float,
    live_winners: list[dict], live_losers: list[dict],
    live_wr: float, lifetime_wr: float,
) -> str:
    from llm_client import LLMClient

    win_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}  "
        f"presence_wr={r['presence_wr']*100:.1f}% / "
        f"absence_wr={r['absence_wr']*100:.1f}%  "
        f"Δ={r['delta_pp']:+.1f}pp (n={r['presence_n_wl']})"
        for r in top_winners[:8]
    )
    anti_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}  "
        f"presence_wr={r['presence_wr']*100:.1f}% / "
        f"absence_wr={r['absence_wr']*100:.1f}%  "
        f"Δ={r['delta_pp']:+.1f}pp (n={r['presence_n_wl']})"
        for r in top_anti[:8]
    )
    sec_lines = "\n".join(
        f"  • {sec}: n={info['n']}, WR={info['wr']*100:.1f}%"
        for sec, info in sorted(sector_lt.items(),
                                       key=lambda x: -(x[1].get("wr") or 0))
    )

    win_signal_lines = "\n".join(
        f"  • {s['symbol']} ({s['sector']}, {s['date']}): {s['outcome']}"
        for s in live_winners[:8]
    )
    los_signal_lines = "\n".join(
        f"  • {s['symbol']} ({s['sector']}, {s['date']}): {s['outcome']}"
        for s in live_losers
    )

    prompt = f"""You are interpreting feature differentiator analysis
for the Bear BULL_PROXY cell — a support-rejection / contrarian-long
signal in Bear regime.

## Cell context (very thin)

• Phase 5: ZERO combinations — even thinner than Bear DOWN_TRI's 19 WATCH.
  Standard differentiator analysis NOT FEASIBLE; this is lifetime-only
  fallback.
• Live: n=13, 11W/2L = **{live_wr*100:.1f}% WR**
• Lifetime: n=891, **{lifetime_wr*100:.1f}% WR**
• Gap: {(live_wr - lifetime_wr)*100:+.1f}pp — parallel to Bear UP_TRI's
  +38.9pp inflation (likely Phase-5-equivalent selection bias + sub-
  regime structure).

## Sub-regime breakdown (Bear detector applied to lifetime n=891)

  hot  (vol > 0.70 AND 60d < -0.10):  n=86 (9.7%)  WR={hot_wr*100:.1f}%
  cold (everything else):               n=805 (90.3%) WR={cold_wr*100:.1f}%
  Δ hot − cold: +{(hot_wr-cold_wr)*100:.1f}pp

Live (n=13):
  hot:  n=7  WR=85.7% (6W/1L)
  cold: n=6  WR=83.3% (5W/1L)
  → live hot/cold equal (vs lifetime +18pp delta) — borderline cold
    behaves like hot. Same as Bear UP_TRI's S2 finding.

## Lifetime feature differential (n=891)

### Top 8 winner features

{win_lines}

### Top 8 anti-features

{anti_lines}

## Lifetime sector ranking

{sec_lines}

## Live 11 winners (sample)

{win_signal_lines}

## Live 2 losers

{los_signal_lines}

## Cross-cell comparisons

### Bear UP_TRI key findings (for reference)
- Lifetime baseline 55.7%; hot sub-regime 68.3% / cold 53.4%
- Top winner: swing_high_count_20d=low (+23.3pp lifetime delta)
- Top winner #2: nifty_60d_return_pct=low (+14.1pp)
- wk4 lifetime WINNER (+10.5pp); wk2 anti
- Sectors: CapGoods/Auto/Other top (defensive)

### Bear DOWN_TRI key findings (for reference)
- Lifetime baseline 46.1%; mediocre, 0 Phase 5 winners
- wk2 +15pp WINNER, wk4 -17.5pp ANTI (INVERTED vs Bear UP_TRI!)
- nifty_60d=low ANTI (+ for UP_TRI; - for DOWN_TRI)
- Sectors: defensives top, cyclicals bottom

### Now — Bear BULL_PROXY shows what?

## Your task

1. **Mechanism — what does Bear BULL_PROXY actually capture?**
   Bull_proxy fires on potential support rejection (test of low,
   reversal candle). In Bear regime, this is a contrarian-long bet.
   Reference established concepts (institutional bottom-fishing,
   short-cover squeeze, support-bounce mean reversion).

2. **Cross-cell comparison vs Bear UP_TRI.** Both are bullish setups
   in Bear regime. Are the lifetime feature signatures similar
   (same mechanism) or different (different mechanism)?

3. **Cross-cell comparison vs Bear DOWN_TRI.** Inverted direction.
   Should Bear BULL_PROXY's wk2/wk4 calendar pattern align with Bear
   UP_TRI (wk4 winner) or Bear DOWN_TRI (wk2 winner)?

4. **Sub-regime structure.** Is Bear BULL_PROXY tri-modal like Bear
   UP_TRI (hot/warm/cold) or simpler? Lifetime hot 9.7% vs Bear UP_TRI
   hot 15% — smaller hot zone. Why?

5. **DEFERRED vs FILTER vs BROAD-BAND vs KILL?**
   With 0 Phase 5 combos, live 11W/2L looks great but unfiltered
   raw signal. Lifetime 47.3% baseline + 16.4pp hot lift. What's
   your honest production verdict?

Format: markdown, ## sections. 3-4 short paragraphs each. Be ruthless
about thin data; explicit about cross-cell parallels."""

    client = LLMClient()
    return client.synthesize_findings(prompt, max_tokens=3000)


def main():
    print("─" * 80)
    print("CELL: Bear BULL_PROXY — P2 differentiator analysis (lifetime-only)")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bp = df[(df["regime"] == "Bear") & (df["signal"] == "BULL_PROXY")].copy()
    bp["wlf"] = bp["outcome"].apply(_wlf)
    bp_wl = bp[bp["wlf"].isin(["W", "L", "F"])].copy()

    nw = (bp_wl["wlf"] == "W").sum()
    nl = (bp_wl["wlf"] == "L").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLifetime n={len(bp_wl)}, baseline_wr={baseline_wr*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # ── A. Lifetime feature differential ────────────────────────────
    print(f"\n══ A. Lifetime feature differential (n={len(bp_wl)}) ══")
    diff = lifetime_feature_differential(
        bp_wl, FEATURE_PANEL, spec_by_id, bounds_cache, min_n=30)

    print(f"\n  Top 12 winner features (positive delta):")
    print(f"  {'feature':<32}{'level':<10}{'pres_wr':>10}"
          f"{'abs_wr':>10}{'delta':>10}")
    print("  " + "─" * 72)
    top_winners = sorted(diff, key=lambda r: -r["delta_pp"])[:12]
    for r in top_winners:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")

    print(f"\n  Top 10 anti-features (negative delta):")
    top_anti = sorted(diff, key=lambda r: r["delta_pp"])[:10]
    for r in top_anti:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")

    # ── B. Sub-regime stratification (lifetime) ─────────────────────
    print(f"\n══ B. Sub-regime stratification (lifetime) ══")
    bp_wl["sub"] = bp_wl.apply(
        lambda r: detect_bear_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_nifty_60d_return_pct"),
        ).subregime,
        axis=1,
    )
    sub_wr = {}
    for s in ["hot", "cold"]:
        grp = bp_wl[bp_wl["sub"] == s]
        gw = (grp["wlf"] == "W").sum()
        gl = (grp["wlf"] == "L").sum()
        wr = gw / (gw + gl) if (gw + gl) > 0 else 0
        sub_wr[s] = {"n": int(len(grp)), "wr": float(wr)}
        print(f"  {s}: n={len(grp)}, WR={wr*100:.1f}%")

    # Sector × sub-regime
    print(f"\n  Sector × hot/cold (n≥10 per cell):")
    print(f"  {'sector':<10}{'hot_n':>6}{'hot_wr':>8}{'cold_n':>7}{'cold_wr':>9}")
    sector_subreg = {}
    for sec, grp in bp_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        h = grp[grp["sub"] == "hot"]
        c = grp[grp["sub"] == "cold"]
        h_w = (h["wlf"] == "W").sum(); h_l = (h["wlf"] == "L").sum()
        c_w = (c["wlf"] == "W").sum(); c_l = (c["wlf"] == "L").sum()
        h_wr = h_w / (h_w + h_l) if (h_w + h_l) >= 10 else None
        c_wr = c_w / (c_w + c_l) if (c_w + c_l) >= 30 else None
        if h_wr is None and c_wr is None:
            continue
        sector_subreg[str(sec)] = {
            "hot_n": int(len(h)), "hot_wr": h_wr,
            "cold_n": int(len(c)), "cold_wr": c_wr,
        }
        h_str = f"{h_wr*100:.0f}%" if h_wr is not None else "—"
        c_str = f"{c_wr*100:.0f}%" if c_wr is not None else "—"
        print(f"  {sec:<10}{len(h):>6}{h_str:>8}{len(c):>7}{c_str:>9}")

    # ── C. Cross-cell comparison vs Bear UP_TRI key features ────────
    print(f"\n══ C. Cross-cell comparison vs Bear UP_TRI ══")
    print(f"\n  Same-feature comparison (Bear BULL_PROXY vs Bear UP_TRI lifetime delta):")
    cross_cell = {}
    for fid, lvl in [
        ("nifty_60d_return_pct", "low"),
        ("day_of_month_bucket", "wk2"),
        ("day_of_month_bucket", "wk4"),
        ("swing_high_count_20d", "low"),
        ("higher_highs_intact_flag", "True"),
        ("nifty_vol_regime", "High"),
    ]:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in bp_wl.columns:
            continue
        mask = bp_wl[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache)
        ).fillna(False)
        p = bp_wl[mask]
        a = bp_wl[~mask]
        n_p = (p["wlf"] == "W").sum() + (p["wlf"] == "L").sum()
        n_a = (a["wlf"] == "W").sum() + (a["wlf"] == "L").sum()
        if n_p < 20:
            continue
        wr_p = (p["wlf"] == "W").sum() / n_p if n_p > 0 else None
        wr_a = (a["wlf"] == "W").sum() / n_a if n_a > 0 else None
        delta = (wr_p - wr_a) * 100 if wr_p and wr_a else None
        cross_cell[f"{fid}={lvl}"] = {
            "presence_n": int(n_p),
            "presence_wr": float(wr_p) if wr_p else None,
            "absence_wr": float(wr_a) if wr_a else None,
            "delta_pp": float(delta) if delta is not None else None,
        }
        delta_str = f"{delta:+.1f}pp" if delta is not None else "—"
        print(f"  {fid}={lvl:<6} delta={delta_str} (n={n_p})")

    # ── D. Live winners feature inspection ──────────────────────────
    print(f"\n══ D. Live signals feature inspection (n=13) ══")
    live = pd.read_parquet(LIVE_FEATURES_PATH)
    live_bp = live[(live["regime"] == "Bear") & (live["signal"] == "BULL_PROXY")].copy()
    live_bp["wlf"] = live_bp["outcome"].apply(_wlf)

    feat_cols = ["feat_ema_alignment", "feat_MACD_signal",
                  "feat_higher_highs_intact_flag",
                  "feat_market_breadth_pct", "feat_RSI_14"]
    live_winners = [
        {**{c: r[c] for c in feat_cols if c in r.index},
         "symbol": r["symbol"], "sector": r["sector"],
         "date": str(r["date"]), "outcome": r["outcome"]}
        for _, r in live_bp[live_bp["wlf"] == "W"].iterrows()
    ]
    live_losers = [
        {**{c: r[c] for c in feat_cols if c in r.index},
         "symbol": r["symbol"], "sector": r["sector"],
         "date": str(r["date"]), "outcome": r["outcome"]}
        for _, r in live_bp[live_bp["wlf"] == "L"].iterrows()
    ]

    print(f"  Winners (n={len(live_winners)}):")
    for w in live_winners:
        print(f"    {w['symbol']:<18} {w['sector']:<8} {w['date'][:10]} "
              f"ema={w.get('feat_ema_alignment')}, "
              f"MACD={w.get('feat_MACD_signal')}")

    print(f"\n  Losers (n={len(live_losers)}):")
    for l in live_losers:
        print(f"    {l['symbol']:<18} {l['sector']:<8} {l['date'][:10]} "
              f"ema={l.get('feat_ema_alignment')}, "
              f"MACD={l.get('feat_MACD_signal')}")

    # Sector lifetime breakdown
    sector_lt = {}
    for sec, grp in bp_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        nw_s = (grp["wlf"] == "W").sum()
        nl_s = (grp["wlf"] == "L").sum()
        if nw_s + nl_s < 30:
            continue
        sector_lt[str(sec)] = {
            "n": int(len(grp)),
            "wr": float(nw_s / (nw_s + nl_s)),
        }

    out = {
        "lifetime_universe": {
            "n_total": int(len(bp_wl)),
            "baseline_wr": float(baseline_wr),
        },
        "top_winner_features_lifetime": top_winners,
        "top_anti_features_lifetime": top_anti,
        "subregime_wr": sub_wr,
        "sector_subregime": sector_subreg,
        "cross_cell_features": cross_cell,
        "sector_lifetime": sector_lt,
        "live_winners_features": live_winners,
        "live_losers_features": live_losers,
    }

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM analysis ────────────────────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for cross-cell mechanism interpretation...")
    print("─" * 80)
    md = llm_mechanism_interpretation(
        top_winners, top_anti, sector_lt,
        sub_wr["hot"]["wr"], sub_wr["cold"]["wr"],
        live_winners, live_losers,
        live_wr=11/13, lifetime_wr=baseline_wr)
    LLM_OUTPUT_PATH.write_text(
        f"# Bear BULL_PROXY Differentiator Mechanism Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{md}\n"
    )
    print(f"Saved: {LLM_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
