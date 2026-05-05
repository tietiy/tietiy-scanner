"""Smoke tests for shadow_ops/alerts.py."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from shadow_ops.alerts import (
    ACKS_FILENAME,
    ALERTS_FILENAME,
    Alert,
    AlertValidationError,
    UnknownAlertIdError,
    acknowledge_alert,
    emit_alert,
    list_acknowledgments,
    list_alerts,
    unacknowledged_critical,
)


def test_emit_alert_creates_jsonl_file_on_first_call(tmp_path):
    a = emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE",
                   "data_ingest", "yfinance fetch failed for LTIM.NS",
                   context={"failed_symbols": ["LTIM.NS"]},
                   logical_date="2026-05-06")
    p = tmp_path / ALERTS_FILENAME
    assert p.exists()
    rec = json.loads(p.read_text().strip())
    assert rec["alert_id"].startswith("alert_2026-05-06_")
    assert rec["severity"] == "WARNING"
    assert rec["alert_type"] == "DATA_INGEST_FAILURE"
    assert rec["context"] == {"failed_symbols": ["LTIM.NS"]}
    assert a.alert_id == rec["alert_id"]


def test_emit_alert_appends_to_existing_jsonl(tmp_path):
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
               "first", logical_date="2026-05-06")
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_PARTIAL", "data_ingest",
               "second", logical_date="2026-05-06")
    alerts = list_alerts(tmp_path)
    assert len(alerts) == 2
    assert [a.message for a in alerts] == ["first", "second"]


def test_alert_id_format_and_per_date_sequence(tmp_path):
    """alert_id = alert_<logical_date>_<seq>; seq is per-(run_dir, logical_date)."""
    a1 = emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
                    "x1", logical_date="2026-05-06")
    a2 = emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
                    "x2", logical_date="2026-05-06")
    a3 = emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
                    "y1", logical_date="2026-05-07")
    assert a1.alert_id == "alert_2026-05-06_001"
    assert a2.alert_id == "alert_2026-05-06_002"
    assert a3.alert_id == "alert_2026-05-07_001"


def test_alert_validation_rejects_invalid_severity(tmp_path):
    with pytest.raises(AlertValidationError, match="severity"):
        emit_alert(tmp_path, "PROBABLY_BAD", "DATA_INGEST_FAILURE",
                   "data_ingest", "x", logical_date="2026-05-06")


def test_alert_validation_rejects_invalid_alert_type(tmp_path):
    with pytest.raises(AlertValidationError, match="alert_type"):
        emit_alert(tmp_path, "WARNING", "MADE_UP_TYPE",
                   "data_ingest", "x", logical_date="2026-05-06")


def test_emit_alert_default_logical_date_is_today_utc(tmp_path):
    """When logical_date arg omitted, it defaults to today UTC."""
    from datetime import datetime, timezone
    today_iso = datetime.now(timezone.utc).date().isoformat()
    a = emit_alert(tmp_path, "INFO", "SCAN_PARTIAL", "daily_scan", "test")
    assert a.logical_date == today_iso


def test_emit_alert_creates_run_dir_if_missing(tmp_path):
    new_dir = tmp_path / "fresh_campaign"
    assert not new_dir.exists()
    emit_alert(new_dir, "CRITICAL", "PRE_SCAN_CHECK_FAILURE",
               "pre_scan_check", "test", logical_date="2026-05-06")
    assert new_dir.exists()
    assert (new_dir / ALERTS_FILENAME).exists()


def test_acknowledge_alert_writes_to_sidecar(tmp_path):
    a = emit_alert(tmp_path, "CRITICAL", "REGIME_CLASSIFIER_ERROR",
                   "regime_classifier", "test failure",
                   logical_date="2026-05-06")
    rec = acknowledge_alert(tmp_path, a.alert_id,
                             reason="data was actually fine on retry",
                             by="operator")
    assert rec["alert_id"] == a.alert_id
    assert "acknowledged_at_utc" in rec
    assert rec["acknowledged_by"] == "operator"
    p = tmp_path / ACKS_FILENAME
    assert p.exists()
    line = p.read_text().strip()
    assert json.loads(line)["alert_id"] == a.alert_id
    # alerts.jsonl is unchanged (sidecar pattern)
    alerts_line = (tmp_path / ALERTS_FILENAME).read_text().strip()
    assert "acknowledged_at_utc" not in alerts_line


def test_acknowledge_alert_unknown_alert_id_raises(tmp_path):
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
               "x", logical_date="2026-05-06")
    with pytest.raises(UnknownAlertIdError, match="alert_NOT_REAL"):
        acknowledge_alert(tmp_path, "alert_NOT_REAL",
                           reason="testing")


def test_unacknowledged_critical_returns_only_critical_unacked(tmp_path):
    a_crit = emit_alert(tmp_path, "CRITICAL", "REGIME_CLASSIFIER_ERROR",
                         "regime_classifier", "x",
                         logical_date="2026-05-06")
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_PARTIAL", "data_ingest",
               "y", logical_date="2026-05-06")
    a_crit2 = emit_alert(tmp_path, "CRITICAL", "SCAN_ERROR", "daily_scan",
                          "z", logical_date="2026-05-06")
    # Ack one critical
    acknowledge_alert(tmp_path, a_crit.alert_id, reason="investigated")

    out = unacknowledged_critical(tmp_path,
                                   on_or_before_date=date(2026, 5, 6))
    assert [a.alert_id for a in out] == [a_crit2.alert_id]


def test_unacknowledged_critical_filters_by_date(tmp_path):
    """Alerts with logical_date > cutoff are excluded."""
    a_today = emit_alert(tmp_path, "CRITICAL", "SCAN_ERROR", "daily_scan",
                          "today", logical_date="2026-05-06")
    a_future = emit_alert(tmp_path, "CRITICAL", "SCAN_ERROR", "daily_scan",
                           "future", logical_date="2026-05-08")
    out = unacknowledged_critical(tmp_path,
                                   on_or_before_date=date(2026, 5, 6))
    assert [a.alert_id for a in out] == [a_today.alert_id]
    out2 = unacknowledged_critical(tmp_path,
                                    on_or_before_date=date(2026, 5, 8))
    assert {a.alert_id for a in out2} == {a_today.alert_id, a_future.alert_id}


def test_list_alerts_returns_empty_for_missing_file(tmp_path):
    assert list_alerts(tmp_path) == []


def test_list_acknowledgments_returns_empty_for_missing_file(tmp_path):
    assert list_acknowledgments(tmp_path) == []
