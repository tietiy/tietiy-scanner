"""
Emission — write analyzer outputs in defined schemas.

Three emitters:
  • emit_barcodes_json:           production-facing (ACTIVE + KILL only)
  • emit_patterns_full_json:      analyzer-internal (all tiers)
  • emit_findings_synthesis:      human-readable digest (LLM-synthesized)

Schema versioning: schema_version=1 stamped on top-level dict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 1
ACTIVE_TIERS = ("ACTIVE_TAKE_FULL", "ACTIVE_TAKE_SMALL", "ACTIVE_WATCH")
PRODUCTION_TIERS = ACTIVE_TIERS + ("KILL",)
TIER_SORT_ORDER = {
    "ACTIVE_TAKE_FULL": 0, "ACTIVE_TAKE_SMALL": 1, "ACTIVE_WATCH": 2,
    "KILL": 3,
    "DORMANT_REGIME": 4, "DORMANT_INSUFFICIENT_DATA": 5,
    "DORMANT_DEFERRED": 6,
    "CANDIDATE": 7, "DEPRECATED": 8,
}


def _barcode_id(pattern_id: str) -> str:
    return f"bc_{pattern_id[:12]}"


def _sort_key(p: dict) -> tuple:
    tier = p.get("tier_classification", {}).get("tier", "DEPRECATED")
    score = p.get("scoring", {}).get("score", 0.0)
    return (TIER_SORT_ORDER.get(tier, 99), -score)


def _format_pattern_for_barcode(p: dict) -> dict:
    """Lightweight schema for production barcodes.json."""
    tier = p["tier_classification"]["tier"]
    score = p["scoring"]["score"]
    action = "REJECT" if tier == "KILL" else (
        "TAKE_FULL" if tier == "ACTIVE_TAKE_FULL" else
        "TAKE_SMALL" if tier == "ACTIVE_TAKE_SMALL" else
        "WATCH" if tier == "ACTIVE_WATCH" else "NONE")
    stat = p.get("statistical_evidence", {})
    live = p.get("live_evidence", {})
    rc = p.get("regime_coverage", {})
    return {
        "barcode_id": _barcode_id(p["pattern_id"]),
        "pattern_id": p["pattern_id"],
        "tier": tier,
        "action": action,
        "score": score,
        "cohort": p["cohort"],
        "features": p["features"],
        "feature_count": p["feature_count"],
        "mechanism": {
            "text": p.get("mechanism", "unclear"),
            "concept": p.get("mechanism_concept"),
            "clarity": p.get("mechanism_clarity", 0),
        },
        "evidence_summary": {
            "lifetime_n": stat.get("lifetime_n_test"),
            "lifetime_wr": stat.get("lifetime_test_wr"),
            "baseline_wr": stat.get("lifetime_baseline_wr"),
            "edge_pp": stat.get("lifetime_edge_pp"),
            "drift_train_test": stat.get("lifetime_drift"),
            "live_n": live.get("live_n", 0),
            "live_wr": live.get("live_wr"),
            "phase_5_tier": live.get("phase_5_tier"),
            "convergence_count": p.get("convergence_sources", {}).get("count"),
            "regimes_with_edge": rc.get("regimes_with_edge", []),
        },
        "scoring_breakdown": p.get("scoring", {}).get("sub_scores", {}),
        "scoring_profile": p.get("scoring", {}).get("profile"),
        "lifecycle": {
            "current_state": tier,
            "history": [],  # v1: empty; v2 will populate transitions
            "last_transition": None,
        },
        "relationships": {
            "subsumes": [],   # v2 placeholder
            "conflicts_with": [],
            "co_fires_with": [],
        },
    }


def emit_barcodes_json(patterns: list[dict], output_path: Path,
                          run_metadata: Optional[dict] = None) -> dict:
    """Filter to ACTIVE + KILL, sort, write JSON."""
    filtered = [p for p in patterns
                  if p.get("tier_classification", {}).get("tier")
                  in PRODUCTION_TIERS]
    sorted_p = sorted(filtered, key=_sort_key)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metadata": run_metadata or {},
        "barcodes": [_format_pattern_for_barcode(p) for p in sorted_p],
        "tier_counts": {
            t: sum(1 for p in filtered
                     if p["tier_classification"]["tier"] == t)
            for t in PRODUCTION_TIERS
        },
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, indent=2, default=str))
    return payload


def emit_patterns_full_json(patterns: list[dict], output_path: Path,
                                run_metadata: Optional[dict] = None) -> dict:
    """All patterns regardless of tier (analyzer-internal). Full evidence."""
    sorted_p = sorted(patterns, key=_sort_key)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metadata": run_metadata or {},
        "patterns": sorted_p,
        "tier_distribution": {},
    }
    # Tier distribution count
    for p in sorted_p:
        t = p.get("tier_classification", {}).get("tier", "DEPRECATED")
        payload["tier_distribution"][t] = payload["tier_distribution"].get(t, 0) + 1
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, indent=2, default=str))
    return payload


def _build_synthesis_prompt(patterns: list[dict]) -> str:
    """Build the synthesis prompt for ANALYZER_findings.md."""
    n_total = len(patterns)
    tier_counts: dict[str, int] = {}
    for p in patterns:
        t = p.get("tier_classification", {}).get("tier", "DEPRECATED")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    # Top 10 by score (regardless of tier)
    sorted_by_score = sorted(
        patterns, key=lambda p: -p.get("scoring", {}).get("score", 0))[:10]
    top_lines = []
    for p in sorted_by_score:
        feats = " & ".join(f"{f['feature_id']}={f['level']}" for f in p["features"])
        cohort = p["cohort"]
        c_str = f"{cohort['signal_type']}×{cohort['regime']}×{cohort['horizon']}"
        score = p.get("scoring", {}).get("score", 0)
        tier = p.get("tier_classification", {}).get("tier")
        clarity = p.get("mechanism_clarity", 0)
        mech = p.get("mechanism", "")
        concept = p.get("mechanism_concept")
        top_lines.append(
            f"- [{tier}] score={score:.0f} | {c_str} | {feats}\n"
            f"  mechanism (clarity {clarity}, concept={concept}): {mech}")

    # Mechanism clarity distribution
    clar = [p.get("mechanism_clarity", 0) for p in patterns]
    high_clar = sum(1 for c in clar if c >= 80)
    mid_clar = sum(1 for c in clar if 50 <= c < 80)
    low_clar = sum(1 for c in clar if c < 50)

    return f"""You are summarizing a quantitative analyzer's first pass over a portfolio of trading rule candidates. Write a concise findings markdown digest with the sections listed.

