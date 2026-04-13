# scanner/weekend_summary.py
# Sends weekly recap on Saturday morning
# Triggered by cron-job.org on Saturdays at 9 AM IST
#
# V1 FIX — W1:
# - Resolved signals now detected via `outcome` field
#   (TARGET_HIT / STOP_HIT / DAY6_WIN / DAY6_LOSS / DAY6_FLAT)
#   NOT via `result` field (WON/STOPPED/EXITED) which is
#   often still PENDING on live-resolved signals
# - Week filter now uses `outcome_date` with `exit_date`
#   as fallback — `exit_date_actual` was frequently None
# - gen=1 filter — backfill signals excluded from stats
# - Win/loss/flat classification aligned to outcome values
# - top_winner / top_loser only from signals with pnl_pct
# - Added signal type breakdown to stats payload
# - Added phase progress (resolved vs 30 target)
#
# V1.1 FIX — TR5:
# - --force flag bypasses Saturday check for testing
# ─────────────────────────────────────────────────────

import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from journal       import load_history, get_open_trades
from telegram_bot  import send_weekend_summary

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

# ── OUTCOME SETS (aligned to outcome_evaluator) ───────
OUTCOME_WIN  = {'TARGET_HIT', 'DAY6_WIN'}
OUTCOME_LOSS = {'STOP_HIT',   'DAY6_LOSS'}
OUTCOME_FLAT = {'DAY6_FLAT'}
OUTCOME_DONE = OUTCOME_WIN | OUTCOME_LOSS | OUTCOME_FLAT

RESOLVED_TARGET = 30   # Phase 2 unlock threshold


def _get_week_start():
    """Returns Monday of current week as date."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def _resolve_date(sig):
    """
    Best available date for when signal was resolved.
    Priority: outcome_date → exit_date_actual → exit_date
    """
    return (
        sig.get('outcome_date')     or
        sig.get('exit_date_actual') or
        sig.get('exit_date')        or ''
    )


def run_weekend_summary():
    """
    Compiles weekly stats and sends Telegram summary.
    Only runs on Saturday (weekday == 5).
    Use --force flag to bypass Saturday check for testing.
    """
    print("[weekend_summary] Starting...")

    today = date.today()

    # TR5 FIX: --force bypasses Saturday check
    force = '--force' in sys.argv
    if today.weekday() != 5 and not force:
        print(f"[weekend_summary] Not Saturday "
              f"(weekday={today.weekday()}) — skipping. "
              f"Use --force to run anyway.")
        return
    if force:
        print("[weekend_summary] --force flag — "
              "bypassing Saturday check")

    week_start     = _get_week_start()
    week_start_str = week_start.isoformat()
    today_str      = today.isoformat()

    print(f"[weekend_summary] Week: "
          f"{week_start_str} → {today_str}")

    history = load_history()

    # ── W1 FIX: use outcome field + gen=1 filter ──────
    # Live signals only (gen=1), resolved via outcome field
    live_all = [
        s for s in history
        if (s.get('generation', 1) or 1) >= 1
        and s.get('layer')  == 'MINI'
        and s.get('action') == 'TOOK'
    ]

    # All-time resolved live signals (for phase progress)
    all_resolved = [
        s for s in live_all
        if (s.get('outcome') or '') in OUTCOME_DONE
    ]

    # Resolved THIS WEEK — use best available date
    resolved_this_week = [
        s for s in all_resolved
        if _resolve_date(s) >= week_start_str
    ]

    # W/L/F classification from outcome values
    wins   = [s for s in resolved_this_week
              if s.get('outcome') in OUTCOME_WIN]
    losses = [s for s in resolved_this_week
              if s.get('outcome') in OUTCOME_LOSS]
    flats  = [s for s in resolved_this_week
              if s.get('outcome') in OUTCOME_FLAT]

    total    = len(resolved_this_week)
    win_rate = round(len(wins) / total * 100) \
               if total > 0 else 0

    # ── SIGNAL TYPE BREAKDOWN (this week) ─────────────
    type_counts = {}
    for s in resolved_this_week:
        t = s.get('signal', 'Unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    # ── ACTIVE SIGNALS ────────────────────────────────
    active = get_open_trades()

    # Next exit dates (from active signals)
    next_exits = []
    for s in active:
        ed = s.get('exit_date') or ''
        if ed and ed > today_str:
            try:
                d = datetime.strptime(ed, '%Y-%m-%d')
                next_exits.append(d.strftime('%b %d'))
            except Exception:
                pass
    next_exits = sorted(set(next_exits))[:3]

    # ── TOP WINNER / LOSER (this week) ────────────────
    with_pnl = [
        s for s in resolved_this_week
        if s.get('pnl_pct') is not None
    ]
    top_winner = None
    top_loser  = None

    if with_pnl:
        by_pnl = sorted(
            with_pnl,
            key=lambda x: float(x.get('pnl_pct') or 0),
            reverse=True)
        best  = by_pnl[0]
        worst = by_pnl[-1]
        if float(best.get('pnl_pct')  or 0) > 0:
            top_winner = best
        if float(worst.get('pnl_pct') or 0) < 0:
            top_loser  = worst

    # ── PHASE PROGRESS ────────────────────────────────
    total_resolved_live = len(all_resolved)
    phase_note = None
    if total_resolved_live >= RESOLVED_TARGET:
        phase_note = (
            f"Phase 2 unlocked: "
            f"{total_resolved_live} resolved")
    else:
        remaining = RESOLVED_TARGET - total_resolved_live
        phase_note = (
            f"Phase 1: {total_resolved_live}/"
            f"{RESOLVED_TARGET} resolved "
            f"({remaining} to unlock)")

    # ── ASSEMBLE STATS ────────────────────────────────
    stats = {
        'resolved':    total,
        'wins':        len(wins),
        'losses':      len(losses),
        'flats':       len(flats),
        'win_rate':    win_rate,
        'active':      len(active),
        'next_exits':  next_exits,
        'top_winner':  top_winner,
        'top_loser':   top_loser,
        'type_counts':         type_counts,
        'phase_note':          phase_note,
        'total_resolved_live': total_resolved_live,
        'week_start':          week_start_str,
    }

    print(f"[weekend_summary] "
          f"resolved={total} "
          f"W={len(wins)} "
          f"L={len(losses)} "
          f"F={len(flats)} "
          f"WR={win_rate}% "
          f"active={len(active)} "
          f"phase={phase_note}")

    try:
        send_weekend_summary(stats)
        print("[weekend_summary] Telegram sent")
    except Exception as e:
        print(f"[weekend_summary] Telegram error: {e}")

    print("[weekend_summary] Done")


if __name__ == '__main__':
    run_weekend_summary()
