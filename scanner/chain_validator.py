# ── chain_validator.py ───────────────────────────────
# Audits today's workflow chain. Writes system_health.json
# with status per expected step.
#
# PHILOSOPHY:
# Instead of checking "did the workflow run" (fragile,
# needs git log parsing), we check "did the expected
# side effects happen" (robust, just reads files).
#
# CHECKS:
# 1. morning_scan    → meta.json last_scan is today
# 2. open_validate   → open_prices.json date is today
# 3. eod_update      → eod_prices.json has today's date
# 4. outcome_eval    → signal_history.json modified today
# 5. pattern_miner   → patterns.json generated today
#
# OUTPUT: output/system_health.json
# CONSUMED BY: sidebar health card in ui.js (future)
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HEALTH_FILE = os.path.join(_OUTPUT, 'system_health.json')


def _today_str():
    """Today in IST."""
    from calendar_utils import get_market_status
    try:
        return date.today().isoformat()
    except Exception:
        return datetime.utcnow().date().isoformat()


def _is_weekend_or_holiday():
    """Skip validation on non-trading days."""
    try:
        from calendar_utils import get_market_status
        status = get_market_status()
        return not status.get('is_trading', False)
    except Exception:
        # Fallback: Saturday/Sunday check
        d = date.today()
        return d.weekday() >= 5


def _file_age_seconds(path):
    """Seconds since file was last modified. None if missing."""
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        return (datetime.utcnow().timestamp() - mtime)
    except Exception:
        return None


def _check_morning_scan(today):
    path = os.path.join(_OUTPUT, 'meta.json')
    if not os.path.exists(path):
        return {'status': 'error',
                'note': 'meta.json missing'}

    try:
        with open(path, 'r') as f:
            meta = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'meta.json unreadable: {e}'}

    market_date = meta.get('market_date', '')
    if market_date != today:
        return {'status': 'error',
                'note': f'meta.market_date={market_date} '
                        f'not today'}

    is_trading = meta.get('is_trading_day', True)
    if not is_trading:
        return {'status': 'ok',
                'note': 'Non-trading day'}

    signals_found = meta.get('signals_found', 0)
    universe      = meta.get('universe_size', 0)

    if universe == 0:
        return {'status': 'error',
                'note': 'Universe empty — scan failed'}

    return {'status': 'ok',
            'note': f'Scanned {universe} stocks, '
                    f'{signals_found} signals'}


def _check_open_validate(today):
    path = os.path.join(_OUTPUT, 'open_prices.json')
    if not os.path.exists(path):
        return {'status': 'warn',
                'note': 'open_prices.json not yet written'}

    try:
        with open(path, 'r') as f:
            op = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'open_prices.json unreadable: {e}'}

    op_date = op.get('date', '')
    if op_date != today:
        return {'status': 'warn',
                'note': f'open_prices.date={op_date} '
                        f'not today'}

    count = op.get('count', 0)
    if count == 0:
        return {'status': 'ok',
                'note': 'No signals entering today'}

    return {'status': 'ok',
            'note': f'{count} opens validated at '
                    f'{op.get("fetch_time", "?")}'}


def _check_eod_prices(today):
    path = os.path.join(_OUTPUT, 'eod_prices.json')
    if not os.path.exists(path):
        return {'status': 'warn',
                'note': 'eod_prices.json not yet written'}

    try:
        with open(path, 'r') as f:
            eod = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'eod_prices.json unreadable: {e}'}

    # Check if ANY symbol has today's data
    has_today = False
    symbol_count = 0
    for sym, dates in eod.items():
        if isinstance(dates, dict):
            symbol_count += 1
            if today in dates:
                has_today = True

    if symbol_count == 0:
        return {'status': 'error',
                'note': 'eod_prices.json empty'}

    if not has_today:
        return {'status': 'warn',
                'note': f'No symbol has {today} data yet'}

    return {'status': 'ok',
            'note': f'EOD written for {symbol_count} symbols'}


