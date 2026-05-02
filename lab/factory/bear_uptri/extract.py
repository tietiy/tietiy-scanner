"""
Bear UP_TRI cell — B1: data extraction + descriptive comparison.

Pulls Bear UP_TRI combinations from Phase 5 outputs and splits them into
VALIDATED / PRELIMINARY / REJECTED / WATCH groups for comparative analysis.

NO new patterns generated. NO production code. Read-only EDA on Phase 1-5
artifacts.

Bear UP_TRI is the strongest cohort across the entire Lab pipeline:
  • 100% Phase 5 validation rate (87/87 evaluable)
  • 98 live signals at 94.6% WR
  • +38.9pp gap from 55.7% lifetime baseline (largest regime-shift artifact)

This module produces the comparison table that grounds B2 (differentiator
analysis) and B3 (filter articulation).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
_REPO_ROOT = _LAB_ROOT.parent

DEFAULT_INPUT = _LAB_ROOT / "output" / "combinations_live_validated.parquet"
LIVE_FEATURES_INPUT = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
DEFAULT_OUTPUT = _HERE / "comparison_stats.json"

GROUPS = ("VALIDATED", "PRELIMINARY", "REJECTED", "WATCH")


def load_bear_uptri(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Load Phase 5 output, filter to UP_TRI × Bear."""
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "UP_TRI")
                & (df["regime"] == "Bear")].copy()


def _safe_mean(s: pd.Series) -> Optional[float]:
    s = s.dropna()
    return float(s.mean()) if len(s) else None


def descriptive_stats(group_df: pd.DataFrame) -> dict:
    """Compute descriptive stats for one group."""
    n = len(group_df)
    if n == 0:
        return {"count": 0}

    edge = (group_df["test_wr"] - group_df["baseline_wr"]).dropna()
    return {
        "count": n,
        "lifetime": {
            "test_wr_mean": _safe_mean(group_df["test_wr"]),
            "test_wr_median": float(group_df["test_wr"].median())
                if group_df["test_wr"].notna().any() else None,
            "baseline_wr_mean": _safe_mean(group_df["baseline_wr"]),
            "edge_pp_mean": _safe_mean(edge),
            "drift_train_test_mean": _safe_mean(
                group_df["drift_train_test_pp"].abs()),
            "test_n_mean": _safe_mean(group_df["test_n"]),
            "test_n_median": float(group_df["test_n"].median())
                if group_df["test_n"].notna().any() else None,
        },
        "live": {
            "live_n_mean": _safe_mean(group_df["live_n"]),
            "live_n_median": float(group_df["live_n"].median())
                if group_df["live_n"].notna().any() else None,
            "live_n_total": int(group_df["live_n"].fillna(0).sum()),
            "live_w_total": int(group_df["live_n_wins"].fillna(0).sum()),
            "live_l_total": int(group_df["live_n_losses"].fillna(0).sum()),
            "live_wr_mean": _safe_mean(group_df["live_wr"]),
        },
        "horizon_distribution": (
            group_df["horizon"].value_counts().to_dict()),
        "phase_4_tier_distribution": (
            group_df["tier"].value_counts().to_dict()),
        "feature_count_distribution": (
            group_df["feature_count"].value_counts().sort_index().to_dict()),
    }


