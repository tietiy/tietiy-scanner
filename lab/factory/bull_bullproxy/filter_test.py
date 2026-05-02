"""
Bull BULL_PROXY cell — BP3: verdict articulation + filter back-test.

Tests 5 candidate verdict structures:
  A. healthy_bull + 20d=high (best practical filter from BP2)
  B. healthy_bull alone (sub-regime gating only)
  C. wk4 alone (universal calendar)
  D. wk4 + healthy_bull (combined)
  E. DEFERRED unfiltered

Saves: lab/factory/bull_bullproxy/filter_test_results.json
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

_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bp3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bp3", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bp3"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "filter_test_results.json"


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _wr(grp: pd.DataFrame) -> dict:
    nw = int((grp["wlf"] == "W").sum())
    nl = int((grp["wlf"] == "L").sum())
    n_wl = nw + nl
    return {"n": len(grp), "n_w": nw, "n_l": nl, "n_wl": n_wl,
            "wr": (nw / n_wl) if n_wl > 0 else None}


def main():
    print("─" * 80)
    print("BP3: Bull BULL_PROXY verdict articulation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bp = df[(df["regime"] == "Bull") & (df["signal"] == "BULL_PROXY")].copy()
    bp["wlf"] = bp["outcome"].apply(_wlf)
    lt = bp[bp["wlf"].isin(["W", "L", "F"])].copy()
    baseline_wr = _wr(lt)["wr"]
    print(f"\nLifetime: n={len(lt)}, baseline {baseline_wr*100:.1f}%")

    lt["sub"] = lt.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    n20_spec = spec_by_id["nifty_20d_return_pct"]

    # Verdict A: healthy_bull + 20d=high
    a_mask_sub = lt["sub"] == "healthy_bull"
    a_mask_n20 = lt["feat_nifty_20d_return_pct"].apply(
        lambda v: matches_level(n20_spec, v, "high", bounds_cache)
    ).fillna(False)
    a_match = lt[a_mask_sub & a_mask_n20]
    a_wr = _wr(a_match)

    # Verdict B: healthy_bull alone
    b_match = lt[lt["sub"] == "healthy_bull"]
    b_wr = _wr(b_match)

    # Verdict C: wk4 alone
    c_match = lt[lt["feat_day_of_month_bucket"] == "wk4"]
    c_wr = _wr(c_match)

    # Verdict D: wk4 + healthy_bull
    d_match = lt[(lt["sub"] == "healthy_bull")
                  & (lt["feat_day_of_month_bucket"] == "wk4")]
    d_wr = _wr(d_match)

    # Verdict E: recovery_bull alone (strongest single sub-regime)
    e_match = lt[lt["sub"] == "recovery_bull"]
    e_wr = _wr(e_match)

    # Verdict F: DEFERRED unfiltered
    f_wr = _wr(lt)

    candidates = [
        {"name": "Verdict A — healthy_bull × nifty_20d=high",
         "wr_info": a_wr},
        {"name": "Verdict B — healthy_bull alone (sub-regime gating)",
         "wr_info": b_wr},
        {"name": "Verdict C — wk4 alone (universal calendar)",
         "wr_info": c_wr},
        {"name": "Verdict D — wk4 × healthy_bull",
         "wr_info": d_wr},
        {"name": "Verdict E — recovery_bull alone",
         "wr_info": e_wr},
        {"name": "Verdict F — DEFERRED unfiltered baseline",
         "wr_info": f_wr},
    ]

    out = {
        "lifetime_baseline_wr": float(baseline_wr),
        "candidates": [],
    }

    print(f"\n══ Candidate verdict evaluation ══\n")
    for c in candidates:
        wr_info = c["wr_info"]
        n = wr_info["n_wl"]
        wr = wr_info["wr"]
        match_rate = wr_info["n"] / len(lt)
        lift = (wr - baseline_wr) * 100 if wr is not None else None

        print(f"{c['name']}")
        print(f"  matches: {n} ({match_rate*100:.1f}%) of {len(lt)} lifetime")
        if wr is not None:
            print(f"  matched WR: {wr*100:.1f}%, "
                  f"lift over baseline: {lift:+.1f}pp")
        print()

        out["candidates"].append({
            "name": c["name"],
            "n_match": int(n),
            "match_rate": float(match_rate),
            "matched_wr": float(wr) if wr is not None else None,
            "lift_pp": float(lift) if lift is not None else None,
        })

    # Recommendation
    print("═" * 80)
    print("RECOMMENDATION")
    print("═" * 80)

    A = out["candidates"][0]
    B = out["candidates"][1]
    D = out["candidates"][3]

    final_verdict = None
    rationale = []

    # Prefer high-precision Verdict A if n >= 100 and lift >= +5pp
    if (A["matched_wr"] is not None and A["matched_wr"] >= 0.55
            and A["lift_pp"] >= 5 and A["n_match"] >= 100):
        final_verdict = "DEFERRED with provisional Verdict A (healthy_bull × 20d=high)"
        rationale.append(
            f"Verdict A: n={A['n_match']}, WR={A['matched_wr']*100:.1f}%, "
            f"lift={A['lift_pp']:+.1f}pp")
        rationale.append(
            "Verdict A combines sub-regime gating (healthy_bull) + universal "
            "Bull bullish anchor (20d_return=high). Robust evidence across "
            "Bull bullish cells.")
        rationale.append(
            "DEFERRED because no live validation possible (0 Bull live signals). "
            "Production: SKIP default; manual enable.")
    elif B["matched_wr"] is not None and B["matched_wr"] >= 0.52:
        final_verdict = "DEFERRED with provisional Verdict B (healthy_bull alone)"
        rationale.append(
            f"Verdict B: n={B['n_match']}, WR={B['matched_wr']*100:.1f}%, "
            f"lift={B['lift_pp']:+.1f}pp")
        rationale.append(
            "Sub-regime gating alone provides modest edge; Verdict A's "
            "feature combination too narrow.")
    else:
        final_verdict = "DEFERRED unfiltered"
        rationale.append("No filter clears practical threshold.")

    print(f"\nFINAL VERDICT: {final_verdict}")
    for r_line in rationale:
        print(f"  • {r_line}")

    out["final_verdict"] = final_verdict
    out["rationale"] = rationale
    out["production_action"] = (
        "Default SKIP. Manual enable for healthy_bull × nifty_20d=high "
        "filter (~62.5% lifetime WR, +11.4pp lift). Activation requires "
        "Bull regime active + ≥30 live Bull BULL_PROXY signals + "
        "matched-WR ≥ 50%."
    )
    out["session_2_recommendation"] = (
        "DO NOT proceed. Lifetime-only methodology exhausted in BP2-BP3. "
        "Bull regime cell trio complete; synthesis is next natural step."
    )

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
