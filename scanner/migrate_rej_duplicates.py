"""
migrate_rej_duplicates.py v4 — RESTORE LAYER TO MINI

Earlier v2 script set layer='ALPHA' on -REJ records.
But stats.js filters took = layer==MINI && action==TOOK.
So these 32 records got hidden from Stats despite
having correct outcomes.

This script: for any -REJ record with action=TOOK and
terminal outcome, ensure layer=MINI so stats.js counts them.

Idempotent: safe to re-run.
"""

import json
import os
import sys
from datetime import datetime, timezone

HISTORY_FILE = 'output/signal_history.json'
BACKUP_DIR = 'backups'

TERMINAL_OUTCOMES = {
    'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT',
    'STOP_HIT', 'TARGET_HIT',
}


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def backup_file():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    backup_path = f'{BACKUP_DIR}/signal_history.{stamp}.pre-layer-fix.json'
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
    log(f'Total records: {len(history)}')

    fixed = 0
    skipped_not_rej = 0
    skipped_rejected = 0
    skipped_no_outcome = 0
    skipped_already_mini = 0

    fix_details = []

    for record in history:
        sid = record.get('id', '')

        if not sid.endswith('-REJ'):
            skipped_not_rej += 1
            continue

        # Leave proper REJECTED records alone
        if (record.get('action') == 'REJECTED' and
                record.get('result') == 'REJECTED'):
            skipped_rejected += 1
            continue

        # Must have terminal outcome to be a "took" trade
        if record.get('outcome') not in TERMINAL_OUTCOMES:
            skipped_no_outcome += 1
            continue

        current_layer = record.get('layer')

        if current_layer == 'MINI':
            skipped_already_mini += 1
            continue

        # Flip layer to MINI
        record['layer'] = 'MINI'
        record['layer_fix_applied'] = 'restore_mini_2026-04-18'
        fixed += 1
        fix_details.append(
            f'  {sid}: layer={current_layer!r} -> MINI, '
            f'outcome={record.get("outcome")}'
        )

    log(f'Layer fixed to MINI: {fixed}')
    log(f'Skipped - already MINI: {skipped_already_mini}')
    log(f'Skipped - REJECTED (proper): {skipped_rejected}')
    log(f'Skipped - no terminal outcome: {skipped_no_outcome}')
    log(f'Skipped - not -REJ: {skipped_not_rej}')

    if fix_details:
        log('--- fixed records ---')
        for line in fix_details[:40]:
            log(line)
        log('--- end ---')

    if fixed == 0:
        log('Nothing to fix. Exiting without write.')
        return 0

    log('Writing updated signal_history.json...')
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    log(f'Layer fix complete. {fixed} records restored.')
    return fixed


def send_telegram(message):
    try:
        import urllib.request, urllib.parse
        token = os.environ.get('TELEGRAM_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        if not token or not chat_id:
            log('Telegram secrets not set')
            return
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        log('Telegram notification sent')
    except Exception as e:
        log(f'Telegram failed: {e}')


def main():
    log('=== REJ Layer Fix v4 ===')
    if not os.path.exists(HISTORY_FILE):
        log(f'ERROR: {HISTORY_FILE} not found')
        sys.exit(1)
    try:
        backup_path = backup_file()
        fixed = migrate()
        send_telegram(
            f'<b>REJ Layer Fix Complete</b>\n'
            f'Records restored to MINI: <b>{fixed}</b>\n'
            f'Stats should now show these as resolved.'
        )
    except Exception as e:
        log(f'ERROR: {e}')
        send_telegram(f'<b>REJ Layer Fix Failed</b>\n{str(e)[:200]}')
        sys.exit(1)


if __name__ == '__main__':
    main()
