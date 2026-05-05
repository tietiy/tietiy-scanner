"""shadow_ops/data_ingest.py — Step 1 of shadow_ops v1 daily scan.

Refreshes lab/cache/<SYMBOL>_NS.parquet daily via yfinance for the 188-symbol
universe + lab/cache/_index_NSEI.parquet (Nifty index). First step of every
daily scan workflow per architecture doc §6.5.

Idempotent: running on the same date twice produces identical parquet contents
(content equality, NOT byte equality — pandas/pyarrow embed write timestamps).
Failure-isolated: per-symbol failures don't kill the run.

Design note: mirrors lab/infrastructure/data_fetcher.py's yfinance call shape
and retry pattern, but implements its own incremental merge logic. No import
dependency on data_fetcher.py.

Sector indices (^CNXIT, ^CNXPHARMA, ^CNXFMCG, etc.) are NOT refreshed by this
module. If shadow_ops/regime_classifier.py (Step 2) finds it needs them fresh
for daily regime computation, that's a Step 2 concern to address. In v1, we
assume FeatureExtractor handles sector indices from existing lab/cache/ contents.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

# ============================================================
# Paths and constants
# ============================================================

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent

DEFAULT_UNIVERSE_CSV = _REPO_ROOT / "data" / "fno_universe.csv"
DEFAULT_CACHE_DIR = _REPO_ROOT / "lab" / "cache"

NIFTY_SYMBOL = "^NSEI"
DEFAULT_LOOKBACK_DAYS = 7
RETRY_DELAYS_SEC = [5, 15, 30]   # 3 retries with exponential backoff


# ============================================================
# Data classes
# ============================================================

@dataclass
class SymbolUpdateResult:
    """Result of a single-symbol parquet update."""
    symbol: str
    status: str                          # "OK" | "FAILED" | "NO_NEW_DATA"
    rows_added: int = 0
    rows_updated: int = 0                # rows where existing NaN Close was replaced with fresh non-NaN
    latest_date_before: Optional[str] = None
    latest_date_after: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0


@dataclass
class IngestRunResult:
    """Result of a full daily_data_ingest run."""
    run_timestamp_utc: str
    end_date: str
    universe_size: int
    symbols_succeeded: List[str] = field(default_factory=list)
    symbols_failed: List[Tuple[str, str]] = field(default_factory=list)  # (symbol, error)
    symbols_no_new_data: List[str] = field(default_factory=list)
    index_status: dict = field(default_factory=dict)
    latest_dates: Dict[str, str] = field(default_factory=dict)
    overall_status: str = "PENDING"
    elapsed_seconds: float = 0.0


# ============================================================
# Helpers
# ============================================================

def safe_filename(symbol: str) -> str:
    """`^NSEI` → `_index_NSEI`; `RELIANCE.NS` → `RELIANCE_NS`. Mirrors data_fetcher.py."""
    if symbol.startswith("^"):
        return f"_index_{symbol[1:]}"
    return symbol.replace(".", "_")


def parquet_path_for_symbol(symbol: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Resolve symbol → parquet path: <cache_dir>/<safe_filename>.parquet."""
    return Path(cache_dir) / f"{safe_filename(symbol)}.parquet"


