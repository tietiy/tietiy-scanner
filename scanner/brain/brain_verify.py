"""Brain verify — pre-verification framework + 4 deterministic candidate generators.

Per Y' architecture lock (Step 4 design pass): brain_verify ships
- verification framework (verify_proposal + build_proposal_candidate +
  score_priority + log_verification_failure) per §6 schema rules;
- 4 deterministic candidate generators (boost_promote / boost_demote /
  cohort_review / kill_rule brain-side) consuming Step 3 derived views;
- run_step4 orchestrator piping all candidates through verify.

Step 5 LLM gates layer on top to produce regime_alert + exposure_warn
+ enrich Step 4 candidates with deeper synthesis.

LOCKS:
- 16 violation codes per V-1 taxonomy
- IRREVERSIBLE_ALLOWLIST = frozenset() per §6 (no irreversible types)
- expires_at INFORMATIONAL ONLY for Wave 5; Step 5/6 don't filter
- candidate_id stable per cohort identity (V-2 CORRECTION 1):
  brain_<type>_<cohort_axis>_<filter_signature>_<as_of_date>
- proposed_rule_entry mirrors mini_scanner_rules schema per V-2 CORRECTION 3:
  boost_patterns: id/active/signal/sector/regime/tier/conviction_tag/...
  kill_patterns:  id/active/signal/sector/[regime extension]/reason/...
- score_priority: type_w + confidence_w + log10(n+1) cap 2.0 + tier_w

See doc/brain_design_v1.md §3 (tier classifier), §5 (proposal types),
§6 (claim/counter/effect/reversibility format).
See doc/wave5_prerequisites_2026-04-27.md S-6 (mini_scanner regime-axis
defensive read; surfaces only when first brain-side kill_rule candidate
ships approved with regime axis).
"""
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from scanner.brain import brain_state


_IST = timezone(timedelta(hours=5, minutes=30))
_UTC = timezone.utc

# ── Locks ─────────────────────────────────────────────────────────────
IRREVERSIBLE_ALLOWLIST: frozenset = frozenset()  # §6: empty per spec

_VALID_TYPES = frozenset({
    "kill_rule", "boost_promote", "boost_demote",
    "regime_alert", "exposure_warn", "cohort_review", "query_promote",
})
_VALID_CONFIDENCES = frozenset({"high", "medium", "low"})

_TYPE_REQUIRES_FILTER = frozenset({
    "boost_promote", "boost_demote", "kill_rule", "cohort_review",
})

# Tier-to-rule schema mapping (§3 + V-10 CORRECTION 3 lock)
_TIER_TO_RULE = {
    "S": ("A", "TAKE_FULL"),
    "M": ("B", "TAKE_SMALL"),
}

# score_priority weights (V-3)
_TYPE_WEIGHTS = {
    "kill_rule":      4.0,
    "boost_promote":  3.0,
    "regime_alert":   2.0,
    "exposure_warn":  2.0,
    "cohort_review":  1.0,
    "query_promote":  1.0,
    "boost_demote":   0.0,
}
_CONFIDENCE_WEIGHTS = {"high": 3.0, "medium": 2.0, "low": 1.0}
_TIER_WEIGHTS = {"S": 3.0, "M": 2.0, "W": 1.0, "Candidate": 0.0}

# kill_rule generation gates (V-13)
_KILL_MIN_N = 10
_KILL_EDGE_THRESHOLD_PP = -10.0  # cohort must be ≤ -10pp below baseline

# verification_failures retention (V-4)
_FAILURES_MAX_RETENTION = 1000


# ====================================================================
# Verification framework (V-1 through V-9)
# ====================================================================