def _check_outcome_eval(today):
    path = os.path.join(_OUTPUT, 'signal_history.json')
    if not os.path.exists(path):
        return {'status': 'error',
                'note': 'signal_history.json missing'}

    age = _file_age_seconds(path)
    if age is None:
        return {'status': 'error',
                'note': 'Cannot check file age'}

    # Should be modified within last 24 hours on any trading day
    if age > 86400:
        return {'status': 'warn',
                'note': f'Not modified in '
                        f'{int(age/3600)} hours'}

    try:
        with open(path, 'r') as f:
            data = json.load(f)
        history = data.get('history', [])
        total    = len(history)
        pending  = sum(1 for s in history
                       if s.get('result') == 'PENDING')
        resolved = total - pending

        return {'status': 'ok',
                'note': f'{total} records, '
                        f'{pending} pending, '
                        f'{resolved} resolved'}
    except Exception as e:
        return {'status': 'error',
                'note': f'history unreadable: {e}'}


def _check_pattern_miner(today):
    path = os.path.join(_OUTPUT, 'patterns.json')
    if not os.path.exists(path):
        return {'status': 'warn',
                'note': 'patterns.json not generated yet'}

    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'patterns.json unreadable: {e}'}

    generated_at = data.get('generated_at', '')
    if not generated_at.startswith(today):
        return {'status': 'warn',
                'note': f'Last run: {generated_at[:10]}'}

    summary = data.get('summary', {})
    total   = summary.get('total_patterns', 0)
    val     = summary.get('validated', 0)
    pre     = summary.get('preliminary', 0)

    return {'status': 'ok',
            'note': f'{total} patterns '
                    f'(V:{val} P:{pre})'}


def _determine_overall(checks):
    statuses = [c['status'] for c in checks.values()]
    if 'error' in statuses:
        return 'error'
    if 'warn' in statuses:
        return 'warn'
    return 'healthy'


def run_chain_validation():
    print("[chain_validator] Starting validation...")

    today = _today_str()

    if _is_weekend_or_holiday():
        print(f"[chain_validator] Non-trading day — "
              f"skipping detailed checks")
        health = {
            'schema_version': 1,
            'generated_at': datetime.utcnow()
                .replace(tzinfo=timezone.utc)
                .isoformat(),
            'date': today,
            'trading_day': False,
            'overall': 'skipped',
            'checks': {},
            'alerts': [],
        }
    else:
        print(f"[chain_validator] Validating chain "
              f"for {today}...")

        checks = {
            'morning_scan':   _check_morning_scan(today),
            'open_validate':  _check_open_validate(today),
            'eod_update':     _check_eod_prices(today),
            'outcome_eval':   _check_outcome_eval(today),
            'pattern_miner':  _check_pattern_miner(today),
        }

        alerts = []
        for step, result in checks.items():
            symbol = {'ok': '✓', 'warn': '⚠', 'error': '✗'}.get(
                result['status'], '?')
            print(f"[chain_validator]   {symbol} {step}: "
                  f"{result['note']}")
            if result['status'] == 'error':
                alerts.append(f"{step}: {result['note']}")

        overall = _determine_overall(checks)

        health = {
            'schema_version': 1,
            'generated_at': datetime.utcnow()
                .replace(tzinfo=timezone.utc)
                .isoformat(),
            'date': today,
            'trading_day': True,
            'overall': overall,
            'checks': checks,
            'alerts': alerts,
        }

    os.makedirs(_OUTPUT, exist_ok=True)
    try:
        with open(HEALTH_FILE, 'w') as f:
            json.dump(health, f, indent=2, default=str)
        print(f"[chain_validator] system_health.json "
              f"written — overall: {health['overall']}")
    except Exception as e:
        print(f"[chain_validator] Write failed: {e}")
        raise

    return health


if __name__ == '__main__':
    run_chain_validation()
