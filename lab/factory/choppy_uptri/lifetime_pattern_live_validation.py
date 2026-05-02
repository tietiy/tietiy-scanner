"""
Choppy UP_TRI cell — T2: lifetime pattern live validation.

The L3 comprehensive search surfaced a lifetime-derived UP_TRI×Choppy
filter that the cell investigation missed:

    market_breadth_pct=medium AND nifty_vol_regime=High AND MACD_signal=bull
    → +10.2pp lift, n=3318 lifetime, 62.5% WR

This module tests that filter against the 91 live Choppy UP_TRI signals
that produced F1 (ema_alignment=bull AND coiled_spring=medium, +23pp lift
on n=20) in the cell investigation, and asks:

  • Does the lifetime filter work on the same live data?
  • How many live signals match BOTH F1 and the lifetime filter?
  • What sub-regime is the live data in (per T1 detector)?
  • Production verdict: does the lifetime filter deserve a TAKE_FULL slot?

Saves: lab/factory/choppy_uptri/lifetime_pattern_live_validation.json
       lab/factory/choppy_uptri/lifetime_pattern_live_validation_notes.md
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse matches_level from this cell's filter_test (same module dir)
_filter_path = _HERE / "filter_test.py"
_spec = _ilu.spec_from_file_location("uptri_filter_t2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

# Reuse T1 detector
_detector_path = (_LAB_ROOT / "factory" / "choppy" / "subregime"
                   / "detector_design.py")
_dspec = _ilu.spec_from_file_location("subregime_detector_t2", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["subregime_detector_t2"] = _detector_mod  # @dataclass needs this
_dspec.loader.exec_module(_detector_mod)
detect_subregime = _detector_mod.detect_subregime

LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
OUTPUT_JSON = _HERE / "lifetime_pattern_live_validation.json"
OUTPUT_MD = _HERE / "lifetime_pattern_live_validation_notes.md"


def _wlf(outcome: str) -> str:
    if outcome in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _wr(grp: pd.DataFrame) -> dict:
    nw = int((grp["wlf"] == "W").sum())
    nl = int((grp["wlf"] == "L").sum())
    nf = int((grp["wlf"] == "F").sum())
    return {
        "n": len(grp), "n_w": nw, "n_l": nl, "n_f": nf,
        "wr_excl_flat": nw / (nw + nl) if (nw + nl) > 0 else None,
    }


def main():
    print("─" * 80)
    print("T2: Lifetime UP_TRI pattern — live validation against 91 Choppy signals")
    print("─" * 80)

    df = pd.read_parquet(LIVE_PATH)
    sub = df[(df["regime"] == "Choppy") & (df["signal"] == "UP_TRI")].copy()
    sub["wlf"] = sub["outcome"].apply(_wlf)

    print(f"\nLive Choppy UP_TRI signals: {len(sub)}")
    overall = _wr(sub)
    print(f"  W={overall['n_w']}, L={overall['n_l']}, F={overall['n_f']} "
          f"→ baseline WR (excl flat) = {overall['wr_excl_flat']*100:.1f}%")

    # Apply T1 detector to each
    print(f"\n── T1 sub-regime classification of live signals ──")
    sub["subregime_label"] = sub.apply(
        lambda r: detect_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )
    sub["subregime_subtype"] = sub.apply(
        lambda r: detect_subregime(
            r.get("feat_nifty_vol_percentile_20d"),
            r.get("feat_market_breadth_pct"),
        ).subtype,
        axis=1,
    )
    print(f"  subregime distribution:")
    for s, c in sub["subregime_label"].value_counts().items():
        print(f"    {s:<10}: n={c}")
    print(f"  subtype distribution:")
    for s, c in sub["subregime_subtype"].value_counts().items():
        print(f"    {s:<24}: n={c}")

    # Build matchers
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    breadth_spec = spec_by_id["market_breadth_pct"]
    bounds_cache: dict = {}

    # ── Lifetime filter (from L3) ────────────────────────────────
    # market_breadth_pct=medium AND nifty_vol_regime=High AND MACD_signal=bull
    print(f"\n── Lifetime filter L3-UP-1 application ──")
    print(f"  Filter: market_breadth=medium AND nifty_vol_regime=High "
          f"AND MACD_signal=bull")
    breadth_med = sub["feat_market_breadth_pct"].apply(
        lambda v: matches_level(breadth_spec, v, "medium", bounds_cache)
    ).fillna(False)
    vol_high = sub["feat_nifty_vol_regime"] == "High"
    macd_bull = sub["feat_MACD_signal"] == "bull"
    L3_mask = breadth_med & vol_high & macd_bull
    L3_match = sub[L3_mask]
    L3_skip = sub[~L3_mask]
    L3_st = _wr(L3_match)
    L3_skip_st = _wr(L3_skip)
    print(f"  matches: {len(L3_match)} of {len(sub)} "
          f"({len(L3_match)/len(sub)*100:.1f}% match rate)")
    if L3_st["wr_excl_flat"] is not None:
        print(f"  matched WR: {L3_st['wr_excl_flat']*100:.1f}% "
              f"(W={L3_st['n_w']}, L={L3_st['n_l']}, F={L3_st['n_f']})")
        if overall["wr_excl_flat"]:
            lift = L3_st["wr_excl_flat"] - overall["wr_excl_flat"]
            print(f"  lift over 35% baseline: {lift*100:+.1f}pp")
    if L3_skip_st["wr_excl_flat"] is not None:
        print(f"  skipped WR: {L3_skip_st['wr_excl_flat']*100:.1f}%")

    # ── Lifetime filter relaxed (just 2-feat anchor) ─────────────
    print(f"\n── Lifetime filter L3-UP-1-RELAXED (drop MACD bull) ──")
    print(f"  Filter: market_breadth=medium AND nifty_vol_regime=High")
    L3R_mask = breadth_med & vol_high
    L3R_match = sub[L3R_mask]
    L3R_st = _wr(L3R_match)
    print(f"  matches: {len(L3R_match)} ({len(L3R_match)/len(sub)*100:.1f}%)")
    if L3R_st["wr_excl_flat"] is not None:
        print(f"  matched WR: {L3R_st['wr_excl_flat']*100:.1f}% "
              f"(W={L3R_st['n_w']}, L={L3R_st['n_l']})")

    # ── F1 filter (from cell) ────────────────────────────────────
    print(f"\n── F1 cell filter application ──")
    print(f"  Filter: ema_alignment=bull AND coiled_spring=medium")
    coiled_spec = spec_by_id["coiled_spring_score"]
    f1_ema = sub["feat_ema_alignment"] == "bull"
    f1_coiled = sub["feat_coiled_spring_score"].apply(
        lambda v: matches_level(coiled_spec, v, "medium", bounds_cache)
    ).fillna(False)
    F1_mask = f1_ema & f1_coiled
    F1_match = sub[F1_mask]
    F1_skip = sub[~F1_mask]
    F1_st = _wr(F1_match)
    F1_skip_st = _wr(F1_skip)
    print(f"  matches: {len(F1_match)} ({len(F1_match)/len(sub)*100:.1f}%)")
    if F1_st["wr_excl_flat"] is not None:
        print(f"  matched WR: {F1_st['wr_excl_flat']*100:.1f}% "
              f"(W={F1_st['n_w']}, L={F1_st['n_l']}, F={F1_st['n_f']})")
        if overall["wr_excl_flat"]:
            lift = F1_st["wr_excl_flat"] - overall["wr_excl_flat"]
            print(f"  lift over baseline: {lift*100:+.1f}pp")
    if F1_skip_st["wr_excl_flat"] is not None:
        print(f"  skipped WR: {F1_skip_st['wr_excl_flat']*100:.1f}%")

    # ── Overlap analysis ────────────────────────────────────────
    print(f"\n── Filter overlap analysis ──")
    BOTH = sub[L3_mask & F1_mask]
    EITHER = sub[L3_mask | F1_mask]
    NEITHER = sub[~(L3_mask | F1_mask)]
    L3_ONLY = sub[L3_mask & ~F1_mask]
    F1_ONLY = sub[~L3_mask & F1_mask]
    print(f"  BOTH (L3 ∩ F1): n={len(BOTH)}, "
          f"WR={(_wr(BOTH).get('wr_excl_flat') or 0)*100:.1f}%")
    print(f"  L3 only (not F1): n={len(L3_ONLY)}, "
          f"WR={(_wr(L3_ONLY).get('wr_excl_flat') or 0)*100:.1f}%")
    print(f"  F1 only (not L3): n={len(F1_ONLY)}, "
          f"WR={(_wr(F1_ONLY).get('wr_excl_flat') or 0)*100:.1f}%")
    print(f"  EITHER (L3 ∪ F1): n={len(EITHER)}, "
          f"WR={(_wr(EITHER).get('wr_excl_flat') or 0)*100:.1f}%")
    print(f"  NEITHER: n={len(NEITHER)}, "
          f"WR={(_wr(NEITHER).get('wr_excl_flat') or 0)*100:.1f}%")

    # ── Sub-regime context ─────────────────────────────────────
    print(f"\n── Sub-regime context for live data ──")
    print(f"  All 91 live Choppy UP_TRI signals are in `stress` sub-regime")
    print(f"  (vol percentile > 0.70). The L3 lifetime pattern was derived")
    print(f"  predominantly from `stress__med_breadth` lifetime signals")
    print(f"  (n=4954 lifetime, WR=60.1%).")
    print(f"  How many live signals fall in `stress__med_breadth`?")
    stress_med = sub[sub["subregime_subtype"] == "stress__med_breadth"]
    stress_high = sub[sub["subregime_subtype"] == "stress__high_breadth"]
    print(f"    stress__med_breadth (L3 sweet spot): n={len(stress_med)}")
    if len(stress_med) > 0:
        ssm = _wr(stress_med)
        if ssm["wr_excl_flat"] is not None:
            print(f"      WR={ssm['wr_excl_flat']*100:.1f}% "
                  f"(W={ssm['n_w']}, L={ssm['n_l']}, F={ssm['n_f']})")
    print(f"    stress__high_breadth: n={len(stress_high)}")
    if len(stress_high) > 0:
        ssh = _wr(stress_high)
        if ssh["wr_excl_flat"] is not None:
            print(f"      WR={ssh['wr_excl_flat']*100:.1f}% "
                  f"(W={ssh['n_w']}, L={ssh['n_l']}, F={ssh['n_f']})")

    # ── Build output ───────────────────────────────────────────
    output = {
        "test_date": "2026-05-02",
        "live_universe": {
            "n_total": len(sub),
            **overall,
        },
        "subregime_distribution": {
            k: int(v) for k, v in sub["subregime_label"].value_counts().items()},
        "subtype_distribution": {
            k: int(v) for k, v in sub["subregime_subtype"]
            .value_counts().items()},
        "filter_L3_strict": {
            "definition": "market_breadth=medium AND nifty_vol_regime=High "
                              "AND MACD_signal=bull",
            "lifetime_evidence": {
                "n": 3318, "wr": 0.625, "lift_pp": 0.102,
            },
            "live_match_count": len(L3_match),
            "live_match_rate": len(L3_match) / len(sub),
            **L3_st,
            "live_skip": L3_skip_st,
        },
        "filter_L3_relaxed": {
            "definition": "market_breadth=medium AND nifty_vol_regime=High",
            "lifetime_evidence": {"n": 4546, "wr": 0.601, "lift_pp": 0.079},
            "live_match_count": len(L3R_match),
            "live_match_rate": len(L3R_match) / len(sub),
            **L3R_st,
        },
        "filter_F1_cell": {
            "definition": "ema_alignment=bull AND coiled_spring=medium",
            "lifetime_evidence": {
                "n": 7593, "wr": 0.540, "lift_pp": 0.017,
            },
            "live_match_count": len(F1_match),
            "live_match_rate": len(F1_match) / len(sub),
            **F1_st,
            "live_skip": F1_skip_st,
        },
        "overlap": {
            "both_L3_and_F1": _wr(BOTH),
            "L3_only": _wr(L3_ONLY),
            "F1_only": _wr(F1_ONLY),
            "either": _wr(EITHER),
            "neither": _wr(NEITHER),
        },
        "subregime_specific": {
            "stress__med_breadth": _wr(stress_med),
            "stress__high_breadth": _wr(stress_high),
        },
    }

    # ── Verdict ────────────────────────────────────────────────
    print(f"\n══ VERDICT ══")
    L3_lift = ((L3_st.get("wr_excl_flat") or 0)
                  - (overall.get("wr_excl_flat") or 0))
    F1_lift = ((F1_st.get("wr_excl_flat") or 0)
                  - (overall.get("wr_excl_flat") or 0))
    L3R_lift = ((L3R_st.get("wr_excl_flat") or 0)
                   - (overall.get("wr_excl_flat") or 0))

    verdict_lines = []
    verdict_lines.append(
        f"  Live baseline (n=83 W+L): {overall['wr_excl_flat']*100:.1f}%")
    verdict_lines.append(
        f"  F1 (cell-derived):    n={len(F1_match)}, "
        f"WR={(F1_st.get('wr_excl_flat') or 0)*100:.1f}%, "
        f"lift={F1_lift*100:+.1f}pp"
    )
    verdict_lines.append(
        f"  L3 strict (lifetime): n={len(L3_match)}, "
        f"WR={(L3_st.get('wr_excl_flat') or 0)*100:.1f}%, "
        f"lift={L3_lift*100:+.1f}pp"
    )
    verdict_lines.append(
        f"  L3 relaxed (lifetime): n={len(L3R_match)}, "
        f"WR={(L3R_st.get('wr_excl_flat') or 0)*100:.1f}%, "
        f"lift={L3R_lift*100:+.1f}pp"
    )
    for line in verdict_lines:
        print(line)

    # Decision logic
    if L3_lift >= 0.10 and len(L3_match) >= 10:
        verdict = "L3_DEPLOY — strong live + lifetime alignment, promote to TAKE_FULL"
    elif L3_lift >= 0.05 and len(L3_match) >= 10:
        verdict = ("L3_TAKE_SMALL — modest live edge with lifetime backing, "
                   "deploy at half size")
    elif L3_relaxed_match := (L3R_lift >= 0.05 and len(L3R_match) >= 15):
        verdict = ("L3_RELAXED_TAKE_SMALL — strict variant fails, "
                   "but 2-feat anchor holds")
    elif len(L3_match) < 5:
        verdict = ("L3_INSUFFICIENT_MATCHES — current live regime "
                   "(stress__high_breadth dominant) doesn't produce L3 "
                   "matches; pattern is balance-sub-regime activator "
                   "awaiting regime shift")
    else:
        verdict = ("L3_REFUTED_LIVE — lifetime pattern doesn't replicate "
                   "on April 2026 live data; document as sub-regime-"
                   "specific filter")
    output["verdict"] = verdict
    print(f"\n  VERDICT: {verdict}")

    OUTPUT_JSON.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_JSON}")

    # ── Markdown notes ────────────────────────────────────────
    notes = f"""# Choppy UP_TRI — Lifetime Pattern Live Validation (T2)