def verify_proposal(p: dict) -> tuple[bool, list[str]]:
    """Returns (is_valid, violations) where violations is list of V-1
    violation codes. Empty violations list ⇒ valid.
    """
    violations: list[str] = []

    # Structural
    ptype = p.get("type")
    if ptype not in _VALID_TYPES:
        violations.append("missing_type")
    if not p.get("source"):
        violations.append("missing_source")
    if not p.get("title"):
        violations.append("missing_title")

    # Claim
    claim = p.get("claim")
    if not isinstance(claim, dict):
        violations.append("missing_claim_dict")
        claim = {}

    if not (isinstance(claim.get("what"), str) and claim["what"].strip()):
        violations.append("missing_claim_what")
    if not (isinstance(claim.get("expected_effect"), str)
            and claim["expected_effect"].strip()):
        violations.append("missing_claim_expected_effect")
    if "confidence" not in claim:
        violations.append("missing_claim_confidence")
    elif claim["confidence"] not in _VALID_CONFIDENCES:
        violations.append("invalid_claim_confidence")

    # Counter
    counter = p.get("counter")
    if not isinstance(counter, dict):
        violations.append("missing_counter_dict")
        counter = {}

    counter_evidence = counter.get("evidence")
    if counter_evidence is None:
        violations.append("missing_counter_evidence_field")
    elif isinstance(counter_evidence, list) and len(counter_evidence) == 0:
        # §6: empty allowed only if confidence=high AND no_counter_rationale populated
        md = p.get("decision_metadata", {}) or {}
        rationale = md.get("no_counter_rationale", "")
        rationale_ok = isinstance(rationale, str) and rationale.strip()
        confidence_high = claim.get("confidence") == "high"
        if not (confidence_high and rationale_ok):
            violations.append("missing_counter_evidence_without_rationale")

    counter_risks = counter.get("risks")
    if not isinstance(counter_risks, list) or len(counter_risks) == 0:
        violations.append("empty_counter_risks")

    # Reversibility
    reversibility = p.get("reversibility")
    if not (isinstance(reversibility, str) and reversibility.strip()):
        violations.append("missing_reversibility")
    elif "IRREVERSIBLE" in reversibility and ptype not in IRREVERSIBLE_ALLOWLIST:
        violations.append("irreversible_outside_allowlist")

    # evidence_refs
    refs = p.get("evidence_refs")
    if not isinstance(refs, list) or len(refs) == 0:
        violations.append("missing_evidence_refs")
    elif any((not isinstance(r, str)) or (not r.strip()) for r in refs):
        violations.append("invalid_evidence_ref_format")

    return (len(violations) == 0, violations)


def build_proposal_candidate(
    *,
    proposal_type: str,
    source: str,
    source_view: str,
    title: str,
    claim_what: str,
    claim_expected_effect: str,
    claim_confidence: str,
    counter_evidence: list,
    counter_risks: list,
    reversibility: str,
    evidence_refs: list,
    cohort_filter_signature: Optional[str] = None,
    cohort_axis: Optional[str] = None,
    decision_metadata: Optional[dict] = None,
    legacy_id: Optional[str] = None,
    as_of_date: Optional[str] = None,
) -> dict:
    """Constructor producing §5-shaped candidate dict.

    Per V-2 CORRECTION 1: candidate_id derived from stable cohort
    identity (cohort_axis + cohort_filter_signature + as_of_date), NOT
    content hash. Same cohort produces consistent prefix across runs.

    Per V-2 CORRECTION 2: expires_at populated for §5 compliance but
    informational only at Wave 5.
    """
    if proposal_type not in _VALID_TYPES:
        raise ValueError(f"invalid proposal_type: {proposal_type!r}")

    today = as_of_date or datetime.now(_IST).date().isoformat()
    now_utc = datetime.now(_UTC).isoformat()
    now_ist = datetime.now(_IST).isoformat()

    if proposal_type in _TYPE_REQUIRES_FILTER:
        if not cohort_filter_signature:
            raise ValueError(
                f"proposal_type={proposal_type!r} requires "
                f"cohort_filter_signature kwarg")

    # candidate_id per CORRECTION 1
    if proposal_type in ("boost_promote", "boost_demote"):
        candidate_id = (f"brain_{proposal_type}_{cohort_axis}_"
                        f"{cohort_filter_signature}_{today}")
    elif proposal_type == "kill_rule":
        candidate_id = (f"brain_kill_rule_"
                        f"{cohort_filter_signature}_{today}")
    elif proposal_type == "cohort_review":
        # cohort_filter_signature carries the thin_id (rule_id or pattern_id)
        candidate_id = (f"brain_cohort_review_"
                        f"{cohort_filter_signature}_{today}")
    else:
        # regime_alert / exposure_warn / query_promote: Step 5 owns
        # IDs; here we fall back to a content hash for completeness
        h = hashlib.sha256(
            (title + claim_what).encode("utf-8")
        ).hexdigest()[:8]
        candidate_id = f"brain_{proposal_type}_{h}_{today}"

    expires_at = (datetime.fromisoformat(now_ist)
                  + timedelta(days=7)).isoformat()

    return {
        "candidate_id": candidate_id,
        "type": proposal_type,
        "source": source,
        "source_view": source_view,
        "legacy_id": legacy_id,
        "title": title,
        "claim": {
            "what": claim_what,
            "expected_effect": claim_expected_effect,
            "confidence": claim_confidence,
        },
        "counter": {
            "evidence": counter_evidence,
            "risks": counter_risks,
        },
        "reversibility": reversibility,
        "evidence_refs": evidence_refs,
        "decision_metadata": decision_metadata or {},
        "status": "pending",
        "generated_at": now_ist,
        "created_at": now_ist,
        "expires_at": expires_at,
        "approver": None,
        "decision_at": None,
        "decision_reason": None,
    }


