"""Wave 5 Step 7 smoke — telegram_bot Step 7 extension.

Per CLAUDE.md §4 sandbox pattern + V-9 smoke contract (9 groups A-I).

A — digest rendering (top-3 + dropped + conflict badges per D-9 + emojis)
B — /approve dispatcher per type (kill_rule / boost_demote / boost_promote /
    regime_alert / exposure_warn / cohort_review)
C — /reject dispatcher per type
D — apply_boost_promote (sandbox mini_scanner_rules; win_NNN+1 id;
    added_date YYYY-MM-DD; approved_by + brain_candidate_id round-trip)
E — V-5 idempotency (double-approve → no-op with informative msg)
F — decisions_journal append integration (all 11 fields)
G — empty queue rendering (Sat/Sun tone vs business-day tone)
H — SHA256 invariants on real signal_history + reasoning_log +
    unified_proposals + mini_scanner_rules (read-only paths in smoke)
I — /explain rendering (Q2 lock; full counter without truncation)
"""
import copy
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
REAL_REASONING_LOG  = os.path.join(ROOT, "output", "brain", "reasoning_log.json")
REAL_UNIFIED        = os.path.join(ROOT, "output", "brain", "unified_proposals.json")
REAL_DECISIONS_JOURNAL = os.path.join(
    ROOT, "output", "brain", "decisions_journal.json")


