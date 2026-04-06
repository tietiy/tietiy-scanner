# ── outcome_evaluator.py ─────────────────────────────
# Evaluates signal outcomes using 6-day OHLC window
# Matches actual trading rules exactly
#
# FIXES APPLIED:
#   BUG B — entry fallback chain fixed
#   BUG C — tracking_start only set once
#   BUG E — verbose logging for OPEN signals
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HOLIDAYS_FILE = os.path.join(
    _OUTPUT, 'nse_holidays.json')

FLAT_PCT = 0.5


# ── HOLIDAY HELPERS ───────────────────────────────────

def _load_holidays():
    try:
        with open(HOLIDAYS_FILE, 'r') as f:
            data = json.load(f)
        return data.get('holidays', [])
    except Exception:
        return []


def _is_trading_day(date_obj, holidays):
    if date_obj.weekday() >= 5:
        return False
    return date_obj.strftime(
        '%Y-%m-%d') not in holidays


def _get_entry_date(detection_date_str, holidays):
    cur = datetime.strptime(
        detection_date_str,
        '%Y-%m-%d').date() + timedelta(days=1)
    for _ in range(30):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)
    return cur


def _get_nth_trading_day(start_date, n, holidays):
    count = 1
    cur   = start_date
    while count < n:
        cur += timedelta(days=1)
        if _is_trading_day(cur, holidays):
            count += 1
    return cur


def _count_trading_days(start_date, end_date,
                        holidays):
    count = 0
    cur   = start_date
    while cur <= end_date:
        if _is_trading_day(cur, holidays):
            count += 1
        cur += timedelta(days=1)
    return count


# ── PRICE FETCHER ─────────────────────────────────────

def _fetch_ohlc(symbol, start_date,
                end_date, retries=2):
    fetch_start = start_date - timedelta(days=3)
    fetch_end   = end_date   + timedelta(days=3)

    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                start       = fetch_start.strftime(
                    '%Y-%m-%d'),
                end         = fetch_end.strftime(
                    '%Y-%m-%d'),
                progress    = False,
                auto_adjust = False,
            )
            if df is None or df.empty:
                continue

            if isinstance(df.columns,
                          pd.MultiIndex):
                df.columns = [
                    c[0] for c in df.columns]

            df.index = pd.to_datetime(
                df.index, errors='coerce')
            if df.index.tzinfo:
                df.index = \
                    df.index.tz_localize(None)

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


# ── ENTRY PRICE RESOLVER — BUG B FIX ─────────────────
# Old records may have scan_price = None
# Must try all possible price fields

def _resolve_entry(signal):
    for field in [
        'scan_price', 'actual_open',
        'entry', 'entry_est'
    ]:
        val = signal.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except Exception:
                continue
    return None


# ── EVALUATE SINGLE SIGNAL ────────────────────────────

