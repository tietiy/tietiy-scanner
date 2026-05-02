"""
Bear DOWN_TRI cell — D1: data extraction + descriptive comparison +
thin-data assessment.

Bear DOWN_TRI is the contrarian short signal in Bear regime. Per T3
plan + Bear UP_TRI cell completion notes, this cell is expected to be
data-thin — possibly DEFERRED outcome.

Key context:
  • Lifetime baseline ~46.1% WR (n≈3,640) — moderate, not strong
  • Live n=11 (April 2026): 2 wins / 9 losses = 18.2% WR
  • 6 of 11 live signals in Bank sector (kill_001 cohort, 0 wins)
  • Phase 5: 19 combinations total, ALL WATCH (0 V / 0 P / 0 R)

Because Phase 5 has 0 VALIDATED + 0 PRELIMINARY (every combo is WATCH
due to insufficient live matches), the standard winners-vs-rejected
differentiator analysis cannot run as it does for Bear UP_TRI. This
module documents that constraint explicitly and proposes alternative
analysis paths (kill_001 extension, lifetime baseline as production
guide).

This module produces the comparison table that grounds D2 (differentiator
analysis) and D3 (verdict articulation).
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
ENRICHED_INPUT = _LAB_ROOT / "output" / "enriched_signals.parquet"
DEFAULT_OUTPUT = _HERE / "comparison_stats.json"

GROUPS = ("VALIDATED", "PRELIMINARY", "REJECTED", "WATCH")


def load_bear_downtri(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Load Phase 5 output, filter to DOWN_TRI × Bear."""
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "DOWN_TRI")
                & (df["regime"] == "Bear")].copy()


def _safe_mean(s: pd.Series) -> Optional[float]:
    s = s.dropna()
    return float(s.mean()) if len(s) else None


def descriptive_stats(group_df: pd.DataFrame) -> dict:
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
    """Read live_signals_with_features.parquet to surface raw live universe."""
    df = pd.read_parquet(LIVE_FEATURES_INPUT)
    sub = df[(df["regime"] == "Bear") & (df["signal"] == "DOWN_TRI")].copy()

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

    # Per-signal breakdown (n=11 is small, list each)
    out["signals"] = []
    for _, r in sub.iterrows():
        out["signals"].append({
            "date": str(r["date"]) if "date" in sub.columns else None,
            "symbol": r["symbol"],
            "sector": r["sector"],
            "outcome": r["outcome"],
            "wlf": r["wlf"],
            "feat_ema_alignment": r.get("feat_ema_alignment"),
            "feat_MACD_signal": r.get("feat_MACD_signal"),
            "feat_market_breadth_pct": r.get("feat_market_breadth_pct"),
            "feat_nifty_vol_regime": r.get("feat_nifty_vol_regime"),
            "feat_nifty_60d_return_pct": r.get("feat_nifty_60d_return_pct"),
            "feat_day_of_week": r.get("feat_day_of_week"),
        })

    if "sector" in sub.columns:
        out["sector_distribution"] = sub["sector"].value_counts().to_dict()
        sec_wr = {}
        for sec, grp in sub.groupby("sector"):
            grw = (grp["wlf"] == "W").sum()
            grl = (grp["wlf"] == "L").sum()
            sec_wr[str(sec)] = {
                "n": int(len(grp)),
                "w": int(grw), "l": int(grl),
                "wr": float(grw / (grw + grl)) if (grw + grl) > 0 else None,
            }
        out["sector_wr"] = sec_wr

    if "feat_nifty_vol_regime" in sub.columns:
        out["vol_regime_distribution"] = (
            sub["feat_nifty_vol_regime"].value_counts().to_dict())

    return out


