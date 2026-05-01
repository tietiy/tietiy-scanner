"""
Choppy UP_TRI cell — C1: data extraction + descriptive comparison.

Pulls Choppy UP_TRI combinations from Phase 5 outputs and splits them into
VALIDATED / PRELIMINARY / REJECTED / WATCH groups for comparative analysis.

NO new patterns generated. NO production code. Read-only EDA on Phase 1-5
artifacts.
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
DEFAULT_OUTPUT = _HERE / "comparison_stats.json"

GROUPS = ("VALIDATED", "PRELIMINARY", "REJECTED", "WATCH")


def load_choppy_uptri(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Load Phase 5 output, filter to UP_TRI × Choppy."""
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "UP_TRI")
                & (df["regime"] == "Choppy")].copy()


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


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    """Run full extraction + descriptive comparison."""
    df = load_choppy_uptri(input_path)
    out = {
        "total_choppy_uptri": len(df),
        "horizon_breakdown": df["horizon"].value_counts().to_dict(),
        "groups": {},
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def _print_summary_table(stats: dict) -> None:
    """Surface comparison summary to terminal."""
    print()
    print("═" * 80)
    print("Choppy UP_TRI — descriptive comparison across groups")
    print("═" * 80)
    print(f"\nTotal Choppy UP_TRI combinations: {stats['total_choppy_uptri']}")
    print(f"Horizon split: {stats['horizon_breakdown']}")

    # Header row
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


def main():
    print("─" * 80)
    print("CELL 1: Choppy UP_TRI — C1 data extraction + descriptive comparison")
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
    rej_test_wr = (g.get("REJECTED", {}).get("lifetime", {}).get("test_wr_mean")
                     or 0)
    if val_test_wr and rej_test_wr:
        print(f"\nLifetime test_wr: VALIDATED {val_test_wr*100:.1f}% vs "
              f"REJECTED {rej_test_wr*100:.1f}% — "
              f"{'similar' if abs(val_test_wr-rej_test_wr) < 0.02 else 'different'}")
    val_drift = g.get("VALIDATED", {}).get("lifetime", {}).get(
        "drift_train_test_mean")
    rej_drift = g.get("REJECTED", {}).get("lifetime", {}).get(
        "drift_train_test_mean")
    if val_drift is not None and rej_drift is not None:
        print(f"Lifetime drift: VALIDATED {val_drift*100:.1f}pp vs "
              f"REJECTED {rej_drift*100:.1f}pp")


if __name__ == "__main__":
    main()
