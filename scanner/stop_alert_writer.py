# ── stop_alert_writer.py ─────────────────────────────
# Runs every 5 min during market hours via stop_check.yml
# Fetches current intraday prices for open positions
# Checks stop proximity AND target hits
# Writes stop_alerts.json to output/
#
# B3 FIX: Target hit detection added alongside stop check
# F1 FIX: Dual track — target hit fires Telegram once,
#         signal continues observing till Day 6
# NEW:    ltp_updated_at written to output for PWA
#
# V1.1 FIXES:
# - BX2: Holiday/weekend guard — exits immediately
#         if market is closed, no alerts sent
# - BX4: Target hit dedup already existed (F1) —
#         confirmed working, sig_id based
# - BX6: entry_valid=False signals excluded from
#         stop monitoring — never entered, ignore
# - BX7: Same stock same direction dedup —
#         if stock has multiple signals, only
#         send ONE alert per stock per cycle
#
# V1.2 FIXES:
# - BX8: Stop alert dedup persisted to file —
#         stop_alerts_sent.json resets daily.
#         Prevents same breach firing every 5 min.
#
# V2 FIXES:
# - SA1: Terminal outcome filter — signals already
#         resolved (STOP_HIT, TARGET_HIT, DAY6_*)
#         are excluded from stop monitoring entirely.
#         Prevents dead signals re-alerting next day.
# - SA2: Timezone fix — all timestamps now use
#         UTC+5:30 (IST) instead of server UTC.
#         Fixes "03:02 AM IST" showing UTC time.
# ─────────────────────────────────────────────────────

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import get_open_trades
from telegram_bot import send_message

# ── PATHS ─────────────────────────────────────────────
_HERE              = os.path.dirname(
    os.path.abspath(__file__))
_ROOT              = os.path.dirname(_HERE)
_OUTPUT            = os.path.join(_ROOT, 'output')
OUT_FILE           = os.path.join(
    _OUTPUT, 'stop_alerts.json')
TARGET_ALERTS_FILE = os.path.join(
    _OUTPUT, 'target_alerts_sent.json')
STOP_ALERTS_FILE   = os.path.join(
    _OUTPUT, 'stop_alerts_sent.json')

# ── THRESHOLDS ────────────────────────────────────────
NEAR_STOP_PCT = 2.0
AT_STOP_PCT   = 0.5

# SA1: Terminal outcomes — signals with these are
# fully closed and must never be monitored.
_TERMINAL_OUTCOMES = {
    'STOP_HIT',
    'TARGET_HIT',
    'DAY6_WIN',
    'DAY6_LOSS',
    'DAY6_FLAT',
}


# SA2: IST TIMESTAMP HELPER ───────────────────────────
def _now_ist_str():
    """
    SA2 FIX: Returns current time as IST string.
    GitHub Actions runners are UTC — datetime.now()
    returns UTC, not IST. This applies +5:30 offset
    so all alert timestamps show correct IST time.
    """
    ist_offset = timezone(timedelta(hours=5,
                                    minutes=30))
    return datetime.now(tz=ist_offset).strftime(
        '%I:%M %p IST')


def _now_ist_date():
    """SA2 FIX: Returns current date in IST."""
    ist_offset = timezone(timedelta(hours=5,
                                    minutes=30))
    return datetime.now(tz=ist_offset).date()


# ── BX2: TRADING DAY GUARD ────────────────────────────
def _is_trading_day() -> bool:
    today = _now_ist_date()
    if today.weekday() >= 5:
        return False
    try:
        holidays_file = os.path.join(
            _OUTPUT, 'nse_holidays.json')
        if os.path.exists(holidays_file):
            with open(holidays_file, 'r') as f:
                data = json.load(f)
            holidays = data.get('holidays', [])
            if today.isoformat() in holidays:
                return False
    except Exception:
        pass
    return True


# ── TARGET ALERT DEDUP ────────────────────────────────
def _load_target_alerts_sent():
    try:
        with open(TARGET_ALERTS_FILE, 'r') as f:
            data = json.load(f)
        if data.get('date') != \
                _now_ist_date().isoformat():
            return set()
        return set(data.get('sent_ids', []))
    except Exception:
        return set()