def score_priority(p: dict, derived_views: dict) -> float:
    """Heuristic ranking — higher score = higher priority for top-3.
    Pure deterministic; no LLM. Step 5 may layer LLM re-ranking.
    """
    type_score = _TYPE_WEIGHTS.get(p.get("type"), 0.0)
    conf_score = _CONFIDENCE_WEIGHTS.get(
        (p.get("claim") or {}).get("confidence"), 0.0)

    md = p.get("decision_metadata") or {}
    n = md.get("n", 0) or 0
    n_score = min(math.log10(n + 1), 2.0) if n > 0 else 0.0

    tier = md.get("tier", "Candidate")
    tier_score = _TIER_WEIGHTS.get(tier, 0.0)

    return round(type_score + conf_score + n_score + tier_score, 2)


def log_verification_failure(p: dict, violations: list,
                              source_caller: str,
                              output_dir: str = "output") -> None:
    """Append failure entry to output/brain/verification_failures.json
    (1000-entry cap; oldest dropped on overflow).
    """
    path = os.path.join(output_dir, "brain", "verification_failures.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {
            "schema_version": 1,
            "view_name": "verification_failures",
            "max_retention": _FAILURES_MAX_RETENTION,
            "failures": [],
        }

    failures = existing.get("failures", [])
    failures.append({
        "failed_at": datetime.now(_IST).isoformat(),
        "source_caller": source_caller,
        "candidate_input": p,
        "violations": violations,
    })
    # Cap at last 1000
    if len(failures) > _FAILURES_MAX_RETENTION:
        failures = failures[-_FAILURES_MAX_RETENTION:]
    existing["failures"] = failures

    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    payload = json.dumps(existing, indent=2, ensure_ascii=False)
    tmp_path = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp_path, path)


# ====================================================================
# Deterministic candidate generators (V-10 through V-13)
# ====================================================================

def _short_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def _cohort_filter_signature(cohort_filter: dict) -> str:
    """Deterministic from filter dict (sorted keys; same as Step 3
    _cohort_id helper)."""
    parts = [f"{k}={cohort_filter[k]}" for k in sorted(cohort_filter.keys())]
    return "__".join(parts)


