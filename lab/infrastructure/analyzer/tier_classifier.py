"""
Tier classifier — assigns one of 9 tiers per pattern based on score + context.

Tier taxonomy:
  ACTIVE_TAKE_FULL          score 80+, viable for full-size live trading
  ACTIVE_TAKE_SMALL         score 65-79, partial-size viable
  ACTIVE_WATCH              score 50-64, watch-list candidate
  DORMANT_REGIME            high score but cohort regime not currently present
  DORMANT_INSUFFICIENT_DATA high score but no live data yet
  DORMANT_DEFERRED          high score but Phase 5 REJECTED (regime sub-character)
  CANDIDATE                 score 30-49, mid-confidence
  DEPRECATED                score < 30 OR explicitly killed
  KILL                      special: REJECT signal when matched

Override priority (always check in this order):
  1. KILL (e.g., triangle_quality_ascending in Bear) — overrides all
  2. DORMANT_REGIME (Bull cohort, no live data, score ≥ 50)
  3. DORMANT_INSUFFICIENT_DATA (live unavailable but cohort active, score ≥ 50)
  4. DORMANT_DEFERRED (Phase 5 REJECTED, score ≥ 50)
  5. Score-based primary tier
"""
from __future__ import annotations

from typing import Optional

# Score thresholds
SCORE_ACTIVE_FULL = 80
SCORE_ACTIVE_SMALL = 65
SCORE_ACTIVE_WATCH = 50
SCORE_CANDIDATE = 30
DORMANT_FLOOR_SCORE = 50  # below this, dormant overrides don't apply

# Features whose presence triggers KILL classification (lifetime negative
# effect_size from Phase 2 / surfaced as Tier S in Bear cohort would be
# the contradiction; pre-listed here for v1 simplicity)
KILL_FEATURE_IDS = frozenset({
    "triangle_quality_ascending",  # Phase 2 negative effect_size in Bear
})


def _score_based_primary(score: float) -> str:
    if score >= SCORE_ACTIVE_FULL:
        return "ACTIVE_TAKE_FULL"
    if score >= SCORE_ACTIVE_SMALL:
        return "ACTIVE_TAKE_SMALL"
    if score >= SCORE_ACTIVE_WATCH:
        return "ACTIVE_WATCH"
    if score >= SCORE_CANDIDATE:
        return "CANDIDATE"
    return "DEPRECATED"


def _has_kill_feature(evidence: dict) -> bool:
    """Pattern uses a feature flagged as KILL (e.g., triangle_quality_ascending)."""
    for f in evidence.get("features", []):
        if f.get("feature_id") in KILL_FEATURE_IDS:
            return True
    return False


def _is_cohort_regime_blocked(evidence: dict) -> bool:
    """Bull cohort with no live data → DORMANT_REGIME."""
    cohort_regime = evidence.get("cohort", {}).get("regime")
    live_avail = evidence.get("live_evidence", {}).get("available", False)
    return cohort_regime == "Bull" and not live_avail


def _is_live_unavailable(evidence: dict) -> bool:
    """Live data not available (cohort active, but per-pattern live_n was 0)."""
    live = evidence.get("live_evidence", {})
    return not live.get("available", False) or live.get("live_n", 0) == 0


def _is_phase5_rejected(evidence: dict) -> bool:
    return evidence.get("live_evidence", {}).get("phase_5_tier") == "REJECTED"


def classify_pattern(evidence: dict, score: float) -> dict:
    """Apply override + score logic; return tier + override reason."""
    # Step 1: KILL trumps all
    if _has_kill_feature(evidence):
        return {
            "tier": "KILL",
            "primary_tier": _score_based_primary(score),
            "override_reason": (
                "Pattern uses feature flagged as KILL "
                "(e.g. triangle_quality_ascending in Bear cohort, "
                "Phase 2 negative effect_size)"),
        }

    primary = _score_based_primary(score)

    # Step 2: DORMANT overrides only apply if score ≥ DORMANT_FLOOR
    if score < DORMANT_FLOOR_SCORE:
        return {
            "tier": primary, "primary_tier": primary,
            "override_reason": None,
        }

    # Step 3: DORMANT_REGIME (Bull cohort, no live)
    if _is_cohort_regime_blocked(evidence):
        return {
            "tier": "DORMANT_REGIME",
            "primary_tier": primary,
            "override_reason": (
                "Bull cohort; no live Bull regime data in current window. "
                "Awaiting Bull regime return."),
        }

    # Step 4: DORMANT_DEFERRED (Phase 5 REJECTED but lifetime evidence still strong)
    if _is_phase5_rejected(evidence):
        return {
            "tier": "DORMANT_DEFERRED",
            "primary_tier": primary,
            "override_reason": (
                "Phase 5 live evidence REJECTED. Current regime sub-character "
                "may differ from historical. Lifetime evidence preserved for "
                "future re-evaluation."),
        }

    # Step 5: DORMANT_INSUFFICIENT_DATA (cohort active but no live data per pattern)
    if _is_live_unavailable(evidence):
        return {
            "tier": "DORMANT_INSUFFICIENT_DATA",
            "primary_tier": primary,
            "override_reason": (
                "Live cohort active but no live signals matched this pattern. "
                "Pattern remains lifetime-validated; awaits live samples."),
        }

    # No override → score-based primary
    return {
        "tier": primary, "primary_tier": primary,
        "override_reason": None,
    }


def classify_all(evidences_with_scoring: list[dict]) -> list[dict]:
    """Apply tier classification to every evidence vector with scoring.

    Each input dict must have 'scoring' key with 'score' field (from pattern_scorer).
    Returns evidences with new key 'tier_classification' attached.
    """
    out = []
    for ev in evidences_with_scoring:
        score = ev.get("scoring", {}).get("score", 0.0)
        tier_info = classify_pattern(ev, score)
        ev_out = dict(ev)
        ev_out["tier_classification"] = tier_info
        out.append(ev_out)
    return out
