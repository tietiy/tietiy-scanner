"""shadow_ops/regime_classifier.py — Step 2 of shadow_ops v1 daily scan.

Computes regime + sub_regime classification for a single scan_date using the
canonical lab/ pipeline. IMPORTS FeatureExtractor and add_derived_features
from their canonical locations; never duplicates or forks.

ARCHITECTURAL NOTE — REGIME COMPUTATION

`regime` (Bull/Bear/Choppy) is determined by scanner/'s slope/EMA50 classifier
(scanner/main.py:267-317). lab/factory/opus_iteration/_validate_paths.py:
add_derived_features treats regime as a passthrough INPUT — it dispatches on
regime to compute sub_regime but doesn't compute regime itself.

For shadow ops's forward operation we need to produce regime ourselves. We
MIRROR scanner's slope/EMA50 logic in `_classify_regime_slope_ema50` (below)
with explicit verbatim-copy discipline. The cross-validation test
(test_classify_for_known_historical_dates_cross_validation) is the runtime
drift detector — if scanner's classifier changes upstream and this mirror
isn't kept in sync, the cross-validation test FAILS, surfacing the drift.

`sub_regime` (hot/warm/cold for Bear, etc.) is computed by the canonical
add_derived_features call, which IS imported from lab/.

This is the SECOND step of every daily scan workflow per §6.5 (after
data_ingest.py).

FUTURE WORK
Refactor scanner to expose regime classification as a clean importable
function (e.g., scanner/regime_classifier.py:classify_from_close()). Then
shadow_ops can import from canonical scanner location, consistent with the
import-from-canonical pattern used for FeatureExtractor + add_derived_features.
Out of scope for shadow_ops v1; tracked for future cleanup.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

# ============================================================
# Canonical-source imports (DO NOT duplicate this code)
# ============================================================
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
sys.path.insert(0, str(_REPO_ROOT / "lab" / "infrastructure"))
sys.path.insert(0, str(_REPO_ROOT / "lab" / "factory" / "opus_iteration"))

from feature_extractor import FeatureExtractor          # noqa: E402
from feature_loader import FeatureRegistry              # noqa: E402
from _validate_paths import add_derived_features        # noqa: E402


# ============================================================
# Constants
# ============================================================

DEFAULT_CACHE_DIR = _REPO_ROOT / "lab" / "cache"
DEFAULT_NIFTY_PARQUET = DEFAULT_CACHE_DIR / "_index_NSEI.parquet"

SYNTHETIC_SYMBOL = "RELIANCE.NS"
SYNTHETIC_SECTOR = "Other"

# Window used by scanner's get_nifty_info() — matches yfinance period='3mo'
# (~63 trading days). We take the last 90 calendar days from scan_date.
SCANNER_REGIME_WINDOW_DAYS = 90


# ============================================================
# Dataclass
# ============================================================

@dataclass
class RegimeClassification:
    """Output of classify_regime_for_date.

    All fields fully populated on success. On error, classify_regime_for_date
    raises an exception (no silent fallback).
    """
    scan_date: str                          # YYYY-MM-DD
    regime: str                             # 'Bull' | 'Bear' | 'Choppy'
    sub_regime: Optional[str]               # 'hot' | 'warm' | 'cold' for Bear; etc.
    inputs: Dict[str, object]               # 7 fields for tamper-evidence + diagnostics
    features_sha: str                       # SHA-256 hex digest of inputs
    classified_at_utc: str                  # ISO 8601
    nifty_close_latest_date: str            # YYYY-MM-DD (latest date in truncated nifty window)


# ============================================================
# Regime via scanner-mirror slope/EMA50 logic
# ============================================================

def _classify_regime_slope_ema50(nifty_close: pd.Series,
                                  scan_date: pd.Timestamp) -> Dict[str, object]:
    """MIRROR of scanner/main.py:267-317 (get_nifty_info regime block).

    Verbatim logic copy. If scanner's classifier changes, this MUST be updated;
    the cross-validation test will detect drift but not auto-fix it.

    Scanner does:
        df = yf.download(NIFTY_SYMBOL, period='3mo', progress=False, auto_adjust=True)
        closes     = df['Close']
        ema50      = closes.ewm(span=50).mean()
        slope      = ema50.diff(10) / ema50.shift(10)
        above      = closes > ema50
        last_slope = float(slope.iloc[-1])
        last_above = bool(above.iloc[-1])
        if last_slope > 0.005 and last_above: regime = 'Bull'
        elif last_slope < -0.005 and not last_above: regime = 'Bear'
        else: regime = 'Choppy'

    For shadow's forward operation, we read from a longer-history parquet
    (lab/cache/_index_NSEI.parquet) and truncate to the same 3-month-equivalent
    window ending at scan_date.
    """
    # Truncate to scan_date inclusive
    in_range = nifty_close.loc[nifty_close.index <= scan_date]

    # Take last 90 calendar days (~63 trading days, matches scanner's period='3mo')
    cutoff = scan_date - pd.Timedelta(days=SCANNER_REGIME_WINDOW_DAYS)
    closes = in_range.loc[in_range.index >= cutoff]

    if len(closes) < 50:
        raise ValueError(
            f"insufficient nifty close history for ema50: have {len(closes)} rows "
            f"in [{cutoff.date()}, {scan_date.date()}], need >= 50"
        )

    # ── Verbatim mirror of scanner logic from here ──
    ema50 = closes.ewm(span=50).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    above = closes > ema50
    last_slope = float(slope.iloc[-1])
    last_above = bool(above.iloc[-1])

    if last_slope > 0.005 and last_above:
        regime = "Bull"
    elif last_slope < -0.005 and not last_above:
        regime = "Bear"
    else:
        regime = "Choppy"
    # ── End verbatim mirror ──

    return {
        "regime": regime,
        "last_slope": last_slope,
        "last_above_ema50": last_above,
    }


# ============================================================
# Singleton FeatureExtractor (init is expensive; reuse across calls)
# ============================================================

_extractor_instance: Optional[FeatureExtractor] = None
_extractor_cache_dir: Optional[Path] = None


def _get_extractor(cache_dir: Path = DEFAULT_CACHE_DIR) -> FeatureExtractor:
    """Lazy-instantiate FeatureExtractor singleton.

    Init loads 188 stock close parquets + index/sector indices (~3-5s).
    Subsequent calls reuse the same instance. If cache_dir changes between
    calls (rare), reinitialize.
    """
    global _extractor_instance, _extractor_cache_dir
    cache_dir = Path(cache_dir)
    if _extractor_instance is None or _extractor_cache_dir != cache_dir:
        registry = FeatureRegistry.load_all()
        _extractor_instance = FeatureExtractor(registry=registry, cache_dir=cache_dir)
        _extractor_cache_dir = cache_dir
    return _extractor_instance


# ============================================================
# SHA helper
# ============================================================

def _compute_features_sha(inputs: Dict[str, object]) -> str:
    """SHA-256 hex digest of canonical-form JSON of inputs dict.

    Sorted keys, deterministic float repr. Tamper-evident: same inputs always
    produce the same hash; any change (cache shift, feature drift, mirror
    update) produces a different hash.
    """
    # Convert numpy floats / NaN to JSON-compatible form
    canonical = {}
    for k in sorted(inputs.keys()):
        v = inputs[k]
        if isinstance(v, (np.floating, float)):
            if pd.isna(v):
                canonical[k] = None
            else:
                # repr with full precision
                canonical[k] = float(v)
        elif isinstance(v, (np.integer, int)):
            canonical[k] = int(v)
        elif isinstance(v, (np.bool_, bool)):
            canonical[k] = bool(v)
        else:
            canonical[k] = v if v is None else str(v)
    payload = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ============================================================
# Main classification entry
# ============================================================

def classify_regime_for_date(scan_date: date,
                              cache_dir: Path = DEFAULT_CACHE_DIR) -> RegimeClassification:
    """Compute regime + sub_regime for scan_date via canonical lab/ pipeline.

    Pipeline:
      1. Load Nifty close from lab/cache/_index_NSEI.parquet, truncate to scan_date.
      2. Classify regime via scanner-mirror slope/EMA50 logic.
      3. Build synthetic signal_row (RELIANCE.NS, sector='Other', regime=<step 2>).
      4. FeatureExtractor.extract_single() → dict of 114 features.
      5. Build single-row DataFrame with scan_date + regime + feat_* columns.
      6. add_derived_features() → adds sub_regime column.
      7. Construct + return RegimeClassification.

    Raises:
        FileNotFoundError if cache_dir/_index_NSEI.parquet missing.
        ValueError if Nifty data is stale (latest date < scan_date).
        ValueError if Nifty data has insufficient history for EMA50.
    """
    cache_dir = Path(cache_dir)
    nifty_parquet = cache_dir / "_index_NSEI.parquet"
    scan_ts = pd.Timestamp(scan_date)
    scan_date_iso = scan_ts.date().isoformat()

    # --- Step 1: Load Nifty close ---
    if not nifty_parquet.exists():
        raise FileNotFoundError(f"nifty parquet missing: {nifty_parquet}")
    nifty_df = pd.read_parquet(nifty_parquet)
    nifty_df.index = pd.to_datetime(nifty_df.index)
    nifty_close = nifty_df["Close"].sort_index().dropna()

    nifty_latest = nifty_close.index.max()
    if nifty_latest < scan_ts:
        raise ValueError(
            f"nifty close stale: latest={nifty_latest.date().isoformat()}, "
            f"requested={scan_date_iso}"
        )

    # --- Step 2: Classify regime via scanner-mirror ---
    regime_result = _classify_regime_slope_ema50(nifty_close, scan_ts)
    regime = regime_result["regime"]
    last_slope = regime_result["last_slope"]
    last_above_ema50 = regime_result["last_above_ema50"]

    # The latest Nifty date used (truncated to scan_date)
    used_window = nifty_close.loc[nifty_close.index <= scan_ts]
    nifty_used_latest = used_window.index.max().date().isoformat()

    # --- Step 3: Build synthetic signal_row ---
    synthetic_signal = pd.Series({
        "scan_date": scan_date_iso,
        "symbol": SYNTHETIC_SYMBOL,
        "sector": SYNTHETIC_SECTOR,
        "regime": regime,
        "regime_score": 0,
        "sec_mom": "Neutral",
        "rs_q": "Neutral",
    })

    # --- Step 4: Extract features via canonical FeatureExtractor ---
    fx = _get_extractor(cache_dir)
    synthetic_parquet = cache_dir / f"{SYNTHETIC_SYMBOL.replace('.', '_')}.parquet"
    if not synthetic_parquet.exists():
        raise FileNotFoundError(
            f"synthetic-signal symbol parquet missing: {synthetic_parquet}. "
            f"Run shadow_ops/data_ingest.py first."
        )
    stock_history = pd.read_parquet(synthetic_parquet)
    stock_history.index = pd.to_datetime(stock_history.index)
    stock_history = stock_history.sort_index()
    feat_dict = fx.extract_single(synthetic_signal, stock_history)

    # --- Step 5: Build single-row DataFrame for add_derived_features ---
    row = {
        "scan_date": scan_date_iso,
        "symbol": SYNTHETIC_SYMBOL,
        "sector": SYNTHETIC_SECTOR,
        "regime": regime,
        "outcome": None,    # required-ish for outcome_to_won; None → won=None
    }
    for k, v in feat_dict.items():
        row[f"feat_{k}"] = v
    df = pd.DataFrame([row])

    # --- Step 6: add_derived_features → sub_regime ---
    df_derived = add_derived_features(df)
    sub_regime = df_derived["sub_regime"].iloc[0]
    if isinstance(sub_regime, float) and pd.isna(sub_regime):
        sub_regime = None

    # --- Step 7: Build inputs dict + hash ---
    inputs = {
        "feat_nifty_vol_percentile_20d": _to_python_scalar(
            feat_dict.get("nifty_vol_percentile_20d")),
        "feat_nifty_60d_return_pct": _to_python_scalar(
            feat_dict.get("nifty_60d_return_pct")),
        "feat_nifty_200d_return_pct": _to_python_scalar(
            feat_dict.get("nifty_200d_return_pct")),
        "feat_market_breadth_pct": _to_python_scalar(
            feat_dict.get("market_breadth_pct")),
        "last_slope": float(last_slope),
        "last_above_ema50": bool(last_above_ema50),
        "nifty_close_latest_date": nifty_used_latest,
    }
    features_sha = _compute_features_sha(inputs)

    return RegimeClassification(
        scan_date=scan_date_iso,
        regime=regime,
        sub_regime=sub_regime,
        inputs=inputs,
        features_sha=features_sha,
        classified_at_utc=datetime.now(timezone.utc).isoformat(),
        nifty_close_latest_date=nifty_used_latest,
    )


def _to_python_scalar(v):
    """Coerce numpy scalar / NaN to Python types for JSON-friendliness."""
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if isinstance(v, (np.floating,)):
        return None if pd.isna(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    """python -m shadow_ops.regime_classifier [--date YYYY-MM-DD]

    Defaults to today (UTC). Prints RegimeClassification as JSON.
    Exit codes:
      0 — success
      1 — data error (FileNotFoundError, stale data, insufficient history)
      2 — unexpected exception
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="Classify regime + sub_regime for a single scan_date.")
    parser.add_argument("--date", type=str, default=None,
                        help="Scan date (YYYY-MM-DD). Default: today.")
    parser.add_argument("--cache-dir", type=str, default=str(DEFAULT_CACHE_DIR),
                        help="Cache dir containing _index_NSEI.parquet etc.")
    args = parser.parse_args()

    if args.date:
        scan_date = date.fromisoformat(args.date)
    else:
        scan_date = date.today()

    try:
        result = classify_regime_for_date(scan_date, Path(args.cache_dir))
    except (FileNotFoundError, ValueError) as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        return 1
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        return 2

    # Print JSON, dataclass-style
    out = {
        "scan_date": result.scan_date,
        "regime": result.regime,
        "sub_regime": result.sub_regime,
        "inputs": result.inputs,
        "features_sha": result.features_sha,
        "classified_at_utc": result.classified_at_utc,
        "nifty_close_latest_date": result.nifty_close_latest_date,
    }
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
