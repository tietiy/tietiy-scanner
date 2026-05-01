"""
Choppy regime — L1: lifetime data extraction + segmentation.

Reads enriched_signals.parquet, filters to regime=Choppy, segments across:
  • signal_type (UP_TRI / DOWN_TRI / BULL_PROXY)
  • year buckets (2011-2026)
  • nifty_vol_regime (Low / Medium / High) — sub-regime proxy
  • sector (13 universe sectors)

Outputs aggregate baseline WRs per cohort + sub-regime counts.
Saves to lab/factory/choppy/lifetime/data_summary.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "data_summary.json"


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
    print("L1: Choppy lifetime data extraction + segmentation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    ch = df[df["regime"] == "Choppy"].copy()
    ch["wlf"] = ch["outcome"].apply(_wlf)
    ch_wl = ch[ch["wlf"].isin(["W", "L", "F"])].copy()
    ch_wl["scan_date"] = pd.to_datetime(ch_wl["scan_date"])
    ch_wl["year"] = ch_wl["scan_date"].dt.year

    n_total = len(ch_wl)
    print(f"\nTotal lifetime Choppy signals (W/L/F): {n_total}")
    overall = _wr_stats(ch_wl)
    print(f"Aggregate baseline WR: {overall['wr']*100:.1f}% "
          f"(W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']})")

    out = {
        "total": overall,
        "by_signal_type": {},
        "by_year": {},
        "by_nifty_vol_regime": {},
        "by_signal_x_vol": {},
        "by_sector": {},
        "by_signal_x_sector": {},
    }

    # By signal type
    print(f"\n── By signal_type ──")
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        s = ch_wl[ch_wl["signal"] == sig]
        st = _wr_stats(s)
        out["by_signal_type"][sig] = st
        if st["wr"] is not None:
            print(f"  {sig:<12}: n={st['n']:>6}  W={st['n_w']:>5}  "
                  f"L={st['n_l']:>5}  WR={st['wr']*100:.1f}%")

    # By year (sub-regime over time)
    print(f"\n── By year (temporal sub-regime profile) ──")
    print(f"  {'year':<6}{'n':>6}{'WR':>8}")
    for yr, grp in ch_wl.groupby("year"):
        st = _wr_stats(grp)
        out["by_year"][int(yr)] = st
        if st["wr"] is not None:
            print(f"  {yr:<6}{st['n']:>6}{st['wr']*100:>7.1f}%")

    # By nifty_vol_regime (within Choppy)
    print(f"\n── By nifty_vol_regime (sub-regime within Choppy) ──")
    if "feat_nifty_vol_regime" in ch_wl.columns:
        for vol, grp in ch_wl.groupby("feat_nifty_vol_regime"):
            st = _wr_stats(grp)
            out["by_nifty_vol_regime"][str(vol)] = st
            if st["wr"] is not None:
                print(f"  {vol:<10}: n={st['n']:>6}  WR={st['wr']*100:.1f}%")

        # Signal × vol cross-tab
        print(f"\n── Signal × vol_regime cross-tab (key for L4) ──")
        print(f"  {'signal':<12}{'vol':<10}{'n':>6}{'WR':>8}")
        for (sig, vol), grp in ch_wl.groupby(["signal", "feat_nifty_vol_regime"]):
            st = _wr_stats(grp)
            key = f"{sig}|{vol}"
            out["by_signal_x_vol"][key] = st
            if st["wr"] is not None and st["n"] >= 50:
                print(f"  {sig:<12}{str(vol):<10}{st['n']:>6}{st['wr']*100:>7.1f}%")

    # By sector
    print(f"\n── By sector (lifetime Choppy, all signal types) ──")
    sec_stats = []
    for sec, grp in ch_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        out["by_sector"][str(sec)] = st
        sec_stats.append((str(sec), st))
    # Sort by WR descending
    sec_stats.sort(key=lambda t: -(t[1].get("wr") or 0))
    print(f"  {'sector':<14}{'n':>6}{'W':>5}{'L':>5}{'WR':>8}")
    for sec, st in sec_stats:
        if st["wr"] is None:
            continue
        print(f"  {sec:<14}{st['n']:>6}{st['n_w']:>5}{st['n_l']:>5}{st['wr']*100:>7.1f}%")

    # Signal × sector
    print(f"\n── Signal × sector top performers (n≥100) ──")
    cross_stats = []
    for (sig, sec), grp in ch_wl.groupby(["signal", "sector"]):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        key = f"{sig}|{sec}"
        out["by_signal_x_sector"][key] = st
        if st["n"] >= 100 and st["wr"] is not None:
            cross_stats.append((sig, sec, st))
    cross_stats.sort(key=lambda t: -t[2]["wr"])
    print(f"  {'signal':<12}{'sector':<14}{'n':>6}{'WR':>8}")
    for sig, sec, st in cross_stats[:15]:
        print(f"  {sig:<12}{sec:<14}{st['n']:>6}{st['wr']*100:>7.1f}%")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
