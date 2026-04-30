"""
MS-1 — Backtest Lab data fetcher.

Per ROADMAP.md MS-1 spec: fetch + cache 15-year OHLCV for 188 F&O stocks +
^NSEI + ^NSEBANK indices. Batched yfinance with retry/backoff. Resumable.
Coverage logged to /lab/logs/fetch_report.json.

Usage:
    python lab/infrastructure/data_fetcher.py            # full fetch
    python lab/infrastructure/data_fetcher.py --smoke    # 5-symbol verification
    python lab/infrastructure/data_fetcher.py --refetch  # ignore cache; refetch all

Coverage thresholds (per ROADMAP):
    OK      = >= 1000 rows  (sufficient for multi-year analysis)
    PARTIAL = < 1000 rows
    FAILED  = no data after retries

Exit codes:
    0 = success (coverage_pct >= 70%)
    1 = partial (30% <= coverage_pct < 70%); MS-2 may proceed with reduced universe
    2 = critical (coverage_pct < 30%); T1 tripwire — HALT before MS-2

NSE bhav copy fallback: documented in /lab/infrastructure/NSE_BHAV_FALLBACK.md
(NOT auto-attempted; manual user action if T1 fires).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

# ── Paths ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
_UNIVERSE_CSV = _REPO_ROOT / "data" / "fno_universe.csv"
_CACHE_DIR = _LAB_ROOT / "cache"
_LOGS_DIR = _LAB_ROOT / "logs"
_FETCH_REPORT = _LOGS_DIR / "fetch_report.json"

# ── Constants per ROADMAP MS-1 ────────────────────────────────────────
_PERIOD_START = "2011-01-01"
_PERIOD_END = "2026-04-30"  # snapshot date; updated when re-running
_BATCH_SIZE = 25
_BATCH_DELAY_SEC = 2.0
_RETRY_DELAYS = [5, 15, 30]  # 3 attempts: 5s, 15s, 30s exponential
_OK_ROW_FLOOR = 1000
# Tickers cross-validated against scanner/main.py:SECTOR_INDICES (production scanner
# uses these 7 sector tickers via yfinance in live runs, confirmed valid).
_INDEX_SYMBOLS = ["^NSEI", "^NSEBANK", "^CNXIT", "^CNXPHARMA", "^CNXAUTO",
                  "^CNXMETAL", "^CNXENERGY", "^CNXFMCG", "^CNXINFRA"]
_SMOKE_SYMBOLS = ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "^NSEI", "^NSEBANK"]


# ── Coverage report data classes ──────────────────────────────────────
@dataclass
class SymbolFetchResult:
    symbol: str
    status: str  # "OK" | "PARTIAL" | "FAILED" | "CACHED_SKIP"
    rows: int = 0
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None
    parquet_path: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0


@dataclass
class FetchReport:
    started_at: str
    finished_at: Optional[str] = None
    period_start: str = _PERIOD_START
    period_end: str = _PERIOD_END
    universe_size: int = 0
    smoke_mode: bool = False
    refetch: bool = False
    results: list[SymbolFetchResult] = field(default_factory=list)
    coverage_pct: float = 0.0
    coverage_status: str = "PENDING"  # "OK" | "PARTIAL_OK" | "CRITICAL"


# ── Helpers ───────────────────────────────────────────────────────────

def _safe_filename(symbol: str) -> str:
    """`^NSEI` → `_index_NSEI`; `RELIANCE.NS` → `RELIANCE_NS`."""
    if symbol.startswith("^"):
        return f"_index_{symbol[1:]}"
    return symbol.replace(".", "_")


def _parquet_path(symbol: str) -> Path:
    return _CACHE_DIR / f"{_safe_filename(symbol)}.parquet"


def _load_universe() -> list[str]:
    if not _UNIVERSE_CSV.exists():
        raise FileNotFoundError(f"Universe CSV not found: {_UNIVERSE_CSV}")
    symbols = []
    with open(_UNIVERSE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = (row.get("symbol") or "").strip()
            if sym:
                symbols.append(sym)
    return symbols


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Fetch core ────────────────────────────────────────────────────────

def fetch_symbol(symbol: str,
                 period_start: str = _PERIOD_START,
                 period_end: str = _PERIOD_END,
                 retry_delays: list = None) -> SymbolFetchResult:
    """Fetch single symbol's OHLCV. Returns SymbolFetchResult.
    Retries up to len(retry_delays) times with exponential backoff."""
    retry_delays = retry_delays or _RETRY_DELAYS
    attempts = 0
    last_error: Optional[str] = None

    for attempt_idx in range(len(retry_delays) + 1):
        attempts = attempt_idx + 1
        try:
            df = yf.download(
                symbol,
                start=period_start,
                end=period_end,
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is None or df.empty:
                last_error = "empty_dataframe"
            else:
                # Flatten potential MultiIndex columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                # Ensure datetime index without tz
                df.index = pd.to_datetime(df.index, errors="coerce")
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df = df.dropna(how="all")
                rows = len(df)
                if rows == 0:
                    last_error = "all_rows_nan"
                else:
                    out_path = _parquet_path(symbol)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(out_path, compression="snappy")
                    earliest = df.index.min().date().isoformat() if rows else None
                    latest = df.index.max().date().isoformat() if rows else None
                    status = "OK" if rows >= _OK_ROW_FLOOR else "PARTIAL"
                    return SymbolFetchResult(
                        symbol=symbol,
                        status=status,
                        rows=rows,
                        earliest_date=earliest,
                        latest_date=latest,
                        parquet_path=str(out_path.relative_to(_REPO_ROOT)),
                        attempts=attempts,
                    )
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"

        # Sleep before next retry (except after final attempt)
        if attempt_idx < len(retry_delays):
            delay = retry_delays[attempt_idx]
            print(f"  [{symbol}] attempt {attempts} failed ({last_error}); "
                  f"sleeping {delay}s...", flush=True)
            time.sleep(delay)

    return SymbolFetchResult(
        symbol=symbol,
        status="FAILED",
        error=last_error,
        attempts=attempts,
    )


def fetch_universe(symbols: list[str],
                   refetch: bool = False) -> FetchReport:
    """Fetch all symbols in batches with delays. Resumable: skip already-cached
    unless refetch=True."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    report = FetchReport(
        started_at=_now_iso(),
        universe_size=len(symbols),
        refetch=refetch,
    )

    total = len(symbols)
    print(f"[fetcher] Universe: {total} symbols; period {_PERIOD_START} → {_PERIOD_END}",
          flush=True)
    print(f"[fetcher] Batch size {_BATCH_SIZE}; batch delay {_BATCH_DELAY_SEC}s; "
          f"retry delays {_RETRY_DELAYS}", flush=True)

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = symbols[batch_start:batch_start + _BATCH_SIZE]
        print(f"\n[fetcher] Batch {batch_start // _BATCH_SIZE + 1} "
              f"({batch_start + 1}-{min(batch_start + _BATCH_SIZE, total)}/{total})",
              flush=True)

        for sym in batch:
            cache_path = _parquet_path(sym)
            if cache_path.exists() and not refetch:
                # Resume mode: skip + load row count
                try:
                    cached_df = pd.read_parquet(cache_path)
                    rows = len(cached_df)
                    earliest = (cached_df.index.min().date().isoformat()
                                if rows else None)
                    latest = (cached_df.index.max().date().isoformat()
                              if rows else None)
                    status = "OK" if rows >= _OK_ROW_FLOOR else "PARTIAL"
                    result = SymbolFetchResult(
                        symbol=sym,
                        status="CACHED_SKIP",
                        rows=rows,
                        earliest_date=earliest,
                        latest_date=latest,
                        parquet_path=str(cache_path.relative_to(_REPO_ROOT)),
                    )
                    print(f"  [{sym}] CACHED ({rows} rows; skip)", flush=True)
                    report.results.append(result)
                    continue
                except Exception as e:
                    print(f"  [{sym}] cache read failed ({e}); refetching",
                          flush=True)

            result = fetch_symbol(sym)
            print(f"  [{sym}] {result.status} (rows={result.rows}, "
                  f"attempts={result.attempts})", flush=True)
            report.results.append(result)

        # Inter-batch delay
        if batch_start + _BATCH_SIZE < total:
            time.sleep(_BATCH_DELAY_SEC)

    report.finished_at = _now_iso()

    # Coverage computation
    ok_count = sum(1 for r in report.results
                   if r.status in ("OK", "CACHED_SKIP") and r.rows >= _OK_ROW_FLOOR)
    report.coverage_pct = round(ok_count / total * 100, 2) if total else 0.0
    if report.coverage_pct >= 70.0:
        report.coverage_status = "OK"
    elif report.coverage_pct >= 30.0:
        report.coverage_status = "PARTIAL_OK"
    else:
        report.coverage_status = "CRITICAL"

    return report


