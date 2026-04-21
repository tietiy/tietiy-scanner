# scanner/eod_prices_writer.py
# Runs at 3:35 PM IST via eod_master.yml
# Fetches closing prices for all open positions
# Checks if close breached stop level
# Flags probable stop hits for trader awareness
# Writes eod_prices.json to output/
#
# B1 FIX: _assess_exit_due now returns True only when
#   days_left == 1 (exit is tomorrow only).
#
# V2 FIXES:
#   EP1: Timezone fix — UTC+5:30 IST timestamps.
#   EP2: Deduplicate yfinance fetches — unique ticker
#        price map, fetch once per ticker.
#   EP3: nan guard in _assess_stop — close=nan was
#        triggering false HIT:7 when EOD runs before
#        market open (1 AM run). Any nan price now
#        returns UNKNOWN immediately, no assessment.
#
# CRIT-01 FIX (Apr 21 2026 night):
#   - Fetch OPEN price in addition to close/high/low.
#   - Store full OHLC in results array per symbol.
#   - Add ohlc_by_symbol nested dict to top-level
#     output for outcome_evaluator schema compatibility.
#   - Schema now writes BOTH:
#       (a) flat results[] for stop_check/telegram (legacy)
#       (b) ohlc_by_symbol{symbol:{date:{ohlc}}} for
#           outcome_evaluator._build_ohlc_from_eod()
#   - Outcome_evaluator's CRIT-02 fix reads (b).
# ─────────────────────────────────────────────────────

import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import get_open_trades
from telegram_bot import send_exit_tomorrow

# ── PATHS ─────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')
OUT_FILE = os.path.join(_OUTPUT, 'eod_prices.json')

# ── THRESHOLDS ────────────────────────────────────────
STOP_BREACH_BUFFER = 0.005


# ── EP1: IST TIMESTAMP HELPERS ────────────────────────

def _now_ist():
    ist_offset = timezone(timedelta(hours=5,
                                    minutes=30))
    return datetime.now(tz=ist_offset)


def _now_ist_str():
    return _now_ist().strftime('%I:%M %p IST')


def _today_ist():
    return _now_ist().date()


# ── EP3: NAN HELPER ───────────────────────────────────

def _is_nan(v):
    """
    EP3 FIX: Returns True if value is None or
    float NaN. yfinance returns float('nan') when
    market is closed or data unavailable.
    Used to guard _assess_stop before any arithmetic.
    """
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


# ── HELPERS ───────────────────────────────────────────

