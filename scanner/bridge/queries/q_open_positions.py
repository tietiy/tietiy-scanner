"""
q_open_positions — query plugin returning currently-active positions.

Active = PENDING + signal_date in the last 6 trading days + signal_date < today.
These are positions you've already entered (or should have, per bridge L1 of
prior days), not today's new signals.

Returned records include a 'day_count' field for UX rendering (Day 1 of 6,
Day 5 of 6, etc.). Bridge composers populate the open_positions[] array of
bridge_state.json with these.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §10 (bridge_state schema, open_positions array).
"""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


QUERY_NAME = "q_open_positions"
QUERY_DESCRIPTION = (
    "Returns currently-open active positions from prior days"
)
INPUT_FILES = ["signal_history.json"]

_IST = ZoneInfo("Asia/Kolkata")
_PENDING = "PENDING"
_MAX_DAY_COUNT = 6  # holding window per scanner design

# Defensive import: fall back to calendar-day count if calendar_utils
# can't be loaded (e.g., test sandbox without meta_writer wired).
try:
    from scanner.calendar_utils import is_trading_day as _is_trading_day
    _HAS_CAL = True
except Exception:
    _is_trading_day = None
    _HAS_CAL = False


def run(history_data: dict,
        market_date: Optional[str] = None) -> list:
    """
    Return PENDING records from prior days, within the 6-day holding
    window. Each record gets a computed 'day_count' field (1-based;
    signal_date is Day 1, today is Day N). Sort: day_count descending
    (oldest / exit-tomorrow first).
    """
    if not isinstance(history_data, dict):
        return []

    history = history_data.get("history")
    if not isinstance(history, list):
        return []

    target_date_str = market_date or _today_ist()
    try:
        target_date = datetime.strptime(
            target_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return []

    out: list = []
    for record in history:
        if not isinstance(record, dict):
            continue
        # signal_history records use canonical 'date', not 'signal_date'.
        signal_date_str = record.get("date")
        result = record.get("result")
        if signal_date_str is None or result != _PENDING:
            continue

        try:
            sd = datetime.strptime(
                signal_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        # Skip today's new signals (q_signal_today's job)
        if sd >= target_date:
            continue

        day_count = _trading_day_count(sd, target_date)
        if day_count is None or day_count > _MAX_DAY_COUNT:
            continue

        enriched = dict(record)
        enriched["day_count"] = day_count
        out.append(enriched)

    # Stable sort: oldest first (highest day_count first)
    out.sort(key=lambda r: r["day_count"], reverse=True)
    return out


def _today_ist() -> str:
    return datetime.now(_IST).date().isoformat()


def _trading_day_count(signal_date, market_date) -> Optional[int]:
    """
    1-based count: signal_date is Day 1, each subsequent trading
    day increments. On market_date, returns total trading days
    elapsed including signal_date itself.

    Falls back to calendar-day count if calendar_utils unavailable.
    """
    if market_date < signal_date:
        return None

    if _HAS_CAL:
        days = 1
        d = signal_date
        while d < market_date:
            d += timedelta(days=1)
            if _is_trading_day(d):
                days += 1
        return days

    # Fallback: calendar-day count
    return (market_date - signal_date).days + 1
