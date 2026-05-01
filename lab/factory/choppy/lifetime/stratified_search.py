"""
Choppy regime — L4: sector × calendar × volatility stratification.

Beyond L1's flat segmentation and L3's combinatorial search, L4 asks: do the
L3 winning combos hold uniformly across sectors and calendar buckets, or are
they concentrated in particular cells?

Three stratification axes per signal_type:
  A. Sector × signal_type cross-tab (n≥200 per cell)
  B. Calendar buckets: day_of_week, week_of_month, month_of_year
  C. Volatility-conditional WR for the L3 winning patterns:
       UP_TRI:    market_breadth_pct=medium  within each nifty_vol_regime
       DOWN_TRI:  market_breadth_pct=medium  within each nifty_vol_regime
       BULL_PROXY: market_breadth_pct=high   within each nifty_vol_regime

Saves to: lab/factory/choppy/lifetime/stratified_findings.json
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

from feature_loader import FeatureRegistry  # noqa: E402

_filter_path = _LAB_ROOT / "factory" / "choppy_uptri" / "filter_test.py"
_spec = _ilu.spec_from_file_location("uptri_filter_l4", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "stratified_findings.json"

MIN_CELL_N = 200  # minimum n for sector cells to surface
MIN_CALENDAR_N = 100


def _wlf(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
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


def main():
    print("─" * 80)
    print("L4: Choppy lifetime sector × calendar × volatility stratification")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    ch = df[df["regime"] == "Choppy"].copy()
    ch["wlf"] = ch["outcome"].apply(_wlf)
    ch_wl = ch[ch["wlf"].isin(["W", "L", "F"])].copy()
    ch_wl["scan_date"] = pd.to_datetime(ch_wl["scan_date"])
    ch_wl["month"] = ch_wl["scan_date"].dt.month
    ch_wl["year"] = ch_wl["scan_date"].dt.year

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}
    breadth_spec = spec_by_id.get("market_breadth_pct")

    findings: dict = {
        "by_signal_type": {},
        "summary": {},
    }

    for sig_type in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub = ch_wl[ch_wl["signal"] == sig_type]
        baseline = _wr_stats(sub)
        sig_findings: dict = {
            "n_total": baseline["n"],
            "baseline_wr": baseline["wr"],
            "by_sector": {},
            "by_day_of_week": {},
            "by_week_of_month": {},
            "by_month": {},
            "vol_conditional_breadth_medium": {},
            "vol_conditional_breadth_high": {},
        }
        print(f"\n══ {sig_type} × Choppy "
              f"(n={baseline['n']}, baseline={baseline['wr']*100:.1f}%) ══")

        # A. Sector
        print(f"\n── Sector breakdown (n≥{MIN_CELL_N}) ──")
        sector_rows = []
        for sec, grp in sub.groupby("sector"):
            if pd.isna(sec):
                continue
            st = _wr_stats(grp)
            if st["n"] < MIN_CELL_N or st["wr"] is None:
                continue
            lift = st["wr"] - baseline["wr"]
            entry = {**st, "lift_pp": lift}
            sig_findings["by_sector"][str(sec)] = entry
            sector_rows.append((sec, st, lift))
        sector_rows.sort(key=lambda t: -t[2])
        print(f"  {'sector':<12}{'n':>6}{'wr':>8}{'lift':>8}")
        for sec, st, lift in sector_rows:
            print(f"  {sec:<12}{st['n']:>6}{st['wr']*100:>7.1f}%"
                  f"{lift*100:>+7.1f}pp")

        # B. Calendar
        print(f"\n── Day-of-week ──")
        for dow in ("Mon", "Tue", "Wed", "Thu", "Fri"):
            grp = sub[sub["feat_day_of_week"] == dow]
            st = _wr_stats(grp)
            if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
                continue
            lift = st["wr"] - baseline["wr"]
            sig_findings["by_day_of_week"][dow] = {**st, "lift_pp": lift}
            print(f"  {dow:<6}: n={st['n']:>6}, "
                  f"WR={st['wr']*100:.1f}%, lift={lift*100:+.1f}pp")

        print(f"\n── Week-of-month ──")
        for wk in ("wk1", "wk2", "wk3", "wk4"):
            grp = sub[sub["feat_day_of_month_bucket"] == wk]
            st = _wr_stats(grp)
            if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
                continue
            lift = st["wr"] - baseline["wr"]
            sig_findings["by_week_of_month"][wk] = {**st, "lift_pp": lift}
            print(f"  {wk:<6}: n={st['n']:>6}, "
                  f"WR={st['wr']*100:.1f}%, lift={lift*100:+.1f}pp")

        print(f"\n── Month-of-year ──")
        for m in range(1, 13):
            grp = sub[sub["month"] == m]
            st = _wr_stats(grp)
            if st["n"] < MIN_CALENDAR_N or st["wr"] is None:
                continue
            lift = st["wr"] - baseline["wr"]
            sig_findings["by_month"][m] = {**st, "lift_pp": lift}
            mon_lbl = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1]
            print(f"  {mon_lbl:<6}: n={st['n']:>6}, "
                  f"WR={st['wr']*100:.1f}%, lift={lift*100:+.1f}pp")

        # C. Volatility-conditional breadth tests (L3 winning combo)
        breadth_target = "high" if sig_type == "BULL_PROXY" else "medium"
        target_key = (f"vol_conditional_breadth_{breadth_target}")
        print(f"\n── Vol-conditional WR for breadth={breadth_target} "
              f"(L3 winning level) ──")
        for vol in ("Low", "Medium", "High"):
            cohort = sub[sub["feat_nifty_vol_regime"] == vol]
            cohort_st = _wr_stats(cohort)
            if cohort_st["n"] < MIN_CALENDAR_N:
                continue
            mask = cohort["feat_market_breadth_pct"].apply(
                lambda v: matches_level(breadth_spec, v, breadth_target,
                                              bounds_cache))
            matched = cohort[mask.fillna(False)]
            mst = _wr_stats(matched)
            if mst["wr"] is None:
                continue
            entry = {
                "vol_regime": vol,
                "cohort_n": cohort_st["n"],
                "cohort_wr": cohort_st["wr"],
                "matched_n": mst["n"],
                "matched_wr": mst["wr"],
                "lift_within_cohort_pp": mst["wr"] - cohort_st["wr"],
                "lift_vs_global_pp": mst["wr"] - baseline["wr"],
            }
            sig_findings[target_key][vol] = entry
            print(f"  vol={vol:<8} cohort: n={cohort_st['n']:>6} "
                  f"WR={cohort_st['wr']*100:.1f}% │ "
                  f"breadth={breadth_target}: n={mst['n']:>6} "
                  f"WR={mst['wr']*100:.1f}% "
                  f"(lift_global={entry['lift_vs_global_pp']*100:+.1f}pp, "
                  f"lift_cohort={entry['lift_within_cohort_pp']*100:+.1f}pp)")

        findings["by_signal_type"][sig_type] = sig_findings

    # Cross-signal summary surface: top 3 sector × signal lifts, top 3 month
    # × signal lifts, vol-conditional best
    print()
    print("═" * 80)
    print("L4 SYNTHESIS")
    print("═" * 80)
    top_sector_signal = []
    for sig, payload in findings["by_signal_type"].items():
        for sec, st in payload["by_sector"].items():
            top_sector_signal.append((sig, sec, st["n"], st["wr"], st["lift_pp"]))
    top_sector_signal.sort(key=lambda t: -t[4])
    print(f"\n  Top 5 sector × signal_type lifts:")
    for sig, sec, n, wr, lift in top_sector_signal[:5]:
        print(f"    {sig:<12} {sec:<10} n={n:>5} WR={wr*100:.1f}% "
              f"lift={lift*100:+.1f}pp")
    print(f"\n  Bottom 3 sector × signal_type lifts (avoid):")
    for sig, sec, n, wr, lift in top_sector_signal[-3:]:
        print(f"    {sig:<12} {sec:<10} n={n:>5} WR={wr*100:.1f}% "
              f"lift={lift*100:+.1f}pp")

    findings["summary"] = {
        "top_sector_signal_lifts": [
            {"signal": s, "sector": sec, "n": n, "wr": wr, "lift_pp": lift}
            for s, sec, n, wr, lift in top_sector_signal[:10]
        ],
        "bottom_sector_signal_lifts": [
            {"signal": s, "sector": sec, "n": n, "wr": wr, "lift_pp": lift}
            for s, sec, n, wr, lift in top_sector_signal[-5:]
        ],
    }

    OUTPUT_PATH.write_text(json.dumps(findings, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
