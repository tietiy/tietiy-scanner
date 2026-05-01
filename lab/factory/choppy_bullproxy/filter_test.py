"""
Choppy BULL_PROXY cell — C3: filter back-test against 8 live signals.

Methodology adapted: no Phase 5 winners exist, so the "narrow exception"
hypothesis is tested using:
  1. The WATCH cluster's feature signature (coiled_spring=medium +
     ema_alignment=bull) — proposed as the survivable subset
  2. The REJECTED cluster's feature signature (ema20_distance=high +
     market_breadth=high) — proposed as KILL conditions

Tests against 8 live BULL_PROXY Choppy signals (2W: INDUSINDBK, VOLTAS;
6L: ALKEM, EICHERMOT, SBILIFE, SUNDARMFIN, MFSL, HINDZINC).
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

# Reuse choppy_uptri/filter_test.py helpers via importlib
_uptri_filter_path = (_LAB_ROOT / "factory" / "choppy_uptri"
                          / "filter_test.py")
_spec = _ilu.spec_from_file_location("uptri_filter", _uptri_filter_path)
_uptri_filter = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_uptri_filter)
matches_level = _uptri_filter.matches_level
apply_filter = _uptri_filter.apply_filter
evaluate_filter = _uptri_filter.evaluate_filter
_parse_numeric_thresholds = _uptri_filter._parse_numeric_thresholds

from feature_loader import FeatureRegistry  # noqa: E402

OUTPUT_PATH = _HERE / "filter_test_results.json"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"


def main():
    print("─" * 80)
    print("CELL 3: Choppy BULL_PROXY — C3 filter articulation + back-test")
    print("─" * 80)

    live = pd.read_parquet(LIVE_PATH)
    df = live[(live["signal"] == "BULL_PROXY")
                & (live["regime"] == "Choppy")].copy()
    n = len(df)
    nw = (df["wlf"] == "W").sum(); nl = (df["wlf"] == "L").sum()
    nf = (df["wlf"] == "F").sum()
    baseline_wr = nw / (nw + nl) if (nw + nl) > 0 else 0
    print(f"\nLive Choppy BULL_PROXY universe: {n} signals "
          f"(W={nw}, L={nl}, F={nf})")
    print(f"Baseline WR: {baseline_wr*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # Audit feature values for the 8 live signals
    print()
    print("── Live signal feature values for key WATCH-cluster features ──")
    print(f"\n{'symbol':<14}{'wlf':<5}{'ema_align':<12}"
          f"{'coiled_score':>14}{'ema20_dist':>12}{'mkt_breadth':>13}")
    print("─" * 70)
    for _, r in df.sort_values(["wlf", "symbol"]).iterrows():
        cs = r.get("feat_coiled_spring_score")
        cs_str = f"{cs:.1f}" if pd.notna(cs) else "—"
        ed = r.get("feat_ema20_distance_pct")
        ed_str = f"{ed:.4f}" if pd.notna(ed) else "—"
        mb = r.get("feat_market_breadth_pct")
        mb_str = f"{mb:.3f}" if pd.notna(mb) else "—"
        marker = "★" if r["wlf"] == "W" else " "
        print(f"{marker}{r['symbol']:<13}{r['wlf']:<5}"
              f"{str(r.get('feat_ema_alignment','—')):<12}"
              f"{cs_str:>14}{ed_str:>12}{mb_str:>13}")

    # ── Candidate filters ────────────────────────────────────────────
    candidates = [
        {
            "name": "F1: WATCH-cluster signature (coiled=medium AND ema=bull)",
            "required": [("coiled_spring_score", "medium"),
                            ("ema_alignment", "bull")],
            "forbidden": [],
        },
        {
            "name": "F2: ema_alignment=bull (single feature, tested in UP_TRI cell)",
            "required": [("ema_alignment", "bull")],
            "forbidden": [],
        },
        {
            "name": "F3: REJECT cluster KILL (forbid extended momentum)",
            "required": [],
            "forbidden": [("ema20_distance_pct", "high"),
                             ("market_breadth_pct", "high")],
        },
        {
            "name": "F4: WATCH signature + KILL anti-features",
            "required": [("coiled_spring_score", "medium"),
                            ("ema_alignment", "bull")],
            "forbidden": [("ema20_distance_pct", "high")],
        },
        {
            "name": "F5: Single anti — forbid market_breadth_pct=high",
            "required": [],
            "forbidden": [("market_breadth_pct", "high")],
        },
    ]

    results = []
    print()
    for cand in candidates:
        result = evaluate_filter(df, cand["name"], cand["required"],
                                      cand["forbidden"], spec_by_id, bounds_cache)
        results.append(result)
        m_wr = (f"{result['matched_wr']*100:.1f}%"
                  if result["matched_wr"] is not None else "—")
        s_wr = (f"{result['skipped_wr']*100:.1f}%"
                  if result["skipped_wr"] is not None else "—")
        lift = ((result["matched_wr"] - baseline_wr) * 100
                  if result["matched_wr"] is not None else 0.0)
        print(f"\n{cand['name']}")
        print(f"  matched: {result['n_matched']} signals "
              f"(W={result['n_matched_w']}, L={result['n_matched_l']}) "
              f"→ WR={m_wr}  (lift {lift:+.1f}pp)")
        print(f"  skipped: {result['n_skipped']} signals "
              f"(W={result['n_skipped_w']}, L={result['n_skipped_l']}) "
              f"→ WR={s_wr}")

    # ── Verdict ──────────────────────────────────────────────────────
    print()
    print("═" * 80)
    print("VERDICT")
    print("═" * 80)
    # Live n=8 is small. Look for any filter where matched_wr ≥ 50% with
    # at least 2 matched W+L
    qualifying = [r for r in results
                    if r["matched_wr"] is not None
                    and r["matched_wr"] >= 0.50
                    and (r["n_matched_w"] + r["n_matched_l"]) >= 2]
    if qualifying:
        best = max(qualifying, key=lambda r: r["matched_wr"]
                       * (r["n_matched_w"] + r["n_matched_l"]))
        print(f"\nBest filter (n_wl ≥ 2, WR ≥ 50%): {best['name']}")
        print(f"  matched WR: {best['matched_wr']*100:.1f}%")
        print(f"  match rate: {best['match_rate']*100:.1f}%")
        print(f"  lift over baseline: "
              f"{(best['matched_wr']-baseline_wr)*100:+.1f}pp")
    else:
        print("\nNo filter clears 50% WR with ≥2 matched W+L.")
        print("All 6 losers + 2 winners distribute across filter conditions.")
        print("CELL VERDICT: CONFIRMED DEAD or NEAR-DEAD in Choppy regime.")
        print("  Production action: REJECT all Choppy BULL_PROXY signals.")
        print("  Re-evaluate when live n grows ≥30 with at least 5 winners.")

    out = {
        "baseline_universe": {
            "n": int(n), "n_w": int(nw), "n_l": int(nl), "n_f": int(nf),
            "baseline_wr": baseline_wr,
        },
        "candidate_filters": results,
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
