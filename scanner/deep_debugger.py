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

# Field type expectations for per-signal audit
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

# V5 fields that must exist
_V5_FIELDS = [
    'user_action', 'is_sa', 'sa_parent_id',
    'sa_parent_outcome', 'rs_strong',
    'grade_A', 'sec_leading',
]

MAX_TELEGRAM_LINES = 40   # safety cap per message


# ── TELEGRAM ESCAPE ───────────────────────────────────
def _esc(text):
    if text is None:
        return '—'
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
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
    """Find a signal record by stock symbol + date."""
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
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        delta = (date.today() - d).days
        return f'{delta}d ago'
    except Exception:
        return date_str


def _send(lines, send_tg):
    text = '\n'.join(lines)
    print(text)
    if send_tg and TELEGRAM_AVAILABLE:
        # chunk if needed
        try:
            send_message(text)
        except Exception as e:
            print(f"[debugger] Telegram error: {e}")


# ── MODE 1: FULL AUDIT ────────────────────────────────
def run_audit(history, send_tg=False):
    """
    Scans all signals for data integrity issues.
    Checks: type mismatches, logical errors,
    missing V5 fields, duplicate IDs, bad outcomes.
    """
    print("[debugger] Running full audit...")

    issues   = []
    seen_ids = {}

    for i, sig in enumerate(history):
        sid  = sig.get('id', f'idx:{i}')
        sym  = _sym(sig.get('symbol', '?'))
        dt   = sig.get('date', '?')
        tag  = f"{sym}/{dt}"

        # ── Duplicate ID ──────────────────────────────
        if sid in seen_ids:
            issues.append(
                f"DUP_ID  {tag} — id={sid} "
                f"also at idx {seen_ids[sid]}")
        else:
            seen_ids[sid] = i

        # ── Unknown signal type ───────────────────────
        stype = sig.get('signal', '')
        if stype not in VALID_SIGNALS:
            issues.append(
                f"BAD_SIG {tag} — signal='{stype}'")

        # ── Field type mismatches ─────────────────────
        for field, expected in _FIELD_TYPES.items():
            val = sig.get(field)
            if val is None:
                continue
            if not isinstance(val, expected):
                issues.append(
                    f"BAD_TYPE {tag} — "
                    f"{field}={repr(val)} "
                    f"(expected {expected})")

        # ── Missing V5 fields ─────────────────────────
        missing_v5 = [f for f in _V5_FIELDS
                      if f not in sig]
        if missing_v5:
            issues.append(
                f"NO_V5   {tag} — "
                f"missing: {', '.join(missing_v5)}")

        # ── TOOK signals: logical price checks ────────
        if sig.get('action') == 'TOOK':
            entry  = float(sig.get('entry')  or 0)
            stop   = float(sig.get('stop')   or 0)
            target = float(sig.get('target_price') or 0)
            dirn   = sig.get('direction', 'LONG')

            if entry > 0 and stop > 0:
                if dirn == 'LONG' and stop >= entry:
                    issues.append(
                        f"STOP_ERR {tag} — "
                        f"stop {stop} >= entry {entry} "
                        f"(LONG)")
                if dirn == 'SHORT' and stop <= entry:
                    issues.append(
                        f"STOP_ERR {tag} — "
                        f"stop {stop} <= entry {entry} "
                        f"(SHORT)")

            if entry > 0 and target > 0:
                if dirn == 'LONG' and target <= entry:
                    issues.append(
                        f"TGT_ERR  {tag} — "
                        f"target {target} <= entry {entry}")
                if dirn == 'SHORT' and target >= entry:
                    issues.append(
                        f"TGT_ERR  {tag} — "
                        f"target {target} >= entry {entry}")

            # exit_date before entry date
            sig_date  = sig.get('date', '')
            exit_date = sig.get('exit_date', '')
            if sig_date and exit_date and exit_date <= sig_date:
                issues.append(
                    f"DATE_ERR {tag} — "
                    f"exit_date {exit_date} <= "
                    f"signal_date {sig_date}")

        # ── Outcome inconsistencies ───────────────────
        outcome = sig.get('outcome') or ''
        result  = sig.get('result',  '')
        action  = sig.get('action',  '')

        # REJECTED with outcome=OPEN
        if result == 'REJECTED' and outcome == 'OPEN':
            issues.append(
                f"BAD_OUT  {tag} — "
                f"REJECTED but outcome=OPEN")

        # PENDING with outcome=DONE
        if (result == 'PENDING'
                and outcome in OUTCOME_DONE):
            issues.append(
                f"STUCK    {tag} — "
                f"outcome={outcome} but result=PENDING")

        # TOOK with pnl but no outcome
        if (action == 'TOOK'
                and sig.get('pnl_pct') is not None
                and outcome not in OUTCOME_DONE):
            issues.append(
                f"PNL_OPEN {tag} — "
                f"has pnl_pct but outcome not resolved")

    # ── Summary ───────────────────────────────────────
    live = [s for s in history
            if (s.get('generation', 1) or 1) >= 1]
    gen0 = len(history) - len(live)

    lines = []
    lines.append('🔍 *DEEP AUDIT*')
    lines.append(f'{date.today().isoformat()}')
    lines.append('')
    lines.append(
        f'Checked: {_esc(str(len(history)))} signals '
        f'\\(gen1={_esc(str(len(live)))} '
        f'gen0={_esc(str(gen0))}\\)')
    lines.append('')

    if not issues:
        lines.append('✅ No issues found\\.')
    else:
        lines.append(
            f'❌ *{_esc(str(len(issues)))} issues found:*')
        lines.append('')
        for iss in issues[:MAX_TELEGRAM_LINES]:
            lines.append(f'  • {_esc(iss)}')
        if len(issues) > MAX_TELEGRAM_LINES:
            lines.append(
                f'  \\.\\.\\. '
                f'+{len(issues) - MAX_TELEGRAM_LINES} more')

    _send(lines, send_tg)
    return len(issues)


