# ── open_validator.py ────────────────────────────────
# Fetches actual open prices at 9:25 AM IST
# for all PENDING signals from signal_history.json
#
# Runs via open_validate.yml at 9:25 AM IST
#
# What it does:
#   1. Load all PENDING signals from history
#   2. Fetch actual open price via yfinance
#   3. Calculate gap vs scan_price
#   4. Flag GAP_SKIP if gap > 3%
#   5. Flag GAP_WARNING if gap > 1.5%
#   6. Update actual_open in signal_history.json
#   7. Write open_prices.json for frontend cards
#
# open_prices.json schema:
#   {
#     "date": "2026-04-07",
#     "fetch_time": "09:26 IST",
#     "results": [
#       {
#         "symbol":       "TATASTEEL.NS",
#         "actual_open":  195.48,
#         "scan_price":   190.40,
#         "gap_pct":      2.67,
#         "gap_status":   "OK",
#         "note":         "",
#         "fetch_time":   "09:26 IST"
#       }
#     ]
#   }
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)

# ── PATHS ─────────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

OPEN_PRICES_FILE = os.path.join(
    _OUTPUT, 'open_prices.json')

# ── THRESHOLDS ────────────────────────────────────────
GAP_SKIP_PCT    = 3.0   # gap > 3% → skip signal
GAP_WARNING_PCT = 1.5   # gap > 1.5% → warning


# ── FETCH OPEN PRICE ──────────────────────────────────

def _fetch_open(symbol, retries=2):
    """
    Fetches today's open price for a symbol.
    Returns float or None on failure.
    """
    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(symbol)
            # Get today's data
            df = ticker.history(
                period   = '2d',
                interval = '1d',
                auto_adjust = False,
            )

            if df is None or df.empty:
                continue

            if isinstance(df.columns,
                          pd.MultiIndex):
                df.columns = [
                    c[0] for c in df.columns]

            # Get most recent row
            today_str = date.today().strftime(
                '%Y-%m-%d')

            # Try to get today's open
            df.index = pd.to_datetime(
                df.index).tz_localize(None) \
                if df.index.tzinfo \
                else pd.to_datetime(df.index)

            # Filter to today
            today_rows = df[
                df.index.date ==
                date.today()
            ]

            if not today_rows.empty:
                open_price = float(
                    today_rows['Open'].iloc[-1])
                if open_price > 0:
                    return open_price

            # Fallback: last row
            open_price = float(
                df['Open'].iloc[-1])
            if open_price > 0:
                return open_price

        except Exception as e:
            print(f"[open_validator] "
                  f"Fetch error {symbol} "
                  f"attempt {attempt}: {e}")

    return None


# ── GAP CALCULATOR ────────────────────────────────────

def _calc_gap(scan_price, actual_open,
              direction):
    """
    Calculates gap percentage.
    Positive = favourable gap
    Negative = adverse gap
    """
    try:
        sp = float(scan_price)
        op = float(actual_open)
        if sp <= 0:
            return 0.0
        raw_pct = (op - sp) / sp * 100
        if direction == 'LONG':
            return round(raw_pct, 2)
        else:
            return round(-raw_pct, 2)
    except Exception:
        return 0.0


def _gap_status(gap_pct, direction):
    """
    Returns status string and note.
    gap_pct is signed (+ = favourable)
    For assessment we use absolute value
    because both directions can be bad.
    """
    abs_gap = abs(gap_pct)

    if abs_gap >= GAP_SKIP_PCT:
        note = (f"Gap {gap_pct:+.1f}% — "
                f"skip this signal")
        return 'SKIP', note

    if abs_gap >= GAP_WARNING_PCT:
        note = (f"Gap {gap_pct:+.1f}% — "
                f"reduced R:R, trade with caution")
        return 'WARNING', note

    return 'OK', ''


# ── MAIN FUNCTION ─────────────────────────────────────

