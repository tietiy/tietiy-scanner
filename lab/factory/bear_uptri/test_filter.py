"""
Tests for bear_uptri/filter_test.py.

Run:
    .venv/bin/python -m pytest lab/factory/bear_uptri/test_filter.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_HERE))

from feature_loader import FeatureRegistry  # noqa: E402
from filter_test import (  # noqa: E402
    matches_level, apply_filter, evaluate_filter,
    _parse_numeric_thresholds,
)


def test_parse_numeric_thresholds_typical():
    th = {"low": "<0.3", "medium": "0.3-0.7", "high": ">0.7"}
    assert _parse_numeric_thresholds(th) == (0.3, 0.7)


def test_parse_numeric_thresholds_missing():
    th = {"low": None, "high": None}
    assert _parse_numeric_thresholds(th) is None


def test_matches_level_nifty_60d_return():
    """nifty_60d_return_pct: low <-0.05, medium -0.05..0.05, high >0.05."""
    reg = FeatureRegistry.load_all()
    spec = reg.get("nifty_60d_return_pct")
    # Confirm thresholds parse cleanly
    bounds = _parse_numeric_thresholds(spec.level_thresholds)
    assert bounds is not None
    low_b, high_b = bounds
    # low matches values below low_b
    assert matches_level(spec, low_b - 0.001, "low") is True
    assert matches_level(spec, high_b + 0.001, "high") is True
    # medium = inclusive band
    assert matches_level(spec, (low_b + high_b) / 2, "medium") is True


def test_matches_level_inside_bar_flag_bool():
    reg = FeatureRegistry.load_all()
    spec = reg.get("inside_bar_flag")
    assert matches_level(spec, True, "True") is True
    assert matches_level(spec, False, "True") is False
    assert matches_level(spec, True, "False") is False


def test_apply_filter_nifty_anchor():
    """Filter requires nifty_60d_return_pct=low."""
    reg = FeatureRegistry.load_all()
    spec = reg.get("nifty_60d_return_pct")
    bounds = _parse_numeric_thresholds(spec.level_thresholds)
    low_b, _ = bounds
    df = pd.DataFrame({
        "feat_nifty_60d_return_pct": [low_b - 0.05, low_b + 0.001, low_b - 0.10, 0.10],
    })
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    mask = apply_filter(df, [("nifty_60d_return_pct", "low")], [],
                            spec_by_id, {})
    # rows 0 and 2 are below low_b (low); row 1 is just above; row 3 is high
    assert mask.tolist() == [True, False, True, False]


def test_apply_filter_with_forbidden_wk4():
    df = pd.DataFrame({
        "feat_inside_bar_flag": [True, True, True, False],
        "feat_day_of_month_bucket": ["wk1", "wk4", "wk2", "wk1"],
    })
    reg = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    mask = apply_filter(df, [("inside_bar_flag", "True")],
                            [("day_of_month_bucket", "wk4")],
                            spec_by_id, {})
    # row 1 fails forbidden; row 3 fails required
    assert mask.tolist() == [True, False, True, False]


def test_evaluate_filter_returns_required_fields():
    df = pd.DataFrame({
        "feat_inside_bar_flag": [True, True, False, False],
        "wlf": ["W", "W", "L", "L"],
    })
    reg = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    result = evaluate_filter(df, "test", [("inside_bar_flag", "True")], [],
                                  spec_by_id, {})
    for k in ("name", "n_matched", "n_skipped", "matched_wr", "skipped_wr",
              "match_rate"):
        assert k in result
    assert result["n_matched"] == 2
    assert result["n_skipped"] == 2
    assert result["matched_wr"] == 1.0
    assert result["skipped_wr"] == 0.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