def load_universe(universe_path: Path = DEFAULT_UNIVERSE_CSV) -> List[str]:
    """Load FNO universe symbols from CSV. Returns list of '<TICKER>.NS' strings."""
    universe_path = Path(universe_path)
    if not universe_path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {universe_path}")
    symbols: List[str] = []
    with open(universe_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = (row.get("symbol") or "").strip()
            if sym:
                symbols.append(sym)
    return symbols


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Fetch core (yfinance with retry/backoff)
# ============================================================

def fetch_symbol_ohlc(symbol: str,
                      start_date: date,
                      end_date: date,
                      retry_delays: Optional[List[int]] = None) -> Tuple[pd.DataFrame, int, Optional[str]]:
    """Download yfinance OHLC for symbol over [start_date, end_date].

    yfinance's `end` parameter is EXCLUSIVE — caller must add +1 day if they want
    the end_date itself included. To minimize caller error, this function adds +1
    internally so end_date IS inclusive from the caller's perspective.

    Returns (df, attempts, error_message). On persistent failure: empty df.
    """
    delays = retry_delays if retry_delays is not None else RETRY_DELAYS_SEC
    attempts = 0
    last_error: Optional[str] = None

    # yfinance end is exclusive — bump by 1 day so caller's end_date is included
    yf_end = (end_date + timedelta(days=1)).isoformat()
    yf_start = start_date.isoformat()

    for attempt_idx in range(len(delays) + 1):
        attempts = attempt_idx + 1
        try:
            df = yf.download(
                symbol,
                start=yf_start,
                end=yf_end,
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is None or df.empty:
                last_error = "empty_dataframe"
            else:
                # Flatten potential MultiIndex columns (yfinance returns MultiIndex
                # even for single-symbol in recent versions)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                # Coerce index to tz-naive datetime
                df.index = pd.to_datetime(df.index, errors="coerce")
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df.index.name = "Date"
                # Drop rows where ALL columns are NaN (matches data_fetcher.py)
                df = df.dropna(how="all")
                if len(df) == 0:
                    last_error = "all_rows_nan"
                else:
                    return df, attempts, None
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"

        # Sleep before retry (except on last iteration)
        if attempt_idx < len(delays):
            time.sleep(delays[attempt_idx])

    return pd.DataFrame(), attempts, last_error


# ============================================================
# Idempotent merge
# ============================================================

def _atomic_write_parquet(df: pd.DataFrame, parquet_path: Path) -> None:
    """Write df to parquet via temp file + os.replace for atomicity."""
    parquet_path = Path(parquet_path)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = parquet_path.with_suffix(parquet_path.suffix + ".tmp")
    df.to_parquet(tmp_path, compression="snappy")
    os.replace(tmp_path, parquet_path)


def update_symbol_parquet(symbol: str,
                          parquet_path: Path,
                          fresh_data: pd.DataFrame) -> SymbolUpdateResult:
    """Idempotent merge of fresh_data into existing parquet."""
    parquet_path = Path(parquet_path)

    if fresh_data is None or fresh_data.empty:
        # Nothing to merge. Report based on whether existing parquet exists.
        if parquet_path.exists():
            existing = pd.read_parquet(parquet_path)
            latest = existing.index.max().date().isoformat() if len(existing) else None
            return SymbolUpdateResult(
                symbol=symbol,
                status="NO_NEW_DATA",
                rows_added=0,
                rows_updated=0,
                latest_date_before=latest,
                latest_date_after=latest,
            )
        return SymbolUpdateResult(
            symbol=symbol,
            status="FAILED",
            error="empty_fresh_data_and_no_existing_parquet",
        )

    # Case 1: parquet doesn't exist — write fresh_data directly.
    if not parquet_path.exists():
        _atomic_write_parquet(fresh_data.sort_index(), parquet_path)
        latest = fresh_data.index.max().date().isoformat() if len(fresh_data) else None
        return SymbolUpdateResult(
            symbol=symbol,
            status="OK",
            rows_added=int(len(fresh_data)),
            rows_updated=0,
            latest_date_before=None,
            latest_date_after=latest,
        )

    # Case 2: parquet exists — merge.
    existing = pd.read_parquet(parquet_path)
    latest_before = existing.index.max().date().isoformat() if len(existing) else None
    existing_dates = set(existing.index)
    fresh_dates = set(fresh_data.index)

    # rows_added: dates in fresh but not in existing
    new_dates = fresh_dates - existing_dates
    rows_added = len(new_dates)

    # rows_updated: dates in BOTH where existing.Close is NaN AND fresh.Close is non-NaN
    overlap_dates = fresh_dates & existing_dates
    rows_updated = 0
    if overlap_dates and "Close" in existing.columns and "Close" in fresh_data.columns:
        for d in overlap_dates:
            ex_close = existing.loc[d, "Close"]
            fr_close = fresh_data.loc[d, "Close"]
            if pd.isna(ex_close) and not pd.isna(fr_close):
                rows_updated += 1

    # Concat with fresh LAST so drop_duplicates keep='last' lets fresh win.
    combined = pd.concat([existing, fresh_data])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined.sort_index()
    combined.index.name = "Date"

    _atomic_write_parquet(combined, parquet_path)

    latest_after = combined.index.max().date().isoformat() if len(combined) else None
    return SymbolUpdateResult(
        symbol=symbol,
        status="OK",
        rows_added=int(rows_added),
        rows_updated=int(rows_updated),
        latest_date_before=latest_before,
        latest_date_after=latest_after,
    )


def update_index_parquet(cache_dir: Path = DEFAULT_CACHE_DIR,
                         lookback_days: int = DEFAULT_LOOKBACK_DAYS,
                         end_date: Optional[date] = None) -> SymbolUpdateResult:
    """Daily refresh for the Nifty index parquet (^NSEI → _index_NSEI.parquet)."""
    end = end_date or date.today()
    start = end - timedelta(days=lookback_days)

    fresh, attempts, err = fetch_symbol_ohlc(NIFTY_SYMBOL, start, end)
    if err is not None:
        return SymbolUpdateResult(
            symbol=NIFTY_SYMBOL,
            status="FAILED",
            error=err,
            attempts=attempts,
        )

    parquet_path = parquet_path_for_symbol(NIFTY_SYMBOL, cache_dir)
    result = update_symbol_parquet(NIFTY_SYMBOL, parquet_path, fresh)
    result.attempts = attempts
    return result


# ============================================================
# Main entry point
# ============================================================

def daily_data_ingest(
    universe_path: Path = DEFAULT_UNIVERSE_CSV,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    end_date: Optional[date] = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    skip_index: bool = False,
    verbose: bool = True,
) -> IngestRunResult:
    """Daily yfinance refresh for the FNO universe + Nifty index."""
    t_start = time.time()
    end = end_date or date.today()
    start = end - timedelta(days=lookback_days)

    universe = load_universe(universe_path)
    result = IngestRunResult(
        run_timestamp_utc=_now_utc_iso(),
        end_date=end.isoformat(),
        universe_size=len(universe),
    )

    if verbose:
        print(f"[data_ingest] universe={len(universe)} symbols  "
              f"window=[{start.isoformat()}, {end.isoformat()}]  "
              f"cache_dir={cache_dir}")

    # --- Per-symbol fetch + update
    for i, symbol in enumerate(universe, start=1):
        try:
            fresh, attempts, err = fetch_symbol_ohlc(symbol, start, end)
            if err is not None:
                result.symbols_failed.append((symbol, err))
                if verbose:
                    print(f"  [{i:>3}/{len(universe)}] {symbol:<20}  FAILED  ({err}, attempts={attempts})")
                continue
            parquet_path = parquet_path_for_symbol(symbol, cache_dir)
            upd = update_symbol_parquet(symbol, parquet_path, fresh)
            upd.attempts = attempts
            if upd.status == "OK":
                result.symbols_succeeded.append(symbol)
                if upd.latest_date_after:
                    result.latest_dates[symbol] = upd.latest_date_after
                if verbose:
                    print(f"  [{i:>3}/{len(universe)}] {symbol:<20}  OK      "
                          f"(+{upd.rows_added} new, +{upd.rows_updated} filled, latest={upd.latest_date_after})")
            elif upd.status == "NO_NEW_DATA":
                result.symbols_no_new_data.append(symbol)
                if upd.latest_date_after:
                    result.latest_dates[symbol] = upd.latest_date_after
                if verbose:
                    print(f"  [{i:>3}/{len(universe)}] {symbol:<20}  NO_NEW  (latest={upd.latest_date_after})")
            else:  # FAILED
                result.symbols_failed.append((symbol, upd.error or "unknown"))
                if verbose:
                    print(f"  [{i:>3}/{len(universe)}] {symbol:<20}  FAILED  ({upd.error})")
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            result.symbols_failed.append((symbol, err_msg))
            if verbose:
                print(f"  [{i:>3}/{len(universe)}] {symbol:<20}  EXCEPTION  ({err_msg})")

    # --- Index
    if skip_index:
        result.index_status = {"skipped": True}
        if verbose:
            print(f"  [index] {NIFTY_SYMBOL}  SKIPPED (skip_index=True)")
    else:
        idx_result = update_index_parquet(cache_dir, lookback_days, end)
        result.index_status = {
            "symbol": NIFTY_SYMBOL,
            "status": idx_result.status,
            "rows_added": idx_result.rows_added,
            "rows_updated": idx_result.rows_updated,
            "latest_date_after": idx_result.latest_date_after,
            "error": idx_result.error,
            "attempts": idx_result.attempts,
        }
        if verbose:
            if idx_result.status == "OK":
                print(f"  [index] {NIFTY_SYMBOL}  OK      "
                      f"(+{idx_result.rows_added} new, +{idx_result.rows_updated} filled, "
                      f"latest={idx_result.latest_date_after})")
            else:
                print(f"  [index] {NIFTY_SYMBOL}  {idx_result.status}  ({idx_result.error})")

    # --- Overall status
    n_ok = len(result.symbols_succeeded) + len(result.symbols_no_new_data)
    n_total = len(universe)
    pct_ok = n_ok / n_total if n_total > 0 else 0.0
    index_ok = (skip_index or result.index_status.get("status") == "OK"
                or result.index_status.get("status") == "NO_NEW_DATA")

    if pct_ok == 1.0 and index_ok:
        result.overall_status = "OK"
    elif pct_ok >= 0.5 and index_ok:
        result.overall_status = "PARTIAL"
    else:
        result.overall_status = "ERROR"

    result.elapsed_seconds = round(time.time() - t_start, 2)

    if verbose:
        print()
        print(f"[data_ingest] Done. status={result.overall_status}  "
              f"succeeded={len(result.symbols_succeeded)}/{n_total}  "
              f"no_new_data={len(result.symbols_no_new_data)}  "
              f"failed={len(result.symbols_failed)}  "
              f"elapsed={result.elapsed_seconds}s")

    return result


# ============================================================
# CLI entry point
# ============================================================

def _main_cli() -> int:
    """CLI entry point. Exit code: 0=OK, 1=PARTIAL, 2=ERROR."""
    result = daily_data_ingest()
    if result.overall_status == "OK":
        return 0
    if result.overall_status == "PARTIAL":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(_main_cli())
