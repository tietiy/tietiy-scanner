"""
Bull BULL_PROXY cell — BP1: lifetime extraction + Bull sub-regime
application + direction-alignment with Bull UP_TRI.

Pure lifetime methodology (0 live Bull signals). n=2,685 lifetime
Bull BULL_PROXY signals; baseline 51.1% WR (above 50% — strongest
Bull-side baseline of the 3 Bull cells).

Direction-alignment hypothesis: Bull BULL_PROXY follows Bull UP_TRI
direction (both bullish setups). Predicted:
  • Best sub-regime should be recovery_bull (matches UP_TRI's 60.2%)
  • Worst sub-regime should be late_bull (matches UP_TRI's 45.1%)
  • If TRUE → confirms cross-cell directional alignment within regime
  • If FALSE → architectural surprise; investigate

Saves: lab/factory/bull_bullproxy/data_summary.json
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
_dspec = _ilu.spec_from_file_location("bull_subregime_bp1", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bp1"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime

# Bull UP_TRI sub-regime WRs (for direction-alignment comparison)
BULL_UPTRI_WR = {
    "recovery_bull": 0.602,
    "healthy_bull": 0.584,
    "normal_bull": 0.513,
    "late_bull": 0.451,
}


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
    print("BP1: Bull BULL_PROXY lifetime extract + sub-regime + alignment")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bp = df[(df["regime"] == "Bull") & (df["signal"] == "BULL_PROXY")].copy()
    bp["wlf"] = bp["outcome"].apply(_wlf)
    bp_wl = bp[bp["wlf"].isin(["W", "L", "F"])].copy()
    bp_wl["scan_date"] = pd.to_datetime(bp_wl["scan_date"])
    bp_wl["year"] = bp_wl["scan_date"].dt.year

    n_total = len(bp_wl)
    print(f"\nLifetime Bull BULL_PROXY: n={n_total}")
    if n_total < 500:
        print(f"⚠ HALT: lifetime n<500")

    overall = _wr_stats(bp_wl)
    print(f"Aggregate baseline WR: {overall['wr']*100:.1f}% "
          f"(W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']})")

    # Live check
    live = pd.read_parquet(LIVE_PATH)
    bull_bp_live = live[(live["regime"] == "Bull") & (live["signal"] == "BULL_PROXY")]
    print(f"Live Bull BULL_PROXY: {len(bull_bp_live)}")

    # Apply Bull sub-regime detector
    bp_wl["sub"] = bp_wl.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    out = {
        "lifetime_universe": overall,
        "live_universe": {"n_total": int(len(bull_bp_live))},
        "subregime_distribution": {},
        "by_sector": {},
        "direction_alignment": {},
    }

    # Sub-regime distribution + direction-alignment with Bull UP_TRI
    print(f"\n══ Sub-regime distribution (Bull detector applied) ══")
    print(f"  {'sub-regime':<14}{'n':>6}{'%':>6}{'WR':>8}{'lift':>8}"
          f"{'UP_TRI WR':>10}{'aligned?':>11}")
    sub_wrs = {}
    for sub in ["recovery_bull", "healthy_bull", "normal_bull", "late_bull",
                "unknown"]:
        grp = bp_wl[bp_wl["sub"] == sub]
        if len(grp) == 0:
            continue
        st = _wr_stats(grp)
        lift = (st["wr"] - overall["wr"]) * 100 if st["wr"] else 0
        uptri_wr = BULL_UPTRI_WR.get(sub, None)
        out["subregime_distribution"][sub] = {
            "n": int(st["n"]),
            "pct": float(st["n"] / n_total),
            "wr": float(st["wr"]) if st["wr"] is not None else None,
            "lift_pp": float(lift),
            "bull_uptri_wr": uptri_wr,
        }
        sub_wrs[sub] = st["wr"]
        align_str = ""
        if uptri_wr is not None and st["wr"] is not None:
            # Aligned if both above baseline or both below baseline
            uptri_baseline = 0.520  # Bull UP_TRI baseline
            bp_baseline = overall["wr"]
            uptri_above = uptri_wr > uptri_baseline
            bp_above = st["wr"] > bp_baseline
            align_str = "✓ aligned" if uptri_above == bp_above else "✗ DIVERGE"
        print(f"  {sub:<14}{st['n']:>6}{st['n']/n_total*100:>5.1f}%"
              f"{(st['wr'] or 0)*100:>7.1f}%{lift:>+7.1f}pp"
              f"{(uptri_wr*100 if uptri_wr else 0):>9.1f}%"
              f"  {align_str:<11}")

    # Direction-alignment verdict
    print()
    print("─" * 80)
    print("Direction-alignment verdict (Bull BULL_PROXY vs Bull UP_TRI)")
    print("─" * 80)

    # Score: how many sub-regimes have same direction (above/below baseline)
    aligned_count = 0
    diverge_count = 0
    for sub, info in out["subregime_distribution"].items():
        if info.get("bull_uptri_wr") is None or info.get("wr") is None:
            continue
        uptri_above = info["bull_uptri_wr"] > 0.520
        bp_above = info["wr"] > overall["wr"]
        if uptri_above == bp_above:
            aligned_count += 1
        else:
            diverge_count += 1

    if aligned_count >= 3:
        align_verdict = (f"✓ ALIGNED ({aligned_count}/{aligned_count+diverge_count}) "
                         f"— Bull BULL_PROXY follows Bull UP_TRI direction "
                         f"(both bullish cells)")
    elif diverge_count >= 3:
        align_verdict = (f"✗ DIVERGE ({diverge_count}/{aligned_count+diverge_count}) "
                         f"— surprise: Bull BULL_PROXY does NOT follow Bull "
                         f"UP_TRI's sub-regime structure")
    else:
        align_verdict = (f"MIXED ({aligned_count} aligned, {diverge_count} "
                         f"diverging)")

    print(f"  {align_verdict}")
    out["direction_alignment"] = {
        "verdict": align_verdict,
        "aligned_count": aligned_count,
        "diverge_count": diverge_count,
    }

    # Sector
    print(f"\n══ Sector × WR (lifetime, n>=100) ══")
    sec_rows = []
    for sec, grp in bp_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        st = _wr_stats(grp)
        if st["n"] < 100 or st["wr"] is None:
            continue
        lift = (st["wr"] - overall["wr"]) * 100
        out["by_sector"][str(sec)] = {
            "n": int(st["n"]), "wr": float(st["wr"]),
            "lift_pp": float(lift),
        }
        sec_rows.append((str(sec), st, lift))
    sec_rows.sort(key=lambda t: -t[2])
    print(f"  {'sector':<12}{'n':>6}{'WR':>8}{'lift':>8}")
    for sec, st, lift in sec_rows:
        print(f"  {sec:<12}{st['n']:>6}{st['wr']*100:>7.1f}%{lift:>+7.1f}pp")

    # Compare to Bear BULL_PROXY
    print()
    print("─" * 80)
    print("Comparison to Bear BULL_PROXY (parallel cell)")
    print("─" * 80)
    print(f"  Bear BULL_PROXY lifetime baseline:  47.3%")
    print(f"  Bull BULL_PROXY lifetime baseline:  {overall['wr']*100:.1f}%")
    print(f"  Difference: {(overall['wr'] - 0.473)*100:+.1f}pp")
    print(f"  Bear BULL_PROXY hot sub-regime:     63.7% (+16.4pp lift)")
    print(f"  Bull BULL_PROXY recovery_bull:      "
          f"{(sub_wrs.get('recovery_bull', 0))*100:.1f}% "
          f"({(sub_wrs.get('recovery_bull', 0) - overall['wr'])*100:+.1f}pp lift)")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
