"""Unit tests for classifier.py (5-gate decision tree)."""
import pytest

from scanner.regime_v2.classifier import classify_regime


def _f(**overrides):
    """Build a feature dict with sensible defaults; override what test cares about."""
    base = {
        "above_ema50": False,
        "above_ema200": False,
        "above_ema20": False,
        "slope_10d_ema50": 0.0,
        "ret20_pct": 0.0,
        "realized_vol_20d_pct": 15.0,
        "india_vix": None,
        "vix_change_10d_pct": None,
        "banknifty_rs_pp": None,
    }
    base.update(overrides)
    return base


# ----- VIX-AVAILABLE MODE -----

def test_bull_with_vix():
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.01, ret20_pct=8.0, india_vix=15.0,
    ))
    assert state == "BULL"


def test_bull_blocked_by_vix():
    # Slope strong, but VIX too high → not Bull
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.01, ret20_pct=8.0, india_vix=22.0,
    ))
    assert state != "BULL"


def test_bear_with_vix():
    state, _, _ = classify_regime(_f(
        above_ema50=False, above_ema200=False,
        slope_10d_ema50=-0.005, ret20_pct=-4.0, india_vix=24.0,
    ))
    assert state == "BEAR"


def test_bull_recovery_with_vix():
    # Above EMA50, slope just positive (≤0.005), strong ret20, low vix
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.003, ret20_pct=5.0, india_vix=17.0,
    ))
    assert state == "BULL_RECOVERY"


def test_bear_recovery():
    state, _, _ = classify_regime(_f(
        above_ema50=False, above_ema200=False,
        slope_10d_ema50=0.001, ret20_pct=1.0, india_vix=20.0,
    ))
    assert state == "BEAR_RECOVERY"


def test_choppy_residual():
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=False,
        slope_10d_ema50=0.001, ret20_pct=1.0, india_vix=20.0,
    ))
    # Above_ema50 True, below 200, weak slope, low ret20 → no gate matches → CHOPPY
    assert state == "CHOPPY"


# ----- VIX-MISSING / DEGRADED MODE -----

def test_bull_degraded_mode_slope_or_ret20():
    # retune2 Fix E: VIX-degraded BULL gate uses slope>0.004 OR ret20>3%.
    # Either momentum signal qualifies (plus structural reqs).

    # Slope below 0.004 BUT ret20 strong (>3%) → Bull qualifies
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.001, ret20_pct=5.0,
    ))  # no vix
    assert state == "BULL", "ret20>3% should qualify under degraded mode"

    # Slope above 0.004 (loose threshold) — also qualifies
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.005, ret20_pct=1.0,
    ))
    assert state == "BULL", "slope>0.004 should qualify under degraded mode"

    # Both fail — slope tiny AND ret20 low — should NOT be Bull
    state, _, _ = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.001, ret20_pct=1.5,
    ))
    assert state != "BULL"


def test_bull_recovery_suppressed_in_degraded_mode():
    # retune2 Fix E note: Bull gate in degraded mode is now slope>0.004 OR ret20>3%
    # So we need conditions that fail BULL but would have triggered BULL_RECOVERY.
    # Use slope=0.003 (fails 0.004) AND ret20=2.0 (fails 3.0): Bull-Recovery
    # would fire with VIX (ret20>3 needed there), but here both gates fail.
    state, _, trace = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.003, ret20_pct=2.0,
    ))
    assert state != "BULL"
    assert state != "BULL_RECOVERY"
    assert state == "CHOPPY"
    bull_recov = [t for t in trace if t.get("gate") == "BULL_RECOVERY"]
    assert bull_recov and bull_recov[0].get("reason") == "suppressed_vix_missing"


def test_bear_works_without_vix():
    # Bear doesn't require VIX (only excludes it from the gate); without VIX
    # the gate omits the vix condition entirely.
    state, _, _ = classify_regime(_f(
        above_ema50=False, above_ema200=False,
        slope_10d_ema50=-0.005, ret20_pct=-4.0,
    ))
    assert state == "BEAR"


def test_bear_recovery_works_without_vix():
    # Bear-Recovery uses no VIX in its conditions
    state, _, _ = classify_regime(_f(
        above_ema50=False, above_ema200=False,
        slope_10d_ema50=0.001, ret20_pct=1.0,
    ))
    assert state == "BEAR_RECOVERY"


# ----- ROBUSTNESS -----

def test_missing_core_features_returns_choppy():
    state, conf, trace = classify_regime({
        "above_ema50": True,
        # slope and ret20 missing
    })
    assert state == "CHOPPY"
    assert conf == 0.0


def test_nan_slope_returns_choppy():
    state, _, _ = classify_regime(_f(slope_10d_ema50=float("nan"), ret20_pct=1.0))
    assert state == "CHOPPY"


def test_gate_trace_records_evaluation():
    state, _, trace = classify_regime(_f(
        above_ema50=True, above_ema200=True,
        slope_10d_ema50=0.01, ret20_pct=8.0, india_vix=15.0,
    ))
    assert state == "BULL"
    # Trace should have entries for gates tested; first matched should be Bull
    matched_gates = [t["gate"] for t in trace if t.get("matched")]
    assert "BULL" in matched_gates
