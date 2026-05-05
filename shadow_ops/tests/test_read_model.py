"""Smoke tests for shadow_ops/read_model.py.

Pure derivation tests: seed a run directory with TradeCard / LifecycleEvent /
FillSimulation events, run regenerate_read_model, assert TradeCardCurrent
rows have the expected derived fields.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Optional

import pytest

from shadow_ops.journal import JournalWriter, JournalReader
from shadow_ops.read_model import (
    OUTPUT_FILENAME,
    TradeCardCurrent,
    regenerate_read_model,
)
from shadow_ops.schemas import (
    FillSimulation,
    LifecycleEvent,
    TradeCard,
)


# ============================================================
# Helpers
# ============================================================

def _make_card(card_id: str = "card_2018-10-26_TEST.NS",
               symbol: str = "TEST.NS",
               proposed_entry: float = 100.0,
               proposed_stop: float = 95.0,
               proposed_target: float = 110.0,
               scan_date: str = "2018-10-26") -> TradeCard:
    return TradeCard(
        event_id=f"card_snap_{scan_date}_{symbol}_001",
        event_type="trade_card",
        timestamp_utc=f"{scan_date}T10:35:44+00:00",
        card_id=card_id,
        scan_event_id=f"scan_{scan_date}_001",
        candidate_signal_id=f"cand_{scan_date}_{symbol}_001",
        symbol=symbol,
        sector="Pharma",
        rule_id="rule_019_bear_uptri_hot_refinement",
        rule_031_confirm=0,
        kill_001_match=False,
        scan_date=scan_date,
        proposed_entry_price=proposed_entry,
        proposed_stop=proposed_stop,
        proposed_target=proposed_target,
        atr=2.0,
        current_state="PROPOSED",
        state_history=[{"state": "PROPOSED",
                        "timestamp_utc": f"{scan_date}T10:35:44+00:00",
                        "reason": "rule_019_match"}],
    )


def _make_entry_lc(card_id: str, eval_iso: str = "2018-10-29",
                   actual_open: float = 99.5) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card_id}_001",
        event_type="lifecycle_event",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=card_id,
        from_state="PROPOSED",
        to_state="ACTIVE",
        reason="entry_t1_open",
        trigger_data={"actual_entry_price": actual_open,
                      "actual_entry_date": eval_iso,
                      "fill_event_id": f"fill_{eval_iso}_{card_id}_001"},
    )


def _make_entry_fill(card_id: str, eval_iso: str = "2018-10-29",
                     d1_open: float = 99.5,
                     data_source: str = "lab/cache/TEST_NS.parquet",
                     sha: str = "a" * 64) -> FillSimulation:
    return FillSimulation(
        event_id=f"fill_{eval_iso}_{card_id}_001",
        event_type="fill_simulation",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=card_id,
        fill_attempt_type="ENTRY",
        fill_date=eval_iso,
        fill_decision="FILLED",
        fill_price=d1_open,
        ohlcv={"open": d1_open, "high": 100.0, "low": 99.0,
               "close": 99.8, "volume": 1_000_000},
        fill_logic_applied="audit_faithful_t1_open_unconditional",
        pnl_pct=None,
        data_source=data_source,
        data_source_sha256=sha,
    )


def _make_terminal_lc(card_id: str, to_state: str, day_n: int,
                      eval_iso: str, exit_price: float, pnl_pct: float,
                      reason: str, seq: int = 1) -> LifecycleEvent:
    return LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=card_id,
        from_state="ACTIVE",
        to_state=to_state,
        reason=reason,
        trigger_data={"exit_price": exit_price,
                      "exit_date": eval_iso,
                      "exit_day": day_n,
                      "pnl_pct": pnl_pct,
                      "fill_event_id": f"fill_{eval_iso}_{card_id}_{seq:03d}"},
    )


def _make_terminal_fill(card_id: str, fill_attempt_type: str,
                        eval_iso: str, exit_price: float, pnl_pct: float,
                        fill_logic: str, seq: int = 1,
                        data_source: str = "lab/cache/TEST_NS.parquet",
                        sha: str = "b" * 64) -> FillSimulation:
    return FillSimulation(
        event_id=f"fill_{eval_iso}_{card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=card_id,
        fill_attempt_type=fill_attempt_type,
        fill_date=eval_iso,
        fill_decision="FILLED",
        fill_price=exit_price,
        ohlcv={"open": 99.0, "high": 100.0, "low": 94.0, "close": 95.0, "volume": 1_000_000},
        fill_logic_applied=fill_logic,
        pnl_pct=pnl_pct,
        data_source=data_source,
        data_source_sha256=sha,
    )


def _seed(run_dir: Path, events) -> None:
    w = JournalWriter(run_dir)
    for ev in events:
        w.write_event(ev)


def _read_currents(run_dir: Path) -> List[dict]:
    path = run_dir / OUTPUT_FILENAME
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ============================================================
# Tests
# ============================================================

def test_proposed_only_card_yields_state_PROPOSED_with_nulls(tmp_path):
    """Card with no lifecycle events stays PROPOSED; actual_* / exit_* / realized_*
    all None."""
    card = _make_card()
    _seed(tmp_path, [card])

    result = regenerate_read_model(tmp_path)
    assert result.n_cards == 1 and result.n_proposed == 1

    rows = _read_currents(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["current_state"] == "PROPOSED"
    assert row["actual_entry_date"] is None
    assert row["actual_entry_price"] is None
    assert row["actual_exit_date"] is None
    assert row["actual_exit_price"] is None
    assert row["exit_reason"] is None
    assert row["exit_day"] is None
    assert row["realized_pnl_pct"] is None
    assert row["realized_R"] is None
    assert row["data_source"] is None
    assert row["data_source_sha256"] is None
    assert row["direction"] == "LONG"


def test_active_card_populates_actual_entry_only(tmp_path):
    """Card has PROPOSED → ACTIVE only. actual_entry_* populated; exit_* still None."""
    card = _make_card()
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, d1_open=99.5),
        _make_entry_lc(card.card_id, actual_open=99.5),
    ])

    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "ACTIVE"
    assert row["actual_entry_date"] == "2018-10-29"
    assert row["actual_entry_price"] == 99.5
    assert row["actual_exit_date"] is None
    assert row["realized_pnl_pct"] is None
    assert row["data_source"] is None  # spec: only populated for terminal cards
    assert row["data_source_sha256"] is None


def test_terminal_stop_card_populates_all_actuals(tmp_path):
    """Card walked through PROPOSED → ACTIVE → HYPOTHETICAL_STOPPED."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, d1_open=99.5),
        _make_entry_lc(card.card_id, actual_open=99.5),
        _make_terminal_fill(card.card_id, "STOP", "2018-10-31",
                            exit_price=95.0, pnl_pct=-5.0,
                            fill_logic="stop_hit_d3"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_STOPPED", day_n=3,
                          eval_iso="2018-10-31", exit_price=95.0, pnl_pct=-5.0,
                          reason="stop_hit_d3"),
    ])

    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "HYPOTHETICAL_STOPPED"
    assert row["actual_entry_price"] == 99.5
    assert row["actual_exit_date"] == "2018-10-31"
    assert row["actual_exit_price"] == 95.0
    assert row["exit_reason"] == "stop_hit_d3"
    assert row["exit_day"] == 3
    assert row["realized_pnl_pct"] == -5.0
    assert row["data_source"] == "lab/cache/TEST_NS.parquet"
    assert row["data_source_sha256"] == "b" * 64


