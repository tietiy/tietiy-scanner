# ── ltp_writer.py ────────────────────────────────────
# Fetches current LTP for all PENDING signals
# Runs every 5 min during market hours via cron
#
# L1 FIX: Use 1m intraday bars for LTP, not daily bars.
# Daily bars during market hours = yesterday's close (stale).
# 1m bars = current intraday price (~15 min delay yfinance).
#
# S3 FIX: Alert if LTP data is stale (>30 min old).
#
# V1.1 FIX:
# - BX3: Holiday/weekend guard — exits immediately
#        if market is closed, no fetch attempted
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

# ── TELEGRAM IMPORT ───────────────────────────────────
try:
    from telegram_bot import send_message, _esc
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ── PATHS ─────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

LTP_FILE = os.path.join(_OUTPUT, 'ltp_prices.json')

# IST = UTC + 5:30
_IST = timedelta(hours=5, minutes=30)

# S3: Stale threshold
STALE_MINUTES = 30


def _ist_now():
    """Returns current IST datetime."""
    return datetime.utcnow() + _IST


def _ist_now_str():
    """Returns current IST time as HH:MM AM/PM."""
    return _ist_now().strftime('%I:%M %p')


def _is_market_hours():
    """
    Returns True if currently in NSE market hours
    (9:15 AM - 3:30 PM IST).
    """
    now          = _ist_now()
    market_open  = now.replace(
        hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(
        hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


# ── BX3: TRADING DAY GUARD ────────────────────────────
def _is_trading_day() -> bool:
    """
    Returns True only on weekdays that are
    not NSE holidays.
    Reads nse_holidays.json from output/.
    LTP fetch should never run on holidays —
    yfinance returns no data and wastes Actions
    minutes.
    """
    today = date.today()
    # Weekend check
    if today.weekday() >= 5:
        return False
    # Holiday check
    try:
        holidays_file = os.path.join(
            _OUTPUT, 'nse_holidays.json')
        if os.path.exists(holidays_file):
            with open(holidays_file, 'r') as f:
                data = json.load(f)
            holidays = data.get('holidays', [])
            if today.isoformat() in holidays:
                return False
    except Exception:
        pass
    return True


def _parse_fetch_time(fetch_time_str, date_str):
    """
    Parse fetch_time like '11:02 AM' with
    date into datetime.
    """
    try:
        dt_str = f"{date_str} {fetch_time_str}"
        return datetime.strptime(
            dt_str, '%Y-%m-%d %I:%M %p')
    except Exception:
        return None


# ── S3: STALE CHECK ───────────────────────────────────
def _check_stale_ltp():
    """
    Check if existing LTP data is stale (>30 min old).
    Only alerts during market hours.
    Returns True if stale warning was sent.
    """
    if not _is_market_hours():
        return False

    if not os.path.exists(LTP_FILE):
        return False

    try:
        with open(LTP_FILE, 'r') as f:
            data = json.load(f)

        file_date  = data.get('date', '')
        fetch_time = data.get('fetch_time', '')

        if not file_date or not fetch_time:
            return False

        last_fetch = _parse_fetch_time(
            fetch_time, file_date)
        if not last_fetch:
            return False

        now         = _ist_now()
        age_minutes = (
            now - last_fetch
        ).total_seconds() / 60

        if age_minutes > STALE_MINUTES:
            print(f"[ltp] WARNING: Data is "
                  f"{age_minutes:.0f} min old")
            _send_stale_warning(
                age_minutes, fetch_time)
            return True

        return False

    except Exception as e:
        print(f"[ltp] Stale check error: {e}")
        return False


def _send_stale_warning(age_minutes, last_fetch_time):
    """Send Telegram alert for stale LTP data."""
    if not TELEGRAM_AVAILABLE:
        return

    try:
        lines = []
        lines.append('⚠️ *LTP DATA STALE*')
        lines.append('')
        lines.append(
            f'Last update: '
            f'{_esc(last_fetch_time)}')
        lines.append(
            f'Age: '
            f'{_esc(f"{age_minutes:.0f}")} minutes')
        lines.append('')
        lines.append(
            'Stop alerts may be delayed\\.')
        lines.append(
            'Check ltp\\_updater workflow\\.')

        send_message('\n'.join(lines))
        print("[ltp] Stale warning sent to Telegram")
    except Exception as e:
        print(f"[ltp] Stale warning send error: {e}")


# ── FETCH LTP ─────────────────────────────────────────
def _fetch_ltp(symbol, retries=2):
    """
    L1 FIX: Fetches intraday price via 1m bars.
    Falls back to 5m if 1m unavailable.
    Prev_close from a separate daily bars call.
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

            if isinstance(
                    df.columns, pd.MultiIndex):
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
            if isinstance(
                    daily.columns, pd.MultiIndex):
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
        pass

    return ltp, prev_close


# ── MAIN FUNCTION ─────────────────────────────────────
def run_ltp_update():
    """
    Main entry. Called from ltp_updater.yml
    every 5 min during market hours.

    V1.1 BX3 FIX: Exits immediately on holidays
    and weekends — no fetch attempted, no stale
    data written.
    """
    print("[ltp] Starting LTP update...")

    # BX3 FIX: Holiday/weekend guard
    # LTP fetch is meaningless on closed days —
    # NSE is not trading, yfinance returns no data
    if not _is_trading_day():
        today_str = date.today().isoformat()
        print(f"[ltp] {today_str} is a holiday "
              f"or weekend — skipping LTP fetch")
        return

    # ── S3: Check for stale data before update ────────
    _check_stale_ltp()

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

    # ── S3: Alert if high failure rate ────────────────
    total = success + failed
    if total > 0 and failed > 0:
        fail_pct = (failed / total) * 100
        if fail_pct >= 50:
            _send_high_failure_warning(
                failed, total, fetch_time)


def _send_high_failure_warning(
        failed, total, fetch_time):
    """Alert if >50% of LTP fetches failed."""
    if not TELEGRAM_AVAILABLE:
        return

    try:
        lines = []
        lines.append('⚠️ *LTP FETCH ISSUES*')
        lines.append('')
        lines.append(
            f'Failed: {_esc(str(failed))}'
            f'/{_esc(str(total))} symbols')
        lines.append(
            f'Time: {_esc(fetch_time)}')
        lines.append('')
        lines.append(
            'yfinance may be rate limited\\.')

        send_message('\n'.join(lines))
        print("[ltp] High failure warning sent")
    except Exception as e:
        print(f"[ltp] Warning send error: {e}")


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
