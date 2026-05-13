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

from typing import Dict, List, Optional, Tuple, Any

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
    # retune1 Fix B: steady-state confirm reduced 3 → 2 (matches recovery cadence).
    steady_confirm_days: int = 2,
    recovery_confirm_days: int = 2,
    # retune1 Fix C: rolling-window counter parameters (entry side).
    # 3-of-5 window tolerates 2 bounce days per 5-day stretch.
    steady_window_size: int = 5,
    steady_window_required: int = 3,
    recovery_window_size: int = 4,
    recovery_window_required: int = 2,
    # retune2 Fix F: asymmetric persistence — exit from BULL/BEAR is sticky.
    # 4-of-7 window tolerates 2-3 bounce days per week before exiting trend.
    exit_window_size: int = 7,
    exit_window_required: int = 4,
    # retune2 Fix G: 5-day minimum hold for BEAR/BULL after entry.
    # retune4 Fix N: verified redundant with Fix G — Fix G already enforces
    # 5-day minimum commitment after BEAR/BULL commits via days_in_state guard.
    trend_min_hold_days: int = 5,
    use_rolling_window: bool = True,
    whipsaw_window: int = 10,
    # retune4 Fix M: asymmetric lockdown — 2 days exiting trend, 5 entering.
    whipsaw_lockdown_default: int = 5,
    whipsaw_lockdown_trend_exit: int = 2,
    whipsaw_threshold: int = 3,
    initial_state: str = "CHOPPY",
    # retune4 Fix L: whipsaw exemption when dd_from_50d_high < -8%.
    # Pass a pd.Series aligned with raw_states. None = exemption disabled.
    dd_from_50d_high_pct: Optional[pd.Series] = None,
    drawdown_exemption_threshold: float = -8.0,
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
    # retune1 Fix C: rolling window of recent raw proposals.
    # retune2 Fix F: window size now max of entry/exit/recovery windows so
    # we have enough history for sticky-exit evaluation.
    from collections import deque
    rolling: deque = deque(maxlen=max(steady_window_size, recovery_window_size,
                                        exit_window_size))

    transition_dates_recent: List[pd.Timestamp] = []
    lockdown_remaining = 0
    # retune2 Fix G: days_in_state counter — hard floor for BEAR/BULL exit.
    days_in_state = 0
    TREND_STATES = {"BULL", "BEAR"}

    for ts, raw in raw_states.items():
        if raw is None or (isinstance(raw, float) and raw != raw):
            # NaN → keep current; don't pollute the rolling window
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            if lockdown_remaining > 0:
                lockdown_remaining -= 1
            days_in_state += 1
            continue

        # retune2 Fix H: prefer terminal over recovery when both feasible.
        # If raw is a recovery state, peek at the rolling window — if the
        # corresponding terminal state has been ≥ required count of the last
        # entry_window bars, treat raw as the terminal (escalate).
        if raw == "BEAR_RECOVERY":
            recent_window = list(rolling)[-steady_window_size:] if rolling else []
            if recent_window.count("BEAR") >= steady_window_required:
                raw = "BEAR"
        elif raw == "BULL_RECOVERY":
            recent_window = list(rolling)[-steady_window_size:] if rolling else []
            if recent_window.count("BULL") >= steady_window_required:
                raw = "BULL"

        # Update rolling window
        rolling.append(raw)

        # retune4 Fix L: check for drawdown exemption.
        # If dd_from_50d_high < -8% on this bar, whipsaw lockdown is suppressed
        # (deep crashes have legitimate transitions; don't penalize them).
        in_drawdown_exemption = False
        if dd_from_50d_high_pct is not None:
            try:
                dd_val = dd_from_50d_high_pct.loc[ts]
                if dd_val is not None and dd_val == dd_val and dd_val < drawdown_exemption_threshold:
                    in_drawdown_exemption = True
            except (KeyError, TypeError):
                pass

        # Lockdown takes precedence: force CHOPPY (whipsaw guard overrides everything)
        # ... EXCEPT during drawdown exemption per Fix L.
        if lockdown_remaining > 0 and not in_drawdown_exemption:
            if current != "CHOPPY":
                transition_log.append({
                    "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                    "from": current,
                    "to": "CHOPPY",
                    "reason": "whipsaw_lockdown",
                })
                transition_dates_recent.append(ts)
                current = "CHOPPY"
                days_in_state = 0
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            lockdown_remaining -= 1
            days_in_state += 1
            continue
        elif lockdown_remaining > 0 and in_drawdown_exemption:
            # In exemption — decrement counter but don't force CHOPPY
            lockdown_remaining -= 1

        if raw == current:
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)
            days_in_state += 1
            continue

        # retune2 Fix G: 5-day minimum hold for BEAR/BULL.
        # If currently in a trend state and have not yet held for trend_min_hold_days,
        # block the exit (keep current).
        if current in TREND_STATES and days_in_state < trend_min_hold_days:
            smoothed.append(current)
            regime_pending.append(raw)  # advertise as pending but don't commit
            confidence_pending.append(days_in_state / trend_min_hold_days)
            days_in_state += 1
            continue

        # retune2 Fix F: asymmetric persistence — exit from trend state uses
        # sticky 4-of-7 window. Entry into any state uses 3-of-5 (steady) or
        # 2-of-4 (recovery).
        is_exit_from_trend = current in TREND_STATES
        if is_exit_from_trend:
            window_size = exit_window_size
            required = exit_window_required
            window_mode = "exit_sticky"
        elif raw in RECOVERY_STATES:
            window_size = recovery_window_size
            required = recovery_window_required
            window_mode = "recovery_entry"
        else:
            window_size = steady_window_size
            required = steady_window_required
            window_mode = "steady_entry"

        recent = list(rolling)[-window_size:] if use_rolling_window else None
        if use_rolling_window:
            count_in_window = recent.count(raw)
        else:
            count_in_window = 0

        if count_in_window >= required:
            new_state = raw
            if raw not in ALLOWED_TRANSITIONS.get(current, set()):
                intermediate = _find_intermediate(current, raw)
                if intermediate is not None and intermediate != current:
                    transition_log.append({
                        "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                        "from": current,
                        "to": intermediate,
                        "reason": f"forced_intermediate_en_route_to_{raw}",
                        "window_mode": window_mode,
                    })
                    transition_dates_recent.append(ts)
                    current = intermediate
                    days_in_state = 0
                    smoothed.append(current)
                    regime_pending.append(raw)
                    confidence_pending.append(0.0)
                    _trim_recent(transition_dates_recent, ts, whipsaw_window)
                    if len(transition_dates_recent) >= whipsaw_threshold:
                        lockdown_remaining = whipsaw_lockdown
                    continue

            transition_log.append({
                "date": str(ts.date()) if hasattr(ts, "date") else str(ts),
                "from": current,
                "to": new_state,
                "reason": "confirmed_rolling",
                "window_count": count_in_window,
                "window_size": window_size,
                "window_required": required,
                "window_mode": window_mode,
            })
            transition_dates_recent.append(ts)
            current = new_state
            days_in_state = 0
            smoothed.append(current)
            regime_pending.append(None)
            confidence_pending.append(0.0)

            _trim_recent(transition_dates_recent, ts, whipsaw_window)
            if len(transition_dates_recent) >= whipsaw_threshold and not in_drawdown_exemption:
                # retune4 Fix M: asymmetric lockdown duration.
                # If we just exited a trend state (BULL/BEAR) to non-trend, use short lockdown.
                prev_was_trend = (current == "CHOPPY" and len(transition_log) > 0 and
                                   transition_log[-1].get("from") in TREND_STATES)
                if prev_was_trend:
                    lockdown_remaining = whipsaw_lockdown_trend_exit
                else:
                    lockdown_remaining = whipsaw_lockdown_default
        else:
            smoothed.append(current)
            regime_pending.append(raw)
            confidence_pending.append(count_in_window / required)
            days_in_state += 1

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
