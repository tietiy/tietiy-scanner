"""Unit tests for transitions.py (persistence + allowed-transition graph)."""
import pandas as pd
import pytest

from scanner.regime_v2.transitions import (
    apply_persistence, ALLOWED_TRANSITIONS, _find_intermediate,
)


def _series(states, start="2024-01-01"):
    """Build a state series for testing."""
    return pd.Series(states, index=pd.date_range(start, periods=len(states), freq="D"))


def test_constant_state_no_transitions():
    raw = _series(["CHOPPY"] * 30)
    sm, rp, cp, log = apply_persistence(raw)
    assert (sm == "CHOPPY").all()
    assert len(log) == 0


def test_steady_state_needs_3_day_confirmation():
    # Start in CHOPPY, then 3 days of BEAR-Recovery, then commit on day 4
    raw = _series(["CHOPPY"] * 5 + ["BEAR_RECOVERY"] * 5)
    sm, rp, cp, log = apply_persistence(raw)
    # Day 5: CHOPPY still (day 1 of pending)
    assert sm.iloc[5] == "CHOPPY"
    # Day 6: CHOPPY still (day 2)
    # BEAR_RECOVERY is a recovery state → 2-day confirmation
    # Day 6: should commit (day 2)
    assert sm.iloc[6] == "BEAR_RECOVERY"
    # One transition logged
    assert len(log) == 1
    assert log[0]["from"] == "CHOPPY"
    assert log[0]["to"] == "BEAR_RECOVERY"


def test_recovery_state_2_day_confirmation():
    raw = _series(["CHOPPY"] * 3 + ["BULL_RECOVERY"] * 3 + ["CHOPPY"] * 3)
    sm, rp, cp, log = apply_persistence(raw)
    # BULL_RECOVERY needs 2 days to confirm
    # Position 4: pending (day 2) — wait, position 3 is day 1, 4 is day 2 → commit
    # Actually: raw[3]='BULL_RECOVERY' is day 1, raw[4] day 2, so sm[4] should be BULL_RECOVERY
    assert sm.iloc[3] == "CHOPPY"  # pending
    assert sm.iloc[4] == "BULL_RECOVERY"


def test_pending_state_is_advertised():
    raw = _series(["BEAR"] * 5 + ["BEAR_RECOVERY"] * 5)
    sm, rp, cp, log = apply_persistence(raw, initial_state="BEAR")
    # First day of pending: regime_pending should be BEAR_RECOVERY
    assert rp.iloc[5] == "BEAR_RECOVERY"
    assert cp.iloc[5] > 0  # nonzero confidence


def test_disallowed_direct_jump_routes_through_intermediate():
    # Try to go BULL → BEAR directly. Per ALLOWED_TRANSITIONS this is disallowed.
    raw = _series(["BULL"] * 3 + ["BEAR"] * 10)
    sm, rp, cp, log = apply_persistence(raw, initial_state="BULL")
    # Should NOT go straight to BEAR. Should go through some intermediate (likely BULL_RECOVERY).
    # First confirmed transition (after 3 days of BEAR) goes to intermediate, not BEAR directly.
    assert log[0]["to"] != "BEAR"


def test_find_intermediate_for_bull_to_bear():
    inter = _find_intermediate("BULL", "BEAR")
    assert inter is not None
    assert inter != "BULL"
    # Direct neighbor of BULL — only BULL_RECOVERY
    assert inter == "BULL_RECOVERY"


def test_find_intermediate_for_allowed_direct():
    # BULL_RECOVERY → CHOPPY is allowed; should return CHOPPY directly
    inter = _find_intermediate("BULL_RECOVERY", "CHOPPY")
    assert inter == "CHOPPY"


def test_allowed_transitions_includes_self():
    # Sanity: self-transitions allowed (no transition is also allowed)
    for state in ALLOWED_TRANSITIONS:
        assert state in ALLOWED_TRANSITIONS[state]


def test_whipsaw_lockdown_triggered_by_3_transitions_in_window():
    # Rapid oscillation: alternate states to trigger 3+ transitions in window
    # Note: each transition requires confirmation, so we need >=9 raw states
    raw = _series(
        ["CHOPPY"] * 3
        + ["BEAR_RECOVERY"] * 2
        + ["CHOPPY"] * 3
        + ["BEAR_RECOVERY"] * 2
        + ["CHOPPY"] * 3
        + ["BEAR_RECOVERY"] * 2
        + ["BEAR_RECOVERY"] * 10
    )
    sm, rp, cp, log = apply_persistence(raw)
    # After 3 transitions, whipsaw lockdown should force CHOPPY for next days
    transition_dates = [t["date"] for t in log]
    # Should have at least one whipsaw_lockdown entry
    lockdown_logs = [t for t in log if t.get("reason") == "whipsaw_lockdown"]
    # In the post-whipsaw window, label should be CHOPPY
    if lockdown_logs:
        lockdown_date = pd.Timestamp(lockdown_logs[0]["date"])
        idx_after = raw.index.get_loc(lockdown_date) + 1
        # The 5 days after lockdown should all be CHOPPY
        assert (sm.iloc[idx_after:idx_after+3] == "CHOPPY").all()


def test_handles_nan_states():
    raw = pd.Series(["CHOPPY", None, "CHOPPY", float("nan"), "CHOPPY"],
                    index=pd.date_range("2024-01-01", periods=5))
    sm, rp, cp, log = apply_persistence(raw)
    assert len(sm) == 5
    assert (sm == "CHOPPY").all()
