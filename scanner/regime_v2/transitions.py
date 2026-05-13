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
ALLOWED_TRANSITIONS = {
    "BULL": {"BULL_RECOVERY", "BULL"},
    "BULL_RECOVERY": {"BULL", "BULL_RECOVERY", "CHOPPY", "BEAR_RECOVERY"},
    "CHOPPY": {"CHOPPY", "BULL_RECOVERY", "BEAR_RECOVERY"},
    "BEAR_RECOVERY": {"BEAR_RECOVERY", "BEAR", "BULL_RECOVERY", "CHOPPY"},
    "BEAR": {"BEAR", "BEAR_RECOVERY", "CHOPPY"},
}


def apply_persistence(
    raw_states: pd.Series,
    *,
    steady_confirm_days: int = 3,
    recovery_confirm_days: int = 2,
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
    pending_state: Optional[str] = None
    pending_days = 0

    transition_dates_recent: List[pd.Timestamp] = []
    lockdown_remaining = 0

    for ts, raw in raw_states.items():
        if raw is None or (isinstance(raw, float) and raw != raw):
            # NaN → keep current
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            if lockdown_remaining > 0:
                lockdown_remaining -= 1
            continue

        # Lockdown takes precedence: force CHOPPY
        if lockdown_remaining > 0:
            if current != "CHOPPY":
                # On entry to lockdown, transition to CHOPPY immediately
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
            pending_state = None
            pending_days = 0
            continue

        if raw == current:
            # No change proposed
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            pending_state = None
            pending_days = 0
            continue

        # raw != current — proposed change
        if pending_state == raw:
            pending_days += 1
        else:
            pending_state = raw
            pending_days = 1

        confirm_needed = (recovery_confirm_days
                         if raw in RECOVERY_STATES else steady_confirm_days)

        if pending_days >= confirm_needed:
            # Check allowed-transition graph
            new_state = raw
            if raw not in ALLOWED_TRANSITIONS.get(current, set()):
                # Disallowed direct jump — force through intermediate
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
                    # Stay pending toward target
                    pending_state = raw
                    pending_days = 0
                    smoothed.append(current)
                    regime_pending.append(raw)
                    confidence_pending.append(0.0)
                    # Whipsaw check
                    _trim_recent(transition_dates_recent, ts, whipsaw_window)
                    if len(transition_dates_recent) >= whipsaw_threshold:
                        lockdown_remaining = whipsaw_lockdown
                    continue

            # Commit
            transition_log.append({
                "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                "from": current,
                "to": new_state,
                "reason": "confirmed",
                "confirm_days": pending_days,
            })
            transition_dates_recent.append(ts)
            current = new_state
            pending_state = None
            pending_days = 0
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)

            # Whipsaw check after commit
            _trim_recent(transition_dates_recent, ts, whipsaw_window)
            if len(transition_dates_recent) >= whipsaw_threshold:
                lockdown_remaining = whipsaw_lockdown
        else:
            # Pending — keep current label, advertise pending state
            smoothed.append(current)
            regime_pending.append(raw)
            confidence_pending.append(pending_days / confirm_needed)

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
