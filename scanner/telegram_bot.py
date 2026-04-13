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
# V1.1 FIXES:
# - HC1/HC2/HC3: _to_ist() converts all UTC timestamps
#   to IST (UTC+5:30) before display in Telegram.
# - MC2: send_exit_tomorrow deduplicates same stock
# - MC3: send_open_validation deduplicates same stock
# - TG1: /today command — morning brief
# - TG2: /exits command — today + tomorrow exits
# - TG3: /stops command — stop proximity from LTP
# - TG4: /pnl command — unrealized P&L on open positions
# - poll_and_respond() accepts ltp_prices param
# - W1/TR5: send_weekend_summary now shows phase_note,
#   type_counts breakdown, week date range
# - BX1: _find_next_exit crash when exit_date is None
#   fixed — None guarded with or ''
# - TG6: _get_updates now tracks offset in
#   output/tg_offset.json — commands never missed
#   across cron cycles
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
import json
import time
import requests
from datetime import date, datetime, timezone, timedelta

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get(
    'TELEGRAM_CHAT_ID', '8493010921')

PWA_URL = 'https://tietiy.github.io/tietiy-scanner/'


# ── HC1/HC2/HC3: UTC → IST CONVERTER ─────────────────
def _to_ist(time_str: str) -> str:
    if not time_str or str(time_str).strip() in (
            '—', '', 'None', 'none'):
        return '—'

    time_str = str(time_str).strip()

    try:
        if re.match(r'^\d{1,2}:\d{2}:\d{2}$', time_str):
            parts = time_str.split(':')
            h, m = int(parts[0]), int(parts[1])
        elif re.match(r'^\d{1,2}:\d{2}$', time_str):
            h, m = map(int, time_str.split(':'))
        else:
            return time_str

        total = h * 60 + m + 330
        ist_h = (total // 60) % 24
        ist_m = total % 60

        period  = 'AM' if ist_h < 12 else 'PM'
        disp_h  = ist_h % 12 or 12
        return f'{disp_h}:{ist_m:02d} {period} IST'

    except Exception:
        return time_str


def _to_ist_safe(time_str: str) -> str:
    try:
        return _to_ist(time_str)
    except Exception:
        return str(time_str or '—')


# ── CORE SEND WITH RETRY + CHUNKING ───────────────────
def send_message(text: str,
                 max_retries: int = 3,
                 reply_markup: dict = None) -> bool:
    if not TELEGRAM_TOKEN:
        print('[telegram] No TELEGRAM_TOKEN — skipping')
        return False

    MAX_LENGTH = 4000

    if len(text) <= MAX_LENGTH:
        return _send_single_message(
            text, max_retries,
            reply_markup=reply_markup)

    chunks = _split_message(text, MAX_LENGTH)
    print(f'[telegram] Message too long '
          f'({len(text)} chars), '
          f'splitting into {len(chunks)} chunks')

    success = True
    for i, chunk in enumerate(chunks):
        print(f'[telegram] Sending chunk '
              f'{i+1}/{len(chunks)} '
              f'({len(chunk)} chars)')
        rm = (reply_markup
              if i == len(chunks) - 1 else None)
        if not _send_single_message(
                chunk, max_retries, reply_markup=rm):
            success = False
        if i < len(chunks) - 1:
            time.sleep(1)

    return success


def _split_message(text: str,
                   max_length: int) -> list:
    if len(text) <= max_length:
        return [text]

    chunks  = []
    current = ''

    for line in text.split('\n'):
        if len(line) > max_length:
            if current:
                chunks.append(current.rstrip('\n'))
                current = ''
            for i in range(
                    0, len(line), max_length - 10):
                chunks.append(
                    line[i:i + max_length - 10])
            continue

        if len(current) + len(line) + 1 > max_length:
            chunks.append(current.rstrip('\n'))
            current = line + '\n'
        else:
            current += line + '\n'

    if current.strip():
        chunks.append(current.rstrip('\n'))

    return chunks


def _send_single_message(
        text: str,
        max_retries: int = 3,
        reply_markup: dict = None) -> bool:

    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/sendMessage')

    for attempt in range(max_retries):
        try:
            payload = {
                'chat_id':    TELEGRAM_CHAT_ID,
                'text':       text,
                'parse_mode': 'MarkdownV2',
                'disable_web_page_preview': True,
            }
            if reply_markup:
                payload['reply_markup'] = reply_markup

            r = requests.post(
                url, json=payload, timeout=15)

            if r.status_code == 200:
                print(f'[telegram] Sent OK '
                      f'(attempt {attempt+1})')
                return True

            if r.status_code == 429:
                retry_after = r.json().get(
                    'parameters', {}
                ).get('retry_after', 5)
                print(f'[telegram] Rate limited, '
                      f'waiting {retry_after}s')
                time.sleep(retry_after)
                continue

            print(f'[telegram] Attempt {attempt+1} '
                  f'failed: {r.status_code} '
                  f'{r.text[:100]}')

        except requests.exceptions.Timeout:
            print(f'[telegram] Attempt '
                  f'{attempt+1} timeout')
        except Exception as e:
            print(f'[telegram] Attempt '
                  f'{attempt+1} error: {e}')

        if attempt < max_retries - 1:
            delay = 2 ** (attempt + 1)
            print(f'[telegram] Retrying in {delay}s...')
            time.sleep(delay)

    print('[telegram] MarkdownV2 failed, '
          'trying plain text fallback')
    try:
        plain   = _strip_markdown(text)
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text':    plain,
            'disable_web_page_preview': True,
        }
        r = requests.post(
            url, json=payload, timeout=15)
        if r.status_code == 200:
            print('[telegram] Sent OK (plain fallback)')
            return True
        print(f'[telegram] Plain fallback failed: '
              f'{r.status_code}')
        return False
    except Exception as e:
        print(f'[telegram] Plain fallback error: {e}')
        return False


