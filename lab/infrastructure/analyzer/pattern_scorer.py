"""
Pattern scorer — computes 5 sub-scores + composite score per pattern.

Sub-scores (each 0-100):
  • statistical_strength_score — Wilson + drift inverse + p-value + n_test
  • convergence_score — count of source phases (1→25, 2→50, 3→70, 4+→90+)
  • mechanism_score — LLM-evaluated clarity (0-100, defaults to 30 on failure)
  • live_evidence_score — VALIDATED 95 / PRELIMINARY 70 / WATCH 40 / REJECTED 0
  • regime_breadth_score — 1 regime 30 / 2 regimes 70 / 3 regimes 100

Composite (Profile 1 — live data available):
  score = stat·0.30 + conv·0.25 + mech·0.20 + live·0.15 + regime·0.10

Composite (Profile 2 — Bull cohort, no live):
  score = stat·0.35 + conv·0.30 + mech·0.25 + regime·0.10

Profile detection: Bull cohort + live unavailable → Profile 2.
"""
from __future__ import annotations

import math
from typing import Optional


# ── Score weights ─────────────────────────────────────────────────────

PROFILE_1_WEIGHTS = {
    "statistical": 0.30, "convergence": 0.25,
    "mechanism": 0.20, "live": 0.15, "regime": 0.10,
}
PROFILE_2_WEIGHTS = {
    "statistical": 0.35, "convergence": 0.30,
    "mechanism": 0.25, "regime": 0.10,
}

# Mechanism default when API call fails
MECHANISM_DEFAULT_ON_FAIL = 30


# ── Sub-scores ────────────────────────────────────────────────────────

def statistical_strength_score(stat: dict) -> float:
    """Aggregate Wilson lower, drift, p-value, sample size into 0-100."""
    wilson = stat.get("wilson_lower_95") or 0.5
    drift = abs(stat.get("lifetime_drift") or 0.0)
    p_val = stat.get("p_value") or 1.0
    n_test = stat.get("lifetime_n_test") or 0
    baseline = stat.get("lifetime_baseline_wr") or 0.5

    # Wilson sub: how much does the lower bound exceed baseline?
    wilson_excess = max(0.0, wilson - baseline)
    wilson_pts = min(40.0, wilson_excess * 200.0)  # 0-40 (20pp excess → 40)

    # Drift sub: lower drift = higher score (drift is a fraction, e.g. 0.05)
    drift_pts = max(0.0, 25.0 - drift * 200.0)  # 0-25 (drift 0 → 25, 0.125 → 0)

    # p-value sub: log-scaled
    if p_val > 0:
        p_pts = min(20.0, max(0.0, -math.log10(p_val) * 4.0))
    else:
        p_pts = 20.0

    # Sample size sub: capped diminishing returns
    n_pts = min(15.0, n_test / 100.0 * 15.0)  # 0-15 (n=100+ → 15)

    return round(min(100.0, wilson_pts + drift_pts + p_pts + n_pts), 1)


def convergence_score(convergence: dict,
                          method_agreement: Optional[float] = None) -> float:
    """Count of convergence sources → score, with method-agreement bonus."""
    count = convergence.get("count", 0)
    if count <= 0:
        base = 0.0
    elif count == 1:
        base = 25.0
    elif count == 2:
        base = 50.0
    elif count == 3:
        base = 70.0
    else:  # 4+
        base = 90.0
    if method_agreement is not None and method_agreement >= 4:
        base = min(100.0, base + 10.0)
    return round(base, 1)


def live_evidence_score(live: dict) -> float:
    """Phase 5 tier → score. Returns None for cohort-blocked (Profile 2 won't use)."""
    if not live.get("available", False):
        return 0.0  # not used in Profile 2 composite
    tier = live.get("phase_5_tier", "WATCH")
    if tier == "VALIDATED":
        return 95.0
    if tier == "PRELIMINARY":
        return 70.0
    if tier == "WATCH":
        return 40.0
    if tier == "REJECTED":
        return 0.0
    return 30.0


