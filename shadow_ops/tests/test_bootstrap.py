"""Smoke tests for shadow_ops/bootstrap.py.

Most tests use --allow-dirty-git=True because the repo state during pytest
isn't deterministic. One test exercises the git-clean check directly.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from shadow_ops.alerts import list_alerts, ALERTS_FILENAME
from shadow_ops.bootstrap import (
    BootstrapError,
    RUN_CONFIG_FILENAME,
    RUN_CONFIG_SCHEMA_VERSION,
    bootstrap_campaign,
)
from shadow_ops.daily_scan import ACTIVE_RULE_IDS
from shadow_ops.journal import JournalWriter
from shadow_ops.schemas import ScanEvent


# ============================================================
# Helpers
# ============================================================

def _real_rules_json(tmp_path: Path,
                     include_all: bool = True,
                     inactive: list = None) -> Path:
    """Build a minimal rules JSON with the 3 active rule IDs."""
    p = tmp_path / "rules.json"
    inactive = set(inactive or [])
    rules = []
    if include_all:
        for rid in ACTIVE_RULE_IDS:
            rules.append({"id": rid,
                          "active": rid not in inactive,
                          "expected_wr": 0.71,
                          "evidence": {"n": 240, "wr": 0.71, "tier": "test"}})
    p.write_text(json.dumps({"rules": rules}))
    return p


# ============================================================
# Tests
# ============================================================

def test_bootstrap_success_creates_run_config(tmp_path):
    rules = _real_rules_json(tmp_path)
    run_dir = tmp_path / "campaign_X"
    res = bootstrap_campaign(
        run_dir=run_dir,
        campaign_id="campaign_X",
        campaign_start_date=date(2026, 5, 6),
        operator="test_op",
        notes="initial trial",
        rules_path=rules,
        allow_dirty_git=True,
    )
    assert run_dir.exists()
    cfg_path = run_dir / RUN_CONFIG_FILENAME
    assert cfg_path.exists()
    cfg = json.loads(cfg_path.read_text())
    assert cfg["schema_version"] == RUN_CONFIG_SCHEMA_VERSION
    assert cfg["campaign_id"] == "campaign_X"
    assert cfg["campaign_start_date"] == "2026-05-06"
    assert cfg["operator"] == "test_op"
    assert cfg["notes"] == "initial trial"
    assert set(cfg["rules_enabled"]) == set(ACTIVE_RULE_IDS)
    assert cfg["entry_logic"] == "audit_faithful_t1_open_unconditional"
    assert cfg["holding_days"] == 6
    assert cfg["target_r_multiple"] == 2.0
    assert cfg["flat_threshold_pct"] == 0.5
    assert cfg["slippage_bps_assumption"] == 0
    # SHAs are populated and the right shape
    assert len(cfg["rules_sha256_at_bootstrap"]) == 64
    assert len(cfg["git_commit_sha"]) >= 40

    # Returned dataclass aligns
    assert res.campaign_id == "campaign_X"
    assert Path(res.run_config_path) == cfg_path
    assert res.rules_sha256_at_bootstrap == cfg["rules_sha256_at_bootstrap"]


def test_bootstrap_writes_sha_matching_rules_file(tmp_path):
    """rules_sha256_at_bootstrap == hashlib.sha256(file)."""
    rules = _real_rules_json(tmp_path)
    res = bootstrap_campaign(
        run_dir=tmp_path / "c",
        campaign_id="c",
        campaign_start_date=date(2026, 5, 6),
        rules_path=rules,
        allow_dirty_git=True,
    )
    expected = hashlib.sha256(rules.read_bytes()).hexdigest()
    assert res.rules_sha256_at_bootstrap == expected


def test_bootstrap_emits_INFO_alert(tmp_path):
    rules = _real_rules_json(tmp_path)
    run_dir = tmp_path / "c"
    bootstrap_campaign(
        run_dir=run_dir, campaign_id="c",
        campaign_start_date=date(2026, 5, 6),
        operator="op", rules_path=rules, allow_dirty_git=True,
    )
    alerts = list_alerts(run_dir)
    assert len(alerts) == 1
    assert alerts[0].severity == "INFO"
    assert alerts[0].alert_type == "BOOTSTRAP_COMPLETE"
    assert alerts[0].context["campaign_id"] == "c"
    assert alerts[0].context["operator"] == "op"


def test_bootstrap_refuses_when_run_config_already_exists(tmp_path):
    rules = _real_rules_json(tmp_path)
    run_dir = tmp_path / "c"
    bootstrap_campaign(
        run_dir=run_dir, campaign_id="c",
        campaign_start_date=date(2026, 5, 6),
        rules_path=rules, allow_dirty_git=True,
    )
    with pytest.raises(BootstrapError, match="already exists"):
        bootstrap_campaign(
            run_dir=run_dir, campaign_id="c2",
            campaign_start_date=date(2026, 5, 7),
            rules_path=rules, allow_dirty_git=True,
        )


def test_bootstrap_refuses_when_run_dir_has_jsonl_events(tmp_path):
    """run_dir has events from a prior campaign — refuse to bootstrap."""
    rules = _real_rules_json(tmp_path)
    run_dir = tmp_path / "c"
    # Pre-seed a scan_event without a run_config (simulating a campaign run on
    # an older codebase that didn't have bootstrap)
    JournalWriter(run_dir).write_event(ScanEvent(
        event_id="scan_2026-05-05_001",
        event_type="scan_event",
        timestamp_utc="2026-05-05T16:00:00+00:00",
        scan_date="2026-05-05",
        regime="Bear", sub_regime="hot",
        sub_regime_inputs={}, n_signals_universe=0, n_signals_post_filter=0,
        scan_status="OK", scan_duration_ms=0,
        git_commit_sha="abc123",
        data_versions={},
    ))
    with pytest.raises(BootstrapError, match="JSONL events"):
        bootstrap_campaign(
            run_dir=run_dir, campaign_id="c",
            campaign_start_date=date(2026, 5, 6),
            rules_path=rules, allow_dirty_git=True,
        )


def test_bootstrap_refuses_on_missing_rule(tmp_path):
    """Rules JSON missing a required rule_id → refuse."""
    p = tmp_path / "partial_rules.json"
    p.write_text(json.dumps({"rules": [
        {"id": "rule_019_bear_uptri_hot_refinement", "active": True},
        # missing rule_031 and kill_001
    ]}))
    with pytest.raises(BootstrapError, match="missing required rule"):
        bootstrap_campaign(
            run_dir=tmp_path / "c", campaign_id="c",
            campaign_start_date=date(2026, 5, 6),
            rules_path=p, allow_dirty_git=True,
        )


def test_bootstrap_refuses_on_inactive_rule(tmp_path):
    rules = _real_rules_json(tmp_path, inactive=["kill_001"])
    with pytest.raises(BootstrapError, match="inactive"):
        bootstrap_campaign(
            run_dir=tmp_path / "c", campaign_id="c",
            campaign_start_date=date(2026, 5, 6),
            rules_path=rules, allow_dirty_git=True,
        )


def test_bootstrap_refuses_on_missing_rules_file(tmp_path):
    with pytest.raises(BootstrapError, match="rules JSON missing"):
        bootstrap_campaign(
            run_dir=tmp_path / "c", campaign_id="c",
            campaign_start_date=date(2026, 5, 6),
            rules_path=tmp_path / "does_not_exist.json",
            allow_dirty_git=True,
        )


def test_bootstrap_creates_run_dir_if_missing(tmp_path):
    rules = _real_rules_json(tmp_path)
    run_dir = tmp_path / "deep" / "nested" / "campaign"
    assert not run_dir.exists()
    bootstrap_campaign(
        run_dir=run_dir, campaign_id="c",
        campaign_start_date=date(2026, 5, 6),
        rules_path=rules, allow_dirty_git=True,
    )
    assert run_dir.exists()
    assert (run_dir / RUN_CONFIG_FILENAME).exists()


def test_bootstrap_handles_optional_fields(tmp_path):
    """operator and notes are optional; absent values are None in run_config."""
    rules = _real_rules_json(tmp_path)
    res = bootstrap_campaign(
        run_dir=tmp_path / "c", campaign_id="c",
        campaign_start_date=date(2026, 5, 6),
        rules_path=rules, allow_dirty_git=True,
    )
    cfg = json.loads(Path(res.run_config_path).read_text())
    assert cfg["operator"] is None
    assert cfg["notes"] is None
