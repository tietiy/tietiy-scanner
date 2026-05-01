"""
Phase 4 combination generator — produces feature combinations × levels per
cohort cell for downstream walk-forward testing.

Per (signal_type × regime × horizon) cohort cell:
  • Top-20 features sourced from lifetime-{regime} of feature_importance.json
  • 1-feature combos: 20 × ≤3 levels = ≤60 per cohort
  • 2-feature combos: C(20,2) × ≤9 = ≤1,710 per cohort
  • 3-feature combos: C(20,3) × ≤27 = ≤30,780 per cohort
  • 4-feature combos: pruned aggressively (top-10 features only +
                        ≥2-of-4 with univariate edge_pp > 0.05);
                        capped at 5,000 per cohort

Levels per feature:
  • Numeric (float/int): low / medium / high using spec thresholds parsed
                           from feature_library JSON (`<X`, `X-Y`, `>X`)
  • Boolean: True / False
  • Categorical: top-N most-frequent enum values (capped at 3)

Output: lab/output/combinations_pending.parquet (flat schema with up to
4 (feature_id, level) pairs per row).
"""
from __future__ import annotations

import hashlib
import json
import sys
from itertools import combinations, product
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_HERE))

from feature_loader import FeatureRegistry, FeatureSpec  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402
from cohort_horizon_config import (  # noqa: E402
    list_active_cohort_cells, COHORT_HORIZONS, COHORT_SKIP,
)

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
OUTPUT_PATH = _LAB_ROOT / "output" / "combinations_pending.parquet"

MAX_LEVELS_PER_FEATURE = 3
TOP_N_FEATURES = 20
TOP_N_FEATURES_4COMBO = 10  # 4-combos draw from top 10 only
EDGE_PP_4COMBO_FLOOR = 0.05  # ≥2 of 4 features need edge_pp > this
COMBO_4FEAT_CAP = 5_000  # cap per cohort


# ── Threshold parsing ──────────────────────────────────────────────────

def _parse_numeric_thresholds(level_thresholds: dict) -> Optional[tuple[float, float]]:
    """Parse spec thresholds like {"low": "<0.3", "medium": "0.3-0.7",
    "high": ">0.7"} into (low_bound, high_bound). None if unparseable."""
    if not isinstance(level_thresholds, dict):
        return None
    low_str = level_thresholds.get("low")
    high_str = level_thresholds.get("high")
    if low_str is None or high_str is None:
        return None
    try:
        low_bound = float(str(low_str).replace("<", "").strip())
        high_bound = float(str(high_str).replace(">", "").strip())
        return (low_bound, high_bound)
    except (ValueError, AttributeError):
        return None


def derive_levels(spec: FeatureSpec, signal_values: pd.Series) -> list[str]:
    """Derive valid level labels for a feature, capped at MAX_LEVELS_PER_FEATURE.

    For categorical features, returns the most-frequent enum values up to cap.
    For boolean features, returns ["True", "False"] (2 levels).
    For numeric features with parseable thresholds, returns ["low","medium","high"].
    For numeric without thresholds, falls back to tercile-based labels using data.
    """
    if spec.value_type == "bool":
        return ["True", "False"]
    if spec.value_type == "categorical":
        # Use top-N frequencies in this cohort's actual data
        non_null = signal_values.dropna()
        if non_null.empty:
            return []
        counts = non_null.astype(str).value_counts()
        top = counts.head(MAX_LEVELS_PER_FEATURE).index.tolist()
        return top
    # numeric (float/int)
    bounds = _parse_numeric_thresholds(spec.level_thresholds)
    if bounds is None:
        return []  # skip features without parseable thresholds
    return ["low", "medium", "high"]


