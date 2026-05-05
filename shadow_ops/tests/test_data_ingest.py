"""Smoke tests for shadow_ops/data_ingest.py.

Network-requiring tests are marked with @pytest.mark.network and can be skipped
via `pytest -m "not network"` if running offline.

Note on idempotency tests: parquet writes embed pandas/pyarrow metadata
(creation timestamps, library versions). Idempotency means CONTENT identity via
DataFrame.equals(), NOT byte-identical files.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shadow_ops.data_ingest import (
    DEFAULT_CACHE_DIR,
    DEFAULT_UNIVERSE_CSV,
    NIFTY_SYMBOL,
    daily_data_ingest,
    fetch_symbol_ohlc,
    load_universe,
    parquet_path_for_symbol,
    safe_filename,
    update_index_parquet,
    update_symbol_parquet,
)


# ============================================================
# Offline tests
# ============================================================

def test_universe_loads_188_symbols():
    """Universe CSV resolves to 188 symbols, includes expected leaders."""
    symbols = load_universe()
    assert len(symbols) == 188, f"expected 188 symbols, got {len(symbols)}"
    assert symbols[0] == "HDFCBANK.NS", f"first symbol mismatch: {symbols[0]}"
    assert "RELIANCE.NS" in symbols
    assert "INFY.NS" in symbols
    # All symbols should end with .NS suffix (NSE convention)
    assert all(s.endswith(".NS") for s in symbols), \
        f"non-.NS symbols found: {[s for s in symbols if not s.endswith('.NS')]}"


def test_safe_filename_conventions():
    """safe_filename matches data_fetcher.py conventions."""
    assert safe_filename("^NSEI") == "_index_NSEI"
    assert safe_filename("^NSEBANK") == "_index_NSEBANK"
    assert safe_filename("RELIANCE.NS") == "RELIANCE_NS"
    assert safe_filename("HDFCBANK.NS") == "HDFCBANK_NS"


def test_parquet_path_for_symbol_resolves_correctly():
    """parquet_path_for_symbol joins cache_dir with safe_filename."""
    p = parquet_path_for_symbol("RELIANCE.NS", Path("/tmp/cache"))
    assert p == Path("/tmp/cache/RELIANCE_NS.parquet")
    p2 = parquet_path_for_symbol("^NSEI", Path("/tmp/cache"))
    assert p2 == Path("/tmp/cache/_index_NSEI.parquet")


def test_update_symbol_parquet_idempotent(tmp_path):
    """Idempotency: running update twice with the same fresh_data produces
    content-identical parquet on second call (rows_added == 0).

    Idempotency means CONTENT identity (DataFrame.equals), NOT byte identity —
    parquet metadata varies between writes.
    """
    parquet_path = tmp_path / "TEST_NS.parquet"

    # Synthesize 5 days of OHLC data (no network needed)
    dates = pd.date_range("2026-04-25", periods=5, freq="B")  # 5 business days
    fresh = pd.DataFrame({
        "Open":      [100.0, 101.0, 102.0, 103.0, 104.0],
        "High":      [101.5, 102.5, 103.5, 104.5, 105.5],
        "Low":       [99.5,  100.5, 101.5, 102.5, 103.5],
        "Close":     [101.0, 102.0, 103.0, 104.0, 105.0],
        "Adj Close": [101.0, 102.0, 103.0, 104.0, 105.0],
        "Volume":    [1000000, 1100000, 1200000, 1300000, 1400000],
    }, index=dates)
    fresh.index.name = "Date"

    # First call: parquet doesn't exist, all rows added
    r1 = update_symbol_parquet("TEST.NS", parquet_path, fresh)
    assert r1.status == "OK", f"first call status={r1.status}, error={r1.error}"
    assert r1.rows_added == 5
    assert r1.rows_updated == 0
    assert parquet_path.exists()

    df_after_first = pd.read_parquet(parquet_path)

    # Second call with same fresh_data: idempotent — no new rows, no update
    r2 = update_symbol_parquet("TEST.NS", parquet_path, fresh)
    assert r2.status == "OK", f"second call status={r2.status}, error={r2.error}"
    assert r2.rows_added == 0, f"expected 0 new rows on second call, got {r2.rows_added}"
    assert r2.rows_updated == 0, f"expected 0 updated rows, got {r2.rows_updated}"

    df_after_second = pd.read_parquet(parquet_path)

    # Content equality (NOT byte equality — parquet metadata varies)
    assert df_after_first.shape == df_after_second.shape
    assert df_after_first.equals(df_after_second), \
        "parquet content differs between idempotent calls"


def test_update_symbol_parquet_nan_close_replacement(tmp_path):
    """When existing parquet has NaN Close on a date and fresh data has non-NaN
    Close on the same date, rows_updated counts that row, and the merged parquet
    has the fresh value."""
    parquet_path = tmp_path / "TEST_NS.parquet"

    # Existing parquet: 3 days, last day has NaN Close (simulates partial yfinance return)
    existing_dates = pd.date_range("2026-04-25", periods=3, freq="B")
    existing = pd.DataFrame({
        "Open":      [100.0, 101.0, 102.0],
        "High":      [101.5, 102.5, 103.5],
        "Low":       [99.5,  100.5, 101.5],
        "Close":     [101.0, 102.0, np.nan],   # ← NaN on last day
        "Adj Close": [101.0, 102.0, np.nan],
        "Volume":    [1000000, 1100000, 1200000],
    }, index=existing_dates)
    existing.index.name = "Date"
    existing.to_parquet(parquet_path, compression="snappy")

    # Fresh: same 3 dates, last day now has valid Close
    fresh = pd.DataFrame({
        "Open":      [100.0, 101.0, 102.0],
        "High":      [101.5, 102.5, 103.5],
        "Low":       [99.5,  100.5, 101.5],
        "Close":     [101.0, 102.0, 103.0],   # ← non-NaN now
        "Adj Close": [101.0, 102.0, 103.0],
        "Volume":    [1000000, 1100000, 1200000],
    }, index=existing_dates)
    fresh.index.name = "Date"

    r = update_symbol_parquet("TEST.NS", parquet_path, fresh)
    assert r.status == "OK"
    assert r.rows_added == 0       # all dates already existed
    assert r.rows_updated == 1     # the NaN-Close row was filled in

    merged = pd.read_parquet(parquet_path)
    assert not pd.isna(merged.loc[existing_dates[2], "Close"])
    assert merged.loc[existing_dates[2], "Close"] == 103.0


def test_update_symbol_parquet_empty_fresh_existing_present(tmp_path):
    """Empty fresh_data with existing parquet → NO_NEW_DATA, parquet untouched."""
    parquet_path = tmp_path / "TEST_NS.parquet"
    dates = pd.date_range("2026-04-25", periods=3, freq="B")
    existing = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0],
        "High": [101.5, 102.5, 103.5],
        "Low":  [99.5,  100.5, 101.5],
        "Close": [101.0, 102.0, 103.0],
        "Adj Close": [101.0, 102.0, 103.0],
        "Volume": [1000000, 1100000, 1200000],
    }, index=dates)
    existing.index.name = "Date"
    existing.to_parquet(parquet_path, compression="snappy")

    r = update_symbol_parquet("TEST.NS", parquet_path, pd.DataFrame())
    assert r.status == "NO_NEW_DATA"
    assert r.rows_added == 0
    assert r.latest_date_after == dates[-1].date().isoformat()


def test_update_symbol_parquet_empty_fresh_no_existing(tmp_path):
    """Empty fresh_data with no existing parquet → FAILED."""
    parquet_path = tmp_path / "DOES_NOT_EXIST.parquet"
    r = update_symbol_parquet("TEST.NS", parquet_path, pd.DataFrame())
    assert r.status == "FAILED"
    assert "empty_fresh_data" in (r.error or "")


# ============================================================
# Network-requiring tests
# ============================================================

@pytest.mark.network
def test_fetch_symbol_returns_expected_schema():
    """Fetch RELIANCE.NS for the last 7 days; verify schema matches existing parquet."""
    today = date.today()
    df, attempts, err = fetch_symbol_ohlc("RELIANCE.NS", today - timedelta(days=14), today)
    assert err is None, f"fetch failed: {err}"
    assert not df.empty, "fetch returned empty DataFrame"
    # Required columns from existing parquet schema (§3.3 of architecture doc)
    expected_cols = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    assert expected_cols.issubset(set(df.columns)), \
        f"missing columns: {expected_cols - set(df.columns)}"
    # Index is DatetimeIndex, tz-naive
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is None
    # At least 1 row (last 14 calendar days has at least some trading days)
    assert len(df) >= 1


@pytest.mark.network
def test_failure_isolation_with_invalid_symbol(tmp_path):
    """daily_data_ingest with an invalid symbol doesn't crash; symbol is in failed list."""
    # Build a tiny universe CSV with a deliberate bogus symbol
    bogus_csv = tmp_path / "tiny_universe.csv"
    bogus_csv.write_text("symbol,sector,grade\nBOGUS_DOESNOT_EXIST.NS,Bank,B\n")

    result = daily_data_ingest(
        universe_path=bogus_csv,
        cache_dir=tmp_path,
        skip_index=True,            # don't fetch ^NSEI for this isolation test
        verbose=False,
    )
    # Should not have crashed
    assert result.universe_size == 1
    # Bogus symbol should be in failed list (yfinance returns empty for unknown ticker)
    assert len(result.symbols_failed) == 1
    assert result.symbols_failed[0][0] == "BOGUS_DOESNOT_EXIST.NS"


