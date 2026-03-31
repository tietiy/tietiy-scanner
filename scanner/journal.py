# ── journal.py ───────────────────────────────────────
# Owns signal_history.json and signal_archive.json
# ONLY this file writes these two files
# Nothing else touches them
#
# Key rules:
# 1. Dedup on every write — same id never written twice
# 2. Backup before every write
# 3. Validate after every write — read back and parse
# 4. Active window = 90 trading days in main file
# 5. Older records move to signal_archive.json
# 6. Lifelong data preserved in archive — never deleted
# 7. auto-TOOK default — every DEPLOY signal recorded
# 8. schema_version = 4 on all records
# ─────────────────────────────────────────────────────

import json
import os
import sys
import shutil
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from config import PIVOT_LOOKBACK

# ── PATHS ─────────────────────────────────────────────
# journal.py sits in scanner/
# output/ is one level up from scanner/
_HERE       = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(
                  os.path.dirname(_HERE), 'output')

HISTORY_FILE  = os.path.join(
                    _OUTPUT_DIR, 'signal_history.json')
ARCHIVE_FILE  = os.path.join(
                    _OUTPUT_DIR, 'signal_archive.json')
BACKUP_FILE   = os.path.join(
                    _OUTPUT_DIR,
                    'signal_history.backup.json')

SCHEMA_VERSION   = 4
ACTIVE_DAYS      = 90   # days kept in main file
ARCHIVE_DAYS     = 9999 # days kept in archive (forever)


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
    """
    Load JSON from path.
    Returns default structure if file missing or corrupt.
    """
    if not os.path.exists(path):
        return default_fn()
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        # migrate schema if needed
        if 'history' not in data:
            return default_fn()
        return data
    except Exception as e:
        print(f"[journal] Load error {path}: {e}")
        return default_fn()


def _save_json(path, data):
    """
    Save JSON to path.
    Raises exception if write or validation fails.
    """
    _ensure_output_dir()

    # Write to temp file first then rename (atomic write)
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    # Validate — read back and parse
    try:
        with open(tmp_path, 'r') as f:
            validated = json.load(f)
        if 'history' not in validated:
            raise ValueError("history key missing after write")
    except Exception as e:
        os.remove(tmp_path)
        raise RuntimeError(
            f"[journal] Write validation failed: {e}")

    # Atomic replace
    os.replace(tmp_path, path)


def _backup_history():
    """
    Copy signal_history.json to backup before any write.
    Silent if source doesn't exist yet.
    """
    if os.path.exists(HISTORY_FILE):
        try:
            shutil.copy2(HISTORY_FILE, BACKUP_FILE)
        except Exception as e:
            print(f"[journal] Backup warning: {e}")


def _make_id(signal_date, symbol, signal_type,
             attempt=1):
    """
    Unique ID for every signal record.
    Format: YYYY-MM-DD-SYMBOL-SIGNAL_TYPE
    Second attempt appends -SA
    """
    sym_clean = symbol.replace('.NS', '')
    base = f"{signal_date}-{sym_clean}-{signal_type}"
    if attempt == 2:
        base += "-SA"
    return base


def _trading_day_cutoff(days_back):
    """
    Returns a date string `days_back` calendar days ago.
    Used for archive split — simple calendar days.
    For 90 trading days, using 130 calendar days
    as a safe approximation (accounts for weekends/holidays).
    """
    approx_calendar = int(days_back * 1.45)
    cutoff = date.today() - timedelta(days=approx_calendar)
    return cutoff.isoformat()


# ── CORE PUBLIC FUNCTIONS ─────────────────────────────

def load_history():
    """
    Returns full history list from signal_history.json.
    Used by main.py to pass to detect_second_attempt().
    """
    data = _load_json(HISTORY_FILE, _empty_history)
    return data.get('history', [])


def load_archive():
    """
    Returns full archive list from signal_archive.json.
    """
    data = _load_json(ARCHIVE_FILE, _empty_archive)
    return data.get('history', [])


def get_history_count():
    """
    Returns total record count in signal_history.json.
    Used by meta_writer.py for history_record_count.
    """
    data = _load_json(HISTORY_FILE, _empty_history)
    return len(data.get('history', []))