def test_terminal_target_card_populates_all_actuals(tmp_path):
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, d1_open=100.5),
        _make_entry_lc(card.card_id, actual_open=100.5),
        _make_terminal_fill(card.card_id, "TARGET", "2018-11-01",
                            exit_price=110.0, pnl_pct=10.0,
                            fill_logic="target_hit_d4"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_FILLED", day_n=4,
                          eval_iso="2018-11-01", exit_price=110.0, pnl_pct=10.0,
                          reason="target_hit_d4"),
    ])

    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "HYPOTHETICAL_FILLED"
    assert row["actual_exit_price"] == 110.0
    assert row["exit_reason"] == "target_hit_d4"
    assert row["exit_day"] == 4
    assert row["realized_pnl_pct"] == 10.0


def test_terminal_expired_card_populates_all_actuals(tmp_path):
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, d1_open=100.0),
        _make_entry_lc(card.card_id, actual_open=100.0),
        _make_terminal_fill(card.card_id, "EXPIRY", "2018-11-05",
                            exit_price=102.0, pnl_pct=2.0,
                            fill_logic="day6_open_exit_win"),
        _make_terminal_lc(card.card_id, "EXPIRED", day_n=6,
                          eval_iso="2018-11-05", exit_price=102.0, pnl_pct=2.0,
                          reason="d6_open_exit"),
    ])

    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "EXPIRED"
    assert row["exit_reason"] == "d6_open_exit"
    assert row["exit_day"] == 6
    assert row["realized_pnl_pct"] == 2.0