def generate_boost_promote_candidates(cohort_health: dict) -> list:
    """V-10: Tier M+S cohorts → boost_promote candidates.
    Mirrors mini_scanner_rules.boost_patterns[] schema in
    decision_metadata.proposed_rule_entry per CORRECTION 3.
    """
    candidates = []
    for cohort in cohort_health.get("cohorts", []):
        tier = cohort.get("tier")
        if tier not in ("M", "S"):
            continue

        cf = cohort.get("cohort_filter", {})
        signature = _cohort_filter_signature(cf)
        rule_tier, conviction_tag = _TIER_TO_RULE[tier]

        sig_type = cf.get("signal_type")
        sector = cf.get("sector")
        regime = cf.get("regime")

        # Rule entry mirroring boost_patterns[] schema
        rule_id = f"boost_brain_{_short_hash(signature)}"
        rule_entry = {
            "id": rule_id,
            "active": True,
            "signal": sig_type,
            "sector": sector,
            "regime": regime,
            "tier": rule_tier,
            "conviction_tag": conviction_tag,
            "reason": (f"brain_step4: cohort Tier {tier}, n={cohort['n']}, "
                       f"wr={cohort['wr']*100:.1f}%, "
                       f"edge {cohort['edge_vs_baseline_pp']:+.1f}pp"),
            "added_date": None,
            "source": "brain_step4",
            "evidence": {
                "wr": cohort["wr"],
                "n": cohort["n"],
                "tier": "validated",
            },
        }

        # Counter evidence (V-14): 2 deterministic strings
        counter_ev = [
            (f"Wilson 95% lower bound {cohort['wr_wilson_lower']:.4f} "
             f"{'well above' if cohort['wr_wilson_lower'] >= 0.65 else 'near'} "
             f"Tier {'S' if tier == 'S' else 'M'} floor — sample size adequate"),
        ]
        if "r_multiple" in cohort:
            r_mult = cohort["r_multiple"]
            if tier == "M":
                counter_ev.append(
                    f"R-multiple {r_mult} below Tier S threshold (1.0); "
                    f"promotion is to Tier M (B/TAKE_SMALL) only, "
                    f"not Tier S (A/TAKE_FULL)")
            else:  # S
                counter_ev.append(
                    f"R-multiple {r_mult} meets Tier S threshold (≥1.0)")

        # Counter risks: cross-view checks (V-14)
        risks = [
            (f"Cohort tier may drift on next archive comparison; "
             f"demotion auto-fires per §3"),
            ("R-multiple distribution under D-8 review (Day-6 forced-exit "
             "dominance per project_anchor §7 D-8)"),
        ]

        title = (f"{sig_type} × {regime or sector}: n={cohort['n']}, "
                 f"{cohort['wr']*100:.1f}% WR, Tier {tier} "
                 f"→ boost candidate ({conviction_tag})")

        match_descr = []
        if sig_type: match_descr.append(f"signal={sig_type}")
        if regime: match_descr.append(f"regime={regime}")
        if sector: match_descr.append(f"sector={sector}")

        candidate = build_proposal_candidate(
            proposal_type="boost_promote",
            source="brain_step4",
            source_view="cohort_health",
            title=title,
            claim_what=(f"Promote boost_pattern: {', '.join(match_descr)} "
                        f"(Tier {rule_tier} / {conviction_tag})"),
            claim_expected_effect=(
                f"Surface as Tier-{rule_tier} boost on cohort matches; "
                f"observed {cohort['edge_vs_baseline_pp']:+.1f}pp edge over "
                f"per-signal baseline"),
            claim_confidence="high",
            counter_evidence=counter_ev,
            counter_risks=risks,
            reversibility="1-line revert in mini_scanner_rules.json boost_patterns[]",
            evidence_refs=[
                f"cohort_health.json#{cohort['cohort_id']}",
                f"patterns.json#sig={sig_type}",
            ],
            cohort_filter_signature=signature,
            cohort_axis=cohort.get("cohort_axis"),
            decision_metadata={
                "tier": tier,
                "n": cohort["n"],
                "wr": cohort["wr"],
                "wr_wilson_lower": cohort["wr_wilson_lower"],
                "edge_pp": cohort["edge_vs_baseline_pp"],
                "r_multiple": cohort.get("r_multiple"),
                "cohort_axis": cohort.get("cohort_axis"),
                "cohort_filter": cf,
                "proposed_rule_entry": rule_entry,
            },
        )
        candidates.append(candidate)
    return candidates


