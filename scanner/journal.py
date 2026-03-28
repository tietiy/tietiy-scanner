import csv
import os
import sys
from datetime import date, datetime
sys.path.insert(0, os.path.dirname(__file__))
from config import JOURNAL_DIR

JOURNAL_FILE  = f"{JOURNAL_DIR}/trades.csv"
JOURNAL_COLS  = [
    'trade_id','date_detected','stock','signal_type',
    'age','regime','regime_score','vol_q','rs_q',
    'sec_mom','bear_bonus','conviction_score','action',
    'entry_type','entry_estimate','entry_actual',
    'stop_price','target_price','exit_rule',
    'exit_date_plan','exit_date_actual',
    'exit_price','exit_type','position_size',
    'risk_amount','pnl_pct','pnl_rs',
    'status','notes'
]

def ensure_journal():
    """Create journal file if it doesn't exist"""
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    if not os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=JOURNAL_COLS)
            writer.writeheader()

def load_journal():
    """Load all trades from journal"""
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
    """Save all trades back to journal"""
    ensure_journal()
    with open(JOURNAL_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=JOURNAL_COLS)
        writer.writeheader()
        writer.writerows(trades)

def generate_trade_id(stock, signal, date_str):
    """Generate unique trade ID"""
    d = date_str.replace('-','')
    s = stock.replace('.NS','').replace('&','')
    return f"{d}_{s}_{signal[:2]}"

def log_signal(sig):
    """
    Log a new signal to journal.
    Called when signal is first detected.
    """
    trades = load_journal()
    trade_id = generate_trade_id(
        sig['symbol'], sig['signal'],
        date.today().isoformat()
    )
    # Check if already logged today
    for t in trades:
        if t['trade_id'] == trade_id:
            return trade_id

    row = {
        'trade_id':        trade_id,
        'date_detected':   date.today().isoformat(),
        'stock':           sig['symbol'],
        'signal_type':     sig['signal'],
        'age':             sig.get('age',''),
        'regime':          sig.get('regime',''),
        'regime_score':    sig.get('regime_score',''),
        'vol_q':           sig.get('vol_q',''),
        'rs_q':            sig.get('rs_q',''),
        'sec_mom':         sig.get('sec_mom',''),
        'bear_bonus':      sig.get('bear_bonus',''),
        'conviction_score':sig.get('score',''),
        'action':          sig.get('action',''),
        'entry_type':      'NextDayOpen',
        'entry_estimate':  sig.get('entry_est',''),
        'entry_actual':    '',
        'stop_price':      sig.get('stop',''),
        'target_price':    sig.get('target',''),
        'exit_rule':       sig.get('exit_rule',''),
        'exit_date_plan':  sig.get('exit_date',''),
        'exit_date_actual':'',
        'exit_price':      '',
        'exit_type':       '',
        'position_size':   sig.get('shares',''),
        'risk_amount':     sig.get('risk_amt',''),
        'pnl_pct':         '',
        'pnl_rs':          '',
        'status':          'PENDING',
        'notes':           '',
    }
    trades.append(row)
    save_journal(trades)
    return trade_id

def update_entry(trade_id, actual_entry):
    """Update with actual entry price after open"""
    trades = load_journal()
    for t in trades:
        if t['trade_id'] == trade_id:
            t['entry_actual'] = actual_entry
            t['status']       = 'OPEN'
            break
    save_journal(trades)

def update_pnl(trade_id, current_price):
    """Update P&L for open trade"""
    trades = load_journal()
    for t in trades:
        if t['trade_id'] == trade_id and t['status'] == 'OPEN':
            try:
                entry = float(t['entry_actual'] or
                              t['entry_estimate'])
                stop  = float(t['stop_price'])
                size  = int(t['position_size'] or 0)
                # Long or short
                direction = 1 if entry > stop else -1
                pnl_pct = direction*(current_price-entry)/entry*100
                pnl_rs  = direction*(current_price-entry)*size
                t['pnl_pct'] = round(pnl_pct, 2)
                t['pnl_rs']  = round(pnl_rs, 0)
            except:
                pass
            break
    save_journal(trades)

def close_trade(trade_id, exit_price, exit_type):
    """Close a trade with final price"""
    trades = load_journal()
    for t in trades:
        if t['trade_id'] == trade_id:
            try:
                entry = float(t['entry_actual'] or
                              t['entry_estimate'])
                stop  = float(t['stop_price'])
                size  = int(t['position_size'] or 0)
                direction = 1 if entry > stop else -1
                pnl_pct = direction*(exit_price-entry)/entry*100
                pnl_rs  = direction*(exit_price-entry)*size
                t['exit_price']       = exit_price
                t['exit_type']        = exit_type
                t['exit_date_actual'] = date.today().isoformat()
                t['pnl_pct']          = round(pnl_pct, 2)
                t['pnl_rs']           = round(pnl_rs, 0)
                t['status'] = ('WON' if pnl_pct > 0
                               else 'STOPPED' if exit_type == 'Stop'
                               else 'EXITED')
            except:
                t['status'] = 'CLOSED'
            break
    save_journal(trades)

def get_open_trades():
    """Returns all open trades"""
    trades = load_journal()
    return [t for t in trades
            if t['status'] in ('OPEN', 'PENDING')]

def get_recent_trades(n=10):
    """Returns last n closed trades"""
    trades = load_journal()
    closed = [t for t in trades
              if t['status'] in ('WON','STOPPED','EXITED')]
    return closed[-n:]

def get_system_health():
    """
    Returns system health based on recent performance.
    HOT = WR >= 70% last 5 trades
    COLD = WR <= 40% last 5 trades
    NORMAL = everything else
    """
    recent = get_recent_trades(5)
    if len(recent) < 3:
        return 'NORMAL', len(recent)
    wins = sum(1 for t in recent if t['status'] == 'WON')
    wr   = wins / len(recent) * 100
    if wr >= 70:
        return 'HOT', round(wr)
    elif wr <= 40:
        return 'COLD', round(wr)
    return 'NORMAL', round(wr)

def get_journal_summary():
    """Returns summary stats for Telegram"""
    trades  = load_journal()
    open_t  = [t for t in trades if t['status'] == 'OPEN']
    closed  = [t for t in trades
               if t['status'] in ('WON','STOPPED','EXITED')]
    wins    = sum(1 for t in closed if t['status'] == 'WON')
    wr      = round(wins/len(closed)*100) if closed else 0
    health, health_wr = get_system_health()
    return {
        'total_trades':  len(trades),
        'open_trades':   len(open_t),
        'closed_trades': len(closed),
        'wins':          wins,
        'win_rate':      wr,
        'health':        health,
        'health_wr':     health_wr,
    }