# ── MODE 2: SINGLE SIGNAL INSPECT ────────────────────
def run_signal_inspect(history, symbol,
                       sig_date, send_tg=False):
    """
    Full field-by-field dump of a specific signal.
    Flags suspicious values inline.
    """
    matches = _find_signal(history, symbol, sig_date)

    lines = []
    lines.append(
        f'🔬 *SIGNAL INSPECT · '
        f'{_esc(symbol.upper())} · '
        f'{_esc(sig_date)}*')
    lines.append('')

    if not matches:
        lines.append(
            f'No TOOK signal found for '
            f'{_esc(symbol)} on {_esc(sig_date)}\\.')
        lines.append(
            'Check symbol spelling and date format '
            '\\(YYYY\\-MM\\-DD\\)\\.')
        _send(lines, send_tg)
        return 1

    for sig in matches:
        stype = sig.get('signal', '?')
        score = sig.get('score', 0)
        lines.append(
            f'*{_esc(stype)}* · '
            f'{_esc(str(score))}/10 · '
            f'gen={_esc(str(sig.get("generation")))}')
        lines.append('')

        # ── Core identity ─────────────────────────────
        lines.append('*IDENTITY*')
        lines.append(
            f'  id: {_esc(sig.get("id", "—"))}')
        lines.append(
            f'  schema_v: '
            f'{_esc(str(sig.get("schema_version")))}')
        lines.append(
            f'  layer: {_esc(sig.get("layer"))} · '
            f'action: {_esc(sig.get("action"))}')
        lines.append('')

        # ── Trade levels ──────────────────────────────
        entry  = sig.get('entry')
        stop   = sig.get('stop')
        target = sig.get('target_price')
        dirn   = sig.get('direction', 'LONG')

        lines.append('*TRADE LEVELS*')
        lines.append(
            f'  entry:  {_esc(str(entry))} '
            f'stop: {_esc(str(stop))} '
            f'target: {_esc(str(target))}')

        # flag bad levels inline
        if entry and stop:
            e, s = float(entry), float(stop)
            if dirn == 'LONG' and s >= e:
                lines.append(
                    '  ⚠️ Stop >= entry on LONG')
            if dirn == 'SHORT' and s <= e:
                lines.append(
                    '  ⚠️ Stop <= entry on SHORT')
        if not target:
            lines.append(
                '  ⚠️ target\\_price is None')
        lines.append('')

        # ── Context ───────────────────────────────────
        lines.append('*CONTEXT*')
        lines.append(
            f'  regime: {_esc(sig.get("regime"))} · '
            f'stock\\_regime: '
            f'{_esc(sig.get("stock_regime"))}')
        lines.append(
            f'  age: {_esc(str(sig.get("age")))} · '
            f'sector: {_esc(sig.get("sector"))}')
        lines.append(
            f'  bear\\_bonus: '
            f'{_esc(str(sig.get("bear_bonus")))} · '
            f'vol\\_confirm: '
            f'{_esc(str(sig.get("vol_confirm")))}')
        lines.append(
            f'  rs\\_strong: '
            f'{_esc(str(sig.get("rs_strong")))} · '
            f'sec\\_leading: '
            f'{_esc(str(sig.get("sec_leading")))} · '
            f'grade\\_A: '
            f'{_esc(str(sig.get("grade_A")))}')
        lines.append('')

        # ── SA tracking ───────────────────────────────
        if sig.get('is_sa'):
            lines.append('*SA TRACKING*')
            lines.append(
                f'  is\\_sa: True · '
                f'parent: '
                f'{_esc(sig.get("sa_parent_id"))}')
            lines.append(
                f'  parent\\_outcome: '
                f'{_esc(sig.get("sa_parent_outcome"))}')
            if sig.get('sa_parent_outcome') is None:
                lines.append(
                    '  ⚠️ parent outcome not yet '
                    'populated')
            lines.append('')

        # ── Outcome ───────────────────────────────────
        lines.append('*OUTCOME*')
        lines.append(
            f'  outcome: '
            f'{_esc(sig.get("outcome"))} · '
            f'result: {_esc(sig.get("result"))}')
        lines.append(
            f'  pnl\\_pct: '
            f'{_esc(_pnl_str(sig.get("pnl_pct")))} · '
            f'outcome\\_date: '
            f'{_esc(sig.get("outcome_date"))}')
        lines.append(
            f'  mfe: '
            f'{_esc(str(sig.get("mfe_pct")))}% · '
            f'mae: '
            f'{_esc(str(sig.get("mae_pct")))}%')
        lines.append(
            f'  exit\\_date: '
            f'{_esc(sig.get("exit_date"))} · '
            f'actual: '
            f'{_esc(sig.get("exit_date_actual"))}')
        lines.append('')

        # ── V5 field check ────────────────────────────
        missing_v5 = [f for f in _V5_FIELDS
                      if f not in sig]
        if missing_v5:
            lines.append(
                f'⚠️ Missing V5 fields: '
                f'{_esc(", ".join(missing_v5))}')
        else:
            lines.append('✅ All V5 fields present')

    _send(lines, send_tg)
    return 0


