"""Smoke tests for shadow_ops/schemas.py."""
from __future__ import annotations

import json

import pytest

from shadow_ops.schemas import (
    CURRENT_SCHEMA_VERSION,
    CandidateSignal,
    Event,
    FillSimulation,
    LifecycleEvent,
    ScanEvent,
    TradeCard,
    ValidationError,
)


# ============================================================
# Helpers
# ============================================================

def _valid_scan_event_kwargs():
    return dict(
        event_id="scan_2026-05-05_001",
        event_type="scan_event",
        timestamp_utc="2026-05-05T10:35:42+00:00",
        scan_date="2026-05-05",
        regime="Bear",
        sub_regime="hot",
        sub_regime_inputs={"feat_nifty_vol_percentile_20d": 0.78},
        n_signals_universe=188,
        n_signals_post_filter=23,
        scan_status="OK",
        scan_duration_ms=4521,
        git_commit_sha="ae519fb6abcdef",
        data_versions={"enriched_signals_sha256": "abc..."},
    )


def _valid_candidate_signal_kwargs():
    return dict(
        event_id="cand_2026-05-05_LUPIN.NS_001",
        event_type="candidate_signal",
        timestamp_utc="2026-05-05T10:35:43+00:00",
        scan_event_id="scan_2026-05-05_001",
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
        rule_features_snapshot={"atr": 23.45, "stop": 1820.5},
    )


def _valid_trade_card_kwargs():
    return dict(
        event_id="card_snap_2026-05-05_LUPIN.NS_001",
        event_type="trade_card",
        timestamp_utc="2026-05-05T10:35:44+00:00",
        card_id="card_2026-05-05_LUPIN.NS",
        scan_event_id="scan_2026-05-05_001",
        candidate_signal_id="cand_2026-05-05_LUPIN.NS_001",
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
        state_history=[{"state": "PROPOSED", "timestamp_utc": "2026-05-05T10:35:44+00:00",
                        "reason": "rule_019_match"}],
    )


def _valid_lifecycle_event_kwargs():
    return dict(
        event_id="lc_2026-05-06_card_2026-05-05_LUPIN.NS_001",
        event_type="lifecycle_event",
        timestamp_utc="2026-05-06T03:50:01+00:00",
        card_id="card_2026-05-05_LUPIN.NS",
        from_state="PROPOSED",
        to_state="ACTIVE",
        reason="hypothetical_fill_at_next_open",
        trigger_data={"fill_date": "2026-05-06", "fill_price": 1892.50},
    )


def _valid_fill_simulation_kwargs():
    return dict(
        event_id="fill_2026-05-06_card_2026-05-05_LUPIN.NS",
        event_type="fill_simulation",
        timestamp_utc="2026-05-06T03:50:01+00:00",
        card_id="card_2026-05-05_LUPIN.NS",
        fill_attempt_type="ENTRY",
        fill_date="2026-05-06",
        fill_decision="FILLED",
        fill_price=1892.50,
        ohlcv={"open": 1890.0, "high": 1898.1, "low": 1881.0, "close": 1894.0, "volume": 2350000},
        fill_logic_applied="breakout_within_3_days_v1",
        slippage_bps=0,
        data_source="lab/cache/LUPIN_NS.parquet",
        data_source_sha256="abc123...",
    )


# ============================================================
# Construction tests (one per event type)
# ============================================================

def test_scan_event_construction():
    ev = ScanEvent(**_valid_scan_event_kwargs())
    assert ev.event_type == "scan_event"
    assert ev.regime == "Bear"
    assert ev.sub_regime == "hot"
    assert ev.event_schema_version == CURRENT_SCHEMA_VERSION


def test_candidate_signal_construction():
    ev = CandidateSignal(**_valid_candidate_signal_kwargs())
    assert ev.event_type == "candidate_signal"
    assert ev.symbol == "LUPIN.NS"
    assert ev.rule_019_match is True


def test_trade_card_construction():
    ev = TradeCard(**_valid_trade_card_kwargs())
    assert ev.event_type == "trade_card"
    assert ev.card_id == "card_2026-05-05_LUPIN.NS"
    assert ev.current_state == "PROPOSED"
    assert ev.realized_R is None  # optional unset


def test_lifecycle_event_construction():
    ev = LifecycleEvent(**_valid_lifecycle_event_kwargs())
    assert ev.event_type == "lifecycle_event"
    assert ev.from_state == "PROPOSED"
    assert ev.to_state == "ACTIVE"


