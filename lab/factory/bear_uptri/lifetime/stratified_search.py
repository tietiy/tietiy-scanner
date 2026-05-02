"""
Bear UP_TRI cell — S1: sector × sub-regime × calendar stratification.

Beyond L1's flat segmentation and L2's combinatorial search, S1 asks:
do the L1+L2 patterns concentrate in particular sectors, calendar
buckets, or sub-regime states?

Three stratification axes per signal_type:
  A. Sector × hot/cold sub-regime cross-tab (n≥200 per cell)
  B. Calendar buckets (DoW / week-of-month / month) × hot/cold
  C. Within-hot feature characterization (winners-vs-losers in hot only)
  D. Cold cascade refinement (mutually-exclusive cascade test)

Sub-regime gating definition (from L1):
  HOT  = nifty_vol_percentile_20d > 0.70 AND nifty_60d_return_pct < -0.10
  COLD = everything else

Saves to: lab/factory/bear_uptri/lifetime/stratified_findings.json
LLM analysis to: lab/factory/bear_uptri/lifetime/stratified_llm_analysis.md
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse this cell's matches_level
_filter_path = _HERE.parent / "filter_test.py"
_spec = _ilu.spec_from_file_location("bear_uptri_filter_s1", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "stratified_findings.json"
OUTPUT_LLM = _HERE / "stratified_llm_analysis.md"

MIN_CELL_N = 200
MIN_CALENDAR_N = 100

# Sub-regime gate (from L1)
HOT_VOL_THRESHOLD = 0.70  # nifty_vol_percentile_20d
HOT_RETURN_THRESHOLD = -0.10  # nifty_60d_return_pct (low if < -0.10)


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _wr_stats(grp: pd.DataFrame) -> dict:
    nw = int((grp["wlf"] == "W").sum())
    nl = int((grp["wlf"] == "L").sum())
    nf = int((grp["wlf"] == "F").sum())
    return {
        "n": len(grp), "n_w": nw, "n_l": nl, "n_f": nf,
        "wr": (nw / (nw + nl)) if (nw + nl) > 0 else None,
    }


def _classify_subregime(row) -> str:
    vp = row.get("feat_nifty_vol_percentile_20d")
    n60 = row.get("feat_nifty_60d_return_pct")
    if pd.isna(vp) or pd.isna(n60):
        return "unknown"
    if vp > HOT_VOL_THRESHOLD and n60 < HOT_RETURN_THRESHOLD:
        return "hot"
    return "cold"


def main():
    print("─" * 80)
    print("S1: Bear UP_TRI stratified search at lifetime scale")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bear") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()
    bu_wl["scan_date"] = pd.to_datetime(bu_wl["scan_date"])
    bu_wl["month"] = bu_wl["scan_date"].dt.month
    bu_wl["year"] = bu_wl["scan_date"].dt.year
    bu_wl["sub"] = bu_wl.apply(_classify_subregime, axis=1)

    overall = _wr_stats(bu_wl)
    baseline_wr = overall["wr"]
    print(f"\nLifetime: n={overall['n']}, baseline_wr={baseline_wr*100:.1f}%")
    sub_dist = bu_wl["sub"].value_counts()
    print(f"Sub-regime distribution: hot={sub_dist.get('hot', 0)} "
          f"({sub_dist.get('hot', 0)/overall['n']*100:.1f}%), "
          f"cold={sub_dist.get('cold', 0)} "
          f"({sub_dist.get('cold', 0)/overall['n']*100:.1f}%), "
          f"unknown={sub_dist.get('unknown', 0)}")
    hot_st = _wr_stats(bu_wl[bu_wl["sub"] == "hot"])
    cold_st = _wr_stats(bu_wl[bu_wl["sub"] == "cold"])
    print(f"Hot WR: {hot_st['wr']*100:.1f}% | Cold WR: {cold_st['wr']*100:.1f}%")

    findings: dict = {
        "lifetime_n": overall["n"],
        "lifetime_baseline_wr": baseline_wr,
        "subregime_distribution": {
            "hot": int(sub_dist.get("hot", 0)),
            "cold": int(sub_dist.get("cold", 0)),
            "unknown": int(sub_dist.get("unknown", 0)),
        },
        "hot_wr": hot_st["wr"],
        "cold_wr": cold_st["wr"],
        "by_sector": {},
        "by_dow": {},
        "by_week_of_month": {},
        "by_month": {},
        "by_year": {},
        "hot_internal_features": {},
        "cold_cascade": {},
    }

    # ── A. Sector × sub-regime ────────────────────────────────────────
    print(f"\n══ A. Sector × sub-regime stratification ══")
    sector_rows = []
    for sec, grp in bu_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        if st["n"] < MIN_CELL_N or st["wr"] is None:
            continue
        # Within hot
        h = _wr_stats(grp[grp["sub"] == "hot"])
        c = _wr_stats(grp[grp["sub"] == "cold"])
        entry = {
            "n": st["n"], "wr": st["wr"],
            "lift_pp": st["wr"] - baseline_wr,
            "hot_n": h["n"], "hot_wr": h["wr"],
            "cold_n": c["n"], "cold_wr": c["wr"],
        }
        findings["by_sector"][str(sec)] = entry
        sector_rows.append((str(sec), st["n"], st["wr"], st["wr"] - baseline_wr,
                            h["n"], h["wr"], c["n"], c["wr"]))
    sector_rows.sort(key=lambda t: -t[3])
    print(f"  {'sector':<12}{'n':>6}{'all_wr':>8}{'lift':>8}"
          f"{'hot_n':>6}{'hot_wr':>8}{'cold_n':>7}{'cold_wr':>9}")
    print("  " + "─" * 90)
    for sec, n_all, wr, lift, h_n, h_wr, c_n, c_wr in sector_rows:
        print(f"  {sec:<12}{n_all:>6}{wr*100:>7.1f}%{lift*100:>+7.1f}pp"
              f"{h_n:>6}"
              f"{(h_wr*100):>7.1f}%" if h_wr is not None else f"{'—':>8}",
              end="")
        print(f"{c_n:>7}"
              f"{(c_wr*100):>8.1f}%" if c_wr is not None else f"{'—':>9}")

    # ── B. Calendar (DoW × week × month × year) ──────────────────────
    print(f"\n══ B. Calendar effects (DoW / week / month / year) ══")
    print(f"\n  Day-of-week:")
    for dow in ("Mon", "Tue", "Wed", "Thu", "Fri"):
        grp = bu_wl[bu_wl["feat_day_of_week"] == dow]
        st = _wr_stats(grp)
        if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
            continue
        h = _wr_stats(grp[grp["sub"] == "hot"])
        c = _wr_stats(grp[grp["sub"] == "cold"])
        findings["by_dow"][dow] = {
            "n": st["n"], "wr": st["wr"],
            "lift_pp": st["wr"] - baseline_wr,
            "hot_wr": h["wr"], "cold_wr": c["wr"],
        }
        print(f"    {dow:<5}: n={st['n']:>4} WR={st['wr']*100:.1f}% "
              f"lift={(st['wr']-baseline_wr)*100:+.1f}pp "
              f"(hot {h['n']}@{(h['wr'] or 0)*100:.0f}% / "
              f"cold {c['n']}@{(c['wr'] or 0)*100:.0f}%)")

    print(f"\n  Week-of-month:")
    for wk in ("wk1", "wk2", "wk3", "wk4"):
        grp = bu_wl[bu_wl["feat_day_of_month_bucket"] == wk]
        st = _wr_stats(grp)
        if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
            continue
        h = _wr_stats(grp[grp["sub"] == "hot"])
        c = _wr_stats(grp[grp["sub"] == "cold"])
        findings["by_week_of_month"][wk] = {
            "n": st["n"], "wr": st["wr"],
            "lift_pp": st["wr"] - baseline_wr,
            "hot_wr": h["wr"], "cold_wr": c["wr"],
        }
        print(f"    {wk:<5}: n={st['n']:>4} WR={st['wr']*100:.1f}% "
              f"lift={(st['wr']-baseline_wr)*100:+.1f}pp "
              f"(hot {h['n']}@{(h['wr'] or 0)*100:.0f}% / "
              f"cold {c['n']}@{(c['wr'] or 0)*100:.0f}%)")

    print(f"\n  Month-of-year (top 5 best/worst by lift):")
    month_rows = []
    for m in range(1, 13):
        grp = bu_wl[bu_wl["month"] == m]
        st = _wr_stats(grp)
        if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
            continue
        findings["by_month"][m] = {
            "n": st["n"], "wr": st["wr"],
            "lift_pp": st["wr"] - baseline_wr,
        }
        month_rows.append((m, st["n"], st["wr"], st["wr"] - baseline_wr))
    month_rows.sort(key=lambda t: -t[3])
    mon_lbl = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m, n, wr, lift in month_rows[:5] + month_rows[-3:]:
        print(f"    {mon_lbl[m-1]:<5}: n={n:>5} WR={wr*100:.1f}% "
              f"lift={lift*100:+.1f}pp")

    print(f"\n  Year (since 2010 — structural breaks?):")
    year_rows = []
    for yr in sorted(bu_wl["year"].unique()):
        grp = bu_wl[bu_wl["year"] == yr]
        st = _wr_stats(grp)
        if st["wr"] is None:
            continue
        findings["by_year"][int(yr)] = {
            "n": st["n"], "wr": st["wr"],
            "lift_pp": st["wr"] - baseline_wr,
        }
        year_rows.append((yr, st["n"], st["wr"], st["wr"] - baseline_wr))
    for yr, n, wr, lift in year_rows:
        print(f"    {yr:<5}: n={n:>5} WR={wr*100:.1f}% "
              f"lift={lift*100:+.1f}pp")

    # ── C. Within-hot feature characterization ───────────────────────
    print(f"\n══ C. Within-HOT feature characterization "
          f"(what distinguishes winners vs losers in hot sub-regime?) ══")
    hot_data = bu_wl[bu_wl["sub"] == "hot"].copy()
    print(f"  hot universe: n={len(hot_data)}, "
          f"WR={(_wr_stats(hot_data)['wr'] or 0)*100:.1f}%")
    candidate_features = [
        ("ema_alignment", "categorical"),
        ("market_breadth_pct", "numeric"),
        ("ROC_10", "numeric"),
        ("inside_bar_flag", "bool"),
        ("swing_high_count_20d", "numeric"),
        ("consolidation_quality", "categorical"),
        ("range_compression_60d", "numeric"),
        ("ema50_slope_20d_pct", "numeric"),
        ("multi_tf_alignment_score", "numeric"),
        ("RSI_14", "numeric"),
    ]

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    hot_features_table = []
    for fid, _ in candidate_features:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in hot_data.columns:
            continue
        for lvl in ["low", "medium", "high"] if spec.value_type == "numeric" \
                else (["True", "False"] if spec.value_type == "bool"
                      else hot_data[col].dropna().astype(str)
                      .value_counts().head(3).index.tolist()):
            mask = hot_data[col].apply(
                lambda v: matches_level(spec, v, lvl, bounds_cache)
            ).fillna(False)
            present = hot_data[mask]
            absent = hot_data[~mask]
            p_st = _wr_stats(present)
            a_st = _wr_stats(absent)
            if p_st["n_w"] + p_st["n_l"] < 50 or a_st["n_w"] + a_st["n_l"] < 50:
                continue
            if p_st["wr"] is None or a_st["wr"] is None:
                continue
            delta = (p_st["wr"] - a_st["wr"]) * 100
            hot_features_table.append({
                "feature_id": fid, "level": lvl,
                "presence_n": p_st["n_w"] + p_st["n_l"],
                "presence_wr": p_st["wr"],
                "absence_wr": a_st["wr"],
                "delta_pp": delta,
            })

    hot_features_table.sort(key=lambda r: -r["delta_pp"])
    print(f"  {'feature':<32}{'level':<10}{'pres_wr':>10}"
          f"{'abs_wr':>10}{'delta':>10}")
    print("  " + "─" * 72)
    for r in hot_features_table[:10]:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    print(f"\n  Bottom 3 (within-hot anti-features):")
    for r in hot_features_table[-3:]:
        print(f"  {r['feature_id']:<32}{r['level']:<10}"
              f"{r['presence_wr']*100:>9.1f}%{r['absence_wr']*100:>9.1f}%"
              f"{r['delta_pp']:>+9.1f}pp")
    findings["hot_internal_features"] = {
        "top_10_winners": hot_features_table[:10],
        "bottom_3_anti": hot_features_table[-3:],
    }

    # ── D. Cold cascade refinement (mutually-exclusive cascade test) ─
    print(f"\n══ D. Cold sub-regime cascade refinement ══")
    cold_data = bu_wl[bu_wl["sub"] == "cold"].copy()
    cold_baseline = _wr_stats(cold_data)["wr"]
    print(f"  cold universe: n={len(cold_data)}, "
          f"WR={cold_baseline*100:.1f}%")

    # Apply cascade in priority order, mutually exclusive
    wk4_spec = None  # categorical
    wk4_mask = cold_data["feat_day_of_month_bucket"] == "wk4"
    swing_low_spec = spec_by_id["swing_high_count_20d"]
    swing_low_mask = cold_data["feat_swing_high_count_20d"].apply(
        lambda v: matches_level(swing_low_spec, v, "low", bounds_cache)
    ).fillna(False)
    breadth_spec = spec_by_id["market_breadth_pct"]
    breadth_low_mask = cold_data["feat_market_breadth_pct"].apply(
        lambda v: matches_level(breadth_spec, v, "low", bounds_cache)
    ).fillna(False)
    ema50_spec = spec_by_id["ema50_slope_20d_pct"]
    ema50_low_mask = cold_data["feat_ema50_slope_20d_pct"].apply(
        lambda v: matches_level(ema50_spec, v, "low", bounds_cache)
    ).fillna(False)

    # Cascade tier 1: wk4 AND swing_high=low
    tier1_mask = wk4_mask & swing_low_mask
    tier1 = cold_data[tier1_mask]
    # Tier 2: NOT tier1 AND (breadth=low AND ema50=low AND swing=low)
    tier2_mask = ~tier1_mask & (breadth_low_mask & ema50_low_mask
                                  & swing_low_mask)
    tier2 = cold_data[tier2_mask]
    # Tier 3: NOT tier1/2 AND wk4 alone
    tier3_mask = ~tier1_mask & ~tier2_mask & wk4_mask
    tier3 = cold_data[tier3_mask]
    # SKIP: rest
    skip_mask = ~tier1_mask & ~tier2_mask & ~tier3_mask
    skipped = cold_data[skip_mask]

    cascade_rows = [
        ("Tier 1: wk4 × swing_high=low (TAKE_FULL)", tier1),
        ("Tier 2: breadth=low × ema50=low × swing=low (TAKE_SMALL)", tier2),
        ("Tier 3: wk4 alone (WATCH/TAKE_SMALL)", tier3),
        ("SKIP (no match)", skipped),
    ]
    cascade_results = []
    print(f"  {'tier':<55}{'n':>6}{'wr':>8}{'lift_cold':>11}")
    print("  " + "─" * 80)
    for name, grp in cascade_rows:
        st = _wr_stats(grp)
        wr_str = f"{st['wr']*100:.1f}%" if st["wr"] is not None else "—"
        lift_str = (f"{(st['wr']-cold_baseline)*100:+.1f}pp"
                    if st["wr"] else "—")
        print(f"  {name:<55}{st['n']:>6}{wr_str:>8}{lift_str:>11}")
        cascade_results.append({
            "tier": name, "n": st["n"], "wr": st["wr"],
            "lift_vs_cold_pp": ((st["wr"] - cold_baseline) * 100
                                  if st["wr"] is not None else None),
        })

    findings["cold_cascade"] = {
        "cold_baseline_wr": cold_baseline,
        "tiers": cascade_results,
    }

    # ── Save + summary ──────────────────────────────────────────────
    OUTPUT_PATH.write_text(json.dumps(findings, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM analysis ─────────────────────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for stratified mechanism analysis...")
    print("─" * 80)
    sector_summary = "\n".join(
        f"  • {sec}: all={p['wr']*100:.1f}% (n={p['n']}), "
        f"hot={(p['hot_wr'] or 0)*100:.1f}% (n={p['hot_n']}), "
        f"cold={(p['cold_wr'] or 0)*100:.1f}% (n={p['cold_n']})"
        for sec, p in sorted(findings["by_sector"].items(),
                                  key=lambda x: -x[1]["wr"])[:8]
    )
    cal_summary = (
        f"  Best DoW: " + ", ".join(
            f"{d}:{p['wr']*100:.0f}%"
            for d, p in sorted(findings["by_dow"].items(),
                                    key=lambda x: -x[1]["wr"])[:3]
        ) + "\n  Best week: " + ", ".join(
            f"{w}:{p['wr']*100:.0f}%"
            for w, p in sorted(findings["by_week_of_month"].items(),
                                    key=lambda x: -x[1]["wr"])
        )
    )
    hot_top_lines = "\n".join(
        f"  • {r['feature_id']}={r['level']}: "
        f"+{r['delta_pp']:.1f}pp within-hot delta"
        for r in hot_features_table[:5]
    )
    cascade_lines = "\n".join(
        f"  • {r['tier']}: n={r['n']}, "
        f"WR={(r['wr'] or 0)*100:.1f}%, "
        f"lift_vs_cold={r['lift_vs_cold_pp'] or 0:+.1f}pp"
        for r in cascade_results
    )

    prompt = f"""You are interpreting stratified analysis for the Bear