# ── MODE 3: LIFECYCLE TRACE ───────────────────────────
def run_lifecycle(history, symbol,
                  sig_date, send_tg=False):
    """
    Traces a signal through its full lifecycle:
    logged → open_validated → ltp_tracked →
    outcome_evaluated.
    Shows what happened at each step and what's missing.
    """
    matches = _find_signal(history, symbol, sig_date)

    lines = []
    lines.append(
        f'🔄 *LIFECYCLE · '
        f'{_esc(symbol.upper())} · '
        f'{_esc(sig_date)}*')
    lines.append('')

    if not matches:
        lines.append(
            f'No signal found for '
            f'{_esc(symbol)} on {_esc(sig_date)}\\.')
        _send(lines, send_tg)
        return 1

    sig = matches[0]

    def _step(icon, name, value, note=None):
        line = f'{icon} *{_esc(name)}*: {_esc(str(value))}'
        if note:
            line += f' — {_esc(note)}'
        lines.append(line)

    def _missing(name, why):
        lines.append(
            f'❓ *{_esc(name)}*: not yet — {_esc(why)}')

    # Step 1: Logged
    _step('1️⃣', 'Logged',
          sig.get('date', '?'),
          f'scan_time: {sig.get("scan_time", "?")}')
    _step('  ', 'Signal',
          f'{sig.get("signal")} score={sig.get("score")} '
          f'age={sig.get("age")}')
    _step('  ', 'Levels',
          f'entry={sig.get("entry")} '
          f'stop={sig.get("stop")} '
          f'target={sig.get("target_price")}')
    lines.append('')

    # Step 2: Open validation
    actual_open = sig.get('actual_open')
    if actual_open is not None:
        gap = sig.get('gap_pct')
        valid = sig.get('entry_valid')
        _step('2️⃣', 'Open validated',
              f'₹{actual_open}',
              f'gap={gap}% valid={valid}')
        if valid is False:
            lines.append(
                '  ⚠️ Entry marked invalid — '
                'gap too large')
    else:
        _missing('Open validation',
                 'open_validator not yet run '
                 'or signal date is today')
    lines.append('')

    # Step 3: LTP tracking
    ltp_data = _load_json_file('ltp_prices.json')
    ltp_val  = None
    if ltp_data:
        prices = ltp_data.get('prices', {})
        sym_key = sig.get('symbol', '')
        ltp_val = (prices.get(sym_key) or
                   prices.get(
                       sym_key.replace('.NS', '')))

    if ltp_val:
        _step('3️⃣', 'LTP tracking',
              f'₹{ltp_val}',
              ltp_data.get('ltp_updated_at', ''))
    else:
        outcome = sig.get('outcome') or ''
        if outcome in OUTCOME_DONE:
            _step('3️⃣', 'LTP tracking',
                  'Resolved — no active LTP')
        else:
            _missing('LTP tracking',
                     'not in ltp_prices.json — '
                     'may be outside market hours')
    lines.append('')

    # Step 4: Stop alerts
    stop_data   = _load_json_file('stop_alerts.json')
    stop_alerts = []
    if stop_data:
        sym_key = sig.get('symbol', '')
        all_a   = stop_data.get('alerts', [])
        stop_alerts = [
            a for a in all_a
            if a.get('symbol') == sym_key
        ]

    if stop_alerts:
        for a in stop_alerts:
            _step('⚠️', 'Stop alert',
                  a.get('alert_level', '?'),
                  f'check_time={a.get("check_time")}')
    else:
        lines.append('4️⃣ *Stop alerts*: none active')
    lines.append('')

    # Step 5: Outcome evaluation
    outcome = sig.get('outcome') or ''
    if outcome in OUTCOME_DONE:
        icon = '✅' if outcome in OUTCOME_WIN else '❌'
        _step('5️⃣', 'Outcome resolved',
              outcome,
              f'pnl={_pnl_str(sig.get("pnl_pct"))} '
              f'date={sig.get("outcome_date")}')
        mfe = sig.get('mfe_pct')
        mae = sig.get('mae_pct')
        if mfe is not None or mae is not None:
            lines.append(
                f'  MFE: {mfe}% · MAE: {mae}%')
    elif outcome == 'OPEN':
        exit_date = sig.get('exit_date', '?')
        _missing('Outcome',
                 f'signal still open · '
                 f'exit_date={exit_date}')
    else:
        _missing('Outcome',
                 f'outcome={outcome} — '
                 f'unexpected state')

    lines.append('')
    lines.append(
        f'user\\_action: '
        f'{_esc(str(sig.get("user_action")))}')

    _send(lines, send_tg)
    return 0


