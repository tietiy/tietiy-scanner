import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(text, parse_mode='HTML'):
    """Send a Telegram message"""
    try:
        url  = f"{BASE_URL}/sendMessage"
        data = {
            'chat_id':    TELEGRAM_CHAT_ID,
            'text':       text,
            'parse_mode': parse_mode,
        }
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def fmt_signal_block(sig):
    """Format one signal for Telegram"""
    action  = sig.get('action','')
    score   = sig.get('score', 0)
    signal  = sig.get('signal','')
    symbol  = sig.get('symbol','').replace('.NS','')
    sector  = sig.get('sector','')
    age     = sig.get('age', 0)
    regime  = sig.get('regime','')
    vol_q   = sig.get('vol_q','')
    rs_q    = sig.get('rs_q','')
    entry   = sig.get('entry_est', 0)
    stop    = sig.get('stop', 0)
    target  = sig.get('target', None)
    rr      = sig.get('rr', None)
    shares  = sig.get('shares', 0)
    risk    = sig.get('risk_amt', 0)
    ex_date = sig.get('exit_date','')
    ex_rule = sig.get('exit_rule','')
    bear_b  = sig.get('bear_bonus', False)

    # Action emoji
    if action == 'DEPLOY':
        emoji = '✅'
    elif action == 'WATCH':
        emoji = '👁'
    else:
        emoji = '⚠️'

    # Signal arrow
    arrow = '▲' if signal in ('UP_TRI','BULL_PROXY') else '▼'

    # Bear bonus tag
    bear_tag = ' 🐻' if bear_b else ''

    # Target line
    if target:
        tgt_line = f"Target: ₹{target:,.2f} | R:R {rr}"
    else:
        tgt_line = f"Exit: {ex_date} open ({ex_rule})"

    # Expiry warning
    exp_warn = ''
    if sig.get('expiry_warn'):
        exp_warn = '\n⚠️ <i>Expiry week — consider reducing size</i>'

    block = (
        f"{emoji} <b>{symbol}</b> — {signal} {arrow}{bear_tag}\n"
        f"Score: {score}/10 | Age: {age} | {sector}\n"
        f"Regime: {regime} | Vol: {vol_q} | RS: {rs_q}\n"
        f"Entry: ~₹{entry:,.2f} (tomorrow 9:15 open)\n"
        f"Stop: ₹{stop:,.2f}\n"
        f"{tgt_line}\n"
        f"Size: {shares} shares | Risk: ₹{risk:,.0f}"
        f"{exp_warn}"
    )
    return block

