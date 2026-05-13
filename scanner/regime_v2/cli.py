"""CLI entry point for regime_v2.

Usage:
    python -m scanner.regime_v2 --backfill \
        --from 2011-01-01 --to 2026-05-05 \
        --nifty data/historical/nifty.parquet \
        --banknifty data/historical/banknifty.parquet \
        --out output/regime_v2/regime_historical.parquet
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

import pandas as pd

from .classifier import classify_regime
from .features import compute_features
from .io import load_ohlcv, write_jsonl
from .transitions import apply_persistence


def cmd_backfill(args) -> int:
    print(f"[regime_v2] backfill {args._from} → {args.to}")
    ohlcv = load_ohlcv(args.nifty)
    print(f"  loaded nifty: shape={ohlcv.shape} range={ohlcv.index.min()}→{ohlcv.index.max()}")

    bk: Optional[pd.DataFrame] = None
    if args.banknifty and os.path.exists(args.banknifty):
        bk = load_ohlcv(args.banknifty)
        print(f"  loaded banknifty: shape={bk.shape}")

    vix_series: Optional[pd.Series] = None
    if args.vix and os.path.exists(args.vix):
        vix_df = load_ohlcv(args.vix)
        vix_series = vix_df["Close"].astype(float)
        print(f"  loaded vix: shape={vix_df.shape}")
    else:
        print("  vix: NOT AVAILABLE — running in degraded mode (design §04 'VIX missing')")

    # Filter date range
    start = pd.Timestamp(args._from)
    end = pd.Timestamp(args.to)
    ohlcv = ohlcv.loc[(ohlcv.index >= start) & (ohlcv.index <= end)]
    if bk is not None:
        bk = bk.loc[(bk.index >= start) & (bk.index <= end)]

    # Compute features
    feats = compute_features(ohlcv, banknifty_ohlcv=bk, vix_series=vix_series)
    print(f"  computed features: shape={feats.shape}")

    # Classify each bar (raw states, ignoring persistence)
    raw_states = []
    gate_traces = []
    for ts, row in feats.iterrows():
        feat_dict = {col: (None if pd.isna(val) else val) for col, val in row.items()}
        state, conf, trace = classify_regime(feat_dict)
        raw_states.append(state)
        gate_traces.append(trace)

    raw_series = pd.Series(raw_states, index=feats.index, name="state_raw")

    # Apply persistence
    smoothed, regime_pending, conf_pending, tlog = apply_persistence(raw_series)
    print(f"  raw transitions: {(raw_series != raw_series.shift()).sum()}")
    print(f"  smoothed transitions: {len(tlog)}")

    # Build output frame
    out = pd.DataFrame({
        "state_raw": raw_series,
        "state": smoothed,
        "regime_pending": regime_pending,
        "confidence_pending": conf_pending,
    })
    for col in ["nifty_close", "slope_10d_ema50", "above_ema50", "above_ema200",
                "ret20_pct", "realized_vol_20d_pct", "india_vix",
                "vix_change_10d_pct", "banknifty_rs_pp"]:
        if col in feats.columns:
            out[col] = feats[col]

    # Write outputs
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_parquet(args.out)
    print(f"  wrote {args.out} ({out.shape[0]} rows)")

    # Write transition log
    tlog_path = args.out.replace(".parquet", "_transitions.jsonl")
    with open(tlog_path, "w") as f:
        for t in tlog:
            f.write(json.dumps(t) + "\n")
    print(f"  wrote {tlog_path} ({len(tlog)} transitions)")

    # State distribution summary
    print("\n  state distribution (smoothed):")
    dist = out["state"].value_counts()
    for state, n in dist.items():
        print(f"    {state:18} {n:>5}  ({n/len(out)*100:.1f}%)")

    return 0


def cmd_side_by_side(args) -> int:
    """Compute V2 for a single date and append to comparison log."""
    print(f"[regime_v2] single-date classify {args.date}")
    ohlcv = load_ohlcv(args.nifty)
    bk = load_ohlcv(args.banknifty) if args.banknifty and os.path.exists(args.banknifty) else None
    vix_series = load_ohlcv(args.vix)["Close"] if args.vix and os.path.exists(args.vix) else None
    feats = compute_features(ohlcv, banknifty_ohlcv=bk, vix_series=vix_series)
    target = pd.Timestamp(args.date)
    if target not in feats.index:
        print(f"  date {args.date} not in features index")
        return 1
    row = feats.loc[target]
    feat_dict = {col: (None if pd.isna(val) else val) for col, val in row.items()}
    state, conf, trace = classify_regime(feat_dict)
    rec = {
        "date": str(target.date()),
        "state": state,
        "confidence": conf,
        "features": feat_dict,
        "gate_trace": trace,
    }
    print(json.dumps(rec, default=str, indent=2))
    write_jsonl(rec, args.out)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="scanner.regime_v2")
    sub = p.add_subparsers(dest="cmd", required=False)

    pb = sub.add_parser("backfill", help="Backfill historical regime labels")
    pb.add_argument("--from", dest="_from", required=True)
    pb.add_argument("--to", required=True)
    pb.add_argument("--nifty", required=True)
    pb.add_argument("--banknifty", default=None)
    pb.add_argument("--vix", default=None)
    pb.add_argument("--out", default="output/regime_v2/regime_historical.parquet")
    pb.set_defaults(func=cmd_backfill)

    ps = sub.add_parser("side-by-side", help="Single-date classification")
    ps.add_argument("--date", required=True)
    ps.add_argument("--nifty", required=True)
    ps.add_argument("--banknifty", default=None)
    ps.add_argument("--vix", default=None)
    ps.add_argument("--out", default="output/regime_v2/side_by_side.jsonl")
    ps.set_defaults(func=cmd_side_by_side)

    # Support legacy `--backfill` style for the spec
    legacy = argparse.ArgumentParser(add_help=False)
    legacy.add_argument("--backfill", action="store_true")
    if argv is None:
        argv = sys.argv[1:]
    if "--backfill" in argv:
        # Rewrite to subcommand
        new_argv = ["backfill"] + [a for a in argv if a != "--backfill"]
        argv = new_argv

    args = p.parse_args(argv)
    if not hasattr(args, "func"):
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
