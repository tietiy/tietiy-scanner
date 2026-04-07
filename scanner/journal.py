# scanner/journal.py
# Owns signal_history.json and signal_archive.json
# ONLY this file writes these two files
#
# BUG 3 FIX: backfill_generation_flags() now also
#   normalizes vol_confirm from string → boolean.
#   "True"/"true" → True, "False"/"false" → False
#
# BUG 4 FIX: exit_date now computed using proper
#   trading-day calculation (skip weekends). Previously
#   used timedelta(days=8) which was calendar days only.
#
# BUG 5 FIX: log_rejected() now sets outcome=None
#   (not "OPEN"). Rejected signals have no trade.
#   This prevents outcome_evaluator from processing them.
#
# BUG 6 FIX: scan_time now stored as UTC explicitly.
#   Was labeled "IST" but stored UTC value.
#
# Key rules:
# 1. Dedup on every write — same id never written twice
# 2. Backup before every write
# 3. Validate after every write
# 4. Active window = 90 trading days in main file
# 5. Older records move to signal_archive.json
# 6. Lifelong data preserved in archive — never deleted
# 7. Auto-TOOK default — every signal recorded
# 8. schema_version = 4 on all records

import json
import os
import sys
import shutil
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from config import PIVOT_LOOKBACK

# ── PATHS ─────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(os.path.dirname(_HERE), 'output')

HISTORY_FILE = os.path.join(_OUTPUT_DIR, 'signal_history.json')
ARCHIVE_FILE = os.path.join(_OUTPUT_DIR, 'signal_archive.json')
BACKUP_FILE  = os.path.join(
    _OUTPUT_DIR, 'signal_history.backup.json')

SCHEMA_VERSION = 4
ACTIVE_DAYS    = 90
ARCHIVE_DAYS   = 9999

# ── LIVE START DATE ───────────────────────────────────
# Signals before this date = generation=0 (backfill)
# Signals from this date = generation=1 (live)
LIVE_START_DATE = "2026-04-06"


# ── HELPERS ───────────────────────────────────────────
def _ensure_output_dir():
    os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _empty_history():
    return {"schema_version": SCHEMA_VERSION, "history": []}


def _empty_archive():
    return {"schema_version": SCHEMA_VERSION, "history": []}


def _load_json(path, default_fn):
    if not os.path.exists(path):
        return default_fn()
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if 'history' not in data:
            return default_fn()
        return data
    except Exception as e:
        print(f"[journal] Load error {path}: {e}")
        return default_fn()


def _save_json(path, data):
    _ensure_output_dir()
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    try:
        with open(tmp_path, 'r') as f:
            validated = json.load(f)
        if 'history' not in validated:
            raise ValueError("history key missing after write")
    except Exception as e:
        os.remove(tmp_path)
        raise RuntimeError(
            f"[journal] Write validation failed: {e}")
    os.replace(tmp_path, path)


def _backup_history():
    if os.path.exists(HISTORY_FILE):
        try:
            shutil.copy2(HISTORY_FILE, BACKUP_FILE)
        except Exception as e:
            print(f"[journal] Backup warning: {e}")


def _make_id(signal_date, symbol, signal_type, attempt=1):
    sym_clean = symbol.replace('.NS', '')
    base = f"{signal_date}-{sym_clean}-{signal_type}"
    if attempt == 2:
        base += "-SA"
    return base


def _trading_day_cutoff(days_back):
    approx_calendar = int(days_back * 1.45)
    cutoff = date.today() - timedelta(days=approx_calendar)
    return cutoff.isoformat()


def _get_generation(signal_date_str):
    """
    Returns (generation, data_quality).
    generation=0 = pre-live backfill data
    generation=1 = live scanner data
    """
    if signal_date_str and signal_date_str >= LIVE_START_DATE:
        return 1, 'live'
    return 0, 'backfill'