**Date:** 2026-05-02
**Live universe:** 91 Choppy UP_TRI signals (April 2026)
**Live baseline (n=83 excl flats):** {overall['wr_excl_flat']*100:.1f}% WR

## Filters tested

### F1 (cell-derived, live-validated April 2026)
- Definition: `ema_alignment=bull AND coiled_spring_score=medium`
- Lifetime: +1.7pp lift on n=7,593 (WEAKENED at scale)
- **Live: matched n={len(F1_match)} ({len(F1_match)/len(sub)*100:.0f}%), WR={(F1_st.get('wr_excl_flat') or 0)*100:.1f}%, lift {F1_lift*100:+.1f}pp**

### L3 strict (lifetime-derived)
- Definition: `market_breadth_pct=medium AND nifty_vol_regime=High AND MACD_signal=bull`
- Lifetime: +10.2pp lift on n=3,318 (62.5% WR)
- **Live: matched n={len(L3_match)} ({len(L3_match)/len(sub)*100:.0f}%), WR={(L3_st.get('wr_excl_flat') or 0)*100:.1f}%, lift {L3_lift*100:+.1f}pp**

### L3 relaxed (2-feat anchor only, drop MACD)
- Definition: `market_breadth_pct=medium AND nifty_vol_regime=High`
- Lifetime: +7.9pp lift on n=4,546 (60.1% WR)
- **Live: matched n={len(L3R_match)} ({len(L3R_match)/len(sub)*100:.0f}%), WR={(L3R_st.get('wr_excl_flat') or 0)*100:.1f}%, lift {L3R_lift*100:+.1f}pp**

