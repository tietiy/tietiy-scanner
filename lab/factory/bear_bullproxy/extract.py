"""
Bear BULL_PROXY cell — P1: data extraction + descriptive comparison +
sub-regime classification.

⚠ HALT-LEVEL FINDING ⚠

Bear BULL_PROXY has **ZERO** Phase 5 combinations in
`combinations_live_validated.parquet`. Not 0 winners (like Bear DOWN_TRI's
19 WATCH) — literally 0 combos total. The Lab's Phase 4/5 pipeline
produced no surviving Bear BULL_PROXY combinations.

This means standard cell methodology (winners-vs-rejected differentiator
analysis) is fundamentally not feasible for this cell. Falling back to
lifetime-only analysis — same path as Bear DOWN_TRI cell — with
DEFERRED as the most likely outcome.

Live and lifetime data DO exist:
  • Live: n=13 Bear BULL_PROXY signals, 11W/2L = 84.6% WR
  • Lifetime: n=891 Bear BULL_PROXY signals, 47.3% WR
  • Apparent gap: +37.3pp (parallel to Bear UP_TRI's +38.9pp)

Bear sub-regime detector applied (built in Bear UP_TRI Session 2):
  hot:  vol_percentile_20d > 0.70 AND nifty_60d_return < -0.10
  warm: vol > 0.70 AND -0.10 ≤ 60d < 0
  cold: everything else

Apply detector to live + lifetime to characterize sub-regime distribution.
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent

DEFAULT_INPUT = _LAB_ROOT / "output" / "combinations_live_validated.parquet"
LIVE_FEATURES_INPUT = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
ENRICHED_INPUT = _LAB_ROOT / "output" / "enriched_signals.parquet"
DEFAULT_OUTPUT = _HERE / "comparison_stats.json"

GROUPS = ("VALIDATED", "PRELIMINARY", "REJECTED", "WATCH")

# Reuse Bear sub-regime detector (built in Bear UP_TRI Session 2)
_detector_path = (_LAB_ROOT / "factory" / "bear" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bear_subregime_p1", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bear_subregime_p1"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bear_subregime = _detector_mod.detect_bear_subregime


def load_bear_bullproxy(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    df = pd.read_parquet(input_path)
    return df[(df["signal_type"] == "BULL_PROXY")
                & (df["regime"] == "Bear")].copy()


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _safe_mean(s: pd.Series) -> Optional[float]:
    s = s.dropna()
    return float(s.mean()) if len(s) else None


def descriptive_stats(group_df: pd.DataFrame) -> dict:
    n = len(group_df)
    if n == 0:
        return {"count": 0}
    return {
        "count": n,
        "lifetime": {
            "test_wr_mean": _safe_mean(group_df["test_wr"]),
        },
        "live": {
            "live_n_total": int(group_df["live_n"].fillna(0).sum())
            if "live_n" in group_df.columns else 0,
        },
    }


def descriptive_live_signals() -> dict:
    """Read live_signals_with_features.parquet to surface raw live universe."""
    df = pd.read_parquet(LIVE_FEATURES_INPUT)
    sub = df[(df["regime"] == "Bear") & (df["signal"] == "BULL_PROXY")].copy()
    sub["wlf"] = sub["outcome"].apply(_wlf)

    # Apply Bear sub-regime detector
    sub["sub"] = sub.apply(
        lambda r: detect_bear_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_nifty_60d_return_pct"),
        ).subregime,
        axis=1,
    )

    nw = (sub["wlf"] == "W").sum()
    nl = (sub["wlf"] == "L").sum()
    nf = (sub["wlf"] == "F").sum()

    out = {
        "n_total": int(len(sub)),
        "n_w": int(nw),
        "n_l": int(nl),
        "n_f": int(nf),
        "wr_excl_flat": float(nw / (nw + nl)) if (nw + nl) > 0 else None,
        "subregime_distribution": {
            k: int(v) for k, v in sub["sub"].value_counts().items()
        },
    }

    # WR by sub-regime
    sub_wr = {}
    for s in ("hot", "warm", "cold"):
        grp = sub[sub["sub"] == s]
        if len(grp) == 0:
            continue
        gw = (grp["wlf"] == "W").sum()
        gl = (grp["wlf"] == "L").sum()
        sub_wr[s] = {
            "n": int(len(grp)),
            "n_w": int(gw), "n_l": int(gl),
            "wr": float(gw / (gw + gl)) if (gw + gl) > 0 else None,
        }
    out["wr_by_subregime"] = sub_wr

    out["signals"] = []
    for _, r in sub.iterrows():
        out["signals"].append({
            "date": str(r["date"]) if "date" in sub.columns else None,
            "symbol": r["symbol"],
            "sector": r["sector"],
            "outcome": r["outcome"],
            "wlf": r["wlf"],
            "subregime": r["sub"],
            "feat_ema_alignment": r.get("feat_ema_alignment"),
            "feat_MACD_signal": r.get("feat_MACD_signal"),
            "feat_market_breadth_pct": r.get("feat_market_breadth_pct"),
            "feat_nifty_vol_percentile_20d": r.get(
                "feat_nifty_vol_percentile_20d"),
            "feat_nifty_60d_return_pct": r.get("feat_nifty_60d_return_pct"),
            "feat_day_of_week": r.get("feat_day_of_week"),
            "feat_day_of_month_bucket": r.get("feat_day_of_month_bucket"),
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

    return out


def descriptive_lifetime() -> dict:
    """Lifetime Bear BULL_PROXY baseline + sector + sub-regime breakdown."""
    df = pd.read_parquet(ENRICHED_INPUT)
    bp = df[(df["regime"] == "Bear") & (df["signal"] == "BULL_PROXY")].copy()
    bp_wl = bp[bp["outcome"].isin(["DAY6_WIN", "TARGET_HIT",
                                          "DAY6_LOSS", "STOP_HIT",
                                          "DAY6_FLAT"])].copy()
    bp_wl["wlf"] = bp_wl["outcome"].apply(_wlf)

    # Apply detector
    bp_wl["sub"] = bp_wl.apply(
        lambda r: detect_bear_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_nifty_60d_return_pct"),
        ).subregime,
        axis=1,
    )

    nw = (bp_wl["wlf"] == "W").sum()
    nl = (bp_wl["wlf"] == "L").sum()
    nf = (bp_wl["wlf"] == "F").sum()
    baseline_wr = nw / (nw + nl) if (nw + nl) > 0 else None

    # WR by sub-regime
    sub_wr = {}
    for s in ("hot", "warm", "cold"):
        grp = bp_wl[bp_wl["sub"] == s]
        if len(grp) == 0:
            continue
        gw = (grp["wlf"] == "W").sum()
        gl = (grp["wlf"] == "L").sum()
        sub_wr[s] = {
            "n": int(len(grp)),
            "n_w": int(gw), "n_l": int(gl),
            "wr": float(gw / (gw + gl)) if (gw + gl) > 0 else None,
            "pct_of_lifetime": float(len(grp) / len(bp_wl)),
        }

    # Sector WR
    sec_wr = {}
    for sec, grp in bp_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        grw = (grp["wlf"] == "W").sum()
        grl = (grp["wlf"] == "L").sum()
        if grw + grl < 30:
            continue
        sec_wr[str(sec)] = {
            "n": int(len(grp)),
            "wr": float(grw / (grw + grl)) if (grw + grl) > 0 else None,
        }

    return {
        "n_total": int(len(bp_wl)),
        "n_w": int(nw), "n_l": int(nl), "n_f": int(nf),
        "baseline_wr": float(baseline_wr) if baseline_wr is not None else None,
        "wr_by_subregime": sub_wr,
        "sector_wr": sec_wr,
    }


def build_comparison_stats(input_path: Path = DEFAULT_INPUT) -> dict:
    df = load_bear_bullproxy(input_path)
    out = {
        "total_bear_bullproxy_combos": len(df),
        "halt_warning": (
            "0 Phase 5 combinations exist for Bear BULL_PROXY — "
            "standard cell methodology NOT FEASIBLE. Falling back to "
            "lifetime-only analysis (parallel to Bear DOWN_TRI path). "
            "DEFERRED is most likely outcome."
        ) if len(df) == 0 else None,
        "groups": {},
        "live_signal_universe": descriptive_live_signals(),
        "lifetime_universe": descriptive_lifetime(),
    }
    for tier in GROUPS:
        sub = df[df["live_tier"] == tier] if "live_tier" in df.columns else df.iloc[:0]
        out["groups"][tier] = descriptive_stats(sub)
    return out


def _print_summary(stats: dict) -> None:
    print()
    print("═" * 80)
    print("Bear BULL_PROXY — descriptive comparison")
    print("═" * 80)

    total = stats["total_bear_bullproxy_combos"]
    print(f"\n⚠ Total Phase 5 combinations: {total}")
    if stats.get("halt_warning"):
        print(f"⚠ {stats['halt_warning']}")

    # Live universe
    lu = stats["live_signal_universe"]
    print()
    print("─" * 80)
    print("Live universe (signal-level)")
    print("─" * 80)
    print(f"  n total = {lu['n_total']}")
    print(f"  W={lu['n_w']}, L={lu['n_l']}, F={lu['n_f']}")
    if lu.get("wr_excl_flat") is not None:
        print(f"  baseline WR = {lu['wr_excl_flat']*100:.1f}%")
    print(f"\n  Sub-regime distribution:")
    for s, n in lu.get("subregime_distribution", {}).items():
        info = lu.get("wr_by_subregime", {}).get(s, {})
        wr = info.get("wr")
        wr_str = f"WR={wr*100:.1f}%" if wr is not None else "WR=—"
        print(f"    {s:<8} n={n:<3}  {wr_str} (W={info.get('n_w',0)}, "
              f"L={info.get('n_l',0)})")

    print(f"\n  Sector breakdown (live):")
    for sec, info in sorted(lu.get("sector_wr", {}).items(),
                                  key=lambda x: -(x[1].get("wr") or 0)):
        wr_str = f"WR={info['wr']*100:.0f}%" if info["wr"] is not None else "—"
        print(f"    {sec:<10} n={info['n']:>2}  W={info['w']}  "
              f"L={info['l']}  {wr_str}")

    print(f"\n  Per-signal details:")
    print(f"  {'date':<12}{'symbol':<18}{'sector':<10}{'sub':<8}"
          f"{'outcome':<12}")
    for s in lu.get("signals", []):
        print(f"  {(s.get('date') or '')[:10]:<12}"
              f"{s.get('symbol') or '':<18}"
              f"{s.get('sector') or '':<10}"
              f"{(s.get('subregime') or ''):<8}"
              f"{(s.get('outcome') or ''):<12}")

    # Lifetime
    lt = stats["lifetime_universe"]
    print()
    print("─" * 80)
    print("Lifetime universe")
    print("─" * 80)
    print(f"  n total = {lt['n_total']}")
    print(f"  W={lt['n_w']}, L={lt['n_l']}, F={lt['n_f']}")
    print(f"  baseline WR = {(lt['baseline_wr'] or 0)*100:.1f}%")
    print(f"\n  Sub-regime distribution (lifetime):")
    for s, info in lt.get("wr_by_subregime", {}).items():
        pct = info.get("pct_of_lifetime", 0) * 100
        wr = info.get("wr") or 0
        print(f"    {s:<8} n={info['n']:<5} ({pct:.1f}%)  WR={wr*100:.1f}%")

    print(f"\n  Sector × WR (lifetime, n≥30):")
    sec_rows = sorted(lt.get("sector_wr", {}).items(),
                          key=lambda x: -(x[1].get("wr") or 0))
    for sec, info in sec_rows:
        print(f"    {sec:<10} n={info['n']:>5} WR={info['wr']*100:.1f}%")


def _thin_data_assessment(stats: dict) -> dict:
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

    return {
        "winners_VP_count": winners,
        "rejected_count": rej_n,
        "watch_count": watch_n,
        "phase5_total": val_n + pre_n + rej_n + watch_n,
        "live_n": live_n,
        "lifetime_n": lifetime_n,
        "lifetime_wr": lifetime_wr,
        "live_wr": live_wr,
        "live_lifetime_gap_pp": (
            (live_wr - lifetime_wr) * 100
            if live_wr is not None and lifetime_wr is not None else None
        ),
        "halt_condition_met": (winners == 0
                                  and (val_n + pre_n + rej_n + watch_n) == 0),
        "recommended_path": (
            "DEFERRED — Phase 5 has 0 combinations. Same fallback path "
            "as Bear DOWN_TRI: lifetime-only differentiator analysis + "
            "sub-regime cascade test → DEFERRED verdict with provisional "
            "filter (if lifetime supports). NO Sessions 2-3."
            if (val_n + pre_n + rej_n + watch_n) == 0 else
            "STANDARD CELL or thin-data investigate"
        ),
    }


def main():
    print("─" * 80)
    print("CELL: Bear BULL_PROXY — P1 data extraction + sub-regime")
    print("─" * 80)
    stats = build_comparison_stats()
    stats["thin_data_assessment"] = _thin_data_assessment(stats)
    DEFAULT_OUTPUT.write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nSaved: {DEFAULT_OUTPUT}")
    _print_summary(stats)

    # Surface
    print()
    print("═" * 80)
    print("Initial observations + thin-data assessment")
    print("═" * 80)
    a = stats["thin_data_assessment"]
    print(f"\n  Phase 5 total combos: {a['phase5_total']}")
    print(f"  Winners (V+P): {a['winners_VP_count']}, Rejected: "
          f"{a['rejected_count']}, Watch: {a['watch_count']}")
    print(f"  Live n: {a['live_n']}, Lifetime n: {a['lifetime_n']}")
    if a["live_wr"] is not None and a["lifetime_wr"] is not None:
        print(f"  Live WR: {a['live_wr']*100:.1f}%, "
              f"Lifetime WR: {a['lifetime_wr']*100:.1f}%, "
              f"Gap: {a['live_lifetime_gap_pp']:+.1f}pp")

    print(f"\n  Halt condition met: {a['halt_condition_met']}")
    print(f"  Recommended path: {a['recommended_path']}")


if __name__ == "__main__":
    main()