def descriptive_lifetime() -> dict:
    """Lifetime Bear DOWN_TRI baseline + sector breakdown."""
    df = pd.read_parquet(ENRICHED_INPUT)
    bd = df[(df["regime"] == "Bear") & (df["signal"] == "DOWN_TRI")].copy()
    bd_wl = bd[bd["outcome"].isin(["DAY6_WIN", "TARGET_HIT",
                                          "DAY6_LOSS", "STOP_HIT",
                                          "DAY6_FLAT"])].copy()

    def _wlf(o):
        if o in ("DAY6_WIN", "TARGET_HIT"):
            return "W"
        if o in ("DAY6_LOSS", "STOP_HIT"):
            return "L"
        if o == "DAY6_FLAT":
            return "F"
        return "?"

    bd_wl["wlf"] = bd_wl["outcome"].apply(_wlf)
    nw = (bd_wl["wlf"] == "W").sum()
    nl = (bd_wl["wlf"] == "L").sum()
    nf = (bd_wl["wlf"] == "F").sum()
    baseline_wr = nw / (nw + nl) if (nw + nl) > 0 else None

    # Sector × WR
    sec_wr = {}
    for sec, grp in bd_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        grw = (grp["wlf"] == "W").sum()
        grl = (grp["wlf"] == "L").sum()
        if grw + grl < 50:  # min n for sector reporting
            continue
        sec_wr[str(sec)] = {
            "n": int(len(grp)),
            "wr": float(grw / (grw + grl)) if (grw + grl) > 0 else None,
        }

    return {
        "n_total": int(len(bd_wl)),
        "n_w": int(nw), "n_l": int(nl), "n_f": int(nf),
        "baseline_wr": float(baseline_wr) if baseline_wr is not None else None,
        "sector_wr": sec_wr,
    }


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    df = load_bear_downtri(input_path)
    out = {
        "total_bear_downtri_combos": len(df),
        "horizon_breakdown": df["horizon"].value_counts().to_dict(),
        "groups": {},
        "live_signal_universe": descriptive_live_signals(),
        "lifetime_universe": descriptive_lifetime(),
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def _print_summary_table(stats: dict) -> None:
    print()
    print("═" * 80)
    print("Bear DOWN_TRI — descriptive comparison across groups")
    print("═" * 80)
    print(f"\nTotal Bear DOWN_TRI combinations (Phase 5): "
          f"{stats['total_bear_downtri_combos']}")
    print(f"Horizon split: {stats['horizon_breakdown']}")

    cols = list(GROUPS)
    print(f"\n{'metric':<32}", end="")
    for c in cols:
        print(f"{c:>14}", end="")
    print()
    print("─" * (32 + 14 * len(cols)))

    def _row(label, getter):
        print(f"{label:<32}", end="")
        for c in cols:
            g = stats["groups"].get(c, {})
            v = getter(g)
            cell = "—" if v is None else (f"{v:.3f}" if isinstance(v, float)
                                              else str(v))
            print(f"{cell:>14}", end="")
        print()

    _row("count", lambda g: g.get("count"))
    _row("test_wr (mean)",
          lambda g: g.get("lifetime", {}).get("test_wr_mean"))
    _row("baseline_wr (mean)",
          lambda g: g.get("lifetime", {}).get("baseline_wr_mean"))
    _row("edge_pp (mean)",
          lambda g: g.get("lifetime", {}).get("edge_pp_mean"))
    _row("test_n (mean)",
          lambda g: g.get("lifetime", {}).get("test_n_mean"))
    _row("live_n total",
          lambda g: g.get("live", {}).get("live_n_total"))
    _row("live_w total",
          lambda g: g.get("live", {}).get("live_w_total"))
    _row("live_l total",
          lambda g: g.get("live", {}).get("live_l_total"))

    # Live universe surface
    lu = stats.get("live_signal_universe", {})
    print()
    print("─" * 80)
    print("Bear DOWN_TRI live universe (signal-level)")
    print("─" * 80)
    print(f"  n total = {lu.get('n_total')}")
    print(f"  W={lu.get('n_w')}, L={lu.get('n_l')}, F={lu.get('n_f')}")
    if lu.get("wr_excl_flat") is not None:
        print(f"  baseline WR (excl F): {lu['wr_excl_flat']*100:.1f}%")
    if "sector_wr" in lu:
        print(f"\n  Sector breakdown (live):")
        for sec, info in lu["sector_wr"].items():
            wr_str = (f"WR={info['wr']*100:.0f}%"
                      if info["wr"] is not None else "WR=—")
            print(f"    {sec:<10} n={info['n']:>2}  W={info['w']}  "
                  f"L={info['l']}  {wr_str}")

    # Per-signal details (small n)
    if "signals" in lu:
        print(f"\n  Per-signal details (n={lu['n_total']}):")
        print(f"  {'date':<12}{'symbol':<18}{'sector':<10}"
              f"{'outcome':<12}{'ema':<8}{'MACD':<8}")
        for s in lu["signals"]:
            print(f"  {(s.get('date') or '')[:10]:<12}"
                  f"{s.get('symbol') or '':<18}"
                  f"{s.get('sector') or '':<10}"
                  f"{s.get('outcome') or '':<12}"
                  f"{(s.get('feat_ema_alignment') or '')[:7]:<8}"
                  f"{(s.get('feat_MACD_signal') or '')[:7]:<8}")

    # Lifetime baseline
    lt = stats.get("lifetime_universe", {})
    print()
    print("─" * 80)
    print("Bear DOWN_TRI lifetime baseline")
    print("─" * 80)
    print(f"  n total = {lt.get('n_total')}")
    print(f"  W={lt.get('n_w')}, L={lt.get('n_l')}, F={lt.get('n_f')}")
    print(f"  baseline WR = {(lt.get('baseline_wr') or 0)*100:.1f}%")
    if "sector_wr" in lt and lt["sector_wr"]:
        print(f"\n  Sector × WR (lifetime, n≥50):")
        sec_rows = sorted(lt["sector_wr"].items(),
                              key=lambda x: -(x[1].get("wr") or 0))
        for sec, info in sec_rows:
            print(f"    {sec:<10} n={info['n']:>5} WR={info['wr']*100:.1f}%")


def _thin_data_assessment(stats: dict) -> dict:
    """Assess data thinness and recommend session direction."""
    g = stats["groups"]
    val_n = g.get("VALIDATED", {}).get("count", 0)
    pre_n = g.get("PRELIMINARY", {}).get("count", 0)
    rej_n = g.get("REJECTED", {}).get("count", 0)
    watch_n = g.get("WATCH", {}).get("count", 0)
    winners = val_n + pre_n
    live_n = stats["live_signal_universe"].get("n_total", 0)
    lifetime_n = stats["lifetime_universe"].get("n_total", 0)
    lifetime_wr = stats["lifetime_universe"].get("baseline_wr")
    live_wr = stats["live_signal_universe"].get("wr_excl_flat")

    assessment = {
        "winners_VP_count": winners,
        "rejected_count": rej_n,
        "watch_count": watch_n,
        "live_n": live_n,
        "lifetime_n": lifetime_n,
        "lifetime_wr": lifetime_wr,
        "live_wr": live_wr,
        "live_lifetime_gap_pp": (
            (live_wr - lifetime_wr) * 100
            if live_wr is not None and lifetime_wr is not None else None
        ),
        "concerns": [],
        "recommended_path": None,
    }

    # Concerns
    if winners == 0:
        assessment["concerns"].append(
            "0 winners (V+P) in Phase 5 — standard winners-vs-rejected "
            "differentiator analysis NOT FEASIBLE. All 19 combos are WATCH.")
    if winners + rej_n < 5:
        assessment["concerns"].append(
            f"Total evaluable (V+P+R) = {winners + rej_n} < 5. "
            "Insufficient for confident differentiator analysis.")
    if live_n < 15:
        assessment["concerns"].append(
            f"Live n={live_n} < 15. Filter back-test will have very wide "
            "CIs. DEFERRED candidacy strong.")
    if (live_wr is not None and lifetime_wr is not None
        and (live_wr - lifetime_wr) < -0.20):
        assessment["concerns"].append(
            f"Live WR ({live_wr*100:.1f}%) is far below lifetime "
            f"({lifetime_wr*100:.1f}%) — current sub-regime is "
            f"hostile to Bear DOWN_TRI; possible KILL/extend kill_001.")

    # Recommended path
    if winners == 0 and live_n < 15:
        assessment["recommended_path"] = (
            "DEFERRED — but proceed with D2/D3 to investigate "
            "lifetime patterns + kill_001 extension hypotheses. "
            "Full filter cell deferred until quarterly Phase 5 re-run."
        )
    elif winners >= 5 and live_n >= 20:
        assessment["recommended_path"] = (
            "STANDARD CELL — sufficient data for filter analysis."
        )
    else:
        assessment["recommended_path"] = (
            "INVESTIGATE — proceed with D2/D3 to determine if KILL "
            "extension or DEFERRED is more appropriate."
        )

    return assessment


def main():
    print("─" * 80)
    print("CELL: Bear DOWN_TRI — D1 data extraction + descriptive comparison")
    print("─" * 80)
    stats = build_comparison_stats()

    # Thin-data assessment
    stats["thin_data_assessment"] = _thin_data_assessment(stats)

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nSaved: {DEFAULT_OUTPUT}")
    _print_summary_table(stats)

    # Initial observations
    print()
    print("═" * 80)
    print("Initial observations + thin-data assessment")
    print("═" * 80)
    a = stats["thin_data_assessment"]
    print(f"\n  Winners (V+P): {a['winners_VP_count']}  "
          f"Rejected: {a['rejected_count']}  "
          f"Watch: {a['watch_count']}")
    print(f"  Live n: {a['live_n']}  Lifetime n: {a['lifetime_n']}")
    if a["live_wr"] is not None and a["lifetime_wr"] is not None:
        print(f"  Live WR: {a['live_wr']*100:.1f}% / "
              f"Lifetime WR: {a['lifetime_wr']*100:.1f}% / "
              f"Gap: {a['live_lifetime_gap_pp']:+.1f}pp")
        print(f"  ⚠ Gap INVERTED vs Bear UP_TRI (live worse than lifetime)")
    print()
    print(f"  Concerns:")
    for c in a["concerns"]:
        print(f"    • {c}")
    print()
    print(f"  Recommended path:")
    print(f"    {a['recommended_path']}")


if __name__ == "__main__":
    main()
