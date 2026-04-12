# scanner/backup_manager.py
# Rolling backups of signal_history.json
# Keeps last 7 days, auto-cleans older
#
# V1 FIX — M7:
# - Archive file also backed up daily
# - Integrity check after every backup copy
# - Size trend check — warns if file shrinks
#   vs previous day (data loss indicator)
# - Telegram notification on success + size info
# - --verify CLI flag to audit existing backups
#
# BUG FIX: f-string backslash syntax error fixed
#   in _send_backup_summary — dict access extracted
#   to variables before f-string (Python 3.11 compat)
# ─────────────────────────────────────────────────────

import os
import json
import shutil
import argparse
from datetime import date, datetime, timedelta

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HISTORY_FILE = os.path.join(_OUTPUT, 'signal_history.json')
ARCHIVE_FILE = os.path.join(_OUTPUT, 'signal_archive.json')
BACKUP_DIR   = os.path.join(_OUTPUT, 'backups')

RETENTION_DAYS   = 7
SHRINK_WARN_PCT  = 5    # warn if file shrinks > 5%

# ── OPTIONAL TELEGRAM ─────────────────────────────────
try:
    from telegram_bot import send_message
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


# ── INTEGRITY CHECK ───────────────────────────────────
def _verify_json(path):
    """
    Returns (ok, record_count, size_kb, error).
    ok=True means file is valid JSON with history key.
    """
    if not os.path.exists(path):
        return False, 0, 0, 'File not found'
    try:
        size_kb = os.path.getsize(path) / 1024
        with open(path, 'r') as f:
            data = json.load(f)
        if 'history' not in data:
            return False, 0, size_kb, 'Missing history key'
        count = len(data['history'])
        return True, count, size_kb, None
    except json.JSONDecodeError as e:
        return False, 0, 0, f'Invalid JSON: {e}'
    except Exception as e:
        return False, 0, 0, f'Read error: {e}'


def _get_prev_backup_size(prefix, today_str):
    """
    Returns size_kb of yesterday's backup for comparison.
    Returns None if no previous backup found.
    """
    if not os.path.exists(BACKUP_DIR):
        return None
    yesterday = (date.today() - timedelta(days=1)
                 ).strftime('%Y-%m-%d')
    prev_name = f"{prefix}.{yesterday}.json"
    prev_path = os.path.join(BACKUP_DIR, prev_name)
    if not os.path.exists(prev_path):
        return None
    try:
        return os.path.getsize(prev_path) / 1024
    except Exception:
        return None


# ── BACKUP ONE FILE ───────────────────────────────────
def _backup_file(source_path, prefix, today_str,
                 send_tg=False):
    """
    Backs up a single file. Returns result dict.
    """
    result = {
        'prefix':     prefix,
        'ok':         False,
        'size_kb':    0,
        'records':    0,
        'shrink':     False,
        'shrink_pct': 0,
        'error':      None,
    }

    if not os.path.exists(source_path):
        result['error'] = 'Source not found'
        print(f"[backup] {prefix}: source missing — skip")
        return result

    backup_name = f"{prefix}.{today_str}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    # Copy
    try:
        shutil.copy2(source_path, backup_path)
    except Exception as e:
        result['error'] = str(e)
        print(f"[backup] {prefix}: copy failed: {e}")
        return result

    # Integrity check on the copy
    ok, count, size_kb, err = _verify_json(backup_path)
    result['size_kb'] = size_kb
    result['records'] = count

    if not ok:
        result['error'] = f'Integrity fail: {err}'
        print(f"[backup] {prefix}: integrity check "
              f"FAILED — {err}")
        try:
            os.remove(backup_path)
        except Exception:
            pass
        return result

    # Size shrink check
    prev_size = _get_prev_backup_size(prefix, today_str)
    if prev_size and prev_size > 0:
        shrink_pct = (
            (prev_size - size_kb) / prev_size * 100)
        if shrink_pct > SHRINK_WARN_PCT:
            result['shrink']     = True
            result['shrink_pct'] = round(shrink_pct, 1)
            print(f"[backup] {prefix}: shrink "
                  f"{result['shrink_pct']}% "
                  f"({prev_size:.1f} → {size_kb:.1f} KB)")

    result['ok'] = True
    print(f"[backup] {prefix}: {backup_name} "
          f"({size_kb:.1f} KB · {count} records)")
    return result


