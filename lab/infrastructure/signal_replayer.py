"""
MS-2 — Backtest Lab signal replayer.

Per ROADMAP.md MS-2 spec: replay UP_TRI / DOWN_TRI / BULL_PROXY signal detection
on historical OHLC. Cross-validate against output/signal_history.json for
2026-04 window (T2 tripwire: < 80% match → HALT).

Purity audit (this module's import boundary):
- scanner.scanner_core.detect_signals: PURE given (df, symbol, sector, regime,
  regime_score, sector_momentum, nifty_close). Module-level constants from
  scanner.config; no global mutable state.
- scanner.scanner_core._get_stock_regime: PURE on df only.
- scanner.scanner_core._get_nifty_pct: PURE on nifty_close only.

Replay model:
- For each (symbol, scan_date): truncate symbol's cached OHLCV to dates ≤
  scan_date; pass truncated df to detect_signals; detector treats last_bar of
  df as "today's" bar.
- regime + regime_score: read from regime_history.parquet (MS-3 output) joined
  on scan_date.
- sector_momentum: read from sector_momentum_history.parquet (MS-3 output)
  joined on scan_date.
- nifty_close: read from ^NSEI cache, truncated to ≤ scan_date.

Outcome computation (D6 W/L/F):
- entry: next-trading-day OPEN after scan_date (per non-negotiable trading rule)
- D6 exit: 6th trading day after entry; outcome at OPEN of D6 day
- stop-hit: any low ≤ stop_price on entry-day → D6-day inclusive → STOP exit
  recorded at stop_price on hit day
- target-hit: any high ≥ target_price on entry-day → D6-day inclusive → TARGET
  exit at target_price on hit day
- target_price = entry + R_multiple × (entry - stop_price); R_multiple = 2.0
  per scanner.config TARGET_R_MULTIPLE
- W/L/F threshold: ±0.5% from entry on D6 open (matching live outcome_evaluator
  semantics where small moves = FLAT)

Output:
- /lab/output/backtest_signals.parquet — full backtest signals + outcomes

Cross-validation (T2 tripwire):
- Filter regenerated signals to scan_date in [2026-04-01, 2026-04-29]
- Compare against output/signal_history.json same window
- Match key: (date, symbol, signal) tuple
- Match metric: matched_signals / live_signals
- If < 80%: HALT (do NOT mark MS-2 complete)

CLI:
    python lab/infrastructure/signal_replayer.py --smoke  # synthetic smoke
    python lab/infrastructure/signal_replayer.py          # full replay
    python lab/infrastructure/signal_replayer.py --validate-only  # only run cross-val
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent
_CACHE_DIR = _LAB_ROOT / "cache"
_LAB_OUTPUT = _LAB_ROOT / "output"
_LOGS_DIR = _LAB_ROOT / "logs"
_UNIVERSE_CSV = _REPO_ROOT / "data" / "fno_universe.csv"
_LIVE_HISTORY = _REPO_ROOT / "output" / "signal_history.json"
_BACKTEST_SIGNALS = _LAB_OUTPUT / "backtest_signals.parquet"
_REGIME_HISTORY = _LAB_OUTPUT / "regime_history.parquet"
_SECTOR_MOMENTUM_HISTORY = _LAB_OUTPUT / "sector_momentum_history.parquet"
_VALIDATION_REPORT = _LOGS_DIR / "ms2_cross_validation_report.json"
_NIFTY_CACHE = _CACHE_DIR / "_index_NSEI.parquet"

# ── Replay constants ──────────────────────────────────────────────────
_VALIDATION_WINDOW_START = "2026-04-01"
_VALIDATION_WINDOW_END = "2026-04-29"
_MIN_MATCH_PCT = 80.0  # T2 tripwire threshold
_FLAT_THRESHOLD_PCT = 0.5  # |pnl| < 0.5% → DAY6_FLAT
_TARGET_R_MULTIPLE = 2.0  # matches scanner.config TARGET_R_MULTIPLE
_HOLDING_DAYS = 6  # D6 exit


# ── Detector imports (pure-function audit confirmed) ────────────────
def _import_detector():
    """Lazy import; allows module to load even if scanner deps unmet."""
    sys.path.insert(0, str(_REPO_ROOT))
    from scanner.scanner_core import detect_signals  # noqa: E402
    return detect_signals


# ── Universe loader ───────────────────────────────────────────────────
def load_universe() -> dict[str, str]:
    """Returns {symbol: sector} mapping from fno_universe.csv."""
    if not _UNIVERSE_CSV.exists():
        raise FileNotFoundError(_UNIVERSE_CSV)
    out = {}
    with open(_UNIVERSE_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = (row.get("symbol") or "").strip()
            sec = (row.get("sector") or "").strip()
            if sym:
                out[sym] = sec
    return out


def load_cached_ohlcv(symbol: str) -> Optional[pd.DataFrame]:
    """Load symbol's cached OHLCV parquet. Returns None if not cached."""
    safe = symbol.replace(".", "_").replace("^", "_index_")
    path = _CACHE_DIR / f"{safe}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ── Outcome computation (D6 W/L/F + stop/target hit) ─────────────────

