# ── recover_stuck_signals.py ─────────────────────────
# ONE-TIME RECOVERY SCRIPT
#
# Purpose: Resolve signals stuck in PENDING state
# because outcome_evaluator.py yfinance fetches
# returned empty on Apr 17, 2026 EOD run (and prior).
#
# Data source: output/eod_prices.json (contains OHLC
# for every open position from stop-check run — this
# data exists and is fresh).
#
# Logic:
#   1. Find signals: result=="PENDING",
#      outcome in (OPEN, None), entry_valid!=False,
#      effective_exit_date <= today
#   2. Match to eod_prices.json entry by
#      symbol + signal + signal_date
#   3. If stop_hit:true → STOP_HIT
#      Else → DAY6_WIN / DAY6_LOSS / DAY6_FLAT by
#      close vs entry (close instead of open —
#      fallback because eod_prices has no open)
#   4. Write outcome fields matching schema v5
#   5. Propagate SA child outcomes (HC5)
#   6. Send Telegram summary
#
# SAFETY:
#   - _backup_history() called before write
#   - Skips terminal outcomes (OE2 guard)
#   - Skips entry_valid=False (gap invalidated)
#   - STOP_HIT pnl forced negative (OE3)
#   - r_multiple capped (OE1)
#   - failure_reason via existing classifier (H12)
#   - Flags data_quality="recovery_close_fallback"
#     on every recovered signal for later filtering
#   - Preserves existing mfe_pct/mae_pct from LTP
#
# USAGE: Run via GitHub Actions manual dispatch.
#        Workflow: recover_stuck_signals.yml
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)
from outcome_evaluator import (
    _load_holidays,
    _is_trading_day,
    _next_trading_day,
    _get_entry_date,
    _get_nth_trading_day,
    _count_trading_days,
    _resolve_entry,
    _calculate_target,
    _calc_pnl_pct,
    _calc_r_multiple,
    _classify_failure_reason,
    _propagate_sa_outcome,
    _TERMINAL_OUTCOMES,
    FLAT_PCT,
)

_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')
EOD_FILE = os.path.join(_OUTPUT, 'eod_prices.json')


# ── EOD LOADER ────────────────────────────────────────

def _load_eod_prices():
    """Load eod_prices.json and build lookup map."""
    try:
        with open(EOD_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[recover] Cannot load "
              f"eod_prices.json: {e}")
        return None, {}

    eod_date = data.get('date', '')
    results  = data.get('results', [])

    # Build lookup: (symbol, signal, signal_date)
    # → OHLC record
    lookup = {}
    for rec in results:
        key = (
            rec.get('symbol', ''),
            rec.get('signal', ''),
            rec.get('signal_date', ''),
        )
        lookup[key] = rec

    print(f"[recover] eod_prices.json date="
          f"{eod_date} records={len(results)}")

    return eod_date, lookup


# ── TELEGRAM ──────────────────────────────────────────

def _send_telegram(message):
    """Send summary to Telegram."""
    try:
        import requests
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat  = os.environ.get('TELEGRAM_CHAT_ID')
        if not token or not chat:
            print("[recover] Telegram secrets "
                  "missing — skipping send")
            return
        url = (f"https://api.telegram.org/bot"
               f"{token}/sendMessage")
        r = requests.post(url, json={
            'chat_id'     : chat,
            'text'        : message,
            'parse_mode'  : 'HTML',
        }, timeout=10)
        if r.status_code == 200:
            print("[recover] Telegram sent")
        else:
            print(f"[recover] Telegram failed: "
                  f"{r.status_code} {r.text}")
    except Exception as e:
        print(f"[recover] Telegram error: {e}")


# ── RESOLVE SIGNAL FROM EOD RECORD ────────────────────

