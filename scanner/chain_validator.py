# ── chain_validator.py ───────────────────────────────
# Audits today's workflow chain. Writes system_health.json
# with status per expected step.
#
# PHILOSOPHY:
# Instead of checking "did the workflow run" (fragile,
# needs git log parsing), we check "did the expected
# side effects happen" (robust, just reads files).
#
# CHECKS (7 total, post M-05):
# 1. morning_scan    → meta.json last_scan is today
# 2. open_validate   → open_prices.json date is today
# 3. eod_update      → eod_prices.json has today's date
# 4. outcome_eval    → signal_history.json modified today
# 5. pattern_miner   → patterns.json generated today
# 6. rule_proposer   → proposed_rules.json generated today  [M-05]
# 7. contra_tracker  → contra_shadow.json structurally valid [M-05]
#
# M-05 FIX (Apr 25 2026):
#   Added _check_rule_proposer() and _check_contra_tracker().
#   Previously, rule_proposer and contra_tracker could be
#   silently broken for weeks and chain_validator would still
#   report overall='healthy'. This mirrors the intelligence
#   chain actually shipped in eod_master.yml (morning_scan →
#   open_validate → ltp → stop → eod → outcome_eval →
#   pattern_miner → rule_proposer, with contra_tracker firing
#   during morning scan on kill_switch matches).
#
#   Note on contra_tracker semantics: contra_shadow.json is
#   lazy-created on first kill match and only updated when
#   new kills fire or shadows resolve. Staleness alone is NOT
#   an alert — on days with no kill_pattern matches, the file
#   legitimately doesn't move. Only missing file, unreadable
#   file, or counter drift trigger warn/error.
#
#   Note on rule_proposer semantics: rule_proposer early-returns
#   without writing if patterns.json has zero patterns. So a
#   stale proposed_rules.json could be (a) genuine chain break,
#   or (b) benign 0-pattern day. The warn note mentions both
#   possibilities so operator knows where to look.
#
# OUTPUT: output/system_health.json
# CONSUMED BY: sidebar health card in ui.js (future),
#              PWA Telegram alerts on error-status checks.
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import datetime, date, timedelta, timezone
from calendar_utils import ist_today, ist_now, ist_now_str, is_trading_day

sys.path.insert(0, os.path.dirname(__file__))

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HEALTH_FILE = os.path.join(_OUTPUT, 'system_health.json')


def _today_str():
    """Today in IST."""
    from calendar_utils import get_market_status
    try:
        return ist_today().isoformat()
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
        d = ist_today()
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


# ── M-05 (Apr 25 2026): rule_proposer step check ─────
def _check_rule_proposer(today):
    """
    Validates rule_proposer.py step.

    Expected side effect: proposed_rules.json regenerated every
    EOD after pattern_miner runs. If present but stale, either
    chain broke between pattern_miner and rule_proposer, OR
    pattern_miner produced 0 patterns and rule_proposer legitimately
    skipped its write. The warn note mentions both so the operator
    can check patterns.json to distinguish.
    """
    path = os.path.join(_OUTPUT, 'proposed_rules.json')
    if not os.path.exists(path):
        return {'status': 'warn',
                'note': 'proposed_rules.json not generated yet'}

    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'proposed_rules.json unreadable: {e}'}

    generated_at = data.get('generated_at', '')
    if not generated_at.startswith(today):
        return {'status': 'warn',
                'note': f'Last run: {generated_at[:10]} — '
                        f'rule_proposer did not write today '
                        f'(0-pattern day or chain break)'}

    total   = data.get('total_proposals', 0)
    pending = data.get('pending_count', 0)
    active  = data.get('active_kill_rules_count', 0)

    return {'status': 'ok',
            'note': f'{total} proposals '
                    f'(P:{pending} Active:{active})'}


# ── M-05 (Apr 25 2026): contra_tracker step check ────
def _check_contra_tracker(today):
    """
    Validates contra_tracker.py step.

    contra_shadow.json is lazy-created on first kill_switch match.
    On days with no kill-rule hits, generated_at stays stale — that
    is benign, not broken. Only missing file, unreadable file, or
    counter drift trigger warn/error. File existence is softened to
    warn (not error) because a brand-new install with no kill
    matches ever would legitimately have no file.

    Schema integrity check: total_tracked must equal len(shadows).
    If they diverge, contra_tracker is double-writing or the counter
    update is skipping records — worth surfacing.
    """
    path = os.path.join(_OUTPUT, 'contra_shadow.json')
    if not os.path.exists(path):
        return {'status': 'warn',
                'note': 'contra_shadow.json not yet created '
                        '(no kill-switch matches ever '
                        'OR write path broken)'}

    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        return {'status': 'error',
                'note': f'contra_shadow.json unreadable: {e}'}

    shadows  = data.get('shadows', [])
    total    = data.get('total_tracked', 0)
    resolved = data.get('resolved_count', 0)
    pending  = data.get('pending_count', 0)

    # Schema integrity — counters must match the list
    if total != len(shadows):
        return {'status': 'warn',
                'note': f'Counter drift: total_tracked={total} '
                        f'but shadows list has {len(shadows)}'}

    generated_at = data.get('generated_at', '') or ''
    last_str = generated_at[:10] or 'never'

    # Staleness is BENIGN for this file — only the absence of
    # kill-switch matches since last write. Surface the date
    # without flagging as warn.
    if not generated_at.startswith(today):
        return {'status': 'ok',
                'note': f'{total} shadows '
                        f'(R:{resolved} P:{pending}) — '
                        f'last: {last_str}'}

    return {'status': 'ok',
            'note': f'{total} shadows '
                    f'(R:{resolved} P:{pending}) — fresh today'}


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
            'rule_proposer':  _check_rule_proposer(today),    # M-05
            'contra_tracker': _check_contra_tracker(today),   # M-05
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
