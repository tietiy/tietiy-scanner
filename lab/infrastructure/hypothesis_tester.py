"""
MS-4 — Backtest Lab hypothesis tester (train/test OOS protocol per
PROMOTION_PROTOCOL.md Gate 3).

Implements three-tier structure (Tier S/A/B/REJECT) for both BOOST and KILL
patterns + filter sub-cohort inheritance. Statistical thresholds locked per
PROMOTION_PROTOCOL.md commit at founding (b8dfc30).

This module is CORRECTNESS-CRITICAL: every Lab pattern decision flows through
these threshold evaluators. Unit tests in test_hypothesis_tester.py MUST pass
before any real cohort hypothesis runs.

Public API:
    compute_cohort_stats(signals_df, cohort_filter, outcome_field='outcome')
        → dict with {n_total, n_resolved, n_open, n_win, n_loss, n_flat,
          wr_excl_flat, wr_excl_flat_excl_open, wilson_lower_95, p_value_vs_50}

    train_test_split(signals_df, split_date='2023-01-01')
        → (train_df, test_df) chronological split

    evaluate_boost_tier(train_stats, test_stats)
        → 'S' / 'A' / 'B' / 'REJECT' per Gate 3 BOOST tier thresholds

    evaluate_kill_tier(train_stats, test_stats)
        → 'S' / 'A' / 'B' / 'REJECT' per Gate 3 KILL tier thresholds

    evaluate_hypothesis(signals_df, cohort_filter, hypothesis_type='BOOST')
        → master function: split → cohort stats on train + test → tier eval
        → returns full hypothesis report dict
        (Renamed from test_hypothesis to avoid pytest's test_* auto-discovery collision)

Tier thresholds (PROMOTION_PROTOCOL.md Gate 3 verbatim):

BOOST patterns (positive-edge cohorts):
  Tier S: train_wr ≥ 0.75 AND train_n ≥ 100 AND test_wr ≥ 0.65 AND test_n ≥ 30 AND drift < 0.10
  Tier A: train_wr ≥ 0.65 AND train_n ≥ 50 AND test_wr ≥ 0.55 AND test_n ≥ 20 AND drift < 0.15
  Tier B: train_wr ≥ 0.60 AND train_n ≥ 30 AND test_wr ≥ 0.50 AND test_n ≥ 15 AND drift < 0.20

KILL patterns (negative-edge cohorts; actively suppressed):
  Tier S: train_wr ≤ 0.25 AND train_n ≥ 100 AND test_wr ≤ 0.30 AND test_n ≥ 30 AND drift < 0.10
  Tier A: train_wr ≤ 0.35 AND train_n ≥ 50 AND test_wr ≤ 0.40 AND test_n ≥ 20 AND drift < 0.15
  Tier B: train_wr ≤ 0.40 AND train_n ≥ 30 AND test_wr ≤ 0.45 AND test_n ≥ 15 AND drift < 0.20

drift = |train_wr - test_wr|

NO REAL COHORT EXECUTION in this module. Pure functions; outcomes_d6 already
computed by signal_replayer.py upstream.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# ── Constants per PROMOTION_PROTOCOL.md Gate 3 ────────────────────────

_DEFAULT_SPLIT_DATE = "2023-01-01"
_WILSON_Z_95 = 1.96

# BOOST tier thresholds
_BOOST_TIER_S = {"train_wr_min": 0.75, "train_n_min": 100,
                  "test_wr_min": 0.65, "test_n_min": 30, "drift_max": 0.10}
_BOOST_TIER_A = {"train_wr_min": 0.65, "train_n_min": 50,
                  "test_wr_min": 0.55, "test_n_min": 20, "drift_max": 0.15}
_BOOST_TIER_B = {"train_wr_min": 0.60, "train_n_min": 30,
                  "test_wr_min": 0.50, "test_n_min": 15, "drift_max": 0.20}

# KILL tier thresholds
_KILL_TIER_S = {"train_wr_max": 0.25, "train_n_min": 100,
                 "test_wr_max": 0.30, "test_n_min": 30, "drift_max": 0.10}
_KILL_TIER_A = {"train_wr_max": 0.35, "train_n_min": 50,
                 "test_wr_max": 0.40, "test_n_min": 20, "drift_max": 0.15}
_KILL_TIER_B = {"train_wr_max": 0.40, "train_n_min": 30,
                 "test_wr_max": 0.45, "test_n_min": 15, "drift_max": 0.20}

# Wilson lower + p-value gates (BOOST only; PROMOTION_PROTOCOL.md lines 65 + 72)
_BOOST_TIER_S_WILSON_MIN = 0.60
_BOOST_TIER_A_WILSON_MIN = 0.50
_BOOST_P_VALUE_MAX = 0.05

# Outcome label sets
_WIN_OUTCOMES = {"DAY6_WIN", "TARGET_HIT"}
_LOSS_OUTCOMES = {"DAY6_LOSS", "STOP_HIT"}
_FLAT_OUTCOMES = {"DAY6_FLAT"}
_OPEN_OUTCOMES = {"OPEN"}


# ── Cohort filter ─────────────────────────────────────────────────────

def filter_cohort(signals_df: pd.DataFrame, cohort_filter: dict) -> pd.DataFrame:
    """Filter signals_df by cohort_filter dict. Each (key, value) pair must
    match. None values in cohort_filter are wildcards (no filter on that key).
    """
    if signals_df is None or signals_df.empty:
        return signals_df
    df = signals_df
    for key, val in cohort_filter.items():
        if val is None:
            continue
        if key not in df.columns:
            # Filter key not present in df — treat as no-match (empty result)
            return df.iloc[0:0]
        df = df[df[key] == val]
    return df


# ── Wilson lower bound + p-value ──────────────────────────────────────

def wilson_lower_bound_95(wins: int, n: int) -> float:
    """Wilson 95% lower bound. Returns 0.0 if n=0."""
    if n <= 0:
        return 0.0
    p_hat = wins / n
    z = _WILSON_Z_95
    z2 = z * z
    denom = 1 + z2 / n
    centre = p_hat + z2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * n)) / n)
    return round((centre - margin) / denom, 4)


def binomial_p_value_vs_50(wins: int, n: int) -> float:
    """Two-sided binomial test against null p=0.5. Returns p-value.
    For n large enough, normal approximation is reasonable; else exact.
    """
    if n <= 0:
        return 1.0
    # Use normal approximation: z = (x - n*0.5) / sqrt(n*0.25)
    expected = n * 0.5
    var = n * 0.25
    if var <= 0:
        return 1.0
    z = abs((wins - expected) / math.sqrt(var))
    # Two-sided p-value via standard normal CDF approximation
    # Using erf-based approximation
    p = 2 * (1 - _normal_cdf(z))
    return round(max(0.0, min(1.0, p)), 6)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using erf approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ── Cohort stats ──────────────────────────────────────────────────────

def compute_cohort_stats(signals_df: pd.DataFrame,
                          cohort_filter: dict,
                          outcome_field: str = "outcome") -> dict:
    """Compute cohort statistics for a filtered subset.

    Returns
    -------
    dict
        {n_total, n_resolved, n_open, n_win, n_loss, n_flat, wr_excl_flat,
         wr_excl_flat_excl_open, wilson_lower_95, p_value_vs_50}

    Notes
    -----
    - n_total includes OPEN signals.
    - n_resolved = n_win + n_loss + n_flat (OPEN excluded).
    - wr_excl_flat = wins / (wins + losses) (FLAT excluded; OPEN excluded).
    - wr_excl_flat_excl_open = same as wr_excl_flat (legacy alias).
    - Wilson + p-value computed on (wins, wins + losses) — flats and opens excluded.
    """
    cohort = filter_cohort(signals_df, cohort_filter)

    n_total = len(cohort)
    if n_total == 0 or outcome_field not in cohort.columns:
        return {
            "n_total": n_total, "n_resolved": 0, "n_open": 0,
            "n_win": 0, "n_loss": 0, "n_flat": 0,
            "wr_excl_flat": None, "wr_excl_flat_excl_open": None,
            "wilson_lower_95": None, "p_value_vs_50": None,
        }

    outcomes = cohort[outcome_field].astype(str)
    n_win = int(outcomes.isin(_WIN_OUTCOMES).sum())
    n_loss = int(outcomes.isin(_LOSS_OUTCOMES).sum())
    n_flat = int(outcomes.isin(_FLAT_OUTCOMES).sum())
    n_open = int(outcomes.isin(_OPEN_OUTCOMES).sum())
    n_resolved = n_win + n_loss + n_flat

    if (n_win + n_loss) > 0:
        wr_excl_flat = round(n_win / (n_win + n_loss), 4)
        wilson = wilson_lower_bound_95(n_win, n_win + n_loss)
        p_val = binomial_p_value_vs_50(n_win, n_win + n_loss)
    else:
        wr_excl_flat = None
        wilson = None
        p_val = None

    return {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_open": n_open,
        "n_win": n_win,
        "n_loss": n_loss,
        "n_flat": n_flat,
        "wr_excl_flat": wr_excl_flat,
        "wr_excl_flat_excl_open": wr_excl_flat,  # legacy alias
        "wilson_lower_95": wilson,
        "p_value_vs_50": p_val,
    }


# ── Train/test split ──────────────────────────────────────────────────

def train_test_split(signals_df: pd.DataFrame,
                      split_date: str = _DEFAULT_SPLIT_DATE,
                      date_field: str = "scan_date") -> tuple:
    """Chronological split: rows with date_field < split_date → train;
    rows with date_field ≥ split_date → test. Returns (train_df, test_df)."""
    if signals_df is None or signals_df.empty:
        return signals_df, signals_df
    if date_field not in signals_df.columns:
        raise ValueError(f"date_field {date_field!r} not in signals_df columns")

    # Normalize: support both string YYYY-MM-DD and Timestamp
    dates = pd.to_datetime(signals_df[date_field])
    cutoff = pd.to_datetime(split_date)

    train_mask = dates < cutoff
    test_mask = dates >= cutoff
    train_df = signals_df[train_mask].copy()
    test_df = signals_df[test_mask].copy()
    return train_df, test_df


# ── Tier evaluators (Gate 3) ──────────────────────────────────────────

def evaluate_boost_tier(train_stats: dict, test_stats: dict,
                         decision_log: Optional[list] = None) -> str:
    """Returns 'S' / 'A' / 'B' / 'REJECT' per Gate 3 BOOST thresholds.

    Tier S/A additionally require train Wilson 95% lower bound + train p-value
    gates per PROMOTION_PROTOCOL.md Gate 3 lines 65 + 72:
      Tier S: train_wilson_lower ≥ 0.60 AND train_p_value < 0.05
      Tier A: train_wilson_lower ≥ 0.50 AND train_p_value < 0.05
      Tier B: NO Wilson/p gate (watch-only per spec).

    If decision_log is provided, per-criterion pass/fail lines are appended.
    """
    log = decision_log if decision_log is not None else []
    twr = train_stats.get("wr_excl_flat")
    ewr = test_stats.get("wr_excl_flat")

    if twr is None or ewr is None:
        log.append("BOOST REJECT: train_wr or test_wr is None (insufficient resolved signals).")
        return "REJECT"

    if _check_boost_tier(train_stats, test_stats, "S", _BOOST_TIER_S,
                         _BOOST_TIER_S_WILSON_MIN, require_wilson_p=True, log=log):
        return "S"
    if _check_boost_tier(train_stats, test_stats, "A", _BOOST_TIER_A,
                         _BOOST_TIER_A_WILSON_MIN, require_wilson_p=True, log=log):
        return "A"
    if _check_boost_tier(train_stats, test_stats, "B", _BOOST_TIER_B,
                         wilson_min=None, require_wilson_p=False, log=log):
        return "B"
    return "REJECT"


def _check_boost_tier(train_stats: dict, test_stats: dict,
                      tier_name: str, thresholds: dict,
                      wilson_min: Optional[float],
                      require_wilson_p: bool,
                      log: list) -> bool:
    """Run gate checks for a single boost tier; emit per-criterion log lines.
    Returns True if all gates pass. Caller guarantees twr/ewr are non-None.
    """
    twr = train_stats.get("wr_excl_flat")
    tn = train_stats.get("n_win", 0) + train_stats.get("n_loss", 0)
    ewr = test_stats.get("wr_excl_flat")
    en = test_stats.get("n_win", 0) + test_stats.get("n_loss", 0)
    twilson = train_stats.get("wilson_lower_95")
    tp_val = train_stats.get("p_value_vs_50")
    drift = abs(twr - ewr)

    checks = [
        (f"train_wr {twr} >= {thresholds['train_wr_min']}",
         twr >= thresholds["train_wr_min"]),
        (f"train_n {tn} >= {thresholds['train_n_min']}",
         tn >= thresholds["train_n_min"]),
        (f"test_wr {ewr} >= {thresholds['test_wr_min']}",
         ewr >= thresholds["test_wr_min"]),
        (f"test_n {en} >= {thresholds['test_n_min']}",
         en >= thresholds["test_n_min"]),
        (f"drift {round(drift, 4)} < {thresholds['drift_max']}",
         drift < thresholds["drift_max"]),
    ]
    if require_wilson_p:
        checks.append((f"train_wilson_lower {twilson} >= {wilson_min}",
                       twilson is not None and twilson >= wilson_min))
        checks.append((f"train_p_value {tp_val} < {_BOOST_P_VALUE_MAX}",
                       tp_val is not None and tp_val < _BOOST_P_VALUE_MAX))

    all_pass = all(passed for _, passed in checks)
    verdict = "PASS" if all_pass else "FAIL"
    log.append(f"Tier {tier_name} BOOST [{verdict}]:")
    for desc, passed in checks:
        log.append(f"  {'✓' if passed else '✗'} {desc}")
    return all_pass


def evaluate_kill_tier(train_stats: dict, test_stats: dict) -> str:
    """Returns 'S' / 'A' / 'B' / 'REJECT' per Gate 3 KILL thresholds."""
    twr = train_stats.get("wr_excl_flat")
    tn = train_stats.get("n_win", 0) + train_stats.get("n_loss", 0)
    ewr = test_stats.get("wr_excl_flat")
    en = test_stats.get("n_win", 0) + test_stats.get("n_loss", 0)

    if twr is None or ewr is None:
        return "REJECT"
    drift = abs(twr - ewr)

    # Tier S
    if (twr <= _KILL_TIER_S["train_wr_max"]
            and tn >= _KILL_TIER_S["train_n_min"]
            and ewr <= _KILL_TIER_S["test_wr_max"]
            and en >= _KILL_TIER_S["test_n_min"]
            and drift < _KILL_TIER_S["drift_max"]):
        return "S"
    # Tier A
    if (twr <= _KILL_TIER_A["train_wr_max"]
            and tn >= _KILL_TIER_A["train_n_min"]
            and ewr <= _KILL_TIER_A["test_wr_max"]
            and en >= _KILL_TIER_A["test_n_min"]
            and drift < _KILL_TIER_A["drift_max"]):
        return "A"
    # Tier B
    if (twr <= _KILL_TIER_B["train_wr_max"]
            and tn >= _KILL_TIER_B["train_n_min"]
            and ewr <= _KILL_TIER_B["test_wr_max"]
            and en >= _KILL_TIER_B["test_n_min"]
            and drift < _KILL_TIER_B["drift_max"]):
        return "B"
    return "REJECT"


# ── Master test_hypothesis ────────────────────────────────────────────

def evaluate_hypothesis(signals_df: pd.DataFrame,
                          cohort_filter: dict,
                          hypothesis_type: str = "BOOST",
                          train_period: tuple = ("2011-01-01", "2022-12-31"),
                          test_period: tuple = ("2023-01-01", "2026-04-30"),
                          date_field: str = "scan_date") -> dict:
    """Master hypothesis tester per PROMOTION_PROTOCOL.md Gate 3.

    Pipeline:
    1. Filter signals_df by cohort_filter
    2. Train/test split chronologically
    3. Compute cohort stats on each split
    4. Evaluate tier per hypothesis_type
    5. Return full report

    Parameters
    ----------
    hypothesis_type : str
        'BOOST' | 'KILL' | 'FILTER' (filter inherits parent boost/kill criteria;
        caller must specify which via parent hypothesis_type semantically.)

    Returns
    -------
    dict
        {hypothesis, cohort, train_period, test_period, train_stats, test_stats,
         drift, tier, decision_log}
    """
    if hypothesis_type not in ("BOOST", "KILL", "FILTER"):
        raise ValueError(f"hypothesis_type must be BOOST/KILL/FILTER; got {hypothesis_type!r}")

    # Apply cohort filter once
    cohort_all = filter_cohort(signals_df, cohort_filter)

    # Split chronologically
    train_df, test_df = train_test_split(
        cohort_all, split_date=train_period[1], date_field=date_field)
    # Further filter train + test to their respective periods
    train_df = _filter_date_range(train_df, train_period[0], train_period[1], date_field)
    test_df = _filter_date_range(test_df, test_period[0], test_period[1], date_field)

    # Compute stats per split (no further cohort filter; already applied)
    train_stats = compute_cohort_stats(train_df, cohort_filter={})
    test_stats = compute_cohort_stats(test_df, cohort_filter={})

    # Evaluate tier — collect per-criterion pass/fail log
    tier_log: list = []
    if hypothesis_type == "BOOST" or hypothesis_type == "FILTER":
        # FILTER inherits BOOST tier criteria by default; caller can call
        # evaluate_kill_tier separately for FILTER on a kill parent
        tier = evaluate_boost_tier(train_stats, test_stats, decision_log=tier_log)
    else:  # KILL
        tier = evaluate_kill_tier(train_stats, test_stats)

    # Drift
    twr = train_stats.get("wr_excl_flat")
    ewr = test_stats.get("wr_excl_flat")
    drift = abs(twr - ewr) if (twr is not None and ewr is not None) else None

    # Decision log: explain WHY this tier was assigned (or REJECT reason)
    decision_log = _build_decision_log(train_stats, test_stats, drift, tier, hypothesis_type)
    if tier_log:
        decision_log.append("--- Per-tier gate evaluation ---")
        decision_log.extend(tier_log)

    return {
        "hypothesis": hypothesis_type,
        "cohort": cohort_filter,
        "train_period": train_period,
        "test_period": test_period,
        "train_stats": train_stats,
        "test_stats": test_stats,
        "drift_pp": round(drift * 100, 2) if drift is not None else None,
        "tier": tier,
        "decision_log": decision_log,
    }


def _filter_date_range(df: pd.DataFrame, start: str, end: str,
                        date_field: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    dates = pd.to_datetime(df[date_field])
    mask = (dates >= pd.to_datetime(start)) & (dates <= pd.to_datetime(end))
    return df[mask].copy()


def _build_decision_log(train_stats: dict, test_stats: dict,
                         drift: Optional[float], tier: str,
                         hypothesis_type: str) -> list[str]:
    """Generate human-readable decision audit trail."""
    log = []
    twr = train_stats.get("wr_excl_flat")
    tn = train_stats.get("n_win", 0) + train_stats.get("n_loss", 0)
    ewr = test_stats.get("wr_excl_flat")
    en = test_stats.get("n_win", 0) + test_stats.get("n_loss", 0)

    log.append(f"Hypothesis type: {hypothesis_type}")
    log.append(f"Train: WR={twr} n={tn} (W={train_stats.get('n_win')} L={train_stats.get('n_loss')})")
    log.append(f"Test:  WR={ewr} n={en} (W={test_stats.get('n_win')} L={test_stats.get('n_loss')})")
    log.append(f"Drift: {drift if drift is None else round(drift, 4)}")
    log.append(f"Wilson lower (train): {train_stats.get('wilson_lower_95')}")
    log.append(f"Wilson lower (test):  {test_stats.get('wilson_lower_95')}")
    log.append(f"p-value vs 50% (train): {train_stats.get('p_value_vs_50')}")
    log.append(f"p-value vs 50% (test):  {test_stats.get('p_value_vs_50')}")
    log.append(f"Tier verdict: {tier}")
    return log
