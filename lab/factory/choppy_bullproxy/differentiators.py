"""
Choppy BULL_PROXY cell — C2: differentiator analysis.

Adapted methodology — no Phase 5 winners exist (0 VALIDATED + 0 PRELIMINARY).
Instead:
  (a) Compare REJECTED (96) vs WATCH (79) — same Phase 4 evidence, different
      live n. Are they feature-distinguishable? (Expected: no, since Phase 5
      tier difference is sample-size-driven.)
  (b) Audit 8 live signals — compare features of 2 winners vs 6 losers.
      Tiny sample, but the only path to "narrow exception" claim.
  (c) Compare live signal features to Phase 4 surviving combinations — do
      the 8 live signals match any Phase 4 pattern? If 2 winners match
      patterns the 6 losers don't, that's the exception.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

# Import choppy_uptri shared helpers via importlib to avoid path collision
# with our own extract.py module
import importlib.util as _ilu
_uptri_diff_path = (_LAB_ROOT / "factory" / "choppy_uptri"
                       / "differentiators.py")
_spec = _ilu.spec_from_file_location("uptri_diff", _uptri_diff_path)
_uptri_diff = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_uptri_diff)
feature_presence = _uptri_diff.feature_presence
_row_features = _uptri_diff._row_features
differentiator_scores = _uptri_diff.differentiator_scores
TOP_K = _uptri_diff.TOP_K

_local_spec = _ilu.spec_from_file_location(
    "local_bullproxy_extract", _HERE / "extract.py")
_local_mod = _ilu.module_from_spec(_local_spec)
_local_spec.loader.exec_module(_local_mod)
load_choppy_bullproxy = _local_mod.load_choppy_bullproxy

OUTPUT_PATH = _HERE / "differentiators.json"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"


def live_signal_feature_audit() -> dict:
    """For 8 live Choppy BULL_PROXY signals, surface feature values of
    winners vs losers for key features."""
    live = pd.read_parquet(LIVE_PATH)
    cb = live[(live["signal"] == "BULL_PROXY")
                 & (live["regime"] == "Choppy")].copy()
    winners = cb[cb["wlf"] == "W"]
    losers = cb[cb["wlf"] == "L"]

    # Pull a wide set of features that distinguished UP_TRI Choppy
    # plus general regime/breadth/momentum features
    key_features = [
        "ema_alignment", "coiled_spring_score", "MACD_signal",
        "MACD_histogram_slope", "MACD_histogram_sign",
        "RSI_14", "ROC_10", "nifty_vol_regime",
        "market_breadth_pct", "advance_decline_ratio_20d",
        "regime_score", "sector_momentum_state",
        "52w_high_distance_pct", "52w_low_distance_pct",
        "ema20_distance_pct", "ema50_slope_5d_pct", "ema50_slope_20d_pct",
        "consolidation_quality", "range_compression_60d",
        "higher_highs_intact_flag", "swing_high_count_20d",
        "vol_q", "vol_ratio_20d", "obv_slope_20d_pct",
        "fib_618_proximity_atr", "fib_50_proximity_atr",
        "fib_382_proximity_atr",
        "fvg_unfilled_above_count", "ob_bullish_proximity",
        "support_zone_distance_atr", "resistance_zone_distance_atr",
        "day_of_week", "day_of_month_bucket",
    ]

    audit = []
    for f in key_features:
        col = f"feat_{f}"
        if col not in cb.columns:
            continue
        winner_vals = list(winners[col].dropna().tolist())
        loser_vals = list(losers[col].dropna().tolist())
        audit.append({
            "feature_id": f,
            "winner_values": winner_vals,
            "loser_values": loser_vals,
        })
    return {
        "n_winners": len(winners),
        "n_losers": len(losers),
        "winner_symbols": winners["symbol"].tolist(),
        "loser_symbols": losers["symbol"].tolist(),
        "feature_audit": audit,
    }


def main():
    print("─" * 80)
    print("CELL 3: Choppy BULL_PROXY — C2 differentiator analysis (adapted)")
    print("─" * 80)

    # Load combinations
    df = load_choppy_bullproxy()
    rejected = df[df["live_tier"] == "REJECTED"]
    watch = df[df["live_tier"] == "WATCH"]
    print(f"\nREJECTED: {len(rejected)}  WATCH: {len(watch)}")

    # Differentiator: REJECTED vs WATCH (sanity check that they're feature-similar)
    # Use REJECTED as "winners" position and WATCH as "rejected" — purely
    # to surface if any feature systematically differs between groups
    diff = differentiator_scores(rejected, watch)
    print(f"\nREJECTED vs WATCH feature differentiation (top 5 by abs delta):")
    print(f"  All near-zero deltas → same Phase-4 patterns, distinguished only "
          f"by live sample availability.")
    print(f"\n  {'feature':<35}{'level':<10}{'rej%':>8}{'watch%':>8}{'delta':>8}")
    print("  " + "─" * 67)
    diff_sorted_abs = sorted(diff, key=lambda r: -abs(r["differentiator_score"]))
    for r in diff_sorted_abs[:5]:
        print(f"  {r['feature_id']:<35}{r['level']:<10}"
              f"{r['rejected_pct']*100:>7.1f}%{r['winners_pct']*100:>7.1f}%"
              f"{r['differentiator_score']*100:>+7.1f}")

    # Live signal audit
    print()
    print("─" * 80)
    print("Live signal feature audit (n=8 = 2W + 6L)")
    print("─" * 80)
    audit = live_signal_feature_audit()
    print(f"\nWinners (n={audit['n_winners']}): {audit['winner_symbols']}")
    print(f"Losers (n={audit['n_losers']}): {audit['loser_symbols']}")

    # Surface features that DIFFER between the 2 winners and 6 losers
    print()
    print("Features where winner values differ from loser values (potential exception):")
    print(f"\n  {'feature':<35}{'winners':<35}{'losers':<35}")
    print("  " + "─" * 105)
    interesting = []
    for fa in audit["feature_audit"]:
        w_vals = fa["winner_values"]
        l_vals = fa["loser_values"]
        if not w_vals or not l_vals:
            continue
        # For categorical/bool: check if winner values are in any loser
        try:
            if all(isinstance(v, str) for v in w_vals + l_vals):
                w_set = set(w_vals); l_set = set(l_vals)
                # Both winners share a value not in losers → differentiator candidate
                w_only = w_set - l_set
                if w_only and len(w_set) <= 2:
                    interesting.append({
                        "feature": fa["feature_id"],
                        "winner_only_values": list(w_only),
                        "winner_values": w_vals, "loser_values": l_vals,
                    })
                    w_str = ", ".join(str(v) for v in w_vals)
                    l_str = ", ".join(set(str(v) for v in l_vals))
                    marker = "★" if w_only else " "
                    print(f"   {marker}{fa['feature_id']:<33}{w_str[:33]:<35}"
                          f"{l_str[:33]:<35}")
            else:
                # numeric — check if winner range is disjoint from loser range
                w_min, w_max = min(w_vals), max(w_vals)
                l_min, l_max = min(l_vals), max(l_vals)
                # Distinct if winner range outside loser range
                if w_min > l_max or w_max < l_min:
                    interesting.append({
                        "feature": fa["feature_id"],
                        "winner_range": [w_min, w_max],
                        "loser_range": [l_min, l_max],
                    })
                    print(f"   ★{fa['feature_id']:<33}"
                          f"[{w_min:.3f}..{w_max:.3f}]"
                          .ljust(35) +
                          f"[{l_min:.3f}..{l_max:.3f}]")
        except Exception:
            pass

    if not interesting:
        print("\n  No features cleanly separate the 2 winners from 6 losers.")

    # Save
    out = {
        "rejected_vs_watch_top_diffs": diff_sorted_abs[:20],
        "live_signal_audit": audit,
        "winner_distinguishing_features": interesting,
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