def generate_boost_demote_candidates(cohort_health: dict,
                                     prior_archive: Optional[dict]) -> list:
    """V-11: tier transition vs prior archive. First-run (None prior) → []."""
    if prior_archive is None:
        return []

    prior_by_id = {c["cohort_id"]: c
                   for c in prior_archive.get("cohorts", [])}
    tier_order = ["Candidate", "W", "M", "S"]

    candidates = []
    for cohort in cohort_health.get("cohorts", []):
        cohort_id = cohort["cohort_id"]
        prior = prior_by_id.get(cohort_id)
        if not prior:
            continue
        prior_tier = prior.get("tier", "Candidate")
        current_tier = cohort.get("tier", "Candidate")
        try:
            prior_idx = tier_order.index(prior_tier)
            current_idx = tier_order.index(current_tier)
        except ValueError:
            continue
        if current_idx >= prior_idx:
            # not a demotion (same or improved)
            continue

        cf = cohort.get("cohort_filter", {})
        signature = _cohort_filter_signature(cf)
        sig_type = cf.get("signal_type")
        sector = cf.get("sector")
        regime = cf.get("regime")

        # Mutation form (CORRECTION 3): set_fields per current_tier
        if current_tier in _TIER_TO_RULE:
            new_rule_tier, new_conv = _TIER_TO_RULE[current_tier]
            set_fields = {"tier": new_rule_tier, "conviction_tag": new_conv}
        else:
            # Demotion below W → deactivate
            set_fields = {"active": False}

        target_match = {"signal": sig_type}
        if sector is not None:
            target_match["sector"] = sector
        if regime is not None:
            target_match["regime"] = regime

        candidate = build_proposal_candidate(
            proposal_type="boost_demote",
            source="brain_step4",
            source_view="cohort_health",
            title=(f"{sig_type} × {regime or sector}: tier dropped "
                   f"{prior_tier} → {current_tier} (audit log)"),
            claim_what=(f"Auto-demote boost_pattern: signal={sig_type} "
                        f"from prior tier {prior_tier} to {current_tier}"),
            claim_expected_effect=(
                f"Influence on bucket assignment reduces; "
                f"set_fields={set_fields}"),
            claim_confidence="high",
            counter_evidence=[],  # empty allowed: confidence=high + rationale
            counter_risks=[
                ("Demotion may underweight cohort if drop is sampling noise "
                 "rather than real edge decay"),
            ],
            reversibility=(
                "Demotion auto-reverses when next archive shows "
                "prior-tier threshold met again"),
            evidence_refs=[
                f"cohort_health.json#{cohort_id}",
                f"brain/history/<prior_date>_cohort_health.json#{cohort_id}",
            ],
            cohort_filter_signature=signature,
            cohort_axis=cohort.get("cohort_axis"),
            decision_metadata={
                "prior_tier": prior_tier,
                "current_tier": current_tier,
                "cohort_axis": cohort.get("cohort_axis"),
                "cohort_filter": cf,
                "no_counter_rationale": (
                    "Auto-demote per brain_design §3; not subject to "
                    "approval (informational audit entry)"),
                "proposed_rule_mutation": {
                    "target_rule_match": target_match,
                    "set_fields": set_fields,
                },
            },
        )
        candidates.append(candidate)
    return candidates