# ── BUG 4 FIX: TRADING DAY EXIT DATE ─────────────────
def _add_trading_days(start_date, n):
    """
    Returns the date that is n trading days after
    start_date, skipping weekends.
    Holidays not available in journal context —
    weekend skip only. calendar_utils handles holidays
    for outcome_evaluator which uses a separate function.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(
            start_date, '%Y-%m-%d').date()
    count = 0
    cur   = start_date
    while count < n:
        cur += timedelta(days=1)
        if cur.weekday() < 5:   # 0=Mon … 4=Fri
            count += 1
    return cur


def _get_exit_date(signal_date_str):
    """
    Computes the exit date: entry is next trading day
    after signal date, exit is 6 trading days after entry.
    Total = 7 trading days after signal date (entry + 5
    more trading days = day 6 at open).
    Uses _add_trading_days which skips weekends.
    """
    try:
        sig_date = datetime.strptime(
            signal_date_str, '%Y-%m-%d').date()
        # Entry = next trading day after signal
        entry_date = _add_trading_days(sig_date, 1)
        # Exit = 5 trading days after entry
        # (trade days 1-5, exit at open of day 6)
        exit_date  = _add_trading_days(entry_date, 5)
        return exit_date.isoformat()
    except Exception:
        # Fallback to approximate
        try:
            sig_dt = datetime.strptime(
                signal_date_str, '%Y-%m-%d').date()
            return (sig_dt + timedelta(days=9)).isoformat()
        except Exception:
            return None


# ── TARGET PRICE HELPER ───────────────────────────────
def _calculate_target(entry, stop, direction):
    try:
        entry = float(entry or 0)
        stop  = float(stop  or 0)
        risk  = abs(entry - stop)
        if risk <= 0 or entry <= 0:
            return None
        if direction == 'LONG':
            return round(entry + 2 * risk, 2)
        else:
            return round(entry - 2 * risk, 2)
    except Exception:
        return None


# ── SCAN PRICE HELPER ─────────────────────────────────
def _resolve_scan_price(sig):
    for field in ['entry_est', 'entry', 'scan_price']:
        val = sig.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except Exception:
                continue
    return None


# ── CORE PUBLIC FUNCTIONS ─────────────────────────────
def load_history():
    data = _load_json(HISTORY_FILE, _empty_history)
    return data.get('history', [])


def load_archive():
    data = _load_json(ARCHIVE_FILE, _empty_archive)
    return data.get('history', [])


def get_history_count():
    data = _load_json(HISTORY_FILE, _empty_history)
    return len(data.get('history', []))


def ensure_archive_exists():
    """
    Creates an empty signal_archive.json if it does not
    exist. Called on startup.
    """
    _ensure_output_dir()
    if not os.path.exists(ARCHIVE_FILE):
        try:
            _save_json(ARCHIVE_FILE, _empty_archive())
            print("[journal] signal_archive.json "
                  "created (empty)")
        except Exception as e:
            print(f"[journal] Archive init failed: {e}")


def log_signal(sig, layer='MINI'):
    _ensure_output_dir()

    today     = date.today().isoformat()
    symbol    = sig.get('symbol', '')
    signal_t  = sig.get('signal', '')
    attempt   = sig.get('attempt_number', 1)
    direction = sig.get('direction', 'LONG')
    record_id = _make_id(today, symbol, signal_t, attempt)

    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    existing_ids = {r.get('id') for r in history}
    if record_id in existing_ids:
        print(f"[journal] Duplicate skipped: {record_id}")
        return

    # BUG 4 FIX: use trading-day exit date
    exit_date    = _get_exit_date(today)
    scan_price   = _resolve_scan_price(sig)
    entry_est    = sig.get('entry_est', None)
    stop         = sig.get('stop', None)
    target_price = _calculate_target(
        scan_price or entry_est, stop, direction)

    generation, data_quality = _get_generation(today)

    # BUG 6 FIX: label as UTC (was labeled IST but stored UTC)
    scan_time_utc = datetime.utcnow().strftime('%H:%M UTC')

    # Normalize vol_confirm on incoming signal
    vc = sig.get('vol_confirm', False)
    if isinstance(vc, str):
        vc = vc.strip().lower() == 'true'

    record = {
        "id":               record_id,
        "schema_version":   SCHEMA_VERSION,
        "generation":       generation,
        "data_quality":     data_quality,
        "date":             today,
        "symbol":           symbol,
        "sector":           sig.get('sector', ''),
        "grade":            sig.get('grade', 'C'),
        "signal":           signal_t,
        "direction":        direction,
        "age":              sig.get('age', 0),
        "score":            sig.get('score', 0),
        "regime":           sig.get('regime', ''),
        "regime_score":     sig.get('regime_score', 0),
        "vol_q":            sig.get('vol_q', ''),
        "vol_confirm":      vc,        # always boolean
        "rs_q":             sig.get('rs_q', ''),
        "sec_mom":          sig.get('sec_mom', ''),
        "bear_bonus":       bool(sig.get('bear_bonus', False)),
        "stock_regime":     sig.get('stock_regime', ''),
        "scan_price":       scan_price,
        "scan_time":        scan_time_utc,
        "pivot_price":      sig.get('pivot_price', None),
        "pivot_date":       sig.get('pivot_date', ''),
        "entry":            scan_price or entry_est,
        "stop":             stop,
        "atr":              sig.get('atr', None),
        "exit_date":        exit_date,
        "target_price":     target_price,
        "actual_open":      None,
        "adjusted_rr":      None,
        "entry_valid":      None,
        "gap_pct":          None,
        "outcome":          "OPEN",
        "outcome_date":     None,
        "outcome_price":    None,
        "tracking_start":   None,
        "tracking_end":     None,
        "mfe_pct":          None,
        "mae_pct":          None,
        "days_to_outcome":  None,
        "exit_price":       None,
        "exit_type":        None,
        "exit_date_actual": None,
        "pnl_pct":          None,
        "pnl_rs":           None,
        "result":           "PENDING",
        "action":           "TOOK",
        "attempt_number":   attempt,
        "parent_signal_id": sig.get('parent_signal_id', None),
        "parent_signal":    sig.get('parent_signal', None),
        "parent_date":      sig.get('parent_date', None),
        "parent_result":    sig.get('parent_result', None),
        "layer":            layer,
        "rejection_reason": None,
        "scanner_version":  sig.get('scanner_version', 'v2.0'),
    }

    _backup_history()
    history.append(record)
    data['history'] = history

    try:
        _save_json(HISTORY_FILE, data)
        print(f"[journal] Logged: {record_id} "
              f"target={target_price} "
              f"scan_price={scan_price} "
              f"gen={generation}")
    except RuntimeError as e:
        print(f"[journal] CRITICAL write failed: {e}")


def log_rejected(sig, rejection_reason,
                 rejection_filter, threshold):
    _ensure_output_dir()

    today     = date.today().isoformat()
    symbol    = sig.get('symbol', '')
    signal_t  = sig.get('signal', '')
    direction = sig.get('direction', 'LONG')
    record_id = _make_id(
        today, symbol, signal_t) + '-REJ'

    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    existing_ids = {r.get('id') for r in history}
    if record_id in existing_ids:
        return

    scan_price   = _resolve_scan_price(sig)
    stop         = sig.get('stop', None)
    target_price = _calculate_target(
        scan_price, stop, direction)

    generation, data_quality = _get_generation(today)

    # BUG 6 FIX: label as UTC
    scan_time_utc = datetime.utcnow().strftime('%H:%M UTC')

    # Normalize vol_confirm
    vc = sig.get('vol_confirm', False)
    if isinstance(vc, str):
        vc = vc.strip().lower() == 'true'

    record = {
        "id":                  record_id,
        "schema_version":      SCHEMA_VERSION,
        "generation":          generation,
        "data_quality":        data_quality,
        "date":                today,
        "symbol":              symbol,
        "sector":              sig.get('sector', ''),
        "grade":               sig.get('grade', 'C'),
        "signal":              signal_t,
        "direction":           direction,
        "age":                 sig.get('age', 0),
        "score":               sig.get('score', 0),
        "regime":              sig.get('regime', ''),
        "regime_score":        sig.get('regime_score', 0),
        "vol_q":               sig.get('vol_q', ''),
        "vol_confirm":         vc,     # always boolean
        "rs_q":                sig.get('rs_q', ''),
        "sec_mom":             sig.get('sec_mom', ''),
        "bear_bonus":          bool(
                                   sig.get('bear_bonus', False)),
        "stock_regime":        sig.get('stock_regime', ''),
        "scan_price":          scan_price,
        "scan_time":           scan_time_utc,
        "entry":               scan_price,
        "stop":                stop,
        "atr":                 sig.get('atr', None),
        "exit_date":           None,
        "target_price":        target_price,
        "actual_open":         None,
        "adjusted_rr":         None,
        "entry_valid":         None,
        "gap_pct":             None,
        # BUG 5 FIX: rejected signals have no trade,
        # outcome must be None — NOT "OPEN".
        # "OPEN" caused outcome_evaluator to attempt
        # tracking on rejected signals.
        "outcome":             None,
        "outcome_date":        None,
        "outcome_price":       None,
        "tracking_start":      None,
        "tracking_end":        None,
        "mfe_pct":             None,
        "mae_pct":             None,
        "days_to_outcome":     None,
        "exit_price":          None,
        "exit_type":           None,
        "exit_date_actual":    None,
        "pnl_pct":             None,
        "pnl_rs":              None,
        "result":              "REJECTED",
        "action":              "REJECTED",
        "attempt_number":      sig.get('attempt_number', 1),
        "parent_signal_id":    sig.get(
                                   'parent_signal_id', None),
        "parent_signal":       sig.get('parent_signal', None),
        "parent_date":         sig.get('parent_date', None),
        "parent_result":       None,
        "layer":               "ALPHA",
        "rejection_reason":    rejection_reason,
        "rejection_filter":    rejection_filter,
        "rejection_threshold": threshold,
        "scanner_version":     sig.get(
                                   'scanner_version', 'v2.0'),
    }

    _backup_history()
    history.append(record)
    data['history'] = history

    try:
        _save_json(HISTORY_FILE, data)
    except RuntimeError as e:
        print(f"[journal] Rejected log failed: {e}")


def update_open_price(symbol, signal_date,
                      actual_open, adjusted_rr,
                      entry_valid, gap_pct):
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol
                and record.get('date') == signal_date
                and record.get('result') == 'PENDING'):
            record['actual_open'] = actual_open
            record['adjusted_rr'] = adjusted_rr
            record['entry_valid'] = entry_valid
            record['gap_pct']     = gap_pct
            updated = True
            break

    if updated:
        _backup_history()
        data['history'] = history
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[journal] Open price updated: {symbol}")
        except RuntimeError as e:
            print(f"[journal] Open price update failed: {e}")


def close_trade(symbol, signal_date,
                exit_price, exit_type):
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol
                and record.get('date') == signal_date
                and record.get('result') == 'PENDING'):
            entry = float(record.get('entry') or 0)
            size  = float(
                record.get('position_size') or 0)

            if entry > 0:
                direction = (
                    1 if record.get('direction') == 'LONG'
                    else -1)
                pnl_pct = round(
                    direction *
                    (exit_price - entry) /
                    entry * 100, 2)
                pnl_rs = round(
                    direction *
                    (exit_price - entry) * size,
                    0) if size > 0 else None

                record['exit_price']       = exit_price
                record['exit_type']        = exit_type
                record['exit_date_actual'] = (
                    date.today().isoformat())
                record['pnl_pct'] = pnl_pct
                record['pnl_rs']  = pnl_rs
                record['result']  = (
                    'STOPPED'   if exit_type == 'StopHit'
                    else 'WON'  if pnl_pct > 0
                    else 'EXITED')
            else:
                record['result']    = 'EXITED'
                record['exit_type'] = exit_type

            updated = True
            break

    if updated:
        _backup_history()
        data['history'] = history
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[journal] Trade closed: {symbol}")
        except RuntimeError as e:
            print(f"[journal] Close trade failed: {e}")


def archive_old_records():
    cutoff = _trading_day_cutoff(ACTIVE_DAYS)

    hist_data = _load_json(HISTORY_FILE, _empty_history)
    arch_data = _load_json(ARCHIVE_FILE, _empty_archive)

    history = hist_data.get('history', [])
    archive = arch_data.get('history', [])

    keep    = []
    to_move = []

    for record in history:
        rec_date = record.get('date', '9999-12-31')
        if record.get('result') == 'PENDING':
            keep.append(record)
        elif rec_date >= cutoff:
            keep.append(record)
        else:
            to_move.append(record)

    if not to_move:
        return

    archive_ids    = {r.get('id') for r in archive}
    new_to_archive = [
        r for r in to_move
        if r.get('id') not in archive_ids
    ]

    if new_to_archive:
        archive.extend(new_to_archive)
        arch_data['history'] = archive
        try:
            _save_json(ARCHIVE_FILE, arch_data)
            print(f"[journal] Archived "
                  f"{len(new_to_archive)} records")
        except RuntimeError as e:
            print(f"[journal] Archive write failed: {e}")
            return

    hist_data['history'] = keep
    _backup_history()
    try:
        _save_json(HISTORY_FILE, hist_data)
        print(f"[journal] History trimmed → "
              f"{len(keep)} active records")
    except RuntimeError as e:
        print(f"[journal] History trim failed: {e}")


# ── S5 — BACKFILL TARGET PRICES ───────────────────────
def backfill_target_prices():
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    fixed   = 0

    for record in history:
        if record.get('target_price') is not None:
            continue
        if record.get('result') != 'PENDING':
            continue

        entry     = (record.get('entry') or
                     record.get('scan_price'))
        stop      = record.get('stop')
        direction = record.get('direction', 'LONG')

        target = _calculate_target(entry, stop, direction)

        if target is not None:
            record['target_price'] = target
            fixed += 1

    if fixed > 0:
        _backup_history()
        data['history'] = history
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[journal] S5 backfill: fixed "
                  f"target_price on {fixed} signals")
        except RuntimeError as e:
            print(f"[journal] S5 backfill failed: {e}")
    else:
        print("[journal] S5 backfill: nothing to fix")


# ── GENERATION BACKFILL + VOL_CONFIRM NORMALIZE ───────
def backfill_generation_flags():
    """
    1. Sets generation=0 for pre-live signals,
       generation=1 for live signals. Idempotent.
    2. BUG 3 FIX: Normalizes vol_confirm from
       string "True"/"False" to boolean True/False.
       Early records were stored as strings due to
       numpy bool_ serialization before S3 fix.
    3. BUG 5 FIX: Ensures REJECTED records have
       outcome=None (not "OPEN").
    4. BUG 6 FIX: Scan times already labeled correctly
       going forward. Old records left as-is (minor).
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    gen_fixed  = 0
    vol_fixed  = 0
    out_fixed  = 0
    any_change = False

    for record in history:
        # Generation flag
        if record.get('generation') is None:
            sig_date = record.get('date', '')
            generation, data_quality = \
                _get_generation(sig_date)
            record['generation']   = generation
            record['data_quality'] = data_quality
            gen_fixed += 1
            any_change = True

        # BUG 3 FIX: vol_confirm string → boolean
        vc = record.get('vol_confirm')
        if isinstance(vc, str):
            record['vol_confirm'] = \
                vc.strip().lower() == 'true'
            vol_fixed  += 1
            any_change  = True

        # BUG 5 FIX: REJECTED records should have
        # outcome=None, not "OPEN"
        if (record.get('result') == 'REJECTED'
                and record.get('outcome') == 'OPEN'):
            record['outcome'] = None
            out_fixed  += 1
            any_change  = True

    if any_change:
        _backup_history()
        data['history'] = history
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[journal] Backfill complete: "
                  f"gen={gen_fixed} | "
                  f"vol_confirm={vol_fixed} | "
                  f"outcome_fixed={out_fixed}")
        except RuntimeError as e:
            print(f"[journal] Backfill failed: {e}")
    else:
        print("[journal] Backfill: nothing to fix")


