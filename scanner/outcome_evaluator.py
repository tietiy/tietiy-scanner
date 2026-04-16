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
#
# V1.1 FIXES:
#   TR3: _next_trading_day() + effective_tracking_end
#        Day 6 open rolls forward if tracking_end
#        falls on holiday — prevents wrong P&L from
#        using last-available-bar as Day 6 price.
#   HC5: update_sa_parent_outcome() called when
#        parent signal resolves — propagates outcome
#        to all SA child signals automatically.
#   H12: _classify_failure_reason() — rule-based
#        classifier writes failure_reason field at
#        resolution time for every resolved signal.
#   H13: failure_reason field added to schema.
#
# V2 FIXES:
#   OE1: _calc_r_multiple() added — STOP_HIT always
#        stores r_multiple=-1.0, TARGET_HIT=+2.0.
#        Impossible R values (e.g. -9.70R) prevented.
#   OE2: _evaluate_signal() returns early if signal
#        already has a terminal outcome — prevents
#        duplicate resolution of closed signals.
#   OE3: STOP_HIT pnl_pct forced negative — a stop
#        hit can never produce a positive P&L.
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

# OE2: Terminal outcomes — signals with these are
# fully closed and must never be re-evaluated.
_TERMINAL_OUTCOMES = {
    'STOP_HIT',
    'TARGET_HIT',
    'DAY6_WIN',
    'DAY6_LOSS',
    'DAY6_FLAT',
}


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


def _next_trading_day(d, holidays):
    """
    TR3 FIX: Roll forward to nearest trading day.
    Used when tracking_end falls on a holiday —
    ensures Day 6 open is fetched from a real
    market day, not a closed day.
    """
    cur = d
    for _ in range(14):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)
    return cur


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


# OE1: R-MULTIPLE CALCULATOR ──────────────────────────

def _calc_r_multiple(entry, stop,
                     outcome_price, direction,
                     outcome_type=None):
    """
    OE1 FIX: Calculate R-multiple from entry/stop/
    outcome_price. Caps at fixed values for terminal
    outcomes to prevent impossible R values:
      STOP_HIT   → always -1.0R (stop = 1R loss)
      TARGET_HIT → always +2.0R (target = 2R win)
    For DAY6 outcomes, calculated from actual move.
    """
    # Hard caps for fixed-exit outcomes
    if outcome_type == 'STOP_HIT':
        return -1.0
    if outcome_type == 'TARGET_HIT':
        return 2.0

    # DAY6 outcomes — calculated from actual move
    try:
        entry         = float(entry)
        stop          = float(stop)
        outcome_price = float(outcome_price)
        risk          = abs(entry - stop)
        if risk <= 0:
            return None
        if direction == 'LONG':
            pnl = outcome_price - entry
        else:
            pnl = entry - outcome_price
        return round(pnl / risk, 2)
    except Exception:
        return None


# ── H12/H13: FAILURE REASON CLASSIFIER ───────────────

