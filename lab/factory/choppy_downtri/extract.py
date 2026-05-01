"""
Choppy DOWN_TRI cell — C1: data extraction + descriptive comparison.

Note: Phase 5 produced ALL 25 Choppy DOWN_TRI Phase-5 entries in WATCH tier
(insufficient live data per combination). Live universe is 3 signals (all
losses). This cell will be DEFERRED — descriptive analysis only, no
filter back-test possible (no winners-vs-rejected split).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

# Reuse shared logic from choppy_uptri/extract.py
sys.path.insert(0, str(_LAB_ROOT / "factory" / "choppy_uptri"))
from extract import descriptive_stats, GROUPS  # noqa: E402

DEFAULT_INPUT = _LAB_ROOT / "output" / "combinations_live_validated.parquet"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_PATH = _HERE / "comparison_stats.json"


def load_choppy_downtri(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "DOWN_TRI")
                & (df["regime"] == "Choppy")].copy()


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    df = load_choppy_downtri(input_path)
    out = {
        "total_choppy_downtri": len(df),
        "horizon_breakdown": df["horizon"].value_counts().to_dict(),
        "groups": {},
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def build_live_universe_stats() -> dict:
    """Live Choppy DOWN_TRI signals — n=3 in current data window."""
    live = pd.read_parquet(LIVE_PATH)
    cd = live[(live["signal"] == "DOWN_TRI")
                 & (live["regime"] == "Choppy")].copy()
    n = len(cd)
    nw = int((cd["wlf"] == "W").sum())
    nl = int((cd["wlf"] == "L").sum())
    nf = int((cd["wlf"] == "F").sum())
    sample = []
    for _, r in cd.iterrows():
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
    print("CELL 2: Choppy DOWN_TRI — C1 data extraction + descriptive comparison")
    print("─" * 80)
    stats = build_comparison_stats()
    live_stats = build_live_universe_stats()
    out = {**stats, "live_universe": live_stats}
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"\nTotal Choppy DOWN_TRI combinations: {stats['total_choppy_downtri']}")
    print(f"Horizon split: {stats['horizon_breakdown']}")
    print(f"\nPhase 5 tier distribution:")
    for tier in GROUPS:
        n = stats["groups"][tier].get("count", 0)
        if n > 0:
            ld = stats["groups"][tier].get("lifetime", {})
            tw = ld.get("test_wr_mean")
            tw_str = f"{tw*100:.1f}%" if tw else "—"
            print(f"  {tier}: {n} combinations  (lifetime test_wr={tw_str})")
        else:
            print(f"  {tier}: 0 combinations")

    print(f"\nLive Choppy DOWN_TRI universe:")
    print(f"  n={live_stats['n_live']}  W={live_stats['n_w']}  "
          f"L={live_stats['n_l']}  F={live_stats['n_f']}")
    if live_stats["live_wr_excl_f"] is not None:
        print(f"  baseline live WR (excl F): {live_stats['live_wr_excl_f']*100:.1f}%")
    print(f"\n  Live signals:")
    for s in live_stats["sample_signals"]:
        print(f"    {s['symbol']:<14} {s['date']:<12} {s['wlf']:<3} "
              f"pnl={s['pnl_pct']:+.2f}%  outcome={s['outcome']}")

    # DEFERRED determination
    print()
    print("═" * 80)
    print("CELL VERDICT")
    print("═" * 80)
    n_live = live_stats["n_live"]
    n_winners = sum(1 for tier in ("VALIDATED", "PRELIMINARY")
                       for _ in [stats["groups"][tier].get("count", 0)]
                       if _ > 0)
    val_n = stats["groups"]["VALIDATED"]["count"]
    pre_n = stats["groups"]["PRELIMINARY"]["count"]
    rej_n = stats["groups"]["REJECTED"]["count"]
    if val_n + pre_n == 0 and rej_n == 0:
        verdict = "DEFERRED"
        print(f"\nALL 25 Phase 5 combinations in WATCH tier (no VALIDATED/REJECTED split).")
        print(f"Live universe = {n_live} signals (all losses) — below 8-signal threshold.")
        print(f"\nCELL CLASSIFICATION: DEFERRED")
        print("  Cannot perform winner-vs-rejected differentiator analysis "
              "(no winners or rejected exist).")
        print("  Cannot perform filter back-test (live n too small).")
        print("  Cell deferred until quarterly Phase 5 re-run accumulates more "
              "Choppy DOWN_TRI live signals.")


if __name__ == "__main__":
    main()
