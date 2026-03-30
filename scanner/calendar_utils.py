from datetime import date, timedelta
import pandas as pd

NSE_HOLIDAYS = {
    date(2025, 1, 26), date(2025, 3, 14),
    date(2025, 4, 14), date(2025, 4, 18),
    date(2025, 5, 1),  date(2025, 8, 15),
    date(2025, 8, 27), date(2025, 10, 2),
    date(2025, 10, 21),date(2025, 10, 22),
    date(2025, 11, 5), date(2026, 3, 31),   # Eid-ul-Fitr
    date(2026, 1, 26), date(2026, 3, 4),
    date(2026, 3, 20), date(2026, 4, 3),
    date(2026, 4, 14), date(2026, 5, 1),
    date(2026, 8, 15), date(2026, 10, 2),
}

def is_trading_day(d=None):
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return d.weekday() < 5 and d not in NSE_HOLIDAYS

def next_trading_day(from_date=None):
    if from_date is None:
        from_date = date.today()
    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date)
    d = from_date + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d

def trading_day_after_n(from_date, n):
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
    return trading_day_after_n(entry_date, n)

def is_expiry_week(d=None):
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
