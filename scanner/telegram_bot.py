# scanner/telegram_bot.py
# All Telegram message formatting and sending
#
# Message designs confirmed:
# 1. Morning scan   — spoiler price details, stock regime visible
# 2. Open validate  — gap focused, silent if all OK
# 3. Stop alert     — compact, urgent
# 4. Exit tomorrow  — entry + ltp + % vs entry
# 5. EOD summary    — signal type + outcome + P&L
# ─────────────────────────────────────────────────────

import os
import requests

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8493010921')


# ── CORE SEND ─────────────────────────────────────────
def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN:
        print('[telegram] No TELEGRAM_TOKEN — skipping')
        return False
    url     = (f'https://api.telegram.org/'
               f'bot{TELEGRAM_TOKEN}/sendMessage')
    payload = {
        'chat_id':    TELEGRAM_CHAT_ID,
        'text':       text,
        'parse_mode': 'MarkdownV2',
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f'[telegram] Sent OK ({r.status_code})')
        return True
    except Exception as e:
        print(f'[telegram] Error: {e}')
        # Fallback: try without parse_mode
        try:
            payload['parse_mode'] = 'HTML'
            payload['text']       = _md_to_html(text)
            r = requests.post(
                url, json=payload, timeout=10)
            r.raise_for_status()
            print(f'[telegram] Sent OK HTML fallback')
            return True
        except Exception as e2:
            print(f'[telegram] HTML fallback error: {e2}')
            return False


def _md_to_html(text):
    """Basic MarkdownV2 to HTML conversion for fallback."""
    import re
    # Spoiler: ||text|| → <tg-spoiler>text</tg-spoiler>
    text = re.sub(
        r'\|\|(.+?)\|\|',
        r'<tg-spoiler>\1</tg-spoiler>',
        text, flags=re.DOTALL)
    # Bold: *text* → <b>text</b>
    text = re.sub(r'\*(.+?)\*', r'<b>\1</b>', text)
    # Escape remaining HTML chars
    return text


# ── ESCAPE FOR MARKDOWNV2 ─────────────────────────────
def _esc(text):
    """
    Escape special characters for Telegram MarkdownV2.
    Must escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    Do NOT escape inside spoiler tags — handled separately.
    """
    if text is None:
        return '—'
    text = str(text)
    special = r'\_*[]()~`>#+-=|{}.!'
    for ch in special:
        text = text.replace(ch, f'\\{ch}')
    return text


def _spoiler(text):
    """Wrap text in Telegram spoiler tags."""
    return f'||{text}||'


# ── PRICE FORMATTERS ──────────────────────────────────
def _p(val):
    """Format price as ₹X or ₹X,XXX — no escaping needed inside spoiler."""
    try:
        f = float(val)
        if f <= 0:
            return '—'
        if f >= 1000:
            return f'₹{f:,.0f}'
        return f'₹{f:.2f}'
    except Exception:
        return '—'


def _p_esc(val):
    """Format price, escaped for MarkdownV2 outside spoiler."""
    return _esc(_p(val))


def _pct(val, favorable=True):
    """Format percentage with sign."""
    try:
        f = float(val)
        sign = '+' if f >= 0 else ''
        return f'{sign}{f:.1f}%'
    except Exception:
        return '—'


def _rr_calc(entry, stop, target, direction='LONG'):
    """Calculate R:R. Returns string or None."""
    try:
        e = float(entry  or 0)
        s = float(stop   or 0)
        t = float(target or 0)
        if not e or not s or not t:
            return None
        risk   = abs(e - s)
        reward = abs(t - e)
        if risk <= 0:
            return None
        rr = reward / risk
        return f'{rr:.1f}x'
    except Exception:
        return None


def _resolve(sig, *fields):
    """Try multiple field names, return first valid float > 0."""
    for field in fields:
        val = sig.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except Exception:
                continue
    return None


def _sig_emoji(signal_type):
    t = (signal_type or '').upper()
    if 'UP'   in t: return '🟢'
    if 'DOWN' in t: return '🔻'
    if 'BULL' in t: return '🟢'
    return '📌'


