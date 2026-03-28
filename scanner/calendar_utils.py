from datetime import date, timedelta
import pandas as pd

# ── NSE HOLIDAYS 2025-2026 ────────────────────────
NSE_HOLIDAYS = {
    # 2025
    date(2025, 1, 26),   # Republic Day
    date(2025, 3, 14),   # Holi
    date(2025, 4, 14),   # Dr Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Diwali Laxmi Pujan
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Prakash Gurpurb
    date(2025, 11, 20),  # Chhatrapati Shivaji
    # 2026
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 4),    # Mahashivratri
    date(2026, 3, 20),   # Holi
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
}

def is_trading_day(d=None):
    """Returns True if given date is a trading day"""
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    # Weekend check
    if d.weekday() >= 5:
        return False
    # Holiday check
    if d in NSE_HOLIDAYS:
        return False
    return True

def next_trading_day(from_date=None):
    """Returns next trading day from given date"""
    if from_date is None:
        from_date = date.today()
    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)
    d = from_date + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d

def trading_day_after_n(from_date, n):
    """Returns the date after n trading days"""
    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)
    d = from_date
    count = 0
    while count < n:
        d += timedelta(days=1)
        if is_trading_day(d):
            count += 1
    return d

def days_until_exit(entry_date, n=6):
    """Calculate exit date (Day 6 = 6 trading days)"""
    return trading_day_after_n(entry_date, n)

def is_expiry_week(d=None):
    """Returns True if date is within expiry week (last Thu ±2 days)"""
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    # Find last Thursday of the month
    year, month = d.year, d.month
    last_day = date(year, month, 1)
    last_thu = None
    while last_day.month == month:
        if last_day.weekday() == 3:
            last_thu = last_day
        last_day += timedelta(days=1)
    if last_thu is None:
        return False
    diff = abs((d - last_thu).days)
    return diff <= 2

def is_month_end(d=None):
    """Returns True if within last 4 trading days of month"""
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    bdays = pd.bdate_range(
        f"{d.year}-{d.month:02d}-01", d
    )
    return len(bdays) >= 21

def get_market_status():
    """Returns dict with today's trading status"""
    today = date.today()
    trading = is_trading_day(today)
    next_td = next_trading_day(today)
    return {
        'today':        today.isoformat(),
        'is_trading':   trading,
        'next_trading': next_td.isoformat(),
        'is_expiry_wk': is_expiry_week(today),
        'is_month_end': is_month_end(today),
        'reason': (
            'NSE Holiday' if today in NSE_HOLIDAYS
            else 'Weekend' if today.weekday() >= 5
            else 'Trading Day'
        )
    }

if __name__ == '__main__':
    status = get_market_status()
    print(f"Today: {status['today']}")
    print(f"Trading: {status['is_trading']}")
    print(f"Next trading day: {status['next_trading']}")
    print(f"Expiry week: {status['is_expiry_wk']}")
    print(f"Status: {status['reason']}")