# ── MODE 4: SA CHAIN VALIDATOR ────────────────────────
def run_sa_check(history, send_tg=False):
    """
    For every SA signal, validates:
    - Parent signal exists in history
    - Parent has resolved outcome
    - sa_parent_outcome field is populated
    """
    sa_signals = [
        s for s in history
        if s.get('is_sa') is True
        or (s.get('signal') or '').endswith('_SA')
    ]

    lines = []
    lines.append('🔗 *SA CHAIN VALIDATOR*')
    lines.append(f'{date.today().isoformat()}')
    lines.append('')
    lines.append(
        f'SA signals found: '
        f'{_esc(str(len(sa_signals)))}')
    lines.append('')

    if not sa_signals:
        lines.append(
            'No SA signals in history yet\\.')
        _send(lines, send_tg)
        return 0

    all_ids   = {s.get('id') for s in history}
    issues    = 0

    for sig in sa_signals:
        sym       = _sym(sig.get('symbol', '?'))
        dt        = sig.get('date', '?')
        stype     = sig.get('signal', '?')
        parent_id = sig.get('sa_parent_id')
        p_outcome = sig.get('sa_parent_outcome')

        tag = f'{_esc(sym)}/{_esc(dt)}'

        if not parent_id:
            lines.append(
                f'⚠️ {tag} — '
                f'no sa\\_parent\\_id set')
            issues += 1
            continue

        # Find parent in history
        parent = next(
            (s for s in history
             if s.get('id') == parent_id), None)

        if not parent:
            lines.append(
                f'❌ {tag} — parent not found: '
                f'{_esc(parent_id)}')
            issues += 1
            continue

        parent_outcome = parent.get('outcome') or ''

        if parent_outcome in OUTCOME_DONE:
            if p_outcome is None:
                lines.append(
                    f'⚠️ {tag} — parent resolved '
                    f'\\({_esc(parent_outcome)}\\) '
                    f'but sa\\_parent\\_outcome '
                    f'not propagated')
                issues += 1
            elif p_outcome != parent_outcome:
                lines.append(
                    f'⚠️ {tag} — '
                    f'sa\\_parent\\_outcome='
                    f'{_esc(p_outcome)} but '
                    f'parent actual='
                    f'{_esc(parent_outcome)}')
                issues += 1
            else:
                lines.append(
                    f'✅ {tag} — '
                    f'{_esc(stype)} · parent '
                    f'{_esc(parent_outcome)} ✓')
        else:
            lines.append(
                f'⏳ {tag} — '
                f'parent still open')

    lines.append('')
    if issues == 0:
        lines.append('✅ All SA chains valid\\.')
    else:
        lines.append(
            f'❌ {_esc(str(issues))} '
            f'SA chain issues found\\.')

    _send(lines, send_tg)
    return issues


