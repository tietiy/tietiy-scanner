# ── eod_prices_writer.py ─────────────────────────────
# Runs at 3:35 PM IST via eod_update.yml
# Fetches closing prices for all open positions
# Checks if close breached stop level
# Flags probable stop hits for trader awareness
# Writes eod_prices.json to output/
#
# IMPORTANT: This is a FLAG only — not a definitive exit
# Stop hits are confirmed at next day's open
# Page shows "⚠️ Possible stop hit — verify at open"
# Trader makes final decision
# ─────────────────────────────────────────────────────

import json
import os
import sys
from datetime import date, datetime

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import get_open_trades
from telegram_bot import send_exit_tomorrow          # ← F9 ADDED

# ── PATHS ─────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')
OUT_FILE = os.path.join(_OUTPUT, 'eod_prices.json')

# ── THRESHOLDS ────────────────────────────────────────
# STOP_BREACH_BUFFER: how close to stop = probable hit
# 0.0 = exactly at stop
# 0.005 = within 0.5% of stop = flag it
STOP_BREACH_BUFFER = 0.005


# ── HELPERS ───────────────────────────────────────────

def _fetch_eod_price(symbol, retries=2):
    """
    Fetch today's closing price for a symbol.
    Runs at 3:35 PM — market closed at 3:30 PM.
    Closing price should be settled.

    Returns (close_price, high_price, low_price)
    or (None, None, None) on failure.
    """
    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                period='5d',
                interval='1d',
                progress=False,
                auto_adjust=False,
            )

            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            df.index = pd.to_datetime(
                df.index, errors='coerce')
            if df.index.tzinfo:
                df.index = df.index.tz_localize(None)

            # Get today's row
            today_str  = date.today().isoformat()
            today_rows = df[
                df.index.strftime('%Y-%m-%d')
                == today_str
            ]

            if today_rows.empty:
                # Use last available row
                if len(df) > 0:
                    row   = df.iloc[-1]
                    close = float(row['Close'])
                    high  = float(row['High'])
                    low   = float(row['Low'])
                    return close, high, low
                continue

            row   = today_rows.iloc[-1]
            close = float(row['Close'])
            high  = float(row['High'])
            low   = float(row['Low'])
            return close, high, low

        except Exception as e:
            print(f"[eod_writer] Fetch attempt "
                  f"{attempt+1} failed {symbol}: {e}")

    return None, None, None


def _assess_stop(trade, close, high, low):
    """
    Assess whether stop was hit today.

    For LONG positions:
        Stop hit if low <= stop price
        (price traded at or below stop intraday)

    For SHORT positions:
        Stop hit if high >= stop price
        (price traded at or above stop intraday)

    Returns:
        stop_hit       : bool — definitive breach
        stop_probable  : bool — close near stop
        stop_status    : str  — 'HIT'/'PROBABLE'/'SAFE'
        note           : str  — explanation
        pnl_pct        : float — unrealized P&L at close
        pnl_r          : float — P&L in R multiples
    """
    try:
        stop      = float(trade.get('stop', 0) or 0)
        entry     = float(trade.get('entry', 0)
                    or trade.get('scan_price', 0) or 0)
        direction = trade.get('direction', 'LONG')

        if stop <= 0 or entry <= 0:
            return (False, False, 'UNKNOWN',
                    'Price data incomplete',
                    None, None)

        # Risk per share
        if direction == 'LONG':
            risk = entry - stop
        else:
            risk = stop - entry

        if risk <= 0:
            return (False, False, 'UNKNOWN',
                    'Invalid stop/entry',
                    None, None)

        # P&L at close
        if direction == 'LONG':
            pnl_pct = round(
                (close - entry) / entry * 100, 2)
            pnl_r   = round(
                (close - entry) / risk, 2)
        else:
            pnl_pct = round(
                (entry - close) / entry * 100, 2)
            pnl_r   = round(
                (entry - close) / risk, 2)

        # Stop hit assessment
        if direction == 'LONG':
            # Definitive: intraday low hit stop
            if low is not None and low <= stop:
                return (True, True, 'HIT',
                        f"Intraday low ₹{low:.2f} "
                        f"hit stop ₹{stop:.2f} — "
                        f"exit confirmed",
                        pnl_pct, pnl_r)

            # Probable: close within buffer of stop
            buffer = stop * (1 + STOP_BREACH_BUFFER)
            if close <= buffer:
                return (False, True, 'PROBABLE',
                        f"Close ₹{close:.2f} near "
                        f"stop ₹{stop:.2f} — "
                        f"verify at tomorrow open",
                        pnl_pct, pnl_r)

        elif direction == 'SHORT':
            # Definitive: intraday high hit stop
            if high is not None and high >= stop:
                return (True, True, 'HIT',
                        f"Intraday high ₹{high:.2f} "
                        f"hit stop ₹{stop:.2f} — "
                        f"exit confirmed",
                        pnl_pct, pnl_r)

            # Probable: close within buffer of stop
            buffer = stop * (1 - STOP_BREACH_BUFFER)
            if close >= buffer:
                return (False, True, 'PROBABLE',
                        f"Close ₹{close:.2f} near "
                        f"stop ₹{stop:.2f} — "
                        f"verify at tomorrow open",
                        pnl_pct, pnl_r)

        # Safe — stop not threatened
        return (False, False, 'SAFE',
                f"Close ₹{close:.2f} | "
                f"Stop ₹{stop:.2f} | "
                f"P&L {pnl_r:+.2f}R",
                pnl_pct, pnl_r)

    except Exception as e:
        print(f"[eod_writer] Assess error: {e}")
        return (False, False, 'UNKNOWN',
                'Assessment failed',
                None, None)


