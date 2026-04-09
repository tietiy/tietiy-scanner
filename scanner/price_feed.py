# ── scanner/price_feed.py ─────────────────────────────
# F3: Price feed abstraction layer
# All price fetching goes through get_prices()
# Switch source in config.py: PRICE_SOURCE = "yfinance"
#
# Current adapters:
#   yfinance  — default, 15min delay, no auth needed
#   5paisa    — future, real-time, needs daily token
#
# Usage:
#   from price_feed import get_prices
#   prices = get_prices(['RELIANCE.NS', 'TCS.NS'])
#   # returns {'RELIANCE.NS': 2450.5, 'TCS.NS': 3820.0}
# ─────────────────────────────────────────────────────

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from config import PRICE_SOURCE


# ── YFINANCE ADAPTER ─────────────────────────────────
def _fetch_yfinance(symbols: list) -> dict:
    """
    Fetch current prices via yfinance.
    Uses 1m intraday during market hours.
    Falls back to daily close if 1m unavailable.
    Returns dict: symbol → price (float)
    """
    import yfinance as yf
    import pandas as pd

    prices = {}

    # Batch download — faster than one-by-one
    try:
        tickers = yf.Tickers(' '.join(symbols))
        for sym in symbols:
            try:
                # Try 1m first
                df = yf.download(
                    sym,
                    period='1d',
                    interval='1m',
                    progress=False,
                    auto_adjust=False,
                )
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [c[0] for c in df.columns]
                    prices[sym] = float(df.iloc[-1]['Close'])
                    continue

                # Fallback daily
                df = yf.download(
                    sym,
                    period='5d',
                    interval='1d',
                    progress=False,
                    auto_adjust=False,
                )
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [c[0] for c in df.columns]
                    prices[sym] = float(df.iloc[-1]['Close'])

            except Exception as e:
                print(f"[price_feed] yfinance error {sym}: {e}")
                prices[sym] = None

    except Exception as e:
        print(f"[price_feed] Batch error: {e}")

    return prices


# ── 5PAISA ADAPTER (STUB) ─────────────────────────────
def _fetch_5paisa(symbols: list) -> dict:
    """
    5paisa MarketFeed adapter.
    Requires:
      - FIVEPAISA_ACCESS_TOKEN in env
      - ScripCode mapping pre-loaded
    Falls back to yfinance if token missing.
    NOT ACTIVE — stub for future integration.
    """
    token = os.environ.get('FIVEPAISA_ACCESS_TOKEN', '')

    if not token:
        print("[price_feed] 5paisa token missing — "
              "falling back to yfinance")
        return _fetch_yfinance(symbols)

    # Placeholder — wire py5paisa here when ready
    print("[price_feed] 5paisa adapter not yet wired — "
          "falling back to yfinance")
    return _fetch_yfinance(symbols)


# ── PUBLIC API ────────────────────────────────────────
def get_prices(symbols: list) -> dict:
    """
    Main entry point. Called by ltp_writer
    and stop_alert_writer.

    Args:
        symbols: list of NSE symbols e.g. ['RELIANCE.NS']

    Returns:
        dict: symbol → float price or None on failure
    """
    if not symbols:
        return {}

    source = PRICE_SOURCE.lower()

    print(f"[price_feed] Fetching {len(symbols)} prices "
          f"via {source}")

    if source == '5paisa':
        return _fetch_5paisa(symbols)
    else:
        return _fetch_yfinance(symbols)


def get_price(symbol: str) -> float | None:
    """
    Single symbol convenience wrapper.
    Returns float price or None.
    """
    result = get_prices([symbol])
    return result.get(symbol)
