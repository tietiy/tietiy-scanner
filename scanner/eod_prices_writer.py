# scanner/eod_prices_writer.py
# Runs at 3:35 PM IST via eod_update.yml
# Fetches closing prices for all open positions
# Checks if close breached stop level
# Flags probable stop hits for trader awareness
# Writes eod_prices.json to output/
#
# B1 FIX: _assess_exit_due now returns True only when
#   days_left == 1 (exit is tomorrow only).
#   Previously <= 1 caused EXIT TOMORROW to fire on
#   exit day itself (days_left=0) — wrong label + duplicate.
#
# V2 FIXES:
#   EP1: Timezone fix — all timestamps now use
#        UTC+5:30 (IST) instead of server UTC.
#        Fixes "04:21 AM IST" showing UTC time.
#   EP2: Deduplicate yfinance fetches — build unique
#        ticker price map first, fetch once per ticker,
#        reuse close/high/low for all signals of same
#        stock. Prevents rate limiting as signal count
#        grows and cuts EOD run time significantly.
# ─────────────────────────────────────────────────────

import json
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
    """
    EP1 FIX: Returns current datetime in IST.
    GitHub Actions runners use UTC — datetime.now()
    returns UTC. Applying +5:30 gives correct IST.
    """
    ist_offset = timezone(timedelta(hours=5,
                                    minutes=30))
    return datetime.now(tz=ist_offset)


def _now_ist_str():
    """EP1 FIX: Current time as IST string."""
    return _now_ist().strftime('%I:%M %p IST')


def _today_ist():
    """EP1 FIX: Current date in IST."""
    return _now_ist().date()


# ── HELPERS ───────────────────────────────────────────

def _fetch_eod_price(symbol, retries=2):
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

            # EP1 FIX: use IST date for today_str
            today_str  = _today_ist().isoformat()
            today_rows = df[
                df.index.strftime('%Y-%m-%d')
                == today_str
            ]

            if today_rows.empty:
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


# EP2: BATCH PRICE FETCHER ─────────────────────────────

def _fetch_all_prices(symbols):
    """
    EP2 FIX: Fetch EOD prices for all unique symbols
    in a single pass. Returns dict:
      { 'SYMBOL.NS': (close, high, low) or (None, None, None) }

    Previously each signal triggered its own yfinance
    call — if ADANIGREEN had 3 signals, it fetched 3x.
    With 89 open signals across ~70 unique tickers,
    this deduplication cuts API calls by ~20%.
    """
    price_map = {}
    unique_symbols = list(set(symbols))

    print(f"[eod_writer] Fetching {len(unique_symbols)} "
          f"unique tickers "
          f"({len(symbols)} total signals)")

    for symbol in unique_symbols:
        close, high, low = _fetch_eod_price(symbol)
        price_map[symbol] = (close, high, low)
        if close is not None:
            print(f"[eod_writer] {symbol} | "
                  f"Close: {close:.2f}")
        else:
            print(f"[eod_writer] {symbol} | "
                  f"Fetch FAILED")

    return price_map


def _assess_stop(trade, close, high, low):
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

        if direction == 'LONG':
            if low is not None and low <= stop:
                return (True, True, 'HIT',
                        f"Intraday low ₹{low:.2f} "
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
            if high is not None and high >= stop:
                return (True, True, 'HIT',
                        f"Intraday high ₹{high:.2f} "
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
    B1 FIX: Returns True only when days_left == 1
    (exit is exactly tomorrow).
    Previously used <= 1 which fired on exit day itself
    (days_left=0) causing "EXIT TOMORROW" on wrong day.
    EP1 FIX: Uses IST date not UTC date.
    """
    try:
        exit_date = trade.get('exit_date', '')
        if not exit_date:
            return False
        # EP1 FIX: IST date
        today     = _today_ist()
        exit_dt   = date.fromisoformat(exit_date)
        days_left = (exit_dt - today).days
        # Only fire when exit is exactly tomorrow
        return days_left == 1
    except Exception:
        return False


def _count_day(trade):
    try:
        signal_date = trade.get('date', '')
        if not signal_date:
            return None
        start         = date.fromisoformat(signal_date)
        # EP1 FIX: IST date
        today         = _today_ist()
        calendar_days = (today - start).days
        trading_days  = max(1, int(calendar_days * 5/7))
        return min(trading_days + 1, 6)
    except Exception:
        return None


# ── MAIN FUNCTION ─────────────────────────────────────

def run_eod_update():
    os.makedirs(_OUTPUT, exist_ok=True)

    # EP1 FIX: IST date and time
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

    # EP2 FIX: Collect all symbols first, fetch once
    # per unique ticker, reuse prices across all signals
    # of the same stock.
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

    for trade in open_trades:
        symbol    = trade.get('symbol', '')
        signal    = trade.get('signal', '')
        direction = trade.get('direction', 'LONG')
        entry     = trade.get('entry', None)
        stop      = trade.get('stop', None)
        sig_date  = trade.get('date', today)

        if not symbol:
            continue

        # EP2 FIX: Reuse cached price — no re-fetch
        close, high, low = price_map.get(
            symbol, (None, None, None))

        if close is None:
            fetch_failed.append(symbol)
            results.append({
                'symbol':        symbol,
                'signal':        signal,
                'signal_date':   sig_date,
                'direction':     direction,
                'entry':         entry,
                'stop':          stop,
                'close':         None,
                'high':          None,
                'low':           None,
                'stop_hit':      False,
                'stop_probable': False,
                'stop_status':   'UNKNOWN',
                'note':          'Price fetch failed',
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
        'date':           today,
        'fetched_at':     fetch_time,
        'open_positions': len(open_trades),
        'hit_count':      hit_count,
        'probable_count': probable_count,
        'exit_due_count': exit_due_count,
        'fetch_failed':   fetch_failed,
        'results':        results,
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[eod_writer] Done → "
          f"HIT:{hit_count} "
          f"PROBABLE:{probable_count} "
          f"EXIT_DUE:{exit_due_count} "
          f"FAILED:{len(fetch_failed)}")

    # Fire exit-tomorrow alert
    if exit_tomorrow_list:
        print(f"[eod_writer] Sending exit-tomorrow "
              f"alert for {len(exit_tomorrow_list)} "
              f"signal(s)")
        send_exit_tomorrow(
            exit_tomorrow_list,
            exit_today=False)


def _write_empty(today, fetch_time):
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