def descriptive_live_signals() -> dict:
    """Read live_signals_with_features.parquet to surface raw live universe.

    The combinations parquet stores per-pattern stats; raw signal-level
    breakdowns (sector, vol regime, calendar) require the feature-joined
    live signals file.
    """
    df = pd.read_parquet(LIVE_FEATURES_INPUT)
    sub = df[(df["regime"] == "Bear") & (df["signal"] == "UP_TRI")].copy()

    def _wlf(o: str) -> str:
        if o in ("DAY6_WIN", "TARGET_HIT"):
            return "W"
        if o in ("DAY6_LOSS", "STOP_HIT"):
            return "L"
        if o == "DAY6_FLAT":
            return "F"
        return "?"

    sub["wlf"] = sub["outcome"].apply(_wlf)
    nw = (sub["wlf"] == "W").sum()
    nl = (sub["wlf"] == "L").sum()
    nf = (sub["wlf"] == "F").sum()
    out = {
        "n_total": int(len(sub)),
        "n_w": int(nw),
        "n_l": int(nl),
        "n_f": int(nf),
        "wr_excl_flat": float(nw / (nw + nl)) if (nw + nl) > 0 else None,
    }
    if "sector" in sub.columns:
        out["sector_distribution"] = sub["sector"].value_counts().head(15).to_dict()
        # WR by sector
        sec_wr = {}
        for sec, grp in sub.groupby("sector"):
            grw = (grp["wlf"] == "W").sum()
            grl = (grp["wlf"] == "L").sum()
            if grw + grl > 0:
                sec_wr[str(sec)] = {
                    "n": int(len(grp)),
                    "wr": float(grw / (grw + grl)),
                }
        out["sector_wr"] = sec_wr
    if "feat_nifty_vol_regime" in sub.columns:
        out["vol_regime_distribution"] = (
            sub["feat_nifty_vol_regime"].value_counts().to_dict())
    if "feat_day_of_week" in sub.columns:
        out["day_of_week_distribution"] = (
            sub["feat_day_of_week"].value_counts().to_dict())
    return out


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    """Run full extraction + descriptive comparison."""
    df = load_bear_uptri(input_path)
    out = {
        "total_bear_uptri": len(df),
        "horizon_breakdown": df["horizon"].value_counts().to_dict(),
        "groups": {},
        "live_signal_universe": descriptive_live_signals(),
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def _print_summary_table(stats: dict) -> None:
    """Surface comparison summary to terminal."""
    print()
    print("═" * 80)
    print("Bear UP_TRI — descriptive comparison across groups")
    print("═" * 80)
    print(f"\nTotal Bear UP_TRI combinations: {stats['total_bear_uptri']}")
    print(f"Horizon split: {stats['horizon_breakdown']}")

    cols = list(GROUPS)
    print(f"\n{'metric':<35}", end="")
    for c in cols:
        print(f"{c:>14}", end="")
    print()
    print("─" * (35 + 14 * len(cols)))

    def _row(label, getter):
        print(f"{label:<35}", end="")
        for c in cols:
            g = stats["groups"].get(c, {})
            v = getter(g)
            if v is None:
                cell = "—"
            elif isinstance(v, float):
                cell = f"{v:.3f}"
            else:
                cell = str(v)
            print(f"{cell:>14}", end="")
        print()

    _row("count", lambda g: g.get("count"))
    _row("test_wr (mean)",
          lambda g: g.get("lifetime", {}).get("test_wr_mean"))
    _row("baseline_wr (mean)",
          lambda g: g.get("lifetime", {}).get("baseline_wr_mean"))
    _row("edge_pp (mean)",
          lambda g: g.get("lifetime", {}).get("edge_pp_mean"))
    _row("drift train→test (mean)",
          lambda g: g.get("lifetime", {}).get("drift_train_test_mean"))
    _row("test_n (mean)",
          lambda g: g.get("lifetime", {}).get("test_n_mean"))
    _row("live_n total",
          lambda g: g.get("live", {}).get("live_n_total"))
    _row("live_w total",
          lambda g: g.get("live", {}).get("live_w_total"))
    _row("live_l total",
          lambda g: g.get("live", {}).get("live_l_total"))
    _row("live_wr (mean of combos)",
          lambda g: g.get("live", {}).get("live_wr_mean"))

    print()
    print("Horizon distribution per group:")
    for c in cols:
        h = stats["groups"].get(c, {}).get("horizon_distribution", {})
        print(f"  {c}: {h}")

    print()
    print("Phase 4 tier distribution per group:")
    for c in cols:
        t = stats["groups"].get(c, {}).get("phase_4_tier_distribution", {})
        print(f"  {c}: {t}")

    print()
    print("Feature count distribution per group:")
    for c in cols:
        fc = stats["groups"].get(c, {}).get("feature_count_distribution", {})
        print(f"  {c}: {fc}")

    # Live universe surface
    lu = stats.get("live_signal_universe", {})
    print()
    print("─" * 80)
    print("Bear UP_TRI live signal universe (signal-level)")
    print("─" * 80)
    print(f"  n total = {lu.get('n_total')}")
    print(f"  W={lu.get('n_w')}, L={lu.get('n_l')}, F={lu.get('n_f')}")
    if lu.get("wr_excl_flat") is not None:
        print(f"  baseline WR (excl flat) = {lu['wr_excl_flat']*100:.1f}%")
    if "sector_distribution" in lu:
        print(f"\n  Sector distribution:")
        for sec, cnt in list(lu["sector_distribution"].items())[:13]:
            wr_info = lu.get("sector_wr", {}).get(sec, {})
            wr_str = (f"  WR={wr_info.get('wr', 0)*100:.1f}%"
                      if "wr" in wr_info else "")
            print(f"    {sec:<12} n={cnt:>3}{wr_str}")
    if "vol_regime_distribution" in lu:
        print(f"\n  Vol regime distribution:")
        for vol, cnt in lu["vol_regime_distribution"].items():
            print(f"    {vol:<10} n={cnt}")
    if "day_of_week_distribution" in lu:
        print(f"\n  Day-of-week distribution:")
        for dow, cnt in lu["day_of_week_distribution"].items():
            print(f"    {dow:<6} n={cnt}")


def main():
    print("─" * 80)
    print("CELL: Bear UP_TRI — B1 data extraction + descriptive comparison")
    print("─" * 80)
    stats = build_comparison_stats()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nSaved: {DEFAULT_OUTPUT}")
    _print_summary_table(stats)

    # Initial observations surface
    print()
    print("═" * 80)
    print("Initial observations")
    print("═" * 80)
    g = stats["groups"]
    val_n = g.get("VALIDATED", {}).get("count", 0)
    pre_n = g.get("PRELIMINARY", {}).get("count", 0)
    rej_n = g.get("REJECTED", {}).get("count", 0)
    watch_n = g.get("WATCH", {}).get("count", 0)
    winners = val_n + pre_n
    evaluable = winners + rej_n
    if evaluable > 0:
        print(f"\nWinners (V+P): {winners} | Rejected: {rej_n} | "
              f"Watch: {watch_n}")
        print(f"Validation rate among evaluable: {winners/evaluable*100:.1f}% "
              f"({winners}/{evaluable})")
    val_test_wr = (g.get("VALIDATED", {}).get("lifetime", {}).get("test_wr_mean")
                     or 0)
    pre_test_wr = (g.get("PRELIMINARY", {}).get("lifetime", {}).get("test_wr_mean")
                     or 0)
    watch_test_wr = (g.get("WATCH", {}).get("lifetime", {}).get("test_wr_mean")
                       or 0)
    print(f"\nLifetime test_wr: VALIDATED {val_test_wr*100:.1f}% / "
          f"PRELIMINARY {pre_test_wr*100:.1f}% / "
          f"WATCH {watch_test_wr*100:.1f}%")
    val_drift = g.get("VALIDATED", {}).get("lifetime", {}).get(
        "drift_train_test_mean")
    if val_drift is not None:
        print(f"Lifetime drift train→test: VALIDATED {val_drift*100:.1f}pp")

    # Live regime gap
    lu = stats.get("live_signal_universe", {})
    if lu.get("wr_excl_flat"):
        live_wr = lu["wr_excl_flat"]
        gap = (live_wr * 100) - 55.7  # lifetime Bear UP_TRI baseline
        print(f"\nLive vs lifetime gap: live {live_wr*100:.1f}% − "
              f"lifetime baseline 55.7% = {gap:+.1f}pp")
        print("  ⚠ This is the largest regime-shift artifact in Lab data.")
        print("  ⚠ Cell findings expected to weaken at lifetime "
              "validation in Session 2.")


if __name__ == "__main__":
    main()
