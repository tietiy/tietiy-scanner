"""
Tests for choppy_uptri/filter_test.py.

Run:
    .venv/bin/python -m pytest lab/factory/choppy_uptri/test_filter.py -v
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
    bounds = _parse_numeric_thresholds(th)
    assert bounds == (0.3, 0.7)


def test_parse_numeric_thresholds_missing():
    th = {"low": None, "medium": None, "high": None}
    assert _parse_numeric_thresholds(th) is None


def test_matches_level_categorical():
    reg = FeatureRegistry.load_all()
    spec = reg.get("ema_alignment")
    assert matches_level(spec, "bull", "bull") is True
    assert matches_level(spec, "mixed", "bull") is False


def test_matches_level_numeric():
    """coiled_spring_score: low <33, medium 33-67, high >67."""
    reg = FeatureRegistry.load_all()
    spec = reg.get("coiled_spring_score")
    assert matches_level(spec, 25, "low") is True
    assert matches_level(spec, 25, "medium") is False
    assert matches_level(spec, 50, "medium") is True
    assert matches_level(spec, 50, "low") is False
    assert matches_level(spec, 80, "high") is True
    assert matches_level(spec, 80, "medium") is False


def test_matches_level_handles_nan():
    reg = FeatureRegistry.load_all()
    spec = reg.get("coiled_spring_score")
    assert matches_level(spec, float("nan"), "low") is False
    assert matches_level(spec, float("nan"), "medium") is False


def test_apply_filter_basic():
    """1-feature filter: signal matches if ema_alignment=bull."""
    df = pd.DataFrame({
        "feat_ema_alignment": ["bull", "mixed", "bull", "bear"],
        "feat_coiled_spring_score": [50, 25, 80, 30],
    })
    reg = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    mask = apply_filter(df, [("ema_alignment", "bull")], [],
                            spec_by_id, {})
    assert mask.tolist() == [True, False, True, False]


def test_apply_filter_with_forbidden():
    """ema_alignment=bull AND NOT coiled_spring_score=high."""
    df = pd.DataFrame({
        "feat_ema_alignment": ["bull", "bull", "bull", "mixed"],
        "feat_coiled_spring_score": [50, 80, 25, 25],
    })
    reg = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    mask = apply_filter(df, [("ema_alignment", "bull")],
                            [("coiled_spring_score", "high")],
                            spec_by_id, {})
    # 1st (bull, 50=medium): True; 2nd (bull, 80=high) excluded; 3rd
    # (bull, 25=low): True; 4th (mixed): False
    assert mask.tolist() == [True, False, True, False]


def test_evaluate_filter_returns_required_fields():
    df = pd.DataFrame({
        "feat_ema_alignment": ["bull", "bull", "mixed", "mixed"],
        "feat_coiled_spring_score": [50, 25, 50, 80],
        "wlf": ["W", "W", "L", "L"],
    })
    reg = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in reg.list_all()}
    result = evaluate_filter(df, "test", [("ema_alignment", "bull")], [],
                                  spec_by_id, {})
    for k in ("name", "required", "n_matched", "n_skipped",
              "matched_wr", "skipped_wr", "match_rate"):
        assert k in result
    assert result["n_matched"] == 2
    assert result["n_skipped"] == 2
    assert result["matched_wr"] == 1.0
    assert result["skipped_wr"] == 0.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
