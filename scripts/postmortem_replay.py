"""Phase 2: Replay scanner detectors across 15 years of OHLCV.

For each cached stock:
1. Run add_indicators + detect_pivots + build_zones + add_zone_proximity once.
2. Iterate every valid scan-day index i in [warmup..n-1]; emit raw signals
   exactly as scanner_core.detect_signals would have at that snapshot.
3. Compute V1 regime per scan date from Nifty parquet.
4. For each signal, simulate 6-trading-day forward outcome:
   entry = next bar open, stop and target supplied by scanner, R:R=2:1.

Saves to: output/historical_analysis/all_signals_15y.parquet
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

REPO = "/Users/abhisheklalwani/code/tietiy-scanner"
sys.path.insert(0, REPO)
from scanner.scanner_core import (
    add_indicators, detect_pivots, build_zones, add_zone_proximity,
)
from scanner.scorer import score_signal
from scanner.config import (
    PIVOT_LOOKBACK, STOP_MULT, SMC_COOLDOWN,
    BP_CLOSE_POS_MIN, BP_LOWER_WICK_MIN,
)

CACHE_DIR = os.path.join(REPO, "data", "historical", "cache")
UNIVERSE_CSV = os.path.join(REPO, "data", "fno_universe.csv")
NIFTY_PARQUET = os.path.join(REPO, "data", "historical", "nifty.parquet")
OUT_PARQUET = os.path.join(REPO, "output", "historical_analysis",
                           "all_signals_15y.parquet")

LB = PIVOT_LOOKBACK
WARMUP_BARS = 250  # require 1 year of data before first signal
FORWARD_DAYS = 6


def compute_v1_regime(nifty: pd.DataFrame) -> pd.DataFrame:
    """V1 regime per Nifty bar — same logic as scanner_core._get_stock_regime
    and scanner.main.get_nifty_info."""
    closes = nifty["Close"]
    ema50 = closes.ewm(span=50).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    above = closes > ema50
    ret20 = (closes / closes.shift(20) - 1) * 100

    regime = pd.Series("Choppy", index=nifty.index)
    regime[(slope > 0.005) & above] = "Bull"
    regime[(slope < -0.005) & ~above] = "Bear"

    regime_score = pd.Series(0, index=nifty.index)
    regime_score[ret20 > 5] = 2
    regime_score[(ret20 > 2) & (ret20 <= 5)] = 1
    regime_score[(ret20 < -2)] = -1

    ret30 = (closes / closes.shift(30) - 1) * 100
    return pd.DataFrame({
        "regime": regime, "regime_score": regime_score,
        "ret20_pct": ret20, "ret30_pct": ret30,
        "nifty_close": closes,
    })


def per_bar_vol_rs(df: pd.DataFrame, nifty_close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Vectorised vol_q/vol_confirm/rs_q computed for every bar."""
    vol = df["Volume"]
    avg20 = vol.rolling(20).mean().shift(1)
    vr = vol / avg20
    vol_q = pd.Series("Average", index=df.index)
    vol_q[vr > 1.5] = "High"
    vol_q[vr < 0.7] = "Thin"
    vol_confirm = vr >= 1.2

    closes = df["Close"]
    s_ret_20 = closes / closes.shift(20) - 1
    nifty_aligned = nifty_close.reindex(df.index, method="nearest")
    n_ret_20 = nifty_aligned / nifty_aligned.shift(20) - 1
    diff_pp = (s_ret_20 - n_ret_20) * 100
    rs_q = pd.Series("Neutral", index=df.index)
    rs_q[diff_pp > 3] = "Strong"
    rs_q[diff_pp < -3] = "Weak"
    return vol_q, vol_confirm.fillna(False), rs_q