def _reply_message(chat_id, text: str) -> bool:
    if not TELEGRAM_TOKEN:
        return False
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/sendMessage')
    try:
        r = requests.post(url, json={
            'chat_id': chat_id,
            'text':    text,
            'disable_web_page_preview': True,
        }, timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f'[telegram] Reply error: {e}')
        return False


def _strip_markdown(text):
    text = re.sub(
        r'\|\|(.+?)\|\|', r'\1',
        text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = re.sub(
        r'\[(.+?)\]\((.+?)\)', r'\1 \2', text)
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


# ── R4: INLINE KEYBOARD ───────────────────────────────
def _pwa_keyboard():
    return {
        'inline_keyboard': [[{
            'text': '📱 Open TIE TIY',
            'url':  PWA_URL,
        }]]
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


def _rr_calc(entry, stop, target,
             direction='LONG'):
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


# ── SHARED CONSTANTS ──────────────────────────────────
_DONE = {'TARGET_HIT', 'STOP_HIT',
         'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT'}
_WIN  = {'TARGET_HIT', 'DAY6_WIN'}
_LOSS = {'STOP_HIT', 'DAY6_LOSS'}


# ── COMMAND HANDLER ───────────────────────────────────
def poll_and_respond(meta: dict,
                     history: list,
                     ltp_prices: dict = None,
                     window_minutes: int = 30
                     ) -> int:
    if not TELEGRAM_TOKEN:
        print('[telegram] No token — skipping poll')
        return 0

    updates = _get_updates()
    if not updates:
        return 0

    ltp_prices = ltp_prices or {}
    now_ts     = time.time()
    cutoff_ts  = now_ts - (window_minutes * 60)
    processed  = 0

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

        cmd = text.split('@')[0].split()[0].lower()
        print(f'[telegram] Command: {cmd} '
              f'from chat {chat_id}')

        if cmd == '/status':
            _respond_status(chat_id, meta)
        elif cmd == '/signals':
            _respond_signals(chat_id, history)
        elif cmd == '/stats':
            _respond_stats(chat_id, history)
        elif cmd == '/health':
            _respond_health(chat_id, meta)
        elif cmd == '/today':
            _respond_today(
                chat_id, meta, history, ltp_prices)
        elif cmd == '/exits':
            _respond_exits(chat_id, history, ltp_prices)
        elif cmd == '/stops':
            _respond_stops(chat_id, history, ltp_prices)
        elif cmd == '/pnl':
            _respond_pnl(chat_id, history, ltp_prices)
        elif cmd == '/help':
            _respond_help(chat_id)
        else:
            continue

        processed += 1

    print(f'[telegram] Commands processed: {processed}')
    return processed


# ── TG6: GET UPDATES WITH OFFSET TRACKING ────────────
# Persists last seen update_id in output/tg_offset.json
# so each poll cycle only sees NEW commands.
# Without this, old updates block new commands.
def _get_updates() -> list:
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/getUpdates')

    _root       = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    offset_file = os.path.join(
        _root, 'output', 'tg_offset.json')

    # Read last known offset
    offset = None
    try:
        if os.path.exists(offset_file):
            with open(offset_file, 'r') as f:
                offset = json.load(f).get('offset')
    except Exception:
        pass

    try:
        params = {'limit': 50, 'timeout': 5}
        if offset:
            params['offset'] = offset

        r = requests.get(
            url, params=params, timeout=10)

        if r.status_code == 200:
            updates = r.json().get('result', [])

            # Acknowledge — write next offset
            # so next poll skips already seen updates
            if updates:
                next_offset = (
                    updates[-1]['update_id'] + 1)
                try:
                    with open(
                            offset_file, 'w') as f:
                        json.dump(
                            {'offset': next_offset},
                            f)
                    print(f'[telegram] Offset saved: '
                          f'{next_offset}')
                except Exception as e:
                    print(f'[telegram] Offset save '
                          f'error: {e}')

            return updates

        print(f'[telegram] getUpdates failed: '
              f'{r.status_code}')
        return []
    except Exception as e:
        print(f'[telegram] getUpdates error: {e}')
        return []


# ── /status ───────────────────────────────────────────
def _respond_status(chat_id, meta: dict):
    regime      = meta.get('regime', '—')
    active      = meta.get('active_signals_count', 0)
    market_date = meta.get('market_date', '—')
    scan_time   = meta.get('scan_time', '—')
    is_trading  = meta.get('is_trading_day', True)

    scan_ist = _to_ist_safe(scan_time)

    try:
        d        = datetime.strptime(
            market_date, '%Y-%m-%d')
        date_fmt = d.strftime('%b %d')
    except Exception:
        date_fmt = market_date

    status_str = ('Trading day' if is_trading
                  else 'Market closed')

    lines = [
        '📊 TIE TIY STATUS',
        '',
        f'Regime    : {regime}',
        f'Active    : {active} signals',
        f'Last scan : {date_fmt} at {scan_ist}',
        f'Today     : {status_str}',
        '',
        PWA_URL,
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── /signals ──────────────────────────────────────────
def _respond_signals(chat_id, history: list):
    try:
        from calendar_utils import get_day_number
        _day_fn = get_day_number
    except Exception:
        _day_fn = None

    open_sigs = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and s.get('generation', 1) is not None
        and (s.get('generation') or 0) >= 1
    ]

    if not open_sigs:
        _reply_message(chat_id,
            'No open signals right now.')
        return

    open_sigs.sort(
        key=lambda x: float(
            x.get('score', 0) or 0),
        reverse=True)

    lines = [f'📌 OPEN SIGNALS ({len(open_sigs)})', '']

    for s in open_sigs[:20]:
        sym   = (s.get('symbol') or '?') \
                .replace('.NS', '')
        stype = s.get('signal', '?')
        score = s.get('score', 0)
        emoji = _sig_emoji(stype)

        day_str = ''
        if _day_fn and s.get('date'):
            try:
                dn      = _day_fn(s['date'])
                day_str = f' · Day {dn}/6'
                if dn >= 5:
                    day_str += ' ⚠️'
            except Exception:
                pass

        lines.append(
            f'{emoji} {sym}  {stype}  '
            f'{score}/10{day_str}')

    if len(open_sigs) > 20:
        lines.append(
            f'... +{len(open_sigs)-20} more')

    lines.append('')
    lines.append(PWA_URL)
    _reply_message(chat_id, '\n'.join(lines))


# ── /stats ────────────────────────────────────────────
def _respond_stats(chat_id, history: list):
    live = [
        s for s in history
        if s.get('action') == 'TOOK'
        and s.get('generation') is not None
        and (s.get('generation') or 0) >= 1
    ]

    resolved = [s for s in live
                if (s.get('outcome') or '')
                in _DONE]
    wins     = [s for s in resolved
                if s.get('outcome') in _WIN]
    losses   = [s for s in resolved
                if s.get('outcome') in _LOSS]
    open_n   = len(live) - len(resolved)

    wr_str = '—'
    if len(resolved) >= 5:
        wr     = round(
            len(wins) / len(resolved) * 100)
        wr_str = f'{wr}%'
    elif resolved:
        wr_str = (f'({len(resolved)} resolved, '
                  f'need 5+)')

    lines = [
        '📈 QUICK STATS', '',
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


# ── /health ───────────────────────────────────────────
def _respond_health(chat_id, meta: dict):
    scan_time   = meta.get('scan_time', '—')
    ltp_time    = meta.get('ltp_updated_at', '—')
    market_date = meta.get('market_date', '—')
    active      = meta.get('active_signals_count', 0)
    wf_status   = meta.get('workflow_status', '—')
    regime      = meta.get('regime', '—')
    schema_ver  = meta.get('schema_version', '—')

    scan_ist = _to_ist_safe(scan_time)
    ltp_ist  = _to_ist_safe(ltp_time)

    try:
        d        = datetime.strptime(
            market_date, '%Y-%m-%d')
        date_fmt = d.strftime('%b %d')
    except Exception:
        date_fmt = market_date

    lines = [
        '🏥 SYSTEM HEALTH', '',
        f'Last scan  : {date_fmt} at {scan_ist}',
        f'LTP update : {ltp_ist}',
        f'Active     : {active} signals',
        f'Regime     : {regime}',
        f'Schema     : v{schema_ver}',
        f'Workflows  : {wf_status}',
        '',
        ('All systems nominal ✅'
         if wf_status not in
            ('FAILED', 'ERROR', '')
         else '⚠️ Check workflows'),
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── TG1: /today ───────────────────────────────────────
def _respond_today(chat_id, meta: dict,
                   history: list,
                   ltp_prices: dict):
    regime    = meta.get('regime', '—')
    scan_ist  = _to_ist_safe(
        meta.get('scan_time', ''))
    active    = meta.get('active_signals_count', 0)
    today_str = date.today().strftime('%a %d %b')

    today_iso   = date.today().isoformat()
    exits_today = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and s.get('exit_date', '') == today_iso
    ]

    tomorrow   = (date.today() +
                  timedelta(days=1)).isoformat()
    exits_tmrw = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and s.get('exit_date', '') == tomorrow
    ]

    new_today = [
        s for s in history
        if s.get('date', '') == today_iso
        and (s.get('generation') or 0) >= 1
    ]

    lines = [
        f'📅 TODAY — {today_str}',
        f'Market: {regime}  |  Scan: {scan_ist}',
        '',
    ]

    if exits_today:
        lines.append(
            f'🚨 EXIT TODAY — '
            f'{len(exits_today)} signals')
        lines.append(
            'Sell at 9:15 AM open. No extensions.')

        enriched = _enrich_with_pnl(
            exits_today, ltp_prices)
        enriched.sort(
            key=lambda x: float(
                x.get('pnl_pct') or 0),
            reverse=True)

        for e in enriched[:5]:
            sym = e['sym']
            pnl = e.get('pnl_pct')
            if pnl is None:
                icon = '📌'; pct = '—'
            elif pnl >= 3:
                icon = '🟢'; pct = f'+{pnl:.1f}%'
            elif pnl >= 0:
                icon = '🟡'; pct = f'+{pnl:.1f}%'
            else:
                icon = '🔴'; pct = f'{pnl:.1f}%'
            lines.append(f'  {icon} {sym}  {pct}')

        if len(exits_today) > 5:
            lines.append(
                f'  ... +{len(exits_today)-5} more')
        lines.append('')

    if exits_tmrw:
        syms = ', '.join(
            (s.get('symbol', '?')
             .replace('.NS', ''))
            for s in exits_tmrw[:6])
        lines.append(
            f'⏰ EXIT TOMORROW — '
            f'{len(exits_tmrw)} signals')
        lines.append(syms)
        if len(exits_tmrw) > 6:
            lines.append(
                f'  +{len(exits_tmrw)-6} more')
        lines.append('')

    if new_today:
        lines.append(
            f'🔔 NEW TODAY — '
            f'{len(new_today)} signals')
        new_sorted = sorted(
            new_today,
            key=lambda x: float(
                x.get('score', 0) or 0),
            reverse=True)
        for s in new_sorted[:3]:
            sym   = (s.get('symbol', '?')
                     .replace('.NS', ''))
            score = s.get('score', 0)
            stype = s.get('signal', '?')
            lines.append(
                f'  {_sig_emoji(stype)} '
                f'{sym}  {score}/10')
        if len(new_today) > 3:
            lines.append(
                f'  ... +{len(new_today)-3} more')
        lines.append('')
    else:
        lines.append('No new signals today.')
        lines.append('')

    lines.append(f'Active positions: {active}')
    lines.append(PWA_URL)
    _reply_message(chat_id, '\n'.join(lines))


# ── TG2: /exits ───────────────────────────────────────
def _respond_exits(chat_id, history: list,
                   ltp_prices: dict):
    today_iso = date.today().isoformat()
    tomorrow  = (date.today() +
                 timedelta(days=1)).isoformat()

    exits_today = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and s.get('exit_date', '') == today_iso
    ]
    exits_tmrw = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and s.get('exit_date', '') == tomorrow
    ]

    lines = ['⏰ UPCOMING EXITS', '']

    if exits_today:
        lines.append(
            f'TODAY ({today_iso}) — '
            f'{len(exits_today)} signals')
        lines.append('Sell at 9:15 AM open')

        enriched = _enrich_with_pnl(
            exits_today, ltp_prices)
        enriched.sort(
            key=lambda x: float(
                x.get('pnl_pct') or 0),
            reverse=True)

        for e in enriched:
            pnl  = e.get('pnl_pct')
            icon = ('🟢' if pnl and pnl >= 3
                    else '🟡' if pnl and pnl >= 0
                    else '🔴' if pnl else '📌')
            pct  = (f'{pnl:+.1f}%'
                    if pnl is not None else '—')
            lines.append(
                f'  {icon} {e["sym"]}  {pct}')
        lines.append('')
    else:
        lines.append('No exits today.')
        lines.append('')

    if exits_tmrw:
        lines.append(
            f'TOMORROW ({tomorrow}) — '
            f'{len(exits_tmrw)} signals')

        enriched = _enrich_with_pnl(
            exits_tmrw, ltp_prices)
        enriched.sort(
            key=lambda x: float(
                x.get('pnl_pct') or 0),
            reverse=True)

        for e in enriched[:10]:
            pnl  = e.get('pnl_pct')
            pct  = (f'{pnl:+.1f}%'
                    if pnl is not None else '—')
            icon = ('🟢' if pnl and pnl >= 3
                    else '🟡' if pnl and pnl >= 0
                    else '🔴' if pnl else '📌')
            lines.append(
                f'  {icon} {e["sym"]}  {pct}')

        if len(exits_tmrw) > 10:
            lines.append(
                f'  ... +{len(exits_tmrw)-10} more')
    else:
        lines.append('No exits tomorrow.')

    lines.append('')
    lines.append('Rule: sell at open. No extensions.')
    _reply_message(chat_id, '\n'.join(lines))


