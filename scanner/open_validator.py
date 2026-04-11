# scanner/open_validator.py
# Fetches actual open prices at 9:27 AM IST
# for PENDING signals whose ENTRY DATE is today.
#
# KEY FIX: signals are dated the detection day (e.g. Apr 7).
# Entry is the next trading day (e.g. Apr 8).
# This validator runs at 9:27 AM on the ENTRY date.
# So filter by entry_date == today, not signal_date == today.
#
# ALSO FIXED: _fetch_open uses 1m intraday bars, first bar Open.
# Daily bars not available at 9:27 AM (candle not closed yet).
#
# TELEGRAM FIX: Now sends open validation results to Telegram.
#
# S1 FIX: Skip if already validated today (for retry crons).
# ─────────────────────────────────────────────────────

import os
import sys
import json
import time
from datetime import date, datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)

# ── TELEGRAM IMPORT ───────────────────────────────────
try:
    from telegram_bot import send_open_validation
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[open_validator] telegram_bot not available")

# ── PATHS ─────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

OPEN_PRICES_FILE = os.path.join(_OUTPUT, 'open_prices.json')
HOLIDAYS_FILE    = os.path.join(_OUTPUT, 'nse_holidays.json')

# ── THRESHOLDS ────────────────────────────────────────
GAP_SKIP_PCT    = 3.0
GAP_WARNING_PCT = 1.5


# ── HOLIDAY HELPERS ───────────────────────────────────
def _load_holidays():
    try:
        with open(HOLIDAYS_FILE, 'r') as f:
            return json.load(f).get('holidays', [])
    except Exception:
        return []


def _is_trading_day(d, holidays):
    return d.weekday() < 5 and d.strftime('%Y-%m-%d') not in holidays


def _next_trading_day(from_date, holidays):
    """Returns the next trading day after from_date."""
    cur = from_date + timedelta(days=1)
    for _ in range(30):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)
    return cur


# ── SKIP-IF-DONE CHECK ────────────────────────────────
def _already_validated_today():
    """
    Returns True if open_prices.json exists with today's date
    and has at least one result OR explicitly marked complete.
    Used by retry crons to skip if primary run succeeded.
    """
    today_str = date.today().isoformat()
    
    if not os.path.exists(OPEN_PRICES_FILE):
        return False
    
    try:
        with open(OPEN_PRICES_FILE, 'r') as f:
            data = json.load(f)
        
        if data.get('date') != today_str:
            return False
        
        # Has results OR marked as "no entries today"
        results = data.get('results', [])
        if len(results) > 0:
            print(f"[open_validator] Already validated today "
                  f"({len(results)} signals) — skipping")
            return True
        
        # Check if it was a "no entries" day
        if data.get('count') == 0:
            print("[open_validator] Already ran today "
                  "(0 entries) — skipping")
            return True
        
        return False
        
    except Exception as e:
        print(f"[open_validator] Error checking existing: {e}")
        return False


# ── FETCH OPEN PRICE ──────────────────────────────────
def _fetch_open(symbol, retries=3):
    """
    Fetches actual 9:15 AM open price using 1-minute bars.
    Takes the FIRST bar of today's session = market open price.
    Daily bars are NOT used — daily candle not closed at 9:27 AM.
    """
    for attempt in range(retries):
        try:
            df = yf.download(
                symbol,
                period      = '1d',
                interval    = '1m',
                progress    = False,
                auto_adjust = False,
            )

            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]

                # Normalize to IST
                if df.index.tzinfo is not None:
                    df.index = df.index.tz_convert('Asia/Kolkata')
                else:
                    df.index = df.index.tz_localize(
                        'UTC').tz_convert('Asia/Kolkata')

                today_str  = date.today().strftime('%Y-%m-%d')
                today_bars = df[
                    df.index.strftime('%Y-%m-%d') == today_str
                ]

                if not today_bars.empty:
                    open_price = float(today_bars['Open'].iloc[0])
                    if open_price > 0:
                        bar_time = today_bars.index[0].strftime('%H:%M')
                        print(f"[open_validator] {symbol.replace('.NS','')} "
                              f"open=₹{open_price:.2f} "
                              f"bar={bar_time} IST "
                              f"({len(today_bars)} bars)")
                        return open_price
                else:
                    print(f"[open_validator] {symbol.replace('.NS','')} "
                          f"— {len(df)} 1m bars but none match {today_str}")

        except Exception as e:
            print(f"[open_validator] {symbol.replace('.NS','')} "
                  f"attempt {attempt+1} error: {e}")

        if attempt < retries - 1:
            time.sleep(3)

    # Fallback: 5-minute bars
    print(f"[open_validator] {symbol.replace('.NS','')} "
          f"— trying 5m fallback")
    try:
        df = yf.download(
            symbol,
            period      = '1d',
            interval    = '5m',
            progress    = False,
            auto_adjust = False,
        )
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if df.index.tzinfo is not None:
                df.index = df.index.tz_convert('Asia/Kolkata')
            else:
                df.index = df.index.tz_localize(
                    'UTC').tz_convert('Asia/Kolkata')
            today_str  = date.today().strftime('%Y-%m-%d')
            today_bars = df[
                df.index.strftime('%Y-%m-%d') == today_str
            ]
            if not today_bars.empty:
                open_price = float(today_bars['Open'].iloc[0])
                if open_price > 0:
                    print(f"[open_validator] {symbol.replace('.NS','')} "
                          f"5m fallback open=₹{open_price:.2f}")
                    return open_price
    except Exception as e:
        print(f"[open_validator] {symbol.replace('.NS','')} "
              f"5m fallback error: {e}")

    print(f"[open_validator] {symbol.replace('.NS','')} "
          f"— all fetches failed")
    return None


