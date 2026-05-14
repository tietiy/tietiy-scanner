"""Phase 1: Cache 15-year OHLCV for the F&O universe.

Downloads each symbol once, writes data/historical/cache/<sym>.parquet.
Skips symbols that already have a cached file. Failures are logged to
data/historical/cache/_failed.json.

Idempotent — safe to re-run.
"""
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

REPO = "/Users/abhisheklalwani/code/tietiy-scanner"
UNIVERSE = os.path.join(REPO, "data", "fno_universe.csv")
CACHE_DIR = os.path.join(REPO, "data", "historical", "cache")
FAILED_LOG = os.path.join(CACHE_DIR, "_failed.json")

START_DATE = "2011-01-01"
END_DATE = "2026-05-15"  # inclusive of today


def load_symbols():
    with open(UNIVERSE) as f:
        reader = csv.DictReader(f)
        return [(r["symbol"], r.get("sector", "Other"), r.get("grade", "B"))
                for r in reader if r["symbol"].strip()]


def fetch_one(symbol: str) -> tuple[str, str | None]:
    path = os.path.join(CACHE_DIR, f"{symbol.replace('/', '_')}.parquet")
    if os.path.exists(path):
        return symbol, None  # already cached

    try:
        df = yf.download(symbol, start=START_DATE, end=END_DATE,
                         progress=False, auto_adjust=False, threads=False)
        if df is None or df.empty:
            return symbol, "empty"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df.index = pd.to_datetime(df.index, errors="coerce")
        if df.index.tzinfo:
            df.index = df.index.tz_localize(None)
        df = df[df.index.notna()].dropna(subset=["Close"])
        if len(df) < 250:
            return symbol, f"too_few_bars_{len(df)}"
        df.to_parquet(path)
        return symbol, None
    except Exception as e:
        return symbol, f"exception_{type(e).__name__}_{str(e)[:60]}"


def main():
    symbols = load_symbols()
    print(f"Symbols in universe: {len(symbols)}")
    cached = [s for s, _, _ in symbols
              if os.path.exists(
                  os.path.join(CACHE_DIR, f"{s.replace('/', '_')}.parquet"))]
    print(f"Already cached: {len(cached)} (will skip)")
    todo = [s for s, _, _ in symbols
            if not os.path.exists(
                os.path.join(CACHE_DIR, f"{s.replace('/', '_')}.parquet"))]
    print(f"To download: {len(todo)}")

    if not todo:
        print("All cached. Done.")
        return

    results = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(fetch_one, sym): sym for sym in todo}
        done_count = 0
        for fut in as_completed(futures):
            sym, err = fut.result()
            results[sym] = err
            done_count += 1
            status = "OK" if err is None else f"FAIL ({err})"
            if done_count % 20 == 0 or err is not None:
                print(f"  [{done_count}/{len(todo)}] {sym}: {status}")

    failed = {s: e for s, e in results.items() if e is not None}
    ok = len(results) - len(failed)
    print(f"\nResults: {ok} ok, {len(failed)} failed")
    if failed:
        with open(FAILED_LOG, "w") as f:
            json.dump(failed, f, indent=2)
        print(f"Failures written to {FAILED_LOG}")
        for s, e in list(failed.items())[:10]:
            print(f"  - {s}: {e}")


if __name__ == "__main__":
    main()
