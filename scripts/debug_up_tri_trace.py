"""Trace why scanner saw zero UP_TRI on 2026-05-14.

Imports the production functions (prepare, add_indicators,
detect_pivots, detect_signals) and runs them on a target symbol,
printing every gate. Production source is read-only; no edits.

Usage:
    .venv/bin/python scripts/debug_up_tri_trace.py BAJAJ-AUTO.NS
    .venv/bin/python scripts/debug_up_tri_trace.py BAJAJ-AUTO.NS \\
        ADANIENT.NS CIPLA.NS
"""
from __future__ import annotations

import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np
import pandas as pd

from scanner.scanner_core import (
    prepare, add_indicators, detect_pivots, build_zones,
    add_zone_proximity, detect_signals,
)
from scanner.config import PIVOT_LOOKBACK, STOP_MULT


def trace_one(symbol: str, *, verbose: bool = True) -> dict:
    """Run the production pipeline on one symbol with verbose tracing."""
    LB = PIVOT_LOOKBACK
    print(f"\n{'='*70}")
    print(f"=== TRACING: {symbol}")
    print(f"{'='*70}")

    # ---- Step 1: prepare() — fresh yfinance pull ----
    print("\n[STEP 1] prepare(period='1y') — yfinance download")
    df, reason = prepare(symbol, period="1y")
    if df is None:
        print(f"  FAIL — prepare returned None, reason={reason}")
        return {"symbol": symbol, "result": "prepare_failed", "reason": reason}
    n = len(df)
    first_date = df.index[0].date().isoformat()
    last_date = df.index[-1].date().isoformat()
    print(f"  OK — bars={n}, range={first_date} → {last_date}")
    print(f"  last 3 rows (Close, Low, High):")
    for ts, row in df.tail(3).iterrows():
        print(f"    {ts.date()}  C={row['Close']:.2f}  L={row['Low']:.2f}  H={row['High']:.2f}")

    # *** CRITICAL CHECK *** — does today's bar exist?
    today_str = "2026-05-14"
    in_df_dates = {ts.date().isoformat() for ts in df.index}
    has_today = today_str in in_df_dates
    print(f"  has 2026-05-14 bar? {has_today}")

    # ---- Step 2: add_indicators ----
    print("\n[STEP 2] add_indicators")
    df = add_indicators(df)
    atr_last = df["atrS"].iloc[-1]
    print(f"  OK — atrS last bar = {atr_last:.4f}")

    # ---- Step 3: detect_pivots ----
    print(f"\n[STEP 3] detect_pivots(lookback={LB})")
    df = detect_pivots(df)
    n_pl = int(df["pivot_low"].sum())
    n_ph = int(df["pivot_high"].sum())
    print(f"  OK — pivot_low count={n_pl}, pivot_high count={n_ph}")
    # Most recent pivot_lows
    pl_dates = df.index[df["pivot_low"].values][-5:]
    print(f"  last 5 pivot_low dates: {[d.date().isoformat() for d in pl_dates]}")

    # ---- Step 4: build_zones + add_zone_proximity ----
    df = build_zones(df)
    df = add_zone_proximity(df)

    # ---- Step 5: replicate the UP_TRI loop manually (matches lines 322-377) ----
    print(f"\n[STEP 5] UP_TRI candidate loop (last_bar={n-1}, LB={LB}, ages 0-3)")
    closes = df["Close"].values
    lows = df["Low"].values
    atr_v = df["atrS"].values
    pl_v = df["pivot_low"].values
    last_bar = n - 1
    pass_count = 0

    for age in range(0, 4):
        pb = last_bar - age - LB
        bar_date = df.index[pb].date().isoformat() if 0 <= pb < n else "OOB"
        print(f"\n  age={age}  pb={pb}  pb_date={bar_date}")

        if pb < LB or pb >= n:
            print(f"    FAIL — pb out of valid range (need {LB} <= pb < {n})")
            continue

        is_pl = bool(pl_v[pb])
        print(f"    pl_v[pb]={is_pl}")
        if not is_pl:
            print(f"    FAIL — not a pivot_low at index {pb} ({bar_date})")
            continue

        atr = atr_v[pb]
        print(f"    atr_v[pb]={atr:.4f}")
        if np.isnan(atr) or atr <= 0:
            print(f"    FAIL — atr is NaN or <= 0")
            continue

        pivot_px = lows[pb]
        entry_est = closes[last_bar]
        stop = round(pivot_px - STOP_MULT * atr, 2)
        print(f"    pivot_low={pivot_px:.2f}  entry_est={entry_est:.2f}  stop={stop:.2f}")
        print(f"    buffer (entry - stop) = {entry_est - stop:.2f} "
              f"({(entry_est - stop)/entry_est * 100:.2f}% of entry)")

        if stop >= entry_est:
            print(f"    FAIL — stop ({stop}) >= entry_est ({entry_est})")
            continue

        print(f"    PASS — UP_TRI candidate at age={age}, pb_date={bar_date}")
        pass_count += 1

    # ---- Step 6: actually call production detect_signals ----
    print(f"\n[STEP 6] detect_signals (full production call)")
    sigs = detect_signals(
        df, symbol=symbol, sector="Test",
        regime="Choppy", regime_score=0,
        sector_momentum={}, nifty_close=None,
    )
    up_tri = [s for s in sigs if s.get("signal") == "UP_TRI"]
    print(f"  detect_signals returned {len(sigs)} signals total, "
          f"{len(up_tri)} UP_TRI")
    for s in up_tri:
        print(f"    age={s['age']} pivot_date={s['pivot_date']} "
              f"pivot_price={s['pivot_price']} entry_est={s['entry_est']} "
              f"stop={s['stop']}")

    return {
        "symbol": symbol,
        "n_bars": n,
        "last_bar_date": last_date,
        "has_today_bar": has_today,
        "manual_pass_count": pass_count,
        "production_up_tri_count": len(up_tri),
    }


def main(argv: list[str]) -> int:
    if not argv:
        argv = ["BAJAJ-AUTO.NS"]
    results = []
    for sym in argv:
        results.append(trace_one(sym))

    # Summary table
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"{'symbol':22} {'n_bars':>7} {'last_bar':>12} {'has_today':>10} "
          f"{'manual':>7} {'prod':>5}")
    for r in results:
        if "result" in r and r["result"] == "prepare_failed":
            print(f"{r['symbol']:22} prepare_failed reason={r.get('reason')}")
            continue
        print(f"{r['symbol']:22} {r['n_bars']:>7} {r['last_bar_date']:>12} "
              f"{str(r['has_today_bar']):>10} {r['manual_pass_count']:>7} "
              f"{r['production_up_tri_count']:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
