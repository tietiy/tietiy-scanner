"""
Unit tests for feature_extractor.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_feature_extractor.py -v

Coverage groups:
  A. Schema integrity (5)
  B. Cheap feature correctness (10)
  C. Triangle algorithm (5)
  D. Fib algorithm (5)
  E. Swing features (3)
  F. Candle flags (4)
  G. Integration on real signals (3)
  H. No-future-leakage (2)
  I. Cross-family caching efficiency (1)
  Total ≈ 38 tests.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from feature_extractor import (  # noqa: E402
    CachedIndicators,
    FeatureExtractor,
    _CROSS_STOCK_MIN_COVERAGE,
    _DEFERRED_3A,
    _EXPECTED_FEATURE_COUNT,
    _FEAT_PREFIX,
)
from feature_loader import FeatureRegistry  # noqa: E402


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def registry():
    return FeatureRegistry.load_all()


@pytest.fixture(scope="module")
def extractor(registry):
    return FeatureExtractor(registry=registry)


@pytest.fixture
def synthetic_ohlcv_long():
    """130-bar synthetic OHLCV with mild trending behavior; stable for cheap features."""
    n = 130
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    np.random.seed(42)
    closes = 100.0 + np.random.RandomState(7).randn(n).cumsum() * 0.5
    opens = closes - 0.1
    highs = closes + 0.5
    lows = closes - 0.5
    return pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows, "Close": closes,
        "Volume": np.full(n, 1000.0),
    }, index=dates)


@pytest.fixture
def synthetic_signal_long():
    return pd.Series({
        "scan_date": pd.Timestamp("2024-06-30"),
        "symbol": "TEST.NS", "sector": "Bank", "direction": "LONG",
        "regime": "Bull", "regime_score": 0,
        "sec_mom": "Neutral", "rs_q": "Neutral", "vol_q": "Average",
    })


@pytest.fixture
def real_signals():
    """Load 5 real signals from backtest_signals.parquet for integration."""
    df = pd.read_parquet("lab/output/backtest_signals.parquet")
    # Use signals with ≥252 bars of history available
    later = df[df["scan_date"] >= "2018-01-01"].head(5)
    return later


# ════════════════════════════════════════════════════════════════════
# Group A: Schema integrity (5 tests)
# ════════════════════════════════════════════════════════════════════

def test_extract_returns_dataframe_with_114_feat_cols(extractor, real_signals):
    out = extractor.extract(real_signals.iloc[:1])
    feat_cols = [c for c in out.columns if c.startswith(_FEAT_PREFIX)]
    assert len(feat_cols) == _EXPECTED_FEATURE_COUNT, \
        f"expected {_EXPECTED_FEATURE_COUNT} feat_* cols, got {len(feat_cols)}"


def test_feat_column_naming_convention(extractor, registry, real_signals):
    out = extractor.extract(real_signals.iloc[:1])
    expected_ids = {s.feature_id for s in registry.list_all()}
    actual_ids = {c[len(_FEAT_PREFIX):] for c in out.columns
                    if c.startswith(_FEAT_PREFIX)}
    # Allow internal _extractor_error column to coexist; just ensure all
    # registry IDs are present.
    assert expected_ids.issubset(actual_ids), \
        f"missing feature IDs: {expected_ids - actual_ids}"


def test_original_signal_columns_preserved(extractor, real_signals):
    out = extractor.extract(real_signals.iloc[:1])
    for col in real_signals.columns:
        assert col in out.columns, f"original col {col} dropped"


def test_signal_index_preserved(extractor, real_signals):
    out = extractor.extract(real_signals.iloc[:1])
    pd.testing.assert_index_equal(out.index, real_signals.iloc[:1].index)


def test_feature_dtypes_reasonable(extractor, registry, real_signals):
    out = extractor.extract(real_signals.iloc[:1])
    # Verify a few representative feat_* columns have appropriate dtypes
    # (pandas will coerce to object/float depending on content).
    assert out["feat_RSI_14"].dtype.kind in ("f", "i", "O"), \
        "feat_RSI_14 dtype unexpected"
    assert out["feat_ema_alignment"].dtype.kind in ("O", "U"), \
        "feat_ema_alignment should be object/string"


# ════════════════════════════════════════════════════════════════════
# Group B: Cheap feature correctness (10 tests with synthetic data)
# ════════════════════════════════════════════════════════════════════

def test_vol_ratio_20d_synthetic():
    """vol_ratio_20d = today_vol / mean(volume[-21:-1])."""
    vol = pd.Series([100.0] * 20 + [200.0])  # 20 baseline + 1 today
    ratio = FeatureExtractor._vol_ratio(vol, 20)
    assert ratio == pytest.approx(2.0)


def test_safe_div_returns_nan_on_zero():
    assert pd.isna(FeatureExtractor._safe_div(1.0, 0.0))
    assert pd.isna(FeatureExtractor._safe_div(np.nan, 1.0))
    assert FeatureExtractor._safe_div(10.0, 5.0) == pytest.approx(2.0)


def test_consecutive_streak_known_sequence():
    """Up streak: trailing consecutive close > prev_close."""
    # close diffs: +1 +1 -1 +1 +1 +1 → trailing 3 ups
    close = pd.Series([100, 101, 102, 101, 102, 103, 104])
    assert FeatureExtractor._consecutive_streak(close, up=True) == 3
    assert FeatureExtractor._consecutive_streak(close, up=False) == 0


def test_close_pos_in_range_via_volume_family(extractor):
    """close_pos_in_range = (close - low) / (high - low)."""
    cache = CachedIndicators(
        ohlcv=pd.DataFrame(), scan_date=pd.Timestamp("2024-01-01"),
        close_at_signal=110.0, high_at_signal=120.0, low_at_signal=100.0,
        open_at_signal=105.0, volume_at_signal=1000.0, atr_at_signal=5.0,
    )
    # Build minimal ohlcv to avoid index errors elsewhere
    ohlcv = pd.DataFrame(
        {"Open": [105], "High": [120], "Low": [100], "Close": [110],
         "Volume": [1000.0]},
        index=pd.DatetimeIndex([pd.Timestamp("2024-01-01")]),
    )
    sig = pd.Series({"vol_q": "Average"})
    feats = extractor._compute_family_volume(cache, ohlcv, sig)
    # close_pos_in_range = (110-100)/(120-100) = 0.5
    assert feats["close_pos_in_range"] == pytest.approx(0.5)
    # body_to_range_ratio = abs(110-105)/20 = 0.25
    assert feats["body_to_range_ratio"] == pytest.approx(0.25)


def test_round_number_proximity_at_known_levels():
    # Close = 102.5, scale ≤ 1000 → step 100 → nearest = 100; proximity = 2.5/102.5
    assert FeatureExtractor._round_number_proximity(102.5) == pytest.approx(2.5 / 102.5)
    # Close = 1505, scale ≤ 10000 → step 500 → nearest = 1500; proximity = 5/1505
    assert FeatureExtractor._round_number_proximity(1505.0) == pytest.approx(5.0 / 1505.0)
    # Close = 95, scale ≤ 100 → step 10 → nearest = 100 (rounded up); proximity = 5/95
    assert FeatureExtractor._round_number_proximity(95.0) == pytest.approx(5.0 / 95.0)


def test_return_pct_known_series():
    close = pd.Series([100, 102, 104, 106, 108])  # 5 bars
    # 4-bar return: 108/100 - 1 = 0.08
    assert FeatureExtractor._return_pct(close, 4) == pytest.approx(0.08)


def test_inside_day_streak_known_sequence():
    """Inside day streak: today.high <= prev.high AND today.low >= prev.low."""
    # Bars: H = [100,99,98,97]; L = [80,81,82,83] → 3 inside days trailing
    ohlcv = pd.DataFrame({
        "Open": [90, 90, 90, 90], "Close": [90, 90, 90, 90],
        "High": [100, 99, 98, 97], "Low": [80, 81, 82, 83],
        "Volume": [1000, 1000, 1000, 1000],
    })
    streak = FeatureExtractor._inside_day_streak(ohlcv)
    assert streak == 3


def test_range_compression_synthetic():
    """range_compression_5d = (max(H[-5:]) - min(L[-5:])) / mean(close[-5:])."""
    ohlcv = pd.DataFrame({
        "Open": [100] * 5, "Close": [100] * 5,
        "High": [105, 104, 103, 102, 101],  # max=105
        "Low": [95, 96, 97, 98, 99],  # min=95
        "Volume": [1000] * 5,
    })
    rc = FeatureExtractor._range_compression(ohlcv, 5)
    # (105 - 95) / 100 = 0.10
    assert rc == pytest.approx(0.10)


def test_ema_alignment_categorical():
    assert FeatureExtractor._ema_alignment(120, 110, 100, 90) == "bull"
    assert FeatureExtractor._ema_alignment(80, 90, 100, 110) == "bear"
    assert FeatureExtractor._ema_alignment(100, 105, 95, 110) == "mixed"
    assert FeatureExtractor._ema_alignment(np.nan, 105, 95, 110) == "mixed"


def test_regime_state_passthrough(extractor, synthetic_ohlcv_long):
    """regime_state should pass through from signal_row (default 'Choppy')."""
    sig = pd.Series({
        "scan_date": synthetic_ohlcv_long.index[-1], "symbol": "TEST.NS",
        "sector": "Bank", "direction": "LONG", "regime": "Bull",
        "regime_score": 5, "sec_mom": "Strong", "rs_q": "Top",
        "vol_q": "Average",
    })
    feats = extractor.extract_single(sig, synthetic_ohlcv_long)
    assert feats["regime_state"] == "Bull"
    assert feats["sector_momentum_state"] == "Strong"


# ════════════════════════════════════════════════════════════════════
# Group C: Triangle algorithm (5 tests)
# ════════════════════════════════════════════════════════════════════

def _build_30bar_ohlcv():
    dates30 = pd.date_range("2024-05-08", periods=30, freq="B")
    return pd.DataFrame({
        "Open": np.full(30, 108.0), "High": np.full(30, 112.0),
        "Low": np.full(30, 100.0), "Close": np.full(30, 108.0),
        "Volume": np.full(30, 1000.0),
    }, index=dates30)


def _make_cache(ohlcv30, close=110.0, atr=2.0):
    return CachedIndicators(
        ohlcv=ohlcv30, scan_date=ohlcv30.index[-1],
        close_at_signal=close, high_at_signal=close + 1, low_at_signal=close - 1,
        open_at_signal=close, volume_at_signal=1000.0, atr_at_signal=atr,
    )


def test_triangle_ascending_clean_synthetic(extractor):
    """Flat highs at 112 + steep rising lows 90→100→110 should yield quality > 50."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=111.5)
    cache.pivot_highs = [(dates[5], 112.0), (dates[12], 112.0), (dates[20], 112.0)]
    cache.pivot_lows = [(dates[8], 90.0), (dates[15], 100.0), (dates[24], 110.0)]
    result = extractor._triangle_features(cache, ohlcv30, lookback=30)
    assert result["quality_ascending"] > 50, \
        f"clean ascending should score >50, got {result['quality_ascending']}"
    assert result["quality_descending"] == 0


