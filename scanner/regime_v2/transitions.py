"""Persistence + transition layer per doc/regime_v2_design/02_state_space.md §"Persistence rules".

Rules:
  P1 — Steady states (BULL/BEAR/CHOPPY) require 3-day confirmation before flip.
  P2 — Recovery states (BULL_RECOVERY/BEAR_RECOVERY) require 2-day confirmation.
  P3 — Whipsaw guard: 3+ transitions in 10 trading days → force CHOPPY for 5 days.

Allowed transitions (design §02 "Allowed direct transitions"):
  Bull <-> Bull-Recovery
  Bull-Recovery <-> Choppy, Bear-Recovery
  Choppy <-> Bull-Recovery, Bear-Recovery   (NOT direct to Bull or Bear)
  Bear-Recovery <-> Bull-Recovery, Choppy, Bear
  Bear <-> Bear-Recovery, Choppy
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd


STEADY_STATES = {"BULL", "BEAR", "CHOPPY"}
RECOVERY_STATES = {"BULL_RECOVERY", "BEAR_RECOVERY"}

# Per design §02 "Allowed direct transitions"
# retune1 Fix A: forensic showed forced intermediate routing (CHOPPY → BEAR_RECOVERY → BEAR)
# added 2-3 day latency at crash entry; direct CHOPPY → BEAR and CHOPPY → BULL allowed.
# Recoveries remain valid intermediate states, just not mandatory.
ALLOWED_TRANSITIONS = {
    "BULL": {"BULL_RECOVERY", "BULL", "CHOPPY"},
    "BULL_RECOVERY": {"BULL", "BULL_RECOVERY", "CHOPPY", "BEAR_RECOVERY"},
    "CHOPPY": {"CHOPPY", "BULL_RECOVERY", "BEAR_RECOVERY", "BULL", "BEAR"},  # +direct BULL/BEAR
    "BEAR_RECOVERY": {"BEAR_RECOVERY", "BEAR", "BULL_RECOVERY", "CHOPPY"},
    "BEAR": {"BEAR", "BEAR_RECOVERY", "CHOPPY"},
}


def apply_persistence(
    raw_states: pd.Series,
    *,
    # retune1 Fix B: steady-state confirm reduced 3 → 2 (matches recovery cadence,
    # reduces counter-reset sensitivity by ~33%).
    steady_confirm_days: int = 2,
    recovery_confirm_days: int = 2,
    # retune1 Fix C: rolling-window counter parameters.
    # Real crashes have intraday bounces; strict consecutive counter never commits.
    # 3-of-5 window tolerates 2 bounce days per 5-day stretch.
    steady_window_size: int = 5,
    steady_window_required: int = 3,
    recovery_window_size: int = 4,
    recovery_window_required: int = 2,
    use_rolling_window: bool = True,
    whipsaw_window: int = 10,
    whipsaw_lockdown: int = 5,
    whipsaw_threshold: int = 3,
    initial_state: str = "CHOPPY",
) -> Tuple[pd.Series, pd.Series, pd.Series, List[Dict]]:
    """Apply persistence + transition rules to a raw state series.

    Args:
        raw_states: pd.Series indexed by trading-day date, values are state strings.
        steady_confirm_days: N for P1.
        recovery_confirm_days: N for P2.
        whipsaw_window: window in trading days for P3.
        whipsaw_lockdown: how many days to force CHOPPY after whipsaw.
        whipsaw_threshold: 3+ transitions trigger P3.
        initial_state: assumed state before the first observation.

    Returns:
        (smoothed_states, regime_pending, confidence_pending, transition_log)
        - smoothed_states: pd.Series of confirmed labels.
        - regime_pending: pd.Series — the proposed-but-unconfirmed state, or None.
        - confidence_pending: pd.Series float 0..1 — days_pending / required_days.
        - transition_log: list of dicts, one per actual transition.
    """
    smoothed: List[str] = []
    regime_pending: List[Optional[str]] = []
    confidence_pending: List[float] = []
    transition_log: List[Dict] = []

    current = initial_state
    # retune1 Fix C: track rolling window of recent raw proposals (not just
    # consecutive). Each entry is (timestamp, raw_state).
    from collections import deque
    rolling: deque = deque(maxlen=max(steady_window_size, recovery_window_size))

    transition_dates_recent: List[pd.Timestamp] = []
    lockdown_remaining = 0

    for ts, raw in raw_states.items():
        if raw is None or (isinstance(raw, float) and raw != raw):
            # NaN → keep current; don't pollute the rolling window
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            if lockdown_remaining > 0:
                lockdown_remaining -= 1
            continue

        # Always update rolling window with this bar's raw proposal
        rolling.append(raw)

        # Lockdown takes precedence: force CHOPPY
        if lockdown_remaining > 0:
            if current != "CHOPPY":
                transition_log.append({
                    "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                    "from": current,
                    "to": "CHOPPY",
                    "reason": "whipsaw_lockdown",
                })
                transition_dates_recent.append(ts)
                current = "CHOPPY"
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            lockdown_remaining -= 1
            continue

        if raw == current:
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            continue

        # raw != current — check if rolling window supports a commit.
        # retune1 Fix C: count occurrences of `raw` in last W bars.
        if raw in RECOVERY_STATES:
            window_size = recovery_window_size
            required = recovery_window_required
        else:
            window_size = steady_window_size
            required = steady_window_required

        # Slice the most-recent window_size entries from rolling
        recent = list(rolling)[-window_size:] if use_rolling_window else None
        if use_rolling_window:
            count_in_window = recent.count(raw)
        else:
            # Fallback to legacy consecutive counter
            count_in_window = sum(1 for s in recent[::-1] if s == raw and not (recent[::-1].index(s)))

        if count_in_window >= required:
            # Check allowed-transition graph
            new_state = raw
            if raw not in ALLOWED_TRANSITIONS.get(current, set()):
                # Disallowed direct jump — force through intermediate.
                # After retune1 Fix A, most CHOPPY → terminal jumps ARE allowed.
                intermediate = _find_intermediate(current, raw)
                if intermediate is not None and intermediate != current:
                    transition_log.append({
                        "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                        "from": current,
                        "to": intermediate,
                        "reason": f"forced_intermediate_en_route_to_{raw}",
                    })
                    transition_dates_recent.append(ts)
                    current = intermediate
                    smoothed.append(current)
                    regime_pending.append(raw)
                    confidence_pending.append(0.0)
                    _trim_recent(transition_dates_recent, ts, whipsaw_window)
                    if len(transition_dates_recent) >= whipsaw_threshold:
                        lockdown_remaining = whipsaw_lockdown
                    continue

            # Commit
            transition_log.append({
                "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                "from": current,
                "to": new_state,
                "reason": "confirmed_rolling",
                "window_count": count_in_window,
                "window_size": window_size,
                "window_required": required,
            })
            transition_dates_recent.append(ts)
            current = new_state
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)

            _trim_recent(transition_dates_recent, ts, whipsaw_window)
            if len(transition_dates_recent) >= whipsaw_threshold:
                lockdown_remaining = whipsaw_lockdown
        else:
            # Pending — advertise the most-frequent non-current state in window
            smoothed.append(current)
            regime_pending.append(raw)
            confidence_pending.append(count_in_window / required)

    sm = pd.Series(smoothed, index=raw_states.index, name="state")
    rp = pd.Series(regime_pending, index=raw_states.index, name="regime_pending")
    cp = pd.Series(confidence_pending, index=raw_states.index, name="confidence_pending")
    return sm, rp, cp, transition_log


def _trim_recent(buf: List[pd.Timestamp], now: pd.Timestamp, window: int) -> None:
    """Drop transitions older than `window` trading days from now."""
    if not buf:
        return
    cutoff = now - pd.Timedelta(days=window * 2)  # calendar approximation; window is trading days but +buffer
    while buf and buf[0] < cutoff:
        buf.pop(0)


def _find_intermediate(from_state: str, to_state: str) -> Optional[str]:
    """Return the first state on a BFS path from `from_state` to `to_state`,
    excluding `from_state` itself. Used to bridge disallowed direct jumps.
    """
    if to_state in ALLOWED_TRANSITIONS.get(from_state, set()):
        return to_state
    # BFS
    visited = {from_state}
    queue = [(from_state, [from_state])]
    while queue:
        node, path = queue.pop(0)
        for nbr in ALLOWED_TRANSITIONS.get(node, set()):
            if nbr in visited:
                continue
            new_path = path + [nbr]
            if nbr == to_state:
                # Return the first hop after from_state
                return new_path[1] if len(new_path) > 1 else nbr
            visited.add(nbr)
            queue.append((nbr, new_path))
    return None