def _outcome_emoji(outcome):
    o = (outcome or '').upper()
    if 'TARGET' in o:       return '🎯'
    if 'STOP'   in o:       return '🛑'
    if 'WIN'    in o:       return '✅'
    if 'LOSS'   in o:       return '🔴'
    if 'FLAT'   in o:       return '〰️'
    return '📌'


def _stock_regime_tag(sig):
    """Returns stk:Bull / stk:Bear / stk:Choppy or empty."""
    sr = sig.get('stock_regime', '')
    if not sr:
        return ''
    return f'stk:{sr}'


# ── 1. MORNING SCAN ───────────────────────────────────
def send_morning_scan(signals: list, meta: dict):
    """
    Design: compact visible line per signal with stock regime.
    Price details hidden in spoiler — tap to reveal.
    Sorted by score descending.
    """
    date_str     = meta.get('market_date', 'today')
    regime       = meta.get('regime', '')
    universe     = meta.get('universe_size', 0)
    active_count = meta.get('active_signals_count',
                   meta.get('signals_found', 0))
    new_count    = len(signals)

    # Sort by score descending
    sorted_sigs = sorted(
        signals,
        key=lambda x: float(x.get('score', 0) or 0),
        reverse=True)

    lines = []
    lines.append(
        f'🔔 *TIE TIY · {_esc(date_str)} · '
        f'{_esc(regime)}*')
    lines.append('')
    lines.append(
        f'{_esc(str(new_count))} new signals · '
        f'{_esc(str(active_count))} active')
    lines.append('')

    if not sorted_sigs:
        lines.append(
            'No new signals today\\. Market watching\\.')
    else:
        for sig in sorted_sigs:
            sym       = (sig.get('symbol') or '?') \
                        .replace('.NS', '')
            stype     = sig.get('signal', '?')
            score     = sig.get('score', 0)
            age       = sig.get('age', 0)
            sr_tag    = _stock_regime_tag(sig)
            direction = sig.get('direction', 'LONG')
            emoji     = _sig_emoji(stype)

            entry  = _resolve(sig,
                'actual_open', 'scan_price',
                'entry', 'entry_est')
            stop   = _resolve(sig, 'stop')
            target = _resolve(sig, 'target_price',
                              'target')
            rr     = _rr_calc(entry, stop, target,
                               direction)

            # Visible line — name, type, score, age,
            # stock regime
            visible = (
                f'{emoji} *{_esc(sym)}* · '
                f'{_esc(stype)} · '
                f'{_esc(str(score))}/10 · '
                f'Age {_esc(str(age))}'
                + (f' · {_esc(sr_tag)}'
                   if sr_tag else ''))

            # Spoiler line — price details
            # No escaping inside spoiler
            spoiler_parts = []
            if entry:
                spoiler_parts.append(
                    f'Entry {_p(entry)}')
            if stop:
                spoiler_parts.append(
                    f'Stop {_p(stop)}')
            if target:
                spoiler_parts.append(
                    f'Target {_p(target)}')
            if rr:
                spoiler_parts.append(
                    f'R:R {rr}')
            spoiler_text = ' · '.join(
                spoiler_parts) if spoiler_parts \
                else 'Price data unavailable'

            lines.append(visible)
            lines.append(_spoiler(spoiler_text))
            lines.append('')

    lines.append(
        '🔗 tietiy\\.github\\.io/tietiy\\-scanner/')

    send_message('\n'.join(lines))


# ── 2. OPEN VALIDATION ────────────────────────────────
def send_open_validation(confirmed: list,
                         rejected: list):
    """
    Design: gap focused.
    Show all signals with gap status.
    Flag clearly if skip needed.
    """
    lines = []
    lines.append('📋 *Open Prices · 9:25 AM*')
    lines.append('')

    all_results = confirmed + rejected
    if not all_results:
        lines.append(
            'No signals entering today\\.')
        send_message('\n'.join(lines))
        return

    has_skip    = any(
        s.get('gap_status') == 'SKIP'
        for s in all_results)
    has_warning = any(
        s.get('gap_status') == 'WARNING'
        for s in all_results)

    for sig in all_results:
        sym        = (sig.get('symbol') or '?') \
                     .replace('.NS', '')
        actual     = _resolve(sig, 'actual_open',
                              'open_price')
        gap        = sig.get('gap_pct')
        gap_status = sig.get('gap_status', 'OK')

        if gap_status == 'SKIP':
            icon = '❌'
        elif gap_status == 'WARNING':
            icon = '⚠️'
        else:
            icon = '✅'

        gap_str = ''
        if gap is not None:
            try:
                gap_str = (f' gap '
                           f'{float(gap):+.1f}%')
            except Exception:
                pass

        lines.append(
            f'{icon} *{_esc(sym)}*  '
            f'{_p_esc(actual)}'
            f'{_esc(gap_str)}  '
            f'{_esc(gap_status)}')

    lines.append('')
    if has_skip:
        lines.append(
            '❌ *Skip signals marked above\\. '
            'Gap too large\\.*')
    elif has_warning:
        lines.append(
            '⚠️ Caution signals above — reduced R:R\\.')
    else:
        lines.append(
            'All entries valid\\. Enter at market\\.')

    send_message('\n'.join(lines))