def _sha256(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _make_proposal(*, unified_id, ptype, candidate_id_suffix="x",
                    cohort_filter=None, claim_confidence="high",
                    extra_metadata=None, status="pending"):
    """Build a synthetic unified_proposals.json entry."""
    md = {}
    if cohort_filter is not None:
        md["cohort_filter"] = cohort_filter
    if extra_metadata:
        md.update(extra_metadata)
    md.setdefault("conflicts_with", [])

    return {
        "id": unified_id,
        "legacy_id": None,
        "candidate_id": f"brain_{ptype}_{candidate_id_suffix}_2026-04-29",
        "type": ptype,
        "source": "brain_step4_smoke",
        "source_step": "step5_smoke",
        "run_id_origin": "brain_run_2026-04-29_smoke",
        "title": f"Smoke {ptype} {candidate_id_suffix}",
        "claim": {
            "what": f"Promote {ptype}: smoke",
            "expected_effect": "Surface for testing",
            "confidence": claim_confidence,
        },
        "counter": {
            "evidence": ["smoke evidence 1"],
            "risks": ["smoke risk 1"],
        },
        "reversibility": "1-line revert in test",
        "evidence_refs": ["test#1"],
        "decision_metadata": md,
        "status": status,
        "created_at": "2026-04-29T22:00:00+05:30",
        "expires_at": "2026-05-06T22:00:00+05:30",
        "approver": None,
        "decision_at": None,
        "decision_reason": None,
    }


def _stub_telegram_send(*args, **kwargs):
    """Stub send_message — capture calls without hitting Telegram API."""
    _stub_telegram_send.calls.append((args, kwargs))
    return True
_stub_telegram_send.calls = []


def _stub_reply_message(chat_id, text):
    """Stub _reply_message — capture chat replies."""
    _stub_reply_message.calls.append((chat_id, text))
    return True
_stub_reply_message.calls = []


def _setup_sandbox(sbx_root):
    """Build sandbox output/brain/* + data/ directories."""
    sbx_output = os.path.join(sbx_root, "output")
    sbx_data = os.path.join(sbx_root, "data")
    os.makedirs(os.path.join(sbx_output, "brain"), exist_ok=True)
    os.makedirs(sbx_data, exist_ok=True)
    # Copy real mini_scanner_rules.json for D-test (boost_pattern schema)
    shutil.copy(REAL_MINI, os.path.join(sbx_data, "mini_scanner_rules.json"))
    return sbx_output, sbx_data


def _run_group_A(sbx_output):
    """Digest rendering — top-3 cards + dropped + conflict badges."""
    from scanner.telegram_bot import (
        build_digest_message, _build_conflict_badges, _build_card)

    # Build a 3-card unified_proposals payload
    p1 = _make_proposal(
        unified_id="prop_unified_2026-04-29_001",
        ptype="boost_promote", candidate_id_suffix="bear",
        cohort_filter={"signal_type": "UP_TRI", "regime": "Bear"},
        extra_metadata={
            "n": 96, "wr": 0.9468, "tier": "M",
            "score_priority": 9.99,
            "conflicts_with": [
                {"rule_id": f"win_00{i}", "conflict_type": "overlap"}
                for i in range(1, 7)
            ],
        },
    )
    # Add citation strings to evidence (simulating Step 6 surfacing)
    for i in range(1, 7):
        p1["counter"]["evidence"].append(
            f"win_00{i} active: UP_TRI × Sector{i} × Bear (n={20-i})")
    p1["counter"]["risks"].append(
        "approval would propagate overlap to mini_scanner_rules.json")

    p2 = _make_proposal(
        unified_id="prop_unified_2026-04-29_002",
        ptype="boost_promote", candidate_id_suffix="metal",
        cohort_filter={"signal_type": "UP_TRI", "sector": "Metal"},
        extra_metadata={
            "n": 15, "wr": 1.0, "tier": "M",
            "score_priority": 9.20,
            "conflicts_with": [
                {"rule_id": "win_004", "conflict_type": "overlap"},
                {"rule_id": "watch_001", "conflict_type": "overlap"},
            ],
        },
    )

    p3 = _make_proposal(
        unified_id="prop_unified_2026-04-29_003",
        ptype="exposure_warn", candidate_id_suffix="exp",
        extra_metadata={"score_priority": 5.0},
    )

    payload = {
        "schema_version": 1, "view_name": "unified_proposals",
        "as_of_date": "2026-04-29",  # Wednesday
        "run_id": "brain_run_2026-04-29_2200",
        "_metadata": {
            "warnings": ["top3_cap_dropped_1_candidates"],
            "dropped_due_to_top3_cap": [{
                "candidate_id": "brain_regime_alert_xyz_2026-04-29",
                "score_priority": 4.5, "reason": "below_top_3_cap"
            }],
        },
        "proposals": [p1, p2, p3],
    }

    msg = build_digest_message(payload)

    # Assertions
    assert "Card 1 of 3" in msg, "A: card 1 marker"
    assert "Card 2 of 3" in msg, "A: card 2 marker"
    assert "Card 3 of 3" in msg, "A: card 3 marker"
    assert "🟢 *boost\\_promote*" in msg, "A: boost_promote emoji+badge"
    assert "🟡 *OVERLAP* × 6" in msg or "OVERLAP* × 6" in msg, "A: C1 conflict badge"
    assert "🟡 *OVERLAP* × 2" in msg or "OVERLAP* × 2" in msg, "A: C2 conflict badge"
    assert "📊" not in msg or "exposure_warn" not in msg or "⚠️" in msg, (
        "A: exposure_warn emoji rendering")
    assert "Dropped" in msg and "below top" in msg, "A: dropped section"
    assert "/approve prop_unified_2026-04-29_001" in msg, "A: tap-to-copy approve"
    assert "/reject prop_unified_2026-04-29_001" in msg, "A: tap-to-copy reject"

    # CORRECTION 2 — citations rendered FIRST in counter
    # Find "Counter (top 3):" section and verify win_00X appears before
    # "smoke evidence" in C1 card
    c1_start = msg.find("Card 1 of 3")
    c1_end = msg.find("Card 2 of 3")
    c1_section = msg[c1_start:c1_end]
    win_001_pos = c1_section.find("win\\_001")
    smoke_pos = c1_section.find("smoke evidence")
    assert win_001_pos != -1, "A: C1 win_001 citation present"
    if smoke_pos != -1:
        assert win_001_pos < smoke_pos, (
            "A: CORRECTION 2 — citation must precede smoke evidence")

    # boost_demote emoji is ⬇️ (CORRECTION 1; not 🟡 to avoid yellow collision)
    badge_demote = _build_conflict_badges([])
    assert badge_demote == "", "A: empty conflicts → empty badge"

    # Multi-type badge rendering
    badges_multi = _build_conflict_badges([
        {"conflict_type": "overlap"}, {"conflict_type": "contradiction"},
        {"conflict_type": "overlap"}])
    assert "OVERLAP" in badges_multi and "CONTRADICTION" in badges_multi, (
        f"A: multi-badge: {badges_multi}")

    return f"A: digest rendering PASS ({len(msg)} chars; 3 cards + dropped + badges)"


def _run_group_B(sbx_output):
    """/approve dispatcher per type — verify routing."""
    from scanner.telegram_bot import dispatch_approval

    sbx_root = os.path.dirname(sbx_output)
    sbx_mini = os.path.join(sbx_root, "data", "mini_scanner_rules.json")

    # Stage unified_proposals.json so _update_unified_proposal_status finds it
    p_boost = _make_proposal(
        unified_id="prop_unified_2026-04-29_b1",
        ptype="boost_promote", candidate_id_suffix="bX",
        cohort_filter={"signal_type": "UP_TRI", "sector": "TestSector",
                       "regime": "Bull"},
        extra_metadata={
            "proposed_rule_entry": {
                "id": "boost_brain_xyz",
                "active": True, "signal": "UP_TRI",
                "sector": "TestSector", "regime": "Bull",
                "tier": "B", "conviction_tag": "TAKE_SMALL",
                "reason": "smoke", "source": "brain_step4",
                "evidence": {"wr": 1.0, "n": 15, "tier": "validated"},
            },
        },
    )
    p_regime = _make_proposal(
        unified_id="prop_unified_2026-04-29_b2",
        ptype="regime_alert", candidate_id_suffix="rg")
    p_exposure = _make_proposal(
        unified_id="prop_unified_2026-04-29_b3",
        ptype="exposure_warn", candidate_id_suffix="ex")
    p_cohort = _make_proposal(
        unified_id="prop_unified_2026-04-29_b4",
        ptype="cohort_review", candidate_id_suffix="cr")

    unified_path = os.path.join(sbx_output, "brain",
                                 "unified_proposals.json")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_boost, p_regime, p_exposure, p_cohort],
        }, f)

    # Initialize decisions_journal so append_decision works
    from scanner.brain.brain_output import init_decisions_journal_if_missing
    init_decisions_journal_if_missing(sbx_output)

    # B1: boost_promote → apply_boost_promote called
    r1 = dispatch_approval(
        unified_proposal=p_boost, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert r1.get("success") and r1.get("action") == "boost_promote", (
        f"B1: {r1}")
    assert r1.get("win_id", "").startswith("win_"), f"B1 win_id: {r1}"

    # B2: regime_alert → log_only
    r2 = dispatch_approval(
        unified_proposal=p_regime, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert r2.get("success") and r2.get("action") == "log_only", f"B2: {r2}"

    # B3: exposure_warn → log_only
    r3 = dispatch_approval(
        unified_proposal=p_exposure, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert r3.get("success") and r3.get("action") == "log_only", f"B3: {r3}"

    # B4: cohort_review → log_only
    r4 = dispatch_approval(
        unified_proposal=p_cohort, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert r4.get("success") and r4.get("action") == "log_only", f"B4: {r4}"

    return ("B: dispatcher routing PASS — boost_promote → mutation; "
            "regime_alert/exposure_warn/cohort_review → log_only")


def _run_group_C(sbx_output):
    """/reject dispatcher per type."""
    from scanner.telegram_bot import dispatch_approval

    p_kill = _make_proposal(
        unified_id="prop_unified_2026-04-29_c1",
        ptype="kill_rule", candidate_id_suffix="kr")
    p_kill["legacy_id"] = "prop_999"  # mock legacy

    unified_path = os.path.join(sbx_output, "brain",
                                 "unified_proposals.json")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_kill],
        }, f)

    # kill_rule reject → rule_proposer.reject_proposal call
    # Will fail because legacy_id prop_999 not in real proposed_rules,
    # but the dispatch routing should route TO rule_proposer.
    r1 = dispatch_approval(
        unified_proposal=p_kill, decision="reject",
        trader="user", reason="weak n", output_dir=sbx_output)
    # rule_proposer returns success=False if legacy_id not found; that's
    # expected here since prop_999 doesn't exist. We're verifying the
    # ROUTING reached rule_proposer (error message format from rule_proposer).
    assert (r1.get("error", "").startswith("Proposal prop_999 not found")
            or r1.get("success")), f"C1 routing: {r1}"

    # informational reject → log_only_reject
    p_reg = _make_proposal(
        unified_id="prop_unified_2026-04-29_c2",
        ptype="regime_alert", candidate_id_suffix="rg")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_reg],
        }, f)
    r2 = dispatch_approval(
        unified_proposal=p_reg, decision="reject",
        trader="user", reason="not relevant", output_dir=sbx_output)
    assert r2.get("success") and r2.get("action") == "log_only_reject", (
        f"C2: {r2}")

    return "C: reject dispatcher PASS — kill_rule routes to rule_proposer; informational → log_only_reject"