# ── TG3: /stops ───────────────────────────────────────
def _respond_stops(chat_id, history: list,
                   ltp_prices: dict):
    ltp_ist = _to_ist_safe(
        ltp_prices.get('ltp_updated_at', ''))
    prices  = ltp_prices.get('prices', {})

    open_sigs = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and (s.get('generation') or 0) >= 1
    ]

    if not open_sigs:
        _reply_message(chat_id,
            'No open signals to check.')
        return

    danger  = []
    caution = []
    safe    = []
    no_data = []

    for s in open_sigs:
        sym   = (s.get('symbol', '?')
                 .replace('.NS', ''))
        sym_k = s.get('symbol', '')
        stop  = _resolve(s, 'stop')
        entry = _resolve(s,
            'actual_open', 'scan_price', 'entry')
        dirn  = s.get('direction', 'LONG')

        ltp = (prices.get(sym_k)
               or prices.get(sym))
        if ltp:
            try:
                ltp = float(ltp)
            except Exception:
                ltp = None

        if not ltp or not stop or not entry:
            no_data.append(sym)
            continue

        stop  = float(stop)
        entry = float(entry)

        if dirn == 'LONG':
            buf_pct = (ltp - stop) / stop * 100
        else:
            buf_pct = (stop - ltp) / stop * 100

        item = {
            'sym': sym, 'ltp': ltp,
            'stop': stop, 'buf_pct': buf_pct,
        }

        if buf_pct < 0:
            danger.append(item)
        elif buf_pct < 2:
            danger.append(item)
        elif buf_pct < 5:
            caution.append(item)
        else:
            safe.append(item)

    ltp_line = (f'LTP as of {ltp_ist}'
                if ltp_ist != '—' else 'LTP data')

    lines = [f'🛑 STOP PROXIMITY', f'{ltp_line}', '']

    if danger:
        lines.append(
            '🚨 DANGER — within 2% of stop:')
        for d in sorted(danger,
                        key=lambda x: x['buf_pct']):
            pct = f"{d['buf_pct']:.1f}%"
            if d['buf_pct'] < 0:
                pct = (f"BREACHED "
                       f"{d['buf_pct']:.1f}%")
            lines.append(
                f"  {d['sym']}  "
                f"LTP {_p(d['ltp'])}  "
                f"Stop {_p(d['stop'])}  ({pct})")
        lines.append('')

    if caution:
        lines.append('⚠️ CAUTION — 2-5% buffer:')
        for d in sorted(caution,
                        key=lambda x: x['buf_pct']):
            lines.append(
                f"  {d['sym']}  "
                f"{d['buf_pct']:.1f}% buffer")
        lines.append('')

    safe_syms = ', '.join(
        d['sym'] for d in safe[:8])
    if safe_syms:
        lines.append(f'✅ SAFE (>5%): {safe_syms}')
        if len(safe) > 8:
            lines.append(
                f'   +{len(safe)-8} more safe')

    if no_data:
        lines.append('')
        lines.append(
            f'No LTP: {", ".join(no_data[:5])}')

    if not danger and not caution:
        lines.append('')
        lines.append(
            'All positions safely above stop.')

    _reply_message(chat_id, '\n'.join(lines))


