"""
q_regime_baseline — query plugin returning regime baseline performance
(all signals in the regime, all sectors, all signal_types).

Reads from signal_history.json records using canonical field names
(`regime`, `result`, `pnl_pct`).

Bridge composer puts the result into evidence.regime_baseline on the SDR.
Used by bucket_engine Gate 4 thin-fallback logic.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9, §5 (Gate 4 thin fallback).
"""

from typing import Optional


QUERY_NAME = "q_regime_baseline"
QUERY_DESCRIPTION = (
    "Regime baseline performance (all signals in regime, all sectors)"
)
INPUT_FILES = ["signal_history.json"]


# Canonical outcome-based resolution (matches pattern_miner.py).
_TERMINAL_OUTCOMES = {
    "TARGET_HIT", "STOP_HIT",
    "DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT",
}
_WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}


def run(signal: dict, history_data: dict) -> Optional[dict]:
    if not isinstance(signal, dict) or not isinstance(history_data, dict):
        return None

    sig_regime = signal.get("regime")
    if not sig_regime:
        return None

    history = history_data.get("history")
    if not isinstance(history, list):
        return None

    matches = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("outcome") not in _TERMINAL_OUTCOMES:
            continue
        if r.get("regime") != sig_regime:
            continue
        matches.append(r)

    n = len(matches)
    if n == 0:
        return None

    wins = sum(1 for r in matches if r.get("outcome") in _WIN_OUTCOMES)
    wr = wins / n
    avg_pnl = _mean_field(matches, "pnl_pct")

    return {
        "n": n,
        "wr": round(wr, 4),
        "avg_pnl": avg_pnl,
    }


def _mean_field(records: list, field: str) -> Optional[float]:
    values = [r.get(field) for r in records
              if isinstance(r.get(field), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 2)
