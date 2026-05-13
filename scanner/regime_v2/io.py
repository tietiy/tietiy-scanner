"""I/O helpers for regime_v2 module.

Output schema per design §03 "Where each feature gets stored" and §04.

regime_features.jsonl: one JSON object per line, containing
  { "date": "YYYY-MM-DD", "features": {...} }

regime_state.jsonl: one per line,
  { "date": "...", "state": "BEAR_RECOVERY", "regime_pending": null,
    "confidence_pending": 0.0, "gate_trace": [...] }
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

import pandas as pd


def load_ohlcv(path: str) -> pd.DataFrame:
    """Load a parquet or csv OHLCV file. Index must be a DatetimeIndex or
    convertible to one.
    """
    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    elif path.endswith(".csv"):
        df = pd.read_csv(path, parse_dates=True, index_col=0)
    else:
        raise ValueError(f"Unsupported file extension: {path}")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def write_jsonl(record: Dict, path: str) -> None:
    """Append a single JSON object as one line to a JSONL file. Creates the
    parent directory if missing.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=_json_default) + "\n")


def write_regime_features(features: Dict, date: str, out_path: str) -> None:
    write_jsonl({"date": date, "features": features}, out_path)


def write_regime_state(
    state: str,
    date: str,
    *,
    regime_pending: Optional[str] = None,
    confidence_pending: float = 0.0,
    gate_trace: Optional[list] = None,
    out_path: str,
) -> None:
    rec = {
        "date": date,
        "state": state,
        "regime_pending": regime_pending,
        "confidence_pending": confidence_pending,
        "gate_trace": gate_trace or [],
    }
    write_jsonl(rec, out_path)


def _json_default(obj):
    import datetime
    import numpy as np
    if isinstance(obj, (pd.Timestamp, datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        if obj != obj:  # NaN
            return None
        return float(obj)
    return str(obj)
