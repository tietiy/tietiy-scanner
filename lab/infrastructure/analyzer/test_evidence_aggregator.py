"""
Unit tests for analyzer/evidence_aggregator.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_evidence_aggregator.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pattern_unifier import UnifiedPattern  # noqa: E402
from evidence_aggregator import (  # noqa: E402
    aggregate_evidence, _phase2_method_agreement, _detect_regime_agnostic,
)


# ── Fixtures ──────────────────────────────────────────────────────────

def _make_p4_row(combo_id, signal, regime, horizon, test_wr, baseline_wr,
                    test_n=50, drift=0.05, wilson_lo=None,
                    p_value=None, tier="A"):
    return {
        "combo_id": combo_id, "signal_type": signal, "regime": regime,
        "horizon": horizon, "test_n": test_n, "test_wr": test_wr,
        "baseline_wr": baseline_wr,
        "drift_train_test_pp": drift,
        "test_wilson_lower_95": wilson_lo,
        "test_p_value_vs_baseline": p_value, "tier": tier,
    }


def _make_p5_row(combo_id, live_n, live_wr, live_tier="VALIDATED",
                    cohort_blocked=False, drift=0.03):
    return {
        "combo_id": combo_id, "live_n": live_n,
        "live_n_wins": int(live_wr * live_n) if live_wr else 0,
        "live_n_losses": live_n - int(live_wr * live_n) if live_wr else 0,
        "live_wr": live_wr,
        "live_drift_vs_test": drift,
        "live_tier": live_tier,
        "cohort_blocked": cohort_blocked,
    }


def _make_unified_pattern(combo_id, signal, regime, horizon, features,
                              edge_pp=0.20, tier="A"):
    return UnifiedPattern(
        pattern_id=f"pid_{combo_id}",
        anchor_combo_id=combo_id,
        supporting_combo_ids=[],
        cohort_signal_type=signal,
        cohort_regime=regime, cohort_horizon=horizon,
        features=[{"feature_id": fid, "level": lvl} for fid, lvl in features],
        feature_count=len(features),
        anchor_tier=tier,
        anchor_test_wr=0.5 + edge_pp,
        anchor_edge_pp=edge_pp,
        cluster_size=1,
    )


# ── _phase2_method_agreement ──────────────────────────────────────────

def test_phase2_lookup_finds_feature():
    importance = {
        "cohorts": {
            "lifetime-Bear": {
                "ranked_features": [
                    {"feature_id": "ema_alignment",
                     "aggregate_rank": 3, "robustness": 4},
                    {"feature_id": "RSI_14",
                     "aggregate_rank": 7, "robustness": 3},
                ]
            }
        }
    }
    rank, agree = _phase2_method_agreement(importance, "Bear", "ema_alignment")
    assert rank == 3 and agree == 4


def test_phase2_lookup_missing_feature_returns_none():
    importance = {
        "cohorts": {"lifetime-Bear": {"ranked_features": [
            {"feature_id": "ema_alignment", "aggregate_rank": 3, "robustness": 4}]}}
    }
    rank, agree = _phase2_method_agreement(importance, "Bear", "missing_feature")
    assert rank is None and agree is None


def test_phase2_lookup_missing_cohort_returns_none():
    rank, agree = _phase2_method_agreement({"cohorts": {}},
                                                "Bear", "ema_alignment")
    assert rank is None


# ── regime-agnostic detection ────────────────────────────────────────

def test_regime_agnostic_when_two_regimes_share_pattern():
    bear_pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bear", "D10",
        [("ema_alignment", "bull"), ("RSI_14", "high")], edge_pp=0.20)
    bull_pat = _make_unified_pattern(
        "c2", "UP_TRI", "Bull", "D10",
        [("ema_alignment", "bull"), ("RSI_14", "high")], edge_pp=0.18)
    is_ag, regimes = _detect_regime_agnostic(
        bear_pat.features, [bear_pat, bull_pat],
        "UP_TRI", {"D10"})
    assert is_ag is True
    assert "Bear" in regimes and "Bull" in regimes


def test_not_regime_agnostic_when_single_regime():
    bear_pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bear", "D10",
        [("ema_alignment", "bull"), ("RSI_14", "high")], edge_pp=0.20)
    is_ag, regimes = _detect_regime_agnostic(
        bear_pat.features, [bear_pat], "UP_TRI", {"D10"})
    assert is_ag is False
    assert regimes == ["Bear"]


# ── aggregate_evidence end-to-end ────────────────────────────────────

def test_aggregate_evidence_basic_schema():
    """Single pattern with both Phase 4 + Phase 5 data → full evidence vector."""
    pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bear", "D10",
        [("ema_alignment", "bull")], edge_pp=0.30, tier="S")
    p4 = pd.DataFrame([_make_p4_row(
        "c1", "UP_TRI", "Bear", "D10", test_wr=0.83, baseline_wr=0.53,
        test_n=33, drift=0.05, wilson_lo=0.65, p_value=1e-6, tier="S")])
    p5 = pd.DataFrame([_make_p5_row("c1", live_n=12, live_wr=0.92,
                                          live_tier="VALIDATED")])
    importance = {
        "cohorts": {"lifetime-Bear": {"ranked_features": [
            {"feature_id": "ema_alignment", "aggregate_rank": 3,
             "robustness": 4}]}}
    }
    out = aggregate_evidence([pat], p4, p5, importance, {})
    assert len(out) == 1
    ev = out[0]
    # Schema sanity
    for k in ("pattern_id", "anchor_combo_id", "supporting_combo_ids",
              "cohort", "features", "feature_count",
              "statistical_evidence", "live_evidence", "feature_evidence",
              "regime_coverage", "convergence_sources", "cluster_size"):
        assert k in ev
    # Statistical
    assert ev["statistical_evidence"]["lifetime_n_test"] == 33
    assert abs(ev["statistical_evidence"]["lifetime_test_wr"] - 0.83) < 1e-9
    assert abs(ev["statistical_evidence"]["lifetime_edge_pp"] - 0.30) < 1e-9
    assert ev["statistical_evidence"]["phase_4_tier"] == "S"
    # Live
    assert ev["live_evidence"]["available"] is True
    assert ev["live_evidence"]["live_n"] == 12
    assert ev["live_evidence"]["phase_5_tier"] == "VALIDATED"
    # Feature evidence
    assert ev["feature_evidence"]["phase_2_avg_rank"] == 3.0
    # Convergence
    assert ev["convergence_sources"]["count"] == 3  # P4 + P5 + P2
    assert ev["convergence_sources"]["phase_4_walk_forward"] is True
    assert ev["convergence_sources"]["phase_5_live"] is True
    assert ev["convergence_sources"]["phase_2_importance"] is True


def test_aggregate_evidence_bull_cohort_blocked():
    """Bull cohort patterns: live_evidence.available = False, cohort_blocked = True."""
    pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bull", "D10",
        [("ema_alignment", "bull")], edge_pp=0.20)
    p4 = pd.DataFrame([_make_p4_row(
        "c1", "UP_TRI", "Bull", "D10", test_wr=0.71, baseline_wr=0.51,
        tier="A")])
    p5 = pd.DataFrame([_make_p5_row("c1", live_n=0, live_wr=None,
                                          live_tier="WATCH",
                                          cohort_blocked=True)])
    out = aggregate_evidence([pat], p4, p5, {"cohorts": {}}, {})
    ev = out[0]
    assert ev["live_evidence"]["available"] is False
    assert ev["live_evidence"].get("cohort_blocked") is True
    assert ev["convergence_sources"]["phase_5_live"] is False
    # Convergence count = 1 (just P4) since P2 cohort not provided + P5 unavailable
    assert ev["convergence_sources"]["count"] == 1


def test_aggregate_evidence_no_phase5_data():
    """Evidence aggregator works without Phase 5 input (defensive)."""
    pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bear", "D10",
        [("ema_alignment", "bull")], edge_pp=0.20)
    p4 = pd.DataFrame([_make_p4_row(
        "c1", "UP_TRI", "Bear", "D10", test_wr=0.73, baseline_wr=0.53)])
    out = aggregate_evidence([pat], p4, None, {"cohorts": {}}, {})
    assert len(out) == 1
    assert out[0]["live_evidence"]["available"] is False


def test_regime_agnostic_in_full_evidence_aggregation():
    """Same features in two regimes both with edge → regime_agnostic = True."""
    bear_pat = _make_unified_pattern(
        "c1", "UP_TRI", "Bear", "D10",
        [("ema_alignment", "bull")], edge_pp=0.20)
    bull_pat = _make_unified_pattern(
        "c2", "UP_TRI", "Bull", "D10",
        [("ema_alignment", "bull")], edge_pp=0.18)
    p4 = pd.DataFrame([
        _make_p4_row("c1", "UP_TRI", "Bear", "D10", 0.73, 0.53),
        _make_p4_row("c2", "UP_TRI", "Bull", "D10", 0.69, 0.51),
    ])
    out = aggregate_evidence([bear_pat, bull_pat], p4, None,
                                  {"cohorts": {}}, {})
    bear_ev = next(e for e in out if e["cohort"]["regime"] == "Bear")
    assert bear_ev["regime_coverage"]["regime_agnostic"] is True
    assert set(bear_ev["regime_coverage"]["regimes_with_edge"]) == {"Bear", "Bull"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
