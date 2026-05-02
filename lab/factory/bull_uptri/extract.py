"""
Bull UP_TRI cell — BU1a: lifetime data extraction.

NO live Bull data exists (current April-May 2026 has 0 Bull-classified
signals). Pure lifetime methodology. n=38,100 lifetime Bull UP_TRI
signals — largest single-cell cohort across the Lab.

Filter:
  signal_type = UP_TRI
  regime = Bull
  outcome ∈ {DAY6_WIN, TARGET_HIT, DAY6_LOSS, STOP_HIT, DAY6_FLAT}

Saves: lab/factory/bull_uptri/data_summary.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
LIVE_FEATURES_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "data_summary.json"


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


def main():
    print("─" * 80)
    print("BU1a: Bull UP_TRI lifetime extraction (no live data)")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bull") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()
    bu_wl["scan_date"] = pd.to_datetime(bu_wl["scan_date"])
    bu_wl["year"] = bu_wl["scan_date"].dt.year

    n_total = len(bu_wl)
    print(f"\nLifetime Bull UP_TRI: n={n_total}")
    if n_total < 5000:
        print(f"⚠ HALT condition: lifetime n<5000")

    overall = _wr_stats(bu_wl)
    print(f"Aggregate baseline WR: {overall['wr']*100:.1f}% "
          f"(W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']})")

    # Live data check
    live = pd.read_parquet(LIVE_FEATURES_PATH)
    bull_live = live[live["regime"] == "Bull"]
    print(f"Live Bull signals (any type): {len(bull_live)}")

    out = {
        "lifetime_universe": overall,
        "live_universe": {"n_total": int(len(bull_live))},
        "by_year": {},
        "by_sector": {},
        "by_signal_only": {},
    }

    # By year
    print(f"\n── By year ──")
    print(f"  {'year':<6}{'n':>6}{'W':>6}{'L':>6}{'WR':>8}")
    for yr, grp in bu_wl.groupby("year"):
        st = _wr_stats(grp)
        out["by_year"][int(yr)] = st
        if st["wr"] is not None:
            print(f"  {yr:<6}{st['n']:>6}{st['n_w']:>6}{st['n_l']:>6}"
                  f"{st['wr']*100:>7.1f}%")

    # By sector
    print(f"\n── By sector ──")
    sec_rows = []
    for sec, grp in bu_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        out["by_sector"][str(sec)] = st
        sec_rows.append((str(sec), st))
    sec_rows.sort(key=lambda t: -(t[1].get("wr") or 0))
    print(f"  {'sector':<12}{'n':>6}{'W':>6}{'L':>6}{'WR':>8}")
    for sec, st in sec_rows:
        if st["wr"] is None:
            continue
        print(f"  {sec:<12}{st['n']:>6}{st['n_w']:>6}{st['n_l']:>6}"
              f"{st['wr']*100:>7.1f}%")

    # By feature distributions for predicted axes
    print(f"\n── Predicted axis feature distributions ──")
    axis_features = [
        "feat_nifty_200d_return_pct",
        "feat_nifty_60d_return_pct",
        "feat_nifty_vol_percentile_20d",
        "feat_market_breadth_pct",
        "feat_multi_tf_alignment_score",
        "feat_advance_decline_ratio_20d",
        "feat_sector_rank_within_universe",
    ]
    for col in axis_features:
        if col in bu_wl.columns:
            s = bu_wl[col].dropna()
            print(f"  {col[5:]:<32} n={len(s)} "
                  f"min={s.min():.3f} q25={s.quantile(.25):.3f} "
                  f"median={s.median():.3f} q75={s.quantile(.75):.3f} "
                  f"max={s.max():.3f}")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