def replay_one_stock(args) -> list[dict]:
    """Run signal replay on one cached stock. Returns list of signal dicts."""
    sym, sector, grade, regime_df, nifty_close, cache_path = args
    try:
        df = pd.read_parquet(cache_path)
    except Exception as e:
        return []
    if len(df) < WARMUP_BARS + FORWARD_DAYS + 10:
        return []

    df = df.sort_index()
    df = add_indicators(df)
    df = detect_pivots(df)
    df = build_zones(df)
    df = add_zone_proximity(df)

    vol_q_s, vol_c_s, rs_q_s = per_bar_vol_rs(df, nifty_close)
    df["vol_q"] = vol_q_s
    df["vol_confirm"] = vol_c_s
    df["rs_q"] = rs_q_s

    closes = df["Close"].values
    opens = df["Open"].values
    highs = df["High"].values
    lows = df["Low"].values
    atr_v = df["atrS"].values
    ema50v = df["ema50"].values
    pl_v = df["pivot_low"].values
    ph_v = df["pivot_high"].values
    nSZ_v = df["nearSZ"].values
    szL_v = df["szL"].values
    vol_q_v = df["vol_q"].values
    vol_c_v = df["vol_confirm"].values
    rs_q_v = df["rs_q"].values
    n = len(df)
    dates = df.index

    # Align regime per scan date
    reg_aligned = regime_df.reindex(dates, method="ffill")
    reg_arr = reg_aligned["regime"].values
    reg_score_arr = reg_aligned["regime_score"].fillna(0).astype(int).values
    ret30_arr = reg_aligned["ret30_pct"].values

    signals = []

    def append_sig(scan_i: int, sig_type: str, age: int, direction: str,
                   pivot_i: int, entry_est: float, stop: float):
        # entry on bar scan_i + 1 open
        if scan_i + 1 >= n or scan_i + FORWARD_DAYS >= n:
            return  # not enough forward bars
        risk = abs(entry_est - stop)
        if direction == "LONG":
            target = round(entry_est + 2 * risk, 2)
        else:
            target = round(entry_est - 2 * risk, 2)

        entry_open = float(opens[scan_i + 1])
        if direction == "LONG":
            if entry_open <= stop:
                outcome = "GAP_INVALID"; exit_price = entry_open; exit_day = 0
                pnl_pct = (exit_price - entry_open) / entry_open * 100
                return _add(signals, scan_i, pivot_i, sig_type, age, direction,
                            entry_open, stop, target, outcome, exit_price, exit_day,
                            pnl_pct, sym, sector, grade,
                            vol_q_v, vol_c_v, rs_q_v, reg_arr, reg_score_arr,
                            ret30_arr, dates)
        else:
            if entry_open >= stop:
                outcome = "GAP_INVALID"; exit_price = entry_open; exit_day = 0
                pnl_pct = (entry_open - exit_price) / entry_open * 100
                return _add(signals, scan_i, pivot_i, sig_type, age, direction,
                            entry_open, stop, target, outcome, exit_price, exit_day,
                            pnl_pct, sym, sector, grade,
                            vol_q_v, vol_c_v, rs_q_v, reg_arr, reg_score_arr,
                            ret30_arr, dates)

        # Walk forward up to FORWARD_DAYS bars
        outcome = "DAY6_EXIT"; exit_price = None; exit_day = FORWARD_DAYS
        for d in range(1, FORWARD_DAYS + 1):
            bar_i = scan_i + d
            hi = float(highs[bar_i]); lo = float(lows[bar_i])
            if direction == "LONG":
                # check stop and target. If both same bar → assume stop (worst case)
                if lo <= stop:
                    outcome = "STOP_HIT"; exit_price = stop; exit_day = d; break
                if hi >= target:
                    outcome = "TARGET_HIT"; exit_price = target; exit_day = d; break
            else:
                if hi >= stop:
                    outcome = "STOP_HIT"; exit_price = stop; exit_day = d; break
                if lo <= target:
                    outcome = "TARGET_HIT"; exit_price = target; exit_day = d; break
        if outcome == "DAY6_EXIT":
            exit_price = float(closes[scan_i + FORWARD_DAYS])
            exit_day = FORWARD_DAYS

        if direction == "LONG":
            pnl_pct = (exit_price - entry_open) / entry_open * 100
        else:
            pnl_pct = (entry_open - exit_price) / entry_open * 100

        _add(signals, scan_i, pivot_i, sig_type, age, direction,
             entry_open, stop, target, outcome, exit_price, exit_day,
             pnl_pct, sym, sector, grade,
             vol_q_v, vol_c_v, rs_q_v, reg_arr, reg_score_arr,
             ret30_arr, dates)

    bp_last = -999  # cooldown counter for BULL_PROXY

    for i in range(WARMUP_BARS, n - FORWARD_DAYS):
        # UP_TRI: ages 0..3
        for age in range(0, 4):
            pb = i - age - LB
            if pb < LB or pb >= n:
                continue
            if not pl_v[pb]:
                continue
            atr = atr_v[pb]
            if np.isnan(atr) or atr <= 0:
                continue
            pivot_px = lows[pb]
            entry_est = closes[i]
            stop = round(pivot_px - STOP_MULT * atr, 2)
            if stop >= entry_est:
                continue
            append_sig(i, "UP_TRI", age, "LONG", pb, entry_est, stop)

        # DOWN_TRI: age 0 only
        pb = i - 0 - LB
        if LB <= pb < n and ph_v[pb]:
            atr = atr_v[pb]
            if not (np.isnan(atr) or atr <= 0):
                pivot_px = highs[pb]
                entry_est = closes[i]
                stop = round(pivot_px + STOP_MULT * atr, 2)
                if stop > entry_est:
                    append_sig(i, "DOWN_TRI", 0, "SHORT", pb, entry_est, stop)

        # BULL_PROXY: ages 0-1, looking back up to 19 bars
        # Replicates the production loop: at scan-day i, sweep j ∈ [max(LB, i-19), i].
        bp_last_local = bp_last
        for j in range(max(LB, i - 19), i + 1):
            atr = atr_v[j]
            if np.isnan(atr) or atr <= 0:
                continue
            if closes[j] < ema50v[j]:
                continue
            if (j - bp_last_local) <= SMC_COOLDOWN:
                continue
            if not nSZ_v[j]:
                continue
            br = highs[j] - lows[j]
            if br < 1e-6:
                continue
            cpos = (closes[j] - lows[j]) / br
            lwick = (min(opens[j], closes[j]) - lows[j]) / br
            if not (cpos >= BP_CLOSE_POS_MIN and
                    lwick >= BP_LOWER_WICK_MIN and
                    closes[j] > opens[j]):
                continue
            bp_last_local = j
            age = i - j
            if age > 1:
                continue
            stop_z = (szL_v[j] - 0.5 * atr
                      if not np.isnan(szL_v[j])
                      else lows[j] - atr)
            stop_z = round(stop_z, 2)
            if stop_z >= closes[i]:
                continue
            append_sig(i, "BULL_PROXY", age, "LONG", j, closes[i], stop_z)
        # Note: bp_last cooldown is per-scan-day (production uses local var),
        # so resetting outer bp_last is unnecessary.

    return signals


