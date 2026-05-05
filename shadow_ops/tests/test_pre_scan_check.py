"""Smoke tests for shadow_ops/pre_scan_check.py.

Each test stages a controlled scenario (good or specifically-broken) and
verifies the corresponding check passes/fails as expected.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from shadow_ops.alerts import emit_alert
from shadow_ops.journal import JournalWriter
from shadow_ops.pre_scan_check import (
    CHECK_NAMES,
    PreScanCheckResult,
    run_pre_scan_checks,
)
from shadow_ops.schemas import LifecycleEvent, TradeCard


# ============================================================
# Helpers
# ============================================================

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_real_universe_csv(tmp_path: Path, n: int = 188) -> Path:
    """Build a tmp universe.csv with the expected size + columns."""
    p = tmp_path / "fno_universe.csv"
    rows = ["symbol,sector,grade"]
    for i in range(n):
        rows.append(f"SYM{i:03d}.NS,Pharma,B")
    p.write_text("\n".join(rows) + "\n")
    return p


def _build_real_rules_json(tmp_path: Path, *, include_all: bool = True,
                            inactive: list = None) -> Path:
    """Build a minimal rules JSON with the 3 active rule IDs."""
    p = tmp_path / "rules.json"
    inactive = set(inactive or [])
    rules = []
    if include_all:
        for rid in ("rule_019_bear_uptri_hot_refinement",
                    "rule_031_bear_uptri_it_hot",
                    "kill_001"):
            rules.append({"id": rid, "active": rid not in inactive})
    p.write_text(json.dumps({"rules": rules}))
    return p


def _build_fresh_nifty_parquet(cache_dir: Path, latest_date: str) -> Path:
    """Build a tmp nifty parquet with `latest_date` as its last index."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp(latest_date)
    idx = pd.date_range(end=end, periods=200, freq="B")
    df = pd.DataFrame({"Close": [22000.0 + i for i in range(len(idx))]},
                       index=idx)
    df.index.name = "Date"
    p = cache_dir / "_index_NSEI.parquet"
    df.to_parquet(p)
    return p


def _good_args(tmp_path: Path, scan_date: date = date(2018, 10, 26)) -> dict:
    """Stage all dependencies for a passing run on a fixed historical date.
    Skip git_clean — repo state isn't deterministic in CI."""
    cache_dir = tmp_path / "cache"
    universe = _build_real_universe_csv(tmp_path)
    rules = _build_real_rules_json(tmp_path)
    _build_fresh_nifty_parquet(cache_dir, scan_date.isoformat())
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    return dict(
        run_dir=run_dir,
        scan_date=scan_date,
        cache_dir=cache_dir,
        universe_csv=universe,
        rules_path=rules,
        skip=["git_clean"],
    )


# ============================================================
# Pass/fail per check
# ============================================================

def test_all_checks_pass_with_good_setup(tmp_path):
    result = run_pre_scan_checks(**_good_args(tmp_path))
    failed = [c.name for c in result.failed]
    assert result.all_passed, f"unexpected failures: {failed}"


def test_universe_csv_missing_fails(tmp_path):
    args = _good_args(tmp_path)
    args["universe_csv"].unlink()
    result = run_pre_scan_checks(**args)
    assert not result.all_passed
    by_name = {c.name: c for c in result.checks}
    assert not by_name["universe_csv"].ok
    assert "missing" in by_name["universe_csv"].message


def test_universe_csv_wrong_size_fails(tmp_path):
    args = _good_args(tmp_path)
    args["universe_csv"] = _build_real_universe_csv(tmp_path, n=50)
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["universe_csv"].ok
    assert "size 50" in by_name["universe_csv"].message


def test_rules_json_missing_required_rule_fails(tmp_path):
    args = _good_args(tmp_path)
    # Rebuild without all required rules
    p = tmp_path / "partial_rules.json"
    p.write_text(json.dumps({"rules": [
        {"id": "rule_019_bear_uptri_hot_refinement", "active": True},
        # missing rule_031, kill_001
    ]}))
    args["rules_path"] = p
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["rules_json"].ok
    assert "missing required rule" in by_name["rules_json"].message


