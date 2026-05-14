"""kill_002 outcome tracker.

Tracks the would-be P&L of DOWN_TRI signals that kill_002 rejected.
We do not trade them — we just record what they would have done.

Workflow:
- `init` mode (run once on rejection day): read scan_log.json and
  capture each rejected DOWN_TRI as a pending entry in
  output/kill_002_tracking.json.
- `update` mode (run on subsequent trading days): for each pending
  entry, fetch the latest price via yfinance and check whether the
  short would have hit stop, target, or completed 6-day timeout.

Hard rule: this script reads scan_log + writes its own tracking file
only. It does not touch production state.

Usage:
    .venv/bin/python scripts/kill_002_tracker.py init
    .venv/bin/python scripts/kill_002_tracker.py update
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta
from typing import Optional

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_LOG = os.path.join(REPO, "output", "scan_log.json")
TRACK_PATH = os.path.join(REPO, "output", "kill_002_tracking.json")
HOLDING_DAYS = 6  # Day-6 exit per scanner convention


def _today() -> str:
    return date.today().isoformat()


def _load_tracking() -> dict:
    if os.path.exists(TRACK_PATH):
        with open(TRACK_PATH) as fh:
            return json.load(fh)
    return {"schema_version": 1, "created_at": _today(), "trades": []}


def _save_tracking(data: dict) -> None:
    with open(TRACK_PATH, "w") as fh:
        json.dump(data, fh, indent=2, default=str)


def _trading_days_between(start: str, end: str) -> int:
    """Count NSE-ish trading days between two ISO dates (weekdays only,
    no holiday calendar — close enough for a 6-day window)."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    days = 0
    cur = s + timedelta(days=1)
    while cur <= e:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


def cmd_init() -> int:
    with open(SCAN_LOG) as fh:
        sl = json.load(fh)
    rejection_date = sl.get("date") or sl.get("scan_date") or _today()
    rejected = [r for r in sl.get("rejected", []) if r.get("signal") == "DOWN_TRI"]

    tracking = _load_tracking()
    existing_ids = {t["id"] for t in tracking["trades"]}
    new_count = 0
    for r in rejected:
        trade_id = f"{rejection_date}-{r['symbol']}"
        if trade_id in existing_ids:
            continue
        tracking["trades"].append({
            "id": trade_id,
            "rejection_date": rejection_date,
            "rejection_rule": "kill_002",
            "symbol": r["symbol"],
            "signal": r["signal"],
            "direction": r.get("direction", "SHORT"),
            "sector": r.get("sector"),
            "entry_price": r.get("entry_est"),
            "stop_price": r.get("stop"),
            "target_price": r.get("target_price"),
            "pivot_price": r.get("pivot_price"),
            "days_held": 0,
            "status": "pending",
            "outcome": None,
            "exit_price": None,
            "exit_date": None,
            "would_be_pnl_pct": None,
            "last_checked": None,
        })
        new_count += 1

    tracking["last_init"] = _today()
    _save_tracking(tracking)
    print(f"init: captured {new_count} new trades (total tracked: {len(tracking['trades'])})")
    for t in tracking["trades"][-new_count:] if new_count else []:
        print(f"  {t['id']:40} entry={t['entry_price']:>9.2f} stop={t['stop_price']:>9.2f} target={t['target_price']:>9.2f}")
    return 0


def _fetch_history_since(symbol: str, start_date: str):
    """Return DataFrame of daily OHLCV for symbol from start_date through today.
    Empty DataFrame on any failure."""
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        df = t.history(start=start_date, auto_adjust=False)
        return df
    except Exception as e:
        print(f"  WARN: yfinance failed for {symbol}: {e}")
        import pandas as pd
        return pd.DataFrame()