def send_morning_alert(signals, market_info, exits_today,
                       open_positions, system_health):
    """Send the 8:45 AM morning alert"""
    today     = market_info.get('today','')
    regime    = market_info.get('regime','')
    reg_score = market_info.get('regime_score', 0)
    nifty_px  = market_info.get('nifty_price', 0)
    nifty_chg = market_info.get('nifty_change', 0)
    leaders   = market_info.get('sector_leaders', [])
    health    = system_health.get('health','NORMAL')
    health_wr = system_health.get('health_wr', 0)

    # Health emoji
    h_emoji = '🟢' if health=='HOT' else '🔴' if health=='COLD' else '🟡'

    # Bear bonus banner
    bear_banner = ''
    if regime == 'Bear':
        bear_banner = (
            '\n🐻 <b>BEAR BONUS ACTIVE</b> — '
            'UP_TRI highest conviction\n'
        )

    # Nifty arrow
    n_arrow = '▲' if nifty_chg >= 0 else '▼'
    n_sign  = '+' if nifty_chg >= 0 else ''

    # Header
    msg = (
        f"🔔 <b>TIE TIY MORNING SCAN — {today}</b>\n\n"
        f"📊 <b>MARKET</b>\n"
        f"Nifty: {nifty_px:,.0f} {n_arrow} {n_sign}{nifty_chg:.1f}%\n"
        f"Regime: <b>{regime}</b> | Score: {reg_score}"
        f"{bear_banner}\n"
    )

    # Sector leaders
    if leaders:
        msg += f"📈 Sector Leaders: {' | '.join(leaders)}\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"

    # Signals
    deploy = [s for s in signals if s.get('action')=='DEPLOY']
    watch  = [s for s in signals if s.get('action')=='WATCH']

    if not signals:
        msg += "📭 No signals today\n"
    else:
        msg += f"🚀 <b>SIGNALS TODAY — {len(signals)} found</b>\n\n"
        for i, sig in enumerate(deploy, 1):
            msg += f"{i}. {fmt_signal_block(sig)}\n\n"
        if watch:
            msg += f"👁 <b>WATCH ({len(watch)})</b>\n"
            for sig in watch:
                symbol = sig['symbol'].replace('.NS','')
                score  = sig.get('score',0)
                signal = sig.get('signal','')
                age    = sig.get('age',0)
                msg += (f"• {symbol} {signal} "
                        f"Age:{age} Score:{score}/10\n")

    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"

    # Exits today
    if exits_today:
        msg += "📤 <b>EXIT TODAY (9:15 open)</b>\n"
        for t in exits_today:
            stock  = t['stock'].replace('.NS','')
            signal = t['signal_type']
            entry  = t.get('entry_actual') or t.get('entry_estimate','')
            pnl    = t.get('pnl_pct','')
            pnl_s  = f" | Est P&L: {pnl}%" if pnl else ''
            msg += f"• {stock} {signal} — Entry ₹{entry}{pnl_s}\n"
        msg += "\n"

    # Active stops
    if open_positions:
        msg += "🛡 <b>ACTIVE STOPS</b>\n"
        for t in open_positions:
            stock  = t['stock'].replace('.NS','')
            stop   = t.get('stop_price','')
            day_n  = t.get('day_number','?')
            msg += f"• {stock}: Stop ₹{stop} (Day {day_n} of 6)\n"
        msg += "\n"

    # System health
    msg += (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{h_emoji} System: <b>{health}</b> "
        f"(WR {health_wr}% last 5)\n"
    )

    return send_message(msg)

def send_stop_alert(trade, current_price):
    """Send immediate stop hit alert"""
    stock  = trade['stock'].replace('.NS','')
    signal = trade['signal_type']
    entry  = trade.get('entry_actual') or trade.get('entry_estimate')
    stop   = trade['stop_price']
    msg = (
        f"🚨 <b>STOP HIT ALERT — {stock}</b>\n\n"
        f"Signal: {signal}\n"
        f"Entry: ₹{entry}\n"
        f"Stop: ₹{stop}\n"
        f"Current: ₹{current_price:,.2f} — "
        f"<b>STOP BREACHED</b>\n\n"
        f"⚡ Action: EXIT at next available price\n"
        f"Journal will be updated automatically"
    )
    return send_message(msg)

def send_large_move_alert(trade, current_price, move_pct, atr_mult):
    """Send large adverse move warning"""
    stock  = trade['stock'].replace('.NS','')
    signal = trade['signal_type']
    stop   = trade['stop_price']
    msg = (
        f"⚠️ <b>LARGE ADVERSE MOVE — {stock}</b>\n\n"
        f"Signal: {signal}\n"
        f"Today move: {move_pct:+.1f}% "
        f"({atr_mult:.1f}x ATR) against position\n"
        f"Stop not hit yet: ₹{stop}\n"
        f"Current: ₹{current_price:,.2f}\n\n"
        f"<i>Monitor closely. Possible news event.</i>"
    )
    return send_message(msg)

def send_eod_summary(open_positions, exits_done, market_info):
    """Send 3:35 PM EOD summary"""
    today = market_info.get('today','')
    msg   = f"📊 <b>TIE TIY EOD — {today}</b>\n\n"

    if open_positions:
        msg += "📈 <b>Open Positions</b>\n"
        for t in open_positions:
            stock  = t['stock'].replace('.NS','')
            signal = t['signal_type']
            pnl    = t.get('pnl_pct','')
            day_n  = t.get('day_number','?')
            pnl_s  = f"{pnl}%" if pnl else '—'
            msg += (f"→ {stock} {signal}: "
                    f"{pnl_s} (Day {day_n} of 6)\n")
    else:
        msg += "No open positions\n"

    if exits_done:
        msg += "\n✅ <b>Exited Today</b>\n"
        for t in exits_done:
            stock = t['stock'].replace('.NS','')
            pnl   = t.get('pnl_pct','')
            msg  += f"→ {stock}: {pnl}%\n"

    # Next exits
    msg += (
        f"\n<i>Next scheduled runs: "
        f"8:45 AM tomorrow</i>"
    )
    return send_message(msg)

