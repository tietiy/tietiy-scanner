"""Brain output — Step 6 unified proposal queue + decisions_journal init + dual-write adapter.

Per Wave 5 Step 6 design lock (V-1..V-12 + LOCK A/B/C):
- Conflict detection per §5.1 typology (kill_pattern/boost_pattern/watch_pattern
  matching; contradiction/redundant/overlap classification)
- Surfacing into counter.evidence + counter.risks + decision_metadata.conflicts_with
  per §5.1 required format (programmatic citation strings; structured list-of-dicts)
- Verification of surfacing format (§5.1 3 new violation codes — owned here per
  ee4007d state-dependent vs shape-dependent separation)
- Top-3 selection per V-1 (pure score_priority desc; alphabetical candidate_id
  tie-break for determinism)
- unified_proposals.json schema per V-2 (top-level + per-entry contracts)
- Dual-write to proposed_rules.json per V-3 scope: {kill_rule, boost_demote}
  only; brain_candidate_id round-trip field added to dual-written entries
- decisions_journal.json initialized if missing per V-4 (Step 6 owns init only;
  Step 7 owns appends after trader actions)
- run_id semantics per V-5 (brain_run_<YYYY-MM-DD>_<HHMM> IST)
- Step 7 boundary preserved per V-12 (Step 6 ends at file write; Step 7 owns
  Telegram + approval mutation dispatch)

ARCHITECTURAL NOTES:
- §5.1 violation codes (conflict_evidence_missing / conflict_risk_missing /
  conflict_metadata_missing) live in verify_conflict_surfacing() here, NOT in
  brain_verify.verify_proposal. Per ee4007d: §5.1 codes are STATE-DEPENDENT
  (need mini_scanner_rules to detect conflicts), §6 codes are pure shape.
  brain_verify owns shape; brain_output owns §5.1 semantics. Both gate entry
  to unified_proposals.json.
- decisions_journal.json is JOURNAL (append-only forever per K-4), not a
  snapshot view. Bypass brain_state.write_brain_artifact (which requires
  as_of_date + writes history archive). Use _atomic_write_journal helper.

See doc/brain_design_v1.md §5 / §5.1 / §6 / §2 (D-4 weekend behavior).
See doc/project_anchor_v1.md §7 D-2 / D-4.
Locked design commits anchoring this implementation:
  27b60cb (D-2 + D-4 amendments), 997d4af (§5.1 watch_pattern row),
  ee4007d (§5.1 verifier-location correction).
"""
import copy
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from scanner.brain import brain_state, brain_verify


_IST = timezone(timedelta(hours=5, minutes=30))
_UTC = timezone.utc

# ── Locked constants per §5.1 + V-1..V-12 ───────────────────────────
_BRAIN_DIRNAME = "brain"
_DECISIONS_JOURNAL_NAME = "decisions_journal"
_UNIFIED_PROPOSALS_NAME = "unified_proposals"

_TOP_N_DEFAULT = 3
_PROPOSAL_DEFAULT_EXPIRY_DAYS = 7  # §1 soft constraint

# Type → conflict relevance (per §5.1 table)
_INFORMATIONAL_TYPES = frozenset({"regime_alert", "exposure_warn", "cohort_review"})
_CONFLICT_RELEVANT_TYPES = frozenset({"kill_rule", "boost_promote"})

# Active-rule sources per type (per §5.1 typology)
# kill_rule conflicts with active boost_pattern (contradiction)
# boost_promote conflicts with kill_pattern (contradiction),
#                            boost_pattern (redundant or overlap),
#                            watch_pattern (overlap, per LOCK A 997d4af)
_CONFLICT_LOOKUPS = {
    "kill_rule": [
        ("boost_patterns", "contradiction"),
    ],
    "boost_promote": [
        ("kill_patterns", "contradiction"),
        ("boost_patterns", None),  # None = differentiated redundant/overlap
        ("watch_patterns", "overlap"),
    ],
}

# V-3 dual-write scope
_DUAL_WRITE_TYPES = frozenset({"kill_rule", "boost_demote"})

# Per-action mapping for dual-write (rule_proposer schema compatibility)
_DUAL_WRITE_ACTION_MAP = {
    "kill_rule": "kill",
    "boost_demote": "demote_boost",
}


# ====================================================================
# §5.1 conflict surfacing — detection + populate + verify
# ====================================================================

