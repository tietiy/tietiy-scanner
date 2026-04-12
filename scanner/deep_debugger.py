# scanner/deep_debugger.py
# Deep signal forensics tool for TIE TIY Scanner
# NEW FILE — V1 Fix L6
#
# Usage (GitHub Actions manual dispatch or local):
#   python scanner/deep_debugger.py --audit
#   python scanner/deep_debugger.py --signal TATASTEEL 2026-04-06
#   python scanner/deep_debugger.py --lifecycle TATASTEEL 2026-04-06
#   python scanner/deep_debugger.py --sa-check
#   python scanner/deep_debugger.py --regime-audit UP_TRI Bear
#   python scanner/deep_debugger.py --audit --telegram
#
# All modes can add --telegram to send results to Telegram.
# Exit codes: 0=clean, 1=issues found, 2=error
#
# BUG FIX: _send() uses plain text — audit output is
#   data-heavy with special chars that break MarkdownV2
# BUG FIX: run_audit() gen0/gen1 display count —
#   (generation or 1) was treating 0 as falsy,
#   counting gen0 signals as gen1 in display only.
# ─────────────────────────────────────────────────────

import os
import sys
import json
import argparse
from datetime import date, datetime, timedelta

# ── PATH SETUP ────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

sys.path.insert(0, _HERE)

# ── OPTIONAL IMPORTS ──────────────────────────────────
try:
    from telegram_bot import send_message
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from journal import load_history, load_archive
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False


# ── CONSTANTS ─────────────────────────────────────────
OUTCOME_WIN  = {'TARGET_HIT', 'DAY6_WIN'}
OUTCOME_LOSS = {'STOP_HIT',   'DAY6_LOSS'}
OUTCOME_FLAT = {'DAY6_FLAT'}
OUTCOME_DONE = OUTCOME_WIN | OUTCOME_LOSS | OUTCOME_FLAT

VALID_SIGNALS = {
    'UP_TRI', 'DOWN_TRI', 'BULL_PROXY',
    'UP_TRI_SA', 'DOWN_TRI_SA',
}

_FIELD_TYPES = {
    'id':             str,
    'date':           str,
    'symbol':         str,
    'signal':         str,
    'direction':      str,
    'score':          (int, float),
    'entry':          (int, float),
    'stop':           (int, float),
    'result':         str,
    'generation':     int,
    'vol_confirm':    bool,
    'bear_bonus':     bool,
    'is_sa':          bool,
    'grade_A':        bool,
    'rs_strong':      bool,
    'sec_leading':    bool,
}

_V5_FIELDS = [
    'user_action', 'is_sa', 'sa_parent_id',
    'sa_parent_outcome', 'rs_strong',
    'grade_A', 'sec_leading',
]

MAX_TELEGRAM_LINES = 40


# ── TELEGRAM ESCAPE ───────────────────────────────────
def _esc(text):
    if text is None:
        return '—'
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


# ── PLAIN TEXT STRIP ──────────────────────────────────
def _plain(text):
    import re
    text = re.sub(r'\|\|(.+?)\|\|', r'\1',
                  text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)',
                  r'\1 \2', text)
    text = re.sub(r'\\(.)', r'\1', text)
    return text


# ── LOAD ──────────────────────────────────────────────
def _load_all():
    if not JOURNAL_AVAILABLE:
        print("[debugger] journal.py not available")
        return []
    try:
        return load_history()
    except Exception as e:
        print(f"[debugger] Load error: {e}")
        return []


