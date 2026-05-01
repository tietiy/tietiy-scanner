"""
Unit tests for live_feature_joiner.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_live_feature_joiner.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_feature_joiner import (  # noqa: E402
    LiveFeatureJoiner,
    RESOLVED_OUTCOMES,
    WIN_OUTCOMES,
    LOSS_OUTCOMES,
    FLAT_OUTCOMES,
    _wlf_label,
)
from feature_extractor import _FEAT_PREFIX  # noqa: E402


# ────────────────────────────────────────────────────────────────────
# Module-scope fixture: build joined DataFrame once (expensive due to
# orphan re-extraction); reuse across tests.
# ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def joined():
    j = LiveFeatureJoiner()
    return j.build(), j.report


# ════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════

def test_wlf_label_mapping():
    assert _wlf_label("DAY6_WIN") == "W"
    assert _wlf_label("TARGET_HIT") == "W"
    assert _wlf_label("DAY6_LOSS") == "L"
    assert _wlf_label("STOP_HIT") == "L"
    assert _wlf_label("DAY6_FLAT") == "F"
    assert _wlf_label("OPEN") == "?"


def test_all_resolved_signals_joined(joined):
    df, report = joined
    # All resolved signals should be present in joined output (after dedup)
    assert len(df) == report.total_after_dedup
    assert report.total_resolved >= 200, (
        f"expected ≥200 resolved live signals; got {report.total_resolved}")


def test_label_distribution_matches_history(joined):
    df, report = joined
    # W must equal DAY6_WIN + TARGET_HIT
    n_win = int((df["wlf"] == "W").sum())
    n_loss = int((df["wlf"] == "L").sum())
    n_flat = int((df["wlf"] == "F").sum())
    # Cross-check against raw outcome
    raw_win = int(df["outcome"].isin(WIN_OUTCOMES).sum())
    raw_loss = int(df["outcome"].isin(LOSS_OUTCOMES).sum())
    raw_flat = int(df["outcome"].isin(FLAT_OUTCOMES).sum())
    assert n_win == raw_win
    assert n_loss == raw_loss
    assert n_flat == raw_flat
    assert n_win + n_loss + n_flat == len(df)


def test_no_all_nan_feature_rows_after_orphan_extraction(joined):
    df, report = joined
    feat_cols = [c for c in df.columns
                  if c.startswith(_FEAT_PREFIX)
                  and c != _FEAT_PREFIX + "_extractor_error"]
    assert len(feat_cols) == 114, f"expected 114 feat_* cols, got {len(feat_cols)}"
    # Count rows where ALL feat_* are NaN — should equal unrecoverable orphans
    all_nan = df[feat_cols].isna().all(axis=1)
    unrecov = report.total_orphans_unrecoverable
    assert int(all_nan.sum()) == unrecov, (
        f"all-NaN rows ({int(all_nan.sum())}) should match unrecoverable "
        f"orphans ({unrecov})")


def test_schema_integrity(joined):
    df, report = joined
    # Required columns present
    for col in ("date", "symbol", "signal", "outcome", "regime", "wlf"):
        assert col in df.columns, f"missing required col: {col}"
    # 114 feat_* columns
    feat_cols = [c for c in df.columns
                  if c.startswith(_FEAT_PREFIX)
                  and c != _FEAT_PREFIX + "_extractor_error"]
    assert len(feat_cols) == 114
    # Cohort sizes match expectations from pre-flight
    assert report.cohort_n["Bull"] == 0, (
        f"Bull live cohort should be 0 (April 2026 data); "
        f"got {report.cohort_n['Bull']}")
    # Post-dedup sizes (after dropping ~32 -REJ duplicates concentrated in Bear)
    assert report.cohort_n["Bear"] >= 80, (
        f"Bear live cohort should retain ≥80 signals after dedup; "
        f"got {report.cohort_n['Bear']}")
    assert report.cohort_n["Choppy"] >= 80


def test_dedup_drops_rej_duplicates(joined):
    df, report = joined
    # No row should have -REJ in id
    assert not df["id"].str.endswith("-REJ", na=False).any(), (
        "REJ duplicates not dropped; dedup logic broken")
    # Dedup count check
    assert report.total_dedup_dropped >= 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
