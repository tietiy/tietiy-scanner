import requests
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send_message(text, parse_mode='HTML'):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured — skipping")
        return False
    try:
        print(f"Sending Telegram to chat {TELEGRAM_CHAT_ID[:6]}...")
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
    symbol   = sig.get('symbol','').replace('.NS','')
    signal   = sig.get('signal', '')
    sector   = sig.get('sector', '')
    age      = sig.get('age', 0)
    regime   = sig.get('regime', '')
    vol_q    = sig.get('vol_q', '')
    rs_q     = sig.get('rs_q', '')
    entry    = sig.get('entry_est', 0)
    stop     = sig.get('stop', 0)
    target   = sig.get('target', None)
    rr       = sig.get('rr', None)
    shares   = sig.get('shares', 0)
    risk     = sig.get('risk_amt', 0)
    ex_date  = sig.get('exit_date', '')
    exit_rule= sig.get('exit_rule', '')
    bear_b   = sig.get('bear_bonus', False)
    score    = sig.get('score', 0)
    action   = sig.get('action', '')

    arrow    = 'UP' if signal in (
        'UP_TRI', 'BULL_PROXY') else 'DOWN'
    bear_tag = ' [BEAR BONUS]' if bear_b else ''
    icon     = 'DEPLOY' if action == 'DEPLOY' \
               else 'WATCH'
    tgt_line = (f"Target: Rs{target:,.2f} R:R {rr}"
                if target
                else f"Exit: {ex_date} open ({exit_rule})")
    return (
        f"{icon} {symbol} {signal} {arrow}{bear_tag}\n"
        f"Score:{score}/10 Age:{age} {sector}\n"
        f"Regime:{regime} Vol:{vol_q} RS:{rs_q}\n"
        f"Entry: Rs{entry:,.2f} (next 9:15 open)\n"
        f"Stop:  Rs{stop:,.2f}\n"
        f"{tgt_line}\n"
        f"Size:{shares} shares Risk:Rs{risk:,.0f}"
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

    msg  = (
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
                sym  = sig['symbol'].replace('.NS','')
                sc   = sig.get('score', 0)
                sgnl = sig.get('signal', '')
                age  = sig.get('age', 0)
                msg += (f"- {sym} {sgnl} "
                        f"Age:{age} Score:{sc}\n")

    msg += "\n---\n"

    if exits_today:
        msg += "EXIT TODAY (9:15 open)\n"
        for t in exits_today:
            stk = t.get('stock','').replace('.NS','')
            stp = t.get('signal_type', '')
            msg += f"- {stk} {stp}\n"
        msg += "\n"

    if open_positions:
        msg += "ACTIVE STOPS\n"
        for t in open_positions:
            stk = t.get('stock','').replace('.NS','')
            stp = t.get('stop_price', '')
            day = t.get('day_number', '?')
            msg += f"- {stk} Stop:{stp} Day{day}\n"

    msg += f"\nSystem: {h_icon}"

    print(f"Telegram message length: {len(msg)}")
    send_message(msg)


def send_eod_summary(open_trades, exits_done,
                     market_info):
    today = market_info.get('today', '')
    msg   = f"TIE TIY EOD -- {today}\n\n"

    if exits_done:
        msg += "EXITS TODAY\n"
        for t in exits_done:
            stk = t.get('stock','').replace('.NS','')
            pnl = t.get('pnl_pct', '')
            msg += (f"- {stk}"
                    f"{' '+str(pnl)+'%' if pnl else ''}\n")
        msg += "\n"

    if open_trades:
        msg += "OPEN POSITIONS\n"
        for t in open_trades:
            stk = t.get('stock','').replace('.NS','')
            day = t.get('day_number', '?')
            pnl = t.get('pnl_pct', '')
            msg += (f"- {stk} Day{day}"
                    f"{' '+str(pnl)+'%' if pnl else ''}\n")
    else:
        msg += "No open positions\n"

    send_message(msg)


def send_stop_alert(trade, stop_price):
    stk   = trade.get('stock','').replace('.NS','')
    stype = trade.get('signal_type', '')
    entry = trade.get('entry_actual',
                      trade.get('entry_estimate', 0))
    msg   = (
        f"STOP HIT -- {stk}\n"
        f"Signal: {stype}\n"
        f"Entry: Rs{entry}\n"
        f"Stop: Rs{stop_price}\n"
        f"Exit at stop price NOW"
    )
    send_message(msg)


def send_holiday_notice(reason):
    send_message(
        f"TIE TIY -- Market Closed\n"
        f"Reason: {reason}\nNo scan today.")


def send_large_move_alert(symbol, move_pct, atr):
    send_message(
        f"LARGE MOVE -- {symbol}\n"
        f"Move: {move_pct:.1f}%  ATR: {atr:.2f}\n"
        f"Check open positions.")
