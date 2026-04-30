"""
INV-012 — BTST signal discovery (4 detectors × 3 hold variants = 12 cells).

Per pre-registered hypothesis (patterns.json INV-012): end-of-day patterns may
predict next-day open or next-day close strength. Tests 4 candidate BTST
detectors with 3 hold variants each.

Detectors (all LONG):
  1. BTST_LAST_30MIN_STRENGTH:
     - close_pos_in_range >= 0.75 (top 25% of today's range)
     - today_close > prior_5d_high
     - today_volume > 1.5 × prior_20d_avg_volume

  2. BTST_SECTOR_LEADER_ROTATION:
     - stock's sector momentum today = "Leading"
     - 5-days-ago momentum was "Lagging" or "Neutral"
     - close_pos_in_range >= 0.70

  3. BTST_POST_PULLBACK_RESUMPTION:
     - UP_TRI signal in past 5 days resolved as DAY6_WIN or TARGET_HIT
     - subsequent pullback 3-5% from highest close in window
     - today_close > prior_3d_high (resumption)

  4. BTST_INSIDE_DAY_BREAKOUT:
     - today_high <= prev_high AND today_low >= prev_low (inside day)
     - Signal fires on inside-day T; entry at T close; outcomes computed via
       HOLD variants (gap-up next day shows in HOLD_OPEN pnl)

Hold variants (entry = signal-day close, LONG):
  HOLD_OPEN:  exit at next-day open (T+1)
  HOLD_CLOSE: exit at next-day close (T+1)
  HOLD_D2:    exit at T+2 close

Stop logic: stop_price = entry × 0.97 (3% below; tighter than swing for shorter hold).
Stop hit if any low ≤ stop_price during hold window → exit at stop_price.

Outcome: pnl_pct = (exit - entry) / entry × 100; W/L/F at ±0.5%.

Pipeline:
  1. Load 188 stock parquets; build features per stock
  2. Load sector_momentum, regime, UP_TRI W history (for Detector 3)
  3. Run all 4 detectors per stock
  4. Compute 3 hold variants per signal
  5. Aggregate by (detector × hold) → 12 cells; lifetime + tier eval
  6. Sub-cohort breakdown for cells with n ≥ 200
  7. UP_TRI baseline comparison
  8. Write findings.md (7 sections)

Direction handling: all BTST signals LONG (no SHORT semantics needed).
hypothesis_tester used exclusively for tier evaluation.

NO promotion calls; findings.md is data-only.
"""
from __future__ import annotations

import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup + imports ──────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from hypothesis_tester import (  # noqa: E402
    compute_cohort_stats,
    evaluate_hypothesis,
    wilson_lower_bound_95,
    binomial_p_value_vs_50,
)

# ── Constants ─────────────────────────────────────────────────────────

_CACHE_DIR = _LAB_ROOT / "cache"
_REGIME_PATH = _LAB_ROOT / "output" / "regime_history.parquet"
_SECTOR_MOM_PATH = _LAB_ROOT / "output" / "sector_momentum_history.parquet"
_UNIVERSE_CSV = _REPO_ROOT / "data" / "fno_universe.csv"
_BASELINE_SIGNALS = _LAB_ROOT / "output" / "backtest_signals.parquet"
_OUTPUT_PARQUET = _LAB_ROOT / "output" / "backtest_signals_INV012.parquet"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-012_findings.md"

# Detector thresholds
_D1_CLOSE_POS_MIN = 0.75
_D1_VOL_MULTIPLE = 1.5
_D1_VOL_LOOKBACK = 20
_D1_BREAKOUT_LOOKBACK = 5

_D2_CLOSE_POS_MIN = 0.70
_D2_MOMENTUM_LOOKBACK = 5

_D3_UP_TRI_LOOKBACK = 5
_D3_PULLBACK_MIN = 0.03
_D3_PULLBACK_MAX = 0.05
_D3_RESUMPTION_LOOKBACK = 3

_MIN_HISTORY_BARS = 25  # need rolling features

# Outcome computation
_BTST_STOP_PCT = 0.03   # 3% below entry
_FLAT_THRESHOLD_PCT = 0.5

# Tier evaluation
_N_MIN_RESOLVED = 30
_N_MIN_SUBCOHORT = 30
_N_MIN_SUBCOHORT_FULL = 200  # threshold for subcohort breakdown per spec

_DETECTORS = [
    "BTST_LAST_30MIN_STRENGTH",
    "BTST_SECTOR_LEADER_ROTATION",
    "BTST_POST_PULLBACK_RESUMPTION",
    "BTST_INSIDE_DAY_BREAKOUT",
]
_HOLD_VARIANTS = ["HOLD_OPEN", "HOLD_CLOSE", "HOLD_D2"]


# ── Helpers ───────────────────────────────────────────────────────────

def _classify_outcome(pnl_pct: float) -> str:
    if pnl_pct > _FLAT_THRESHOLD_PCT:
        return "DAY6_WIN"
    if pnl_pct < -_FLAT_THRESHOLD_PCT:
        return "DAY6_LOSS"
    return "DAY6_FLAT"


def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
    if n1 < 5 or n2 < 5:
        return None
    p1 = w1 / n1; p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _round_pct(x: Optional[float]) -> Optional[float]:
    return round(x * 100, 2) if x is not None else None


# ── Universe + lookups ────────────────────────────────────────────────

def load_sector_lookup() -> dict:
    df = pd.read_csv(_UNIVERSE_CSV)
    return dict(zip(df["symbol"], df["sector"]))


def stock_parquets() -> list[Path]:
    return [p for p in sorted(_CACHE_DIR.glob("*.parquet"))
            if not p.name.startswith("_index_")]