def test_rules_json_required_rule_inactive_fails(tmp_path):
    args = _good_args(tmp_path)
    args["rules_path"] = _build_real_rules_json(
        tmp_path, inactive=["kill_001"])
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["rules_json"].ok
    assert "inactive" in by_name["rules_json"].message


def test_cache_freshness_stale_fails(tmp_path):
    args = _good_args(tmp_path, scan_date=date(2026, 5, 6))
    # Rebuild with stale latest date (1 month before scan_date)
    _build_fresh_nifty_parquet(args["cache_dir"], "2026-04-01")
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["cache_freshness"].ok
    assert "stale" in by_name["cache_freshness"].message


def test_run_dir_consistency_rescan_fails(tmp_path):
    args = _good_args(tmp_path, scan_date=date(2018, 10, 26))
    # Pre-populate run_dir with a scan_event for the SAME date
    from shadow_ops.schemas import ScanEvent
    JournalWriter(args["run_dir"]).write_event(ScanEvent(
        event_id="scan_2018-10-26_001",
        event_type="scan_event",
        timestamp_utc="2018-10-26T16:00:00+00:00",
        scan_date="2018-10-26",
        regime="Bear", sub_regime="hot",
        sub_regime_inputs={}, n_signals_universe=0, n_signals_post_filter=0,
        scan_status="OK", scan_duration_ms=0,
        git_commit_sha="abc123",
        data_versions={},
    ))
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["run_dir_consistency"].ok
    assert "re-scan" in by_name["run_dir_consistency"].message


def test_unacked_critical_blocks(tmp_path):
    args = _good_args(tmp_path, scan_date=date(2018, 10, 26))
    # Stage an unacked CRITICAL alert before today
    emit_alert(args["run_dir"], "CRITICAL", "SCAN_ERROR", "daily_scan",
               "yesterday's scan errored", logical_date="2018-10-25")
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["unacked_critical"].ok
    assert "unacknowledged CRITICAL" in by_name["unacked_critical"].message


def test_unacked_critical_passes_after_ack(tmp_path):
    from shadow_ops.alerts import acknowledge_alert
    args = _good_args(tmp_path, scan_date=date(2018, 10, 26))
    a = emit_alert(args["run_dir"], "CRITICAL", "SCAN_ERROR", "daily_scan",
                    "yesterday's scan errored",
                    logical_date="2018-10-25")
    acknowledge_alert(args["run_dir"], a.alert_id,
                       reason="investigated, retried scan succeeded")
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert by_name["unacked_critical"].ok


def test_lifecycle_integrity_orphan_event_fails(tmp_path):
    args = _good_args(tmp_path, scan_date=date(2018, 10, 27))
    # Seed an orphan lifecycle event (no matching trade_card)
    JournalWriter(args["run_dir"]).write_event(LifecycleEvent(
        event_id="lc_2018-10-26_orphan_card_001",
        event_type="lifecycle_event",
        timestamp_utc="2018-10-26T03:50:00+00:00",
        card_id="orphan_card",
        from_state="PROPOSED", to_state="ACTIVE",
        reason="entry_t1_open",
        trigger_data={"actual_entry_price": 100.0,
                      "actual_entry_date": "2018-10-26"},
    ))
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert not by_name["lifecycle_integrity"].ok
    assert "orphan" in by_name["lifecycle_integrity"].message


def test_skip_check_excludes_named(tmp_path):
    """Skipping a check name removes it from the results."""
    args = _good_args(tmp_path)
    args["skip"] = ["git_clean", "cache_freshness"]
    result = run_pre_scan_checks(**args)
    names = [c.name for c in result.checks]
    assert "cache_freshness" not in names
    assert "git_clean" not in names
    assert sorted(result.skipped) == sorted(["cache_freshness", "git_clean"])


def test_new_run_dir_passes_consistency_and_lifecycle_checks(tmp_path):
    """A run_dir that doesn't exist yet should not fail run_dir_consistency
    or lifecycle_integrity (it's a fresh campaign)."""
    args = _good_args(tmp_path)
    args["run_dir"].rmdir()  # remove the empty dir we created
    assert not args["run_dir"].exists()
    result = run_pre_scan_checks(**args)
    by_name = {c.name: c for c in result.checks}
    assert by_name["run_dir_consistency"].ok
    assert by_name["lifecycle_integrity"].ok
    assert by_name["unacked_critical"].ok