def _save_target_alert_sent(signal_id, sent_ids):
    sent_ids.add(signal_id)
    try:
        with open(TARGET_ALERTS_FILE, 'w') as f:
            json.dump({
                'date':     _now_ist_date().isoformat(),
                'sent_ids': list(sent_ids),
            }, f)
    except Exception as e:
        print(f"[stop_alert] Dedup save error: {e}")


# ── BX8: STOP ALERT DEDUP ─────────────────────────────
# Persists sent stop alerts to file so dedup
# survives across 5-min cron runs.
# Resets automatically each new day.

def _load_stop_alerts_sent():
    try:
        with open(STOP_ALERTS_FILE, 'r') as f:
            data = json.load(f)
        if data.get('date') != \
                _now_ist_date().isoformat():
            return set()
        return set(data.get('sent_keys', []))
    except Exception:
        return set()


def _save_stop_alert_sent(key, sent_keys):
    sent_keys.add(key)
    try:
        with open(STOP_ALERTS_FILE, 'w') as f:
            json.dump({
                'date':      _now_ist_date().isoformat(),
                'sent_keys': list(sent_keys),
            }, f)
    except Exception as e:
        print(
            f"[stop_alert] Stop dedup save error: {e}")


# ── HELPERS ───────────────────────────────────────────
def _fetch_current_price(symbol, retries=2):
    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                period='1d',
                interval='1m',
                progress=False,
                auto_adjust=False,
            )

            if df is not None and not df.empty:
                if isinstance(
                        df.columns, pd.MultiIndex):
                    df.columns = [
                        c[0] for c in df.columns]
                price      = float(
                    df.iloc[-1]['Close'])
                # SA2 FIX: use IST time
                fetch_time = _now_ist_str()
                return price, fetch_time

            df = yf.download(
                symbol,
                period='5d',
                interval='1d',
                progress=False,
                auto_adjust=False,
            )

            if df is not None and not df.empty:
                if isinstance(
                        df.columns, pd.MultiIndex):
                    df.columns = [
                        c[0] for c in df.columns]
                price      = float(
                    df.iloc[-1]['Close'])
                # SA2 FIX: use IST time
                fetch_time = _now_ist_str()
                return price, fetch_time

        except Exception as e:
            print(f"[stop_alert] Fetch attempt "
                  f"{attempt+1} failed {symbol}: {e}")

    return None, None


def _assess_stop_level(trade, current_price):
    try:
        stop      = float(
            trade.get('stop', 0) or 0)
        entry     = float(
            trade.get('entry', 0)
            or trade.get('scan_price', 0) or 0)
        direction = trade.get('direction', 'LONG')

        if stop <= 0 or entry <= 0:
            return ('UNKNOWN', None, None, None,
                    'Missing stop or entry')

        risk = (entry - stop
                if direction == 'LONG'
                else stop - entry)

        if risk <= 0:
            return ('UNKNOWN', None, None, None,
                    'Invalid risk calculation')

        pct_from_stop = round(
            abs(current_price - stop) / stop * 100,
            2)

        if direction == 'LONG':
            pnl_pct = round(
                (current_price - entry)
                / entry * 100, 2)
            pnl_r   = round(
                (current_price - entry) / risk, 2)
        else:
            pnl_pct = round(
                (entry - current_price)
                / entry * 100, 2)
            pnl_r   = round(
                (entry - current_price) / risk, 2)

        if direction == 'LONG':
            if current_price <= stop:
                return ('BREACHED', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"STOP BREACHED — "
                        f"₹{current_price:.2f} below "
                        f"stop ₹{stop:.2f}")
            diff = ((current_price - stop)
                    / stop * 100)
            if diff <= AT_STOP_PCT:
                return ('AT', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"AT STOP — "
                        f"₹{current_price:.2f} within "
                        f"0.5% of stop ₹{stop:.2f}")
            if diff <= NEAR_STOP_PCT:
                return ('NEAR', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"NEAR STOP — "
                        f"₹{current_price:.2f} within "
                        f"2% of stop ₹{stop:.2f}")

        elif direction == 'SHORT':
            if current_price >= stop:
                return ('BREACHED', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"STOP BREACHED — "
                        f"₹{current_price:.2f} above "
                        f"stop ₹{stop:.2f}")
            diff = ((stop - current_price)
                    / stop * 100)
            if diff <= AT_STOP_PCT:
                return ('AT', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"AT STOP — within 0.5% "
                        f"of stop")
            if diff <= NEAR_STOP_PCT:
                return ('NEAR', pct_from_stop,
                        pnl_pct, pnl_r,
                        f"NEAR STOP — within 2% "
                        f"of stop")

        return ('SAFE', pct_from_stop,
                pnl_pct, pnl_r,
                f"Safe ₹{current_price:.2f} | "
                f"{pnl_r:+.2f}R")

    except Exception as e:
        print(f"[stop_alert] Stop assess error: {e}")
        return ('UNKNOWN', None, None, None,
                'Assessment error')


