# ── journal.py ───────────────────────────────────────
# Owns signal_history.json and signal_archive.json
# ONLY this file writes these two files
#
# Key rules:
# 1. Dedup on every write — same id never written twice
# 2. Backup before every write
# 3. Validate after every write — read back and parse
# 4. Active window = 90 trading days in main file
# 5. Older records move to signal_archive.json
# 6. Lifelong data preserved in archive — never deleted
# 7. auto-TOOK default — every signal recorded
# 8. schema_version = 4 on all records
#
# FIX 3 — stock_regime field added to log_signal()
# FIX 4 — scan_price fallback fixed (was showing "—")
# ─────────────────────────────────────────────────────

import json
import os
import sys
import shutil
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from config import PIVOT_LOOKBACK

# ── PATHS ─────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(
                  os.path.dirname(_HERE), 'output')

HISTORY_FILE = os.path.join(
                   _OUTPUT_DIR, 'signal_history.json')
ARCHIVE_FILE = os.path.join(
                   _OUTPUT_DIR, 'signal_archive.json')
BACKUP_FILE  = os.path.join(
                   _OUTPUT_DIR,
                   'signal_history.backup.json')

SCHEMA_VERSION = 4
ACTIVE_DAYS    = 90
ARCHIVE_DAYS   = 9999


# ── HELPERS ───────────────────────────────────────────

def _ensure_output_dir():
    os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _empty_history():
    return {
        "schema_version": SCHEMA_VERSION,
        "history": []
    }


def _empty_archive():
    return {
        "schema_version": SCHEMA_VERSION,
        "history": []
    }


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
            raise ValueError(
                "history key missing after write")
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


def _make_id(signal_date, symbol, signal_type,
             attempt=1):
    sym_clean = symbol.replace('.NS', '')
    base = f"{signal_date}-{sym_clean}-{signal_type}"
    if attempt == 2:
        base += "-SA"
    return base


def _trading_day_cutoff(days_back):
    approx_calendar = int(days_back * 1.45)
    cutoff = date.today() - timedelta(
        days=approx_calendar)
    return cutoff.isoformat()


# ── TARGET PRICE HELPER ───────────────────────────────

def _calculate_target(entry, stop, direction):
    """
    Returns 2R target price.
    LONG:  entry + 2 × (entry - stop)
    SHORT: entry - 2 × (stop  - entry)
    Returns None if inputs invalid.
    """
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


# ── SCAN PRICE HELPER — FIX 4 ─────────────────────────
# Was showing "—" because entry_est was None
# Now tries multiple fallback fields

def _resolve_scan_price(sig):
    """
    Resolves the best available scan price
    from signal dict.
    Tries entry_est → entry → scan_price → None
    """
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


