"""
Choppy regime — L2: cell findings validation (consolidated).

Reads prior validation outputs (V1, V2, V3 from lab/factory/) and produces
a unified summary under lab/factory/choppy/lifetime/cell_validation.json.

This module does NOT recompute (V1/V2/V3 already produced lifetime evidence
at commits d59989de / 0fa7aa5c / 07101d27). It consolidates verdicts for
the L5 synthesis.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent

V1_PATH = (_LAB_ROOT / "factory" / "choppy_uptri"
              / "lifetime_validation.json")
V2_PATH = (_LAB_ROOT / "factory" / "choppy"
              / "universal_antifeatures_validation.json")
V3_PATH = (_LAB_ROOT / "factory" / "choppy_bullproxy"
              / "lifetime_reinvestigation.json")

OUTPUT_PATH = _HERE / "cell_validation.json"


def main():
    print("─" * 80)
    print("L2: Choppy cell findings validation (consolidated)")
    print("─" * 80)

    summary = {
        "v1_F1_lifetime": None,
        "v2_anti_features_lifetime": None,
        "v3_bullproxy_kill_lifetime": None,
        "verdicts": {},
    }

    # V1: F1 / F4 filter validation
    if V1_PATH.exists():
        v1 = json.loads(V1_PATH.read_text())
        summary["v1_F1_lifetime"] = v1
        f1 = v1.get("lifetime_F1", {})
        f4 = v1.get("lifetime_F4", {})
        live_f1 = v1.get("live_comparison", {}).get("live_F1_wr", 0)
        live_f4 = v1.get("live_comparison", {}).get("live_F4_wr", 0)
        baseline = v1.get("lifetime_baseline", {}).get("wr", 0)
        f1_lift = (f1.get("matched_wr", 0) or 0) - baseline
        f4_lift = (f4.get("matched_wr", 0) or 0) - baseline
        live_lift_f1 = live_f1 - 0.349  # live baseline
        live_lift_f4 = live_f4 - 0.349
        print(f"\n── V1: UP_TRI F1 / F4 filters ──")
        print(f"  F1 live: {live_f1*100:.1f}% WR, +{live_lift_f1*100:.1f}pp lift")
        print(f"  F1 lifetime: {(f1.get('matched_wr',0) or 0)*100:.1f}% WR, "
              f"{f1_lift*100:+.1f}pp lift over {baseline*100:.1f}% baseline")
        print(f"  F1 verdict: {f1.get('verdict','—')}")
        print(f"  F4 live: {live_f4*100:.1f}% WR, +{live_lift_f4*100:.1f}pp lift")
        print(f"  F4 lifetime: {(f4.get('matched_wr',0) or 0)*100:.1f}% WR, "
              f"{f4_lift*100:+.1f}pp lift")
        print(f"  F4 verdict: {f4.get('verdict','—')}")
        summary["verdicts"]["F1"] = {
            "lift_live_pp": live_lift_f1, "lift_lifetime_pp": f1_lift,
            "delta_pp": (live_lift_f1 - f1_lift),
            "production_status": "WEAKENED — regime-shift adaptive only",
        }
        summary["verdicts"]["F4"] = {
            "lift_live_pp": live_lift_f4, "lift_lifetime_pp": f4_lift,
            "delta_pp": (live_lift_f4 - f4_lift),
            "production_status": "WEAKENED — same regime-shift dependency",
        }
    else:
        print(f"⚠ V1 output missing: {V1_PATH}")

    # V2: universal anti-features
    if V2_PATH.exists():
        v2 = json.loads(V2_PATH.read_text())
        summary["v2_anti_features_lifetime"] = v2
        print(f"\n── V2: Universal anti-features ──")
        n_confirmed = 0; n_weak = 0; n_refuted = 0
        for r in v2.get("anti_features", []):
            verdict = r.get("verdict", "")
            disc = r.get("discrimination_pp")
            disc_str = f"{disc*100:+.1f}pp" if disc is not None else "—"
            print(f"  {r['feature_id']}={r['level']:<10} "
                  f"disc={disc_str:>10}  {verdict}")
            if verdict.startswith("CONFIRMED"):
                n_confirmed += 1
            elif verdict.startswith("WEAK"):
                n_weak += 1
            elif verdict.startswith("REFUTED"):
                n_refuted += 1
        summary["verdicts"]["universal_anti_features"] = {
            "n_confirmed": n_confirmed, "n_weak": n_weak,
            "n_refuted": n_refuted,
            "production_status": (
                "REFUTED — do NOT use as universal kill conditions"
                if n_refuted >= 3 else
                "PARTIAL — use selectively"),
        }
    else:
        print(f"⚠ V2 output missing: {V2_PATH}")

    # V3: BULL_PROXY KILL verdict
    if V3_PATH.exists():
        v3 = json.loads(V3_PATH.read_text())
        summary["v3_bullproxy_kill_lifetime"] = v3
        print(f"\n── V3: BULL_PROXY KILL verdict ──")
        verdict = v3.get("overall_verdict")
        print(f"  Overall verdict: {verdict}")
        promising = v3.get("promising_filters", [])
        print(f"  Promising filters at lifetime (≥+10pp lift, n≥50): "
              f"{len(promising)}")
        if promising:
            for p in promising[:3]:
                print(f"    {p['name']}: lift={p.get('matched_wr',0)*100:.1f}%, "
                      f"n={p.get('n_matched_wl', 0)}")
        # Best lift filter (even if not "promising" by ≥10pp)
        best = max(v3.get("filters_tested", []),
                      key=lambda r: ((r.get("matched_wr") or 0)
                                        - v3["lifetime_universe"]["baseline_wr"]),
                      default=None)
        if best and best.get("matched_wr"):
            lift = best["matched_wr"] - v3["lifetime_universe"]["baseline_wr"]
            print(f"  Best filter (even below threshold): {best['name']}")
            print(f"    n={best['n_matched']}, WR={best['matched_wr']*100:.1f}%, "
                  f"lift={lift*100:+.1f}pp")
        summary["verdicts"]["bullproxy_kill"] = {
            "verdict": verdict,
            "production_status": (
                "KILL CONFIRMED — REJECT all Choppy BULL_PROXY signals"
                if verdict == "KILL_CONFIRMED" else "REVISE"),
        }
    else:
        print(f"⚠ V3 output missing: {V3_PATH}")

    # Overall
    print()
    print("═" * 80)
    print("L2 CONSOLIDATED VERDICTS")
    print("═" * 80)
    print()
    for finding, v in summary["verdicts"].items():
        print(f"  {finding}:")
        if "production_status" in v:
            print(f"    {v['production_status']}")
        if "delta_pp" in v:
            print(f"    delta_pp (live − lifetime): {v['delta_pp']*100:+.1f}pp")

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