def _load_json_file(filename):
    path = os.path.join(_OUTPUT, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


# ── HELPERS ───────────────────────────────────────────
def _sym(s):
    return (s or '').replace('.NS', '')


def _find_signal(history, symbol, sig_date):
    sym_clean = symbol.upper().replace('.NS', '')
    matches = [
        r for r in history
        if _sym(r.get('symbol', '')).upper() == sym_clean
        and r.get('date', '') == sig_date
        and r.get('action') == 'TOOK'
    ]
    return matches


def _pnl_str(val):
    if val is None:
        return '—'
    f = float(val)
    return ('+' if f >= 0 else '') + f'{f:.2f}%'


def _age_str(date_str):
    if not date_str:
        return '—'
    try:
        d = datetime.strptime(
            date_str, '%Y-%m-%d').date()
        delta = (date.today() - d).days
        return f'{delta}d ago'
    except Exception:
        return date_str


# ── PLAIN TEXT SEND ───────────────────────────────────
def _send(lines, send_tg):
    text = '\n'.join(lines)
    print(text)

    if not send_tg:
        return

    token   = os.environ.get('TELEGRAM_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

    if not token or not chat_id:
        print("[debugger] No Telegram credentials")
        return

    plain   = _plain(text)
    MAX_LEN = 4000
    chunks  = []

    if len(plain) <= MAX_LEN:
        chunks = [plain]
    else:
        lines_split = plain.split('\n')
        current     = ''
        for line in lines_split:
            if len(current) + len(line) + 1 > MAX_LEN:
                chunks.append(current.rstrip('\n'))
                current = line + '\n'
            else:
                current += line + '\n'
        if current.strip():
            chunks.append(current.rstrip('\n'))

    import requests as _req
    url = (f'https://api.telegram.org/'
           f'bot{token}/sendMessage')

    for i, chunk in enumerate(chunks):
        try:
            r = _req.post(url, json={
                'chat_id':                  chat_id,
                'text':                     chunk,
                'disable_web_page_preview': True,
            }, timeout=15)
            if r.status_code == 200:
                print(f'[debugger] Telegram chunk '
                      f'{i+1}/{len(chunks)} sent')
            else:
                print(f'[debugger] Telegram failed: '
                      f'{r.status_code}')
        except Exception as e:
            print(f'[debugger] Telegram error: {e}')

        if i < len(chunks) - 1:
            import time
            time.sleep(1)


# ── MODE 1: FULL AUDIT ────────────────────────────────
def run_audit(history, send_tg=False):
    print("[debugger] Running full audit...")

    issues   = []
    seen_ids = {}

    for i, sig in enumerate(history):
        sid  = sig.get('id', f'idx:{i}')
        sym  = _sym(sig.get('symbol', '?'))
        dt   = sig.get('date', '?')
        tag  = f"{sym}/{dt}"

        if sid in seen_ids:
            issues.append(
                f"DUP_ID  {tag} — id={sid} "
                f"also at idx {seen_ids[sid]}")
        else:
            seen_ids[sid] = i

        stype = sig.get('signal', '')
        if stype not in VALID_SIGNALS:
            issues.append(
                f"BAD_SIG {tag} — signal='{stype}'")

        for field, expected in _FIELD_TYPES.items():
            val = sig.get(field)
            if val is None:
                continue
            if not isinstance(val, expected):
                issues.append(
                    f"BAD_TYPE {tag} — "
                    f"{field}={repr(val)} "
                    f"(expected {expected})")

        missing_v5 = [f for f in _V5_FIELDS
                      if f not in sig]
        if missing_v5:
            issues.append(
                f"NO_V5   {tag} — "
                f"missing: {', '.join(missing_v5)}")

        if sig.get('action') == 'TOOK':
            entry  = float(sig.get('entry')  or 0)
            stop   = float(sig.get('stop')   or 0)
            target = float(
                sig.get('target_price') or 0)
            dirn   = sig.get('direction', 'LONG')

            if entry > 0 and stop > 0:
                if dirn == 'LONG' and stop >= entry:
                    issues.append(
                        f"STOP_ERR {tag} — "
                        f"stop {stop} >= entry "
                        f"{entry} (LONG)")
                if dirn == 'SHORT' and stop <= entry:
                    issues.append(
                        f"STOP_ERR {tag} — "
                        f"stop {stop} <= entry "
                        f"{entry} (SHORT)")

            if entry > 0 and target > 0:
                if dirn == 'LONG' and target <= entry:
                    issues.append(
                        f"TGT_ERR  {tag} — "
                        f"target {target} <= "
                        f"entry {entry}")
                if dirn == 'SHORT' and target >= entry:
                    issues.append(
                        f"TGT_ERR  {tag} — "
                        f"target {target} >= "
                        f"entry {entry}")

            sig_date  = sig.get('date', '')
            exit_date = sig.get('exit_date', '')
            if (sig_date and exit_date
                    and exit_date <= sig_date):
                issues.append(
                    f"DATE_ERR {tag} — "
                    f"exit_date {exit_date} <= "
                    f"signal_date {sig_date}")

        outcome = sig.get('outcome') or ''
        result  = sig.get('result',  '')
        action  = sig.get('action',  '')

        if result == 'REJECTED' and outcome == 'OPEN':
            issues.append(
                f"BAD_OUT  {tag} — "
                f"REJECTED but outcome=OPEN")

        if (result == 'PENDING'
                and outcome in OUTCOME_DONE):
            issues.append(
                f"STUCK    {tag} — "
                f"outcome={outcome} but "
                f"result=PENDING")

        if (action == 'TOOK'
                and sig.get('pnl_pct') is not None
                and outcome not in OUTCOME_DONE):
            issues.append(
                f"PNL_OPEN {tag} — "
                f"has pnl_pct but outcome "
                f"not resolved")

    # BUG FIX: generation=0 is falsy in Python.
    # (s.get('generation', 1) or 1) returns 1 for gen=0
    # because `0 or 1 = 1`. Use explicit None check.
    gen1 = [s for s in history
            if s.get('generation') is not None
            and s.get('generation') >= 1]
    gen0 = [s for s in history
            if s.get('generation') == 0]

    lines = []
    lines.append('DEEP AUDIT')
    lines.append(date.today().isoformat())
    lines.append('')
    lines.append(
        f'Checked: {len(history)} signals '
        f'(gen1={len(gen1)} gen0={len(gen0)})')
    lines.append('')

    if not issues:
        lines.append('No issues found.')
    else:
        lines.append(
            f'{len(issues)} issues found:')
        lines.append('')
        for iss in issues[:MAX_TELEGRAM_LINES]:
            lines.append(f'  {iss}')
        if len(issues) > MAX_TELEGRAM_LINES:
            extra = len(issues) - MAX_TELEGRAM_LINES
            lines.append(f'  ... +{extra} more')

    _send(lines, send_tg)
    return len(issues)


# ── MODE 2: SINGLE SIGNAL INSPECT ────────────────────
def run_signal_inspect(history, symbol,
                       sig_date, send_tg=False):
    matches = _find_signal(history, symbol, sig_date)

    lines = []
    lines.append(
        f'SIGNAL INSPECT: '
        f'{symbol.upper()} / {sig_date}')
    lines.append('')

    if not matches:
        lines.append(
            f'No TOOK signal found for '
            f'{symbol} on {sig_date}.')
        lines.append(
            'Check symbol spelling and date '
            'format (YYYY-MM-DD).')
        _send(lines, send_tg)
        return 1

    for sig in matches:
        stype = sig.get('signal', '?')
        score = sig.get('score', 0)
        lines.append(
            f'{stype} | {score}/10 | '
            f'gen={sig.get("generation")}')
        lines.append('')

        lines.append('IDENTITY')
        lines.append(
            f'  id: {sig.get("id", "—")}')
        lines.append(
            f'  schema_v: '
            f'{sig.get("schema_version")}')
        lines.append(
            f'  layer: {sig.get("layer")} | '
            f'action: {sig.get("action")}')
        lines.append('')

        entry  = sig.get('entry')
        stop   = sig.get('stop')
        target = sig.get('target_price')
        dirn   = sig.get('direction', 'LONG')

        lines.append('TRADE LEVELS')
        lines.append(
            f'  entry: {entry} | '
            f'stop: {stop} | '
            f'target: {target}')

        if entry and stop:
            e, s = float(entry), float(stop)
            if dirn == 'LONG' and s >= e:
                lines.append(
                    '  WARNING: Stop >= entry on LONG')
            if dirn == 'SHORT' and s <= e:
                lines.append(
                    '  WARNING: Stop <= entry on SHORT')
        if not target:
            lines.append(
                '  WARNING: target_price is None')
        lines.append('')

        lines.append('CONTEXT')
        lines.append(
            f'  regime: {sig.get("regime")} | '
            f'stock_regime: '
            f'{sig.get("stock_regime")}')
        lines.append(
            f'  age: {sig.get("age")} | '
            f'sector: {sig.get("sector")}')
        lines.append(
            f'  bear_bonus: {sig.get("bear_bonus")} | '
            f'vol_confirm: {sig.get("vol_confirm")}')
        lines.append(
            f'  rs_strong: {sig.get("rs_strong")} | '
            f'sec_leading: {sig.get("sec_leading")} | '
            f'grade_A: {sig.get("grade_A")}')
        lines.append('')

        if sig.get('is_sa'):
            lines.append('SA TRACKING')
            lines.append(
                f'  is_sa: True | '
                f'parent: {sig.get("sa_parent_id")}')
            lines.append(
                f'  parent_outcome: '
                f'{sig.get("sa_parent_outcome")}')
            if sig.get('sa_parent_outcome') is None:
                lines.append(
                    '  WARNING: parent outcome '
                    'not yet populated')
            lines.append('')

        lines.append('OUTCOME')
        lines.append(
            f'  outcome: {sig.get("outcome")} | '
            f'result: {sig.get("result")}')
        lines.append(
            f'  pnl_pct: '
            f'{_pnl_str(sig.get("pnl_pct"))} | '
            f'outcome_date: '
            f'{sig.get("outcome_date")}')
        lines.append(
            f'  mfe: {sig.get("mfe_pct")}% | '
            f'mae: {sig.get("mae_pct")}%')
        lines.append(
            f'  exit_date: {sig.get("exit_date")} | '
            f'actual: '
            f'{sig.get("exit_date_actual")}')
        lines.append('')

        missing_v5 = [f for f in _V5_FIELDS
                      if f not in sig]
        if missing_v5:
            lines.append(
                f'MISSING V5: '
                f'{", ".join(missing_v5)}')
        else:
            lines.append('All V5 fields present.')

    _send(lines, send_tg)
    return 0


# ── MODE 3: LIFECYCLE TRACE ───────────────────────────
def run_lifecycle(history, symbol,
                  sig_date, send_tg=False):
    matches = _find_signal(history, symbol, sig_date)

    lines = []
    lines.append(
        f'LIFECYCLE: {symbol.upper()} / {sig_date}')
    lines.append('')

    if not matches:
        lines.append(
            f'No signal found for '
            f'{symbol} on {sig_date}.')
        _send(lines, send_tg)
        return 1

    sig = matches[0]

    def _step(icon, name, value, note=None):
        line = f'{icon} {name}: {value}'
        if note:
            line += f' | {note}'
        lines.append(line)

    def _missing(name, why):
        lines.append(f'? {name}: not yet | {why}')

    _step('1', 'Logged',
          sig.get('date', '?'),
          f'scan_time: {sig.get("scan_time", "?")}')
    _step('  ', 'Signal',
          f'{sig.get("signal")} '
          f'score={sig.get("score")} '
          f'age={sig.get("age")}')
    _step('  ', 'Levels',
          f'entry={sig.get("entry")} '
          f'stop={sig.get("stop")} '
          f'target={sig.get("target_price")}')
    lines.append('')

    actual_open = sig.get('actual_open')
    if actual_open is not None:
        gap   = sig.get('gap_pct')
        valid = sig.get('entry_valid')
        _step('2', 'Open validated',
              f'Rs.{actual_open}',
              f'gap={gap}% valid={valid}')
        if valid is False:
            lines.append(
                '  WARNING: Entry invalid — '
                'gap too large — '
                'outcome_evaluator will skip')
    else:
        _missing('Open validation',
                 'open_validator not yet run')
    lines.append('')

    ltp_data = _load_json_file('ltp_prices.json')
    ltp_val  = None
    if ltp_data:
        prices  = ltp_data.get('prices', {})
        sym_key = sig.get('symbol', '')
        ltp_val = (prices.get(sym_key) or
                   prices.get(
                       sym_key.replace('.NS', '')))

    if ltp_val:
        _step('3', 'LTP tracking',
              f'Rs.{ltp_val}',
              ltp_data.get('ltp_updated_at', ''))
    else:
        outcome = sig.get('outcome') or ''
        if outcome in OUTCOME_DONE:
            _step('3', 'LTP tracking',
                  'Resolved — no active LTP')
        else:
            _missing('LTP tracking',
                     'not in ltp_prices.json')
    lines.append('')

    stop_data   = _load_json_file('stop_alerts.json')
    stop_alerts = []
    if stop_data:
        sym_key     = sig.get('symbol', '')
        all_a       = stop_data.get('alerts', [])
        stop_alerts = [
            a for a in all_a
            if a.get('symbol') == sym_key]

    if stop_alerts:
        for a in stop_alerts:
            _step('!', 'Stop alert',
                  a.get('alert_level', '?'),
                  f'time={a.get("check_time")}')
    else:
        lines.append('4. Stop alerts: none active')
    lines.append('')

    outcome = sig.get('outcome') or ''
    if outcome in OUTCOME_DONE:
        _step('5', 'Outcome resolved',
              outcome,
              f'pnl={_pnl_str(sig.get("pnl_pct"))} '
              f'date={sig.get("outcome_date")}')
        mfe = sig.get('mfe_pct')
        mae = sig.get('mae_pct')
        if mfe is not None or mae is not None:
            lines.append(
                f'  MFE: {mfe}% | MAE: {mae}%')
    elif outcome == 'OPEN':
        exit_date = sig.get('exit_date', '?')
        _missing('Outcome',
                 f'still open | exit={exit_date}')
    else:
        _missing('Outcome',
                 f'outcome={outcome} unexpected')

    lines.append('')
    lines.append(
        f'user_action: {sig.get("user_action")}')

    _send(lines, send_tg)
    return 0


# ── MODE 4: SA CHAIN VALIDATOR ────────────────────────
def run_sa_check(history, send_tg=False):
    sa_signals = [
        s for s in history
        if s.get('is_sa') is True
        or (s.get('signal') or '').endswith('_SA')
    ]

    lines = []
    lines.append('SA CHAIN VALIDATOR')
    lines.append(date.today().isoformat())
    lines.append('')
    lines.append(
        f'SA signals found: {len(sa_signals)}')
    lines.append('')

    if not sa_signals:
        lines.append('No SA signals in history yet.')
        _send(lines, send_tg)
        return 0

    issues = 0

    for sig in sa_signals:
        sym       = _sym(sig.get('symbol', '?'))
        dt        = sig.get('date', '?')
        stype     = sig.get('signal', '?')
        parent_id = sig.get('sa_parent_id')
        p_outcome = sig.get('sa_parent_outcome')
        tag       = f'{sym}/{dt}'

        if not parent_id:
            lines.append(
                f'WARN {tag} — no sa_parent_id set')
            issues += 1
            continue

        parent = next(
            (s for s in history
             if s.get('id') == parent_id), None)

        if not parent:
            lines.append(
                f'FAIL {tag} — parent not found: '
                f'{parent_id}')
            issues += 1
            continue

        parent_outcome = parent.get('outcome') or ''

        if parent_outcome in OUTCOME_DONE:
            if p_outcome is None:
                lines.append(
                    f'WARN {tag} — parent resolved '
                    f'({parent_outcome}) but '
                    f'sa_parent_outcome not propagated')
                issues += 1
            elif p_outcome != parent_outcome:
                lines.append(
                    f'WARN {tag} — mismatch: '
                    f'stored={p_outcome} '
                    f'actual={parent_outcome}')
                issues += 1
            else:
                lines.append(
                    f'OK   {tag} — {stype} | '
                    f'parent {parent_outcome}')
        else:
            lines.append(
                f'WAIT {tag} — parent still open')

    lines.append('')
    if issues == 0:
        lines.append('All SA chains valid.')
    else:
        lines.append(
            f'{issues} SA chain issues found.')

    _send(lines, send_tg)
    return issues


# ── MODE 5: REGIME AUDIT ──────────────────────────────
def run_regime_audit(history, signal_type,
                     regime, send_tg=False):
    filtered = [
        s for s in history
        if (s.get('signal') or '').upper() ==
            signal_type.upper()
        and (
            (s.get('stock_regime') or
             s.get('regime') or '')
            .upper() == regime.upper()
        )
        and s.get('action') == 'TOOK'
        # BUG FIX: explicit None check for generation
        and s.get('generation') is not None
        and s.get('generation') >= 1
    ]

    lines = []
    lines.append(
        f'REGIME AUDIT: '
        f'{signal_type.upper()} / {regime.upper()}')
    lines.append(date.today().isoformat())
    lines.append('')
    lines.append(
        f'Signals found: {len(filtered)}')
    lines.append('')

    if not filtered:
        lines.append('No signals match this filter.')
        _send(lines, send_tg)
        return 0

    resolved = [
        s for s in filtered
        if (s.get('outcome') or '') in OUTCOME_DONE
    ]
    wins = [
        s for s in resolved
        if s.get('outcome') in OUTCOME_WIN
    ]

    wr_str = '—'
    if len(resolved) >= 3:
        wr     = round(
            len(wins) / len(resolved) * 100)
        wr_str = f'{wr}%'

    lines.append(
        f'Resolved: {len(resolved)} | WR: {wr_str}')
    lines.append('')

    filtered.sort(
        key=lambda x: x.get('date', ''),
        reverse=True)

    for s in filtered[:MAX_TELEGRAM_LINES]:
        sym     = _sym(s.get('symbol', '?'))
        score   = s.get('score', 0)
        outcome = s.get('outcome') or 'OPEN'
        pnl     = _pnl_str(s.get('pnl_pct'))
        dt      = s.get('date', '?')
        age     = s.get('age', '?')
        bb      = 'BEAR' if s.get('bear_bonus') else ''

        icon = (
            'TGT' if outcome == 'TARGET_HIT' else
            'WIN' if outcome == 'DAY6_WIN'   else
            'STP' if outcome == 'STOP_HIT'   else
            'LOS' if outcome == 'DAY6_LOSS'  else
            'FLT' if outcome == 'DAY6_FLAT'  else
            'OPN'
        )

        lines.append(
            f'{icon} {sym} {dt} '
            f'sc={score} age={age} '
            f'{bb} {pnl}')

    if len(filtered) > MAX_TELEGRAM_LINES:
        extra = (len(filtered) - MAX_TELEGRAM_LINES)
        lines.append(f'... +{extra} more not shown')

    _send(lines, send_tg)
    return 0


# ── MAIN ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='TIE TIY Deep Debugger')
    parser.add_argument(
        '--audit', action='store_true',
        help='Full data integrity audit')
    parser.add_argument(
        '--signal', nargs=2,
        metavar=('SYMBOL', 'DATE'),
        help='Inspect a specific signal')
    parser.add_argument(
        '--lifecycle', nargs=2,
        metavar=('SYMBOL', 'DATE'),
        help='Trace signal lifecycle')
    parser.add_argument(
        '--sa-check', action='store_true',
        help='Validate all SA parent chains')
    parser.add_argument(
        '--regime-audit', nargs=2,
        metavar=('SIGNAL_TYPE', 'REGIME'),
        help='Regime audit: --regime-audit UP_TRI Bear')
    parser.add_argument(
        '--telegram', action='store_true',
        help='Send results to Telegram')

    args = parser.parse_args()

    if not any([
        args.audit, args.signal,
        args.lifecycle, args.sa_check,
        args.regime_audit,
    ]):
        parser.print_help()
        sys.exit(0)

    history = _load_all()
    if not history:
        print("[debugger] No history loaded — aborting")
        sys.exit(2)

    print(f"[debugger] Loaded {len(history)} signals")

    exit_code = 0

    if args.audit:
        issues = run_audit(history, args.telegram)
        if issues > 0:
            exit_code = 1

    if args.signal:
        sym, dt = args.signal
        rc = run_signal_inspect(
            history, sym, dt, args.telegram)
        if rc > 0:
            exit_code = 1

    if args.lifecycle:
        sym, dt = args.lifecycle
        rc = run_lifecycle(
            history, sym, dt, args.telegram)
        if rc > 0:
            exit_code = 1

    if args.sa_check:
        issues = run_sa_check(history, args.telegram)
        if issues > 0:
            exit_code = 1

    if args.regime_audit:
        stype, regime = args.regime_audit
        run_regime_audit(
            history, stype, regime, args.telegram)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