def log_signal(sig, layer='MINI'):
    """
    Appends a signal to signal_history.json.
    Called from main.py for every DEPLOY signal.

    Parameters:
        sig   : dict from scorer.py output
        layer : 'MINI' (default) or 'ALPHA'

    Rules:
        - Dedup by id — skip if already exists
        - Backup before write
        - Validate after write
        - auto-TOOK default (action = 'TOOK')
    """
    _ensure_output_dir()

    today     = date.today().isoformat()
    symbol    = sig.get('symbol', '')
    signal_t  = sig.get('signal', '')
    attempt   = sig.get('attempt_number', 1)
    record_id = _make_id(today, symbol,
                         signal_t, attempt)

    # Load current history
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    # Dedup check — skip if id already exists
    existing_ids = {r.get('id') for r in history}
    if record_id in existing_ids:
        print(f"[journal] Duplicate skipped: {record_id}")
        return

    # Calculate exit date (Day 6 = 5 trading days after entry)
    # Simple approximation: add 8 calendar days
    # Accounts for weekends. Not holiday-aware here —
    # nse_holidays.json handles display in JS
    entry_date = datetime.strptime(today, '%Y-%m-%d')
    exit_dt    = entry_date + timedelta(days=8)
    exit_date  = exit_dt.strftime('%Y-%m-%d')

    # Build record with full schema v4
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
        "direction":        sig.get('direction', ''),
        "age":              sig.get('age', 0),
        "score":            sig.get('score', 0),
        "regime":           sig.get('regime', ''),
        "regime_score":     sig.get('regime_score', 0),
        "vol_q":            sig.get('vol_q', ''),
        "vol_confirm":      sig.get('vol_confirm', False),
        "rs_q":             sig.get('rs_q', ''),
        "sec_mom":          sig.get('sec_mom', ''),
        "bear_bonus":       sig.get('bear_bonus', False),

        # Price
        "scan_price":       sig.get('entry_est', None),
        "scan_time":        datetime.utcnow().strftime(
                                '%H:%M IST'),
        "pivot_price":      sig.get('pivot_price', None),
        "pivot_date":       sig.get('pivot_date', ''),
        "entry":            sig.get('entry_est', None),
        "stop":             sig.get('stop', None),
        "atr":              sig.get('atr', None),
        "exit_date":        exit_date,

        # Open validation (filled by open_validator.py)
        "actual_open":      None,
        "adjusted_rr":      None,
        "entry_valid":      None,
        "gap_pct":          None,

        # Outcome (filled when trade closes)
        "exit_price":       None,
        "exit_type":        None,
        "exit_date_actual": None,
        "pnl_pct":          None,
        "pnl_rs":           None,
        "result":           "PENDING",

        # Action — auto-TOOK default
        # After 1 month of data collection, review
        # whether to add manual Took/Skip buttons
        "action":           "TOOK",

        # Second attempt fields
        "attempt_number":   attempt,
        "parent_signal_id": sig.get(
                                'parent_signal_id', None),
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
                                'scanner_version', 'v2.0'),
    }

    # Backup before write
    _backup_history()

    # Append and save
    history.append(record)
    data['history'] = history

    try:
        _save_json(HISTORY_FILE, data)
        print(f"[journal] Logged: {record_id}")
    except RuntimeError as e:
        print(f"[journal] CRITICAL write failed: {e}")


