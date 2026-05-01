"""
Choppy UP_TRI cell — C2: feature differentiator analysis.

For (VALIDATED + PRELIMINARY) vs REJECTED groups, identify which (feature_id,
level) tuples appear disproportionately in winners vs losers.

differentiator_score = presence_in_winners_pct - presence_in_rejected_pct
  • positive: feature favors winners
  • negative: feature favors rejected (anti-feature for Choppy UP_TRI)

Also surfaces:
  • common winner pairs (2-feature sets in ≥30% of winners)
  • Top-3 features per cohort axis (calendar / volatility / breadth / structure)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from extract import load_choppy_uptri  # noqa: E402

OUTPUT_PATH = _HERE / "differentiators.json"

# Pair frequency threshold (≥30% of winners)
PAIR_FREQ_THRESHOLD = 0.30
TOP_K = 20


def _row_features(row: pd.Series) -> list[tuple[str, str]]:
    """Extract list of (feature_id, level) tuples from a combinations row."""
    pairs = []
    for slot in ("a", "b", "c", "d"):
        fid = row.get(f"feature_{slot}_id")
        lvl = row.get(f"feature_{slot}_level")
        if pd.notna(fid) and pd.notna(lvl):
            pairs.append((str(fid), str(lvl)))
    return pairs


def feature_presence(df: pd.DataFrame) -> dict[tuple[str, str], int]:
    """Count how many combinations contain each (feature_id, level) pair."""
    counts: dict[tuple[str, str], int] = Counter()
    for _, row in df.iterrows():
        for pair in _row_features(row):
            counts[pair] += 1
    return dict(counts)


def feature_pair_presence(df: pd.DataFrame) -> dict[frozenset, int]:
    """Count co-occurrence of 2-feature pairs across combinations."""
    counts: dict[frozenset, int] = Counter()
    for _, row in df.iterrows():
        feats = _row_features(row)
        for a, b in combinations(feats, 2):
            counts[frozenset([a, b])] += 1
    return dict(counts)


def differentiator_scores(winners: pd.DataFrame,
                              rejected: pd.DataFrame) -> list[dict]:
    """For every (feature, level) pair, compute differentiator_score."""
    nw = max(1, len(winners))
    nr = max(1, len(rejected))
    w_counts = feature_presence(winners)
    r_counts = feature_presence(rejected)
    all_pairs = set(w_counts.keys()) | set(r_counts.keys())
    rows = []
    for pair in all_pairs:
        w_n = w_counts.get(pair, 0)
        r_n = r_counts.get(pair, 0)
        rows.append({
            "feature_id": pair[0],
            "level": pair[1],
            "winners_count": w_n,
            "winners_pct": w_n / nw,
            "rejected_count": r_n,
            "rejected_pct": r_n / nr,
            "differentiator_score": w_n / nw - r_n / nr,
        })
    rows.sort(key=lambda r: -r["differentiator_score"])
    return rows


def common_winner_pairs(winners: pd.DataFrame,
                            threshold: float = PAIR_FREQ_THRESHOLD
                            ) -> list[dict]:
    """Pairs present in at least `threshold` of winners."""
    nw = max(1, len(winners))
    pair_counts = feature_pair_presence(winners)
    out = []
    for pair, n in pair_counts.items():
        if n / nw >= threshold:
            f1, f2 = sorted(pair)
            out.append({
                "feature_a": f"{f1[0]}={f1[1]}",
                "feature_b": f"{f2[0]}={f2[1]}",
                "winners_count": n,
                "winners_pct": n / nw,
            })
    out.sort(key=lambda x: -x["winners_count"])
    return out


def feature_axis_distribution(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Group features by family axis (calendar / volatility / breadth / etc).

    Returns nested dict: {axis: {feature_id=level: count}}.
    """
    AXIS_MAP = {
        # Calendar
        "day_of_week": "calendar", "day_of_month_bucket": "calendar",
        "days_to_monthly_expiry": "calendar",
        # Volatility
        "nifty_vol_regime": "volatility",
        "nifty_vol_percentile_20d": "volatility",
        "daily_volatility_pct": "volatility",
        "atr_compression_pct": "volatility",
        # Breadth / market
        "market_breadth_pct": "breadth", "advance_decline_ratio_20d": "breadth",
        "regime_score": "breadth", "regime_state": "breadth",
        "sector_momentum_state": "breadth",
        # Trend / structure
        "ema_alignment": "trend", "ema20_distance_pct": "trend",
        "ema50_distance_pct": "trend", "ema200_distance_pct": "trend",
        "ema20_slope_5d_pct": "trend", "ema50_slope_5d_pct": "trend",
        "ema50_slope_20d_pct": "trend", "MACD_signal": "trend",
        "MACD_histogram_sign": "trend", "MACD_histogram_slope": "trend",
        # Momentum / RS
        "RSI_14": "momentum", "RSI_9": "momentum", "ROC_10": "momentum",
        "daily_5d_return_pct": "momentum",
        "daily_20d_return_pct": "momentum",
        "daily_60d_return_pct": "momentum",
        "weekly_2w_return_pct": "momentum",
        "weekly_4w_return_pct": "momentum",
        "stock_rs_vs_nifty_60d": "momentum",
        "consecutive_up_days": "momentum",
        "consecutive_down_days": "momentum",
        # Pattern / position
        "52w_high_distance_pct": "position",
        "52w_low_distance_pct": "position",
        "range_position_in_window": "position",
        "higher_highs_intact_flag": "position",
        "swing_high_count_20d": "pattern",
        "last_swing_high_distance_atr": "pattern",
        # Compression
        "range_compression_5d": "compression",
        "range_compression_10d": "compression",
        "range_compression_20d": "compression",
        "range_compression_60d": "compression",
        "compression_duration": "compression",
        "consolidation_quality": "compression",
        "coiled_spring_score": "compression",
        "bollinger_band_width_pct": "compression",
        "bollinger_squeeze_20d": "compression",
        "NR4_flag": "compression", "NR7_flag": "compression",
        "inside_day_flag": "compression",
        "inside_day_streak": "compression",
        "inside_bar_flag": "pattern", "outside_bar_flag": "pattern",
        # Volume
        "vol_q": "volume", "vol_ratio_5d": "volume",
        "vol_ratio_10d": "volume", "vol_ratio_20d": "volume",
        "vol_ratio_50d": "volume",
        "obv_slope_20d_pct": "volume",
        "vol_climax_flag": "volume", "vol_dryup_flag": "volume",
        # Nifty / sector context
        "nifty_20d_return_pct": "macro",
        "nifty_60d_return_pct": "macro",
        "nifty_200d_return_pct": "macro",
        "bank_nifty_20d_return_pct": "macro",
        "bank_nifty_60d_return_pct": "macro",
        "sector_index_20d_return_pct": "macro",
        "sector_index_60d_return_pct": "macro",
        "sector_rank_within_universe": "macro",
        # Institutional zones
        "fvg_above_proximity": "zones",
        "fvg_below_proximity": "zones",
        "fvg_unfilled_above_count": "zones",
        "fvg_unfilled_below_count": "zones",
        "ob_bullish_proximity": "zones",
        "ob_bearish_proximity": "zones",
        "pivot_distance_atr": "zones",
        "support_zone_distance_atr": "zones",
        "resistance_zone_distance_atr": "zones",
        "consolidation_zone_distance_atr": "zones",
        "breakout_strength_atr": "zones",
        "round_number_proximity_pct": "zones",
        "prior_swing_high_distance_pct": "zones",
        "prior_swing_low_distance_pct": "zones",
        "fib_382_proximity_atr": "zones",
        "fib_50_proximity_atr": "zones",
        "fib_618_proximity_atr": "zones",
        "fib_786_proximity_atr": "zones",
        "fib_1272_extension_proximity_atr": "zones",
        "fib_1618_extension_proximity_atr": "zones",
        "rs_q": "momentum",
        "multi_tf_alignment_score": "trend",
        "uptrend_age_days": "trend", "downtrend_age_days": "trend",
        "MACD_signal": "trend",
        "body_to_range_ratio": "candle",
        "upper_wick_ratio": "candle", "lower_wick_ratio": "candle",
        "close_pos_in_range": "candle",
        "accumulation_distribution_signed": "volume",
        "vol_trend_slope_20d": "volume",
        "volume_at_pivot_ratio": "volume",
        "stock_regime": "macro", "bear_bonus": "macro",
        "triangle_quality_ascending": "pattern",
        "triangle_quality_descending": "pattern",
        "triangle_compression_pct": "compression",
        "triangle_touches_count": "pattern",
        "triangle_age_bars": "pattern",
        "swing_low_count_20d": "pattern",
        "bullish_engulf_flag": "candle",
        "bearish_engulf_flag": "candle",
        "hammer_flag": "candle",
        "shooting_star_flag": "candle",
        "gap_up_pct": "candle",
        "gap_down_pct": "candle",
    }

    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, row in df.iterrows():
        for fid, lvl in _row_features(row):
            axis = AXIS_MAP.get(fid, "other")
            out[axis][f"{fid}={lvl}"] += 1
    return {k: dict(v) for k, v in out.items()}


