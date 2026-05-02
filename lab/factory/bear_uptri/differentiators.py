"""
Bear UP_TRI cell — B2: feature differentiator analysis.

Bear UP_TRI has 0 REJECTED in Phase 5 (100% validation rate). The standard
winners-vs-rejected differentiation isn't available, so this module does:

  • Winners (V+P, n=87) vs WATCH (n=405) differentiator scoring
    — WATCH = patterns that DID survive Phase 4 walk-forward but did NOT
    accumulate live matches, so they're effectively "didn't qualify for
    live evaluation". They function as the unobserved counterfactual.

  • Common 2-feature pairs in winners (≥30% of winners)
  • Sector concentration in winners
  • Axis distribution (calendar / volatility / breadth / etc.)

After analysis, send to Sonnet 4.5 for mechanism interpretation:
  "Bear UP_TRI has 100% Phase 5 validation. Top winner features [...].
   Why does Bear UP_TRI work so reliably? What features should be most
   trusted for filter design?"
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from extract import load_bear_uptri  # noqa: E402

OUTPUT_PATH = _HERE / "differentiators.json"
LLM_OUTPUT_PATH = _HERE / "differentiators_llm_interpretation.md"

PAIR_FREQ_THRESHOLD = 0.30
TOP_K = 20

# Same axis map as choppy_uptri (feature library is shared)
AXIS_MAP = {
    "day_of_week": "calendar", "day_of_month_bucket": "calendar",
    "days_to_monthly_expiry": "calendar",
    "nifty_vol_regime": "volatility",
    "nifty_vol_percentile_20d": "volatility",
    "daily_volatility_pct": "volatility",
    "atr_compression_pct": "volatility",
    "market_breadth_pct": "breadth",
    "advance_decline_ratio_20d": "breadth",
    "regime_score": "breadth", "regime_state": "breadth",
    "sector_momentum_state": "breadth",
    "ema_alignment": "trend", "ema20_distance_pct": "trend",
    "ema50_distance_pct": "trend", "ema200_distance_pct": "trend",
    "ema20_slope_5d_pct": "trend", "ema50_slope_5d_pct": "trend",
    "ema50_slope_20d_pct": "trend", "MACD_signal": "trend",
    "MACD_histogram_sign": "trend", "MACD_histogram_slope": "trend",
    "RSI_14": "momentum", "RSI_9": "momentum", "ROC_10": "momentum",
    "daily_5d_return_pct": "momentum",
    "daily_20d_return_pct": "momentum",
    "daily_60d_return_pct": "momentum",
    "weekly_2w_return_pct": "momentum",
    "weekly_4w_return_pct": "momentum",
    "stock_rs_vs_nifty_60d": "momentum",
    "consecutive_up_days": "momentum",
    "consecutive_down_days": "momentum",
    "52w_high_distance_pct": "position",
    "52w_low_distance_pct": "position",
    "range_position_in_window": "position",
    "higher_highs_intact_flag": "position",
    "swing_high_count_20d": "pattern",
    "last_swing_high_distance_atr": "pattern",
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
    "vol_q": "volume", "vol_ratio_5d": "volume",
    "vol_ratio_10d": "volume", "vol_ratio_20d": "volume",
    "vol_ratio_50d": "volume",
    "obv_slope_20d_pct": "volume",
    "vol_climax_flag": "volume", "vol_dryup_flag": "volume",
    "nifty_20d_return_pct": "macro",
    "nifty_60d_return_pct": "macro",
    "nifty_200d_return_pct": "macro",
    "bank_nifty_20d_return_pct": "macro",
    "bank_nifty_60d_return_pct": "macro",
    "sector_index_20d_return_pct": "macro",
    "sector_index_60d_return_pct": "macro",
    "sector_rank_within_universe": "macro",
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


def _row_features(row: pd.Series) -> list[tuple[str, str]]:
    pairs = []
    for slot in ("a", "b", "c", "d"):
        fid = row.get(f"feature_{slot}_id")
        lvl = row.get(f"feature_{slot}_level")
        if pd.notna(fid) and pd.notna(lvl):
            pairs.append((str(fid), str(lvl)))
    return pairs


def feature_presence(df: pd.DataFrame) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = Counter()
    for _, row in df.iterrows():
        for pair in _row_features(row):
            counts[pair] += 1
    return dict(counts)


def feature_pair_presence(df: pd.DataFrame) -> dict[frozenset, int]:
    counts: dict[frozenset, int] = Counter()
    for _, row in df.iterrows():
        feats = _row_features(row)
        for a, b in combinations(feats, 2):
            counts[frozenset([a, b])] += 1
    return dict(counts)


def differentiator_scores(winners: pd.DataFrame,
                              comparator: pd.DataFrame) -> list[dict]:
    nw = max(1, len(winners))
    nc = max(1, len(comparator))
    w_counts = feature_presence(winners)
    c_counts = feature_presence(comparator)
    all_pairs = set(w_counts.keys()) | set(c_counts.keys())
    rows = []
    for pair in all_pairs:
        w_n = w_counts.get(pair, 0)
        c_n = c_counts.get(pair, 0)
        rows.append({
            "feature_id": pair[0],
            "level": pair[1],
            "winners_count": w_n,
            "winners_pct": w_n / nw,
            "comparator_count": c_n,
            "comparator_pct": c_n / nc,
            "differentiator_score": w_n / nw - c_n / nc,
        })
    rows.sort(key=lambda r: -r["differentiator_score"])
    return rows


def common_winner_pairs(winners: pd.DataFrame,
                            threshold: float = PAIR_FREQ_THRESHOLD
                            ) -> list[dict]:
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
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, row in df.iterrows():
        for fid, lvl in _row_features(row):
            axis = AXIS_MAP.get(fid, "other")
            out[axis][f"{fid}={lvl}"] += 1
    return {k: dict(v) for k, v in out.items()}


def build_differentiators_analysis() -> dict:
    df = load_bear_uptri()
    val = df[df["live_tier"] == "VALIDATED"]
    pre = df[df["live_tier"] == "PRELIMINARY"]
    rej = df[df["live_tier"] == "REJECTED"]
    watch = df[df["live_tier"] == "WATCH"]
    winners = pd.concat([val, pre], ignore_index=True)

    # Primary comparator: WATCH (since 0 REJECTED)
    diff_vs_watch = differentiator_scores(winners, watch)
    pairs_w = common_winner_pairs(winners, threshold=PAIR_FREQ_THRESHOLD)

    return {
        "n_winners": len(winners),
        "n_validated": len(val),
        "n_preliminary": len(pre),
        "n_rejected": len(rej),
        "n_watch": len(watch),
        "comparator_basis": "WATCH (0 REJECTED in Phase 5)",
        "top_winner_features_vs_watch": diff_vs_watch[:TOP_K],
        "top_anti_features_vs_watch": diff_vs_watch[-TOP_K:][::-1],
        "common_winner_pairs": pairs_w,
        "winners_axis_distribution": feature_axis_distribution(winners),
        "watch_axis_distribution": feature_axis_distribution(watch),
    }


def _print_top(rows: list[dict], label: str, k: int = 10) -> None:
    print()
    print(f"── {label} ──")
    print(f"{'feature':<38}{'level':<12}{'win%':>8}{'comp%':>9}{'diff':>8}")
    print("─" * 75)
    for r in rows[:k]:
        print(f"  {r['feature_id']:<36}{r['level']:<12}"
              f"{r['winners_pct']*100:>7.1f}%{r['comparator_pct']*100:>8.1f}%"
              f"{r['differentiator_score']*100:>+7.1f}")


def llm_mechanism_interpretation(out: dict) -> str:
    """Send winner features + anti-features to Sonnet 4.5 for mechanism analysis."""
    from llm_client import LLMClient

    top_winners = out["top_winner_features_vs_watch"][:10]
    top_anti = out["top_anti_features_vs_watch"][:10]
    common_pairs = out["common_winner_pairs"][:10]

    win_lines = "\n".join(
        f"  - {r['feature_id']}={r['level']}  "
        f"(winners {r['winners_pct']*100:.0f}%, "
        f"watch {r['comparator_pct']*100:.0f}%, "
        f"diff {r['differentiator_score']*100:+.0f}pp)"
        for r in top_winners
    )
    anti_lines = "\n".join(
        f"  - {r['feature_id']}={r['level']}  "
        f"(winners {r['winners_pct']*100:.0f}%, "
        f"watch {r['comparator_pct']*100:.0f}%, "
        f"diff {r['differentiator_score']*100:+.0f}pp)"
        for r in top_anti
    )
    pair_lines = "\n".join(
        f"  - {p['feature_a']}  +  {p['feature_b']}  "
        f"({p['winners_pct']*100:.0f}% of winners)"
        for p in common_pairs
    )

    prompt = f"""You are interpreting feature differentiator analysis for