# ── MAIN BACKUP ───────────────────────────────────────
def run_backup(send_tg=False):
    """
    Creates dated backups of signal_history.json
    and signal_archive.json.
    Validates integrity. Checks size trends.
    Cleans up backups older than RETENTION_DAYS.
    """
    print("[backup] Starting...")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    today_str = date.today().strftime('%Y-%m-%d')

    hist_result = _backup_file(
        HISTORY_FILE, 'signal_history',
        today_str, send_tg)
    arch_result = _backup_file(
        ARCHIVE_FILE, 'signal_archive',
        today_str, send_tg)

    cleanup_count = _cleanup_old_backups()
    if cleanup_count > 0:
        print(f"[backup] Cleaned {cleanup_count} "
              f"old backups")

    backups = _list_backups()
    print(f"[backup] Total backups: {len(backups)}")

    if send_tg and TELEGRAM_AVAILABLE:
        _send_backup_summary(
            hist_result, arch_result,
            len(backups), today_str)

    if not hist_result['ok']:
        print(f"[backup] History backup FAILED: "
              f"{hist_result['error']}")
        return False

    print("[backup] Done")
    return True


# ── TELEGRAM SUMMARY ──────────────────────────────────
def _send_backup_summary(hist, arch,
                         backup_count, today_str):
    def _esc(t):
        if t is None:
            return '—'
        t = str(t)
        for ch in r'\_*[]()~`>#+-=|{}.!':
            t = t.replace(ch, f'\\{ch}')
        return t

    lines = []
    today_esc = _esc(today_str)
    lines.append(f'💾 *BACKUP · {today_esc}*')
    lines.append('')

    # BUG FIX: extract all dict access + formatting
    # to plain variables before f-strings.
    # Python 3.11 forbids backslashes inside f-string
    # {} expressions — e.g. f"{d[\"key\"]}" fails.

    # History
    if hist['ok']:
        hist_size    = f"{hist['size_kb']:.1f}"
        hist_records = str(hist['records'])
        if hist['shrink']:
            shrink_pct  = str(hist['shrink_pct'])
            shrink_note = f" shrunk {shrink_pct}%"
        else:
            shrink_note = ''
        hist_size_esc    = _esc(hist_size)
        hist_records_esc = _esc(hist_records)
        shrink_esc       = _esc(shrink_note)
        lines.append(
            f'✅ signal\\_history: '
            f'{hist_size_esc} KB '
            f'· {hist_records_esc} records'
            f'{shrink_esc}')
    else:
        hist_err = _esc(str(hist['error']))
        lines.append(
            f'❌ signal\\_history: {hist_err}')

    # Archive
    if arch['ok']:
        arch_size        = f"{arch['size_kb']:.1f}"
        arch_records     = str(arch['records'])
        arch_size_esc    = _esc(arch_size)
        arch_records_esc = _esc(arch_records)
        lines.append(
            f'✅ signal\\_archive: '
            f'{arch_size_esc} KB '
            f'· {arch_records_esc} records')
    elif arch['error'] == 'Source not found':
        lines.append(
            '○ signal\\_archive: not yet created')
    else:
        arch_err = _esc(str(arch['error']))
        lines.append(
            f'⚠️ signal\\_archive: {arch_err}')

    lines.append('')
    bc_esc  = _esc(str(backup_count))
    ret_esc = _esc(str(RETENTION_DAYS))
    lines.append(
        f'Keeping {bc_esc} backups · '
        f'{ret_esc}d retention')

    try:
        send_message('\n'.join(lines))
    except Exception as e:
        print(f"[backup] Telegram error: {e}")


