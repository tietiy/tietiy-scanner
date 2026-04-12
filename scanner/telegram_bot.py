# scanner/telegram_bot.py
# All Telegram message formatting and sending
#
# Message designs:
# 1. Morning scan   — spoiler price details, stock regime visible
# 2. Open validate  — gap focused, silent if all OK
# 3. Stop alert     — compact, urgent
# 4. Exit tomorrow  — entry + ltp + % vs entry
# 5. EOD summary    — signal type + outcome + P&L
# 6. Heartbeat      — daily alive signal + workflow status
# 7. Workflow fail  — alert on GitHub Action failure
# 8. Weekend summary — weekly recap
#
# V1 FIXES APPLIED:
# - R2  : Telegram command handler (/status /signals /stats)
# - R4  : Inline keyboard on morning scan (URL button)
# - M11 : /health command — system health detail
#
# PRIOR FIXES RETAINED:
# D1: send_morning_scan reads active_signals_count from meta
# B1: send_exit_tomorrow accepts exit_today flag
# Q2: send_message retry + exponential backoff
# Q3: send_heartbeat shows workflow status
# Q4: send_message auto-chunks > 4000 chars
# ─────────────────────────────────────────────────────

import os
import re
import time
import requests
from datetime import date, datetime, timezone

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8493010921')

PWA_URL = 'https://tietiy.github.io/tietiy-scanner/'

# ── CORE SEND WITH RETRY + CHUNKING ───────────────────
def send_message(text: str,
                 max_retries: int = 3,
                 reply_markup: dict = None) -> bool:
    """
    Send Telegram message with retry, backoff, auto-chunking.
    reply_markup only sent with first chunk (for inline keyboards).
    """
    if not TELEGRAM_TOKEN:
        print('[telegram] No TELEGRAM_TOKEN — skipping')
        return False

    MAX_LENGTH = 4000

    if len(text) <= MAX_LENGTH:
        return _send_single_message(
            text, max_retries, reply_markup=reply_markup)

    chunks = _split_message(text, MAX_LENGTH)
    print(f'[telegram] Message too long ({len(text)} chars), '
          f'splitting into {len(chunks)} chunks')

    success = True
    for i, chunk in enumerate(chunks):
        print(f'[telegram] Sending chunk {i+1}/{len(chunks)} '
              f'({len(chunk)} chars)')
        # only attach reply_markup to last chunk so button
        # appears at the bottom of the full message
        rm = reply_markup if i == len(chunks) - 1 else None
        if not _send_single_message(chunk, max_retries,
                                    reply_markup=rm):
            success = False
        if i < len(chunks) - 1:
            time.sleep(1)

    return success


def _split_message(text: str, max_length: int) -> list:
    if len(text) <= max_length:
        return [text]

    chunks  = []
    current = ''

    for line in text.split('\n'):
        if len(line) > max_length:
            if current:
                chunks.append(current.rstrip('\n'))
                current = ''
            for i in range(0, len(line), max_length - 10):
                chunks.append(line[i:i + max_length - 10])
            continue

        if len(current) + len(line) + 1 > max_length:
            chunks.append(current.rstrip('\n'))
            current = line + '\n'
        else:
            current += line + '\n'

    if current.strip():
        chunks.append(current.rstrip('\n'))

    return chunks


