"""
Bear DOWN_TRI cell — D2: feature differentiator analysis with
thin-data caveat.

Standard winners-vs-rejected analysis is NOT FEASIBLE for this cell
(0 V / 0 P / 0 R in Phase 5). This module uses 4 alternative approaches:

  A. LIFETIME differentiator analysis — compare features in lifetime
     winners (W) vs losers (L) within n=3,640 Bear DOWN_TRI signals.
     Larger sample, more reliable than Phase 5 patterns.

  B. Bank vs non-Bank lifetime comparison — characterize the kill_001
     cohort and propose kill rule extensions.

  C. Live 2-winners feature inspection — IPCALAB and VINATIORGA — what
     do they share that the 9 losers don't?

  D. Direction-specific feature check — DOWN_TRI is contrarian short
     in Bear; bull-aligned features (ema_bull, MACD_bull) should
     anti-correlate with wins.

After tabulation, send to Sonnet 4.5 for mechanism interpretation:
"Bear DOWN_TRI live 18.2% vs lifetime 46.1% — INVERTED gap. Why
might Bear DOWN_TRI fail in current Bear sub-regime when lifetime
supports it? What features should anchor a viable filter?"
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse matches_level from bear_uptri
_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_d2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
LIVE_FEATURES_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "differentiators.json"
LLM_OUTPUT_PATH = _HERE / "differentiators_llm_interpretation.md"

# Direction-relevant features for DOWN_TRI (contrarian short in Bear)
DIRECTION_FEATURES = [
    ("ema_alignment", "categorical"),
    ("MACD_signal", "categorical"),
    ("MACD_histogram_sign", "categorical"),
    ("MACD_histogram_slope", "categorical"),
    ("higher_highs_intact_flag", "bool"),
    ("RSI_14", "numeric"),
    ("ROC_10", "numeric"),
    ("ema50_slope_20d_pct", "numeric"),
]
# General feature panel
FEATURE_PANEL = [
    ("nifty_60d_return_pct", "numeric"),
    ("nifty_vol_regime", "categorical"),
    ("nifty_vol_percentile_20d", "numeric"),
    ("market_breadth_pct", "numeric"),
    ("day_of_week", "categorical"),
    ("day_of_month_bucket", "categorical"),
    ("swing_high_count_20d", "numeric"),
    ("swing_low_count_20d", "numeric"),
    ("inside_bar_flag", "bool"),
    ("range_compression_60d", "numeric"),
    ("consolidation_quality", "categorical"),
    ("multi_tf_alignment_score", "numeric"),
    ("52w_high_distance_pct", "numeric"),
    ("52w_low_distance_pct", "numeric"),
    ("compression_duration", "numeric"),
] + DIRECTION_FEATURES


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
    min_n: int = 100,
) -> list[dict]:
    """For each (feature, level), compute presence_wr vs absence_wr
    in lifetime data.

    feature_panel: list of (feature_id, value_type) tuples.
    Returns: list of dicts ranked by abs(delta_pp).
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
        else:  # numeric
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
            wr_p = ((present["wlf"] == "W").sum() / n_p_wl
                    if n_p_wl > 0 else None)
            wr_a = ((absent["wlf"] == "W").sum() / n_a_wl
                    if n_a_wl > 0 else None)
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


