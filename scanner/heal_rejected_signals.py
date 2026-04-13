# scanner/heal_rejected_signals.py
# ─────────────────────────────────────────────────────
# ONE-TIME DATA FIX — C2
#
# Problem: 43 signals were accidentally marked as
# REJECTED (action=REJECTED, layer=ALPHA) when the
# mini scanner was briefly taken out of shadow mode
# during testing. These should all be TOOK signals
# since shadow mode was active — no signals should
# have been genuinely rejected.
#
# Investigation logic:
#   1. Find all REJECTED records in history
#   2. Split into two groups:
#      A. gen=0 backfill signals (11 expected) —
#         these are pre-live and excluded from stats.
#         Safe to leave as REJECTED or convert.
#      B. gen=1 live signals (32 expected) —
#         these should be TOOK since shadow mode
#         was active. Convert to TOOK + PENDING.
#   3. Report findings before any writes
#   4. With --fix flag: convert gen=1 REJECTED
#      signals to TOOK PENDING
#
# Run first with --report to see what's there.
# Then run with --fix to apply correction.
# Always backs up before writing.
#
# Usage:
#   python scanner/heal_rejected_signals.py --report
#   python scanner/heal_rejected_signals.py --fix
#   python scanner/heal_rejected_signals.py --fix
#                                           --gen1-only
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

# Live start date — signals from this date forward
# are gen=1 live signals
LIVE_START_DATE = '2026-04-06'


def _is_rejected(sig):
    return (sig.get('action') == 'REJECTED'
            or sig.get('result') == 'REJECTED')


def _is_gen1(sig):
    gen = sig.get('generation')
    if gen is None:
        # If no generation field, check date
        return sig.get('date', '') >= LIVE_START_DATE
    return int(gen) >= 1


def _is_gen0(sig):
    gen = sig.get('generation')
    if gen is None:
        return sig.get('date', '') < LIVE_START_DATE
    return int(gen) == 0


def run_report(history):
    """Print investigation report — no writes."""
    all_rej = [s for s in history if _is_rejected(s)]

    print(f'\n[heal_rej] INVESTIGATION REPORT')
    print(f'  Total rejected: {len(all_rej)}')

    gen1_rej = [s for s in all_rej if _is_gen1(s)]
    gen0_rej = [s for s in all_rej if _is_gen0(s)]
    unk_rej  = [s for s in all_rej
                if not _is_gen1(s) and not _is_gen0(s)]

    print(f'  Gen=1 live rejected: {len(gen1_rej)}')
    print(f'  Gen=0 backfill rejected: {len(gen0_rej)}')
    print(f'  Unknown generation: {len(unk_rej)}')

    if gen1_rej:
        print(f'\n[heal_rej] GEN=1 REJECTED SIGNALS '
              f'(should be TOOK):')
        by_date = {}
        for s in gen1_rej:
            d = s.get('date', 'unknown')
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(s)

        for date in sorted(by_date.keys()):
            sigs = by_date[date]
            print(f'  {date}: {len(sigs)} signals')
            for s in sigs[:5]:
                sym    = (s.get('symbol','?')
                          .replace('.NS',''))
                signal = s.get('signal','?')
                score  = s.get('score','?')
                reason = s.get(
                    'rejection_reason', '—')
                print(f'    {sym} {signal} '
                      f'score={score} '
                      f'reason={reason}')
            if len(sigs) > 5:
                print(f'    ... +{len(sigs)-5} more')

    if gen0_rej:
        print(f'\n[heal_rej] GEN=0 BACKFILL REJECTED '
              f'(excluded from stats — leave as-is):')
        for s in gen0_rej[:5]:
            sym    = (s.get('symbol','?')
                      .replace('.NS',''))
            signal = s.get('signal','?')
            print(f'  {sym} {signal} '
                  f'date={s.get("date","?")}')
        if len(gen0_rej) > 5:
            print(f'  ... +{len(gen0_rej)-5} more')

    # Rejection reason breakdown
    if gen1_rej:
        print(f'\n[heal_rej] REJECTION REASON BREAKDOWN '
              f'(gen=1 only):')
        reasons = {}
        for s in gen1_rej:
            r = s.get('rejection_reason', 'unknown')
            reasons[r] = reasons.get(r, 0) + 1
        for r, n in sorted(
                reasons.items(),
                key=lambda x: -x[1]):
            print(f'  {r}: {n}')

    print(f'\n[heal_rej] RECOMMENDATION:')
    if len(gen1_rej) > 0:
        print(f'  Run with --fix to convert '
              f'{len(gen1_rej)} gen=1 REJECTED '
              f'signals to TOOK PENDING')
    else:
        print(f'  No gen=1 rejected signals found.')
        print(f'  Nothing to fix.')

    return gen1_rej, gen0_rej


