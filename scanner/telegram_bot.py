# ── telegram_bot.py ──────────────────────────────────
# Telegram alert sender for TIE TIY Scanner
#
# FIX 5 — Active stops section corrected:
#   t.get('stock') → t.get('symbol')
#   t.get('stop_price') → t.get('stop')
#   t.get('day_number') → calculated from date
#   Shows max 10 most recent open positions
#   EOD summary also fixed same way
# ─────────────────────────────────────────────────────

import requests
import os
import sys
from datetime import date as _date
sys.path.insert(0, os.path.dirname(__file__))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


# ── HELPERS ───────────────────────────────────────────

def _sym(t):
    """Clean symbol from any signal/trade record."""
    return (t.get('symbol') or
            t.get('stock') or '').replace('.NS', '')


def _calc_day(detection_date_str):
    """
    Calculate trading day number from detection date.
    Simple calendar-day approximation.
    Returns 1-6.
    """
    try:
        det   = _date.fromisoformat(
            str(detection_date_str)[:10])
        today = _date.today()
        delta = (today - det).days
        # Entry is day after detection
        # So day number = delta (roughly)
        return max(1, min(delta, 6))
    except Exception:
        return '?'


def _fmt_stop(t):
    """Format stop price from record."""
    stp = t.get('stop') or t.get('stop_price')
    if not stp:
        return '—'
    try:
        return f"Rs{float(stp):,.2f}"
    except Exception:
        return str(stp)