def llm_mechanism_interpretation(top_winners: list[dict],
                                       top_anti: list[dict],
                                       sector_lifetime: dict,
                                       live_winners_features: list[dict],
                                       live_losers_features: list[dict],
                                       live_wr: float,
                                       lifetime_wr: float) -> str:
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
        for sec, info in sorted(sector_lifetime.items(),
                                       key=lambda x: -(x[1].get("wr") or 0))
    )

    win_signal_lines = "\n".join(
        f"  • {s['symbol']} ({s['sector']}, {s['date']}): "
        f"ema={s.get('feat_ema_alignment')}, "
        f"MACD={s.get('feat_MACD_signal')}, "
        f"vol_regime={s.get('feat_nifty_vol_regime')}"
        for s in live_winners_features
    )
    los_signal_lines = "\n".join(
        f"  • {s['symbol']} ({s['sector']}): "
        f"ema={s.get('feat_ema_alignment')}, "
        f"MACD={s.get('feat_MACD_signal')}"
        for s in live_losers_features[:6]
    )

    prompt = f"""You are interpreting feature differentiator analysis
for the Bear DOWN_TRI cell — a contrarian short signal in Bear regime.

## Cell context (challenging)

• Phase 5: 0 VALIDATED / 0 PRELIMINARY / 0 REJECTED — all 19 combos
  are WATCH (no Phase-5 winners observed). Standard differentiator
  analysis NOT FEASIBLE.
• Live data: n=11, 2W/9L = **{live_wr*100:.1f}% WR**
• Lifetime: n=3,640, **{lifetime_wr*100:.1f}% WR**
• Gap: {(live_wr - lifetime_wr)*100:+.1f}pp — INVERTED vs Bear UP_TRI
  (live is WORSE than lifetime — opposite direction of UP_TRI cell)
• kill_001 already deployed: Bank sector excluded; in live, all 6
  Bank signals lost (0/6 = 0% WR confirms kill_001 still correct)

## Lifetime feature differential (winners vs losers, n=3,640)

### Top 8 winner features (positive delta = present in winners)

{win_lines}

### Top 8 anti-features (negative delta = present in losers)

{anti_lines}

## Lifetime sector ranking (Bear DOWN_TRI baseline 46.1%)

{sec_lines}

## Live 2 winners (the only Bear DOWN_TRI live wins)

{win_signal_lines}

## Live 9 losers (top 6)

{los_signal_lines}

## Your task

1. **Why does Bear DOWN_TRI INVERT?** Live 18.2% vs lifetime 46.1%.
   Choppy F1 and Bear UP_TRI showed live > lifetime (Phase-5 selection
   bias inflating live). Bear DOWN_TRI live < lifetime — what
   mechanism flips this?

2. **Mechanism for the cell at lifetime**. Bear DOWN_TRI = descending
   triangle short setup in Bear market. Lifetime says it works at
   46% (mediocre). What trading mechanism does this capture? When
   does shorting a Bear-market descending triangle make sense?

3. **kill_001 (Bank exclusion) — extend to other sectors?** Lifetime
   sector ranking shows Auto/Energy/Metal at 40-41% (worst). Should
   kill_001 extend to these? Or are sector-mismatch rules sufficient?

4. **Filter candidates from lifetime data**. Given the differential
   above, what 1-2 feature combination would you propose as a
   provisional Bear DOWN_TRI filter? Be conservative given thin
   live data.

5. **DEFERRED vs KILL vs FILTER recommendation**. Given:
   - 0 winners in Phase 5 → can't validate live
   - Lifetime supports moderate edge (46%, not strong)
   - Live n=11 too thin
   - kill_001 (Bank) confirmed
   What's your honest verdict for production deployment? Be specific.

Format: markdown, ## sections per question. 3-4 short paragraphs each.
Be specific, ruthless about thin data, honest about uncertainty."""

    client = LLMClient()
    return client.synthesize_findings(prompt, max_tokens=2800)