# ============================================================
# realized_R derivation
# ============================================================

def test_realized_R_stop_hit_approximately_minus_one(tmp_path):
    """Exit at stop price = 1R loss by definition. Tolerance 0.01."""
    # entry=1234.56, stop=1187.34 → risk_pct ≈ 3.8254%
    # exit at stop: pnl = (1187.34-1234.56)/1234.56*100 = -3.8254... → rounded -3.83
    # realized_R = -3.83 / 3.8254... ≈ -1.0012  (within tolerance of -1.0)
    card = _make_card(proposed_entry=1234.56, proposed_stop=1187.34,
                      proposed_target=1329.00)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id),
        _make_entry_lc(card.card_id),
        _make_terminal_fill(card.card_id, "STOP", "2018-10-31",
                            exit_price=1187.34, pnl_pct=-3.83,
                            fill_logic="stop_hit_d3"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_STOPPED", day_n=3,
                          eval_iso="2018-10-31", exit_price=1187.34, pnl_pct=-3.83,
                          reason="stop_hit_d3"),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert abs(row["realized_R"] - (-1.0)) < 0.01


def test_realized_R_target_hit_approximately_plus_two(tmp_path):
    """Exit at 2R target = 2.0R win by definition. Tolerance 0.01."""
    # entry=1234.56, stop=1187.34, target=1329.00 → 2R target
    # exit at target: pnl = (1329-1234.56)/1234.56*100 = 7.6492... → rounded 7.65
    # risk_pct = 47.22/1234.56*100 = 3.8254...
    # realized_R = 7.65 / 3.8254 ≈ 1.9998
    card = _make_card(proposed_entry=1234.56, proposed_stop=1187.34,
                      proposed_target=1329.00)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id),
        _make_entry_lc(card.card_id),
        _make_terminal_fill(card.card_id, "TARGET", "2018-11-01",
                            exit_price=1329.00, pnl_pct=7.65,
                            fill_logic="target_hit_d4"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_FILLED", day_n=4,
                          eval_iso="2018-11-01", exit_price=1329.00, pnl_pct=7.65,
                          reason="target_hit_d4"),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert abs(row["realized_R"] - 2.0) < 0.01


def test_realized_R_None_when_pnl_pct_None(tmp_path):
    """ACTIVE-only card: no terminal fill → pnl_pct None → realized_R None."""
    card = _make_card()
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id),
        _make_entry_lc(card.card_id),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["realized_pnl_pct"] is None
    assert row["realized_R"] is None