# ── CLEANUP ───────────────────────────────────────────
def _cleanup_old_backups():
    """Remove backups older than RETENTION_DAYS."""
    if not os.path.exists(BACKUP_DIR):
        return 0

    cutoff  = date.today() - timedelta(
        days=RETENTION_DAYS)
    removed = 0

    for filename in os.listdir(BACKUP_DIR):
        if not filename.endswith('.json'):
            continue
        if not (filename.startswith('signal_history.')
             or filename.startswith('signal_archive.')):
            continue
        try:
            parts     = filename.rsplit('.', 2)
            date_part = parts[-2]
            file_date = datetime.strptime(
                date_part, '%Y-%m-%d').date()
            if file_date < cutoff:
                os.remove(os.path.join(
                    BACKUP_DIR, filename))
                print(f"[backup] Removed: {filename}")
                removed += 1
        except Exception:
            continue

    return removed


# ── LIST BACKUPS ──────────────────────────────────────
def _list_backups():
    """List all backup files sorted by name."""
    if not os.path.exists(BACKUP_DIR):
        return []
    return sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.endswith('.json') and (
            f.startswith('signal_history.') or
            f.startswith('signal_archive.'))
    ])


# ── VERIFY EXISTING BACKUPS ───────────────────────────
def verify_backups():
    """
    M7: --verify flag. Checks all existing backups
    for JSON integrity and reports status.
    """
    backups = _list_backups()
    if not backups:
        print("[backup] No backups found to verify")
        return

    print(f"[backup] Verifying {len(backups)} backups...")
    ok_count   = 0
    fail_count = 0

    for filename in backups:
        path = os.path.join(BACKUP_DIR, filename)
        ok, count, size_kb, err = _verify_json(path)
        if ok:
            print(f"  ok {filename} "
                  f"({size_kb:.1f} KB · {count} records)")
            ok_count += 1
        else:
            print(f"  fail {filename} — {err}")
            fail_count += 1

    print(f"[backup] Verify complete: "
          f"{ok_count} OK · {fail_count} failed")


# ── RESTORE ───────────────────────────────────────────
def restore_backup(date_str: str):
    """
    Restore signal_history.json from a dated backup.
    Use with caution — overwrites current file.
    Creates a safety backup of current file first.
    """
    backup_name = f"signal_history.{date_str}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(backup_path):
        print(f"[backup] Not found: {backup_name}")
        return False

    ok, count, size_kb, err = _verify_json(backup_path)
    if not ok:
        print(f"[backup] Backup invalid: {err} — "
              f"aborting restore")
        return False

    print(f"[backup] Restoring from {backup_name} "
          f"({count} records)...")

    if os.path.exists(HISTORY_FILE):
        safety = HISTORY_FILE + '.pre-restore'
        shutil.copy2(HISTORY_FILE, safety)
        print(f"[backup] Safety copy: .pre-restore")

    try:
        shutil.copy2(backup_path, HISTORY_FILE)
        print(f"[backup] Restored successfully")
        return True
    except Exception as e:
        print(f"[backup] Restore failed: {e}")
        return False


# ── CLI ───────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='TIE TIY Backup Manager')
    parser.add_argument(
        '--verify', action='store_true',
        help='Verify all existing backups')
    parser.add_argument(
        '--restore', metavar='DATE',
        help='Restore from date (YYYY-MM-DD)')
    parser.add_argument(
        '--list', action='store_true',
        help='List all backups')
    parser.add_argument(
        '--telegram', action='store_true',
        help='Send Telegram notification on backup')

    args = parser.parse_args()

    if args.verify:
        verify_backups()
    elif args.restore:
        restore_backup(args.restore)
    elif args.list:
        backups = _list_backups()
        print(f"Backups ({len(backups)}):")
        for b in backups:
            path = os.path.join(BACKUP_DIR, b)
            ok, count, size_kb, _ = _verify_json(path)
            status = 'ok' if ok else 'fail'
            print(f"  {status} {b} "
                  f"({size_kb:.1f} KB · {count} records)")
    else:
        run_backup(send_tg=args.telegram)