def mechanism_score(clarity: int) -> float:
    """LLM-evaluated clarity (0-100) → directly used as score."""
    return float(max(0, min(100, clarity)))


def regime_breadth_score(regime_coverage: dict) -> float:
    """Single 30, two 70, three 100."""
    regimes = regime_coverage.get("regimes_with_edge", [])
    n = len(regimes)
    if n >= 3:
        return 100.0
    if n == 2:
        return 70.0
    return 30.0


# ── Profile detection ────────────────────────────────────────────────

def is_profile_2(evidence: dict) -> bool:
    """Profile 2: Bull cohort with no live data available."""
    regime = evidence.get("cohort", {}).get("regime")
    live_avail = evidence.get("live_evidence", {}).get("available", False)
    return regime == "Bull" and not live_avail


# ── Composite ────────────────────────────────────────────────────────

def composite_score(evidence: dict, mechanism_clarity: int) -> dict:
    """Compute all sub-scores + composite + profile used.

    Returns dict:
      {
        "score": <0-100>,
        "profile": "profile_1" or "profile_2",
        "sub_scores": {statistical, convergence, mechanism, live, regime}
      }
    """
    stat = evidence.get("statistical_evidence", {})
    conv = evidence.get("convergence_sources", {})
    live = evidence.get("live_evidence", {})
    feat_ev = evidence.get("feature_evidence", {})
    rc = evidence.get("regime_coverage", {})

    sub_stat = statistical_strength_score(stat)
    sub_conv = convergence_score(
        conv, method_agreement=feat_ev.get("phase_2_avg_method_agreement"))
    sub_mech = mechanism_score(mechanism_clarity)
    sub_live = live_evidence_score(live)
    sub_regime = regime_breadth_score(rc)

    if is_profile_2(evidence):
        w = PROFILE_2_WEIGHTS
        score = (sub_stat * w["statistical"]
                  + sub_conv * w["convergence"]
                  + sub_mech * w["mechanism"]
                  + sub_regime * w["regime"])
        profile = "profile_2"
    else:
        w = PROFILE_1_WEIGHTS
        score = (sub_stat * w["statistical"]
                  + sub_conv * w["convergence"]
                  + sub_mech * w["mechanism"]
                  + sub_live * w["live"]
                  + sub_regime * w["regime"])
        profile = "profile_1"

    return {
        "score": round(score, 1),
        "profile": profile,
        "sub_scores": {
            "statistical_strength": sub_stat,
            "convergence": sub_conv,
            "mechanism": sub_mech,
            "live_evidence": sub_live,
            "regime_breadth": sub_regime,
        },
        "weights_used": dict(w),
    }


# ── Driver: score all patterns w/ LLM mechanism evaluation ────────────

def score_all_patterns(evidences: list[dict],
                          llm_client,
                          progress_every: int = 50) -> list[dict]:
    """For each evidence vector, generate mechanism via LLM + compute score.

    Returns evidence list augmented with:
      • mechanism (text)
      • mechanism_concept (str or None)
      • mechanism_clarity (int 0-100)
      • scoring (dict from composite_score)
    """
    # Batch-generate mechanisms via thread pool (llm_client handles concurrency)
    pattern_inputs = [
        {
            "cohort": e["cohort"],
            "features": e["features"],
            "statistical_evidence": e["statistical_evidence"],
        }
        for e in evidences
    ]
    print(f"  Generating mechanisms for {len(pattern_inputs)} patterns...")
    mechanism_responses = llm_client.batch_generate_mechanisms(
        pattern_inputs, progress_every=progress_every)

    # Pair responses with evidence
    out = []
    for ev, resp in zip(evidences, mechanism_responses):
        clarity = resp.clarity if resp else MECHANISM_DEFAULT_ON_FAIL
        scoring = composite_score(ev, clarity)
        out_ev = dict(ev)
        out_ev["mechanism"] = resp.mechanism if resp else "unclear (LLM failed)"
        out_ev["mechanism_concept"] = resp.concept if resp else None
        out_ev["mechanism_clarity"] = clarity
        out_ev["scoring"] = scoring
        out.append(out_ev)
    return out
