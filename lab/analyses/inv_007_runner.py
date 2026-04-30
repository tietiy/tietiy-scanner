"""
INV-007 — Volatility regime filter discovery (Nifty 20-day vol percentile buckets).

Per pre-registered hypothesis in patterns.json: filtering existing UP_TRI / DOWN_TRI
/ BULL_PROXY signals by Nifty 20-day realized vol percentile bucket may yield
better tier-eligibility than unfiltered cohorts.

Pipeline:
  1. Load ^NSEI from cache; compute 20-day rolling realized vol (annualized)
  2. Bucket dates: Low (<p30), Medium (p30-p70), High (>p70) using full 15-yr distribution
  3. Join vol_bucket to backtest signals via scan_date
  4. For each (signal × vol_bucket) of 9 cells: lifetime stats + tier eval
  5. Compare each cell to unfiltered baseline (full signal cohort, all buckets)
  6. Identify surfaces (CANDIDATE per safe-default 2: |Δ WR| ≥ 5pp + p < 0.05 + n ≥ 100)

Direction handling: uses hypothesis_tester.evaluate_hypothesis exclusively, which
operates on backtest_signals.outcome column (correct SHORT semantics for DOWN_TRI
per signal_replayer.compute_d6_outcome). NO LONG-only manual pnl recomputation —
explicitly avoids the INV-006 runner bug pattern.

Outputs:
  - /lab/analyses/INV-007_findings.md (6 sections; ~10-30 KB)
  - /lab/logs/inv_007_run.log

NO promotion calls. NO patterns.json changes. Findings.md is data-only.
"""
from __future__ import annotations

import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup + imports ──────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from hypothesis_tester import (  # noqa: E402
    compute_cohort_stats,
    evaluate_hypothesis,
    wilson_lower_bound_95,
    binomial_p_value_vs_50,
)

# ── Constants ─────────────────────────────────────────────────────────

_SIGNALS_PATH = _LAB_ROOT / "output" / "backtest_signals.parquet"
_NIFTY_PATH = _LAB_ROOT / "cache" / "_index_NSEI.parquet"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-007_findings.md"

_TRAIN_END = "2022-12-31"
_TEST_START = "2023-01-01"

_VOL_LOOKBACK = 20  # 20-day rolling realized vol
_ANNUALIZE_FACTOR = math.sqrt(252)
_BUCKET_LOW_PCTL = 0.30
_BUCKET_HIGH_PCTL = 0.70

_SIGNALS_TO_EVALUATE = ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]
_VOL_BUCKETS = ["Low", "Medium", "High"]

# Surface verdict thresholds (safe-default 2)
_DELTA_WR_PP_MIN = 0.05  # 5pp
_P_VALUE_MAX = 0.05
_N_MIN_FILTERED = 100


# ── Helpers ───────────────────────────────────────────────────────────

def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
    """Two-proportion z-test; two-sided p-value. None if either n<5."""
    if n1 < 5 or n2 < 5:
        return None
    p1 = w1 / n1
    p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _classify_surface_verdict(wr_filtered: Optional[float], n_filtered: int,
                                wr_baseline: Optional[float], n_baseline: int) -> tuple:
    """Apply safe-default 2 surface threshold. Returns (verdict, delta_pp, p_val)."""
    if (wr_filtered is None or wr_baseline is None
            or n_filtered < _N_MIN_FILTERED):
        return ("INSUFFICIENT_N", None, None)
    delta = wr_filtered - wr_baseline  # signed
    w_f = round(wr_filtered * n_filtered)
    w_b = round(wr_baseline * n_baseline)
    p_val = _two_proportion_p_value(w_f, n_filtered, w_b, n_baseline)
    if abs(delta) >= _DELTA_WR_PP_MIN and p_val is not None and p_val < _P_VALUE_MAX:
        verdict = "CANDIDATE"
    elif abs(delta) >= 0.02 and p_val is not None and p_val < 0.10:
        # Below threshold but directionally consistent (per safe-default 2)
        verdict = "MARGINAL"
    else:
        verdict = "NO_EDGE"
    return (verdict, round(delta, 4), p_val)


