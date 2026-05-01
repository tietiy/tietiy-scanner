"""
Generator for lab/feature_library/<feature_id>.json × 114.

One-time / regeneration helper. Encodes the canonical 114-feature spec from
`lab/COMBINATION_ENGINE_FEATURE_SPEC.md` (v2.1) as Python data, then writes
one JSON file per feature.

Re-run after spec updates to regenerate the JSON library cleanly.

Run:
    .venv/bin/python lab/infrastructure/_generate_feature_library.py

Output: lab/feature_library/<feature_id>.json × 114, plus printed family-count
summary for verification.
"""
from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_OUT_DIR = _LAB_ROOT / "feature_library"

SPEC_VERSION = "v2.1"


def _bool_thresholds() -> dict:
    """Boolean / categorical features have no numeric thresholds."""
    return {"low": None, "medium": None, "high": None}


# ── Feature definitions, family by family ────────────────────────────

FEATURES: list[dict] = []

# ── Family 1 — Compression / range (15) ──────────────────────────────
FAM1_COMPRESSION = [
    {
        "feature_id": "range_compression_5d",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.02", "medium": "0.02-0.05", "high": ">0.05"},
        "direction": "bullish (low)",
        "mechanism": "Tighter range over 5d = recent accumulation/distribution; breakout follow-through statistically higher post-compression. range / avg_close formula.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "range_compression_10d",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.03", "medium": "0.03-0.07", "high": ">0.07"},
        "direction": "bullish (low)",
        "mechanism": "Tighter range over 10d = accumulation/distribution; 10d timeframe captures intermediate compression.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "range_compression_20d",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.05", "medium": "0.05-0.12", "high": ">0.12"},
        "direction": "bullish (low)",
        "mechanism": "Tighter range over 20d = accumulation/distribution; 20d timeframe captures swing-trader compression.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "range_compression_60d",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.08", "medium": "0.08-0.20", "high": ">0.20"},
        "direction": "bullish (low)",
        "mechanism": "Tighter range over 60d = quarterly-scale accumulation/distribution; longer base = explosive breakout potential.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "compression_duration",
        "value_type": "int", "value_range": "0-60",
        "level_thresholds": {"low": "<5", "medium": "5-15", "high": ">15"},
        "direction": "bullish (high)",
        "mechanism": "Days inside <5% range; longer compression = more pent-up energy; explosive moves more likely on resolution.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "inside_day_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Today's high <= prior high AND today's low >= prior low. Classical narrow-range pattern that precedes expansion days.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "inside_day_streak",
        "value_type": "int", "value_range": "0-10",
        "level_thresholds": {"low": "<2", "medium": "2-3", "high": ">3"},
        "direction": "bullish (high)",
        "mechanism": "Consecutive inside days; longer streak = stronger compression = stronger breakout candidate.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "NR4_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Today's range = narrowest of last 4 days. Classical pre-breakout volatility-contraction pattern.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "NR7_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Today's range = narrowest of last 7 days. Stronger compression signal than NR4.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "bollinger_squeeze_20d",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish",
        "mechanism": "Bollinger Band width < Keltner Channel width = volatility contraction; classical pre-breakout setup.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "bollinger_band_width_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.04", "medium": "0.04-0.10", "high": ">0.10"},
        "direction": "bullish (low)",
        "mechanism": "BB width / mid-band; lower = more contracted volatility, higher breakout potential.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "atr_compression_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.0", "high": ">1.0"},
        "direction": "bullish (low)",
        "mechanism": "Current ATR / 60d avg ATR; <1 = vol contraction; <0.5 = strong contraction. Complements range-based features with true-range perspective.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "range_position_in_window",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.25", "medium": "0.25-0.75", "high": ">0.75"},
        "direction": "both (regime-dep)",
        "mechanism": "Close position in 20d high-low range; <0.25 near low (potential reversal), >0.75 near high (continuation candidate).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "coiled_spring_score",
        "value_type": "float", "value_range": "0-100",
        "level_thresholds": {"low": "<33", "medium": "33-67", "high": ">67"},
        "direction": "bullish (high)",
        "mechanism": "Composite of compression + favorable trend (low ATR ratio + positive EMA alignment + low BB width); designed to capture prime breakout setups.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "consolidation_quality",
        "value_type": "categorical", "value_range": "tight / loose / none",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (tight)",
        "mechanism": "Human-readable bucket combining range tightness + parallel/wedge geometry. tight = textbook consolidation; loose = noisy chop; none = no clear pattern.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
]

