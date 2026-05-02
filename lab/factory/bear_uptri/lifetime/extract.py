"""
Bear UP_TRI cell — L1a: lifetime data extraction + segmentation.

Reads enriched_signals.parquet, filters to regime=Bear AND signal=UP_TRI,
segments across:
  • year buckets (2011-2026)
  • nifty_vol_regime (Low / Medium / High) — sub-regime proxy
  • sector (13 universe sectors)
  • nifty_60d_return_pct buckets (low/medium/high)
  • subregime label (per T1 detector logic)

Outputs aggregate baseline WRs per cohort.
Saves to lab/factory/bear_uptri/lifetime/data_summary.json.

Predictions per Session 2 prompt:
  • Total ≈ 15,151 (per S1 readiness notes)
  • Aggregate baseline WR ≈ 55.7%
  • Hot sub-regime (nifty_60d=low × vol=High) ≈ <30% of lifetime
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "data_summary.json"

# Reuse T1 sub-regime detector
_detector_path = (_LAB_ROOT / "factory" / "choppy" / "subregime"
                   / "detector_design.py")
_dspec = _ilu.spec_from_file_location("subregime_detector_l1", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["subregime_detector_l1"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_subregime = _detector_mod.detect_subregime


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
    print("L1a: Bear UP_TRI lifetime data extraction + segmentation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bear") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()
    bu_wl["scan_date"] = pd.to_datetime(bu_wl["scan_date"])
    bu_wl["year"] = bu_wl["scan_date"].dt.year

    n_total = len(bu_wl)
    print(f"\nTotal lifetime Bear UP_TRI signals (W/L/F): {n_total}")
    if n_total < 5000:
        print(f"⚠ HALT condition: lifetime count {n_total} < 5,000")

    overall = _wr_stats(bu_wl)
    print(f"Aggregate baseline WR: {overall['wr']*100:.1f}% "
          f"(W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']})")
    if overall["wr"] is not None and overall["wr"] > 0.80:
        print(f"⚠ HALT condition: lifetime baseline {overall['wr']*100:.1f}% > 80%")

    out = {
        "total": overall,
        "by_year": {},
        "by_nifty_vol_regime": {},
        "by_nifty_60d_return": {},
        "by_subregime_subtype": {},
        "by_sector": {},
        "by_signal_x_vol": {},
        "hot_subregime": {},
    }

    # By year
    print(f"\n── By year (temporal sub-regime profile) ──")
    print(f"  {'year':<6}{'n':>6}{'WR':>8}")
    for yr, grp in bu_wl.groupby("year"):
        st = _wr_stats(grp)
        out["by_year"][int(yr)] = st
        if st["wr"] is not None:
            print(f"  {yr:<6}{st['n']:>6}{st['wr']*100:>7.1f}%")

    # By nifty_vol_regime
    print(f"\n── By nifty_vol_regime ──")
    if "feat_nifty_vol_regime" in bu_wl.columns:
        for vol in ["Low", "Medium", "High"]:
            grp = bu_wl[bu_wl["feat_nifty_vol_regime"] == vol]
            st = _wr_stats(grp)
            out["by_nifty_vol_regime"][vol] = st
            if st["wr"] is not None:
                print(f"  {vol:<10}: n={st['n']:>6}  WR={st['wr']*100:.1f}%")

    # By nifty_60d_return_pct (categorical bins via spec thresholds)
    print(f"\n── By nifty_60d_return_pct level ──")
    sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
    from feature_loader import FeatureRegistry  # noqa: E402
    reg = FeatureRegistry.load_all()
    spec = reg.get("nifty_60d_return_pct")
    th = spec.level_thresholds
    low_b = float(str(th["low"]).replace("<", "").strip())
    high_b = float(str(th["high"]).replace(">", "").strip())
    print(f"  thresholds: low<{low_b}, high>{high_b}")
    bu_wl["_n60_level"] = bu_wl["feat_nifty_60d_return_pct"].apply(
        lambda v: ("low" if v < low_b
                  else ("high" if v > high_b else "medium"))
        if pd.notna(v) else None)
    for lvl in ["low", "medium", "high"]:
        grp = bu_wl[bu_wl["_n60_level"] == lvl]
        st = _wr_stats(grp)
        out["by_nifty_60d_return"][lvl] = st
        if st["wr"] is not None:
            pct = len(grp) / n_total * 100
            print(f"  {lvl:<8}: n={st['n']:>6} ({pct:>4.1f}%)  "
                  f"WR={st['wr']*100:.1f}%")

    # Apply T1 subregime detector → subtype
    print(f"\n── By subregime subtype (T1 detector) ──")
    bu_wl["_subtype"] = bu_wl.apply(
        lambda r: detect_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_market_breadth_pct"),
        ).subtype,
        axis=1,
    )
    for subtype, cnt in (bu_wl["_subtype"].value_counts().head(12)
                            .items()):
        grp = bu_wl[bu_wl["_subtype"] == subtype]
        st = _wr_stats(grp)
        out["by_subregime_subtype"][str(subtype)] = st
        pct = cnt / n_total * 100
        if st["wr"] is not None:
            print(f"  {subtype:<24}: n={st['n']:>6} "
                  f"({pct:>4.1f}%)  WR={st['wr']*100:.1f}%")

    # By sector
    print(f"\n── By sector (lifetime Bear UP_TRI) ──")
    sec_stats = []
    for sec, grp in bu_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        out["by_sector"][str(sec)] = st
        sec_stats.append((str(sec), st))
    sec_stats.sort(key=lambda t: -(t[1].get("wr") or 0))
    print(f"  {'sector':<14}{'n':>6}{'W':>5}{'L':>5}{'WR':>8}")
    for sec, st in sec_stats:
        if st["wr"] is None:
            continue
        print(f"  {sec:<14}{st['n']:>6}{st['n_w']:>5}{st['n_l']:>5}"
              f"{st['wr']*100:>7.1f}%")

    # ── HOT sub-regime test: nifty_60d=low AND nifty_vol=High ─────────
    print(f"\n── HOT SUB-REGIME TEST (nifty_60d=low × nifty_vol=High) ──")
    hot = bu_wl[(bu_wl["_n60_level"] == "low")
                & (bu_wl["feat_nifty_vol_regime"] == "High")]
    cold = bu_wl[~((bu_wl["_n60_level"] == "low")
                  & (bu_wl["feat_nifty_vol_regime"] == "High"))]
    hot_st = _wr_stats(hot)
    cold_st = _wr_stats(cold)
    pct_hot = len(hot) / n_total * 100 if n_total else 0
    print(f"  hot:  n={hot_st['n']:>6} ({pct_hot:.1f}% of lifetime)  "
          f"WR={hot_st['wr']*100:.1f}%" if hot_st['wr']
          else f"  hot: n={hot_st['n']}")
    print(f"  cold: n={cold_st['n']:>6} ({100-pct_hot:.1f}%)  "
          f"WR={cold_st['wr']*100:.1f}%" if cold_st['wr']
          else f"  cold: n={cold_st['n']}")
    if hot_st["wr"] and cold_st["wr"]:
        diff = (hot_st["wr"] - cold_st["wr"]) * 100
        print(f"  Δ hot − cold: {diff:+.1f}pp")
    out["hot_subregime"] = {
        "definition": "nifty_60d_return_pct=low AND nifty_vol_regime=High",
        "hot_n": hot_st["n"], "hot_wr": hot_st["wr"],
        "cold_n": cold_st["n"], "cold_wr": cold_st["wr"],
        "hot_pct_of_lifetime": pct_hot,
    }

    # Signal × vol cross-tab (bear UP_TRI specific)
    if "feat_nifty_vol_regime" in bu_wl.columns:
        for vol in ["Low", "Medium", "High"]:
            for n60 in ["low", "medium", "high"]:
                grp = bu_wl[(bu_wl["feat_nifty_vol_regime"] == vol)
                            & (bu_wl["_n60_level"] == n60)]
                st = _wr_stats(grp)
                key = f"{vol}|{n60}"
                out["by_signal_x_vol"][key] = st

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
