"""
Unit tests for analyzer/pattern_scorer.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_pattern_scorer.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pattern_scorer import (  # noqa: E402
    statistical_strength_score, convergence_score, live_evidence_score,
    mechanism_score, regime_breadth_score,
    is_profile_2, composite_score,
    PROFILE_1_WEIGHTS, PROFILE_2_WEIGHTS,
)


# ── statistical_strength_score ────────────────────────────────────────

def test_stat_score_strong_evidence():
    """High Wilson, low drift, low p-value, n_test=100 → near 100."""
    stat = {
        "wilson_lower_95": 0.78, "lifetime_baseline_wr": 0.50,
        "lifetime_drift": 0.03, "p_value": 1e-8,
        "lifetime_n_test": 100,
    }
    s = statistical_strength_score(stat)
    assert s > 80


def test_stat_score_weak_evidence():
    stat = {
        "wilson_lower_95": 0.55, "lifetime_baseline_wr": 0.51,
        "lifetime_drift": 0.10, "p_value": 0.05,
        "lifetime_n_test": 30,
    }
    s = statistical_strength_score(stat)
    assert s < 50


def test_stat_score_no_data_returns_zero_ish():
    stat = {}
    s = statistical_strength_score(stat)
    # All defaults → wilson 0.5, baseline 0.5 → 0pt; drift 0 → 25pt; p_val 1.0 → 0pt; n=0 → 0pt
    assert 20 < s < 35


# ── convergence_score ────────────────────────────────────────────────

def test_convergence_score_each_count():
    assert convergence_score({"count": 0}) == 0.0
    assert convergence_score({"count": 1}) == 25.0
    assert convergence_score({"count": 2}) == 50.0
    assert convergence_score({"count": 3}) == 70.0
    assert convergence_score({"count": 4}) == 90.0
    assert convergence_score({"count": 7}) == 90.0


def test_convergence_method_agreement_bonus():
    """4/4 method agreement → +10 bonus."""
    assert convergence_score({"count": 2}, method_agreement=4) == 60.0
    assert convergence_score({"count": 4}, method_agreement=4) == 100.0
    assert convergence_score({"count": 2}, method_agreement=2) == 50.0  # no bonus


# ── live_evidence_score ──────────────────────────────────────────────

def test_live_score_per_tier():
    assert live_evidence_score({"available": True, "phase_5_tier": "VALIDATED"}) == 95.0
    assert live_evidence_score({"available": True, "phase_5_tier": "PRELIMINARY"}) == 70.0
    assert live_evidence_score({"available": True, "phase_5_tier": "WATCH"}) == 40.0
    assert live_evidence_score({"available": True, "phase_5_tier": "REJECTED"}) == 0.0
    assert live_evidence_score({"available": False}) == 0.0


# ── mechanism_score ─────────────────────────────────────────────────

def test_mechanism_score_clamps_to_0_100():
    assert mechanism_score(0) == 0.0
    assert mechanism_score(50) == 50.0
    assert mechanism_score(100) == 100.0
    assert mechanism_score(150) == 100.0
    assert mechanism_score(-10) == 0.0


# ── regime_breadth_score ────────────────────────────────────────────

def test_regime_breadth():
    assert regime_breadth_score({"regimes_with_edge": ["Bear"]}) == 30.0
    assert regime_breadth_score({"regimes_with_edge": ["Bear", "Bull"]}) == 70.0
    assert regime_breadth_score(
        {"regimes_with_edge": ["Bear", "Bull", "Choppy"]}) == 100.0
    assert regime_breadth_score({"regimes_with_edge": []}) == 30.0


# ── is_profile_2 ────────────────────────────────────────────────────

def test_profile_2_detected_for_bull_cohort_no_live():
    ev = {"cohort": {"regime": "Bull"}, "live_evidence": {"available": False}}
    assert is_profile_2(ev) is True


def test_profile_1_for_bear_cohort_with_live():
    ev = {"cohort": {"regime": "Bear"}, "live_evidence": {"available": True}}
    assert is_profile_2(ev) is False


def test_profile_1_for_bull_cohort_with_live():
    """If somehow Bull has live data, Profile 1 still applies."""
    ev = {"cohort": {"regime": "Bull"}, "live_evidence": {"available": True}}
    assert is_profile_2(ev) is False


# ── composite_score ─────────────────────────────────────────────────

def _build_evidence(regime="Bear", live_avail=True, live_tier="VALIDATED",
                       baseline=0.50, test_wr=0.80, drift=0.05,
                       wilson=0.65, p_val=1e-6, n_test=50,
                       conv_count=3, method_agreement=4,
                       regimes_with_edge=("Bear",)):
    return {
        "cohort": {"regime": regime},
        "statistical_evidence": {
            "wilson_lower_95": wilson,
            "lifetime_baseline_wr": baseline,
            "lifetime_test_wr": test_wr,
            "lifetime_drift": drift,
            "p_value": p_val,
            "lifetime_n_test": n_test,
        },
        "convergence_sources": {"count": conv_count},
        "feature_evidence": {
            "phase_2_avg_method_agreement": method_agreement
        },
        "live_evidence": {
            "available": live_avail, "phase_5_tier": live_tier,
        },
        "regime_coverage": {
            "regimes_with_edge": list(regimes_with_edge),
        },
    }


def test_composite_score_profile_1_strong():
    ev = _build_evidence()
    result = composite_score(ev, mechanism_clarity=85)
    assert result["profile"] == "profile_1"
    assert result["score"] >= 70  # strong-evidence pattern should score high


def test_composite_score_profile_2_bull():
    """Bull cohort → Profile 2 (4 weights, no live)."""
    ev = _build_evidence(regime="Bull", live_avail=False, live_tier="WATCH")
    result = composite_score(ev, mechanism_clarity=70)
    assert result["profile"] == "profile_2"
    # Profile 2 weights sum to 1.0
    weights = result["weights_used"]
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    # Live sub_score not used in profile 2
    assert "live" not in weights


def test_composite_score_includes_all_subscores():
    ev = _build_evidence()
    result = composite_score(ev, mechanism_clarity=60)
    for k in ("statistical_strength", "convergence", "mechanism",
                "live_evidence", "regime_breadth"):
        assert k in result["sub_scores"]


def test_profile_1_weights_sum_to_one():
    assert abs(sum(PROFILE_1_WEIGHTS.values()) - 1.0) < 1e-9


def test_profile_2_weights_sum_to_one():
    assert abs(sum(PROFILE_2_WEIGHTS.values()) - 1.0) < 1e-9


def test_composite_score_rejected_pattern_low():
    """Pattern with REJECTED phase_5_tier should score lower."""
    ev = _build_evidence(live_tier="REJECTED")
    result = composite_score(ev, mechanism_clarity=70)
    # live sub_score = 0, drags composite
    ev_validated = _build_evidence(live_tier="VALIDATED")
    result_v = composite_score(ev_validated, mechanism_clarity=70)
    assert result["score"] < result_v["score"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
