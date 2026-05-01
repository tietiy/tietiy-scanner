"""
Unit tests for analyzer/pattern_unifier.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_pattern_unifier.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pattern_unifier import (  # noqa: E402
    UnifiedPattern, jaccard, combo_feature_set, unify_combinations,
    UnionFind, JACCARD_THRESHOLD, _pattern_id,
)


# ── jaccard ───────────────────────────────────────────────────────────

def test_jaccard_identical():
    a = frozenset([("f1", "high"), ("f2", "low")])
    assert jaccard(a, a) == 1.0


def test_jaccard_disjoint():
    a = frozenset([("f1", "high")])
    b = frozenset([("f2", "low")])
    assert jaccard(a, b) == 0.0


def test_jaccard_partial_overlap():
    """Two 2-feature combos sharing 1 feature: 1/3 (below 0.6 threshold)."""
    a = frozenset([("f1", "high"), ("f2", "low")])
    b = frozenset([("f1", "high"), ("f3", "med")])
    assert abs(jaccard(a, b) - 1 / 3) < 1e-9


def test_jaccard_2_3_overlap():
    """1-feature ⊂ 2-feature: 1/2."""
    a = frozenset([("f1", "high")])
    b = frozenset([("f1", "high"), ("f2", "low")])
    assert abs(jaccard(a, b) - 0.5) < 1e-9


def test_jaccard_3_2_overlap():
    """2-feature core ⊂ 3-feature: 2/3 (above 0.6 threshold)."""
    a = frozenset([("f1", "high"), ("f2", "low")])
    b = frozenset([("f1", "high"), ("f2", "low"), ("f3", "med")])
    assert abs(jaccard(a, b) - 2 / 3) < 1e-9
    assert jaccard(a, b) >= JACCARD_THRESHOLD


# ── combo_feature_set ────────────────────────────────────────────────

def test_combo_feature_set_extracts_all_slots():
    row = {
        "feature_a_id": "f1", "feature_a_level": "high",
        "feature_b_id": "f2", "feature_b_level": "low",
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    s = combo_feature_set(row)
    assert ("f1", "high") in s and ("f2", "low") in s
    assert len(s) == 2


def test_combo_feature_set_handles_nan():
    row = {
        "feature_a_id": "f1", "feature_a_level": "high",
        "feature_b_id": float("nan"), "feature_b_level": float("nan"),
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    s = combo_feature_set(row)
    assert s == frozenset([("f1", "high")])


# ── UnionFind ────────────────────────────────────────────────────────

def test_union_find_basic():
    uf = UnionFind(5)
    uf.union(0, 1)
    uf.union(2, 3)
    assert uf.find(0) == uf.find(1)
    assert uf.find(2) == uf.find(3)
    assert uf.find(0) != uf.find(2)
    uf.union(1, 2)  # transitive merge
    assert uf.find(0) == uf.find(3)


# ── unify_combinations end-to-end ────────────────────────────────────

def _make_combo_row(combo_id, signal_type, regime, horizon, features,
                       test_wr, baseline_wr, tier="A"):
    """Build a fake combinations_lifetime row."""
    row = {
        "combo_id": combo_id,
        "signal_type": signal_type, "regime": regime, "horizon": horizon,
        "feature_count": len(features),
        "test_wr": test_wr, "baseline_wr": baseline_wr,
        "tier": tier,
        "feature_a_id": None, "feature_a_level": None,
        "feature_b_id": None, "feature_b_level": None,
        "feature_c_id": None, "feature_c_level": None,
        "feature_d_id": None, "feature_d_level": None,
    }
    for i, (fid, lvl) in enumerate(features[:4]):
        slot = chr(ord("a") + i)
        row[f"feature_{slot}_id"] = fid
        row[f"feature_{slot}_level"] = lvl
    return row


def test_transitive_clustering_4_variant_case():
    """BULL_PROXY-style example: anchor (a,b) connects (a,b,c)/(a,b,d)/(a,b,e)
    via 0.667 Jaccard each; the 3-feature variants only share 0.5 with each
    other but should still cluster transitively."""
    rows = [
        _make_combo_row("anchor", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y")], 0.70, 0.50),
        _make_combo_row("v1", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y"), ("c", "z")], 0.68, 0.50),
        _make_combo_row("v2", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y"), ("d", "z")], 0.68, 0.50),
        _make_combo_row("v3", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y"), ("e", "z")], 0.68, 0.50),
    ]
    df = pd.DataFrame(rows)
    patterns = unify_combinations(df)
    assert len(patterns) == 1, f"expected 1 unified pattern, got {len(patterns)}"
    p = patterns[0]
    assert p.cluster_size == 4
    # Anchor should be the broadest (2-feature) variant
    assert p.anchor_combo_id == "anchor"
    assert p.feature_count == 2


def test_anchor_picks_broader_pattern():
    """When test_wr ties, smaller feature_count wins (broader pattern)."""
    rows = [
        _make_combo_row("c2feat", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y")], 0.70, 0.50, tier="A"),
        _make_combo_row("c3feat", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y"), ("c", "z")], 0.70, 0.50, tier="A"),
    ]
    df = pd.DataFrame(rows)
    patterns = unify_combinations(df)
    assert len(patterns) == 1
    assert patterns[0].anchor_combo_id == "c2feat"


def test_cohort_isolation():
    """Same features in different cohorts should NOT cluster together."""
    rows = [
        _make_combo_row("bear_combo", "UP_TRI", "Bear", "D10",
                          [("a", "x"), ("b", "y")], 0.70, 0.50),
        _make_combo_row("bull_combo", "UP_TRI", "Bull", "D10",
                          [("a", "x"), ("b", "y")], 0.65, 0.51),
        _make_combo_row("choppy_combo", "UP_TRI", "Choppy", "D6",
                          [("a", "x"), ("b", "y")], 0.62, 0.49),
    ]
    df = pd.DataFrame(rows)
    patterns = unify_combinations(df)
    assert len(patterns) == 3, "different cohorts should not merge"


def test_level_differentiation():
    """Same feature_id but different levels should NOT cluster."""
    rows = [
        _make_combo_row("level_high", "UP_TRI", "Bear", "D10",
                          [("a", "high"), ("b", "low")], 0.70, 0.50),
        _make_combo_row("level_low", "UP_TRI", "Bear", "D10",
                          [("a", "low"), ("b", "high")], 0.65, 0.50),
    ]
    df = pd.DataFrame(rows)
    patterns = unify_combinations(df)
    # No shared (feature_id, level) tuples → Jaccard = 0 → 2 separate patterns
    assert len(patterns) == 2


def test_pattern_id_stable():
    """Same cohort + features → same pattern_id; different → different."""
    cohort_a = ("UP_TRI", "Bear", "D10")
    feats_a = [("ema_alignment", "bull"), ("RSI_14", "high")]
    feats_a_reordered = [("RSI_14", "high"), ("ema_alignment", "bull")]
    feats_b = [("ema_alignment", "bear"), ("RSI_14", "high")]
    pid_a = _pattern_id(cohort_a, feats_a)
    pid_a_re = _pattern_id(cohort_a, feats_a_reordered)
    pid_b = _pattern_id(cohort_a, feats_b)
    assert pid_a == pid_a_re
    assert pid_a != pid_b


def test_unify_missing_column_raises():
    df = pd.DataFrame([{
        "combo_id": "x", "signal_type": "UP_TRI", "regime": "Bear",
        "horizon": "D10", "feature_count": 1,
        # missing test_wr / baseline_wr / tier
    }])
    with pytest.raises(ValueError, match="missing required column"):
        unify_combinations(df)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
