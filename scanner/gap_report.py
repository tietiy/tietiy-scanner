# scanner/gap_report.py
# Weekly gap risk analysis — Monday morning
# New file — Phase 4 prep
#
# Reads open_prices history from signal_history.json
# gap_pct field (written by open_validator.py).
# Identifies stocks/sectors with frequent large gaps.
# Sends Monday morning Telegram report.
#
# Usage:
#   python scanner/gap_report.py
#   python scanner/gap_report.py --telegram
#   python scanner/gap_report.py --min-samples 3
# ─────────────────────────────────────────────────────

import os
import sys
import json
import argparse
from datetime import date, datetime
from collections import defaultdict

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

sys.path.insert(0, _HERE)

HISTORY_FILE = os.path.join(_OUTPUT,
    'signal_history.json')

# Gap thresholds
GAP_LARGE_PCT  = 3.0   # skip-worthy gap
GAP_WARN_PCT   = 1.5   # reduced R:R gap
MIN_SAMPLES    = 3     # min signals to include stock

# ── OPTIONAL TELEGRAM ─────────────────────────────────
try:
    from telegram_bot import send_message
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


# ── ESCAPE ────────────────────────────────────────────
def _esc(text):
    if text is None: return '—'
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


# ── LOAD ──────────────────────────────────────────────
def _load_history():
    if not os.path.exists(HISTORY_FILE):
        print('[gap_report] signal_history.json '
              'not found')
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
        return data.get('history', [])
    except Exception as e:
        print(f'[gap_report] Load error: {e}')
        return []


# ── ANALYSIS ──────────────────────────────────────────
def _analyse(history, min_samples=MIN_SAMPLES):
    """
    Analyse gap_pct patterns across all signals
    that have open validation data.

    Returns:
        stock_stats  — per-stock gap summary
        sector_stats — per-sector gap summary
        signal_stats — per-signal-type gap summary
        overall      — aggregate stats
        samples      — raw gap records
    """
    # Only TOOK signals with gap_pct recorded
    gapped = [
        s for s in history
        if s.get('action') == 'TOOK'
        and s.get('gap_pct') is not None
        and (s.get('generation', 1) or 1) >= 1
    ]

    if not gapped:
        return None

    samples = []
    for s in gapped:
        sym    = (s.get('symbol') or '?') \
                 .replace('.NS', '')
        gap    = float(s.get('gap_pct') or 0)
        valid  = s.get('entry_valid', True)
        sector = s.get('sector') or 'Other'
        signal = s.get('signal') or '?'
        dt     = s.get('date') or ''

        samples.append({
            'sym':    sym,
            'gap':    gap,
            'abs':    abs(gap),
            'large':  abs(gap) >= GAP_LARGE_PCT,
            'warn':   abs(gap) >= GAP_WARN_PCT,
            'valid':  valid is not False,
            'sector': sector,
            'signal': signal,
            'date':   dt,
        })

    # ── Per-stock stats ───────────────────────────────
    stock_map = defaultdict(lambda: {
        'gaps': [], 'large': 0, 'warn': 0,
        'invalid': 0, 'sector': '', 'signal': ''})

    for rec in samples:
        sm = stock_map[rec['sym']]
        sm['gaps'].append(rec['abs'])
        sm['sector'] = rec['sector']
        sm['signal'] = rec['signal']
        if rec['large']:  sm['large']   += 1
        if rec['warn']:   sm['warn']    += 1
        if not rec['valid']: sm['invalid'] += 1

    stock_stats = []
    for sym, sm in stock_map.items():
        n        = len(sm['gaps'])
        if n < min_samples:
            continue
        avg_gap  = sum(sm['gaps']) / n
        large_rt = round(sm['large'] / n * 100)
        warn_rt  = round(sm['warn']  / n * 100)
        risk_lvl = (
            'HIGH'   if large_rt >= 50 else
            'MEDIUM' if warn_rt  >= 40 else
            'LOW')
        stock_stats.append({
            'sym':       sym,
            'n':         n,
            'avg_gap':   round(avg_gap, 2),
            'large_pct': large_rt,
            'warn_pct':  warn_rt,
            'invalid':   sm['invalid'],
            'sector':    sm['sector'],
            'signal':    sm['signal'],
            'risk':      risk_lvl,
        })

    stock_stats.sort(
        key=lambda x: (
            x['risk'] == 'HIGH',
            x['large_pct'],
            x['avg_gap']),
        reverse=True)

    # ── Per-sector stats ──────────────────────────────
    sector_map = defaultdict(lambda: {
        'gaps': [], 'large': 0, 'n': 0})

    for rec in samples:
        sm = sector_map[rec['sector']]
        sm['gaps'].append(rec['abs'])
        sm['n'] += 1
        if rec['large']: sm['large'] += 1

    sector_stats = []
    for sec, sm in sector_map.items():
        n = sm['n']
        if n < min_samples:
            continue
        avg_gap  = sum(sm['gaps']) / n
        large_rt = round(sm['large'] / n * 100)
        sector_stats.append({
            'sector':    sec,
            'n':         n,
            'avg_gap':   round(avg_gap, 2),
            'large_pct': large_rt,
        })

    sector_stats.sort(
        key=lambda x: x['avg_gap'],
        reverse=True)

    # ── Per-signal-type stats ─────────────────────────
    sig_map = defaultdict(lambda: {
        'gaps': [], 'large': 0, 'n': 0})

    for rec in samples:
        sm = sig_map[rec['signal']]
        sm['gaps'].append(rec['abs'])
        sm['n'] += 1
        if rec['large']: sm['large'] += 1

    signal_stats = []
    for sig, sm in sig_map.items():
        n = sm['n']
        if n < 2:
            continue
        avg_gap  = sum(sm['gaps']) / n
        large_rt = round(sm['large'] / n * 100)
        signal_stats.append({
            'signal':    sig,
            'n':         n,
            'avg_gap':   round(avg_gap, 2),
            'large_pct': large_rt,
        })

    signal_stats.sort(
        key=lambda x: x['avg_gap'],
        reverse=True)

    # ── Overall ───────────────────────────────────────
    all_gaps   = [r['abs'] for r in samples]
    n          = len(all_gaps)
    avg        = sum(all_gaps) / n if n else 0
    large_n    = sum(1 for r in samples if r['large'])
    warn_n     = sum(1 for r in samples if r['warn'])
    invalid_n  = sum(1 for r in samples
                     if not r['valid'])

    overall = {
        'total_signals':  n,
        'avg_gap':        round(avg, 2),
        'large_n':        large_n,
        'large_pct':      round(large_n / n * 100)
                          if n else 0,
        'warn_n':         warn_n,
        'warn_pct':       round(warn_n  / n * 100)
                          if n else 0,
        'invalid_n':      invalid_n,
        'invalid_pct':    round(invalid_n / n * 100)
                          if n else 0,
    }

    return {
        'stock_stats':  stock_stats,
        'sector_stats': sector_stats,
        'signal_stats': signal_stats,
        'overall':      overall,
        'samples':      samples,
        'n':            n,
    }