# ── Phase 1: Compute volatility series + buckets ──────────────────────

def compute_nifty_vol_buckets() -> tuple[pd.DataFrame, dict]:
    """Load Nifty close, compute 20-day rolling realized vol, assign buckets.
    Returns (vol_df, summary_dict)."""
    print("[INV-007] loading Nifty…", flush=True)
    nifty = pd.read_parquet(_NIFTY_PATH)
    nifty.index = pd.to_datetime(nifty.index)
    nifty = nifty.sort_index()
    nifty = nifty.dropna(subset=["Close"])
    print(f"[INV-007] Nifty rows after dropna: {len(nifty)}", flush=True)

    log_returns = np.log(nifty["Close"] / nifty["Close"].shift(1))
    rolling_vol = log_returns.rolling(_VOL_LOOKBACK).std() * _ANNUALIZE_FACTOR
    n_nan_vol = rolling_vol.isna().sum()
    print(f"[INV-007] vol series NaN count (warm-up + first row): {n_nan_vol}", flush=True)

    # Percentile thresholds across full distribution (excluding NaN)
    valid_vol = rolling_vol.dropna()
    p30 = float(valid_vol.quantile(_BUCKET_LOW_PCTL))
    p70 = float(valid_vol.quantile(_BUCKET_HIGH_PCTL))
    print(f"[INV-007] vol percentiles: p30={p30:.4f}, p70={p70:.4f}", flush=True)

    def _bucket(v):
        if pd.isna(v):
            return None
        if v < p30:
            return "Low"
        if v <= p70:
            return "Medium"
        return "High"

    vol_df = pd.DataFrame({
        "date": nifty.index,
        "nifty_close": nifty["Close"].values,
        "log_ret": log_returns.values,
        "vol_20d_ann": rolling_vol.values,
    })
    vol_df["vol_bucket"] = vol_df["vol_20d_ann"].apply(_bucket)
    vol_df["scan_date_str"] = vol_df["date"].dt.strftime("%Y-%m-%d")

    # Bucket distribution summary
    bucket_counts = vol_df.dropna(subset=["vol_bucket"])["vol_bucket"].value_counts().to_dict()
    print(f"[INV-007] bucket day counts: {bucket_counts}", flush=True)

    summary = {
        "nifty_rows": len(nifty),
        "vol_nan_count": int(n_nan_vol),
        "p30": p30, "p70": p70,
        "bucket_day_counts": bucket_counts,
    }
    return vol_df, summary


# ── Phase 2: Join vol bucket to signals + per-cell evaluation ─────────

def join_signals_with_vol(signals_df: pd.DataFrame, vol_df: pd.DataFrame) -> pd.DataFrame:
    """Merge vol_bucket onto signals via scan_date."""
    vol_lookup = vol_df.set_index("scan_date_str")[["vol_20d_ann", "vol_bucket"]].copy()
    out = signals_df.copy()
    out["vol_20d_ann"] = out["scan_date"].map(vol_lookup["vol_20d_ann"])
    out["vol_bucket"] = out["scan_date"].map(vol_lookup["vol_bucket"])
    return out


