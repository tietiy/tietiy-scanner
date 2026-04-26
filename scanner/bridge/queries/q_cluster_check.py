"""
q_cluster_check — query plugin detecting cluster warnings.

Scans signal_history.json for similar signals (same signal_type + sector)
in the last 14 calendar days. Two warnings:

  1. cluster_count: too many similar signals fired in the window
  2. cluster_loss: of the resolved signals in that cluster, WR is bad

The Apr 6-8 cluster (32 DOWN_TRIs in 3 days, all losers) is the canonical
example. Bridge composer uses these warnings to downgrade Gate-4 STRONG
classifications and surface alerts to the user.

Reads from signal_history.json records using canonical field names
(`signal`, `sector`, `date`, `outcome`). Win/loss math uses canonical
outcome-based logic (matches pattern_miner.py).

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §4 (SDR.evidence.cluster_warnings).
"""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


QUERY_NAME = "q_cluster_check"
QUERY_DESCRIPTION = (
    "Detects cluster warnings (too many similar signals in short window)"
)
INPUT_FILES = ["signal_history.json"]


_IST = ZoneInfo("Asia/Kolkata")
_TERMINAL_OUTCOMES = {
    "TARGET_HIT", "STOP_HIT",
    "DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT",
}
_WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}

_WINDOW_DAYS = 14
_COUNT_WARN_N = 10       # n>=10 in 14 days → warning severity
_COUNT_CRITICAL_N = 15   # n>=15 → critical severity
_LOSS_MIN_RESOLVED = 5   # need at least this many resolved before loss check
_LOSS_WR_MAX = 0.30      # resolved wr<=0.30 → cluster_loss critical


def run(signal: dict,
        history_data: dict,
        market_date: Optional[str] = None) -> list:
    """Returns list of warning dicts (zero or more)."""
    if not isinstance(signal, dict) or not isinstance(history_data, dict):
        return []

    sig_type   = signal.get("signal_type") or signal.get("signal")
    sig_sector = signal.get("sector")
    if not sig_type or not sig_sector:
        return []

    history = history_data.get("history")
    if not isinstance(history, list):
        return []

    target_date = _parse_date(market_date) if market_date else _today_ist()
    if target_date is None:
        return []
    cutoff = target_date - timedelta(days=_WINDOW_DAYS)

    cluster = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("signal") != sig_type:
            continue
        if r.get("sector") != sig_sector:
            continue
        rd = _parse_date(r.get("date"))
        if rd is None or rd < cutoff or rd > target_date:
            continue
        cluster.append(r)

    warnings: list = []

    # === Warning 1: cluster_count ===
    n = len(cluster)
    if n >= _COUNT_CRITICAL_N:
        warnings.append({
            "type": "cluster_count",
            "severity": "critical",
            "message": (
                f"{n} {sig_type} signals fired in {sig_sector} "
                f"in last {_WINDOW_DAYS} days — extreme clustering"
            ),
            "evidence": {
                "n": n,
                "window_days": _WINDOW_DAYS,
                "signal_type": sig_type,
                "sector": sig_sector,
            },
        })
    elif n >= _COUNT_WARN_N:
        warnings.append({
            "type": "cluster_count",
            "severity": "warning",
            "message": (
                f"{n} {sig_type} signals fired in {sig_sector} "
                f"in last {_WINDOW_DAYS} days — clustering"
            ),
            "evidence": {
                "n": n,
                "window_days": _WINDOW_DAYS,
                "signal_type": sig_type,
                "sector": sig_sector,
            },
        })

    # === Warning 2: cluster_loss ===
    resolved = [r for r in cluster
                if r.get("outcome") in _TERMINAL_OUTCOMES]
    if len(resolved) >= _LOSS_MIN_RESOLVED:
        wins = sum(1 for r in resolved
                   if r.get("outcome") in _WIN_OUTCOMES)
        wr = wins / len(resolved)
        if wr <= _LOSS_WR_MAX:
            warnings.append({
                "type": "cluster_loss",
                "severity": "critical",
                "message": (
                    f"Recent cluster of {sig_type} in {sig_sector} "
                    f"resolved at {wr*100:.0f}% WR "
                    f"({wins}/{len(resolved)} wins) — historic loss pattern"
                ),
                "evidence": {
                    "n_in_cluster": n,
                    "n_resolved": len(resolved),
                    "wins": wins,
                    "wr": round(wr, 4),
                    "window_days": _WINDOW_DAYS,
                    "signal_type": sig_type,
                    "sector": sig_sector,
                },
            })

    return warnings


def _today_ist():
    return datetime.now(_IST).date()


def _parse_date(s):
    if not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None
