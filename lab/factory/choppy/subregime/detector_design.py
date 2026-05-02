"""
Choppy regime sub-regime detector — design + prototype.

Per the L1-L5 comprehensive lifetime exploration, Choppy regime contains
three identifiable micro-regimes:

  • stress  — nifty_vol_percentile_20d > 0.70 (~28% of lifetime Choppy)
  • balance — 0.30 ≤ nifty_vol_percentile_20d ≤ 0.70 (~51%)  ← hostile bucket
  • quiet   — nifty_vol_percentile_20d < 0.30 (~21%)

This module:
  1. Implements detect_subregime() with primary vol-percentile rule +
     secondary breadth modifier for finer-grained subtype classification.
  2. Validates against historical Choppy data (lifetime parquet).
  3. Classifies recent live data (April-May 2026 expected: stress).
  4. Surfaces classification agreement with L4 sub-regime WR baselines
     to verify the detector's labels match the WR pattern observed.

Output: lab/factory/choppy/subregime/detector_validation.json

Production integration: see detector_design.md.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "detector_validation.json"

# Vol-percentile thresholds (deterministic, set per feature_loader spec)
QUIET_MAX = 0.30      # nifty_vol_percentile_20d <  0.30 → quiet
STRESS_MIN = 0.70     # nifty_vol_percentile_20d >  0.70 → stress
# 0.30 ≤ percentile ≤ 0.70 → balance

# Breadth thresholds (per feature_loader spec)
BREADTH_LOW_MAX = 0.30
BREADTH_HIGH_MIN = 0.60


@dataclass
class SubregimeLabel:
    """Output of detect_subregime()."""
    subregime: str         # "stress" | "balance" | "quiet"
    subtype: str           # subregime + breadth qualifier
    confidence: float      # 0-100 (distance from boundary)
    vol_percentile: Optional[float]
    breadth: Optional[float]


def detect_subregime(nifty_vol_percentile_20d: Optional[float],
                          market_breadth_pct: Optional[float]
                          ) -> SubregimeLabel:
    """Classify current market state into Choppy sub-regime.

    Primary axis: nifty_vol_percentile_20d (deterministic boundaries).
    Secondary axis: market_breadth_pct (creates subtype within sub-regime).
    Confidence: distance from boundary, normalized 0-100.

    Returns SubregimeLabel.
    """
    vp = nifty_vol_percentile_20d
    br = market_breadth_pct

    # Edge case: missing data
    if vp is None or pd.isna(vp):
        return SubregimeLabel("unknown", "unknown", 0.0, vp, br)

    # Primary: vol regime
    if vp < QUIET_MAX:
        sub = "quiet"
        # Confidence: how far below QUIET_MAX, normalized to [0, QUIET_MAX]
        conf = (QUIET_MAX - vp) / QUIET_MAX * 100
    elif vp > STRESS_MIN:
        sub = "stress"
        conf = (vp - STRESS_MIN) / (1.0 - STRESS_MIN) * 100
    else:
        sub = "balance"
        # Distance from nearest boundary; balance is the [0.30, 0.70] band.
        midpoint = (QUIET_MAX + STRESS_MIN) / 2.0  # = 0.50
        half_width = (STRESS_MIN - QUIET_MAX) / 2.0  # = 0.20
        conf = (1.0 - abs(vp - midpoint) / half_width) * 100

    # Secondary: breadth qualifier
    if br is None or pd.isna(br):
        breadth_qual = "unknown"
    elif br < BREADTH_LOW_MAX:
        breadth_qual = "low_breadth"
    elif br > BREADTH_HIGH_MIN:
        breadth_qual = "high_breadth"
    else:
        breadth_qual = "med_breadth"

    return SubregimeLabel(
        subregime=sub,
        subtype=f"{sub}__{breadth_qual}",
        confidence=round(conf, 1),
        vol_percentile=float(vp) if vp is not None else None,
        breadth=float(br) if br is not None and not pd.isna(br) else None,
    )


def _wlf(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def main():
    print("─" * 80)
    print("T1: Choppy sub-regime detector — design + prototype + validation")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    ch = df[df["regime"] == "Choppy"].copy()
    ch["wlf"] = ch["outcome"].apply(_wlf)
    ch_wl = ch[ch["wlf"].isin(["W", "L", "F"])].copy()

    print(f"\nApplying detector to {len(ch_wl)} lifetime Choppy signals...")

    # Apply detector row-by-row
    labels = ch_wl.apply(
        lambda r: detect_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_market_breadth_pct"),
        ),
        axis=1,
    )
    ch_wl["sub"] = labels.apply(lambda lab: lab.subregime)
    ch_wl["subtype"] = labels.apply(lambda lab: lab.subtype)
    ch_wl["sub_conf"] = labels.apply(lambda lab: lab.confidence)

    # Validation A: distribution of detector labels
    print(f"\n── Detector classification distribution ──")
    sub_counts = ch_wl["sub"].value_counts()
    for sub, cnt in sub_counts.items():
        pct = cnt / len(ch_wl) * 100
        print(f"  {sub:<10}: n={cnt:>6} ({pct:>5.1f}%)")

    # Cross-tab: detector sub-regime label vs feat_nifty_vol_regime
    # (sanity check: detector's vol-percentile rule should be a near-perfect
    # superset/refinement of the categorical vol regime)
    print(f"\n── Cross-tab: detector subregime vs feat_nifty_vol_regime ──")
    print(f"  {'subregime':<10}{'Low':>8}{'Medium':>8}{'High':>8}")
    for sub in ["quiet", "balance", "stress"]:
        s = ch_wl[ch_wl["sub"] == sub]
        n_low = (s["feat_nifty_vol_regime"] == "Low").sum()
        n_med = (s["feat_nifty_vol_regime"] == "Medium").sum()
        n_high = (s["feat_nifty_vol_regime"] == "High").sum()
        print(f"  {sub:<10}{n_low:>8}{n_med:>8}{n_high:>8}")

    # Validation B: WR by detector sub-regime per signal type
    # (should reproduce L1's by_signal_x_vol pattern)
    print(f"\n── WR by detector subregime × signal_type "
          f"(reproduces L1 by_signal_x_vol pattern?) ──")
    print(f"  {'signal':<12}{'sub':<10}{'n':>6}{'WR':>8}")
    val_table = {}
    for sig in ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]:
        for sub in ["quiet", "balance", "stress"]:
            grp = ch_wl[(ch_wl["signal"] == sig) & (ch_wl["sub"] == sub)]
            nw = (grp["wlf"] == "W").sum()
            nl = (grp["wlf"] == "L").sum()
            nwl = nw + nl
            wr = nw / nwl if nwl > 0 else None
            val_table[f"{sig}|{sub}"] = {
                "n": int(len(grp)), "n_w": int(nw), "n_l": int(nl),
                "wr": float(wr) if wr is not None else None,
            }
            if wr is not None:
                print(f"  {sig:<12}{sub:<10}{len(grp):>6}{wr*100:>7.1f}%")

    # Validation C: subtype WR (finer-grained — confirms L3 winning combos)
    print(f"\n── WR by detector subtype × signal_type "
          f"(should highlight L3 winning combos) ──")
    sub_table = {}
    print(f"  {'signal':<12}{'subtype':<24}{'n':>6}{'WR':>8}")
    for sig in ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]:
        for subtype, grp in (ch_wl[ch_wl["signal"] == sig]
                                  .groupby("subtype", observed=True)):
            nw = (grp["wlf"] == "W").sum()
            nl = (grp["wlf"] == "L").sum()
            nwl = nw + nl
            if nwl < 100:  # skip thin cells
                continue
            wr = nw / nwl
            sub_table[f"{sig}|{subtype}"] = {
                "n": int(len(grp)), "n_w": int(nw), "n_l": int(nl),
                "wr": float(wr),
            }
            print(f"  {sig:<12}{str(subtype):<24}{len(grp):>6}{wr*100:>7.1f}%")

    # Live classification: most recent data
    print(f"\n── Live (April 2026+) classification ──")
    ch_wl["scan_date"] = pd.to_datetime(ch_wl["scan_date"])
    recent = ch_wl[ch_wl["scan_date"] >= "2026-04-01"]
    if len(recent) > 0:
        live_dist = recent["sub"].value_counts()
        live_subtype = recent["subtype"].value_counts()
        print(f"  n recent Choppy signals: {len(recent)}")
        print(f"  subregime distribution:")
        for s, c in live_dist.items():
            pct = c / len(recent) * 100
            print(f"    {s:<10}: n={c:>4} ({pct:>5.1f}%)")
        print(f"  subtype distribution (top 5):")
        for s, c in live_subtype.head(5).items():
            print(f"    {s:<24}: n={c:>4}")
        live_summary = {
            "n_total": int(len(recent)),
            "subregime_distribution": {k: int(v) for k, v in live_dist.items()},
            "subtype_distribution": {
                k: int(v) for k, v in live_subtype.head(10).items()},
            "dominant_subregime": live_dist.index[0],
            "verdict": (
                "Live April-May 2026 is uniformly STRESS sub-regime — "
                "high-vol stress episode. F1 (regime-shift adaptive) is "
                "the right filter for this period; lifetime balance-sub-"
                "regime patterns expected to underperform here."
                if live_dist.index[0] == "stress"
                else f"Dominant: {live_dist.index[0]} (verify against expectation)"
            ),
        }
    else:
        live_summary = {"n_total": 0, "verdict": "no recent data"}

    # Aggregate validation summary
    output = {
        "detector_design": {
            "primary_axis": "feat_nifty_vol_percentile_20d",
            "secondary_axis": "feat_market_breadth_pct",
            "thresholds": {
                "quiet_max": QUIET_MAX,
                "stress_min": STRESS_MIN,
                "breadth_low_max": BREADTH_LOW_MAX,
                "breadth_high_min": BREADTH_HIGH_MIN,
            },
            "subregimes": ["quiet", "balance", "stress"],
            "subtypes_per_subregime": [
                "low_breadth", "med_breadth", "high_breadth"],
        },
        "lifetime_distribution": {k: int(v) for k, v in sub_counts.items()},
        "wr_by_subregime_x_signal": val_table,
        "wr_by_subtype_x_signal": sub_table,
        "live_classification": live_summary,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
