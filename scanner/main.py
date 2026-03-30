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
    get_system_health, update_pnl, close_trade
)
from telegram_bot import (
    send_morning_alert, send_eod_summary,
    send_stop_alert, send_holiday_notice
)
from html_builder import build_html

NIFTY_SYMBOL = "^NSEI"

SECTOR_INDICES = {
    "Bank":   "^NSEBANK",
    "IT":     "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "Auto":   "^CNXAUTO",
    "Metal":  "^CNXMETAL",
    "Energy": "^CNXENERGY",
    "FMCG":   "^CNXFMCG",
    "Infra":  "^CNXINFRA",
}


def get_nifty_info():
    try:
        df = yf.download(NIFTY_SYMBOL, period='3mo',
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        closes     = df['Close']
        ema50      = closes.ewm(span=50).mean()
        slope      = ema50.diff(10) / ema50.shift(10)
        above      = closes > ema50
        last_slope = float(slope.iloc[-1])
        last_above = bool(above.iloc[-1])

        if last_slope > 0.005 and last_above:
            regime = 'Bull'
        elif last_slope < -0.005 and not last_above:
            regime = 'Bear'
        else:
            regime = 'Choppy'

        ret20     = (float(closes.iloc[-1]) /
                     float(closes.iloc[-20]) - 1) * 100
        s_ret     = (2 if ret20 > 5 else
                     1 if ret20 > 2 else
                    -2 if ret20 < -5 else
                    -1 if ret20 < -2 else 0)
        s_ema     = 1 if last_above else -1
        reg_score = int(np.clip(s_ret + s_ema, -4, 4))

        prev_close = float(closes.iloc[-2])
        last_close = float(closes.iloc[-1])
        nifty_chg  = ((last_close - prev_close) /
                      prev_close * 100)

        return {
            'regime':       regime,
            'regime_score': reg_score,
            'nifty_price':  round(last_close, 2),
            'nifty_change': round(nifty_chg, 2),
            'today':        date.today().strftime(
                                '%d %b %Y'),
        }
    except Exception as e:
        print(f"Nifty fetch error: {e}")
        return {
            'regime':       'Choppy',
            'regime_score': 0,
            'nifty_price':  0,
            'nifty_change': 0,
            'today':        date.today().strftime(
                                '%d %b %Y'),
        }


def get_sector_momentum():
    momentum = {}
    for sector, sym in SECTOR_INDICES.items():
        try:
            df = yf.download(sym, period='1mo',
                              progress=False,
                              auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            ret = (float(df['Close'].iloc[-1]) /
                   float(df['Close'].iloc[0]) - 1) * 100
            momentum[sector] = ('Leading' if ret > 2 else
                                 'Lagging' if ret < -2 else
                                 'Neutral')
        except:
            momentum[sector] = 'Neutral'
    return momentum


def get_sector_leaders(momentum):
    return [s for s, m in momentum.items()
            if m == 'Leading']


def check_exits():
    today  = date.today()
    trades = get_open_trades()
    exits  = []
    for t in trades:
        try:
            entry_d = datetime.strptime(
                t.get('entry_date', ''),
                '%Y-%m-%d').date()
            exit_d = days_until_exit(entry_d, 6)
            if exit_d <= today:
                exits.append(t)
                close_trade(
                    t['trade_id'],
                    t.get('current_price',
                          t.get('entry_actual', 0)),
                    'Day6')
        except:
            pass
    return exits


def check_stops():
    trades = get_open_trades()
    for t in trades:
        try:
            sym = t['stock']
            df  = yf.download(sym, period='2d',
                               progress=False,
                               auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            if df.empty:
                continue
            low     = float(df['Low'].iloc[-1])
            high    = float(df['High'].iloc[-1])
            stop    = float(t.get('stop_price', 0))
            sig_dir = t.get('direction', 'LONG')
            hit = (sig_dir == 'LONG'  and low  <= stop or
                   sig_dir == 'SHORT' and high >= stop)
            if hit:
                close_trade(t['trade_id'], stop, 'StopHit')
                send_stop_alert(t, stop)
                print(f"STOP HIT: {sym} @ {stop}")
        except Exception as e:
            print(f"Stop check error "
                  f"{t.get('stock','')}: {e}")


def run_morning_scan():
    status = get_market_status()
    if not status['is_trading']:
        print(f"Not a trading day: {status['reason']}")
        try:
            send_holiday_notice(status['reason'])
        except:
            pass
        return

    print("Fetching market data...")
    market_info     = get_nifty_info()
    sector_momentum = get_sector_momentum()
    market_info['sector_leaders'] = get_sector_leaders(
        sector_momentum)

    print(f"Regime: {market_info['regime']} "
          f"Score: {market_info['regime_score']}")

    universe   = load_universe()
    sector_map = get_sector_map()
    grade_map  = get_grade_map()

    try:
        nifty_df = yf.download(
            NIFTY_SYMBOL, period='3mo',
            progress=False, auto_adjust=True)
        if isinstance(nifty_df.columns, pd.MultiIndex):
            nifty_df.columns = [c[0]
                                 for c in nifty_df.columns]
        nifty_close = nifty_df['Close']
    except:
        nifty_close = None

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

    print(f"Raw signals before filter: {len(all_signals)}")

    # min_score=1 — age2/3 in non-bear score 1 point
    # (regime only). min_score=2 was dropping them.
    # WATCH/DEPLOY labels still separate quality tiers.
    signals = filter_signals(all_signals, min_score=1)
    print(f"Signals found: {len(signals)}")

    # Print breakdown for monitoring
    deploy = [s for s in signals
              if s.get('action') == 'DEPLOY']
    watch  = [s for s in signals
              if s.get('action') == 'WATCH']
    print(f"  DEPLOY: {len(deploy)}  "
          f"WATCH: {len(watch)}  "
          f"OTHER: {len(signals)-len(deploy)-len(watch)}")

    for sig in signals:
        try:
            log_signal(sig)
        except:
            pass

    open_trades  = get_open_trades()
    exits_today  = check_exits()
    recent       = get_recent_trades(10)
    health_s, hw = get_system_health()
    system_health = {
        'health':    health_s,
        'health_wr': hw,
    }

    send_morning_alert(
        signals, market_info, exits_today,
        open_trades, system_health
    )

    build_html(
        signals, market_info, sector_momentum,
        open_trades, recent, system_health
    )

    print("Morning scan complete.")


def run_stop_check():
    status = get_market_status()
    if not status['is_trading']:
        return
    print(f"Stop check — "
          f"{datetime.now().strftime('%H:%M')}")
    check_stops()


def run_eod():
    status = get_market_status()
    if not status['is_trading']:
        return
    print("EOD update...")
    market_info     = get_nifty_info()
    sector_momentum = get_sector_momentum()
    open_trades     = get_open_trades()

    for trade in open_trades:
        if trade.get('status') == 'OPEN':
            try:
                sym = trade['stock']
                df  = yf.download(
                    sym, period='5d',
                    progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0]
                                  for c in df.columns]
                current = float(df['Close'].iloc[-1])
                update_pnl(trade['trade_id'], current)
            except:
                pass

    exits_done   = check_exits()
    health_s, hw = get_system_health()
    system_health = {
        'health':    health_s,
        'health_wr': hw,
    }
    recent = get_recent_trades(10)

    build_html(
        [], market_info, sector_momentum,
        get_open_trades(), recent, system_health
    )
    send_eod_summary(open_trades, exits_done,
                     market_info)
    print("EOD complete.")


if __name__ == '__main__':
    mode = (sys.argv[1]
            if len(sys.argv) > 1 else 'morning')
    if mode == 'morning':
        run_morning_scan()
    elif mode == 'stops':
        run_stop_check()
    elif mode == 'eod':
        run_eod()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python main.py "
              "[morning|stops|eod]")
