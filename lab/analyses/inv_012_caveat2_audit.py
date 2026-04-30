"""
INV-012 verification — Caveat 2 audit per detector.

The 9.31% MS-2 miss-rate (23 missing live signals from Apr 2026) may not be
evenly distributed across signal types or detectors. This audit determines if
INV-012 detector findings disproportionately depend on potentially-affected
signal regions.

Pipeline:
  1. Load 23 missing-from-MS-2 live signal dates from ms2_cross_validation_report
  2. Load INV-012 backtest_signals_INV012.parquet
  3. For each detector × HOLD_OPEN cell:
     - Count INV-012 signals on missing-MS-2 dates within detector cohort
     - Compute counterfactual WR excluding those date-symbol combinations
     - Compare to original cell WR
  4. Surface table; classify "Material" if Δ_WR > 1pp

Output: terminal surface only. NO findings.md write. NO commit yet (separate).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_INV012_PARQUET = _LAB_ROOT / "output" / "backtest_signals_INV012.parquet"
_MS2_REPORT = _LAB_ROOT / "logs" / "ms2_cross_validation_report.json"

_FLAT_THRESHOLD_PCT = 0.5
_DETECTORS = [
    "BTST_LAST_30MIN_STRENGTH",
    "BTST_SECTOR_LEADER_ROTATION",
    "BTST_POST_PULLBACK_RESUMPTION",
    "BTST_INSIDE_DAY_BREAKOUT",
]


def main():
    # Load missing live signals
    r = json.load(open(_MS2_REPORT))
    missing = r.get("missing_in_regen", [])
    print(f"[BLOCK 3] Caveat 2: {len(missing)} live signals not regenerated in MS-2",
          flush=True)
    missing_dates = sorted(set(m[0] for m in missing))
    missing_symbols = sorted(set(m[1] for m in missing))
    missing_signal_types = sorted(set(m[2] for m in missing))
    print(f"[BLOCK 3] missing dates: {len(missing_dates)} unique "
          f"(range {min(missing_dates)} → {max(missing_dates)})", flush=True)
    print(f"[BLOCK 3] missing symbols: {len(missing_symbols)} unique", flush=True)
    print(f"[BLOCK 3] missing signal types: {missing_signal_types}", flush=True)

    # Build missing date×symbol set for set-based filtering
    missing_pairs = set((m[0], m[1]) for m in missing)
    print(f"[BLOCK 3] missing (date, symbol) pairs: {len(missing_pairs)}", flush=True)

    # Load INV-012 signals
    df = pd.read_parquet(_INV012_PARQUET)
    print(f"[BLOCK 3] INV-012 signals: {len(df)} rows", flush=True)

    # Per-detector × HOLD_OPEN audit
    print()
    print("=" * 130)
    print("CAVEAT 2 AUDIT — per detector × HOLD_OPEN cell")
    print("=" * 130)
    print(f"{'Detector':<35} {'Original_WR':>12} {'Affected_n':>12} "
          f"{'Affected_pct':>14} {'WR_excl_affected':>18} {'Δ_pp':>7} {'Material?':>11}")

    for detector in _DETECTORS:
        cell = df[df["detector_id"] == detector].copy()
        if cell.empty:
            continue
        # Compute HOLD_OPEN outcome counts
        out_col = "HOLD_OPEN_outcome"
        if out_col not in cell.columns:
            continue
        # Original cell stats (matches INV-012 lifetime cell)
        orig_win = ((cell[out_col] == "DAY6_WIN") | (cell[out_col] == "TARGET_HIT")).sum()
        orig_loss = ((cell[out_col] == "DAY6_LOSS") | (cell[out_col] == "STOP_HIT")).sum()
        orig_n_excl = orig_win + orig_loss
        orig_wr = orig_win / orig_n_excl if orig_n_excl > 0 else None

        # Identify affected signals (date,symbol) pair matches a missing-MS-2 entry
        # Match also broader: any signal on a missing date (since miss might affect
        # neighboring detection)
        cell_pair = list(zip(cell["scan_date"], cell["symbol"]))
        affected_mask_pair = pd.Series(
            [(d, s) in missing_pairs for d, s in cell_pair], index=cell.index)
        # Date-only filter (broader)
        affected_mask_date = cell["scan_date"].isin(missing_dates)
        # Use date-only as the conservative "could be affected" set
        n_affected_pair = int(affected_mask_pair.sum())
        n_affected_date = int(affected_mask_date.sum())

        # Counterfactual: exclude all signals on missing dates
        excl = cell[~affected_mask_date]
        excl_win = ((excl[out_col] == "DAY6_WIN") | (excl[out_col] == "TARGET_HIT")).sum()
        excl_loss = ((excl[out_col] == "DAY6_LOSS") | (excl[out_col] == "STOP_HIT")).sum()
        excl_n_excl = excl_win + excl_loss
        excl_wr = excl_win / excl_n_excl if excl_n_excl > 0 else None

        if orig_wr is not None and excl_wr is not None:
            delta_pp = (excl_wr - orig_wr) * 100
            material = "MATERIAL" if abs(delta_pp) > 1.0 else "not material"
        else:
            delta_pp = None
            material = "—"
        affected_pct = n_affected_date / len(cell) * 100 if len(cell) > 0 else 0
        excl_wr_str = f"{excl_wr:.4f}" if excl_wr is not None else "—"
        delta_pp_str = f"{delta_pp:+.4f}" if delta_pp is not None else "—"
        affected_pct_str = f"{affected_pct:.3f}%"
        print(f"{detector:<35} {orig_wr:>11.4f} "
              f"{n_affected_date:>12} {affected_pct_str:>14} "
              f"{excl_wr_str:>18} {delta_pp_str:>7} {material:>11}")

    # Detector 3 specific note: POST_PULLBACK_RESUMPTION uses UP_TRI W history
    # from backtest_signals.parquet, which itself is regenerated by MS-2.
    # Examine if the 23 missing live signals are UP_TRI winners that would
    # affect Detector 3's lookback.
    print()
    print("Detector 3 POST_PULLBACK_RESUMPTION — UP_TRI W history exposure check:")
    missing_up_tri = [m for m in missing if m[2] == "UP_TRI"]
    print(f"  Missing live signals of type UP_TRI: {len(missing_up_tri)}")
    # Note: these are live UP_TRI signals not in regen; we don't know their
    # outcome (would they have been W?). Worst case: all 23 were W → Detector 3
    # may have missed identifying ~23 signals × 5-day-lookback windows = at most
    # ~115 day-symbol combinations (out of 605 Detector 3 signals total).
    # This is informational only — actual impact depends on outcomes.
    print(f"  Detector 3 total signals: 605 (lifetime)")
    print(f"  Worst-case Detector 3 lookback window exposure: "
          f"23 missing × 5-day lookback ≈ 115 day-symbol combos affected")
    print(f"  If proportion of missing-as-W matches universe rate (~52%): "
          f"~{int(23 * 0.52)} W signals possibly missed in Detector 3 lookback")

    # Universe-wide note
    print()
    print("Decision criteria:")
    print("  MATERIAL: |Δ_WR| > 1pp absolute when affected dates excluded")
    print("  Not material: |Δ_WR| ≤ 1pp")


if __name__ == "__main__":
    main()