def log_signal(sig, layer='MINI'):
    """
    Appends a signal to signal_history.json.

    FIX 3: stock_regime field now stored
    FIX 4: scan_price uses _resolve_scan_price()
           no longer shows "—" in tap panel
    """
    _ensure_output_dir()

    today     = date.today().isoformat()
    symbol    = sig.get('symbol', '')
    signal_t  = sig.get('signal', '')
    attempt   = sig.get('attempt_number', 1)
    direction = sig.get('direction', 'LONG')
    record_id = _make_id(today, symbol,
                         signal_t, attempt)

    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    existing_ids = {r.get('id') for r in history}
    if record_id in existing_ids:
        print(f"[journal] Duplicate skipped: "
              f"{record_id}")
        return

    # Exit date approximation for display
    entry_date = datetime.strptime(today, '%Y-%m-%d')
    exit_dt    = entry_date + timedelta(days=8)
    exit_date  = exit_dt.strftime('%Y-%m-%d')

    # FIX 4 — resolve scan price with fallbacks
    scan_price   = _resolve_scan_price(sig)
    entry_est    = sig.get('entry_est', None)
    stop         = sig.get('stop', None)
    target_price = _calculate_target(
        scan_price or entry_est, stop, direction)

    record = {
        # Identity
        "id":               record_id,
        "schema_version":   SCHEMA_VERSION,
        "date":             today,
        "symbol":           symbol,
        "sector":           sig.get('sector', ''),
        "grade":            sig.get('grade', 'C'),

        # Signal
        "signal":           signal_t,
        "direction":        direction,
        "age":              sig.get('age', 0),
        "score":            sig.get('score', 0),
        "regime":           sig.get('regime', ''),
        "regime_score":     sig.get('regime_score', 0),
        "vol_q":            sig.get('vol_q', ''),
        "vol_confirm":      sig.get('vol_confirm',
                                    False),
        "rs_q":             sig.get('rs_q', ''),
        "sec_mom":          sig.get('sec_mom', ''),
        "bear_bonus":       sig.get('bear_bonus',
                                    False),

        # FIX 3 — individual stock regime
        "stock_regime":     sig.get('stock_regime', ''),

        # Price — FIX 4 applied
        "scan_price":       scan_price,
        "scan_time":        datetime.utcnow().strftime(
                                '%H:%M IST'),
        "pivot_price":      sig.get('pivot_price',
                                    None),
        "pivot_date":       sig.get('pivot_date', ''),
        "entry":            scan_price or entry_est,
        "stop":             stop,
        "atr":              sig.get('atr', None),
        "exit_date":        exit_date,

        # Phase 1 — target price
        "target_price":     target_price,

        # Open validation
        "actual_open":      None,
        "adjusted_rr":      None,
        "entry_valid":      None,
        "gap_pct":          None,

        # Phase 1 — outcome tracking
        "outcome":          "OPEN",
        "outcome_date":     None,
        "outcome_price":    None,
        "tracking_start":   None,
        "tracking_end":     None,
        "mfe_pct":          None,
        "mae_pct":          None,
        "days_to_outcome":  None,

        # Legacy outcome fields
        "exit_price":       None,
        "exit_type":        None,
        "exit_date_actual": None,
        "pnl_pct":          None,
        "pnl_rs":           None,
        "result":           "PENDING",

        # Action
        "action":           "TOOK",

        # Second attempt
        "attempt_number":   attempt,
        "parent_signal_id": sig.get(
                                'parent_signal_id',
                                None),
        "parent_signal":    sig.get(
                                'parent_signal', None),
        "parent_date":      sig.get(
                                'parent_date', None),
        "parent_result":    sig.get(
                                'parent_result', None),

        # System
        "layer":            layer,
        "rejection_reason": None,
        "scanner_version":  sig.get(
                                'scanner_version',
                                'v2.0'),
    }

    _backup_history()
    history.append(record)
    data['history'] = history

    try:
        _save_json(HISTORY_FILE, data)
        print(f"[journal] Logged: {record_id} "
              f"target={target_price} "
              f"scan_price={scan_price}")
    except RuntimeError as e:
        print(f"[journal] CRITICAL write failed: {e}")


