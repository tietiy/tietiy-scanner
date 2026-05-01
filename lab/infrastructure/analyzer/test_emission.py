"""
Unit tests for analyzer/emission.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/analyzer/test_emission.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emission import (  # noqa: E402
    emit_barcodes_json, emit_patterns_full_json, emit_findings_synthesis,
    SCHEMA_VERSION, ACTIVE_TIERS, PRODUCTION_TIERS, _sort_key,
    _format_pattern_for_barcode, _build_synthesis_prompt,
)


def _build_pattern(pattern_id="abc123def456", tier="ACTIVE_TAKE_FULL",
                       score=85.0, signal_type="UP_TRI", regime="Bear",
                       horizon="D10", features=None):
    return {
        "pattern_id": pattern_id,
        "anchor_combo_id": f"combo_{pattern_id[:6]}",
        "supporting_combo_ids": [],
        "cohort": {"signal_type": signal_type, "regime": regime,
                       "horizon": horizon},
        "features": features or [{"feature_id": "ema_alignment",
                                       "level": "bull"}],
        "feature_count": len(features) if features else 1,
        "statistical_evidence": {
            "lifetime_n_test": 33, "lifetime_test_wr": 0.85,
            "lifetime_baseline_wr": 0.54, "lifetime_edge_pp": 0.31,
            "lifetime_drift": 0.05,
        },
        "live_evidence": {"available": True, "live_n": 12, "live_wr": 0.92,
                              "phase_5_tier": "VALIDATED"},
        "regime_coverage": {"regimes_with_edge": ["Bear"]},
        "convergence_sources": {"count": 3},
        "mechanism": "Counter-trend bounce in oversold market.",
        "mechanism_concept": "weak_hands_capitulation",
        "mechanism_clarity": 80,
        "scoring": {
            "score": score,
            "profile": "profile_1",
            "sub_scores": {"statistical_strength": 80, "convergence": 70,
                              "mechanism": 80, "live_evidence": 95,
                              "regime_breadth": 30},
        },
        "tier_classification": {"tier": tier, "primary_tier": tier,
                                    "override_reason": None},
    }


# ── _sort_key ─────────────────────────────────────────────────────────

def test_sort_key_orders_by_tier_then_score():
    p1 = _build_pattern(tier="ACTIVE_TAKE_FULL", score=80)
    p2 = _build_pattern(tier="ACTIVE_TAKE_SMALL", score=95)  # higher score
    p3 = _build_pattern(tier="ACTIVE_TAKE_FULL", score=85)
    sorted_p = sorted([p1, p2, p3], key=_sort_key)
    # ACTIVE_TAKE_FULL comes first (regardless of higher-scored TAKE_SMALL)
    assert sorted_p[0]["tier_classification"]["tier"] == "ACTIVE_TAKE_FULL"
    assert sorted_p[1]["tier_classification"]["tier"] == "ACTIVE_TAKE_FULL"
    assert sorted_p[2]["tier_classification"]["tier"] == "ACTIVE_TAKE_SMALL"
    # Within same tier, higher score first
    assert sorted_p[0]["scoring"]["score"] >= sorted_p[1]["scoring"]["score"]


# ── _format_pattern_for_barcode ──────────────────────────────────────

def test_barcode_format_has_lightweight_schema():
    p = _build_pattern()
    bc = _format_pattern_for_barcode(p)
    for k in ("barcode_id", "pattern_id", "tier", "action", "score",
              "cohort", "features", "mechanism", "evidence_summary",
              "scoring_breakdown", "lifecycle", "relationships"):
        assert k in bc
    # Action mapping
    assert bc["action"] == "TAKE_FULL"
    # Mechanism nested fields present
    assert "text" in bc["mechanism"]
    assert "concept" in bc["mechanism"]
    assert "clarity" in bc["mechanism"]
    # Evidence summary numeric
    assert bc["evidence_summary"]["lifetime_n"] == 33
    # v1 lifecycle stub
    assert bc["lifecycle"]["history"] == []
    # v1 relationships stub
    assert bc["relationships"]["subsumes"] == []


def test_barcode_action_for_kill():
    p = _build_pattern(tier="KILL")
    bc = _format_pattern_for_barcode(p)
    assert bc["action"] == "REJECT"


def test_barcode_action_for_active_watch():
    p = _build_pattern(tier="ACTIVE_WATCH")
    bc = _format_pattern_for_barcode(p)
    assert bc["action"] == "WATCH"


# ── emit_barcodes_json ───────────────────────────────────────────────

def test_emit_barcodes_filters_to_production_tiers(tmp_path):
    """Only ACTIVE + KILL tiers are written; CANDIDATE/DEPRECATED/DORMANT excluded."""
    patterns = [
        _build_pattern(tier="ACTIVE_TAKE_FULL", score=85),
        _build_pattern(tier="ACTIVE_TAKE_SMALL", score=70),
        _build_pattern(tier="ACTIVE_WATCH", score=55),
        _build_pattern(tier="KILL", score=20),
        _build_pattern(tier="CANDIDATE", score=40),
        _build_pattern(tier="DORMANT_REGIME", score=80),
        _build_pattern(tier="DEPRECATED", score=15),
    ]
    out = tmp_path / "barcodes.json"
    payload = emit_barcodes_json(patterns, out)
    assert out.exists()
    saved = json.loads(out.read_text())
    barcodes = saved["barcodes"]
    # Only 4 production-tier patterns retained
    assert len(barcodes) == 4
    tiers_in = {b["tier"] for b in barcodes}
    assert tiers_in == {"ACTIVE_TAKE_FULL", "ACTIVE_TAKE_SMALL",
                          "ACTIVE_WATCH", "KILL"}


def test_emit_barcodes_schema_version_stamped(tmp_path):
    out = tmp_path / "barcodes.json"
    emit_barcodes_json([_build_pattern()], out)
    saved = json.loads(out.read_text())
    assert saved["schema_version"] == SCHEMA_VERSION
    assert "generated_at" in saved
    assert "tier_counts" in saved


def test_emit_barcodes_sorted_correctly(tmp_path):
    patterns = [
        _build_pattern(pattern_id="aaa1", tier="ACTIVE_WATCH", score=55),
        _build_pattern(pattern_id="bbb2", tier="ACTIVE_TAKE_FULL", score=88),
        _build_pattern(pattern_id="ccc3", tier="KILL", score=20),
    ]
    out = tmp_path / "barcodes.json"
    emit_barcodes_json(patterns, out)
    saved = json.loads(out.read_text())
    bcs = saved["barcodes"]
    assert bcs[0]["tier"] == "ACTIVE_TAKE_FULL"
    assert bcs[1]["tier"] == "ACTIVE_WATCH"
    assert bcs[2]["tier"] == "KILL"


# ── emit_patterns_full_json ──────────────────────────────────────────

def test_emit_patterns_full_includes_all_tiers(tmp_path):
    patterns = [
        _build_pattern(tier="ACTIVE_TAKE_FULL"),
        _build_pattern(tier="DORMANT_REGIME"),
        _build_pattern(tier="DEPRECATED"),
    ]
    out = tmp_path / "patterns_full.json"
    emit_patterns_full_json(patterns, out)
    saved = json.loads(out.read_text())
    assert len(saved["patterns"]) == 3
    assert saved["schema_version"] == SCHEMA_VERSION
    tier_dist = saved["tier_distribution"]
    assert tier_dist["ACTIVE_TAKE_FULL"] == 1
    assert tier_dist["DORMANT_REGIME"] == 1


# ── emit_findings_synthesis ──────────────────────────────────────────

def test_emit_findings_uses_llm_client(tmp_path):
    """Synthesizer should call llm_client.synthesize_findings + write file."""
    mock_llm = MagicMock()
    mock_llm.synthesize_findings.return_value = "## Run summary\n\nTest digest body."
    mock_llm.total_cost = 0.05
    mock_llm.cache_hits = 100
    mock_llm.total_calls = 50
    patterns = [_build_pattern()]
    out = tmp_path / "ANALYZER_findings.md"
    result = emit_findings_synthesis(patterns, out, mock_llm)
    assert out.exists()
    text = out.read_text()
    assert "Test digest body" in text
    assert "Cost summary" in text
    assert mock_llm.synthesize_findings.called
    # Returned summary
    assert result["total_calls"] == 50
    assert result["cost_total"] == 0.05


def test_synthesis_prompt_includes_pattern_count_and_tiers():
    patterns = [
        _build_pattern(tier="ACTIVE_TAKE_FULL"),
        _build_pattern(tier="ACTIVE_TAKE_FULL"),
        _build_pattern(tier="DORMANT_REGIME"),
    ]
    prompt = _build_synthesis_prompt(patterns)
    assert "Total unified patterns: 3" in prompt
    assert "ACTIVE_TAKE_FULL" in prompt
    assert "Top 10 patterns" in prompt


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