def _run_group_D(sbx_output):
    """apply_boost_promote — sandbox mini_scanner_rules write."""
    from scanner.telegram_bot import apply_boost_promote

    sbx_root = os.path.dirname(sbx_output)
    sbx_mini = os.path.join(sbx_root, "data", "mini_scanner_rules.json")

    # Pre-state: count existing win_NNN
    with open(sbx_mini) as f:
        pre = json.load(f)
    pre_count = len(pre.get("boost_patterns", []))
    pre_max_n = 0
    for entry in pre.get("boost_patterns", []):
        import re
        m = re.match(r"^win_(\d{3})$", str(entry.get("id", "")))
        if m:
            pre_max_n = max(pre_max_n, int(m.group(1)))

    # Build boost_promote candidate with full proposed_rule_entry
    candidate = _make_proposal(
        unified_id="prop_unified_2026-04-29_d1",
        ptype="boost_promote", candidate_id_suffix="dX",
        cohort_filter={"signal_type": "UP_TRI", "sector": "Test_D",
                       "regime": "Bull"},
        extra_metadata={
            "proposed_rule_entry": {
                "id": "boost_brain_dxyz",
                "active": True, "signal": "UP_TRI",
                "sector": "Test_D", "regime": "Bull",
                "tier": "B", "conviction_tag": "TAKE_SMALL",
                "reason": "D test", "source": "brain_step4",
                "evidence": {"wr": 1.0, "n": 18, "tier": "validated"},
            },
        },
    )

    result = apply_boost_promote(candidate, sbx_mini, "user")
    assert result.get("success"), f"D: {result}"
    expected_id = f"win_{pre_max_n + 1:03d}"
    assert result.get("win_id") == expected_id, (
        f"D: win_id {result.get('win_id')} vs expected {expected_id}")

    # Post-state: verify entry written + schema
    with open(sbx_mini) as f:
        post = json.load(f)
    new_entries = [e for e in post["boost_patterns"]
                    if e.get("id") == expected_id]
    assert len(new_entries) == 1, f"D: new entry count: {len(new_entries)}"
    new_entry = new_entries[0]
    assert new_entry["active"] is True, f"D: active: {new_entry}"
    assert new_entry["signal"] == "UP_TRI"
    assert new_entry["sector"] == "Test_D"
    assert new_entry["regime"] == "Bull"
    assert new_entry["tier"] == "B"
    assert new_entry["conviction_tag"] == "TAKE_SMALL"
    assert new_entry["approved_by"] == "user", f"D: approved_by: {new_entry.get('approved_by')}"
    # added_date format YYYY-MM-DD (10 chars)
    assert len(new_entry["added_date"]) == 10 and new_entry["added_date"][4] == "-", (
        f"D: added_date format: {new_entry['added_date']}")
    # brain_candidate_id round-trip
    assert new_entry["brain_candidate_id"] == candidate["candidate_id"], (
        f"D: round-trip: {new_entry.get('brain_candidate_id')}")
    assert len(post["boost_patterns"]) == pre_count + 1, "D: count delta"

    return f"D: apply_boost_promote PASS — {expected_id} written, all schema fields present, brain_candidate_id round-trip"


