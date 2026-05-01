"""
Evidence aggregator — for each unified pattern, build evidence_vector
consolidating Phase 1-5 outputs.

Inputs:
  • Unified patterns (from pattern_unifier.UnifiedPattern list)
  • combinations_lifetime.parquet (Phase 4: walk-forward results)
  • combinations_live_validated.parquet (Phase 5: live tier verdicts)
  • feature_importance.json (Phase 2: ranked features per cohort)
  • baselines.json (Phase 3: cohort × horizon baselines)

Optional (placeholder for v2):
  • lab/findings/INV_REGISTER.json (empty in v1)
  • data/brain_proposals_log.jsonl (empty in v1)

Output: list of evidence_vector dicts per pattern.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


def _safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dict."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _phase2_method_agreement(importance_data: dict, regime: str,
                                feature_id: str) -> tuple[Optional[float], Optional[int]]:
    """Return (avg_borda_rank, methods_agree_top25) for the feature in
    the lifetime-{regime} cohort."""
    cohort_key = f"lifetime-{regime}"
    cohort = importance_data.get("cohorts", {}).get(cohort_key)
    if cohort is None:
        return (None, None)
    for f in cohort.get("ranked_features", []):
        if f.get("feature_id") == feature_id:
            return (f.get("aggregate_rank"), f.get("robustness"))
    return (None, None)


def _detect_regime_agnostic(pattern_features: list,
                                all_unified_patterns: list,
                                all_signal_type: str,
                                all_horizon_set: set,
                                edge_floor: float = 0.05) -> tuple[bool, list[str]]:
    """A pattern is regime-agnostic if the same feature combination appears
    in multiple regimes (Bear/Bull/Choppy) within the same signal_type, with
    edge_pp ≥ edge_floor in each.

    Returns (is_agnostic, list_of_regimes_with_edge).
    """
    feat_set = frozenset((f["feature_id"], f["level"]) for f in pattern_features)
    regimes_with_edge = set()
    for p in all_unified_patterns:
        if p.cohort_signal_type != all_signal_type:
            continue
        p_set = frozenset((f["feature_id"], f["level"]) for f in p.features)
        if p_set == feat_set and p.anchor_edge_pp >= edge_floor:
            regimes_with_edge.add(p.cohort_regime)
    return (len(regimes_with_edge) >= 2, sorted(regimes_with_edge))


def aggregate_evidence(
        unified_patterns: list,                    # UnifiedPattern list
        combinations_phase4_df: pd.DataFrame,
        combinations_phase5_df: pd.DataFrame,
        importance_data: dict,
        baselines_data: dict) -> list[dict]:
    """Build evidence_vector per unified pattern.

    Returns list of dicts with keys per spec:
      pattern_id, anchor_combo_id, supporting_combo_ids,
      cohort, features, feature_count,
      statistical_evidence, live_evidence, feature_evidence,
      regime_coverage, convergence_sources
    """
    # Index Phase 4 + Phase 5 outputs by combo_id for fast lookup
    p4_by_id = {r["combo_id"]: r for _, r in combinations_phase4_df.iterrows()}
    if combinations_phase5_df is not None and len(combinations_phase5_df) > 0:
        p5_by_id = {r["combo_id"]: r for _, r in combinations_phase5_df.iterrows()}
    else:
        p5_by_id = {}

    out: list[dict] = []

    for pat in unified_patterns:
        anchor = p4_by_id.get(pat.anchor_combo_id)
        if anchor is None:
            continue  # shouldn't happen but skip defensively

        # Statistical evidence (from Phase 4 walk-forward)
        baseline_wr = float(anchor.get("baseline_wr", 0.0) or 0.0)
        test_wr = float(anchor.get("test_wr", 0.0) or 0.0)
        stat = {
            "lifetime_n_test": int(anchor.get("test_n", 0) or 0),
            "lifetime_test_wr": test_wr,
            "lifetime_baseline_wr": baseline_wr,
            "lifetime_edge_pp": round(test_wr - baseline_wr, 4),
            "lifetime_drift": round(
                float(anchor.get("drift_train_test_pp", 0.0) or 0.0), 4),
            "wilson_lower_95": (float(anchor["test_wilson_lower_95"])
                                  if pd.notna(anchor.get("test_wilson_lower_95"))
                                  else None),
            "p_value": (float(anchor["test_p_value_vs_baseline"])
                          if pd.notna(anchor.get("test_p_value_vs_baseline"))
                          else None),
            "phase_4_tier": str(anchor.get("tier", "B")),
        }

        # Live evidence (from Phase 5)
        live_row = p5_by_id.get(pat.anchor_combo_id)
        if live_row is not None and not (live_row.get("cohort_blocked", False)):
            live_n = int(live_row.get("live_n", 0) or 0)
            live_wr = (float(live_row["live_wr"])
                          if pd.notna(live_row.get("live_wr")) else None)
            live = {
                "live_n": live_n,
                "live_w": int(live_row.get("live_n_wins", 0) or 0),
                "live_l": int(live_row.get("live_n_losses", 0) or 0),
                "live_wr": live_wr,
                "live_drift_vs_lifetime": (
                    float(live_row["live_drift_vs_test"])
                    if pd.notna(live_row.get("live_drift_vs_test")) else None),
                "phase_5_tier": str(live_row.get("live_tier", "WATCH")),
                "available": True,
            }
        elif live_row is not None and live_row.get("cohort_blocked", False):
            live = {
                "live_n": 0, "live_w": 0, "live_l": 0,
                "live_wr": None, "live_drift_vs_lifetime": None,
                "phase_5_tier": "WATCH",
                "available": False,
                "cohort_blocked": True,
            }
        else:
            live = {
                "live_n": 0, "live_w": 0, "live_l": 0,
                "live_wr": None, "live_drift_vs_lifetime": None,
                "phase_5_tier": "WATCH",
                "available": False,
            }

        # Feature evidence (Phase 2 importance ranks for anchor's features)
        fe_ranks = []
        fe_method_agreements = []
        for f in pat.features:
            avg_rank, method_agree = _phase2_method_agreement(
                importance_data, pat.cohort_regime, f["feature_id"])
            if avg_rank is not None:
                fe_ranks.append(avg_rank)
            if method_agree is not None:
                fe_method_agreements.append(method_agree)
        feature_evidence = {
            "phase_2_avg_rank": (
                round(sum(fe_ranks) / len(fe_ranks), 1)
                if fe_ranks else None),
            "phase_2_avg_method_agreement": (
                round(sum(fe_method_agreements) / len(fe_method_agreements), 2)
                if fe_method_agreements else None),
        }

        # Regime coverage (cross-cohort agnostic detection)
        is_agnostic, regimes_with_edge = _detect_regime_agnostic(
            pat.features, unified_patterns, pat.cohort_signal_type,
            {pat.cohort_horizon})
        regime_coverage = {
            "regimes_with_edge": regimes_with_edge,
            "regime_agnostic": is_agnostic,
            "primary_regime": pat.cohort_regime,
        }

        # Convergence sources
        sources = []
        if stat["lifetime_n_test"] > 0:
            sources.append("phase_4_walk_forward")
        if live["available"] and live["live_n"] > 0:
            sources.append("phase_5_live")
        if feature_evidence["phase_2_avg_rank"] is not None:
            sources.append("phase_2_importance")
        # INV findings + brain proposals: placeholder (empty in v1)
        inv_findings: list[str] = []
        brain_proposals: list[str] = []
        convergence_sources = {
            "phase_4_walk_forward": "phase_4_walk_forward" in sources,
            "phase_5_live": "phase_5_live" in sources,
            "phase_2_importance": "phase_2_importance" in sources,
            "inv_findings": inv_findings,
            "brain_proposals": brain_proposals,
            "count": len(sources) + len(inv_findings) + len(brain_proposals),
        }

        out.append({
            "pattern_id": pat.pattern_id,
            "anchor_combo_id": pat.anchor_combo_id,
            "supporting_combo_ids": pat.supporting_combo_ids,
            "cohort": {
                "signal_type": pat.cohort_signal_type,
                "regime": pat.cohort_regime,
                "horizon": pat.cohort_horizon,
            },
            "features": pat.features,
            "feature_count": pat.feature_count,
            "statistical_evidence": stat,
            "live_evidence": live,
            "feature_evidence": feature_evidence,
            "regime_coverage": regime_coverage,
            "convergence_sources": convergence_sources,
            "cluster_size": pat.cluster_size,
        })

    return out