a Bear regime UP_TRI (ascending triangle breakout) trading cell. The cell
is **the strongest cohort across the entire investigation pipeline**:

• 100% Phase 5 validation rate (87 of 87 evaluable patterns)
• Live signals: 74, baseline WR = 94.6%
• Live-vs-lifetime gap: +38.9pp (live 94.6% vs lifetime 55.7%)
• Vol regime in live data: 100% High (uniform stress)
• Phase 4 tier in winners: 45 S, 15 A, 4 B (S-tier dominates — opposite of
  Choppy where S/A all REJECTED)

## Top winner features (vs WATCH baseline)

{win_lines}

## Top anti-features (vs WATCH baseline) — features OVER-represented in WATCH

{anti_lines}

## Common 2-feature pairs in winners (≥30% co-occurrence)

{pair_lines}

## Your task

1. **Mechanism**: What trading mechanism explains why Bear UP_TRI works
   so reliably? Reference established concepts (oversold mean reversion,
   bear-rally compression, capitulation reversal, sector rotation,
   institutional accumulation, regime transition). 3-5 sentences.

2. **Most trusted features for filter design**: Of the winner features,
   which 2-3 should anchor the production filter? Why those and not
   others? Be specific.

3. **Anti-feature interpretation**: What do the WATCH-over-represented
   features tell us about *what doesn't work* in Bear UP_TRI?

