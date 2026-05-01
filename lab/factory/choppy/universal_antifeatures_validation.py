"""
Choppy regime — V2 universal anti-features lifetime validation.

The Choppy regime synthesis playbook claimed 4 universal anti-features:
  1. higher_highs_intact_flag = True
  2. ema20_distance_pct = high
  3. MACD_histogram_slope = falling
  4. market_breadth_pct = high

For each, test at lifetime scale (35,496 Choppy signals across all signal
types). Compute:
  • WR_with_antifeature_present
  • WR_with_antifeature_absent
  • discrimination = WR_absent - WR_present (positive = anti-feature confirmed)

Verdict:
  CONFIRMED — discrimination ≥ 5pp (statistically meaningful negative effect)
  WEAK — discrimination 0-5pp (small effect, may not justify universal claim)
  REFUTED — discrimination ≤ 0 (anti-feature actually neutral or positive)

Tests across signal types separately and combined.
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

from feature_loader import FeatureRegistry  # noqa: E402

_filter_path = (_LAB_ROOT / "factory" / "choppy_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("uptri_filter_v2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "universal_antifeatures_validation.json"

ANTI_FEATURES = [
    ("higher_highs_intact_flag", "True"),
    ("ema20_distance_pct", "high"),
    ("MACD_histogram_slope", "falling"),
    ("market_breadth_pct", "high"),
]


def _wlf_lifetime(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _wr(grp: pd.DataFrame) -> tuple:
    nw = (grp["wlf"] == "W").sum()
    nl = (grp["wlf"] == "L").sum()
    return ((nw / (nw + nl)) if (nw + nl) > 0 else None,
            int(nw), int(nl))


def evaluate_anti_feature(df: pd.DataFrame, fid: str, lvl: str,
                              spec_by_id: dict, bounds_cache: dict) -> dict:
    spec = spec_by_id.get(fid)
    if spec is None:
        return {"feature_id": fid, "level": lvl, "error": "spec not found"}
    col = f"feat_{fid}"
    if col not in df.columns:
        return {"feature_id": fid, "level": lvl, "error": "column missing"}
    mask = df[col].apply(
        lambda v: matches_level(spec, v, lvl, bounds_cache))
    present = df[mask]
    absent = df[~mask & df[col].notna()]
    p_wr, p_w, p_l = _wr(present)
    a_wr, a_w, a_l = _wr(absent)
    discrimination = (
        (a_wr - p_wr) if (p_wr is not None and a_wr is not None) else None
    )
    if discrimination is None:
        verdict = "INSUFFICIENT_DATA"
    elif discrimination >= 0.05:
        verdict = "CONFIRMED (≥5pp negative effect)"
    elif discrimination > 0:
        verdict = "WEAK (0-5pp negative effect)"
    else:
        verdict = "REFUTED (no/positive effect)"
    return {
        "feature_id": fid, "level": lvl,
        "n_present": len(present), "n_absent": len(absent),
        "wr_present": float(p_wr) if p_wr is not None else None,
        "wr_absent": float(a_wr) if a_wr is not None else None,
        "discrimination_pp": float(discrimination) if discrimination is not None else None,
        "verdict": verdict,
    }


def main():
    print("─" * 80)
    print("CELL: Choppy regime — V2 universal anti-features lifetime validation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    sub = df[df["regime"] == "Choppy"].copy()
    sub["wlf"] = sub["outcome"].apply(_wlf_lifetime)
    sub_wl = sub[sub["wlf"].isin(["W", "L", "F"])].copy()
    n_total = len(sub_wl)
    print(f"\nLifetime Choppy universe: {n_total} signals "
          f"(across UP_TRI/DOWN_TRI/BULL_PROXY)")
    nw = (sub_wl["wlf"] == "W").sum()
    nl = (sub_wl["wlf"] == "L").sum()
    print(f"Aggregate baseline WR: {nw/(nw+nl)*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    out = {
        "lifetime_universe": {
            "n": n_total, "n_w": int(nw), "n_l": int(nl),
            "baseline_wr": float(nw / (nw + nl)),
        },
        "anti_features": [],
        "per_signal_type": {},
    }

    # Aggregate across all 3 signal types
    print(f"\n── Aggregate (all Choppy, n={n_total}) ──")
    print(f"{'feature':<28}{'level':<10}{'n_present':>10}"
          f"{'wr_present':>12}{'wr_absent':>11}{'disc(pp)':>10}{'verdict':>30}")
    print("─" * 110)
    for fid, lvl in ANTI_FEATURES:
        r = evaluate_anti_feature(sub_wl, fid, lvl,
                                       spec_by_id, bounds_cache)
        out["anti_features"].append(r)
        if "error" in r:
            print(f"  {fid:<26}{lvl:<10} ERROR: {r['error']}")
            continue
        print(f"  {fid:<26}{lvl:<10}{r['n_present']:>10}"
              f"{(r['wr_present'] or 0)*100:>11.1f}%"
              f"{(r['wr_absent'] or 0)*100:>10.1f}%"
              f"{(r['discrimination_pp'] or 0)*100:>+9.1f}"
              f"  {r['verdict']:<30}")

    # Per signal-type breakdown
    print(f"\n── Per signal-type ──")
    for sig_type in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub_st = sub_wl[sub_wl["signal"] == sig_type].copy()
        n_st = len(sub_st)
        if n_st < 100:
            continue
        nw_st = (sub_st["wlf"] == "W").sum()
        nl_st = (sub_st["wlf"] == "L").sum()
        baseline_st = nw_st / (nw_st + nl_st)
        print(f"\n  {sig_type} (n={n_st}, baseline WR={baseline_st*100:.1f}%):")
        out["per_signal_type"][sig_type] = {
            "n": n_st, "baseline_wr": float(baseline_st),
            "anti_features": [],
        }
        for fid, lvl in ANTI_FEATURES:
            r = evaluate_anti_feature(sub_st, fid, lvl,
                                           spec_by_id, bounds_cache)
            out["per_signal_type"][sig_type]["anti_features"].append(r)
            if "error" in r:
                continue
            print(f"    {fid:<26}{lvl:<10}{r['n_present']:>8}"
                  f"  wr_p={(r['wr_present'] or 0)*100:>5.1f}%  "
                  f"wr_a={(r['wr_absent'] or 0)*100:>5.1f}%  "
                  f"disc={(r['discrimination_pp'] or 0)*100:>+5.1f}pp  "
                  f"{r['verdict']}")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # Summary verdict
    print()
    print("═" * 80)
    print("V2 SUMMARY — universal anti-features at lifetime scale")
    print("═" * 80)
    print()
    n_confirmed = sum(1 for r in out["anti_features"]
                         if r.get("verdict", "").startswith("CONFIRMED"))
    n_weak = sum(1 for r in out["anti_features"]
                    if r.get("verdict", "").startswith("WEAK"))
    n_refuted = sum(1 for r in out["anti_features"]
                       if r.get("verdict", "").startswith("REFUTED"))
    print(f"  CONFIRMED at lifetime: {n_confirmed} of {len(ANTI_FEATURES)}")
    print(f"  WEAK at lifetime:      {n_weak} of {len(ANTI_FEATURES)}")
    print(f"  REFUTED at lifetime:   {n_refuted} of {len(ANTI_FEATURES)}")


if __name__ == "__main__":
    main()
