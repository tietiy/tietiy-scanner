"""
Phase 1B BLOCK 4 — Sample feature extraction (1000 signals).

Stratified-samples the 105,987-signal backtest universe (proportional to
signal-type mix), runs FeatureExtractor.extract() to produce 114 feat_*
columns per signal, saves enriched parquet, and surfaces a 7-section
validation report for user review before BLOCK 5 (full 105,987 extraction).

Run:
    .venv/bin/python lab/analyses/inv_phase1b_sample_extraction.py

NO production scanner modifications. Lab-only.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import (  # noqa: E402
    FeatureExtractor, _FEAT_PREFIX, _EXPECTED_FEATURE_COUNT,
)

# ── Constants ─────────────────────────────────────────────────────────
INPUT_PATH = _LAB_ROOT / "output" / "backtest_signals.parquet"
OUTPUT_PATH = _LAB_ROOT / "output" / "enriched_signals_sample.parquet"
SAMPLE_SIZE = 1000
SEED = 42

# Cheap-feature NaN threshold for POTENTIAL_BUG flag
CHEAP_NAN_BUG_THRESHOLD = 0.10
GENERAL_NAN_ISSUE_THRESHOLD = 0.50

# Reference features that should rarely be NaN
LOW_NAN_REFERENCE_FEATURES = (
    "regime_state", "vol_ratio_20d", "ema50_distance_pct",
)

# Distribution-check reference features
DISTRIBUTION_REFERENCES = [
    ("vol_ratio_20d", "0.1 to 5.0, median ~1.0"),
    ("ema50_distance_pct", "-0.5 to 0.5, median near 0"),
    ("RSI_14", "0-100, median ~50"),
    ("range_compression_20d", "0-1, median ~0.05-0.10"),
    ("close_pos_in_range", "0-1, median ~0.5"),
]

# Representative features per family for sample row dump
REP_FEATURES_BY_FAMILY = {
    "compression": [
        "range_compression_20d", "bollinger_squeeze_20d",
        "coiled_spring_score", "consolidation_quality", "inside_day_streak",
    ],
    "institutional_zone": [
        "resistance_zone_distance_atr", "support_zone_distance_atr",
        "fvg_unfilled_above_count", "ob_bullish_proximity",
        "fib_618_proximity_atr",
    ],
    "momentum": [
        "ema_alignment", "RSI_14", "MACD_signal",
        "daily_5d_return_pct", "consecutive_up_days",
    ],
    "volume": [
        "vol_ratio_20d", "vol_q", "close_pos_in_range",
        "vol_climax_flag", "obv_slope_20d_pct",
    ],
    "regime": [
        "regime_state", "nifty_vol_regime", "stock_rs_vs_nifty_60d",
        "market_breadth_pct", "sector_rank_within_universe",
    ],
    "pattern": [
        "triangle_quality_ascending", "swing_high_count_20d",
        "higher_highs_intact_flag", "bullish_engulf_flag", "gap_up_pct",
    ],
}


def _is_nan_series(series: pd.Series) -> pd.Series:
    """pd.isna for numeric/None values; treat strings as non-NaN."""
    return series.apply(
        lambda v: False if isinstance(v, str) else pd.isna(v))


def _stratified_sample(df: pd.DataFrame, n_target: int,
                         seed: int) -> pd.DataFrame:
    """Stratified sample by `signal` column (proportional)."""
    if "signal" not in df.columns or df["signal"].nunique() <= 1:
        return df.sample(n=min(n_target, len(df)), random_state=seed)

    type_counts = df["signal"].value_counts()
    fractions = type_counts / type_counts.sum()
    target_per_type = (fractions * n_target).round().astype(int).to_dict()
    # Adjust to exactly n_target if rounding drift
    diff = n_target - sum(target_per_type.values())
    if diff != 0:
        # Adjust via the largest type
        largest_type = max(target_per_type, key=target_per_type.get)
        target_per_type[largest_type] += diff

    samples = []
    for sig_type, n in target_per_type.items():
        stype_df = df[df["signal"] == sig_type]
        n = min(n, len(stype_df))
        samples.append(stype_df.sample(n=n, random_state=seed))
    return pd.concat(samples).sort_index()


def main():
    print("─" * 72)
    print("Phase 1B BLOCK 4 — Sample extraction (1000 signals)")
    print("─" * 72)

    # ── Load input ────────────────────────────────────────────────────
    print(f"\nLoading input: {INPUT_PATH}")
    if not INPUT_PATH.exists():
        sys.exit(f"FATAL: input not found at {INPUT_PATH}")
    df = pd.read_parquet(INPUT_PATH)
    print(f"  Total signals: {len(df)}")
    if "signal" in df.columns:
        print(f"  signal-type mix: {df['signal'].value_counts().to_dict()}")

    # ── Stratified sample ────────────────────────────────────────────
    sample_df = _stratified_sample(df, SAMPLE_SIZE, SEED)
    print(f"\nStratified sample (random_state={SEED}): {len(sample_df)} signals")
    if "signal" in sample_df.columns:
        print(f"  sample mix: {sample_df['signal'].value_counts().to_dict()}")

    # ── Load registry + extractor ─────────────────────────────────────
    print(f"\nLoading FeatureRegistry + FeatureExtractor (universe pre-load)...")
    t0 = time.time()
    reg = FeatureRegistry.load_all()
    fx = FeatureExtractor(registry=reg)
    init_time = time.time() - t0
    print(f"  Init complete: {init_time:.2f}s "
            f"(registry={len(reg)}, universe={fx._universe_close.shape if fx._universe_close is not None else 'NONE'})")

    # ── Extract ───────────────────────────────────────────────────────
    print(f"\nExtracting features on {len(sample_df)} signals...")
    t1 = time.time()
    enriched = fx.extract(sample_df)
    extract_time = time.time() - t1
    print(f"  Extraction complete: {extract_time:.1f}s "
          f"({extract_time * 1000 / len(sample_df):.1f} ms/signal)")

    # ── Save ──────────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_parquet(OUTPUT_PATH, index=True)
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_mb:.1f} MB)")

    # ── Validation ────────────────────────────────────────────────────
    surface_validation(enriched, reg)


def surface_validation(enriched: pd.DataFrame, reg: FeatureRegistry) -> None:
    feat_cols = [c for c in enriched.columns
                  if c.startswith(_FEAT_PREFIX)
                  and c != _FEAT_PREFIX + "_extractor_error"]
    sig_cols = [c for c in enriched.columns
                  if not c.startswith(_FEAT_PREFIX)]
    n = len(enriched)

    fam_for_id = {s.feature_id: s.family for s in reg.list_all()}
    cplx_for_id = {s.feature_id: s.computation_complexity for s in reg.list_all()}

    # ── SECTION 1 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 1: SCHEMA CHECK ═══")
    print("═" * 72)
    print(f"Total columns: {len(enriched.columns)}")
    print(f"feat_* columns: {len(feat_cols)} / {_EXPECTED_FEATURE_COUNT} expected")
    expected_ids = {s.feature_id for s in reg.list_all()}
    actual_ids = {c[len(_FEAT_PREFIX):] for c in feat_cols}
    missing = expected_ids - actual_ids
    print(f"Missing feat columns: {sorted(missing) if missing else 'NONE'}")
    print(f"Original signal columns preserved: {len(sig_cols)} cols")
    print(f"  → {sig_cols}")
    print(f"Sample size processed: {n}")
    err_col = _FEAT_PREFIX + "_extractor_error"
    if err_col in enriched.columns:
        n_errors = int(enriched[err_col].notna().sum())
        print(f"Per-signal extraction errors: {n_errors}/{n}")
        if n_errors > 0:
            print(f"  Example errors: {enriched[err_col].dropna().head(3).tolist()}")

    # NaN stats per feature
    nan_stats = []
    for c in feat_cols:
        fid = c[len(_FEAT_PREFIX):]
        nan_count = int(_is_nan_series(enriched[c]).sum())
        nan_rate = nan_count / n
        nan_stats.append((
            fid, fam_for_id.get(fid, "?"),
            cplx_for_id.get(fid, "?"), nan_count, nan_rate,
        ))
    nan_stats.sort(key=lambda t: -t[4])

    # ── SECTION 2 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 2: NaN RATE PER FEATURE (top 20 highest) ═══")
    print("═" * 72)
    print(f"{'feature_id':<40} {'family':<22} {'cplx':<10} "
          f"{'count':>6} {'rate':>8}  flag")
    print("─" * 110)
    for fid, fam, cplx, ct, rate in nan_stats[:20]:
        flag = ""
        if rate > GENERAL_NAN_ISSUE_THRESHOLD:
            flag = "POTENTIAL_ISSUE"
        if cplx == "cheap" and rate > CHEAP_NAN_BUG_THRESHOLD:
            flag = "POTENTIAL_BUG"
        print(f"{fid:<40} {fam:<22} {cplx:<10} {ct:>6} "
              f"{rate:>7.1%}  {flag}")

    # ── SECTION 3 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 3: NaN RATE PER FEATURE (bottom 5 — least NaN) ═══")
    print("═" * 72)
    print(f"{'feature_id':<40} {'family':<22} {'cplx':<10} "
          f"{'count':>6} {'rate':>8}")
    print("─" * 90)
    for fid, fam, cplx, ct, rate in nan_stats[-5:]:
        print(f"{fid:<40} {fam:<22} {cplx:<10} {ct:>6} {rate:>7.1%}")

    print("\nReference features (should have <5% NaN):")
    for fid in LOW_NAN_REFERENCE_FEATURES:
        col = _FEAT_PREFIX + fid
        if col in enriched.columns:
            nan_rate = _is_nan_series(enriched[col]).sum() / n
            ok = "✓" if nan_rate < 0.05 else "✗ FLAG"
            print(f"  {fid}: {nan_rate:.1%} NaN  {ok}")

    # ── SECTION 4 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 4: DISTRIBUTION SANITY (cheap features) ═══")
    print("═" * 72)
    print(f"{'feature_id':<28} {'min':>10} {'median':>10} {'max':>10} "
          f"{'std':>10}  expected")
    print("─" * 110)
    for fid, expected in DISTRIBUTION_REFERENCES:
        col = _FEAT_PREFIX + fid
        if col in enriched.columns:
            s = pd.to_numeric(enriched[col], errors="coerce").dropna()
            if len(s):
                print(f"{fid:<28} {s.min():>10.3f} {s.median():>10.3f} "
                      f"{s.max():>10.3f} {s.std():>10.3f}  {expected}")
            else:
                print(f"{fid:<28} (all-NaN)")

    # ── SECTION 5 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 5: 5 SAMPLE ROWS (representative features by family) ═══")
    print("═" * 72)
    rng = np.random.RandomState(7)
    sample_idx = rng.choice(enriched.index, size=min(5, n), replace=False)
    for i, idx in enumerate(sample_idx, 1):
        row = enriched.loc[idx]
        print(f"\n--- SAMPLE {i}: idx={idx} ---")
        print(f"  symbol={row.get('symbol','?')}  "
              f"scan_date={row.get('scan_date','?')}  "
              f"signal={row.get('signal','?')}  "
              f"sector={row.get('sector','?')}  "
              f"direction={row.get('direction','?')}")
        for fam, fids in REP_FEATURES_BY_FAMILY.items():
            print(f"  [{fam}]")
            for fid in fids:
                col = _FEAT_PREFIX + fid
                val = row.get(col, "MISSING")
                if isinstance(val, float):
                    if pd.isna(val):
                        print(f"    {fid}: NaN")
                    else:
                        print(f"    {fid}: {val:.4f}")
                else:
                    print(f"    {fid}: {val}")

    # ── SECTION 6 ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 6: ALGORITHM-CRITICAL FEATURES ═══")
    print("═" * 72)

    def num_col(fid: str):
        c = _FEAT_PREFIX + fid
        if c in enriched.columns:
            return pd.to_numeric(enriched[c], errors="coerce")
        return pd.Series(dtype=float)

    tri_asc = num_col("triangle_quality_ascending")
    tri_desc = num_col("triangle_quality_descending")
    print("triangle_quality_ascending:")
    print(f"  >0:  {(tri_asc > 0).sum()}/{n} ({(tri_asc > 0).mean():.1%})")
    print(f"  >50: {(tri_asc > 50).sum()}/{n} ({(tri_asc > 50).mean():.1%})")
    print(f"  >70: {(tri_asc > 70).sum()}/{n} ({(tri_asc > 70).mean():.1%})")
    nz = tri_asc[tri_asc > 0]
    print(f"  median (non-zero): "
          f"{nz.median():.1f}" if len(nz) else "  (no non-zero values)")
    print("triangle_quality_descending:")
    print(f"  >0:  {(tri_desc > 0).sum()}/{n} ({(tri_desc > 0).mean():.1%})")
    print(f"  >50: {(tri_desc > 50).sum()}/{n}")
    print(f"  >70: {(tri_desc > 70).sum()}/{n}")
    nzd = tri_desc[tri_desc > 0]
    print(f"  median (non-zero): "
          f"{nzd.median():.1f}" if len(nzd) else "  (no non-zero values)")

    fib = num_col("fib_618_proximity_atr").dropna()
    if len(fib):
        print(f"\nfib_618_proximity_atr: count_non_nan={len(fib)}/{n}, "
              f"median={fib.median():.2f}, "
              f"IQR=[{fib.quantile(0.25):.2f}, {fib.quantile(0.75):.2f}]")
    else:
        print("\nfib_618_proximity_atr: ALL NaN")

    sw = num_col("swing_high_count_20d")
    print("\nswing_high_count_20d distribution:")
    if not sw.isna().all():
        sw_dist = sw.dropna().astype(int).value_counts().sort_index().to_dict()
        print(f"  {sw_dist}")
    else:
        print("  ALL NaN")

    hh_col = _FEAT_PREFIX + "higher_highs_intact_flag"
    if hh_col in enriched.columns:
        hh = enriched[hh_col]
        hh_count = int((hh == True).sum())
        print(f"\nhigher_highs_intact_flag: {hh_count}/{n} "
              f"({hh_count / n:.1%}) flagged True")

    # Bug checks
    print()
    if (tri_asc.fillna(0) == 0).all() and (tri_desc.fillna(0) == 0).all():
        print("⚠ ALGORITHM BUG: triangle_quality_* all zero — investigate")
    elif ((tri_asc > 0).sum() == 0 and (tri_desc > 0).sum() == 0):
        print("⚠ NOTE: 0 signals show triangle structure "
              "(rare in real data; not necessarily a bug)")

    fib_cols = [c for c in feat_cols if "fib_" in c]
    if fib_cols and all(num_col(c[len(_FEAT_PREFIX):]).isna().all()
                          for c in fib_cols):
        print("⚠ ALGORITHM BUG: all Fib features = NaN")

    # ── SECTION 7: User review gate ───────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ SECTION 7: USER REVIEW GATE ═══")
    print("═" * 72)
    print()
    print("USER REVIEW REQUIRED before Block 5 full extraction.")
    print("Inspect sections above. Look for:")
    print("- Unexpected NaN concentrations")
    print("- Distribution anomalies (constant values, impossible ranges)")
    print("- Triangle/Fib features all-zeros or all-NaN")
    print("- Sample row values that don't match domain intuition")
    print()
    print("If sample looks clean → reply 'BLOCK 4 APPROVED, proceed to Block 5'")
    print("If sample has issues → reply with specific concerns; "
          "iterate before Block 5")
    print()


if __name__ == "__main__":
    main()