# ── 3. STOP ALERT ─────────────────────────────────────
def send_stop_alert(signal: dict):
    """
    Design: compact, urgent, actionable.
    Name + price + stop + distance + action.
    """
    sym   = (signal.get('symbol') or '?') \
            .replace('.NS', '')
    stype = signal.get('signal', '?')
    stop  = _resolve(signal, 'stop')
    price = _resolve(signal, 'current_price',
                     'ltp', 'close')
    level = signal.get('alert_level', 'NEAR')
    note  = signal.get('note', '')

    if level == 'BREACHED':
        icon = '🚨'
        action = 'Exit immediately at market\\.'
    elif level == 'AT':
        icon = '🔴'
        action = 'At stop level\\. Exit if next tick goes against\\.'
    else:
        icon = '⚠️'
        action = 'Watch closely\\.'

    lines = []
    lines.append(
        f'{icon} *STOP ALERT · '
        f'{signal.get("check_time", "")}*')
    lines.append('')
    lines.append(
        f'*{_esc(sym)}* · {_esc(stype)}')
    lines.append(
        f'Price {_p_esc(price)}  '
        f'Stop {_p_esc(stop)}  '
        f'{_esc(level)}')
    lines.append('')
    lines.append(action)
    lines.append(
        'Rule: stop hit intraday \\= '
        'exit same day\\.')

    send_message('\n'.join(lines))


# ── 4. EXIT TOMORROW ──────────────────────────────────
def send_exit_tomorrow(signals: list):
    """
    Design: entry + ltp + % vs entry per signal.
    Green/red/warning emoji by P&L.
    Sorted worst to best so negatives are visible first.
    """
    if not signals:
        return

    lines = []
    lines.append(
        f'⏰ *EXIT TOMORROW — Day 6 Open*')
    lines.append(
        f'{_esc(str(len(signals)))} signals · '
        f'Sell at 9:15 AM open\\. No extensions\\.')
    lines.append('')

    # Calculate P&L for each, sort worst first
    enriched = []
    for sig in signals:
        sym       = (sig.get('symbol') or '?') \
                    .replace('.NS', '')
        stype     = sig.get('signal',
                    sig.get('signal_type', '?'))
        direction = sig.get('direction', 'LONG')

        entry = _resolve(sig,
            'actual_open', 'scan_price',
            'entry', 'entry_price')
        ltp   = _resolve(sig, 'ltp',
                         'close', 'current_price')

        pnl_pct = None
        if entry and ltp:
            try:
                raw = (ltp - entry) / entry * 100
                pnl_pct = raw if direction == 'LONG' \
                          else -raw
            except Exception:
                pass

        enriched.append({
            'sym':      sym,
            'stype':    stype,
            'entry':    entry,
            'ltp':      ltp,
            'pnl_pct':  pnl_pct,
            'direction': direction,
        })

    # Sort: worst P&L first (negatives at top = urgent)
    enriched.sort(
        key=lambda x: float(
            x['pnl_pct'] or 0))

    for e in enriched:
        pnl = e['pnl_pct']

        if pnl is None:
            icon = '📌'
            pnl_str = '—'
        elif pnl >= 3:
            icon    = '🟢'
            pnl_str = _esc(_pct(pnl))
        elif pnl >= 0:
            icon    = '🟡'
            pnl_str = _esc(_pct(pnl))
        elif pnl >= -2:
            icon    = '⚠️'
            pnl_str = _esc(_pct(pnl))
        else:
            icon    = '🔴'
            pnl_str = _esc(_pct(pnl))

        # Pad name for alignment
        sym_padded = _esc(
            e['sym'].ljust(12))

        lines.append(
            f'{icon} {sym_padded}  '
            f'{_p_esc(e["ltp"])}  '
            f'{pnl_str}')

    lines.append('')
    lines.append(
        'Sell at open\\. '
        'Do not wait\\. '
        'Do not chase close\\.')

    send_message('\n'.join(lines))