def _assess_target_hit(trade, current_price):
    try:
        target    = float(
            trade.get('target_price', 0) or 0)
        entry     = float(
            trade.get('entry', 0)
            or trade.get('scan_price', 0) or 0)
        direction = trade.get('direction', 'LONG')

        if target <= 0 or entry <= 0:
            return False, None

        if direction == 'LONG':
            hit = current_price >= target
        else:
            hit = current_price <= target

        if hit:
            if direction == 'LONG':
                pnl_pct = round(
                    (current_price - entry)
                    / entry * 100, 2)
            else:
                pnl_pct = round(
                    (entry - current_price)
                    / entry * 100, 2)
            return True, pnl_pct

        return False, None

    except Exception as e:
        print(f"[stop_alert] Target assess error: {e}")
        return False, None


def _send_target_hit_alert(trade, current_price,
                           pnl_pct, check_time):
    sym    = (trade.get('symbol') or '?')\
              .replace('.NS', '')
    stype  = trade.get('signal', '?')
    target = trade.get('target_price', 0)
    entry  = (trade.get('entry')
              or trade.get('scan_price') or 0)
    score  = trade.get('score', 0)

    sign    = '+' if (pnl_pct or 0) >= 0 else ''
    pnl_str = (f"{sign}{pnl_pct:.1f}%"
               if pnl_pct is not None else '—')

    def _e(v):
        for ch in r'\_*[]()~`>#+-=|{}.!':
            v = str(v).replace(ch, f'\\{ch}')
        return v

    def _p(v):
        try:
            f = float(v)
            if f >= 10000: return f'₹{f:,.0f}'
            if f >= 1000:  return f'₹{f:,.2f}'
            return f'₹{f:.2f}'
        except Exception:
            return '—'

    lines = [
        f'🎯 *TARGET HIT\\!*  {_e(check_time)}',
        '',
        f'*{_e(sym)}* · {_e(stype)} · '
        f'{_e(str(score))}/10',
        f'Entry {_e(_p(entry))}  →  '
        f'Target {_e(_p(target))}',
        f'LTP {_e(_p(current_price))}  '
        f'P\\&L *{_e(pnl_str)}*',
        '',
        f'Observing till Day 6 open\\.',
    ]

    send_message('\n'.join(lines))


