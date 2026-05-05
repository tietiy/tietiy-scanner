"""Smoke tests for shadow_ops/journal.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadow_ops.journal import (
    ChecksumMismatchError,
    DuplicateEventIdError,
    InvalidJsonlError,
    JournalReader,
    JournalWriter,
)
from shadow_ops.schemas import (
    CandidateSignal,
    LifecycleEvent,
    ScanEvent,
    TradeCard,
    FillSimulation,
)


# ============================================================
# Helpers (factory functions for valid events)
# ============================================================

def _make_scan_event(eid="scan_001"):
    return ScanEvent(
        event_id=eid,
        event_type="scan_event",
        timestamp_utc="2026-05-05T10:35:42+00:00",
        scan_date="2026-05-05",
        regime="Bear",
        sub_regime="hot",
        sub_regime_inputs={"vp": 0.78},
        n_signals_universe=188,
        n_signals_post_filter=23,
        scan_status="OK",
        scan_duration_ms=4521,
        git_commit_sha="abc123",
        data_versions={},
    )


def _make_candidate(eid="cand_001", scan_event_id="scan_001"):
    return CandidateSignal(
        event_id=eid,
        event_type="candidate_signal",
        timestamp_utc="2026-05-05T10:35:43+00:00",
        scan_event_id=scan_event_id,
        scan_date="2026-05-05",
        symbol="LUPIN.NS",
        sector="Pharma",
        signal="UP_TRI",
        regime="Bear",
        sub_regime="hot",
        rule_019_match=True,
        rule_031_match=False,
        kill_001_match=False,
        trigger_disposition="TRADE_CARD_PROPOSED",
        rule_features_snapshot={},
    )


def _make_trade_card(eid="card_snap_001", card_id="card_001"):
    return TradeCard(
        event_id=eid,
        event_type="trade_card",
        timestamp_utc="2026-05-05T10:35:44+00:00",
        card_id=card_id,
        scan_event_id="scan_001",
        candidate_signal_id="cand_001",
        symbol="LUPIN.NS",
        sector="Pharma",
        rule_id="rule_019_bear_uptri_hot_refinement",
        rule_031_confirm=0,
        kill_001_match=False,
        scan_date="2026-05-05",
        proposed_entry_price=1890.20,
        proposed_stop=1820.50,
        proposed_target=2030.30,
        atr=23.45,
        current_state="PROPOSED",
    )


def _make_lifecycle(eid="lc_001", card_id="card_001",
                    from_state="PROPOSED", to_state="ACTIVE"):
    return LifecycleEvent(
        event_id=eid,
        event_type="lifecycle_event",
        timestamp_utc="2026-05-06T03:50:01+00:00",
        card_id=card_id,
        from_state=from_state,
        to_state=to_state,
        reason="hypothetical_fill",
        trigger_data={},
    )


def _make_fill_sim(eid="fill_001", card_id="card_001"):
    return FillSimulation(
        event_id=eid,
        event_type="fill_simulation",
        timestamp_utc="2026-05-06T03:50:01+00:00",
        card_id=card_id,
        fill_attempt_type="ENTRY",
        fill_date="2026-05-06",
        fill_decision="FILLED",
        fill_price=1892.50,
        ohlcv={"open": 1890.0, "high": 1898.1, "low": 1881.0, "close": 1894.0, "volume": 2350000},
        fill_logic_applied="breakout_within_3_days_v1",
    )


# ============================================================
# Tests
# ============================================================

def test_writer_creates_files_on_first_write(tmp_path):
    """First write creates the JSONL file + checksum sidecar."""
    w = JournalWriter(tmp_path)
    ev = _make_scan_event()
    w.write_event(ev)
    assert (tmp_path / "scan_events.jsonl").exists()
    assert (tmp_path / "scan_events.jsonl.checksum").exists()


def test_write_then_read_round_trip(tmp_path):
    """Write events, read back, verify content equality."""
    w = JournalWriter(tmp_path)
    ev = _make_scan_event(eid="scan_xyz")
    w.write_event(ev)
    r = JournalReader(tmp_path)
    events = r.all_scan_events()
    assert len(events) == 1
    assert events[0].event_id == "scan_xyz"
    assert events[0].to_dict() == ev.to_dict()


def test_duplicate_event_id_raises(tmp_path):
    """Writing two events with same event_id to same file raises."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event(eid="dup"))
    with pytest.raises(DuplicateEventIdError, match="dup"):
        w.write_event(_make_scan_event(eid="dup"))


def test_event_id_unique_per_file_not_global(tmp_path):
    """Same event_id in different event-type files is allowed (different files)."""
    w = JournalWriter(tmp_path)
    # ScanEvent with event_id="X" and CandidateSignal with event_id="X" — both succeed
    w.write_event(_make_scan_event(eid="X"))
    w.write_event(_make_candidate(eid="X"))
    # Both files should exist with one event each
    r = JournalReader(tmp_path)
    assert len(r.all_scan_events()) == 1
    assert len(r.all_candidate_signals()) == 1


def test_checksum_detects_external_modification(tmp_path):
    """Tamper with JSONL file directly; next write_event raises ChecksumMismatchError."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event(eid="first"))
    # Tamper: append a line directly (without going through the writer)
    jsonl_path = tmp_path / "scan_events.jsonl"
    with open(jsonl_path, "a") as f:
        f.write('{"event_id": "tampered", "event_type": "scan_event"}\n')
    # Next write should detect the mismatch
    # Use a fresh writer to reset id_cache (simulates a new process)
    w2 = JournalWriter(tmp_path)
    with pytest.raises(ChecksumMismatchError):
        w2.write_event(_make_scan_event(eid="second"))


def test_checksum_initialized_on_first_write(tmp_path):
    """First write to a new file initializes the checksum sidecar."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event())
    ck_path = tmp_path / "scan_events.jsonl.checksum"
    assert ck_path.exists()
    content = ck_path.read_text().strip()
    # Should be a 64-char hex SHA-256 digest
    assert len(content) == 64
    assert all(c in "0123456789abcdef" for c in content)