# ── CONSOLE REPORT ────────────────────────────────────
def _print_report(result):
    today = date.today().isoformat()
    print('=' * 50)
    print(f'GAP RISK REPORT · {today}')
    print('=' * 50)

    ov = result['overall']
    print(f"\nSamples: {ov['total_signals']} signals "
          f"with gap data")
    print(f"Avg gap:  {ov['avg_gap']}%")
    print(f"Large (>{GAP_LARGE_PCT}%): "
          f"{ov['large_n']} "
          f"({ov['large_pct']}%)")
    print(f"Warn  (>{GAP_WARN_PCT}%): "
          f"{ov['warn_n']} "
          f"({ov['warn_pct']}%)")
    print(f"Invalid:  {ov['invalid_n']} "
          f"({ov['invalid_pct']}%)")

    print('\n── HIGH RISK STOCKS ──')
    high = [s for s in result['stock_stats']
            if s['risk'] == 'HIGH']
    if high:
        for s in high[:10]:
            print(f"  {s['sym']:<15} "
                  f"avg={s['avg_gap']}% "
                  f"large={s['large_pct']}% "
                  f"n={s['n']}")
    else:
        print('  None found')

    print('\n── BY SIGNAL TYPE ──')
    for s in result['signal_stats']:
        print(f"  {s['signal']:<15} "
              f"avg={s['avg_gap']}% "
              f"large={s['large_pct']}% "
              f"n={s['n']}")

    print('\n── TOP SECTORS BY AVG GAP ──')
    for s in result['sector_stats'][:5]:
        print(f"  {s['sector']:<20} "
              f"avg={s['avg_gap']}% "
              f"n={s['n']}")

    print('')


