"""
Bear DOWN_TRI cell — D3: verdict articulation + filter back-test.

Three candidate verdicts considered:
  A. FILTER candidate (wk2/wk3 timing) — from D2 lifetime differentials
  B. FILTER candidate strict (wk2/wk3 + vol=High + HHs intact)
  C. KILL extension (kill_001 → +Auto, Energy, Metal sectors)

Tests each against:
  • Lifetime cohort (n=3,640) — primary statistical evidence
  • Live cohort (n=11) — extreme thinness, treated as anecdotal

Surfaces explicit verdict recommendation: FILTER / KILL / DEFERRED.

Saves: lab/factory/bear_downtri/filter_test_results.json
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402

_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_d3", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

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
    nf = int((grp["wlf"] == "F").sum())
    n_wl = nw + nl
    return {
        "n": len(grp), "n_w": nw, "n_l": nl, "n_f": nf,
        "n_wl": n_wl,
        "wr": (nw / n_wl) if n_wl > 0 else None,
    }


def evaluate_on_cohort(df: pd.DataFrame, name: str,
                          required_eqs: list[tuple[str, str, str]],
                          required_levels: list[tuple[str, str]],
                          forbidden_levels: list[tuple[str, str]],
                          forbidden_sectors: list[str],
                          spec_by_id: dict,
                          bounds_cache: dict,
                          cohort_label: str) -> dict:
    """Apply rule (mix of categorical eqs, level matches, sector excludes).

    required_eqs: list of (column, ==value, label) for non-feature columns
    required_levels: list of (feature_id, level) — feature must match
    forbidden_levels: list of (feature_id, level) — feature must NOT match
    forbidden_sectors: list of sector names to skip
    """
    n = len(df)
    if n == 0:
        return {"name": name, "cohort": cohort_label, "n_input": 0}

    mask = pd.Series([True] * n, index=df.index)

    for col, val, _ in required_eqs:
        if col in df.columns:
            mask = mask & (df[col].astype(str) == str(val))

    for fid, lvl in required_levels:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue
        m = df[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache)).fillna(False)
        mask = mask & m

    for fid, lvl in forbidden_levels:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = f"feat_{fid}"
        if col not in df.columns:
            continue
        m = df[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache)).fillna(False)
        mask = mask & ~m

    if forbidden_sectors:
        mask = mask & ~df["sector"].isin(forbidden_sectors)

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
    print("CELL: Bear DOWN_TRI — D3 verdict articulation + filter back-test")
    print("─" * 80)

    # Lifetime cohort
    df = pd.read_parquet(ENRICHED_PATH)
    bd = df[(df["regime"] == "Bear") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    lt = bd[bd["wlf"].isin(["W", "L", "F"])].copy()

    # Live cohort
    live = pd.read_parquet(LIVE_FEATURES_PATH)
    lv = live[(live["regime"] == "Bear") & (live["signal"] == "DOWN_TRI")].copy()
    lv["wlf"] = lv["outcome"].apply(_wlf)

    print(f"\nLifetime cohort: n={len(lt)}, "
          f"baseline WR={(_wr(lt)['wr'] or 0)*100:.1f}%")
    print(f"Live cohort: n={len(lv)}, "
          f"baseline WR={(_wr(lv)['wr'] or 0)*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # ── Candidate verdicts ───────────────────────────────────────────
    candidates = [
        {
            "name": "Verdict A — FILTER: wk2/wk3 timing",
            "required_eqs": [],
            "required_levels": [],
            "forbidden_levels": [
                ("day_of_month_bucket", "wk1"),
                ("day_of_month_bucket", "wk4"),
            ],
            "forbidden_sectors": ["Bank"],  # kill_001
        },
        {
            "name": "Verdict B — FILTER: wk2/wk3 + High vol + HHs intact",
            "required_eqs": [],
            "required_levels": [
                ("nifty_vol_regime", "High"),
                ("higher_highs_intact_flag", "True"),
            ],
            "forbidden_levels": [
                ("day_of_month_bucket", "wk1"),
                ("day_of_month_bucket", "wk4"),
            ],
            "forbidden_sectors": ["Bank"],
        },
        {
            "name": "Verdict C — KILL extension: kill Bank+Auto+Energy+Metal",
            "required_eqs": [],
            "required_levels": [],
            "forbidden_levels": [],
            "forbidden_sectors": ["Bank", "Auto", "Energy", "Metal"],
        },
        {
            "name": "Verdict D — DEFERRED baseline (kill_001 only)",
            "required_eqs": [],
            "required_levels": [],
            "forbidden_levels": [],
            "forbidden_sectors": ["Bank"],
        },
    ]

    results = []
    for cand in candidates:
        # On lifetime
        lt_res = evaluate_on_cohort(
            lt, cand["name"], cand["required_eqs"],
            cand["required_levels"], cand["forbidden_levels"],
            cand["forbidden_sectors"], spec_by_id, bounds_cache,
            cohort_label="lifetime")
        # On live
        lv_res = evaluate_on_cohort(
            lv, cand["name"], cand["required_eqs"],
            cand["required_levels"], cand["forbidden_levels"],
            cand["forbidden_sectors"], spec_by_id, bounds_cache,
            cohort_label="live")
        results.append({
            "name": cand["name"],
            "lifetime": lt_res,
            "live": lv_res,
        })

    # ── Surface results ─────────────────────────────────────────────
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
            mwr = (x.get("matched_wr") or 0) * 100 if x.get("matched_wr") else None
            swr = (x.get("skipped_wr") or 0) * 100 if x.get("skipped_wr") else None
            lift = x.get("lift_over_baseline_pp")
            mw, ml = x.get("match_W_L", (0, 0))
            sw, sl = x.get("skip_W_L", (0, 0))

            print(f"  {key:<10}: input={n_input}, match={n_match} "
                  f"({mr:.1f}%)")
            if mwr is not None:
                print(f"    matched: W={mw}, L={ml}, WR={mwr:.1f}%, "
                      f"lift={lift:+.1f}pp" if lift is not None
                      else f"    matched: W={mw}, L={ml}, WR={mwr:.1f}%")
            if swr is not None:
                print(f"    skipped: W={sw}, L={sl}, WR={swr:.1f}%")

    # ── Verdict synthesis ───────────────────────────────────────────
    print()
    print("═" * 80)
    print("VERDICT SYNTHESIS")
    print("═" * 80)

    A = next(r for r in results if "Verdict A" in r["name"])
    B = next(r for r in results if "Verdict B" in r["name"])
    C = next(r for r in results if "Verdict C" in r["name"])
    D = next(r for r in results if "Verdict D" in r["name"])

    A_lt_wr = A["lifetime"].get("matched_wr") or 0
    A_lt_lift = A["lifetime"].get("lift_over_baseline_pp") or 0
    A_lt_n = A["lifetime"].get("match_count") or 0
    A_lv_wr = A["live"].get("matched_wr") or 0
    A_lv_n = A["live"].get("match_count") or 0

    B_lt_wr = B["lifetime"].get("matched_wr") or 0
    B_lt_lift = B["lifetime"].get("lift_over_baseline_pp") or 0
    B_lt_n = B["lifetime"].get("match_count") or 0
    B_lv_n = B["live"].get("match_count") or 0

    C_lt_wr = C["lifetime"].get("matched_wr") or 0
    C_lt_lift = C["lifetime"].get("lift_over_baseline_pp") or 0
    C_lt_n = C["lifetime"].get("match_count") or 0
    C_lv_wr = C["live"].get("matched_wr") or 0

    print()
    print(f"  Verdict A (FILTER wk2/wk3 + Bank kill):")
    print(f"    lifetime: n={A_lt_n}, WR={A_lt_wr*100:.1f}%, "
          f"lift={A_lt_lift:+.1f}pp")
    print(f"    live:     n={A_lv_n}, WR={A_lv_wr*100:.1f}% "
          f"(thin: n<5)")

    print(f"\n  Verdict B (FILTER strict + Bank kill):")
    print(f"    lifetime: n={B_lt_n}, WR={B_lt_wr*100:.1f}%, "
          f"lift={B_lt_lift:+.1f}pp")
    print(f"    live:     n={B_lv_n} (likely too thin to meaningfully test)")

    print(f"\n  Verdict C (KILL extension Bank+Auto+Energy+Metal):")
    print(f"    lifetime: n={C_lt_n}, WR={C_lt_wr*100:.1f}%, "
          f"lift={C_lt_lift:+.1f}pp")
    print(f"    live: matched WR={C_lv_wr*100:.1f}%")

    # Final recommendation
    print()
    print("─" * 80)
    print("RECOMMENDATION")
    print("─" * 80)

    # Decision logic
    final_verdict = None
    rationale = []

    # If FILTER A has reasonable lift + sample size at lifetime
    if A_lt_lift >= 5 and A_lt_n >= 500:
        # And the live signals (1 of 11 not in Bank, not in wk1/wk4) are positive
        # We need to check live too...
        live_lift = ((A_lv_wr - 2/11) * 100) if A_lv_n > 0 else None
        if A_lv_n >= 5:
            # Real live evidence
            final_verdict = "FILTER (Verdict A)"
            rationale.append(
                f"Lifetime lift +{A_lt_lift:.1f}pp on n={A_lt_n} "
                f"(strong sample); live n={A_lv_n} matches.")
        else:
            # Lifetime-strong but live-thin → DEFERRED with provisional filter
            final_verdict = "DEFERRED with provisional Verdict A filter"
            rationale.append(
                f"Lifetime lift +{A_lt_lift:.1f}pp on n={A_lt_n} is "
                f"meaningful, but live matches n={A_lv_n} too thin to "
                f"validate.")
            rationale.append(
                "Production: maintain kill_001 (Bank exclusion); apply "
                "wk2/wk3 timing as PROVISIONAL filter; mark cell "
                "DEFERRED until 20+ more live signals accumulate.")
    else:
        final_verdict = "DEFERRED (kill_001 only)"
        rationale.append(
            "No filter shows meaningful lifetime lift + adequate sample.")

    print(f"\nFINAL VERDICT: {final_verdict}")
    for r_line in rationale:
        print(f"  • {r_line}")

    # Save
    out = {
        "lifetime_baseline_wr": (_wr(lt).get("wr")),
        "live_baseline_wr": (_wr(lv).get("wr")),
        "candidates": results,
        "final_verdict": final_verdict,
        "rationale": rationale,
        "production_action": (
            "Maintain kill_001 (Bank exclusion). Apply wk2/wk3 timing as "
            "PROVISIONAL FILTER for non-Bank Bear DOWN_TRI signals. Cell "
            "marked DEFERRED until ≥20 additional live signals accumulate "
            "with ≥50% matched WR under the wk2/wk3 + Bank-exclusion rule."
            if "DEFERRED" in final_verdict else
            "Deploy filter rules per recommended verdict."
        ),
        "session_2_recommendation": (
            "DO NOT proceed to Session 2 (lifetime validation). The cell "
            "lacks Phase 5 winners to validate, and live data is too thin "
            "to support filter back-test. Re-evaluate at quarterly "
            "Phase 5 re-run (estimated 6-12 months for sufficient live "
            "samples to accumulate)."
            if "DEFERRED" in final_verdict else
            "Proceed to Session 2 lifetime validation."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