def signal_matches_level(spec: FeatureSpec, values: pd.Series, level: str,
                            bounds_cache: dict) -> pd.Series:
    """Vectorized: return boolean mask of signals where feature is at `level`.
    `bounds_cache` keyed by feature_id holds pre-parsed (low_bound, high_bound)
    for numeric features.
    """
    if spec.value_type == "bool":
        # values may be bool, int 0/1, or string "True"/"False"
        if level == "True":
            return values.astype(bool, errors="ignore") == True  # noqa
        else:
            return values.astype(bool, errors="ignore") == False  # noqa
    if spec.value_type == "categorical":
        return values.astype(str) == str(level)
    # numeric
    bounds = bounds_cache.get(spec.feature_id)
    if bounds is None:
        bounds = _parse_numeric_thresholds(spec.level_thresholds)
        bounds_cache[spec.feature_id] = bounds
    if bounds is None:
        return pd.Series([False] * len(values), index=values.index)
    low_b, high_b = bounds
    if level == "low":
        return values < low_b
    if level == "high":
        return values > high_b
    # medium
    return (values >= low_b) & (values <= high_b)


# ── Combination ID hashing ────────────────────────────────────────────

def _combo_hash(signal_type: str, regime: str, horizon: str,
                  feature_levels: list[tuple[str, str]]) -> str:
    """Deterministic hash of the cohort + (sorted) feature-level pairs."""
    sorted_pairs = sorted(feature_levels)
    payload = f"{signal_type}|{regime}|{horizon}|{sorted_pairs}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Generator ──────────────────────────────────────────────────────────

def _resolve_cohort_top_features(importance_data: dict,
                                     regime: str,
                                     n: int = TOP_N_FEATURES) -> list[dict]:
    """Return top-N feature dicts (with feature_id + univariate_edge_pp) for
    the given regime, sourced from `lifetime-{regime}` cohort."""
    cohort_key = f"lifetime-{regime}"
    cohort = importance_data["cohorts"].get(cohort_key)
    if cohort is None:
        raise KeyError(f"feature_importance missing cohort {cohort_key}")
    return cohort["ranked_features"][:n]


def generate_combinations(
        signals_df: pd.DataFrame,
        importance_data: dict,
        registry: FeatureRegistry,
        active_cells: list[tuple[str, str, str]],
        verbose: bool = True) -> pd.DataFrame:
    """Generate all combinations across active cohort cells."""
    rows: list[dict] = []
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict[str, Optional[tuple[float, float]]] = {}

    for sig_type, regime, horizon in active_cells:
        # Cohort signals (used only to derive categorical level frequencies)
        cohort_signals = signals_df[
            (signals_df["signal"] == sig_type)
            & (signals_df["regime"] == regime)
        ]
        top_features = _resolve_cohort_top_features(
            importance_data, regime, TOP_N_FEATURES)

        # Build per-feature levels list
        feature_levels: list[tuple[str, list[str]]] = []
        edge_pp_by_id: dict[str, float] = {}
        for f in top_features:
            fid = f["feature_id"]
            spec = spec_by_id.get(fid)
            if spec is None:
                continue
            col = _FEAT_PREFIX + fid
            if col not in cohort_signals.columns:
                continue
            vals = cohort_signals[col]
            levels = derive_levels(spec, vals)
            if not levels:
                continue
            feature_levels.append((fid, levels))
            edge_pp_by_id[fid] = float(f.get("univariate_edge_pp") or 0.0)

        if verbose:
            n_feats_used = len(feature_levels)
            print(f"  {sig_type:<12} × {regime:<8} × {horizon:<3}  "
                  f"top-{n_feats_used} features × levels:")

        # 1-feature combos
        for fid, levels in feature_levels:
            for lvl in levels:
                rows.append(_combo_row(sig_type, regime, horizon,
                                          [(fid, lvl)]))

        # 2-feature combos
        for (fid_a, levels_a), (fid_b, levels_b) in combinations(
                feature_levels, 2):
            for la, lb in product(levels_a, levels_b):
                rows.append(_combo_row(sig_type, regime, horizon,
                                          [(fid_a, la), (fid_b, lb)]))

        # 3-feature combos
        for (fid_a, levels_a), (fid_b, levels_b), (fid_c, levels_c) in (
                combinations(feature_levels, 3)):
            for la, lb, lc in product(levels_a, levels_b, levels_c):
                rows.append(_combo_row(sig_type, regime, horizon,
                                          [(fid_a, la), (fid_b, lb),
                                           (fid_c, lc)]))

        # 4-feature combos — pruned (top-10 features only,
        # ≥2 of 4 features must have edge_pp > floor)
        top10_set = {fid for fid, _ in feature_levels[:TOP_N_FEATURES_4COMBO]}
        feature_levels_top10 = [(fid, lvls) for fid, lvls in feature_levels
                                  if fid in top10_set]
        n_4combo = 0
        for combo in combinations(feature_levels_top10, 4):
            fids_in_combo = [c[0] for c in combo]
            n_high_edge = sum(1 for fid in fids_in_combo
                                if edge_pp_by_id.get(fid, 0) > EDGE_PP_4COMBO_FLOOR)
            if n_high_edge < 2:
                continue
            for level_combo in product(*[c[1] for c in combo]):
                rows.append(_combo_row(sig_type, regime, horizon,
                                          list(zip(fids_in_combo, level_combo))))
                n_4combo += 1
                if n_4combo >= COMBO_4FEAT_CAP:
                    break
            if n_4combo >= COMBO_4FEAT_CAP:
                break

    return pd.DataFrame(rows)