def parquet_to_symbol(p: Path) -> str:
    return p.stem.replace("_NS", ".NS")


def load_regime_lookup() -> pd.Series:
    rdf = pd.read_parquet(_REGIME_PATH)
    rdf["date"] = pd.to_datetime(rdf["date"])
    return rdf.set_index(rdf["date"].dt.strftime("%Y-%m-%d"))["regime"]


def load_sector_momentum_lookup() -> pd.DataFrame:
    if not _SECTOR_MOM_PATH.exists():
        return pd.DataFrame()
    sdf = pd.read_parquet(_SECTOR_MOM_PATH)
    sdf["date"] = pd.to_datetime(sdf["date"])
    return sdf.set_index(sdf["date"].dt.strftime("%Y-%m-%d"))


def load_up_tri_winners() -> dict:
    """Returns dict[symbol] → set of scan_date strings where UP_TRI resolved as W."""
    bdf = pd.read_parquet(_BASELINE_SIGNALS)
    win = bdf[(bdf["signal"] == "UP_TRI")
                & bdf["outcome"].isin(["DAY6_WIN", "TARGET_HIT"])]
    out = {}
    for _, row in win.iterrows():
        sym = row["symbol"]
        out.setdefault(sym, set()).add(row["scan_date"])
    return out


# ── Per-stock detector ───────────────────────────────────────────────

def detect_btst_for_stock(df: pd.DataFrame, symbol: str, sector: Optional[str],
                           sec_mom_df: pd.DataFrame,
                           up_tri_w_dates: set) -> list[dict]:
    """Run all 4 BTST detectors for one stock. Returns list of signal records."""
    if len(df) < _MIN_HISTORY_BARS + 2:
        return []
    df = df.sort_index().copy()
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    if len(df) < _MIN_HISTORY_BARS + 2:
        return []

    # Common features
    df["range"] = df["High"] - df["Low"]
    # close_pos_in_range; if range == 0 set 0.5 (flat day)
    df["close_pos"] = np.where(df["range"] > 0,
                                  (df["Close"] - df["Low"]) / df["range"],
                                  0.5)
    df["prev_close"] = df["Close"].shift(1)
    df["prev_high"] = df["High"].shift(1)
    df["prev_low"] = df["Low"].shift(1)
    df["prior_5d_high"] = df["High"].rolling(_D1_BREAKOUT_LOOKBACK).max().shift(1)
    df["prior_3d_high"] = df["High"].rolling(_D3_RESUMPTION_LOOKBACK).max().shift(1)
    df["prior_20d_avg_vol"] = df["Volume"].rolling(_D1_VOL_LOOKBACK).mean().shift(1)
    df["vol_ratio"] = df["Volume"] / df["prior_20d_avg_vol"]
    # Pullback features for D3: highest close in past 5 days excluding today
    df["prior_5d_max_close"] = df["Close"].rolling(_D3_UP_TRI_LOOKBACK).max().shift(1)

    signals = []

    # ── Detector 1: Last 30-min strength ──
    d1_mask = (
        (df["close_pos"] >= _D1_CLOSE_POS_MIN)
        & (df["Close"] > df["prior_5d_high"])
        & (df["vol_ratio"] > _D1_VOL_MULTIPLE)
    )
    for ts, row in df[d1_mask].iterrows():
        if pd.isna(row["prior_5d_high"]) or pd.isna(row["vol_ratio"]):
            continue
        signals.append({
            "detector_id": "BTST_LAST_30MIN_STRENGTH",
            "scan_date": ts.strftime("%Y-%m-%d"),
            "symbol": symbol, "sector": sector or "Unknown",
            "entry_close": float(row["Close"]),
            "today_high": float(row["High"]),
            "today_low": float(row["Low"]),
            "close_pos": round(float(row["close_pos"]), 4),
            "vol_ratio": round(float(row["vol_ratio"]), 4),
        })

    # ── Detector 2: Sector leader rotation ──
    if sector and not sec_mom_df.empty and sector in sec_mom_df.columns:
        # Vectorize: get today_state and 5-days-ago state per date
        date_strs = df.index.strftime("%Y-%m-%d")
        today_state = pd.Series(
            [sec_mom_df.loc[d, sector] if d in sec_mom_df.index else None
             for d in date_strs],
            index=df.index)
        # 5-trading-days-ago state
        ago_state = today_state.shift(_D2_MOMENTUM_LOOKBACK)
        d2_mask = (
            (today_state == "Leading")
            & (ago_state.isin(["Lagging", "Neutral"]))
            & (df["close_pos"] >= _D2_CLOSE_POS_MIN)
        )
        for ts, row in df[d2_mask].iterrows():
            if pd.isna(row["close_pos"]):
                continue
            signals.append({
                "detector_id": "BTST_SECTOR_LEADER_ROTATION",
                "scan_date": ts.strftime("%Y-%m-%d"),
                "symbol": symbol, "sector": sector,
                "entry_close": float(row["Close"]),
                "today_high": float(row["High"]),
                "today_low": float(row["Low"]),
                "close_pos": round(float(row["close_pos"]), 4),
                "today_momentum": "Leading",
                "ago_momentum": str(ago_state.loc[ts]),
            })

    # ── Detector 3: Post-pullback resumption ──
    if up_tri_w_dates:
        # For each row: check if any up_tri W date in [T-5, T-1]
        for ts, row in df.iterrows():
            today_str = ts.strftime("%Y-%m-%d")
            # Lookback window dates (T-5 to T-1 trading days)
            try:
                idx = df.index.get_loc(ts)
            except KeyError:
                continue
            if idx < _D3_UP_TRI_LOOKBACK + 1:
                continue
            window_dates = set(df.index[idx - _D3_UP_TRI_LOOKBACK:idx]
                                  .strftime("%Y-%m-%d"))
            if not (window_dates & up_tri_w_dates):
                continue
            # Pullback check
            if pd.isna(row["prior_5d_max_close"]) or pd.isna(row["prev_close"]):
                continue
            highest = float(row["prior_5d_max_close"])
            if highest <= 0:
                continue
            pre_today_close = float(row["prev_close"])
            pullback_pct = (highest - pre_today_close) / highest
            if not (_D3_PULLBACK_MIN <= pullback_pct <= _D3_PULLBACK_MAX):
                continue
            # Resumption check
            if pd.isna(row["prior_3d_high"]):
                continue
            if float(row["Close"]) <= float(row["prior_3d_high"]):
                continue
            signals.append({
                "detector_id": "BTST_POST_PULLBACK_RESUMPTION",
                "scan_date": today_str,
                "symbol": symbol, "sector": sector or "Unknown",
                "entry_close": float(row["Close"]),
                "today_high": float(row["High"]),
                "today_low": float(row["Low"]),
                "pullback_pct": round(pullback_pct, 4),
            })

    # ── Detector 4: Inside-day breakout (signal fires on inside day; outcome
    #    via HOLD variants captures gap-up confirmation) ──
    d4_mask = (
        (df["High"] <= df["prev_high"])
        & (df["Low"] >= df["prev_low"])
        & df["prev_high"].notna()
    )
    for ts, row in df[d4_mask].iterrows():
        signals.append({
            "detector_id": "BTST_INSIDE_DAY_BREAKOUT",
            "scan_date": ts.strftime("%Y-%m-%d"),
            "symbol": symbol, "sector": sector or "Unknown",
            "entry_close": float(row["Close"]),
            "today_high": float(row["High"]),
            "today_low": float(row["Low"]),
            "prev_high": float(row["prev_high"]),
            "prev_low": float(row["prev_low"]),
        })

    return signals


