"""
INV-012 verification — Overnight bias baseline (NULL hypothesis test).

Tests whether INV-012 BTST detectors capture a unique edge OR merely the
well-documented overnight gap bias in Indian equities.

NULL hypothesis: unconditional buy-close → sell-open across all stocks × days
yields a similar WR to the BTST detectors. If detector WR ≈ baseline WR, the
detectors are not selecting a unique edge — just inheriting the universe-wide
overnight bias.

Pipeline:
  1. Load 188 stock parquets
  2. For each stock × each trading day: compute (next_day_open / today_close - 1) × 100
  3. FLAT threshold ±0.5%; classify W/L/F
  4. Aggregate lifetime WR_excl_flat across all stock-days
  5. Year-by-year + sector breakdown
  6. Compare each INV-012 HOLD_OPEN cell vs baseline via 2-prop z-test

Output: terminal surface only. NO findings.md. NO promotion calls.
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
_CACHE_DIR = _LAB_ROOT / "cache"
_UNIVERSE_CSV = _REPO_ROOT / "data" / "fno_universe.csv"

_FLAT_THRESHOLD_PCT = 0.5

# INV-012 HOLD_OPEN cell results (from inv_012_run.log; recorded for comparison)
_INV012_CELLS = [
    ("BTST_LAST_30MIN_STRENGTH × HOLD_OPEN", 0.7715, 8597),
    ("BTST_SECTOR_LEADER_ROTATION × HOLD_OPEN", 0.6948, 6426),
    ("BTST_POST_PULLBACK_RESUMPTION × HOLD_OPEN", 0.7297, 344),
    ("BTST_INSIDE_DAY_BREAKOUT × HOLD_OPEN", 0.6689, 42419),
]


def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
    if n1 < 5 or n2 < 5:
        return None
    p1 = w1 / n1; p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _wilson_lower_95(wins: int, n: int) -> Optional[float]:
    if n <= 0:
        return None
    p_hat = wins / n
    z = 1.96
    z2 = z * z
    denom = 1 + z2 / n
    centre = p_hat + z2 / (2 * n)
    margin = z * ((p_hat * (1 - p_hat) + z2 / (4 * n)) / n) ** 0.5
    return round((centre - margin) / denom, 4)


def stock_parquets() -> list[Path]:
    return [p for p in sorted(_CACHE_DIR.glob("*.parquet"))
            if not p.name.startswith("_index_")]


def parquet_to_symbol(p: Path) -> str:
    return p.stem.replace("_NS", ".NS")


def main():
    sector_lookup = dict(zip(
        pd.read_csv(_UNIVERSE_CSV)["symbol"],
        pd.read_csv(_UNIVERSE_CSV)["sector"]))
    print(f"[BLOCK 2] universe: {len(sector_lookup)} symbols", flush=True)

    parquets = stock_parquets()
    print(f"[BLOCK 2] scanning {len(parquets)} stock parquets…", flush=True)

    records = []
    n_skipped = 0
    t0 = time.time()
    for i, p in enumerate(parquets):
        symbol = parquet_to_symbol(p)
        sector = sector_lookup.get(symbol, "Unknown")
        try:
            df = pd.read_parquet(p).sort_index()
            df = df.dropna(subset=["Open", "Close"])
            if len(df) < 2:
                n_skipped += 1; continue
            # Overnight return: (next_open / today_close - 1) × 100
            today_close = df["Close"]
            next_open = df["Open"].shift(-1)
            overnight_pct = (next_open / today_close - 1) * 100
            for ts, pct in overnight_pct.dropna().items():
                pct = float(pct)
                if pct > _FLAT_THRESHOLD_PCT:
                    outcome = "WIN"
                elif pct < -_FLAT_THRESHOLD_PCT:
                    outcome = "LOSS"
                else:
                    outcome = "FLAT"
                records.append({
                    "scan_date": ts.strftime("%Y-%m-%d"),
                    "year": ts.year,
                    "symbol": symbol,
                    "sector": sector,
                    "overnight_pct": pct,
                    "outcome": outcome,
                })
        except Exception as e:
            print(f"  skip {p.name}: {e}", flush=True)
            n_skipped += 1
        if (i + 1) % 50 == 0:
            print(f"[BLOCK 2] {i+1}/{len(parquets)} stocks; "
                  f"{len(records)} records ({time.time()-t0:.1f}s)", flush=True)

    rdf = pd.DataFrame(records)
    print(f"[BLOCK 2] universe overnight records: {len(rdf)} "
          f"({n_skipped} stocks skipped, {time.time()-t0:.1f}s)", flush=True)

    # Lifetime baseline
    n_total = len(rdf)
    n_win = int((rdf["outcome"] == "WIN").sum())
    n_loss = int((rdf["outcome"] == "LOSS").sum())
    n_flat = int((rdf["outcome"] == "FLAT").sum())
    n_excl_flat = n_win + n_loss
    baseline_wr = n_win / n_excl_flat if n_excl_flat > 0 else None
    baseline_wilson = _wilson_lower_95(n_win, n_excl_flat)
    avg_pnl = rdf["overnight_pct"].mean()

    print()
    print("=" * 100)
    print("UNIVERSE OVERNIGHT BIAS BASELINE (NULL hypothesis)")
    print("=" * 100)
    print(f"Total stock-days: {n_total}")
    print(f"  WIN (>+0.5% overnight): {n_win} ({n_win/n_total*100:.2f}%)")
    print(f"  LOSS (<-0.5% overnight): {n_loss} ({n_loss/n_total*100:.2f}%)")
    print(f"  FLAT (±0.5%): {n_flat} ({n_flat/n_total*100:.2f}%)")
    print(f"  n_excl_flat: {n_excl_flat}")
    print(f"  WR_excl_flat: {baseline_wr:.4f} ({baseline_wr*100:.2f}%)")
    print(f"  Wilson lower 95: {baseline_wilson}")
    print(f"  Avg overnight return: {avg_pnl:+.4f}%")

    print()
    print("Year-by-year breakdown:")
    print(f"{'Year':<6} {'n_total':>9} {'WR_excl_flat':>14} {'avg_pnl%':>10}")
    yearly = rdf.groupby("year").agg(
        n_win=("outcome", lambda x: (x == "WIN").sum()),
        n_loss=("outcome", lambda x: (x == "LOSS").sum()),
        n_total=("outcome", "count"),
        avg_pnl=("overnight_pct", "mean"),
    )
    for y, row in yearly.iterrows():
        n_e = row["n_win"] + row["n_loss"]
        wr = row["n_win"] / n_e if n_e > 0 else None
        print(f"{int(y):<6} {int(row['n_total']):>9} "
              f"{wr if wr is None else f'{wr:.4f}':>14} "
              f"{row['avg_pnl']:>+9.3f}%")

    print()
    print("Top 8 sectors by overnight WR:")
    sector_wr = rdf.groupby("sector").agg(
        n_win=("outcome", lambda x: (x == "WIN").sum()),
        n_loss=("outcome", lambda x: (x == "LOSS").sum()),
        n_total=("outcome", "count"),
        avg_pnl=("overnight_pct", "mean"),
    )
    sector_wr["n_excl_flat"] = sector_wr["n_win"] + sector_wr["n_loss"]
    sector_wr["wr"] = sector_wr["n_win"] / sector_wr["n_excl_flat"]
    sector_wr = sector_wr.sort_values("wr", ascending=False)
    print(f"{'Sector':<14} {'n_total':>9} {'n_excl_flat':>13} {'WR':>8} {'avg_pnl%':>10}")
    for sec, row in sector_wr.head(8).iterrows():
        print(f"{sec:<14} {int(row['n_total']):>9} {int(row['n_excl_flat']):>13} "
              f"{row['wr']:>7.4f} {row['avg_pnl']:>+9.3f}%")

    # ── Compare INV-012 HOLD_OPEN cells vs baseline ──
    print()
    print("=" * 100)
    print("INV-012 HOLD_OPEN cells vs UNIVERSE BASELINE")
    print("=" * 100)
    print(f"{'Cell':<48} {'Det_WR':>8} {'Base_WR':>8} {'Δ pp':>7} {'p-value':>10} {'Verdict':>20}")
    for cell_name, det_wr, det_n in _INV012_CELLS:
        # 2-prop z-test: detector vs baseline
        w_det = round(det_wr * det_n)
        w_base = n_win
        delta_pp = (det_wr - baseline_wr) * 100
        p_val = _two_proportion_p_value(w_det, det_n, w_base, n_excl_flat)
        # Decision criteria
        if delta_pp >= 5 and p_val is not None and p_val < 0.01:
            verdict = "REAL_EDGE"
        elif delta_pp >= 3 and p_val is not None and p_val < 0.05:
            verdict = "MARGINAL"
        elif delta_pp < 3 or (p_val is not None and p_val > 0.05):
            verdict = "LIKELY_BIAS_CAPTURE"
        else:
            verdict = "INDETERMINATE"
        print(f"{cell_name:<48} {det_wr:>8.4f} {baseline_wr:>8.4f} {delta_pp:>+6.2f} "
              f"{p_val if p_val is not None else 'na':>10} {verdict:>20}")

    print()
    print("Decision criteria:")
    print("  REAL_EDGE: detector WR ≥ baseline + 5pp AND p < 0.01")
    print("  MARGINAL: detector WR ≥ baseline + 3pp AND p < 0.05")
    print("  LIKELY_BIAS_CAPTURE: <3pp above baseline OR p > 0.05")


if __name__ == "__main__":
    main()
