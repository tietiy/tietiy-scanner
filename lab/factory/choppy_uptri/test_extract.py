"""
Tests for choppy_uptri/extract.py.

Run:
    .venv/bin/python -m pytest lab/factory/choppy_uptri/test_extract.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract import (  # noqa: E402
    load_choppy_uptri, descriptive_stats, build_comparison_stats, GROUPS,
)


def test_load_filters_to_choppy_uptri():
    df = load_choppy_uptri()
    assert (df["signal_type"] == "UP_TRI").all()
    assert (df["regime"] == "Choppy").all()
    assert len(df) > 0


def test_load_includes_both_horizons():
    df = load_choppy_uptri()
    horizons = set(df["horizon"].unique())
    assert "D5" in horizons
    assert "D6" in horizons


def test_descriptive_stats_handles_empty_group():
    empty = pd.DataFrame()
    s = descriptive_stats(empty)
    assert s == {"count": 0}


def test_descriptive_stats_returns_required_keys():
    df = load_choppy_uptri()
    val = df[df["live_tier"] == "VALIDATED"]
    s = descriptive_stats(val)
    assert "count" in s
    assert "lifetime" in s
    assert "live" in s
    assert "horizon_distribution" in s
    assert "phase_4_tier_distribution" in s
    assert s["count"] > 0


def test_build_comparison_stats_has_all_4_groups():
    stats = build_comparison_stats()
    for g in GROUPS:
        assert g in stats["groups"]


def test_winners_minimum_count():
    """Per HALT condition: V+P should be ≥20."""
    stats = build_comparison_stats()
    val_n = stats["groups"]["VALIDATED"]["count"]
    pre_n = stats["groups"]["PRELIMINARY"]["count"]
    assert val_n + pre_n >= 20, (
        f"V+P={val_n+pre_n} below HALT threshold 20")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
