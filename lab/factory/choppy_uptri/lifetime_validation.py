"""
Choppy UP_TRI cell — V1 lifetime validation.

Apply F1 (ema_alignment=bull AND coiled_spring_score=medium) and F4 (F1 + no
falling MACD + no HHs intact) filters to the full 27,260 lifetime UP_TRI ×
Choppy signals from enriched_signals.parquet.

Compare matched WR + lift to live finding:
  Live F1: matched 20/91 (22%), 58% WR, +23pp over 35% baseline
  Live F4: matched 6/91 (7%), 67% WR, +32pp over 35% baseline

Lifetime baseline for UP_TRI × Choppy is ~52% — so lift in absolute pp will
be smaller, but matched WR should remain elevated above 60% if filter
generalizes.

Verdict thresholds (per task spec):
  CONFIRMED: matched WR within 5pp of live (i.e., 53-63% lifetime if live=58%)
  WEAKENED: matched WR 5-15pp below live (43-53% lifetime)
  DISAGREES: matched WR >15pp below live, or below baseline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse choppy_uptri/filter_test.py helpers via importlib
import importlib.util as _ilu
_filter_path = _HERE / "filter_test.py"
_spec = _ilu.spec_from_file_location("uptri_filter_v", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level
apply_filter = _filter_mod.apply_filter

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "lifetime_validation.json"

# Live findings to compare against
LIVE_F1_WR = 0.579
LIVE_F1_LIFT = 0.230
LIVE_F4_WR = 0.667
LIVE_F4_LIFT = 0.317


def _wlf_lifetime(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def evaluate_lifetime(df: pd.DataFrame, name: str,
                          required: list, forbidden: list,
                          spec_by_id: dict, bounds_cache: dict) -> dict:
    mask = apply_filter(df, required, forbidden, spec_by_id, bounds_cache)
    matched = df[mask]; skipped = df[~mask]

    def _wr(grp):
        nw = (grp["wlf"] == "W").sum()
        nl = (grp["wlf"] == "L").sum()
        return (nw / (nw + nl)) if (nw + nl) > 0 else None, int(nw), int(nl)

    m_wr, m_w, m_l = _wr(matched)
    s_wr, s_w, s_l = _wr(skipped)
    return {
        "name": name,
        "n_total": len(df),
        "n_matched": len(matched),
        "n_matched_w": m_w, "n_matched_l": m_l,
        "matched_wr": float(m_wr) if m_wr is not None else None,
        "match_rate": len(matched) / len(df) if len(df) > 0 else 0.0,
        "n_skipped": len(skipped),
        "n_skipped_w": s_w, "n_skipped_l": s_l,
        "skipped_wr": float(s_wr) if s_wr is not None else None,
    }


def _verdict(lifetime_wr: float, live_wr: float, baseline_wr: float) -> str:
    """Classify lifetime/live agreement."""
    if lifetime_wr is None:
        return "INSUFFICIENT_DATA"
    if lifetime_wr < baseline_wr:
        return "DISAGREES (lifetime below baseline)"
    diff_to_live = abs(lifetime_wr - live_wr)
    if diff_to_live <= 0.05:
        return "CONFIRMED (within 5pp)"
    elif diff_to_live <= 0.15:
        return "WEAKENED (5-15pp lower than live)"
    else:
        return "DISAGREES (>15pp difference)"


def main():
    print("─" * 80)
    print("CELL: Choppy UP_TRI — V1 lifetime validation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    sub = df[(df["signal"] == "UP_TRI") & (df["regime"] == "Choppy")].copy()
    sub["wlf"] = sub["outcome"].apply(_wlf_lifetime)
    sub = sub[sub["wlf"].isin(["W", "L", "F"])].copy()

    n = len(sub)
    nw = (sub["wlf"] == "W").sum()
    nl = (sub["wlf"] == "L").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLifetime UP_TRI × Choppy: n={n} (W={nw}, L={nl}, F={(sub['wlf']=='F').sum()})")
    print(f"Lifetime baseline WR (excl F): {baseline_wr*100:.1f}%")
    print(f"Live baseline (for comparison): 34.9%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # Filter F1
    f1 = evaluate_lifetime(
        sub, "F1: ema_bull AND coiled=medium",
        [("ema_alignment", "bull"), ("coiled_spring_score", "medium")],
        [], spec_by_id, bounds_cache)
    # Filter F4
    f4 = evaluate_lifetime(
        sub, "F4: F1 + no falling MACD + no HHs intact",
        [("ema_alignment", "bull"), ("coiled_spring_score", "medium")],
        [("MACD_histogram_slope", "falling"),
         ("higher_highs_intact_flag", "True")],
        spec_by_id, bounds_cache)

    out = {
        "lifetime_baseline": {
            "n": int(n), "n_w": int(nw), "n_l": int(nl),
            "wr": baseline_wr,
        },
        "live_comparison": {
            "live_baseline_wr": 0.349,
            "live_F1_wr": LIVE_F1_WR,
            "live_F1_lift_pp": LIVE_F1_LIFT,
            "live_F4_wr": LIVE_F4_WR,
            "live_F4_lift_pp": LIVE_F4_LIFT,
        },
        "lifetime_F1": f1,
        "lifetime_F4": f4,
    }

    # Compute lifts + verdicts
    for label, fil in [("F1", f1), ("F4", f4)]:
        m_wr = fil["matched_wr"]
        live_wr = LIVE_F1_WR if label == "F1" else LIVE_F4_WR
        verdict = _verdict(m_wr, live_wr, baseline_wr)
        lift_lifetime = (m_wr - baseline_wr) if m_wr is not None else None
        fil["lift_over_lifetime_baseline"] = lift_lifetime
        fil["verdict"] = verdict

        print()
        print(f"── Filter {label}: {fil['name']} ──")
        print(f"  matched: {fil['n_matched']}/{n} "
              f"({fil['match_rate']*100:.1f}%) — "
              f"W={fil['n_matched_w']}, L={fil['n_matched_l']}")
        if m_wr is not None:
            print(f"  matched WR: {m_wr*100:.1f}%")
            print(f"  skipped WR: {fil['skipped_wr']*100:.1f}%")
            print(f"  lift over lifetime baseline ({baseline_wr*100:.1f}%): "
                  f"{lift_lifetime*100:+.1f}pp")
            print(f"  live finding: matched WR={live_wr*100:.1f}%, "
                  f"lift +{(live_wr - 0.349)*100:.1f}pp over live baseline")
            print(f"  verdict: {verdict}")
        else:
            print(f"  matched WR: undefined (no W+L)")

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # Overall verdict summary
    print()
    print("═" * 80)
    print("V1 SUMMARY")
    print("═" * 80)
    print(f"\n  F1 lifetime verdict: {f1['verdict']}")
    print(f"  F4 lifetime verdict: {f4['verdict']}")


if __name__ == "__main__":
    main()
