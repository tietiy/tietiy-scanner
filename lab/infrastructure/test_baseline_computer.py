"""
Unit tests for baseline_computer.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_baseline_computer.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baseline_computer import (  # noqa: E402
    BaselineComputer,
    SignalOutcome,
    compute_signal_outcome,
    wilson_interval,
    binomial_p_two_sided,
    confidence_tier,
    FLAT_THRESHOLD,
)


# ════════════════════════════════════════════════════════════════════
# Wilson interval math
# ════════════════════════════════════════════════════════════════════

def test_wilson_interval_known_values():
    """k=8, n=10 → expected ~[0.49, 0.94] per standard Wilson tables."""
    lower, upper = wilson_interval(8, 10)
    assert 0.45 <= lower <= 0.55, f"Wilson lower for 8/10: got {lower}"
    assert 0.92 <= upper <= 0.96, f"Wilson upper for 8/10: got {upper}"


def test_wilson_interval_edge_cases():
    # All wins
    lower, upper = wilson_interval(10, 10)
    assert lower > 0.65 and upper == 1.0
    # All losses
    lower, upper = wilson_interval(0, 10)
    assert lower == 0.0 and upper < 0.35
    # n=0
    lower, upper = wilson_interval(0, 0)
    assert lower == 0.0 and upper == 0.0
    # 50/50
    lower, upper = wilson_interval(50, 100)
    assert 0.40 <= lower <= 0.42
    assert 0.59 <= upper <= 0.61


def test_wilson_interval_large_n():
    # Large n — Wilson should converge to normal approximation
    lower, upper = wilson_interval(580, 1000)
    # Empirical: 0.549, 0.610 for n=1000 k=580 (verified)
    assert 0.54 <= lower <= 0.56
    assert 0.60 <= upper <= 0.62


# ════════════════════════════════════════════════════════════════════
# Binomial p-value
# ════════════════════════════════════════════════════════════════════

def test_binomial_p_at_null():
    # k = n/2, exactly null → p ≈ 1
    p = binomial_p_two_sided(50, 100, 0.5)
    assert p > 0.9


def test_binomial_p_clearly_significant():
    # 80 wins out of 100 with null=0.5 → p << 0.001
    p = binomial_p_two_sided(80, 100, 0.5)
    assert p < 0.001


def test_binomial_p_n_zero():
    assert binomial_p_two_sided(0, 0, 0.5) == 1.0


# ════════════════════════════════════════════════════════════════════
# Confidence tier
# ════════════════════════════════════════════════════════════════════

def test_confidence_tier_thresholds():
    assert confidence_tier(150) == "high"
    assert confidence_tier(100) == "high"
    assert confidence_tier(99) == "low"
    assert confidence_tier(30) == "low"
    assert confidence_tier(29) == "too_low"
    assert confidence_tier(0) == "too_low"


# ════════════════════════════════════════════════════════════════════
# compute_signal_outcome — synthetic OHLCV scenarios
# ════════════════════════════════════════════════════════════════════

def _build_synthetic_ohlcv(closes: list[float],
                              start_date: str = "2024-01-01") -> pd.DataFrame:
    n = len(closes)
    dates = pd.date_range(start_date, periods=n, freq="B")
    # Simple OHLC: high/low ±0.5 around close
    df = pd.DataFrame({
        "Open": closes,
        "High": [c + 0.5 for c in closes],
        "Low": [c - 0.5 for c in closes],
        "Close": closes,
        "Volume": [1000] * n,
    }, index=dates)
    return df


def test_long_signal_no_stop_hit_winner():
    """LONG, entry=100, stop=95. Forward closes: 102, 103, 105, 107, 108.
    D5 close = 108. Return = (108-100)/100 = 0.08. Win."""
    ohlcv = _build_synthetic_ohlcv([100, 102, 103, 105, 107, 108])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=95,
                                 direction="LONG", horizon_days=5)
    assert o.label == "W"
    assert o.exit_type == "HORIZON_CLOSE"
    assert o.exit_day == 5
    assert abs(o.return_pct - 0.08) < 1e-6


def test_long_signal_stop_hit_on_day_2():
    """LONG, entry=100, stop=95. Bars after scan: closes=[98, 93, 99, 100, 102].
    Forward bar 1 (close=98, Low=97.5) — no breach.
    Forward bar 2 (close=93, Low=92.5) — breaches stop=95 → exit_day=2.
    Return = (95-100)/100 = -0.05."""
    # 6 bars total: scan_date bar + 5 forward bars (handles horizon=5)
    ohlcv = _build_synthetic_ohlcv([100, 98, 93, 99, 100, 102])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=95,
                                 direction="LONG", horizon_days=5)
    assert o.label == "L"
    assert o.exit_type == "STOP_HIT"
    assert o.exit_day == 2
    assert abs(o.return_pct - (-0.05)) < 1e-6


def test_short_signal_no_stop_winner():
    """SHORT, entry=100, stop=105. Closes drift down: 99, 97, 95, 92, 90.
    D5 close = 90. Return = (100-90)/100 = 0.10. Win."""
    ohlcv = _build_synthetic_ohlcv([100, 99, 97, 95, 92, 90])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=105,
                                 direction="SHORT", horizon_days=5)
    assert o.label == "W"
    assert o.exit_type == "HORIZON_CLOSE"
    assert abs(o.return_pct - 0.10) < 1e-6


def test_short_signal_stop_hit():
    """SHORT, entry=100, stop=105. Forward closes: 102, 107, 105, 100, 98.
    Forward bar 2 (close=107, High=107.5) breaches stop=105 → exit_day=2.
    Exit at stop=105. SHORT return = (100-105)/100 = -0.05. Loss."""
    # 6 bars: scan_date + 5 forward
    ohlcv = _build_synthetic_ohlcv([100, 102, 107, 105, 100, 98])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=105,
                                 direction="SHORT", horizon_days=5)
    assert o.label == "L"
    assert o.exit_type == "STOP_HIT"
    assert o.exit_day == 2
    assert abs(o.return_pct - (-0.05)) < 1e-6


def test_flat_outcome_excluded_from_wl():
    """LONG, entry=100, stop=95. Closes: 100, 100.05, 100.02, 100.01, 100.0.
    Final close 100.0 → return 0.0 → flat."""
    ohlcv = _build_synthetic_ohlcv([100, 100.05, 100.02, 100.01, 100.0])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=95,
                                 direction="LONG", horizon_days=4)
    # forward bar 4 = closes[4]=100.0 → return 0.0; |return| < FLAT_THRESHOLD
    assert o.label == "F"
    assert o.exit_type == "HORIZON_CLOSE"


def test_insufficient_history_returns_INSUFFICIENT():
    """Only 3 bars of forward history; ask for 5-day horizon."""
    ohlcv = _build_synthetic_ohlcv([100, 101, 102, 103])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=100, stop=95,
                                 direction="LONG", horizon_days=5)
    assert o.label == "INSUFFICIENT"
    assert o.exit_type == "INSUFFICIENT"
    assert o.return_pct is None


def test_no_entry_price_returns_NO_DATA():
    ohlcv = _build_synthetic_ohlcv([100, 101, 102, 103, 104, 105])
    scan_date = ohlcv.index[0]
    o = compute_signal_outcome(ohlcv, scan_date,
                                 entry_price=np.nan, stop=95,
                                 direction="LONG", horizon_days=5)
    assert o.label == "NO_DATA"


# ════════════════════════════════════════════════════════════════════
# BaselineComputer aggregation
# ════════════════════════════════════════════════════════════════════

def test_aggregate_produces_expected_structure():
    """Synthetic outcomes DataFrame with 2 cohorts × 2 horizons; verify
    aggregate emits stats and validation counts."""
    outcomes = pd.DataFrame([
        # UP_TRI × Bear × D6 — clear win cohort
        *[{"sig_idx": i, "signal": "UP_TRI", "regime": "Bear", "horizon": 6,
            "label": "W", "return_pct": 0.05, "exit_type": "HORIZON_CLOSE",
            "exit_day": 6} for i in range(80)],
        *[{"sig_idx": i, "signal": "UP_TRI", "regime": "Bear", "horizon": 6,
            "label": "L", "return_pct": -0.04, "exit_type": "STOP_HIT",
            "exit_day": 3} for i in range(20)],
        # UP_TRI × Bear × D10 — different mix
        *[{"sig_idx": i, "signal": "UP_TRI", "regime": "Bear", "horizon": 10,
            "label": "W", "return_pct": 0.07, "exit_type": "HORIZON_CLOSE",
            "exit_day": 10} for i in range(70)],
        *[{"sig_idx": i, "signal": "UP_TRI", "regime": "Bear", "horizon": 10,
            "label": "L", "return_pct": -0.04, "exit_type": "STOP_HIT",
            "exit_day": 3} for i in range(30)],
        # DOWN_TRI × Bull × D6 — too small
        *[{"sig_idx": i, "signal": "DOWN_TRI", "regime": "Bull", "horizon": 6,
            "label": "L", "return_pct": -0.02, "exit_type": "HORIZON_CLOSE",
            "exit_day": 6} for i in range(5)],
    ])
    result = BaselineComputer.aggregate(outcomes)
    assert "cohorts" in result
    upd6 = result["cohorts"]["UP_TRI"]["Bear"]["D6"]
    assert upd6["n"] == 100
    assert upd6["n_wins"] == 80
    assert upd6["n_losses"] == 20
    assert abs(upd6["wr"] - 0.80) < 1e-6
    assert upd6["confidence"] == "high"
    # Wilson lower > 0.7 for 80/100
    assert upd6["wilson_lower_95"] > 0.7
    # p-value vs 50% should be very small
    assert upd6["p_value_vs_50"] < 1e-6

    # DOWN_TRI × Bull × D6 too few signals → marked too_low
    dnd6 = result["cohorts"]["DOWN_TRI"]["Bull"]["D6"]
    assert dnd6["confidence"] == "too_low"
    assert dnd6["wr"] is None  # skipped
    assert result["validation"]["cells_skipped_insufficient_n"] >= 1
    assert result["validation"]["cells_high_confidence"] >= 2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