def log_rejected(sig, rejection_reason,
                 rejection_filter, threshold):
    """
    Logs a signal that was rejected by mini_scanner.py
    to signal_history.json with result = REJECTED.
    Used for shadow mode analysis in stats tab.

    Parameters:
        sig              : signal dict
        rejection_reason : str e.g. 'score_below_threshold'
        rejection_filter : str e.g. 'min_score'
        threshold        : value of threshold at time
    """
    _ensure_output_dir()

    today     = date.today().isoformat()
    symbol    = sig.get('symbol', '')
    signal_t  = sig.get('signal', '')
    record_id = _make_id(
        today, symbol, signal_t) + '-REJ'

    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])

    existing_ids = {r.get('id') for r in history}
    if record_id in existing_ids:
        return

    record = {
        "id":               record_id,
        "schema_version":   SCHEMA_VERSION,
        "date":             today,
        "symbol":           symbol,
        "sector":           sig.get('sector', ''),
        "grade":            sig.get('grade', 'C'),
        "signal":           signal_t,
        "direction":        sig.get('direction', ''),
        "age":              sig.get('age', 0),
        "score":            sig.get('score', 0),
        "regime":           sig.get('regime', ''),
        "regime_score":     sig.get('regime_score', 0),
        "vol_q":            sig.get('vol_q', ''),
        "vol_confirm":      sig.get('vol_confirm', False),
        "rs_q":             sig.get('rs_q', ''),
        "sec_mom":          sig.get('sec_mom', ''),
        "bear_bonus":       sig.get('bear_bonus', False),
        "scan_price":       sig.get('entry_est', None),
        "scan_time":        datetime.utcnow().strftime(
                                '%H:%M IST'),
        "entry":            sig.get('entry_est', None),
        "stop":             sig.get('stop', None),
        "atr":              sig.get('atr', None),
        "exit_date":        None,
        "actual_open":      None,
        "adjusted_rr":      None,
        "entry_valid":      None,
        "gap_pct":          None,
        "exit_price":       None,
        "exit_type":        None,
        "exit_date_actual": None,
        "pnl_pct":          None,
        "pnl_rs":           None,
        "result":           "REJECTED",
        "action":           "REJECTED",
        "attempt_number":   sig.get('attempt_number', 1),
        "parent_signal_id": sig.get(
                                'parent_signal_id', None),
        "parent_signal":    sig.get(
                                'parent_signal', None),
        "parent_date":      sig.get(
                                'parent_date', None),
        "parent_result":    None,
        "layer":            "ALPHA",
        "rejection_reason": rejection_reason,
        "rejection_filter": rejection_filter,
        "rejection_threshold": threshold,
        "scanner_version":  sig.get(
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
    """
    Called by open_validator.py at 9:25 AM.
    Updates the actual open price fields on a signal.
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol and
                record.get('date') == signal_date and
                record.get('result') == 'PENDING'):
            record['actual_open']  = actual_open
            record['adjusted_rr']  = adjusted_rr
            record['entry_valid']  = entry_valid
            record['gap_pct']      = gap_pct
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


def close_trade(symbol, signal_date, exit_price,
                exit_type):
    """
    Closes a trade — marks result as WON/STOPPED/EXITED.
    Called from main.py or future outcome recording logic.

    exit_type options:
        'StopHit'  → result = STOPPED
        'DayExit'  → result = EXITED (Day 6 rule)
        'Manual'   → result = EXITED
    """
    data    = _load_json(HISTORY_FILE, _empty_history)
    history = data.get('history', [])
    updated = False

    for record in history:
        if (record.get('symbol') == symbol and
                record.get('date') == signal_date and
                record.get('result') == 'PENDING'):
            entry = float(record.get('entry') or 0)
            stop  = float(record.get('stop') or 0)
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
                    'STOPPED' if exit_type == 'StopHit'
                    else 'WON' if pnl_pct > 0
                    else 'EXITED')
            else:
                record['result'] = 'EXITED'
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
    Moves records older than ACTIVE_DAYS from
    signal_history.json to signal_archive.json.

    Active file stays fast and light.
    Archive preserves every record forever.
    Called from main.py once per scan.
    """
    cutoff = _trading_day_cutoff(ACTIVE_DAYS)

    # Load both files
    hist_data = _load_json(
                    HISTORY_FILE, _empty_history)
    arch_data = _load_json(
                    ARCHIVE_FILE, _empty_archive)

    history = hist_data.get('history', [])
    archive = arch_data.get('history', [])

    # Split: keep recent, move old
    keep     = []
    to_move  = []

    for record in history:
        rec_date = record.get('date', '9999-12-31')
        # Always keep PENDING regardless of age
        if record.get('result') == 'PENDING':
            keep.append(record)
        elif rec_date >= cutoff:
            keep.append(record)
        else:
            to_move.append(record)

    if not to_move:
        return  # Nothing to archive

    # Dedup archive — don't add what's already there
    archive_ids = {r.get('id') for r in archive}
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
            return  # Don't remove from history if archive failed

    # Save trimmed history
    hist_data['history'] = keep
    _backup_history()
    try:
        _save_json(HISTORY_FILE, hist_data)
        print(f"[journal] History trimmed → "
              f"{len(keep)} active records")
    except RuntimeError as e:
        print(f"[journal] History trim failed: {e}")


# ── QUERY FUNCTIONS ───────────────────────────────────
# Used by main.py and stats calculations

def get_open_trades():
    """Returns all PENDING records."""
    history = load_history()
    return [r for r in history
            if r.get('result') == 'PENDING']


def get_recent_closed(n=10):
    """Returns last n closed records."""
    history = load_history()
    closed  = [r for r in history
               if r.get('result') in
               ('WON', 'STOPPED', 'EXITED')]
    closed.sort(key=lambda x: x.get('date', ''))
    return closed[-n:]


def get_system_health():
    """
    Returns health status based on last 5 closed trades.
    HOT   = WR >= 70%
    COLD  = WR <= 40%
    NORMAL = between
    """
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
    """
    Returns recent history for a specific symbol.
    Used by detect_second_attempt() in scanner_core.py.
    """
    cutoff  = (date.today() -
               timedelta(days=days_back)).isoformat()
    history = load_history()
    return [
        r for r in history
        if r.get('symbol') == symbol
        and r.get('date', '') >= cutoff
    ]


def get_summary():
    """
    Full summary dict for meta_writer and stats tab.
    """
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