# ── Outcome computation per hold variant ─────────────────────────────

def compute_hold_outcomes(stock_df: pd.DataFrame, scan_date: str,
                            entry_close: float) -> dict:
    """Compute outcomes for 3 hold variants: HOLD_OPEN (T+1 open), HOLD_CLOSE
    (T+1 close), HOLD_D2 (T+2 close). LONG semantics. 3% stop below entry."""
    scan_ts = pd.Timestamp(scan_date)
    post = stock_df[stock_df.index > scan_ts]
    stop_price = entry_close * (1 - _BTST_STOP_PCT)

    out = {}
    # HOLD_OPEN — needs ≥1 forward bar
    if len(post) < 1:
        out["HOLD_OPEN_pnl"] = None
        out["HOLD_OPEN_outcome"] = "OPEN"
    else:
        t1_row = post.iloc[0]
        t1_open = float(t1_row["Open"]) if not pd.isna(t1_row["Open"]) else None
        # Stop check on T+1: any low ≤ stop before open? Open is the first price
        # of the day so HOLD_OPEN exit is the open itself. Stop hit only checked
        # for HOLD_CLOSE / HOLD_D2 (intra-day windows).
        if t1_open is None:
            out["HOLD_OPEN_pnl"] = None
            out["HOLD_OPEN_outcome"] = "OPEN"
        else:
            # If T+1 open < stop_price, treat as STOP_HIT (gap-down through stop)
            if t1_open <= stop_price:
                pnl = (stop_price - entry_close) / entry_close * 100
                out["HOLD_OPEN_pnl"] = round(pnl, 4)
                out["HOLD_OPEN_outcome"] = "STOP_HIT"
            else:
                pnl = (t1_open - entry_close) / entry_close * 100
                out["HOLD_OPEN_pnl"] = round(pnl, 4)
                out["HOLD_OPEN_outcome"] = _classify_outcome(pnl)

    # HOLD_CLOSE — needs ≥1 forward bar
    if len(post) < 1:
        out["HOLD_CLOSE_pnl"] = None
        out["HOLD_CLOSE_outcome"] = "OPEN"
    else:
        t1_row = post.iloc[0]
        t1_low = float(t1_row["Low"]) if not pd.isna(t1_row["Low"]) else None
        t1_close = float(t1_row["Close"]) if not pd.isna(t1_row["Close"]) else None
        if t1_close is None:
            out["HOLD_CLOSE_pnl"] = None
            out["HOLD_CLOSE_outcome"] = "OPEN"
        elif t1_low is not None and t1_low <= stop_price:
            pnl = (stop_price - entry_close) / entry_close * 100
            out["HOLD_CLOSE_pnl"] = round(pnl, 4)
            out["HOLD_CLOSE_outcome"] = "STOP_HIT"
        else:
            pnl = (t1_close - entry_close) / entry_close * 100
            out["HOLD_CLOSE_pnl"] = round(pnl, 4)
            out["HOLD_CLOSE_outcome"] = _classify_outcome(pnl)

    # HOLD_D2 — needs ≥2 forward bars
    if len(post) < 2:
        out["HOLD_D2_pnl"] = None
        out["HOLD_D2_outcome"] = "OPEN"
    else:
        # Scan T+1 and T+2 for stop hit
        stop_hit_day = None
        for i in range(2):
            row_i = post.iloc[i]
            low_i = float(row_i["Low"]) if not pd.isna(row_i["Low"]) else None
            if low_i is not None and low_i <= stop_price:
                stop_hit_day = i + 1
                break
        if stop_hit_day is not None:
            pnl = (stop_price - entry_close) / entry_close * 100
            out["HOLD_D2_pnl"] = round(pnl, 4)
            out["HOLD_D2_outcome"] = "STOP_HIT"
        else:
            t2_close = float(post.iloc[1]["Close"]) if not pd.isna(post.iloc[1]["Close"]) else None
            if t2_close is None:
                out["HOLD_D2_pnl"] = None
                out["HOLD_D2_outcome"] = "OPEN"
            else:
                pnl = (t2_close - entry_close) / entry_close * 100
                out["HOLD_D2_pnl"] = round(pnl, 4)
                out["HOLD_D2_outcome"] = _classify_outcome(pnl)
    return out