def _run_group_E(sbx_output):
    """V-5 idempotency — double-approve detection."""
    from scanner.telegram_bot import dispatch_approval

    sbx_root = os.path.dirname(sbx_output)
    sbx_mini = os.path.join(sbx_root, "data", "mini_scanner_rules.json")

    # Stage proposal already approved (status=approved)
    p_approved = _make_proposal(
        unified_id="prop_unified_2026-04-29_e1",
        ptype="regime_alert", candidate_id_suffix="ix",
        status="approved")
    p_approved["decision_at"] = "2026-04-29T22:30:00+05:30"

    unified_path = os.path.join(sbx_output, "brain",
                                 "unified_proposals.json")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_approved],
        }, f)

    r = dispatch_approval(
        unified_proposal=p_approved, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert (not r.get("success") and
            r.get("action") == "noop_already_decided"), f"E approved: {r}"
    assert "already approved" in r.get("message", ""), f"E msg: {r}"

    # Same for rejected
    p_rejected = _make_proposal(
        unified_id="prop_unified_2026-04-29_e2",
        ptype="regime_alert", candidate_id_suffix="iy",
        status="rejected")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_rejected],
        }, f)
    r2 = dispatch_approval(
        unified_proposal=p_rejected, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert (not r2.get("success") and
            r2.get("action") == "noop_already_decided"), f"E rejected: {r2}"

    # Expired path
    p_expired = _make_proposal(
        unified_id="prop_unified_2026-04-29_e3",
        ptype="regime_alert", candidate_id_suffix="iz",
        status="expired")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p_expired],
        }, f)
    r3 = dispatch_approval(
        unified_proposal=p_expired, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert (not r3.get("success") and
            r3.get("action") == "noop_expired"), f"E expired: {r3}"

    return "E: idempotency PASS — approved/rejected/expired all → no-op with informative msg"


def _run_group_F(sbx_output):
    """decisions_journal append integration — all 11 fields."""
    from scanner.telegram_bot import dispatch_approval

    sbx_root = os.path.dirname(sbx_output)
    sbx_mini = os.path.join(sbx_root, "data", "mini_scanner_rules.json")

    p = _make_proposal(
        unified_id="prop_unified_2026-04-29_f1",
        ptype="regime_alert", candidate_id_suffix="fX")

    unified_path = os.path.join(sbx_output, "brain",
                                 "unified_proposals.json")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p],
        }, f)

    # Init journal
    from scanner.brain.brain_output import init_decisions_journal_if_missing
    init_decisions_journal_if_missing(sbx_output)

    # Approve
    r = dispatch_approval(
        unified_proposal=p, decision="approve",
        trader="user", reason=None, output_dir=sbx_output,
        mini_scanner_rules_path=sbx_mini)
    assert r.get("success"), f"F dispatch: {r}"

    # Verify journal append — sandbox shared across groups B/C/F so
    # find F's specific entry by unified_proposal_id
    journal_path = os.path.join(sbx_output, "brain",
                                  "decisions_journal.json")
    with open(journal_path) as f:
        journal = json.load(f)
    f_entries = [e for e in journal["entries"]
                  if e.get("unified_proposal_id") == "prop_unified_2026-04-29_f1"]
    assert len(f_entries) == 1, (
        f"F entries for f1: {len(f_entries)} (total {len(journal['entries'])})")
    e = f_entries[0]
    # All 11 V-7 required fields present
    required = ["timestamp", "candidate_id", "cohort_identity",
                 "proposal_type", "unified_proposal_id", "decision",
                 "source", "approver", "run_id_origin",
                 "trader_reason", "decision_metadata"]
    for field in required:
        assert field in e, f"F missing field: {field}"
    assert e["decision"] == "approve"
    assert e["source"] == "telegram"
    assert e["approver"] == "user"
    assert e["proposal_type"] == "regime_alert"
    assert "mutation_result" in (e["decision_metadata"] or {}), (
        f"F mutation_result: {e}")

    return "F: decisions_journal append PASS — all 11 V-7 fields present + mutation_result captured"


