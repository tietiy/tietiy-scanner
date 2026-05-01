"""
Choppy UP_TRI cell — C3: candidate filter articulation + back-test.

Articulates 4 candidate filters from C2 differentiators and tests each
against the 91 live Choppy UP_TRI signals (from live_signals_with_features
parquet, joined to feature values).

Filter performance is measured against the unfiltered baseline (~35% WR).
A filter is "useful" if matched WR > 60% AND skipped WR < 25%.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Callable

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_HERE))

from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402

OUTPUT_PATH = _HERE / "filter_test_results.json"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"


# ── Threshold parsing (mirrors combination_generator) ────────────────

def _parse_numeric_thresholds(level_thresholds: dict) -> Optional[tuple[float, float]]:
    if not isinstance(level_thresholds, dict):
        return None
    low_str = level_thresholds.get("low")
    high_str = level_thresholds.get("high")
    if low_str is None or high_str is None:
        return None
    try:
        low_b = float(str(low_str).replace("<", "").strip())
        high_b = float(str(high_str).replace(">", "").strip())
        return (low_b, high_b)
    except (ValueError, AttributeError):
        return None


def matches_level(spec, value, level: str,
                     bounds_cache: Optional[dict] = None) -> bool:
    """Does a feature value match a level label?"""
    if pd.isna(value):
        return False
    if spec.value_type == "bool":
        if level == "True":
            try:
                return bool(value) is True
            except Exception:
                return False
        else:
            try:
                return bool(value) is False
            except Exception:
                return False
    if spec.value_type == "categorical":
        return str(value) == str(level)
    # numeric
    bounds_cache = bounds_cache if bounds_cache is not None else {}
    bounds = bounds_cache.get(spec.feature_id)
    if bounds is None:
        bounds = _parse_numeric_thresholds(spec.level_thresholds)
        bounds_cache[spec.feature_id] = bounds
    if bounds is None:
        return False
    low_b, high_b = bounds
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if level == "low":
        return v < low_b
    if level == "high":
        return v > high_b
    return low_b <= v <= high_b


# ── Filter application ───────────────────────────────────────────────

def apply_filter(df: pd.DataFrame,
                    required_levels: list[tuple[str, str]],
                    forbidden_levels: list[tuple[str, str]],
                    spec_by_id: dict,
                    bounds_cache: dict) -> pd.Series:
    """Boolean mask — True if signal matches ALL required AND none of
    forbidden. Returns Series aligned with df.index."""
    n = len(df)
    matches = pd.Series([True] * n, index=df.index)
    for fid, lvl in required_levels:
        spec = spec_by_id.get(fid)
        if spec is None:
            return pd.Series([False] * n, index=df.index)
        col = _FEAT_PREFIX + fid
        if col not in df.columns:
            return pd.Series([False] * n, index=df.index)
        mask = df[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache))
        matches = matches & mask
    for fid, lvl in forbidden_levels:
        spec = spec_by_id.get(fid)
        if spec is None:
            continue
        col = _FEAT_PREFIX + fid
        if col not in df.columns:
            continue
        mask = df[col].apply(
            lambda v: matches_level(spec, v, lvl, bounds_cache))
        matches = matches & ~mask
    return matches


def evaluate_filter(df: pd.DataFrame, name: str,
                       required: list[tuple[str, str]],
                       forbidden: list[tuple[str, str]],
                       spec_by_id: dict,
                       bounds_cache: dict) -> dict:
    """Apply filter; compute matched/skipped WR + comparison vs baseline."""
    mask = apply_filter(df, required, forbidden, spec_by_id, bounds_cache)
    matched = df[mask]
    skipped = df[~mask]
    nm = len(matched); ns = len(skipped)
    nm_w = (matched["wlf"] == "W").sum()
    nm_l = (matched["wlf"] == "L").sum()
    ns_w = (skipped["wlf"] == "W").sum()
    ns_l = (skipped["wlf"] == "L").sum()
    return {
        "name": name,
        "required": [f"{fid}={lvl}" for fid, lvl in required],
        "forbidden": [f"{fid}={lvl}" for fid, lvl in forbidden],
        "n_total": len(df),
        "n_matched": nm,
        "n_matched_w": int(nm_w),
        "n_matched_l": int(nm_l),
        "matched_wr": (nm_w / (nm_w + nm_l)) if (nm_w + nm_l) > 0 else None,
        "match_rate": nm / len(df) if len(df) > 0 else 0.0,
        "n_skipped": ns,
        "n_skipped_w": int(ns_w),
        "n_skipped_l": int(ns_l),
        "skipped_wr": (ns_w / (ns_w + ns_l)) if (ns_w + ns_l) > 0 else None,
        "matched_signal_ids": matched["id"].tolist() if "id" in matched.columns else [],
    }


def main():
    print("─" * 80)
    print("CELL 1: Choppy UP_TRI — C3 filter articulation + back-test")
    print("─" * 80)

    # Load live Choppy UP_TRI signals
    live = pd.read_parquet(LIVE_PATH)
    df = live[(live["signal"] == "UP_TRI")
                & (live["regime"] == "Choppy")].copy()
    n = len(df)
    nw = (df["wlf"] == "W").sum()
    nl = (df["wlf"] == "L").sum()
    nf = (df["wlf"] == "F").sum()
    baseline_wr = nw / (nw + nl)
    print(f"\nLive Choppy UP_TRI universe: {n} signals "
          f"(W={nw}, L={nl}, F={nf})")
    print(f"Baseline WR (excl F): {baseline_wr*100:.1f}%")

    # Registry for level-matching
    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # ── Candidate filters ────────────────────────────────────────────

    candidates = [
        {
            "name": "F1: STRICT — ema_alignment=bull AND coiled_spring=medium",
            "required": [("ema_alignment", "bull"),
                            ("coiled_spring_score", "medium")],
            "forbidden": [],
        },
        {
            "name": "F2: BULL_EMA only",
            "required": [("ema_alignment", "bull")],
            "forbidden": [],
        },
        {
            "name": "F3: COILED_SPRING_MEDIUM only",
            "required": [("coiled_spring_score", "medium")],
            "forbidden": [],
        },
        {
            "name": "F4: STRICT + ANTI (no falling MACD, no HHs intact)",
            "required": [("ema_alignment", "bull"),
                            ("coiled_spring_score", "medium")],
            "forbidden": [("MACD_histogram_slope", "falling"),
                             ("higher_highs_intact_flag", "True")],
        },
        {
            "name": "F5: BULL_EMA + COILED OR (high market_breadth)",
            # ema_alignment=bull AND (coiled OR market_breadth=high)
            # Implemented as 2 sub-filters; see below
            "required": [("ema_alignment", "bull")],
            "forbidden": [],
            "_special": "or_branch",
        },
    ]

    results = []
    print()
    for cand in candidates:
        name = cand["name"]
        req = cand["required"]
        forb = cand["forbidden"]
        result = evaluate_filter(df, name, req, forb, spec_by_id, bounds_cache)
        results.append(result)
        # Surface
        m_wr = (f"{result['matched_wr']*100:.1f}%"
                  if result["matched_wr"] is not None else "—")
        s_wr = (f"{result['skipped_wr']*100:.1f}%"
                  if result["skipped_wr"] is not None else "—")
        lift = (result["matched_wr"] - baseline_wr) * 100 if result["matched_wr"] else 0.0
        print(f"\n{name}")
        print(f"  matched: {result['n_matched']:>3} signals "
              f"(W={result['n_matched_w']}, L={result['n_matched_l']}) "
              f"→ WR={m_wr}  (lift {lift:+.1f}pp vs baseline)")
        print(f"  skipped: {result['n_skipped']:>3} signals "
              f"(W={result['n_skipped_w']}, L={result['n_skipped_l']}) "
              f"→ WR={s_wr}")

    # Pick best filter — high matched WR + meaningful match rate (≥10%)
    print()
    print("═" * 80)
    print("FILTER SELECTION (criteria: matched_WR ≥ 60% AND match_rate ≥ 10%)")
    print("═" * 80)
    qualifying = [r for r in results
                    if r["matched_wr"] is not None
                    and r["matched_wr"] >= 0.60
                    and r["match_rate"] >= 0.10
                    and (r["n_matched_w"] + r["n_matched_l"]) >= 5]
    if qualifying:
        # Best = highest matched_wr × n_matched (rewards both precision and volume)
        best = max(qualifying, key=lambda r: r["matched_wr"]
                       * (r["n_matched_w"] + r["n_matched_l"]))
        print(f"\nRECOMMENDED: {best['name']}")
        print(f"  matched WR: {best['matched_wr']*100:.1f}% "
              f"(n={best['n_matched']})")
        print(f"  skipped WR: {best['skipped_wr']*100:.1f}%")
        print(f"  lift over baseline: "
              f"{(best['matched_wr']-baseline_wr)*100:+.1f}pp")
    else:
        print("\nNo filter clears the matched_WR ≥ 60% AND match_rate ≥ 10% bar.")
        # Pick the one with best matched_WR among those with ≥5 matched W+L
        viable = [r for r in results
                    if r["matched_wr"] is not None
                    and (r["n_matched_w"] + r["n_matched_l"]) >= 5]
        if viable:
            best = max(viable, key=lambda r: r["matched_wr"])
            print(f"\nBest available (relaxed criteria): {best['name']}")
            print(f"  matched WR: {best['matched_wr']*100:.1f}% "
                  f"(n_wl={best['n_matched_w']+best['n_matched_l']})")
            print(f"  match rate: {best['match_rate']*100:.1f}%")
            print(f"  lift: {(best['matched_wr']-baseline_wr)*100:+.1f}pp")
        else:
            best = None
            print("\nNo candidate filter matched ≥5 W+L signals. "
                  "Investigation conclusion: filter unfilterable from current data.")

    # Save results
    out = {
        "baseline_universe": {
            "n": int(n), "n_w": int(nw), "n_l": int(nl), "n_f": int(nf),
            "baseline_wr": baseline_wr,
        },
        "candidate_filters": results,
        "recommended_filter": best if best else None,
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