def _resolve(trade: dict) -> Optional[dict]:
    """For a pending trade, fetch history since rejection_date and
    determine whether stop / target / day-6 exit was hit. Returns the
    fields to merge into the trade dict, or None on fetch failure."""
    df = _fetch_history_since(trade["symbol"], trade["rejection_date"])
    if df.empty:
        return None

    stop = trade["stop_price"]
    target = trade["target_price"]
    entry = trade["entry_price"]
    rejection_dt = date.fromisoformat(trade["rejection_date"])

    # Walk bars in order (skip the rejection-day bar — short would have
    # been opened next day at trade["entry_price"]). For each bar test
    # whether the bar's High >= stop (short stopped out) or Low <= target
    # (short hit target). Tie-break: if both occur same bar, assume stop
    # (worst case for the short).
    days_held = 0
    result = None
    for ts, row in df.iterrows():
        bar_date = ts.date() if hasattr(ts, "date") else ts
        if bar_date <= rejection_dt:
            continue
        days_held += 1
        high = float(row["High"])
        low = float(row["Low"])
        # Stop loss for a short = stock price rises to stop_price
        if high >= stop:
            result = {
                "outcome": "stop_hit",
                "status": "resolved",
                "exit_price": stop,
                "exit_date": str(bar_date),
                "days_held": days_held,
            }
            break
        if low <= target:
            result = {
                "outcome": "target_hit",
                "status": "resolved",
                "exit_price": target,
                "exit_date": str(bar_date),
                "days_held": days_held,
            }
            break
        if days_held >= HOLDING_DAYS:
            close = float(row["Close"])
            result = {
                "outcome": "day6_exit",
                "status": "resolved",
                "exit_price": close,
                "exit_date": str(bar_date),
                "days_held": days_held,
            }
            break

    if result is None:
        # Still tracking — no exit signal hit yet, fewer than 6 trading days elapsed
        last_close = float(df["Close"].iloc[-1])
        last_date = df.index[-1].date()
        return {
            "outcome": None,
            "status": "pending",
            "exit_price": None,
            "exit_date": None,
            "days_held": days_held,
            "last_close": last_close,
            "last_date": str(last_date),
        }

    # P&L for a SHORT: gain when price falls. (entry - exit) / entry * 100
    result["would_be_pnl_pct"] = round((entry - result["exit_price"]) / entry * 100.0, 2)
    return result


def cmd_update() -> int:
    tracking = _load_tracking()
    pending = [t for t in tracking["trades"] if t["status"] == "pending"]
    print(f"update: {len(pending)} pending trade(s) to check")
    if not pending:
        return 0

    today = _today()
    resolved_now = 0
    for t in pending:
        # Avoid spamming yfinance: only fetch if today > rejection_date
        if t["rejection_date"] >= today:
            print(f"  {t['symbol']}: skipped (rejection_date {t['rejection_date']} is today or future)")
            continue
        upd = _resolve(t)
        if upd is None:
            print(f"  {t['symbol']}: fetch failure — left as pending")
            continue
        t.update(upd)
        t["last_checked"] = today
        if upd["status"] == "resolved":
            resolved_now += 1
            print(f"  {t['symbol']}: RESOLVED outcome={upd['outcome']} "
                  f"exit={upd['exit_price']:.2f} pnl={upd['would_be_pnl_pct']:+.2f}% "
                  f"(days_held={upd['days_held']})")
        else:
            print(f"  {t['symbol']}: still pending — days_held={upd['days_held']} last_close={upd.get('last_close')}")

    tracking["last_update"] = today
    _save_tracking(tracking)

    # Summary
    resolved = [t for t in tracking["trades"] if t["status"] == "resolved"]
    if resolved:
        wins = [t for t in resolved if t["outcome"] == "target_hit"]
        losses = [t for t in resolved if t["outcome"] == "stop_hit"]
        flats = [t for t in resolved if t["outcome"] == "day6_exit"]
        avg_pnl = sum(t["would_be_pnl_pct"] for t in resolved) / len(resolved)
        print(f"\nResolved cohort: n={len(resolved)} "
              f"target_hit={len(wins)} stop_hit={len(losses)} day6_exit={len(flats)} "
              f"avg_would_be_pnl={avg_pnl:+.2f}%")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["init", "update"])
    args = p.parse_args(argv)
    if args.mode == "init":
        return cmd_init()
    return cmd_update()


if __name__ == "__main__":
    sys.exit(main())