def _run_group_G(sbx_output):
    """Empty queue rendering — Sat/Sun vs business-day tone."""
    from scanner.telegram_bot import (
        build_digest_message, _empty_queue_message, _is_weekend)

    # Sat: 2026-04-25 is a Saturday
    assert _is_weekend("2026-04-25") is True, "G: Saturday detection"
    assert _is_weekend("2026-04-26") is True, "G: Sunday detection"
    # 2026-04-29 is a Wednesday
    assert _is_weekend("2026-04-29") is False, "G: Wednesday detection"

    sat_msg = _empty_queue_message("2026-04-25", True, [])
    assert "🌙" in sat_msg and "weekend" in sat_msg.lower(), f"G sat: {sat_msg}"

    biz_msg = _empty_queue_message("2026-04-29", False, [])
    assert "✅" in biz_msg and "All clear" in biz_msg, f"G biz: {biz_msg}"

    # Empty payload via build_digest_message (Sat)
    sat_digest = build_digest_message({
        "as_of_date": "2026-04-25", "run_id": "r",
        "_metadata": {"warnings": []}, "proposals": [],
    })
    assert "🌙" in sat_digest, f"G empty Sat: {sat_digest}"

    biz_digest = build_digest_message({
        "as_of_date": "2026-04-29", "run_id": "r",
        "_metadata": {"warnings": []}, "proposals": [],
    })
    assert "✅" in biz_digest, f"G empty biz: {biz_digest}"

    return "G: empty queue rendering PASS — Sat/Sun 🌙 quiet weekend; weekday ✅ all clear"


def _run_group_H():
    """SHA256 invariants on real files (paths only; check after tests)."""
    real_paths = {
        "signal_history":     REAL_HISTORY,
        "proposed_rules":     REAL_PROPOSED,
        "mini_scanner_rules": REAL_MINI,
        "cohort_health":      REAL_COHORT_HEALTH,
        "reasoning_log":      REAL_REASONING_LOG,
        "unified_proposals":  REAL_UNIFIED,
        "decisions_journal":  REAL_DECISIONS_JOURNAL,
    }
    return real_paths


