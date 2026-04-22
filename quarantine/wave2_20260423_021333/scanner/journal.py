# scanner/journal.py
# Owns signal_history.json and signal_archive.json
# ONLY this file writes these two files
#
# BUG 3 FIX: backfill_generation_flags() normalizes
#   vol_confirm from string → boolean.
#
# BUG 4 FIX: exit_date uses trading-day calculation.
#
# BUG 5 FIX: log_rejected() sets outcome=None.
#
# BUG 6 FIX: scan_time stored as UTC explicitly.
#
# V1 FIXES APPLIED:
# - L5  : user_action field + update_user_action()
#         Lets frontend persist Took/Skip to record
# - R1  : schema_version 4 → 5
#         New fields: user_action, is_sa,
#         rs_strong, grade_A, sec_leading
#         backfill_schema_v5() migration function
# - R6  : SA signal tracking
#         is_sa flag, sa_parent_id, sa_parent_outcome
#         update_sa_parent_outcome()
#         get_sa_signals()
#
# Key rules:
# 1. Dedup on every write — same id never written twice
# 2. Backup before every write
# 3. Validate after every write
# 4. Active window = 90 trading days in main file
# 5. Older records move to signal_archive.json
# 6. Lifelong data preserved in archive — never deleted
# 7. Auto-TOOK default — every signal recorded
# 8. schema_version = 5 on all new records

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

SCHEMA_VERSION = 5          # R1: bumped from 4
ACTIVE_DAYS    = 90
ARCHIVE_DAYS   = 9999

# ── LIVE START DATE ───────────────────────────────────
LIVE_START_DATE = "2026-04-06"

# ── V5 DEFAULT VALUES ─────────────────────────────────
# Used by backfill_schema_v5() and new records.
# Keeps migration and record creation in sync.
_V5_DEFAULTS = {
    "user_action":      None,   # L5: None/TOOK/SKIPPED
    "is_sa":            False,  # R6: second attempt flag
    "sa_parent_id":     None,   # R6: parent signal id
    "sa_parent_outcome": None,  # R6: filled on parent resolve
    "rs_strong":        False,  # quality flag (was missing)
    "grade_A":          False,  # quality flag (was missing)
    "sec_leading":      False,  # quality flag (was missing)
}


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
    if signal_date_str and signal_date_str >= LIVE_START_DATE:
        return 1, 'live'
    return 0, 'backfill'


# ── R6: SA HELPERS ────────────────────────────────────
def _is_sa(signal_type: str) -> bool:
    """True if signal type ends with _SA (second attempt)."""
    return (signal_type or '').upper().endswith('_SA')


def _sa_parent_id(signal_date, symbol,
                  signal_type, parent_date=None):
    """
    Derive the parent signal id from an SA signal.
    Parent signal type = SA type with _SA stripped.
    Parent date = parent_date if provided, else signal_date.
    """
    base_type  = (signal_type or '').upper()
    if base_type.endswith('_SA'):
        base_type = base_type[:-3]
    sym_clean  = symbol.replace('.NS', '')
    date_str   = parent_date or signal_date
    return f"{date_str}-{sym_clean}-{base_type}"


# ── BUG 4 FIX: TRADING DAY EXIT DATE ─────────────────
def _add_trading_days(start_date, n):
    if isinstance(start_date, str):
        start_date = datetime.strptime(
            start_date, '%Y-%m-%d').date()
    count = 0
    cur   = start_date
    while count < n:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            count += 1
    return cur


def _get_exit_date(signal_date_str):
    try:
        sig_date   = datetime.strptime(
            signal_date_str, '%Y-%m-%d').date()
        entry_date = _add_trading_days(sig_date, 1)
        exit_date  = _add_trading_days(entry_date, 5)
        return exit_date.isoformat()
    except Exception:
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