# ── TG4: /pnl ─────────────────────────────────────────
def _respond_pnl(chat_id, history: list,
                 ltp_prices: dict):
    ltp_ist = _to_ist_safe(
        ltp_prices.get('ltp_updated_at', ''))

    open_sigs = [
        s for s in history
        if s.get('action') == 'TOOK'
        and (s.get('outcome') or '') not in _DONE
        and (s.get('generation') or 0) >= 1
    ]

    if not open_sigs:
        _reply_message(chat_id, 'No open positions.')
        return

    enriched = _enrich_with_pnl(
        open_sigs, ltp_prices)
    enriched_with = [
        e for e in enriched
        if e.get('pnl_pct') is not None]
    no_data = [
        e['sym'] for e in enriched
        if e.get('pnl_pct') is None]

    enriched_with.sort(
        key=lambda x: float(x['pnl_pct']),
        reverse=True)

    ltp_line = (f'Based on LTP {ltp_ist}'
                if ltp_ist != '—'
                else 'Based on last LTP')

    lines = [
        '📊 UNREALIZED P&L',
        f'{ltp_line}',
        f'({len(enriched_with)} positions)',
        '',
    ]

    for e in enriched_with[:15]:
        pnl  = e['pnl_pct']
        icon = ('🟢' if pnl >= 3
                else '🟡' if pnl >= 0 else '🔴')
        lines.append(
            f'{icon} {e["sym"]}  {pnl:+.1f}%')

    if len(enriched_with) > 15:
        lines.append(
            f'... +{len(enriched_with)-15} more')

    if enriched_with:
        avg = (sum(e['pnl_pct']
                   for e in enriched_with)
               / len(enriched_with))
        lines.append('')
        lines.append(f'Avg open P&L: {avg:+.1f}%')
        winners = sum(1 for e in enriched_with
                      if e['pnl_pct'] > 0)
        losers  = sum(1 for e in enriched_with
                      if e['pnl_pct'] < 0)
        lines.append(
            f'Up: {winners}  Down: {losers}')

    if no_data:
        lines.append('')
        lines.append(
            f'No LTP for: '
            f'{", ".join(no_data[:4])}')

    _reply_message(chat_id, '\n'.join(lines))