@pytest.mark.network
def test_lookback_recovery(tmp_path):
    """Stale parquet (last date well before today) gets brought up to date by ingest.

    Content-equality check: idempotent re-run of the ingest produces the same merged
    parquet content (DataFrame.equals).
    """
    parquet_path = tmp_path / "RELIANCE_NS.parquet"

    # Seed a stale parquet with one row from a known historical date
    seed_date = pd.Timestamp("2026-04-15")
    stale = pd.DataFrame({
        "Open": [1300.0], "High": [1310.0], "Low": [1290.0],
        "Close": [1305.0], "Adj Close": [1305.0], "Volume": [1000000],
    }, index=[seed_date])
    stale.index.name = "Date"
    stale.to_parquet(parquet_path, compression="snappy")

    # Run the per-symbol fetch + update directly (faster than full daily_data_ingest)
    today = date.today()
    fresh, _, err = fetch_symbol_ohlc("RELIANCE.NS", today - timedelta(days=14), today)
    assert err is None
    r1 = update_symbol_parquet("RELIANCE.NS", parquet_path, fresh)
    assert r1.status == "OK"
    assert r1.rows_added > 0, "expected new rows after recovering stale parquet"

    df_after_first = pd.read_parquet(parquet_path)
    # Latest date should be much more recent than seed
    assert df_after_first.index.max() > seed_date

    # Idempotent re-run with same fresh data: content identical
    r2 = update_symbol_parquet("RELIANCE.NS", parquet_path, fresh)
    assert r2.status == "OK"
    assert r2.rows_added == 0

    df_after_second = pd.read_parquet(parquet_path)
    assert df_after_first.shape == df_after_second.shape
    assert df_after_first.equals(df_after_second)


@pytest.mark.network
def test_index_parquet_update(tmp_path):
    """update_index_parquet successfully refreshes _index_NSEI.parquet."""
    # No seed parquet — let update create from scratch
    r = update_index_parquet(cache_dir=tmp_path, lookback_days=14)
    assert r.status == "OK", f"index update failed: {r.error}"
    assert r.rows_added > 0

    parquet_path = tmp_path / "_index_NSEI.parquet"
    assert parquet_path.exists()
    df = pd.read_parquet(parquet_path)
    assert "Close" in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)
