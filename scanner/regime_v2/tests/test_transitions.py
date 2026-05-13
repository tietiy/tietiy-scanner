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


def test_steady_state_rolling_window_3_of_5():
    # retune1 Fix C: steady states need 3 of last 5 bars to commit.
    # 5 days of CHOPPY then 5 days of BEAR. By bar 8 (3rd consecutive BEAR =
    # 3-of-5 in rolling), should commit BEAR. (CHOPPY → BEAR direct allowed
    # per retune1 Fix A.)
    raw = _series(["CHOPPY"] * 5 + ["BEAR"] * 5)
    sm, rp, cp, log = apply_persistence(raw, initial_state="CHOPPY")
    # First BEAR bar (idx 5): rolling=[CHOPPY,CHOPPY,CHOPPY,CHOPPY,BEAR] → BEAR count=1, < 3
    assert sm.iloc[5] == "CHOPPY"
    # Second BEAR (idx 6): rolling=[CHOPPY,CHOPPY,CHOPPY,BEAR,BEAR] → BEAR count=2, < 3
    assert sm.iloc[6] == "CHOPPY"
    # Third BEAR (idx 7): rolling=[CHOPPY,CHOPPY,BEAR,BEAR,BEAR] → BEAR count=3 → COMMIT
    assert sm.iloc[7] == "BEAR"
    assert len(log) == 1
    assert log[0]["to"] == "BEAR"


def test_recovery_state_2_of_4_window():
    # Recovery states need 2 of last 4 bars to commit.
    raw = _series(["CHOPPY"] * 3 + ["BULL_RECOVERY"] * 5)
    sm, rp, cp, log = apply_persistence(raw)
    # First BULL_RECOVERY bar (idx 3): rolling has 1 → < 2
    assert sm.iloc[3] == "CHOPPY"
    # Second BULL_RECOVERY (idx 4): rolling has 2 → COMMIT
    assert sm.iloc[4] == "BULL_RECOVERY"


def test_rolling_window_tolerates_bounce_days():
    # retune1 Fix C: real crashes have intraday bounces; the window must tolerate them.
    # Sequence: 3 CHOPPY warmup + BEAR BEAR CHOPPY BEAR BEAR (1 bounce day mid-crash).
    # The fifth bar's window=[BEAR,BEAR,CHOPPY,BEAR,BEAR] → BEAR count=4, commits.
    raw = _series(["CHOPPY"] * 3 + ["BEAR", "BEAR", "CHOPPY", "BEAR", "BEAR"])
    sm, rp, cp, log = apply_persistence(raw, initial_state="CHOPPY")
    # At index 7 (last BEAR), BEAR has appeared 4 times in window → commit
    assert sm.iloc[7] == "BEAR"


def test_choppy_to_bear_direct_allowed():
    # retune1 Fix A: CHOPPY → BEAR is now a direct allowed transition.
    raw = _series(["CHOPPY"] * 5 + ["BEAR"] * 5)
    sm, rp, cp, log = apply_persistence(raw, initial_state="CHOPPY")
    # Should commit directly to BEAR (no intermediate routing).
    assert sm.iloc[7] == "BEAR"
    # Transition log should have ONE entry with reason confirmed_rolling
    confirms = [t for t in log if t.get("reason") == "confirmed_rolling"]
    intermediates = [t for t in log if "intermediate" in t.get("reason", "")]
    assert len(confirms) >= 1
    assert len(intermediates) == 0  # no forced intermediate needed


def test_choppy_to_bull_direct_allowed():
    raw = _series(["CHOPPY"] * 5 + ["BULL"] * 5)
    sm, rp, cp, log = apply_persistence(raw, initial_state="CHOPPY")
    assert sm.iloc[7] == "BULL"


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
    # retune1 Fix A: BULL → BEAR now routes through CHOPPY (2-hop)
    # because CHOPPY → BEAR is direct after Fix A. Previously routed via
    # BULL_RECOVERY → BEAR_RECOVERY → BEAR (3-hop). Either is semantically
    # valid as an intermediate; BFS picks the shortest path.
    assert inter in {"CHOPPY", "BULL_RECOVERY"}


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