def _tuple_axes(candidate: dict) -> tuple:
    """Extract (signal, sector, regime) from candidate.cohort_filter
    (Step 4 stable signature populated by build_proposal_candidate
    decision_metadata.cohort_filter). Defensive fallback: parse
    cohort_filter_signature string. None on any axis = wildcard."""
    md = candidate.get("decision_metadata") or {}
    cf = md.get("cohort_filter") or {}
    if not cf:
        sig = md.get("cohort_filter_signature", "")
        if sig:
            for pair in sig.split("__"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cf[k] = v
    return (
        cf.get("signal_type") or cf.get("signal"),
        cf.get("sector"),
        cf.get("regime"),
    )


def _axis_match(a, b) -> bool:
    """Wildcard-null match per §5.1: None on either side matches anything;
    else exact equality."""
    if a is None or b is None:
        return True
    return a == b


def _tuple_match(p_tuple: tuple, r_tuple: tuple) -> bool:
    """Per §5.1 'wildcard nulls match' across (signal, sector, regime)."""
    return all(_axis_match(p, r) for p, r in zip(p_tuple, r_tuple))


def _classify_boost_promote_vs_boost_pattern(p_tuple: tuple,
                                              r_tuple: tuple) -> str:
    """Per §5.1 row: redundant if EXACT same tuple (None==None counts as
    same); overlap otherwise (at least one axis differs)."""
    if p_tuple == r_tuple:
        return "redundant"
    return "overlap"


def _build_citation(rule_id: str, signal, sector, regime, n: Any) -> str:
    """Per §5.1 required surfacing format: programmatic citation.
    Format: '<rule_id> active: <signal> × <sector> × <regime> (n=<n>)'.
    Nulls render as 'any'."""
    sig = signal or "any"
    sec = sector or "any"
    reg = regime or "any"
    return f"{rule_id} active: {sig} × {sec} × {reg} (n={n})"


def _build_risk_string(conflict_type: str) -> str:
    """Per §5.1 required surfacing format: exact-match risk string.
    Format: 'approval would propagate <conflict_type> to mini_scanner_rules.json'."""
    return (f"approval would propagate {conflict_type} "
            f"to mini_scanner_rules.json")


def _extract_rule_n(rule: dict) -> Any:
    """Best-effort n extraction from rule dict. mini_scanner_rules
    schema variants: kill_pattern.evidence.n, boost_pattern.evidence.n,
    watch_pattern.evidence.n. Returns 'unknown' if missing."""
    ev = rule.get("evidence") or {}
    return ev.get("n", "unknown")


def detect_conflicts(candidate: dict, mini_scanner_rules: dict) -> list[dict]:
    """Per §5.1 conflict definition + typology. Returns list of internal
    conflict objects with extras for citation generation. Caller passes
    to populate_conflict_surfacing.

    Returns []: candidate type is informational, no rules match, or
    proposal is boost_demote (referenced action, not conflict).

    Each returned dict: {rule_id, conflict_type, signal, sector, regime,
    n}. The first two are persisted into decision_metadata.conflicts_with;
    the remaining are used to build citation strings.
    """
    ptype = candidate.get("type")
    if ptype in _INFORMATIONAL_TYPES:
        return []
    if ptype not in _CONFLICT_RELEVANT_TYPES:
        return []

    p_tuple = _tuple_axes(candidate)
    if all(axis is None for axis in p_tuple):
        # No filter axes — defensive; should not happen for
        # conflict-relevant types per Step 4 generators.
        return []

    lookups = _CONFLICT_LOOKUPS.get(ptype, [])
    out = []

    for rule_collection_key, fixed_conflict_type in lookups:
        rules = mini_scanner_rules.get(rule_collection_key) or []
        for rule in rules:
            if not rule.get("active", False):
                continue
            r_tuple = (
                rule.get("signal"),
                rule.get("sector"),
                rule.get("regime"),
            )
            if not _tuple_match(p_tuple, r_tuple):
                continue

            if fixed_conflict_type is not None:
                conflict_type = fixed_conflict_type
            else:
                # boost_promote × boost_pattern → differentiate
                conflict_type = _classify_boost_promote_vs_boost_pattern(
                    p_tuple, r_tuple)

            out.append({
                "rule_id": rule.get("id", "unknown"),
                "conflict_type": conflict_type,
                "signal": rule.get("signal"),
                "sector": rule.get("sector"),
                "regime": rule.get("regime"),
                "n": _extract_rule_n(rule),
            })

    return out


def populate_conflict_surfacing(candidate: dict,
                                  conflicts: list[dict]) -> dict:
    """Per §5.1 required surfacing format. Mutates candidate (deep copy
    semantics — input untouched, enriched copy returned).

    For each conflict: append programmatic citation to counter.evidence[];
    set decision_metadata.conflicts_with as list-of-objects.
    For each unique conflict_type: append exact-match risk to counter.risks[].
    """
    enriched = copy.deepcopy(candidate)

    if not conflicts:
        # Ensure decision_metadata.conflicts_with key exists (empty)
        # per V-2 schema for downstream consumers.
        enriched.setdefault("decision_metadata", {})
        enriched["decision_metadata"].setdefault("conflicts_with", [])
        return enriched

    counter = enriched.setdefault("counter", {})
    counter.setdefault("evidence", [])
    counter.setdefault("risks", [])
    metadata = enriched.setdefault("decision_metadata", {})

    for conf in conflicts:
        citation = _build_citation(
            conf["rule_id"], conf["signal"], conf["sector"],
            conf["regime"], conf["n"])
        if citation not in counter["evidence"]:
            counter["evidence"].append(citation)

    seen_types: set = set()
    for conf in conflicts:
        ct = conf["conflict_type"]
        if ct in seen_types:
            continue
        seen_types.add(ct)
        risk = _build_risk_string(ct)
        if risk not in counter["risks"]:
            counter["risks"].append(risk)

    metadata["conflicts_with"] = [
        {"rule_id": c["rule_id"], "conflict_type": c["conflict_type"]}
        for c in conflicts
    ]

    return enriched


def verify_conflict_surfacing(candidate: dict,
                                mini_scanner_rules: dict) -> tuple:
    """Per §5.1 + ee4007d location lock. State-dependent semantic
    validator (needs mini_scanner_rules context). Three new violation
    codes:
      - conflict_evidence_missing
      - conflict_risk_missing
      - conflict_metadata_missing

    Re-runs detect_conflicts to catch the bypass case (candidate
    constructed without populate_conflict_surfacing).

    Returns (is_valid, violations).
    """
    violations: list[str] = []
    ptype = candidate.get("type")

    if ptype in _INFORMATIONAL_TYPES:
        return (True, [])

    metadata = candidate.get("decision_metadata") or {}
    conflicts_with = metadata.get("conflicts_with")

    detected = detect_conflicts(candidate, mini_scanner_rules)

    # conflict_metadata_missing: detector saw conflicts but persisted
    # metadata is empty/missing.
    if detected and not conflicts_with:
        violations.append("conflict_metadata_missing")
        return (False, violations)

    if not conflicts_with:
        return (True, [])

    counter = candidate.get("counter") or {}
    evidence = counter.get("evidence") or []
    risks = counter.get("risks") or []

    # conflict_evidence_missing: every persisted rule_id needs its
    # programmatic-format citation in counter.evidence.
    for entry in conflicts_with:
        rule_id = entry.get("rule_id", "")
        if not any((isinstance(e, str) and e.startswith(f"{rule_id} active: "))
                   for e in evidence):
            violations.append("conflict_evidence_missing")
            break

    # conflict_risk_missing: every unique conflict_type needs exact-match
    # risk string in counter.risks.
    unique_types = set(e.get("conflict_type") for e in conflicts_with)
    for ct in unique_types:
        expected = _build_risk_string(ct)
        if expected not in risks:
            violations.append("conflict_risk_missing")
            break

    return (len(violations) == 0, violations)


# ====================================================================
# Top-N selection (V-1)
# ====================================================================

def apply_top_n_selection(candidates: list[dict],
                           n: int = _TOP_N_DEFAULT) -> tuple[list, list]:
    """Per V-1: pure score_priority desc + alphabetical candidate_id
    tie-break for determinism.

    score_priority is read from decision_metadata.score_priority.
    Caller (orchestrator) computes via brain_verify.score_priority and
    stamps onto the candidate before this function is invoked.

    Returns (kept, dropped).
    """
    def sort_key(c: dict) -> tuple:
        score = (c.get("decision_metadata") or {}).get("score_priority", 0.0)
        cid = c.get("candidate_id", "")
        return (-float(score), cid)

    ranked = sorted(candidates, key=sort_key)
    return (ranked[:n], ranked[n:])


# ====================================================================
# unified_proposals.json entry construction (V-2)
# ====================================================================

def build_unified_proposal_entry(*,
                                   candidate: dict,
                                   unified_id: str,
                                   run_id: str,
                                   source_step: str,
                                   legacy_id: Optional[str] = None) -> dict:
    """Per V-2 schema. Builds one unified_proposals.proposals[] entry
    from a Step 5 (or Step 4-direct) candidate.

    NOTE: takes unified_id explicitly (Phase 2 design clarification on
    V-9 surface — id generation lives in orchestrator scope to track
    seq counter). Diverges from V-9 lock surface by 1 kwarg name.
    """
    now_ist = datetime.now(_IST).isoformat()
    expires_at = candidate.get("expires_at") or (
        (datetime.now(_IST) + timedelta(
            days=_PROPOSAL_DEFAULT_EXPIRY_DAYS)).isoformat())

    md = candidate.get("decision_metadata") or {}

    return {
        "id":                unified_id,
        "legacy_id":         legacy_id,
        "candidate_id":      candidate.get("candidate_id"),
        "type":              candidate.get("type"),
        "source":            candidate.get("source"),
        "source_step":       source_step,
        "run_id_origin":     run_id,
        "title":             candidate.get("title"),
        "claim":             candidate.get("claim", {}),
        "counter":           candidate.get("counter", {}),
        "reversibility":     candidate.get("reversibility", ""),
        "evidence_refs":     candidate.get("evidence_refs", []),
        "decision_metadata": md,
        "status":            "pending",
        "created_at":        now_ist,
        "expires_at":        expires_at,
        "approver":          None,
        "decision_at":       None,
        "decision_reason":   None,
    }


# ====================================================================
# decisions_journal.json (V-4) — init + append
# ====================================================================

def _decisions_journal_path(output_dir: str) -> str:
    return os.path.join(output_dir, _BRAIN_DIRNAME,
                        f"{_DECISIONS_JOURNAL_NAME}.json")


def _atomic_write_journal(path: str, payload: str) -> int:
    """Atomic write helper for journal-style files (decisions_journal).
    Bypasses brain_state.write_brain_artifact (which writes daily
    archive snapshots) — journals are append-only forever per K-4.
    """
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.{os.getpid()}.tmp"
    encoded = payload.encode("utf-8")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        n = os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp_path, path)
    return n