UP_TRI cell. Lifetime universe: 15,151 signals, baseline 55.7% WR.
Sub-regime split: hot 15% (68.3% WR) / cold 85% (53.4% WR).

## Sector × sub-regime (top 8)

{sector_summary}

## Calendar effects

{cal_summary}

## Within-HOT feature characterization (winners vs losers in hot sub-regime)

{hot_top_lines}

## Cold cascade results (mutually exclusive)

{cascade_lines}

## Your task

1. **Mechanism — what does "Bear UP_TRI" actually capture?**
   Reference established concepts (flight to quality, sector rotation,
   institutional capitulation buying, oversold mean reversion, regime
   transition catching). Be specific about which sectors + when.

2. **Sector concentration — does Bear UP_TRI work in specific sectors
   or universally?** What does the sector ranking tell us?

3. **Calendar effects — are wk4 and other calendar effects mechanistic
   or noise?** How would a trader use this in real-time?

4. **Within-hot characterization — do features that distinguish
   winners-from-losers WITHIN HOT add signal?** Or is the hot sub-
   regime itself sufficient?

5. **Cascade design — does the 4-tier cascade for cold sub-regime
   produce meaningful separation?** Are there cleaner alternatives?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific and concrete."""

    from llm_client import LLMClient
    client = LLMClient()
    md = client.synthesize_findings(prompt, max_tokens=2800)
    OUTPUT_LLM.write_text(
        f"# Bear UP_TRI Stratified Mechanism Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{md}\n"
    )
    print(f"Saved: {OUTPUT_LLM}")


if __name__ == "__main__":
    main()
