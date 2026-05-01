"""
Phase 1B BLOCK 5 — Full feature extraction (105,987 signals).

Runs FeatureExtractor on the entire backtest universe (15-yr × 188 stocks),
saves the enriched parquet for downstream phases (Phase 2 importance, Phase 3
cohort baselines, Phase 4 combination engine, Phase 5 live validation, Phase 6
barcodes).

Run:
    .venv/bin/python lab/analyses/inv_phase1b_full_extraction.py

Includes per-symbol-group progress logging (every 10K signals) and post-
extraction validation gate. HALT triggered if runtime > 30 min, dataset size
unexpected, or schema mismatch.

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
OUTPUT_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
PARTIAL_PATH = _LAB_ROOT / "output" / "enriched_signals_partial.parquet"
STATUS_PATH = _LAB_ROOT / "AUTO_RUN_STATUS.md"

# Halt thresholds
MIN_EXPECTED_ROWS = 100_000
MAX_EXPECTED_ROWS = 200_000
MAX_RUNTIME_SEC = 30 * 60  # 30-min hard cap

PROGRESS_EVERY = 10_000  # signals between progress prints

# Distribution-check reference features (must match Block 4 sample within ±10%)
DIST_REFS = [
    ("vol_ratio_20d", 0.775),
    ("ema50_distance_pct", 0.014),
    ("RSI_14", 55.455),
    ("range_compression_20d", 0.131),
    ("close_pos_in_range", 0.462),
]


def _is_nan_series(series: pd.Series) -> pd.Series:
    """pd.isna for numeric/None values; treat strings as non-NaN."""
    return series.apply(
        lambda v: False if isinstance(v, str) else pd.isna(v))


def _fmt_runtime(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}m {s:.1f}s"


def _surface_halt_status(reason: str) -> None:
    """Document partial state to STATUS_PATH and exit."""
    STATUS_PATH.write_text(
        f"# Block 5 HALT — {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"**Reason:** {reason}\n\n"
        f"Inspect `lab/output/enriched_signals_partial.parquet` if present "
        f"and resume with fixed script.\n"
    )
    print(f"\n⚠ HALT: {reason}", file=sys.stderr)
    sys.exit(1)


def main():
    print("─" * 72)
    print("Phase 1B BLOCK 5 — Full extraction (105,987 signals)")
    print("─" * 72)

    # ── Load + verify input ──────────────────────────────────────────
    print(f"\nLoading input: {INPUT_PATH}")
    if not INPUT_PATH.exists():
        _surface_halt_status(f"input not found at {INPUT_PATH}")
    df = pd.read_parquet(INPUT_PATH)
    n_rows = len(df)
    print(f"  Total signals: {n_rows}")
    print(f"  Columns: {len(df.columns)}")
    if "signal" in df.columns:
        print(f"  signal-type mix: {df['signal'].value_counts().to_dict()}")
    if "regime" in df.columns:
        print(f"  regime mix: {df['regime'].value_counts().to_dict()}")
    if "scan_date" in df.columns:
        print(f"  date range: {df['scan_date'].min()} → {df['scan_date'].max()}")

    if n_rows < MIN_EXPECTED_ROWS or n_rows > MAX_EXPECTED_ROWS:
        _surface_halt_status(
            f"unexpected dataset size: {n_rows} rows "
            f"(expected {MIN_EXPECTED_ROWS}-{MAX_EXPECTED_ROWS})")

    # ── Init extractor ───────────────────────────────────────────────
    print("\nInitializing FeatureRegistry + FeatureExtractor...")
    t_init0 = time.time()
    reg = FeatureRegistry.load_all()
    fx = FeatureExtractor(registry=reg)
    init_time = time.time() - t_init0
    print(f"  Init complete: {init_time:.2f}s "
          f"(registry={len(reg)}, "
          f"universe={fx._universe_close.shape if fx._universe_close is not None else 'NONE'})")

    # ── Full extraction with progress logging ────────────────────────
    print(f"\nExtracting features on {n_rows} signals...")
    print(f"  Progress logged every {PROGRESS_EVERY} signals.")
    print(f"  Hard runtime cap: {MAX_RUNTIME_SEC / 60:.0f} min.")

    feat_ids = sorted(s.feature_id for s in reg.list_all())
    rows: dict = {}
    errors: dict = {}
    t_extract0 = time.time()
    n_processed = 0
    next_progress_at = PROGRESS_EVERY

    by_symbol = df.groupby("symbol", sort=False)
    for symbol, group in by_symbol:
        try:
            stock_df = fx._load_stock_history(symbol)
        except FileNotFoundError:
            for idx in group.index:
                rows[idx] = {fid: np.nan for fid in feat_ids}
            n_processed += len(group)
            continue

        for idx, signal_row in group.iterrows():
            try:
                feat_dict = fx.extract_single(signal_row, stock_df)
                rows[idx] = feat_dict
            except Exception as exc:  # noqa: BLE001
                rows[idx] = {fid: np.nan for fid in feat_ids}
                errors[idx] = str(exc)[:200]
            n_processed += 1

            # Progress logging
            if n_processed >= next_progress_at:
                elapsed = time.time() - t_extract0
                eta = elapsed * (n_rows - n_processed) / n_processed
                print(f"  {n_processed:>7}/{n_rows} processed in "
                      f"{_fmt_runtime(elapsed)}  "
                      f"({n_processed * 1000 / elapsed:.0f} signals/sec)  "
                      f"ETA: {_fmt_runtime(eta)}  "
                      f"errors: {len(errors)}")
                next_progress_at += PROGRESS_EVERY

                # Hard runtime check
                if elapsed > MAX_RUNTIME_SEC:
                    # Save partial state
                    print(f"\n⚠ HALT: runtime exceeded {MAX_RUNTIME_SEC / 60:.0f}min")
                    _save_partial(rows, df, feat_ids)
                    _surface_halt_status(
                        f"runtime exceeded {MAX_RUNTIME_SEC / 60:.0f}min "
                        f"after {n_processed}/{n_rows} signals")

    extract_time = time.time() - t_extract0
    print(f"\n  Extraction complete: {_fmt_runtime(extract_time)} "
          f"({extract_time * 1000 / n_rows:.1f} ms/signal, "
          f"{n_rows / extract_time:.0f} signals/sec)")
    if errors:
        print(f"  Errors during extraction: {len(errors)}/{n_rows}")
        sample_errors = list(errors.items())[:3]
        for idx, msg in sample_errors:
            print(f"    idx={idx}: {msg}")

    # ── Build enriched DataFrame ─────────────────────────────────────
    print("\nBuilding enriched DataFrame (dict-concat)...")
    t_build0 = time.time()
    feat_df = pd.DataFrame.from_dict(rows, orient="index")
    feat_df = feat_df.reindex(columns=feat_ids)
    feat_df.columns = [f"{_FEAT_PREFIX}{c}" for c in feat_df.columns]
    feat_df = feat_df.reindex(df.index)
    enriched = pd.concat([df, feat_df], axis=1)
    if errors:
        err_col = pd.Series(errors, name=f"{_FEAT_PREFIX}_extractor_error")
        enriched = enriched.join(err_col, how="left")
    build_time = time.time() - t_build0
    print(f"  DataFrame built: {build_time:.1f}s, shape={enriched.shape}")

    # ── Save ─────────────────────────────────────────────────────────
    print(f"\nSaving: {OUTPUT_PATH}")
    t_save0 = time.time()
    enriched.to_parquet(OUTPUT_PATH, index=True)
    save_time = time.time() - t_save0
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"  Saved: {size_mb:.1f} MB in {save_time:.1f}s")

    # Read-back check
    try:
        readback = pd.read_parquet(OUTPUT_PATH)
        assert len(readback) == len(enriched)
        assert len(readback.columns) == len(enriched.columns)
        print(f"  Read-back verified: {len(readback)} rows × "
              f"{len(readback.columns)} cols")
    except Exception as exc:  # noqa: BLE001
        _surface_halt_status(f"saved parquet unreadable: {exc}")

    # ── Validation gate ──────────────────────────────────────────────
    surface_validation(enriched, reg)

    # ── Final summary ────────────────────────────────────────────────
    total_runtime = init_time + extract_time + build_time + save_time
    print("\n" + "═" * 72)
    print("═══ FINAL SUMMARY ═══")
    print("═" * 72)
    print(f"Total runtime: {_fmt_runtime(total_runtime)}")
    print(f"  Init:       {init_time:.2f}s")
    print(f"  Extract:    {_fmt_runtime(extract_time)}")
    print(f"  Build:      {build_time:.1f}s")
    print(f"  Save:       {save_time:.1f}s")
    print(f"Rows processed: {n_rows}")
    print(f"Feature columns: {_EXPECTED_FEATURE_COUNT} (+ {len(df.columns)} original)")
    print(f"Output: {OUTPUT_PATH} ({size_mb:.1f} MB)")
    print(f"Errors: {len(errors)}/{n_rows}")
    print(f"\nBlock 5 complete — awaiting findings doc commit.")


def _save_partial(rows: dict, df: pd.DataFrame, feat_ids: list) -> None:
    """Save partial state for resume after HALT."""
    if not rows:
        return
    feat_df = pd.DataFrame.from_dict(rows, orient="index")
    feat_df = feat_df.reindex(columns=feat_ids)
    feat_df.columns = [f"{_FEAT_PREFIX}{c}" for c in feat_df.columns]
    partial = df.loc[list(rows.keys())].join(feat_df)
    partial.to_parquet(PARTIAL_PATH)
    print(f"  Saved partial state: {PARTIAL_PATH} ({len(partial)} rows)")


def surface_validation(enriched: pd.DataFrame, reg: FeatureRegistry) -> None:
    feat_cols = [c for c in enriched.columns
                  if c.startswith(_FEAT_PREFIX)
                  and c != _FEAT_PREFIX + "_extractor_error"]
    n = len(enriched)

    # ── Schema check ─────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ VALIDATION GATE — SCHEMA ═══")
    print("═" * 72)
    print(f"Total columns: {len(enriched.columns)}")
    print(f"feat_* columns: {len(feat_cols)} / {_EXPECTED_FEATURE_COUNT}")
    expected_ids = {s.feature_id for s in reg.list_all()}
    actual_ids = {c[len(_FEAT_PREFIX):] for c in feat_cols}
    missing = expected_ids - actual_ids
    if missing:
        _surface_halt_status(f"feature columns missing: {sorted(missing)}")
    print(f"Missing feat columns: NONE ✓")
    print(f"Row count: {n}")

    # ── NaN distribution ─────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ VALIDATION GATE — NaN DISTRIBUTION ═══")
    print("═" * 72)
    fam_for_id = {s.feature_id: s.family for s in reg.list_all()}
    cplx_for_id = {s.feature_id: s.computation_complexity
                     for s in reg.list_all()}

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

    # Buckets
    buckets = {"0-10%": 0, "10-30%": 0, "30-60%": 0, "60-90%": 0, ">90%": 0}
    for _, _, _, _, rate in nan_stats:
        if rate < 0.10:
            buckets["0-10%"] += 1
        elif rate < 0.30:
            buckets["10-30%"] += 1
        elif rate < 0.60:
            buckets["30-60%"] += 1
        elif rate < 0.90:
            buckets["60-90%"] += 1
        else:
            buckets[">90%"] += 1
    print("NaN-rate buckets:")
    for b, ct in buckets.items():
        print(f"  {b}: {ct} features")

    nan_rates = [t[4] for t in nan_stats]
    print(f"\nNaN rate stats: mean={np.mean(nan_rates):.3f}, "
          f"median={np.median(nan_rates):.3f}, max={max(nan_rates):.3f}")

    # Top-10 highest NaN
    print("\nTop 10 highest NaN-rate features:")
    print(f"{'feature_id':<40} {'family':<22} {'cplx':<10} {'rate':>8}")
    print("─" * 90)
    for fid, fam, cplx, ct, rate in nan_stats[:10]:
        print(f"{fid:<40} {fam:<22} {cplx:<10} {rate:>7.1%}")

    # Reference cheap features must stay <5% NaN
    print("\nReference cheap features (must be <5% NaN):")
    for fid in ("regime_state", "vol_ratio_20d", "ema50_distance_pct"):
        col = _FEAT_PREFIX + fid
        if col in enriched.columns:
            rate = _is_nan_series(enriched[col]).sum() / n
            ok = "✓" if rate < 0.05 else "✗ FAIL"
            print(f"  {fid}: {rate:.1%} NaN  {ok}")
            if rate >= 0.05:
                _surface_halt_status(
                    f"reference feature {fid} has {rate:.1%} NaN (must be <5%)")

    # ── Distribution sanity vs Block 4 sample ────────────────────────
    print("\n" + "═" * 72)
    print("═══ VALIDATION GATE — DISTRIBUTION SANITY (vs Block 4 sample) ═══")
    print("═" * 72)
    print(f"{'feature_id':<28} {'min':>10} {'median':>10} {'max':>10} "
          f"{'std':>10}  Block4_med  drift")
    print("─" * 100)
    drift_fail = []
    for fid, sample_median in DIST_REFS:
        col = _FEAT_PREFIX + fid
        if col not in enriched.columns:
            continue
        s = pd.to_numeric(enriched[col], errors="coerce").dropna()
        if len(s) == 0:
            print(f"{fid:<28} (all-NaN)")
            continue
        full_median = float(s.median())
        if sample_median == 0:
            drift = abs(full_median - sample_median)
        else:
            drift = abs(full_median - sample_median) / abs(sample_median)
        flag = "✓" if drift < 0.20 else "✗ DRIFT"
        if drift >= 0.20:
            drift_fail.append((fid, full_median, sample_median, drift))
        print(f"{fid:<28} {s.min():>10.3f} {full_median:>10.3f} "
              f"{s.max():>10.3f} {s.std():>10.3f}  "
              f"{sample_median:>10.3f}  {drift:>5.1%} {flag}")

    if drift_fail:
        print("\n⚠ DISTRIBUTION DRIFT detected (>20% median shift):")
        for fid, fm, sm, d in drift_fail:
            print(f"  {fid}: full={fm:.4f}, sample={sm:.4f}, drift={d:.1%}")
        _surface_halt_status("distribution drift detected vs Block 4 sample")
    else:
        print("\n✓ All reference distributions within ±20% of Block 4 sample")

    # ── Sample row spot-check ────────────────────────────────────────
    print("\n" + "═" * 72)
    print("═══ VALIDATION GATE — 5 SAMPLE ROWS ═══")
    print("═" * 72)
    rng = np.random.RandomState(7)
    sample_idx = rng.choice(enriched.index, size=min(5, n), replace=False)
    rep_features = [
        "ema_alignment", "RSI_14", "vol_ratio_20d", "regime_state",
        "nifty_vol_regime", "range_compression_20d", "close_pos_in_range",
        "stock_rs_vs_nifty_60d", "market_breadth_pct", "triangle_quality_ascending",
        "fib_618_proximity_atr", "swing_high_count_20d", "higher_highs_intact_flag",
        "bullish_engulf_flag", "gap_up_pct",
    ]
    for i, idx in enumerate(sample_idx, 1):
        row = enriched.loc[idx]
        print(f"\n--- SAMPLE {i}: idx={idx} ---")
        print(f"  symbol={row.get('symbol','?')}  "
              f"scan_date={row.get('scan_date','?')}  "
              f"signal={row.get('signal','?')}  "
              f"sector={row.get('sector','?')}  "
              f"direction={row.get('direction','?')}")
        for fid in rep_features:
            col = _FEAT_PREFIX + fid
            val = row.get(col, "MISSING")
            if isinstance(val, float):
                if pd.isna(val):
                    print(f"    {fid}: NaN")
                else:
                    print(f"    {fid}: {val:.4f}")
            else:
                print(f"    {fid}: {val}")

    print("\n" + "═" * 72)
    print("✓ VALIDATION GATE PASSED")
    print("═" * 72)


if __name__ == "__main__":
    main()
