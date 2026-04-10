# ── ltp_writer.py ────────────────────────────────────
# Fetches current LTP for all PENDING signals
# Runs every 5 min during market hours via cron
#
# L1 FIX: Use 1m intraday bars for LTP, not daily bars.
# Daily bars during market hours = yesterday's close (stale).
# 1m bars = current intraday price (~15 min delay yfinance).
#
# Schema:
#   {
#     "date": "2026-04-07",
#     "fetch_time": "11:02 AM",
#     "prices": {
#       "TATASTEEL.NS": {
#         "ltp":        195.48,
#         "change_pct": +2.67,
#         "fetch_time": "11:02 AM"
#       }
#     }
#   }
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import load_history

# ── PATHS ─────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

LTP_FILE = os.path.join(_OUTPUT, 'ltp_prices.json')

# IST = UTC + 5:30
_IST = timedelta(hours=5, minutes=30)


def _ist_now_str():
    """Returns current IST time as HH:MM AM/PM."""
    return (datetime.utcnow() + _IST).strftime('%I:%M %p')


# ── FETCH LTP ─────────────────────────────────────────
def _fetch_ltp(symbol, retries=2):
    """
    L1 FIX: Fetches intraday price via 1m bars.
    Falls back to 5m if 1m unavailable.
    Prev_close from a separate daily bars call.

    Old code used interval='1d' which returns
    yesterday's close unchanged all day — that
    was the LTP-stuck bug.
    """
    ltp = None

    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(symbol)

            # ── 1m first (real intraday) ───────────────
            df = ticker.history(
                period      = '1d',
                interval    = '1m',
                auto_adjust = False,
            )

            # ── 5m fallback ────────────────────────────
            if df is None or df.empty:
                df = ticker.history(
                    period      = '1d',
                    interval    = '5m',
                    auto_adjust = False,
                )

            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [
                    c[0] for c in df.columns]

            if df.index.tzinfo:
                df.index = df.index.tz_localize(None)

            if df.empty:
                continue

            last = float(df['Close'].iloc[-1])
            if last > 0:
                ltp = last
                break

        except Exception as e:
            print(f"[ltp] Fetch error "
                  f"{symbol} attempt {attempt}: {e}")

    if ltp is None:
        return None, None

    # ── Prev close from daily bars ─────────────────────
    prev_close = ltp  # safe default
    try:
        daily = yf.Ticker(symbol).history(
            period      = '5d',
            interval    = '1d',
            auto_adjust = False,
        )
        if daily is not None and not daily.empty:
            if isinstance(daily.columns, pd.MultiIndex):
                daily.columns = [
                    c[0] for c in daily.columns]
            if daily.index.tzinfo:
                daily.index = \
                    daily.index.tz_localize(None)
            if len(daily) >= 2:
                prev_close = float(
                    daily['Close'].iloc[-2])
            else:
                prev_close = float(
                    daily['Close'].iloc[-1])
    except Exception:
        pass  # keep ltp as prev_close fallback

    return ltp, prev_close


# ── MAIN FUNCTION ─────────────────────────────────────
def run_ltp_update():
    """
    Main entry. Called from ltp_updater.yml
    every 5 min during market hours.

    Only fetches prices for PENDING signals —
    not the full universe.
    """
    print("[ltp] Starting LTP update...")

    today_str  = date.today().isoformat()
    fetch_time = _ist_now_str()

    # Load PENDING signals only
    history = load_history()
    pending = [
        s for s in history
        if s.get('result') == 'PENDING'
    ]

    if not pending:
        print("[ltp] No pending signals")
        _write_ltp({}, today_str, fetch_time)
        return

    # Deduplicate symbols
    symbols = list({
        s.get('symbol', '')
        for s in pending
        if s.get('symbol', '')
    })

    print(f"[ltp] Fetching {len(symbols)} "
          f"symbols... ({fetch_time})")

    prices  = {}
    success = 0
    failed  = 0

    for symbol in symbols:
        ltp, prev_close = _fetch_ltp(symbol)

        if ltp is None:
            print(f"[ltp] Failed: {symbol}")
            failed += 1
            continue

        change_pct = 0.0
        if prev_close and prev_close > 0:
            change_pct = round(
                (ltp - prev_close) /
                prev_close * 100, 2)

        prices[symbol] = {
            'ltp':        round(ltp, 2),
            'prev_close': round(prev_close, 2)
                          if prev_close else None,
            'change_pct': change_pct,
            'fetch_time': fetch_time,
        }
        success += 1

        sym_clean = symbol.replace('.NS', '')
        arrow     = '▲' if change_pct >= 0 else '▼'
        print(f"[ltp] {sym_clean} "
              f"₹{ltp:.2f} "
              f"{arrow}{abs(change_pct):.1f}%")

    _write_ltp(prices, today_str, fetch_time)

    print(f"[ltp] Complete — "
          f"success:{success} "
          f"failed:{failed} "
          f"time:{fetch_time}")


# ── WRITE ltp_prices.json ─────────────────────────────
def _write_ltp(prices, today_str, fetch_time):
    os.makedirs(_OUTPUT, exist_ok=True)

    data = {
        'date':       today_str,
        'fetch_time': fetch_time,
        'count':      len(prices),
        'prices':     prices,
    }

    try:
        with open(LTP_FILE, 'w') as f:
            json.dump(
                data, f, indent=2, default=str)
        print(f"[ltp] ltp_prices.json written "
              f"→ {len(prices)} prices")
    except Exception as e:
        print(f"[ltp] Write failed: {e}")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_ltp_update()
