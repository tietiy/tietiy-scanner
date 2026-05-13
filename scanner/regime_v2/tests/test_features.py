"""Unit tests for features.py."""
import math
import numpy as np
import pandas as pd
import pytest

from scanner.regime_v2.features import compute_features, feature_dict_at


def _make_ohlcv(closes):
    """Build a synthetic OHLCV DataFrame from a list of closes."""
    n = len(closes)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    df = pd.DataFrame({
        "Open": closes,
        "High": [c * 1.005 for c in closes],
        "Low": [c * 0.995 for c in closes],
        "Close": closes,
        "Adj Close": closes,
        "Volume": [1000] * n,
    }, index=idx)
    return df


def test_compute_features_empty():
    df = compute_features(pd.DataFrame())
    assert df.empty


def test_compute_features_basic_shape():
    closes = [100 + i for i in range(300)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    assert len(feats) == 300
    assert "ema50" in feats.columns
    assert "slope_10d_ema50" in feats.columns
    assert "above_ema50" in feats.columns
    assert "ret20_pct" in feats.columns
    # EMA50 needs warmup; later values should be defined
    assert not pd.isna(feats["ema50"].iloc[-1])
    assert not pd.isna(feats["slope_10d_ema50"].iloc[-1])


def test_above_ema50_logic():
    # Strongly rising series: close should be above EMA50
    closes = [100 * (1.01 ** i) for i in range(200)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    assert feats["above_ema50"].iloc[-1]


def test_ret20_pct_computation():
    closes = [100] * 25
    closes[-1] = 110  # +10% jump on last bar relative to close[-21]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    # ret20_pct = (close[-1] / close[-21]) - 1) * 100
    assert abs(feats["ret20_pct"].iloc[-1] - 10.0) < 0.01


def test_slope_sign_for_rising_series():
    closes = [100 + i * 0.5 for i in range(150)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    # Steadily rising — slope_10d_ema50 should be positive at end
    assert feats["slope_10d_ema50"].iloc[-1] > 0


def test_slope_sign_for_falling_series():
    closes = [200 - i * 0.5 for i in range(150)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    assert feats["slope_10d_ema50"].iloc[-1] < 0


def test_feature_dict_at_returns_python_types():
    closes = [100 + i for i in range(150)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    d = feature_dict_at(feats, df.index[-1])
    assert isinstance(d, dict)
    assert isinstance(d.get("above_ema50"), bool)
    # Floats present (slope, ret20)
    assert isinstance(d.get("slope_10d_ema50"), (float, type(None)))


def test_feature_dict_at_missing_date():
    closes = [100 + i for i in range(50)]
    df = _make_ohlcv(closes)
    feats = compute_features(df)
    d = feature_dict_at(feats, "1990-01-01")
    assert d == {}


def test_vix_optional():
    closes = [100 + i for i in range(150)]
    df = _make_ohlcv(closes)
    # With VIX
    vix_series = pd.Series([15.0 + (i % 5) for i in range(150)], index=df.index)
    feats = compute_features(df, vix_series=vix_series)
    assert not pd.isna(feats["india_vix"].iloc[-1])
    # Without VIX
    feats2 = compute_features(df)
    assert pd.isna(feats2["india_vix"].iloc[-1])