# ── QUALITY FLAG NORMALISER ───────────────────────────
def _bool_flag(sig, field):
    """Safely extract a boolean quality flag from signal."""
    v = sig.get(field, False)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == 'true'
    return bool(v)


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
    _ensure_output_dir()
    if not os.path.exists(ARCHIVE_FILE):
        try:
            _save_json(ARCHIVE_FILE, _empty_archive())
            print("[journal] signal_archive.json created (empty)")
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

    exit_date    = _get_exit_date(today)
    scan_price   = _resolve_scan_price(sig)
    entry_est    = sig.get('entry_est', None)
    stop         = sig.get('stop', None)
    target_price = _calculate_target(
        scan_price or entry_est, stop, direction)

    generation, data_quality = _get_generation(today)
    scan_time_utc = datetime.utcnow().strftime('%H:%M UTC')

    vc = sig.get('vol_confirm', False)
    if isinstance(vc, str):
        vc = vc.strip().lower() == 'true'

    # R6: SA detection
    sa_flag     = _is_sa(signal_t)
    parent_date = sig.get('parent_date', None)
    parent_id   = (
        _sa_parent_id(today, symbol, signal_t, parent_date)
        if sa_flag else None
    )

    record = {
        # ── identity ──────────────────────────────────
        "id":               record_id,
        "schema_version":   SCHEMA_VERSION,
        "generation":       generation,
        "data_quality":     data_quality,
        # ── signal context ────────────────────────────
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
        "stock_regime":     sig.get('stock_regime', ''),
        # ── quality flags ─────────────────────────────
        "vol_q":            sig.get('vol_q', ''),
        "vol_confirm":      vc,
        "rs_q":             sig.get('rs_q', ''),
        "rs_strong":        _bool_flag(sig, 'rs_strong'),
        "sec_mom":          sig.get('sec_mom', ''),
        "sec_leading":      _bool_flag(sig, 'sec_leading'),
        "bear_bonus":       bool(sig.get('bear_bonus', False)),
        "grade_A":          (sig.get('grade', 'C') == 'A'),
        # ── price / trade levels ──────────────────────
        "scan_price":       scan_price,
        "scan_time":        scan_time_utc,
        "pivot_price":      sig.get('pivot_price', None),
        "pivot_date":       sig.get('pivot_date', ''),
        "entry":            scan_price or entry_est,
        "stop":             stop,
        "atr":              sig.get('atr', None),
        "exit_date":        exit_date,
        "target_price":     target_price,
        # ── open validation (filled by open_validator) ─
        "actual_open":      None,
        "adjusted_rr":      None,
        "entry_valid":      None,
        "gap_pct":          None,
        # ── outcome tracking ──────────────────────────
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
        # ── status ────────────────────────────────────
        "result":           "PENDING",
        "action":           "TOOK",
        # ── L5: user decision ─────────────────────────
        "user_action":      None,
        # ── R6: SA tracking ───────────────────────────
        "is_sa":            sa_flag,
        "sa_parent_id":     parent_id,
        "sa_parent_outcome": None,
        # ── lineage ───────────────────────────────────
        "attempt_number":   attempt,
        "parent_signal_id": sig.get('parent_signal_id', None),
        "parent_signal":    sig.get('parent_signal', None),
        "parent_date":      parent_date,
        "parent_result":    sig.get('parent_result', None),
        # ── meta ──────────────────────────────────────
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
              f"gen={generation} "
              f"is_sa={sa_flag}")
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
    scan_time_utc = datetime.utcnow().strftime('%H:%M UTC')

    vc = sig.get('vol_confirm', False)
    if isinstance(vc, str):
        vc = vc.strip().lower() == 'true'

    sa_flag = _is_sa(signal_t)

    record = {
        # ── identity ──────────────────────────────────
        "id":                  record_id,
        "schema_version":      SCHEMA_VERSION,
        "generation":          generation,
        "data_quality":        data_quality,
        # ── signal context ────────────────────────────
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
        "stock_regime":        sig.get('stock_regime', ''),
        # ── quality flags ─────────────────────────────
        "vol_q":               sig.get('vol_q', ''),
        "vol_confirm":         vc,
        "rs_q":                sig.get('rs_q', ''),
        "rs_strong":           _bool_flag(sig, 'rs_strong'),
        "sec_mom":             sig.get('sec_mom', ''),
        "sec_leading":         _bool_flag(sig, 'sec_leading'),
        "bear_bonus":          bool(sig.get('bear_bonus', False)),
        "grade_A":             (sig.get('grade', 'C') == 'A'),
        # ── price ─────────────────────────────────────
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
        # BUG 5 FIX: rejected = no trade, outcome = None
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
        # ── status ────────────────────────────────────
        "result":              "REJECTED",
        "action":              "REJECTED",
        # ── L5 ────────────────────────────────────────
        "user_action":         None,
        # ── R6 ────────────────────────────────────────
        "is_sa":               sa_flag,
        "sa_parent_id":        None,
        "sa_parent_outcome":   None,
        # ── lineage ───────────────────────────────────
        "attempt_number":      sig.get('attempt_number', 1),
        "parent_signal_id":    sig.get(
                                   'parent_signal_id', None),
        "parent_signal":       sig.get('parent_signal', None),
        "parent_date":         sig.get('parent_date', None),
        "parent_result":       None,
        # ── meta ──────────────────────────────────────
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


# ── L5: UPDATE USER ACTION ────────────────────────────
def update_user_action(record_id: str, action: str):
    """
    Persist frontend Took/Skip decision to record.
    action: 'TOOK' | 'SKIPPED' | None (to clear)
    Called when user taps a button and frontend
    wants server-side persistence (optional path).
    Safe to call repeatedly — idempotent.
    """
    valid = {'TOOK', 'SKIPPED', None}
    if action not in valid:
        print(f"[journal] Invalid user_action: {action}")
        return False

    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if record.get('id') == record_id:
            record['user_action'] = action
            updated = True
            break

    if not updated:
        print(f"[journal] update_user_action: "
              f"id not found: {record_id}")
        return False

    _backup_history()
    data['history'] = history
    try:
        _save_json(HISTORY_FILE, data)
        print(f"[journal] user_action={action} "
              f"set on {record_id}")
        return True
    except RuntimeError as e:
        print(f"[journal] update_user_action failed: {e}")
        return False


# ── R6: UPDATE SA PARENT OUTCOME ─────────────────────
def update_sa_parent_outcome(parent_id: str,
                             parent_outcome: str):
    """
    When a parent signal resolves, propagate its outcome
    to all open SA child signals referencing it.
    Called from outcome_evaluator after a signal closes.
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = 0

    for record in history:
        if (record.get('is_sa')
                and record.get('sa_parent_id') == parent_id
                and record.get('sa_parent_outcome') is None):
            record['sa_parent_outcome'] = parent_outcome
            updated += 1

    if not updated:
        return

    _backup_history()
    data['history'] = history
    try:
        _save_json(HISTORY_FILE, data)
        print(f"[journal] SA parent outcome propagated: "
              f"parent={parent_id} "
              f"outcome={parent_outcome} "
              f"children_updated={updated}")
    except RuntimeError as e:
        print(f"[journal] SA propagation failed: {e}")


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
        target    = _calculate_target(
            entry, stop, direction)

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


# ── R1: SCHEMA V5 MIGRATION ───────────────────────────
def backfill_schema_v5():
    """
    Adds V5 fields to all existing records that lack them.
    Idempotent — only touches records missing the fields.
    Fields added: user_action, is_sa, sa_parent_id,
    sa_parent_outcome, rs_strong, grade_A, sec_leading.
    Also bumps schema_version to 5 on each record.
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    fixed   = 0

    for record in history:
        changed = False

        # bump record-level schema version
        if record.get('schema_version', 0) < 5:
            record['schema_version'] = SCHEMA_VERSION
            changed = True

        # add any missing V5 fields
        for field, default in _V5_DEFAULTS.items():
            if field not in record:
                # special case: derive is_sa from signal type
                if field == 'is_sa':
                    record['is_sa'] = _is_sa(
                        record.get('signal', ''))
                # grade_A: derive from grade field
                elif field == 'grade_A':
                    record['grade_A'] = (
                        record.get('grade', 'C') == 'A')
                else:
                    record[field] = default
                changed = True

        if changed:
            fixed += 1

    if fixed > 0:
        _backup_history()
        data['history']       = history
        data['schema_version'] = SCHEMA_VERSION
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[journal] Schema V5 migration: "
                  f"{fixed} records updated")
        except RuntimeError as e:
            print(f"[journal] V5 migration failed: {e}")
    else:
        print("[journal] Schema V5: all records current")