def _resolve_from_eod(signal, eod_rec,
                      eod_date, holidays):
    """
    Take a stuck signal and an eod_prices.json
    matching record. Compute outcome and write
    fields in-place. Returns (outcome, success_bool).
    """
    sym       = signal.get('symbol', '')
    direction = signal.get('direction', 'LONG')
    det_date  = signal.get('date', '')

    entry = _resolve_entry(signal)
    stop_val = signal.get('stop', None)
    stop = float(stop_val) if stop_val else None

    if not entry or not stop:
        print(f"[recover] Skip {sym} — "
              f"missing entry/stop")
        return None, False

    # Ensure target is set
    target = signal.get('target_price')
    if not target:
        target = _calculate_target(
            entry, stop, direction)
        if target:
            signal['target_price'] = target
    else:
        try:
            target = float(target)
        except Exception:
            target = _calculate_target(
                entry, stop, direction)
            if target:
                signal['target_price'] = target

    if not target:
        print(f"[recover] Skip {sym} — "
              f"no target")
        return None, False

    # Pull OHLC from eod record
    try:
        close = float(eod_rec.get('close', 0))
        high  = float(eod_rec.get('high',  0))
        low   = float(eod_rec.get('low',   0))
        stop_hit_flag = bool(
            eod_rec.get('stop_hit', False))
    except Exception as e:
        print(f"[recover] {sym} — bad eod "
              f"OHLC: {e}")
        return None, False

    if close <= 0:
        print(f"[recover] {sym} — close<=0, "
              f"cannot resolve")
        return None, False

    # Compute entry_date, tracking_end from det_date
    try:
        entry_date   = _get_entry_date(
            det_date, holidays)
        tracking_end = _get_nth_trading_day(
            entry_date, 6, holidays)
        effective_tracking_end = _next_trading_day(
            tracking_end, holidays)
    except Exception as e:
        print(f"[recover] {sym} date err: {e}")
        return None, False

    # Determine outcome
    outcome     = None
    exit_price  = None
    exit_day    = None
    exit_date_v = None

    if stop_hit_flag:
        # STOP_HIT — trust stop_alert_writer flag
        outcome     = 'STOP_HIT'
        exit_price  = round(stop, 2)
        exit_day    = 6  # (recovered at Day 6 EOD,
                         # may have hit earlier)
        exit_date_v = eod_date
        print(f"[recover] {sym} → STOP_HIT "
              f"(from eod stop_hit flag)")
    else:
        # DAY 6 resolution using CLOSE as fallback
        # (eod_prices has no open — acceptable
        # trade-off, flagged via data_quality)
        if direction == 'LONG':
            move_pct = (close - entry) / entry * 100
        else:
            move_pct = (entry - close) / entry * 100

        if move_pct > FLAT_PCT:
            outcome = 'DAY6_WIN'
        elif move_pct < -FLAT_PCT:
            outcome = 'DAY6_LOSS'
        else:
            outcome = 'DAY6_FLAT'

        exit_price  = round(close, 2)
        exit_day    = 6
        exit_date_v = eod_date

        print(f"[recover] {sym} → {outcome} "
              f"move {move_pct:+.2f}% "
              f"close ₹{close:.2f}")

    # Compute pnl_pct
    pnl_pct = _calc_pnl_pct(
        entry, exit_price, direction)

    # OE3: force STOP_HIT negative
    if outcome == 'STOP_HIT':
        if pnl_pct is not None and pnl_pct > 0:
            print(f"[recover] OE3 fix {sym} — "
                  f"flipping pnl {pnl_pct}%")
            pnl_pct = -abs(pnl_pct)

    # OE1: r_multiple with hard caps
    r_mult = _calc_r_multiple(
        entry         = entry,
        stop          = stop,
        outcome_price = exit_price,
        direction     = direction,
        outcome_type  = outcome,
    )

    # Preserve existing mfe/mae from LTP tracking
    # (don't overwrite — LTP tracking across 6 days
    # is more accurate than single-day eod)
    mfe_existing = signal.get('mfe_pct')
    mae_existing = signal.get('mae_pct')

    # H12: classifier
    failure_reason = _classify_failure_reason(
        signal   = signal,
        outcome  = outcome,
        exit_day = exit_day,
        mae_pct  = mae_existing or 0,
    )

    # WRITE FIELDS (matches outcome_evaluator)
    signal['outcome']        = outcome
    signal['outcome_date']   = exit_date_v
    signal['outcome_price']  = exit_price
    signal['pnl_pct']        = pnl_pct
    signal['r_multiple']     = r_mult
    signal['exit_type']      = outcome
    signal['exit_day']       = exit_day
    signal['failure_reason'] = failure_reason
    signal['day6_open']      = exit_price  # close used
    signal['days_to_outcome']= exit_day

    # Keep existing mfe/mae; only fill if missing
    if mfe_existing is None:
        signal['mfe_pct'] = 0.0
    if mae_existing is None:
        signal['mae_pct'] = 0.0

    # effective_exit_date
    signal['effective_exit_date'] = \
        effective_tracking_end.strftime('%Y-%m-%d')

    # tracking_start / tracking_end if missing
    if not signal.get('tracking_start'):
        signal['tracking_start'] = \
            entry_date.strftime('%Y-%m-%d')
    if not signal.get('tracking_end'):
        signal['tracking_end'] = \
            tracking_end.strftime('%Y-%m-%d')

    # Recovery flag for later filtering
    signal['data_quality'] = 'recovery_close_fallback'
    signal['recovery_source'] = 'eod_prices.json'
    signal['recovery_date']   = str(date.today())

    # Map outcome → result
    if outcome == 'TARGET_HIT':
        signal['result'] = 'WON'
    elif outcome == 'STOP_HIT':
        signal['result'] = 'STOPPED'
    else:
        signal['result'] = 'EXITED'

    return outcome, True


# ── MAIN ──────────────────────────────────────────────

