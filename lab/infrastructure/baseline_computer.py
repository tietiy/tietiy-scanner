"""
Baseline computer — universe baseline WR per (signal_type × regime × horizon).

Phase 3 prereq per `lab/COMBINATION_ENGINE_PLAN.md`. NO production scanner
modifications. Lab-only.

For each cohort × horizon, computes unconditional WR + statistical confidence
(Wilson 95% interval + binomial p-value vs 50% null).

Outcome derivation: walks forward N trading days from scan_date through the
stock's cached parquet OHLC. Stop-out detection uses daily Low (LONG) / High
(SHORT) breach. If stop not hit, exit at horizon close. Return computed with
direction sign applied. Flat threshold |return| < 0.001 (0.1%) excludes
near-zero outcomes from W/L counts.

Usage:
    from baseline_computer import BaselineComputer
    bc = BaselineComputer(signals_df, cache_dir)
    outcomes = bc.compute_outcomes(horizons=[1,2,3,5,6,8,10,15,20])
    baselines = bc.aggregate(outcomes)
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent

# ── Constants ─────────────────────────────────────────────────────────
DEFAULT_CACHE_DIR = _LAB_ROOT / "cache"
DEFAULT_HORIZONS = (1, 2, 3, 5, 6, 8, 10, 15, 20)

# Flat threshold: |return| below this counts as F (excluded from WR)
FLAT_THRESHOLD = 0.001

# Confidence-tier sample-size cuts
N_HIGH_CONFIDENCE = 100
N_LOW_CONFIDENCE = 30


def _symbol_to_parquet(symbol: str) -> str:
    return symbol.replace(".NS", "_NS").replace(".BO", "_BO") + ".parquet"


# ── Stat helpers ──────────────────────────────────────────────────────

def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Returns (lower, upper).

    Per Wikipedia 'Binomial proportion confidence interval' formula. Robust
    for small n (better than normal approximation).
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def binomial_p_two_sided(k: int, n: int, p_null: float = 0.5) -> float:
    """Two-sided binomial test p-value: P(|X - n*p_null| >= |k - n*p_null|).

    Uses scipy if available; falls back to manual normal approximation for
    large n. Returns 1.0 if n == 0.
    """
    if n == 0:
        return 1.0
    try:
        from scipy import stats
        # binomtest available scipy >= 1.7
        try:
            res = stats.binomtest(k, n, p=p_null, alternative="two-sided")
            return float(res.pvalue)
        except AttributeError:
            return float(stats.binom_test(k, n, p=p_null, alternative="two-sided"))
    except ImportError:
        # Normal approximation (z-test)
        mu = n * p_null
        sigma = math.sqrt(n * p_null * (1 - p_null))
        if sigma == 0:
            return 1.0
        z = abs(k - mu) / sigma
        # Two-sided
        from math import erfc
        return float(erfc(z / math.sqrt(2)))


def confidence_tier(n: int) -> str:
    if n >= N_HIGH_CONFIDENCE:
        return "high"
    if n >= N_LOW_CONFIDENCE:
        return "low"
    return "too_low"


# ── Per-signal outcome computation ────────────────────────────────────

@dataclass
class SignalOutcome:
    """Outcome of one (signal, horizon) combination."""
    label: str  # "W", "L", "F", "INSUFFICIENT", "NO_DATA"
    return_pct: Optional[float]
    exit_type: str  # "STOP_HIT", "HORIZON_CLOSE", or "INSUFFICIENT"
    exit_day: Optional[int]


def compute_signal_outcome(stock_ohlcv: pd.DataFrame,
                              scan_date: pd.Timestamp,
                              entry_price: float,
                              stop: float,
                              direction: str,
                              horizon_days: int,
                              flat_threshold: float = FLAT_THRESHOLD) -> SignalOutcome:
    """Walk forward `horizon_days` trading days from scan_date in the stock's
    cached OHLCV. Apply stop-out logic. Return labeled outcome.

    Direction: 'LONG' means we profit when price rises; 'SHORT' means we profit
    when price falls. Stop is a fixed price level (not a % offset).
    """
    if pd.isna(entry_price) or entry_price <= 0:
        return SignalOutcome("NO_DATA", None, "NO_DATA", None)

    # Slice forward window: trading days STRICTLY after scan_date
    forward = stock_ohlcv.loc[stock_ohlcv.index > scan_date]
    if len(forward) < horizon_days:
        return SignalOutcome("INSUFFICIENT", None, "INSUFFICIENT", None)

    window = forward.iloc[:horizon_days]

    # Stop-out detection (daily granularity)
    stop_hit_day = None
    if direction == "LONG":
        if not pd.isna(stop) and stop > 0:
            breach = (window["Low"].values <= stop)
            if breach.any():
                stop_hit_day = int(np.argmax(breach)) + 1  # 1-indexed
    else:  # SHORT
        if not pd.isna(stop) and stop > 0:
            breach = (window["High"].values >= stop)
            if breach.any():
                stop_hit_day = int(np.argmax(breach)) + 1

    if stop_hit_day is not None:
        exit_price = float(stop)
        exit_type = "STOP_HIT"
        exit_day = stop_hit_day
    else:
        exit_price = float(window["Close"].iloc[-1])
        exit_type = "HORIZON_CLOSE"
        exit_day = horizon_days

    if direction == "LONG":
        return_pct = (exit_price - entry_price) / entry_price
    else:  # SHORT
        return_pct = (entry_price - exit_price) / entry_price

    if exit_type == "STOP_HIT":
        # Stop-outs are losses by definition (entry direction adverse to stop)
        label = "L"
    elif return_pct > flat_threshold:
        label = "W"
    elif return_pct < -flat_threshold:
        label = "L"
    else:
        label = "F"

    return SignalOutcome(label, float(return_pct), exit_type, exit_day)


# ── BaselineComputer driver ───────────────────────────────────────────

class BaselineComputer:
    """Drives outcome computation across (signal × horizon) and aggregation
    per cohort × horizon."""

    def __init__(self, signals_df: pd.DataFrame,
                 cache_dir: Path = DEFAULT_CACHE_DIR,
                 entry_col: str = "entry_price"):
        self.signals = signals_df.copy()
        # Ensure scan_date is Timestamp
        self.signals["scan_date"] = pd.to_datetime(self.signals["scan_date"])
        self.cache_dir = Path(cache_dir)
        self.entry_col = entry_col
        self._stock_cache: dict[str, Optional[pd.DataFrame]] = {}

    def _load_stock(self, symbol: str) -> Optional[pd.DataFrame]:
        if symbol not in self._stock_cache:
            path = self.cache_dir / _symbol_to_parquet(symbol)
            if not path.exists():
                self._stock_cache[symbol] = None
            else:
                try:
                    df = pd.read_parquet(path)
                    df.index = pd.to_datetime(df.index)
                    df = df.sort_index().dropna(subset=["Close"])
                    self._stock_cache[symbol] = df
                except Exception:
                    self._stock_cache[symbol] = None
        return self._stock_cache[symbol]

    def compute_outcomes(self,
                            horizons: Iterable[int] = DEFAULT_HORIZONS,
                            progress_every: int = 10_000) -> pd.DataFrame:
        """Compute outcomes for every (signal × horizon) combination.

        Returns DataFrame with columns:
            sig_idx, signal, regime, horizon, label, return_pct,
            exit_type, exit_day
        """
        horizons_list = list(horizons)
        rows = []
        n_total = len(self.signals)
        n_processed = 0
        next_progress = progress_every

        # Group by symbol for cache efficiency
        for symbol, group in self.signals.groupby("symbol", sort=False):
            stock = self._load_stock(symbol)
            for idx, sig in group.iterrows():
                if stock is None:
                    for h in horizons_list:
                        rows.append({
                            "sig_idx": idx, "signal": sig.get("signal"),
                            "regime": sig.get("regime"), "horizon": h,
                            "label": "NO_DATA", "return_pct": None,
                            "exit_type": "NO_DATA", "exit_day": None,
                        })
                    n_processed += 1
                    continue

                entry_price = sig.get(self.entry_col)
                stop = sig.get("stop")
                direction = sig.get("direction", "LONG")
                scan_date = sig["scan_date"]

                for h in horizons_list:
                    o = compute_signal_outcome(
                        stock, scan_date, entry_price, stop, direction, h)
                    rows.append({
                        "sig_idx": idx,
                        "signal": sig.get("signal"),
                        "regime": sig.get("regime"),
                        "horizon": h,
                        "label": o.label,
                        "return_pct": o.return_pct,
                        "exit_type": o.exit_type,
                        "exit_day": o.exit_day,
                    })

                n_processed += 1
                if n_processed >= next_progress:
                    pct = 100 * n_processed / n_total
                    print(f"  {n_processed:>7}/{n_total} signals "
                          f"({pct:.1f}%) outcomes computed",
                          file=sys.stderr)
                    next_progress += progress_every

        return pd.DataFrame(rows)

    @staticmethod
    def aggregate(outcomes: pd.DataFrame) -> dict:
        """Aggregate per (signal × regime × horizon) into baseline stats."""
        result: dict = {"cohorts": {}, "validation": {
            "cells_total": 0, "cells_high_confidence": 0,
            "cells_low_confidence": 0, "cells_too_low": 0,
            "cells_skipped_insufficient_n": 0,
        }}
        # Filter to W/L/F (exclude INSUFFICIENT/NO_DATA from cell denominators)
        valid = outcomes[outcomes["label"].isin(["W", "L", "F"])].copy()

        signal_types = sorted(valid["signal"].dropna().unique())
        regimes = sorted(valid["regime"].dropna().unique())
        horizons = sorted(valid["horizon"].unique())

        for sig_type in signal_types:
            result["cohorts"][sig_type] = {}
            for regime in regimes:
                result["cohorts"][sig_type][regime] = {}
                for h in horizons:
                    cell = valid[(valid["signal"] == sig_type)
                                  & (valid["regime"] == regime)
                                  & (valid["horizon"] == h)]
                    n = len(cell)
                    n_w = int((cell["label"] == "W").sum())
                    n_l = int((cell["label"] == "L").sum())
                    n_f = int((cell["label"] == "F").sum())
                    n_wl = n_w + n_l
                    if n_wl < 10:
                        # Too few resolved outcomes; mark and skip stats
                        result["validation"]["cells_skipped_insufficient_n"] += 1
                        result["cohorts"][sig_type][regime][f"D{h}"] = {
                            "n": n, "n_wins": n_w, "n_losses": n_l,
                            "n_flat": n_f,
                            "wr": None, "wilson_lower_95": None,
                            "wilson_upper_95": None, "p_value_vs_50": None,
                            "median_return_pct": None, "avg_return_pct": None,
                            "std_return_pct": None,
                            "max_drawdown_in_trade_pct": None,
                            "confidence": "too_low",
                        }
                        continue
                    wr = n_w / n_wl
                    wl, wu = wilson_interval(n_w, n_wl)
                    p = binomial_p_two_sided(n_w, n_wl, 0.5)
                    rets = cell["return_pct"].dropna()
                    cell_stats = {
                        "n": n,
                        "n_wins": n_w,
                        "n_losses": n_l,
                        "n_flat": n_f,
                        "wr": float(wr),
                        "wilson_lower_95": float(wl),
                        "wilson_upper_95": float(wu),
                        "p_value_vs_50": float(p),
                        "median_return_pct": (float(rets.median())
                                                if len(rets) else None),
                        "avg_return_pct": (float(rets.mean())
                                              if len(rets) else None),
                        "std_return_pct": (float(rets.std())
                                              if len(rets) > 1 else None),
                        # max_drawdown_in_trade_pct: optional Phase 3 extra;
                        # not computable from horizon-close-only outcomes
                        # (would need bar-level MFE/MAE per signal). Left None.
                        "max_drawdown_in_trade_pct": None,
                        "confidence": confidence_tier(n_wl),
                    }
                    result["cohorts"][sig_type][regime][f"D{h}"] = cell_stats
                    result["validation"]["cells_total"] += 1
                    if cell_stats["confidence"] == "high":
                        result["validation"]["cells_high_confidence"] += 1
                    elif cell_stats["confidence"] == "low":
                        result["validation"]["cells_low_confidence"] += 1
                    else:
                        result["validation"]["cells_too_low"] += 1
        return result