# ── GAP CALCULATOR ────────────────────────────────────
def _calc_gap(scan_price, actual_open, direction):
    try:
        sp      = float(scan_price)
        op      = float(actual_open)
        if sp <= 0:
            return 0.0
        raw_pct = (op - sp) / sp * 100
        # Positive = favourable for the trade direction
        return round(raw_pct if direction == 'LONG' else -raw_pct, 2)
    except Exception:
        return 0.0


def _gap_status(gap_pct):
    abs_gap = abs(gap_pct)
    if abs_gap >= GAP_SKIP_PCT:
        return 'SKIP', f"Gap {gap_pct:+.1f}% — skip this signal (>{GAP_SKIP_PCT:.0f}%)"
    if abs_gap >= GAP_WARNING_PCT:
        return 'WARNING', f"Gap {gap_pct:+.1f}% — reduced R:R, trade with caution"
    return 'OK', ''


# ── MAIN FUNCTION ─────────────────────────────────────
def run_open_validation():
    """
    Runs at 9:27 AM IST on each trading day.

    Finds PENDING signals whose ENTRY DATE is today.
    Entry date = next trading day after signal detection date.
    Example: signal detected Apr 7 → entry date Apr 8 → run Apr 8.

    Fetches actual open price from yfinance 1m bars.
    Updates actual_open in signal_history.json.
    Writes open_prices.json for frontend.
    Sends results to Telegram.
    
    S1 FIX: Skips if already validated today (for retry crons).
    """
    print("[open_validator] Starting...")

    # ── S1: Skip if already done today ────────────────
    if _already_validated_today():
        return

    today     = date.today()
    today_str = today.strftime('%Y-%m-%d')
    now_ist   = datetime.now().strftime('%H:%M IST')

    print(f"[open_validator] Entry date: {today_str} · {now_ist}")

    holidays = _load_holidays()

    # Load history
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[open_validator] Cannot load history: {e}")
        return

    history = data.get('history', [])

    # ── KEY FIX ───────────────────────────────────────
    # Find PENDING signals whose entry date == today.
    # Entry date = next trading day after signal date.
    # Do NOT filter by signal_date == today.
    # ─────────────────────────────────────────────────
    pending_entry_today = []
    for s in history:
        if s.get('result')  != 'PENDING': continue
        if s.get('action')  != 'TOOK':    continue
        if s.get('actual_open') is not None: continue  # already fetched

        sig_date_str = s.get('date', '')
        if not sig_date_str:
            continue

        try:
            sig_date   = datetime.strptime(
                sig_date_str, '%Y-%m-%d').date()
            entry_date = _next_trading_day(sig_date, holidays)
            if entry_date == today:
                pending_entry_today.append(s)
        except Exception:
            continue

    print(f"[open_validator] Signals entering today: "
          f"{len(pending_entry_today)}")

    if not pending_entry_today:
        print("[open_validator] No signals entering today "
              "— writing empty output")
        _write_open_prices([], today_str, now_ist)

        # ── TELEGRAM: No entries today ────────────────
        if TELEGRAM_AVAILABLE:
            try:
                send_open_validation([], [])
                print("[open_validator] Telegram sent (0 entries)")
            except Exception as e:
                print(f"[open_validator] Telegram error: {e}")
        return

    # Log what we're processing
    for s in pending_entry_today:
        sym = (s.get('symbol') or '').replace('.NS', '')
        print(f"[open_validator]   → {sym} "
              f"{s.get('signal','')} "
              f"detected={s.get('date','')} "
              f"scan_price={s.get('scan_price') or s.get('entry','?')}")

    results     = []
    updated     = 0
    history_map = {s.get('id'): i for i, s in enumerate(history)}

    # Deduplicate symbols — fetch each once
    symbol_to_sigs = {}
    for sig in pending_entry_today:
        sym = sig.get('symbol', '')
        if sym not in symbol_to_sigs:
            symbol_to_sigs[sym] = []
        symbol_to_sigs[sym].append(sig)

    fetched_prices = {}  # sym → open_price or None

    for sym in symbol_to_sigs:
        if not sym:
            continue
        open_price = _fetch_open(sym)
        fetched_prices[sym] = open_price

    # Apply results to all matching signals
    for sym, sigs in symbol_to_sigs.items():
        actual_open = fetched_prices.get(sym)

        for sig in sigs:
            direction  = sig.get('direction', 'LONG')
            scan_price = (sig.get('scan_price') or
                          sig.get('entry')      or
                          sig.get('entry_est'))

            if actual_open is None:
                results.append({
                    'symbol':      sym,
                    'signal':      sig.get('signal', ''),
                    'signal_date': sig.get('date', ''),
                    'actual_open': None,
                    'scan_price':  scan_price,
                    'gap_pct':     None,
                    'gap_status':  'UNKNOWN',
                    'note':        'Price fetch failed',
                    'fetch_time':  now_ist,
                })
                continue

            gap_pct            = _calc_gap(scan_price, actual_open, direction) \
                                  if scan_price else 0.0
            gap_stat, gap_note = _gap_status(gap_pct)

            results.append({
                'symbol':      sym,
                'signal':      sig.get('signal', ''),
                'signal_date': sig.get('date', ''),
                'actual_open': round(actual_open, 2),
                'scan_price':  scan_price,
                'gap_pct':     gap_pct,
                'gap_status':  gap_stat,
                'note':        gap_note,
                'fetch_time':  now_ist,
            })

            # Update history record
            sig_id = sig.get('id', '')
            if sig_id in history_map:
                idx = history_map[sig_id]
                history[idx]['actual_open'] = round(actual_open, 2)
                history[idx]['gap_pct']     = gap_pct
                history[idx]['entry_valid'] = (gap_stat != 'SKIP')
                history[idx]['adjusted_rr'] = None
                updated += 1

                print(f"[open_validator] Updated: "
                      f"{sym.replace('.NS','')} "
                      f"open=₹{actual_open:.2f} "
                      f"gap={gap_pct:+.1f}% "
                      f"→ {gap_stat}")

    # Save updated history
    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[open_validator] History updated: "
                  f"{updated} records")
        except Exception as e:
            print(f"[open_validator] History save failed: {e}")

    # Write open_prices.json
    _write_open_prices(results, today_str, now_ist)

    skipped  = sum(1 for r in results if r.get('gap_status') == 'SKIP')
    warnings = sum(1 for r in results if r.get('gap_status') == 'WARNING')
    ok       = sum(1 for r in results if r.get('gap_status') == 'OK')

    print(f"[open_validator] Complete — "
          f"{len(results)} processed | "
          f"OK:{ok} WARNING:{warnings} SKIP:{skipped}")

    # ── TELEGRAM: Send validation results ─────────────
    if TELEGRAM_AVAILABLE:
        try:
            ok_warn = [r for r in results if r.get('gap_status') != 'SKIP']
            skipped_list = [r for r in results if r.get('gap_status') == 'SKIP']
            send_open_validation(ok_warn, skipped_list)
            print("[open_validator] Telegram sent")
        except Exception as e:
            print(f"[open_validator] Telegram error: {e}")


def _write_open_prices(results, today_str, fetch_time):
    os.makedirs(_OUTPUT, exist_ok=True)
    data = {
        'date':       today_str,
        'fetch_time': fetch_time,
        'count':      len(results),
        'results':    results,
    }
    try:
        with open(OPEN_PRICES_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[open_validator] open_prices.json written "
              f"→ {len(results)} records")
    except Exception as e:
        print(f"[open_validator] Write failed: {e}")


if __name__ == '__main__':
    run_open_validation()