# ── GENERATION BACKFILL + ALL NORMALISATION ───────────
def backfill_generation_flags():
    """
    Master backfill — runs all normalisation passes:
    1. generation / data_quality flags
    2. vol_confirm string → boolean  (BUG 3)
    3. REJECTED outcome → None       (BUG 5)
    4. Schema V5 fields              (R1)
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    gen_fixed  = 0
    vol_fixed  = 0
    out_fixed  = 0
    any_change = False

    for record in history:
        # 1. Generation flag
        if record.get('generation') is None:
            sig_date = record.get('date', '')
            generation, data_quality = \
                _get_generation(sig_date)
            record['generation']   = generation
            record['data_quality'] = data_quality
            gen_fixed  += 1
            any_change  = True

        # 2. vol_confirm string → boolean
        vc = record.get('vol_confirm')
        if isinstance(vc, str):
            record['vol_confirm'] = \
                vc.strip().lower() == 'true'
            vol_fixed  += 1
            any_change  = True

        # 3. REJECTED records → outcome = None
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
            print(f"[journal] Backfill: "
                  f"gen={gen_fixed} | "
                  f"vol_confirm={vol_fixed} | "
                  f"outcome_fixed={out_fixed}")
        except RuntimeError as e:
            print(f"[journal] Backfill failed: {e}")
            return
    else:
        print("[journal] Backfill: nothing to fix")

    # 4. Schema V5 — always run as second pass
    backfill_schema_v5()


# ── QUERY FUNCTIONS ───────────────────────────────────
def get_open_trades():
    history = load_history()
    return [
        r for r in history
        if r.get('result')  == 'PENDING'
        and r.get('action') == 'TOOK'
    ]


def get_active_signals_count():
    return len(get_open_trades())


def get_recent_closed(n=10):
    history = load_history()
    closed  = [
        r for r in history
        if r.get('result') in ('WON', 'STOPPED', 'EXITED')
    ]
    closed.sort(key=lambda x: x.get('date', ''))
    return closed[-n:]


# ── R6: SA QUERY ──────────────────────────────────────
def get_sa_signals(open_only=False):
    """
    Returns all SA signals from history.
    open_only=True → only PENDING SA signals.
    """
    history = load_history()
    sa = [r for r in history if r.get('is_sa')]
    if open_only:
        sa = [r for r in sa
              if r.get('result') == 'PENDING']
    return sa


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