# ── MODE 5: REGIME AUDIT ──────────────────────────────
def run_regime_audit(history, signal_type,
                     regime, send_tg=False):
    """
    Shows all signals of a given type + regime
    with their outcomes in a compact table.
    Useful for validating backtest expectations
    against live data.
    """
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
        and (s.get('generation', 1) or 1) >= 1
    ]

    lines = []
    lines.append(
        f'🌡️ *REGIME AUDIT · '
        f'{_esc(signal_type.upper())} · '
        f'{_esc(regime.upper())}*')
    lines.append(f'{date.today().isoformat()}')
    lines.append('')
    lines.append(
        f'Signals found: '
        f'{_esc(str(len(filtered)))}')
    lines.append('')

    if not filtered:
        lines.append('No signals match this filter\\.')
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
        wr = round(len(wins) / len(resolved) * 100)
        wr_str = f'{wr}%'

    lines.append(
        f'Resolved: {_esc(str(len(resolved)))} · '
        f'WR: {_esc(wr_str)}')
    lines.append('')

    # Table: sym | score | outcome | pnl
    filtered.sort(
        key=lambda x: x.get('date', ''), reverse=True)

    for s in filtered[:MAX_TELEGRAM_LINES]:
        sym     = _sym(s.get('symbol', '?'))
        score   = s.get('score', 0)
        outcome = s.get('outcome') or 'OPEN'
        pnl     = _pnl_str(s.get('pnl_pct'))
        dt      = s.get('date', '?')
        age     = s.get('age', '?')
        bb      = '🔥' if s.get('bear_bonus') else ''

        icon = (
            '🎯' if outcome == 'TARGET_HIT' else
            '✅' if outcome == 'DAY6_WIN'   else
            '🛑' if outcome == 'STOP_HIT'   else
            '❌' if outcome == 'DAY6_LOSS'  else
            '〰️' if outcome == 'DAY6_FLAT'  else
            '⏳'
        )

        lines.append(
            f'{icon} *{_esc(sym)}* '
            f'{_esc(dt)} '
            f'sc={_esc(str(score))} '
            f'age={_esc(str(age))} '
            f'{bb} '
            f'{_esc(pnl)}')

    if len(filtered) > MAX_TELEGRAM_LINES:
        lines.append(
            f'\\.\\.\\. '
            f'+{len(filtered) - MAX_TELEGRAM_LINES}'
            f' more not shown')

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
        help='Inspect a specific signal: '
             '--signal TATASTEEL 2026-04-06')
    parser.add_argument(
        '--lifecycle', nargs=2,
        metavar=('SYMBOL', 'DATE'),
        help='Trace signal lifecycle: '
             '--lifecycle TATASTEEL 2026-04-06')
    parser.add_argument(
        '--sa-check', action='store_true',
        help='Validate all SA parent chains')
    parser.add_argument(
        '--regime-audit', nargs=2,
        metavar=('SIGNAL_TYPE', 'REGIME'),
        help='Regime audit: '
             '--regime-audit UP_TRI Bear')
    parser.add_argument(
        '--telegram', action='store_true',
        help='Send results to Telegram')

    args = parser.parse_args()

    # Must specify at least one mode
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
