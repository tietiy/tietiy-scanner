"""
Bear UP_TRI cell — B3: candidate filter articulation + back-test.

Articulates 4-5 candidate filters from B2 differentiators and tests each
against the 74 live Bear UP_TRI signals.

Bear UP_TRI baseline is exceptionally high (94.6% WR, 70W/4L) so traditional
"lift over baseline" framing matters less. Filter usefulness here is about:
  • Does the filter sustain 95%+ matched WR (precision)?
  • Does the filter capture a meaningful share of high-WR signals (recall)?
  • Does the skipped subset show concentrated losses (safety)?

A useful filter for Bear UP_TRI signals when match_rate ≥ 30% AND
matched_wr ≥ 95% AND skipped_wr < matched_wr by ≥10pp.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_HERE))

from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402

OUTPUT_PATH = _HERE / "filter_test_results.json"
LIVE_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"


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


def apply_filter(df: pd.DataFrame,
                    required_levels: list[tuple[str, str]],
                    forbidden_levels: list[tuple[str, str]],
                    spec_by_id: dict,
                    bounds_cache: dict) -> pd.Series:
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
    print("CELL: Bear UP_TRI — B3 filter articulation + back-test")
    print("─" * 80)

    live = pd.read_parquet(LIVE_PATH)
    df = live[(live["signal"] == "UP_TRI")
                & (live["regime"] == "Bear")].copy()

    def _wlf(o):
        if o in ("DAY6_WIN", "TARGET_HIT"):
            return "W"
        if o in ("DAY6_LOSS", "STOP_HIT"):
            return "L"
        if o == "DAY6_FLAT":
            return "F"
        return "?"
    df["wlf"] = df["outcome"].apply(_wlf)

    n = len(df)
    nw = (df["wlf"] == "W").sum()
    nl = (df["wlf"] == "L").sum()
    nf = (df["wlf"] == "F").sum()
    baseline_wr = nw / (nw + nl) if (nw + nl) > 0 else 0.0
    print(f"\nLive Bear UP_TRI universe: {n} signals "
          f"(W={nw}, L={nl}, F={nf})")
    print(f"Baseline WR (excl F): {baseline_wr*100:.1f}%")

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    # ── Candidate filters (per B2 differentiator output) ──────────────
    candidates = [
        {
            "name": "F1: nifty_60d=low (regime anchor — safest per LLM)",
            "required": [("nifty_60d_return_pct", "low")],
            "forbidden": [],
        },
        {
            "name": "F2: nifty_60d=low + inside_bar=True (conservative 2-feat)",
            "required": [("nifty_60d_return_pct", "low"),
                            ("inside_bar_flag", "True")],
            "forbidden": [],
        },
        {
            "name": "F3: F1 + skip wk4 + skip ema_bear (regime + defensive anti)",
            "required": [("nifty_60d_return_pct", "low")],
            "forbidden": [("day_of_month_bucket", "wk4"),
                             ("ema_alignment", "bear")],
        },
        {
            "name": "F4: F2 + swing_high_low (3-feat high precision)",
            "required": [("nifty_60d_return_pct", "low"),
                            ("inside_bar_flag", "True"),
                            ("swing_high_count_20d", "low")],
            "forbidden": [],
        },
        {
            "name": "F5: inside_bar=True only (geometric — regime-independent)",
            "required": [("inside_bar_flag", "True")],
            "forbidden": [],
        },
        {
            "name": "F6: F1 + consolidation=none (LLM #2 anchor)",
            "required": [("nifty_60d_return_pct", "low"),
                            ("consolidation_quality", "none")],
            "forbidden": [],
        },
    ]

    results = []
    print()
    for cand in candidates:
        result = evaluate_filter(df, cand["name"], cand["required"],
                                       cand["forbidden"], spec_by_id,
                                       bounds_cache)
        results.append(result)
        m_wr = (f"{result['matched_wr']*100:.1f}%"
                  if result["matched_wr"] is not None else "—")
        s_wr = (f"{result['skipped_wr']*100:.1f}%"
                  if result["skipped_wr"] is not None else "—")
        print(f"\n{cand['name']}")
        print(f"  matched: {result['n_matched']:>3} signals "
              f"(W={result['n_matched_w']}, L={result['n_matched_l']}) "
              f"→ WR={m_wr}  match_rate={result['match_rate']*100:.0f}%")
        print(f"  skipped: {result['n_skipped']:>3} signals "
              f"(W={result['n_skipped_w']}, L={result['n_skipped_l']}) "
              f"→ WR={s_wr}")

    # ── Filter selection ────────────────────────────────────────────────
    print()
    print("═" * 80)
    print("FILTER SELECTION (Bear UP_TRI: precision + recall + concentration)")
    print("═" * 80)
    print()
    print("Bear UP_TRI baseline (94.6%) is so high that filters are about")
    print("choosing the highest-PRECISION subset that retains meaningful recall.")
    print()

    # Score: matched_wr × match_rate (precision × recall trade-off)
    scored = []
    for r in results:
        if r["matched_wr"] is None:
            continue
        if (r["n_matched_w"] + r["n_matched_l"]) < 5:
            continue
        score = r["matched_wr"] * r["match_rate"]
        scored.append((r, score))
    scored.sort(key=lambda t: -t[1])

    print(f"Filter ranking (precision × recall):")
    print(f"  {'rank':<6}{'matched_wr':>12}{'match_rate':>12}{'score':>10}  filter")
    for i, (r, s) in enumerate(scored, 1):
        print(f"  {i:<6}{r['matched_wr']*100:>11.1f}%"
              f"{r['match_rate']*100:>11.0f}%{s:>10.3f}  {r['name'][:60]}")

    # Recommended: best balance of precision (≥95%) and recall (≥30%)
    qualifying = [r for r, s in scored
                    if r["matched_wr"] >= 0.95 and r["match_rate"] >= 0.30]
    if qualifying:
        # Best by matched_wr × n_matched
        best = max(qualifying,
                       key=lambda r: r["matched_wr"]
                       * (r["n_matched_w"] + r["n_matched_l"]))
        print(f"\nRECOMMENDED FILTER: {best['name']}")
        print(f"  matched WR: {best['matched_wr']*100:.1f}% "
              f"(n={best['n_matched_w']+best['n_matched_l']})")
        print(f"  skipped WR: "
              f"{(best['skipped_wr'] or 0)*100:.1f}% "
              f"(n={best['n_skipped_w']+best['n_skipped_l']})")
        print(f"  match rate: {best['match_rate']*100:.1f}%")
    elif scored:
        # Relaxed: just pick highest matched_wr × match_rate
        best = scored[0][0]
        print(f"\nNo filter clears matched_WR≥95% AND match_rate≥30%.")
        print(f"Best by score: {best['name']}")
        print(f"  matched WR: {best['matched_wr']*100:.1f}%, "
              f"match rate: {best['match_rate']*100:.1f}%")
    else:
        best = None
        print("\nNo candidate filter has ≥5 matched W+L signals.")

    out = {
        "baseline_universe": {
            "n": int(n), "n_w": int(nw), "n_l": int(nl), "n_f": int(nf),
            "baseline_wr": float(baseline_wr),
        },
        "selection_criteria": {
            "matched_wr_min": 0.95,
            "match_rate_min": 0.30,
            "rationale": "Bear UP_TRI baseline is 94.6% — filter must "
                              "sustain or improve precision while keeping "
                              "≥30% recall.",
        },
        "candidate_filters": results,
        "recommended_filter": best if best else None,
    }
    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