def _classify_failure_reason(signal, outcome,
                              exit_day, mae_pct):
    """
    H12 FIX: Rule-based classifier for failure and
    win reasons. Runs at resolution time. Returns a
    plain-language string stored as failure_reason
    on the signal record.

    Used by journal.js to show traders WHY a signal
    succeeded or failed — not just the outcome badge.
    """
    age         = int(signal.get('age', 0) or 0)
    vol_confirm = signal.get('vol_confirm', False)
    sec_leading = signal.get('sec_leading', False)
    rs_strong   = signal.get('rs_strong', False)
    bear_bonus  = signal.get('bear_bonus', False)
    stock_regime= (signal.get('stock_regime') or '')
    mkt_regime  = (signal.get('regime') or '')
    entry_valid = signal.get('entry_valid')
    gap_pct     = abs(float(
        signal.get('gap_pct') or 0))
    mae         = float(mae_pct or 0)
    sig_type    = (signal.get('signal') or '')

    # ── WINS ──────────────────────────────────────
    if outcome == 'TARGET_HIT':
        if bear_bonus and age == 0:
            return ('Bear regime fresh breakout '
                    '— highest conviction setup')
        elif vol_confirm and sec_leading:
            return ('Volume confirmed + sector '
                    'leading — strong alignment')
        elif vol_confirm and rs_strong:
            return ('Volume confirmed + strong RS '
                    '— momentum behind move')
        elif vol_confirm:
            return ('Volume confirmed breakout '
                    '— clean directional move')
        else:
            return 'Price reached target in 6 days'

    if outcome == 'DAY6_WIN':
        if bear_bonus:
            return ('Bear regime — gradual move '
                    'held through 6 days')
        return ('Gradual move to target '
                '— held through full window')

    # ── STOP HITS ─────────────────────────────────
    if outcome == 'STOP_HIT':
        if entry_valid is False:
            return ('Gap at open invalidated entry '
                    '— trade was not taken')
        if exit_day == 1 and gap_pct > 2.0:
            return ('Gapped through stop at open '
                    '— Day 1 gap risk')
        if mae > 10:
            return ('Heavy move against position '
                    '— event or regime shock')
        if mae > 5:
            return ('Strong directional move '
                    'against — stop correctly hit')
        if mae < 2.5:
            return ('Stop hit by normal volatility '
                    '— stop may be too tight')
        return 'Directional move against — stop hit'

    # ── DAY 6 LOSSES ──────────────────────────────
    if outcome == 'DAY6_LOSS':
        if not vol_confirm:
            return ('Breakout without volume '
                    '— weak setup, no follow-through')
        if age > 1:
            return ('Late entry — breakout momentum '
                    'was already stale')
        if (stock_regime and mkt_regime
                and stock_regime.upper()
                != mkt_regime.upper()):
            return ('Stock and market regime '
                    'misaligned — no confirmation')
        if 'DOWN_TRI' in sig_type:
            return ('Short setup failed to follow '
                    'through in 6 days')
        return ('No directional move in 6 days '
                '— setup did not trigger')

    # ── DAY 6 FLATS ───────────────────────────────
    if outcome == 'DAY6_FLAT':
        if not vol_confirm:
            return ('Price moved without volume '
                    '— false breakout absorbed')
        if age > 0:
            return ('Aged setup — edge reduced '
                    'by time at entry')
        return ('Market absorbed the breakout '
                '— no net direction in 6 days')

    return None


# ── EVALUATE SINGLE SIGNAL ────────────────────────────