def send_fno_change_alert(added, removed):
    """Alert when F&O universe changes"""
    if not added and not removed:
        return
    msg = "📋 <b>F&O UNIVERSE UPDATE</b>\n\n"
    if added:
        msg += "➕ Added:\n"
        for s in added:
            msg += f"• {s}\n"
    if removed:
        msg += "\n➖ Removed:\n"
        for s in removed:
            msg += f"• {s}\n"
        msg += ("\n⚠️ Check any open signals "
                "on removed stocks manually")
    return send_message(msg)

def send_holiday_notice(next_trading):
    """Alert on market holiday"""
    msg = (
        f"📅 <b>NSE Holiday today</b>\n"
        f"No scan. Next trading day: {next_trading}"
    )
    return send_message(msg)

def handle_command(command):
    """Handle Telegram commands from webhook"""
    from journal import (get_open_trades, get_recent_trades,
                         get_journal_summary, get_system_health)

    cmd = command.strip().lower()

    if cmd == '/status':
        open_t = get_open_trades()
        if not open_t:
            send_message("No open positions currently.")
            return
        msg = "📈 <b>Open Positions</b>\n\n"
        for t in open_t:
            stock  = t['stock'].replace('.NS','')
            signal = t['signal_type']
            entry  = t.get('entry_actual') or t.get('entry_estimate')
            stop   = t['stop_price']
            pnl    = t.get('pnl_pct','—')
            msg += (f"• {stock} {signal}\n"
                    f"  Entry: ₹{entry} | Stop: ₹{stop}\n"
                    f"  P&L: {pnl}%\n\n")
        send_message(msg)

    elif cmd == '/stops':
        open_t = get_open_trades()
        if not open_t:
            send_message("No active stops.")
            return
        msg = "🛡 <b>Active Stops</b>\n\n"
        for t in open_t:
            stock = t['stock'].replace('.NS','')
            stop  = t['stop_price']
            msg  += f"• {stock}: ₹{stop}\n"
        send_message(msg)

    elif cmd == '/journal':
        recent = get_recent_trades(10)
        if not recent:
            send_message("No completed trades yet.")
            return
        msg = "📓 <b>Last 10 Trades</b>\n\n"
        for t in recent:
            stock  = t['stock'].replace('.NS','')
            status = t['status']
            pnl    = t.get('pnl_pct','—')
            emoji  = '✅' if status=='WON' else '❌'
            msg   += f"{emoji} {stock}: {pnl}%\n"
        send_message(msg)

    elif cmd == '/score':
        health, wr = get_system_health()
        summary    = get_journal_summary()
        h_emoji = ('🟢' if health=='HOT'
                   else '🔴' if health=='COLD'
                   else '🟡')
        msg = (
            f"📊 <b>System Health</b>\n\n"
            f"{h_emoji} Status: {health}\n"
            f"WR last 5: {wr}%\n"
            f"Total trades: {summary['total_trades']}\n"
            f"Overall WR: {summary['win_rate']}%\n"
            f"Open: {summary['open_trades']}"
        )
        send_message(msg)

    elif cmd == '/help':
        msg = (
            "🤖 <b>TIE TIY Commands</b>\n\n"
            "/status  — open positions + P&L\n"
            "/stops   — all active stop levels\n"
            "/journal — last 10 trades\n"
            "/score   — system health\n"
            "/help    — this message"
        )
        send_message(msg)

    else:
        send_message(
            f"Unknown command: {command}\n"
            "Type /help for available commands"
        )
