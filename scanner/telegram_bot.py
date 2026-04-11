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
#
# CHANGES:
# D1 FIX: send_morning_scan reads active_signals_count from meta
# NEW: scan_time + ltp_updated_at shown in morning scan header
# B1 FIX: send_exit_tomorrow accepts exit_today flag
# Q2 FIX: send_message has retry with exponential backoff
# Q3 FIX: send_heartbeat shows workflow status
# Q4 FIX: send_message auto-chunks messages > 4000 chars
# ─────────────────────────────────────────────────────

import os
import re
import time
import requests
from datetime import date, datetime

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '8493010921')


# ── CORE SEND WITH RETRY + CHUNKING ───────────────────
def send_message(text: str, max_retries: int = 3) -> bool:
    """
    Send Telegram message with retry, backoff, and auto-chunking.
    
    - Splits messages > 4000 chars into multiple messages
    - Tries MarkdownV2 first, falls back to plain text
    - Retry delays: 2s, 4s, 8s (exponential backoff)
    """
    if not TELEGRAM_TOKEN:
        print('[telegram] No TELEGRAM_TOKEN — skipping')
        return False

    # ── Chunk if needed (4096 limit, use 4000 for safety) ──
    MAX_LENGTH = 4000
    
    if len(text) <= MAX_LENGTH:
        return _send_single_message(text, max_retries)
    
    # Split into chunks at newlines
    chunks = _split_message(text, MAX_LENGTH)
    print(f'[telegram] Message too long ({len(text)} chars), '
          f'splitting into {len(chunks)} chunks')
    
    success = True
    for i, chunk in enumerate(chunks):
        print(f'[telegram] Sending chunk {i + 1}/{len(chunks)} '
              f'({len(chunk)} chars)')
        if not _send_single_message(chunk, max_retries):
            success = False
        # Small delay between chunks to avoid rate limiting
        if i < len(chunks) - 1:
            time.sleep(1)
    
    return success


def _split_message(text: str, max_length: int) -> list:
    """
    Split message into chunks at newline boundaries.
    Tries to keep logical sections together.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current = ""
    
    for line in text.split('\n'):
        # If single line exceeds max, force split
        if len(line) > max_length:
            if current:
                chunks.append(current.rstrip('\n'))
                current = ""
            # Split long line at max_length
            for i in range(0, len(line), max_length - 10):
                chunks.append(line[i:i + max_length - 10])
            continue
        
        # Check if adding line exceeds max
        if len(current) + len(line) + 1 > max_length:
            chunks.append(current.rstrip('\n'))
            current = line + '\n'
        else:
            current += line + '\n'
    
    if current.strip():
        chunks.append(current.rstrip('\n'))
    
    return chunks


def _send_single_message(text: str, max_retries: int = 3) -> bool:
    """
    Send a single message with retry and exponential backoff.
    """
    url = (f'https://api.telegram.org/'
           f'bot{TELEGRAM_TOKEN}/sendMessage')

    # ── Attempt 1: MarkdownV2 with retries ────────────
    for attempt in range(max_retries):
        try:
            payload = {
                'chat_id':                  TELEGRAM_CHAT_ID,
                'text':                     text,
                'parse_mode':               'MarkdownV2',
                'disable_web_page_preview': True,
            }
            r = requests.post(url, json=payload, timeout=15)
            
            if r.status_code == 200:
                print(f'[telegram] Sent OK (attempt {attempt + 1})')
                return True
            
            # Rate limited — wait and retry
            if r.status_code == 429:
                retry_after = r.json().get(
                    'parameters', {}).get('retry_after', 5)
                print(f'[telegram] Rate limited, waiting {retry_after}s')
                time.sleep(retry_after)
                continue
            
            # Other error — log and try next attempt
            print(f'[telegram] Attempt {attempt + 1} failed: '
                  f'{r.status_code} {r.text[:100]}')
            
        except requests.exceptions.Timeout:
            print(f'[telegram] Attempt {attempt + 1} timeout')
        except Exception as e:
            print(f'[telegram] Attempt {attempt + 1} error: {e}')
        
        # Exponential backoff: 2s, 4s, 8s
        if attempt < max_retries - 1:
            delay = 2 ** (attempt + 1)
            print(f'[telegram] Retrying in {delay}s...')
            time.sleep(delay)

    # ── Attempt 2: Plain text fallback ────────────────
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


def _strip_markdown(text):
    text = re.sub(r'\|\|(.+?)\|\|', r'\1', text,
                  flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)',
                  r'\1 \2', text)
    text = re.sub(r'\\(.)', r'\1', text)
    return text


# ── MARKDOWNV2 ESCAPING ───────────────────────────────
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


# ── 1. MORNING SCAN ───────────────────────────────────
def send_morning_scan(signals: list, meta: dict):
    """
    Compact visible line per signal showing stock regime.
    Price details hidden in spoiler — tap to reveal.
    Sorted by score descending.
    Shows scan_time + ltp_updated_at if provided in meta.
    Link at bottom as clickable hyperlink.
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
        lines.append(
            _esc('  ·  '.join(timing_parts)))

    lines.append('')

    if not sorted_sigs:
        lines.append(
            'No new signals today\\. '
            'Market watching\\.')
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
                spoiler_parts) \
                if spoiler_parts \
                else 'Price data unavailable'

            lines.append(visible)
            lines.append(_spoiler(spoiler_text))
            lines.append('')

    lines.append(
        _link(
            'tietiy\\.github\\.io/tietiy\\-scanner/',
            'https://tietiy.github.io/tietiy-scanner/'
        ))

    send_message('\n'.join(lines))