def log_rejected(sig, rejection_reason,
                 rejection_filter, threshold):
    """
    Logs a rejected signal.
    result = REJECTED. Used for shadow mode analysis.
    """
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

    # FIX 4 applied to rejected signals too
    scan_price   = _resolve_scan_price(sig)
    stop         = sig.get('stop', None)
    target_price = _calculate_target(
        scan_price, stop, direction)

    record = {
        "id":                  record_id,
        "schema_version":      SCHEMA_VERSION,
        "date":                today,
        "symbol":              symbol,
        "sector":              sig.get('sector', ''),
        "grade":               sig.get('grade', 'C'),
        "signal":              signal_t,
        "direction":           direction,
        "age":                 sig.get('age', 0),
        "score":               sig.get('score', 0),
        "regime":              sig.get('regime', ''),
        "regime_score":        sig.get('regime_score',
                                       0),
        "vol_q":               sig.get('vol_q', ''),
        "vol_confirm":         sig.get('vol_confirm',
                                       False),
        "rs_q":                sig.get('rs_q', ''),
        "sec_mom":             sig.get('sec_mom', ''),
        "bear_bonus":          sig.get('bear_bonus',
                                       False),

        # FIX 3 — stock regime on rejected too
        "stock_regime":        sig.get(
                                   'stock_regime', ''),

        # FIX 4 — resolved scan price
        "scan_price":          scan_price,
        "scan_time":           datetime.utcnow()
                               .strftime('%H:%M IST'),
        "entry":               scan_price,
        "stop":                stop,
        "atr":                 sig.get('atr', None),
        "exit_date":           None,
        "target_price":        target_price,

        # Open validation
        "actual_open":         None,
        "adjusted_rr":         None,
        "entry_valid":         None,
        "gap_pct":             None,

        # Outcome fields
        "outcome":             "OPEN",
        "outcome_date":        None,
        "outcome_price":       None,
        "tracking_start":      None,
        "tracking_end":        None,
        "mfe_pct":             None,
        "mae_pct":             None,
        "days_to_outcome":     None,

        # Legacy
        "exit_price":          None,
        "exit_type":           None,
        "exit_date_actual":    None,
        "pnl_pct":             None,
        "pnl_rs":              None,
        "result":              "REJECTED",
        "action":              "REJECTED",

        # Second attempt
        "attempt_number":      sig.get(
                                   'attempt_number', 1),
        "parent_signal_id":    sig.get(
                                   'parent_signal_id',
                                   None),
        "parent_signal":       sig.get(
                                   'parent_signal',
                                   None),
        "parent_date":         sig.get(
                                   'parent_date', None),
        "parent_result":       None,

        # System
        "layer":               "ALPHA",
        "rejection_reason":    rejection_reason,
        "rejection_filter":    rejection_filter,
        "rejection_threshold": threshold,
        "scanner_version":     sig.get(
                                   'scanner_version',
                                   'v2.0'),
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
    """
    Called by open_validator.py at 9:25 AM.
    Updates actual open price fields on a signal.
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol and
                record.get('date') == signal_date and
                record.get('result') == 'PENDING'):
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
            print(f"[journal] Open price updated: "
                  f"{symbol}")
        except RuntimeError as e:
            print(f"[journal] Open price update "
                  f"failed: {e}")


def close_trade(symbol, signal_date, exit_price,
                exit_type):
    """
    Closes a trade record.
    exit_type: 'StopHit' / 'DayExit' / 'Manual'
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol and
                record.get('date') == signal_date and
                record.get('result') == 'PENDING'):
            entry = float(record.get('entry') or 0)
            size  = float(
                record.get('position_size') or 0)

            if entry > 0:
                direction = (
                    1 if record.get(
                        'direction') == 'LONG' else -1)
                pnl_pct = round(
                    direction *
                    (exit_price - entry) /
                    entry * 100, 2)
                pnl_rs = round(
                    direction *
                    (exit_price - entry) * size, 0) \
                    if size > 0 else None

                record['exit_price']       = exit_price
                record['exit_type']        = exit_type
                record['exit_date_actual'] = (
                    date.today().isoformat())
                record['pnl_pct']          = pnl_pct
                record['pnl_rs']           = pnl_rs
                record['result']           = (
                    'STOPPED'
                    if exit_type == 'StopHit'
                    else 'WON' if pnl_pct > 0
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
    """
    Moves records older than ACTIVE_DAYS to archive.
    PENDING records always kept in active file.
    """
    cutoff = _trading_day_cutoff(ACTIVE_DAYS)

    hist_data = _load_json(
                    HISTORY_FILE, _empty_history)
    arch_data = _load_json(
                    ARCHIVE_FILE, _empty_archive)

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
            print(f"[journal] Archive write "
                  f"failed: {e}")
            return

    hist_data['history'] = keep
    _backup_history()
    try:
        _save_json(HISTORY_FILE, hist_data)
        print(f"[journal] History trimmed → "
              f"{len(keep)} active records")
    except RuntimeError as e:
        print(f"[journal] History trim failed: {e}")


# ── QUERY FUNCTIONS ───────────────────────────────────

def get_open_trades():
    history = load_history()
    return [r for r in history
            if r.get('result') == 'PENDING']


def get_recent_closed(n=10):
    history = load_history()
    closed  = [r for r in history
               if r.get('result') in
               ('WON', 'STOPPED', 'EXITED')]
    closed.sort(
        key=lambda x: x.get('date', ''))
    return closed[-n:]


def get_system_health():
    recent = get_recent_closed(5)
    if len(recent) < 3:
        return 'NORMAL', 0
    wins = sum(1 for r in recent
               if r.get('result') == 'WON')
    wr   = round(wins / len(recent) * 100)
    if wr >= 70:
        return 'HOT',    wr
    if wr <= 40:
        return 'COLD',   wr
    return 'NORMAL', wr


def get_history_for_symbol(symbol, days_back=15):
    cutoff  = (date.today() -
               timedelta(days=days_back)).isoformat()
    history = load_history()
    return [
        r for r in history
        if r.get('symbol') == symbol
        and r.get('date', '') >= cutoff
    ]


def get_summary():
    history = load_history()
    open_t  = [r for r in history
               if r.get('result') == 'PENDING']
    closed  = [r for r in history
               if r.get('result') in
               ('WON', 'STOPPED', 'EXITED')]
    wins    = sum(1 for r in closed
                  if r.get('result') == 'WON')
    wr      = round(wins / len(closed) * 100) \
              if closed else 0
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