def _fetch_eod_price(symbol, retries=2):
    """
    CRIT-01 FIX: Now returns 4-tuple (open, close, high, low)
    instead of 3-tuple (close, high, low). open price needed
    for outcome_evaluator's D6A logic and accurate Day 6
    outcome calculations.
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

            today_str  = _today_ist().isoformat()
            today_rows = df[
                df.index.strftime('%Y-%m-%d')
                == today_str
            ]

            if today_rows.empty:
                if len(df) > 0:
                    row    = df.iloc[-1]
                    open_  = float(row['Open'])
                    close  = float(row['Close'])
                    high   = float(row['High'])
                    low    = float(row['Low'])
                    return open_, close, high, low
                continue

            row    = today_rows.iloc[-1]
            open_  = float(row['Open'])
            close  = float(row['Close'])
            high   = float(row['High'])
            low    = float(row['Low'])
            return open_, close, high, low

        except Exception as e:
            print(f"[eod_writer] Fetch attempt "
                  f"{attempt+1} failed {symbol}: {e}")

    return None, None, None, None


# EP2: BATCH PRICE FETCHER ─────────────────────────────

def _fetch_all_prices(symbols):
    """
    CRIT-01 FIX: price_map now stores 4-tuple
    (open, close, high, low) per symbol.
    """
    price_map = {}
    unique_symbols = list(set(symbols))

    print(f"[eod_writer] Fetching {len(unique_symbols)} "
          f"unique tickers "
          f"({len(symbols)} total signals)")

    for symbol in unique_symbols:
        open_, close, high, low = _fetch_eod_price(symbol)
        price_map[symbol] = (open_, close, high, low)
        if close is not None and not _is_nan(close):
            print(f"[eod_writer] {symbol} | "
                  f"O:{open_:.2f} C:{close:.2f}"
                  if open_ is not None and not _is_nan(open_)
                  else f"[eod_writer] {symbol} | "
                       f"Close: {close:.2f}")
        else:
            print(f"[eod_writer] {symbol} | "
                  f"Close: nan")

    return price_map


def _assess_stop(trade, close, high, low):
    # EP3 FIX: nan guard — must be first check.
    if _is_nan(close):
        return (False, False, 'UNKNOWN',
                'No price data — market closed '
                'or fetch before open',
                None, None)

    try:
        stop      = float(trade.get('stop', 0) or 0)
        entry     = float(trade.get('entry', 0)
                    or trade.get('scan_price', 0) or 0)
        direction = trade.get('direction', 'LONG')

        if stop <= 0 or entry <= 0:
            return (False, False, 'UNKNOWN',
                    'Price data incomplete',
                    None, None)

        if direction == 'LONG':
            risk = entry - stop
        else:
            risk = stop - entry

        if risk <= 0:
            return (False, False, 'UNKNOWN',
                    'Invalid stop/entry',
                    None, None)

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

        # EP3 FIX: also guard high/low before use
        low_safe  = low  if not _is_nan(low)  else None
        high_safe = high if not _is_nan(high) else None

        if direction == 'LONG':
            if low_safe is not None and low_safe <= stop:
                return (True, True, 'HIT',
                        f"Intraday low ₹{low_safe:.2f} "
                        f"hit stop ₹{stop:.2f} — "
                        f"exit confirmed",
                        pnl_pct, pnl_r)

            buffer = stop * (1 + STOP_BREACH_BUFFER)
            if close <= buffer:
                return (False, True, 'PROBABLE',
                        f"Close ₹{close:.2f} near "
                        f"stop ₹{stop:.2f} — "
                        f"verify at tomorrow open",
                        pnl_pct, pnl_r)

        elif direction == 'SHORT':
            if high_safe is not None and high_safe >= stop:
                return (True, True, 'HIT',
                        f"Intraday high ₹{high_safe:.2f} "
                        f"hit stop ₹{stop:.2f} — "
                        f"exit confirmed",
                        pnl_pct, pnl_r)

            buffer = stop * (1 - STOP_BREACH_BUFFER)
            if close >= buffer:
                return (False, True, 'PROBABLE',
                        f"Close ₹{close:.2f} near "
                        f"stop ₹{stop:.2f} — "
                        f"verify at tomorrow open",
                        pnl_pct, pnl_r)

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
    B1 FIX: Returns True only when days_left == 1.
    EP1 FIX: Uses IST date not UTC date.
    """
    try:
        exit_date = trade.get('exit_date', '')
        if not exit_date:
            return False
        today     = _today_ist()
        exit_dt   = date.fromisoformat(exit_date)
        days_left = (exit_dt - today).days
        return days_left == 1
    except Exception:
        return False


def _count_day(trade):
    try:
        signal_date = trade.get('date', '')
        if not signal_date:
            return None
        start         = date.fromisoformat(signal_date)
        today         = _today_ist()
        calendar_days = (today - start).days
        trading_days  = max(1, int(calendar_days * 5/7))
        return min(trading_days + 1, 6)
    except Exception:
        return None


# ── MAIN FUNCTION ─────────────────────────────────────

