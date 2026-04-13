# scanner/heal_sa_signals.py
# ─────────────────────────────────────────────────────
# ONE-TIME DATA FIX — C1
#
# Problem: ADANIGREEN and BSE fired DOWN_TRI_SA signals
# on Apr 8. Both had gap-too-large at open (entry_valid
# = False). outcome_evaluator assigned fake outcomes
# using actual_open as entry even though the trade was
# never entered. This produced nonsense P&L values that
# contaminate win rate, MAE avg, and gap report stats.
#
# Fix: Reset both signals to clean PENDING state:
#   - outcome       → None (removes fake outcome)
#   - result        → PENDING
#   - entry_valid   → False (already set, confirm)
#   - pnl_pct       → None
#   - mae_pct       → None
#   - mfe_pct       → None
#   - exit_type     → None
#   - exit_day      → None
#   - failure_reason→ "Gap at open invalidated entry
#                      — trade was not taken"
#
# Run once from GitHub Actions workflow_dispatch or
# locally. Backs up history before modifying.
#
# Usage:
#   python scanner/heal_sa_signals.py
#   python scanner/heal_sa_signals.py --dry-run
# ─────────────────────────────────────────────────────

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)

# Signals to reset — symbol + signal type + date
# These are the two confirmed invalid SA signals
TARGETS = [
    {
        'symbol': 'ADANIGREEN.NS',
        'signal': 'UP_TRI_SA',
        'date':   '2026-04-08',
    },
    {
        'symbol': 'BSE.NS',
        'signal': 'DOWN_TRI_SA',
        'date':   '2026-04-08',
    },
]

# Fields to clear on each target signal
CLEAR_FIELDS = [
    'outcome',
    'outcome_date',
    'outcome_price',
    'pnl_pct',
    'mfe_pct',
    'mae_pct',
    'exit_type',
    'exit_day',
    'days_to_outcome',
    'post_target_move',
    'day6_open',
]


def _match(sig, target):
    """Check if signal matches a target spec."""
    sym_match = (
        sig.get('symbol', '').upper()
        == target['symbol'].upper()
        or sig.get('symbol', '').upper()
        == target['symbol'].replace('.NS', '').upper()
    )
    sig_match = (
        sig.get('signal', '').upper()
        == target['signal'].upper()
    )
    date_match = sig.get('date', '') == target['date']
    return sym_match and sig_match and date_match


def run_heal(dry_run=False):
    print('[heal_sa] Starting C1 SA signal heal...')
    if dry_run:
        print('[heal_sa] DRY RUN — no changes written')

    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f'[heal_sa] Cannot load history: {e}')
        return

    history = data.get('history', [])
    healed  = 0
    found   = []

    for i, sig in enumerate(history):
        for target in TARGETS:
            if not _match(sig, target):
                continue

            sym    = sig.get('symbol', '?')
            signal = sig.get('signal', '?')
            date   = sig.get('date', '?')

            print(f'\n[heal_sa] Found: {sym} '
                  f'{signal} {date}')
            print(f'  Before: outcome={sig.get("outcome")} '
                  f'result={sig.get("result")} '
                  f'pnl={sig.get("pnl_pct")} '
                  f'entry_valid={sig.get("entry_valid")}')

            if dry_run:
                print(f'  Would reset to PENDING')
                found.append(i)
                continue

            # Clear outcome fields
            for field in CLEAR_FIELDS:
                if field in sig:
                    del history[i][field]

            # Set clean state
            history[i]['outcome']       = None
            history[i]['result']        = 'PENDING'
            history[i]['entry_valid']   = False
            history[i]['failure_reason'] = (
                'Gap at open invalidated entry '
                '— trade was not taken')

            print(f'  After:  outcome=None '
                  f'result=PENDING '
                  f'entry_valid=False')
            healed += 1
            found.append(i)
            break   # matched — move to next signal

    print(f'\n[heal_sa] Found {len(found)} '
          f'target signals')

    if not found:
        print('[heal_sa] No matching signals found '
              '— check symbol/signal/date in TARGETS')
        return

    if not dry_run:
        _backup_history()
        data['history'] = history
        try:
            _save_json(HISTORY_FILE, data)
            print(f'[heal_sa] Done — '
                  f'{healed} signals reset to PENDING')
        except Exception as e:
            print(f'[heal_sa] Save failed: {e}')
    else:
        print('[heal_sa] Dry run complete — '
              'run without --dry-run to apply')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing')
    args = parser.parse_args()
    run_heal(dry_run=args.dry_run)