def write_fetch_report(report: FetchReport) -> Path:
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    with open(_FETCH_REPORT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return _FETCH_REPORT


def print_summary(report: FetchReport) -> None:
    print()
    print("=" * 72)
    print("MS-1 FETCH SUMMARY")
    print("=" * 72)
    print(f"  Universe:       {report.universe_size}")
    print(f"  Coverage:       {report.coverage_pct}% ({report.coverage_status})")
    print()
    by_status: dict = {}
    for r in report.results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    for s, n in sorted(by_status.items()):
        print(f"  {s:<14s} {n}")
    print()
    print(f"  Report: {_FETCH_REPORT.relative_to(_REPO_ROOT)}")
    print(f"  Cache:  {_CACHE_DIR.relative_to(_REPO_ROOT)}/")


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MS-1 Backtest Lab data fetcher (yfinance + parquet cache)")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke mode: fetch 5 verification symbols only")
    parser.add_argument("--refetch", action="store_true",
                        help="Ignore cache; refetch all symbols")
    args = parser.parse_args()

    if args.smoke:
        symbols = list(_SMOKE_SYMBOLS)
        print(f"[fetcher] SMOKE MODE: {len(symbols)} symbols")
    else:
        universe = _load_universe()
        symbols = universe + _INDEX_SYMBOLS
        print(f"[fetcher] FULL MODE: {len(universe)} stocks + "
              f"{len(_INDEX_SYMBOLS)} indices = {len(symbols)} symbols")

    report = fetch_universe(symbols, refetch=args.refetch)
    if args.smoke:
        report.smoke_mode = True
    write_fetch_report(report)
    print_summary(report)

    # Exit codes per spec
    if report.coverage_status == "CRITICAL":
        return 2
    if report.coverage_status == "PARTIAL_OK":
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[fetcher] Interrupted", file=sys.stderr)
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(3)