def _send_stop_alert_msg(trade, current_price,
                         alert_level, check_time):
    sym   = (trade.get('symbol') or '?')\
             .replace('.NS', '')
    stype = trade.get('signal', '?')
    stop  = trade.get('stop', 0)

    def _e(v):
        for ch in r'\_*[]()~`>#+-=|{}.!':
            v = str(v).replace(ch, f'\\{ch}')
        return v

    def _p(v):
        try:
            f = float(v)
            if f >= 10000: return f'₹{f:,.0f}'
            if f >= 1000:  return f'₹{f:,.2f}'
            return f'₹{f:.2f}'
        except Exception:
            return '—'

    if alert_level == 'BREACHED':
        icon   = '🚨'
        action = 'Exit immediately at market\\.'
    elif alert_level == 'AT':
        icon   = '🔴'
        action = ('At stop\\. '
                  'Exit if next tick against\\.')
    else:
        icon   = '⚠️'
        action = 'Watch closely\\.'

    lines = [
        f'{icon} *STOP {_e(alert_level)} · '
        f'{_e(check_time)}*',
        '',
        f'*{_e(sym)}* · {_e(stype)}',
        f'Price {_e(_p(current_price))}  '
        f'Stop {_e(_p(stop))}',
        '',
        action,
    ]

    send_message('\n'.join(lines))