def test_reader_returns_empty_list_for_missing_file(tmp_path):
    """Reading from a run_dir with no JSONL files returns empty lists, no error."""
    r = JournalReader(tmp_path)
    assert r.all_scan_events() == []
    assert r.all_candidate_signals() == []
    assert r.all_trade_cards() == []
    assert r.all_lifecycle_events() == []
    assert r.all_fill_simulations() == []


def test_reader_returns_events_in_write_order(tmp_path):
    """Events read back in the order they were written."""
    w = JournalWriter(tmp_path)
    for i in range(5):
        w.write_event(_make_scan_event(eid=f"scan_{i:03d}"))
    r = JournalReader(tmp_path)
    events = r.all_scan_events()
    assert len(events) == 5
    assert [e.event_id for e in events] == [f"scan_{i:03d}" for i in range(5)]


def test_trade_card_history_returns_lifecycle_events_for_card(tmp_path):
    """trade_card_history filters lifecycle events by card_id, in write order."""
    w = JournalWriter(tmp_path)
    # Two cards, three lifecycle events for each
    w.write_event(_make_lifecycle(eid="lc1_a", card_id="card_A",
                                   from_state="PROPOSED", to_state="ACTIVE"))
    w.write_event(_make_lifecycle(eid="lc1_b", card_id="card_B",
                                   from_state="PROPOSED", to_state="NO_FILL"))
    w.write_event(_make_lifecycle(eid="lc2_a", card_id="card_A",
                                   from_state="ACTIVE", to_state="HYPOTHETICAL_FILLED"))
    w.write_event(_make_lifecycle(eid="lc3_a", card_id="card_A",
                                   from_state="HYPOTHETICAL_FILLED",
                                   to_state="HYPOTHETICAL_STOPPED"))

    r = JournalReader(tmp_path)
    history_a = r.trade_card_history("card_A")
    assert [e.event_id for e in history_a] == ["lc1_a", "lc2_a", "lc3_a"]
    history_b = r.trade_card_history("card_B")
    assert [e.event_id for e in history_b] == ["lc1_b"]


def test_latest_trade_card_state_derives_from_lifecycle(tmp_path):
    """latest_trade_card_state returns the to_state of the most recent lifecycle event."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_lifecycle(eid="lc1", card_id="card_A",
                                   from_state="PROPOSED", to_state="ACTIVE"))
    w.write_event(_make_lifecycle(eid="lc2", card_id="card_A",
                                   from_state="ACTIVE",
                                   to_state="HYPOTHETICAL_FILLED"))
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state("card_A") == "HYPOTHETICAL_FILLED"


def test_latest_trade_card_state_missing_card_raises(tmp_path):
    r = JournalReader(tmp_path)
    with pytest.raises(KeyError, match="card_unknown"):
        r.latest_trade_card_state("card_unknown")


def test_invalid_jsonl_line_raises_clear_error(tmp_path):
    """Reading a malformed JSONL line raises InvalidJsonlError with location info."""
    # Write one valid event via the writer to establish the file properly,
    # then manually append a malformed line as line 2.
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event(eid="good_line_1"))
    jsonl_path = tmp_path / "scan_events.jsonl"
    with open(jsonl_path, "a") as f:
        f.write("not-valid-json\n")

    r = JournalReader(tmp_path)
    with pytest.raises(InvalidJsonlError) as exc_info:
        r.all_scan_events()
    # Error message includes file path + line number
    assert "scan_events.jsonl" in str(exc_info.value)
    assert ":2" in str(exc_info.value)  # line 2 is the bad one


def test_event_class_dispatch(tmp_path):
    """Writer routes events to the correct file based on type."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event(eid="s1"))
    w.write_event(_make_candidate(eid="c1"))
    w.write_event(_make_trade_card(eid="t1"))
    w.write_event(_make_lifecycle(eid="l1"))
    w.write_event(_make_fill_sim(eid="f1"))

    expected_files = {
        "scan_events.jsonl": "scan_event",
        "candidate_signals.jsonl": "candidate_signal",
        "trade_cards.jsonl": "trade_card",
        "lifecycle_events.jsonl": "lifecycle_event",
        "fill_simulations.jsonl": "fill_simulation",
    }
    for filename, expected_type in expected_files.items():
        path = tmp_path / filename
        assert path.exists(), f"{filename} should exist"
        with open(path) as f:
            line = f.readline().strip()
            assert json.loads(line)["event_type"] == expected_type


def test_find_event_returns_correct_event(tmp_path):
    """find_event returns matching event or None."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan_event(eid="want"))
    w.write_event(_make_scan_event(eid="other"))

    r = JournalReader(tmp_path)
    found = r.find_event("want", ScanEvent)
    assert found is not None
    assert found.event_id == "want"

    missing = r.find_event("does_not_exist", ScanEvent)
    assert missing is None


def test_flock_allows_sequential_writes(tmp_path):
    """flock releases properly so sequential writes succeed (smoke check)."""
    w = JournalWriter(tmp_path)
    # 10 sequential writes — each acquires + releases the flock
    for i in range(10):
        w.write_event(_make_scan_event(eid=f"seq_{i}"))
    assert len(JournalReader(tmp_path).all_scan_events()) == 10
