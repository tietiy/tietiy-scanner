"""Smoke tests for shadow_ops/regime_classifier.py.

Cross-validation tests verify that shadow's classifier produces output
bit-for-bit equivalent to the audit pipeline's regime + sub_regime values
in lab/output/enriched_signals.parquet for the same scan_date.

Network-requiring tests are marked @pytest.mark.network (today-classification
needs current data). The cross-validation tests run against historical data
in lab/cache/ + lab/output/, so they're offline-safe IF those parquets are
populated locally.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from shadow_ops.regime_classifier import (
    DEFAULT_CACHE_DIR,
    RegimeClassification,
    _classify_regime_slope_ema50,
    _compute_features_sha,
    classify_regime_for_date,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENRICHED_SIGNALS_PATH = _REPO_ROOT / "lab" / "output" / "enriched_signals.parquet"


# ============================================================
# Helpers — pick representative cross-validation dates
# ============================================================

def _pick_cross_validation_dates() -> dict:
    """Pull one historical date for each of: Bear+hot, Bull, Choppy.

    Reads lab/output/enriched_signals.parquet. Picks the first row per
    (regime, sub_regime) combination so the test is deterministic.
    """
    if not ENRICHED_SIGNALS_PATH.exists():
        return {}
    df = pd.read_parquet(ENRICHED_SIGNALS_PATH)
    # add_derived_features happens at walkforward.load_data time but
    # enriched_signals.parquet stores raw + features; sub_regime is NOT
    # persisted. We need to add_derived_features here to get sub_regime.
    import sys
    sys.path.insert(0, str(_REPO_ROOT / "lab" / "factory" / "opus_iteration"))
    from _validate_paths import add_derived_features
    df = add_derived_features(df)

    picks: dict = {}
    # Bear+hot — pick the first matching row
    bear_hot = df[(df["regime"] == "Bear") & (df["sub_regime"] == "hot")]
    if len(bear_hot):
        first = bear_hot.iloc[0]
        picks["bear_hot"] = {
            "scan_date": first["scan_date"],
            "expected_regime": "Bear",
            "expected_sub_regime": "hot",
        }
    # Bull — pick the first Bull row
    bull = df[df["regime"] == "Bull"]
    if len(bull):
        first = bull.iloc[0]
        picks["bull"] = {
            "scan_date": first["scan_date"],
            "expected_regime": "Bull",
            "expected_sub_regime": first["sub_regime"],
        }
    # Choppy — pick the first Choppy row
    choppy = df[df["regime"] == "Choppy"]
    if len(choppy):
        first = choppy.iloc[0]
        picks["choppy"] = {
            "scan_date": first["scan_date"],
            "expected_regime": "Choppy",
            "expected_sub_regime": first["sub_regime"],
        }
    return picks


# ============================================================
# Cross-validation tests (CRITICAL — validate audit-equivalence)
# ============================================================

@pytest.mark.network
@pytest.mark.skipif(not ENRICHED_SIGNALS_PATH.exists(),
                    reason="enriched_signals.parquet not present locally")
def test_classify_for_known_historical_dates_cross_validation():
    """Cross-validate classifier against audit pipeline output for 3 historical dates.

    For each of (Bear+hot, Bull, Choppy):
      - Run shadow's classify_regime_for_date(date)
      - Compare to enriched_signals.parquet's regime + sub_regime for that date
      - Verify EXACT match.

    Mismatch == FAIL (cross-validation drift). Surfaces:
      - Which date mismatched.
      - Shadow's regime/sub_regime.
      - Audit's regime/sub_regime.
      - Shadow's inputs dict (so the cause is debuggable).
    """
    picks = _pick_cross_validation_dates()
    assert picks, "no cross-validation dates picked — enriched_signals.parquet may be empty"

    failures = []
    for label, pick in picks.items():
        scan_date_str = pick["scan_date"]
        expected_regime = pick["expected_regime"]
        expected_sub_regime = pick["expected_sub_regime"]
        scan_date_obj = date.fromisoformat(str(scan_date_str)[:10])

        result = classify_regime_for_date(scan_date_obj)

        actual_regime = result.regime
        actual_sub_regime = result.sub_regime

        # Normalize None vs NaN comparison
        def _norm(v):
            return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v

        if (actual_regime != expected_regime
                or _norm(actual_sub_regime) != _norm(expected_sub_regime)):
            failures.append({
                "label": label,
                "scan_date": scan_date_str,
                "expected": (expected_regime, expected_sub_regime),
                "actual": (actual_regime, actual_sub_regime),
                "inputs": result.inputs,
            })

    if failures:
        msg = "Cross-validation mismatches:\n" + json.dumps(failures, indent=2, default=str)
        pytest.fail(msg)


# ============================================================
# Live "today" classification
# ============================================================

@pytest.mark.network
def test_classify_for_today():
    """Classifier returns a valid result for today's date."""
    result = classify_regime_for_date(date.today())
    assert isinstance(result, RegimeClassification)
    assert result.regime in ("Bull", "Bear", "Choppy")
    assert result.scan_date == date.today().isoformat()
    assert result.classified_at_utc.endswith("+00:00") or "Z" in result.classified_at_utc \
        or "+" in result.classified_at_utc, f"unexpected timestamp format: {result.classified_at_utc}"
    assert result.nifty_close_latest_date  # non-empty


# ============================================================
# Inputs completeness
# ============================================================