def _combo_row(signal_type: str, regime: str, horizon: str,
                  feature_levels: list[tuple[str, str]]) -> dict:
    fc = len(feature_levels)
    sorted_fl = sorted(feature_levels)
    row = {
        "combo_id": _combo_hash(signal_type, regime, horizon, sorted_fl),
        "signal_type": signal_type,
        "regime": regime,
        "horizon": horizon,
        "feature_count": fc,
    }
    for i, (fid, lvl) in enumerate(sorted_fl):
        slot = chr(ord("a") + i)
        row[f"feature_{slot}_id"] = fid
        row[f"feature_{slot}_level"] = lvl
    # Pad missing slots
    for i in range(fc, 4):
        slot = chr(ord("a") + i)
        row[f"feature_{slot}_id"] = None
        row[f"feature_{slot}_level"] = None
    return row


def main():
    print("─" * 72)
    print("Phase 4 SUB-BLOCK 4B — Combination generator")
    print("─" * 72)

    print(f"\nLoading: {ENRICHED_PATH}")
    signals_df = pd.read_parquet(ENRICHED_PATH)
    print(f"  signals: {len(signals_df)}")

    print(f"Loading: {IMPORTANCE_PATH}")
    with open(IMPORTANCE_PATH) as fh:
        importance = json.load(fh)

    registry = FeatureRegistry.load_all()
    active_cells = list_active_cohort_cells()
    print(f"\nActive cohort cells: {len(active_cells)}")

    print("\nGenerating combinations per cohort:")
    combos = generate_combinations(signals_df, importance, registry, active_cells)
    print(f"\nTotal combinations generated: {len(combos)}")

    # Per-cohort breakdown by feature count
    print("\nPer-cohort × feature_count breakdown:")
    breakdown = combos.groupby(
        ["signal_type", "regime", "horizon", "feature_count"]).size()
    print(breakdown.unstack(fill_value=0).to_string())

    # HALT check: total combo count
    if len(combos) > 1_000_000:
        sys.exit(f"HALT: {len(combos)} combos > 1M limit")
    if len(combos) < 1_000:
        sys.exit(f"HALT: {len(combos)} combos < 1K floor")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combos.to_parquet(OUTPUT_PATH, index=False)
    size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_mb:.1f} MB, {len(combos)} rows)")


if __name__ == "__main__":
    main()