# ── /help ─────────────────────────────────────────────
def _respond_help(chat_id):
    lines = [
        '🤖 TIE TIY BOT COMMANDS',
        '',
        '/today   — morning brief: exits + new signals',
        '/exits   — who exits today + tomorrow',
        '/pnl     — unrealized P&L on open positions',
        '/stops   — stop proximity check',
        '/signals — all open positions + day count',
        '/stats   — resolved count + win rate',
        '/status  — regime + active + last scan',
        '/health  — system diagnostics',
        '/help    — this message',
        '',
        PWA_URL,
    ]
    _reply_message(chat_id, '\n'.join(lines))


# ── SHARED HELPER: ENRICH WITH PNL ───────────────────
def _enrich_with_pnl(signals: list,
                     ltp_prices: dict) -> list:
    prices = ltp_prices.get('prices', {}) \
             if ltp_prices else {}
    result = []

    for s in signals:
        sym_raw = s.get('symbol', '?')
        sym     = sym_raw.replace('.NS', '')
        dirn    = s.get('direction', 'LONG')

        entry = _resolve(s,
            'actual_open', 'scan_price',
            'entry', 'entry_est')
        ltp   = (prices.get(sym_raw)
                 or prices.get(sym))

        pnl_pct = None
        if entry and ltp:
            try:
                ltp_f   = float(ltp)
                raw     = (ltp_f - entry) \
                          / entry * 100
                pnl_pct = round(
                    raw if dirn == 'LONG'
                    else -raw, 1)
            except Exception:
                pass

        item = dict(s)
        item['sym']     = sym
        item['pnl_pct'] = pnl_pct
        result.append(item)

    return result