def init_decisions_journal_if_missing(output_dir: str = "output") -> bool:
    """Per V-4: Step 6 owns init-if-missing. Returns True if created,
    False if already existed.
    """
    path = _decisions_journal_path(output_dir)
    if os.path.exists(path):
        return False

    header = {
        "schema_version": 1,
        "view_name": _DECISIONS_JOURNAL_NAME,
        "created_at": datetime.now(_IST).isoformat(),
        "_metadata": {
            "retention_policy": "FULL_NO_PRUNE_PER_K-4_LOCK",
            "total_decisions": 0,
        },
        "entries": [],
    }
    payload = json.dumps(header, indent=2, ensure_ascii=False)
    _atomic_write_journal(path, payload)
    return True


def append_decision(*,
                    unified_proposal_id: str,
                    candidate_id: str,
                    decision: str,
                    source: str,
                    approver: str,
                    run_id_origin: str,
                    proposal_type: Optional[str] = None,
                    cohort_identity: Optional[str] = None,
                    trader_reason: Optional[str] = None,
                    decision_metadata: Optional[dict] = None,
                    output_dir: str = "output") -> None:
    """Per V-4 append. Append-only forever (K-4). Atomic via
    _atomic_write_journal.

    Step 7 is the primary caller (after trader /approve or /reject).
    Step 6 does NOT call this during run_step6 (no decisions yet).
    """
    valid_decisions = frozenset({"approve", "reject", "expired",
                                  "auto_applied", "auto_demoted"})
    valid_sources = frozenset({"telegram", "pwa_deep_link", "auto"})
    if decision not in valid_decisions:
        raise ValueError(
            f"invalid decision: {decision!r}; must be one of "
            f"{sorted(valid_decisions)}")
    if source not in valid_sources:
        raise ValueError(
            f"invalid source: {source!r}; must be one of "
            f"{sorted(valid_sources)}")

    path = _decisions_journal_path(output_dir)
    if not os.path.exists(path):
        # Defensive: should be initialized by Step 6.
        init_decisions_journal_if_missing(output_dir)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entry = {
        "timestamp":           datetime.now(_IST).isoformat(),
        "candidate_id":        candidate_id,
        "cohort_identity":     cohort_identity,
        "proposal_type":       proposal_type,
        "unified_proposal_id": unified_proposal_id,
        "decision":            decision,
        "trader_reason":       trader_reason,
        "source":              source,
        "approver":            approver,
        "run_id_origin":       run_id_origin,
        "decision_metadata":   decision_metadata or {},
    }
    data.setdefault("entries", []).append(entry)
    md = data.setdefault("_metadata", {})
    md["total_decisions"] = len(data["entries"])

    payload = json.dumps(data, indent=2, ensure_ascii=False)
    _atomic_write_journal(path, payload)