# ── Main detection + outcome ─────────────────────────────────────────

def detect_and_compute_all(sector_lookup: dict, sec_mom_df: pd.DataFrame,
                            up_tri_winners: dict) -> pd.DataFrame:
    """Run all 4 detectors across universe; compute 3 hold outcomes per signal."""
    parquets = stock_parquets()
    print(f"[INV-012] scanning {len(parquets)} stock parquets…", flush=True)
    all_records = []
    n_skipped = 0
    t0 = time.time()
    for i, p in enumerate(parquets):
        symbol = parquet_to_symbol(p)
        sector = sector_lookup.get(symbol)
        try:
            df = pd.read_parquet(p)
            if not all(c in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]):
                n_skipped += 1; continue
            stock_up_tri_w = up_tri_winners.get(symbol, set())
            sigs = detect_btst_for_stock(df, symbol, sector, sec_mom_df, stock_up_tri_w)
            # Compute hold outcomes for each signal
            df_sorted = df.sort_index()
            for sig in sigs:
                outcomes = compute_hold_outcomes(
                    df_sorted, sig["scan_date"], sig["entry_close"])
                rec = {**sig, **outcomes}
                all_records.append(rec)
        except Exception as e:
            print(f"  skip {p.name}: {e}", flush=True)
            n_skipped += 1
        if (i + 1) % 25 == 0:
            print(f"[INV-012] {i+1}/{len(parquets)} stocks; "
                  f"{len(all_records)} signals so far ({time.time()-t0:.1f}s)",
                  flush=True)
    print(f"[INV-012] detection+outcomes done: {len(all_records)} records, "
          f"{n_skipped} stocks skipped, {time.time()-t0:.1f}s", flush=True)
    return pd.DataFrame(all_records)


def join_regime(signals_df: pd.DataFrame, regime_lookup: pd.Series) -> pd.DataFrame:
    if signals_df.empty:
        return signals_df
    signals_df = signals_df.copy()
    signals_df["regime"] = signals_df["scan_date"].map(regime_lookup)
    return signals_df


# ── Tier evaluation per cell ─────────────────────────────────────────

