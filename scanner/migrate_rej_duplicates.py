"""
migrate_rej_duplicates.py — RESOLVE -REJ RECORDS FROM PARENTS

Apr 6 2026 shadow mode created 32 -REJ duplicates that never got outcomes.
Strategy: inherit outcome from parent signal (same symbol + signal, no -REJ suffix).
Result: these count as real trades in Stats (Option C — shadow mode is real data).

Safe to re-run (idempotent): skips records that already have terminal outcomes.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

HISTORY_FILE = 'output/signal_history.json'
BACKUP_DIR = 'backups'

# Fields we copy from parent into -REJ child
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


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def backup_file():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
    backup_path = f'{BACKUP_DIR}/signal_history.{stamp}.pre-rej-resolve.json'

    with open(HISTORY_FILE, 'r') as f:
        content = f.read()

    with open(backup_path, 'w') as f:
        f.write(content)

    log(f'Backup created: {backup_path} ({len(content)} bytes)')
    return backup_path


def find_parent(rej_id, records_by_id):
    """Given '2026-04-06-INFY-UP_TRI-REJ', return the parent record dict."""
    if not rej_id.endswith('-REJ'):
        return None
    parent_id = rej_id[:-4]  # strip '-REJ'
    return records_by_id.get(parent_id)


def migrate():
    log('Loading signal_history.json...')
    with open(HISTORY_FILE, 'r') as f:
        data = json.load(f)

    history = data.get('history', [])
    total = len(history)
    log(f'Total records: {total}')

    # Build parent lookup
    records_by_id = {r.get('id'): r for r in history if r.get('id')}

    resolved = 0
    skipped_already_terminal = 0
    skipped_no_parent = 0
    skipped_parent_pending = 0
    skipped_not_rej = 0
    skipped_already_rejected = 0

    resolve_details = []
    no_parent_details = []

    for record in history:
        sid = record.get('id', '')

        if not sid.endswith('-REJ'):
            skipped_not_rej += 1
            continue

        # Skip Apr 1 properly-rejected records (action=REJECTED, result=REJECTED)
        if record.get('action') == 'REJECTED' and record.get('result') == 'REJECTED':
            skipped_already_rejected += 1
            continue

        # Already has terminal outcome? Skip (idempotent re-runs)
        if record.get('outcome') in TERMINAL_OUTCOMES:
            skipped_already_terminal += 1
            continue

        # Find parent
        parent = find_parent(sid, records_by_id)
        if not parent:
            skipped_no_parent += 1
            no_parent_details.append(sid)
            continue

        # Parent must have terminal outcome
        parent_outcome = parent.get('outcome')
        if parent_outcome not in TERMINAL_OUTCOMES:
            skipped_parent_pending += 1
            continue

        # Inherit fields from parent
        for field in INHERIT_FIELDS:
            if field in parent:
                record[field] = parent[field]

        # Tag migration
        record['migration_source'] = 'rej_resolved_from_parent_2026-04-18'
        record['migration_applied'] = 'rej_resolve_2026-04-18'
        record['parent_signal_id'] = parent.get('id')

        resolved += 1
        resolve_details.append(
            f'  {sid}: outcome={parent_outcome}, '
            f'pnl={parent.get("pnl_pct")}, '
            f'day6_open={parent.get("day6_open")}'
        )

    log(f'Resolved from parent: {resolved}')
    log(f'Skipped - already terminal: {skipped_already_terminal}')
    log(f'Skipped - already REJECTED: {skipped_already_rejected}')
    log(f'Skipped - parent still pending: {skipped_parent_pending}')
    log(f'Skipped - no parent found: {skipped_no_parent}')
    log(f'Skipped - not -REJ: {skipped_not_rej}')

    if no_parent_details:
        log('--- -REJ with no parent ---')
        for sid in no_parent_details[:20]:
            log(f'  {sid}')

    if resolve_details:
        log('--- resolved records (first 40) ---')
        for line in resolve_details[:40]:
            log(line)
        log('--- end ---')

    if resolved == 0:
        log('No records needed resolving. Exiting without write.')
        return 0

    log('Writing updated signal_history.json...')
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    log(f'Migration complete. {resolved} records resolved from parents.')
    return resolved


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
    log('=== REJ Resolve Migration ===')

    if not os.path.exists(HISTORY_FILE):
        log(f'ERROR: {HISTORY_FILE} not found')
        sys.exit(1)

    try:
        backup_path = backup_file()
        resolved = migrate()

        msg = (
            f'<b>REJ Resolve Complete</b>\n'
            f'Records resolved from parent: <b>{resolved}</b>\n'
            f'These now count as real trades in Stats.\n'
            f'Backup: {os.path.basename(backup_path)}'
        )
        send_telegram(msg)

    except Exception as e:
        log(f'ERROR: {e}')
        send_telegram(
            f'<b>REJ Resolve Failed</b>\n{str(e)[:200]}'
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
