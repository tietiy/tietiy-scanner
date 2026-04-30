"""
INV-012 verification — INSIDE_DAY_BREAKOUT tightening exploration.

INSIDE_DAY_BREAKOUT × HOLD_OPEN n=42,419 too lax (T6 flagged in INV-012).
BLOCK 2 baseline check showed this detector is at -0.17pp vs baseline (i.e.,
LIKELY_BIAS_CAPTURE — not a real edge). Tightening with quality filters tests
whether subsets exist where the edge becomes real.

5 candidate filter variants tested:
  A — + volume filter: today_volume > 1.5× 20-day avg
  B — + sector_momentum = Leading (8 indexed sectors only)
  C — + regime != Choppy (only Bear or Bull)
  D — + range tightness: yesterday's range < 3% of yesterday's close
  E — + composite (A + B): volume AND sector_momentum=Leading

For each variant: compute n_post_filter, WR_post, drift, train/test split,
Wilson lower; compare to baseline 66.89% AND universe overnight bias 67.06%.

Decision: "best tightening candidate" =
  - n in 2K-8K range (operationally tractable)
  - WR ≥ baseline (66.89%) maintained
  - Wilson lower ≥ 0.55
  - meaningful edge over universe overnight bias (≥ 5pp)

Output: terminal surface only.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from hypothesis_tester import (  # noqa: E402
    compute_cohort_stats,
    evaluate_hypothesis,
    wilson_lower_bound_95,
)

_INV012_PARQUET = _LAB_ROOT / "output" / "backtest_signals_INV012.parquet"
_CACHE_DIR = _LAB_ROOT / "cache"
_REGIME_PATH = _LAB_ROOT / "output" / "regime_history.parquet"
_SECTOR_MOM_PATH = _LAB_ROOT / "output" / "sector_momentum_history.parquet"

_BASELINE_WR = 0.6689  # INV-012 INSIDE_DAY × HOLD_OPEN baseline
_UNIVERSE_OVERNIGHT_BIAS = 0.6706  # BLOCK 2 measured baseline


def _summarize(cell: pd.DataFrame, label: str) -> dict:
    """Compute lifetime + tier eval for a filtered cell."""
    if cell.empty:
        return {"label": label, "n": 0, "wr": None, "wilson": None,
                "tier_eval_status": "EMPTY"}
    cell = cell.copy()
    cell["outcome"] = cell["HOLD_OPEN_outcome"]
    cell["pnl_pct"] = cell["HOLD_OPEN_pnl"]
    win = ((cell["outcome"] == "DAY6_WIN") | (cell["outcome"] == "TARGET_HIT")).sum()
    loss = ((cell["outcome"] == "DAY6_LOSS") | (cell["outcome"] == "STOP_HIT")).sum()
    flat = (cell["outcome"] == "DAY6_FLAT").sum()
    n_excl = int(win + loss)
    wr = round(win / n_excl, 4) if n_excl > 0 else None
    wilson = wilson_lower_bound_95(int(win), n_excl) if n_excl > 0 else None
    avg_pnl = round(cell["pnl_pct"].mean(), 4) if len(cell) > 0 else None
    out = {
        "label": label, "n": len(cell), "n_excl_flat": n_excl,
        "wr": wr, "wilson": wilson, "avg_pnl": avg_pnl,
        "boost_tier": None, "drift_pp": None, "tier_eval_status": None,
    }
    if n_excl < 30:
        out["tier_eval_status"] = "INSUFFICIENT_N"
        return out
    try:
        boost = evaluate_hypothesis(
            cell, cohort_filter={}, hypothesis_type="BOOST")
        out["boost_tier"] = boost["tier"]
        out["drift_pp"] = boost["drift_pp"]
        out["tier_eval_status"] = "OK"
    except Exception as e:
        out["tier_eval_status"] = f"ERROR: {e}"
    return out


def _load_volume_features(symbol_to_dates: dict) -> dict:
    """For each (symbol, date), compute today_volume / 20d_avg_volume."""
    cache_lookup = {}
    for sym in symbol_to_dates:
        parquet_name = sym.replace(".NS", "_NS") + ".parquet"
        p = _CACHE_DIR / parquet_name
        if not p.exists():
            continue
        df = pd.read_parquet(p).sort_index()
        df = df.dropna(subset=["Volume", "Close", "High", "Low"])
        df["vol_20d_avg"] = df["Volume"].rolling(20).mean().shift(1)
        df["vol_ratio"] = df["Volume"] / df["vol_20d_avg"]
        df["prev_range"] = (df["High"].shift(1) - df["Low"].shift(1))
        df["prev_close"] = df["Close"].shift(1)
        df["prev_range_pct"] = df["prev_range"] / df["prev_close"]
        for ts in df.index:
            ds = ts.strftime("%Y-%m-%d")
            cache_lookup[(sym, ds)] = {
                "vol_ratio": float(df.loc[ts, "vol_ratio"])
                  if not pd.isna(df.loc[ts, "vol_ratio"]) else None,
                "prev_range_pct": float(df.loc[ts, "prev_range_pct"])
                  if not pd.isna(df.loc[ts, "prev_range_pct"]) else None,
            }
    return cache_lookup


def main():
    df = pd.read_parquet(_INV012_PARQUET)
    inside = df[df["detector_id"] == "BTST_INSIDE_DAY_BREAKOUT"].copy()
    print(f"[BLOCK 4] INSIDE_DAY_BREAKOUT signals: {len(inside)}", flush=True)

    # Pre-load vol_ratio + prev_range_pct features for filter A and D
    print(f"[BLOCK 4] computing vol_ratio + prev_range_pct features…", flush=True)
    symbol_to_dates = {}
    for _, r in inside.iterrows():
        symbol_to_dates.setdefault(r["symbol"], set()).add(r["scan_date"])
    feature_lookup = _load_volume_features(symbol_to_dates)
    print(f"[BLOCK 4] feature lookup built: {len(feature_lookup)} entries",
          flush=True)

    # Attach features to inside DataFrame
    inside["vol_ratio"] = inside.apply(
        lambda r: feature_lookup.get((r["symbol"], r["scan_date"]), {}).get("vol_ratio"),
        axis=1)
    inside["prev_range_pct"] = inside.apply(
        lambda r: feature_lookup.get((r["symbol"], r["scan_date"]), {}).get("prev_range_pct"),
        axis=1)

    # Sector_momentum lookup for filter B
    sec_mom_df = pd.read_parquet(_SECTOR_MOM_PATH)
    sec_mom_df["date"] = pd.to_datetime(sec_mom_df["date"])
    sec_mom_indexed = sec_mom_df.set_index(sec_mom_df["date"].dt.strftime("%Y-%m-%d"))

    def _sec_mom(row):
        sec = row["sector"]; ds = row["scan_date"]
        if ds in sec_mom_indexed.index and sec in sec_mom_indexed.columns:
            return sec_mom_indexed.loc[ds, sec]
        return "Neutral"
    inside["sec_mom"] = inside.apply(_sec_mom, axis=1)

    # Build variant masks
    variants = []
    variants.append(("BASELINE", pd.Series(True, index=inside.index)))
    variants.append((
        "A: +volume>1.5× 20d_avg",
        inside["vol_ratio"].notna() & (inside["vol_ratio"] > 1.5)))
    variants.append((
        "B: +sector_mom=Leading",
        inside["sec_mom"] == "Leading"))
    variants.append((
        "C: +regime!=Choppy",
        inside["regime"].isin(["Bear", "Bull"])))
    variants.append((
        "D: +prev_range_pct<0.03",
        inside["prev_range_pct"].notna() & (inside["prev_range_pct"] < 0.03)))
    variants.append((
        "E: composite A+B",
        inside["vol_ratio"].notna() & (inside["vol_ratio"] > 1.5)
        & (inside["sec_mom"] == "Leading")))

    # Surface results
    print()
    print("=" * 130)
    print("INSIDE_DAY_BREAKOUT TIGHTENING — variant comparison")
    print("=" * 130)
    print(f"{'Variant':<32} {'n':>8} {'n_excl_flat':>12} {'WR':>8} {'Δ vs base (pp)':>16} "
          f"{'Δ vs univ_bias (pp)':>20} {'Wilson':>8} {'BoostTier':>10} {'Tractable?':>12}")
    for label, mask in variants:
        cell = inside[mask]
        s = _summarize(cell, label)
        wr = s["wr"]
        n = s["n"]
        wilson = s["wilson"]
        boost = s["boost_tier"] if s["tier_eval_status"] == "OK" else s["tier_eval_status"]
        if wr is not None:
            d_base = (wr - _BASELINE_WR) * 100
            d_univ = (wr - _UNIVERSE_OVERNIGHT_BIAS) * 100
            d_base_str = f"{d_base:+.2f}"
            d_univ_str = f"{d_univ:+.2f}"
            # Tractable: n in 2K-8K AND WR maintained AND Wilson ≥ 0.55 AND edge over universe ≥ 5pp
            tractable_n = (2000 <= n <= 8000)
            tractable_wr = wr >= _BASELINE_WR
            tractable_wilson = wilson is not None and wilson >= 0.55
            tractable_edge = d_univ >= 5.0
            tractable = (tractable_n and tractable_wr
                          and tractable_wilson and tractable_edge)
            tractable_str = ("TRACTABLE" if tractable
                              else f"NO ({'n' if not tractable_n else ''}"
                                   f"{'-WR' if not tractable_wr else ''}"
                                   f"{'-Wilson' if not tractable_wilson else ''}"
                                   f"{'-edge' if not tractable_edge else ''})")
        else:
            d_base_str = d_univ_str = tractable_str = "—"
            wr = None
        wilson_str = f"{wilson:.4f}" if wilson is not None else "—"
        wr_str = f"{wr:.4f}" if wr is not None else "—"
        if label == "BASELINE":
            tractable_str = "NO (too lax)"
        print(f"{label:<32} {n:>8} {s.get('n_excl_flat', 0):>12} {wr_str:>8} "
              f"{d_base_str:>16} {d_univ_str:>20} {wilson_str:>8} "
              f"{str(boost):>10} {tractable_str:>12}")

    print()
    print(f"Reference baselines:")
    print(f"  INSIDE_DAY_BREAKOUT × HOLD_OPEN baseline WR: {_BASELINE_WR}")
    print(f"  Universe overnight bias (BLOCK 2): {_UNIVERSE_OVERNIGHT_BIAS}")
    print()
    print("Decision criteria (TRACTABLE = all four):")
    print("  - n in 2K-8K range (operationally tractable)")
    print("  - WR ≥ baseline 66.89% maintained")
    print("  - Wilson lower 95 ≥ 0.55")
    print("  - meaningful edge over universe overnight bias (≥ 5pp)")


if __name__ == "__main__":
    main()
