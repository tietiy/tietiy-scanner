import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

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
    get_system_health, update_pnl, close_trade, check_exits
)
from telegram_bot import (
    send_morning_alert, send_eod_summary,
    send_stop_alert, send_holiday_notice
)
from html_builder import build_html

NIFTY_SYMBOL   = "^NSEI"
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
        last_slope = slope.iloc[-1]
        last_above = bool(above.iloc[-1])

        if last_slope > 0.005 and last_above:
            regime = 'Bull'
        elif last_slope < -0.005 and not last_above:
            regime = 'Bear'
        else:
            regime = 'Choppy'

        ret20        = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100
        regime_score = (2 if ret20 > 5 else 1 if ret20 > 2
                        else -1 if ret20 < -2 else 0)

        return {
            'regime':       regime,
            'regime_score': regime_score,
            'nifty_close':  round(float(closes.iloc[-1]), 2),
            'ret20':        round(float(ret20), 2),
            'sector_leaders': []
        }
    except Exception as e:
        print(f"Nifty info error: {e}")
        return {
            'regime': 'Choppy', 'regime_score': 0,
            'nifty_close': 0, 'ret20': 0,
            'sector_leaders': []
        }


def get_sector_momentum():
    momentum = {}
    for sector, sym in SECTOR_INDICES.items():
        try:
            df = yf.download(sym, period='1mo',
                             progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            closes = df['Close']
            ret    = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
            momentum[sector] = round(float(ret), 2)
        except:
            momentum[sector] = 0.0
    return momentum


def get_sector_leaders(momentum):
    sorted_s = sorted(momentum.items(),
                      key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_s[:3]]


def check_stops():
    open_trades = get_open_trades()
    for trade in open_trades:
        if trade.get('status') != 'OPEN':
            continue
        try:
            sym = trade['stock']
            df  = yf.download(sym, period='5d',
                              progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            low     = float(df['Low'].iloc[-1])
            stop    = float(trade.get('stop', 0))
            if low <= stop:
                close_trade(trade['trade_id'], stop, 'STOP')
                send_stop_alert(trade, stop)
        except:
            pass


# ── SCAN LOG WRITER ───────────────────────────────
def write_scan_log(signals, scan_date):
    import json
    log_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        '..', 'docs', 'scan_log.json'
    ))

    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log = json.load(f)
    else:
        log = []

    entry = {
        "date": scan_date,
        "signals": [
            {
                "stock":  s.get('stock', ''),
                "signal": s.get('signal', ''),
                "score":  s.get('score', 0),
                "entry":  round(float(s.get('entry', 0)), 2),
                "stop":   round(float(s.get('stop', 0)), 2),
                "target": round(float(s.get('target', 0)), 2),
                "age":    s.get('age', 0),
                "sector": s.get('sector', ''),
                "grade":  s.get('grade', 'B'),
            }
            for s in signals
        ]
    }

    log = [e for e in log if e.get('date') != scan_date]
    log.append(entry)
    log = sorted(log, key=lambda x: x['date'])[-30:]

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w') as f:
        json.dump(log, f, indent=2)

    print(f"Scan log written — {len(signals)} signals for {scan_date}")


# ── MORNING SCAN ──────────────────────────────────
def run_morning_scan():
    status = get_market_status()
    if not status['is_trading']:
        print(f"Not a trading day: {status['reason']}")
        send_holiday_notice(status['reason'])
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
            nifty_df.columns = [c[0] for c in nifty_df.columns]
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

    signals = filter_signals(all_signals, min_score=2)
    print(f"Signals found: {len(signals)}")

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

    write_scan_log(signals, date.today().isoformat())

    print("Morning scan complete.")


# ── STOP CHECK ────────────────────────────────────
def run_stop_check():
    status = get_market_status()
    if not status['is_trading']:
        return
    print(f"Stop check — {datetime.now().strftime('%H:%M')}")
    check_stops()


# ── EOD UPDATE ────────────────────────────────────
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
                    df.columns = [c[0] for c in df.columns]
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
    send_eod_summary(open_trades, exits_done, market_info)
    print("EOD complete.")


# ── ENTRY POINT ───────────────────────────────────
if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'morning'
    if mode == 'morning':
        run_morning_scan()
    elif mode == 'stops':
        run_stop_check()
    elif mode == 'eod':
        run_eod()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python main.py [morning|stops|eod]")