# ====================================================================
# Dual-write to proposed_rules.json (V-3)
# ====================================================================

def _build_proposed_rules_entry(candidate: dict, prop_id: str) -> dict:
    """Map brain candidate → proposed_rules.json entry per V-3 mapping
    table. Adds brain_candidate_id round-trip field."""
    ptype = candidate.get("type")
    action = _DUAL_WRITE_ACTION_MAP.get(ptype)
    if action is None:
        raise ValueError(f"type {ptype!r} not in _DUAL_WRITE_TYPES")

    md = candidate.get("decision_metadata") or {}
    cf = md.get("cohort_filter") or {}
    pre = md.get("proposed_rule_entry") or {}

    target_signal = (cf.get("signal_type") or cf.get("signal")
                     or pre.get("signal"))
    target_sector = cf.get("sector") or pre.get("sector")
    target_regime = cf.get("regime") or pre.get("regime")

    now_z = datetime.utcnow().isoformat() + "Z"

    evidence: dict = {}
    for k in ("n", "wr", "edge_pp", "tier"):
        if k in md:
            evidence[k] = md.get(k)

    base = {
        "id":                 prop_id,
        "pattern_id":         md.get("cohort_filter_signature", ""),
        "action":             action,
        "target_signal":      target_signal,
        "target_sector":      target_sector,
        "evidence":           evidence,
        "status":             "pending",
        "proposed_date":      now_z,
        "approved_date":      None,
        "approved_by":        None,
        "rejected_date":      None,
        "rejected_reason":    None,
        "last_updated":       now_z,
        "insight":            (candidate.get("claim") or {}).get(
                                  "expected_effect", ""),
        # NEW round-trip field per V-3
        "brain_candidate_id": candidate.get("candidate_id"),
        "source":             "brain_step6_dual_write",
    }
    if action == "demote_boost":
        base["target_regime"] = target_regime

    return base