def evaluate_cell(signals_df: pd.DataFrame, signal_type: str,
                   vol_bucket: str) -> dict:
    """Filter to (signal × vol_bucket) cell, run lifetime stats + tier eval."""
    cohort = signals_df[(signals_df["signal"] == signal_type)
                          & (signals_df["vol_bucket"] == vol_bucket)]
    lifetime = compute_cohort_stats(cohort, cohort_filter={})
    n_excl_flat = lifetime["n_win"] + lifetime["n_loss"]

    result = {
        "signal": signal_type, "vol_bucket": vol_bucket,
        "n_total": lifetime["n_total"], "n_resolved": lifetime["n_resolved"],
        "n_excl_flat": n_excl_flat,
        "n_win": lifetime["n_win"], "n_loss": lifetime["n_loss"],
        "n_flat": lifetime["n_flat"],
        "wr_excl_flat": lifetime["wr_excl_flat"],
        "wilson_lower_95": lifetime["wilson_lower_95"],
        "p_value_vs_50": lifetime["p_value_vs_50"],
        "boost_tier": None, "boost_train_wr": None, "boost_test_wr": None,
        "boost_drift_pp": None, "kill_tier": None, "kill_train_wr": None,
        "kill_test_wr": None, "kill_drift_pp": None,
        "tier_eval_status": None, "error": None,
    }

    if n_excl_flat < _N_MIN_FILTERED:
        result["tier_eval_status"] = "INSUFFICIENT_N"
        return result

    # Run hypothesis_tester via evaluate_hypothesis on the cohort
    # (cohort_filter applied to subset already; pass {} to evaluate_hypothesis)
    try:
        boost = evaluate_hypothesis(
            cohort, cohort_filter={}, hypothesis_type="BOOST")
        result["boost_tier"] = boost["tier"]
        result["boost_train_wr"] = boost["train_stats"]["wr_excl_flat"]
        result["boost_test_wr"] = boost["test_stats"]["wr_excl_flat"]
        result["boost_drift_pp"] = boost["drift_pp"]
        kill = evaluate_hypothesis(
            cohort, cohort_filter={}, hypothesis_type="KILL")
        result["kill_tier"] = kill["tier"]
        result["kill_train_wr"] = kill["train_stats"]["wr_excl_flat"]
        result["kill_test_wr"] = kill["test_stats"]["wr_excl_flat"]
        result["kill_drift_pp"] = kill["drift_pp"]
        result["tier_eval_status"] = "OK"
    except Exception as e:
        result["error"] = str(e)
        result["tier_eval_status"] = "ERROR"
    return result


def evaluate_unfiltered_baseline(signals_df: pd.DataFrame, signal_type: str) -> dict:
    """Compute lifetime baseline for full signal cohort (all vol buckets, including NaN excluded)."""
    cohort = signals_df[(signals_df["signal"] == signal_type)
                          & signals_df["vol_bucket"].notna()]
    lifetime = compute_cohort_stats(cohort, cohort_filter={})
    return {
        "signal": signal_type,
        "n_total": lifetime["n_total"], "n_excl_flat": lifetime["n_win"] + lifetime["n_loss"],
        "wr_excl_flat": lifetime["wr_excl_flat"],
        "wilson_lower_95": lifetime["wilson_lower_95"],
    }


# ── Findings.md writer ────────────────────────────────────────────────

def _round_pct(x: Optional[float]) -> Optional[float]:
    return round(x * 100, 2) if x is not None else None