def test_triangle_descending_clean_synthetic(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=101.0)
    cache.pivot_highs = [(dates[5], 130.0), (dates[12], 120.0), (dates[20], 110.0)]
    cache.pivot_lows = [(dates[8], 100.0), (dates[15], 100.0), (dates[24], 100.0)]
    result = extractor._triangle_features(cache, ohlcv30, lookback=30)
    assert result["quality_descending"] > 50
    assert result["quality_ascending"] == 0


def test_triangle_strong_uptrend_no_triangle(extractor):
    """Both highs and lows rising = uptrend, NOT a triangle. Quality < 30 both."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=130.0)
    cache.pivot_highs = [(dates[5], 110.0), (dates[12], 120.0), (dates[20], 130.0)]
    cache.pivot_lows = [(dates[8], 105.0), (dates[15], 115.0), (dates[24], 125.0)]
    result = extractor._triangle_features(cache, ohlcv30, lookback=30)
    assert result["quality_ascending"] < 30
    assert result["quality_descending"] < 30


def test_triangle_random_walk_no_triangle(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=105.0)
    cache.pivot_highs = [(dates[5], 109.0), (dates[12], 113.0), (dates[20], 108.0)]
    cache.pivot_lows = [(dates[8], 102.0), (dates[15], 105.0), (dates[24], 99.0)]
    result = extractor._triangle_features(cache, ohlcv30, lookback=30)
    assert result["quality_ascending"] < 30
    assert result["quality_descending"] < 30


def test_triangle_insufficient_pivots_returns_zero(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30)
    cache.pivot_highs = [(dates[5], 112.0), (dates[12], 112.0)]  # only 2
    cache.pivot_lows = [(dates[8], 100.0)]  # only 1
    result = extractor._triangle_features(cache, ohlcv30, lookback=30)
    assert result["quality_ascending"] == 0
    assert result["quality_descending"] == 0
    assert result["touches"] == 0


# ════════════════════════════════════════════════════════════════════
# Group D: Fib algorithm (5 tests)
# ════════════════════════════════════════════════════════════════════

def test_fib_uptrend_50_at_midpoint(extractor):
    """Up impulse 100→150, current price 125 = exactly 50% retrace."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=125.0, atr=2.0)
    cache.pivot_highs = [(dates[5], 150.0)]
    cache.pivot_lows = [(dates[15], 100.0)]
    sig = pd.Series({"direction": "LONG"})
    result = extractor._fib_features(cache, ohlcv30, sig, lookback=30)
    assert result["fib_50_proximity_atr"] == pytest.approx(0.0, abs=1e-6)