def run_fix(history, gen1_only=True):
    """Convert accidentally rejected signals to TOOK."""
    all_rej = [s for s in history if _is_rejected(s)]

    if gen1_only:
        to_fix = [s for s in all_rej if _is_gen1(s)]
        skip   = [s for s in all_rej if _is_gen0(s)]
        print(f'\n[heal_rej] Fixing {len(to_fix)} '
              f'gen=1 rejected signals')
        print(f'[heal_rej] Leaving {len(skip)} '
              f'gen=0 backfill rejected unchanged')
    else:
        to_fix = all_rej
        print(f'\n[heal_rej] Fixing all '
              f'{len(to_fix)} rejected signals')

    if not to_fix:
        print('[heal_rej] Nothing to fix')
        return 0

    fixed  = 0
    id_set = {s.get('id') for s in to_fix
              if s.get('id')}

    for i, sig in enumerate(history):
        sig_id = sig.get('id')
        # Match by id if available
        if sig_id and sig_id in id_set:
            matches = True
        elif not sig_id:
            # Fallback: match by symbol+signal+date
            matches = any(
                sig.get('symbol') == t.get('symbol')
                and sig.get('signal') == t.get('signal')
                and sig.get('date')   == t.get('date')
                for t in to_fix)
        else:
            matches = False

        if not matches:
            continue

        if not _is_rejected(sig):
            continue

        sym    = (sig.get('symbol','?')
                  .replace('.NS',''))
        signal = sig.get('signal','?')
        date   = sig.get('date','?')

        print(f'[heal_rej] Converting: '
              f'{sym} {signal} {date}')

        # Convert to TOOK PENDING
        history[i]['action'] = 'TOOK'
        history[i]['layer']  = 'MINI'
        history[i]['result'] = 'PENDING'

        # Clear rejection fields
        for field in ['rejection_reason',
                      'rejection_filter',
                      'rejection_threshold']:
            if field in history[i]:
                del history[i][field]

        # Set outcome to OPEN explicitly
        history[i]['outcome'] = None

        fixed += 1

    return fixed


def main():
    parser = argparse.ArgumentParser(
        description='Heal accidentally rejected signals')
    parser.add_argument(
        '--report',
        action='store_true',
        help='Show investigation report only')
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Apply fix — convert gen=1 rejected to TOOK')
    parser.add_argument(
        '--all-generations',
        action='store_true',
        help='Fix gen=0 backfill too (default: gen=1 only)')
    args = parser.parse_args()

    if not args.report and not args.fix:
        print('Usage:')
        print('  --report          investigate first')
        print('  --fix             apply correction')
        print('  --all-generations include gen=0')
        return

    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f'[heal_rej] Cannot load history: {e}')
        return

    history = data.get('history', [])

    if args.report or args.fix:
        # Always show report first
        gen1_rej, gen0_rej = run_report(history)

    if args.fix:
        if not gen1_rej and not args.all_generations:
            print('\n[heal_rej] Nothing to fix')
            return

        print('\n[heal_rej] Applying fix...')
        gen1_only = not args.all_generations
        _backup_history()

        fixed = run_fix(history, gen1_only=gen1_only)

        if fixed > 0:
            data['history'] = history
            try:
                _save_json(HISTORY_FILE, data)
                print(f'\n[heal_rej] Done — '
                      f'{fixed} signals converted '
                      f'to TOOK PENDING')
                print('[heal_rej] Refresh PWA to '
                      'see updated counts')
            except Exception as e:
                print(f'[heal_rej] Save failed: {e}')
        else:
            print('[heal_rej] No signals were modified')


if __name__ == '__main__':
    main()
