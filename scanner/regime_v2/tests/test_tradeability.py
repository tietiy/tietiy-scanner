"""Unit tests for tradeability.py (Scheme B logic)."""
import pandas as pd
import pytest

from scanner.regime_v2.tradeability import classify_tradeability, compute_tradeability


def test_raw_bear_is_tradeable():
    r = classify_tradeability("BEAR", ret_30d_prior_pct=-3.0)
    assert r["v2_bear_tradeable"] is True
    assert r["bypass_path"] == "raw_bear"
    assert r["tradeability_source"] == "v2_raw_bear"


def test_raw_bear_recovery_is_tradeable():
    r = classify_tradeability("BEAR_RECOVERY", ret_30d_prior_pct=2.0)
    assert r["v2_bear_tradeable"] is True
    assert r["bypass_path"] == "raw_bear_recovery"
    assert r["tradeability_source"] == "v2_raw_bear"


def test_choppy_with_deep_drawdown_uses_bypass():
    r = classify_tradeability("CHOPPY", ret_30d_prior_pct=-12.0)
    assert r["v2_bear_tradeable"] is True
    assert r["bypass_path"] == "group_a_bypass"
    assert r["tradeability_source"] == "v2_bypass_deep_crash"


def test_choppy_at_exact_threshold_uses_bypass():
    # -9.0 is the threshold — inclusive
    r = classify_tradeability("CHOPPY", ret_30d_prior_pct=-9.0)
    assert r["v2_bear_tradeable"] is True
    assert r["bypass_path"] == "group_a_bypass"


def test_choppy_shallow_drawdown_not_tradeable():
    r = classify_tradeability("CHOPPY", ret_30d_prior_pct=-3.0)
    assert r["v2_bear_tradeable"] is False
    assert r["bypass_path"] == "none"
    assert r["tradeability_source"] == "not_tradeable"


def test_bull_not_tradeable():
    r = classify_tradeability("BULL", ret_30d_prior_pct=-12.0)
    # Even with deep drawdown, BULL raw blocks tradeability
    assert r["v2_bear_tradeable"] is False
    assert r["bypass_path"] == "none"


def test_bull_recovery_not_tradeable():
    r = classify_tradeability("BULL_RECOVERY", ret_30d_prior_pct=0.0)
    assert r["v2_bear_tradeable"] is False
    assert r["bypass_path"] == "none"


def test_none_ret30_with_choppy_not_tradeable():
    # Missing ret_30d data → cannot trigger bypass
    r = classify_tradeability("CHOPPY", ret_30d_prior_pct=None)
    assert r["v2_bear_tradeable"] is False
    assert r["bypass_path"] == "none"


def test_compute_tradeability_dataframe_roundtrip():
    signals = pd.DataFrame({
        "id": ["A", "B", "C", "D"],
        "date": pd.to_datetime(
            ["2026-04-01", "2026-04-02", "2026-04-03", "2026-04-04"]
        ),
        "ret_30d_prior_at_signal": [-12.0, -3.0, -1.0, 5.0],
    })
    regime_hist = pd.DataFrame({
        "state_raw": ["CHOPPY", "CHOPPY", "BEAR", "BULL"],
        "state": ["CHOPPY", "CHOPPY", "CHOPPY", "BULL"],
    }, index=pd.to_datetime(
        ["2026-04-01", "2026-04-02", "2026-04-03", "2026-04-04"]
    ))

    out = compute_tradeability(signals, regime_hist)

    # Row A: CHOPPY raw + ret_30d -12% → group_a_bypass
    assert out.loc[0, "v2_bear_tradeable"] is True or out.loc[0, "v2_bear_tradeable"] == True
    assert out.loc[0, "bypass_path"] == "group_a_bypass"
    # Row B: CHOPPY raw + ret_30d -3% → not tradeable
    assert bool(out.loc[1, "v2_bear_tradeable"]) is False
    assert out.loc[1, "bypass_path"] == "none"
    # Row C: BEAR raw → raw_bear
    assert bool(out.loc[2, "v2_bear_tradeable"]) is True
    assert out.loc[2, "bypass_path"] == "raw_bear"
    # Row D: BULL raw → none
    assert bool(out.loc[3, "v2_bear_tradeable"]) is False
    assert out.loc[3, "bypass_path"] == "none"

    # Verify the 5 expected columns exist
    for col in ("regime_v2_raw", "regime_v2_smooth", "v2_bear_tradeable",
                "bypass_path", "tradeability_source"):
        assert col in out.columns, f"missing column {col}"


def test_compute_tradeability_handles_signal_on_non_regime_date():
    # Signal date later than last regime bar — should fall back gracefully (None state)
    signals = pd.DataFrame({
        "date": pd.to_datetime(["2030-01-01"]),
        "ret_30d_prior_at_signal": [-5.0],
    })
    regime_hist = pd.DataFrame({
        "state_raw": ["CHOPPY"],
        "state": ["CHOPPY"],
    }, index=pd.to_datetime(["2026-04-01"]))

    out = compute_tradeability(signals, regime_hist)
    # Future signal has no bar at or after — regime_v2_raw should be None
    assert out.loc[0, "regime_v2_raw"] is None
    assert bool(out.loc[0, "v2_bear_tradeable"]) is False
