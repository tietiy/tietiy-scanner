"""
migrate_rej_duplicates.py — ONE-TIME MIGRATION

Problem: Apr 6 2026 shadow mode created duplicate records with '-REJ' suffix.
These have action='TOOK', result='PENDING', layer='MINI' — identical fields
to real signals. Stats.js and journal.js count them as open positions,
inflating "Open Now" count by ~32 phantom positions.

Fix: Find all records where id ends with '-REJ' AND result='PENDING'.
Mark them as action='REJECTED', layer='ALPHA', result='REJECTED'.
They disappear from open positions but remain in history for audit.

Run: Manual dispatch only. Safe to re-run (idempotent).
"""

import json
import os
import sys
from datetime import datetime, timezone

HISTORY_FILE = 'output/signal_history.json'
BACKUP_DIR = 'backups'


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def backup_file():
    """Create timestamped backup before migration."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    backup_path = f'{BACKUP_DIR}/signal_history.{stamp}.pre-rej-migrate.json'

    with open(HISTORY_FILE, 'r') as f:
        content = f.read()

    with open(backup_path, 'w') as f:
        f.write(content)

    log(f'Backup created: {backup_path} ({len(content)} bytes)')
    return backup_path


def migrate():
    log('Loading signal_history.json...')
    with open(HISTORY_FILE, 'r') as f:
        data = json.load(f)

    history = data.get('history', [])
    total = len(history)
    log(f'Total records: {total}')

    migrated = 0
    skipped = 0
    already_rejected = 0

    for record in history:
        sid = record.get('id', '')

        if not sid.endswith('-REJ'):
            continue

        current_action = record.get('action')
        current_result = record.get('result')

        # Already handled (Apr 1 backfill has action=REJECTED already)
        if current_action == 'REJECTED' and current_result == 'REJECTED':
            already_rejected += 1
            continue

        # Only migrate those still flagged as TOOK+PENDING
        if current_action == 'TOOK' and current_result == 'PENDING':
            record['action'] = 'REJECTED'
            record['result'] = 'REJECTED'
            record['layer'] = 'ALPHA'
            if not record.get('rejection_reason'):
                record['rejection_reason'] = (
                    'shadow_mode_duplicate_migrated_2026-04-18'
                )
            record['migration_applied'] = (
                'rej_duplicate_cleanup_2026-04-18'
            )
            migrated += 1
        else:
            # Terminal outcomes — leave alone
            skipped += 1

    log(f'Migrated: {migrated}')
    log(f'Already rejected (skipped): {already_rejected}')
    log(f'Other -REJ records (skipped): {skipped}')

    if migrated == 0:
        log('No records needed migration. Exiting without write.')
        return 0

    # Write back
    log('Writing updated signal_history.json...')
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    log(f'✓ Migration complete. {migrated} records updated.')
    return migrated


def send_telegram(message):
    """Best-effort Telegram notification."""
    try:
        import urllib.request
        import urllib.parse

        token = os.environ.get('TELEGRAM_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        if not token or not chat_id:
            log('Telegram secrets not set, skipping notification')
            return

        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }).encode()

        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()

        log('Telegram notification sent')

    except Exception as e:
        log(f'Telegram notification failed: {e}')


def main():
    log('=== REJ Duplicate Migration ===')

    if not os.path.exists(HISTORY_FILE):
        log(f'ERROR: {HISTORY_FILE} not found')
        sys.exit(1)

    try:
        backup_path = backup_file()
        migrated = migrate()

        msg = (
            f'<b>🧹 REJ Migration Complete</b>\n'
            f'Records cleaned: <b>{migrated}</b>\n'
            f'Backup: {os.path.basename(backup_path)}\n'
            f'Open Now count should drop by ~{migrated}.'
        )
        send_telegram(msg)

    except Exception as e:
        log(f'ERROR: {e}')
        send_telegram(
            f'<b>❌ REJ Migration Failed</b>\n{str(e)[:200]}'
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