def write_findings_md(vol_summary: dict,
                       baselines: dict,
                       cells: list[dict],
                       n_signals_loaded: int,
                       n_signals_dropped: int,
                       output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# INV-007 — Volatility regime filter discovery\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write(f"**Vol definition:** Nifty 20-day rolling realized vol "
                f"(std of daily log returns × √252).\n\n")
        f.write(f"**Bucket thresholds:** "
                f"Low <p{int(_BUCKET_LOW_PCTL*100)} ({vol_summary['p30']:.4f}); "
                f"Medium p{int(_BUCKET_LOW_PCTL*100)}-p{int(_BUCKET_HIGH_PCTL*100)}; "
                f"High >p{int(_BUCKET_HIGH_PCTL*100)} ({vol_summary['p70']:.4f}).\n\n")
        f.write(f"**Bucket day counts (15-year distribution):** "
                f"{vol_summary['bucket_day_counts']}\n\n")

        # Caveats
        f.write("---\n\n## ⚠️ Caveats\n\n")
        f.write(f"**Vol warm-up exclusion:** First {_VOL_LOOKBACK} trading days have "
                f"NaN rolling vol; signals from those dates excluded from analysis. "
                f"Total signals dropped: {n_signals_dropped} of {n_signals_loaded} loaded.\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate) inherited:** filtered cohorts at "
                "marginal n vulnerable to miss-rate; user re-validates surfaced "
                "candidates post-Caveat 2 audit before any promotion.\n\n")
        f.write("**Direction handling:** uses `hypothesis_tester.evaluate_hypothesis` "
                "exclusively which operates on `backtest_signals.outcome` column "
                "(correct SHORT semantics for DOWN_TRI per `signal_replayer.compute_d6_outcome`). "
                "No LONG-only manual pnl recomputation — explicitly avoids INV-006 runner bug pattern.\n\n")

        # ── Section 0 — Methodology ──
        f.write("---\n\n## Methodology\n\n")
        f.write(f"1. Load `^NSEI` close from cache; compute log returns; "
                f"rolling 20-day std × √252 = annualized realized vol.\n")
        f.write(f"2. Compute percentile thresholds across full 15-year vol distribution: "
                f"p30={vol_summary['p30']:.4f}, p70={vol_summary['p70']:.4f}.\n")
        f.write(f"3. Assign vol_bucket per date: Low (<p30), Medium (p30-p70), High (>p70).\n")
        f.write(f"4. Join vol_bucket to backtest signals via `scan_date`.\n")
        f.write(f"5. For each (signal × vol_bucket) of 9 cells: lifetime stats + train/test "
                f"split + hypothesis_tester (BOOST + KILL).\n")
        f.write(f"6. Compare each cell to unfiltered baseline (full signal cohort, "
                f"all buckets); classify CANDIDATE / MARGINAL / NO_EDGE per safe-default 2 "
                f"(|Δ WR| ≥ 5pp + p < 0.05 + n ≥ 100 → CANDIDATE).\n\n")

        # ── Section 1 — Per-signal × per-bucket results ──
        f.write("---\n\n## Section 1 — Per-signal × per-bucket results\n\n")
        f.write("Unfiltered baselines (lifetime, full signal cohort across all buckets, "
                "vol-NaN signals excluded):\n\n")
        f.write("| Signal | n_excl_flat | Lifetime WR | Wilson_lower_95 |\n")
        f.write("|--------|-------------|-------------|------------------|\n")
        for sig in _SIGNALS_TO_EVALUATE:
            b = baselines.get(sig, {})
            f.write(f"| {sig} | {b.get('n_excl_flat')} | {b.get('wr_excl_flat')} | "
                    f"{b.get('wilson_lower_95')} |\n")
        f.write("\nPer-cell results (signal × vol_bucket):\n\n")
        f.write("| Signal | Vol_bucket | n_excl_flat | WR | Wilson_lower | "
                "Δ vs base (pp) | p-value | BoostTier | KillTier | Verdict |\n")
        f.write("|--------|-----------|-------------|-----|--------------|"
                "----------------|---------|----------|----------|--------|\n")
        for cell in cells:
            sig = cell["signal"]; bucket = cell["vol_bucket"]
            n = cell["n_excl_flat"]; wr = cell["wr_excl_flat"]
            wilson = cell["wilson_lower_95"]
            base = baselines.get(sig, {})
            verdict, delta, p_val = _classify_surface_verdict(
                wr, n, base.get("wr_excl_flat"), base.get("n_excl_flat", 0))
            delta_pp = _round_pct(delta)
            p_str = p_val if p_val is not None else "—"
            boost_tier = cell.get("boost_tier", "—")
            kill_tier = cell.get("kill_tier", "—")
            if cell["tier_eval_status"] == "INSUFFICIENT_N":
                boost_tier = kill_tier = "INSUFFICIENT_N"
                verdict = "INSUFFICIENT_N"
            elif cell["tier_eval_status"] == "ERROR":
                boost_tier = kill_tier = f"ERROR: {cell.get('error', '?')}"
            f.write(f"| {sig} | {bucket} | {n} | {wr} | {wilson} | "
                    f"{delta_pp} | {p_str} | {boost_tier} | {kill_tier} | {verdict} |\n")
        f.write("\n")

        # ── Section 2 — Surfaces ──
        f.write("---\n\n## Section 2 — Surfaced filter candidates\n\n")
        candidates = []
        marginals = []
        for cell in cells:
            base = baselines.get(cell["signal"], {})
            verdict, delta, p_val = _classify_surface_verdict(
                cell["wr_excl_flat"], cell["n_excl_flat"],
                base.get("wr_excl_flat"), base.get("n_excl_flat", 0))
            entry = {**cell, "verdict": verdict, "delta_wr": delta, "p_value": p_val}
            if verdict == "CANDIDATE":
                candidates.append(entry)
            elif verdict == "MARGINAL":
                marginals.append(entry)
        candidates.sort(key=lambda x: -abs(x.get("delta_wr") or 0))
        f.write(f"**CANDIDATE cells (|Δ WR| ≥ 5pp + p < 0.05 + n ≥ 100):** {len(candidates)}\n\n")
        if candidates:
            f.write("| Signal | Vol_bucket | n | WR | Δ vs base (pp) | p-value | Direction |\n")
            f.write("|--------|-----------|---|-----|---------------|---------|----------|\n")
            for c in candidates:
                direction = "improves" if (c.get("delta_wr") or 0) > 0 else "degrades"
                f.write(f"| {c['signal']} | {c['vol_bucket']} | {c['n_excl_flat']} | "
                        f"{c['wr_excl_flat']} | {_round_pct(c['delta_wr'])} | "
                        f"{c['p_value']} | {direction} |\n")
        else:
            f.write("_No CANDIDATE cells surfaced._\n")
        f.write(f"\n**MARGINAL cells (|Δ WR| ≥ 2pp + p < 0.10 but below CANDIDATE threshold):** {len(marginals)}\n\n")
        if marginals:
            f.write("| Signal | Vol_bucket | n | WR | Δ vs base (pp) | p-value |\n")
            f.write("|--------|-----------|---|-----|---------------|---------|\n")
            for m in marginals:
                f.write(f"| {m['signal']} | {m['vol_bucket']} | {m['n_excl_flat']} | "
                        f"{m['wr_excl_flat']} | {_round_pct(m['delta_wr'])} | "
                        f"{m['p_value']} |\n")
        else:
            f.write("_No MARGINAL cells._\n")
        f.write("\n")

        # ── Section 3 — Tier evaluation per surfaced cell ──
        f.write("---\n\n## Section 3 — Tier evaluation per cell\n\n")
        f.write("Train/test OOS split (2011-2022 / 2023-2026); tier per "
                "PROMOTION_PROTOCOL.md Gate 3.\n\n")
        f.write("| Signal | Vol_bucket | Boost_train_WR | Boost_test_WR | "
                "Boost_drift_pp | BoostTier | Kill_train_WR | Kill_test_WR | "
                "Kill_drift_pp | KillTier |\n")
        f.write("|--------|-----------|----------------|----------------|"
                "----------------|----------|---------------|--------------|"
                "----------------|----------|\n")
        for cell in cells:
            if cell["tier_eval_status"] != "OK":
                continue
            f.write(f"| {cell['signal']} | {cell['vol_bucket']} | "
                    f"{cell['boost_train_wr']} | {cell['boost_test_wr']} | "
                    f"{cell['boost_drift_pp']} | {cell['boost_tier']} | "
                    f"{cell['kill_train_wr']} | {cell['kill_test_wr']} | "
                    f"{cell['kill_drift_pp']} | {cell['kill_tier']} |\n")
        f.write("\n")
        # Note any cohorts that earned tier (S/A/B)
        tier_hits = [c for c in cells if c["tier_eval_status"] == "OK"
                      and (c.get("boost_tier") in ("S", "A", "B")
                           or c.get("kill_tier") in ("S", "A", "B"))]
        f.write(f"**Cells earning Lab tier (S/A/B) on either BOOST or KILL hypothesis:** "
                f"{len(tier_hits)}\n\n")
        for hit in tier_hits:
            tiers = []
            if hit.get("boost_tier") in ("S", "A", "B"):
                tiers.append(f"BOOST {hit['boost_tier']}")
            if hit.get("kill_tier") in ("S", "A", "B"):
                tiers.append(f"KILL {hit['kill_tier']}")
            f.write(f"- `{hit['signal']} × {hit['vol_bucket']}` → {', '.join(tiers)}\n")
        f.write("\n")

        # ── Section 4 — Cross-signal patterns ──
        f.write("---\n\n## Section 4 — Cross-signal patterns\n\n")
        f.write("Per-bucket Δ WR averaged across signal types:\n\n")
        per_bucket_deltas = {b: [] for b in _VOL_BUCKETS}
        for cell in cells:
            base = baselines.get(cell["signal"], {})
            if (cell["wr_excl_flat"] is not None
                    and base.get("wr_excl_flat") is not None
                    and cell["n_excl_flat"] >= _N_MIN_FILTERED):
                per_bucket_deltas[cell["vol_bucket"]].append(
                    cell["wr_excl_flat"] - base["wr_excl_flat"])
        f.write("| Vol_bucket | Avg Δ WR (pp) | n_signals_evaluated |\n")
        f.write("|-----------|---------------|----------------------|\n")
        for b in _VOL_BUCKETS:
            deltas = per_bucket_deltas[b]
            if deltas:
                avg = round(sum(deltas) / len(deltas) * 100, 2)
                f.write(f"| {b} | {avg:+.2f} | {len(deltas)} |\n")
            else:
                f.write(f"| {b} | (no cells qualifying) | 0 |\n")
        f.write("\n")
        f.write("Universal direction interpretation:\n")
        for b in _VOL_BUCKETS:
            deltas = per_bucket_deltas[b]
            if not deltas:
                continue
            avg_pp = sum(deltas) / len(deltas) * 100
            same_sign = all(d >= 0 for d in deltas) or all(d <= 0 for d in deltas)
            if abs(avg_pp) >= 2 and same_sign:
                direction = "improves" if avg_pp > 0 else "degrades"
                f.write(f"- **{b} vol regime: universally {direction}** WR "
                        f"(avg {avg_pp:+.2f} pp across all 3 signals; same sign).\n")
            else:
                f.write(f"- **{b} vol regime: signal-specific** (avg {avg_pp:+.2f} pp; "
                        f"signs vary OR magnitude below 2pp).\n")
        f.write("\n")

        # ── Section 5 — Headline findings ──
        f.write("---\n\n## Section 5 — Headline findings (data only; NO promotion calls)\n\n")
        f.write(f"- **Cells evaluated:** {len(cells)} (3 signals × 3 vol buckets)\n")
        n_insuff = sum(1 for c in cells if c["tier_eval_status"] == "INSUFFICIENT_N")
        n_err = sum(1 for c in cells if c["tier_eval_status"] == "ERROR")
        f.write(f"- **INSUFFICIENT_N cells:** {n_insuff}\n")
        f.write(f"- **ERROR cells:** {n_err}\n")
        f.write(f"- **CANDIDATE filter cells:** {len(candidates)}\n")
        f.write(f"- **MARGINAL cells:** {len(marginals)}\n")
        f.write(f"- **Tier-earning cells (BOOST or KILL S/A/B):** {len(tier_hits)}\n\n")
        # Synthesized 1-2 sentence summary
        if candidates:
            top = candidates[0]
            f.write(f"**Headline:** Vol regime filter surfaces {len(candidates)} "
                    f"CANDIDATE(s); strongest is `{top['signal']} × {top['vol_bucket']}` "
                    f"at Δ WR {_round_pct(top['delta_wr']):+.2f}pp (p={top['p_value']}). "
                    f"User reviews per-cell tier eligibility before any filter promotion.\n\n")
        elif marginals:
            f.write(f"**Headline:** No CANDIDATE filters surfaced at the 5pp+0.05 threshold; "
                    f"{len(marginals)} MARGINAL cells suggest directional patterns but "
                    f"below promotion-grade significance. Vol regime filter does not yield "
                    f"clear edge in current universe.\n\n")
        else:
            f.write(f"**Headline:** Vol regime filter shows NO_EDGE across all 9 cells. "
                    f"No filter promotion candidates surfaced; vol regime adds no statistically "
                    f"significant differentiation to UP_TRI / DOWN_TRI / BULL_PROXY signals "
                    f"in 15-year backtest.\n\n")

        # ── Section 6 — Open questions ──
        f.write("---\n\n## Section 6 — Open questions for user review\n\n")
        f.write("1. **CANDIDATE filter promotion:** for each CANDIDATE cell in Section 2, "
                "does sub-cohort tier-eligibility (Section 3) clear PROMOTION_PROTOCOL Gate 3? "
                "User decides per cell whether to add filter to mini_scanner_rules.\n\n")
        f.write("2. **Cross-signal universal patterns (Section 4):** if any vol regime "
                "universally improves or degrades WR across all 3 signal types, consider "
                "global filter (single config flag) vs signal-specific (per-signal filter).\n\n")
        f.write("3. **Caveat 2 audit dependency:** any CANDIDATE filter at marginal n "
                "(say n_filtered < 200) needs Caveat 2 audit before promotion.\n\n")
        f.write("4. **Vol bucket boundary sensitivity:** current p30 / p70 are arbitrary; "
                "user could request sensitivity analysis (p25/p75 or p20/p80) if findings "
                "depend strongly on bucket definition.\n\n")
        f.write("5. **patterns.json INV-007 status:** PRE_REGISTERED → COMPLETED is "
                "user-only transition.\n\n")

        f.write("---\n\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. "
                "No promotion decisions are made by CC. "
                "User reviews end-to-end + applies Gate 7 (user review) before any "
                "patterns.json status change or main-branch promotion.\n")


