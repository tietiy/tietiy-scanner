"""V2 tradeability gate — raw-state + Group A bypass.

Per output/regime_v2/validation/scheme_comparison_final.md (Scheme B):
a signal is bear-tradeable if the raw classifier state at the signal
date is BEAR/BEAR_RECOVERY, or if the raw state is CHOPPY and the
prior 30-day Nifty return is at or below -9% (Group A capitulation
bypass).

Module is READ-ONLY w.r.t. production. Output goes to
output/regime_v2/v2_tradeability_final.parquet and is consumed only by
the V2 module itself.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd


GROUP_A_RET30_THRESHOLD = -9.0


def classify_tradeability(state_raw: str, ret_30d_prior_pct: Optional[float]) -> dict:
    """Return the 3 output fields for one signal.

    Args:
        state_raw: V2 raw classifier output. One of
            BULL / BULL_RECOVERY / CHOPPY / BEAR_RECOVERY / BEAR (or None).
        ret_30d_prior_pct: Nifty 30-day return ending the bar before the
            signal date. Negative values indicate prior decline; the
            Group A bypass triggers at <= -9%.

    Returns:
        dict with keys v2_bear_tradeable (bool), bypass_path (str),
        tradeability_source (str).
    """
    if state_raw == "BEAR":
        return {
            "v2_bear_tradeable": True,
            "bypass_path": "raw_bear",
            "tradeability_source": "v2_raw_bear",
        }
    if state_raw == "BEAR_RECOVERY":
        return {
            "v2_bear_tradeable": True,
            "bypass_path": "raw_bear_recovery",
            "tradeability_source": "v2_raw_bear",
        }
    if state_raw == "CHOPPY":
        # Group A bypass: deep prior-30d drawdown signals capitulation
        if ret_30d_prior_pct is not None and ret_30d_prior_pct <= GROUP_A_RET30_THRESHOLD:
            return {
                "v2_bear_tradeable": True,
                "bypass_path": "group_a_bypass",
                "tradeability_source": "v2_bypass_deep_crash",
            }
    return {
        "v2_bear_tradeable": False,
        "bypass_path": "none",
        "tradeability_source": "not_tradeable",
    }


def compute_tradeability(
    signals: pd.DataFrame,
    regime_history: pd.DataFrame,
    *,
    date_col: str = "date",
    ret_30d_col: str = "ret_30d_prior_at_signal",
) -> pd.DataFrame:
    """Annotate a signals dataframe with the 5 V2 tradeability fields.

    Args:
        signals: dataframe with at least `date_col` and `ret_30d_col` columns.
        regime_history: dataframe indexed by date with `state_raw` and `state`
            columns. Must cover (or extend past) every signal's date.
        date_col: name of the date column in `signals`.
        ret_30d_col: name of the prior-30d return column in `signals`.

    Returns:
        A new dataframe equal to `signals` with these columns added:
          - regime_v2_raw (str)
          - regime_v2_smooth (str)
          - v2_bear_tradeable (bool)
          - bypass_path (str)
          - tradeability_source (str)
    """
    if signals.empty:
        out = signals.copy()
        for col in ("regime_v2_raw", "regime_v2_smooth", "bypass_path",
                    "tradeability_source"):
            out[col] = pd.Series([], dtype="object")
        out["v2_bear_tradeable"] = pd.Series([], dtype="bool")
        return out

    hist = regime_history.copy()
    hist.index = pd.to_datetime(hist.index).normalize()

    def lookup(ts: pd.Timestamp, col: str) -> Optional[str]:
        if ts in hist.index:
            return hist.loc[ts, col]
        future = hist.loc[hist.index >= ts]
        if len(future) > 0:
            return future.iloc[0][col]
        return None

    out = signals.copy()
    dates = pd.to_datetime(out[date_col]).dt.normalize()
    out["regime_v2_raw"] = dates.apply(lambda t: lookup(t, "state_raw"))
    out["regime_v2_smooth"] = dates.apply(lambda t: lookup(t, "state"))

    results = [
        classify_tradeability(raw, rp)
        for raw, rp in zip(out["regime_v2_raw"], out[ret_30d_col])
    ]
    out["v2_bear_tradeable"] = [r["v2_bear_tradeable"] for r in results]
    out["bypass_path"] = [r["bypass_path"] for r in results]
    out["tradeability_source"] = [r["tradeability_source"] for r in results]
    return out