def _evaluate_signal(signal, holidays):

    # OE2 FIX: Early return if already resolved.
    # Prevents duplicate resolution of closed signals
    # across multiple EOD runs (dead signal re-alert
    # root cause).
    current_outcome = signal.get('outcome', 'OPEN')
    if current_outcome in _TERMINAL_OUTCOMES:
        return signal

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

    # TR3 FIX: Roll tracking_end forward if it falls
    # on a holiday. Prevents using wrong OHLC bar
    # (last available) as the Day 6 open price.
    effective_tracking_end = _next_trading_day(
        tracking_end, holidays)

    if effective_tracking_end != tracking_end:
        print(f"[outcome] {sym} — tracking_end "
              f"{tracking_end} is holiday, "
              f"rolling to {effective_tracking_end}")

    today = date.today()

    # Set tracking dates once
    if not signal.get('tracking_start'):
        signal['tracking_start'] = \
            entry_date.strftime('%Y-%m-%d')
    if not signal.get('tracking_end'):
        signal['tracking_end'] = \
            tracking_end.strftime('%Y-%m-%d')

    # Always store effective exit date
    signal['effective_exit_date'] = \
        effective_tracking_end.strftime('%Y-%m-%d')

    if today < entry_date:
        print(f"[outcome] {sym} — "
              f"entry {entry_date} not reached")
        return signal

    # TR3 FIX: Fetch up to effective_tracking_end
    # so Day 6 open data is available even when
    # original tracking_end was a holiday.
    fetch_end = min(today, effective_tracking_end)
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

    # Only scan up to tracking_end (original)
    # not effective — stop/target only valid
    # during the 6 trading-day window
    scan_end_ts = pd.Timestamp(tracking_end)

    for ts, row in ohlc.iterrows():
        # Stop scanning after original tracking_end
        if ts > scan_end_ts:
            break
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

    # TR3 FIX: Use effective_tracking_end for Day 6
    # open price — correctly handles holiday rollover
    if today >= effective_tracking_end:
        try:
            # First try effective (rolled) date
            day6_ts = pd.Timestamp(
                effective_tracking_end)

            if day6_ts in ohlc.index:
                day6_open = float(
                    ohlc.loc[day6_ts, 'Open'])
            else:
                # Data not yet available — will
                # retry on next EOD run
                print(f"[outcome] {sym} — "
                      f"Day 6 open data not yet "
                      f"available for "
                      f"{effective_tracking_end}")
                day6_open = None

            if day6_open is not None:
                if (real_exit_outcome == 'TARGET_HIT'
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
                          f"{post_target_move:+.1f}%"
                          f" (Day6 open "
                          f"₹{day6_open:.2f})")

                if (real_exit_outcome is None
                        and day6_open):
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

                    real_exit_date  = \
                        effective_tracking_end
                    real_exit_price = round(
                        day6_open, 2)
                    real_exit_day   = 6

                    print(f"[outcome] {sym} → "
                          f"{real_exit_outcome} "
                          f"move {move_pct:+.1f}% "
                          f"Day6 open "
                          f"₹{day6_open:.2f}")

        except Exception as e:
            print(f"[outcome] Day6 error "
                  f"{sym}: {e}")

    # ── WRITE BACK ────────────────────────────────
    if real_exit_outcome:
        pnl_pct = _calc_pnl_pct(
            entry, real_exit_price, direction)

        # OE3 FIX: STOP_HIT pnl_pct must always be
        # negative. A stop hit cannot produce a
        # positive P&L — force negative if wrong.
        if real_exit_outcome == 'STOP_HIT':
            if pnl_pct is not None and pnl_pct > 0:
                print(f"[outcome] OE3 fix {sym} — "
                      f"STOP_HIT had positive pnl "
                      f"{pnl_pct}%, forcing negative")
                pnl_pct = -abs(pnl_pct)

        # OE1 FIX: Calculate R-multiple with hard
        # caps for STOP_HIT and TARGET_HIT outcomes.
        # Prevents impossible values like -9.70R.
        r_multiple = _calc_r_multiple(
            entry         = entry,
            stop          = stop,
            outcome_price = real_exit_price,
            direction     = direction,
            outcome_type  = real_exit_outcome,
        )

        # H13: failure_reason field
        failure_reason = _classify_failure_reason(
            signal        = signal,
            outcome       = real_exit_outcome,
            exit_day      = real_exit_day,
            mae_pct       = round(max_adv, 2))

        signal['outcome']        = real_exit_outcome
        signal['outcome_date']   = str(
            real_exit_date)[:10]
        signal['outcome_price']  = real_exit_price
        signal['pnl_pct']        = pnl_pct
        signal['r_multiple']     = r_multiple
        signal['mfe_pct']        = round(max_fav, 2)
        signal['mae_pct']        = round(max_adv, 2)
        signal['exit_type']      = real_exit_outcome
        signal['exit_day']       = real_exit_day
        signal['failure_reason'] = failure_reason

        if day6_open is not None:
            signal['day6_open'] = round(day6_open, 2)
        if post_target_move is not None:
            signal['post_target_move'] = \
                post_target_move

        days_to = _count_trading_days(
            entry_date,
            real_exit_date
            if isinstance(real_exit_date, date)
            else effective_tracking_end,
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


# ── HC5: SA PARENT OUTCOME PROPAGATION ───────────────

def _propagate_sa_outcome(history, parent_id,
                          parent_outcome):
    """
    HC5 FIX: When a parent signal resolves, find all
    SA child signals pointing to it and update their
    sa_parent_outcome field.

    Called from run_outcome_evaluation() immediately
    after a signal is resolved.
    """
    updated = 0
    for sig in history:
        if sig.get('sa_parent_id') == parent_id:
            if sig.get('sa_parent_outcome') \
                    != parent_outcome:
                sig['sa_parent_outcome'] = \
                    parent_outcome
                updated += 1
                print(f"[outcome] SA propagate: "
                      f"{sig.get('symbol','')} "
                      f"sa_parent_outcome="
                      f"{parent_outcome}")
    return updated


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
    # OE2 FIX: exclude terminal outcomes — signals
    # already resolved must never be re-evaluated.
    open_signals = [
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is not False
        and s.get('outcome', 'OPEN')
            not in _TERMINAL_OUTCOMES
    ]

    invalid_skipped = len([
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is False
    ])
    if invalid_skipped > 0:
        print(f"[outcome] Skipping "
              f"{invalid_skipped} signals with "
              f"entry_valid=False "
              f"(gap too large at open)")

    if not open_signals:
        print("[outcome] No open signals")
        return

    print(f"[outcome] Evaluating "
          f"{len(open_signals)} signals...")

    resolved     = 0
    updated      = 0
    sa_propagated = 0

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

                # HC5 FIX: Propagate outcome to
                # any SA children pointing to this
                # signal as their parent
                n = _propagate_sa_outcome(
                    history, sig_id, after)
                sa_propagated += n

    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[outcome] Done — "
                  f"resolved:{resolved} "
                  f"updated:{updated} "
                  f"sa_propagated:{sa_propagated}")
        except Exception as e:
            print(f"[outcome] Save failed: {e}")
    else:
        print("[outcome] No updates needed")


if __name__ == '__main__':
    run_outcome_evaluation()