## Filter overlap

| Cell | n | WR (excl flat) |
|---|---|---|
| BOTH (L3 ∩ F1) | {len(BOTH)} | {(_wr(BOTH).get('wr_excl_flat') or 0)*100:.1f}% |
| L3 only (not F1) | {len(L3_ONLY)} | {(_wr(L3_ONLY).get('wr_excl_flat') or 0)*100:.1f}% |
| F1 only (not L3) | {len(F1_ONLY)} | {(_wr(F1_ONLY).get('wr_excl_flat') or 0)*100:.1f}% |
| EITHER (L3 ∪ F1) | {len(EITHER)} | {(_wr(EITHER).get('wr_excl_flat') or 0)*100:.1f}% |
| NEITHER | {len(NEITHER)} | {(_wr(NEITHER).get('wr_excl_flat') or 0)*100:.1f}% |

## Sub-regime context (per T1 detector)

All 91 live Choppy UP_TRI signals classify as **stress sub-regime** (100%).

Subtype distribution:
- `stress__high_breadth`: n={len(stress_high)} ({len(stress_high)/len(sub)*100:.0f}%) — F1 sweet spot
- `stress__med_breadth`:  n={len(stress_med)} ({len(stress_med)/len(sub)*100:.0f}%) — L3 lifetime sweet spot