# ── TELEGRAM REPORT ───────────────────────────────────
def _send_telegram(result):
    if not TELEGRAM_AVAILABLE:
        print('[gap_report] Telegram not available')
        return

    today = date.today().isoformat()
    ov    = result['overall']

    lines = []
    lines.append(
        f'📐 *GAP RISK REPORT · {_esc(today)}*')
    lines.append('')
    lines.append(
        f'Signals with gap data: '
        f'{_esc(str(ov["total_signals"]))}')
    lines.append(
        f'Avg gap: {_esc(str(ov["avg_gap"]))}%')
    lines.append(
        f'Large \\(>{_esc(str(GAP_LARGE_PCT))}%\\): '
        f'{_esc(str(ov["large_n"]))} '
        f'\\({_esc(str(ov["large_pct"]))}%\\)')
    lines.append(
        f'Skip rate: '
        f'{_esc(str(ov["invalid_pct"]))}% of entries '
        f'had gap too large')
    lines.append('')

    # High risk stocks
    high = [s for s in result['stock_stats']
            if s['risk'] == 'HIGH']
    if high:
        lines.append('🚨 *HIGH GAP RISK STOCKS:*')
        for s in high[:8]:
            lines.append(
                f'  {_esc(s["sym"])} — '
                f'avg {_esc(str(s["avg_gap"]))}% · '
                f'{_esc(str(s["large_pct"]))}% '
                f'large gaps · '
                f'{_esc(str(s["n"]))} signals')
        lines.append('')

    # Medium risk
    med = [s for s in result['stock_stats']
           if s['risk'] == 'MEDIUM']
    if med:
        syms = ', '.join(
            _esc(s['sym']) for s in med[:6])
        lines.append(
            f'⚠️ *Medium risk:* {syms}')
        lines.append('')

    # By signal type
    if result['signal_stats']:
        lines.append('*BY SIGNAL TYPE:*')
        for s in result['signal_stats']:
            lines.append(
                f'  {_esc(s["signal"])}: '
                f'avg {_esc(str(s["avg_gap"]))}% · '
                f'large {_esc(str(s["large_pct"]))}% '
                f'\\({_esc(str(s["n"]))} signals\\)')
        lines.append('')

    # Top gap sectors
    if result['sector_stats']:
        top_sec = result['sector_stats'][:3]
        sec_str = ' · '.join(
            f'{_esc(s["sector"])} '
            f'{_esc(str(s["avg_gap"]))}%'
            for s in top_sec)
        lines.append(
            f'🏭 Top gap sectors: {sec_str}')
        lines.append('')

    lines.append(
        '_Gap > 3% at open = skip entry\\. '
        'Plan positions accordingly\\._')

    try:
        send_message('\n'.join(lines))
        print('[gap_report] Telegram sent')
    except Exception as e:
        print(f'[gap_report] Telegram error: {e}')


# ── MAIN ──────────────────────────────────────────────
def run_gap_report(send_tg=False,
                   min_samples=MIN_SAMPLES):
    print('[gap_report] Starting...')

    today = date.today()
    print(f'[gap_report] Date: {today.isoformat()}')

    history = _load_history()
    if not history:
        print('[gap_report] No history — aborting')
        return

    result = _analyse(history,
                      min_samples=min_samples)

    if not result:
        print('[gap_report] No gap data in history yet')
        print('[gap_report] gap_pct is written by '
              'open_validator.py after signals enter')
        if send_tg and TELEGRAM_AVAILABLE:
            send_message(
                '📐 *GAP REPORT* — No gap data yet\\.\n'
                'Populates after open validation runs\\.')
        return

    _print_report(result)

    if send_tg:
        _send_telegram(result)

    print(f'[gap_report] Done — '
          f'{result["n"]} samples analysed')


# ── CLI ───────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='TIE TIY Gap Risk Report')
    parser.add_argument(
        '--telegram', action='store_true',
        help='Send report to Telegram')
    parser.add_argument(
        '--min-samples', type=int,
        default=MIN_SAMPLES,
        help=f'Min signals per stock '
             f'(default: {MIN_SAMPLES})')

    args = parser.parse_args()

    run_gap_report(
        send_tg=args.telegram,
        min_samples=args.min_samples)
