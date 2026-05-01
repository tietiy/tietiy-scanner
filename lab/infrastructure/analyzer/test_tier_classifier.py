"""
Unit tests for analyzer/tier_classifier.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_tier_classifier.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier_classifier import (  # noqa: E402
    classify_pattern, classify_all,
    SCORE_ACTIVE_FULL, SCORE_ACTIVE_SMALL, SCORE_ACTIVE_WATCH, SCORE_CANDIDATE,
    KILL_FEATURE_IDS,
)


def _build_ev(regime="Bear", live_avail=True, live_tier="VALIDATED",
                  live_n=10, features=None):
    return {
        "cohort": {"regime": regime},
        "live_evidence": {"available": live_avail, "phase_5_tier": live_tier,
                              "live_n": live_n},
        "features": features or [{"feature_id": "ema_alignment", "level": "bull"}],
    }


# ── Score-based primary tier ─────────────────────────────────────────

def test_score_85_active_take_full():
    r = classify_pattern(_build_ev(), 85)
    assert r["tier"] == "ACTIVE_TAKE_FULL"


def test_score_70_active_take_small():
    r = classify_pattern(_build_ev(), 70)
    assert r["tier"] == "ACTIVE_TAKE_SMALL"


def test_score_55_active_watch():
    r = classify_pattern(_build_ev(), 55)
    assert r["tier"] == "ACTIVE_WATCH"


def test_score_40_candidate():
    r = classify_pattern(_build_ev(), 40)
    assert r["tier"] == "CANDIDATE"
    assert r["override_reason"] is None


def test_score_25_deprecated():
    r = classify_pattern(_build_ev(), 25)
    assert r["tier"] == "DEPRECATED"


# ── KILL override ────────────────────────────────────────────────────

def test_kill_overrides_active():
    """triangle_quality_ascending in evidence → KILL regardless of score."""
    ev = _build_ev(features=[
        {"feature_id": "triangle_quality_ascending", "level": "high"},
        {"feature_id": "ema_alignment", "level": "bull"},
    ])
    r = classify_pattern(ev, 90)
    assert r["tier"] == "KILL"
    assert r["primary_tier"] == "ACTIVE_TAKE_FULL"  # would-have-been
    assert "KILL" in r["override_reason"] or "negative" in r["override_reason"].lower()


def test_kill_overrides_even_low_score():
    ev = _build_ev(features=[
        {"feature_id": "triangle_quality_ascending", "level": "high"}])
    r = classify_pattern(ev, 20)
    assert r["tier"] == "KILL"


# ── DORMANT_REGIME (Bull cohort) ────────────────────────────────────

def test_dormant_regime_for_bull_cohort_no_live():
    ev = _build_ev(regime="Bull", live_avail=False)
    r = classify_pattern(ev, 80)
    assert r["tier"] == "DORMANT_REGIME"
    assert r["primary_tier"] == "ACTIVE_TAKE_FULL"
    assert "Bull" in r["override_reason"]


def test_dormant_regime_only_when_score_above_floor():
    """Score < 50 → no dormant override; just stays as primary tier."""
    ev = _build_ev(regime="Bull", live_avail=False)
    r = classify_pattern(ev, 35)
    assert r["tier"] == "CANDIDATE"
    assert r["override_reason"] is None


# ── DORMANT_DEFERRED (Phase 5 REJECTED) ─────────────────────────────

def test_dormant_deferred_for_rejected_phase5():
    ev = _build_ev(regime="Choppy", live_avail=True, live_tier="REJECTED",
                       live_n=12)
    r = classify_pattern(ev, 75)
    assert r["tier"] == "DORMANT_DEFERRED"
    assert "REJECTED" in r["override_reason"]


def test_dormant_deferred_below_score_floor_no_override():
    ev = _build_ev(regime="Choppy", live_avail=True, live_tier="REJECTED",
                       live_n=12)
    r = classify_pattern(ev, 35)
    assert r["tier"] == "CANDIDATE"


# ── DORMANT_INSUFFICIENT_DATA (live not available, not Bull) ────────

def test_dormant_insufficient_for_no_live():
    """Pattern in Bear cohort but live_n=0 → DORMANT_INSUFFICIENT_DATA."""
    ev = _build_ev(regime="Bear", live_avail=False)
    r = classify_pattern(ev, 80)
    # Bear → not blocked by Bull rule; falls to insufficient_data
    assert r["tier"] == "DORMANT_INSUFFICIENT_DATA"


def test_dormant_insufficient_for_zero_live_n():
    """live_avail=True but live_n=0 → DORMANT_INSUFFICIENT_DATA."""
    ev = _build_ev(regime="Bear", live_avail=True, live_tier="WATCH",
                       live_n=0)
    r = classify_pattern(ev, 80)
    assert r["tier"] == "DORMANT_INSUFFICIENT_DATA"


# ── Override priority order ────────────────────────────────────────

def test_kill_priority_over_dormant():
    """KILL override comes before DORMANT_REGIME even for Bull cohort."""
    ev = _build_ev(regime="Bull", live_avail=False, features=[
        {"feature_id": "triangle_quality_ascending", "level": "high"}])
    r = classify_pattern(ev, 80)
    assert r["tier"] == "KILL"


def test_dormant_regime_priority_over_dormant_deferred():
    """If both Bull cohort AND Phase 5 REJECTED applied, prefer DORMANT_REGIME."""
    ev = _build_ev(regime="Bull", live_avail=False, live_tier="REJECTED",
                       live_n=10)
    r = classify_pattern(ev, 80)
    # Bull blocking takes precedence (live data isn't usable for Bull cohort
    # anyway)
    assert r["tier"] == "DORMANT_REGIME"


# ── classify_all batch ────────────────────────────────────────────────

def test_classify_all_attaches_tier_classification():
    evs = [
        {**_build_ev(), "scoring": {"score": 85}},
        {**_build_ev(), "scoring": {"score": 35}},
    ]
    out = classify_all(evs)
    assert out[0]["tier_classification"]["tier"] == "ACTIVE_TAKE_FULL"
    assert out[1]["tier_classification"]["tier"] == "CANDIDATE"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
