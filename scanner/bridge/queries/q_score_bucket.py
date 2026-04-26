"""
q_score_bucket — query plugin returning historical performance for
signals at this exact score.

Reads from signal_history.json records using canonical field names
(`score`, `result`). Coerces both sides to int for comparison since
score may be int or float on either side.

Bridge composer puts the result into evidence.score_bucket on the SDR.
Surfaces "signals scored 9 historically have 94% WR (n=18)" insights.

Plugin contract per scanner.bridge.queries._registry.

See doc/bridge_design_v1.md §9.
"""

from typing import Optional


QUERY_NAME = "q_score_bucket"
QUERY_DESCRIPTION = (
    "Historical performance for signals at this exact score"
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

    sig_score = _coerce_int(signal.get("score"))
    if sig_score is None:
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
        rec_score = _coerce_int(r.get("score"))
        if rec_score != sig_score:
            continue
        matches.append(r)

    n = len(matches)
    if n == 0:
        return None

    wins = sum(1 for r in matches if r.get("outcome") in _WIN_OUTCOMES)
    wr = wins / n

    return {
        "score": sig_score,
        "n": n,
        "wr": round(wr, 4),
    }


def _coerce_int(v) -> Optional[int]:
    """int/float → int; everything else → None."""
    if isinstance(v, bool):
        return None  # bool is subclass of int; reject explicitly
    if isinstance(v, (int, float)):
        try:
            return int(v)
        except (ValueError, OverflowError):
            return None
    return None
