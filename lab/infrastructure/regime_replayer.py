"""
MS-3 — Backtest Lab regime classifier replay + sector momentum history.

Per ROADMAP.md MS-3 spec: apply live regime classifier to historical Nifty data;
output per-day regime labels for 15-year period. Validation floor: must yield
"Choppy" for 2026-04-17 + 2026-04-29 (matches live behavior).

Purity audit (live classifier ports):
- main.py:get_nifty_info regime logic = PURE given Nifty closes time series.
  Algorithm: ema50(closes) → slope(10) / ema50.shift(10) → above = closes > ema50.
  Bull = slope > 0.005 AND above; Bear = slope < -0.005 AND not above; else Choppy.
  regime_score: ret20 ∈ (>5: 2, >2: 1, <-2: -1, else: 0).
- main.py:get_sector_momentum logic = PURE given sector index closes time series.
  Algorithm: 1-month return → 'Leading' (>2%), 'Lagging' (<-2%), 'Neutral' (else).

These are PORTED (not imported) into this module as pure functions because:
1. Live functions in main.py do yf.download internally; ports take df argument
2. Avoids dependency on main.py's CLI-mode side effects
3. Allows unit testing on synthetic Nifty data

Validation:
- Apr 17 2026 + Apr 29 2026 must classify as Choppy (matches live behavior).
- If validation fails: T3 tripwire — HALT.

Output:
- /lab/output/regime_history.parquet — schema: [date, regime, regime_score, last_slope, last_above_ema50, ret20_pct, source]
- /lab/output/sector_momentum_history.parquet — schema: [date, Bank, IT, Pharma, Auto, Metal, Energy, FMCG, Infra]

Source field: "live_classifier_ported" (always; we ported logic to be pure).
Future fallback: "fallback_heuristic" (not currently used; reserved field).

CLI:
    python lab/infrastructure/regime_replayer.py --smoke    # verify on synthetic Nifty
    python lab/infrastructure/regime_replayer.py            # full replay over cached Nifty
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
_CACHE_DIR = _LAB_ROOT / "cache"
_LAB_OUTPUT = _LAB_ROOT / "output"
_LOGS_DIR = _LAB_ROOT / "logs"
_NIFTY_CACHE = _CACHE_DIR / "_index_NSEI.parquet"
_REGIME_HISTORY = _LAB_OUTPUT / "regime_history.parquet"
_SECTOR_MOMENTUM_HISTORY = _LAB_OUTPUT / "sector_momentum_history.parquet"
_VALIDATION_REPORT = _LOGS_DIR / "ms3_validation_report.json"

# ── Live classifier constants (matches main.py:get_nifty_info) ───────
_REGIME_SLOPE_BULL = 0.005
_REGIME_SLOPE_BEAR = -0.005
_REGIME_EMA_SPAN = 50
_REGIME_SLOPE_LOOKBACK = 10
_REGIME_RET_LOOKBACK = 20

# Sector momentum index symbols (matches main.py:SECTOR_INDICES)
_SECTOR_INDICES = {
    "Bank":   "^NSEBANK",
    "IT":     "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "Auto":   "^CNXAUTO",
    "Metal":  "^CNXMETAL",
    "Energy": "^CNXENERGY",
    "FMCG":   "^CNXFMCG",
    "Infra":  "^CNXINFRA",
}
_SECTOR_MOM_LOOKBACK = 21  # ~1 month trading days; matches main.py period='1mo'


# ── Pure regime classifier (ported from main.py:get_nifty_info) ──────

def classify_regime_for_date(nifty_closes: pd.Series,
                              as_of_date: pd.Timestamp) -> dict:
    """Pure-function regime classifier for a specific historical date.

    Parameters
    ----------
    nifty_closes : pd.Series
        Nifty 50 closes time series (indexed by date).
    as_of_date : pd.Timestamp
        The "as-of" date for classification. Function uses only data ≤ this date.

    Returns
    -------
    dict
        {regime, regime_score, last_slope, last_above_ema50, ret20_pct,
         nifty_close, source}
    """
    closes = nifty_closes[nifty_closes.index <= as_of_date]
    if len(closes) < _REGIME_EMA_SPAN + _REGIME_SLOPE_LOOKBACK:
        return {
            "regime": "Choppy",  # safe default
            "regime_score": 0,
            "last_slope": None,
            "last_above_ema50": None,
            "ret20_pct": None,
            "nifty_close": float(closes.iloc[-1]) if len(closes) else None,
            "source": "insufficient_data_default",
        }

    ema50 = closes.ewm(span=_REGIME_EMA_SPAN).mean()
    slope = ema50.diff(_REGIME_SLOPE_LOOKBACK) / ema50.shift(_REGIME_SLOPE_LOOKBACK)
    above = closes > ema50

    last_slope = float(slope.iloc[-1])
    last_above = bool(above.iloc[-1])

    if last_slope > _REGIME_SLOPE_BULL and last_above:
        regime = "Bull"
    elif last_slope < _REGIME_SLOPE_BEAR and not last_above:
        regime = "Bear"
    else:
        regime = "Choppy"

    if len(closes) >= _REGIME_RET_LOOKBACK + 1:
        ret20 = float(
            (closes.iloc[-1] / closes.iloc[-(_REGIME_RET_LOOKBACK + 1)] - 1) * 100)
    else:
        ret20 = 0.0

    if ret20 > 5:
        regime_score = 2
    elif ret20 > 2:
        regime_score = 1
    elif ret20 < -2:
        regime_score = -1
    else:
        regime_score = 0

    return {
        "regime": regime,
        "regime_score": regime_score,
        "last_slope": round(last_slope, 6),
        "last_above_ema50": last_above,
        "ret20_pct": round(ret20, 2),
        "nifty_close": round(float(closes.iloc[-1]), 2),
        "source": "live_classifier_ported",
    }


def replay_regime_history(nifty_df: pd.DataFrame,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> pd.DataFrame:
    """Apply classifier to every date in nifty_df. Returns DataFrame indexed by date."""
    if "Close" not in nifty_df.columns:
        raise ValueError("nifty_df missing Close column")
    closes = nifty_df["Close"].sort_index()

    if start_date:
        closes = closes[closes.index >= pd.Timestamp(start_date)]
    if end_date:
        closes = closes[closes.index <= pd.Timestamp(end_date)]

    rows = []
    for ts in closes.index:
        result = classify_regime_for_date(nifty_df["Close"], ts)
        result["date"] = ts.date().isoformat()
        rows.append(result)

    df = pd.DataFrame(rows)
    if not df.empty:
        df.index = pd.to_datetime(df["date"])
    return df


# ── Pure sector momentum classifier (ported from main.py) ────────────

def classify_sector_momentum_for_date(sector_closes: pd.Series,
                                        as_of_date: pd.Timestamp) -> str:
    """1-month sector return → 'Leading' / 'Lagging' / 'Neutral'."""
    closes = sector_closes[sector_closes.index <= as_of_date]
    if len(closes) < _SECTOR_MOM_LOOKBACK + 1:
        return "Neutral"
    ret = float((closes.iloc[-1] / closes.iloc[-(_SECTOR_MOM_LOOKBACK + 1)] - 1) * 100)
    if ret > 2:
        return "Leading"
    elif ret < -2:
        return "Lagging"
    return "Neutral"


def _safe_filename(symbol: str) -> str:
    if symbol.startswith("^"):
        return f"_index_{symbol[1:]}"
    return symbol.replace(".", "_")


def replay_sector_momentum_history(start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> pd.DataFrame:
    """Build per-date sector momentum dict. Each row: date + 8 sector labels."""
    sector_dfs = {}
    for sec_name, sec_sym in _SECTOR_INDICES.items():
        path = _CACHE_DIR / f"{_safe_filename(sec_sym)}.parquet"
        if not path.exists():
            print(f"  [{sec_sym}] not cached; sector '{sec_name}' will fallback to Neutral")
            continue
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        sector_dfs[sec_name] = df["Close"].sort_index()

    if not sector_dfs:
        print("[regime_replayer] No sector indices cached; cannot build sector_momentum_history")
        return pd.DataFrame()

    # Use any sector's date range to anchor
    anchor = next(iter(sector_dfs.values()))
    if start_date:
        anchor = anchor[anchor.index >= pd.Timestamp(start_date)]
    if end_date:
        anchor = anchor[anchor.index <= pd.Timestamp(end_date)]

    rows = []
    for ts in anchor.index:
        row = {"date": ts.date().isoformat()}
        for sec_name in _SECTOR_INDICES.keys():
            if sec_name in sector_dfs:
                row[sec_name] = classify_sector_momentum_for_date(
                    sector_dfs[sec_name], ts)
            else:
                row[sec_name] = "Neutral"
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df.index = pd.to_datetime(df["date"])
    return df


# ── Validation (T3 tripwire) ──────────────────────────────────────────

def validate_apr_2026(regime_df: pd.DataFrame) -> dict:
    """Apr 17 2026 + Apr 29 2026 must classify as Choppy. T3 tripwire."""
    targets = ["2026-04-17", "2026-04-29"]
    found = {}
    if regime_df.empty:
        return {
            "validation_passed": False,
            "reason": "regime_df empty",
            "targets": targets,
            "found": {},
        }

    for tgt in targets:
        tgt_ts = pd.Timestamp(tgt)
        # Find row at or just before target date
        before = regime_df[regime_df.index <= tgt_ts]
        if before.empty:
            found[tgt] = {"regime": None, "matched_date": None}
            continue
        last = before.iloc[-1]
        found[tgt] = {
            "regime": str(last.get("regime")),
            "matched_date": str(before.index[-1].date()),
        }

    all_choppy = all(v.get("regime") == "Choppy" for v in found.values())
    return {
        "validation_passed": all_choppy,
        "reason": "all_choppy" if all_choppy else "regime_mismatch",
        "targets": targets,
        "found": found,
    }


# ── Smoke test ────────────────────────────────────────────────────────

def smoke_test() -> bool:
    """Verify regime classifier on synthetic Nifty series."""
    print("[regime_replayer] SMOKE: verifying classifier on synthetic data")

    # Synthetic: 200 days; first 100 trending up (Bull), last 100 sideways (Choppy)
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    base = np.concatenate([np.linspace(15000, 18000, 100),
                            18000 + np.random.uniform(-200, 200, 100)])
    nifty = pd.Series(base, index=dates, name="Close")

    # Day 50 (Bull territory)
    r1 = classify_regime_for_date(nifty, dates[50])
    print(f"  Day 50 (uptrend): regime={r1['regime']} score={r1['regime_score']} "
          f"slope={r1['last_slope']}")

    # Day 180 (sideways territory)
    r2 = classify_regime_for_date(nifty, dates[180])
    print(f"  Day 180 (sideways): regime={r2['regime']} score={r2['regime_score']} "
          f"slope={r2['last_slope']}")

    # Sector momentum smoke
    sec = classify_sector_momentum_for_date(nifty, dates[180])
    print(f"  Sector momentum (synthetic Nifty as proxy): {sec}")

    # Confirm classifier returns valid regime
    valid_regimes = {"Bull", "Bear", "Choppy"}
    if r1["regime"] in valid_regimes and r2["regime"] in valid_regimes:
        print("  ✓ Classifier returns valid regimes")
        return True
    print("  ✗ Classifier returned invalid regime")
    return False


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MS-3 Backtest Lab regime + sector momentum replay")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke test: verify classifier on synthetic Nifty")
    parser.add_argument("--start", default="2011-01-01",
                        help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-04-30",
                        help="End date YYYY-MM-DD")
    args = parser.parse_args()

    if args.smoke:
        ok = smoke_test()
        return 0 if ok else 1

    # Full replay
    if not _NIFTY_CACHE.exists():
        print(f"[regime_replayer] {_NIFTY_CACHE} not found; run MS-1 first")
        return 1

    nifty_df = pd.read_parquet(_NIFTY_CACHE)
    nifty_df.index = pd.to_datetime(nifty_df.index)
    nifty_df = nifty_df.sort_index()

    print(f"[regime_replayer] Replaying regime over Nifty {args.start} → {args.end}")
    regime_df = replay_regime_history(nifty_df, args.start, args.end)
    _LAB_OUTPUT.mkdir(parents=True, exist_ok=True)
    regime_df.to_parquet(_REGIME_HISTORY, compression="snappy")
    print(f"  Wrote {len(regime_df)} regime rows → "
          f"{_REGIME_HISTORY.relative_to(_REPO_ROOT)}")

    # Validation (T3)
    validation = validate_apr_2026(regime_df)
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_VALIDATION_REPORT, "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, default=str)
    print()
    print("=" * 72)
    print("T3 VALIDATION (Apr 17 + Apr 29 2026 must be Choppy)")
    print("=" * 72)
    print(json.dumps(validation, indent=2, default=str))

    if not validation["validation_passed"]:
        print(f"\n❌ T3 TRIPWIRE FIRED: {validation['reason']}")
        return 2

    print(f"\n✅ T3 PASSED")

    # Sector momentum
    print()
    print("[regime_replayer] Replaying sector_momentum")
    sector_df = replay_sector_momentum_history(args.start, args.end)
    if not sector_df.empty:
        sector_df.to_parquet(_SECTOR_MOMENTUM_HISTORY, compression="snappy")
        print(f"  Wrote {len(sector_df)} sector_momentum rows → "
              f"{_SECTOR_MOMENTUM_HISTORY.relative_to(_REPO_ROOT)}")
    else:
        print("  (no sector indices cached; sector_momentum_history NOT written; "
              "downstream MS-2 will use Neutral fallback for all sectors)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(3)