# ── Main orchestrator ─────────────────────────────────────────────────

def main():
    print(f"[INV-007] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)

    vol_df, vol_summary = compute_nifty_vol_buckets()

    print(f"[INV-007] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    n_loaded = len(signals_df)
    print(f"[INV-007] loaded {n_loaded} signals", flush=True)

    signals_with_vol = join_signals_with_vol(signals_df, vol_df)
    n_with_bucket = signals_with_vol["vol_bucket"].notna().sum()
    n_dropped = n_loaded - n_with_bucket
    print(f"[INV-007] signals with valid vol_bucket: {n_with_bucket} "
          f"(dropped {n_dropped})", flush=True)
    signals_kept = signals_with_vol[signals_with_vol["vol_bucket"].notna()].copy()

    # Unfiltered baselines per signal
    baselines = {}
    for sig in _SIGNALS_TO_EVALUATE:
        baselines[sig] = evaluate_unfiltered_baseline(signals_kept, sig)
        print(f"[INV-007] baseline {sig}: n={baselines[sig]['n_excl_flat']}, "
              f"WR={baselines[sig]['wr_excl_flat']}", flush=True)

    # Per-cell evaluation
    cells = []
    for sig in _SIGNALS_TO_EVALUATE:
        for bucket in _VOL_BUCKETS:
            print(f"[INV-007] evaluating {sig} × {bucket}…", flush=True)
            cell = evaluate_cell(signals_kept, sig, bucket)
            cells.append(cell)
            print(f"  → n_excl_flat={cell['n_excl_flat']}, WR={cell['wr_excl_flat']}, "
                  f"status={cell['tier_eval_status']}, "
                  f"boost={cell.get('boost_tier')}, kill={cell.get('kill_tier')}",
                  flush=True)

    print(f"[INV-007] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(vol_summary, baselines, cells, n_loaded, n_dropped, _OUTPUT_FINDINGS)
    print(f"[INV-007] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-007] FATAL: {e}\n{tb}", flush=True)
        try:
            _OUTPUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
            with open(_OUTPUT_FINDINGS, "w") as f:
                f.write(f"# INV-007 — CRASH at {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write(f"```\n{tb}\n```\n")
        except Exception:
            pass
        raise