# ── 2. OPEN VALIDATION ────────────────────────────────
def send_open_validation(confirmed: list,
                         rejected: list):
    lines = []
    lines.append('📋 *Open Prices · 9:29 AM*')
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
            '⚠️ Caution signals — reduced R:R\\.')
    else:
        lines.append(
            'All entries valid\\. '
            'Enter at market\\.')

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
        f'{icon} *STOP ALERT · '
        f'{_esc(check_time)}*')
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
    """
    Entry + LTP + % vs entry per signal.
    Sorted worst P&L first.
    exit_today=True  → header says EXIT TODAY
    exit_today=False → header says EXIT TOMORROW (default)
    """
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
        f'Sell at 9:15 AM open\\. '
        f'No extensions\\.')
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
                pnl_pct = (raw
                           if direction == 'LONG'
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
    """
    Signal type + outcome + P&L per resolved signal.
    Always sends even if 0 resolved.
    outcomes = full load_history() list
    still_open = count of PENDING TOOK signals
    """
    today_str = date.today().strftime('%Y-%m-%d')

    resolved = [
        o for o in outcomes
        if o.get('outcome')
        and o.get('outcome') not in ('OPEN', None)
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
                pnl_str = f'  {_esc(_pct_str(pnl))}'
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
    """
    Simple alive signal sent before morning scan.
    Shows system status, regime, active count, workflow status.
    """
    today_str   = date.today().strftime('%Y-%m-%d')
    now_time    = datetime.now().strftime('%I:%M %p')
    
    regime      = meta.get('regime', '—')
    active      = meta.get('active_signals_count', 0)
    last_date   = meta.get('market_date', '—')
    last_found  = meta.get('signals_found', 0)
    is_trading  = meta.get('is_trading_day', True)
    wf_status   = meta.get('workflow_status', '')
    
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
    lines.append(f'System: ✅ Online')
    lines.append(f'Regime: {_esc(regime)}')
    lines.append(f'Active: {_esc(str(active))} signals')
    
    if is_trading:
        lines.append(f'Next scan: 8:45 AM')
    else:
        lines.append(f'Today: Market closed')
    
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
    """
    Alert when a GitHub Action workflow fails.
    Called from workflow YAML on failure condition.
    """
    today_str = date.today().strftime('%Y-%m-%d')
    now_time  = datetime.now().strftime('%I:%M %p')
    
    lines = []
    lines.append(f'🚨 *WORKFLOW FAILED*')
    lines.append('')
    lines.append(f'*{_esc(workflow_name)}*')
    lines.append(f'{_esc(today_str)} · {_esc(now_time)}')
    lines.append('')
    lines.append('Check GitHub Actions immediately\\.')
    
    if run_url:
        lines.append('')
        lines.append(
            _link('View logs', 
                  run_url.replace('.', '\\.').replace('-', '\\-')))
    
    send_message('\n'.join(lines))


# ── TEST ──────────────────────────────────────────────
if __name__ == '__main__':
    send_message(
        '✅ *TIE TIY* — Telegram test OK\\.')
