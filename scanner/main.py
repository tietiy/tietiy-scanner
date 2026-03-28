import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date, datetime

from config import DATA_DIR, OUTPUT_DIR, JOURNAL_DIR
from calendar_utils import (
    is_trading_day, get_market_status,
    next_trading_day, days_until_exit
)
from universe import load_universe, get_sector_map, get_grade_map
from scanner_core import prepare, detect_signals
from scorer import enrich_signal, filter_signals
from journal import (
    log_signal, get_open_trades, get_recent_trades,
    get_system_health, get_journal_summary,
    update_pnl, close_trade
)
from telegram_bot import (
    send_morning_alert, send_eod_summary,
    send_stop_alert, send_large_move_alert,
    send_holiday_notice, send_fno_change_alert
)
from html_builder import build_html

NIFTY_SYMBOL   = "^NSEI"
SECTOR_INDICES = {
    "Bank":    "^NSEBANK",
    "IT":      "^CNXIT",
    "Pharma":  "^CNXPHARMA",
    "Auto":    "^CNXAUTO",
    "Metal":   "^CNXMETAL",
    "Energy":  "^CNXENERGY",
    "FMCG":    "^CNXFMCG",
    "Infra":   "^CNXINFRA",
}

def get_nifty_info():
    """Fetch Nifty price and regime"""
    try:
        df = yf.download(NIFTY_SYMBOL, period='3mo',
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        closes   = df['Close']
        ema50    = closes.ewm(span=50).mean()
        slope    = ema50.diff(10) / ema50.shift(10)
        above    = closes > ema50
        last_slope = slope.iloc[-1]
        last_above = above.iloc[-1]

        if last_slope > 0.005 and last_above:
            regime = 'Bull'
        elif last_slope < -0.005 and not last_above:
            regime = 'Bear'
        else:
            regime = 'Choppy'

        # Regime score
        ret20    = (closes.iloc[-1]/closes.iloc[-20]-1)*100
        s_ret    = 2 if ret20>5 else 1 if ret20>2 else -2 if ret20<-5 else -1 if ret20<-2 else 0
        s_ema    = 1 if last_above else -1
        reg_score= int(np.clip(s_ret+s_ema, -4, 4))

        # Price change
        prev_close = closes.iloc[-2]
        last_close = closes.iloc[-1]
        chg_pct    = (last_close-prev_close)/prev_close*100

        return {
            'regime':       regime,
            'regime_score': reg_score,
            'nifty_price':  round(float(last_close), 0),
            'nifty_change': round(float(chg_pct), 2),
            'today':        date.today().strftime('%d %b %Y'),
        }
    except Exception as e:
        print(f"Nifty fetch error: {e}")
        return {
            'regime':'Unknown','regime_score':0,
            'nifty_price':0,'nifty_change':0,
            'today':date.today().strftime('%d %b %Y'),
        }

def get_sector_momentum():
    """Get sector momentum vs Nifty"""
    momentum = {}
    try:
        nifty = yf.download(NIFTY_SYMBOL, period='2mo',
                            progress=False, auto_adjust=True)
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = [c[0] for c in nifty.columns]
        nifty_ret = nifty['Close'].pct_change(20).iloc[-1]

        for sec, sym in SECTOR_INDICES.items():
            try:
                df = yf.download(sym, period='2mo',
                                 progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                sec_ret = df['Close'].pct_change(20).iloc[-1]
                diff    = sec_ret - nifty_ret
                if diff > 0.03:
                    momentum[sec] = 'Leading'
                elif diff < -0.03:
                    momentum[sec] = 'Lagging'
                else:
                    momentum[sec] = 'Neutral'
            except:
                momentum[sec] = 'Neutral'
    except Exception as e:
        print(f"Sector momentum error: {e}")
        for sec in SECTOR_INDICES:
            momentum[sec] = 'Neutral'
    return momentum

def get_sector_leaders(sector_momentum):
    return [s for s,m in sector_momentum.items() if m=='Leading']

def check_stops():
    """Check open trades for stop hits"""
    open_trades = get_open_trades()
    if not open_trades:
        return
    for trade in open_trades:
        if trade['status'] != 'OPEN':
            continue
        try:
            sym   = trade['stock']
            entry = float(trade.get('entry_actual') or
                         trade.get('entry_estimate',0))
            stop  = float(trade['stop_price'])
            atr   = float(trade.get('atr', 0)) or 1

            df = yf.download(sym, period='5d',
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            current = float(df['Close'].iloc[-1])
            direction = 1 if entry > stop else -1

            # Update P&L
            update_pnl(trade['trade_id'], current)

            # Stop hit check
            stop_hit = (direction==1 and current<=stop) or \
                       (direction==-1 and current>=stop)
            if stop_hit:
                send_stop_alert(trade, current)
                close_trade(trade['trade_id'], stop, 'Stop')
                continue

            # Large move check
            prev_close = float(df['Close'].iloc[-2])
            move_pct   = (current-prev_close)/prev_close*100
            adverse    = (direction==1 and move_pct<0) or \
                         (direction==-1 and move_pct>0)
            if adverse and abs(move_pct) > 2*atr/entry*100:
                atr_mult = abs(move_pct)/(atr/entry*100)
                send_large_move_alert(
                    trade, current, move_pct, atr_mult)

        except Exception as e:
            print(f"Stop check error {trade['stock']}: {e}")

def check_exits():
    """Check for trades that should exit today"""
    open_trades = get_open_trades()
    today       = date.today().isoformat()
    exits       = []
    for trade in open_trades:
        plan = trade.get('exit_date_plan','')
        if plan and plan <= today:
            exits.append(trade)
    return exits

def run_morning_scan():
    """Main 8:45 AM scan"""
    print(f"TIE TIY Morning Scan — {date.today()}")

    # Calendar check
    status = get_market_status()
    if not status['is_trading']:
        msg = send_holiday_notice(status['next_trading'])
        print(f"Not a trading day: {status['reason']}")
        return

    # Market info
    print("Fetching market data...")
    market_info      = get_nifty_info()
    sector_momentum  = get_sector_momentum()
    market_info['sector_leaders'] = get_sector_leaders(
        sector_momentum)

    print(f"Regime: {market_info['regime']} "
          f"Score: {market_info['regime_score']}")

    # Load universe
    universe   = load_universe()
    sector_map = get_sector_map()
    grade_map  = get_grade_map()

    # Fetch Nifty close series for RS calc
    try:
        nifty_df    = yf.download(NIFTY_SYMBOL, period='3mo',
                                  progress=False, auto_adjust=True)
        if isinstance(nifty_df.columns, pd.MultiIndex):
            nifty_df.columns = [c[0] for c in nifty_df.columns]
        nifty_close = nifty_df['Close']
    except:
        nifty_close = None

    # Scan all stocks
    all_signals = []
    print(f"Scanning {len(universe)} stocks...")
    for sym in universe:
        try:
            df = prepare(sym, period='1y')
            if df is None:
                continue
            sector = sector_map.get(sym, 'Other')
            sigs   = detect_signals(
                df, sym, sector,
                market_info['regime'],
                market_info['regime_score'],
                sector_momentum,
                nifty_close
            )
            grade = grade_map.get(sym, 'B')
            for sig in sigs:
                sig = enrich_signal(sig, grade)
                all_signals.append(sig)
        except Exception as e:
            print(f"Scan error {sym}: {e}")
            continue

    # Filter — min score 3
    signals = filter_signals(all_signals, min_score=3)
    print(f"Signals found: {len(signals)}")

    # Log to journal
    for sig in signals:
        log_signal(sig)

    # Get journal data
    open_trades  = get_open_trades()
    exits_today  = check_exits()
    recent       = get_recent_trades(10)
    health_s, hw = get_system_health()
    system_health = {
        'health':    health_s,
        'health_wr': hw,
    }

    # Send Telegram alert
    send_morning_alert(
        signals, market_info, exits_today,
        open_trades, system_health
    )

    # Build HTML
    build_html(
        signals, market_info, sector_momentum,
        open_trades, recent, system_health
    )

    print("Morning scan complete.")

def run_stop_check():
    """Stop monitoring run"""
    status = get_market_status()
    if not status['is_trading']:
        return
    print(f"Stop check — {datetime.now().strftime('%H:%M')}")
    check_stops()

def run_eod():
    """3:35 PM EOD run"""
    status = get_market_status()
    if not status['is_trading']:
        return
    print("EOD update...")
    market_info     = get_nifty_info()
    sector_momentum = get_sector_momentum()
    open_trades     = get_open_trades()

    # Update all P&L
    for trade in open_trades:
        if trade['status'] == 'OPEN':
            try:
                sym = trade['stock']
                df  = yf.download(sym, period='5d',
                                  progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                current = float(df['Close'].iloc[-1])
                update_pnl(trade['trade_id'], current)
            except:
                pass

    exits_done = check_exits()
    health_s, hw = get_system_health()
    system_health = {'health':health_s,'health_wr':hw}

    # Rebuild HTML with updated P&L
    recent = get_recent_trades(10)
    build_html(
        [], market_info, sector_momentum,
        get_open_trades(), recent, system_health
    )

    send_eod_summary(open_trades, exits_done, market_info)
    print("EOD complete.")

# ── ENTRY POINT ───────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv)>1 else 'morning'
    if mode == 'morning':
        run_morning_scan()
    elif mode == 'stops':
        run_stop_check()
    elif mode == 'eod':
        run_eod()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python main.py [morning|stops|eod]")