@dataclass
class SignalOutcome:
    entry_date: Optional[str]
    entry_price: Optional[float]
    exit_date: Optional[str]
    exit_price: Optional[float]
    exit_type: str  # "DAY6_WIN" | "DAY6_LOSS" | "DAY6_FLAT" | "STOP_HIT" | "TARGET_HIT" | "OPEN" | "INVALID"
    exit_day: Optional[int]
    pnl_pct: Optional[float]
    outcome: str  # alias for exit_type for live signal_history compat


def compute_d6_outcome(symbol_df: pd.DataFrame,
                        scan_date: pd.Timestamp,
                        entry_price: float,
                        stop_price: float,
                        direction: str = "LONG") -> SignalOutcome:
    """Compute D6 outcome given scan_date + entry + stop. LONG only for now
    (UP_TRI/BULL_PROXY); DOWN_TRI handled by caller flipping sign.

    Trading-day math: entry = next trading day's OPEN; D6 = 6th subsequent
    trading day; outcome at D6 OPEN unless stop/target hit intraday earlier.
    """
    # Find post-scan rows
    post = symbol_df[symbol_df.index > scan_date]
    if len(post) < 1:
        return SignalOutcome(
            entry_date=None, entry_price=None,
            exit_date=None, exit_price=None,
            exit_type="OPEN", exit_day=None, pnl_pct=None,
            outcome="OPEN")

    # Entry = first post-scan row's OPEN
    entry_row = post.iloc[0]
    actual_entry_date = post.index[0].date().isoformat()
    actual_entry_price = float(entry_row["Open"])

    # Target price (TARGET_R_MULTIPLE × risk for LONG)
    risk = abs(entry_price - stop_price)
    if direction == "LONG":
        target_price = entry_price + _TARGET_R_MULTIPLE * risk
    else:  # SHORT (DOWN_TRI)
        target_price = entry_price - _TARGET_R_MULTIPLE * risk

    # Walk forward HOLDING_DAYS bars; check stop/target intraday each bar
    holding = post.head(_HOLDING_DAYS)
    if len(holding) < _HOLDING_DAYS:
        # Insufficient forward data → still OPEN
        return SignalOutcome(
            entry_date=actual_entry_date,
            entry_price=actual_entry_price,
            exit_date=None, exit_price=None,
            exit_type="OPEN", exit_day=None, pnl_pct=None,
            outcome="OPEN")

    for day_n, (ts, row) in enumerate(holding.iterrows(), start=1):
        low = float(row["Low"])
        high = float(row["High"])
        # Stop hit
        if direction == "LONG" and low <= stop_price:
            pnl = (stop_price - entry_price) / entry_price * 100
            return SignalOutcome(
                entry_date=actual_entry_date,
                entry_price=actual_entry_price,
                exit_date=ts.date().isoformat(),
                exit_price=float(stop_price),
                exit_type="STOP_HIT", exit_day=day_n, pnl_pct=round(pnl, 2),
                outcome="STOP_HIT")
        if direction == "SHORT" and high >= stop_price:
            pnl = (entry_price - stop_price) / entry_price * 100
            return SignalOutcome(
                entry_date=actual_entry_date,
                entry_price=actual_entry_price,
                exit_date=ts.date().isoformat(),
                exit_price=float(stop_price),
                exit_type="STOP_HIT", exit_day=day_n, pnl_pct=round(pnl, 2),
                outcome="STOP_HIT")
        # Target hit
        if direction == "LONG" and high >= target_price:
            pnl = (target_price - entry_price) / entry_price * 100
            return SignalOutcome(
                entry_date=actual_entry_date,
                entry_price=actual_entry_price,
                exit_date=ts.date().isoformat(),
                exit_price=float(target_price),
                exit_type="TARGET_HIT", exit_day=day_n, pnl_pct=round(pnl, 2),
                outcome="TARGET_HIT")
        if direction == "SHORT" and low <= target_price:
            pnl = (entry_price - target_price) / entry_price * 100
            return SignalOutcome(
                entry_date=actual_entry_date,
                entry_price=actual_entry_price,
                exit_date=ts.date().isoformat(),
                exit_price=float(target_price),
                exit_type="TARGET_HIT", exit_day=day_n, pnl_pct=round(pnl, 2),
                outcome="TARGET_HIT")

    # No stop/target hit → D6 outcome at D6 OPEN
    d6_row = holding.iloc[-1]
    d6_open = float(d6_row["Open"])
    if direction == "LONG":
        pnl = (d6_open - entry_price) / entry_price * 100
    else:
        pnl = (entry_price - d6_open) / entry_price * 100

    if abs(pnl) < _FLAT_THRESHOLD_PCT:
        outcome_label = "DAY6_FLAT"
    elif pnl > 0:
        outcome_label = "DAY6_WIN"
    else:
        outcome_label = "DAY6_LOSS"

    return SignalOutcome(
        entry_date=actual_entry_date,
        entry_price=actual_entry_price,
        exit_date=holding.index[-1].date().isoformat(),
        exit_price=d6_open,
        exit_type=outcome_label, exit_day=_HOLDING_DAYS,
        pnl_pct=round(pnl, 2), outcome=outcome_label)