def run_open_validation():
    """
    Main entry. Called from main.py at 9:25 AM
    via open_validate.yml workflow.

    Loads PENDING signals from history,
    fetches actual open prices,
    updates signal_history.json,
    writes open_prices.json for frontend.
    """
    print("[open_validator] Starting...")

    today_str  = date.today().isoformat()
    fetch_time = datetime.utcnow().strftime(
        '%H:%M IST')

    # Load history
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[open_validator] "
              f"Cannot load history: {e}")
        return

    history = data.get('history', [])

    # Only process today's PENDING signals
    # These are the signals that will be
    # entered at 9:15 AM today
    pending_today = [
        s for s in history
        if s.get('result') == 'PENDING'
        and s.get('date') == today_str
    ]

    if not pending_today:
        print("[open_validator] "
              "No pending signals today")
        # Write empty open_prices.json
        _write_open_prices([], today_str,
                           fetch_time)
        return

    print(f"[open_validator] "
          f"Processing {len(pending_today)} "
          f"signals...")

    results  = []
    updated  = 0

    # Build history index for fast update
    history_map = {
        s.get('id'): i
        for i, s in enumerate(history)
    }

    for sig in pending_today:
        symbol     = sig.get('symbol', '')
        direction  = sig.get('direction', 'LONG')
        scan_price = (
            sig.get('scan_price') or
            sig.get('entry_est') or
            sig.get('entry') or
            None
        )

        if not symbol:
            continue

        # Fetch actual open
        actual_open = _fetch_open(symbol)

        if actual_open is None:
            print(f"[open_validator] "
                  f"Failed: {symbol}")
            results.append({
                'symbol':      symbol,
                'actual_open': None,
                'scan_price':  scan_price,
                'gap_pct':     None,
                'gap_status':  'UNKNOWN',
                'note':        'Failed to fetch',
                'fetch_time':  fetch_time,
            })
            continue

        # Calculate gap
        gap_pct = _calc_gap(
            scan_price, actual_open, direction) \
            if scan_price else 0.0

        gap_stat, note = _gap_status(
            gap_pct, direction)

        print(f"[open_validator] "
              f"{symbol.replace('.NS','')} "
              f"open={actual_open} "
              f"gap={gap_pct:+.1f}% "
              f"→ {gap_stat}")

        # Build result record for frontend
        result = {
            'symbol':      symbol,
            'actual_open': round(actual_open, 2),
            'scan_price':  scan_price,
            'gap_pct':     gap_pct,
            'gap_status':  gap_stat,
            'note':        note,
            'fetch_time':  fetch_time,
        }
        results.append(result)

        # Update signal_history.json
        sig_id = sig.get('id', '')
        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx]['actual_open'] = \
                round(actual_open, 2)
            history[idx]['gap_pct'] = gap_pct
            history[idx]['entry_valid'] = \
                gap_stat != 'SKIP'
            history[idx]['adjusted_rr'] = None
            updated += 1

    # Save history
    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[open_validator] "
                  f"History updated: "
                  f"{updated} records")
        except Exception as e:
            print(f"[open_validator] "
                  f"History save failed: {e}")

    # Write open_prices.json for frontend
    _write_open_prices(
        results, today_str, fetch_time)

    skipped  = sum(
        1 for r in results
        if r.get('gap_status') == 'SKIP')
    warnings = sum(
        1 for r in results
        if r.get('gap_status') == 'WARNING')

    print(f"[open_validator] Complete — "
          f"{len(results)} processed | "
          f"{skipped} skip | "
          f"{warnings} warning")


# ── WRITE open_prices.json ────────────────────────────

def _write_open_prices(results, today_str,
                       fetch_time):
    """
    Writes open_prices.json to output/
    Frontend app.js reads this to update cards
    from scan_price → actual open price
    """
    os.makedirs(_OUTPUT, exist_ok=True)

    data = {
        'date':       today_str,
        'fetch_time': fetch_time,
        'count':      len(results),
        'results':    results,
    }

    try:
        with open(OPEN_PRICES_FILE, 'w') as f:
            json.dump(
                data, f, indent=2, default=str)
        print(f"[open_validator] "
              f"open_prices.json written "
              f"→ {len(results)} records")
    except Exception as e:
        print(f"[open_validator] "
              f"Write failed: {e}")


# ── ENTRY POINT ───────────────────────────────────────

if __name__ == '__main__':
    run_open_validation()
