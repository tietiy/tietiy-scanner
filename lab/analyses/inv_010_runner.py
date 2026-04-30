"""
INV-010 — GAP_BREAKOUT new entry signal discovery.

Per pre-registered hypothesis (patterns.json INV-010): a stock breaking 5-day
high with gap-up open AND prior 10-day consolidation has higher WR than UP_TRI
base case. Mechanism: gap-up confirms institutional pre-market interest;
consolidation prior signals supply absorption; combined → breakout has stronger
conviction than UP_TRI alone.

Signal definition (LONG):
  rule_1_gap_up:        today_open > prev_close × 1.005
  rule_2_breakout:      today_high > 5_day_high (T-5 to T-1 highs)
  rule_3_consolidation: prior_10d_range / prior_10d_avg_close < 0.05
  rule_4_volume:        today_volume > 1.2 × 20_day_avg_volume
  ALL rules required.

Entry/exit (matching scanner conventions):
  entry_close = today's close
  stop_price = entry × 0.95 (5% below)
  target_price = entry × 1.10 (10% above; 2:1 RR)
  Hold period: D6 default
  Direction: LONG; stop_hit if low ≤ stop, target_hit if high ≥ target

Pipeline:
  1. Load 188 stock parquets (skip _index_*); build per-stock rolling features
  2. Detect GAP_BREAKOUT signals; emit per-signal records
  3. Join sector (fno_universe.csv) + regime (regime_history.parquet)
  4. Compute LONG D6 outcomes per signal
  5. Lifetime cohort stats + train/test OOS + hypothesis_tester (BOOST + KILL)
  6. Sector × regime sub-cohort breakdown
  7. UP_TRI baseline comparison
  8. Write findings.md (7 sections)

Outputs:
  - /lab/output/backtest_signals_INV010.parquet (separate from main)
  - /lab/analyses/INV-010_findings.md
  - /lab/logs/inv_010_run.log

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
_OUTPUT_PARQUET = _LAB_ROOT / "output" / "backtest_signals_INV010.parquet"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-010_findings.md"

# Detector thresholds
_GAP_UP_PCT = 0.005       # 0.5% gap-up minimum
_BREAKOUT_LOOKBACK = 5    # 5-day high break
_CONSOLIDATION_LOOKBACK = 10  # 10-day range / avg_close
_CONSOLIDATION_MAX_PCT = 0.05  # 5% max range
_VOLUME_LOOKBACK = 20     # 20-day avg volume
_VOLUME_MULTIPLE = 1.2    # 1.2× avg volume minimum
_MIN_HISTORY_BARS = 21    # need 21 bars before first eligible signal

# Outcome computation
_HOLDING_DAYS = 6
_STOP_PCT = 0.05          # 5% below entry
_TARGET_PCT = 0.10        # 10% above entry (2:1 RR)
_FLAT_THRESHOLD_PCT = 0.5  # ±0.5% per signal_replayer convention

# Tier evaluation
_TRAIN_END = "2022-12-31"
_TEST_START = "2023-01-01"
_N_MIN_RESOLVED = 30      # below → INSUFFICIENT_N
_N_MIN_SUBCOHORT = 30


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
    p1 = w1 / n1
    p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _round_pct(x: Optional[float]) -> Optional[float]:
    return round(x * 100, 2) if x is not None else None


# ── Universe + sector lookup ──────────────────────────────────────────

def load_sector_lookup() -> dict:
    """Returns dict[symbol_with_NS] → sector."""
    df = pd.read_csv(_UNIVERSE_CSV)
    return dict(zip(df["symbol"], df["sector"]))


def stock_parquets() -> list[Path]:
    """Stock parquets only (exclude _index_*)."""
    return [p for p in sorted(_CACHE_DIR.glob("*.parquet"))
            if not p.name.startswith("_index_")]


def parquet_to_symbol(p: Path) -> str:
    """e.g. HDFCBANK_NS.parquet → HDFCBANK.NS"""
    return p.stem.replace("_NS", ".NS")


# ── Per-stock detector ───────────────────────────────────────────────

def detect_gap_breakouts_for_stock(df: pd.DataFrame, symbol: str,
                                    sector: str) -> list[dict]:
    """Detect GAP_BREAKOUT signals for one stock. Returns list of signal dicts."""
    if len(df) < _MIN_HISTORY_BARS + 2:
        return []
    df = df.sort_index().copy()
    # Drop rows with NaN in required cols (e.g., last row Apr 29 NaN Close)
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    if len(df) < _MIN_HISTORY_BARS + 2:
        return []

    # Rolling features (computed on prior bars only — exclude today via shift)
    df["prev_close"] = df["Close"].shift(1)
    # 5-day high of T-5 to T-1 (exclusive of today)
    df["prior_5d_high"] = df["High"].rolling(_BREAKOUT_LOOKBACK).max().shift(1)
    # 10-day range/avg of T-11 to T-1 (exclusive of today)
    prior10_high = df["High"].rolling(_CONSOLIDATION_LOOKBACK).max().shift(1)
    prior10_low = df["Low"].rolling(_CONSOLIDATION_LOOKBACK).min().shift(1)
    prior10_avg_close = df["Close"].rolling(_CONSOLIDATION_LOOKBACK).mean().shift(1)
    df["prior_10d_range"] = prior10_high - prior10_low
    df["prior_10d_avg_close"] = prior10_avg_close
    df["consolidation_pct"] = df["prior_10d_range"] / df["prior_10d_avg_close"]
    # 20-day avg volume of T-20 to T-1 (exclusive of today)
    df["prior_20d_avg_vol"] = df["Volume"].rolling(_VOLUME_LOOKBACK).mean().shift(1)
    df["vol_ratio"] = df["Volume"] / df["prior_20d_avg_vol"]
    df["gap_pct"] = (df["Open"] - df["prev_close"]) / df["prev_close"]

    # Rule masks
    rule_1 = df["Open"] > df["prev_close"] * (1 + _GAP_UP_PCT)
    rule_2 = df["High"] > df["prior_5d_high"]
    rule_3 = df["consolidation_pct"] < _CONSOLIDATION_MAX_PCT
    rule_4 = df["vol_ratio"] > _VOLUME_MULTIPLE
    all_rules = rule_1 & rule_2 & rule_3 & rule_4

    signals = []
    for ts, row in df[all_rules].iterrows():
        if pd.isna(row["consolidation_pct"]) or pd.isna(row["vol_ratio"]):
            continue
        signals.append({
            "scan_date": ts.strftime("%Y-%m-%d"),
            "symbol": symbol,
            "sector": sector,
            "signal": "GAP_BREAKOUT",
            "direction": "LONG",
            "entry_close": float(row["Close"]),
            "stop_price": round(float(row["Close"]) * (1 - _STOP_PCT), 4),
            "target_price": round(float(row["Close"]) * (1 + _TARGET_PCT), 4),
            "prev_close": float(row["prev_close"]),
            "today_open": float(row["Open"]),
            "today_high": float(row["High"]),
            "today_volume": float(row["Volume"]),
            "gap_pct": round(float(row["gap_pct"]), 4),
            "prior_5d_high": float(row["prior_5d_high"]),
            "consolidation_pct": round(float(row["consolidation_pct"]), 4),
            "vol_ratio": round(float(row["vol_ratio"]), 4),
        })
    return signals


# ── Outcome computation (LONG D6) ────────────────────────────────────

def compute_outcome_long_d6(stock_df: pd.DataFrame, scan_date: str,
                              entry_close: float, stop_price: float,
                              target_price: float) -> dict:
    """LONG D6 outcome from cached OHLC. Returns dict with outcome, exit_price,
    exit_day, pnl_pct."""
    scan_ts = pd.Timestamp(scan_date)
    post = stock_df[stock_df.index > scan_ts]
    if len(post) < _HOLDING_DAYS:
        return {"outcome": "OPEN", "exit_price": None, "exit_day": None,
                "pnl_pct": None}
    holding = post.head(_HOLDING_DAYS)
    for day_n, (ts, row) in enumerate(holding.iterrows(), start=1):
        if pd.isna(row["Low"]) or pd.isna(row["High"]):
            continue
        low = float(row["Low"]); high = float(row["High"])
        # LONG stop hit: low ≤ stop
        if low <= stop_price:
            pnl = (stop_price - entry_close) / entry_close * 100
            return {"outcome": "STOP_HIT", "exit_price": stop_price,
                    "exit_day": day_n, "pnl_pct": round(pnl, 4)}
        # LONG target hit: high ≥ target
        if high >= target_price:
            pnl = (target_price - entry_close) / entry_close * 100
            return {"outcome": "TARGET_HIT", "exit_price": target_price,
                    "exit_day": day_n, "pnl_pct": round(pnl, 4)}
    # Day 6 close exit
    d6_close = float(holding["Close"].iloc[-1])
    if pd.isna(d6_close):
        return {"outcome": "OPEN", "exit_price": None, "exit_day": None,
                "pnl_pct": None}
    pnl = (d6_close - entry_close) / entry_close * 100
    label = _classify_outcome(pnl)
    return {"outcome": label, "exit_price": d6_close,
            "exit_day": _HOLDING_DAYS, "pnl_pct": round(pnl, 4)}


# ── Regime + sector_momentum lookup ──────────────────────────────────

def load_regime_lookup() -> pd.Series:
    rdf = pd.read_parquet(_REGIME_PATH)
    rdf["date"] = pd.to_datetime(rdf["date"])
    return rdf.set_index(rdf["date"].dt.strftime("%Y-%m-%d"))["regime"]


def load_sector_momentum_lookup() -> pd.DataFrame:
    if not _SECTOR_MOM_PATH.exists():
        return pd.DataFrame()
    sdf = pd.read_parquet(_SECTOR_MOM_PATH)
    sdf["date"] = pd.to_datetime(sdf["date"])
    sdf = sdf.set_index(sdf["date"].dt.strftime("%Y-%m-%d"))
    return sdf


# ── Main matrix scan ─────────────────────────────────────────────────

def detect_all_signals(sector_lookup: dict) -> list[dict]:
    """Run detector across every stock parquet."""
    parquets = stock_parquets()
    print(f"[INV-010] scanning {len(parquets)} stock parquets…", flush=True)
    all_signals = []
    n_skipped = 0
    t0 = time.time()
    for i, p in enumerate(parquets):
        symbol = parquet_to_symbol(p)
        sector = sector_lookup.get(symbol)
        if sector is None:
            sector = "Unknown"
        try:
            df = pd.read_parquet(p)
            if not all(c in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]):
                n_skipped += 1; continue
            sigs = detect_gap_breakouts_for_stock(df, symbol, sector)
            all_signals.extend(sigs)
        except Exception as e:
            print(f"  skip {p.name}: {e}", flush=True)
            n_skipped += 1
        if (i + 1) % 25 == 0:
            print(f"[INV-010] {i+1}/{len(parquets)} stocks done; "
                  f"{len(all_signals)} signals so far ({time.time()-t0:.1f}s)",
                  flush=True)
    print(f"[INV-010] detection done: {len(all_signals)} signals, "
          f"{n_skipped} stocks skipped, {time.time()-t0:.1f}s", flush=True)
    return all_signals


def compute_outcomes_for_signals(signals: list[dict]) -> pd.DataFrame:
    """For each signal, compute LONG D6 outcome from cached OHLC."""
    print(f"[INV-010] computing D6 outcomes for {len(signals)} signals…", flush=True)
    # Group signals by symbol to load each parquet once
    by_symbol = {}
    for s in signals:
        by_symbol.setdefault(s["symbol"], []).append(s)
    enriched = []
    t0 = time.time()
    for i, (symbol, sigs) in enumerate(by_symbol.items()):
        parquet_name = symbol.replace(".NS", "_NS") + ".parquet"
        p = _CACHE_DIR / parquet_name
        if not p.exists():
            continue
        df = pd.read_parquet(p).sort_index()
        for s in sigs:
            outcome = compute_outcome_long_d6(
                df, s["scan_date"], s["entry_close"],
                s["stop_price"], s["target_price"])
            row = {**s, **outcome}
            enriched.append(row)
        if (i + 1) % 25 == 0:
            print(f"[INV-010] outcomes {i+1}/{len(by_symbol)} symbols "
                  f"({time.time()-t0:.1f}s)", flush=True)
    return pd.DataFrame(enriched)


def join_regime(signals_df: pd.DataFrame, regime_lookup: pd.Series,
                  sec_mom_df: pd.DataFrame) -> pd.DataFrame:
    if signals_df.empty:
        return signals_df
    signals_df = signals_df.copy()
    signals_df["regime"] = signals_df["scan_date"].map(regime_lookup)
    if not sec_mom_df.empty:
        # Pull per-sector value where available
        def _lookup_sm(row):
            sd = row["scan_date"]; sec = row["sector"]
            if sd in sec_mom_df.index and sec in sec_mom_df.columns:
                return sec_mom_df.loc[sd, sec]
            return "Neutral"
        signals_df["sec_mom"] = signals_df.apply(_lookup_sm, axis=1)
    else:
        signals_df["sec_mom"] = "Neutral"
    return signals_df


# ── Tier evaluation ──────────────────────────────────────────────────

def evaluate_lifetime_tier(signals_df: pd.DataFrame) -> dict:
    """Lifetime cohort stats + train/test split + tier eval (BOOST + KILL)."""
    lifetime = compute_cohort_stats(signals_df, cohort_filter={})
    n_excl_flat = lifetime["n_win"] + lifetime["n_loss"]
    out = {
        "lifetime": lifetime, "n_excl_flat": n_excl_flat,
        "boost_tier": None, "kill_tier": None,
        "boost_train_wr": None, "boost_test_wr": None, "boost_drift_pp": None,
        "boost_train_n": None, "boost_test_n": None,
        "kill_train_wr": None, "kill_test_wr": None, "kill_drift_pp": None,
        "tier_eval_status": None,
    }
    if n_excl_flat < _N_MIN_RESOLVED:
        out["tier_eval_status"] = "INSUFFICIENT_N"
        return out
    try:
        boost = evaluate_hypothesis(
            signals_df, cohort_filter={}, hypothesis_type="BOOST")
        out["boost_tier"] = boost["tier"]
        out["boost_train_wr"] = boost["train_stats"]["wr_excl_flat"]
        out["boost_test_wr"] = boost["test_stats"]["wr_excl_flat"]
        out["boost_train_n"] = (boost["train_stats"]["n_win"]
                                  + boost["train_stats"]["n_loss"])
        out["boost_test_n"] = (boost["test_stats"]["n_win"]
                                 + boost["test_stats"]["n_loss"])
        out["boost_drift_pp"] = boost["drift_pp"]
        kill = evaluate_hypothesis(
            signals_df, cohort_filter={}, hypothesis_type="KILL")
        out["kill_tier"] = kill["tier"]
        out["kill_train_wr"] = kill["train_stats"]["wr_excl_flat"]
        out["kill_test_wr"] = kill["test_stats"]["wr_excl_flat"]
        out["kill_drift_pp"] = kill["drift_pp"]
        out["tier_eval_status"] = "OK"
    except Exception as e:
        out["tier_eval_status"] = f"ERROR: {e}"
    return out


def evaluate_subcohorts(signals_df: pd.DataFrame) -> list[dict]:
    """Sector × regime breakdown. Skip cells with n_excl_flat < N_MIN_SUBCOHORT."""
    cells = []
    sectors = sorted(signals_df["sector"].dropna().unique().tolist())
    regimes = ["Bear", "Choppy", "Bull"]
    for sec in sectors:
        for reg in regimes:
            sub = signals_df[(signals_df["sector"] == sec)
                              & (signals_df["regime"] == reg)]
            stats = compute_cohort_stats(sub, cohort_filter={})
            n_ex = stats["n_win"] + stats["n_loss"]
            cell = {
                "sector": sec, "regime": reg,
                "n_total": stats["n_total"], "n_resolved": stats["n_resolved"],
                "n_excl_flat": n_ex, "n_win": stats["n_win"],
                "n_loss": stats["n_loss"], "n_flat": stats["n_flat"],
                "wr_excl_flat": stats["wr_excl_flat"],
                "wilson_lower_95": stats["wilson_lower_95"],
                "boost_tier": None, "kill_tier": None,
                "tier_status": None,
            }
            if n_ex < _N_MIN_SUBCOHORT:
                cell["tier_status"] = "INSUFFICIENT_N"
            else:
                try:
                    boost = evaluate_hypothesis(
                        sub, cohort_filter={}, hypothesis_type="BOOST")
                    kill = evaluate_hypothesis(
                        sub, cohort_filter={}, hypothesis_type="KILL")
                    cell["boost_tier"] = boost["tier"]
                    cell["kill_tier"] = kill["tier"]
                    cell["tier_status"] = "OK"
                except Exception as e:
                    cell["tier_status"] = f"ERROR: {e}"
            cells.append(cell)
    return cells


# ── UP_TRI baseline comparison ───────────────────────────────────────

def evaluate_up_tri_baseline() -> dict:
    """Lifetime UP_TRI cohort from existing backtest_signals."""
    bdf = pd.read_parquet(_BASELINE_SIGNALS)
    up = bdf[bdf["signal"] == "UP_TRI"]
    stats = compute_cohort_stats(up, cohort_filter={})
    n_ex = stats["n_win"] + stats["n_loss"]
    out = {
        "lifetime": stats, "n_excl_flat": n_ex,
        "boost_tier": None, "kill_tier": None,
        "by_sector": {},
    }
    if n_ex >= _N_MIN_RESOLVED:
        try:
            boost = evaluate_hypothesis(
                up, cohort_filter={}, hypothesis_type="BOOST")
            out["boost_tier"] = boost["tier"]
            kill = evaluate_hypothesis(
                up, cohort_filter={}, hypothesis_type="KILL")
            out["kill_tier"] = kill["tier"]
        except Exception:
            pass
    # Per-sector lifetime WR for UP_TRI
    for sec in up["sector"].dropna().unique():
        sub = up[up["sector"] == sec]
        s = compute_cohort_stats(sub, cohort_filter={})
        out["by_sector"][sec] = {
            "n_excl_flat": s["n_win"] + s["n_loss"],
            "wr_excl_flat": s["wr_excl_flat"],
        }
    return out


# ── Findings.md writer ────────────────────────────────────────────────

def write_findings_md(signals_df: pd.DataFrame, lifetime_eval: dict,
                       subcohorts: list[dict], baseline_up_tri: dict,
                       diagnostics: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(signals_df)
    by_year = signals_df.groupby(
        pd.to_datetime(signals_df["scan_date"]).dt.year).size().to_dict()
    by_sector = signals_df.groupby("sector").size().sort_values(ascending=False).to_dict()

    with open(output_path, "w") as f:
        f.write("# INV-010 — GAP_BREAKOUT new entry signal discovery\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write("**Signal:** GAP_BREAKOUT (LONG; gap-up + 10-day consolidation + "
                "5-day high break + volume confirmation)\n\n")
        f.write(f"**Universe:** 188 F&O stocks × 15-year backtest (2011-2026)\n\n")

        # Caveats
        f.write("---\n\n## ⚠️ Caveats\n\n")
        f.write("**Signal direction:** LONG (consistent with UP_TRI/BULL_PROXY family). "
                "Outcome computation uses LONG D6 semantics: "
                "stop_hit if low ≤ stop_price; target_hit if high ≥ target_price; "
                "pnl = (exit - entry) / entry × 100.\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate)** is INV-010-specific because this "
                "investigation builds a NEW detector from cache parquets directly; not "
                "subject to the original signal_replayer regen miss-rate. However, miss-rate "
                "in cache itself (yfinance gaps, missing volume bars) may affect detection.\n\n")
        f.write("**Adoption requires production work:** any GAP_BREAKOUT promotion to "
                "scanner.scanner_core would be a separate main-branch session (per INV-010 "
                "patterns.json note); INV-010 is data + structured analysis only.\n\n")

        # ── Section 1 — Methodology ──
        f.write("---\n\n## Section 1 — Methodology\n\n")
        f.write("**Signal definition (all 4 rules required):**\n")
        f.write(f"1. `today_open > prev_close × {1 + _GAP_UP_PCT}` (gap up >{_GAP_UP_PCT*100}%)\n")
        f.write(f"2. `today_high > prior_{_BREAKOUT_LOOKBACK}d_high` (5-day high break)\n")
        f.write(f"3. `prior_{_CONSOLIDATION_LOOKBACK}d_range / prior_{_CONSOLIDATION_LOOKBACK}d_avg_close < {_CONSOLIDATION_MAX_PCT}` "
                f"(consolidation: 10-day range <{_CONSOLIDATION_MAX_PCT*100}%)\n")
        f.write(f"4. `today_volume > {_VOLUME_MULTIPLE} × prior_{_VOLUME_LOOKBACK}d_avg_volume` "
                f"(volume confirmation)\n\n")
        f.write("**Entry/exit:**\n")
        f.write(f"- entry_close = today's close\n")
        f.write(f"- stop_price = entry × {1 - _STOP_PCT} (5% below)\n")
        f.write(f"- target_price = entry × {1 + _TARGET_PCT} (10% above; 2:1 RR)\n")
        f.write(f"- Hold period: D{_HOLDING_DAYS} default\n")
        f.write(f"- Direction: LONG; D6 close exit if neither stop nor target hit\n\n")
        f.write("**Pipeline:** for each stock parquet, build rolling features "
                "(prev_close, prior_5d_high, prior_10d_range, prior_10d_avg_close, "
                "prior_20d_avg_volume); detect signals where all 4 rules fire; emit signal "
                "records; compute LONG D6 outcomes; join regime + sector; tier evaluation.\n\n")

        # ── Section 2 — Detection diagnostics ──
        f.write("---\n\n## Section 2 — Detection diagnostics\n\n")
        f.write(f"**Total signals detected:** {n}\n\n")
        f.write(f"**Stocks with at least one signal:** {signals_df['symbol'].nunique()} of 188\n\n")
        f.write(f"**Date range:** {signals_df['scan_date'].min()} → {signals_df['scan_date'].max()}\n\n")
        f.write(f"**Outcome distribution:**\n\n")
        outcome_counts = signals_df["outcome"].value_counts().to_dict()
        f.write("| Outcome | Count | Pct |\n|---|---|---|\n")
        for k, v in outcome_counts.items():
            f.write(f"| {k} | {v} | {v/n*100:.2f}% |\n")
        f.write("\n**Signals by year:**\n\n")
        f.write("| Year | Count |\n|---|---|\n")
        for y in sorted(by_year.keys()):
            f.write(f"| {y} | {by_year[y]} |\n")
        f.write("\n**Signals by sector:**\n\n")
        f.write("| Sector | Count |\n|---|---|\n")
        for s, c in by_sector.items():
            f.write(f"| {s} | {c} |\n")
        f.write("\n")

        # ── Section 3 — Lifetime cohort + tier evaluation ──
        f.write("---\n\n## Section 3 — Lifetime cohort + tier evaluation\n\n")
        lt = lifetime_eval["lifetime"]
        f.write(f"**Lifetime stats:**\n")
        f.write(f"- n_total: {lt['n_total']}\n")
        f.write(f"- n_resolved: {lt['n_resolved']}\n")
        f.write(f"- n_excl_flat: {lifetime_eval['n_excl_flat']}\n")
        f.write(f"- n_win: {lt['n_win']} | n_loss: {lt['n_loss']} | n_flat: {lt['n_flat']} | n_open: {lt['n_open']}\n")
        f.write(f"- WR (excl flat): {lt['wr_excl_flat']}\n")
        f.write(f"- Wilson lower 95: {lt['wilson_lower_95']}\n")
        f.write(f"- p-value vs 50%: {lt['p_value_vs_50']}\n\n")
        f.write(f"**Tier evaluation (train 2011-2022 / test 2023-2026):**\n\n")
        f.write(f"| Hypothesis | Train_WR | Test_WR | Drift_pp | Train_n | Test_n | Tier |\n")
        f.write(f"|---|---|---|---|---|---|---|\n")
        f.write(f"| BOOST | {lifetime_eval.get('boost_train_wr')} | "
                f"{lifetime_eval.get('boost_test_wr')} | "
                f"{lifetime_eval.get('boost_drift_pp')} | "
                f"{lifetime_eval.get('boost_train_n')} | "
                f"{lifetime_eval.get('boost_test_n')} | "
                f"**{lifetime_eval.get('boost_tier')}** |\n")
        f.write(f"| KILL  | {lifetime_eval.get('kill_train_wr')} | "
                f"{lifetime_eval.get('kill_test_wr')} | "
                f"{lifetime_eval.get('kill_drift_pp')} | — | — | "
                f"**{lifetime_eval.get('kill_tier')}** |\n\n")

        # Pnl distribution
        resolved = signals_df[signals_df["outcome"].isin(
            ["DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT", "TARGET_HIT", "STOP_HIT"])]
        if len(resolved) > 0:
            arr = resolved["pnl_pct"].dropna().values
            f.write("**Per-trade pnl distribution (LONG semantics):**\n\n")
            f.write("| Stat | Value |\n|---|---|\n")
            f.write(f"| n | {len(arr)} |\n")
            f.write(f"| Mean | {np.mean(arr):+.3f}% |\n")
            f.write(f"| Median | {np.median(arr):+.3f}% |\n")
            f.write(f"| Std | {np.std(arr, ddof=1):+.3f}% |\n")
            f.write(f"| p5 | {np.percentile(arr, 5):+.3f}% |\n")
            f.write(f"| p25 | {np.percentile(arr, 25):+.3f}% |\n")
            f.write(f"| p75 | {np.percentile(arr, 75):+.3f}% |\n")
            f.write(f"| p95 | {np.percentile(arr, 95):+.3f}% |\n")
            f.write("\n")

        # ── Section 4 — Sector × regime sub-cohort table ──
        f.write("---\n\n## Section 4 — Sector × regime sub-cohort breakdown\n\n")
        ok_cells = [c for c in subcohorts if c["tier_status"] == "OK"]
        insuff_cells = [c for c in subcohorts if c["tier_status"] == "INSUFFICIENT_N"]
        f.write(f"**Cells evaluated:** {len(subcohorts)} ({len(ok_cells)} OK, "
                f"{len(insuff_cells)} INSUFFICIENT_N)\n\n")
        if ok_cells:
            f.write("| Sector | Regime | n_excl_flat | WR | Wilson_lower | BoostTier | KillTier |\n")
            f.write("|--------|--------|-------------|-----|--------------|----------|----------|\n")
            for c in sorted(ok_cells, key=lambda x: -(x["wr_excl_flat"] or 0)):
                f.write(f"| {c['sector']} | {c['regime']} | {c['n_excl_flat']} | "
                        f"{c['wr_excl_flat']} | {c['wilson_lower_95']} | "
                        f"{c['boost_tier']} | {c['kill_tier']} |\n")
            f.write("\n")
        # Surfaces (any cell earning Tier S/A/B on either hypothesis)
        tier_hits = [c for c in ok_cells
                      if c.get("boost_tier") in ("S", "A", "B")
                      or c.get("kill_tier") in ("S", "A", "B")]
        f.write(f"**Sub-cohorts earning Lab tier (S/A/B):** {len(tier_hits)}\n")
        for hit in tier_hits:
            tiers = []
            if hit.get("boost_tier") in ("S", "A", "B"):
                tiers.append(f"BOOST {hit['boost_tier']}")
            if hit.get("kill_tier") in ("S", "A", "B"):
                tiers.append(f"KILL {hit['kill_tier']}")
            f.write(f"- `{hit['sector']} × {hit['regime']}` → {', '.join(tiers)} "
                    f"(n={hit['n_excl_flat']}, WR={hit['wr_excl_flat']})\n")
        f.write("\n")

        # ── Section 5 — UP_TRI baseline comparison ──
        f.write("---\n\n## Section 5 — Comparison to UP_TRI baseline\n\n")
        b_lt = baseline_up_tri["lifetime"]
        f.write(f"**UP_TRI baseline (lifetime, all sectors/regimes):**\n")
        f.write(f"- n_excl_flat: {baseline_up_tri['n_excl_flat']}, "
                f"WR={b_lt['wr_excl_flat']}, Wilson={b_lt['wilson_lower_95']}, "
                f"p={b_lt['p_value_vs_50']}\n")
        f.write(f"- BoostTier: {baseline_up_tri.get('boost_tier')} | "
                f"KillTier: {baseline_up_tri.get('kill_tier')}\n\n")
        # 2-prop p-value: GAP_BREAKOUT vs UP_TRI
        gb_n = lifetime_eval["n_excl_flat"]
        gb_wr = lt["wr_excl_flat"]
        b_n = baseline_up_tri["n_excl_flat"]
        b_wr = b_lt["wr_excl_flat"]
        if gb_n > 0 and b_n > 0 and gb_wr is not None and b_wr is not None:
            delta = round(gb_wr - b_wr, 4)
            w_g = round(gb_wr * gb_n)
            w_b = round(b_wr * b_n)
            p_2prop = _two_proportion_p_value(w_g, gb_n, w_b, b_n)
            f.write(f"**Comparison vs UP_TRI baseline:**\n")
            f.write(f"- Δ WR: {delta:+.4f} ({_round_pct(delta):+.2f} pp)\n")
            f.write(f"- 2-prop z-test p-value: {p_2prop}\n")
            if delta >= 0.03 and p_2prop is not None and p_2prop < 0.05:
                f.write(f"- **Verdict: GAP_BREAKOUT BEATS UP_TRI on lifetime WR (≥3pp + p<0.05)**\n\n")
            elif delta <= -0.03 and p_2prop is not None and p_2prop < 0.05:
                f.write(f"- **Verdict: GAP_BREAKOUT WORSE than UP_TRI on lifetime WR**\n\n")
            else:
                f.write(f"- **Verdict: GAP_BREAKOUT marginal/equivalent vs UP_TRI on lifetime WR**\n\n")

        # Per-sector lifetime WR comparison
        f.write("**Per-sector lifetime WR comparison (sectors with both ≥30 signals):**\n\n")
        gb_by_sector = signals_df.groupby("sector").apply(
            lambda x: compute_cohort_stats(x, cohort_filter={}), include_groups=False).to_dict()
        f.write("| Sector | UP_TRI n | UP_TRI WR | GAP_BREAKOUT n | GAP_BREAKOUT WR | Δ WR pp |\n")
        f.write("|--------|----------|-----------|----------------|------------------|----------|\n")
        for sec in sorted(gb_by_sector.keys()):
            gb_stat = gb_by_sector[sec]
            gb_n_s = gb_stat["n_win"] + gb_stat["n_loss"]
            gb_wr_s = gb_stat["wr_excl_flat"]
            base = baseline_up_tri["by_sector"].get(sec, {})
            b_n_s = base.get("n_excl_flat", 0)
            b_wr_s = base.get("wr_excl_flat")
            if gb_n_s < 30 or b_n_s < 30:
                continue
            d_pp = (gb_wr_s - b_wr_s) * 100 if (gb_wr_s and b_wr_s) else None
            d_str = f"{d_pp:+.2f}" if d_pp is not None else "—"
            f.write(f"| {sec} | {b_n_s} | {b_wr_s} | {gb_n_s} | {gb_wr_s} | {d_str} |\n")
        f.write("\n")

        # ── Section 6 — Headline ──
        f.write("---\n\n## Section 6 — Headline findings (data only; NO promotion calls)\n\n")
        boost_tier_lt = lifetime_eval.get("boost_tier")
        kill_tier_lt = lifetime_eval.get("kill_tier")
        f.write(f"- **Total signals detected:** {n} across 188 stocks × 15 years\n")
        f.write(f"- **Lifetime WR:** {lt['wr_excl_flat']} (n_excl_flat={lifetime_eval['n_excl_flat']})\n")
        f.write(f"- **Lifetime BOOST tier:** **{boost_tier_lt}**\n")
        f.write(f"- **Lifetime KILL tier:** **{kill_tier_lt}**\n")
        f.write(f"- **Sub-cohort tier hits (S/A/B):** {len(tier_hits)} of {len(ok_cells)} "
                f"OK cells\n")
        f.write(f"- **UP_TRI baseline WR:** {b_lt['wr_excl_flat']} "
                f"(n={baseline_up_tri['n_excl_flat']})\n\n")
        # Synthesized headline
        if boost_tier_lt in ("S", "A", "B"):
            headline = (f"GAP_BREAKOUT lifetime cohort earns BOOST Tier {boost_tier_lt} "
                        f"(WR {lt['wr_excl_flat']}; n {lifetime_eval['n_excl_flat']}). "
                        f"User reviews tier eligibility + Caveat 2 audit + sector breakdown "
                        f"before any scanner_core integration decision.")
        elif tier_hits:
            headline = (f"GAP_BREAKOUT lifetime cohort REJECTs at parent tier but {len(tier_hits)} "
                        f"sub-cohorts earn Tier S/A/B. User reviews per-cohort tier eligibility.")
        else:
            headline = (f"GAP_BREAKOUT lifetime cohort REJECTs (BOOST {boost_tier_lt} / "
                        f"KILL {kill_tier_lt}). 0 sub-cohorts earn Lab tier. New signal does "
                        f"not surface tradeable edge in current universe.")
        f.write(f"**Headline:** {headline}\n\n")

        # ── Section 7 — Open questions ──
        f.write("---\n\n## Section 7 — Open questions for user review\n\n")
        f.write("1. **Lifetime tier eligibility:** Does Section 3 BOOST or KILL tier verdict "
                "warrant adding GAP_BREAKOUT to scanner.scanner_core as new signal type? "
                "If no tier earned, decision is to archive new signal definition.\n\n")
        f.write("2. **Sub-cohort tier hits (Section 4):** if any (sector × regime) cell earns "
                "tier even though lifetime REJECT, consider conditional GAP_BREAKOUT signal "
                "(only fires for specific cohorts). Same n + Caveat 2 vulnerability check as "
                "INV-003 surfaced candidates.\n\n")
        f.write("3. **GAP_BREAKOUT vs UP_TRI (Section 5):** does new signal materially beat "
                "existing UP_TRI base case on lifetime WR? If marginal, no incremental value "
                "from adding new signal type.\n\n")
        f.write("4. **Caveat 2 audit dependency:** any tier-eligible cell at marginal n needs "
                "Caveat 2 audit before promotion (same standard as INV-003 candidates).\n\n")
        f.write("5. **Detector parameter sensitivity:** thresholds (0.5% gap, 5% range, 1.2× vol) "
                "are arbitrary; could request sensitivity analysis (different thresholds) "
                "if findings sit near boundaries.\n\n")
        f.write("6. **patterns.json INV-010 status:** PRE_REGISTERED → COMPLETED is "
                "user-only transition.\n\n")

        f.write("---\n\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. "
                "No promotion decisions are made by CC.\n")


# ── Main orchestrator ────────────────────────────────────────────────

def main():
    print(f"[INV-010] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)

    sector_lookup = load_sector_lookup()
    print(f"[INV-010] sector lookup: {len(sector_lookup)} symbols", flush=True)
    regime_lookup = load_regime_lookup()
    sec_mom_df = load_sector_momentum_lookup()
    print(f"[INV-010] regime lookup: {len(regime_lookup)} dates; "
          f"sec_mom: {sec_mom_df.shape if not sec_mom_df.empty else 'empty'}",
          flush=True)

    signals = detect_all_signals(sector_lookup)
    if len(signals) == 0:
        raise SystemExit("[INV-010] T5 TRIPWIRE: zero signals detected")
    if len(signals) > 50_000:
        print(f"[INV-010] WARNING T6: {len(signals)} signals — may be too lax",
              flush=True)

    signals_df = compute_outcomes_for_signals(signals)
    print(f"[INV-010] outcomes computed: {len(signals_df)} rows", flush=True)
    signals_df = join_regime(signals_df, regime_lookup, sec_mom_df)

    # Save signals parquet
    print(f"[INV-010] writing {_OUTPUT_PARQUET}…", flush=True)
    signals_df.to_parquet(_OUTPUT_PARQUET)

    # Tier evaluation
    print(f"[INV-010] lifetime tier evaluation…", flush=True)
    lifetime_eval = evaluate_lifetime_tier(signals_df)
    print(f"[INV-010] lifetime BoostTier: {lifetime_eval.get('boost_tier')}, "
          f"KillTier: {lifetime_eval.get('kill_tier')}", flush=True)

    print(f"[INV-010] sub-cohort breakdown…", flush=True)
    subcohorts = evaluate_subcohorts(signals_df)
    print(f"[INV-010] sub-cohorts: {len(subcohorts)} cells "
          f"({sum(1 for c in subcohorts if c['tier_status'] == 'OK')} OK)",
          flush=True)

    print(f"[INV-010] UP_TRI baseline…", flush=True)
    baseline = evaluate_up_tri_baseline()
    print(f"[INV-010] UP_TRI baseline WR: "
          f"{baseline['lifetime']['wr_excl_flat']} (n={baseline['n_excl_flat']})",
          flush=True)

    diagnostics = {
        "n_signals": len(signals_df),
        "n_stocks_signaled": signals_df["symbol"].nunique(),
    }

    print(f"[INV-010] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(signals_df, lifetime_eval, subcohorts, baseline,
                       diagnostics, _OUTPUT_FINDINGS)
    print(f"[INV-010] complete at {datetime.now(timezone.utc).isoformat()}",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-010] FATAL: {e}\n{tb}", flush=True)
        try:
            _OUTPUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
            with open(_OUTPUT_FINDINGS, "w") as f:
                f.write(f"# INV-010 — CRASH at {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write(f"```\n{tb}\n```\n")
        except Exception:
            pass
        raise