def test_fib_618_calculation(extractor):
    """Up impulse 100→150, current 125. fib_618 = 150 - 0.618*50 = 119.1.
    proximity = |125 - 119.1| / 2 = 2.95"""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=125.0, atr=2.0)
    cache.pivot_highs = [(dates[5], 150.0)]
    cache.pivot_lows = [(dates[15], 100.0)]
    sig = pd.Series({"direction": "LONG"})
    result = extractor._fib_features(cache, ohlcv30, sig, lookback=30)
    expected_fib_618 = 150.0 - 0.618 * 50.0  # 119.1
    expected_proximity = abs(125.0 - expected_fib_618) / 2.0
    assert result["fib_618_proximity_atr"] == pytest.approx(expected_proximity, abs=0.01)


def test_fib_1272_extension_uptrend(extractor):
    """Up impulse 100→150, fib_1272_ext = 150 + 0.272*50 = 163.6.
    Current 125 → proximity = |125 - 163.6| / 2 = 19.3."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=125.0, atr=2.0)
    cache.pivot_highs = [(dates[5], 150.0)]
    cache.pivot_lows = [(dates[15], 100.0)]
    sig = pd.Series({"direction": "LONG"})
    result = extractor._fib_features(cache, ohlcv30, sig, lookback=30)
    expected = abs(125.0 - 163.6) / 2.0
    assert result["fib_1272_extension_proximity_atr"] == pytest.approx(expected, abs=0.05)


def test_fib_no_pivots_returns_nan(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    cache = _make_cache(ohlcv30)
    cache.pivot_highs = []
    cache.pivot_lows = []
    sig = pd.Series({"direction": "LONG"})
    result = extractor._fib_features(cache, ohlcv30, sig, lookback=30)
    for fid in ("fib_382_proximity_atr", "fib_50_proximity_atr",
                  "fib_618_proximity_atr", "fib_786_proximity_atr",
                  "fib_1272_extension_proximity_atr",
                  "fib_1618_extension_proximity_atr"):
        assert pd.isna(result[fid]), f"{fid} should be NaN with no pivots"


def test_fib_direction_switching_long_vs_short(extractor):
    """LONG → uptrend impulse; SHORT → downtrend impulse. With pivots that allow
    both, results should differ."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=110.0, atr=2.0)
    cache.pivot_highs = [(dates[5], 150.0), (dates[20], 120.0)]
    cache.pivot_lows = [(dates[10], 100.0), (dates[25], 105.0)]
    sig_long = pd.Series({"direction": "LONG"})
    sig_short = pd.Series({"direction": "SHORT"})
    long_result = extractor._fib_features(cache, ohlcv30, sig_long, lookback=30)
    short_result = extractor._fib_features(cache, ohlcv30, sig_short, lookback=30)
    # The 50% level should differ between LONG (uses high=150 → low=105 impulse)
    # and SHORT (uses low=100 → high=120 impulse)
    assert (long_result["fib_50_proximity_atr"]
            != short_result["fib_50_proximity_atr"]), \
        "LONG and SHORT should select different impulses"


