"""
Phase 5 — Live signal matcher.

For each Phase 4 combination definition, find live signals from
`live_signals_with_features.parquet` that match the combination's cohort
(signal_type × regime) AND all required feature levels, then attribute
outcomes at the combination's horizon.

Live signal outcomes are pre-computed per horizon using `BaselineComputer`
(Phase 3) so D1/D2/D3/D5/D10/D15 outcomes are derivable beyond the default
D6-only `outcome` column in signal_history.

Late-window note: live data spans 2026-04-01 → 2026-04-23. Cache extends
~04-29. D10/D15 outcomes for late signals will INSUFFICIENT — these
combinations will see lower live_n.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_HERE))

from baseline_computer import BaselineComputer  # noqa: E402
from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402
from combination_generator import (  # noqa: E402
    signal_matches_level, _parse_numeric_thresholds,
)


def precompute_live_outcomes(live_df: pd.DataFrame,
                                cache_dir: Path,
                                horizons: list[int]) -> dict[int, pd.DataFrame]:
    """Compute live outcomes per horizon via BaselineComputer.

    Live `live_signals_with_features.parquet` has columns:
      • date (renamed → scan_date for compute)
      • symbol, signal, regime, direction, entry, stop, sector, vol_q, etc.
    Returns dict[horizon] → DataFrame indexed by sig_idx with label/return_pct.
    """
    df = live_df.copy()
    if "scan_date" not in df.columns:
        df["scan_date"] = pd.to_datetime(df["date"])
    bc = BaselineComputer(df, cache_dir=cache_dir, entry_col="entry")
    outcomes_long = bc.compute_outcomes(horizons=horizons,
                                            progress_every=10_000)
    return {
        h: outcomes_long[outcomes_long["horizon"] == h]
            .set_index("sig_idx")[["label", "return_pct"]]
        for h in horizons
    }


@dataclass
class MatchResult:
    """Per-combination live match result."""
    combo_id: str
    horizon: str
    cohort_match_count: int
    live_n: int
    live_n_wins: int
    live_n_losses: int
    live_n_flat: int
    live_wr: Optional[float]
    matched_sample_ids: list  # first 3 IDs (audit trail; full list bloats parquet)


class LiveSignalMatcher:
    """Apply combination predicates to live signals + attribute outcomes."""

    def __init__(self, live_df: pd.DataFrame,
                 outcomes_by_horizon: dict[int, pd.DataFrame],
                 registry: FeatureRegistry):
        self.live_df = live_df.copy()
        if "scan_date" not in self.live_df.columns:
            self.live_df["scan_date"] = pd.to_datetime(self.live_df["date"])
        self.outcomes_by_h = outcomes_by_horizon
        self.spec_by_id = {s.feature_id: s for s in registry.list_all()}
        self._bounds_cache: dict = {}

    def match_combination(self, combo_row: dict) -> MatchResult:
        """Match one combination to live data; return MatchResult."""
        sig_type = combo_row["signal_type"]
        regime = combo_row["regime"]
        horizon = combo_row["horizon"]
        horizon_int = int(horizon[1:])

        cohort_signals = self.live_df[
            (self.live_df["signal"] == sig_type)
            & (self.live_df["regime"] == regime)
        ]
        cohort_n = len(cohort_signals)

        # Build feature-level predicate from combo_row's feature_a..d slots
        feature_levels = []
        for slot in ("a", "b", "c", "d"):
            fid = combo_row.get(f"feature_{slot}_id")
            lvl = combo_row.get(f"feature_{slot}_level")
            if pd.notna(fid) and pd.notna(lvl):
                feature_levels.append((fid, lvl))

        if not feature_levels or cohort_n == 0:
            return MatchResult(
                combo_id=combo_row["combo_id"],
                horizon=horizon,
                cohort_match_count=cohort_n,
                live_n=0, live_n_wins=0, live_n_losses=0, live_n_flat=0,
                live_wr=None, matched_sample_ids=[],
            )

        # Apply feature-level mask
        masks = []
        for fid, lvl in feature_levels:
            spec = self.spec_by_id.get(fid)
            if spec is None:
                return self._empty_result(combo_row, cohort_n)
            col = _FEAT_PREFIX + fid
            if col not in cohort_signals.columns:
                return self._empty_result(combo_row, cohort_n)
            m = signal_matches_level(spec, cohort_signals[col], lvl,
                                       self._bounds_cache)
            # NaN feature value → does NOT match (defensive, matches Phase 4)
            masks.append(m.fillna(False))

        combined_mask = masks[0]
        for m in masks[1:]:
            combined_mask = combined_mask & m
        matched = cohort_signals[combined_mask]

        # Attribute outcomes at horizon
        outcomes_h = self.outcomes_by_h.get(horizon_int)
        if outcomes_h is None or len(matched) == 0:
            sample_ids = matched["id"].head(3).tolist() if "id" in matched.columns else []
            return MatchResult(
                combo_id=combo_row["combo_id"],
                horizon=horizon,
                cohort_match_count=cohort_n,
                live_n=0, live_n_wins=0, live_n_losses=0, live_n_flat=0,
                live_wr=None, matched_sample_ids=sample_ids,
            )

        idx_intersect = matched.index.intersection(outcomes_h.index)
        sub = outcomes_h.loc[idx_intersect]
        valid = sub[sub["label"].isin(["W", "L", "F"])]
        n = len(valid)
        n_w = int((valid["label"] == "W").sum())
        n_l = int((valid["label"] == "L").sum())
        n_f = int((valid["label"] == "F").sum())
        n_wl = n_w + n_l
        wr = (n_w / n_wl) if n_wl > 0 else None

        sample_ids = matched.loc[idx_intersect, "id"].head(3).tolist() if "id" in matched.columns else []

        return MatchResult(
            combo_id=combo_row["combo_id"],
            horizon=horizon,
            cohort_match_count=cohort_n,
            live_n=n, live_n_wins=n_w, live_n_losses=n_l, live_n_flat=n_f,
            live_wr=wr, matched_sample_ids=sample_ids,
        )

    def _empty_result(self, combo_row: dict, cohort_n: int) -> MatchResult:
        return MatchResult(
            combo_id=combo_row["combo_id"],
            horizon=combo_row["horizon"],
            cohort_match_count=cohort_n,
            live_n=0, live_n_wins=0, live_n_losses=0, live_n_flat=0,
            live_wr=None, matched_sample_ids=[],
        )