def _send_single_message(text: str,
                         max_retries: int = 3,
                         reply_markup: dict = None) -> bool:
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/sendMessage')

    for attempt in range(max_retries):
        try:
            payload = {
                'chat_id':                  TELEGRAM_CHAT_ID,
                'text':                     text,
                'parse_mode':               'MarkdownV2',
                'disable_web_page_preview': True,
            }
            if reply_markup:
                payload['reply_markup'] = reply_markup

            r = requests.post(url, json=payload, timeout=15)

            if r.status_code == 200:
                print(f'[telegram] Sent OK (attempt {attempt+1})')
                return True

            if r.status_code == 429:
                retry_after = r.json().get(
                    'parameters', {}).get('retry_after', 5)
                print(f'[telegram] Rate limited, '
                      f'waiting {retry_after}s')
                time.sleep(retry_after)
                continue

            print(f'[telegram] Attempt {attempt+1} failed: '
                  f'{r.status_code} {r.text[:100]}')

        except requests.exceptions.Timeout:
            print(f'[telegram] Attempt {attempt+1} timeout')
        except Exception as e:
            print(f'[telegram] Attempt {attempt+1} error: {e}')

        if attempt < max_retries - 1:
            delay = 2 ** (attempt + 1)
            print(f'[telegram] Retrying in {delay}s...')
            time.sleep(delay)

    # plain-text fallback (no reply_markup)
    print('[telegram] MarkdownV2 failed, trying plain text fallback')
    try:
        plain = _strip_markdown(text)
        payload = {
            'chat_id':                  TELEGRAM_CHAT_ID,
            'text':                     plain,
            'disable_web_page_preview': True,
        }
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            print('[telegram] Sent OK (plain fallback)')
            return True
        print(f'[telegram] Plain fallback failed: {r.status_code}')
        return False
    except Exception as e:
        print(f'[telegram] Plain fallback error: {e}')
        return False


def _reply_message(chat_id, text: str) -> bool:
    """
    Send reply to a specific chat_id (for command responses).
    Always plain text — simpler, no markdown escaping needed.
    """
    if not TELEGRAM_TOKEN:
        return False
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/sendMessage')
    try:
        r = requests.post(url, json={
            'chat_id':                  chat_id,
            'text':                     text,
            'disable_web_page_preview': True,
        }, timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f'[telegram] Reply error: {e}')
        return False