4. **Mechanism vs sub-regime**: Bear UP_TRI has +38.9pp live-vs-lifetime
   gap. Is the cell capturing a UNIVERSAL Bear edge (filter works in any
   Bear sub-regime) or a SPECIFIC sub-regime edge (current "hot Bear"
   only, will weaken at lifetime scale)? What feature pattern would
   discriminate?

5. **Risk to filter selection**: What features are the BIGGEST risk for
   over-fitting to current April 2026 sub-regime? (Example from Choppy:
   `nifty_vol_regime=High` was an anti-feature in lifetime but coincides
   with 100% of live data, so couldn't be used as a filter.)

Format: markdown, ## sections per question. Be terse — 3-5 short paragraphs
per section."""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=2500)
    return response


def main():
    print("─" * 80)
    print("CELL: Bear UP_TRI — B2 feature differentiator analysis")
    print("─" * 80)
    out = build_differentiators_analysis()

    print(f"\nWinners (V+P): {out['n_winners']} | "
          f"Rejected: {out['n_rejected']} | "
          f"Watch: {out['n_watch']}")
    print(f"Comparator basis: {out['comparator_basis']}")

    _print_top(out["top_winner_features_vs_watch"],
                "TOP 10 WINNER-DISTINGUISHING FEATURES (positive differentiator)",
                10)
    _print_top(out["top_anti_features_vs_watch"],
                "TOP 10 ANTI-FEATURES (over-represented in WATCH)",
                10)

    print()
    print(f"── COMMON FEATURE PAIRS IN WINNERS (≥{PAIR_FREQ_THRESHOLD*100:.0f}%) ──")
    if out["common_winner_pairs"]:
        for p in out["common_winner_pairs"][:15]:
            print(f"  {p['winners_pct']*100:>5.1f}% "
                  f"({p['winners_count']} of {out['n_winners']})  "
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

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # LLM mechanism interpretation
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for mechanism interpretation...")
    print("─" * 80)
    md = llm_mechanism_interpretation(out)
    LLM_OUTPUT_PATH.write_text(
        f"# Bear UP_TRI Differentiator Mechanism Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{md}\n"
    )
    print(f"Saved: {LLM_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