def _add(signals, scan_i, pivot_i, sig_type, age, direction,
         entry, stop, target, outcome, exit_price, exit_day,
         pnl_pct, sym, sector, grade,
         vol_q_v, vol_c_v, rs_q_v, reg_arr, reg_score_arr,
         ret30_arr, dates):
    rec = {
        "symbol": sym,
        "sector": sector,
        "grade": grade,
        "date": dates[scan_i].date(),
        "year": dates[scan_i].year,
        "month": dates[scan_i].month,
        "dow": dates[scan_i].dayofweek,
        "pivot_date": dates[pivot_i].date(),
        "signal_type": sig_type,
        "direction": direction,
        "age": age,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "exit_price": round(float(exit_price), 2),
        "exit_day": exit_day,
        "outcome": outcome,
        "pnl_pct": round(float(pnl_pct), 2),
        "vol_q": vol_q_v[scan_i],
        "vol_confirm": bool(vol_c_v[scan_i]),
        "rs_q": rs_q_v[scan_i],
        "sec_mom": "Neutral",  # historical sec_mom not computed (limitation)
        "regime": reg_arr[scan_i],
        "regime_score": int(reg_score_arr[scan_i]) if not np.isnan(reg_score_arr[scan_i]) else 0,
        "ret_30d_prior": float(ret30_arr[scan_i]) if not np.isnan(ret30_arr[scan_i]) else None,
    }
    # Score using production scorer logic
    score, _bd = score_signal({
        "age": age, "signal": sig_type,
        "regime": rec["regime"],
        "vol_confirm": rec["vol_confirm"],
        "sec_mom": rec["sec_mom"],
        "rs_q": rec["rs_q"],
    }, grade=grade)
    rec["score"] = int(score)
    signals.append(rec)


def main():
    # Load universe
    with open(UNIVERSE_CSV) as f:
        reader = csv.DictReader(f)
        universe = [(r["symbol"], r.get("sector", "Other"), r.get("grade", "B"))
                    for r in reader if r["symbol"].strip()]

    # Load nifty + compute V1 regime
    nifty = pd.read_parquet(NIFTY_PARQUET)
    nifty.index = pd.to_datetime(nifty.index)
    if nifty.index.tzinfo:
        nifty.index = nifty.index.tz_localize(None)
    regime_df = compute_v1_regime(nifty)

    # Filter to symbols that have cache files
    args_list = []
    missing = []
    for sym, sector, grade in universe:
        path = os.path.join(CACHE_DIR, f"{sym.replace('/', '_')}.parquet")
        if not os.path.exists(path):
            missing.append(sym)
            continue
        args_list.append((sym, sector, grade, regime_df, nifty["Close"], path))
    print(f"Stocks to replay: {len(args_list)} (missing: {len(missing)})")

    t0 = time.time()
    all_signals = []
    for i, args in enumerate(args_list, 1):
        sigs = replay_one_stock(args)
        all_signals.extend(sigs)
        if i % 20 == 0 or i == len(args_list):
            elapsed = time.time() - t0
            print(f"  [{i}/{len(args_list)}] {args[0]:18} → "
                  f"{len(sigs):>5} sigs (cumulative {len(all_signals):>7}) "
                  f"@ {elapsed:.1f}s")

    df = pd.DataFrame(all_signals)
    print(f"\nTotal signals: {len(df)}")
    if len(df):
        print(f"Signal type counts: {df['signal_type'].value_counts().to_dict()}")
        print(f"Outcome counts: {df['outcome'].value_counts().to_dict()}")
        print(f"Date range: {df['date'].min()} → {df['date'].max()}")

    df["date"] = pd.to_datetime(df["date"])
    df["pivot_date"] = pd.to_datetime(df["pivot_date"])
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"Wrote {OUT_PARQUET}  ({df.shape})")


if __name__ == "__main__":
    main()
