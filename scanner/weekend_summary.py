# scanner/weekend_summary.py
# Sends weekly recap on Saturday morning
# Triggered by cron-job.org on Saturdays at 9 AM IST
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from journal import load_history, get_open_trades
from telegram_bot import send_weekend_summary

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')


def _get_week_start():
    """Returns Monday of current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def run_weekend_summary():
    """
    Compiles weekly stats and sends Telegram summary.
    Only runs on Saturday (weekday == 5).
    """
    print("[weekend_summary] Starting...")
    
    today = date.today()
    
    # Only run on Saturday
    if today.weekday() != 5:
        print(f"[weekend_summary] Not Saturday (weekday={today.weekday()}) — skipping")
        return
    
    week_start = _get_week_start()
    week_start_str = week_start.isoformat()
    
    print(f"[weekend_summary] Week: {week_start_str} to {today.isoformat()}")
    
    history = load_history()
    
    # Find signals resolved this week
    resolved_this_week = [
        s for s in history
        if s.get('result') in ('WON', 'STOPPED', 'EXITED')
        and s.get('action') == 'TOOK'
        and s.get('exit_date_actual', '') >= week_start_str
    ]
    
    wins   = len([s for s in resolved_this_week if s.get('result') == 'WON'])
    losses = len([s for s in resolved_this_week if s.get('result') == 'STOPPED'])
    flats  = len([s for s in resolved_this_week if s.get('result') == 'EXITED'])
    
    total = wins + losses + flats
    win_rate = round(wins / total * 100) if total > 0 else 0
    
    # Active signals
    active = get_open_trades()
    
    # Next exit dates
    next_exits = []
    for s in active:
        ed = s.get('exit_date', '')
        if ed and ed > today.isoformat():
            try:
                d = datetime.strptime(ed, '%Y-%m-%d')
                next_exits.append(d.strftime('%b %d'))
            except Exception:
                pass
    next_exits = sorted(set(next_exits))[:3]
    
    # Top winner / loser
    top_winner = None
    top_loser = None
    
    if resolved_this_week:
        sorted_by_pnl = sorted(
            resolved_this_week,
            key=lambda x: float(x.get('pnl_pct') or 0),
            reverse=True
        )
        if sorted_by_pnl:
            top_winner = sorted_by_pnl[0]
            top_loser = sorted_by_pnl[-1]
    
    stats = {
        'resolved':    total,
        'wins':        wins,
        'losses':      losses,
        'flats':       flats,
        'win_rate':    win_rate,
        'active':      len(active),
        'next_exits':  next_exits,
        'top_winner':  top_winner if top_winner and (top_winner.get('pnl_pct') or 0) > 0 else None,
        'top_loser':   top_loser if top_loser and (top_loser.get('pnl_pct') or 0) < 0 else None,
    }
    
    print(f"[weekend_summary] Stats: {stats}")
    
    try:
        send_weekend_summary(stats)
        print("[weekend_summary] Telegram sent")
    except Exception as e:
        print(f"[weekend_summary] Telegram error: {e}")
    
    print("[weekend_summary] Done")


if __name__ == '__main__':
    run_weekend_summary()
