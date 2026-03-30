import csv
import os
import sys
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(__file__))
from config import JOURNAL_DIR

JOURNAL_FILE = f"{JOURNAL_DIR}/trades.csv"
JOURNAL_COLS = [
    'trade_id','date_detected','stock',
    'signal_type','age','regime','regime_score',
    'vol_q','rs_q','sec_mom','bear_bonus',
    'conviction_score','action','entry_estimate',
    'entry_actual','stop_price','target_price',
    'exit_rule','exit_date_plan','exit_date_actual',
    'exit_price','exit_type','position_size',
    'risk_amount','pnl_pct','pnl_rs',
    'status','direction','notes',
]


def ensure_journal():
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    if not os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=JOURNAL_COLS)
            writer.writeheader()


def load_journal():
    ensure_journal()
    trades = []
    try:
        with open(JOURNAL_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(dict(row))
    except Exception as e:
        print(f"Journal load error: {e}")
    return trades


def save_journal(trades):
    ensure_journal()
    with open(JOURNAL_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(
            f, fieldnames=JOURNAL_COLS)
        writer.writeheader()
        for t in trades:
            row = {k: t.get(k, '')
                   for k in JOURNAL_COLS}
            writer.writerow(row)


def log_signal(sig):
    ensure_journal()
    today    = date.today().isoformat()
    stock    = sig.get('symbol', '')
    stype    = sig.get('signal', '')
    trade_id = (f"{today.replace('-','')}_{stock}"
                f".replace('.NS','')_{stype[:2]}")
    trades   = load_journal()
    # avoid duplicates
    for t in trades:
        if t['trade_id'] == trade_id:
            return
    row = {k: '' for k in JOURNAL_COLS}
    row.update({
        'trade_id':       trade_id,
        'date_detected':  today,
        'stock':          stock,
        'signal_type':    stype,
        'age':            sig.get('age', ''),
        'regime':         sig.get('regime', ''),
        'regime_score':   sig.get('regime_score', ''),
        'vol_q':          sig.get('vol_q', ''),
        'rs_q':           sig.get('rs_q', ''),
        'sec_mom':        sig.get('sec_mom', ''),
        'bear_bonus':     sig.get('bear_bonus', False),
        'conviction_score':sig.get('score', ''),
        'action':         sig.get('action', ''),
        'entry_estimate': sig.get('entry_est', ''),
        'stop_price':     sig.get('stop', ''),
        'target_price':   sig.get('target', ''),
        'exit_rule':      sig.get('exit_rule', ''),
        'exit_date_plan': sig.get('exit_date', ''),
        'position_size':  sig.get('shares', ''),
        'risk_amount':    sig.get('risk_amt', ''),
        'direction':      sig.get('direction', ''),
        'status':         'PENDING',
    })
    trades.append(row)
    save_journal(trades)


def update_pnl(trade_id, current_price):
    trades = load_journal()
    for t in trades:
        if t['trade_id'] == trade_id:
            try:
                entry = float(
                    t['entry_actual'] or
                    t['entry_estimate'] or 0)
                stop  = float(t['stop_price'] or 0)
                size  = int(t['position_size'] or 0)
                if entry <= 0:
                    break
                direction = (1 if entry > stop else -1)
                pnl_pct = (direction *
                           (current_price - entry) /
                           entry * 100)
                pnl_rs  = (direction *
                           (current_price - entry) *
                           size)
                t['pnl_pct'] = round(pnl_pct, 2)
                t['pnl_rs']  = round(pnl_rs, 0)
                t['status']  = 'OPEN'
            except:
                pass
            break
    save_journal(trades)


def close_trade(trade_id, exit_price, exit_type):
    trades = load_journal()
    for t in trades:
        if t['trade_id'] == trade_id:
            try:
                entry = float(
                    t['entry_actual'] or
                    t['entry_estimate'] or 0)
                stop  = float(t['stop_price'] or 0)
                size  = int(t['position_size'] or 0)
                direction = (1 if entry > stop else -1)
                pnl_pct = (direction *
                           (exit_price - entry) /
                           entry * 100
                           if entry > 0 else 0)
                pnl_rs = (direction *
                          (exit_price - entry) *
                          size)
                t['exit_price']       = exit_price
                t['exit_type']        = exit_type
                t['exit_date_actual'] = (
                    date.today().isoformat())
                t['pnl_pct'] = round(pnl_pct, 2)
                t['pnl_rs']  = round(pnl_rs, 0)
                t['status']  = (
                    'WON'     if pnl_pct > 0 else
                    'STOPPED' if exit_type == 'StopHit'
                    else 'EXITED')
            except:
                t['status'] = 'CLOSED'
            break
    save_journal(trades)


def get_open_trades():
    trades = load_journal()
    return [t for t in trades
            if t.get('status') in ('OPEN', 'PENDING')]


def get_recent_trades(n=10):
    trades = load_journal()
    closed = [t for t in trades
              if t.get('status') in
              ('WON', 'STOPPED', 'EXITED')]
    return closed[-n:]


def get_system_health():
    recent = get_recent_trades(5)
    if len(recent) < 3:
        return 'NORMAL', 0
    wins = sum(1 for t in recent
               if t.get('status') == 'WON')
    wr   = wins / len(recent) * 100
    if wr >= 70:   return 'HOT',    round(wr)
    if wr <= 40:   return 'COLD',   round(wr)
    return 'NORMAL', round(wr)


def get_journal_summary():
    trades  = load_journal()
    open_t  = get_open_trades()
    closed  = [t for t in trades
               if t.get('status') in
               ('WON', 'STOPPED', 'EXITED')]
    wins    = sum(1 for t in closed
                  if t.get('status') == 'WON')
    wr      = round(wins / len(closed) * 100) \
              if closed else 0
    health, hw = get_system_health()
    return {
        'total_trades':  len(trades),
        'open_trades':   len(open_t),
        'closed_trades': len(closed),
        'wins':          wins,
        'win_rate':      wr,
        'health':        health,
        'health_wr':     hw,
    }