def test_realized_R_None_when_risk_pct_zero(tmp_path):
    """Degenerate entry == stop → risk_pct == 0 → realized_R left None."""
    card = _make_card(proposed_entry=100.0, proposed_stop=100.0,
                      proposed_target=110.0)
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, d1_open=100.0),
        _make_entry_lc(card.card_id, actual_open=100.0),
        _make_terminal_fill(card.card_id, "TARGET", "2018-11-01",
                            exit_price=110.0, pnl_pct=10.0,
                            fill_logic="target_hit_d4"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_FILLED", day_n=4,
                          eval_iso="2018-11-01", exit_price=110.0, pnl_pct=10.0,
                          reason="target_hit_d4"),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["realized_pnl_pct"] == 10.0
    assert row["realized_R"] is None  # div-by-zero guard


# ============================================================
# State history + same-day-stop
# ============================================================

def test_state_history_walks_full_timeline(tmp_path):
    """state_history starts with PROPOSED then appends one entry per lifecycle event."""
    card = _make_card()
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id),
        _make_entry_lc(card.card_id),
        _make_terminal_fill(card.card_id, "STOP", "2018-10-31",
                            exit_price=95.0, pnl_pct=-5.0,
                            fill_logic="stop_hit_d3"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_STOPPED", day_n=3,
                          eval_iso="2018-10-31", exit_price=95.0, pnl_pct=-5.0,
                          reason="stop_hit_d3"),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    history = row["state_history"]
    assert [h["state"] for h in history] == [
        "PROPOSED", "ACTIVE", "HYPOTHETICAL_STOPPED"
    ]
    assert history[0]["reason"] == "rule_019_match"
    assert history[1]["reason"] == "entry_t1_open"
    assert history[2]["reason"] == "stop_hit_d3"


def test_d1_same_day_entry_stop_yields_correct_current_state(tmp_path):
    """D1 entry + same-day D1 stop hit → final state HYPOTHETICAL_STOPPED, exit_day=1."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    eval_iso = "2018-10-29"
    _seed(tmp_path, [
        card,
        # ENTRY fill seq=001
        _make_entry_fill(card.card_id, eval_iso=eval_iso, d1_open=95.0),
        _make_entry_lc(card.card_id, eval_iso=eval_iso, actual_open=95.0),
        # STOP fill seq=002 same day
        _make_terminal_fill(card.card_id, "STOP", eval_iso,
                            exit_price=95.0, pnl_pct=-5.0,
                            fill_logic="stop_hit_d1", seq=2),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_STOPPED", day_n=1,
                          eval_iso=eval_iso, exit_price=95.0, pnl_pct=-5.0,
                          reason="stop_hit_d1", seq=2),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "HYPOTHETICAL_STOPPED"
    assert row["exit_day"] == 1
    assert row["actual_entry_price"] == 95.0
    assert row["actual_exit_price"] == 95.0


# ============================================================
# Output file + idempotency
# ============================================================

def test_regenerate_overwrites_existing_file(tmp_path):
    """Pre-existing trade_cards_current.jsonl is overwritten, not appended."""
    output = tmp_path / OUTPUT_FILENAME
    output.write_text("STALE_LINE_FROM_PREVIOUS_RUN\n")

    card = _make_card()
    _seed(tmp_path, [card])
    regenerate_read_model(tmp_path)

    content = output.read_text()
    assert "STALE_LINE_FROM_PREVIOUS_RUN" not in content
    assert content.count("\n") == 1  # exactly one card


def test_regenerate_idempotent_byte_identical(tmp_path):
    """Run twice → byte-identical output."""
    card = _make_card()
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id),
        _make_entry_lc(card.card_id),
        _make_terminal_fill(card.card_id, "TARGET", "2018-11-01",
                            exit_price=110.0, pnl_pct=10.0,
                            fill_logic="target_hit_d4"),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_FILLED", day_n=4,
                          eval_iso="2018-11-01", exit_price=110.0, pnl_pct=10.0,
                          reason="target_hit_d4"),
    ])
    output = tmp_path / OUTPUT_FILENAME

    r1 = regenerate_read_model(tmp_path)
    bytes1 = output.read_bytes()
    r2 = regenerate_read_model(tmp_path)
    bytes2 = output.read_bytes()
    assert bytes1 == bytes2
    assert r1.output_sha256 == r2.output_sha256


def test_checksum_sidecar_updated_on_regeneration(tmp_path):
    """Sidecar hex-encoded SHA-256 matches the actual file content."""
    card = _make_card()
    _seed(tmp_path, [card])
    result = regenerate_read_model(tmp_path)
    output = tmp_path / OUTPUT_FILENAME
    sidecar = Path(str(output) + ".checksum")

    assert sidecar.exists()
    sha_from_sidecar = sidecar.read_text().strip()
    sha_from_file = hashlib.sha256(output.read_bytes()).hexdigest()
    assert sha_from_sidecar == sha_from_file
    assert sha_from_sidecar == result.output_sha256
    assert len(sha_from_sidecar) == 64


# ============================================================
# Provenance + edge cases
# ============================================================

def test_data_source_sha_propagates_from_terminal_fill(tmp_path):
    """Terminal fill's data_source + SHA appear in TradeCardCurrent."""
    card = _make_card()
    expected_sha = "c" * 64
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, sha="a" * 64),  # different SHA on entry
        _make_entry_lc(card.card_id),
        _make_terminal_fill(card.card_id, "TARGET", "2018-11-01",
                            exit_price=110.0, pnl_pct=10.0,
                            fill_logic="target_hit_d4",
                            data_source="lab/cache/TEST_NS.parquet",
                            sha=expected_sha),
        _make_terminal_lc(card.card_id, "HYPOTHETICAL_FILLED", day_n=4,
                          eval_iso="2018-11-01", exit_price=110.0, pnl_pct=10.0,
                          reason="target_hit_d4"),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    # Terminal fill's SHA wins (latest), not the entry fill's
    assert row["data_source_sha256"] == expected_sha
    assert row["data_source"] == "lab/cache/TEST_NS.parquet"