def _assess_exit_due(trade):
    """
    Check if this trade is due for exit tomorrow
    (Day 6 rule — exit at open of day 6).

    Returns True if exit is tomorrow or overdue.
    """
    try:
        exit_date = trade.get('exit_date', '')
        if not exit_date:
            return False
        today    = date.today()
        exit_dt  = date.fromisoformat(exit_date)
        days_left = (exit_dt - today).days
        # exit_date is the date to exit at open
        # if today = exit_date - 1, exit is tomorrow
        return days_left <= 1
    except Exception:
        return False


def _count_day(trade):
    """
    Returns current day number (1-6) of the trade.
    Day 1 = entry day. Day 6 = exit day.
    """
    try:
        signal_date = trade.get('date', '')
        if not signal_date:
            return None
        start    = date.fromisoformat(signal_date)
        today    = date.today()
        calendar_days = (today - start).days
        # Approximate trading days
        # Not holiday-aware here — JS handles display
        trading_days = max(1, int(calendar_days * 5/7))
        return min(trading_days + 1, 6)
    except Exception:
        return None


# ── MAIN FUNCTION ─────────────────────────────────────

def run_eod_update():
    """
    Main entry point. Called by eod_update.yml.

    Workflow:
    1. Load all open positions from signal_history.json
    2. For each position, fetch EOD close/high/low
    3. Assess stop hit status
    4. Check if exit due tomorrow (Day 6)
    5. Write eod_prices.json
    6. Fire exit-tomorrow Telegram alert (F9)
    """

    os.makedirs(_OUTPUT, exist_ok=True)

    today      = date.today().isoformat()
    fetch_time = datetime.utcnow().strftime('%H:%M IST')

    print(f"[eod_writer] Starting EOD update "
          f"for {today} at {fetch_time}")

    # Load open positions
    open_trades = get_open_trades()

    if not open_trades:
        print("[eod_writer] No open positions")
        _write_empty(today, fetch_time)
        return

    print(f"[eod_writer] Checking "
          f"{len(open_trades)} open positions")

    results          = []
    fetch_failed     = []
    hit_count        = 0
    probable_count   = 0
    exit_due_count   = 0
    exit_tomorrow_list = []                              # ← F9 ADDED

    for trade in open_trades:
        symbol    = trade.get('symbol', '')
        signal    = trade.get('signal', '')
        direction = trade.get('direction', 'LONG')
        entry     = trade.get('entry', None)
        stop      = trade.get('stop', None)
        sig_date  = trade.get('date', today)

        if not symbol:
            continue

        print(f"[eod_writer] Fetching EOD: {symbol}")

        # Fetch EOD prices
        close, high, low = _fetch_eod_price(symbol)

        if close is None:
            print(f"[eod_writer] Fetch failed: {symbol}")
            fetch_failed.append(symbol)
            results.append({
                'symbol':       symbol,
                'signal':       signal,
                'signal_date':  sig_date,
                'direction':    direction,
                'entry':        entry,
                'stop':         stop,
                'close':        None,
                'high':         None,
                'low':          None,
                'stop_hit':     False,
                'stop_probable': False,
                'stop_status':  'UNKNOWN',
                'note':         'Price fetch failed',
                'pnl_pct':      None,
                'pnl_r':        None,
                'exit_due':     _assess_exit_due(trade),
                'day_number':   _count_day(trade),
                'fetch_time':   fetch_time,
            })
            continue

        # Assess stop
        (stop_hit, stop_probable,
         stop_status, note,
         pnl_pct, pnl_r) = _assess_stop(
            trade, close, high, low)

        # Check exit due
        exit_due = _assess_exit_due(trade)

        if stop_hit or stop_status == 'HIT':
            hit_count += 1
        elif stop_probable:
            probable_count += 1

        if exit_due:
            exit_due_count += 1
            # ── F9: build payload for Telegram alert ──
            exit_tomorrow_list.append({
                'symbol':       symbol,
                'signal_type':  trade.get('signal_type',
                                signal),
                'entry_price':  entry or 0,
                'stop_price':   stop or 0,
                'target_price': trade.get(
                                'target_price', 0),
                'score':        trade.get('score', 0),
                'ltp':          round(close, 2),
            })

        results.append({
            'symbol':        symbol,
            'signal':        signal,
            'signal_date':   sig_date,
            'direction':     direction,
            'entry':         entry,
            'stop':          stop,
            'close':         round(close, 2),
            'high':          round(high, 2)
                             if high else None,
            'low':           round(low, 2)
                             if low else None,
            'stop_hit':      stop_hit,
            'stop_probable': stop_probable,
            'stop_status':   stop_status,
            'note':          note,
            'pnl_pct':       pnl_pct,
            'pnl_r':         pnl_r,
            'exit_due':      exit_due,
            'day_number':    _count_day(trade),
            'fetch_time':    fetch_time,
        })

        print(f"[eod_writer] {symbol} | "
              f"Close: {close:.2f} | "
              f"Stop: {stop_status} | "
              f"P&L: {pnl_r:+.2f}R"
              if pnl_r is not None
              else f"[eod_writer] {symbol} | "
                   f"Close: {close:.2f} | "
                   f"Stop: {stop_status}")

    # Write eod_prices.json
    output = {
        'date':            today,
        'fetched_at':      fetch_time,
        'open_positions':  len(open_trades),
        'hit_count':       hit_count,
        'probable_count':  probable_count,
        'exit_due_count':  exit_due_count,
        'fetch_failed':    fetch_failed,
        'results':         results,
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[eod_writer] Done → "
          f"HIT:{hit_count} "
          f"PROBABLE:{probable_count} "
          f"EXIT_DUE:{exit_due_count} "
          f"FAILED:{len(fetch_failed)}")

    # ── F9: fire exit-tomorrow Telegram alert ─────────
    # Fires after JSON is written — non-blocking
    if exit_tomorrow_list:
        print(f"[eod_writer] Sending exit-tomorrow "
              f"alert for {len(exit_tomorrow_list)} "
              f"signal(s)")
        send_exit_tomorrow(exit_tomorrow_list)


def _write_empty(today, fetch_time):
    """Write empty eod_prices.json when no positions."""
    output = {
        'date':           today,
        'fetched_at':     fetch_time,
        'open_positions': 0,
        'hit_count':      0,
        'probable_count': 0,
        'exit_due_count': 0,
        'fetch_failed':   [],
        'results':        [],
    }
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print("[eod_writer] Empty eod_prices.json written")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_eod_update()