# ── 1. MORNING SCAN ───────────────────────────────────
def send_morning_scan(signals: list, meta: dict):
    date_str     = meta.get('market_date', 'today')
    regime       = meta.get('regime', '')
    active_count = meta.get(
        'active_signals_count', 0)
    new_count    = len(signals)
    scan_time    = meta.get('scan_time', '')
    ltp_time     = meta.get('ltp_updated_at', '')

    scan_ist = _to_ist_safe(scan_time)
    ltp_ist  = _to_ist_safe(ltp_time)

    sorted_sigs = sorted(
        signals,
        key=lambda x: float(
            x.get('score', 0) or 0),
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
    if scan_ist and scan_ist != '—':
        timing_parts.append(f'Scan {scan_ist}')
    if ltp_ist and ltp_ist != '—':
        timing_parts.append(f'LTP {ltp_ist}')
    if timing_parts:
        lines.append(
            _esc('  ·  '.join(timing_parts)))

    lines.append('')

    if not sorted_sigs:
        lines.append(
            'No new signals today\\. '
            'Market watching\\.')
    else:
        for sig in sorted_sigs:
            sym    = (sig.get('symbol') or '?') \
                     .replace('.NS', '')
            stype  = sig.get('signal', '?')
            score  = sig.get('score', 0)
            age    = sig.get('age', 0)
            sr_tag = _stock_regime_tag(sig)
            dirn   = sig.get('direction', 'LONG')
            emoji  = _sig_emoji(stype)

            entry  = _resolve(sig,
                'actual_open', 'scan_price',
                'entry', 'entry_est')
            stop   = _resolve(sig, 'stop')
            target = _resolve(sig,
                'target_price', 'target')
            rr     = _rr_calc(
                entry, stop, target, dirn)

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
                spoiler_parts.append(
                    f'Entry {_p(entry)}')
            if stop:
                spoiler_parts.append(
                    f'Stop {_p(stop)}')
            if target:
                spoiler_parts.append(
                    f'Target {_p(target)}')
            if rr:
                spoiler_parts.append(f'R:R {rr}')

            spoiler_text = (
                ' · '.join(spoiler_parts)
                if spoiler_parts
                else 'Price data unavailable')

            lines.append(visible)
            lines.append(_spoiler(spoiler_text))
            lines.append('')

    send_message(
        '\n'.join(lines),
        reply_markup=_pwa_keyboard())


# ── 2. OPEN VALIDATION ────────────────────────────────
def send_open_validation(confirmed: list,
                         rejected: list):
    all_results = confirmed + rejected

    if not all_results:
        lines = ['📋 *Open Prices · 9:29 AM*', '']
        lines.append(
            'No signals entering today\\.')
        send_message('\n'.join(lines))
        return

    STATUS_RANK = {
        'SKIP': 3, 'WARNING': 2, 'OK': 1}
    sym_map = {}
    for sig in all_results:
        sym_raw    = (sig.get('symbol') or '?')
        sym        = sym_raw.replace('.NS', '')
        gap_status = sig.get('gap_status', 'OK')
        rank       = STATUS_RANK.get(gap_status, 1)

        if sym not in sym_map:
            sym_map[sym] = sig
        else:
            existing_rank = STATUS_RANK.get(
                sym_map[sym].get(
                    'gap_status', 'OK'), 1)
            if rank > existing_rank:
                sym_map[sym] = sig

    deduped = list(sym_map.values())
    lines   = ['📋 *Open Prices · 9:29 AM*', '']

    has_skip    = any(
        s.get('gap_status') == 'SKIP'
        for s in deduped)
    has_warning = any(
        s.get('gap_status') == 'WARNING'
        for s in deduped)

    for sig in deduped:
        sym        = (sig.get('symbol') or '?') \
                     .replace('.NS', '')
        actual     = _resolve(sig,
            'actual_open', 'open_price')
        gap        = sig.get('gap_pct')
        gap_status = sig.get('gap_status', 'OK')

        icon = ('❌' if gap_status == 'SKIP'
                else '⚠️'
                if gap_status == 'WARNING'
                else '✅')

        gap_str = ''
        if gap is not None:
            try:
                gap_str = (
                    f' gap {float(gap):+.1f}%')
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
            'All entries valid\\. '
            'Enter at market\\.')

    send_message('\n'.join(lines))


