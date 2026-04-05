# ── outcome_evaluator.py ─────────────────────────────
# Evaluates signal outcomes using 6-day window
# Matches actual trading rules exactly:
#   Entry = scan_price (close on detection day)
#   Stop  = from signal record
#   Target = entry + 2×risk
#   Exit  = Day 6 close if neither hit
#
# Runs daily via eod_update.yml at 3:35 PM IST
# Reads:  signal_history.json
# Writes: signal_history.json (updates in place)
#
# Outcome categories:
#   TARGET_HIT  → price hit 2R target within 6 days
#   STOP_HIT    → price hit stop within 6 days
#   DAY6_WIN    → Day 6 close > entry (no hit)
#   DAY6_LOSS   → Day 6 close < entry (no hit)
#   DAY6_FLAT   → Day 6 close ±0.5% of entry (no hit)
#   OPEN        → window not yet complete
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import load_history, _save_json, \
    _backup_history, HISTORY_FILE

# ── PATHS ─────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')

HOLIDAYS_FILE = os.path.join(
    _OUTPUT, 'nse_holidays.json')

# ── FLAT THRESHOLD ────────────────────────────────────
FLAT_PCT = 0.5   # ±0.5% = DAY6_FLAT


# ── HOLIDAY CALENDAR ──────────────────────────────────

def _load_holidays():
    """Load NSE holidays from nse_holidays.json."""
    try:
        with open(HOLIDAYS_FILE, 'r') as f:
            data = json.load(f)
        return data.get('holidays', [])
    except Exception:
        return []


def _is_trading_day(date_obj, holidays):
    """Returns True if date is a trading day."""
    if date_obj.weekday() >= 5:
        return False
    date_str = date_obj.strftime('%Y-%m-%d')
    return date_str not in holidays


def _get_entry_date(detection_date_str, holidays):
    """
    Returns first trading day after detection date.
    Entry = next trading day after signal fires.
    """
    cur = datetime.strptime(
        detection_date_str, '%Y-%m-%d').date()
    cur += timedelta(days=1)

    for _ in range(30):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)

    return cur


def _get_nth_trading_day(start_date, n, holidays):
    """
    Returns the nth trading day from start_date.
    start_date counts as Day 1.
    Returns Day n.
    """
    count = 1
    cur   = start_date

    while count < n:
        cur += timedelta(days=1)
        if _is_trading_day(cur, holidays):
            count += 1

    return cur


def _count_trading_days(start_date, end_date,
                        holidays):
    """Count trading days between two dates inclusive."""
    count = 0
    cur   = start_date
    while cur <= end_date:
        if _is_trading_day(cur, holidays):
            count += 1
        cur += timedelta(days=1)
    return count


# ── PRICE FETCHER ─────────────────────────────────────

def _fetch_ohlc(symbol, start_date, end_date,
                retries=2):
    """
    Fetch daily OHLC from start_date to end_date.
    Returns DataFrame or None on failure.
    """
    # Add buffer days for yfinance date range
    fetch_start = start_date - timedelta(days=3)
    fetch_end   = end_date   + timedelta(days=3)

    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                start  = fetch_start.strftime(
                    '%Y-%m-%d'),
                end    = fetch_end.strftime(
                    '%Y-%m-%d'),
                progress    = False,
                auto_adjust = False,
            )

            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [
                    c[0] for c in df.columns]

            df.index = pd.to_datetime(
                df.index, errors='coerce')
            if df.index.tzinfo:
                df.index = df.index.tz_localize(None)

            # Filter to exact date range
            start_ts = pd.Timestamp(start_date)
            end_ts   = pd.Timestamp(end_date)
            df = df[(df.index >= start_ts) &
                    (df.index <= end_ts)]

            if df.empty:
                continue

            return df

        except Exception as e:
            print(f"[outcome] Fetch error "
                  f"{symbol}: {e}")

    return None