for f in FAM1_COMPRESSION:
    f["family"] = "compression"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Family 2 — Institutional zone (22) ──────────────────────────────
FAM2_INSTITUTIONAL = [
    {
        "feature_id": "fvg_above_proximity",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "regime-dependent",
        "mechanism": "ATRs to nearest above-price fair-value-gap (imbalance zone). Price often revisits FVGs; proximity matters for entry quality.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fvg_below_proximity",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "regime-dependent",
        "mechanism": "ATRs to nearest below-price fair-value-gap. Price often revisits FVGs; proximity matters for entry quality.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fvg_unfilled_above_count",
        "value_type": "int", "value_range": "0-20",
        "level_thresholds": {"low": "<2", "medium": "2-5", "high": ">5"},
        "direction": "bullish (high; targets)",
        "mechanism": "Unfilled FVGs above current price within 60d; more unfilled FVGs = more potential targets in upward direction.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fvg_unfilled_below_count",
        "value_type": "int", "value_range": "0-20",
        "level_thresholds": {"low": "<2", "medium": "2-5", "high": ">5"},
        "direction": "bearish (high; targets)",
        "mechanism": "Unfilled FVGs below current price within 60d; more unfilled FVGs = more potential targets in downward direction.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "ob_bullish_proximity",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "bullish (low)",
        "mechanism": "ATRs to nearest bullish order block (institutional accumulation candle); price often respects these on retest. Low = entry near accumulation zone.",
        "data_source": "OHLCV", "computation_complexity": "expensive",
    },
    {
        "feature_id": "ob_bearish_proximity",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "bearish (low)",
        "mechanism": "ATRs to nearest bearish order block (institutional distribution candle); price often respects these on retest. Low = entry near distribution zone.",
        "data_source": "OHLCV", "computation_complexity": "expensive",
    },
    {
        "feature_id": "support_zone_distance_atr",
        "value_type": "float", "value_range": "0-20",
        "level_thresholds": {"low": "<1", "medium": "1-3", "high": ">3"},
        "direction": "bullish (low)",
        "mechanism": "ATRs to nearest support per existing scanner_core detect_pivots zones; reuse signal-row fields for cheap access. Low = potential bounce zone.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "resistance_zone_distance_atr",
        "value_type": "float", "value_range": "0-20",
        "level_thresholds": {"low": "<1", "medium": "1-3", "high": ">3"},
        "direction": "bearish (low)",
        "mechanism": "ATRs to nearest resistance per scanner_core detect_pivots zones; reuse signal-row fields. Low = price at potential rejection zone.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "prior_swing_high_distance_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.02", "medium": "0.02-0.10", "high": ">0.10"},
        "direction": "bullish (low — about to break)",
        "mechanism": "% to last 20d swing high; close to swing high = potential breakout setup or rejection.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "prior_swing_low_distance_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.02", "medium": "0.02-0.10", "high": ">0.10"},
        "direction": "bearish (low)",
        "mechanism": "% to last 20d swing low; close to swing low = potential breakdown setup or bounce.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "52w_high_distance_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.05", "medium": "0.05-0.20", "high": ">0.20"},
        "direction": "bullish (low)",
        "mechanism": "Classical screener filter; near-52w-high signals momentum strength and institutional interest.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "52w_low_distance_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.05", "medium": "0.05-0.20", "high": ">0.20"},
        "direction": "bearish (low)",
        "mechanism": "% above 52w low; near-52w-low signals weakness or potential value zone.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "fib_382_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both (bounce zone)",
        "mechanism": "38.2% retracement of last impulse; widely-used bounce zone for trend continuation. See Family 2 algorithm spec.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fib_50_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both",
        "mechanism": "50% retracement of last impulse; midpoint bounce zone. See Family 2 algorithm spec.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fib_618_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both",
        "mechanism": "61.8% (golden ratio) retracement of last impulse; classical deep-bounce zone. See Family 2 algorithm spec.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fib_786_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both",
        "mechanism": "78.6% retracement of last impulse; deep retrace; if price holds here, last-line bounce.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fib_1272_extension_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both",
        "mechanism": "1.272 extension of last impulse acts as first target zone; price reaching this level often pauses or reverses. v2.1 addition.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "fib_1618_extension_proximity_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "both",
        "mechanism": "1.618 (golden ratio) extension acts as classical target; institutional profit-taking zone often clusters here. v2.1 addition.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "pivot_distance_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "bullish (low)",
        "mechanism": "ATRs to scanner-detected pivot per existing detect_pivots logic; low = near pivot for potential breakout.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "breakout_strength_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "bullish (high)",
        "mechanism": "ATRs above nearest resistance, if bullish breakout. Separates true breakouts (high) from false ones (low).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "consolidation_zone_distance_atr",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-2", "high": ">2"},
        "direction": "bullish (low — early breakout)",
        "mechanism": "ATRs from base of recent consolidation; low = early in breakout move; high = extended.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "round_number_proximity_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.005", "medium": "0.005-0.02", "high": ">0.02"},
        "direction": "both",
        "mechanism": "% to nearest round-number price (₹100, ₹500, ₹1000 etc.); psychological levels often act as magnets/barriers.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
]