def test_data_source_None_for_active_only_card(tmp_path):
    """Spec: data_source on TradeCardCurrent is populated only from terminal fills."""
    card = _make_card()
    _seed(tmp_path, [
        card,
        _make_entry_fill(card.card_id, data_source="lab/cache/TEST_NS.parquet",
                         sha="a" * 64),
        _make_entry_lc(card.card_id),
    ])
    regenerate_read_model(tmp_path)
    row = _read_currents(tmp_path)[0]
    assert row["current_state"] == "ACTIVE"
    assert row["data_source"] is None
    assert row["data_source_sha256"] is None


def test_orphan_lifecycle_events_silently_ignored(tmp_path):
    """Lifecycle events for unknown card_ids don't crash the regenerator;
    only events matching a TradeCard's card_id are walked."""
    card = _make_card(card_id="card_KNOWN")
    orphan_lc = LifecycleEvent(
        event_id="lc_2018-10-29_card_ORPHAN_001",
        event_type="lifecycle_event",
        timestamp_utc="2018-10-29T03:50:01+00:00",
        card_id="card_ORPHAN",  # no matching TradeCard
        from_state="PROPOSED", to_state="ACTIVE",
        reason="entry_t1_open",
        trigger_data={"actual_entry_price": 99.5,
                      "actual_entry_date": "2018-10-29"},
    )
    _seed(tmp_path, [card, orphan_lc])

    result = regenerate_read_model(tmp_path)
    assert result.n_cards == 1  # only the known card; orphan ignored
    rows = _read_currents(tmp_path)
    assert len(rows) == 1
    assert rows[0]["card_id"] == "card_KNOWN"


def test_empty_run_dir_returns_zero_cards(tmp_path):
    """No event files at all → result.n_cards == 0; output file is empty (0 lines)."""
    result = regenerate_read_model(tmp_path)
    assert result.n_cards == 0
    output = tmp_path / OUTPUT_FILENAME
    assert output.exists()
    assert output.read_text() == ""
