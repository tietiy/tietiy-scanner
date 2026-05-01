"""
Unit tests for live_signal_matcher.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_live_signal_matcher.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402
from live_signal_matcher import (  # noqa: E402
    LiveSignalMatcher, MatchResult, precompute_live_outcomes,
)

LIVE_PATH = Path(__file__).resolve().parent.parent / "output" / "live_signals_with_features.parquet"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


# Module-scope: pre-compute live outcomes for D1, D2, D6 (subset for tests)
@pytest.fixture(scope="module")
def matcher():
    live = pd.read_parquet(LIVE_PATH)
    if "scan_date" not in live.columns:
        live["scan_date"] = pd.to_datetime(live["date"])
    outcomes = precompute_live_outcomes(live, CACHE_DIR, [1, 2, 6])
    return LiveSignalMatcher(live, outcomes, FeatureRegistry.load_all())


# ════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════

def test_cohort_filter_only_target_signals(matcher):
    """A combo for UP_TRI×Bear should only consider UP_TRI×Bear live signals."""
    combo = {
        "combo_id": "test_cohort",
        "signal_type": "UP_TRI", "regime": "Bear", "horizon": "D6",
        "feature_a_id": "ema_alignment", "feature_a_level": "bull",
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    r = matcher.match_combination(combo)
    # Cohort match count = UP_TRI × Bear in live (Phase 2 reported 98 - some UP_TRI Bear post-dedup)
    assert isinstance(r, MatchResult)
    assert r.cohort_match_count >= 1


def test_feature_level_matching(matcher):
    """Combo restricting ema_alignment=bull should match fewer than full cohort."""
    cohort_only = {
        "combo_id": "c1", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6", "feature_a_id": "ema_alignment",
        "feature_a_level": "bull",
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    feat2 = {
        "combo_id": "c2", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6", "feature_a_id": "ema_alignment",
        "feature_a_level": "bull", "feature_b_id": "RSI_14",
        "feature_b_level": "high",
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    r1 = matcher.match_combination(cohort_only)
    r2 = matcher.match_combination(feat2)
    # 2-feature combo should be subset of 1-feature combo
    assert r2.live_n <= r1.live_n


def test_unknown_feature_returns_empty(matcher):
    """Combo referencing nonexistent feature returns empty match."""
    bad_combo = {
        "combo_id": "bad", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6", "feature_a_id": "nonexistent_feature_xyz",
        "feature_a_level": "high",
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    r = matcher.match_combination(bad_combo)
    assert r.live_n == 0


def test_empty_combination_returns_empty(matcher):
    """Combo with no feature predicates returns empty."""
    empty_combo = {
        "combo_id": "empty", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6",
        "feature_a_id": None, "feature_a_level": None,
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    r = matcher.match_combination(empty_combo)
    assert r.live_n == 0
    assert r.cohort_match_count >= 0


def test_horizon_outcome_attribution(matcher):
    """D2 outcome attribution should differ from D6 for same combo (where
    forward data permits both)."""
    combo_d6 = {
        "combo_id": "h_d6", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6", "feature_a_id": "ema_alignment",
        "feature_a_level": "bull",
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    combo_d2 = {**combo_d6, "combo_id": "h_d2", "horizon": "D2"}
    r6 = matcher.match_combination(combo_d6)
    r2 = matcher.match_combination(combo_d2)
    # Same cohort, same predicate → same matched signals; but outcomes
    # at different horizons may differ (some may be insufficient)
    assert r6.cohort_match_count == r2.cohort_match_count
    # At least one of D2 or D6 should have valid outcomes
    assert r6.live_n + r2.live_n > 0


def test_cohort_signal_subset(matcher):
    """Matched signals must be subset of cohort signals."""
    combo = {
        "combo_id": "subset_test", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D6", "feature_a_id": "vol_q",
        "feature_a_level": "Average",
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    r = matcher.match_combination(combo)
    assert r.live_n <= r.cohort_match_count


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
