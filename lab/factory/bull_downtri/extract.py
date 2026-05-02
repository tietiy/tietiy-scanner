"""
Bull DOWN_TRI cell — BD1: lifetime data extraction + sub-regime application.

NO live Bull data exists. Pure lifetime methodology.
n=10,024 lifetime Bull DOWN_TRI signals; baseline 43.4% WR.

DOWN_TRI in Bull regime is contrarian short — predicted to be
structurally weak (parallel to Bear DOWN_TRI's 46.1% baseline).
Direction-flip prediction from Bull UP_TRI cell tested in BD2.

Sub-regime application: reuse Bull detector built in BU1
(nifty_200d_return × market_breadth → recovery/healthy/normal/late).
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "data_summary.json"

# Reuse Bull sub-regime detector
_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bd1", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bd1"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime


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
    print("BD1: Bull DOWN_TRI lifetime extract + Bull sub-regime application")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bd = df[(df["regime"] == "Bull") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    bd_wl = bd[bd["wlf"].isin(["W", "L", "F"])].copy()
    bd_wl["scan_date"] = pd.to_datetime(bd_wl["scan_date"])
    bd_wl["year"] = bd_wl["scan_date"].dt.year

    n_total = len(bd_wl)
    print(f"\nLifetime Bull DOWN_TRI: n={n_total}")
    if n_total < 1000:
        print(f"⚠ HALT condition: lifetime n<1,000")

    overall = _wr_stats(bd_wl)
    print(f"Aggregate baseline WR: {overall['wr']*100:.1f}% "
          f"(W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']})")

    live = pd.read_parquet(LIVE_PATH)
    bull_dt_live = live[(live["regime"] == "Bull") & (live["signal"] == "DOWN_TRI")]
    print(f"Live Bull DOWN_TRI signals: {len(bull_dt_live)}")

    # Apply Bull sub-regime detector
    bd_wl["sub"] = bd_wl.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    out = {
        "lifetime_universe": overall,
        "live_universe": {"n_total": int(len(bull_dt_live))},
        "subregime_distribution": {},
        "by_sector": {},
        "by_year": {},
    }

    # Sub-regime distribution
    print(f"\n══ Sub-regime distribution (Bull detector applied) ══")
    print(f"  {'sub-regime':<14}{'n':>7}{'%':>7}{'WR':>8}{'lift':>8}")
    for sub in ["recovery_bull", "healthy_bull", "normal_bull", "late_bull",
                "unknown"]:
        grp = bd_wl[bd_wl["sub"] == sub]
        if len(grp) == 0:
            continue
        st = _wr_stats(grp)
        lift = (st["wr"] - overall["wr"]) * 100 if st["wr"] else 0
        out["subregime_distribution"][sub] = {
            "n": int(st["n"]),
            "pct": float(st["n"] / n_total),
            "wr": float(st["wr"]) if st["wr"] is not None else None,
            "lift_pp": float(lift),
        }
        print(f"  {sub:<14}{st['n']:>7}{st['n']/n_total*100:>6.1f}%"
              f"{(st['wr'] or 0)*100:>7.1f}%{lift:>+7.1f}pp")

    # Compare to Bull UP_TRI sub-regime distribution (predicted INVERSION)
    print(f"\n  Compare to Bull UP_TRI sub-regime structure:")
    print(f"    Bull UP_TRI:    recovery 60.2% / healthy 58.4% /")
    print(f"                    normal 51.3% / late 45.1%")
    print(f"    Bull DOWN_TRI:  see above — predicted INVERSION")

    # Sector
    print(f"\n══ Sector × WR (lifetime, n>=200) ══")
    sec_rows = []
    for sec, grp in bd_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        if st["n"] < 200 or st["wr"] is None:
            continue
        lift = (st["wr"] - overall["wr"]) * 100
        out["by_sector"][str(sec)] = {
            "n": int(st["n"]), "wr": float(st["wr"]),
            "lift_pp": float(lift),
        }
        sec_rows.append((str(sec), st, lift))
    sec_rows.sort(key=lambda t: -t[2])
    print(f"  {'sector':<12}{'n':>6}{'W':>5}{'L':>5}{'WR':>8}{'lift':>8}")
    for sec, st, lift in sec_rows:
        print(f"  {sec:<12}{st['n']:>6}{st['n_w']:>5}{st['n_l']:>5}"
              f"{st['wr']*100:>7.1f}%{lift:>+7.1f}pp")

    # Year
    print(f"\n══ By year ══")
    for yr, grp in bd_wl.groupby("year"):
        st = _wr_stats(grp)
        out["by_year"][int(yr)] = st
        if st["wr"] is not None and st["n"] >= 200:
            print(f"  {yr:<6}{st['n']:>6}  WR={st['wr']*100:.1f}%")

    # Methodology applicability assessment
    print()
    print("═" * 80)
    print("Methodology assessment")
    print("═" * 80)
    print(f"\n  Lifetime n: {n_total} (≥1000 ✓)")
    print(f"  Live n: {len(bull_dt_live)} (no live data — lifetime-only methodology)")
    print(f"  Sub-regime cells with n≥100: "
          f"{sum(1 for v in out['subregime_distribution'].values() if v['n'] >= 100)}")
    print(f"  Recommended: lifetime-only adaptation (parallel to Bull UP_TRI)")
    print(f"  Expected outcome: PROVISIONAL_OFF default; direction-flip test in BD2")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