# ════════════════════════════════════════════════════════════════════
# Group E: Swing features (3 tests)
# ════════════════════════════════════════════════════════════════════

def test_swing_high_count_20d(extractor):
    """Count of pivot highs in last 20 bars."""
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30)
    # Place 2 pivots in last 20 bars (positions 12-29) and 1 outside
    cache.pivot_highs = [(dates[5], 100.0),  # outside last 20
                            (dates[12], 110.0), (dates[20], 115.0)]
    cache.pivot_lows = []
    result = extractor._swing_features(cache, ohlcv30, lookback=20)
    assert result["swing_high_count_20d"] == 2


def test_last_swing_high_distance_atr(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30, close=105.0, atr=2.0)
    # Most recent pivot in last 30 = at dates[20] = price 115
    cache.pivot_highs = [(dates[5], 100.0), (dates[20], 115.0)]
    cache.pivot_lows = []
    result = extractor._swing_features(cache, ohlcv30, lookback=20)
    expected = abs(105.0 - 115.0) / 2.0  # 5.0
    assert result["last_swing_high_distance_atr"] == pytest.approx(expected)


def test_higher_highs_intact_flag(extractor):
    ohlcv30 = _build_30bar_ohlcv()
    dates = ohlcv30.index
    cache = _make_cache(ohlcv30)
    # 3 chronologically rising highs → True
    cache.pivot_highs = [(dates[5], 100.0), (dates[12], 110.0), (dates[20], 120.0)]
    cache.pivot_lows = []
    result = extractor._swing_features(cache, ohlcv30, lookback=20)
    assert result["higher_highs_intact_flag"] is True
    # Non-rising sequence → False
    cache.pivot_highs = [(dates[5], 110.0), (dates[12], 100.0), (dates[20], 105.0)]
    result = extractor._swing_features(cache, ohlcv30, lookback=20)
    assert result["higher_highs_intact_flag"] is False