def evaluate_cell(signals_df: pd.DataFrame, detector: str,
                   hold_variant: str) -> dict:
    """Evaluate one (detector × hold_variant) cell."""
    cell_df = signals_df[signals_df["detector_id"] == detector].copy()
    pnl_col = f"{hold_variant}_pnl"
    out_col = f"{hold_variant}_outcome"
    if pnl_col not in cell_df.columns or len(cell_df) == 0:
        return {
            "detector_id": detector, "hold_variant": hold_variant,
            "n_total": len(cell_df), "tier_eval_status": "NO_DATA",
        }
    # Build a synthetic outcome column for hypothesis_tester
    cell_df["outcome"] = cell_df[out_col]
    cell_df["pnl_pct"] = cell_df[pnl_col]
    n_total = len(cell_df)
    n_open = (cell_df["outcome"] == "OPEN").sum()
    n_resolved_df = cell_df[cell_df["outcome"].isin(
        ["DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT", "STOP_HIT", "TARGET_HIT"])]
    n_win = ((n_resolved_df["outcome"] == "DAY6_WIN")
              | (n_resolved_df["outcome"] == "TARGET_HIT")).sum()
    n_loss = ((n_resolved_df["outcome"] == "DAY6_LOSS")
               | (n_resolved_df["outcome"] == "STOP_HIT")).sum()
    n_flat = (n_resolved_df["outcome"] == "DAY6_FLAT").sum()
    n_excl_flat = int(n_win + n_loss)
    n_resolved = int(n_win + n_loss + n_flat)
    wr = round(n_win / n_excl_flat, 4) if n_excl_flat > 0 else None
    wilson = wilson_lower_bound_95(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
    p_val = binomial_p_value_vs_50(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
    avg_pnl = round(n_resolved_df["pnl_pct"].mean(), 4) if n_resolved > 0 else None
    out = {
        "detector_id": detector, "hold_variant": hold_variant,
        "n_total": int(n_total), "n_resolved": n_resolved,
        "n_excl_flat": n_excl_flat, "n_win": int(n_win),
        "n_loss": int(n_loss), "n_flat": int(n_flat), "n_open": int(n_open),
        "wr_excl_flat": wr, "wilson_lower_95": wilson,
        "p_value_vs_50": p_val, "avg_pnl_pct": avg_pnl,
        "boost_tier": None, "kill_tier": None,
        "boost_train_wr": None, "boost_test_wr": None, "boost_drift_pp": None,
        "kill_train_wr": None, "kill_test_wr": None, "kill_drift_pp": None,
        "tier_eval_status": None,
    }
    if n_excl_flat < _N_MIN_RESOLVED:
        out["tier_eval_status"] = "INSUFFICIENT_N"
        return out
    try:
        boost = evaluate_hypothesis(
            cell_df, cohort_filter={}, hypothesis_type="BOOST")
        out["boost_tier"] = boost["tier"]
        out["boost_train_wr"] = boost["train_stats"]["wr_excl_flat"]
        out["boost_test_wr"] = boost["test_stats"]["wr_excl_flat"]
        out["boost_drift_pp"] = boost["drift_pp"]
        kill = evaluate_hypothesis(
            cell_df, cohort_filter={}, hypothesis_type="KILL")
        out["kill_tier"] = kill["tier"]
        out["kill_train_wr"] = kill["train_stats"]["wr_excl_flat"]
        out["kill_test_wr"] = kill["test_stats"]["wr_excl_flat"]
        out["kill_drift_pp"] = kill["drift_pp"]
        out["tier_eval_status"] = "OK"
    except Exception as e:
        out["tier_eval_status"] = f"ERROR: {e}"
    return out


def evaluate_subcohorts(signals_df: pd.DataFrame, detector: str,
                          hold_variant: str) -> list[dict]:
    """Sector × regime breakdown for a (detector × hold) cell — only if cell n>=200."""
    cell_df = signals_df[signals_df["detector_id"] == detector].copy()
    pnl_col = f"{hold_variant}_pnl"
    out_col = f"{hold_variant}_outcome"
    if len(cell_df) < _N_MIN_SUBCOHORT_FULL or pnl_col not in cell_df.columns:
        return []
    cell_df["outcome"] = cell_df[out_col]
    cell_df["pnl_pct"] = cell_df[pnl_col]
    cells = []
    sectors = sorted(cell_df["sector"].dropna().unique().tolist())
    for sec in sectors:
        for reg in ["Bear", "Choppy", "Bull"]:
            sub = cell_df[(cell_df["sector"] == sec) & (cell_df["regime"] == reg)]
            stats = compute_cohort_stats(sub, cohort_filter={})
            n_ex = stats["n_win"] + stats["n_loss"]
            if n_ex < _N_MIN_SUBCOHORT:
                continue
            entry = {
                "detector_id": detector, "hold_variant": hold_variant,
                "sector": sec, "regime": reg,
                "n_excl_flat": n_ex, "wr_excl_flat": stats["wr_excl_flat"],
                "wilson_lower_95": stats["wilson_lower_95"],
                "boost_tier": None, "kill_tier": None,
            }
            try:
                b = evaluate_hypothesis(sub, cohort_filter={},
                                          hypothesis_type="BOOST")
                k = evaluate_hypothesis(sub, cohort_filter={},
                                          hypothesis_type="KILL")
                entry["boost_tier"] = b["tier"]
                entry["kill_tier"] = k["tier"]
            except Exception:
                pass
            cells.append(entry)
    return cells


# ── UP_TRI baseline ──────────────────────────────────────────────────

def evaluate_up_tri_baseline() -> dict:
    bdf = pd.read_parquet(_BASELINE_SIGNALS)
    up = bdf[bdf["signal"] == "UP_TRI"]
    stats = compute_cohort_stats(up, cohort_filter={})
    return {
        "lifetime": stats,
        "n_excl_flat": stats["n_win"] + stats["n_loss"],
    }


# ── Findings.md writer ────────────────────────────────────────────────

def _ordered_cells() -> list[tuple]:
    return [(d, h) for d in _DETECTORS for h in _HOLD_VARIANTS]


def write_findings_md(signals_df: pd.DataFrame, cells: list[dict],
                       subcohorts_per_cell: dict, baseline_up_tri: dict,
                       output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_total = len(signals_df)
    by_detector = signals_df["detector_id"].value_counts().to_dict()

    with open(output_path, "w") as f:
        f.write("# INV-012 — BTST signal discovery (4 detectors × 3 hold variants)\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write(f"**Detectors tested:** {', '.join(_DETECTORS)}\n\n")
        f.write(f"**Hold variants:** {', '.join(_HOLD_VARIANTS)}\n\n")
        f.write(f"**Total cells:** 12 (4 × 3)\n\n")

        # Caveats
        f.write("---\n\n## ⚠️ Caveats\n\n")
        f.write("**Direction:** all BTST signals are LONG (entry at signal-day close, "
                "exit at next-day open / next-day close / D2 close). Outcome semantics "
                "use LONG D6-style logic adapted for BTST hold periods.\n\n")
        f.write("**Stop logic:** initial stop = entry × 0.97 (3% below; tighter than "
                "swing because shorter hold). Stop hit if any low ≤ stop_price during "
                "hold window. Gap-down through stop on T+1 open treated as STOP_HIT for "
                "HOLD_OPEN variant.\n\n")
        f.write("**FLAT threshold:** ±0.5% pnl_pct (matches signal_replayer convention).\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate)** is INV-012-specific because this "
                "investigation builds detectors directly from cache. Cache miss-rate "
                "(yfinance gaps) may affect detection at margin.\n\n")
        f.write("**Detector 2 sector_momentum coverage:** only 8 sectors have "
                "sector_momentum data (Bank, IT, Pharma, Auto, Metal, Energy, FMCG, "
                "Infra). Stocks in non-indexed sectors (CapGoods, Consumer, Health, "
                "Other, Chem) are skipped for Detector 2.\n\n")
        f.write("**Detector 3 UP_TRI history dependency:** post-pullback resumption "
                "requires a prior UP_TRI W signal; depends on backtest_signals.parquet "
                "outcome integrity (Caveat 2 inheritance).\n\n")
        f.write("**Detector 4 inside-day breakout:** signal fires on inside-day; "
                "gap-up confirmation is embedded in HOLD_OPEN pnl rather than gating "
                "the signal. Pure inside-day breakouts (without next-day gap-up) "
                "produce HOLD_OPEN pnl ≈ 0 or negative.\n\n")

        # ── Section 1 — Methodology ──
        f.write("---\n\n## Section 1 — Methodology\n\n")
        f.write("**Detector 1 — BTST_LAST_30MIN_STRENGTH:** "
                f"close_pos_in_range ≥ {_D1_CLOSE_POS_MIN}; close > prior {_D1_BREAKOUT_LOOKBACK}-day high; "
                f"volume > {_D1_VOL_MULTIPLE}× prior {_D1_VOL_LOOKBACK}-day avg volume.\n\n")
        f.write("**Detector 2 — BTST_SECTOR_LEADER_ROTATION:** "
                f"today's sector_momentum = Leading; {_D2_MOMENTUM_LOOKBACK}-trading-days-ago "
                f"momentum = Lagging or Neutral; close_pos_in_range ≥ {_D2_CLOSE_POS_MIN}.\n\n")
        f.write("**Detector 3 — BTST_POST_PULLBACK_RESUMPTION:** "
                f"UP_TRI W (DAY6_WIN or TARGET_HIT) within past {_D3_UP_TRI_LOOKBACK} days; "
                f"pullback {_D3_PULLBACK_MIN*100}-{_D3_PULLBACK_MAX*100}% from highest close in window; "
                f"today's close > prior {_D3_RESUMPTION_LOOKBACK}-day high.\n\n")
        f.write("**Detector 4 — BTST_INSIDE_DAY_BREAKOUT:** "
                "today's range fully inside yesterday's range "
                "(today_high ≤ prev_high AND today_low ≥ prev_low). "
                "Gap-up confirmation embedded in HOLD_OPEN pnl, not gating the signal.\n\n")
        f.write(f"**Hold variants (entry = signal-day close):**\n")
        f.write(f"- HOLD_OPEN: exit at next-day open (T+1 open)\n")
        f.write(f"- HOLD_CLOSE: exit at next-day close (T+1 close)\n")
        f.write(f"- HOLD_D2: exit at T+2 close\n\n")
        f.write(f"**Stop:** entry × {1 - _BTST_STOP_PCT} (3% below). Stop hit if any low ≤ stop_price during hold.\n\n")

        # ── Section 2 — Detection diagnostics ──
        f.write("---\n\n## Section 2 — Detection diagnostics\n\n")
        f.write(f"**Total signal records:** {n_total} across all 4 detectors\n\n")
        f.write("**Per-detector signal counts:**\n\n")
        f.write("| Detector | n |\n|---|---|\n")
        for d in _DETECTORS:
            f.write(f"| {d} | {by_detector.get(d, 0)} |\n")
        f.write("\n**Distribution by year:**\n\n")
        f.write("| Year | Total | " + " | ".join(_DETECTORS) + " |\n")
        f.write("|---|---|" + "---|" * len(_DETECTORS) + "\n")
        signals_df_yr = signals_df.copy()
        signals_df_yr["year"] = pd.to_datetime(signals_df_yr["scan_date"]).dt.year
        for y in sorted(signals_df_yr["year"].unique()):
            row = signals_df_yr[signals_df_yr["year"] == y]
            counts = row["detector_id"].value_counts().to_dict()
            row_str = f"| {y} | {len(row)} | " + " | ".join(
                str(counts.get(d, 0)) for d in _DETECTORS) + " |\n"
            f.write(row_str)
        f.write("\n**Top 8 sectors by total signal count:**\n\n")
        if "sector" in signals_df.columns:
            top_sectors = signals_df["sector"].value_counts().head(8).to_dict()
            f.write("| Sector | Total |\n|---|---|\n")
            for s, c in top_sectors.items():
                f.write(f"| {s} | {c} |\n")
        f.write("\n")

        # ── Section 3 — Per-cell tier evaluation (12 cells) ──
        f.write("---\n\n## Section 3 — Per-cell lifetime + tier evaluation (12 cells)\n\n")
        f.write("| Detector | Hold | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | "
                "Train_WR | Test_WR | Drift_pp | BoostTier | KillTier |\n")
        f.write("|----------|------|-------------|-----|--------------|-------------|"
                "----------|---------|----------|----------|----------|\n")
        for cell in cells:
            te_status = cell.get("tier_eval_status")
            if te_status == "INSUFFICIENT_N":
                bt = kt = "INSUFFICIENT_N"
                tr_wr = te_wr = drift = "—"
            elif te_status and te_status.startswith("ERROR"):
                bt = kt = "ERROR"
                tr_wr = te_wr = drift = "—"
            elif te_status == "NO_DATA":
                bt = kt = "NO_DATA"
                tr_wr = te_wr = drift = "—"
            else:
                bt = cell.get("boost_tier"); kt = cell.get("kill_tier")
                tr_wr = cell.get("boost_train_wr")
                te_wr = cell.get("boost_test_wr")
                drift = cell.get("boost_drift_pp")
            f.write(f"| {cell['detector_id']} | {cell['hold_variant']} | "
                    f"{cell.get('n_excl_flat', 0)} | {cell.get('wr_excl_flat')} | "
                    f"{cell.get('wilson_lower_95')} | {cell.get('avg_pnl_pct')} | "
                    f"{tr_wr} | {te_wr} | {drift} | {bt} | {kt} |\n")
        f.write("\n")

        # Tier hits summary
        tier_hits = [c for c in cells if c.get("tier_eval_status") == "OK"
                      and (c.get("boost_tier") in ("S", "A", "B")
                           or c.get("kill_tier") in ("S", "A", "B"))]
        f.write(f"**Cells earning Lab tier (S/A/B):** {len(tier_hits)} of 12\n")
        for hit in tier_hits:
            tiers = []
            if hit.get("boost_tier") in ("S", "A", "B"):
                tiers.append(f"BOOST {hit['boost_tier']}")
            if hit.get("kill_tier") in ("S", "A", "B"):
                tiers.append(f"KILL {hit['kill_tier']}")
            f.write(f"- `{hit['detector_id']} × {hit['hold_variant']}` "
                    f"(n={hit['n_excl_flat']}, WR={hit['wr_excl_flat']}) → "
                    f"{', '.join(tiers)}\n")
        f.write("\n")

        # ── Section 4 — Sub-cohort breakdown ──
        f.write("---\n\n## Section 4 — Sub-cohort breakdown (cells with n ≥ 200 only)\n\n")
        any_subcohort = False
        for cell_key, sub_cells in subcohorts_per_cell.items():
            if not sub_cells:
                continue
            any_subcohort = True
            d_id, h_var = cell_key
            f.write(f"### {d_id} × {h_var}\n\n")
            f.write("| Sector | Regime | n_excl_flat | WR | Wilson_lower | "
                    "BoostTier | KillTier |\n")
            f.write("|--------|--------|-------------|-----|--------------|"
                    "----------|----------|\n")
            for sc in sorted(sub_cells, key=lambda x: -(x["wr_excl_flat"] or 0)):
                f.write(f"| {sc['sector']} | {sc['regime']} | {sc['n_excl_flat']} | "
                        f"{sc['wr_excl_flat']} | {sc['wilson_lower_95']} | "
                        f"{sc['boost_tier']} | {sc['kill_tier']} |\n")
            f.write("\n")
            sub_hits = [s for s in sub_cells
                          if s.get("boost_tier") in ("S", "A", "B")
                          or s.get("kill_tier") in ("S", "A", "B")]
            f.write(f"**Sub-cohort tier hits in this cell:** {len(sub_hits)} of {len(sub_cells)}\n\n")
        if not any_subcohort:
            f.write("_No cells reached n ≥ 200 threshold for sub-cohort breakdown._\n\n")

        # ── Section 5 — UP_TRI baseline + cross-detector synthesis ──
        f.write("---\n\n## Section 5 — UP_TRI baseline + cross-detector synthesis\n\n")
        b_lt = baseline_up_tri["lifetime"]
        f.write(f"**UP_TRI baseline (D6 hold):** WR {b_lt['wr_excl_flat']}, "
                f"n_excl_flat {baseline_up_tri['n_excl_flat']}\n\n")
        f.write("**Cross-detector pattern by hold variant:**\n\n")
        f.write("| Detector | HOLD_OPEN WR | HOLD_CLOSE WR | HOLD_D2 WR | Best Hold |\n")
        f.write("|----------|--------------|---------------|-------------|-----------|\n")
        for d in _DETECTORS:
            wrs = {}
            for h in _HOLD_VARIANTS:
                cell = next((c for c in cells
                              if c["detector_id"] == d and c["hold_variant"] == h), {})
                wrs[h] = cell.get("wr_excl_flat")
            valid_wrs = {k: v for k, v in wrs.items() if v is not None}
            best = max(valid_wrs.items(), key=lambda x: x[1])[0] if valid_wrs else "—"
            f.write(f"| {d} | {wrs.get('HOLD_OPEN')} | "
                    f"{wrs.get('HOLD_CLOSE')} | {wrs.get('HOLD_D2')} | {best} |\n")
        f.write("\n")
        # Best cell overall
        valid_cells = [c for c in cells if c.get("wr_excl_flat") is not None
                        and c.get("n_excl_flat", 0) >= _N_MIN_RESOLVED]
        if valid_cells:
            best_cell = max(valid_cells, key=lambda x: x["wr_excl_flat"])
            f.write(f"**Highest-WR cell:** `{best_cell['detector_id']} × "
                    f"{best_cell['hold_variant']}` — WR {best_cell['wr_excl_flat']} "
                    f"(n_excl_flat {best_cell['n_excl_flat']}; "
                    f"BoostTier {best_cell.get('boost_tier')})\n\n")

        # ── Section 6 — Headline ──
        f.write("---\n\n## Section 6 — Headline findings (data only; NO promotion calls)\n\n")
        f.write(f"- **Total signal records:** {n_total} across 4 detectors × 15 years\n")
        f.write(f"- **Cells evaluated:** 12 (4 × 3)\n")
        f.write(f"- **Cells with sufficient n for tier eval:** "
                f"{sum(1 for c in cells if c.get('tier_eval_status') == 'OK')}\n")
        f.write(f"- **Cells with INSUFFICIENT_N:** "
                f"{sum(1 for c in cells if c.get('tier_eval_status') == 'INSUFFICIENT_N')}\n")
        f.write(f"- **Cells earning Tier S/A/B:** {len(tier_hits)} of 12\n")
        f.write(f"- **UP_TRI baseline WR:** {b_lt['wr_excl_flat']} "
                f"(n {baseline_up_tri['n_excl_flat']})\n\n")

        if tier_hits:
            tier_summary = ", ".join(
                f"{h['detector_id'][:30]}×{h['hold_variant']} "
                f"(WR {h['wr_excl_flat']}, n {h['n_excl_flat']})"
                for h in tier_hits[:3])
            headline = (f"INV-012 surfaces {len(tier_hits)} BTST cells earning Lab "
                        f"tier (S/A/B). Top: {tier_summary}. User reviews per-cell "
                        f"tier eligibility + Caveat 2 audit before any scanner integration.")
        else:
            headline = (f"INV-012 finds 0 of 12 BTST cells earning Lab tier (S/A/B). "
                        f"BTST signal candidates do not surface tradeable edge in current "
                        f"universe. Highest cell WR remains below tier B floor.")
        f.write(f"**Headline:** {headline}\n\n")

        # ── Section 7 — Open questions ──
        f.write("---\n\n## Section 7 — Open questions for user review\n\n")
        f.write("1. **BTST viability:** if any cell earns Lab tier, decide whether to "
                "integrate as new BTST signal type in scanner_core.py. Note BTST has "
                "different time horizon than swing signals — may require bridge L1 "
                "PRE_MARKET composer extension to surface BTST entries before market "
                "open + bridge L2 POST_OPEN composer for next-day exits.\n\n")
        f.write("2. **Sub-cohort tier hits (Section 4):** if any (sector × regime) "
                "sub-cohort earns tier even though parent cell REJECT, consider "
                "conditional BTST signal restricted to specific cohorts. n at margin "
                "(30-200) — Caveat 2 audit critical.\n\n")
        f.write("3. **Detector design improvement:** if 0 cells earn tier, BTST may "
                "still work with refined detector logic (different thresholds; "
                "additional filters). User decides whether to register INV-NN follow-up "
                "with refined definitions.\n\n")
        f.write("4. **HOLD variant best practice:** Section 5 cross-detector table "
                "shows which HOLD variant maximizes WR per detector. Consistent "
                "HOLD_OPEN dominance would inform single-config BTST exit; "
                "detector-specific best-hold would require per-detector exit config.\n\n")
        f.write("5. **Caveat 2 audit dependency:** any tier-eligible cell at marginal n "
                "needs Caveat 2 audit before promotion (parallel to INV-003 / INV-010 candidates).\n\n")
        f.write("6. **patterns.json INV-012 status:** PRE_REGISTERED → COMPLETED is "
                "user-only transition.\n\n")

        f.write("---\n\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. "
                "No promotion decisions are made by CC.\n")


# ── Main orchestrator ────────────────────────────────────────────────

def main():
    print(f"[INV-012] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)

    sector_lookup = load_sector_lookup()
    print(f"[INV-012] sector lookup: {len(sector_lookup)} symbols", flush=True)
    regime_lookup = load_regime_lookup()
    sec_mom_df = load_sector_momentum_lookup()
    print(f"[INV-012] regime: {len(regime_lookup)} dates; "
          f"sec_mom: {sec_mom_df.shape if not sec_mom_df.empty else 'empty'}",
          flush=True)
    up_tri_winners = load_up_tri_winners()
    n_w_dates = sum(len(v) for v in up_tri_winners.values())
    print(f"[INV-012] UP_TRI winners: {len(up_tri_winners)} stocks, "
          f"{n_w_dates} W signals total", flush=True)

    signals_df = detect_and_compute_all(sector_lookup, sec_mom_df, up_tri_winners)
    if len(signals_df) == 0:
        raise SystemExit("[INV-012] T5 TRIPWIRE: zero signals across all detectors")

    # Detection diagnostics — check T3/T6 per detector
    by_d = signals_df["detector_id"].value_counts().to_dict()
    print(f"[INV-012] detector counts: {by_d}", flush=True)
    for d in _DETECTORS:
        n = by_d.get(d, 0)
        if n < 200:
            print(f"[INV-012] T3 NOTE: detector {d} n={n} below 200 floor", flush=True)
        if n > 50_000:
            print(f"[INV-012] T6 NOTE: detector {d} n={n} above 50K (may be too lax)", flush=True)

    signals_df = join_regime(signals_df, regime_lookup)

    # Save signals parquet
    print(f"[INV-012] writing {_OUTPUT_PARQUET}…", flush=True)
    signals_df.to_parquet(_OUTPUT_PARQUET)

    # Per-cell tier evaluation
    print(f"[INV-012] tier evaluation (12 cells)…", flush=True)
    cells = []
    for d in _DETECTORS:
        for h in _HOLD_VARIANTS:
            cell = evaluate_cell(signals_df, d, h)
            cells.append(cell)
            print(f"[INV-012]  {d} × {h}: n_excl_flat={cell.get('n_excl_flat')}, "
                  f"WR={cell.get('wr_excl_flat')}, "
                  f"boost={cell.get('boost_tier')}, kill={cell.get('kill_tier')}",
                  flush=True)

    # Sub-cohort breakdown for cells with n ≥ 200
    print(f"[INV-012] sub-cohort breakdown…", flush=True)
    subcohorts_per_cell = {}
    for d in _DETECTORS:
        for h in _HOLD_VARIANTS:
            sub_cells = evaluate_subcohorts(signals_df, d, h)
            if sub_cells:
                subcohorts_per_cell[(d, h)] = sub_cells
    print(f"[INV-012] sub-cohort cells with breakdown: {len(subcohorts_per_cell)}", flush=True)

    print(f"[INV-012] UP_TRI baseline…", flush=True)
    baseline = evaluate_up_tri_baseline()
    print(f"[INV-012] UP_TRI WR: {baseline['lifetime']['wr_excl_flat']} "
          f"(n={baseline['n_excl_flat']})", flush=True)

    print(f"[INV-012] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(signals_df, cells, subcohorts_per_cell, baseline,
                       _OUTPUT_FINDINGS)
    print(f"[INV-012] complete at {datetime.now(timezone.utc).isoformat()}",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-012] FATAL: {e}\n{tb}", flush=True)
        try:
            _OUTPUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
            with open(_OUTPUT_FINDINGS, "w") as f:
                f.write(f"# INV-012 — CRASH at {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write(f"```\n{tb}\n```\n")
        except Exception:
            pass
        raise
