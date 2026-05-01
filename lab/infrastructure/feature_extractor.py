"""
Feature extractor — computes 114 features per signal per spec v2.1.

Phase 1B per `lab/COMBINATION_ENGINE_PLAN.md`. Feeds Phase 2 importance
analysis + Phase 4 combination engine downstream.

Architecture:
- FeatureExtractor.extract(signals_df) → enriched DataFrame with feat_<id> cols
- Per-signal pipeline: load stock cache once → compute base indicators
  (EMAs/ATR/pivots/weekly) → dispatch to family computers → merge feature dict
- Cross-family caching: pivot detection / EMAs / ATR computed once per signal,
  reused across families that need them (Family 1 + 2 + 6).

NEVER use post-signal data — every computation slices ohlcv_history to
`scan_date` inclusive only. No-future-leakage invariant tested in test suite.

Build sequence:
- 3A (this file): core class + Family 3 momentum + Family 4 volume +
  Family 5 cheap subset (17 of 20; cross-stock features deferred)
- 3B: Family 1 compression + Family 2 institutional zones (FVG/OB/distances)
- 3C: Family 6 patterns + Family 2 Fib + cross-stock Family 5 features
- 3D: comprehensive tests (~30 tests)

NO production scanner modifications. Read-only references to
scanner/scanner_core.py and scanner/config.py for primitives reuse.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
_DEFAULT_CACHE_DIR = _LAB_ROOT / "cache"

# Reuse scanner primitives (read-only import; no scanner/ modification)
sys.path.insert(0, str(_REPO_ROOT / "scanner"))
from config import (  # noqa: E402  (allows runtime path manipulation above)
    PIVOT_LOOKBACK, ATR_PERIOD, EMA_FAST, EMA_MID, EMA_SLOW,
)
from scanner_core import detect_pivots as _scanner_detect_pivots  # noqa: E402

# Local registry import
sys.path.insert(0, str(_HERE))
from feature_loader import FeatureRegistry  # noqa: E402


# ── Constants ─────────────────────────────────────────────────────────

_FEAT_PREFIX = "feat_"
_EXPECTED_FEATURE_COUNT = 114
_FAMILIES_3A = ("momentum", "volume", "regime")  # what 3A implements
_DEFERRED_3A = (  # historical: 3A deferred these to 3C-2; now implemented
    "sector_rank_within_universe",
    "market_breadth_pct",
    "advance_decline_ratio_20d",
)
# Cross-stock minimum universe coverage required to compute breadth/AD/rank;
# below this we return NaN for these 3 features (graceful fallback).
_CROSS_STOCK_MIN_COVERAGE = 100
# Sector index ticker map (matches scanner/main.py SECTOR_INDICES)
_SECTOR_INDEX_MAP = {
    "Bank":   "_index_NSEBANK.parquet",
    "IT":     "_index_CNXIT.parquet",
    "Pharma": "_index_CNXPHARMA.parquet",
    "Auto":   "_index_CNXAUTO.parquet",
    "Metal":  "_index_CNXMETAL.parquet",
    "Energy": "_index_CNXENERGY.parquet",
    "FMCG":   "_index_CNXFMCG.parquet",
    "Infra":  "_index_CNXINFRA.parquet",
}
_NIFTY_INDEX_FILE = "_index_NSEI.parquet"
_BANK_NIFTY_INDEX_FILE = "_index_NSEBANK.parquet"

# 15-yr Nifty vol percentile thresholds (from INV-007 baseline run);
# loaded once at construction
_VOL_PERCENTILE_THRESHOLDS_DEFAULT = {"p30": 0.1082, "p70": 0.1604}


# ── Helper: parse symbol to parquet filename ──────────────────────────

def _symbol_to_parquet(symbol: str) -> str:
    """e.g. 'HDFCBANK.NS' → 'HDFCBANK_NS.parquet'."""
    return symbol.replace(".NS", "_NS").replace(".BO", "_BO") + ".parquet"


# ── Cached indicators dataclass ───────────────────────────────────────

@dataclass
class CachedIndicators:
    """Per-signal indicator cache populated once, reused across families."""
    ohlcv: pd.DataFrame  # Stock's cache up to and including scan_date
    scan_date: pd.Timestamp
    close_at_signal: float
    high_at_signal: float
    low_at_signal: float
    open_at_signal: float
    volume_at_signal: float
    atr_at_signal: Optional[float] = None
    ema20_at_signal: Optional[float] = None
    ema50_at_signal: Optional[float] = None
    ema200_at_signal: Optional[float] = None
    # Pre-computed series (full history up to scan_date)
    ema20_series: Optional[pd.Series] = None
    ema50_series: Optional[pd.Series] = None
    ema200_series: Optional[pd.Series] = None
    atr_series: Optional[pd.Series] = None
    # 3B additions ────────────────────────────────────────────────────────
    # Pivots (full history; list of (Timestamp, price))
    pivot_highs: list = field(default_factory=list)
    pivot_lows: list = field(default_factory=list)
    # Bollinger Bands at signal (B4: 20-period SMA, 2.0σ)
    bb_mid_at_signal: Optional[float] = None
    bb_upper_at_signal: Optional[float] = None
    bb_lower_at_signal: Optional[float] = None
    bb_width_at_signal: Optional[float] = None
    # Keltner Channels at signal (B4: 20-period EMA, 1.5×ATR)
    kc_mid_at_signal: Optional[float] = None
    kc_upper_at_signal: Optional[float] = None
    kc_lower_at_signal: Optional[float] = None
    kc_width_at_signal: Optional[float] = None
    # 52-week extremes
    high_52w_at_signal: Optional[float] = None
    low_52w_at_signal: Optional[float] = None
    # Rolling range_compression_20d series (used by compression_duration +
    # consolidation_zone_distance_atr); full history.
    range_compression_20d_series: Optional[pd.Series] = None
    # 60-bar avg ATR for atr_compression_pct
    atr_avg_60d_at_signal: Optional[float] = None
    weekly_ohlcv: Optional[pd.DataFrame] = None


# ── FeatureExtractor ──────────────────────────────────────────────────

class FeatureExtractor:
    """Computes 114 features per signal across 6 families.

    Construct once per session (loads sector index parquets at init), then
    call extract() repeatedly on signal batches.
    """

    def __init__(self, registry: FeatureRegistry,
                 cache_dir: Optional[Path] = None):
        self.registry = registry
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        if len(registry) != _EXPECTED_FEATURE_COUNT:
            raise ValueError(
                f"FeatureExtractor expects registry with {_EXPECTED_FEATURE_COUNT} "
                f"features; got {len(registry)}")
        # Load index parquets at init — used by Family 5 regime features
        self._nifty_close = self._load_index_close(_NIFTY_INDEX_FILE)
        self._bank_nifty_close = self._load_index_close(_BANK_NIFTY_INDEX_FILE)
        self._sector_indices: dict[str, pd.Series] = {}
        for sector, fname in _SECTOR_INDEX_MAP.items():
            try:
                self._sector_indices[sector] = self._load_index_close(fname)
            except FileNotFoundError:
                self._sector_indices[sector] = None  # Sector index unavailable
        # Pre-compute Nifty vol percentile thresholds from full history
        self._vol_thresholds = self._compute_nifty_vol_thresholds()
        # Cross-stock universe (3C-2): pre-load 188 stock closes at __init__,
        # lazy compute per-scan_date features in _get_cross_stock_at.
        # _universe_close: DataFrame indexed by date, columns = symbol.
        # _universe_sectors: dict {symbol: sector} (read from sector index map
        # if available, else from signal_history/sectors mapping if present).
        self._universe_close: Optional[pd.DataFrame] = None
        self._universe_sectors: dict[str, str] = {}
        self._cross_stock_cache: dict = {}  # {scan_date: {sector_rank,...}}
        self._load_universe()

    # ── Initialization helpers ────────────────────────────────────────

    def _load_index_close(self, filename: str) -> pd.Series:
        path = self.cache_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"index parquet not found: {path}")
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df["Close"].sort_index().dropna()

    def _load_universe(self) -> None:
        """Pre-load 188-stock close series into memory at __init__.
        Reads symbol→sector map from data/fno_universe.csv. Stock closes
        loaded from cache_dir; missing stocks logged + skipped.
        """
        import csv
        universe_csv = _REPO_ROOT / "data" / "fno_universe.csv"
        if not universe_csv.exists():
            self._universe_close = None
            return
        try:
            with open(universe_csv) as fh:
                rdr = csv.DictReader(fh)
                for row in rdr:
                    sym = row.get("symbol", "").strip()
                    sec = row.get("sector", "Other").strip() or "Other"
                    if sym:
                        self._universe_sectors[sym] = sec
        except Exception:
            self._universe_close = None
            return
        # Load each stock's close series; concat into wide DataFrame
        closes_by_sym = {}
        for sym in self._universe_sectors.keys():
            path = self.cache_dir / _symbol_to_parquet(sym)
            if not path.exists():
                continue
            try:
                df = pd.read_parquet(path, columns=["Close"])
                df.index = pd.to_datetime(df.index)
                df = df.sort_index().dropna(subset=["Close"])
                closes_by_sym[sym] = df["Close"]
            except Exception:
                continue
        if len(closes_by_sym) >= _CROSS_STOCK_MIN_COVERAGE:
            self._universe_close = pd.DataFrame(closes_by_sym).sort_index()
        else:
            self._universe_close = None

    def _get_cross_stock_at(self, scan_date: pd.Timestamp,
                              signal_sector: Optional[str]) -> dict:
        """Lazy-compute cross-stock features for given scan_date; cache
        per-date result.

        Returns dict with sector_rank, market_breadth_pct, advance_decline_ratio_20d.
        Falls back to NaN if universe not loaded or coverage at scan_date is
        below _CROSS_STOCK_MIN_COVERAGE.
        """
        nan_result = {
            "sector_rank": np.nan,
            "market_breadth_pct": np.nan,
            "advance_decline_ratio_20d": np.nan,
        }
        if self._universe_close is None:
            return nan_result
        # Use scan_date as cache key (per-date computation reusable across
        # all signals on the same date).
        key = pd.Timestamp(scan_date).normalize()
        if key not in self._cross_stock_cache:
            self._cross_stock_cache[key] = self._compute_cross_stock(key)
        cached = self._cross_stock_cache[key]
        # sector_rank depends on signal's sector
        if signal_sector and cached["sector_returns"] is not None:
            sec_returns = cached["sector_returns"]
            if signal_sector in sec_returns.index:
                # Rank highest return = 1
                sorted_sectors = sec_returns.sort_values(ascending=False)
                rank = int(sorted_sectors.index.get_loc(signal_sector)) + 1
                sector_rank = float(rank)
            else:
                sector_rank = np.nan
        else:
            sector_rank = np.nan
        return {
            "sector_rank": sector_rank,
            "market_breadth_pct": cached["market_breadth_pct"],
            "advance_decline_ratio_20d": cached["advance_decline_ratio_20d"],
        }

    def _compute_cross_stock(self, scan_date: pd.Timestamp) -> dict:
        """Compute breadth + AD ratio + sector returns at scan_date.
        Returns dict (caller does sector lookup)."""
        out = {
            "market_breadth_pct": np.nan,
            "advance_decline_ratio_20d": np.nan,
            "sector_returns": None,
        }
        if self._universe_close is None:
            return out
        # Slice universe_close to dates ≤ scan_date (no future leakage)
        u = self._universe_close.loc[self._universe_close.index <= scan_date]
        if len(u) < 50:
            return out
        # At scan_date, count how many symbols have close > EMA50.
        # Use last bar (most recent date ≤ scan_date).
        last_bar = u.iloc[-1]
        valid_mask = last_bar.notna()
        n_valid = int(valid_mask.sum())
        if n_valid < _CROSS_STOCK_MIN_COVERAGE:
            return out
        # EMA50 across each symbol's close
        ema50 = u.ewm(span=EMA_MID, adjust=False).mean()
        ema50_last = ema50.iloc[-1]
        above = ((last_bar > ema50_last) & valid_mask).sum()
        out["market_breadth_pct"] = float(above) / float(n_valid)
        # Advance/decline ratio: sum (advances - declines) / total over 20d
        if len(u) >= 21:
            diff = u.diff()  # daily change
            tail20 = diff.iloc[-20:]
            adv = (tail20 > 0).sum().sum()
            dec = (tail20 < 0).sum().sum()
            total = adv + dec
            if total > 0:
                out["advance_decline_ratio_20d"] = float(adv - dec) / float(total)
        # Sector returns over last 20 days
        if len(u) >= 21:
            ret_20d = (u.iloc[-1] / u.iloc[-21] - 1).dropna()
            sector_returns = {}
            for sec in set(self._universe_sectors.values()):
                syms_in_sec = [s for s, x in self._universe_sectors.items()
                                  if x == sec and s in ret_20d.index]
                if syms_in_sec:
                    sec_ret = float(ret_20d.loc[syms_in_sec].mean())
                    sector_returns[sec] = sec_ret
            if sector_returns:
                out["sector_returns"] = pd.Series(sector_returns)
        return out

    def _compute_nifty_vol_thresholds(self) -> dict:
        """20d rolling vol percentiles across full Nifty history (per INV-007)."""
        try:
            log_returns = np.log(self._nifty_close / self._nifty_close.shift(1))
            rolling_vol = log_returns.rolling(20).std() * math.sqrt(252)
            valid = rolling_vol.dropna()
            return {
                "p30": float(valid.quantile(0.30)),
                "p70": float(valid.quantile(0.70)),
            }
        except Exception:
            return _VOL_PERCENTILE_THRESHOLDS_DEFAULT.copy()

    # ── Public API ────────────────────────────────────────────────────

    def extract(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Add 114 feat_* columns to signals_df. Batches by symbol for cache efficiency."""
        if signals_df.empty:
            return signals_df.copy()

        feat_ids = sorted(s.feature_id for s in self.registry.list_all())
        # Pre-allocate output columns with NaN
        out = signals_df.copy()
        for fid in feat_ids:
            out[f"{_FEAT_PREFIX}{fid}"] = np.nan

        # Group by symbol
        by_symbol = signals_df.groupby("symbol", sort=False)
        for symbol, group in by_symbol:
            try:
                stock_df = self._load_stock_history(symbol)
            except FileNotFoundError:
                # Mark all features for this symbol's signals as NaN; continue
                continue
            for idx, signal_row in group.iterrows():
                try:
                    feat_dict = self.extract_single(signal_row, stock_df)
                    for fid, val in feat_dict.items():
                        out.at[idx, f"{_FEAT_PREFIX}{fid}"] = val
                except Exception as exc:  # noqa: BLE001 — extractor must be robust
                    # Per-signal failure leaves NaN; surface in caller logs
                    out.at[idx, f"{_FEAT_PREFIX}_extractor_error"] = str(exc)[:200]
        return out

    def extract_single(self, signal_row: pd.Series,
                        stock_history: pd.DataFrame) -> dict:
        """Compute all 114 features for one signal. Returns dict of {feature_id: value}.

        Parameters
        ----------
        signal_row : pd.Series
            Signal record (must include scan_date, symbol, sector, etc.).
        stock_history : pd.DataFrame
            Stock's full OHLCV history. Will be sliced to scan_date inclusive
            internally (no future-leakage).
        """
        scan_date = pd.Timestamp(signal_row["scan_date"])
        # Slice to scan_date inclusive (no future leakage)
        ohlcv = stock_history.loc[stock_history.index <= scan_date]
        if len(ohlcv) < 2:
            # Insufficient history; return all NaN
            return {s.feature_id: np.nan for s in self.registry.list_all()}

        cache = self._compute_cached_indicators(ohlcv, scan_date)

        feats: dict = {}
        # Sub-block 3A families
        feats.update(self._compute_family_momentum(cache, ohlcv, signal_row))
        feats.update(self._compute_family_volume(cache, ohlcv, signal_row))
        feats.update(self._compute_family_regime_cheap(cache, ohlcv, signal_row))
        # Sub-block 3B families
        feats.update(self._compute_family_compression(cache, ohlcv, signal_row))
        feats.update(self._compute_family_zones_no_fib(cache, ohlcv, signal_row))
        # Sub-block 3C-1 family
        feats.update(self._compute_family_pattern(cache, ohlcv, signal_row))
        # Sub-block 3C-2 families — placeholders return NaN until implemented
        for s in self.registry.list_all():
            if s.feature_id not in feats:
                feats[s.feature_id] = np.nan
        return feats

    # ── Cached indicators (computed once per signal) ──────────────────

    def _compute_cached_indicators(self, ohlcv: pd.DataFrame,
                                     scan_date: pd.Timestamp) -> CachedIndicators:
        last = ohlcv.iloc[-1]
        cache = CachedIndicators(
            ohlcv=ohlcv, scan_date=scan_date,
            close_at_signal=float(last["Close"]) if not pd.isna(last["Close"]) else np.nan,
            high_at_signal=float(last["High"]) if not pd.isna(last["High"]) else np.nan,
            low_at_signal=float(last["Low"]) if not pd.isna(last["Low"]) else np.nan,
            open_at_signal=float(last["Open"]) if not pd.isna(last["Open"]) else np.nan,
            volume_at_signal=float(last["Volume"]) if not pd.isna(last["Volume"]) else np.nan,
        )
        # EMAs (ewm with span = period; matches scanner/scanner_core.add_indicators)
        cache.ema20_series = ohlcv["Close"].ewm(span=EMA_FAST, adjust=False).mean()
        cache.ema50_series = ohlcv["Close"].ewm(span=EMA_MID, adjust=False).mean()
        cache.ema200_series = ohlcv["Close"].ewm(span=EMA_SLOW, adjust=False).mean()
        cache.ema20_at_signal = float(cache.ema20_series.iloc[-1]) if len(cache.ema20_series) else np.nan
        cache.ema50_at_signal = float(cache.ema50_series.iloc[-1]) if len(cache.ema50_series) else np.nan
        cache.ema200_at_signal = float(cache.ema200_series.iloc[-1]) if len(cache.ema200_series) else np.nan
        # ATR via true range EWM (matches scanner/scanner_core.add_indicators)
        prev_close = ohlcv["Close"].shift(1)
        tr = pd.concat([
            ohlcv["High"] - ohlcv["Low"],
            (ohlcv["High"] - prev_close).abs(),
            (ohlcv["Low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        cache.atr_series = tr.ewm(span=ATR_PERIOD, adjust=False).mean()
        cache.atr_at_signal = (
            float(cache.atr_series.iloc[-1])
            if len(cache.atr_series) and not pd.isna(cache.atr_series.iloc[-1])
            else np.nan)
        # 60-bar avg ATR (for atr_compression_pct)
        if len(cache.atr_series) >= 60:
            cache.atr_avg_60d_at_signal = float(
                cache.atr_series.iloc[-60:].mean())
        # ── Pivots (C1 spec — reuse scanner_core.detect_pivots) ──────────
        # detect_pivots returns df with bool pivot_low/pivot_high columns.
        # Last `lookback` bars cannot have a pivot identified yet (by design).
        try:
            pivot_df = _scanner_detect_pivots(ohlcv)
            ph_mask = pivot_df["pivot_high"].values
            pl_mask = pivot_df["pivot_low"].values
            high_arr = ohlcv["High"].values
            low_arr = ohlcv["Low"].values
            idx = ohlcv.index
            cache.pivot_highs = [
                (idx[i], float(high_arr[i]))
                for i in range(len(ohlcv)) if ph_mask[i]
            ]
            cache.pivot_lows = [
                (idx[i], float(low_arr[i]))
                for i in range(len(ohlcv)) if pl_mask[i]
            ]
        except Exception:
            cache.pivot_highs = []
            cache.pivot_lows = []
        # ── Bollinger Bands (B4: 20 SMA, 2σ) ─────────────────────────────
        if len(ohlcv) >= 20:
            close20 = ohlcv["Close"].iloc[-20:]
            mid = float(close20.mean())
            std = float(close20.std(ddof=0))
            cache.bb_mid_at_signal = mid
            cache.bb_upper_at_signal = mid + 2.0 * std
            cache.bb_lower_at_signal = mid - 2.0 * std
            cache.bb_width_at_signal = (
                cache.bb_upper_at_signal - cache.bb_lower_at_signal)
        # ── Keltner Channels (B4: 20 EMA, 1.5×ATR) ───────────────────────
        if (cache.ema20_at_signal is not None and not pd.isna(cache.ema20_at_signal)
                and not pd.isna(cache.atr_at_signal)):
            kc_mid = cache.ema20_at_signal
            cache.kc_mid_at_signal = kc_mid
            cache.kc_upper_at_signal = kc_mid + 1.5 * cache.atr_at_signal
            cache.kc_lower_at_signal = kc_mid - 1.5 * cache.atr_at_signal
            cache.kc_width_at_signal = (
                cache.kc_upper_at_signal - cache.kc_lower_at_signal)
        # ── 52-week extremes (252 trading days) ──────────────────────────
        if len(ohlcv) >= 252:
            cache.high_52w_at_signal = float(ohlcv["High"].iloc[-252:].max())
            cache.low_52w_at_signal = float(ohlcv["Low"].iloc[-252:].min())
        elif len(ohlcv) >= 50:
            # Use available history if not full year
            cache.high_52w_at_signal = float(ohlcv["High"].max())
            cache.low_52w_at_signal = float(ohlcv["Low"].min())
        # ── Rolling range_compression_20d series ─────────────────────────
        # range_compression = (rolling_max_high - rolling_min_low) / rolling_mean_close
        if len(ohlcv) >= 20:
            roll_max = ohlcv["High"].rolling(20).max()
            roll_min = ohlcv["Low"].rolling(20).min()
            roll_mean_close = ohlcv["Close"].rolling(20).mean()
            cache.range_compression_20d_series = (
                (roll_max - roll_min) / roll_mean_close.replace(0, np.nan))
        return cache

    # ── Stock history loader ──────────────────────────────────────────

    def _load_stock_history(self, symbol: str) -> pd.DataFrame:
        path = self.cache_dir / _symbol_to_parquet(symbol)
        if not path.exists():
            raise FileNotFoundError(f"stock parquet not found: {path}")
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        # Drop bars where Close is NaN (some end-of-data partial bars)
        df = df.dropna(subset=["Close"])
        return df

    # ── Family 3 — Momentum (25 features) ─────────────────────────────

    def _compute_family_momentum(self, cache: CachedIndicators,
                                  ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        c = cache.close_at_signal
        feats: dict = {}

        # EMA distance %
        feats["ema20_distance_pct"] = self._safe_div(c - cache.ema20_at_signal,
                                                       cache.ema20_at_signal)
        feats["ema50_distance_pct"] = self._safe_div(c - cache.ema50_at_signal,
                                                       cache.ema50_at_signal)
        feats["ema200_distance_pct"] = self._safe_div(c - cache.ema200_at_signal,
                                                        cache.ema200_at_signal)

        # EMA alignment categorical
        feats["ema_alignment"] = self._ema_alignment(
            c, cache.ema20_at_signal, cache.ema50_at_signal, cache.ema200_at_signal)

        # EMA slopes (Nd window)
        feats["ema20_slope_5d_pct"] = self._series_slope_pct(cache.ema20_series, 5)
        feats["ema50_slope_5d_pct"] = self._series_slope_pct(cache.ema50_series, 5)
        feats["ema50_slope_20d_pct"] = self._series_slope_pct(cache.ema50_series, 20)

        # Daily returns
        feats["daily_3d_return_pct"] = self._return_pct(ohlcv["Close"], 3)
        feats["daily_5d_return_pct"] = self._return_pct(ohlcv["Close"], 5)
        feats["daily_20d_return_pct"] = self._return_pct(ohlcv["Close"], 20)
        feats["daily_60d_return_pct"] = self._return_pct(ohlcv["Close"], 60)

        # Weekly returns (10-day ≈ 2w; 20-day ≈ 4w of trading days)
        feats["weekly_2w_return_pct"] = self._return_pct(ohlcv["Close"], 10)
        feats["weekly_4w_return_pct"] = self._return_pct(ohlcv["Close"], 20)

        # RSI
        feats["RSI_14"] = self._rsi(ohlcv["Close"], 14)
        feats["RSI_9"] = self._rsi(ohlcv["Close"], 9)

        # MACD
        macd_signal, macd_hist_sign, macd_hist_slope = self._macd(ohlcv["Close"])
        feats["MACD_signal"] = macd_signal
        feats["MACD_histogram_sign"] = macd_hist_sign
        feats["MACD_histogram_slope"] = macd_hist_slope

        # Consecutive up/down days
        feats["consecutive_up_days"] = self._consecutive_streak(ohlcv["Close"], up=True)
        feats["consecutive_down_days"] = self._consecutive_streak(ohlcv["Close"], up=False)

        # Trend age days (bars since last EMA50 cross)
        feats["uptrend_age_days"] = self._trend_age(ohlcv["Close"], cache.ema50_series, up=True)
        feats["downtrend_age_days"] = self._trend_age(ohlcv["Close"], cache.ema50_series, up=False)

        # Multi-tf alignment score: count of bull-aligned timeframes (daily/weekly/monthly)
        feats["multi_tf_alignment_score"] = self._multi_tf_alignment(ohlcv)

        # Daily volatility: 20d std-dev of log returns
        feats["daily_volatility_pct"] = self._daily_vol_pct(ohlcv["Close"], 20)

        # ROC_10
        feats["ROC_10"] = self._return_pct(ohlcv["Close"], 10)

        return feats

    # ── Family 4 — Volume (15 features) ───────────────────────────────

    def _compute_family_volume(self, cache: CachedIndicators,
                                ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        feats: dict = {}
        vol = cache.volume_at_signal
        h = cache.high_at_signal; l = cache.low_at_signal
        o = cache.open_at_signal; c = cache.close_at_signal

        # Volume ratios
        feats["vol_ratio_5d"] = self._vol_ratio(ohlcv["Volume"], 5)
        feats["vol_ratio_10d"] = self._vol_ratio(ohlcv["Volume"], 10)
        feats["vol_ratio_20d"] = self._vol_ratio(ohlcv["Volume"], 20)
        feats["vol_ratio_50d"] = self._vol_ratio(ohlcv["Volume"], 50)

        # vol_q passthrough from signal-row
        feats["vol_q"] = signal.get("vol_q", "Average")

        # Volume trend slope (20d regression slope, normalized by mean vol)
        feats["vol_trend_slope_20d"] = self._regression_slope_norm(ohlcv["Volume"], 20)

        # Body and wicks
        rng = h - l if (not pd.isna(h) and not pd.isna(l) and h > l) else None
        if rng and rng > 0:
            feats["body_to_range_ratio"] = abs(c - o) / rng
            feats["upper_wick_ratio"] = (h - max(o, c)) / rng
            feats["lower_wick_ratio"] = (min(o, c) - l) / rng
            feats["close_pos_in_range"] = (c - l) / rng
        else:
            feats["body_to_range_ratio"] = np.nan
            feats["upper_wick_ratio"] = np.nan
            feats["lower_wick_ratio"] = np.nan
            feats["close_pos_in_range"] = np.nan

        # vol_climax / vol_dryup flags (vs 20d avg)
        v_avg20 = self._series_mean_excl_last(ohlcv["Volume"], 20)
        if v_avg20 and not pd.isna(v_avg20) and v_avg20 > 0 and not pd.isna(vol):
            ratio = vol / v_avg20
            feats["vol_climax_flag"] = bool(ratio > 2.5)
            feats["vol_dryup_flag"] = bool(ratio < 0.5)
        else:
            feats["vol_climax_flag"] = np.nan
            feats["vol_dryup_flag"] = np.nan

        # Accumulation / distribution signed (sum (close-open) × vol over 20d, normalized)
        feats["accumulation_distribution_signed"] = self._accum_dist_signed(ohlcv, 20)

        # Volume at pivot ratio (signal-row volume vs 20d avg; matches scanner heuristic)
        feats["volume_at_pivot_ratio"] = self._vol_ratio(ohlcv["Volume"], 20)

        # OBV slope 20d normalized
        feats["obv_slope_20d_pct"] = self._obv_slope_norm(ohlcv, 20)

        return feats

    # ── Family 5 — Regime cheap subset (17 of 20) ─────────────────────

    def _compute_family_regime_cheap(self, cache: CachedIndicators,
                                       ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        feats: dict = {}
        scan_date = cache.scan_date

        # Index returns
        feats["nifty_20d_return_pct"] = self._index_return(self._nifty_close, scan_date, 20)
        feats["nifty_60d_return_pct"] = self._index_return(self._nifty_close, scan_date, 60)
        feats["nifty_200d_return_pct"] = self._index_return(self._nifty_close, scan_date, 200)
        feats["bank_nifty_20d_return_pct"] = self._index_return(self._bank_nifty_close, scan_date, 20)
        feats["bank_nifty_60d_return_pct"] = self._index_return(self._bank_nifty_close, scan_date, 60)

        # Sector index returns (depends on signal's sector)
        sector = signal.get("sector", "Unknown")
        sec_close = self._sector_indices.get(sector)
        feats["sector_index_20d_return_pct"] = (
            self._index_return(sec_close, scan_date, 20) if sec_close is not None else np.nan)
        feats["sector_index_60d_return_pct"] = (
            self._index_return(sec_close, scan_date, 60) if sec_close is not None else np.nan)

        # Nifty vol percentile + regime
        nifty_vol = self._compute_nifty_vol_at(scan_date, 20)
        feats["nifty_vol_percentile_20d"] = self._nifty_vol_percentile_at(scan_date)
        feats["nifty_vol_regime"] = self._nifty_vol_regime_bucket(nifty_vol)

        # Signal-row passthroughs
        feats["regime_state"] = signal.get("regime", "Choppy")
        feats["regime_score"] = signal.get("regime_score", 0)
        feats["sector_momentum_state"] = signal.get("sec_mom", "Neutral")
        feats["rs_q"] = signal.get("rs_q", "Neutral")

        # Stock RS vs Nifty (60d)
        stock_60d_ret = self._return_pct(ohlcv["Close"], 60)
        nifty_60d_ret = feats.get("nifty_60d_return_pct")
        feats["stock_rs_vs_nifty_60d"] = (
            stock_60d_ret - nifty_60d_ret
            if (not pd.isna(stock_60d_ret) and not pd.isna(nifty_60d_ret))
            else np.nan)

        # Calendar features
        feats["day_of_month_bucket"] = self._day_of_month_bucket(scan_date)
        feats["day_of_week"] = scan_date.strftime("%a")  # "Mon", "Tue", ...
        feats["days_to_monthly_expiry"] = self._days_to_monthly_expiry(scan_date)

        # Cross-stock features (3C-2) — lazy per-scan_date cache
        cs = self._get_cross_stock_at(scan_date, signal.get("sector"))
        feats["sector_rank_within_universe"] = cs["sector_rank"]
        feats["market_breadth_pct"] = cs["market_breadth_pct"]
        feats["advance_decline_ratio_20d"] = cs["advance_decline_ratio_20d"]

        return feats

    # ── Family 1 — Compression / range (15 features) ──────────────────

    def _compute_family_compression(self, cache: CachedIndicators,
                                      ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        feats: dict = {}
        h = ohlcv["High"]; l = ohlcv["Low"]; c = ohlcv["Close"]
        rng = h - l  # daily range series

        # ── NR4 / NR7 — today's range narrowest of last 4 / 7 ─────────
        if len(rng) >= 4:
            today_rng = float(rng.iloc[-1])
            min4 = float(rng.iloc[-4:].min())
            feats["NR4_flag"] = bool(today_rng <= min4 + 1e-12)
        else:
            feats["NR4_flag"] = np.nan
        if len(rng) >= 7:
            today_rng = float(rng.iloc[-1])
            min7 = float(rng.iloc[-7:].min())
            feats["NR7_flag"] = bool(today_rng <= min7 + 1e-12)
        else:
            feats["NR7_flag"] = np.nan

        # ── atr_compression_pct = current_ATR / 60d avg ATR ────────────
        feats["atr_compression_pct"] = self._safe_div(
            cache.atr_at_signal, cache.atr_avg_60d_at_signal)

        # ── range_compression_Nd = (highN - lowN) / mean_closeN ────────
        for n in (5, 10, 20, 60):
            feats[f"range_compression_{n}d"] = self._range_compression(ohlcv, n)

        # ── range_position_in_window = (close - low20) / (high20 - low20) ──
        if len(ohlcv) >= 20:
            tail = ohlcv.iloc[-20:]
            hi = float(tail["High"].max()); lo = float(tail["Low"].min())
            denom = hi - lo
            feats["range_position_in_window"] = (
                (cache.close_at_signal - lo) / denom if denom > 0 else np.nan)
        else:
            feats["range_position_in_window"] = np.nan

        # ── compression_duration: trailing days where range_compression_20d < 0.05 ──
        s = cache.range_compression_20d_series
        if s is not None and len(s) > 0:
            count = 0
            for v in reversed(s.values):
                if pd.isna(v):
                    break
                if v < 0.05:
                    count += 1
                else:
                    break
            feats["compression_duration"] = int(count)
        else:
            feats["compression_duration"] = np.nan

        # ── Bollinger Band width % (BB upper-lower / mid) ─────────────
        if (cache.bb_mid_at_signal is not None and cache.bb_mid_at_signal != 0
                and cache.bb_width_at_signal is not None):
            feats["bollinger_band_width_pct"] = (
                cache.bb_width_at_signal / cache.bb_mid_at_signal)
        else:
            feats["bollinger_band_width_pct"] = np.nan

        # ── Bollinger Squeeze: BB_width < KC_width ─────────────────────
        if (cache.bb_width_at_signal is not None
                and cache.kc_width_at_signal is not None):
            feats["bollinger_squeeze_20d"] = bool(
                cache.bb_width_at_signal < cache.kc_width_at_signal)
        else:
            feats["bollinger_squeeze_20d"] = np.nan

        # ── coiled_spring_score (A3) ──────────────────────────────────
        rc20 = feats.get("range_compression_20d")
        ema_align = self._ema_alignment(
            cache.close_at_signal, cache.ema20_at_signal,
            cache.ema50_at_signal, cache.ema200_at_signal)
        feats["coiled_spring_score"] = self._coiled_spring_score(rc20, ema_align)

        # ── consolidation_quality (A4) ────────────────────────────────
        feats["consolidation_quality"] = self._consolidation_quality(
            rc20, feats["coiled_spring_score"])

        # ── inside_day_flag: today.H ≤ prev.H AND today.L ≥ prev.L ──
        if len(ohlcv) >= 2:
            prev = ohlcv.iloc[-2]
            feats["inside_day_flag"] = bool(
                cache.high_at_signal <= prev["High"]
                and cache.low_at_signal >= prev["Low"])
        else:
            feats["inside_day_flag"] = np.nan

        # ── inside_day_streak: consecutive trailing inside days ──────
        feats["inside_day_streak"] = self._inside_day_streak(ohlcv)

        return feats

    # ── Family 2 — Institutional zones (no Fib; 16 features) ───────────

    def _compute_family_zones_no_fib(self, cache: CachedIndicators,
                                       ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        feats: dict = {}
        c = cache.close_at_signal
        atr = cache.atr_at_signal

        # ── 52w_high_distance_pct = (high_52w - close) / high_52w ─────
        if cache.high_52w_at_signal and cache.high_52w_at_signal > 0:
            feats["52w_high_distance_pct"] = (
                (cache.high_52w_at_signal - c) / cache.high_52w_at_signal)
        else:
            feats["52w_high_distance_pct"] = np.nan

        # ── 52w_low_distance_pct = (close - low_52w) / low_52w ────────
        if cache.low_52w_at_signal and cache.low_52w_at_signal > 0:
            feats["52w_low_distance_pct"] = (
                (c - cache.low_52w_at_signal) / cache.low_52w_at_signal)
        else:
            feats["52w_low_distance_pct"] = np.nan

        # ── breakout_strength_atr (B5) ────────────────────────────────
        feats["breakout_strength_atr"] = self._breakout_strength_atr(cache, ohlcv)

        # ── consolidation_zone_distance_atr (B6) ──────────────────────
        feats["consolidation_zone_distance_atr"] = (
            self._consolidation_zone_distance_atr(cache, ohlcv))

        # ── FVG features (A1, 4 features) ─────────────────────────────
        fvg_feats = self._fvg_features(cache, ohlcv, lookback=60)
        feats.update(fvg_feats)

        # ── OB features (A2, 2 features) ──────────────────────────────
        ob_feats = self._ob_features(cache, ohlcv, lookback=60)
        feats.update(ob_feats)

        # ── pivot_distance_atr — ATRs to nearest pivot (high or low) ──
        feats["pivot_distance_atr"] = self._pivot_distance_atr(cache)

        # ── prior_swing_high/low_distance_pct — last 20-bar swing ──
        feats["prior_swing_high_distance_pct"] = (
            self._prior_swing_distance_pct(cache, swing="high", lookback=20))
        feats["prior_swing_low_distance_pct"] = (
            self._prior_swing_distance_pct(cache, swing="low", lookback=20))

        # ── resistance/support_zone_distance_atr — nearest pivot above/below ──
        feats["resistance_zone_distance_atr"] = (
            self._zone_distance_atr(cache, side="resistance"))
        feats["support_zone_distance_atr"] = (
            self._zone_distance_atr(cache, side="support"))

        # ── round_number_proximity_pct (B7) ──────────────────────────
        feats["round_number_proximity_pct"] = self._round_number_proximity(c)

        # ── Fib features (6, 3C-2; B8 direction selection) ───────────
        fib = self._fib_features(cache, ohlcv, signal, lookback=30)
        feats.update(fib)

        return feats

    # ── Family 6 — Patterns (17 features; 3C-1) ────────────────────────

    def _compute_family_pattern(self, cache: CachedIndicators,
                                  ohlcv: pd.DataFrame, signal: pd.Series) -> dict:
        """Triangle (5) + swing (4) + candle flags (8) = 17 features.

        Reuses cache.pivot_highs / pivot_lows (already populated for full
        ohlcv history during _compute_cached_indicators)."""
        feats: dict = {}

        # ── Triangle features (5) ────────────────────────────────────
        tri = self._triangle_features(cache, ohlcv, lookback=30)
        feats["triangle_quality_ascending"] = tri["quality_ascending"]
        feats["triangle_quality_descending"] = tri["quality_descending"]
        feats["triangle_compression_pct"] = tri["compression_pct"]
        feats["triangle_touches_count"] = tri["touches"]
        feats["triangle_age_bars"] = tri["age_bars"]

        # ── Swing features (4) ───────────────────────────────────────
        sw = self._swing_features(cache, ohlcv, lookback=20)
        feats["swing_high_count_20d"] = sw["swing_high_count_20d"]
        feats["swing_low_count_20d"] = sw["swing_low_count_20d"]
        feats["last_swing_high_distance_atr"] = sw["last_swing_high_distance_atr"]
        feats["higher_highs_intact_flag"] = sw["higher_highs_intact_flag"]

        # ── Candle flag features (8) ─────────────────────────────────
        cf = self._candle_flag_features(cache, ohlcv)
        feats.update(cf)

        return feats

    # ────────────────────────────────────────────────────────────────────
    # Computation helpers
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_div(numerator, denominator) -> float:
        try:
            if denominator is None or pd.isna(denominator) or denominator == 0:
                return np.nan
            if numerator is None or pd.isna(numerator):
                return np.nan
            return float(numerator) / float(denominator)
        except Exception:
            return np.nan

    @staticmethod
    def _ema_alignment(close, ema20, ema50, ema200) -> str:
        if any(pd.isna(x) for x in (close, ema20, ema50, ema200)):
            return "mixed"
        if close > ema20 > ema50 > ema200:
            return "bull"
        if close < ema20 < ema50 < ema200:
            return "bear"
        return "mixed"

    @staticmethod
    def _series_slope_pct(series: pd.Series, lookback: int) -> float:
        """(series[-1] / series[-lookback-1] - 1). Returns NaN if insufficient."""
        if series is None or len(series) < lookback + 1:
            return np.nan
        try:
            current = float(series.iloc[-1])
            past = float(series.iloc[-lookback - 1])
            if pd.isna(current) or pd.isna(past) or past == 0:
                return np.nan
            return current / past - 1
        except Exception:
            return np.nan

    @staticmethod
    def _return_pct(close: pd.Series, lookback: int) -> float:
        """(close[-1] / close[-lookback-1] - 1)."""
        if close is None or len(close) < lookback + 1:
            return np.nan
        try:
            current = float(close.iloc[-1])
            past = float(close.iloc[-lookback - 1])
            if pd.isna(current) or pd.isna(past) or past == 0:
                return np.nan
            return current / past - 1
        except Exception:
            return np.nan

    @staticmethod
    def _rsi(close: pd.Series, period: int) -> float:
        """Standard RSI: gain/loss exponentially smoothed. Returns NaN if insufficient."""
        if close is None or len(close) < period + 1:
            return np.nan
        try:
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(period, min_periods=period).mean()
            avg_loss = loss.rolling(period, min_periods=period).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            val = float(rsi.iloc[-1])
            return val if not pd.isna(val) else np.nan
        except Exception:
            return np.nan

    @staticmethod
    def _macd(close: pd.Series) -> tuple:
        """Standard MACD: ema12 - ema26; signal = ema9 of MACD.
        Returns (signal_state, histogram_sign, histogram_slope)."""
        if close is None or len(close) < 35:
            return ("neutral", "negative", "flat")
        try:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal_line

            macd_now = float(macd.iloc[-1])
            sig_now = float(signal_line.iloc[-1])
            hist_now = float(hist.iloc[-1])
            hist_3d_ago = float(hist.iloc[-4]) if len(hist) >= 4 else np.nan

            if pd.isna(macd_now) or pd.isna(sig_now):
                return ("neutral", "negative", "flat")

            signal_state = ("bull" if macd_now > sig_now else "bear"
                              if macd_now < sig_now else "neutral")
            hist_sign = "positive" if hist_now > 0 else "negative"
            if pd.isna(hist_3d_ago) or hist_now == hist_3d_ago:
                hist_slope = "flat"
            elif hist_now > hist_3d_ago:
                hist_slope = "rising"
            else:
                hist_slope = "falling"
            return (signal_state, hist_sign, hist_slope)
        except Exception:
            return ("neutral", "negative", "flat")

    @staticmethod
    def _consecutive_streak(close: pd.Series, up: bool) -> int:
        """Count of trailing consecutive close > prev_close (up=True) or close < prev_close."""
        if close is None or len(close) < 2:
            return 0
        try:
            diff = close.diff().iloc[1:]  # drop first NaN
            count = 0
            for v in reversed(diff.values):
                if pd.isna(v):
                    break
                if up and v > 0:
                    count += 1
                elif (not up) and v < 0:
                    count += 1
                else:
                    break
            return count
        except Exception:
            return 0

    @staticmethod
    def _trend_age(close: pd.Series, ema50: pd.Series, up: bool) -> int:
        """Bars since last EMA50 cross-up (up=True) or cross-down."""
        if close is None or ema50 is None or len(close) < 2 or len(ema50) < 2:
            return 0
        try:
            above = (close > ema50).values
            # Walk backwards from end; count bars that match desired side
            count = 0
            target_above = up  # up=True means want above
            for v in reversed(above):
                if v == target_above:
                    count += 1
                else:
                    break
            return int(count)
        except Exception:
            return 0

    def _multi_tf_alignment(self, ohlcv: pd.DataFrame) -> float:
        """Count (0-3) of bullish-aligned timeframes: daily / weekly / monthly EMA50 trend.
        Daily: close > daily ema50; Weekly: close > weekly ema50; Monthly: close > monthly ema50.
        """
        try:
            if len(ohlcv) < 20:
                return 0.0
            score = 0
            close = ohlcv["Close"]
            # Daily
            if len(close) >= 50:
                d_ema = close.ewm(span=50, adjust=False).mean().iloc[-1]
                if close.iloc[-1] > d_ema:
                    score += 1
            # Weekly (resample to W and ema 10)
            if len(close) >= 50:
                weekly = ohlcv.resample("W").last()["Close"].dropna()
                if len(weekly) >= 10:
                    w_ema = weekly.ewm(span=10, adjust=False).mean().iloc[-1]
                    if weekly.iloc[-1] > w_ema:
                        score += 1
            # Monthly (resample to ME and ema 6)
            if len(close) >= 50:
                monthly = ohlcv.resample("ME").last()["Close"].dropna()
                if len(monthly) >= 6:
                    m_ema = monthly.ewm(span=6, adjust=False).mean().iloc[-1]
                    if monthly.iloc[-1] > m_ema:
                        score += 1
            return float(score)
        except Exception:
            return 0.0

    @staticmethod
    def _daily_vol_pct(close: pd.Series, lookback: int) -> float:
        """20d std-dev of daily log returns (NOT annualized)."""
        if close is None or len(close) < lookback + 1:
            return np.nan
        try:
            log_ret = np.log(close / close.shift(1)).dropna()
            if len(log_ret) < lookback:
                return np.nan
            return float(log_ret.iloc[-lookback:].std())
        except Exception:
            return np.nan

    @staticmethod
    def _vol_ratio(volume: pd.Series, lookback: int) -> float:
        """today_vol / mean(volume[-lookback-1:-1]). Excludes today from baseline."""
        if volume is None or len(volume) < lookback + 1:
            return np.nan
        try:
            today = float(volume.iloc[-1])
            baseline = float(volume.iloc[-lookback - 1:-1].mean())
            if pd.isna(today) or pd.isna(baseline) or baseline <= 0:
                return np.nan
            return today / baseline
        except Exception:
            return np.nan

    @staticmethod
    def _series_mean_excl_last(series: pd.Series, lookback: int) -> float:
        """mean(series[-lookback-1:-1])."""
        if series is None or len(series) < lookback + 1:
            return np.nan
        try:
            return float(series.iloc[-lookback - 1:-1].mean())
        except Exception:
            return np.nan

    @staticmethod
    def _regression_slope_norm(series: pd.Series, lookback: int) -> float:
        """Linear regression slope over last `lookback` bars, normalized by mean.
        Returns slope_per_bar / mean(values_in_window). Per spec B1."""
        if series is None or len(series) < lookback:
            return np.nan
        try:
            vals = series.iloc[-lookback:].values
            if pd.isna(vals).any():
                return np.nan
            x = np.arange(len(vals))
            slope, _intercept = np.polyfit(x, vals, 1)
            mean_val = float(np.mean(vals))
            if mean_val == 0:
                return np.nan
            return float(slope) / mean_val
        except Exception:
            return np.nan

    @staticmethod
    def _accum_dist_signed(ohlcv: pd.DataFrame, lookback: int) -> float:
        """Sum of (close-open)*vol over `lookback` bars, normalized by sum(vol*range)."""
        if len(ohlcv) < lookback:
            return np.nan
        try:
            tail = ohlcv.iloc[-lookback:]
            body_signed = (tail["Close"] - tail["Open"]) * tail["Volume"]
            range_volume = (tail["High"] - tail["Low"]).clip(lower=1e-9) * tail["Volume"]
            num = float(body_signed.sum())
            den = float(range_volume.sum())
            if den == 0:
                return np.nan
            normalized = num / den
            return max(-1.0, min(1.0, normalized))
        except Exception:
            return np.nan

    @staticmethod
    def _obv_slope_norm(ohlcv: pd.DataFrame, lookback: int) -> float:
        """OBV regression slope over `lookback` bars, normalized by mean OBV."""
        if len(ohlcv) < lookback + 1:
            return np.nan
        try:
            close = ohlcv["Close"]; vol = ohlcv["Volume"]
            direction = np.sign(close.diff().fillna(0))
            obv = (direction * vol).cumsum()
            obv_window = obv.iloc[-lookback:].values
            if pd.isna(obv_window).any():
                return np.nan
            x = np.arange(len(obv_window))
            slope, _intercept = np.polyfit(x, obv_window, 1)
            mean_val = float(np.mean(obv_window))
            if mean_val == 0:
                return np.nan
            return float(slope) / abs(mean_val)
        except Exception:
            return np.nan

    @staticmethod
    def _index_return(close: Optional[pd.Series], scan_date: pd.Timestamp,
                       lookback: int) -> float:
        """Index return over `lookback` trading days ending at scan_date."""
        if close is None:
            return np.nan
        try:
            window = close.loc[close.index <= scan_date]
            if len(window) < lookback + 1:
                return np.nan
            cur = float(window.iloc[-1])
            past = float(window.iloc[-lookback - 1])
            if pd.isna(cur) or pd.isna(past) or past == 0:
                return np.nan
            return cur / past - 1
        except Exception:
            return np.nan

    def _compute_nifty_vol_at(self, scan_date: pd.Timestamp, lookback: int) -> float:
        try:
            window = self._nifty_close.loc[self._nifty_close.index <= scan_date]
            if len(window) < lookback + 1:
                return np.nan
            log_ret = np.log(window / window.shift(1))
            return float(log_ret.iloc[-lookback:].std() * math.sqrt(252))
        except Exception:
            return np.nan

    def _nifty_vol_percentile_at(self, scan_date: pd.Timestamp) -> float:
        """Nifty 20d vol's percentile rank vs full 15-yr distribution."""
        try:
            window = self._nifty_close.loc[self._nifty_close.index <= scan_date]
            if len(window) < 21:
                return np.nan
            log_ret = np.log(window / window.shift(1))
            current = float(log_ret.iloc[-20:].std() * math.sqrt(252))
            full_log_ret = np.log(self._nifty_close / self._nifty_close.shift(1))
            full_vol = full_log_ret.rolling(20).std() * math.sqrt(252)
            valid = full_vol.dropna()
            if len(valid) == 0:
                return np.nan
            rank = float((valid <= current).sum()) / len(valid)
            return rank
        except Exception:
            return np.nan

    def _nifty_vol_regime_bucket(self, vol: float) -> str:
        if pd.isna(vol):
            return "Medium"
        if vol < self._vol_thresholds["p30"]:
            return "Low"
        if vol > self._vol_thresholds["p70"]:
            return "High"
        return "Medium"

    @staticmethod
    def _day_of_month_bucket(scan_date: pd.Timestamp) -> str:
        d = scan_date.day
        if d <= 7:
            return "wk1"
        if d <= 14:
            return "wk2"
        if d <= 21:
            return "wk3"
        return "wk4"

    @staticmethod
    def _days_to_monthly_expiry(scan_date: pd.Timestamp) -> int:
        """Days until last Thursday of current month (or next month if past)."""
        try:
            year = scan_date.year; month = scan_date.month
            # Find last Thursday of this month
            last_day = (pd.Timestamp(year=year, month=month, day=1)
                          + pd.offsets.MonthEnd(0)).day
            for day in range(last_day, 0, -1):
                test = pd.Timestamp(year=year, month=month, day=day)
                if test.dayofweek == 3:  # Thursday
                    last_thu = test
                    break
            if scan_date <= last_thu:
                return int((last_thu - scan_date).days)
            # Past expiry; next month's last Thursday
            next_month = scan_date + pd.offsets.MonthBegin(1)
            year = next_month.year; month = next_month.month
            last_day = (pd.Timestamp(year=year, month=month, day=1)
                          + pd.offsets.MonthEnd(0)).day
            for day in range(last_day, 0, -1):
                test = pd.Timestamp(year=year, month=month, day=day)
                if test.dayofweek == 3:
                    last_thu = test
                    break
            return int((last_thu - scan_date).days)
        except Exception:
            return -1

    # ────────────────────────────────────────────────────────────────────
    # 3B helpers — compression / institutional zones
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _range_compression(ohlcv: pd.DataFrame, n: int) -> float:
        """range_compression_Nd = (max(high[-N:]) - min(low[-N:])) / mean(close[-N:])"""
        if len(ohlcv) < n:
            return np.nan
        try:
            tail = ohlcv.iloc[-n:]
            hi = float(tail["High"].max())
            lo = float(tail["Low"].min())
            mc = float(tail["Close"].mean())
            if mc <= 0 or pd.isna(hi) or pd.isna(lo) or pd.isna(mc):
                return np.nan
            return (hi - lo) / mc
        except Exception:
            return np.nan

    @staticmethod
    def _coiled_spring_score(rc20: float, ema_align: str) -> float:
        """Per A3: 0.5*compression + 0.5*trend; 0-100."""
        if rc20 is None or pd.isna(rc20):
            return np.nan
        comp = max(0.0, min(100.0, 100.0 - (rc20 / 0.10) * 100.0))
        if ema_align == "bull":
            trend = 100.0
        elif ema_align == "mixed":
            trend = 50.0
        else:
            trend = 0.0
        return float(comp * 0.5 + trend * 0.5)

    @staticmethod
    def _consolidation_quality(rc20: float, coil_score: float) -> str:
        """Per A4: tight / loose / none."""
        if rc20 is None or pd.isna(rc20) or pd.isna(coil_score):
            return "none"
        if rc20 < 0.05 and coil_score > 67:
            return "tight"
        if rc20 < 0.10:
            return "loose"
        return "none"

    @staticmethod
    def _inside_day_streak(ohlcv: pd.DataFrame) -> int:
        """Count of trailing inside days: today.H ≤ prev.H AND today.L ≥ prev.L."""
        if len(ohlcv) < 2:
            return 0
        try:
            high = ohlcv["High"].values
            low = ohlcv["Low"].values
            count = 0
            for i in range(len(ohlcv) - 1, 0, -1):
                if high[i] <= high[i - 1] and low[i] >= low[i - 1]:
                    count += 1
                else:
                    break
            return int(count)
        except Exception:
            return 0

    def _breakout_strength_atr(self, cache: CachedIndicators,
                                 ohlcv: pd.DataFrame) -> float:
        """B5: if close > nearest_resistance: (close-res)/ATR; else 0."""
        if pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0:
            return np.nan
        # Nearest resistance = most recent pivot high <= today.close (i.e.
        # the resistance level just broken). If close > that pivot, return
        # ATRs above; else 0 (no breakout).
        pivot_highs = cache.pivot_highs
        if not pivot_highs:
            return 0.0
        # Look at pivot highs in last 60 trading days
        cutoff = cache.scan_date - timedelta(days=120)  # ~60 trading days, generous
        recent = [(d, p) for d, p in pivot_highs if d >= cutoff]
        if not recent:
            recent = pivot_highs[-5:]
        # Find the highest pivot high that is <= close (i.e. broken through)
        broken = [p for d, p in recent if p <= cache.close_at_signal]
        if not broken:
            return 0.0
        nearest_res = max(broken)  # closest below close
        return (cache.close_at_signal - nearest_res) / cache.atr_at_signal

    def _consolidation_zone_distance_atr(self, cache: CachedIndicators,
                                            ohlcv: pd.DataFrame) -> float:
        """B6: in last 30 bars, find any bar with range_compression_20d < 0.05.
        If found, base = lowest low in those 30 bars; distance = (close-base)/ATR."""
        if pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0:
            return np.nan
        if len(ohlcv) < 30:
            return np.nan
        s = cache.range_compression_20d_series
        if s is None or len(s) < 30:
            return np.nan
        try:
            tail_rc = s.iloc[-30:]
            qualifies = (tail_rc < 0.05).any()
            if not qualifies:
                return np.nan
            base = float(ohlcv["Low"].iloc[-30:].min())
            return (cache.close_at_signal - base) / cache.atr_at_signal
        except Exception:
            return np.nan

    def _fvg_features(self, cache: CachedIndicators,
                        ohlcv: pd.DataFrame, lookback: int = 60) -> dict:
        """A1: 3-candle FVG detection.
        Bullish FVG: bar[i-2].high < bar[i].low AND gap > 0.25*ATR_at_bar[i-1].
        Bearish FVG: bar[i-2].low > bar[i].high AND gap > 0.25*ATR_at_bar[i-1].
        Filled if any subsequent bar's low ≤ bar[i-2].high (bullish) or
        high ≥ bar[i-2].low (bearish).
        """
        out = {
            "fvg_above_proximity": np.nan,
            "fvg_below_proximity": np.nan,
            "fvg_unfilled_above_count": np.nan,
            "fvg_unfilled_below_count": np.nan,
        }
        if (len(ohlcv) < 3 or cache.atr_series is None
                or pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0):
            return out
        n = len(ohlcv)
        start = max(2, n - lookback)
        high = ohlcv["High"].values
        low = ohlcv["Low"].values
        atrS = cache.atr_series.values
        # Each unfilled FVG: (lower_edge, upper_edge)
        unfilled = []
        for i in range(start, n):
            atr_b2 = atrS[i - 1] if i - 1 < len(atrS) else np.nan
            if pd.isna(atr_b2) or atr_b2 <= 0:
                continue
            # Bullish FVG
            if high[i - 2] < low[i]:
                gap = low[i] - high[i - 2]
                if gap > 0.25 * atr_b2:
                    lower_edge = float(high[i - 2])
                    upper_edge = float(low[i])
                    # Check fill: any bar j>i with low ≤ lower_edge
                    filled = False
                    for j in range(i + 1, n):
                        if low[j] <= lower_edge:
                            filled = True; break
                    if not filled:
                        unfilled.append((lower_edge, upper_edge))
                    continue
            # Bearish FVG
            if low[i - 2] > high[i]:
                gap = low[i - 2] - high[i]
                if gap > 0.25 * atr_b2:
                    lower_edge = float(high[i])
                    upper_edge = float(low[i - 2])
                    filled = False
                    for j in range(i + 1, n):
                        if high[j] >= upper_edge:
                            filled = True; break
                    if not filled:
                        unfilled.append((lower_edge, upper_edge))
        # Classify by side relative to close
        c = cache.close_at_signal
        atr = cache.atr_at_signal
        above_distances = []
        below_distances = []
        for low_e, up_e in unfilled:
            if c < low_e:
                above_distances.append((low_e - c) / atr)
            elif c > up_e:
                below_distances.append((c - up_e) / atr)
            # else zone straddles close = treat as effectively filled; skip
        out["fvg_above_proximity"] = (
            float(min(above_distances)) if above_distances else np.nan)
        out["fvg_below_proximity"] = (
            float(min(below_distances)) if below_distances else np.nan)
        out["fvg_unfilled_above_count"] = int(len(above_distances))
        out["fvg_unfilled_below_count"] = int(len(below_distances))
        return out

    def _ob_features(self, cache: CachedIndicators,
                       ohlcv: pd.DataFrame, lookback: int = 60) -> dict:
        """A2: Order Block detection.
        Bullish OB = last bearish (close<open) candle before 3+ consecutive
        bullish (close>open) bars whose cumulative close-to-close gain > 2×ATR
        (measured at OB candle). Bearish OB = symmetric.
        OB persists until invalidated (subsequent close breaks OB body in
        opposite direction). Proximity = ATRs from close to OB body midpoint.
        """
        out = {"ob_bullish_proximity": np.nan, "ob_bearish_proximity": np.nan}
        if (len(ohlcv) < 5 or cache.atr_series is None
                or pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0):
            return out
        n = len(ohlcv)
        start = max(0, n - lookback)
        op = ohlcv["Open"].values
        cl = ohlcv["Close"].values
        atrS = cache.atr_series.values

        bull_obs = []  # list of (idx, body_mid, body_low, body_high)
        bear_obs = []

        for i in range(start, n - 3):
            # Bullish OB candidate: bar i is bearish; bars i+1..i+3 all bullish
            if cl[i] < op[i]:
                if (cl[i + 1] > op[i + 1] and cl[i + 2] > op[i + 2]
                        and cl[i + 3] > op[i + 3]):
                    cum_gain = cl[i + 3] - cl[i]
                    atr_at_ob = atrS[i] if i < len(atrS) else np.nan
                    if (not pd.isna(atr_at_ob) and atr_at_ob > 0
                            and cum_gain > 2.0 * atr_at_ob):
                        body_low = min(op[i], cl[i])
                        body_high = max(op[i], cl[i])
                        body_mid = (op[i] + cl[i]) / 2.0
                        # Invalidation: any subsequent close < body_low
                        invalidated = False
                        for j in range(i + 4, n):
                            if cl[j] < body_low:
                                invalidated = True; break
                        if not invalidated:
                            bull_obs.append((i, body_mid, body_low, body_high))
            # Bearish OB candidate: bar i is bullish; bars i+1..i+3 all bearish
            if cl[i] > op[i]:
                if (cl[i + 1] < op[i + 1] and cl[i + 2] < op[i + 2]
                        and cl[i + 3] < op[i + 3]):
                    cum_loss = cl[i] - cl[i + 3]
                    atr_at_ob = atrS[i] if i < len(atrS) else np.nan
                    if (not pd.isna(atr_at_ob) and atr_at_ob > 0
                            and cum_loss > 2.0 * atr_at_ob):
                        body_low = min(op[i], cl[i])
                        body_high = max(op[i], cl[i])
                        body_mid = (op[i] + cl[i]) / 2.0
                        # Invalidation: any subsequent close > body_high
                        invalidated = False
                        for j in range(i + 4, n):
                            if cl[j] > body_high:
                                invalidated = True; break
                        if not invalidated:
                            bear_obs.append((i, body_mid, body_low, body_high))

        c = cache.close_at_signal
        atr = cache.atr_at_signal
        if bull_obs:
            # Most recent (highest i) bullish OB
            _, mid, _, _ = max(bull_obs, key=lambda t: t[0])
            out["ob_bullish_proximity"] = abs(c - mid) / atr
        if bear_obs:
            _, mid, _, _ = max(bear_obs, key=lambda t: t[0])
            out["ob_bearish_proximity"] = abs(c - mid) / atr
        return out

    def _pivot_distance_atr(self, cache: CachedIndicators) -> float:
        """ATRs from close to nearest pivot (high or low) by date — most recent."""
        if pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0:
            return np.nan
        all_pivots = []
        if cache.pivot_highs:
            all_pivots.append(cache.pivot_highs[-1])  # most recent high
        if cache.pivot_lows:
            all_pivots.append(cache.pivot_lows[-1])  # most recent low
        if not all_pivots:
            return np.nan
        # Most recent by date
        most_recent = max(all_pivots, key=lambda t: t[0])
        _, price = most_recent
        return abs(cache.close_at_signal - price) / cache.atr_at_signal

    def _prior_swing_distance_pct(self, cache: CachedIndicators,
                                     swing: str, lookback: int = 20) -> float:
        """% to most recent swing (high or low) within last `lookback` trading days."""
        c = cache.close_at_signal
        if c <= 0 or pd.isna(c):
            return np.nan
        pivots = cache.pivot_highs if swing == "high" else cache.pivot_lows
        if not pivots:
            return np.nan
        # Filter to last 20 trading days using ohlcv index
        try:
            ohlcv_index = cache.ohlcv.index
            if len(ohlcv_index) < lookback:
                cutoff_date = ohlcv_index[0]
            else:
                cutoff_date = ohlcv_index[-lookback]
            recent_pivots = [(d, p) for d, p in pivots if d >= cutoff_date]
            if not recent_pivots:
                return np.nan
            # Most recent
            _, price = max(recent_pivots, key=lambda t: t[0])
            return abs(price - c) / c
        except Exception:
            return np.nan

    def _zone_distance_atr(self, cache: CachedIndicators, side: str) -> float:
        """Resistance: ATRs to nearest pivot HIGH above close. Support: nearest
        pivot LOW below close. NaN if no qualifying pivot."""
        if pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0:
            return np.nan
        c = cache.close_at_signal
        if side == "resistance":
            candidates = [p for _, p in cache.pivot_highs if p > c]
            if not candidates:
                return np.nan
            nearest = min(candidates)
            return (nearest - c) / cache.atr_at_signal
        else:  # support
            candidates = [p for _, p in cache.pivot_lows if p < c]
            if not candidates:
                return np.nan
            nearest = max(candidates)
            return (c - nearest) / cache.atr_at_signal

    @staticmethod
    def _round_number_proximity(close: float) -> float:
        """B7: price-scaled round number proximity_pct."""
        if pd.isna(close) or close <= 0:
            return np.nan
        if close <= 100:
            step = 10
        elif close <= 1000:
            step = 100
        elif close <= 10000:
            step = 500
        else:
            step = 1000
        nearest = round(close / step) * step
        return abs(close - nearest) / close

    # ────────────────────────────────────────────────────────────────────
    # 3C-1 helpers — pattern features (triangle / swing / candle flags)
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _pivots_in_window(pivots, window_start_date) -> list:
        """Filter pivot list (date, price) to entries with date >= window_start."""
        return [(d, p) for d, p in pivots if d >= window_start_date]

    @staticmethod
    def _linregress_slope_r2(x_vals, y_vals) -> tuple:
        """Linear regression on (x_vals, y_vals); returns (slope, intercept, r²).
        Returns (nan, nan, 0) if fewer than 2 distinct x or y points."""
        if len(x_vals) < 2 or len(y_vals) < 2:
            return (np.nan, np.nan, 0.0)
        try:
            x_arr = np.asarray(x_vals, dtype=float)
            y_arr = np.asarray(y_vals, dtype=float)
            if np.std(x_arr) == 0 or np.std(y_arr) == 0:
                # Perfectly flat case: slope=0, r² = undefined → treat as 1.0
                # (perfectly linear horizontal fits the points exactly)
                slope = 0.0
                intercept = float(np.mean(y_arr))
                # If y_arr is constant, residuals are 0, so r² = 1
                r_squared = 1.0 if np.std(y_arr) == 0 else 0.0
                return (slope, intercept, r_squared)
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            y_pred = slope * x_arr + intercept
            ss_res = float(np.sum((y_arr - y_pred) ** 2))
            ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            return (float(slope), float(intercept), float(max(0.0, r_squared)))
        except Exception:
            return (np.nan, np.nan, 0.0)

    @staticmethod
    def _count_pivots_within_atr(pivot_xs, pivot_ys, slope, intercept, atr) -> int:
        """Count pivots whose price is within ±atr of regression line."""
        if pd.isna(slope) or pd.isna(intercept) or pd.isna(atr) or atr <= 0:
            return 0
        try:
            count = 0
            for x, y in zip(pivot_xs, pivot_ys):
                line_y = slope * x + intercept
                if abs(y - line_y) <= atr:
                    count += 1
            return int(count)
        except Exception:
            return 0

    def _triangle_features(self, cache: CachedIndicators,
                             ohlcv: pd.DataFrame, lookback: int = 30) -> dict:
        """Compute all 5 triangle features in one pass.

        Returns dict with: quality_ascending, quality_descending,
        compression_pct, touches, age_bars.
        """
        out = {
            "quality_ascending": 0.0,
            "quality_descending": 0.0,
            "compression_pct": np.nan,
            "touches": 0,
            "age_bars": 0,
        }
        if (len(ohlcv) < lookback or pd.isna(cache.atr_at_signal)
                or cache.atr_at_signal <= 0):
            return out

        # Window: last `lookback` bars
        window = ohlcv.iloc[-lookback:]
        window_start = window.index[0]
        # Filter cached pivots to window
        ph_in = self._pivots_in_window(cache.pivot_highs, window_start)
        pl_in = self._pivots_in_window(cache.pivot_lows, window_start)

        # Compression factor (B2, B3) — always computable when window has bars
        high_30d_range = float(window["High"].max() - window["Low"].min())
        current_range = float(window["High"].iloc[-1] - window["Low"].iloc[-1])
        out["compression_pct"] = (
            current_range / high_30d_range
            if high_30d_range > 0 else np.nan)

        if len(ph_in) < 3 or len(pl_in) < 3:
            # Insufficient pivots → quality 0; touches 0; age 0
            return out

        # Convert to (bar_index, price) where bar_index = position within window
        # so regression x-axis is uniform.
        # Use ordinal date offset for numeric x-axis.
        date_to_pos = {d: i for i, d in enumerate(window.index)}
        ph_x = np.array([date_to_pos[d] for d, _ in ph_in], dtype=float)
        ph_y = np.array([p for _, p in ph_in], dtype=float)
        pl_x = np.array([date_to_pos[d] for d, _ in pl_in], dtype=float)
        pl_y = np.array([p for _, p in pl_in], dtype=float)

        high_slope, high_intercept, high_r2 = self._linregress_slope_r2(ph_x, ph_y)
        low_slope, low_intercept, low_r2 = self._linregress_slope_r2(pl_x, pl_y)

        # Slope normalization (B1)
        mean_price = float(window["Close"].mean())
        if mean_price <= 0:
            return out
        high_slope_norm = high_slope / mean_price
        low_slope_norm = low_slope / mean_price

        # Touch counts
        atr = cache.atr_at_signal
        high_touches = self._count_pivots_within_atr(
            ph_x, ph_y, high_slope, high_intercept, atr)
        low_touches = self._count_pivots_within_atr(
            pl_x, pl_y, low_slope, low_intercept, atr)
        touch_count = high_touches + low_touches

        # Compression factor for score: 1 - (current/high_30d_range)
        compression_factor = (
            max(0.0, 1.0 - (current_range / high_30d_range))
            if high_30d_range > 0 else 0.0)

        # Ascending: flat highs, rising lows
        asc_score = 0.0
        if (abs(high_slope_norm) < 0.005 and low_slope_norm > 0.005):
            asc_score = (touch_count * 10.0
                          + low_r2 * 30.0 + high_r2 * 30.0
                          + compression_factor * 30.0)
            asc_score = max(0.0, min(100.0, asc_score))
        out["quality_ascending"] = float(asc_score)

        # Descending: falling highs, flat lows
        desc_score = 0.0
        if (high_slope_norm < -0.005 and abs(low_slope_norm) < 0.005):
            desc_score = (touch_count * 10.0
                            + low_r2 * 30.0 + high_r2 * 30.0
                            + compression_factor * 30.0)
            desc_score = max(0.0, min(100.0, desc_score))
        out["quality_descending"] = float(desc_score)

        # Touches: report total (high + low)
        out["touches"] = int(touch_count)

        # Age: bars since first pivot in window that's part of triangle structure.
        # Heuristic: bars since the earliest pivot_high or pivot_low in window.
        all_pivot_pos = list(ph_x) + list(pl_x)
        if all_pivot_pos:
            earliest_pos = int(min(all_pivot_pos))
            out["age_bars"] = int(lookback - 1 - earliest_pos)

        return out

    def _swing_features(self, cache: CachedIndicators,
                          ohlcv: pd.DataFrame, lookback: int = 20) -> dict:
        """Pivot-based swing features."""
        out = {
            "swing_high_count_20d": 0,
            "swing_low_count_20d": 0,
            "last_swing_high_distance_atr": np.nan,
            "higher_highs_intact_flag": False,
        }
        if len(ohlcv) < 2:
            return out
        # Window: last 20 bars
        n = len(ohlcv)
        if n >= lookback:
            window_start = ohlcv.index[-lookback]
        else:
            window_start = ohlcv.index[0]

        ph_in_20 = [(d, p) for d, p in cache.pivot_highs if d >= window_start]
        pl_in_20 = [(d, p) for d, p in cache.pivot_lows if d >= window_start]
        out["swing_high_count_20d"] = int(len(ph_in_20))
        out["swing_low_count_20d"] = int(len(pl_in_20))

        # last_swing_high_distance_atr — over last 30 bars per spec
        if n >= 30:
            window_30_start = ohlcv.index[-30]
        else:
            window_30_start = ohlcv.index[0]
        ph_in_30 = [(d, p) for d, p in cache.pivot_highs if d >= window_30_start]
        if (ph_in_30 and not pd.isna(cache.atr_at_signal)
                and cache.atr_at_signal > 0):
            # Most recent
            _, recent_price = max(ph_in_30, key=lambda t: t[0])
            out["last_swing_high_distance_atr"] = (
                abs(cache.close_at_signal - recent_price)
                / cache.atr_at_signal)

        # higher_highs_intact_flag — last 3 pivot_highs in chronological order
        if len(cache.pivot_highs) >= 3:
            last3 = cache.pivot_highs[-3:]
            if (last3[0][1] < last3[1][1] < last3[2][1]):
                out["higher_highs_intact_flag"] = True

        return out

    @staticmethod
    def _candle_flag_features(cache: CachedIndicators,
                                ohlcv: pd.DataFrame) -> dict:
        """8 candle pattern flags + gap features."""
        out = {
            "bullish_engulf_flag": False,
            "bearish_engulf_flag": False,
            "hammer_flag": False,
            "shooting_star_flag": False,
            "inside_bar_flag": False,
            "outside_bar_flag": False,
            "gap_up_pct": 0.0,
            "gap_down_pct": 0.0,
        }
        if len(ohlcv) < 2:
            return out

        today = ohlcv.iloc[-1]
        prev = ohlcv.iloc[-2]
        t_o = float(today["Open"]); t_c = float(today["Close"])
        t_h = float(today["High"]); t_l = float(today["Low"])
        p_o = float(prev["Open"]); p_c = float(prev["Close"])
        p_h = float(prev["High"]); p_l = float(prev["Low"])

        # Bullish engulf
        if (t_c > t_o and p_c < p_o
                and t_o <= p_c and t_c >= p_o):
            out["bullish_engulf_flag"] = True

        # Bearish engulf (symmetric)
        if (t_c < t_o and p_c > p_o
                and t_o >= p_c and t_c <= p_o):
            out["bearish_engulf_flag"] = True

        # Hammer: small body, long lower wick, at recent low
        rng = t_h - t_l
        if rng > 0:
            body = abs(t_c - t_o)
            lower_wick = min(t_o, t_c) - t_l
            upper_wick = t_h - max(t_o, t_c)
            body_ratio = body / rng
            lower_wick_ratio = lower_wick / rng
            upper_wick_ratio = upper_wick / rng
            # Recent-low check: today's low <= min(low[-10:])
            lookback = 10 if len(ohlcv) >= 10 else len(ohlcv)
            recent_low = float(ohlcv["Low"].iloc[-lookback:].min())
            at_recent_low = t_l <= recent_low + 1e-12
            if body_ratio < 0.3 and lower_wick_ratio > 0.6 and at_recent_low:
                out["hammer_flag"] = True
            # Shooting star: small body, long upper wick, at recent high
            recent_high = float(ohlcv["High"].iloc[-lookback:].max())
            at_recent_high = t_h >= recent_high - 1e-12
            if body_ratio < 0.3 and upper_wick_ratio > 0.6 and at_recent_high:
                out["shooting_star_flag"] = True

        # Inside bar: today.high < prev.high AND today.low > prev.low (strict)
        if t_h < p_h and t_l > p_l:
            out["inside_bar_flag"] = True

        # Outside bar: today.high > prev.high AND today.low < prev.low (strict)
        if t_h > p_h and t_l < p_l:
            out["outside_bar_flag"] = True

        # Gaps (signed split into up/down)
        if p_c > 0:
            ratio = (t_o - p_c) / p_c
            out["gap_up_pct"] = float(max(0.0, ratio))
            out["gap_down_pct"] = float(max(0.0, -ratio))

        return out

    # ────────────────────────────────────────────────────────────────────
    # 3C-2 helpers — Fib retracement / extension features
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _find_uptrend_impulse(pivot_highs, pivot_lows):
        """Highest pivot high → most recent pivot low AFTER it.
        Returns dict {high, low, end_date, direction} or None."""
        if not pivot_highs or not pivot_lows:
            return None
        highest = max(pivot_highs, key=lambda p: p[1])
        high_date = highest[0]
        lows_after = [p for p in pivot_lows if p[0] > high_date]
        if not lows_after:
            return None
        most_recent_low = max(lows_after, key=lambda p: p[0])
        return {"high": highest[1], "low": most_recent_low[1],
                "end_date": most_recent_low[0], "direction": "up"}

    @staticmethod
    def _find_downtrend_impulse(pivot_highs, pivot_lows):
        """Lowest pivot low → most recent pivot high AFTER it."""
        if not pivot_highs or not pivot_lows:
            return None
        lowest = min(pivot_lows, key=lambda p: p[1])
        low_date = lowest[0]
        highs_after = [p for p in pivot_highs if p[0] > low_date]
        if not highs_after:
            return None
        most_recent_high = max(highs_after, key=lambda p: p[0])
        return {"high": most_recent_high[1], "low": lowest[1],
                "end_date": most_recent_high[0], "direction": "down"}

    def _fib_features(self, cache: CachedIndicators,
                        ohlcv: pd.DataFrame, signal: pd.Series,
                        lookback: int = 30) -> dict:
        """6 Fib proximity features per spec v2.1 + B8 direction selection.

        Feature IDs: retracements use fib_<lvl>_proximity_atr (382/50/618/786);
        extensions use fib_<lvl>_extension_proximity_atr (1272/1618).
        """
        levels = {"382": 0.382, "50": 0.50, "618": 0.618,
                   "786": 0.786, "1272": 1.272, "1618": 1.618}
        # Map level → feature_id; extensions have "_extension_" infix
        feat_id_for = {
            "382": "fib_382_proximity_atr",
            "50": "fib_50_proximity_atr",
            "618": "fib_618_proximity_atr",
            "786": "fib_786_proximity_atr",
            "1272": "fib_1272_extension_proximity_atr",
            "1618": "fib_1618_extension_proximity_atr",
        }
        out = {fid: np.nan for fid in feat_id_for.values()}
        if (pd.isna(cache.atr_at_signal) or cache.atr_at_signal <= 0
                or len(ohlcv) < lookback):
            return out
        # Pivots in last `lookback` bars (using window start date)
        window_start = ohlcv.index[-lookback]
        ph_in = [(d, p) for d, p in cache.pivot_highs if d >= window_start]
        pl_in = [(d, p) for d, p in cache.pivot_lows if d >= window_start]
        if not ph_in or not pl_in:
            return out
        # B8 direction selection
        signal_dir = str(signal.get("direction", "")).upper()
        if signal_dir == "LONG":
            impulse = self._find_uptrend_impulse(ph_in, pl_in)
        elif signal_dir == "SHORT":
            impulse = self._find_downtrend_impulse(ph_in, pl_in)
        else:
            up = self._find_uptrend_impulse(ph_in, pl_in)
            down = self._find_downtrend_impulse(ph_in, pl_in)
            if up and down:
                impulse = up if up["end_date"] > down["end_date"] else down
            else:
                impulse = up or down
        if impulse is None:
            return out
        impulse_high = impulse["high"]
        impulse_low = impulse["low"]
        impulse_range = impulse_high - impulse_low
        if impulse_range <= 0:
            return out
        c = cache.close_at_signal
        atr = cache.atr_at_signal
        for level_name, ratio in levels.items():
            if impulse["direction"] == "up":
                if ratio <= 1.0:
                    fib_price = impulse_high - (ratio * impulse_range)
                else:
                    fib_price = impulse_high + ((ratio - 1.0) * impulse_range)
            else:  # down
                if ratio <= 1.0:
                    fib_price = impulse_low + (ratio * impulse_range)
                else:
                    fib_price = impulse_low - ((ratio - 1.0) * impulse_range)
            out[feat_id_for[level_name]] = abs(c - fib_price) / atr
        return out