# ════════════════════════════════════════════════════════════════════
# Group F: Candle flags (4 tests)
# ════════════════════════════════════════════════════════════════════

def test_bullish_engulf_known_pair():
    """Today: green candle that engulfs prev red candle's body.
    Prev body=[98,102] (red). Today body=[97,103] (green) covers prev's body
    because today.open(97) <= prev.close(98) and today.close(103) >= prev.open(102).
    """
    ohlcv = pd.DataFrame({
        "Open": [102, 97],   # prev O=102 (red), today O=97
        "Close": [98, 103],  # prev C=98 (red), today C=103 (green)
        "High": [103, 104], "Low": [97, 96],
        "Volume": [1000, 1000],
    })
    cache = CachedIndicators(
        ohlcv=ohlcv, scan_date=ohlcv.index[-1],
        close_at_signal=103.0, high_at_signal=104.0, low_at_signal=96.0,
        open_at_signal=97.0, volume_at_signal=1000.0, atr_at_signal=2.0,
    )
    out = FeatureExtractor._candle_flag_features(cache, ohlcv)
    assert out["bullish_engulf_flag"] is True
    assert out["bearish_engulf_flag"] is False


def test_hammer_known_candle():
    """10-bar history with hammer at bottom: small body, long lower wick."""
    rows = [{"Open": 100, "Close": 100, "High": 101, "Low": 99,
              "Volume": 1000}] * 9
    rows.append({"Open": 95.5, "Close": 96.0, "High": 96.5, "Low": 90.0,
                  "Volume": 1000})  # hammer
    ohlcv = pd.DataFrame(rows)
    cache = CachedIndicators(
        ohlcv=ohlcv, scan_date=0,
        close_at_signal=96.0, high_at_signal=96.5, low_at_signal=90.0,
        open_at_signal=95.5, volume_at_signal=1000.0, atr_at_signal=1.0,
    )
    out = FeatureExtractor._candle_flag_features(cache, ohlcv)
    assert out["hammer_flag"] is True


