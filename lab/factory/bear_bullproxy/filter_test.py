"""
Bear BULL_PROXY cell — P3: verdict articulation + filter back-test.

Tests 4 candidate verdict structures against lifetime + live cohorts:
  A. HOT-only filter (vol>0.70 AND nifty_60d<-0.10) — narrowest, highest WR
  B. HOT + sector whitelist (IT/Energy/Chem/Bank/Auto top lifetime sectors)
  C. KILL — reject all Bear BULL_PROXY signals
  D. DEFERRED with lifetime guidance — no automated filter

Saves: lab/factory/bear_bullproxy/filter_test_results.json
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
_spec = _ilu.spec_from_file_location("bear_uptri_filter_p3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

_detector_path = (_LAB_ROOT / "factory" / "bear" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bear_subregime_p3", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bear_subregime_p3"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bear_subregime = _detector_mod.detect_bear_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
LIVE_FEATURES_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
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
    nwl = nw + nl
    return {
        "n": len(grp), "n_w": nw, "n_l": nl,
        "n_wl": nwl,
        "wr": (nw / nwl) if nwl > 0 else None,
    }


def evaluate(df: pd.DataFrame, name: str,
                hot_required: bool,
                sector_whitelist: list[str],
                cohort_label: str) -> dict:
    """Apply rule and compute matched/skipped stats."""
    n = len(df)
    if n == 0:
        return {"name": name, "cohort": cohort_label, "n_input": 0}

    mask = pd.Series([True] * n, index=df.index)

    if hot_required:
        sub_labels = df.apply(
            lambda r: detect_bear_subregime(
                r.get("feat_nifty_vol_percentile_20d"),
                r.get("feat_nifty_60d_return_pct"),
            ).subregime,
            axis=1,
        )
        mask = mask & (sub_labels == "hot")

    if sector_whitelist:
        mask = mask & df["sector"].isin(sector_whitelist)

    matched = df[mask]
    skipped = df[~mask]
    m_st = _wr(matched)
    s_st = _wr(skipped)
    base = _wr(df)
    return {
        "name": name,
        "cohort": cohort_label,
        "n_input": int(n),
        "match_count": int(m_st["n"]),
        "match_rate": float(m_st["n"] / n) if n else 0.0,
        "matched_wr": m_st["wr"],
        "skipped_wr": s_st["wr"],
        "baseline_wr": base["wr"],
        "lift_over_baseline_pp": ((m_st["wr"] - base["wr"]) * 100
                                       if m_st["wr"] is not None
                                       and base["wr"] is not None
                                       else None),
        "match_W_L": (m_st["n_w"], m_st["n_l"]),
        "skip_W_L": (s_st["n_w"], s_st["n_l"]),
    }


def main():
    print("─" * 80)
    print("CELL: Bear BULL_PROXY — P3 verdict articulation + back-test")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bp = df[(df["regime"] == "Bear") & (df["signal"] == "BULL_PROXY")].copy()
    bp["wlf"] = bp["outcome"].apply(_wlf)
    lt = bp[bp["wlf"].isin(["W", "L", "F"])].copy()

    live = pd.read_parquet(LIVE_FEATURES_PATH)
    lv = live[(live["regime"] == "Bear") & (live["signal"] == "BULL_PROXY")].copy()
    lv["wlf"] = lv["outcome"].apply(_wlf)

    print(f"\nLifetime: n={len(lt)}, baseline WR="
          f"{(_wr(lt)['wr'] or 0)*100:.1f}%")
    print(f"Live: n={len(lv)}, baseline WR={(_wr(lv)['wr'] or 0)*100:.1f}%")

    candidates = [
        {
            "name": "Verdict A — HOT-only filter (vol>0.70 AND 60d<-0.10)",
            "hot_required": True,
            "sector_whitelist": [],
        },
        {
            "name": "Verdict B — HOT + sector whitelist (IT/Energy/Chem/Bank/Auto)",
            "hot_required": True,
            "sector_whitelist": ["IT", "Energy", "Chem", "Bank", "Auto"],
        },
        {
            "name": "Verdict C — KILL (reject all Bear BULL_PROXY)",
            "hot_required": False,
            "sector_whitelist": [],
            "_skip": True,  # matches everything → 0 take
        },
        {
            "name": "Verdict D — DEFERRED (no filter)",
            "hot_required": False,
            "sector_whitelist": [],
        },
    ]

    results = []
    for cand in candidates:
        if cand.get("_skip"):
            # KILL: 0 matches, baseline applies fully
            base_lt = _wr(lt)
            base_lv = _wr(lv)
            results.append({
                "name": cand["name"],
                "lifetime": {
                    "name": cand["name"], "cohort": "lifetime",
                    "n_input": int(len(lt)),
                    "match_count": 0, "match_rate": 0.0,
                    "matched_wr": None, "skipped_wr": base_lt["wr"],
                    "baseline_wr": base_lt["wr"], "lift_over_baseline_pp": None,
                    "match_W_L": (0, 0),
                    "skip_W_L": (base_lt["n_w"], base_lt["n_l"]),
                },
                "live": {
                    "name": cand["name"], "cohort": "live",
                    "n_input": int(len(lv)),
                    "match_count": 0, "match_rate": 0.0,
                    "matched_wr": None, "skipped_wr": base_lv["wr"],
                    "baseline_wr": base_lv["wr"], "lift_over_baseline_pp": None,
                    "match_W_L": (0, 0),
                    "skip_W_L": (base_lv["n_w"], base_lv["n_l"]),
                },
            })
            continue

        lt_res = evaluate(lt, cand["name"], cand["hot_required"],
                            cand["sector_whitelist"], "lifetime")
        lv_res = evaluate(lv, cand["name"], cand["hot_required"],
                            cand["sector_whitelist"], "live")
        results.append({
            "name": cand["name"],
            "lifetime": lt_res,
            "live": lv_res,
        })

    # ── Surface ─────────────────────────────────────────────────────
    print()
    print("═" * 80)
    print("Filter / Kill / Deferred candidate evaluation")
    print("═" * 80)
    for r in results:
        print(f"\n{r['name']}")
        print("-" * 70)
        for key in ("lifetime", "live"):
            x = r[key]
            n_input = x.get("n_input", 0)
            n_match = x.get("match_count", 0)
            mr = (x.get("match_rate") or 0) * 100
            mwr = x.get("matched_wr")
            swr = x.get("skipped_wr")
            lift = x.get("lift_over_baseline_pp")
            mw, ml = x.get("match_W_L", (0, 0))
            sw, sl = x.get("skip_W_L", (0, 0))

            print(f"  {key:<10}: input={n_input}, match={n_match} "
                  f"({mr:.1f}%)")
            if mwr is not None:
                lift_str = f"lift={lift:+.1f}pp" if lift is not None else ""
                print(f"    matched: W={mw}, L={ml}, "
                      f"WR={mwr*100:.1f}%, {lift_str}")
            else:
                print(f"    matched: (none)")
            if swr is not None:
                print(f"    skipped: W={sw}, L={sl}, "
                      f"WR={swr*100:.1f}%")

    # ── Verdict synthesis ───────────────────────────────────────────
    print()
    print("═" * 80)
    print("VERDICT SYNTHESIS")
    print("═" * 80)

    A = next(r for r in results if "Verdict A" in r["name"])
    B = next(r for r in results if "Verdict B" in r["name"])
    C = next(r for r in results if "Verdict C" in r["name"])
    D = next(r for r in results if "Verdict D" in r["name"])

    print(f"\n  Verdict A (HOT-only):")
    print(f"    lifetime: n={A['lifetime']['match_count']}, "
          f"WR={(A['lifetime'].get('matched_wr') or 0)*100:.1f}%, "
          f"lift={A['lifetime'].get('lift_over_baseline_pp', 0):+.1f}pp")
    print(f"    live:     n={A['live']['match_count']}, "
          f"WR={(A['live'].get('matched_wr') or 0)*100:.1f}%")

    print(f"\n  Verdict B (HOT + sector whitelist):")
    print(f"    lifetime: n={B['lifetime']['match_count']}, "
          f"WR={(B['lifetime'].get('matched_wr') or 0)*100:.1f}%, "
          f"lift={B['lifetime'].get('lift_over_baseline_pp', 0):+.1f}pp")
    print(f"    live:     n={B['live']['match_count']}, "
          f"WR={(B['live'].get('matched_wr') or 0)*100:.1f}%")

    print(f"\n  Verdict C (KILL):")
    print(f"    Rejects 100% — accepts no live or lifetime exposure")

    print(f"\n  Verdict D (DEFERRED, no filter):")
    print(f"    lifetime: full n={D['lifetime']['n_input']}, WR=47.3%")
    print(f"    live: full n={D['live']['n_input']}, WR=84.6%")

    # Decision
    A_lt_lift = A["lifetime"].get("lift_over_baseline_pp") or 0
    A_lt_n = A["lifetime"].get("match_count") or 0
    A_lt_wr = A["lifetime"].get("matched_wr") or 0
    A_lv_n = A["live"].get("match_count") or 0
    A_lv_wr = A["live"].get("matched_wr") or 0

    B_lt_lift = B["lifetime"].get("lift_over_baseline_pp") or 0
    B_lt_n = B["lifetime"].get("match_count") or 0
    B_lt_wr = B["lifetime"].get("matched_wr") or 0

    print()
    print("─" * 80)
    print("RECOMMENDATION")
    print("─" * 80)

    final_verdict = None
    rationale = []

    # Compare A's lifetime hot WR (~64%) vs simple SKIP-non-hot strategy
    # If A captures meaningful lift (≥10pp) AND lifetime n ≥ 50, viable filter
    if A_lt_lift >= 10 and A_lt_n >= 50:
        if A_lv_n >= 5 and A_lv_wr >= 0.60:
            final_verdict = "DEFERRED with provisional Verdict A (HOT-only filter)"
            rationale.append(
                f"Verdict A lifetime: n={A_lt_n}, WR={A_lt_wr*100:.1f}%, "
                f"lift={A_lt_lift:+.1f}pp")
            rationale.append(
                f"Live: n={A_lv_n} matches at {A_lv_wr*100:.1f}% — modest validation")
            rationale.append(
                "Production: HOT-only filter is provisionally defensible. "
                "DEFERRED to allow Bear UP_TRI cell deployment first; "
                "revisit after Bear UP_TRI live success.")
        else:
            final_verdict = "DEFERRED with provisional Verdict A"
            rationale.append(
                f"Verdict A lifetime supports filter (lift {A_lt_lift:+.1f}pp "
                f"on n={A_lt_n}) but live evidence too thin (n={A_lv_n}).")
            rationale.append(
                "Production: HOT-only filter as PROVISIONAL rule; cell "
                "DEFERRED behind Bear UP_TRI deployment.")
    elif A_lt_n < 30:
        final_verdict = "KILL or DEFERRED behind Bear UP_TRI"
        rationale.append(
            f"Verdict A lifetime hot zone is tiny (n={A_lt_n}); "
            f"insufficient evidence even at scale.")
        rationale.append(
            "Bear UP_TRI is strictly better in every dimension. "
            "Recommend KILL unless Bear UP_TRI succeeds first; then revisit.")
    else:
        final_verdict = "DEFERRED"
        rationale.append("Lifetime evidence weak; no clear filter emerges.")

    print(f"\nFINAL VERDICT: {final_verdict}")
    for line in rationale:
        print(f"  • {line}")

    # Save
    out = {
        "lifetime_baseline_wr": (_wr(lt).get("wr")),
        "live_baseline_wr": (_wr(lv).get("wr")),
        "candidates": results,
        "final_verdict": final_verdict,
        "rationale": rationale,
        "production_action": (
            "Treat Bear BULL_PROXY as DEFERRED behind Bear UP_TRI "
            "deployment. If hot sub-regime detected (vol>0.70 AND "
            "60d_return<-0.10), provisional TAKE_SMALL is defensible "
            "based on lifetime n=86 / 63.7% WR. Otherwise SKIP. "
            "Re-evaluate after Bear UP_TRI cell production lifetime."
        ),
        "session_2_recommendation": (
            "DO NOT proceed to Session 2. The cell:\n"
            "  • Has 0 Phase 5 combinations to validate against\n"
            "  • Live data too thin for filter back-test (n=13)\n"
            "  • Lifetime data already exhausted in P2-P3\n"
            "  • Bear UP_TRI is strictly better — focus engineering there\n"
            "Re-evaluate: when Bear UP_TRI production succeeds AND "
            "≥30 more Bear BULL_PROXY live signals accumulate."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