def main():
    print("─" * 80)
    print("CELL: Bear DOWN_TRI — D2 differentiator analysis (lifetime-based)")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bd = df[(df["regime"] == "Bear") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    bd_wl = bd[bd["wlf"].isin(["W", "L", "F"])].copy()

    nw = (bd_wl["wlf"] == "W").sum()
    nl = (bd_wl["wlf"] == "L").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLifetime n={len(bd_wl)}, baseline_wr={baseline_wr*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # ── A. Lifetime feature differential ────────────────────────────
    print(f"\n══ A. Lifetime feature differential (n={len(bd_wl)}) ══")
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

    print(f"\n  Top 10 anti-features (negative delta):")
    top_anti = sorted(diff, key=lambda r: r["delta_pp"])[:10]
    for r in top_anti:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")

    # ── B. Bank vs non-Bank lifetime ────────────────────────────────
    print(f"\n══ B. Bank vs non-Bank lifetime (kill_001 cohort) ══")
    bank = bd_wl[bd_wl["sector"] == "Bank"]
    non_bank = bd_wl[bd_wl["sector"] != "Bank"]
    bank_wr = ((bank["wlf"] == "W").sum()
                / max(1, ((bank["wlf"] == "W").sum()
                          + (bank["wlf"] == "L").sum())))
    non_bank_wr = ((non_bank["wlf"] == "W").sum()
                    / max(1, ((non_bank["wlf"] == "W").sum()
                              + (non_bank["wlf"] == "L").sum())))
    print(f"  Bank lifetime: n={len(bank)}, WR={bank_wr*100:.1f}%")
    print(f"  non-Bank lifetime: n={len(non_bank)}, WR={non_bank_wr*100:.1f}%")
    print(f"  Δ: {(non_bank_wr - bank_wr)*100:+.1f}pp")

    # ── C. Live winners feature inspection ──────────────────────────
    print(f"\n══ C. Live winners (n=2) feature inspection ══")
    live = pd.read_parquet(LIVE_FEATURES_PATH)
    live_bd = live[(live["regime"] == "Bear") & (live["signal"] == "DOWN_TRI")].copy()
    live_bd["wlf"] = live_bd["outcome"].apply(_wlf)
    live_winners = live_bd[live_bd["wlf"] == "W"]
    live_losers = live_bd[live_bd["wlf"] == "L"]

    feat_cols_to_show = [
        "feat_ema_alignment", "feat_MACD_signal", "feat_MACD_histogram_slope",
        "feat_RSI_14", "feat_higher_highs_intact_flag",
        "feat_market_breadth_pct", "feat_nifty_vol_regime",
        "feat_nifty_60d_return_pct", "feat_day_of_week",
        "feat_day_of_month_bucket"
    ]
    print(f"  Winners (n={len(live_winners)}):")
    for _, w in live_winners.iterrows():
        print(f"    {w['symbol']:<18} ({w['sector']:<8}, {w['date']})")
        for c in feat_cols_to_show:
            if c in w.index:
                print(f"      {c[5:]:<28} = {w[c]}")

    # Convert live winners + losers to LLM-friendly format
    live_winner_features = [
        {**{c: r[c] for c in feat_cols_to_show if c in r.index},
         "symbol": r["symbol"], "sector": r["sector"], "date": str(r["date"])}
        for _, r in live_winners.iterrows()
    ]
    live_loser_features = [
        {**{c: r[c] for c in feat_cols_to_show if c in r.index},
         "symbol": r["symbol"], "sector": r["sector"], "date": str(r["date"])}
        for _, r in live_losers.iterrows()
    ]

    # ── D. Direction-specific anti-features ─────────────────────────
    print(f"\n══ D. Direction-specific feature check ══")
    print(f"  DOWN_TRI is contrarian short — bull-aligned features should")
    print(f"  ANTI-correlate with wins. Check ema_alignment=bull, MACD=bull:")
    for fid, lvl in [("ema_alignment", "bull"), ("MACD_signal", "bull"),
                       ("higher_highs_intact_flag", "True")]:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in bd_wl.columns:
            continue
        mask = bd_wl[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache)
        ).fillna(False)
        p = bd_wl[mask]
        a = bd_wl[~mask]
        n_p = (p["wlf"] == "W").sum() + (p["wlf"] == "L").sum()
        n_a = (a["wlf"] == "W").sum() + (a["wlf"] == "L").sum()
        if n_p > 50:
            wr_p = (p["wlf"] == "W").sum() / n_p
            wr_a = (a["wlf"] == "W").sum() / n_a
            print(f"    {fid}={lvl:<6} present {wr_p*100:.1f}% / "
                  f"absent {wr_a*100:.1f}% (Δ {(wr_p-wr_a)*100:+.1f}pp, "
                  f"n_p={n_p})")

    # ── Sector lifetime breakdown ───────────────────────────────────
    sector_lt = {}
    for sec, grp in bd_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        nw_s = (grp["wlf"] == "W").sum()
        nl_s = (grp["wlf"] == "L").sum()
        if nw_s + nl_s < 50:
            continue
        sector_lt[str(sec)] = {
            "n": int(len(grp)),
            "wr": float(nw_s / (nw_s + nl_s)),
        }

    out = {
        "lifetime_universe": {
            "n_total": int(len(bd_wl)),
            "baseline_wr": float(baseline_wr),
        },
        "top_winner_features_lifetime": top_winners,
        "top_anti_features_lifetime": top_anti,
        "kill_001_validation": {
            "bank_lifetime_n": int(len(bank)),
            "bank_lifetime_wr": float(bank_wr),
            "non_bank_lifetime_n": int(len(non_bank)),
            "non_bank_lifetime_wr": float(non_bank_wr),
            "delta_pp": float((non_bank_wr - bank_wr) * 100),
            "verdict": ("kill_001 partially supported — Bank lifetime is "
                       "modestly worse than non-Bank, but not dramatically. "
                       "Live data shows full kill_001 confirmation: 0/6 Bank wins."),
        },
        "live_winners_features": live_winner_features,
        "live_losers_features": live_loser_features,
        "sector_lifetime": sector_lt,
    }

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM analysis ────────────────────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for mechanism interpretation...")
    print("─" * 80)
    md = llm_mechanism_interpretation(
        top_winners, top_anti, sector_lt,
        live_winner_features, live_loser_features,
        live_wr=2/11, lifetime_wr=baseline_wr)
    LLM_OUTPUT_PATH.write_text(
        f"# Bear DOWN_TRI Differentiator Mechanism Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{md}\n"
    )
    print(f"Saved: {LLM_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