def build_differentiators_analysis() -> dict:
    df = load_choppy_uptri()
    val = df[df["live_tier"] == "VALIDATED"]
    pre = df[df["live_tier"] == "PRELIMINARY"]
    rej = df[df["live_tier"] == "REJECTED"]
    winners = pd.concat([val, pre], ignore_index=True)

    diff = differentiator_scores(winners, rej)
    pairs_w = common_winner_pairs(winners, threshold=PAIR_FREQ_THRESHOLD)
    pairs_r = common_winner_pairs(rej, threshold=PAIR_FREQ_THRESHOLD)

    return {
        "n_winners": len(winners),
        "n_rejected": len(rej),
        "top_winner_features": diff[:TOP_K],
        "top_rejected_features": diff[-TOP_K:][::-1],
        "common_winner_pairs": pairs_w,
        "common_rejected_pairs": pairs_r,
        "winners_axis_distribution": feature_axis_distribution(winners),
        "rejected_axis_distribution": feature_axis_distribution(rej),
    }


def _print_top(rows: list[dict], label: str, k: int = 10) -> None:
    print()
    print(f"── {label} ──")
    print(f"{'feature':<40}{'level':<12}{'winners%':>10}{'rejected%':>11}{'diff':>8}")
    print("─" * 81)
    for r in rows[:k]:
        print(f"  {r['feature_id']:<38}{r['level']:<12}"
              f"{r['winners_pct']*100:>9.1f}%{r['rejected_pct']*100:>10.1f}%"
              f"{r['differentiator_score']*100:>+7.1f}")