@pytest.mark.network
def test_inputs_capture_completeness():
    """Verify all 7 features_sha-input fields are present and (mostly) non-null."""
    result = classify_regime_for_date(date.today())
    expected_keys = {
        "feat_nifty_vol_percentile_20d",
        "feat_nifty_60d_return_pct",
        "feat_nifty_200d_return_pct",
        "feat_market_breadth_pct",
        "last_slope",
        "last_above_ema50",
        "nifty_close_latest_date",
    }
    assert set(result.inputs.keys()) == expected_keys, \
        f"inputs key mismatch: {set(result.inputs.keys())} vs {expected_keys}"

    # last_slope, last_above_ema50, nifty_close_latest_date must always be populated
    assert result.inputs["last_slope"] is not None
    assert isinstance(result.inputs["last_above_ema50"], bool)
    assert result.inputs["nifty_close_latest_date"]

    # Market-level features should be populated for any date with sufficient history
    # (today's date has 15+ years of data, so all should be non-null)
    for k in ("feat_nifty_vol_percentile_20d", "feat_nifty_60d_return_pct",
              "feat_nifty_200d_return_pct", "feat_market_breadth_pct"):
        v = result.inputs[k]
        assert v is not None, f"input {k} is None for today (insufficient history?)"


# ============================================================
# SHA determinism
# ============================================================

@pytest.mark.network
def test_features_sha_is_deterministic():
    """Same scan_date + cache state → same features_sha."""
    r1 = classify_regime_for_date(date.today())
    r2 = classify_regime_for_date(date.today())
    assert r1.features_sha == r2.features_sha, \
        f"sha mismatch: {r1.features_sha} != {r2.features_sha}\n" \
        f"r1.inputs={r1.inputs}\nr2.inputs={r2.inputs}"


def test_features_sha_offline_deterministic():
    """SHA helper is deterministic on a synthetic inputs dict (offline)."""
    inputs = {
        "feat_nifty_vol_percentile_20d": 0.78,
        "feat_nifty_60d_return_pct": -0.12,
        "feat_nifty_200d_return_pct": 0.04,
        "feat_market_breadth_pct": 0.32,
        "last_slope": -0.0061,
        "last_above_ema50": False,
        "nifty_close_latest_date": "2026-05-05",
    }
    h1 = _compute_features_sha(inputs)
    h2 = _compute_features_sha(inputs)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest length

    # Changing one field changes the hash
    inputs2 = dict(inputs)
    inputs2["last_slope"] = -0.0062
    h3 = _compute_features_sha(inputs2)
    assert h3 != h1


# ============================================================
# Missing-data error
# ============================================================

def test_missing_data_raises_clear_error(tmp_path):
    """Classifier raises FileNotFoundError if Nifty parquet missing in cache_dir."""
    # tmp_path has no _index_NSEI.parquet
    with pytest.raises(FileNotFoundError) as exc_info:
        classify_regime_for_date(date.today(), cache_dir=tmp_path)
    assert "nifty parquet missing" in str(exc_info.value).lower() \
        or "_index_NSEI.parquet" in str(exc_info.value)


def test_stale_nifty_data_raises_value_error(tmp_path):
    """Classifier raises ValueError if Nifty parquet's latest date < scan_date."""
    # Build a stale parquet ending 2026-04-15
    stale_dates = pd.date_range("2024-01-01", "2026-04-15", freq="B")
    stale_close = pd.DataFrame(
        {"Close": [22000.0 + i * 0.1 for i in range(len(stale_dates))]},
        index=stale_dates,
    )
    stale_close.index.name = "Date"
    parquet_path = tmp_path / "_index_NSEI.parquet"
    stale_close.to_parquet(parquet_path)

    # Request classification for a future date — should raise
    with pytest.raises(ValueError) as exc_info:
        classify_regime_for_date(date(2026, 5, 5), cache_dir=tmp_path)
    assert "stale" in str(exc_info.value).lower()


# ============================================================
# Mirror-function offline test (no FeatureExtractor required)
# ============================================================

def test_classify_regime_slope_ema50_synthetic_bull():
    """Synthetic uptrending Nifty data → 'Bull' classification."""
    dates = pd.date_range("2026-02-01", "2026-05-05", freq="B")
    # Strongly uptrending close — last_slope should be > 0.005, above_ema50 should be True
    closes = pd.Series(
        [22000.0 + i * 50.0 for i in range(len(dates))],
        index=dates,
    )
    result = _classify_regime_slope_ema50(closes, pd.Timestamp("2026-05-05"))
    assert result["regime"] == "Bull"
    assert result["last_slope"] > 0.005
    assert result["last_above_ema50"] is True


def test_classify_regime_slope_ema50_synthetic_bear():
    """Synthetic downtrending Nifty data → 'Bear' classification."""
    dates = pd.date_range("2026-02-01", "2026-05-05", freq="B")
    closes = pd.Series(
        [25000.0 - i * 50.0 for i in range(len(dates))],
        index=dates,
    )
    result = _classify_regime_slope_ema50(closes, pd.Timestamp("2026-05-05"))
    assert result["regime"] == "Bear"
    assert result["last_slope"] < -0.005
    assert result["last_above_ema50"] is False


def test_classify_regime_slope_ema50_insufficient_history():
    """< 50 trading days history → ValueError (mirror of scanner's intent)."""
    # Only 20 days of data
    dates = pd.date_range("2026-04-01", periods=20, freq="B")
    closes = pd.Series([22000.0] * 20, index=dates)
    with pytest.raises(ValueError) as exc_info:
        _classify_regime_slope_ema50(closes, pd.Timestamp("2026-05-05"))
    assert "insufficient" in str(exc_info.value).lower()