def dual_write_to_proposed_rules(candidates: list[dict],
                                  run_id: str,
                                  output_dir: str = "output") -> dict:
    """Per V-3 scope: only kill_rule + boost_demote candidates. Mutates
    output/proposed_rules.json by appending new entries (preserves
    existing; counts recomputed).

    Returns summary {dual_written, skipped, written_ids, skipped_types}.
    """
    from scanner import rule_proposer  # lazy: avoids import side-effects

    eligible = [c for c in candidates
                if c.get("type") in _DUAL_WRITE_TYPES]
    skipped_types = [c.get("type") for c in candidates
                      if c.get("type") not in _DUAL_WRITE_TYPES]

    if not eligible:
        return {
            "dual_written": 0,
            "skipped": len(skipped_types),
            "written_ids": [],
            "skipped_types": skipped_types,
        }

    proposed_rules_path = os.path.join(output_dir, "proposed_rules.json")
    if os.path.exists(proposed_rules_path):
        with open(proposed_rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "schema_version": rule_proposer.SCHEMA_VERSION,
            "proposals": [],
        }

    existing = data.get("proposals", []) or []
    written_ids = []

    for cand in eligible:
        new_id = rule_proposer._generate_proposal_id(existing)
        entry = _build_proposed_rules_entry(cand, new_id)
        existing.append(entry)
        written_ids.append(new_id)

    data["proposals"] = existing
    data["pending_count"] = sum(
        1 for p in existing if p.get("status") == "pending")
    data["approved_count"] = sum(
        1 for p in existing if p.get("status") == "approved")
    data["rejected_count"] = sum(
        1 for p in existing if p.get("status") == "rejected")
    data["total_proposals"] = len(existing)

    tmp_path = proposed_rules_path + f".{os.getpid()}.tmp"
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(payload)
    os.replace(tmp_path, proposed_rules_path)

    return {
        "dual_written": len(written_ids),
        "skipped": len(skipped_types),
        "written_ids": written_ids,
        "skipped_types": skipped_types,
    }


