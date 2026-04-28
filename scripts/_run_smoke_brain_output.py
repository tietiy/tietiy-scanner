"""Wave 5 Step 6 smoke — brain_output unified queue + decisions_journal +
dual-write adapter + §5.1 conflict surfacing.

Per CLAUDE.md §4 sandbox pattern + V-10 smoke contract.

8 groups (A-H):
  A — top-3 selection (0 / 1 / 3 / 4 / 10 candidate counts; alpha tie-break)
  B — unified_proposals.json schema validation (V-2)
  C — dual-write scope (V-3): kill_rule + boost_demote + boost_promote +
      regime_alert mock; only first 2 written; brain_candidate_id round-trip
  D — decisions_journal init + append + idempotency (V-4)
  E — §5.1 conflict surfacing on real today's data (C1 → 6 overlaps;
      C2 → 2 overlaps incl. watch_001 per LOCK A)
  F — empty queue handling (V-7)
  G — rule_proposer adapter wiring (verify legacy_id round-trips)
  H — SHA256 invariants on real signal_history + cohort_health +
      reasoning_log + proposed_rules + mini_scanner_rules
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

REAL_HISTORY        = os.path.join(ROOT, "output", "signal_history.json")
REAL_PROPOSED       = os.path.join(ROOT, "output", "proposed_rules.json")
REAL_MINI           = os.path.join(ROOT, "data", "mini_scanner_rules.json")
REAL_COHORT_HEALTH  = os.path.join(ROOT, "output", "brain", "cohort_health.json")
REAL_REGIME_WATCH   = os.path.join(ROOT, "output", "brain", "regime_watch.json")
REAL_PORTFOLIO      = os.path.join(ROOT, "output", "brain", "portfolio_exposure.json")
REAL_GTG            = os.path.join(ROOT, "output", "brain", "ground_truth_gaps.json")
REAL_REASONING_LOG  = os.path.join(ROOT, "output", "brain", "reasoning_log.json")


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _make_candidate(*, proposal_type, candidate_id_suffix, score=5.0,
                    cohort_filter=None, claim_confidence="high",
                    extra_metadata=None):
    """Build a synthetic candidate with all §6-required fields."""
    md = {"score_priority": score}
    if cohort_filter is not None:
        md["cohort_filter"] = cohort_filter
    if extra_metadata:
        md.update(extra_metadata)

    return {
        "candidate_id": f"brain_{proposal_type}_{candidate_id_suffix}_2026-04-29",
        "type": proposal_type,
        "source": "brain_step4_smoke",
        "title": f"Smoke {proposal_type} {candidate_id_suffix}",
        "claim": {
            "what": f"Promote {proposal_type}: smoke",
            "expected_effect": "Surface for testing",
            "confidence": claim_confidence,
        },
        "counter": {
            "evidence": ["smoke evidence"],
            "risks": ["smoke risk"],
        },
        "reversibility": "1-line revert in test",
        "evidence_refs": ["test#1"],
        "decision_metadata": md,
    }


def _run_group_A(sbx_output):
    """Top-3 selection (V-1)."""
    from scanner.brain.brain_output import apply_top_n_selection

    # A1: 0 candidates
    kept, dropped = apply_top_n_selection([], n=3)
    assert kept == [] and dropped == [], f"A1 0-case: {kept} / {dropped}"

    # A2: 1 candidate
    c1 = _make_candidate(proposal_type="boost_promote", candidate_id_suffix="a", score=5.0)
    kept, dropped = apply_top_n_selection([c1], n=3)
    assert len(kept) == 1 and len(dropped) == 0, f"A2 1-case: {len(kept)}/{len(dropped)}"

    # A3: 3 candidates (no drop)
    cs = [_make_candidate(proposal_type="boost_promote",
                          candidate_id_suffix=f"x{i}", score=5.0 + i)
          for i in range(3)]
    kept, dropped = apply_top_n_selection(cs, n=3)
    assert len(kept) == 3 and len(dropped) == 0, f"A3 3-case: {len(kept)}/{len(dropped)}"
    # Highest score first
    assert kept[0]["decision_metadata"]["score_priority"] == 7.0, (
        f"A3 ordering: {kept[0]['decision_metadata']['score_priority']}")

    # A4: 4 candidates (1 drop, alpha tie-break)
    c_alpha = _make_candidate(proposal_type="regime_alert",
                               candidate_id_suffix="alpha", score=4.0)
    c_beta  = _make_candidate(proposal_type="exposure_warn",
                               candidate_id_suffix="beta",  score=4.0)
    c_high1 = _make_candidate(proposal_type="boost_promote",
                               candidate_id_suffix="high1", score=9.0)
    c_high2 = _make_candidate(proposal_type="boost_promote",
                               candidate_id_suffix="high2", score=8.0)
    kept, dropped = apply_top_n_selection(
        [c_alpha, c_beta, c_high1, c_high2], n=3)
    assert len(kept) == 3 and len(dropped) == 1, f"A4 4-case: {len(kept)}/{len(dropped)}"
    # Top: high1 (9.0), high2 (8.0), then alpha tie-break on full
    # candidate_id (which includes brain_<type>_ prefix). Tie at score=4.0:
    # "brain_exposure_warn_beta_..." < "brain_regime_alert_alpha_..."
    # because 'e' < 'r' in ASCII. So beta kept, alpha dropped.
    assert kept[0]["candidate_id"].endswith("high1_2026-04-29"), f"A4 top: {kept[0]['candidate_id']}"
    assert kept[2]["candidate_id"].endswith("beta_2026-04-29"), f"A4 tie-break (lex on full id; e<r): {kept[2]['candidate_id']}"
    assert dropped[0]["candidate_id"].endswith("alpha_2026-04-29"), f"A4 dropped: {dropped[0]['candidate_id']}"

    # A5: 10 candidates (7 dropped)
    cs10 = [_make_candidate(proposal_type="boost_promote",
                            candidate_id_suffix=f"q{i:02d}",
                            score=float(i)) for i in range(10)]
    kept, dropped = apply_top_n_selection(cs10, n=3)
    assert len(kept) == 3 and len(dropped) == 7, f"A5 10-case"

    return "A: 5 cases PASS (0/1/3/4/10 + alpha tie-break)"


def _run_group_B(sbx_output):
    """unified_proposals.json schema (V-2)."""
    from scanner.brain.brain_output import (
        run_step6, build_unified_proposal_entry,
    )

    # Build a single candidate end-to-end through orchestrator
    cand = _make_candidate(
        proposal_type="boost_promote", candidate_id_suffix="schema",
        score=8.5,
        cohort_filter={"signal_type": "UP_TRI", "sector": "Banking_NEW",
                       "regime": "Bull"})  # No active rule matches Banking_NEW
    minimal_rules = {"kill_patterns": [], "watch_patterns": [],
                     "boost_patterns": []}

    result = run_step6(
        step5_kept_candidates=[cand],
        step5_generated_alerts=[],
        mini_scanner_rules=minimal_rules,
        derived_views={},
        run_id="brain_run_2026-04-29_B001",
        as_of_date="2026-04-29",
        output_dir=sbx_output,
    )
    assert result["status"] == "ok", f"B status: {result}"

    with open(result["unified_proposals_path"]) as f:
        data = json.load(f)

    # Top-level required
    for k in ("schema_version", "view_name", "as_of_date", "run_id",
              "_metadata", "stats", "proposals"):
        assert k in data, f"B top-level missing: {k}"
    assert data["schema_version"] == 1
    assert data["view_name"] == "unified_proposals"
    assert data["as_of_date"] == "2026-04-29"
    assert data["run_id"] == "brain_run_2026-04-29_B001"

    # Per-entry required
    assert len(data["proposals"]) == 1, f"B proposals count: {len(data['proposals'])}"
    e = data["proposals"][0]
    for k in ("id", "candidate_id", "type", "source", "source_step",
              "run_id_origin", "claim", "counter", "reversibility",
              "evidence_refs", "decision_metadata", "status",
              "created_at", "expires_at"):
        assert k in e, f"B entry missing: {k}"
    assert e["id"] == "prop_unified_2026-04-29_001"
    assert e["status"] == "pending"
    assert e["run_id_origin"] == "brain_run_2026-04-29_B001"

    # _metadata fields
    md = data["_metadata"]
    for k in ("total_step5_candidates", "total_surfaced",
              "total_dropped_by_top3_cap", "warnings",
              "dropped_due_to_top3_cap", "dual_write_summary"):
        assert k in md, f"B _metadata missing: {k}"

    # decision_metadata.conflicts_with shape — must be list-of-dicts (or [])
    assert isinstance(e["decision_metadata"].get("conflicts_with"), list), (
        f"B conflicts_with type: {type(e['decision_metadata'].get('conflicts_with'))}")

    return "B: schema validation PASS (top-level + per-entry + _metadata + conflicts_with shape)"


def _run_group_C(sbx_output):
    """Dual-write scope (V-3): kill_rule + boost_demote → write;
    boost_promote + regime_alert → skip."""
    from scanner.brain.brain_output import dual_write_to_proposed_rules

    # Build 4 candidates
    c_kill = _make_candidate(
        proposal_type="kill_rule", candidate_id_suffix="kill1",
        score=10.0,
        cohort_filter={"signal_type": "DOWN_TRI", "sector": "Auto",
                       "regime": "Bear"},
        extra_metadata={"cohort_filter_signature":
                        "regime=Bear__sector=Auto__signal_type=DOWN_TRI",
                        "n": 12, "wr": 0.0, "edge_pp": -25.0,
                        "tier": "Candidate"},
    )
    c_demote = _make_candidate(
        proposal_type="boost_demote", candidate_id_suffix="demote1",
        score=7.0,
        cohort_filter={"signal_type": "UP_TRI", "sector": "Pharma",
                       "regime": "Bear"},
        extra_metadata={"cohort_filter_signature":
                        "regime=Bear__sector=Pharma__signal_type=UP_TRI"},
    )
    c_boost = _make_candidate(
        proposal_type="boost_promote", candidate_id_suffix="boost1",
        score=9.0,
        cohort_filter={"signal_type": "UP_TRI", "sector": "FMCG",
                       "regime": "Bear"},
        extra_metadata={"cohort_filter_signature":
                        "regime=Bear__sector=FMCG__signal_type=UP_TRI"},
    )
    c_regime = _make_candidate(
        proposal_type="regime_alert", candidate_id_suffix="regime1",
        score=6.0)

    # Need a sandbox proposed_rules.json for dual-write
    os.makedirs(sbx_output, exist_ok=True)
    sbx_proposed = os.path.join(sbx_output, "proposed_rules.json")
    # Start fresh
    with open(sbx_proposed, "w") as f:
        json.dump({"schema_version": 1, "proposals": []}, f)

    summary = dual_write_to_proposed_rules(
        [c_kill, c_demote, c_boost, c_regime],
        run_id="brain_run_2026-04-29_C001",
        output_dir=sbx_output,
    )
    assert summary["dual_written"] == 2, f"C dual_written: {summary}"
    assert summary["skipped"] == 2, f"C skipped: {summary}"
    assert "boost_promote" in summary["skipped_types"]
    assert "regime_alert" in summary["skipped_types"]
    assert len(summary["written_ids"]) == 2

    # Verify proposed_rules.json contents
    with open(sbx_proposed) as f:
        data = json.load(f)
    assert len(data["proposals"]) == 2, f"C proposed_rules count: {len(data['proposals'])}"

    # Verify mapping + brain_candidate_id round-trip
    actions_seen = set()
    for entry in data["proposals"]:
        actions_seen.add(entry["action"])
        assert "brain_candidate_id" in entry, f"C round-trip missing: {entry}"
        assert entry["source"] == "brain_step6_dual_write"
    assert actions_seen == {"kill", "demote_boost"}, f"C actions: {actions_seen}"

    # Find kill entry & verify mapping
    kill_entry = next(e for e in data["proposals"] if e["action"] == "kill")
    assert kill_entry["target_signal"] == "DOWN_TRI"
    assert kill_entry["target_sector"] == "Auto"
    assert kill_entry["evidence"]["n"] == 12
    assert kill_entry["evidence"]["edge_pp"] == -25.0
    assert kill_entry["brain_candidate_id"] == c_kill["candidate_id"]

    # Find demote entry & verify mapping
    demote_entry = next(e for e in data["proposals"]
                         if e["action"] == "demote_boost")
    assert demote_entry.get("target_regime") == "Bear", (
        f"C demote regime: {demote_entry.get('target_regime')}")

    return "C: dual-write scope PASS (2 written / 2 skipped + brain_candidate_id round-trip + action mapping + regime field)"


def _run_group_D(sbx_output):
    """decisions_journal init + append + idempotency (V-4)."""
    from scanner.brain.brain_output import (
        init_decisions_journal_if_missing, append_decision)

    journal_path = os.path.join(sbx_output, "brain", "decisions_journal.json")

    # D1: file doesn't exist → init creates
    if os.path.exists(journal_path):
        os.remove(journal_path)
    created = init_decisions_journal_if_missing(sbx_output)
    assert created is True, f"D1 first init: {created}"
    assert os.path.exists(journal_path)

    with open(journal_path) as f:
        data = json.load(f)
    for k in ("schema_version", "view_name", "created_at",
              "_metadata", "entries"):
        assert k in data, f"D1 missing: {k}"
    assert data["entries"] == []
    assert data["_metadata"]["retention_policy"] == "FULL_NO_PRUNE_PER_K-4_LOCK"
    assert data["_metadata"]["total_decisions"] == 0

    # D2: idempotent — second call doesn't recreate
    created2 = init_decisions_journal_if_missing(sbx_output)
    assert created2 is False, f"D2 idempotent: {created2}"

    # D3: append entry
    append_decision(
        unified_proposal_id="prop_unified_2026-04-29_001",
        candidate_id="brain_boost_promote_test_2026-04-29",
        decision="approve",
        source="telegram",
        approver="user",
        run_id_origin="brain_run_2026-04-29_D001",
        proposal_type="boost_promote",
        cohort_identity="boost_promote_test",
        output_dir=sbx_output,
    )
    with open(journal_path) as f:
        data = json.load(f)
    assert len(data["entries"]) == 1
    e = data["entries"][0]
    assert e["decision"] == "approve"
    assert e["source"] == "telegram"
    assert data["_metadata"]["total_decisions"] == 1

    # D4: invalid decision rejected
    try:
        append_decision(
            unified_proposal_id="prop_unified_x",
            candidate_id="x", decision="maybe", source="telegram",
            approver="u", run_id_origin="x", output_dir=sbx_output)
        assert False, "D4 should have raised"
    except ValueError:
        pass

    # D5: invalid source rejected
    try:
        append_decision(
            unified_proposal_id="prop_unified_x",
            candidate_id="x", decision="approve", source="email",
            approver="u", run_id_origin="x", output_dir=sbx_output)
        assert False, "D5 should have raised"
    except ValueError:
        pass

    return "D: decisions_journal PASS (init + idempotent + append + decision/source enum enforcement)"


def _run_group_E(sbx_output):
    """§5.1 conflict surfacing on REAL today's mini_scanner_rules
    + simulated C1/C2 candidates per Phase 1 V-8 prediction.

    C1 (UP_TRI×any×Bear) → 6 overlaps (win_001..win_006); 0 from
        BULL_PROXY win_007 or DOWN_TRI kill_001 or Choppy watch_001.
    C2 (UP_TRI×Metal×any) → 2 overlaps (win_004 + watch_001 per LOCK A);
        0 from other win_NNN sectors / kill / BULL_PROXY.
    """
    from scanner.brain.brain_output import (
        detect_conflicts, populate_conflict_surfacing,
        verify_conflict_surfacing)

    with open(REAL_MINI) as f:
        mini_rules = json.load(f)

    # C1 — UP_TRI × any-sector × Bear (regime-axis)
    c1 = _make_candidate(
        proposal_type="boost_promote",
        candidate_id_suffix="signal+regime_regime=Bear__signal_type=UP_TRI",
        score=9.99,
        cohort_filter={"signal_type": "UP_TRI", "regime": "Bear"},
        extra_metadata={"n": 96, "wr": 0.9468, "edge_pp": 17.9,
                        "tier": "M"},
    )
    conflicts_c1 = detect_conflicts(c1, mini_rules)
    print(f"[E] C1 conflicts found: {len(conflicts_c1)}")
    for c in conflicts_c1:
        print(f"    - {c['rule_id']} type={c['conflict_type']}")
    assert len(conflicts_c1) == 6, f"E C1 expected 6 got {len(conflicts_c1)}"
    rule_ids_c1 = sorted(c["rule_id"] for c in conflicts_c1)
    assert rule_ids_c1 == [f"win_00{i}" for i in range(1, 7)], (
        f"E C1 rule_ids: {rule_ids_c1}")
    assert all(c["conflict_type"] == "overlap" for c in conflicts_c1), (
        f"E C1 types not all overlap")

    # C2 — UP_TRI × Metal × any-regime (sector-axis)
    c2 = _make_candidate(
        proposal_type="boost_promote",
        candidate_id_suffix="signal+sector_sector=Metal__signal_type=UP_TRI",
        score=9.20,
        cohort_filter={"signal_type": "UP_TRI", "sector": "Metal"},
        extra_metadata={"n": 15, "wr": 1.0, "edge_pp": 23.3,
                        "tier": "M"},
    )
    conflicts_c2 = detect_conflicts(c2, mini_rules)
    print(f"[E] C2 conflicts found: {len(conflicts_c2)}")
    for c in conflicts_c2:
        print(f"    - {c['rule_id']} type={c['conflict_type']}")
    assert len(conflicts_c2) == 2, f"E C2 expected 2 got {len(conflicts_c2)}"
    rule_ids_c2 = sorted(c["rule_id"] for c in conflicts_c2)
    assert rule_ids_c2 == ["watch_001", "win_004"], (
        f"E C2 rule_ids: {rule_ids_c2}")
    assert all(c["conflict_type"] == "overlap" for c in conflicts_c2), (
        f"E C2 types not all overlap")

    # Populate surfacing on C1 + verify
    c1_enriched = populate_conflict_surfacing(c1, conflicts_c1)
    md = c1_enriched["decision_metadata"]
    assert md["conflicts_with"] == [
        {"rule_id": rid, "conflict_type": "overlap"}
        for rid in (c["rule_id"] for c in conflicts_c1)
    ], f"E C1 conflicts_with: {md['conflicts_with']}"

    # Citations
    evidence = c1_enriched["counter"]["evidence"]
    for rid in [f"win_00{i}" for i in range(1, 7)]:
        assert any(e.startswith(f"{rid} active: UP_TRI ×") for e in evidence), (
            f"E C1 missing citation for {rid}; got: {evidence}")

    # Single risk (all overlap → 1 unique conflict_type)
    risks = c1_enriched["counter"]["risks"]
    assert any(r == "approval would propagate overlap to mini_scanner_rules.json"
               for r in risks), f"E C1 risk: {risks}"
    assert sum(1 for r in risks if "propagate overlap" in r) == 1, (
        f"E C1 risk count: {risks}")

    # verify_conflict_surfacing on enriched C1 → pass
    ok, viols = verify_conflict_surfacing(c1_enriched, mini_rules)
    assert ok and viols == [], f"E C1 verify: {viols}"

    # verify_conflict_surfacing on UN-enriched C1 → conflict_metadata_missing
    ok2, viols2 = verify_conflict_surfacing(c1, mini_rules)
    assert (not ok2) and viols2 == ["conflict_metadata_missing"], (
        f"E C1 bypass detection: ok={ok2} viols={viols2}")

    # Same for C2
    c2_enriched = populate_conflict_surfacing(c2, conflicts_c2)
    ok3, viols3 = verify_conflict_surfacing(c2_enriched, mini_rules)
    assert ok3 and viols3 == [], f"E C2 verify: {viols3}"

    # Tampered C1: drop a citation → conflict_evidence_missing
    import copy as _copy
    c1_tampered = _copy.deepcopy(c1_enriched)
    c1_tampered["counter"]["evidence"] = [
        e for e in c1_tampered["counter"]["evidence"]
        if not e.startswith("win_001 active:")]
    ok4, viols4 = verify_conflict_surfacing(c1_tampered, mini_rules)
    assert (not ok4) and "conflict_evidence_missing" in viols4, (
        f"E C1 tampered: ok={ok4} viols={viols4}")

    # Tampered C1: drop the risk string → conflict_risk_missing
    c1_tampered2 = _copy.deepcopy(c1_enriched)
    c1_tampered2["counter"]["risks"] = [
        r for r in c1_tampered2["counter"]["risks"]
        if "propagate overlap" not in r]
    ok5, viols5 = verify_conflict_surfacing(c1_tampered2, mini_rules)
    assert (not ok5) and "conflict_risk_missing" in viols5, (
        f"E C1 risk tampered: ok={ok5} viols={viols5}")

    return ("E: conflict surfacing PASS — C1: 6 overlaps win_001..win_006; "
            "C2: 2 overlaps win_004 + watch_001 (LOCK A); "
            "all 3 violation codes confirmed (metadata/evidence/risk)")


def _run_group_F(sbx_output):
    """Empty queue handling (V-7)."""
    from scanner.brain.brain_output import run_step6

    result = run_step6(
        step5_kept_candidates=[],
        step5_generated_alerts=[],
        mini_scanner_rules={"kill_patterns": [], "boost_patterns": [],
                             "watch_patterns": []},
        derived_views={},
        run_id="brain_run_2026-04-29_F001",
        as_of_date="2026-04-29",
        output_dir=sbx_output,
    )
    assert result["status"] == "empty_queue", f"F status: {result}"
    assert result["total_input"] == 0

    with open(result["unified_proposals_path"]) as f:
        data = json.load(f)
    assert data["proposals"] == []
    assert "empty_queue_no_candidates_this_cycle" in data["_metadata"]["warnings"]
    assert data["stats"]["total"] == 0

    # decisions_journal initialized
    journal_path = os.path.join(sbx_output, "brain", "decisions_journal.json")
    assert os.path.exists(journal_path)
    assert result["journal_init_action"] in ("created", "existed")

    return "F: empty queue PASS (empty proposals[] + warning + journal init)"


def _run_group_G(sbx_output):
    """rule_proposer adapter wiring — verify legacy_id round-trips
    from dual-write back into unified_proposals entries."""
    from scanner.brain.brain_output import run_step6

    # Need a sandbox proposed_rules.json to allow real dual-write
    sbx_proposed = os.path.join(sbx_output, "proposed_rules.json")
    with open(sbx_proposed, "w") as f:
        json.dump({"schema_version": 1, "proposals": []}, f)

    c_kill = _make_candidate(
        proposal_type="kill_rule", candidate_id_suffix="killG",
        score=10.0,
        cohort_filter={"signal_type": "DOWN_TRI", "sector": "TestSector",
                       "regime": "Bear"},
        extra_metadata={"cohort_filter_signature":
                        "regime=Bear__sector=TestSector__signal_type=DOWN_TRI",
                        "n": 11, "edge_pp": -22.0},
    )

    result = run_step6(
        step5_kept_candidates=[c_kill],
        step5_generated_alerts=[],
        mini_scanner_rules={"kill_patterns": [], "boost_patterns": [],
                             "watch_patterns": []},
        derived_views={},
        run_id="brain_run_2026-04-29_G001",
        as_of_date="2026-04-29",
        output_dir=sbx_output,
    )
    assert result["status"] == "ok"
    assert result["dual_write_summary"]["dual_written"] == 1

    # Verify unified_proposals legacy_id populated from dual_write
    with open(result["unified_proposals_path"]) as f:
        data = json.load(f)
    assert len(data["proposals"]) == 1
    legacy_id = data["proposals"][0]["legacy_id"]
    assert legacy_id is not None and legacy_id.startswith("prop_"), (
        f"G legacy_id: {legacy_id}")

    # Verify proposed_rules.json entry has matching brain_candidate_id
    with open(sbx_proposed) as f:
        pr_data = json.load(f)
    matching = [e for e in pr_data["proposals"] if e["id"] == legacy_id]
    assert len(matching) == 1, f"G mapping: {matching}"
    assert matching[0]["brain_candidate_id"] == c_kill["candidate_id"]

    return ("G: rule_proposer adapter PASS — legacy_id round-trips into "
            "unified_proposals + brain_candidate_id round-trips into "
            "proposed_rules")


def _run_group_H():
    """SHA256 invariants on real files. Run AFTER all sandbox groups
    to confirm none of them touched real state."""
    real_paths = {
        "signal_history": REAL_HISTORY,
        "proposed_rules": REAL_PROPOSED,
        "mini_scanner_rules": REAL_MINI,
        "cohort_health": REAL_COHORT_HEALTH,
        "regime_watch": REAL_REGIME_WATCH,
        "portfolio_exposure": REAL_PORTFOLIO,
        "ground_truth_gaps": REAL_GTG,
        "reasoning_log": REAL_REASONING_LOG,
    }
    return real_paths


def main():
    # Capture pre-run SHA256 of real files
    pre_hashes = {}
    for name, path in _run_group_H().items():
        if os.path.exists(path):
            pre_hashes[name] = _sha256(path)

    sbx = tempfile.mkdtemp(prefix="smoke_brain_output_")
    sbx_output = os.path.join(sbx, "output")
    os.makedirs(sbx_output, exist_ok=True)

    try:
        results = []
        results.append(_run_group_A(sbx_output))
        results.append(_run_group_B(sbx_output))
        results.append(_run_group_C(sbx_output))
        results.append(_run_group_D(sbx_output))
        results.append(_run_group_E(sbx_output))
        results.append(_run_group_F(sbx_output))
        results.append(_run_group_G(sbx_output))

        # Group H: SHA256 invariants
        for name, path in _run_group_H().items():
            if name not in pre_hashes:
                continue
            post = _sha256(path)
            assert post == pre_hashes[name], (
                f"H invariant: {name} mutated! "
                f"{pre_hashes[name]} → {post}")
        results.append(f"H: SHA256 invariants PASS ({len(pre_hashes)} files unchanged)")

        print()
        print("=" * 72)
        print("ALL 8 GROUPS PASSED")
        print("=" * 72)
        for r in results:
            print(f"  ✓ {r}")
        print()
        print(f"Sandbox: {sbx}")
        return 0

    except AssertionError as e:
        print(f"\n❌ FAIL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        shutil.rmtree(sbx, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
