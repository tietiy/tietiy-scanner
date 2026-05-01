"""
Unit tests for combination_inputs_validator and cohort_horizon_config.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_combination_inputs_validator.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cohort_horizon_config import (  # noqa: E402
    COHORT_HORIZONS, COHORT_SKIP, list_active_cohort_cells, cohort_key,
)
from combination_inputs_validator import (  # noqa: E402
    ValidationError, validate_all, validate_enriched, validate_importance,
    validate_baselines,
)


# ── cohort_horizon_config ─────────────────────────────────────────────

def test_cohort_horizons_keys():
    """Each (signal_type, regime) combo has at least one horizon."""
    assert ("UP_TRI", "Bear") in COHORT_HORIZONS
    assert ("DOWN_TRI", "Bull") in COHORT_HORIZONS
    assert ("BULL_PROXY", "Choppy") in COHORT_HORIZONS
    for k, v in COHORT_HORIZONS.items():
        assert isinstance(k, tuple) and len(k) == 2
        assert isinstance(v, list) and len(v) >= 1
        for h in v:
            assert h.startswith("D")


def test_active_cells_excludes_skip():
    cells = list_active_cohort_cells()
    skip_set = set(COHORT_SKIP)
    for c in cells:
        assert c not in skip_set
    # No DOWN_TRI×Bear×D15/D20 should be present
    assert ("DOWN_TRI", "Bear", "D15") not in cells
    assert ("DOWN_TRI", "Bear", "D20") not in cells


def test_cohort_key_format():
    assert cohort_key("UP_TRI", "Bear", "D10") == "UP_TRI|Bear|D10"


def test_active_cells_count_reasonable():
    """Active cells = sum(horizons per cohort) − cells filtered by COHORT_SKIP.
    COHORT_SKIP entries that aren't in COHORT_HORIZONS don't subtract anything
    (they're defensive against future horizon additions)."""
    horizon_total = sum(len(v) for v in COHORT_HORIZONS.values())
    cohort_horizon_set = {(s, r, h) for (s, r), hzs in COHORT_HORIZONS.items()
                            for h in hzs}
    skips_in_horizons = [c for c in COHORT_SKIP if c in cohort_horizon_set]
    expected = horizon_total - len(skips_in_horizons)
    assert len(list_active_cohort_cells()) == expected
    # Sanity: 20 active cells in current config
    assert len(list_active_cohort_cells()) == 20


# ── combination_inputs_validator ──────────────────────────────────────

def test_validate_enriched_real():
    summary = validate_enriched()
    assert summary["n_rows"] == 105987
    assert summary["n_features"] == 114
    assert summary["outcome_coverage"] >= 0.95
    assert "Bear" in summary["regimes"]
    assert "UP_TRI" in summary["signal_types"]


def test_validate_importance_real():
    summary = validate_importance()
    assert "lifetime-Bear" in summary["cohorts_present"]
    assert "universal-live" in summary["cohorts_present"]
    for c, s in summary["summary"].items():
        assert s["n_features_ranked"] == 114
        assert s["n_top_20"] == 20


def test_validate_baselines_real():
    summary = validate_baselines()
    assert "UP_TRI" in summary["signal_types"]
    assert summary["n_cells"] == 81
    assert summary["n_cells_with_wr"] == 81  # Phase 3 had no skipped cells


def test_validate_all_runs_clean():
    summary = validate_all(verbose=False)
    assert "enriched" in summary
    assert "importance" in summary
    assert "baselines" in summary


def test_validate_enriched_missing_path(tmp_path):
    bogus = tmp_path / "does_not_exist.parquet"
    with pytest.raises(ValidationError, match="not found"):
        validate_enriched(path=bogus)


def test_validate_baselines_malformed(tmp_path):
    bogus = tmp_path / "bad.json"
    bogus.write_text(json.dumps({"not_cohorts": {}}))
    with pytest.raises(ValidationError, match="missing 'cohorts'"):
        validate_baselines(path=bogus)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