# ── TARGET CALCULATOR ─────────────────────────────────

def _calculate_target(entry, stop, direction):
    """
    Target = entry ± 2 × risk
    Returns None if invalid inputs.
    """
    try:
        entry = float(entry)
        stop  = float(stop)
        risk  = abs(entry - stop)
        if risk <= 0:
            return None
        if direction == 'LONG':
            return round(entry + 2 * risk, 2)
        else:
            return round(entry - 2 * risk, 2)
    except Exception:
        return None


# ── OUTCOME EVALUATOR ─────────────────────────────────

def _evaluate_signal(signal, holidays):
    """
    Evaluates a single OPEN signal.

    Returns updated signal dict with outcome fields
    or unchanged signal if window not complete yet.
    """
    sym       = signal.get('symbol', '')
    direction = signal.get('direction', 'LONG')
    det_date  = signal.get('date', '')
    entry     = float(signal.get('scan_price')
                      or signal.get('entry') or 0)
    stop      = float(signal.get('stop') or 0)

    if not sym or not det_date or not entry \
            or not stop:
        print(f"[outcome] Skipping {sym} — "
              f"missing required fields")
        return signal

    # Calculate target if not already stored
    if not signal.get('target_price'):
        target = _calculate_target(
            entry, stop, direction)
        if target:
            signal['target_price'] = target
    else:
        target = float(signal['target_price'])

    if not target:
        print(f"[outcome] Skipping {sym} — "
              f"cannot calculate target")
        return signal

    # Calculate tracking window
    try:
        entry_date   = _get_entry_date(
            det_date, holidays)
        tracking_end = _get_nth_trading_day(
            entry_date, 6, holidays)
    except Exception as e:
        print(f"[outcome] Date error {sym}: {e}")
        return signal

    today = date.today()

    # Store tracking dates
    signal['tracking_start'] = \
        entry_date.strftime('%Y-%m-%d')
    signal['tracking_end']   = \
        tracking_end.strftime('%Y-%m-%d')

    # Window not started yet
    if today < entry_date:
        print(f"[outcome] {sym} — "
              f"window not started yet")
        return signal

    # Fetch OHLC for available days in window
    fetch_end = min(today, tracking_end)
    ohlc      = _fetch_ohlc(sym, entry_date,
                             fetch_end)

    if ohlc is None or ohlc.empty:
        print(f"[outcome] {sym} — "
              f"no OHLC data available")
        return signal

    # ── SCAN EACH DAY ─────────────────────────────
    outcome       = None
    outcome_date  = None
    outcome_price = None
    max_fav       = 0.0   # MFE
    max_adv       = 0.0   # MAE

    for ts, row in ohlc.iterrows():
        try:
            high  = float(row['High'])
            low   = float(row['Low'])
            close = float(row['Close'])
        except Exception:
            continue

        # Update MFE and MAE
        if direction == 'LONG':
            fav = (high  - entry) / entry * 100
            adv = (entry - low)   / entry * 100
        else:
            fav = (entry - low)   / entry * 100
            adv = (high  - entry) / entry * 100

        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)

        # Check stop and target
        if direction == 'LONG':
            stop_hit   = low  <= stop
            target_hit = high >= target
        else:
            stop_hit   = high >= stop
            target_hit = low  <= target

        # Same day: STOP wins (conservative)
        if stop_hit:
            outcome       = 'STOP_HIT'
            outcome_date  = ts.date()
            outcome_price = round(stop, 2)
            print(f"[outcome] {sym} → "
                  f"STOP_HIT on {outcome_date}")
            break

        if target_hit:
            outcome       = 'TARGET_HIT'
            outcome_date  = ts.date()
            outcome_price = round(target, 2)
            print(f"[outcome] {sym} → "
                  f"TARGET_HIT on {outcome_date}")
            break

    # ── DAY 6 EXIT ────────────────────────────────
    if outcome is None and today >= tracking_end:
        # Get Day 6 closing price
        try:
            day6_ts = pd.Timestamp(tracking_end)
            # Find closest available date
            if day6_ts in ohlc.index:
                day6_close = float(
                    ohlc.loc[day6_ts, 'Close'])
            else:
                # Use last available close
                day6_close = float(
                    ohlc['Close'].iloc[-1])

            move_pct = (day6_close - entry) \
                       / entry * 100

            # For SHORT reverse the direction
            if direction == 'SHORT':
                move_pct = -move_pct

            if move_pct > FLAT_PCT:
                outcome = 'DAY6_WIN'
            elif move_pct < -FLAT_PCT:
                outcome = 'DAY6_LOSS'
            else:
                outcome = 'DAY6_FLAT'

            outcome_date  = tracking_end
            outcome_price = round(day6_close, 2)

            print(f"[outcome] {sym} → "
                  f"{outcome} "
                  f"(move {move_pct:+.1f}%)")

        except Exception as e:
            print(f"[outcome] Day 6 close error "
                  f"{sym}: {e}")

    # ── WRITE BACK ────────────────────────────────
    if outcome:
        signal['outcome']       = outcome
        signal['outcome_date']  = str(
            outcome_date)[:10]
        signal['outcome_price'] = outcome_price
        signal['mfe_pct']       = round(max_fav, 2)
        signal['mae_pct']       = round(max_adv, 2)
        signal['days_to_outcome'] = \
            _count_trading_days(
                entry_date,
                outcome_date
                if isinstance(outcome_date, date)
                else tracking_end,
                holidays)
    else:
        # Still open — update MFE/MAE progress
        if max_fav > 0 or max_adv > 0:
            signal['mfe_pct'] = round(max_fav, 2)
            signal['mae_pct'] = round(max_adv, 2)

    return signal


