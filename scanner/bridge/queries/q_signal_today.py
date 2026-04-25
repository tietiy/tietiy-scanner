"""
q_signal_today — query plugin returning today's PENDING signals.

The bridge composer calls this at start of compose to find which signals
need SDRs built today. PENDING means: signal generated, not yet resolved
(result is not one of WON, STOPPED, EXITED, REJECTED, INVALIDATED).

Caller passes pre-loaded history_data; this module never reads files.

Plugin contract per scanner.bridge.queries._registry.
"""

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo


QUERY_NAME = "q_signal_today"
QUERY_DESCRIPTION = (
    "Returns today's PENDING signals from signal_history"
)
INPUT_FILES = ["signal_history.json"]

_IST = ZoneInfo("Asia/Kolkata")
_PENDING = "PENDING"


def run(history_data: dict,
        market_date: Optional[str] = None) -> list:
    """
    Return today's PENDING signal records (insertion order preserved).
    Empty list on any malformed/missing input.
    """
    if not isinstance(history_data, dict):
        return []

    history = history_data.get("history")
    if not isinstance(history, list):
        return []

    target_date = market_date or _today_ist()

    out: list = []
    for record in history:
        if not isinstance(record, dict):
            continue
        # signal_history records use canonical 'date', not 'signal_date'.
        record_date = record.get("date")
        result = record.get("result")
        if record_date is None or result is None:
            continue
        if record_date == target_date and result == _PENDING:
            out.append(record)
    return out


def _today_ist() -> str:
    return datetime.now(_IST).date().isoformat()
