"""
migrate_rej_duplicates.py — RESOLVE -REJ + SYNC RESULT FIELD

v3: Previous version inherited outcome but not result field.
This version ensures ALL fields sync from parent including 'result',
so stats.js correctly counts these as resolved.

Idempotent: safe to re-run.
"""

import json
import os
import sys
from datetime import datetime, timezone

HISTORY_FILE = 'output/signal_history.json'
BACKUP_DIR = 'backups'

INHERIT_FIELDS = [
    'outcome', 'outcome_date', 'outcome_price',
    'exit_type', 'exit_date_actual', 'exit_price',
    'pnl_pct', 'pnl_rs',
    'mfe_pct', 'mae_pct',
    'tracking_start', 'tracking_end',
    'days_to_outcome', 'exit_day',
    'result',
    'effective_exit_date',
    'failure_reason',
    'day6_open', 'post_target_move',
    'r_multiple',
    'adjusted_rr', 'entry_valid', 'gap_pct', 'actual_open',
]

TERMINAL_OUTCOMES = {
    'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT',
    'STOP_HIT', 'TARGET_HIT',
}

TERMINAL_RESULTS = {'EXITED', 'STOPPED', 'WON'}


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def backup_file():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    backup_path = f'{BACKUP_DIR}/signal_history.{stamp}.pre-rej-resync.json'

    with open(HISTORY_FILE, 'r') as f:
        content = f.read()

    with open(backup_path, 'w') as f:
        f.write(content)

    log(f'Backup created: {backup_path} ({len(content)} bytes)')
    return backup_path


def find_parent(rej_id, records_by_id):
    if not rej_id.endswith('-REJ'):
        return None
    parent_id = rej_id[:-4]
    return records_by_id.get(parent_id)


def migrate():
    log('Loading signal_history.json...')
    with open(HISTORY_FILE, 'r') as f:
        data = json.load(f)

    history = data.get('history', [])
    total = len(history)
    log(f'Total records: {total}')

    records_by_id = {r.get('id'): r for r in history if r.get('id')}

    synced = 0
    skipped_not_rej = 0
    skipped_already_rejected = 0
    skipped_no_parent = 0
    skipped_parent_pending = 0
    skipped_fully_synced = 0

    sync_details = []

    for record in history:
        sid = record.get('id', '')

        if not sid.endswith('-REJ'):
            skipped_not_rej += 1
            continue

        if record.get('action') == 'REJECTED' and record.get('result') == 'REJECTED':
            skipped_already_rejected += 1
            continue

        parent = find_parent(sid, records_by_id)
        if not parent:
            skipped_no_parent += 1
            continue

        parent_outcome = parent.get('outcome')
        if parent_outcome not in TERMINAL_OUTCOMES:
            skipped_parent_pending += 1
            continue

        # Check if this -REJ already matches parent fully
        current_result = record.get('result')
        current_outcome = record.get('outcome')
        if (current_result in TERMINAL_RESULTS and
                current_outcome == parent_outcome):
            # Already properly synced — no change needed
            skipped_fully_synced += 1
            continue

        # Sync ALL fields from parent
        before = f'result={current_result!r}, outcome={current_outcome!r}'
        for field in INHERIT_FIELDS:
            if field in parent:
                record[field] = parent[field]

        after = f'result={record.get("result")!r}, outcome={record.get("outcome")!r}'

        record['migration_source'] = 'rej_resolved_from_parent_2026-04-18'
        record['migration_applied'] = 'rej_resync_2026-04-18'
        record['parent_signal_id'] = parent.get('id')

        synced += 1
        sync_details.append(f'  {sid}: {before} -> {after}')

    log(f'Synced from parent: {synced}')
    log(f'Already fully synced (no change): {skipped_fully_synced}')
    log(f'Skipped - already REJECTED: {skipped_already_rejected}')
    log(f'Skipped - parent still pending: {skipped_parent_pending}')
    log(f'Skipped - no parent found: {skipped_no_parent}')
    log(f'Skipped - not -REJ: {skipped_not_rej}')

    if sync_details:
        log('--- synced records ---')
        for line in sync_details[:40]:
            log(line)
        log('--- end ---')

    if synced == 0:
        log('No records needed syncing. Exiting without write.')
        return 0

    log('Writing updated signal_history.json...')
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    log(f'Migration complete. {synced} records synced from parents.')
    return synced


def send_telegram(message):
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
    log('=== REJ Resync Migration v3 ===')

    if not os.path.exists(HISTORY_FILE):
        log(f'ERROR: {HISTORY_FILE} not found')
        sys.exit(1)

    try:
        backup_path = backup_file()
        synced = migrate()

        msg = (
            f'<b>REJ Resync Complete</b>\n'
            f'Records synced: <b>{synced}</b>\n'
            f'Stats should now show these as resolved.'
        )
        send_telegram(msg)

    except Exception as e:
        log(f'ERROR: {e}')
        send_telegram(
            f'<b>REJ Resync Failed</b>\n{str(e)[:200]}'
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
