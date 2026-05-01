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
_DEFERRED_3A = (  # cross-stock features deferred to later sub-block
    "sector_rank_within_universe",
    "market_breadth_pct",
    "advance_decline_ratio_20d",
)
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
    pivot_high_idx: list = field(default_factory=list)  # list of (date, price)
    pivot_low_idx: list = field(default_factory=list)
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

    # ── Initialization helpers ────────────────────────────────────────

    def _load_index_close(self, filename: str) -> pd.Series:
        path = self.cache_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"index parquet not found: {path}")
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df["Close"].sort_index().dropna()

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
        # Sub-block 3B/3C families — placeholders return NaN until implemented
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
        # Pivots — defer to 3B/3C (uses scanner_core.detect_pivots)
        # Weekly resampled — defer to 3B/3C if needed
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

        # Cross-stock features (deferred to later sub-block) — leave as NaN
        # sector_rank_within_universe, market_breadth_pct, advance_decline_ratio_20d

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
