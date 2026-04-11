# scanner/backup_manager.py
# Rolling backups of signal_history.json
# Keeps last 7 days, auto-cleans older
# ─────────────────────────────────────────────────────

import os
import json
import shutil
from datetime import date, datetime, timedelta

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HISTORY_FILE = os.path.join(_OUTPUT, 'signal_history.json')
BACKUP_DIR   = os.path.join(_OUTPUT, 'backups')

RETENTION_DAYS = 7


def run_backup():
    """
    Creates dated backup of signal_history.json.
    Cleans up backups older than RETENTION_DAYS.
    """
    print("[backup] Starting...")

    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Check source file exists
    if not os.path.exists(HISTORY_FILE):
        print("[backup] No signal_history.json found — skipping")
        return False

    # Create dated backup
    today_str   = date.today().strftime('%Y-%m-%d')
    backup_name = f"signal_history.{today_str}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    try:
        shutil.copy2(HISTORY_FILE, backup_path)
        size_kb = os.path.getsize(backup_path) / 1024
        print(f"[backup] Created: {backup_name} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"[backup] Copy failed: {e}")
        return False

    # Cleanup old backups
    cleanup_count = _cleanup_old_backups()
    if cleanup_count > 0:
        print(f"[backup] Cleaned up {cleanup_count} old backups")

    # List current backups
    backups = _list_backups()
    print(f"[backup] Current backups: {len(backups)}")
    for b in backups[-3:]:  # Show last 3
        print(f"[backup]   {b}")

    print("[backup] Done")
    return True


def _cleanup_old_backups():
    """Remove backups older than RETENTION_DAYS."""
    if not os.path.exists(BACKUP_DIR):
        return 0

    cutoff = date.today() - timedelta(days=RETENTION_DAYS)
    removed = 0

    for filename in os.listdir(BACKUP_DIR):
        if not filename.startswith('signal_history.'):
            continue
        if not filename.endswith('.json'):
            continue

        # Extract date from filename
        # Format: signal_history.2026-04-12.json
        try:
            date_part = filename.replace('signal_history.', '') \
                                .replace('.json', '')
            file_date = datetime.strptime(date_part, '%Y-%m-%d').date()

            if file_date < cutoff:
                file_path = os.path.join(BACKUP_DIR, filename)
                os.remove(file_path)
                print(f"[backup] Removed old: {filename}")
                removed += 1
        except Exception:
            continue

    return removed


def _list_backups():
    """List all backup files, sorted by date."""
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith('signal_history.') and \
           filename.endswith('.json'):
            backups.append(filename)

    return sorted(backups)


def restore_backup(date_str: str):
    """
    Restore signal_history.json from a dated backup.
    Use with caution — overwrites current file.
    
    Args:
        date_str: Date in YYYY-MM-DD format
    """
    backup_name = f"signal_history.{date_str}.json"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    if not os.path.exists(backup_path):
        print(f"[backup] Backup not found: {backup_name}")
        return False

    # Create safety backup of current file
    if os.path.exists(HISTORY_FILE):
        safety_path = HISTORY_FILE + '.pre-restore'
        shutil.copy2(HISTORY_FILE, safety_path)
        print(f"[backup] Safety backup: {safety_path}")

    # Restore
    try:
        shutil.copy2(backup_path, HISTORY_FILE)
        print(f"[backup] Restored from: {backup_name}")
        return True
    except Exception as e:
        print(f"[backup] Restore failed: {e}")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) > 2:
            restore_backup(sys.argv[2])
        else:
            print("Usage: python backup_manager.py restore 2026-04-12")
    else:
        run_backup()