def test_inside_bar_flag():
    """today.H < prev.H AND today.L > prev.L (strict)."""
    ohlcv = pd.DataFrame({
        "Open": [100, 100], "Close": [100, 100],
        "High": [105, 103], "Low": [95, 97],
        "Volume": [1000, 1000],
    })
    cache = CachedIndicators(
        ohlcv=ohlcv, scan_date=0,
        close_at_signal=100, high_at_signal=103, low_at_signal=97,
        open_at_signal=100, volume_at_signal=1000.0, atr_at_signal=1.0,
    )
    out = FeatureExtractor._candle_flag_features(cache, ohlcv)
    assert out["inside_bar_flag"] is True
    assert out["outside_bar_flag"] is False


def test_gap_up_pct():
    """gap_up_pct = max(0, (today.open - prev.close) / prev.close)."""
    ohlcv = pd.DataFrame({
        "Open": [100, 105],  # prev open=100, today opens at 105 (gap up)
        "Close": [100, 106], "High": [101, 107], "Low": [99, 104.5],
        "Volume": [1000, 1000],
    })
    cache = CachedIndicators(
        ohlcv=ohlcv, scan_date=0,
        close_at_signal=106.0, high_at_signal=107.0, low_at_signal=104.5,
        open_at_signal=105.0, volume_at_signal=1000.0, atr_at_signal=1.0,
    )
    out = FeatureExtractor._candle_flag_features(cache, ohlcv)
    expected = (105.0 - 100.0) / 100.0
    assert out["gap_up_pct"] == pytest.approx(expected)
    assert out["gap_down_pct"] == 0.0


# ════════════════════════════════════════════════════════════════════
# Group G: Integration on real signals (3 tests)
# ════════════════════════════════════════════════════════════════════

def test_real_signal_returns_114_features(extractor, real_signals):
    sig = real_signals.iloc[0]
    sym_path = Path(f"lab/cache/{sig['symbol'].replace('.NS', '_NS')}.parquet")
    stock_df = pd.read_parquet(sym_path)
    stock_df.index = pd.to_datetime(stock_df.index)
    stock_df = stock_df.sort_index().dropna(subset=["Close"])
    feats = extractor.extract_single(sig, stock_df)
    assert len(feats) == _EXPECTED_FEATURE_COUNT


def test_real_signal_nan_rate_below_50pct(extractor, real_signals):
    sig = real_signals.iloc[0]
    sym_path = Path(f"lab/cache/{sig['symbol'].replace('.NS', '_NS')}.parquet")
    stock_df = pd.read_parquet(sym_path)
    stock_df.index = pd.to_datetime(stock_df.index)
    stock_df = stock_df.sort_index().dropna(subset=["Close"])
    feats = extractor.extract_single(sig, stock_df)

    def _is_nan(v):
        if isinstance(v, str):
            return False
        try:
            return pd.isna(v)
        except Exception:
            return False
    nan_count = sum(1 for v in feats.values() if _is_nan(v))
    nan_rate = nan_count / _EXPECTED_FEATURE_COUNT
    assert nan_rate < 0.5, f"NaN rate {nan_rate:.0%} exceeds 50% threshold"