def test_fill_simulation_construction():
    ev = FillSimulation(**_valid_fill_simulation_kwargs())
    assert ev.event_type == "fill_simulation"
    assert ev.fill_decision == "FILLED"
    assert ev.fill_price == 1892.50


# ============================================================
# Validation rejection tests
# ============================================================

def test_invalid_regime_raises():
    kw = _valid_scan_event_kwargs()
    kw["regime"] = "Sideways"
    with pytest.raises(ValidationError, match="regime"):
        ScanEvent(**kw)


def test_invalid_state_raises():
    kw = _valid_trade_card_kwargs()
    kw["current_state"] = "BOGUS_STATE"
    with pytest.raises(ValidationError, match="current_state"):
        TradeCard(**kw)


def test_required_field_missing_raises():
    """Empty string for a required field triggers validation error."""
    kw = _valid_scan_event_kwargs()
    kw["scan_date"] = ""
    with pytest.raises(ValidationError):
        ScanEvent(**kw)


def test_invalid_event_type_for_class_raises():
    """event_type field must match the subclass's _event_type_value discriminator."""
    kw = _valid_scan_event_kwargs()
    kw["event_type"] = "candidate_signal"  # wrong discriminator for ScanEvent
    with pytest.raises(ValidationError, match="event_type mismatch"):
        ScanEvent(**kw)


def test_invalid_iso_timestamp_raises():
    kw = _valid_scan_event_kwargs()
    kw["timestamp_utc"] = "not-a-timestamp"
    with pytest.raises(ValidationError, match="timestamp_utc"):
        ScanEvent(**kw)


# ============================================================
# Serialization round-trip
# ============================================================

def test_serialize_round_trip():
    """asdict → json → from_json_line produces an equal event."""
    original = ScanEvent(**_valid_scan_event_kwargs())
    line = original.to_json_line()
    parsed = Event.from_json_line(line)
    assert isinstance(parsed, ScanEvent)
    assert parsed.to_dict() == original.to_dict()


def test_optional_fields_handled():
    """None preserved through round-trip for optional fields."""
    kw = _valid_trade_card_kwargs()
    # actual_*, realized_* are None by default
    original = TradeCard(**kw)
    line = original.to_json_line()
    parsed = Event.from_json_line(line)
    assert parsed.actual_entry_date is None
    assert parsed.realized_R is None
    assert parsed.exit_reason is None


def test_classvar_not_in_dict():
    """_event_type_value ClassVar should NOT appear in asdict() / to_dict()."""
    ev = ScanEvent(**_valid_scan_event_kwargs())
    d = ev.to_dict()
    assert "_event_type_value" not in d
    # And not in the JSON line either
    line = ev.to_json_line()
    parsed_dict = json.loads(line)
    assert "_event_type_value" not in parsed_dict


def test_validate_idempotent():
    """validate() can be called multiple times without error or side effects."""
    ev = ScanEvent(**_valid_scan_event_kwargs())
    d1 = ev.to_dict()
    ev.validate()
    ev.validate()
    ev.validate()
    d2 = ev.to_dict()
    assert d1 == d2  # no mutation


def test_sort_keys_deterministic():
    """to_json_line uses sort_keys=True — same content produces byte-identical JSON."""
    ev1 = ScanEvent(**_valid_scan_event_kwargs())
    line1 = ev1.to_json_line()
    # Round-trip and re-serialize: should produce byte-identical output
    parsed = Event.from_json_line(line1)
    line2 = parsed.to_json_line()
    assert line1 == line2

    # Verify keys ARE sorted alphabetically in the JSON output
    parsed_keys = list(json.loads(line1).keys())
    assert parsed_keys == sorted(parsed_keys), \
        f"keys not sorted: {parsed_keys}"


def test_dispatch_unknown_event_type_raises():
    """from_json_line on unknown event_type raises ValidationError."""
    bogus = '{"event_id":"x","event_type":"bogus","timestamp_utc":"2026-05-05T00:00:00+00:00","event_schema_version":"v1"}'
    with pytest.raises(ValidationError, match="unknown event_type"):
        Event.from_json_line(bogus)


def test_forward_compat_extra_fields_dropped():
    """Reading a JSON line with extra unknown fields drops them gracefully."""
    kw = _valid_scan_event_kwargs()
    ev = ScanEvent(**kw)
    d = ev.to_dict()
    d["future_field_not_in_v1"] = "ignored"
    line = json.dumps(d)
    parsed = Event.from_json_line(line)
    assert isinstance(parsed, ScanEvent)
    assert not hasattr(parsed, "future_field_not_in_v1")
