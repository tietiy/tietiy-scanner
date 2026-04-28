"""Wave 5 Step 4 smoke — brain_verify framework + 4 deterministic generators.

Per CLAUDE.md §4 sandbox pattern + V-15 smoke contract.

Group A: verification framework (V-1..V-9) — 9 cases
Group B: deterministic generators (V-10..V-14) — 7 cases
Group C: real-data integration — 4 cases
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

REAL_HISTORY = os.path.join(ROOT, "output", "signal_history.json")
REAL_PROPOSED = os.path.join(ROOT, "output", "proposed_rules.json")
REAL_MINI = os.path.join(ROOT, "data", "mini_scanner_rules.json")
REAL_COHORT_HEALTH = os.path.join(ROOT, "output", "brain", "cohort_health.json")
REAL_GTG = os.path.join(ROOT, "output", "brain", "ground_truth_gaps.json")


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _well_formed_candidate():
    from scanner.brain.brain_verify import build_proposal_candidate
    return build_proposal_candidate(
        proposal_type="boost_promote",
        source="brain_step4",
        source_view="cohort_health",
        title="Test cohort: n=20, 80% WR, Tier M",
        claim_what="Promote boost_pattern: signal=UP_TRI, regime=Bear",
        claim_expected_effect="Surface as Tier-B boost",
        claim_confidence="high",
        counter_evidence=["Wilson lower 0.65 above floor"],
        counter_risks=["Regime may shift"],
        reversibility="1-line revert",
        evidence_refs=["cohort_health.json#test", "patterns.json#test"],
        cohort_filter_signature="regime=Bear__signal_type=UP_TRI",
        cohort_axis="signal+regime",
        decision_metadata={"tier": "M", "n": 20, "wr": 0.8},
    )


def _run_group_A(sbx_output):
    """Verification framework cases."""
    from scanner.brain.brain_verify import (
        verify_proposal, build_proposal_candidate, score_priority,
        log_verification_failure)

    # A1: well-formed
    p = _well_formed_candidate()
    ok, vs = verify_proposal(p)
    assert ok and vs == [], f"A1 fail: {vs}"

    # A2: missing claim.what
    p2 = json.loads(json.dumps(p))
    p2["claim"]["what"] = ""
    ok, vs = verify_proposal(p2)
    assert not ok and "missing_claim_what" in vs, f"A2 fail: {vs}"

    # A3: empty counter.evidence with confidence=medium
    p3 = json.loads(json.dumps(p))
    p3["counter"]["evidence"] = []
    p3["claim"]["confidence"] = "medium"
    ok, vs = verify_proposal(p3)
    assert (not ok and
            "missing_counter_evidence_without_rationale" in vs), f"A3 fail: {vs}"

    # A4: empty counter.evidence with high + no_counter_rationale populated
    p4 = json.loads(json.dumps(p))
    p4["counter"]["evidence"] = []
    p4["claim"]["confidence"] = "high"
    p4["decision_metadata"]["no_counter_rationale"] = "Auto-demote per §3"
    ok, vs = verify_proposal(p4)
    assert ok, f"A4 fail: {vs}"

    # A5: empty counter.risks
    p5 = json.loads(json.dumps(p))
    p5["counter"]["risks"] = []
    ok, vs = verify_proposal(p5)
    assert not ok and "empty_counter_risks" in vs, f"A5 fail: {vs}"

    # A6: IRREVERSIBLE outside allowlist
    p6 = json.loads(json.dumps(p))
    p6["reversibility"] = "IRREVERSIBLE — see counter.risks"
    ok, vs = verify_proposal(p6)
    assert (not ok and
            "irreversible_outside_allowlist" in vs), f"A6 fail: {vs}"

    # A7: build → verify round-trip
    built = _well_formed_candidate()
    ok, vs = verify_proposal(built)
    assert ok and vs == [], f"A7 fail: {vs}"

    # A8: score_priority floats; tier-M cohort (M weight=2.0) above tier-W (W=1.0)
    p_m = build_proposal_candidate(
        proposal_type="boost_promote", source="x", source_view="cohort_health",
        title="t", claim_what="t", claim_expected_effect="t",
        claim_confidence="high",
        counter_evidence=["e"], counter_risks=["r"],
        reversibility="r", evidence_refs=["e"],
        cohort_filter_signature="x", cohort_axis="signal+regime",
        decision_metadata={"tier": "M", "n": 50},
    )
    p_w = build_proposal_candidate(
        proposal_type="boost_promote", source="x", source_view="cohort_health",
        title="t", claim_what="t", claim_expected_effect="t",
        claim_confidence="high",
        counter_evidence=["e"], counter_risks=["r"],
        reversibility="r", evidence_refs=["e"],
        cohort_filter_signature="y", cohort_axis="signal+regime",
        decision_metadata={"tier": "W", "n": 50},
    )
    s_m = score_priority(p_m, {})
    s_w = score_priority(p_w, {})
    assert isinstance(s_m, float) and s_m > s_w, f"A8 fail: {s_m} vs {s_w}"

    # A9: log_verification_failure writes; SHA256 invariant verified externally
    bad = {"type": "boost_promote"}  # malformed
    _, viols = verify_proposal(bad)
    log_verification_failure(bad, viols, "smoke_test", sbx_output)
    fpath = os.path.join(sbx_output, "brain", "verification_failures.json")
    assert os.path.exists(fpath), "A9 fail: failures file missing"
    failures = json.load(open(fpath))
    assert failures["max_retention"] == 1000
    assert len(failures["failures"]) == 1


def _run_group_B(sbx_output):
    """Deterministic generators — uses real cohort_health from REAL_COHORT_HEALTH."""
    from scanner.brain.brain_verify import (
        verify_proposal,
        generate_boost_promote_candidates,
        generate_boost_demote_candidates,
        generate_cohort_review_candidates,
        generate_kill_rule_candidates_brain_side,
        run_step4)

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    gtg = json.load(open(REAL_GTG))
    proposed_rules = json.load(open(REAL_PROPOSED))
    mini_rules = json.load(open(REAL_MINI))

    # B1: today's cohort_health → expect 2 boost_promote
    bp_cands = generate_boost_promote_candidates(cohort_health)
    assert len(bp_cands) == 2, f"B1 fail: expected 2, got {len(bp_cands)}"
    cohort_ids = {c["candidate_id"].rsplit("_", 1)[0] for c in bp_cands}
    expected = {
        "brain_boost_promote_signal+regime_regime=Bear__signal_type=UP_TRI",
        "brain_boost_promote_signal+sector_sector=Metal__signal_type=UP_TRI",
    }
    assert cohort_ids == expected, f"B1 fail cohort ids: {cohort_ids}"
    for c in bp_cands:
        ok, vs = verify_proposal(c)
        assert ok, f"B1 fail verify: {c['candidate_id']}: {vs}"

    # B2: first run (no prior archive) → []
    bd_cands = generate_boost_demote_candidates(cohort_health, None)
    assert bd_cands == [], f"B2 fail: {bd_cands}"

    # B3: simulated prior with UP_TRI×Bear at S → demote candidate
    sim_prior = json.loads(json.dumps(cohort_health))
    for c in sim_prior["cohorts"]:
        if c["cohort_id"] == "regime=Bear__signal_type=UP_TRI":
            c["tier"] = "S"
            break
    bd_cands = generate_boost_demote_candidates(cohort_health, sim_prior)
    assert len(bd_cands) == 1, f"B3 fail: {len(bd_cands)}"
    ok, vs = verify_proposal(bd_cands[0])
    assert ok, f"B3 verify fail: {vs}"
    md = bd_cands[0]["decision_metadata"]
    assert md["prior_tier"] == "S" and md["current_tier"] == "M"
    assert "proposed_rule_mutation" in md

    # B4: today's empty thin lists → 0
    cr_cands = generate_cohort_review_candidates(gtg)
    assert cr_cands == [], f"B4 fail: {cr_cands}"

    # B5: simulated thin_rule → 1 candidate
    sim_gtg = {
        "thin_rules": [{
            "rule_source_kind": "boost_pattern",
            "rule_id": "win_test",
            "n": 2,
            "cohort_filter": {"signal": "UP_TRI", "sector": "Bank"},
        }],
        "thin_patterns": [],
        "_metadata": {"n_threshold_thin": 5},
    }
    cr_cands = generate_cohort_review_candidates(sim_gtg)
    assert len(cr_cands) == 1, f"B5 fail: {len(cr_cands)}"
    ok, vs = verify_proposal(cr_cands[0])
    assert ok, f"B5 verify fail: {vs}"

    # B6: brain-side kill_rule against today's data → 0 after dedup
    kr_cands = generate_kill_rule_candidates_brain_side(
        cohort_health, proposed_rules, mini_rules)
    assert kr_cands == [], (f"B6 fail: expected 0 after dedup, "
                            f"got {len(kr_cands)}")

    # B7: orchestrator
    derived = {"cohort_health": cohort_health, "ground_truth_gaps": gtg}
    final = run_step4(derived, prior_archives={},
                      proposed_rules=proposed_rules,
                      mini_scanner_rules=mini_rules,
                      output_dir=sbx_output)
    assert len(final) == 2, f"B7 fail: expected 2 final, got {len(final)}"
    for c in final:
        ok, vs = verify_proposal(c)
        assert ok, f"B7 verify fail: {c['candidate_id']}: {vs}"


def _run_group_C(sbx_output):
    """Real-data integration."""
    from scanner.brain.brain_verify import (
        verify_proposal, score_priority, run_step4)

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    gtg = json.load(open(REAL_GTG))
    proposed_rules = json.load(open(REAL_PROPOSED))
    mini_rules = json.load(open(REAL_MINI))

    derived = {"cohort_health": cohort_health, "ground_truth_gaps": gtg}
    final = run_step4(derived, prior_archives={},
                      proposed_rules=proposed_rules,
                      mini_scanner_rules=mini_rules,
                      output_dir=sbx_output)

    # C1: 2 candidates expected
    assert len(final) == 2, f"C1 fail: {len(final)} candidates"

    # C2: all pass verify
    for c in final:
        ok, vs = verify_proposal(c)
        assert ok, f"C2 fail: {c['candidate_id']}: {vs}"

    # C3: score_priority orders sensibly (higher n + Tier M > lower)
    scores = [score_priority(c, derived) for c in final]
    assert scores[0] >= scores[1], f"C3 fail: scores {scores} not sorted"

    # C4: SHA256 invariants
    inv_files = [REAL_HISTORY, REAL_PROPOSED, REAL_MINI,
                 REAL_COHORT_HEALTH, REAL_GTG]
    return inv_files


def main():
    inv_before = {}
    for f in [REAL_HISTORY, REAL_PROPOSED, REAL_MINI,
              REAL_COHORT_HEALTH, REAL_GTG]:
        inv_before[f] = _sha256(f)

    sbx = tempfile.mkdtemp(prefix="smoke_brain_verify_")
    sbx_output = os.path.join(sbx, "output")
    os.makedirs(os.path.join(sbx_output, "brain"), exist_ok=True)

    try:
        _run_group_A(sbx_output)
        print("Group A (verification framework, 9 cases): PASS")

        _run_group_B(sbx_output)
        print("Group B (deterministic generators, 7 cases): PASS")

        inv_files = _run_group_C(sbx_output)
        print("Group C (real-data integration, 3 cases): PASS")

        # SHA256 invariants
        for f in inv_files:
            after = _sha256(f)
            assert inv_before[f] == after, f"REAL FILE MUTATED: {f}"
        print(f"C4: SHA256 invariants on {len(inv_files)} real files: PASS")

        print("\nALL GROUPS PASS — Step 4 framework + 4 generators verified")
        return 0
    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    except Exception as e:
        print(f"FAIL: unexpected {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return 1
    finally:
        shutil.rmtree(sbx, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
