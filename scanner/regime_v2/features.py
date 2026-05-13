"""Feature computation per doc/regime_v2_design/03_input_features.md.

VIX is not in the local dataset; this implementation runs in degraded mode
(per design §04 "VIX missing" edge case). Bull gate requires tighter slope
(>0.008); Bull-Recovery cannot fire.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_features(
    ohlcv: pd.DataFrame,
    *,
    banknifty_ohlcv: Optional[pd.DataFrame] = None,
    vix_series: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Compute the 9 features (F1-F9) per design §03 for every bar in `ohlcv`.

    Returns a DataFrame indexed by date with columns:
        nifty_close, ema20, ema50, ema200,
        above_ema20, above_ema50, above_ema200,
        slope_10d_ema50, ret20_pct, realized_vol_20d_pct,
        india_vix, vix_change_10d_pct,
        banknifty_rs_pp  (optional v2.1)

    Bars where rolling windows aren't filled yield NaN for the affected
    features. Downstream classifier must treat NaN as "Unknown" / Choppy.
    """
    if ohlcv.empty:
        return pd.DataFrame()

    close = ohlcv["Close"].astype(float)

    # F1: nifty_close
    nifty_close = close
    # F2-F3: EMA50 + slope
    ema50 = _ema(close, 50)
    slope_10d = (ema50.diff(10) / ema50.shift(10)).astype(float)
    above_ema50 = (close > ema50).astype(bool)
    # F4: ret20%
    ret20_pct = ((close / close.shift(20)) - 1.0) * 100.0
    # F5: above EMA20
    ema20 = _ema(close, 20)
    above_ema20 = (close > ema20).astype(bool)
    # F6: above EMA200
    ema200 = _ema(close, 200)
    above_ema200 = (close > ema200).astype(bool)
    # F7: realized vol 20d annualized %
    log_ret = np.log(close / close.shift(1))
    realized_vol_20d_pct = log_ret.rolling(20).std() * math.sqrt(252) * 100.0

    feats = pd.DataFrame(
        {
            "nifty_close": nifty_close,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "above_ema20": above_ema20,
            "above_ema50": above_ema50,
            "above_ema200": above_ema200,
            "slope_10d_ema50": slope_10d,
            "ret20_pct": ret20_pct,
            "realized_vol_20d_pct": realized_vol_20d_pct,
        },
        index=ohlcv.index,
    )

    # F8-F9: VIX (optional)
    if vix_series is not None and not vix_series.empty:
        vix_aligned = vix_series.reindex(feats.index, method="ffill")
        feats["india_vix"] = vix_aligned
        feats["vix_change_10d_pct"] = (
            (vix_aligned / vix_aligned.shift(10)) - 1.0
        ) * 100.0
    else:
        feats["india_vix"] = np.nan
        feats["vix_change_10d_pct"] = np.nan

    # F10 (v2.1): Bank Nifty relative strength
    if banknifty_ohlcv is not None and not banknifty_ohlcv.empty:
        bk_close = banknifty_ohlcv["Close"].astype(float)
        bk_ret20 = ((bk_close / bk_close.shift(20)) - 1.0) * 100.0
        bk_aligned = bk_ret20.reindex(feats.index, method="ffill")
        feats["banknifty_rs_pp"] = bk_aligned - feats["ret20_pct"]
    else:
        feats["banknifty_rs_pp"] = np.nan

    return feats


def feature_dict_at(feats: pd.DataFrame, date) -> Dict:
    """Return a plain dict snapshot of features at a given date.

    Date can be string 'YYYY-MM-DD' or pd.Timestamp. Returns empty dict if
    the date isn't in the index.
    """
    if isinstance(date, str):
        date = pd.Timestamp(date)
    try:
        row = feats.loc[date]
    except KeyError:
        return {}
    out = {}
    for col, val in row.items():
        # Convert numpy scalars to python types; preserve NaN
        try:
            if pd.isna(val):
                out[col] = None
                continue
        except (TypeError, ValueError):
            pass
        if isinstance(val, (np.bool_, bool)):
            out[col] = bool(val)
        elif isinstance(val, (np.integer, int)):
            out[col] = int(val)
        elif isinstance(val, (np.floating, float)):
            out[col] = float(val)
        else:
            out[col] = val
    return out
