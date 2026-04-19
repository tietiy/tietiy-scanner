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
# ─────────────────────────────────────────────────────

from datetime import date, timedelta
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


def is_trading_day(d=None):
    """
    Returns True if date d is a trading day
    (weekday AND not an NSE holiday).
    """
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def next_trading_day(from_date=None):
    """Returns the next trading day after from_date."""
    if from_date is None:
        from_date = date.today()
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
    return trading_day_after_n(entry_date, n)


def is_expiry_week(d=None):
    """
    Returns True if date d falls within +/- 2 calendar
    days of the month's last Thursday (NSE F&O expiry).
    """
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    year, month = d.year, d.month
    last_thu    = None
    check       = date(year, month, 1)
    while check.month == month:
        if check.weekday() == 3:
            last_thu = check
        check += timedelta(days=1)
    if last_thu is None:
        return False
    return abs((d - last_thu).days) <= 2


def get_market_status():
    """Returns dict with today's trading status."""
    today = date.today()
    return {
        'today':        today.isoformat(),
        'is_trading':   is_trading_day(today),
        'next_trading': next_trading_day(today).isoformat(),
        'is_expiry_wk': is_expiry_week(today),
        'reason': (
            'NSE Holiday' if today in NSE_HOLIDAYS
            else 'Weekend' if today.weekday() >= 5
            else 'Trading Day'
        ),
    }