def run_eod_update():
    """
    CRIT-01 FIX: Output schema now includes
    ohlc_by_symbol nested dict for outcome_evaluator
    compatibility. Existing flat results[] preserved
    for stop_check/telegram backward compatibility.
    """
    os.makedirs(_OUTPUT, exist_ok=True)

    today      = _today_ist().isoformat()
    fetch_time = _now_ist_str()

    print(f"[eod_writer] Starting EOD update "
          f"for {today} at {fetch_time}")

    open_trades = get_open_trades()

    if not open_trades:
        print("[eod_writer] No open positions")
        _write_empty(today, fetch_time)
        return

    print(f"[eod_writer] Checking "
          f"{len(open_trades)} open positions")

    all_symbols = [
        t.get('symbol', '')
        for t in open_trades
        if t.get('symbol', '')
    ]
    price_map = _fetch_all_prices(all_symbols)

    results            = []
    fetch_failed       = []
    hit_count          = 0
    probable_count     = 0
    exit_due_count     = 0
    exit_tomorrow_list = []

    # CRIT-01: ohlc_by_symbol nested dict for
    # outcome_evaluator schema compatibility.
    # Schema: { symbol: { date_str: {open,high,low,close} } }
    ohlc_by_symbol = {}

    for trade in open_trades:
        symbol    = trade.get('symbol', '')
        signal    = trade.get('signal', '')
        direction = trade.get('direction', 'LONG')
        entry     = trade.get('entry', None)
        stop      = trade.get('stop', None)
        sig_date  = trade.get('date', today)

        if not symbol:
            continue

        # CRIT-01: unpack 4-tuple now (open, close, high, low)
        open_, close, high, low = price_map.get(
            symbol, (None, None, None, None))

        # EP3 FIX: treat nan same as None — no data
        if close is None or _is_nan(close):
            fetch_failed.append(symbol)
            results.append({
                'symbol':        symbol,
                'signal':        signal,
                'signal_date':   sig_date,
                'direction':     direction,
                'entry':         entry,
                'stop':          stop,
                'open':          None,
                'close':         None,
                'high':          None,
                'low':           None,
                'stop_hit':      False,
                'stop_probable': False,
                'stop_status':   'UNKNOWN',
                'note':          'No price data',
                'pnl_pct':       None,
                'pnl_r':         None,
                'exit_due':      _assess_exit_due(trade),
                'day_number':    _count_day(trade),
                'fetch_time':    fetch_time,
            })
            continue

        (stop_hit, stop_probable,
         stop_status, note,
         pnl_pct, pnl_r) = _assess_stop(
            trade, close, high, low)

        exit_due = _assess_exit_due(trade)

        if stop_hit or stop_status == 'HIT':
            hit_count += 1
        elif stop_probable:
            probable_count += 1

        if exit_due:
            exit_due_count += 1
            exit_tomorrow_list.append({
                'symbol':       symbol,
                'signal':       trade.get('signal', signal),
                'signal_type':  trade.get('signal_type', signal),
                'direction':    direction,
                'entry':        entry or 0,
                'entry_price':  entry or 0,
                'stop':         stop or 0,
                'stop_price':   stop or 0,
                'target_price': trade.get('target_price', 0),
                'score':        trade.get('score', 0),
                'ltp':          round(close, 2),
                'close':        round(close, 2),
            })

        # CRIT-01: round open price safely
        open_safe = (round(open_, 2)
                     if open_ is not None
                     and not _is_nan(open_)
                     else None)

        results.append({
            'symbol':        symbol,
            'signal':        signal,
            'signal_date':   sig_date,
            'direction':     direction,
            'entry':         entry,
            'stop':          stop,
            'open':          open_safe,
            'close':         round(close, 2),
            'high':          round(high, 2)
                             if high and not _is_nan(high)
                             else None,
            'low':           round(low, 2)
                             if low and not _is_nan(low)
                             else None,
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

        # CRIT-01: Build ohlc_by_symbol entry for
        # outcome_evaluator. Only add if close is valid.
        # Multiple signals per symbol → write once per
        # symbol per date (overwrite is safe — same data).
        if symbol not in ohlc_by_symbol:
            ohlc_by_symbol[symbol] = {}

        ohlc_by_symbol[symbol][today] = {
            'open':  open_safe if open_safe is not None
                                  else round(close, 2),
            'high':  round(high, 2)
                     if high and not _is_nan(high)
                     else round(close, 2),
            'low':   round(low, 2)
                     if low and not _is_nan(low)
                     else round(close, 2),
            'close': round(close, 2),
        }

        if pnl_r is not None:
            print(f"[eod_writer] {symbol} | "
                  f"Close: {close:.2f} | "
                  f"Stop: {stop_status} | "
                  f"P&L: {pnl_r:+.2f}R")
        else:
            print(f"[eod_writer] {symbol} | "
                  f"Close: {close:.2f} | "
                  f"Stop: {stop_status}")

    output = {
        'date':            today,
        'fetched_at':      fetch_time,
        'open_positions':  len(open_trades),
        'hit_count':       hit_count,
        'probable_count':  probable_count,
        'exit_due_count':  exit_due_count,
        'fetch_failed':    fetch_failed,
        'results':         results,
        # CRIT-01: nested dict for outcome_evaluator
        'ohlc_by_symbol':  ohlc_by_symbol,
        'schema_version':  2,
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[eod_writer] Done → "
          f"HIT:{hit_count} "
          f"PROBABLE:{probable_count} "
          f"EXIT_DUE:{exit_due_count} "
          f"FAILED:{len(fetch_failed)} "
          f"OHLC_SYMBOLS:{len(ohlc_by_symbol)}")

    if exit_tomorrow_list:
        print(f"[eod_writer] Sending exit-tomorrow "
              f"alert for {len(exit_tomorrow_list)} "
              f"signal(s)")
        send_exit_tomorrow(
            exit_tomorrow_list,
            exit_today=False)


def _write_empty(today, fetch_time):
    output = {
        'date':            today,
        'fetched_at':      fetch_time,
        'open_positions':  0,
        'hit_count':       0,
        'probable_count':  0,
        'exit_due_count':  0,
        'fetch_failed':    [],
        'results':         [],
        'ohlc_by_symbol':  {},
        'schema_version':  2,
    }
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print("[eod_writer] Empty eod_prices.json written")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_eod_update()