# ── MAIN FUNCTION ─────────────────────────────────────

def run_outcome_evaluation():
    """
    Main entry point. Called from main.py EOD.

    Loads all OPEN signals from signal_history.json
    Evaluates each against 6-day OHLC window
    Writes outcomes back to signal_history.json
    """

    print("[outcome] Starting outcome evaluation...")

    holidays = _load_holidays()
    if not holidays:
        print("[outcome] Warning — no holidays loaded")

    # Load history
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[outcome] Cannot load history: {e}")
        return

    history = data.get('history', [])

    # Filter to OPEN signals only
    open_signals = [
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result',  'PENDING') != 'REJECTED'
    ]

    if not open_signals:
        print("[outcome] No open signals to evaluate")
        return

    print(f"[outcome] Evaluating "
          f"{len(open_signals)} open signals...")

    resolved = 0
    updated  = 0

    # Build lookup for fast update
    history_map = {
        s.get('id'): i
        for i, s in enumerate(history)
    }

    for signal in open_signals:
        sig_id = signal.get('id', '')
        before = signal.get('outcome', 'OPEN')

        updated_sig = _evaluate_signal(
            signal.copy(), holidays)

        after = updated_sig.get('outcome', 'OPEN')

        # Write back to history
        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx] = updated_sig
            updated += 1

            if after != 'OPEN' and before == 'OPEN':
                resolved += 1

                # Also update result field
                # for backwards compatibility
                if after == 'TARGET_HIT':
                    history[idx]['result'] = 'WON'
                elif after == 'STOP_HIT':
                    history[idx]['result'] = 'STOPPED'
                elif after in ('DAY6_WIN',
                               'DAY6_LOSS',
                               'DAY6_FLAT'):
                    history[idx]['result'] = 'EXITED'

    # Save back
    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[outcome] Done — "
                  f"resolved: {resolved} | "
                  f"updated MFE/MAE: {updated}")
        except Exception as e:
            print(f"[outcome] Save failed: {e}")
    else:
        print("[outcome] No updates needed")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_outcome_evaluation()