def main():
    print("─" * 80)
    print("CELL 1: Choppy UP_TRI — C2 feature differentiator analysis")
    print("─" * 80)
    out = build_differentiators_analysis()
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"\nWinners (V+P): {out['n_winners']} | Rejected: {out['n_rejected']}")

    _print_top(out["top_winner_features"],
                "TOP 10 WINNER-DISTINGUISHING FEATURES (positive differentiator)",
                10)
    _print_top(out["top_rejected_features"],
                "TOP 10 REJECTED-DISTINGUISHING FEATURES (anti-features for Choppy UP_TRI)",
                10)

    # Common pairs in winners
    print()
    print(f"── COMMON FEATURE PAIRS IN WINNERS (≥{PAIR_FREQ_THRESHOLD*100:.0f}%) ──")
    if out["common_winner_pairs"]:
        for p in out["common_winner_pairs"][:15]:
            print(f"  {p['winners_pct']*100:>5.1f}% ({p['winners_count']} of {out['n_winners']})  "
                  f"{p['feature_a']}  +  {p['feature_b']}")
    else:
        print("  (none above threshold)")

    print()
    print(f"── COMMON FEATURE PAIRS IN REJECTED (≥{PAIR_FREQ_THRESHOLD*100:.0f}%) ──")
    if out["common_rejected_pairs"]:
        for p in out["common_rejected_pairs"][:10]:
            print(f"  {p['winners_pct']*100:>5.1f}%  "
                  f"{p['feature_a']}  +  {p['feature_b']}")
    else:
        print("  (none above threshold)")

    print()
    print("── AXIS DISTRIBUTION (winners) ──")
    for axis, feats in sorted(out["winners_axis_distribution"].items(),
                                  key=lambda x: -sum(x[1].values())):
        total = sum(feats.values())
        print(f"  {axis}: {total} feature appearances")
        for f, n in sorted(feats.items(), key=lambda x: -x[1])[:3]:
            print(f"    {f}: {n}")


if __name__ == "__main__":
    main()