Run statistics:
- Total unified patterns: {n_total}
- Tier distribution: {json.dumps(tier_counts)}
- Mechanism clarity: {high_clar} high (≥80), {mid_clar} mid (50-79), {low_clar} low (<50)

Top 10 patterns by score (any tier):
{chr(10).join(top_lines)}

Write 5 short markdown sections (each 3-6 sentences):

## Run summary
What this analyzer pass produced. Tier distribution interpretation. Any concerns about distribution shape (e.g., too many DORMANT, too few ACTIVE_FULL).

## Top patterns surfaced
Discuss 2-3 of the top patterns above. Why are they interesting? What mechanism underlies them?

## Mechanism clarity assessment
What % of patterns have clear mechanisms (clarity ≥80) vs reach explanations (<50)? Are the high-clarity patterns concentrated in any cohort? Honest assessment.

## Concerns
Any patterns where statistical evidence is strong but mechanism is unclear (high score + low clarity)? Any tier classifications that look mis-calibrated? Be specific.

## Production readiness
Of the ACTIVE_* tier patterns, which feel production-ready vs which need more evidence? Any DORMANT patterns that look promising for activation when conditions return?

Use plain markdown, no fluff, no preambles.
"""


def emit_findings_synthesis(patterns: list[dict],
                                 output_path: Path,
                                 llm_client,
                                 run_metadata: Optional[dict] = None) -> dict:
    """Generate ANALYZER_findings.md via single LLM synthesis call."""
    prompt = _build_synthesis_prompt(patterns)
    raw = llm_client.synthesize_findings(prompt, max_tokens=2500)

    # Compose final markdown with our own header + LLM body + cost summary
    n_total = len(patterns)
    tier_counts: dict[str, int] = {}
    for p in patterns:
        t = p.get("tier_classification", {}).get("tier", "DEPRECATED")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    cost_total = getattr(llm_client, "total_cost", 0.0)
    cache_hits = getattr(llm_client, "cache_hits", 0)
    total_calls = getattr(llm_client, "total_calls", 0)

    header = (
        f"# ANALYZER findings (run {datetime.utcnow().isoformat()}Z)\n\n"
        f"**Total patterns:** {n_total}\n\n"
        f"**Tier distribution:**\n"
        f"```\n{json.dumps(tier_counts, indent=2)}\n```\n\n"
        f"---\n\n"
    )
    cost_section = (
        f"\n---\n\n## Cost summary\n\n"
        f"- LLM calls: {total_calls}\n"
        f"- Cache hits: {cache_hits}\n"
        f"- Total cost: ${cost_total:.3f}\n"
    )
    body = header + raw + cost_section

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(body)
    return {
        "schema_version": SCHEMA_VERSION,
        "tier_counts": tier_counts,
        "cost_total": cost_total,
        "cache_hits": cache_hits,
        "total_calls": total_calls,
    }