for f in FAM2_INSTITUTIONAL:
    f["family"] = "institutional_zone"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Family 3 — Momentum (25) ─────────────────────────────────────────
FAM3_MOMENTUM = [
    {
        "feature_id": "ema20_distance_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.02", "medium": "-0.02 to 0.02", "high": ">0.02"},
        "direction": "bullish (high+)",
        "mechanism": "(close - ema20) / ema20; price relative to EMA20; positive = above EMA = trend strength.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema50_distance_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "bullish (high+)",
        "mechanism": "(close - ema50) / ema50; price relative to EMA50; positive = above swing-trend MA.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema200_distance_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "bullish (high+)",
        "mechanism": "(close - ema200) / ema200; price relative to EMA200; positive = above long-term trend MA.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema_alignment",
        "value_type": "categorical", "value_range": "bull / mixed / bear",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (bull)",
        "mechanism": "Classical 'bullish stack' (price > EMA20 > EMA50 > EMA200) vs 'bearish stack'. Captures multi-timeframe trend in single category.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema20_slope_5d_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.01", "medium": "-0.01 to 0.01", "high": ">0.01"},
        "direction": "bullish (high+)",
        "mechanism": "(ema20 today / ema20 5d ago - 1); rate of EMA20 change over 5d; rising EMA = healthy uptrend.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema50_slope_5d_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.01", "medium": "-0.01 to 0.01", "high": ">0.01"},
        "direction": "bullish (high+)",
        "mechanism": "(ema50 today / ema50 5d ago - 1); rate of EMA50 change over 5d; rising = trend acceleration.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ema50_slope_20d_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.02", "medium": "-0.02 to 0.02", "high": ">0.02"},
        "direction": "bullish (high+)",
        "mechanism": "(ema50 today / ema50 20d ago - 1); rate of EMA50 change over 20d; rising = sustained trend.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "daily_3d_return_pct",
        "value_type": "float", "value_range": "-0.5 to 0.5",
        "level_thresholds": {"low": "<-0.02", "medium": "-0.02 to 0.02", "high": ">0.02"},
        "direction": "both (regime-dep)",
        "mechanism": "(close T / close T-3 - 1); 3-day rate of change; very short-term momentum captures recent strength/weakness.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "daily_5d_return_pct",
        "value_type": "float", "value_range": "-0.5 to 0.5",
        "level_thresholds": {"low": "<-0.03", "medium": "-0.03 to 0.03", "high": ">0.03"},
        "direction": "both",
        "mechanism": "(close T / close T-5 - 1); 5-day rate of change; week-scale momentum.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "daily_20d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "bullish (high+)",
        "mechanism": "(close T / close T-20 - 1); 20-day rate of change; month-scale momentum.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "daily_60d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "bullish (high+)",
        "mechanism": "(close T / close T-60 - 1); 60-day rate of change; quarterly momentum.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "weekly_2w_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "bullish (high+)",
        "mechanism": "Smooths daily noise; institutional swing-trader timeframe (2-week return).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "weekly_4w_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.08", "medium": "-0.08 to 0.08", "high": ">0.08"},
        "direction": "bullish (high+)",
        "mechanism": "Smooths daily noise; institutional swing-trader timeframe (4-week return).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "RSI_14",
        "value_type": "float", "value_range": "0-100",
        "level_thresholds": {"low": "<30", "medium": "30-70", "high": ">70"},
        "direction": "both (oversold/overbought)",
        "mechanism": "Classical 14-period RSI momentum oscillator; <30 oversold rebound candidate, >70 overbought reversal candidate.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "RSI_9",
        "value_type": "float", "value_range": "0-100",
        "level_thresholds": {"low": "<30", "medium": "30-70", "high": ">70"},
        "direction": "both",
        "mechanism": "9-period RSI; faster than RSI-14; more sensitive to recent price action.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "MACD_signal",
        "value_type": "categorical", "value_range": "bull / bear / neutral",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (bull)",
        "mechanism": "MACD vs signal-line state; bull = MACD above signal line; classical momentum convergence indicator.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "MACD_histogram_sign",
        "value_type": "categorical", "value_range": "positive / negative",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (positive)",
        "mechanism": "Sign of MACD histogram (MACD - signal); positive = bullish momentum; negative = bearish.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "MACD_histogram_slope",
        "value_type": "categorical", "value_range": "rising / falling / flat",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (rising)",
        "mechanism": "Direction of MACD histogram change (today vs 3d ago); rising = momentum strengthening.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "consecutive_up_days",
        "value_type": "int", "value_range": "0-20",
        "level_thresholds": {"low": "<2", "medium": "2-4", "high": ">4"},
        "direction": "bullish (high)",
        "mechanism": "Streak of consecutive up-days; longer streaks may signal exhaustion (mean reversion candidate) or strength (continuation).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "consecutive_down_days",
        "value_type": "int", "value_range": "0-20",
        "level_thresholds": {"low": "<2", "medium": "2-4", "high": ">4"},
        "direction": "bearish (high)",
        "mechanism": "Streak of consecutive down-days; longer = potential reversal candidate or sustained weakness.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "uptrend_age_days",
        "value_type": "int", "value_range": "0-200",
        "level_thresholds": {"low": "<20", "medium": "20-60", "high": ">60"},
        "direction": "bullish (medium — not too mature)",
        "mechanism": "Bars since last EMA50 cross-up; balances 'new trend may not have legs' (low) vs 'old trend may be exhausted' (high).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "downtrend_age_days",
        "value_type": "int", "value_range": "0-200",
        "level_thresholds": {"low": "<20", "medium": "20-60", "high": ">60"},
        "direction": "bearish (medium)",
        "mechanism": "Bars since last EMA50 cross-down; symmetric to uptrend_age_days.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "multi_tf_alignment_score",
        "value_type": "float", "value_range": "0-3",
        "level_thresholds": {"low": "<1", "medium": "1-2", "high": ">2"},
        "direction": "bullish (high)",
        "mechanism": "Composite count of aligned daily/weekly/monthly trends (0-3); higher = stronger multi-timeframe conviction.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "daily_volatility_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.015", "medium": "0.015-0.04", "high": ">0.04"},
        "direction": "regime-dependent",
        "mechanism": "20d std-dev of daily log returns; complements range_compression with vol-of-vol perspective.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "ROC_10",
        "value_type": "float", "value_range": "-0.5 to 0.5",
        "level_thresholds": {"low": "<-0.03", "medium": "-0.03 to 0.03", "high": ">0.03"},
        "direction": "bullish (high+)",
        "mechanism": "Rate of change: (close T / close T-10 - 1); simple 10-day momentum oscillator.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
]

