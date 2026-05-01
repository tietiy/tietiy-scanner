"""
Phase 4 walk-forward tester.

For each combination, evaluates W/L/F outcomes on train (2011-2018),
validate (2019-2022), and test (2023-2025) periods. Computes per-period n /
n_wins / n_losses / wr + drift (|train_wr - test_wr|), edge_pp vs Phase 3
cohort baseline, Wilson 95% on test_wr.

Stop-out logic mirrors `baseline_computer` (daily Low/High breach, exit at
stop). Outcomes cached per (signal_idx × horizon) to avoid 1.5M redundant
walk-forward computations across combinations.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_HERE))

from baseline_computer import (  # noqa: E402
    BaselineComputer, compute_signal_outcome, wilson_interval,
    binomial_p_two_sided, FLAT_THRESHOLD,
)
from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402
from combination_generator import (  # noqa: E402
    signal_matches_level, _parse_numeric_thresholds,
)
from cohort_horizon_config import COHORT_HORIZONS  # noqa: E402

# Period boundaries (scan_date inclusive)
TRAIN_START = pd.Timestamp("2011-01-01")
TRAIN_END = pd.Timestamp("2018-12-31")
VALIDATE_START = pd.Timestamp("2019-01-01")
VALIDATE_END = pd.Timestamp("2022-12-31")
TEST_START = pd.Timestamp("2023-01-01")
TEST_END = pd.Timestamp("2025-12-31")

PERIODS = (
    ("train", TRAIN_START, TRAIN_END),
    ("validate", VALIDATE_START, VALIDATE_END),
    ("test", TEST_START, TEST_END),
)

# Minimum n per period to return a non-INSUFFICIENT_DATA result
MIN_N_PER_PERIOD = 30


@dataclass
class CombinationResult:
    """Walk-forward result for one combination."""
    combo_id: str
    signal_type: str
    regime: str
    horizon: str
    feature_count: int
    # Per-period stats
    train_n: int
    train_n_wins: int
    train_n_losses: int
    train_wr: Optional[float]
    train_avg_return_pct: Optional[float]
    validate_n: int
    validate_n_wins: int
    validate_n_losses: int
    validate_wr: Optional[float]
    validate_avg_return_pct: Optional[float]
    test_n: int
    test_n_wins: int
    test_n_losses: int
    test_wr: Optional[float]
    test_avg_return_pct: Optional[float]
    # Derived metrics
    drift_train_test_pp: Optional[float]
    drift_train_validate_pp: Optional[float]
    edge_pp_test: Optional[float]
    test_wilson_lower_95: Optional[float]
    test_wilson_upper_95: Optional[float]
    test_p_value_vs_baseline: Optional[float]
    baseline_wr: Optional[float]
    skip_reason: Optional[str]


# ── Outcome caching ────────────────────────────────────────────────────

def precompute_outcomes(signals_df: pd.DataFrame,
                          horizons: list[int],
                          cache_dir: Path) -> dict:
    """Compute outcomes for every (signal_idx × horizon) once.

    Returns dict keyed by horizon → DataFrame indexed by signal_idx with
    columns: label, return_pct.
    """
    bc = BaselineComputer(signals_df, cache_dir=cache_dir,
                            entry_col="entry_price")
    outcomes_long = bc.compute_outcomes(horizons=horizons,
                                            progress_every=20_000)
    # Pivot to dict[h] → DataFrame
    out: dict[int, pd.DataFrame] = {}
    for h in horizons:
        sub = outcomes_long[outcomes_long["horizon"] == h]
        sub = sub.set_index("sig_idx")[["label", "return_pct"]]
        out[h] = sub
    return out


# ── Predicate filtering ────────────────────────────────────────────────

def build_combo_mask(cohort_signals: pd.DataFrame,
                       feature_levels: list[tuple[str, str]],
                       spec_by_id: dict,
                       bounds_cache: dict) -> pd.Series:
    """Boolean mask: rows of cohort_signals matching ALL (feature, level) preds.

    feature_levels: list of (feature_id, level_label).
    """
    if not feature_levels:
        return pd.Series([False] * len(cohort_signals), index=cohort_signals.index)
    masks = []
    for fid, lvl in feature_levels:
        spec = spec_by_id.get(fid)
        if spec is None:
            return pd.Series([False] * len(cohort_signals), index=cohort_signals.index)
        col = _FEAT_PREFIX + fid
        if col not in cohort_signals.columns:
            return pd.Series([False] * len(cohort_signals), index=cohort_signals.index)
        m = signal_matches_level(spec, cohort_signals[col], lvl, bounds_cache)
        masks.append(m.fillna(False))
    if not masks:
        return pd.Series([False] * len(cohort_signals), index=cohort_signals.index)
    combined = masks[0]
    for m in masks[1:]:
        combined = combined & m
    return combined


# ── Per-combination evaluation ────────────────────────────────────────

def _period_stats(signals_period: pd.DataFrame,
                    outcomes_h: pd.DataFrame) -> dict:
    """For signals in `signals_period` (index aligned with outcomes_h.index),
    compute per-period n / W / L / WR / avg_return."""
    idx = signals_period.index.intersection(outcomes_h.index)
    if len(idx) == 0:
        return {"n": 0, "n_w": 0, "n_l": 0, "wr": None, "avg_ret": None}
    sub = outcomes_h.loc[idx]
    valid = sub[sub["label"].isin(["W", "L", "F"])]
    n = len(valid)
    n_w = int((valid["label"] == "W").sum())
    n_l = int((valid["label"] == "L").sum())
    n_wl = n_w + n_l
    wr = (n_w / n_wl) if n_wl > 0 else None
    rets = valid["return_pct"].dropna()
    avg_ret = float(rets.mean()) if len(rets) else None
    return {"n": n, "n_w": n_w, "n_l": n_l, "wr": wr, "avg_ret": avg_ret}


def evaluate_combination(combo_row: dict,
                            signals_df: pd.DataFrame,
                            outcomes_by_horizon: dict,
                            spec_by_id: dict,
                            bounds_cache: dict,
                            baselines_data: dict,
                            n_total_combos: int) -> CombinationResult:
    """Evaluate one combination row against the walk-forward periods."""
    sig_type = combo_row["signal_type"]
    regime = combo_row["regime"]
    horizon = combo_row["horizon"]
    horizon_int = int(horizon[1:])  # "D10" → 10

    # Cohort signals (signal_type + regime)
    cohort_signals = signals_df[
        (signals_df["signal"] == sig_type)
        & (signals_df["regime"] == regime)
    ]

    # Build (feature_id, level) list from row's feature_a..d slots.
    # pd.DataFrame.to_dict() returns NaN (not None) for missing slots; check
    # via pd.notna to handle both correctly.
    feature_levels = []
    for slot in ("a", "b", "c", "d"):
        fid = combo_row.get(f"feature_{slot}_id")
        lvl = combo_row.get(f"feature_{slot}_level")
        if pd.notna(fid) and pd.notna(lvl):
            feature_levels.append((fid, lvl))

    mask = build_combo_mask(cohort_signals, feature_levels,
                              spec_by_id, bounds_cache)
    matched = cohort_signals[mask]

    outcomes_h = outcomes_by_horizon.get(horizon_int)
    if outcomes_h is None:
        return _build_skip_result(combo_row, "no_outcomes_for_horizon")

    # Per-period stats
    period_stats = {}
    for name, start, end in PERIODS:
        period_signals = matched[
            (matched["scan_date"] >= start) & (matched["scan_date"] <= end)
        ]
        period_stats[name] = _period_stats(period_signals, outcomes_h)

    # Insufficient n in any period → skip
    for name in ("train", "validate", "test"):
        if period_stats[name]["n"] < MIN_N_PER_PERIOD:
            return _build_skip_result(
                combo_row, f"insufficient_n_{name}",
                period_stats=period_stats)

    # Baseline lookup
    baseline_wr = None
    try:
        baseline_wr = baselines_data["cohorts"][sig_type][regime][horizon].get("wr")
    except KeyError:
        baseline_wr = None

    test_wr = period_stats["test"]["wr"]
    train_wr = period_stats["train"]["wr"]
    validate_wr = period_stats["validate"]["wr"]

    drift_train_test = (
        abs(train_wr - test_wr)
        if (train_wr is not None and test_wr is not None) else None)
    drift_train_validate = (
        abs(train_wr - validate_wr)
        if (train_wr is not None and validate_wr is not None) else None)
    edge_pp = (
        (test_wr - baseline_wr)
        if (test_wr is not None and baseline_wr is not None) else None)

    # Wilson on test_wr
    test_n_wl = period_stats["test"]["n_w"] + period_stats["test"]["n_l"]
    if test_wr is not None and test_n_wl >= 1:
        wlow, wup = wilson_interval(period_stats["test"]["n_w"], test_n_wl)
    else:
        wlow, wup = None, None

    # p-value vs baseline WR (binomial test against null=baseline_wr)
    p_value = None
    if (baseline_wr is not None and test_wr is not None
            and test_n_wl >= 1):
        p_value = binomial_p_two_sided(
            period_stats["test"]["n_w"], test_n_wl, baseline_wr)

    return CombinationResult(
        combo_id=combo_row["combo_id"],
        signal_type=sig_type,
        regime=regime,
        horizon=horizon,
        feature_count=int(combo_row["feature_count"]),
        train_n=period_stats["train"]["n"],
        train_n_wins=period_stats["train"]["n_w"],
        train_n_losses=period_stats["train"]["n_l"],
        train_wr=train_wr,
        train_avg_return_pct=period_stats["train"]["avg_ret"],
        validate_n=period_stats["validate"]["n"],
        validate_n_wins=period_stats["validate"]["n_w"],
        validate_n_losses=period_stats["validate"]["n_l"],
        validate_wr=validate_wr,
        validate_avg_return_pct=period_stats["validate"]["avg_ret"],
        test_n=period_stats["test"]["n"],
        test_n_wins=period_stats["test"]["n_w"],
        test_n_losses=period_stats["test"]["n_l"],
        test_wr=test_wr,
        test_avg_return_pct=period_stats["test"]["avg_ret"],
        drift_train_test_pp=drift_train_test,
        drift_train_validate_pp=drift_train_validate,
        edge_pp_test=edge_pp,
        test_wilson_lower_95=wlow,
        test_wilson_upper_95=wup,
        test_p_value_vs_baseline=p_value,
        baseline_wr=baseline_wr,
        skip_reason=None,
    )


def _build_skip_result(combo_row: dict, reason: str,
                          period_stats: Optional[dict] = None
                          ) -> CombinationResult:
    ps = period_stats or {}
    def _g(p, k):
        return ps.get(p, {}).get(k, 0 if k.startswith("n") else None)
    return CombinationResult(
        combo_id=combo_row["combo_id"],
        signal_type=combo_row["signal_type"],
        regime=combo_row["regime"],
        horizon=combo_row["horizon"],
        feature_count=int(combo_row["feature_count"]),
        train_n=_g("train", "n"),
        train_n_wins=_g("train", "n_w"),
        train_n_losses=_g("train", "n_l"),
        train_wr=_g("train", "wr"),
        train_avg_return_pct=_g("train", "avg_ret"),
        validate_n=_g("validate", "n"),
        validate_n_wins=_g("validate", "n_w"),
        validate_n_losses=_g("validate", "n_l"),
        validate_wr=_g("validate", "wr"),
        validate_avg_return_pct=_g("validate", "avg_ret"),
        test_n=_g("test", "n"),
        test_n_wins=_g("test", "n_w"),
        test_n_losses=_g("test", "n_l"),
        test_wr=_g("test", "wr"),
        test_avg_return_pct=_g("test", "avg_ret"),
        drift_train_test_pp=None, drift_train_validate_pp=None,
        edge_pp_test=None,
        test_wilson_lower_95=None, test_wilson_upper_95=None,
        test_p_value_vs_baseline=None,
        baseline_wr=None,
        skip_reason=reason,
    )


# ── Driver ────────────────────────────────────────────────────────────

def run_walk_forward(combinations_df: pd.DataFrame,
                       signals_df: pd.DataFrame,
                       outcomes_by_horizon: dict,
                       baselines_data: dict,
                       registry: FeatureRegistry,
                       progress_every: int = 5_000) -> pd.DataFrame:
    """Apply walk-forward evaluation to all combinations."""
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}
    n_combos = len(combinations_df)
    n_total_combos = n_combos
    results: list[CombinationResult] = []

    for i, (_, row) in enumerate(combinations_df.iterrows(), 1):
        result = evaluate_combination(
            row.to_dict(), signals_df, outcomes_by_horizon,
            spec_by_id, bounds_cache, baselines_data, n_total_combos)
        results.append(result)
        if i % progress_every == 0:
            print(f"  walk-forward {i}/{n_combos} ({i / n_combos:.0%})",
                  file=sys.stderr)

    # Convert dataclass results → DataFrame
    rows = [r.__dict__ for r in results]
    return pd.DataFrame(rows)
