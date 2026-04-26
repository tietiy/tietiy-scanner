"""
q_stock_recency — query plugin returning recent signal history for
this specific stock.

Reads from signal_history.json records using canonical field names
(`symbol`, `date`, `result`). Returns last_signal_date, last_outcome,
and 30-day lookback stats.

Bridge composer puts the result into evidence.stock_recency on the SDR.
Surfaces "this stock signaled 3 times in last 30 days with 33% WR —
recency warning."

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9.
"""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


QUERY_NAME = "q_stock_recency"
QUERY_DESCRIPTION = (
    "Recent signal history for this specific stock"
)
INPUT_FILES = ["signal_history.json"]


_IST = ZoneInfo("Asia/Kolkata")
# Canonical outcome-based resolution (matches pattern_miner.py).
_TERMINAL_OUTCOMES = {
    "TARGET_HIT", "STOP_HIT",
    "DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT",
}
_WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}
_LOOKBACK_DAYS = 30
_MIN_RESOLVED_FOR_WR = 3


def run(signal: dict,
        history_data: dict,
        market_date: Optional[str] = None) -> Optional[dict]:
    if not isinstance(signal, dict) or not isinstance(history_data, dict):
        return None

    sig_symbol = signal.get("symbol")
    if not sig_symbol:
        return None

    history = history_data.get("history")
    if not isinstance(history, list):
        return None

    target_date = _parse_date(market_date) if market_date else _today_ist()
    if target_date is None:
        return None
    cutoff = target_date - timedelta(days=_LOOKBACK_DAYS)

    # All records for this symbol (with parsed dates)
    all_for_symbol = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("symbol") != sig_symbol:
            continue
        rd = _parse_date(r.get("date"))
        if rd is None:
            continue
        all_for_symbol.append((r, rd))

    if not all_for_symbol:
        return None

    # Sort by date descending — newest first
    all_for_symbol.sort(key=lambda rd: rd[1], reverse=True)

    last_signal_date = all_for_symbol[0][1].isoformat()

    # Most recent record with a terminal outcome — that's its canonical
    # outcome label (TARGET_HIT / STOP_HIT / DAY6_WIN / DAY6_LOSS / DAY6_FLAT).
    last_outcome = None
    for r, _ in all_for_symbol:
        if r.get("outcome") in _TERMINAL_OUTCOMES:
            last_outcome = r.get("outcome")
            break

    # 30-day window: any-record count + resolved-only WR
    in_window = [(r, d) for r, d in all_for_symbol
                 if cutoff <= d <= target_date]
    lookback_30d_count = len(in_window)

    resolved_in_window = [r for r, _ in in_window
                          if r.get("outcome") in _TERMINAL_OUTCOMES]
    if len(resolved_in_window) >= _MIN_RESOLVED_FOR_WR:
        wins = sum(1 for r in resolved_in_window
                   if r.get("outcome") in _WIN_OUTCOMES)
        lookback_30d_wr = round(wins / len(resolved_in_window), 4)
    else:
        lookback_30d_wr = None

    return {
        "last_signal_date":   last_signal_date,
        "last_outcome":       last_outcome,
        "lookback_30d_count": lookback_30d_count,
        "lookback_30d_wr":    lookback_30d_wr,
    }


def _today_ist():
    return datetime.now(_IST).date()


def _parse_date(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None
