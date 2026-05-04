"""Phase 3 Step 3.3.5 — within-symbol outcome autocorrelation diagnostic.

Investigative (not part of formal audit suite). Disambiguates Trial -1 AMBIGUOUS
from date_shift_audit:
  (A) genuine within-symbol momentum clustering  -> benign
  (B) look-ahead feature leakage                 -> catastrophic
  (C) harness boundary artifact                  -> annoying

Method: per-symbol lag-1 autocorrelation of `won` for resolved signals,
computed for rule_019 matches, a cell-specific baseline (UP_TRI / Bear /
non-hot, sub_regime explicitly assigned), and a broad baseline (everything
NOT matching rule_019). If rule_019 autocorr substantially exceeds the cell
baseline, hypothesis (A) is supported.

Output: lab/factory/oos_validation/output/autocorr_diagnostic.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))  # mirrors Stage 1 / Step 3.3 pattern

from walkforward import load_data, matches_rule, RULES_PATH  # noqa: E402

# ============================================================
# Constants
# ============================================================
RULE_ID = "rule_019_bear_uptri_hot_refinement"
GROUP_COL = "symbol"
SORT_COL = "scan_date_dt"
MIN_SIGNALS_PER_SYMBOL = 5  # threshold for inclusion in per-symbol stats

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "autocorr_diagnostic.json"


# ============================================================
# Loaders
# ============================================================
def load_rule(rule_id: str) -> dict:
    rules = json.loads(RULES_PATH.read_text())["rules"]
    for r in rules:
        if r["id"] == rule_id:
            return r
    raise ValueError(f"{rule_id} not found in {RULES_PATH}")


# ============================================================
# Autocorrelation core
# ============================================================
def per_symbol_lag1_autocorr(df_resolved: pd.DataFrame, label: str) -> dict:
    """Compute per-symbol lag-1 autocorrelation stats and pooled autocorr.

    df_resolved must have columns: symbol, scan_date_dt, won (won not NaN).

    Per-symbol stats: only symbols with >= MIN_SIGNALS_PER_SYMBOL rows are
    eligible. Symbols with zero variance in won (all 1s or all 0s) yield
    NaN autocorr — counted separately and excluded from mean/median/std.

    Pooled autocorr: uses ALL valid (won[i], won[i+1]) pairs across all
    symbols (no min-count threshold), single Pearson on the paired columns.
    """
    df = df_resolved.sort_values([GROUP_COL, SORT_COL]).reset_index(drop=True)

    per_sym_counts = df.groupby(GROUP_COL).size()
    sym_5plus = per_sym_counts[per_sym_counts >= MIN_SIGNALS_PER_SYMBOL].index

    per_symbol_autocorrs: list[float] = []
    n_zero_variance = 0
    for sym in sym_5plus:
        s = df.loc[df[GROUP_COL] == sym, "won"].astype(float).reset_index(drop=True)
        if s.nunique(dropna=True) < 2:
            n_zero_variance += 1
            continue
        ac = s.autocorr(lag=1)
        if ac is not None and not (isinstance(ac, float) and np.isnan(ac)):
            per_symbol_autocorrs.append(float(ac))

    # Pooled: build (won, won_next) pairs via groupby-shift, drop NaN edges
    df["_won_next"] = df.groupby(GROUP_COL)["won"].shift(-1)
    pairs = df.dropna(subset=["won", "_won_next"])[["won", "_won_next"]].astype(float)
    if len(pairs) >= 2 and pairs["won"].nunique() >= 2 and pairs["_won_next"].nunique() >= 2:
        pooled = float(pairs["won"].corr(pairs["_won_next"]))
    else:
        pooled = None

    pa_arr = np.array(per_symbol_autocorrs, dtype=float)
    out = {
        "label": label,
        "n_total_resolved_rows": int(len(df)),
        "n_symbols_total": int(len(per_sym_counts)),
        "n_symbols_with_5plus": int(len(sym_5plus)),
        "n_symbols_5plus_with_variance": int(len(per_symbol_autocorrs)),
        "n_symbols_5plus_zero_variance": int(n_zero_variance),
        "n_lag1_pairs_pooled": int(len(pairs)),
        "per_symbol_autocorr_mean": float(np.mean(pa_arr)) if len(pa_arr) > 0 else None,
        "per_symbol_autocorr_median": float(np.median(pa_arr)) if len(pa_arr) > 0 else None,
        "per_symbol_autocorr_std": float(np.std(pa_arr, ddof=1)) if len(pa_arr) > 1 else None,
        "per_symbol_autocorr_p25": float(np.percentile(pa_arr, 25)) if len(pa_arr) > 0 else None,
        "per_symbol_autocorr_p75": float(np.percentile(pa_arr, 75)) if len(pa_arr) > 0 else None,
        "pooled_autocorr": pooled,
    }
    return out


def _fmt(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.6f}"


def _print_block(stats: dict) -> None:
    print(f"  n_total_resolved_rows    = {stats['n_total_resolved_rows']:,}")
    print(f"  n_symbols_total          = {stats['n_symbols_total']:,}")
    print(f"  n_symbols_with_5plus     = {stats['n_symbols_with_5plus']:,}")
    print(f"  n_symbols_5plus_var      = {stats['n_symbols_5plus_with_variance']:,}")
    print(f"  n_symbols_5plus_zero_var = {stats['n_symbols_5plus_zero_variance']:,}")
    print(f"  n_lag1_pairs_pooled      = {stats['n_lag1_pairs_pooled']:,}")
    print(f"  per_symbol_autocorr_mean   = {_fmt(stats['per_symbol_autocorr_mean'])}")
    print(f"  per_symbol_autocorr_median = {_fmt(stats['per_symbol_autocorr_median'])}")
    print(f"  per_symbol_autocorr_std    = {_fmt(stats['per_symbol_autocorr_std'])}")
    print(f"  per_symbol_autocorr_p25    = {_fmt(stats['per_symbol_autocorr_p25'])}")
    print(f"  per_symbol_autocorr_p75    = {_fmt(stats['per_symbol_autocorr_p75'])}")
    print(f"  pooled_autocorr            = {_fmt(stats['pooled_autocorr'])}")
    if "n_excluded_nan_subregime" in stats:
        print(f"  n_excluded_nan_subregime   = {stats['n_excluded_nan_subregime']:,}")


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print("autocorr diagnostic — rule_019 vs cell + broad baselines")
    print("=" * 60)
    t_total = time.time()

    print("\nLoading data + rule...")
    df_full = load_data()
    rule_019 = load_rule(RULE_ID)
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  rule_019: {rule_019['match_fields']} + sub_regime={rule_019.get('sub_regime_constraint')}")

    df_resolved = df_full[df_full["won"].notna()].copy()
    print(f"  resolved rows (won notna): {len(df_resolved):,}")

    # --- Identify rule_019 matches first (used for inversion in broad baseline)
    print("\n  identifying rule_019 matches (df.apply)...")
    t0 = time.time()
    rule_mask = df_resolved.apply(lambda row: matches_rule(row, rule_019), axis=1)
    df_matched = df_resolved[rule_mask].copy()
    print(f"  rule_019 resolved matches: {len(df_matched):,} rows ({time.time()-t0:.1f}s)")

    # --- RULE_019 matches
    print("\n[RULE_019] matches")
    t0 = time.time()
    rule_stats = per_symbol_lag1_autocorr(df_matched, label="rule_019_matches")
    _print_block(rule_stats)
    print(f"  ({time.time()-t0:.1f}s)")

    # --- CELL baseline: UP_TRI in Bear, NOT hot, sub_regime explicitly assigned
    print("\n[CELL BASELINE] signal=UP_TRI AND regime=Bear AND sub_regime notna AND sub_regime != hot")
    t0 = time.time()
    uptri_bear_mask = (df_resolved["signal"] == "UP_TRI") & (df_resolved["regime"] == "Bear")
    n_excluded_nan = int((uptri_bear_mask & df_resolved["sub_regime"].isna()).sum())
    cell_mask = (
        uptri_bear_mask
        & df_resolved["sub_regime"].notna()
        & (df_resolved["sub_regime"] != "hot")
    )
    df_cell = df_resolved[cell_mask].copy()
    print(
        f"  cell-baseline rows: {len(df_cell):,}  "
        f"(excluded {n_excluded_nan:,} NaN-subregime UP_TRI Bear rows)"
    )
    cell_baseline = per_symbol_lag1_autocorr(df_cell, label="baseline_uptri_bear_not_hot")
    cell_baseline["n_excluded_nan_subregime"] = n_excluded_nan
    _print_block(cell_baseline)
    print(f"  ({time.time()-t0:.1f}s)")

    # --- BROAD baseline: everything NOT matching rule_019
    print("\n[BROAD BASELINE] all resolved signals NOT matching rule_019")
    t0 = time.time()
    df_other = df_resolved[~rule_mask].copy()
    print(f"  broad-baseline rows: {len(df_other):,}")
    broad_baseline = per_symbol_lag1_autocorr(df_other, label="baseline_all_other")
    _print_block(broad_baseline)
    print(f"  ({time.time()-t0:.1f}s)")

    # --- Comparison (raw pooled differences, decimal scale)
    rule_pooled = rule_stats["pooled_autocorr"]
    cell_pooled = cell_baseline["pooled_autocorr"]
    broad_pooled = broad_baseline["pooled_autocorr"]

    rule_minus_cell = (
        (rule_pooled - cell_pooled)
        if (rule_pooled is not None and cell_pooled is not None)
        else None
    )
    rule_minus_broad = (
        (rule_pooled - broad_pooled)
        if (rule_pooled is not None and broad_pooled is not None)
        else None
    )

    print("\nCOMPARISON (pooled autocorr — raw absolute differences)")
    print(f"  rule_019 pooled            = {_fmt(rule_pooled)}")
    print(f"  cell_baseline pooled       = {_fmt(cell_pooled)}")
    print(f"  broad_baseline pooled      = {_fmt(broad_pooled)}")
    print(f"  rule_019 - cell_baseline   = {_fmt(rule_minus_cell)}  (most diagnostic)")
    print(f"  rule_019 - broad_baseline  = {_fmt(rule_minus_broad)}  (sanity check)")

    # --- Persist
    out = {
        "rule_id": RULE_ID,
        "group_col": GROUP_COL,
        "sort_col": SORT_COL,
        "min_signals_per_symbol": MIN_SIGNALS_PER_SYMBOL,
        "rule_019_matches": rule_stats,
        "baseline_uptri_bear_not_hot": cell_baseline,
        "baseline_all_other": broad_baseline,
        "comparison_pooled": {
            "rule_019_minus_cell_baseline": rule_minus_cell,
            "rule_019_minus_broad_baseline": rule_minus_broad,
        },
        "elapsed_seconds": round(time.time() - t_total, 2),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total elapsed: {out['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