# ── 3. STOP ALERT ─────────────────────────────────────
def send_stop_alert(signal: dict):
    sym        = (signal.get('symbol') or '?') \
                 .replace('.NS', '')
    stype      = signal.get('signal', '?')
    stop       = _resolve(signal, 'stop')
    price      = _resolve(signal,
        'current_price', 'ltp', 'close')
    level      = signal.get('alert_level', 'NEAR')
    check_time = signal.get('check_time', '')

    check_ist = _to_ist_safe(check_time)

    if level == 'BREACHED':
        icon   = '🚨'
        action = 'Exit immediately at market\\.'
    elif level == 'AT':
        icon   = '🔴'
        action = ('At stop level\\. '
                  'Exit if next tick goes '
                  'against\\.')
    else:
        icon   = '⚠️'
        action = 'Watch closely\\.'

    lines = []
    lines.append(
        f'{icon} *STOP '
        f'{"BREACHED" if level == "BREACHED" else "AT"}'
        f' · {_esc(check_ist)}*')
    lines.append('')
    lines.append(
        f'*{_esc(sym)}* · {_esc(stype)}')
    lines.append(
        f'Price {_p_esc(price)}  '
        f'Stop {_p_esc(stop)}  '
        f'*{_esc(level)}*')
    lines.append('')
    lines.append(action)
    lines.append(
        'Rule: stop hit intraday \\= '
        'exit same day\\.')

    send_message('\n'.join(lines))