for f in FAM3_MOMENTUM:
    f["family"] = "momentum"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Family 4 — Volume (15) ───────────────────────────────────────────
FAM4_VOLUME = [
    {
        "feature_id": "vol_ratio_5d",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.7", "medium": "0.7-1.5", "high": ">1.5"},
        "direction": "bullish (high)",
        "mechanism": "today_vol / 5d_avg; vol relative to recent baseline; high ratio = institutional participation surge.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_ratio_10d",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.7", "medium": "0.7-1.5", "high": ">1.5"},
        "direction": "bullish (high)",
        "mechanism": "today_vol / 10d_avg; vol relative to 2-week baseline.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_ratio_20d",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.7", "medium": "0.7-1.5", "high": ">1.5"},
        "direction": "bullish (high)",
        "mechanism": "today_vol / 20d_avg; vol relative to month baseline; standard institutional participation gauge.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_ratio_50d",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<0.7", "medium": "0.7-1.5", "high": ">1.5"},
        "direction": "bullish (high)",
        "mechanism": "today_vol / 50d_avg; vol relative to quarterly baseline.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_q",
        "value_type": "categorical", "value_range": "Thin / Average / High",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (High)",
        "mechanism": "Existing scanner field — 3-bucket vol classification computed in detect_signals; reuse for combination filter.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_trend_slope_20d",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.02", "medium": "-0.02 to 0.02", "high": ">0.02"},
        "direction": "bullish (high+)",
        "mechanism": "Linear regression slope of 20d volume; rising vol = accumulation; falling vol = distribution or quiet phase.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "body_to_range_ratio",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.3", "medium": "0.3-0.7", "high": ">0.7"},
        "direction": "bullish (high)",
        "mechanism": "abs(close - open) / (high - low); large body = decisive move; small body = indecision (doji-like).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "upper_wick_ratio",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.2", "medium": "0.2-0.5", "high": ">0.5"},
        "direction": "bearish (high — selling pressure)",
        "mechanism": "(high - max(open,close)) / (high - low); long upper wick = sellers stepped in at highs; rejection signal.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "lower_wick_ratio",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.2", "medium": "0.2-0.5", "high": ">0.5"},
        "direction": "bullish (high — buying support)",
        "mechanism": "(min(open,close) - low) / (high - low); long lower wick = buyers supported at lows; rejection of weakness.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "close_pos_in_range",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.3", "medium": "0.3-0.7", "high": ">0.7"},
        "direction": "bullish (high)",
        "mechanism": "INV-012 BTST primitive: (close - low) / (high - low). Close in top 30% of range with volume signature predicts overnight gap-up follow-through above universe baseline; close in bottom 30% predicts overnight reversal pressure. v2.1 addition (Q1 resolution).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_climax_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both (regime-dep)",
        "mechanism": "vol > 2.5× 20d avg; extreme volume often signals reversal (capitulation low or distribution high).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "vol_dryup_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (post-pullback dryup)",
        "mechanism": "vol < 0.5× 20d avg; volume contraction during pullback often precedes resumption of trend.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "accumulation_distribution_signed",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.3 distribution", "medium": "-0.3 to 0.3 neutral", "high": ">0.3 accumulation"},
        "direction": "bullish (high — positive = accumulation)",
        "mechanism": "Sum of (close - open) × vol over 20d window, normalized to [-1,1]. Positive = net accumulation; negative = net distribution. v2 collapse of mirrored pair (Q3 resolution).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "volume_at_pivot_ratio",
        "value_type": "float", "value_range": "0-10",
        "level_thresholds": {"low": "<1.0", "medium": "1.0-2.0", "high": ">2.0"},
        "direction": "bullish (high)",
        "mechanism": "Volume on the pivot bar / 20d avg; high pivot vol = stronger pivot, more conviction in pattern.",
        "data_source": "signal-row+OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "obv_slope_20d_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "bullish (high+)",
        "mechanism": "On-balance volume regression slope over 20d, normalized; rising OBV = accumulation; falling = distribution.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
]