# ── QUERY FUNCTIONS ───────────────────────────────────
def get_open_trades():
    history = load_history()
    # ONLY return PENDING TOOK signals — not REJECTED
    return [
        r for r in history
        if r.get('result')  == 'PENDING'
        and r.get('action') == 'TOOK'
    ]


def get_active_signals_count():
    """
    Returns count of PENDING TOOK signals.
    Used by meta_writer for status bar display.
    """
    return len(get_open_trades())


def get_recent_closed(n=10):
    history = load_history()
    closed  = [
        r for r in history
        if r.get('result') in ('WON', 'STOPPED', 'EXITED')
    ]
    closed.sort(key=lambda x: x.get('date', ''))
    return closed[-n:]


def get_system_health():
    recent = get_recent_closed(5)
    if len(recent) < 3:
        return 'NORMAL', 0
    wins = sum(
        1 for r in recent
        if r.get('result') == 'WON')
    wr = round(wins / len(recent) * 100)
    if wr >= 70:
        return 'HOT',    wr
    if wr <= 40:
        return 'COLD',   wr
    return 'NORMAL', wr


def get_history_for_symbol(symbol, days_back=15):
    cutoff  = (
        date.today() - timedelta(days=days_back)
    ).isoformat()
    history = load_history()
    return [
        r for r in history
        if r.get('symbol') == symbol
        and r.get('date', '') >= cutoff
    ]


def get_summary():
    history = load_history()
    open_t  = [
        r for r in history
        if r.get('result') == 'PENDING'
    ]
    closed  = [
        r for r in history
        if r.get('result') in ('WON', 'STOPPED', 'EXITED')
    ]
    wins = sum(
        1 for r in closed
        if r.get('result') == 'WON')
    wr   = round(
        wins / len(closed) * 100) if closed else 0
    health, hw = get_system_health()

    return {
        'total_trades':  len(history),
        'open_trades':   len(open_t),
        'closed_trades': len(closed),
        'wins':          wins,
        'win_rate':      wr,
        'health':        health,
        'health_wr':     hw,
    }
