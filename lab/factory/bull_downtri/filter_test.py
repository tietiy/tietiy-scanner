"""
Bull DOWN_TRI cell — BD3: verdict articulation + filter back-test.

Tests 5 candidate verdict structures against lifetime cohort:
  A. late_bull only (sub-regime gating)
  B. late_bull × wk3 (highest precision per BD2)
  C. wk3 alone (universal, no sub-regime gating)
  D. KILL (skip all)
  E. DEFERRED baseline (no filter)

Saves: lab/factory/bull_downtri/filter_test_results.json
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
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bd3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bd3", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bd3"] = _detector_mod
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
    return {
        "n": len(grp), "n_w": nw, "n_l": nl,
        "n_wl": n_wl,
        "wr": (nw / n_wl) if n_wl > 0 else None,
    }


def main():
    print("─" * 80)
    print("BD3: Bull DOWN_TRI verdict articulation + filter back-test")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bd = df[(df["regime"] == "Bull") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    lt = bd[bd["wlf"].isin(["W", "L", "F"])].copy()
    baseline_wr = _wr(lt)["wr"]
    print(f"\nLifetime: n={len(lt)}, baseline {baseline_wr*100:.1f}%")

    # Apply Bull sub-regime detector
    lt["sub"] = lt.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    candidates = []

    # Verdict A: late_bull only
    a_match = lt[lt["sub"] == "late_bull"]
    a_wr = _wr(a_match)
    candidates.append({
        "name": "Verdict A — late_bull sub-regime only",
        "n_match": int(a_wr["n_wl"]),
        "n_input": int(len(lt)),
        "match_rate": float(a_wr["n"] / len(lt)),
        "matched_wr": float(a_wr["wr"]) if a_wr["wr"] else None,
        "lift_pp": float((a_wr["wr"] - baseline_wr) * 100) if a_wr["wr"] else None,
    })

    # Verdict B: late_bull × wk3
    b_match = lt[(lt["sub"] == "late_bull")
                  & (lt["feat_day_of_month_bucket"] == "wk3")]
    b_wr = _wr(b_match)
    candidates.append({
        "name": "Verdict B — late_bull × wk3 (highest precision)",
        "n_match": int(b_wr["n_wl"]),
        "n_input": int(len(lt)),
        "match_rate": float(b_wr["n"] / len(lt)),
        "matched_wr": float(b_wr["wr"]) if b_wr["wr"] else None,
        "lift_pp": float((b_wr["wr"] - baseline_wr) * 100) if b_wr["wr"] else None,
    })

    # Verdict C: wk3 alone (universal)
    c_match = lt[lt["feat_day_of_month_bucket"] == "wk3"]
    c_wr = _wr(c_match)
    candidates.append({
        "name": "Verdict C — wk3 alone (universal, no sub-regime)",
        "n_match": int(c_wr["n_wl"]),
        "n_input": int(len(lt)),
        "match_rate": float(c_wr["n"] / len(lt)),
        "matched_wr": float(c_wr["wr"]) if c_wr["wr"] else None,
        "lift_pp": float((c_wr["wr"] - baseline_wr) * 100) if c_wr["wr"] else None,
    })

    # Verdict D: KILL (reject all)
    candidates.append({
        "name": "Verdict D — KILL (reject all Bull DOWN_TRI)",
        "n_match": 0,
        "n_input": int(len(lt)),
        "match_rate": 0.0,
        "matched_wr": None,
        "lift_pp": None,
    })

    # Verdict E: DEFERRED no filter
    e_match = lt
    e_wr = _wr(e_match)
    candidates.append({
        "name": "Verdict E — DEFERRED unfiltered baseline",
        "n_match": int(e_wr["n_wl"]),
        "n_input": int(len(lt)),
        "match_rate": 1.0,
        "matched_wr": float(e_wr["wr"]) if e_wr["wr"] else None,
        "lift_pp": 0.0,
    })

    # Surface
    print()
    print("═" * 80)
    print("Candidate verdict evaluation (lifetime data)")
    print("═" * 80)
    for c in candidates:
        print(f"\n{c['name']}")
        print(f"  matches: {c['n_match']} ({c['match_rate']*100:.1f}%) of "
              f"{c['n_input']} lifetime")
        if c["matched_wr"] is not None:
            print(f"  matched WR: {c['matched_wr']*100:.1f}%, "
                  f"lift over baseline: {c['lift_pp']:+.1f}pp")
        else:
            print(f"  (no matches)")

    # Recommendation
    print()
    print("═" * 80)
    print("RECOMMENDATION")
    print("═" * 80)

    A = candidates[0]
    B = candidates[1]
    C = candidates[2]

    # Decision logic — favor B if precision and meaningful sample, else A
    if (B["matched_wr"] is not None
            and B["matched_wr"] >= 0.55
            and B["n_match"] >= 200):
        verdict = "DEFERRED with provisional Verdict B (late_bull × wk3)"
        rationale = [
            f"Verdict B lifetime: n={B['n_match']}, "
            f"WR={B['matched_wr']*100:.1f}%, lift={B['lift_pp']:+.1f}pp",
            "Strongest Bull DOWN_TRI configuration in lifetime data.",
            "DEFERRED because no live validation possible (0 Bull live signals).",
            "Production: SKIP default; manual enable for late_bull × wk3.",
        ]
    elif A["matched_wr"] is not None and A["matched_wr"] >= 0.50:
        verdict = "DEFERRED with provisional Verdict A (late_bull sub-regime)"
        rationale = [
            f"Verdict A lifetime: n={A['n_match']}, "
            f"WR={A['matched_wr']*100:.1f}%, lift={A['lift_pp']:+.1f}pp",
            "Sub-regime gating gives positive WR; broader than B.",
            "Production: SKIP default; manual enable for late_bull.",
        ]
    else:
        verdict = "DEFERRED (no filter clears 50% threshold)"
        rationale = ["No verdict candidate produces meaningful edge."]

    print(f"\nFINAL VERDICT: {verdict}")
    for r_line in rationale:
        print(f"  • {r_line}")

    out = {
        "lifetime_baseline_wr": float(baseline_wr),
        "candidates": candidates,
        "final_verdict": verdict,
        "rationale": rationale,
        "production_action": (
            "Default SKIP. Manual enable for late_bull sub-regime + wk3 "
            "calendar match (provisional ~70% WR per lifetime). "
            "Activation requires Bull regime present + ≥30 live Bull "
            "DOWN_TRI signals + matched-WR ≥ 50%."
        ),
        "session_2_recommendation": (
            "DO NOT proceed to Session 2. Cell is lifetime-only methodology;"
            " no Phase 5 to validate; lifetime data exhausted in BD2-BD3. "
            "Re-evaluate when Bull regime returns + live signals accumulate."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