def generate_cohort_review_candidates(ground_truth_gaps: dict) -> list:
    """V-12: 1 per thin_rule + 1 per thin_pattern."""
    candidates = []
    today = datetime.now(_IST).date().isoformat()

    for thin in ground_truth_gaps.get("thin_rules", []):
        rule_id = thin.get("rule_id", "?")
        n_obs = thin.get("n", 0)
        kind = thin.get("rule_source_kind", "rule")
        candidate = build_proposal_candidate(
            proposal_type="cohort_review",
            source="brain_step4",
            source_view="ground_truth_gaps",
            title=f"Investigate thin {kind}: {rule_id} (n={n_obs})",
            claim_what=(f"Investigate cohort_health for {kind} {rule_id}: "
                        f"rule active in mini_scanner_rules with n={n_obs} "
                        f"below thin threshold"),
            claim_expected_effect=(
                "Determine whether evidence is genuinely thin or "
                "instrumentation gap (M-13 territory)"),
            claim_confidence="low",
            counter_evidence=[
                (f"Sample n={n_obs} below threshold but rule may have "
                 f"been seeded with backtest_derived data"),
            ],
            counter_risks=[
                ("Investigation may surface need for rule deactivation "
                 "if thinness is real"),
                ("Rule may already be performing well; investigation "
                 "overhead without action"),
            ],
            reversibility="Investigation only; no rule mutation",
            evidence_refs=[
                f"ground_truth_gaps.json#thin_rules/{rule_id}",
                f"mini_scanner_rules.json#{kind}/{rule_id}",
            ],
            cohort_filter_signature=rule_id,
            decision_metadata={
                "rule_source_kind": kind,
                "rule_id": rule_id,
                "n_observed": n_obs,
                "n_threshold": ground_truth_gaps.get(
                    "_metadata", {}).get("n_threshold_thin", 5),
            },
        )
        candidates.append(candidate)

    for thin in ground_truth_gaps.get("thin_patterns", []):
        pattern_id = thin.get("pattern_id", "?")
        n_obs = thin.get("n", 0)
        candidate = build_proposal_candidate(
            proposal_type="cohort_review",
            source="brain_step4",
            source_view="ground_truth_gaps",
            title=f"Investigate thin pattern: {pattern_id} (n={n_obs})",
            claim_what=(f"Investigate pattern {pattern_id}: n={n_obs} "
                        f"below preliminary tier threshold"),
            claim_expected_effect="Determine if pattern warrants further data collection",
            claim_confidence="low",
            counter_evidence=[
                f"Pattern n={n_obs} below preliminary tier; signal-noise unclear",
            ],
            counter_risks=[
                "Investigation overhead without action",
                "Pattern may be artifact of feature combo explosion",
            ],
            reversibility="Investigation only; no rule mutation",
            evidence_refs=[
                f"ground_truth_gaps.json#thin_patterns/{pattern_id}",
                f"patterns.json#{pattern_id}",
            ],
            cohort_filter_signature=pattern_id,
            decision_metadata={
                "pattern_id": pattern_id,
                "n_observed": n_obs,
            },
        )
        candidates.append(candidate)

    return candidates


def generate_kill_rule_candidates_brain_side(
        cohort_health: dict,
        proposed_rules: dict,
        mini_scanner_rules: dict) -> list:
    """V-13: 5-rule suppression check; deduplicates against rule_proposer
    + active mini_scanner_rules.kill_patterns. Today: 0 candidates after
    dedup expected.
    """
    # Build dedup sets
    active_kills = mini_scanner_rules.get("kill_patterns", []) or []
    pending_props = proposed_rules.get("proposals", []) or []

    def _matches_active_kill(sig_type, regime, sector):
        for k in active_kills:
            if not k.get("active", False):
                continue
            if k.get("signal") != sig_type:
                continue
            if k.get("sector") and k["sector"] != sector:
                continue
            if k.get("regime") and k["regime"] != regime:
                continue
            return True
        return False

    def _matches_existing_proposal(sig_type, regime, sector):
        for p in pending_props:
            if p.get("target_signal") != sig_type:
                continue
            if p.get("target_sector") and p["target_sector"] != sector:
                continue
            return True
        return False

    candidates = []
    suppressions = []  # logged for transparency
    for cohort in cohort_health.get("cohorts", []):
        if cohort.get("tier") != "Candidate":
            continue
        if cohort.get("n", 0) < _KILL_MIN_N:
            continue
        edge_pp = cohort.get("edge_vs_baseline_pp", 0)
        if edge_pp > _KILL_EDGE_THRESHOLD_PP:
            suppressions.append((cohort["cohort_id"],
                                 f"edge_pp={edge_pp} > -10pp threshold"))
            continue

        cf = cohort.get("cohort_filter", {})
        sig_type = cf.get("signal_type")
        sector = cf.get("sector")
        regime = cf.get("regime")

        if _matches_active_kill(sig_type, regime, sector):
            suppressions.append((cohort["cohort_id"],
                                 "matches active kill_pattern"))
            continue
        if _matches_existing_proposal(sig_type, regime, sector):
            suppressions.append((cohort["cohort_id"],
                                 "matches existing proposed_rules entry"))
            continue

        signature = _cohort_filter_signature(cf)
        rule_id = f"kill_brain_{_short_hash(signature)}"
        rule_entry = {
            "id": rule_id,
            "active": True,
            "signal": sig_type,
            "sector": sector,
            "regime": regime,  # extension per S-6
            "reason": (f"brain_step4: cohort Tier Candidate, n={cohort['n']}, "
                       f"wr={cohort['wr']*100:.1f}%, "
                       f"edge {edge_pp:+.1f}pp below baseline"),
            "added_date": None,
            "source": "brain_step4",
            "evidence": {
                "wr": cohort["wr"],
                "n": cohort["n"],
                "avg_pnl": cohort.get("avg_pnl_pct", 0),
                "avg_mae": None,
                "avg_mfe": None,
                "tier": "preliminary",
            },
            "contra_shadow_tracked": False,
        }

        match_descr = []
        if sig_type: match_descr.append(f"signal={sig_type}")
        if sector: match_descr.append(f"sector={sector}")
        if regime: match_descr.append(f"regime={regime}")

        candidate = build_proposal_candidate(
            proposal_type="kill_rule",
            source="brain_step4",
            source_view="cohort_health",
            title=(f"{sig_type} × {regime or sector}: n={cohort['n']}, "
                   f"{cohort['wr']*100:.1f}% WR, edge {edge_pp:+.1f}pp "
                   f"→ kill candidate"),
            claim_what=(f"Add kill_pattern: {', '.join(match_descr)}"),
            claim_expected_effect=(
                f"Block ~{cohort['n']//6} signals/month at "
                f"{edge_pp:+.1f}pp edge"),
            claim_confidence="high",
            counter_evidence=[
                (f"Edge {edge_pp:+.1f}pp materially below baseline "
                 f"(threshold {_KILL_EDGE_THRESHOLD_PP}pp)"),
                (f"Sample n={cohort['n']} above kill_rule minimum "
                 f"({_KILL_MIN_N})"),
            ],
            counter_risks=[
                ("Regime mean reversion may invalidate kill if regime shifts"),
                ("Baseline shift if signal mix changes meaningfully"),
            ],
            reversibility="1-line revert in mini_scanner_rules.json kill_patterns[]",
            evidence_refs=[
                f"cohort_health.json#{cohort['cohort_id']}",
                f"patterns.json#sig={sig_type}",
            ],
            cohort_filter_signature=signature,
            decision_metadata={
                "tier": "Candidate",
                "n": cohort["n"],
                "wr": cohort["wr"],
                "edge_pp": edge_pp,
                "cohort_axis": cohort.get("cohort_axis"),
                "cohort_filter": cf,
                "proposed_rule_entry": rule_entry,
            },
        )
        candidates.append(candidate)

    if suppressions:
        for cohort_id, reason in suppressions:
            print(f"[brain_verify.kill_rule] suppressed {cohort_id}: {reason}",
                  file=sys.stderr)

    return candidates