def _evaluate_signal(signal, holidays):
    sym       = signal.get('symbol', '')
    direction = signal.get('direction', 'LONG')
    det_date  = signal.get('date', '')
    stop_val  = signal.get('stop', None)

    # BUG B FIX — full fallback chain
    entry = _resolve_entry(signal)
    stop  = float(stop_val) \
            if stop_val else None

    if not sym or not det_date \
            or not entry or not stop:
        print(f"[outcome] Skip {sym} — "
              f"missing fields "
              f"entry={entry} stop={stop}")
        return signal

    # Calculate target if not stored
    if not signal.get('target_price'):
        target = _calculate_target(
            entry, stop, direction)
        if target:
            signal['target_price'] = target
    else:
        try:
            target = float(
                signal['target_price'])
        except Exception:
            target = _calculate_target(
                entry, stop, direction)
            if target:
                signal['target_price'] = target

    if not target:
        print(f"[outcome] Skip {sym} — "
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

    # BUG C FIX — only set tracking_start once
    if not signal.get('tracking_start'):
        signal['tracking_start'] = \
            entry_date.strftime('%Y-%m-%d')
    if not signal.get('tracking_end'):
        signal['tracking_end'] = \
            tracking_end.strftime('%Y-%m-%d')

    # Window not started yet
    if today < entry_date:
        print(f"[outcome] {sym} — "
              f"entry date {entry_date} "
              f"not reached yet")
        return signal

    # Fetch OHLC
    fetch_end = min(today, tracking_end)
    ohlc      = _fetch_ohlc(
        sym, entry_date, fetch_end)

    if ohlc is None or ohlc.empty:
        print(f"[outcome] {sym} — "
              f"no OHLC data")
        return signal

    # ── SCAN EACH DAY ─────────────────────────────
    outcome       = None
    outcome_date  = None
    outcome_price = None
    max_fav       = 0.0
    max_adv       = 0.0

    for ts, row in ohlc.iterrows():
        try:
            high  = float(row['High'])
            low   = float(row['Low'])
            close = float(row['Close'])
        except Exception:
            continue

        if direction == 'LONG':
            fav = (high  - entry) / entry * 100
            adv = (entry - low)   / entry * 100
        else:
            fav = (entry - low)   / entry * 100
            adv = (high  - entry) / entry * 100

        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)

        if direction == 'LONG':
            stop_hit   = low  <= stop
            target_hit = high >= target
        else:
            stop_hit   = high >= stop
            target_hit = low  <= target

        # Same day: STOP wins
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
        try:
            day6_ts = pd.Timestamp(tracking_end)
            if day6_ts in ohlc.index:
                day6_close = float(
                    ohlc.loc[day6_ts, 'Close'])
            else:
                day6_close = float(
                    ohlc['Close'].iloc[-1])

            move_pct = ((day6_close - entry)
                        / entry * 100)
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
                  f"move {move_pct:+.1f}%")

        except Exception as e:
            print(f"[outcome] Day6 error "
                  f"{sym}: {e}")

    # ── WRITE BACK ────────────────────────────────
    if outcome:
        signal['outcome']       = outcome
        signal['outcome_date']  = str(
            outcome_date)[:10]
        signal['outcome_price'] = outcome_price
        signal['mfe_pct']       = round(
            max_fav, 2)
        signal['mae_pct']       = round(
            max_adv, 2)
        signal['days_to_outcome'] = \
            _count_trading_days(
                entry_date,
                outcome_date
                if isinstance(outcome_date, date)
                else tracking_end,
                holidays)
    else:
        # BUG E FIX — log still-OPEN progress
        days_so_far = _count_trading_days(
            entry_date, today, holidays)
        print(f"[outcome] {sym} "
              f"{signal.get('signal','')} — "
              f"Day {days_so_far}/6 OPEN | "
              f"MFE:+{max_fav:.1f}% "
              f"MAE:-{max_adv:.1f}%")
        if max_fav > 0 or max_adv > 0:
            signal['mfe_pct'] = round(max_fav, 2)
            signal['mae_pct'] = round(max_adv, 2)

    return signal


# ── MAIN FUNCTION ─────────────────────────────────────

def run_outcome_evaluation():
    print("[outcome] Starting evaluation...")

    holidays = _load_holidays()
    if not holidays:
        print("[outcome] Warning — no holidays")

    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[outcome] Cannot load "
              f"history: {e}")
        return

    history = data.get('history', [])

    open_signals = [
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result', 'PENDING')
           != 'REJECTED'
    ]

    if not open_signals:
        print("[outcome] No open signals")
        return

    print(f"[outcome] Evaluating "
          f"{len(open_signals)} signals...")

    resolved = 0
    updated  = 0

    history_map = {
        s.get('id'): i
        for i, s in enumerate(history)
    }

    for signal in open_signals:
        sig_id = signal.get('id', '')
        before = signal.get('outcome', 'OPEN')

        updated_sig = _evaluate_signal(
            signal.copy(), holidays)

        after = updated_sig.get(
            'outcome', 'OPEN')

        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx] = updated_sig
            updated += 1

            if after != 'OPEN' \
                    and before == 'OPEN':
                resolved += 1

                if after == 'TARGET_HIT':
                    history[idx]['result'] = \
                        'WON'
                elif after == 'STOP_HIT':
                    history[idx]['result'] = \
                        'STOPPED'
                elif after in (
                    'DAY6_WIN',
                    'DAY6_LOSS',
                    'DAY6_FLAT'
                ):
                    history[idx]['result'] = \
                        'EXITED'

    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[outcome] Done — "
                  f"resolved:{resolved} "
                  f"updated:{updated}")
        except Exception as e:
            print(f"[outcome] Save failed: {e}")
    else:
        print("[outcome] No updates needed")


if __name__ == '__main__':
    run_outcome_evaluation()