# ── MAIN FUNCTION ─────────────────────────────────────
def run_stop_check():
    os.makedirs(_OUTPUT, exist_ok=True)

    # BX2 FIX: Holiday/weekend guard
    if not _is_trading_day():
        today_str = _now_ist_date().isoformat()
        print(f"[stop_alert] {today_str} is a "
              f"holiday or weekend — skipping")
        _write_empty(
            _now_ist_date().isoformat(),
            _now_ist_str())
        return

    today      = _now_ist_date().isoformat()
    check_time = _now_ist_str()

    print(f"[stop_alert] Stop check at {check_time}")

    open_trades = get_open_trades()

    if not open_trades:
        print("[stop_alert] No open positions")
        _write_empty(today, check_time)
        return

    # BX6 FIX: Exclude entry_valid=False signals
    # SA1 FIX: Exclude terminal outcome signals —
    #   already resolved signals must never be
    #   monitored. Prevents dead signal re-alerts.
    valid_trades = [
        t for t in open_trades
        if t.get('entry_valid') is not False
        and t.get('outcome', 'OPEN')
            not in _TERMINAL_OUTCOMES
    ]

    skipped_invalid = len([
        t for t in open_trades
        if t.get('entry_valid') is False
    ])
    skipped_resolved = len([
        t for t in open_trades
        if t.get('outcome', 'OPEN')
            in _TERMINAL_OUTCOMES
    ])

    if skipped_invalid > 0:
        print(f"[stop_alert] Skipping "
              f"{skipped_invalid} entry_valid=False "
              f"signals")
    if skipped_resolved > 0:
        print(f"[stop_alert] SA1: Skipping "
              f"{skipped_resolved} already-resolved "
              f"signals (terminal outcome)")

    print(f"[stop_alert] Checking "
          f"{len(valid_trades)} positions")

    # Load dedup sets — both persist across runs
    target_alerts_sent = _load_target_alerts_sent()

    # BX8 FIX: Load stop alerts sent today from file
    # Replaces in-memory set that reset every 5 min
    stop_alerted_stocks = _load_stop_alerts_sent()

    alerts           = []
    fetch_failed     = []
    breached_count   = 0
    at_count         = 0
    near_count       = 0
    safe_count       = 0
    target_hit_count = 0

    for trade in valid_trades:
        symbol    = trade.get('symbol', '')
        signal    = trade.get('signal', '')
        direction = trade.get('direction', 'LONG')
        entry     = trade.get('entry', None)
        stop      = trade.get('stop', None)
        sig_date  = trade.get('date', today)
        sig_id    = trade.get('id', '')

        if not symbol:
            continue

        current_price, fetch_time = \
            _fetch_current_price(symbol)

        if current_price is None:
            print(
                f"[stop_alert] Fetch failed: {symbol}")
            fetch_failed.append(symbol)
            alerts.append({
                'symbol':        symbol,
                'signal':        signal,
                'signal_date':   sig_date,
                'direction':     direction,
                'entry':         entry,
                'stop':          stop,
                'current_price': None,
                'alert_level':   'UNKNOWN',
                'target_hit':    False,
                'pct_from_stop': None,
                'pnl_pct':       None,
                'pnl_r':         None,
                'note':          'Price fetch failed',
                'check_time':    check_time,
            })
            continue

        # ── Stop check ────────────────────────────────
        (alert_level,
         pct_from_stop,
         pnl_pct,
         pnl_r,
         note) = _assess_stop_level(
            trade, current_price)

        # BX7 + BX8: dedup key — one alert per
        # stock per direction per DAY (persisted)
        sym_clean       = symbol.replace('.NS', '')
        dedup_key       = f"{sym_clean}_{direction}"
        already_alerted = (
            dedup_key in stop_alerted_stocks)

        if alert_level == 'BREACHED':
            breached_count += 1
            if not already_alerted:
                _send_stop_alert_msg(
                    trade, current_price,
                    alert_level,
                    fetch_time or check_time)
                _save_stop_alert_sent(
                    dedup_key, stop_alerted_stocks)
            else:
                print(f"[stop_alert] Dedup: "
                      f"skip duplicate BREACHED "
                      f"for {sym_clean}")
        elif alert_level == 'AT':
            at_count += 1
            if not already_alerted:
                _send_stop_alert_msg(
                    trade, current_price,
                    alert_level,
                    fetch_time or check_time)
                _save_stop_alert_sent(
                    dedup_key, stop_alerted_stocks)
            else:
                print(f"[stop_alert] Dedup: "
                      f"skip duplicate AT "
                      f"for {sym_clean}")
        elif alert_level == 'NEAR':
            near_count += 1
        elif alert_level == 'SAFE':
            safe_count += 1

        # ── Target check (B3 FIX) ─────────────────────
        target_hit, target_pnl = \
            _assess_target_hit(trade, current_price)

        if target_hit:
            target_hit_count += 1
            print(f"[stop_alert] TARGET HIT: "
                  f"{symbol} @ {current_price:.2f}")

            if (sig_id
                    and sig_id
                    not in target_alerts_sent):
                _send_target_hit_alert(
                    trade, current_price,
                    target_pnl,
                    fetch_time or check_time)
                _save_target_alert_sent(
                    sig_id, target_alerts_sent)

        alerts.append({
            'symbol':        symbol,
            'signal':        signal,
            'signal_date':   sig_date,
            'direction':     direction,
            'entry':         entry,
            'stop':          stop,
            'current_price': round(current_price, 2),
            'alert_level':   alert_level,
            'target_hit':    target_hit,
            'pct_from_stop': pct_from_stop,
            'pnl_pct':       pnl_pct,
            'pnl_r':         pnl_r,
            'note':          note,
            'check_time':    fetch_time or check_time,
        })

        print(f"[stop_alert] {symbol} | "
              f"₹{current_price:.2f} | "
              f"Stop:{alert_level} | "
              f"Target:"
              f"{'HIT' if target_hit else 'open'}")

    # ── Write output ──────────────────────────────────
    output = {
        'date':             today,
        'check_time':       check_time,
        'ltp_updated_at':   check_time,
        'open_positions':   len(valid_trades),
        'breached_count':   breached_count,
        'at_count':         at_count,
        'near_count':       near_count,
        'safe_count':       safe_count,
        'target_hit_count': target_hit_count,
        'fetch_failed':     fetch_failed,
        'has_alerts':       (
            breached_count + at_count) > 0,
        'alerts':           alerts,
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[stop_alert] Done → "
          f"BREACHED:{breached_count} "
          f"AT:{at_count} "
          f"NEAR:{near_count} "
          f"TARGET_HIT:{target_hit_count} "
          f"FAILED:{len(fetch_failed)} "
          f"SKIPPED_INVALID:{skipped_invalid} "
          f"SKIPPED_RESOLVED:{skipped_resolved}")


def _write_empty(today, check_time):
    output = {
        'date':             today,
        'check_time':       check_time,
        'ltp_updated_at':   check_time,
        'open_positions':   0,
        'breached_count':   0,
        'at_count':         0,
        'near_count':       0,
        'safe_count':       0,
        'target_hit_count': 0,
        'fetch_failed':     [],
        'has_alerts':       False,
        'alerts':           [],
    }
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print("[stop_alert] Empty stop_alerts.json written")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_stop_check()
