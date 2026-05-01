"""
Choppy BULL_PROXY cell — C1: data extraction + descriptive comparison.

Phase 5 reported 0% validation rate for this cohort (96 REJECTED, 0 VALIDATED,
0 PRELIMINARY, 79 WATCH from 175 Phase-4 survivors). Live universe is 8 signals
(2W / 6L → 25% WR).

Investigation goal: confirm cohort is structurally dead OR find narrow
exception via REJECTED-vs-WATCH differentiator + live-signal feature audit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

sys.path.insert(0, str(_LAB_ROOT / "factory" / "choppy_uptri"))
from extract import descriptive_stats, GROUPS  # noqa: E402

DEFAULT_INPUT = _LAB_ROOT / "output" / "combinations_live_validated.parquet"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "comparison_stats.json"


def load_choppy_bullproxy(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "BULL_PROXY")
                & (df["regime"] == "Choppy")].copy()


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    df = load_choppy_bullproxy(input_path)
    out = {
        "total_choppy_bullproxy": len(df),
        "horizon_breakdown": df["horizon"].value_counts().to_dict(),
        "groups": {},
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def build_live_universe_stats() -> dict:
    """Live Choppy BULL_PROXY signals — n=8 in current data window."""
    live = pd.read_parquet(LIVE_PATH)
    cb = live[(live["signal"] == "BULL_PROXY")
                 & (live["regime"] == "Choppy")].copy()
    n = len(cb)
    nw = int((cb["wlf"] == "W").sum())
    nl = int((cb["wlf"] == "L").sum())
    nf = int((cb["wlf"] == "F").sum())
    sample = []
    for _, r in cb.iterrows():
        sample.append({
            "id": r.get("id"),
            "symbol": r.get("symbol"),
            "date": str(r.get("date"))[:10],
            "outcome": r.get("outcome"),
            "wlf": r.get("wlf"),
            "pnl_pct": float(r["pnl_pct"]) if pd.notna(r.get("pnl_pct")) else None,
        })
    return {
        "n_live": n,
        "n_w": nw, "n_l": nl, "n_f": nf,
        "live_wr_excl_f": (nw / (nw + nl)) if (nw + nl) > 0 else None,
        "sample_signals": sample,
    }


def main():
    print("─" * 80)
    print("CELL 3: Choppy BULL_PROXY — C1 data extraction + descriptive comparison")
    print("─" * 80)
    stats = build_comparison_stats()
    live_stats = build_live_universe_stats()
    out = {**stats, "live_universe": live_stats}
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"\nTotal Choppy BULL_PROXY combinations: {stats['total_choppy_bullproxy']}")
    print(f"Horizon split: {stats['horizon_breakdown']}")

    print(f"\nPhase 5 tier distribution:")
    for tier in GROUPS:
        n = stats["groups"][tier].get("count", 0)
        if n > 0:
            ld = stats["groups"][tier].get("lifetime", {})
            tw = ld.get("test_wr_mean")
            edge = ld.get("edge_pp_mean")
            tw_str = f"{tw*100:.1f}%" if tw else "—"
            edge_str = f"{edge*100:+.1f}pp" if edge is not None else "—"
            print(f"  {tier}: {n} combinations  (lifetime test_wr={tw_str}, edge={edge_str})")
        else:
            print(f"  {tier}: 0 combinations")

    print(f"\nLive Choppy BULL_PROXY universe:")
    print(f"  n={live_stats['n_live']}  W={live_stats['n_w']}  "
          f"L={live_stats['n_l']}  F={live_stats['n_f']}")
    if live_stats["live_wr_excl_f"] is not None:
        print(f"  baseline live WR (excl F): {live_stats['live_wr_excl_f']*100:.1f}%")
    print(f"\n  Live signals:")
    for s in live_stats["sample_signals"]:
        marker = "★" if s["wlf"] == "W" else " "
        print(f"   {marker}{s['symbol']:<14} {s['date']:<12} {s['wlf']:<3} "
              f"pnl={s['pnl_pct']:+.2f}%  outcome={s['outcome']}")


if __name__ == "__main__":
    main()