# ── Replay core ───────────────────────────────────────────────────────

def replay_signals_for_symbol(symbol: str,
                               sector: str,
                               sym_df: pd.DataFrame,
                               regime_df: Optional[pd.DataFrame] = None,
                               sector_mom_df: Optional[pd.DataFrame] = None,
                               nifty_df: Optional[pd.DataFrame] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> list[dict]:
    """Replay signal detection across symbol's historical OHLCV.

    For each scan_date in sym_df: truncate to ≤ scan_date; call detect_signals;
    compute outcomes; collect rows.
    """
    detect_signals = _import_detector()

    if sym_df is None or sym_df.empty:
        return []
    sym_df = sym_df.sort_index()

    # Date range filter
    if start_date:
        sym_df = sym_df[sym_df.index >= pd.Timestamp(start_date)]
    if end_date:
        sym_df = sym_df[sym_df.index <= pd.Timestamp(end_date)]

    rows = []
    # Need at least 50 bars of history for indicators
    MIN_LOOKBACK = 60
    for i in range(MIN_LOOKBACK, len(sym_df)):
        scan_date = sym_df.index[i]
        truncated = sym_df.iloc[:i + 1]

        # Lookup regime + sector_momentum at scan_date
        regime, regime_score = _lookup_regime(scan_date, regime_df)
        sector_momentum = _lookup_sector_momentum(scan_date, sector_mom_df)

        # Truncate nifty
        nifty_truncated = None
        if nifty_df is not None:
            nifty_truncated = nifty_df[nifty_df.index <= scan_date]["Close"]

        try:
            sigs = detect_signals(
                truncated, symbol, sector,
                regime, regime_score,
                sector_momentum, nifty_close=nifty_truncated)
        except Exception as e:
            # Detector failure on this date — log + continue
            sigs = []

        for s in sigs:
            # Compute D6 outcome
            entry_est = s.get("entry_est") or s.get("entry")
            stop = s.get("stop")
            direction = s.get("direction", "LONG")
            outcome = SignalOutcome(
                entry_date=None, entry_price=None,
                exit_date=None, exit_price=None,
                exit_type="OPEN", exit_day=None, pnl_pct=None,
                outcome="OPEN")
            if entry_est is not None and stop is not None:
                outcome = compute_d6_outcome(
                    sym_df, scan_date, float(entry_est), float(stop), direction)

            rows.append({
                "scan_date": scan_date.date().isoformat(),
                "symbol": symbol,
                "sector": sector,
                "signal": s.get("signal"),
                "direction": direction,
                "age": s.get("age"),
                "regime": regime,
                "regime_score": regime_score,
                "stock_regime": s.get("stock_regime"),
                "score": None,  # score computed separately if needed
                "vol_q": s.get("vol_q"),
                "vol_confirm": s.get("vol_confirm"),
                "rs_q": s.get("rs_q"),
                "sec_mom": s.get("sec_mom"),
                "entry_est": entry_est,
                "stop": stop,
                "atr": s.get("atr"),
                "pivot_price": s.get("pivot_price"),
                "pivot_date": s.get("pivot_date"),
                # Outcome fields
                "entry_date": outcome.entry_date,
                "entry_price": outcome.entry_price,
                "exit_date": outcome.exit_date,
                "exit_price": outcome.exit_price,
                "exit_type": outcome.exit_type,
                "exit_day": outcome.exit_day,
                "pnl_pct": outcome.pnl_pct,
                "outcome": outcome.outcome,
            })
    return rows


def _lookup_regime(scan_date: pd.Timestamp,
                    regime_df: Optional[pd.DataFrame]) -> tuple:
    """Lookup regime + regime_score for scan_date. Defaults if unavailable."""
    if regime_df is None or regime_df.empty:
        return "Choppy", 0
    try:
        df = regime_df[regime_df.index <= scan_date]
        if df.empty:
            return "Choppy", 0
        last = df.iloc[-1]
        return str(last.get("regime", "Choppy")), int(last.get("regime_score", 0))
    except Exception:
        return "Choppy", 0


def _lookup_sector_momentum(scan_date: pd.Timestamp,
                              sector_mom_df: Optional[pd.DataFrame]) -> dict:
    """Lookup sector_momentum dict for scan_date. Empty fallback."""
    if sector_mom_df is None or sector_mom_df.empty:
        return {}
    try:
        df = sector_mom_df[sector_mom_df.index <= scan_date]
        if df.empty:
            return {}
        last = df.iloc[-1].to_dict()
        return {k: v for k, v in last.items() if isinstance(v, str)}
    except Exception:
        return {}


def replay_universe(start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    symbols_filter: Optional[list[str]] = None) -> pd.DataFrame:
    """Replay all symbols in universe; concatenate; return DataFrame."""
    universe = load_universe()
    regime_df = pd.read_parquet(_REGIME_HISTORY) if _REGIME_HISTORY.exists() else None
    if regime_df is not None:
        regime_df.index = pd.to_datetime(regime_df.index)
    sector_mom_df = (pd.read_parquet(_SECTOR_MOMENTUM_HISTORY)
                      if _SECTOR_MOMENTUM_HISTORY.exists() else None)
    if sector_mom_df is not None:
        sector_mom_df.index = pd.to_datetime(sector_mom_df.index)
    nifty_df = pd.read_parquet(_NIFTY_CACHE) if _NIFTY_CACHE.exists() else None
    if nifty_df is not None:
        nifty_df.index = pd.to_datetime(nifty_df.index)

    if symbols_filter:
        universe = {k: v for k, v in universe.items() if k in symbols_filter}

    all_rows = []
    for i, (sym, sec) in enumerate(universe.items()):
        sym_df = load_cached_ohlcv(sym)
        if sym_df is None:
            print(f"  [{sym}] not cached; skip", flush=True)
            continue
        rows = replay_signals_for_symbol(
            sym, sec, sym_df, regime_df, sector_mom_df, nifty_df,
            start_date=start_date, end_date=end_date)
        all_rows.extend(rows)
        if (i + 1) % 25 == 0:
            print(f"  progress {i + 1}/{len(universe)}; rows so far {len(all_rows)}",
                  flush=True)

    df = pd.DataFrame(all_rows)
    return df


# ── Cross-validation (T2 tripwire) ────────────────────────────────────

def cross_validate_against_live(regenerated_df: pd.DataFrame) -> dict:
    """Compare regenerated 2026-04 signals vs live signal_history.json.
    Returns {match_pct, regen_count, live_count, matched_count, missing,
    extra, t2_passed}.
    """
    if not _LIVE_HISTORY.exists():
        return {"error": "live signal_history.json not found"}

    with open(_LIVE_HISTORY, "r", encoding="utf-8") as f:
        live = json.load(f).get("history", [])

    live_window = [
        s for s in live
        if (s.get("date") or "") >= _VALIDATION_WINDOW_START
        and (s.get("date") or "") <= _VALIDATION_WINDOW_END
    ]
    live_keys = {(s["date"], s["symbol"], s["signal"])
                 for s in live_window
                 if s.get("date") and s.get("symbol") and s.get("signal")}

    if regenerated_df is None or regenerated_df.empty:
        return {
            "match_pct": 0.0,
            "regen_count": 0,
            "live_count": len(live_keys),
            "matched_count": 0,
            "t2_passed": False,
        }

    regen_window = regenerated_df[
        (regenerated_df["scan_date"] >= _VALIDATION_WINDOW_START)
        & (regenerated_df["scan_date"] <= _VALIDATION_WINDOW_END)
    ]
    regen_keys = {(r["scan_date"], r["symbol"], r["signal"])
                  for _, r in regen_window.iterrows()
                  if r.get("scan_date") and r.get("symbol") and r.get("signal")}

    matched = live_keys & regen_keys
    missing_in_regen = live_keys - regen_keys
    extra_in_regen = regen_keys - live_keys

    match_pct = (len(matched) / len(live_keys) * 100) if live_keys else 0.0

    return {
        "match_pct": round(match_pct, 2),
        "regen_count": len(regen_keys),
        "live_count": len(live_keys),
        "matched_count": len(matched),
        "missing_in_regen": list(missing_in_regen)[:50],
        "extra_in_regen": list(extra_in_regen)[:50],
        "t2_passed": match_pct >= _MIN_MATCH_PCT,
        "t2_threshold_pct": _MIN_MATCH_PCT,
    }


def write_validation_report(report: dict) -> Path:
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_VALIDATION_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return _VALIDATION_REPORT


# ── Smoke test (synthetic data; verifies pipeline runs without cache) ─

def smoke_test() -> bool:
    """Verify pipeline functions importable + outcome compute works on
    synthetic data. Does NOT require cache (MS-1 may not have run yet)."""
    print("[signal_replayer] SMOKE: verifying detector import + outcome math")
    try:
        detect = _import_detector()
        print(f"  ✓ detect_signals importable: {detect.__name__}")
    except Exception as e:
        print(f"  ✗ detector import failed: {e}")
        return False

    # Synthetic OHLCV: 60 bars rising trend then breakout
    import numpy as np
    dates = pd.date_range("2024-01-01", periods=80, freq="B")
    base = np.linspace(100, 120, 80)
    df = pd.DataFrame({
        "Open": base + np.random.uniform(-0.5, 0.5, 80),
        "High": base + 1.0,
        "Low": base - 1.0,
        "Close": base,
        "Volume": np.random.uniform(100_000, 500_000, 80),
    }, index=dates)

    outcome = compute_d6_outcome(
        df, df.index[60], entry_price=110.0, stop_price=108.0, direction="LONG")
    print(f"  ✓ compute_d6_outcome works: {outcome.outcome} pnl={outcome.pnl_pct}%")
    return True


# ── CLI ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MS-2 Backtest Lab signal replayer + cross-validator")
    parser.add_argument("--smoke", action="store_true",
                        help="Smoke test: verify imports + outcome math (no cache needed)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Skip replay; cross-validate existing backtest_signals.parquet")
    parser.add_argument("--start", default=None,
                        help="Start date YYYY-MM-DD (default: full history)")
    parser.add_argument("--end", default=None,
                        help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--symbols", default=None,
                        help="Comma-separated subset for testing")
    args = parser.parse_args()

    if args.smoke:
        ok = smoke_test()
        return 0 if ok else 1

    if args.validate_only:
        if not _BACKTEST_SIGNALS.exists():
            print(f"[signal_replayer] {_BACKTEST_SIGNALS} not found; "
                  f"run replay first")
            return 1
        df = pd.read_parquet(_BACKTEST_SIGNALS)
        report = cross_validate_against_live(df)
        write_validation_report(report)
        print(json.dumps(report, indent=2, default=str))
        return 0 if report.get("t2_passed") else 2

    # Full replay
    if not _CACHE_DIR.exists() or not list(_CACHE_DIR.glob("*.parquet")):
        print("[signal_replayer] /lab/cache/ empty; run MS-1 data_fetcher first")
        return 1

    symbols_filter = args.symbols.split(",") if args.symbols else None
    print(f"[signal_replayer] Replaying universe; "
          f"start={args.start} end={args.end} "
          f"symbols={'subset:' + str(len(symbols_filter)) if symbols_filter else 'full'}")

    df = replay_universe(args.start, args.end, symbols_filter)
    if df.empty:
        print("[signal_replayer] No signals replayed")
        return 1

    _LAB_OUTPUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_BACKTEST_SIGNALS, compression="snappy")
    print(f"[signal_replayer] Wrote {len(df)} signals → "
          f"{_BACKTEST_SIGNALS.relative_to(_REPO_ROOT)}")

    # Cross-validation
    report = cross_validate_against_live(df)
    write_validation_report(report)
    print()
    print("=" * 72)
    print("CROSS-VALIDATION REPORT (T2 tripwire)")
    print("=" * 72)
    print(json.dumps({k: v for k, v in report.items()
                       if k not in ("missing_in_regen", "extra_in_regen")},
                      indent=2, default=str))

    if not report.get("t2_passed"):
        print(f"\n❌ T2 TRIPWIRE FIRED: match_pct {report.get('match_pct')}% "
              f"< {_MIN_MATCH_PCT}% threshold")
        return 2
    print(f"\n✅ T2 PASSED: match_pct {report.get('match_pct')}%")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(3)