# ── 5. EOD SUMMARY ────────────────────────────────────
def send_eod_summary(outcomes: list,
                     still_open: int):
    """
    Design: signal type + outcome + P&L per resolved.
    Win/loss/flat count at bottom.
    Always sends — even if 0 resolved.
    """
    from datetime import date

    today    = date.today().strftime('%Y\\-%m\\-%d')
    resolved = [
        o for o in outcomes
        if o.get('outcome') and
        o.get('outcome') != 'OPEN'
    ]

    lines = []
    lines.append(
        f'📊 *EOD · {today}*')
    lines.append('')

    if not resolved:
        lines.append(
            f'Resolved: 0    '
            f'Open: {_esc(str(still_open))}')
        lines.append('')
        lines.append(
            'No signals closed today\\.')

        # Find next exit date
        next_exit = _find_next_exit(outcomes)
        if next_exit:
            lines.append(
                f'Next exits: {_esc(next_exit)}')

        send_message('\n'.join(lines))
        return

    # Sort: targets first, then wins, then flat, then stops
    def _sort_key(o):
        out = (o.get('outcome') or '').upper()
        if 'TARGET' in out: return 0
        if 'WIN'    in out: return 1
        if 'FLAT'   in out: return 2
        if 'LOSS'   in out: return 3
        if 'STOP'   in out: return 4
        return 5

    resolved.sort(key=_sort_key)

    lines.append(
        f'Resolved: {_esc(str(len(resolved)))}    '
        f'Open: {_esc(str(still_open))}')
    lines.append('')

    wins   = 0
    losses = 0
    flats  = 0

    for o in resolved:
        sym     = (o.get('symbol') or '?') \
                  .replace('.NS', '')
        stype   = (o.get('signal') or '?')
        outcome = (o.get('outcome') or '?')
        pnl     = o.get('pnl_pct')
        emoji   = _outcome_emoji(outcome)

        out = outcome.upper()
        if 'TARGET' in out or 'WIN' in out:
            wins += 1
        elif 'STOP' in out or 'LOSS' in out:
            losses += 1
        else:
            flats += 1

        pnl_str = ''
        if pnl is not None:
            try:
                pnl_str = f'  {_esc(_pct(pnl))}'
            except Exception:
                pass

        outcome_label = outcome.replace(
            '_', '\\_')

        lines.append(
            f'{emoji} '
            f'*{_esc(sym)}*  '
            f'{_esc(stype)}  '
            f'{outcome_label}'
            f'{pnl_str}')

    lines.append('')
    lines.append(
        f'W:{_esc(str(wins))}  '
        f'L:{_esc(str(losses))}  '
        f'F:{_esc(str(flats))}')

    next_exit = _find_next_exit(outcomes)
    if next_exit:
        lines.append(
            f'Next exits: {_esc(next_exit)}')

    send_message('\n'.join(lines))


# ── NEXT EXIT DATE HELPER ─────────────────────────────
def _find_next_exit(outcomes):
    """Find the nearest future exit_date from open signals."""
    from datetime import date
    today     = date.today().isoformat()
    dates     = []
    for o in outcomes:
        ed = o.get('exit_date', '')
        if ed and ed > today:
            dates.append(ed)
    if not dates:
        return None
    nearest = min(dates)
    try:
        from datetime import datetime
        d = datetime.strptime(nearest, '%Y-%m-%d')
        return d.strftime('%b %d')
    except Exception:
        return nearest


# ── TEST ──────────────────────────────────────────────
if __name__ == '__main__':
    send_message(
        '✅ *TIE TIY* — Telegram test OK\\.')
