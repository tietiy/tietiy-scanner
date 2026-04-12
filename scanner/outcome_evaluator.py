# ── outcome_evaluator.py ─────────────────────────────
# Evaluates signal outcomes using 6-day OHLC window
#
# FIXES:
#   B FIX  — entry fallback chain
#   C FIX  — tracking_start set once only
#   E FIX  — verbose OPEN signal logging
#   OE4    — Day 6 uses OPEN price not CLOSE
#   DI3    — MFE/MAE uses actual_open first
#   PNL    — pnl_pct calculated on resolve
#
# F1 FIX: Dual track — after TARGET_HIT, continue
#         observing till Day 6. Record day6_open
#         and post_target_move as shadow data.
# F2 FIX: post_target_move, day6_open, exit_day,
#         exit_type fields added to schema.
#
# V1 BUG FIX: Skip signals with entry_valid=False
#   Gap too large at open = trade never entered.
#   outcome_evaluator was assigning fake outcomes
#   using actual_open as entry even when flagged
#   invalid — producing nonsense P&L values.
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

            if isinstance(df.columns, pd.MultiIndex):
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


# ── HELPERS ───────────────────────────────────────────

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


def _resolve_entry(signal):
    """DI3 FIX — actual_open preferred."""
    for field in [
        'actual_open',
        'scan_price',
        'entry',
        'entry_est',
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


def _calc_pnl_pct(entry, outcome_price, direction):
    try:
        entry         = float(entry)
        outcome_price = float(outcome_price)
        if entry <= 0:
            return None
        if direction == 'LONG':
            return round(
                (outcome_price - entry)
                / entry * 100, 2)
        else:
            return round(
                (entry - outcome_price)
                / entry * 100, 2)
    except Exception:
        return None


# ── EVALUATE SINGLE SIGNAL ────────────────────────────

def _evaluate_signal(signal, holidays):
    sym       = signal.get('symbol', '')
    direction = signal.get('direction', 'LONG')
    det_date  = signal.get('date', '')
    stop_val  = signal.get('stop', None)

    entry = _resolve_entry(signal)
    stop  = float(stop_val) if stop_val else None

    if not sym or not det_date \
            or not entry or not stop:
        print(f"[outcome] Skip {sym} — "
              f"missing fields "
              f"entry={entry} stop={stop}")
        return signal

    if not signal.get('target_price'):
        target = _calculate_target(
            entry, stop, direction)
        if target:
            signal['target_price'] = target
    else:
        try:
            target = float(signal['target_price'])
        except Exception:
            target = _calculate_target(
                entry, stop, direction)
            if target:
                signal['target_price'] = target

    if not target:
        print(f"[outcome] Skip {sym} — "
              f"cannot calculate target")
        return signal

    try:
        entry_date   = _get_entry_date(
            det_date, holidays)
        tracking_end = _get_nth_trading_day(
            entry_date, 6, holidays)
    except Exception as e:
        print(f"[outcome] Date error {sym}: {e}")
        return signal

    today = date.today()

    # Set tracking dates once
    if not signal.get('tracking_start'):
        signal['tracking_start'] = \
            entry_date.strftime('%Y-%m-%d')
    if not signal.get('tracking_end'):
        signal['tracking_end'] = \
            tracking_end.strftime('%Y-%m-%d')

    if today < entry_date:
        print(f"[outcome] {sym} — "
              f"entry {entry_date} not reached")
        return signal

    fetch_end = min(today, tracking_end)
    ohlc      = _fetch_ohlc(
        sym, entry_date, fetch_end)

    if ohlc is None or ohlc.empty:
        print(f"[outcome] {sym} — no OHLC data")
        return signal

    # ── SCAN EACH DAY ─────────────────────────────
    real_exit_outcome = None
    real_exit_date    = None
    real_exit_price   = None
    real_exit_day     = None
    max_fav           = 0.0
    max_adv           = 0.0

    for ts, row in ohlc.iterrows():
        try:
            high  = float(row['High'])
            low   = float(row['Low'])
            close = float(row['Close'])
        except Exception:
            continue

        # MFE/MAE
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

        # Stop hit — definitive, break immediately
        if stop_hit and real_exit_outcome is None:
            real_exit_outcome = 'STOP_HIT'
            real_exit_date    = ts.date()
            real_exit_price   = round(stop, 2)
            real_exit_day     = _count_trading_days(
                entry_date, ts.date(), holidays)
            print(f"[outcome] {sym} → STOP_HIT "
                  f"Day {real_exit_day}")
            break

        # F1 FIX: Target hit — record but DON'T break
        if target_hit and real_exit_outcome is None:
            real_exit_outcome = 'TARGET_HIT'
            real_exit_date    = ts.date()
            real_exit_price   = round(target, 2)
            real_exit_day     = _count_trading_days(
                entry_date, ts.date(), holidays)
            print(f"[outcome] {sym} → TARGET_HIT "
                  f"Day {real_exit_day} — "
                  f"continuing for Day 6 shadow")

    # ── DAY 6 EXIT + SHADOW DATA ──────────────────
    day6_open        = None
    post_target_move = None

    if today >= tracking_end:
        try:
            day6_ts = pd.Timestamp(tracking_end)

            if day6_ts in ohlc.index:
                day6_open = float(
                    ohlc.loc[day6_ts, 'Open'])
            else:
                day6_open = float(
                    ohlc['Open'].iloc[-1])

            if (real_exit_outcome == 'TARGET_HIT'
                    and day6_open
                    and real_exit_price):
                raw_move = (
                    (day6_open - real_exit_price)
                    / real_exit_price * 100)
                post_target_move = round(
                    raw_move
                    if direction == 'LONG'
                    else -raw_move, 2)
                print(f"[outcome] {sym} → "
                      f"post_target_move: "
                      f"{post_target_move:+.1f}% "
                      f"(Day6 open ₹{day6_open:.2f})")

            if real_exit_outcome is None and day6_open:
                move_pct = (
                    (day6_open - entry)
                    / entry * 100)
                if direction == 'SHORT':
                    move_pct = -move_pct

                if move_pct > FLAT_PCT:
                    real_exit_outcome = 'DAY6_WIN'
                elif move_pct < -FLAT_PCT:
                    real_exit_outcome = 'DAY6_LOSS'
                else:
                    real_exit_outcome = 'DAY6_FLAT'

                real_exit_date  = tracking_end
                real_exit_price = round(day6_open, 2)
                real_exit_day   = 6

                print(f"[outcome] {sym} → "
                      f"{real_exit_outcome} "
                      f"move {move_pct:+.1f}% "
                      f"Day6 open ₹{day6_open:.2f}")

        except Exception as e:
            print(f"[outcome] Day6 error {sym}: {e}")

    # ── WRITE BACK ────────────────────────────────
    if real_exit_outcome:
        pnl_pct = _calc_pnl_pct(
            entry, real_exit_price, direction)

        signal['outcome']       = real_exit_outcome
        signal['outcome_date']  = str(
            real_exit_date)[:10]
        signal['outcome_price'] = real_exit_price
        signal['pnl_pct']       = pnl_pct
        signal['mfe_pct']       = round(max_fav, 2)
        signal['mae_pct']       = round(max_adv, 2)
        signal['exit_type']     = real_exit_outcome
        signal['exit_day']      = real_exit_day

        if day6_open is not None:
            signal['day6_open'] = round(day6_open, 2)
        if post_target_move is not None:
            signal['post_target_move'] = \
                post_target_move

        days_to = _count_trading_days(
            entry_date,
            real_exit_date
            if isinstance(real_exit_date, date)
            else tracking_end,
            holidays)
        signal['days_to_outcome'] = days_to

    else:
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
        print("[outcome] Warning — no holidays loaded")

    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[outcome] Cannot load history: {e}")
        return

    history = data.get('history', [])

    # V1 BUG FIX: exclude entry_valid=False signals
    # These had gap too large at open — trade was never
    # entered. outcome_evaluator must not assign outcomes
    # to signals the trader could not have taken.
    open_signals = [
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is not False
    ]

    # Log how many were skipped due to invalid entry
    invalid_skipped = len([
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is False
    ])
    if invalid_skipped > 0:
        print(f"[outcome] Skipping {invalid_skipped} "
              f"signals with entry_valid=False "
              f"(gap too large at open)")

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

        after = updated_sig.get('outcome', 'OPEN')

        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx] = updated_sig
            updated += 1

            if after != 'OPEN' and before == 'OPEN':
                resolved += 1

                if after == 'TARGET_HIT':
                    history[idx]['result'] = 'WON'
                elif after == 'STOP_HIT':
                    history[idx]['result'] = 'STOPPED'
                elif after in (
                    'DAY6_WIN',
                    'DAY6_LOSS',
                    'DAY6_FLAT',
                ):
                    history[idx]['result'] = 'EXITED'

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