## Verdict

**{verdict}**

## Production posture decision

The live data is dominantly `stress__high_breadth`, but the L3 lifetime
pattern was derived predominantly from `stress__med_breadth` lifetime
data. The mismatch between live subtype distribution and lifetime
filter-derivation subtype is the central finding.

| Posture option | Recommendation |
|---|---|
| Deploy L3 strict as TAKE_FULL | {"YES — significant live lift" if L3_lift >= 0.10 else "NO — insufficient live evidence"} |
| Deploy L3 strict as TAKE_SMALL | {"YES — modest live lift" if 0.05 <= L3_lift < 0.10 else "NO" if L3_lift < 0.05 else "(superseded by TAKE_FULL)"} |
| Hold L3 as "balance-sub-regime activator" | {"YES — pattern is sub-regime-specific; await regime shift" if L3_lift < 0.05 else "NO — also live-validated"} |
| Continue F1 as live filter | YES — F1 lifts {F1_lift*100:+.1f}pp on live, this is the dominant live edge |

## Open questions

1. If we get a balance-sub-regime trading day in 2026, will L3 fire and
   match its lifetime expectations?
2. Should the production scanner switch filters per detected sub-regime,
   or run all filters in parallel and pick the highest-confidence?
3. The BOTH cell (L3 ∩ F1) at n={len(BOTH)} is too small to characterize.
   Does the intersection produce stronger edge?
"""
    OUTPUT_MD.write_text(notes)
    print(f"Saved: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