def run_recovery():
    print("[recover] === STUCK SIGNAL RECOVERY ===")
    print(f"[recover] Run date: {date.today()}")

    # Load holidays
    holidays = _load_holidays()
    if not holidays:
        print("[recover] WARN — no holidays loaded")

    # Load eod_prices.json
    eod_date, eod_lookup = _load_eod_prices()
    if not eod_lookup:
        msg = ("❌ <b>Recovery failed</b>\n"
               "eod_prices.json not loadable "
               "or empty. Aborting without "
               "writing.")
        _send_telegram(msg)
        return

    # Load signal history
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[recover] Cannot load history: {e}")
        _send_telegram(
            f"❌ <b>Recovery failed</b>\n"
            f"Cannot load signal_history.json: "
            f"{e}")
        return

    history = data.get('history', [])
    today   = date.today()

    # Find stuck signals
    # Criteria: PENDING, OPEN outcome (or null),
    # entry_valid not False, effective_exit_date
    # <= today (or tracking_end <= today if
    # no effective_exit_date yet)
    stuck = []
    for s in history:
        if s.get('result') != 'PENDING':
            continue
        if s.get('outcome') in _TERMINAL_OUTCOMES:
            continue
        if s.get('entry_valid') is False:
            continue
        outcome_val = s.get('outcome')
        if outcome_val not in (None, 'OPEN'):
            continue

        # Check exit date window
        exit_date_str = (
            s.get('effective_exit_date')
            or s.get('exit_date')
            or s.get('tracking_end')
            or '')
        if not exit_date_str:
            continue
        try:
            exit_d = datetime.strptime(
                exit_date_str[:10],
                '%Y-%m-%d').date()
        except Exception:
            continue
        if exit_d > today:
            continue

        stuck.append(s)

    print(f"[recover] Found {len(stuck)} "
          f"stuck signals")

    if not stuck:
        _send_telegram(
            "ℹ️ <b>Recovery ran</b>\n"
            "No stuck signals found. "
            "Nothing to resolve.")
        return

    # Build history index map
    history_map = {
        s.get('id'): i
        for i, s in enumerate(history)
    }

    # Process each stuck signal
    resolved    = 0
    skipped     = 0
    sa_prop     = 0
    by_outcome  = {}
    skipped_syms = []

    for signal in stuck:
        sig_id = signal.get('id', '')
        sym    = signal.get('symbol', '')
        sig_t  = signal.get('signal', '')
        sig_d  = signal.get('date', '')

        key = (sym, sig_t, sig_d)
        eod_rec = eod_lookup.get(key)

        if eod_rec is None:
            print(f"[recover] SKIP {sig_id} — "
                  f"no eod match for "
                  f"({sym},{sig_t},{sig_d})")
            skipped += 1
            skipped_syms.append(
                f"{sym}-{sig_t}")
            continue

        # Work on a copy
        updated_sig = signal.copy()
        outcome, ok = _resolve_from_eod(
            updated_sig, eod_rec,
            eod_date, holidays)

        if not ok or not outcome:
            skipped += 1
            skipped_syms.append(
                f"{sym}-{sig_t}")
            continue

        # Write back to history array
        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx] = updated_sig
            resolved += 1

            by_outcome[outcome] = \
                by_outcome.get(outcome, 0) + 1

            # HC5: SA propagation
            n = _propagate_sa_outcome(
                history, sig_id, outcome)
            sa_prop += n

    # Save if anything resolved
    if resolved > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[recover] SAVED — "
                  f"resolved:{resolved} "
                  f"skipped:{skipped} "
                  f"sa_prop:{sa_prop}")
        except Exception as e:
            print(f"[recover] SAVE FAILED: {e}")
            _send_telegram(
                f"❌ <b>Recovery WRITE FAILED</b>\n"
                f"{e}")
            return
    else:
        print("[recover] No signals resolved "
              "— nothing saved")

    # Telegram summary
    lines = []
    lines.append(
        f"✅ <b>Recovery complete</b>")
    lines.append(
        f"Resolved: <b>{resolved}</b>")
    if by_outcome:
        for k, v in sorted(by_outcome.items()):
            lines.append(f"  • {k}: {v}")
    if skipped > 0:
        lines.append(
            f"Skipped: <b>{skipped}</b>")
        if skipped_syms[:10]:
            lines.append(
                "  " + ", ".join(
                    skipped_syms[:10]))
            if len(skipped_syms) > 10:
                lines.append(
                    f"  …+{len(skipped_syms)-10}"
                    f" more")
    if sa_prop > 0:
        lines.append(
            f"SA propagated: {sa_prop}")
    lines.append("")
    lines.append(
        "All recovered signals flagged "
        "<code>data_quality=recovery_"
        "close_fallback</code>")

    _send_telegram("\n".join(lines))


if __name__ == '__main__':
    run_recovery()