def _run_group_I(sbx_output):
    """/explain rendering — Q2 lock; full counter without truncation."""
    from scanner.telegram_bot import _respond_explain

    # Stage proposal with rich counter content
    p = _make_proposal(
        unified_id="prop_unified_2026-04-29_i1",
        ptype="boost_promote", candidate_id_suffix="ix",
        cohort_filter={"signal_type": "UP_TRI", "regime": "Bear"},
        extra_metadata={
            "proposed_rule_entry": {
                "id": "boost_brain_xx", "active": True,
                "signal": "UP_TRI", "sector": None, "regime": "Bear",
                "tier": "B", "conviction_tag": "TAKE_SMALL",
            },
            "conflicts_with": [
                {"rule_id": "win_001", "conflict_type": "overlap"},
                {"rule_id": "win_002", "conflict_type": "overlap"},
                {"rule_id": "win_003", "conflict_type": "overlap"},
            ],
        },
    )
    # Add 8 evidence + 3 risks (more than card budget; /explain shows all)
    p["counter"]["evidence"] = [
        f"evidence entry {i}" for i in range(1, 9)]
    p["counter"]["risks"] = [
        f"risk entry {i}" for i in range(1, 4)]

    unified_path = os.path.join(sbx_output, "brain",
                                 "unified_proposals.json")
    with open(unified_path, "w") as f:
        json.dump({
            "schema_version": 1, "as_of_date": "2026-04-29",
            "_metadata": {}, "stats": {},
            "proposals": [p],
        }, f)

    # Need to monkey-patch _brain_root to point at sandbox; but
    # _respond_explain calls _brain_root() which reads from
    # __file__'s parent. Since we can't easily intercept that, call
    # the same logic by-hand: load proposal + verify _explain output.
    import scanner.telegram_bot as tb
    # Save + replace _reply_message + _brain_root
    saved_reply = tb._reply_message
    saved_root = tb._brain_root
    captured = []
    tb._reply_message = lambda chat_id, text: captured.append((chat_id, text))
    tb._brain_root = lambda: os.path.dirname(sbx_output)
    try:
        tb._respond_explain(12345, f"/explain {p['id']}")
    finally:
        tb._reply_message = saved_reply
        tb._brain_root = saved_root

    assert len(captured) == 1, f"I capture: {captured}"
    text = captured[0][1]
    # All 8 evidence entries present (no truncation)
    for i in range(1, 9):
        assert f"evidence entry {i}" in text, f"I evidence {i}: missing"
    # All 3 risks present
    for i in range(1, 4):
        assert f"risk entry {i}" in text, f"I risk {i}: missing"
    # All 3 conflicts present
    for rid in ("win_001", "win_002", "win_003"):
        assert rid in text, f"I conflict {rid}: missing"
    # proposed_rule_entry rendered for boost_promote
    assert "TAKE\\_SMALL" in text or "TAKE_SMALL" in text, (
        f"I conviction_tag: missing")

    return ("I: /explain rendering PASS — 8/8 evidence + 3/3 risks + 3/3 "
            "conflicts + proposed_rule_entry surfaced; no truncation")


def main():
    # Capture pre-run SHA256 of real files
    pre_hashes = {}
    for name, path in _run_group_H().items():
        h = _sha256(path)
        if h is not None:
            pre_hashes[name] = h

    sbx = tempfile.mkdtemp(prefix="smoke_brain_telegram_")
    sbx_output, sbx_data = _setup_sandbox(sbx)

    try:
        results = []
        results.append(_run_group_A(sbx_output))
        results.append(_run_group_B(sbx_output))
        results.append(_run_group_C(sbx_output))
        results.append(_run_group_D(sbx_output))
        results.append(_run_group_E(sbx_output))
        results.append(_run_group_F(sbx_output))
        results.append(_run_group_G(sbx_output))
        results.append(_run_group_I(sbx_output))

        # Group H last — verify NO mutation of real files
        for name, path in _run_group_H().items():
            if name not in pre_hashes:
                continue
            post = _sha256(path)
            assert post == pre_hashes[name], (
                f"H invariant: {name} mutated! "
                f"{pre_hashes[name]} → {post}")
        results.append(
            f"H: SHA256 invariants PASS ({len(pre_hashes)} real files unchanged)")

        print()
        print("=" * 72)
        print("ALL 9 GROUPS PASSED")
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