def test_real_extract_batch_3_signals(extractor, real_signals):
    out = extractor.extract(real_signals.iloc[:3])
    assert len(out) == 3
    feat_cols = [c for c in out.columns if c.startswith(_FEAT_PREFIX)]
    assert len(feat_cols) >= _EXPECTED_FEATURE_COUNT


# ════════════════════════════════════════════════════════════════════
# Group H: No-future-leakage (2 tests — CRITICAL)
# ════════════════════════════════════════════════════════════════════

def test_no_future_leakage_truncated_vs_full(extractor):
    """At date T, computing features with full history vs truncated history
    (cut at T) must produce identical results."""
    df = pd.read_parquet("lab/output/backtest_signals.parquet")
    sig = df[df["scan_date"] >= "2018-01-01"].iloc[0]
    sym_path = Path(f"lab/cache/{sig['symbol'].replace('.NS', '_NS')}.parquet")
    stock_full = pd.read_parquet(sym_path)
    stock_full.index = pd.to_datetime(stock_full.index)
    stock_full = stock_full.sort_index().dropna(subset=["Close"])
    scan_date = pd.Timestamp(sig["scan_date"])
    stock_trunc = stock_full.loc[stock_full.index <= scan_date]
    feats_full = extractor.extract_single(sig, stock_full)
    feats_trunc = extractor.extract_single(sig, stock_trunc)

    def _eq(a, b):
        if isinstance(a, str) or isinstance(b, str):
            return a == b
        if pd.isna(a) and pd.isna(b):
            return True
        if pd.isna(a) or pd.isna(b):
            return False
        return abs(float(a) - float(b)) < 1e-6

    diffs = [(fid, feats_full[fid], feats_trunc[fid])
                for fid in feats_full
                if not _eq(feats_full[fid], feats_trunc[fid])]
    assert not diffs, f"future leakage on features: {diffs[:5]}"


def test_insufficient_history_returns_nan_gracefully(extractor):
    """5-bar history → most features NaN, no exceptions raised."""
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    np.random.seed(42)
    closes = 100.0 + np.random.RandomState(7).randn(5).cumsum() * 0.1
    ohlcv = pd.DataFrame({
        "Open": closes, "High": closes + 0.5, "Low": closes - 0.5,
        "Close": closes, "Volume": np.full(5, 1000.0),
    }, index=dates)
    sig = pd.Series({
        "scan_date": dates[-1], "symbol": "TEST.NS", "sector": "Bank",
        "direction": "LONG", "regime": "Bull", "regime_score": 0,
        "sec_mom": "Neutral", "rs_q": "Neutral", "vol_q": "Average",
    })
    # Should not raise
    feats = extractor.extract_single(sig, ohlcv)
    assert len(feats) == _EXPECTED_FEATURE_COUNT


# ════════════════════════════════════════════════════════════════════
# Group I: Cross-family caching efficiency (1 test)
# ════════════════════════════════════════════════════════════════════

def test_detect_pivots_called_at_most_once_per_signal(extractor, real_signals):
    """Pivots are computed once in _compute_cached_indicators and reused by
    every family that needs them (zones, swings, triangle, Fib)."""
    sig = real_signals.iloc[0]
    sym_path = Path(f"lab/cache/{sig['symbol'].replace('.NS', '_NS')}.parquet")
    stock_df = pd.read_parquet(sym_path)
    stock_df.index = pd.to_datetime(stock_df.index)
    stock_df = stock_df.sort_index().dropna(subset=["Close"])

    import feature_extractor as fe_mod
    original = fe_mod._scanner_detect_pivots
    call_count = {"n": 0}

    def counting_detect_pivots(df, *a, **kw):
        call_count["n"] += 1
        return original(df, *a, **kw)

    with patch.object(fe_mod, "_scanner_detect_pivots",
                       side_effect=counting_detect_pivots):
        extractor.extract_single(sig, stock_df)

    assert call_count["n"] <= 1, (
        f"detect_pivots called {call_count['n']} times — caching broken")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