# ── 4. EXIT TOMORROW / EXIT TODAY ─────────────────────
def send_exit_tomorrow(signals: list,
                       exit_today: bool = False):
    if not signals:
        return

    header_label = (
        'EXIT TODAY — Sell at 9:15 AM Open'
        if exit_today
        else 'EXIT TOMORROW — Day 6 Open')
    header_icon = '🚨' if exit_today else '⏰'

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
                raw     = (ltp - entry) \
                          / entry * 100
                pnl_pct = (
                    raw if direction == 'LONG'
                    else -raw)
            except Exception:
                pass

        enriched.append({
            'sym': sym, 'stype': stype,
            'entry': entry, 'ltp': ltp,
            'pnl_pct': pnl_pct,
            'direction': direction,
        })

    sym_map = {}
    for e in enriched:
        sym = e['sym']
        if sym not in sym_map:
            sym_map[sym] = {
                'entry': e, 'count': 1}
        else:
            sym_map[sym]['count'] += 1
            existing_pnl = (
                sym_map[sym]['entry'].get(
                    'pnl_pct') or -999)
            new_pnl = e.get('pnl_pct') or -999
            if new_pnl > existing_pnl:
                sym_map[sym]['entry'] = e

    deduped = [
        (v['entry'], v['count'])
        for v in sym_map.values()]
    deduped.sort(
        key=lambda x: float(
            x[0].get('pnl_pct') or 0))

    lines = []
    lines.append(
        f'{header_icon} *{_esc(header_label)}*')
    lines.append(
        f'{_esc(str(len(signals)))} signals · '
        f'Sell at 9:15 AM open\\. '
        f'No extensions\\.')
    lines.append('')

    for e, count in deduped:
        pnl = e['pnl_pct']

        if pnl is None:
            icon = '📌'
            pnl_str = _esc('—')
        elif pnl >= 3:
            icon = '🟢'
            pnl_str = _esc(_pct_str(pnl))
        elif pnl >= 0:
            icon = '🟡'
            pnl_str = _esc(_pct_str(pnl))
        elif pnl >= -2:
            icon = '⚠️'
            pnl_str = _esc(_pct_str(pnl))
        else:
            icon = '🔴'
            pnl_str = _esc(_pct_str(pnl))

        sym_display = _esc(e['sym'])
        if count > 1:
            sym_display += _esc(f' x{count}')

        lines.append(
            f'{icon} *{sym_display}*  '
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
        and o.get('outcome')
           not in ('OPEN', None)
        and o.get('result') != 'REJECTED'
        and o.get('action') == 'TOOK'
    ]

    lines = []
    lines.append(
        f'📊 *EOD · {_esc(today_str)}*')
    lines.append('')

    if not resolved:
        lines.append(
            f'Resolved: 0    '
            f'Open: {_esc(str(still_open))}')
        lines.append('')
        lines.append(
            'No signals closed today\\.')

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
                pnl_str = (
                    f'  {_esc(_pct_str(pnl))}')
            except Exception:
                pass

        outcome_esc = _esc(
            outcome.replace('_', ' '))
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
# BX1 FIX: exit_date may be None in some signals —
# guard with 'or' to prevent NoneType comparison crash
def _find_next_exit(outcomes):
    today = date.today().isoformat()
    dates = [
        o.get('exit_date') or ''
        for o in outcomes
        if (o.get('exit_date') or '') > today
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

    now_utc  = datetime.utcnow()
    now_ist  = now_utc + timedelta(
        hours=5, minutes=30)
    now_time = now_ist.strftime('%I:%M %p IST')

    regime     = meta.get('regime', '—')
    active     = meta.get(
        'active_signals_count', 0)
    last_date  = meta.get('market_date', '—')
    last_found = meta.get('signals_found', 0)
    is_trading = meta.get('is_trading_day', True)
    wf_status  = meta.get('workflow_status', '')
    scan_time  = meta.get('scan_time', '')

    scan_ist = _to_ist_safe(scan_time)

    try:
        d = datetime.strptime(
            last_date, '%Y-%m-%d')
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
    lines.append(
        f'Active: {_esc(str(active))} signals')

    if is_trading:
        lines.append('Next scan: 8:45 AM IST')
    else:
        lines.append('Today: Market closed')

    lines.append('')
    lines.append(
        f'Last scan: {_esc(last_date_fmt)} · '
        f'{_esc(str(last_found))} signals')

    if scan_ist and scan_ist != '—':
        lines.append(
            f'Scan time: {_esc(scan_ist)}')

    if wf_status:
        lines.append(
            f'Workflows: {wf_status}')

    send_message('\n'.join(lines))


# ── 7. WORKFLOW FAILURE ALERT ─────────────────────────
def send_workflow_failure(workflow_name: str,
                          run_url: str = None):
    today_str = date.today().strftime('%Y-%m-%d')

    now_utc  = datetime.utcnow()
    now_ist  = now_utc + timedelta(
        hours=5, minutes=30)
    now_time = now_ist.strftime('%I:%M %p IST')

    lines = []
    lines.append('🚨 *WORKFLOW FAILED*')
    lines.append('')
    lines.append(f'*{_esc(workflow_name)}*')
    lines.append(
        f'{_esc(today_str)} · {_esc(now_time)}')
    lines.append('')
    lines.append(
        'Check GitHub Actions immediately\\.')

    if run_url:
        lines.append('')
        lines.append(
            _link('View logs',
                  run_url
                  .replace('.', '\\.')
                  .replace('-', '\\-')))

    send_message('\n'.join(lines))


# ── 8. WEEKEND SUMMARY ────────────────────────────────
def send_weekend_summary(stats: dict):
    """
    W1/TR5: Now shows phase progress, signal type
    breakdown, and week date range in addition to
    standard W/L/F stats.
    """
    today_str   = date.today().strftime('%Y-%m-%d')

    resolved    = stats.get('resolved',    0)
    wins        = stats.get('wins',        0)
    losses      = stats.get('losses',      0)
    flats       = stats.get('flats',       0)
    win_rate    = stats.get('win_rate',    0)
    active      = stats.get('active',      0)
    next_exits  = stats.get('next_exits',  [])
    top_winner  = stats.get('top_winner',  None)
    top_loser   = stats.get('top_loser',   None)
    phase_note  = stats.get('phase_note',  None)
    type_counts = stats.get('type_counts', {})
    week_start  = stats.get('week_start',  '')

    lines = []
    lines.append(
        f'📅 *WEEKLY RECAP · {_esc(today_str)}*')

    if week_start:
        lines.append(
            f'{_esc(week_start)} → '
            f'{_esc(today_str)}')

    lines.append('')

    if resolved == 0:
        lines.append(
            'No signals resolved this week\\.')
    else:
        lines.append(
            f'Resolved: {_esc(str(resolved))}')
        lines.append(
            f'W:{_esc(str(wins))} '
            f'L:{_esc(str(losses))} '
            f'F:{_esc(str(flats))}')
        lines.append(
            f'Win Rate: {_esc(str(win_rate))}%')

        if type_counts:
            type_parts = []
            for t, n in sorted(
                    type_counts.items(),
                    key=lambda x: -x[1]):
                label = _esc(t.replace('_', ' '))
                type_parts.append(
                    f'{label}:{_esc(str(n))}')
            if type_parts:
                lines.append(
                    '  ' + '  '.join(type_parts))

    lines.append('')
    lines.append(
        f'Active: {_esc(str(active))} signals')

    if next_exits:
        exits_str = ', '.join(next_exits[:3])
        lines.append(
            f'Next exits: {_esc(exits_str)}')

    if phase_note:
        lines.append('')
        lines.append(f'📊 {_esc(phase_note)}')

    if top_winner:
        sym = (top_winner.get('symbol', '')
               .replace('.NS', ''))
        pnl = float(
            top_winner.get('pnl_pct') or 0)
        lines.append('')
        lines.append(
            f'🏆 Best: {_esc(sym)} '
            f'{_esc(f"+{pnl:.1f}%")}')

    if top_loser:
        sym = (top_loser.get('symbol', '')
               .replace('.NS', ''))
        pnl = float(
            top_loser.get('pnl_pct') or 0)
        lines.append(
            f'📉 Worst: {_esc(sym)} '
            f'{_esc(f"{pnl:.1f}%")}')

    lines.append('')
    lines.append('Good trading next week\\! 📈')

    send_message('\n'.join(lines))


# ── TEST ──────────────────────────────────────────────
if __name__ == '__main__':
    send_message(
        '✅ *TIE TIY* — Telegram test OK\\.')
