"""
q_sector_recent_30d — query plugin returning sector performance for the
last 30 calendar days (regardless of signal_type).

Reads from signal_history.json records using canonical field names
(`sector`, `date`, `result`, `pnl_pct`). Filters to records within the
last 30 calendar days from market_date (or today IST if not given).

Bridge composer puts the result into evidence.sector_recent_30d on the SDR.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §4 (SDR.evidence schema).
"""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


QUERY_NAME = "q_sector_recent_30d"
QUERY_DESCRIPTION = (
    "Sector performance for last 30 calendar days "
    "regardless of signal_type"
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
_TREND_WINDOW = 10
_TREND_DELTA = 0.05  # 5pp threshold for improving/declining
_TREND_MIN_N = 20    # below this, trend = None


def run(signal: dict,
        history_data: dict,
        market_date: Optional[str] = None) -> Optional[dict]:
    if not isinstance(signal, dict) or not isinstance(history_data, dict):
        return None

    sig_sector = signal.get("sector")
    if not sig_sector:
        return None

    history = history_data.get("history")
    if not isinstance(history, list):
        return None

    target_date = _parse_date(market_date) if market_date else _today_ist()
    if target_date is None:
        return None
    cutoff = target_date - timedelta(days=_LOOKBACK_DAYS)

    matches = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("outcome") not in _TERMINAL_OUTCOMES:
            continue
        if r.get("sector") != sig_sector:
            continue
        rd = _parse_date(r.get("date"))
        if rd is None or rd < cutoff or rd > target_date:
            continue
        matches.append(r)

    n = len(matches)
    if n == 0:
        return None

    wins = sum(1 for r in matches if r.get("outcome") in _WIN_OUTCOMES)
    wr = wins / n

    avg_pnl = _mean_field(matches, "pnl_pct")
    trend = _trend(matches)

    return {
        "n": n,
        "wr": round(wr, 4),
        "avg_pnl": avg_pnl,
        "trend": trend,
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


def _mean_field(records: list, field: str) -> Optional[float]:
    values = [r.get(field) for r in records
              if isinstance(r.get(field), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _trend(records: list) -> Optional[str]:
    """Compare WR of first 10 vs last 10 records by date.
    Returns None if n < 20."""
    if len(records) < _TREND_MIN_N:
        return None

    sortable = [(r, _parse_date(r.get("date"))) for r in records]
    sortable = [(r, d) for r, d in sortable if d is not None]
    if len(sortable) < _TREND_MIN_N:
        return None

    sortable.sort(key=lambda rd: rd[1])
    first = [r for r, _ in sortable[:_TREND_WINDOW]]
    last  = [r for r, _ in sortable[-_TREND_WINDOW:]]

    first_wr = _wr(first)
    last_wr  = _wr(last)
    delta = last_wr - first_wr

    if delta > _TREND_DELTA:
        return "improving"
    if delta < -_TREND_DELTA:
        return "declining"
    return "stable"


def _wr(records: list) -> float:
    if not records:
        return 0.0
    wins = sum(1 for r in records if r.get("outcome") in _WIN_OUTCOMES)
    return wins / len(records)