# ====================================================================
# Orchestrator (V-9)
# ====================================================================

def run_step4(derived_views: dict,
              prior_archives: Optional[dict] = None,
              proposed_rules: Optional[dict] = None,
              mini_scanner_rules: Optional[dict] = None,
              output_dir: str = "output") -> list:
    """Pipes all candidates through verify_proposal; rejects malformed
    (logged via log_verification_failure); returns clean ranked list
    sorted by score_priority desc.
    """
    cohort_health = derived_views.get("cohort_health", {}) or {}
    ground_truth_gaps = derived_views.get("ground_truth_gaps", {}) or {}
    prior_archives = prior_archives or {}
    proposed_rules = proposed_rules or {}
    mini_scanner_rules = mini_scanner_rules or {}

    raw_candidates: list = []
    raw_candidates.extend(generate_boost_promote_candidates(cohort_health))
    raw_candidates.extend(generate_boost_demote_candidates(
        cohort_health, prior_archives.get("cohort_health")))
    raw_candidates.extend(generate_cohort_review_candidates(ground_truth_gaps))
    raw_candidates.extend(generate_kill_rule_candidates_brain_side(
        cohort_health, proposed_rules, mini_scanner_rules))

    clean: list = []
    for cand in raw_candidates:
        is_valid, violations = verify_proposal(cand)
        if not is_valid:
            log_verification_failure(
                cand, violations, "brain_verify.run_step4", output_dir)
            print(f"[brain_verify.run_step4] REJECTED "
                  f"{cand.get('candidate_id')}: {violations}",
                  file=sys.stderr)
            continue
        clean.append(cand)

    # Sort by priority desc; stable sort preserves original order on ties
    clean.sort(key=lambda c: score_priority(c, derived_views), reverse=True)
    return clean
