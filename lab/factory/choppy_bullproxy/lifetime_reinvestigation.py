"""
Choppy BULL_PROXY cell — V3 lifetime re-investigation.

The live KILL verdict (8 signals, 25% WR) is tested at lifetime scale.

Lifetime BULL_PROXY × Choppy: 1,939 signals, ~50% baseline WR.

Multiple filters tried:
  • Single-feature filters (each top differentiator from V2 + new ideas)
  • Multi-feature filters (compression-coil signature from V2 hypothesis)
  • Sector-conditional filters

Outcome decision:
  • KILL CONFIRMED: no filter beats baseline by ≥10pp on n≥50
  • KILL REVISED: a filter found that lifts WR ≥60% on meaningful sample
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
_spec = _ilu.spec_from_file_location("uptri_filter_v3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level
apply_filter = _filter_mod.apply_filter

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "lifetime_reinvestigation.json"

# Lift threshold for "promising filter" claim
LIFT_THRESHOLD = 0.10
N_THRESHOLD = 50


def _wlf_lifetime(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _wr_stats(grp: pd.DataFrame) -> tuple:
    nw = (grp["wlf"] == "W").sum()
    nl = (grp["wlf"] == "L").sum()
    return ((nw / (nw + nl)) if (nw + nl) > 0 else None,
            int(nw), int(nl))


def evaluate_filter(df, name, required, forbidden, spec_by_id, bounds_cache):
    mask = apply_filter(df, required, forbidden, spec_by_id, bounds_cache)
    matched = df[mask]; skipped = df[~mask]
    m_wr, m_w, m_l = _wr_stats(matched)
    s_wr, s_w, s_l = _wr_stats(skipped)
    return {
        "name": name,
        "required": [f"{f}={l}" for f, l in required],
        "forbidden": [f"{f}={l}" for f, l in forbidden],
        "n_matched": len(matched),
        "n_matched_wl": m_w + m_l,
        "n_matched_w": m_w, "n_matched_l": m_l,
        "matched_wr": float(m_wr) if m_wr is not None else None,
        "match_rate": len(matched) / len(df) if len(df) > 0 else 0.0,
        "n_skipped": len(skipped),
        "skipped_wr": float(s_wr) if s_wr is not None else None,
    }


def main():
    print("─" * 80)
    print("CELL: Choppy BULL_PROXY — V3 lifetime re-investigation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    sub = df[(df["signal"] == "BULL_PROXY")
                & (df["regime"] == "Choppy")].copy()
    sub["wlf"] = sub["outcome"].apply(_wlf_lifetime)
    sub_wl = sub[sub["wlf"].isin(["W", "L", "F"])].copy()
    n = len(sub_wl)
    nw = (sub_wl["wlf"] == "W").sum()
    nl = (sub_wl["wlf"] == "L").sum()
    baseline = nw / (nw + nl)
    print(f"\nLifetime BULL_PROXY × Choppy: n={n}")
    print(f"  W={nw}, L={nl}, F={(sub_wl['wlf']=='F').sum()}")
    print(f"  baseline WR: {baseline*100:.1f}%")
    print(f"  Live finding (KILL verdict): n=8, WR=25%, 0/175 Phase-4 patterns "
          f"validated")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # Sector breakdown — sector-conditional filter testing
    print(f"\n── Sector breakdown of BULL_PROXY × Choppy lifetime ──")
    if "sector" in sub_wl.columns:
        sector_stats = []
        for sec in sub_wl["sector"].dropna().unique():
            s_grp = sub_wl[sub_wl["sector"] == sec]
            s_n = len(s_grp)
            if s_n < 50:
                continue
            s_nw = (s_grp["wlf"] == "W").sum()
            s_nl = (s_grp["wlf"] == "L").sum()
            s_wr = s_nw / (s_nw + s_nl) if (s_nw + s_nl) > 0 else 0
            sector_stats.append((sec, s_n, s_nw, s_nl, s_wr))
        sector_stats.sort(key=lambda x: -x[4])
        print(f"  {'sector':<14}{'n':>6}{'W':>5}{'L':>5}{'WR':>8}")
        for sec, s_n, s_nw, s_nl, s_wr in sector_stats[:13]:
            lift = (s_wr - baseline) * 100
            marker = "★" if lift >= LIFT_THRESHOLD * 100 else " "
            print(f"  {marker}{sec:<13}{s_n:>6}{s_nw:>5}{s_nl:>5}{s_wr*100:>7.1f}%  ({lift:+.1f}pp)")

    # Filter candidates
    candidates = [
        # Compression-coil hypothesis (the WATCH-cluster signature from V2)
        ("F1: ema_bull AND coiled=medium",
         [("ema_alignment", "bull"), ("coiled_spring_score", "medium")], []),
        # Single feature filters
        ("F2: ema_alignment=bull",
         [("ema_alignment", "bull")], []),
        ("F3: coiled_spring_score=medium",
         [("coiled_spring_score", "medium")], []),
        # Anti-feature inversions (per V2 finding that they're actually positive)
        ("F4: market_breadth_pct=high",
         [("market_breadth_pct", "high")], []),
        ("F5: higher_highs_intact_flag=True",
         [("higher_highs_intact_flag", "True")], []),
        # Strict combination
        ("F6: ema_bull + coiled=medium + market_breadth=high",
         [("ema_alignment", "bull"), ("coiled_spring_score", "medium"),
          ("market_breadth_pct", "high")], []),
        # KILL hypothesis test (forbid extended momentum)
        ("F7: forbid (ema20_dist=high AND market_breadth=high)",
         [], [("ema20_distance_pct", "high"),
              ("market_breadth_pct", "high")]),
        # Calendar-based
        ("F8: day_of_week=Tue + bull EMA",
         [("day_of_week", "Tue"), ("ema_alignment", "bull")], []),
    ]

    print(f"\n── Filter back-test ──")
    print(f"{'name':<50}{'n_match':>9}{'wr':>9}{'lift':>9}{'verdict':>20}")
    print("─" * 100)
    results = []
    for name, req, forb in candidates:
        r = evaluate_filter(sub_wl, name, req, forb, spec_by_id, bounds_cache)
        results.append(r)
        if r["matched_wr"] is None:
            verdict = "no matches"
        elif r["n_matched_wl"] < N_THRESHOLD:
            verdict = "too small"
        elif (r["matched_wr"] - baseline) >= LIFT_THRESHOLD:
            verdict = "★ PROMISING"
        elif (r["matched_wr"] - baseline) >= 0.05:
            verdict = "MARGINAL"
        else:
            verdict = "no edge"
        r["verdict"] = verdict
        m_wr = r["matched_wr"]
        wr_str = f"{m_wr*100:.1f}%" if m_wr is not None else "—"
        lift = (m_wr - baseline) * 100 if m_wr is not None else 0
        print(f"  {name:<50}{r['n_matched']:>9}{wr_str:>9}"
              f"{lift:>+8.1f}pp{verdict:>20}")

    # Decide overall verdict
    promising = [r for r in results
                    if r.get("verdict") == "★ PROMISING"]
    out = {
        "lifetime_universe": {
            "n": n, "n_w": int(nw), "n_l": int(nl),
            "baseline_wr": float(baseline),
        },
        "live_finding": {
            "n_live": 8, "live_wr": 0.25, "live_verdict": "KILL",
        },
        "filters_tested": results,
        "promising_filters": promising,
    }

    print()
    print("═" * 80)
    print("V3 SUMMARY — KILL verdict at lifetime scale")
    print("═" * 80)
    if promising:
        print(f"\n⚠ {len(promising)} PROMISING filters found at lifetime scale.")
        print("KILL verdict needs revision. Compression-coil exception may be real.")
        for r in promising:
            print(f"  → {r['name']}: n={r['n_matched_wl']}, "
                  f"wr={r['matched_wr']*100:.1f}%, "
                  f"lift {(r['matched_wr']-baseline)*100:+.1f}pp")
        out["overall_verdict"] = "KILL_REVISED"
    else:
        print(f"\n✓ No filter beats baseline by ≥{LIFT_THRESHOLD*100:.0f}pp "
              f"on n≥{N_THRESHOLD} at lifetime scale.")
        print(f"KILL verdict CONFIRMED. Choppy BULL_PROXY structurally dead.")
        out["overall_verdict"] = "KILL_CONFIRMED"

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