def send_message(text, parse_mode='HTML'):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured — skipping")
        return False
    try:
        print(f"Sending Telegram to chat "
              f"{TELEGRAM_CHAT_ID[:6]}...")
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            data={
                'chat_id':    TELEGRAM_CHAT_ID,
                'text':       text,
                'parse_mode': parse_mode,
            },
            timeout=15
        )
        print(f"Telegram status: {r.status_code}")
        print(f"Telegram response: {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def fmt_signal_block(sig):
    symbol   = _sym(sig)
    signal   = sig.get('signal', '')
    sector   = sig.get('sector', '')
    age      = sig.get('age', 0)
    regime   = sig.get('regime', '')
    stk_reg  = sig.get('stock_regime', '')
    vol_q    = sig.get('vol_q', '')
    rs_q     = sig.get('rs_q', '')
    entry    = sig.get('entry_est', 0) or \
               sig.get('entry', 0) or 0
    stop     = sig.get('stop', 0) or 0
    bear_b   = sig.get('bear_bonus', False)
    score    = sig.get('score', 0)
    action   = sig.get('action', '')

    # Target and R:R from stored fields
    target   = sig.get('target_price', None) or \
               sig.get('target', None)
    direction = sig.get('direction', 'LONG')

    # Calculate R:R if not stored
    rr = None
    if entry and stop:
        try:
            risk = abs(float(entry) - float(stop))
            if risk > 0:
                rr = 2.0  # always 2R by design
        except Exception:
            pass

    ex_date   = sig.get('exit_date', '')
    arrow     = 'UP'   if signal in (
        'UP_TRI', 'BULL_PROXY', 'UP_TRI_SA')  \
                else 'DOWN'
    bear_tag  = ' [BEAR BONUS]' if bear_b else ''
    icon      = 'DEPLOY' if action == 'DEPLOY' \
                else 'WATCH'

    # Shares and risk calculation
    # ₹5000 risk per trade default
    shares = 0
    risk_amt = 0
    if entry and stop:
        try:
            risk_per = abs(float(entry) - float(stop))
            if risk_per > 0:
                shares   = int(5000 / risk_per)
                risk_amt = shares * risk_per
        except Exception:
            pass

    # Target line
    if target:
        try:
            tgt_line = (f"Target: Rs{float(target):,.2f}"
                        f" R:R 2.0")
        except Exception:
            tgt_line = f"Exit: {ex_date} open (Day 6)"
    else:
        tgt_line = f"Exit: {ex_date} open (Day 6)"

    # Stock regime note
    reg_line = regime
    if stk_reg and stk_reg != regime:
        reg_line = f"{regime}(Mkt) {stk_reg}(Stk)"

    return (
        f"{icon} {symbol} {signal} "
        f"{arrow}{bear_tag}\n"
        f"Score:{score}/10 Age:{age} {sector}\n"
        f"Regime:{reg_line} "
        f"Vol:{vol_q} RS:{rs_q}\n"
        f"Entry: Rs{float(entry):,.2f} "
        f"(next 9:15 open)\n"
        f"Stop:  Rs{float(stop):,.2f}\n"
        f"{tgt_line}\n"
        f"Size:{shares} shares "
        f"Risk:Rs{risk_amt:,.0f}"
    )


def send_morning_alert(signals, market_info,
                       exits_today, open_positions,
                       system_health):
    today     = market_info.get('today', '')
    regime    = market_info.get('regime', '')
    reg_score = market_info.get('regime_score', 0)
    nifty_px  = market_info.get('nifty_price', 0)
    nifty_chg = market_info.get('nifty_change', 0)
    leaders   = market_info.get('sector_leaders', [])
    health    = system_health.get('health', 'NORMAL')
    n_arrow   = 'UP' if nifty_chg >= 0 else 'DOWN'
    n_sign    = '+' if nifty_chg >= 0 else ''
    h_icon    = ('GREEN' if health == 'HOT' else
                 'RED'   if health == 'COLD' else
                 'YELLOW')

    bear_banner = ''
    if regime == 'Bear':
        bear_banner = (
            '\nBEAR BONUS ACTIVE '
            '-- UP_TRI highest conviction\n'
        )

    msg = (
        f"TIE TIY MORNING SCAN -- {today}\n\n"
        f"MARKET\n"
        f"Nifty: {nifty_px:,.0f} {n_arrow} "
        f"{n_sign}{nifty_chg:.1f}%\n"
        f"Regime: {regime} Score:{reg_score}"
        f"{bear_banner}\n"
    )

    if leaders:
        msg += f"Leaders: {' | '.join(leaders)}\n"

    msg += "\n---\n"

    deploy = [s for s in signals
              if s.get('action') == 'DEPLOY']
    watch  = [s for s in signals
              if s.get('action') == 'WATCH']

    if not signals:
        msg += "No signals today\n"
    else:
        msg += f"SIGNALS TODAY -- {len(signals)}\n\n"
        for i, sig in enumerate(deploy, 1):
            msg += f"{i}. {fmt_signal_block(sig)}\n\n"
        if watch:
            msg += f"WATCH ({len(watch)})\n"
            for sig in watch:
                sym  = _sym(sig)
                sc   = sig.get('score', 0)
                sgnl = sig.get('signal', '')
                age  = sig.get('age', 0)
                bb   = ' 🔥' if sig.get(
                    'bear_bonus') else ''
                msg += (f"- {sym} {sgnl} "
                        f"Age:{age} "
                        f"Score:{sc}{bb}\n")

    msg += "\n---\n"

    # Exits today
    if exits_today:
        msg += "EXIT TODAY (9:15 open)\n"
        for t in exits_today:
            stk  = _sym(t)
            sgnl = t.get('signal', '')
            msg += f"- {stk} {sgnl}\n"
        msg += "\n"

    # ── FIX 5 — Active open positions ────────────
    # Was: t.get('stock'), t.get('stop_price'),
    #      t.get('day_number') — all wrong fields
    # Now: t.get('symbol'), t.get('stop'),
    #      _calc_day(t.get('date')) — correct fields
    # Cap at 10 most recent to avoid wall of text
    if open_positions:
        # Sort by date descending — newest first
        recent = sorted(
            open_positions,
            key=lambda x: x.get('date', ''),
            reverse=True
        )[:10]

        total = len(open_positions)
        shown = len(recent)
        more  = total - shown

        msg += (f"OPEN POSITIONS "
                f"({total} total)\n")

        for t in recent:
            stk  = _sym(t)
            sig  = t.get('signal', '')
            stp  = _fmt_stop(t)
            day  = _calc_day(t.get('date', ''))
            bb   = ' 🔥' if t.get(
                'bear_bonus') else ''
            msg += (f"- {stk} {sig}{bb} "
                    f"Stop:{stp} "
                    f"Day{day}/6\n")

        if more > 0:
            msg += f"  ...and {more} more\n"
    # ── END FIX 5 ─────────────────────────────────

    msg += f"\nSystem: {h_icon}"

    print(f"Telegram message length: {len(msg)}")
    send_message(msg)


def send_eod_summary(open_trades, exits_done,
                     market_info):
    """
    EOD summary — also uses correct field names
    Same fix as active stops above
    """
    today = market_info.get('today', '')
    msg   = f"TIE TIY EOD -- {today}\n\n"

    if exits_done:
        msg += "EXITS TODAY\n"
        for t in exits_done:
            stk = _sym(t)
            pnl = t.get('pnl_pct', '')
            msg += (f"- {stk}"
                    f"{' '+str(pnl)+'%' if pnl else ''}"
                    f"\n")
        msg += "\n"

    if open_trades:
        # Sort by date descending — newest first
        recent = sorted(
            open_trades,
            key=lambda x: x.get('date', ''),
            reverse=True
        )[:10]

        total = len(open_trades)
        msg  += f"OPEN POSITIONS ({total} total)\n"

        for t in recent:
            stk = _sym(t)
            day = _calc_day(t.get('date', ''))
            stp = _fmt_stop(t)
            sig = t.get('signal', '')
            msg += (f"- {stk} {sig} "
                    f"Stop:{stp} "
                    f"Day{day}/6\n")

        if total > 10:
            msg += f"  ...and {total - 10} more\n"
    else:
        msg += "No open positions\n"

    send_message(msg)


def send_stop_alert(trade, stop_price):
    stk   = _sym(trade)
    stype = trade.get('signal', '') or \
            trade.get('signal_type', '')
    entry = (trade.get('entry') or
             trade.get('actual_open') or
             trade.get('entry_actual') or
             trade.get('entry_estimate') or 0)
    try:
        entry_fmt = f"Rs{float(entry):,.2f}"
    except Exception:
        entry_fmt = str(entry)
    try:
        stop_fmt  = f"Rs{float(stop_price):,.2f}"
    except Exception:
        stop_fmt  = str(stop_price)

    msg = (
        f"STOP HIT -- {stk}\n"
        f"Signal: {stype}\n"
        f"Entry: {entry_fmt}\n"
        f"Stop: {stop_fmt}\n"
        f"Exit at stop price NOW"
    )
    send_message(msg)


def send_holiday_notice(reason):
    send_message(
        f"TIE TIY -- Market Closed\n"
        f"Reason: {reason}\n"
        f"No scan today.")


def send_large_move_alert(symbol, move_pct, atr):
    send_message(
        f"LARGE MOVE -- {symbol}\n"
        f"Move: {move_pct:.1f}%  "
        f"ATR: {atr:.2f}\n"
        f"Check open positions.")