for f in FAM4_VOLUME:
    f["family"] = "volume"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Family 5 — Regime / context (20) ─────────────────────────────────
FAM5_REGIME = [
    {
        "feature_id": "nifty_20d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "both (regime-dep)",
        "mechanism": "Nifty 50 20-day return; broad market context; signals fired in different macro regimes behave differently.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "nifty_60d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "both",
        "mechanism": "Nifty 50 60-day return; quarterly broad-market context.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "nifty_200d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "both",
        "mechanism": "Nifty 50 200-day return; year-scale broad-market trend.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "bank_nifty_20d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "both",
        "mechanism": "Bank Nifty 20-day return; banking-sector momentum at swing-trader timeframe.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "bank_nifty_60d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "both (per INV-002 finding)",
        "mechanism": "Per INV-002 Section 2b, 60d Bank Nifty return materially differentiates Bank-cohort UP_TRI WR. Encodes that filter directly.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "sector_index_20d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.05", "medium": "-0.05 to 0.05", "high": ">0.05"},
        "direction": "bullish (high+)",
        "mechanism": "Stock's sector index 20-day return; sector momentum at swing timeframe.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "sector_index_60d_return_pct",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "bullish (high+)",
        "mechanism": "Stock's sector index 60-day return; sector momentum at quarterly timeframe.",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "nifty_vol_percentile_20d",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.30", "medium": "0.30-0.70", "high": ">0.70"},
        "direction": "both (regime-dep)",
        "mechanism": "Nifty 20-day rolling vol percentile across 15-yr distribution; per INV-007, vol bucket is signal-specific (no universal edge surfaced).",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "nifty_vol_regime",
        "value_type": "categorical", "value_range": "Low / Medium / High",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Categorical wrapper over nifty_vol_percentile_20d using INV-007 bucket boundaries (p30, p70).",
        "data_source": "external", "computation_complexity": "cheap",
    },
    {
        "feature_id": "regime_state",
        "value_type": "categorical", "value_range": "Bear / Bull / Choppy",
        "level_thresholds": _bool_thresholds(),
        "direction": "regime-dependent",
        "mechanism": "Existing scanner classification per get_nifty_info; reuse signal-row field. Foundational context for combination engine.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "regime_score",
        "value_type": "int", "value_range": "-1 to 2",
        "level_thresholds": _bool_thresholds(),
        "direction": "regime-dependent",
        "mechanism": "Existing scanner numeric regime score per ret20-bucketed mapping; reuse signal-row field.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "sector_momentum_state",
        "value_type": "categorical", "value_range": "Lagging / Neutral / Leading",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (Leading)",
        "mechanism": "Existing scanner sector_momentum field (sec_mom); reuse signal-row.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "sector_rank_within_universe",
        "value_type": "int", "value_range": "1-13",
        "level_thresholds": {"low": "<5", "medium": "5-9", "high": ">9"},
        "direction": "bullish (low rank = top)",
        "mechanism": "Stock's sector ranking among all 13 sectors by 20d return; rank 1 = leading sector.",
        "data_source": "cross-stock", "computation_complexity": "medium",
    },
    {
        "feature_id": "stock_rs_vs_nifty_60d",
        "value_type": "float", "value_range": "-1 to 1",
        "level_thresholds": {"low": "<-0.10", "medium": "-0.10 to 0.10", "high": ">0.10"},
        "direction": "bullish (high+)",
        "mechanism": "Stock 60d return - Nifty 60d return; relative strength vs broad market.",
        "data_source": "OHLCV+external", "computation_complexity": "medium",
    },
    {
        "feature_id": "rs_q",
        "value_type": "categorical", "value_range": "Weak / Neutral / Strong",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (Strong)",
        "mechanism": "Existing scanner field — 3-bucket relative strength classification; reuse signal-row.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "market_breadth_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.30", "medium": "0.30-0.60", "high": ">0.60"},
        "direction": "bullish (high+)",
        "mechanism": "% F&O stocks above 50d EMA; cross-stock breadth indicator. High = universe-wide participation.",
        "data_source": "cross-stock", "computation_complexity": "expensive",
    },
    {
        "feature_id": "advance_decline_ratio_20d",
        "value_type": "float", "value_range": "0-3",
        "level_thresholds": {"low": "<0.5", "medium": "0.5-1.5", "high": ">1.5"},
        "direction": "bullish (high+)",
        "mechanism": "20d cumulative advance/decline ratio across F&O universe; high = sustained breadth supportive of trend.",
        "data_source": "cross-stock", "computation_complexity": "expensive",
    },
    {
        "feature_id": "day_of_month_bucket",
        "value_type": "categorical", "value_range": "wk1 / wk2 / wk3 / wk4",
        "level_thresholds": _bool_thresholds(),
        "direction": "both (regime-dep)",
        "mechanism": "Day-of-month bucket: 1-7 (wk1), 8-14 (wk2), 15-21 (wk3), 22-31 (wk4). Calendar-event proxy.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "day_of_week",
        "value_type": "categorical", "value_range": "Mon / Tue / Wed / Thu / Fri",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Day of week; calendar-event proxy.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
    {
        "feature_id": "days_to_monthly_expiry",
        "value_type": "int", "value_range": "0-30",
        "level_thresholds": {"low": "<5", "medium": "5-15", "high": ">15"},
        "direction": "both",
        "mechanism": "Days to monthly F&O expiry (last Thursday of month); calendar-event proxy. Computable from signal date + NSE expiry calendar.",
        "data_source": "signal-row", "computation_complexity": "cheap",
    },
]

for f in FAM5_REGIME:
    f["family"] = "regime"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Family 6 — Pattern (17) ──────────────────────────────────────────
FAM6_PATTERN = [
    {
        "feature_id": "triangle_quality_ascending",
        "value_type": "float", "value_range": "0-100",
        "level_thresholds": {"low": "<33", "medium": "33-67", "high": ">67"},
        "direction": "bullish (high)",
        "mechanism": "Composite quality score: (touch_count × 10) + (R²_lows × 30) + (R²_highs × 30) + (compression_factor × 30). See Family 6 algorithm spec.",
        "data_source": "OHLCV", "computation_complexity": "expensive",
    },
    {
        "feature_id": "triangle_quality_descending",
        "value_type": "float", "value_range": "0-100",
        "level_thresholds": {"low": "<33", "medium": "33-67", "high": ">67"},
        "direction": "bearish (high)",
        "mechanism": "Symmetric to ascending; expects negative slope on highs + flat slope on lows.",
        "data_source": "OHLCV", "computation_complexity": "expensive",
    },
    {
        "feature_id": "triangle_compression_pct",
        "value_type": "float", "value_range": "0-1",
        "level_thresholds": {"low": "<0.05", "medium": "0.05-0.10", "high": ">0.10"},
        "direction": "bullish (low)",
        "mechanism": "today's high-low / (highest pivot high in last 30 bars - lowest pivot low in last 30 bars). Lower = more compressed = stronger breakout candidate.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "triangle_touches_count",
        "value_type": "int", "value_range": "0-10",
        "level_thresholds": {"low": "<3", "medium": "3-5", "high": ">5"},
        "direction": "bullish (high)",
        "mechanism": "Count of pivot highs + pivot lows in last 30 bars within 1 ATR of regression-fit trendlines. Higher = more confirmation.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "triangle_age_bars",
        "value_type": "int", "value_range": "0-100",
        "level_thresholds": {"low": "<10", "medium": "10-30", "high": ">30"},
        "direction": "bullish (medium — not too old)",
        "mechanism": "Bars since triangle pattern initiated. Too new = not enough confirmation; too old = breakout may have already failed or pattern broken.",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "swing_high_count_20d",
        "value_type": "int", "value_range": "0-10",
        "level_thresholds": {"low": "<2", "medium": "2-3", "high": ">3"},
        "direction": "bullish (low — fewer recent highs = breakout potential)",
        "mechanism": "Count of pivot highs in last 20 bars via existing detect_pivots; few highs = price compressing toward breakout. v2 addition (Q2 resolution).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "swing_low_count_20d",
        "value_type": "int", "value_range": "0-10",
        "level_thresholds": {"low": "<2", "medium": "2-3", "high": ">3"},
        "direction": "bullish (high — multiple support touches)",
        "mechanism": "Count of pivot lows in last 20 bars; many = repeated support tests = strengthening floor. v2 addition (Q2 resolution).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "last_swing_high_distance_atr",
        "value_type": "float", "value_range": "0-20",
        "level_thresholds": {"low": "<1", "medium": "1-3", "high": ">3"},
        "direction": "bullish (low — near breakout)",
        "mechanism": "(most_recent_pivot_high_price - today_close) / today_atr14; how far below the most recent pivot high price currently sits (ATR-normalized); near = breakout pending. v2 addition (Q2 resolution).",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "higher_highs_intact_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (1 — sequence maintained)",
        "mechanism": "Take last 3 pivot highs from last 60 bars; return 1 if pivot[i] > pivot[i-1] > pivot[i-2]; intact uptrend structure. v2 addition (Q2 resolution).",
        "data_source": "OHLCV", "computation_complexity": "medium",
    },
    {
        "feature_id": "gap_up_pct",
        "value_type": "float", "value_range": "-0.1 to 0.1",
        "level_thresholds": {"low": "<0.005", "medium": "0.005-0.02", "high": ">0.02"},
        "direction": "bullish (high+)",
        "mechanism": "today_open / prev_close - 1; if positive, gap up. Reuse from existing GAP_BREAKOUT detector logic.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "gap_down_pct",
        "value_type": "float", "value_range": "-0.1 to 0.1",
        "level_thresholds": {"low": "<-0.02", "medium": "-0.02 to -0.005", "high": ">-0.005"},
        "direction": "bearish (high+ | abs)",
        "mechanism": "today_open / prev_close - 1; if negative, gap down. Mirrors gap_up_pct for downside.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "bullish_engulf_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (1)",
        "mechanism": "Today's bullish candle (close>open) fully engulfs prior bearish candle's body; classical reversal pattern.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "bearish_engulf_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bearish (1)",
        "mechanism": "Today's bearish candle (close<open) fully engulfs prior bullish candle's body; classical reversal pattern.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "hammer_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bullish (1)",
        "mechanism": "Small body + long lower wick (>2× body) at recent lows; classical bullish reversal candle.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "shooting_star_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "bearish (1)",
        "mechanism": "Small body + long upper wick (>2× body) at recent highs; classical bearish reversal candle.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "inside_bar_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both",
        "mechanism": "Today's high <= prev_high AND today's low >= prev_low; complement to Family 1 inside_day_flag.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
    {
        "feature_id": "outside_bar_flag",
        "value_type": "bool", "value_range": "0/1",
        "level_thresholds": _bool_thresholds(),
        "direction": "both (volatility expansion)",
        "mechanism": "Today's high > prev_high AND today's low < prev_low; range engulfs prior bar; volatility expansion event.",
        "data_source": "OHLCV", "computation_complexity": "cheap",
    },
]

for f in FAM6_PATTERN:
    f["family"] = "pattern"
    f["spec_version"] = SPEC_VERSION
    FEATURES.append(f)


# ── Generate ─────────────────────────────────────────────────────────

def main():
    expected_counts = {
        "compression": 15,
        "institutional_zone": 22,
        "momentum": 25,
        "volume": 15,
        "regime": 20,
        "pattern": 17,
    }
    expected_total = sum(expected_counts.values())  # 114

    # Verify family counts
    actual_counts = {}
    for f in FEATURES:
        actual_counts[f["family"]] = actual_counts.get(f["family"], 0) + 1
    print(f"[gen] family counts: {actual_counts}")
    if actual_counts != expected_counts:
        raise SystemExit(
            f"FAIL: family counts mismatch. expected={expected_counts}, "
            f"actual={actual_counts}")
    if len(FEATURES) != expected_total:
        raise SystemExit(
            f"FAIL: total count mismatch. expected={expected_total}, "
            f"actual={len(FEATURES)}")

    # Verify all required fields per feature
    required_fields = {
        "feature_id", "family", "value_type", "value_range",
        "level_thresholds", "direction", "mechanism",
        "data_source", "computation_complexity", "spec_version",
    }
    for f in FEATURES:
        missing = required_fields - set(f.keys())
        if missing:
            raise SystemExit(f"FAIL: feature {f.get('feature_id')} missing {missing}")

    # Verify uniqueness of feature_id
    ids = [f["feature_id"] for f in FEATURES]
    if len(ids) != len(set(ids)):
        from collections import Counter
        dups = [k for k, v in Counter(ids).items() if v > 1]
        raise SystemExit(f"FAIL: duplicate feature_ids: {dups}")

    # Verify cost distribution: 67 cheap / 36 medium / 11 expensive
    cost_counts = {}
    for f in FEATURES:
        cost_counts[f["computation_complexity"]] = cost_counts.get(f["computation_complexity"], 0) + 1
    print(f"[gen] cost counts: {cost_counts}")
    expected_costs = {"cheap": 67, "medium": 36, "expensive": 11}
    if cost_counts != expected_costs:
        print(f"WARN: cost distribution differs from spec target. "
              f"expected={expected_costs}, actual={cost_counts}")

    # Create output dir
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write each feature as its own JSON
    for f in FEATURES:
        out_path = _OUT_DIR / f"{f['feature_id']}.json"
        with open(out_path, "w") as fh:
            json.dump(f, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print(f"[gen] wrote {len(FEATURES)} JSON files to {_OUT_DIR}")
    print(f"[gen] spec_version: {SPEC_VERSION}")


if __name__ == "__main__":
    main()