def _strip_markdown(text):
    text = re.sub(r'\|\|(.+?)\|\|', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 \2', text)
    text = re.sub(r'\\(.)', r'\1', text)
    return text


# ── MARKDOWNV2 HELPERS ────────────────────────────────
def _esc(text):
    if text is None:
        return '—'
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


def _spoiler(text):
    return f'||{text}||'


def _link(display, url):
    return f'[{display}]({url})'


# ── R4: INLINE KEYBOARD BUILDER ───────────────────────
def _pwa_keyboard():
    """
    Inline keyboard with single URL button to PWA.
    Attached to morning scan message.
    """
    return {
        'inline_keyboard': [[
            {
                'text': '📱 Open TIE TIY',
                'url':  PWA_URL,
            }
        ]]
    }


# ── PRICE FORMATTERS ──────────────────────────────────
def _p(val):
    try:
        f = float(val)
        if f <= 0:
            return '—'
        if f >= 10000:
            return f'₹{f:,.0f}'
        if f >= 1000:
            return f'₹{f:,.2f}'
        return f'₹{f:.2f}'
    except Exception:
        return '—'


def _p_esc(val):
    return _esc(_p(val))


def _pct_str(val):
    try:
        f    = float(val)
        sign = '+' if f >= 0 else ''
        return f'{sign}{f:.1f}%'
    except Exception:
        return '—'


def _rr_calc(entry, stop, target, direction='LONG'):
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
        return f'{reward / risk:.1f}x'
    except Exception:
        return None


def _resolve(sig, *fields):
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
    if 'TARGET' in o: return '🎯'
    if 'STOP'   in o: return '🛑'
    if 'WIN'    in o: return '✅'
    if 'LOSS'   in o: return '🔴'
    if 'FLAT'   in o: return '〰️'
    return '📌'


def _stock_regime_tag(sig):
    sr = sig.get('stock_regime', '')
    if not sr:
        return ''
    return f'stk:{sr}'


# ── R2 + M11: COMMAND HANDLER ─────────────────────────
# Architecture: poll_and_respond() is called from a cron
# workflow (or piggybacked onto morning_scan workflow).
# Uses 30-minute time window — no offset file needed.
# Supported commands: /status /signals /health /stats
# ──────────────────────────────────────────────────────

def poll_and_respond(meta: dict,
                     history: list,
                     window_minutes: int = 30) -> int:
    """
    Poll Telegram for recent commands and respond.
    Only processes commands from last `window_minutes`.
    Returns count of commands processed.

    Call from workflow after morning scan:
        from telegram_bot import poll_and_respond
        poll_and_respond(meta, history)
    """
    if not TELEGRAM_TOKEN:
        print('[telegram] No token — skipping command poll')
        return 0

    updates = _get_updates()
    if not updates:
        return 0

    now_ts    = time.time()
    cutoff_ts = now_ts - (window_minutes * 60)
    processed = 0

    for update in updates:
        msg = update.get('message', {})
        if not msg:
            continue

        msg_ts = msg.get('date', 0)
        if msg_ts < cutoff_ts:
            continue

        text    = (msg.get('text') or '').strip()
        chat_id = msg.get('chat', {}).get('id')

        if not text.startswith('/') or not chat_id:
            continue

        # strip bot mention e.g. /status@mybot
        cmd = text.split('@')[0].split()[0].lower()

        print(f'[telegram] Command: {cmd} '
              f'from chat {chat_id}')

        if cmd == '/status':
            _respond_status(chat_id, meta)
            processed += 1
        elif cmd == '/signals':
            _respond_signals(chat_id, history)
            processed += 1
        elif cmd == '/stats':
            _respond_stats(chat_id, history)
            processed += 1
        elif cmd == '/health':
            _respond_health(chat_id, meta)
            processed += 1
        elif cmd == '/help':
            _respond_help(chat_id)
            processed += 1

    print(f'[telegram] Commands processed: {processed}')
    return processed


def _get_updates() -> list:
    """Fetch recent updates from Telegram."""
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/getUpdates')
    try:
        r = requests.get(url, params={
            'limit':   50,
            'timeout': 5,
        }, timeout=10)
        if r.status_code == 200:
            return r.json().get('result', [])
        print(f'[telegram] getUpdates failed: {r.status_code}')
        return []
    except Exception as e:
        print(f'[telegram] getUpdates error: {e}')
        return []


# ── R2: /status ───────────────────────────────────────
def _respond_status(chat_id, meta: dict):
    regime      = meta.get('regime', '—')
    active      = meta.get('active_signals_count', 0)
    market_date = meta.get('market_date', '—')
    scan_time   = meta.get('scan_time', '—')
    is_trading  = meta.get('is_trading_day', True)

    try:
        d = datetime.strptime(market_date, '%Y-%m-%d')
        date_fmt = d.strftime('%b %d')
    except Exception:
        date_fmt = market_date

    status_str = 'Trading day' if is_trading else 'Market closed'

    lines = [
        '📊 TIE TIY STATUS',
        '',
        f'Regime    : {regime}',
        f'Active    : {active} signals',
        f'Last scan : {date_fmt} at {scan_time}',
        f'Today     : {status_str}',
        '',
        PWA_URL,
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── R2: /signals ──────────────────────────────────────
def _respond_signals(chat_id, history: list):
    from calendar_utils import get_day_number  # noqa
    # graceful fallback if calendar_utils unavailable
    try:
        _day_fn = get_day_number
    except Exception:
        _day_fn = None

    DONE = {'TARGET_HIT', 'STOP_HIT',
            'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT'}

    open_sigs = [
        s for s in history
        if s.get('layer') == 'MINI'
        and s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in DONE
        and (s.get('generation', 1) or 1) >= 1
    ]

    if not open_sigs:
        _reply_message(chat_id,
            'No open signals right now.')
        return

    open_sigs.sort(
        key=lambda x: float(x.get('score', 0) or 0),
        reverse=True)

    lines = [
        f'📌 OPEN SIGNALS ({len(open_sigs)})',
        '',
    ]

    for s in open_sigs:
        sym   = (s.get('symbol') or '?') \
                .replace('.NS', '')
        stype = s.get('signal', '?')
        score = s.get('score', 0)
        emoji = _sig_emoji(stype)

        day_str = ''
        if _day_fn and s.get('date'):
            try:
                dn = _day_fn(s['date'])
                day_str = f' · Day {dn}/6'
                if dn >= 6:
                    day_str += ' ⚠️'
            except Exception:
                pass

        lines.append(
            f'{emoji} {sym}  {stype}  '
            f'{score}/10{day_str}')

    lines.append('')
    lines.append(PWA_URL)
    _reply_message(chat_id, '\n'.join(lines))


# ── R2: /stats ────────────────────────────────────────
def _respond_stats(chat_id, history: list):
    DONE = {'TARGET_HIT', 'STOP_HIT',
            'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT'}
    WIN  = {'TARGET_HIT', 'DAY6_WIN'}
    LOSS = {'STOP_HIT', 'DAY6_LOSS'}

    live = [
        s for s in history
        if s.get('layer') == 'MINI'
        and s.get('action') == 'TOOK'
        and (s.get('generation', 1) or 1) >= 1
    ]

    resolved = [s for s in live
                if (s.get('outcome') or '') in DONE]
    wins     = [s for s in resolved
                if s.get('outcome') in WIN]
    losses   = [s for s in resolved
                if s.get('outcome') in LOSS]
    open_n   = len(live) - len(resolved)

    wr_str = '—'
    if len(resolved) >= 5:
        wr = round(len(wins) / len(resolved) * 100)
        wr_str = f'{wr}%'
    elif resolved:
        wr_str = f'({len(resolved)} resolved, need 5+)'

    lines = [
        '📈 QUICK STATS',
        '',
        f'Live signals : {len(live)}',
        f'Open now     : {open_n}',
        f'Resolved     : {len(resolved)}',
        f'  Wins       : {len(wins)}',
        f'  Losses     : {len(losses)}',
        f'Win rate     : {wr_str}',
        '',
        'Full stats → ' + PWA_URL,
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── M11: /health ──────────────────────────────────────
def _respond_health(chat_id, meta: dict):
    scan_time   = meta.get('scan_time', '—')
    ltp_time    = meta.get('ltp_updated_at', '—')
    market_date = meta.get('market_date', '—')
    active      = meta.get('active_signals_count', 0)
    wf_status   = meta.get('workflow_status', '—')
    regime      = meta.get('regime', '—')
    schema_ver  = meta.get('schema_version', '—')

    # LTP freshness check
    ltp_age_str = '—'
    if ltp_time and ltp_time != '—':
        try:
            # expects HH:MM format
            now  = datetime.now()
            ltp_dt = datetime.strptime(
                f'{now.date()} {ltp_time}', '%Y-%m-%d %H:%M')
            age_min = int((now - ltp_dt).total_seconds() / 60)
            if age_min < 0:
                ltp_age_str = ltp_time
            elif age_min < 10:
                ltp_age_str = f'{ltp_time} (fresh)'
            elif age_min < 30:
                ltp_age_str = f'{ltp_time} ({age_min}m ago)'
            else:
                ltp_age_str = f'{ltp_time} ⚠️ {age_min}m ago'
        except Exception:
            ltp_age_str = ltp_time

    try:
        d = datetime.strptime(market_date, '%Y-%m-%d')
        date_fmt = d.strftime('%b %d')
    except Exception:
        date_fmt = market_date

    lines = [
        '🏥 SYSTEM HEALTH',
        '',
        f'Last scan  : {date_fmt} at {scan_time}',
        f'LTP update : {ltp_age_str}',
        f'Active     : {active} signals',
        f'Regime     : {regime}',
        f'Schema     : v{schema_ver}',
        f'Workflows  : {wf_status}',
        '',
        'All systems nominal ✅' if wf_status not in
            ('FAILED', 'ERROR', '') else
        '⚠️ Check workflows — possible issue',
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── /help ─────────────────────────────────────────────
def _respond_help(chat_id):
    lines = [
        '🤖 TIE TIY BOT COMMANDS',
        '',
        '/status  — regime + active count + last scan',
        '/signals — all open signals with day count',
        '/stats   — resolved count + win rate',
        '/health  — system health + LTP freshness',
        '/help    — this message',
        '',
        PWA_URL,
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── 1. MORNING SCAN ───────────────────────────────────
def send_morning_scan(signals: list, meta: dict):
    """
    Compact visible line per signal showing stock regime.
    Price details hidden in spoiler.
    Sorted by score descending.
    R4: inline keyboard with PWA link attached.
    """
    date_str     = meta.get('market_date', 'today')
    regime       = meta.get('regime', '')
    active_count = meta.get('active_signals_count', 0)
    new_count    = len(signals)
    scan_time    = meta.get('scan_time', '')
    ltp_time     = meta.get('ltp_updated_at', '')

    sorted_sigs = sorted(
        signals,
        key=lambda x: float(x.get('score', 0) or 0),
        reverse=True)

    lines = []
    lines.append(
        f'🔔 *{_esc("TIE TIY")} · '
        f'{_esc(date_str)} · '
        f'{_esc(regime)}*')
    lines.append('')
    lines.append(
        f'{_esc(str(new_count))} new signals · '
        f'{_esc(str(active_count))} active')

    timing_parts = []
    if scan_time:
        timing_parts.append(f'Scan {scan_time}')
    if ltp_time:
        timing_parts.append(f'LTP {ltp_time}')
    if timing_parts:
        lines.append(_esc('  ·  '.join(timing_parts)))

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
            target = _resolve(sig,
                'target_price', 'target')
            rr     = _rr_calc(
                entry, stop, target, direction)

            sr_part = (f' · {_esc(sr_tag)}'
                       if sr_tag else '')
            visible = (
                f'{emoji} *{_esc(sym)}* · '
                f'{_esc(stype)} · '
                f'{_esc(str(score))}/10 · '
                f'Age {_esc(str(age))}'
                f'{sr_part}')

            spoiler_parts = []
            if entry:
                spoiler_parts.append(f'Entry {_p(entry)}')
            if stop:
                spoiler_parts.append(f'Stop {_p(stop)}')
            if target:
                spoiler_parts.append(f'Target {_p(target)}')
            if rr:
                spoiler_parts.append(f'R:R {rr}')

            spoiler_text = (' · '.join(spoiler_parts)
                            if spoiler_parts
                            else 'Price data unavailable')

            lines.append(visible)
            lines.append(_spoiler(spoiler_text))
            lines.append('')

    # R4: keyboard instead of plain link
    send_message(
        '\n'.join(lines),
        reply_markup=_pwa_keyboard())


# ── 2. OPEN VALIDATION ────────────────────────────────
def send_open_validation(confirmed: list,
                         rejected: list):
    lines = []
    lines.append('📋 *Open Prices · 9:29 AM*')
    lines.append('')

    all_results = confirmed + rejected

    if not all_results:
        lines.append('No signals entering today\\.')
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
        actual     = _resolve(sig,
            'actual_open', 'open_price')
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
                gap_str = f' gap {float(gap):+.1f}%'
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
            '⚠️ Caution signals — reduced R:R\\.')
    else:
        lines.append(
            'All entries valid\\. Enter at market\\.')

    send_message('\n'.join(lines))


# ── 3. STOP ALERT ─────────────────────────────────────
def send_stop_alert(signal: dict):
    sym   = (signal.get('symbol') or '?') \
            .replace('.NS', '')
    stype = signal.get('signal', '?')
    stop  = _resolve(signal, 'stop')
    price = _resolve(signal,
        'current_price', 'ltp', 'close')
    level      = signal.get('alert_level', 'NEAR')
    check_time = signal.get('check_time', '')

    if level == 'BREACHED':
        icon   = '🚨'
        action = 'Exit immediately at market\\.'
    elif level == 'AT':
        icon   = '🔴'
        action = ('At stop level\\. '
                  'Exit if next tick goes against\\.')
    else:
        icon   = '⚠️'
        action = 'Watch closely\\.'

    lines = []
    lines.append(
        f'{icon} *STOP ALERT · {_esc(check_time)}*')
    lines.append('')
    lines.append(f'*{_esc(sym)}* · {_esc(stype)}')
    lines.append(
        f'Price {_p_esc(price)}  '
        f'Stop {_p_esc(stop)}  '
        f'*{_esc(level)}*')
    lines.append('')
    lines.append(action)
    lines.append(
        'Rule: stop hit intraday \\= exit same day\\.')

    send_message('\n'.join(lines))


# ── 4. EXIT TOMORROW / EXIT TODAY ─────────────────────
def send_exit_tomorrow(signals: list,
                       exit_today: bool = False):
    if not signals:
        return

    header_label = (
        'EXIT TODAY — Sell at 9:15 AM Open'
        if exit_today
        else 'EXIT TOMORROW — Day 6 Open'
    )
    header_icon = '🚨' if exit_today else '⏰'

    lines = []
    lines.append(
        f'{header_icon} *{_esc(header_label)}*')
    lines.append(
        f'{_esc(str(len(signals)))} signals · '
        f'Sell at 9:15 AM open\\. No extensions\\.')
    lines.append('')

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
        ltp   = _resolve(sig,
            'ltp', 'close', 'current_price')

        pnl_pct = None
        if entry and ltp:
            try:
                raw     = (ltp - entry) / entry * 100
                pnl_pct = (raw if direction == 'LONG'
                           else -raw)
            except Exception:
                pass

        enriched.append({
            'sym':       sym,
            'stype':     stype,
            'entry':     entry,
            'ltp':       ltp,
            'pnl_pct':   pnl_pct,
            'direction': direction,
        })

    enriched.sort(
        key=lambda x: float(x['pnl_pct'] or 0))

    for e in enriched:
        pnl = e['pnl_pct']

        if pnl is None:
            icon    = '📌'
            pnl_str = _esc('—')
        elif pnl >= 3:
            icon    = '🟢'
            pnl_str = _esc(_pct_str(pnl))
        elif pnl >= 0:
            icon    = '🟡'
            pnl_str = _esc(_pct_str(pnl))
        elif pnl >= -2:
            icon    = '⚠️'
            pnl_str = _esc(_pct_str(pnl))
        else:
            icon    = '🔴'
            pnl_str = _esc(_pct_str(pnl))

        lines.append(
            f'{icon} *{_esc(e["sym"])}*  '
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
    today_str = date.today().strftime('%Y-%m-%d')

    resolved = [
        o for o in outcomes
        if o.get('outcome')
        and o.get('outcome') not in ('OPEN', None)
        and o.get('result') != 'REJECTED'
        and o.get('action') == 'TOOK'
    ]

    lines = []
    lines.append(f'📊 *EOD · {_esc(today_str)}*')
    lines.append('')

    if not resolved:
        lines.append(
            f'Resolved: 0    '
            f'Open: {_esc(str(still_open))}')
        lines.append('')
        lines.append('No signals closed today\\.')

        next_exit = _find_next_exit(outcomes)
        if next_exit:
            lines.append(
                f'Next exits: {_esc(next_exit)}')

        send_message('\n'.join(lines))
        return

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

    wins = losses = flats = 0

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
                pnl_str = f'  {_esc(_pct_str(pnl))}'
            except Exception:
                pass

        outcome_esc = _esc(outcome.replace('_', ' '))
        lines.append(
            f'{emoji} *{_esc(sym)}*  '
            f'{_esc(stype)}  '
            f'{outcome_esc}'
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
    today = date.today().isoformat()
    dates = [
        o.get('exit_date', '')
        for o in outcomes
        if o.get('exit_date', '') > today
        and o.get('result') == 'PENDING'
        and o.get('action') == 'TOOK'
    ]
    if not dates:
        return None
    nearest = min(dates)
    try:
        d = datetime.strptime(nearest, '%Y-%m-%d')
        return d.strftime('%b %d')
    except Exception:
        return nearest


# ── 6. HEARTBEAT ──────────────────────────────────────
def send_heartbeat(meta: dict):
    today_str = date.today().strftime('%Y-%m-%d')
    now_time  = datetime.now().strftime('%I:%M %p')

    regime     = meta.get('regime', '—')
    active     = meta.get('active_signals_count', 0)
    last_date  = meta.get('market_date', '—')
    last_found = meta.get('signals_found', 0)
    is_trading = meta.get('is_trading_day', True)
    wf_status  = meta.get('workflow_status', '')

    try:
        d = datetime.strptime(last_date, '%Y-%m-%d')
        last_date_fmt = d.strftime('%b %d')
    except Exception:
        last_date_fmt = last_date

    lines = []
    lines.append(
        f'💓 *{_esc("TIE TIY")} · '
        f'{_esc(today_str)} · '
        f'{_esc(now_time)}*')
    lines.append('')
    lines.append('System: ✅ Online')
    lines.append(f'Regime: {_esc(regime)}')
    lines.append(f'Active: {_esc(str(active))} signals')

    if is_trading:
        lines.append('Next scan: 8:45 AM')
    else:
        lines.append('Today: Market closed')

    lines.append('')
    lines.append(
        f'Last scan: {_esc(last_date_fmt)} · '
        f'{_esc(str(last_found))} signals')

    if wf_status:
        lines.append(f'Workflows: {wf_status}')

    send_message('\n'.join(lines))


# ── 7. WORKFLOW FAILURE ALERT ─────────────────────────
def send_workflow_failure(workflow_name: str,
                          run_url: str = None):
    today_str = date.today().strftime('%Y-%m-%d')
    now_time  = datetime.now().strftime('%I:%M %p')

    lines = []
    lines.append('🚨 *WORKFLOW FAILED*')
    lines.append('')
    lines.append(f'*{_esc(workflow_name)}*')
    lines.append(f'{_esc(today_str)} · {_esc(now_time)}')
    lines.append('')
    lines.append('Check GitHub Actions immediately\\.')

    if run_url:
        lines.append('')
        lines.append(
            _link('View logs',
                  run_url.replace('.', '\\.')
                         .replace('-', '\\-')))

    send_message('\n'.join(lines))


# ── 8. WEEKEND SUMMARY ────────────────────────────────
def send_weekend_summary(stats: dict):
    today_str  = date.today().strftime('%Y-%m-%d')

    resolved   = stats.get('resolved', 0)
    wins       = stats.get('wins', 0)
    losses     = stats.get('losses', 0)
    flats      = stats.get('flats', 0)
    win_rate   = stats.get('win_rate', 0)
    active     = stats.get('active', 0)
    next_exits = stats.get('next_exits', [])
    top_winner = stats.get('top_winner', None)
    top_loser  = stats.get('top_loser', None)

    lines = []
    lines.append(
        f'📅 *WEEKLY RECAP · {_esc(today_str)}*')
    lines.append('')

    if resolved == 0:
        lines.append('No signals resolved this week\\.')
    else:
        lines.append(f'Resolved: {_esc(str(resolved))}')
        lines.append(
            f'W:{_esc(str(wins))} '
            f'L:{_esc(str(losses))} '
            f'F:{_esc(str(flats))}')
        lines.append(
            f'Win Rate: {_esc(str(win_rate))}%')

    lines.append('')
    lines.append(f'Active: {_esc(str(active))} signals')

    if next_exits:
        exits_str = ', '.join(next_exits[:3])
        lines.append(
            f'Next exits: {_esc(exits_str)}')

    if top_winner:
        sym = top_winner.get('symbol', '') \
                        .replace('.NS', '')
        pnl = top_winner.get('pnl_pct', 0)
        lines.append('')
        lines.append(
            f'🏆 Top: {_esc(sym)} '
            f'{_esc(f"+{pnl:.1f}%")}')

    if top_loser:
        sym = top_loser.get('symbol', '') \
                       .replace('.NS', '')
        pnl = top_loser.get('pnl_pct', 0)
        lines.append(
            f'📉 Worst: {_esc(sym)} '
            f'{_esc(f"{pnl:.1f}%")}')

    lines.append('')
    lines.append('Good trading next week\\! 📈')

    send_message('\n'.join(lines))


# ── TEST ──────────────────────────────────────────────
if __name__ == '__main__':
    send_message('✅ *TIE TIY* — Telegram test OK\\.')
