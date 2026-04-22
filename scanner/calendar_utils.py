# ── calendar_utils.py ────────────────────────────────
# Trading day + holiday helpers
#
# F1 FIX (Apr 20 2026):
# Imports NSE_HOLIDAYS_2026 from meta_writer as the
# SINGLE SOURCE OF TRUTH. Previously this file had
# its own hardcoded list that diverged from
# meta_writer.py, causing silent scanner failures
# on real NSE holidays (Ram Navami Apr 2, Mahavir
# Jayanti Apr 6, etc.).
#
# Old behavior:
#   calendar_utils.NSE_HOLIDAYS (10 entries, wrong dates)
#   meta_writer.NSE_HOLIDAYS_2026 (15 entries, correct)
# New behavior:
#   Both files use meta_writer.NSE_HOLIDAYS_2026
#
# 2025 holidays retained as separate set for any
# historical backtest date lookups.
#
# WAVE 1 FIXES (Apr 23 2026 night):
# - Added ist_today() — UTC-safe IST date helper.
#   Kills H-09 (date.today() UTC drift across 5+ files).
# - Added ist_now() — UTC-safe IST datetime helper.
#   Kills M-06 (duplicated IST helpers in 5 files).
# - Expanded is_trading_day(d=None, holidays=None) —
#   accepts optional external holiday list. Kills
#   H-03 (duplicated _is_trading_day in 4 files —
#   all can now import this one).
# - All 3 helpers are the canonical source going
#   forward. Any new file must import from here,
#   not reimplement.
# ─────────────────────────────────────────────────────

from datetime import date, datetime, timedelta, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# F1: Import 2026 holidays from meta_writer (source of truth)
from meta_writer import NSE_HOLIDAYS_2026 as _HOLIDAYS_2026_STR

# Convert string dates to date objects
_HOLIDAYS_2026 = {
    date(int(d[:4]), int(d[5:7]), int(d[8:10]))
    for d in _HOLIDAYS_2026_STR
}

# Historical 2025 holidays — kept in-file for backtest lookups
_HOLIDAYS_2025 = {
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Eid ul-Fitr
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Dussehra
    date(2025, 10, 22),  # Diwali Laxmi Puja
    date(2025, 11, 5),   # Gurunanak Jayanti
    date(2025, 12, 25),  # Christmas
}

# Combined set for is_trading_day() lookups
NSE_HOLIDAYS = _HOLIDAYS_2025 | _HOLIDAYS_2026

# ── WAVE 1: IST OFFSET ───────────────────────────────
# GitHub Actions runners are UTC. Any use of
# date.today() or datetime.now() returns UTC, which
# at 11:30 PM IST is still "yesterday" in UTC.
# Always use the helpers below, never bare date.today().
_IST_OFFSET = timezone(timedelta(hours=5, minutes=30))


def ist_now():
    """
    WAVE 1 FIX: Returns current datetime in IST timezone.
    Replaces datetime.now() / datetime.utcnow() usage
    across the codebase. Safe on GitHub Actions (UTC)
    and any other server.

    Usage:
      now = ist_now()
      hour = now.hour        # IST hour
      ts   = now.strftime('%I:%M %p IST')
    """
    return datetime.now(tz=_IST_OFFSET)


def ist_today():
    """
    WAVE 1 FIX: Returns current date in IST.
    Replaces date.today() which returns UTC date on
    GitHub Actions runners — causing signal dates,
    exit dates, and resolution dates to drift by one
    day for runs between UTC midnight and IST midnight.

    H-09 killed: 5+ files using date.today() must
    switch to this helper.

    Usage:
      today = ist_today()
      if today < exit_date: ...
    """
    return ist_now().date()


def is_trading_day(d=None, holidays=None):
    """
    WAVE 1 FIX: Returns True if date d is a trading day
    (weekday AND not an NSE holiday).

    Expanded signature:
      d        — date, datetime, ISO string, or None.
                 Defaults to ist_today() when not given.
      holidays — optional iterable of holiday strings
                 ('YYYY-MM-DD') OR date objects. If
                 supplied, uses that set instead of
                 the built-in NSE_HOLIDAYS. This lets
                 callers reading nse_holidays.json pass
                 their loaded list for consistency.

    H-03 killed: 4 files with their own
    _is_trading_day() can now all import and call
    this. Backward-compatible: no-arg call still works.
    """
    # Normalize d
    if d is None:
        d = ist_today()
    elif isinstance(d, str):
        d = date.fromisoformat(d)
    elif isinstance(d, datetime):
        d = d.date()

    # Weekend check
    if d.weekday() >= 5:
        return False

    # Holiday check — external list wins if provided
    if holidays is not None:
        # Normalize incoming holidays to a set of strings
        # (fast lookup) and a set of dates (flex).
        ext_strs = set()
        for h in holidays:
            if isinstance(h, str):
                ext_strs.add(h)
            elif isinstance(h, date):
                ext_strs.add(h.isoformat())
        return d.isoformat() not in ext_strs

    # Built-in default
    return d not in NSE_HOLIDAYS


def next_trading_day(from_date=None):
    """Returns the next trading day after from_date."""
    if from_date is None:
        from_date = ist_today()
    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)
    d = from_date + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def trading_day_after_n(from_date, n):
    """Returns the nth trading day after from_date."""
    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)
    d     = from_date
    count = 0
    while count < n:
        d += timedelta(days=1)
        if is_trading_day(d):
            count += 1
    return d


def days_until_exit(entry_date, n=6):
    """Returns the date that is n trading days after entry."""
    if isinstance(entry_date, str):
        entry_date = date.fromisoformat(entry_date)
    return trading_day_after_n(entry_date, n)


def get_market_status():
    """
    Returns dict describing current market state.
    Used by chain_validator and other consumers.
    """
    now    = ist_now()
    today  = now.date()
    hour   = now.hour
    minute = now.minute
    mins   = hour * 60 + minute

    is_trading = is_trading_day(today)
    market_open_mins  = 9 * 60 + 15   # 9:15
    market_close_mins = 15 * 60 + 30  # 15:30

    if not is_trading:
        phase = 'closed'
    elif mins < market_open_mins:
        phase = 'pre_open'
    elif mins <= market_close_mins:
        phase = 'open'
    else:
        phase = 'after_close'

    return {
        'is_trading':   is_trading,
        'phase':        phase,
        'date':         today.isoformat(),
        'time_ist':     now.strftime('%H:%M'),
    }