# ====================================================================
# run_step6 orchestrator
# ====================================================================

def _stamp_score_priority(candidate: dict, derived_views: dict) -> dict:
    """Compute score_priority via brain_verify and stamp onto
    decision_metadata.score_priority. Caller passes a deep-copy."""
    score = brain_verify.score_priority(candidate, derived_views)
    candidate.setdefault("decision_metadata", {})["score_priority"] = score
    return candidate


def _extract_cohort_identity(candidate: dict) -> str:
    """Strip _<as_of_date> suffix from candidate_id for cross-day key
    per V-4 cohort_identity field."""
    cid = candidate.get("candidate_id", "")
    # Trailing pattern: _YYYY-MM-DD (length 11)
    if len(cid) > 11 and cid[-11] == "_":
        return cid[:-11]
    return cid


def run_step6(*,
              step5_kept_candidates: list[dict],
              step5_generated_alerts: list[dict],
              mini_scanner_rules: dict,
              derived_views: dict,
              run_id: str,
              as_of_date: Optional[str] = None,
              output_dir: str = "output") -> dict:
    """Step 6 orchestrator.

    Pipeline (per V-1..V-12 + LOCK A + ee4007d 4-step finalizer ordering):
      1. Combine step5 kept (filtered+enriched boost_promote) with
         step5 generated (regime_alert / exposure_warn from gates).
      2. Stamp score_priority on each (deep-copied).
      3. detect_conflicts → populate_conflict_surfacing per §5.1.
      4. verify_proposal (§6 shape) + verify_conflict_surfacing (§5.1).
         Failures logged to verification_failures.json + dropped.
      5. apply_top_n_selection (top 3, alpha tie-break).
      6. build_unified_proposal_entry per surfaced.
      7. Dual-write surfaced kill_rule + boost_demote candidates.
      8. Write unified_proposals.json (atomic + history archive).
      9. Initialize decisions_journal.json if missing.

    Step 6 NEVER fires Telegram (per V-12 boundary).
    """
    today = as_of_date or datetime.now(_IST).date().isoformat()

    all_input = list(step5_kept_candidates) + list(step5_generated_alerts)
    total_input = len(all_input)

    if total_input == 0:
        return _write_empty_unified_proposals_and_init_journal(
            run_id=run_id, as_of_date=today, output_dir=output_dir)

    # Step 2: stamp score_priority on deep-copies
    scored: list = []
    for cand in all_input:
        scored.append(_stamp_score_priority(copy.deepcopy(cand), derived_views))

    # Step 3: conflict detection + populate
    enriched: list = []
    for cand in scored:
        conflicts = detect_conflicts(cand, mini_scanner_rules)
        enriched.append(populate_conflict_surfacing(cand, conflicts))

    # Step 4: dual verification
    verified: list = []
    rejected_count = 0
    for cand in enriched:
        ok_shape, viols_shape = brain_verify.verify_proposal(cand)
        ok_conflict, viols_conflict = verify_conflict_surfacing(
            cand, mini_scanner_rules)

        if not ok_shape:
            brain_verify.log_verification_failure(
                cand, viols_shape, "brain_output.run_step6", output_dir)
            print(f"[brain_output] REJECTED §6 shape "
                  f"{cand.get('candidate_id')}: {viols_shape}",
                  file=sys.stderr)
            rejected_count += 1
            continue
        if not ok_conflict:
            brain_verify.log_verification_failure(
                cand, viols_conflict,
                "brain_output.run_step6_conflict", output_dir)
            print(f"[brain_output] REJECTED §5.1 surfacing "
                  f"{cand.get('candidate_id')}: {viols_conflict}",
                  file=sys.stderr)
            rejected_count += 1
            continue
        verified.append(cand)

    # Step 5: top-3 selection
    surfaced, dropped = apply_top_n_selection(verified, _TOP_N_DEFAULT)

    # Step 6: build unified_proposal entries
    proposals: list = []
    for i, cand in enumerate(surfaced, start=1):
        unified_id = f"prop_unified_{today}_{i:03d}"
        proposals.append(build_unified_proposal_entry(
            candidate=cand,
            unified_id=unified_id,
            run_id=run_id,
            source_step="step5_or_step4_passthrough",
            legacy_id=None,
        ))

    # Step 7: dual-write surfaced eligible types only
    dual_write_summary = dual_write_to_proposed_rules(
        surfaced, run_id, output_dir)

    # Patch legacy_id back into corresponding unified entries
    if dual_write_summary["written_ids"]:
        eligible = [c for c in surfaced
                     if c.get("type") in _DUAL_WRITE_TYPES]
        legacy_ids_iter = iter(dual_write_summary["written_ids"])
        for entry, cand in zip(proposals, surfaced):
            if cand.get("type") in _DUAL_WRITE_TYPES:
                entry["legacy_id"] = next(legacy_ids_iter, None)

    # Step 8: write unified_proposals.json
    dropped_metadata = [
        {
            "candidate_id":   c.get("candidate_id"),
            "score_priority": (c.get("decision_metadata") or {}).get(
                                  "score_priority", 0.0),
            "reason":         "below_top_3_cap",
        }
        for c in dropped
    ]

    warnings: list = []
    if dropped:
        warnings.append(f"top3_cap_dropped_{len(dropped)}_candidates")
    if rejected_count:
        warnings.append(f"verify_proposal_failures_{rejected_count}")

    unified_data = {
        "schema_version":     1,
        "view_name":          _UNIFIED_PROPOSALS_NAME,
        "as_of_date":         today,
        "run_id":             run_id,
        "_metadata": {
            "total_step5_candidates":     total_input,
            "total_surfaced":             len(surfaced),
            "total_dropped_by_top3_cap":  len(dropped),
            "total_rejected_at_verify":   rejected_count,
            "warnings":                   warnings,
            "dropped_due_to_top3_cap":    dropped_metadata,
            "dual_write_summary":         dual_write_summary,
        },
        "stats": {
            "total":     len(proposals),
            "pending":   sum(1 for p in proposals
                              if p.get("status") == "pending"),
            "approved":  0,
            "rejected":  0,
            "expired":   0,
        },
        "proposals": proposals,
    }

    write_result = brain_state.write_brain_artifact(
        _UNIFIED_PROPOSALS_NAME, unified_data, output_dir)

    # Step 9: init decisions_journal.json if missing
    journal_created = init_decisions_journal_if_missing(output_dir)

    return {
        "status":               "ok",
        "run_id":               run_id,
        "as_of_date":           today,
        "total_input":          total_input,
        "total_surfaced":       len(surfaced),
        "total_dropped":        len(dropped),
        "total_rejected":       rejected_count,
        "dual_write_summary":   dual_write_summary,
        "journal_init_action":  "created" if journal_created else "existed",
        "unified_proposals_path": write_result["current_path"],
        "unified_proposals_history_path": write_result["history_path"],
    }


def _write_empty_unified_proposals_and_init_journal(
        run_id: str, as_of_date: str, output_dir: str) -> dict:
    """Per V-7: write empty queue with warning + init journal."""
    unified_data = {
        "schema_version":  1,
        "view_name":       _UNIFIED_PROPOSALS_NAME,
        "as_of_date":      as_of_date,
        "run_id":          run_id,
        "_metadata": {
            "total_step5_candidates":     0,
            "total_surfaced":             0,
            "total_dropped_by_top3_cap":  0,
            "total_rejected_at_verify":   0,
            "warnings": ["empty_queue_no_candidates_this_cycle"],
            "dropped_due_to_top3_cap":    [],
            "dual_write_summary": {
                "dual_written": 0, "skipped": 0,
                "written_ids": [], "skipped_types": [],
            },
        },
        "stats": {"total": 0, "pending": 0, "approved": 0,
                  "rejected": 0, "expired": 0},
        "proposals": [],
    }
    write_result = brain_state.write_brain_artifact(
        _UNIFIED_PROPOSALS_NAME, unified_data, output_dir)
    journal_created = init_decisions_journal_if_missing(output_dir)
    return {
        "status":               "empty_queue",
        "run_id":               run_id,
        "as_of_date":           as_of_date,
        "total_input":          0,
        "total_surfaced":       0,
        "total_dropped":        0,
        "total_rejected":       0,
        "dual_write_summary":   unified_data["_metadata"]["dual_write_summary"],
        "journal_init_action":  "created" if journal_created else "existed",
        "unified_proposals_path": write_result["current_path"],
        "unified_proposals_history_path": write_result["history_path"],
    }
