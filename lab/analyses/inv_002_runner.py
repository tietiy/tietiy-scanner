"""
INV-002 — UP_TRI × Bank × Bear validation (small-sample hypothesis).

Live evidence: n=8 W=8 L=0 → 100% WR. Suspiciously perfect; validate against
15-year backtest before any tier promotion.

Cohort: signal=UP_TRI AND sector=Bank AND regime=Bear.
Hypothesis type (Lab tier evaluation): BOOST (cohort presumed positive-edge per
live evidence; investigation tests whether 15-year history corroborates).

Sections (per ROADMAP INV-002):
  1. Lifetime cohort baseline + Bear sub-period analysis (sample-window bias check)
  2. Mechanism-candidate analysis:
     - 2a Oversold rebound (Bank Nifty 14-day RSI < 30 at signal)
     - 2b Rate-cycle correlation proxy (Bank Nifty 60-day return per Caveat 1)
     - 2c Sample-window bias (sub-period WR variance test)
  3. Tier evaluation (parent BOOST + sub-cohort FILTER on differentiators)
  4. Headline findings (data only)
  5. Findings.md generation

Bear sub-period grouping (per safe-default 7): consecutive Bear days; gap > 14
calendar days starts new sub-period; labeled by start year.

NO promotion decisions. NO scope expansion.

Outputs:
  - /lab/analyses/INV-002_findings.md
  - /lab/logs/inv_002_run.log
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
    evaluate_boost_tier,
    evaluate_kill_tier,
    evaluate_hypothesis,
    filter_cohort,
    wilson_lower_bound_95,
    binomial_p_value_vs_50,
)

# ── Constants ─────────────────────────────────────────────────────────

_SIGNALS_PATH = _LAB_ROOT / "output" / "backtest_signals.parquet"
_REGIME_PATH = _LAB_ROOT / "output" / "regime_history.parquet"
_NSEBANK_PATH = _LAB_ROOT / "cache" / "_index_NSEBANK.parquet"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-002_findings.md"

_TRAIN_END = "2022-12-31"
_TEST_START = "2023-01-01"
_DIFF_THRESHOLD_PP = 0.10
_N_MIN_SUBSET = 20
_P_VALUE_DIFF_MAX = 0.10

_BEAR_SUBPERIOD_GAP_DAYS = 14  # gap > N starts new sub-period
_RSI_OVERSOLD_THRESHOLD = 30
_RSI_PERIOD = 14


# ── Helpers ───────────────────────────────────────────────────────────

def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
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


def _classify_diff_verdict(wr_a: Optional[float], n_a: int,
                            wr_b: Optional[float], n_b: int) -> tuple:
    if wr_a is None or wr_b is None or n_a < _N_MIN_SUBSET or n_b < _N_MIN_SUBSET:
        return ("INSUFFICIENT_N", None, None)
    delta = abs(wr_a - wr_b)
    w_a = round(wr_a * n_a)
    w_b = round(wr_b * n_b)
    p_val = _two_proportion_p_value(w_a, n_a, w_b, n_b)
    if delta >= _DIFF_THRESHOLD_PP and (p_val is not None and p_val < _P_VALUE_DIFF_MAX):
        verdict = "CANDIDATE"
    else:
        verdict = "INCONCLUSIVE"
    return (verdict, round(delta, 4), p_val)


def _section_separator(title: str) -> str:
    return f"\n\n## {title}\n\n"


def _round_pct(x: float) -> float:
    return round(x * 100, 2) if x is not None else None


def _compute_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Standard RSI: Wilder smoothing approximation via simple rolling mean."""
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ── Cohort filter + Bear sub-period grouping ──────────────────────────

def filter_inv_002_cohort(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["signal"] == "UP_TRI") &
              (df["sector"] == "Bank") &
              (df["regime"] == "Bear")].copy()


def identify_bear_subperiods(regime_df: pd.DataFrame) -> list[dict]:
    """Group consecutive Bear days into sub-periods. Returns list of
    {sub_period_id, start_date, end_date, n_days}."""
    bear_df = regime_df[regime_df["regime"] == "Bear"].copy()
    if bear_df.empty:
        return []
    bear_df["date_dt"] = pd.to_datetime(bear_df["date"])
    bear_df = bear_df.sort_values("date_dt").reset_index(drop=True)
    sub_periods = []
    current_start = bear_df["date_dt"].iloc[0]
    current_end = current_start
    for i in range(1, len(bear_df)):
        d = bear_df["date_dt"].iloc[i]
        gap = (d - current_end).days
        if gap > _BEAR_SUBPERIOD_GAP_DAYS:
            sub_periods.append({
                "start": current_start.strftime("%Y-%m-%d"),
                "end": current_end.strftime("%Y-%m-%d"),
                "n_days": (current_end - current_start).days + 1,
                "label": f"{current_start.year}_Bear_{current_start.month:02d}",
            })
            current_start = d
        current_end = d
    sub_periods.append({
        "start": current_start.strftime("%Y-%m-%d"),
        "end": current_end.strftime("%Y-%m-%d"),
        "n_days": (current_end - current_start).days + 1,
        "label": f"{current_start.year}_Bear_{current_start.month:02d}",
    })
    return sub_periods


def assign_subperiod_to_signal(scan_date: str, sub_periods: list[dict]) -> Optional[str]:
    sd = pd.Timestamp(scan_date)
    for sp in sub_periods:
        if pd.Timestamp(sp["start"]) <= sd <= pd.Timestamp(sp["end"]):
            return sp["label"]
    return None


# ── Section 1 — Lifetime baseline + Bear sub-periods ─────────────────

def section_1_lifetime_baseline(cohort_df: pd.DataFrame, regime_df: pd.DataFrame) -> dict:
    n_total = len(cohort_df)
    stats = compute_cohort_stats(cohort_df, cohort_filter={})
    cohort_df = cohort_df.copy()
    cohort_df["scan_year"] = pd.to_datetime(cohort_df["scan_date"]).dt.year
    yearly = []
    for year, group in cohort_df.groupby("scan_year"):
        year_stats = compute_cohort_stats(group, cohort_filter={})
        yearly.append({
            "year": int(year),
            "n_resolved": year_stats["n_resolved"],
            "n_win": year_stats["n_win"],
            "n_loss": year_stats["n_loss"],
            "n_flat": year_stats["n_flat"],
            "wr_excl_flat": year_stats["wr_excl_flat"],
            "wilson_lower_95": year_stats["wilson_lower_95"],
        })
    sub_periods = identify_bear_subperiods(regime_df)
    cohort_df["bear_subperiod"] = cohort_df["scan_date"].apply(
        lambda d: assign_subperiod_to_signal(d, sub_periods))
    sub_period_stats = []
    for sp in sub_periods:
        sub_signals = cohort_df[cohort_df["bear_subperiod"] == sp["label"]]
        s = compute_cohort_stats(sub_signals, cohort_filter={})
        sub_period_stats.append({
            "label": sp["label"],
            "start": sp["start"], "end": sp["end"], "n_days": sp["n_days"],
            "n_signals": len(sub_signals),
            "n_resolved": s["n_resolved"], "n_win": s["n_win"],
            "n_loss": s["n_loss"], "n_flat": s["n_flat"],
            "wr_excl_flat": s["wr_excl_flat"],
            "wilson_lower_95": s["wilson_lower_95"],
        })
    cohort_df["sd_dt"] = pd.to_datetime(cohort_df["scan_date"])
    train_df = cohort_df[cohort_df["sd_dt"] <= pd.Timestamp(_TRAIN_END)]
    test_df = cohort_df[cohort_df["sd_dt"] >= pd.Timestamp(_TEST_START)]
    train_stats = compute_cohort_stats(train_df, cohort_filter={})
    test_stats = compute_cohort_stats(test_df, cohort_filter={})
    return {
        "n_total": n_total,
        "lifetime": stats,
        "yearly_breakdown": yearly,
        "train_stats": train_stats,
        "test_stats": test_stats,
        "bear_subperiods_total": len(sub_periods),
        "bear_subperiods": sub_period_stats,
    }


# ── Section 2a — Oversold rebound (RSI < 30) ─────────────────────────

def section_2a_oversold_rebound(cohort_df: pd.DataFrame) -> dict:
    if not _NSEBANK_PATH.exists():
        return {"verdict": "DATA_UNAVAILABLE", "reason": f"{_NSEBANK_PATH.name} missing"}
    bank_idx = pd.read_parquet(_NSEBANK_PATH)
    bank_idx.index = pd.to_datetime(bank_idx.index)
    bank_idx = bank_idx.sort_index()
    bank_idx["rsi_14"] = _compute_rsi(bank_idx["Close"], period=_RSI_PERIOD)
    cohort_df = cohort_df.copy()
    cohort_df["sd_dt"] = pd.to_datetime(cohort_df["scan_date"])
    rsi_at_signal = []
    for sd in cohort_df["sd_dt"].unique():
        ts = pd.Timestamp(sd)
        slc = bank_idx.loc[:ts]
        if len(slc) < _RSI_PERIOD + 1:
            rsi_at_signal.append((sd, np.nan))
            continue
        rsi = float(slc["rsi_14"].iloc[-1]) if not pd.isna(slc["rsi_14"].iloc[-1]) else np.nan
        rsi_at_signal.append((sd, rsi))
    rsi_df = pd.DataFrame(rsi_at_signal, columns=["sd_dt", "nbank_rsi_14"])
    cohort_df = cohort_df.merge(rsi_df, on="sd_dt", how="left")
    oversold = cohort_df[cohort_df["nbank_rsi_14"] < _RSI_OVERSOLD_THRESHOLD]
    not_oversold = cohort_df[cohort_df["nbank_rsi_14"] >= _RSI_OVERSOLD_THRESHOLD]
    oversold_stats = compute_cohort_stats(oversold, cohort_filter={})
    not_oversold_stats = compute_cohort_stats(not_oversold, cohort_filter={})
    n_os = oversold_stats["n_win"] + oversold_stats["n_loss"]
    n_nos = not_oversold_stats["n_win"] + not_oversold_stats["n_loss"]
    verdict, delta, p_val = _classify_diff_verdict(
        oversold_stats["wr_excl_flat"], n_os,
        not_oversold_stats["wr_excl_flat"], n_nos)
    return {
        "oversold_rsi_lt_30": oversold_stats,
        "not_oversold_rsi_gte_30": not_oversold_stats,
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_oversold_resolved": n_os, "n_not_oversold_resolved": n_nos,
        "median_rsi_at_signal": (round(cohort_df["nbank_rsi_14"].median(), 2)
                                  if not cohort_df["nbank_rsi_14"].dropna().empty else None),
    }


# ── Section 2b — Rate-cycle correlation proxy ─────────────────────────

def section_2b_rate_cycle_proxy(cohort_df: pd.DataFrame) -> dict:
    """Bank Nifty 60-day return at signal as Caveat 1 proxy for rate-cycle.
    Negative 60-day return = bear-leaning macro = potential rate-cut window."""
    if not _NSEBANK_PATH.exists():
        return {"verdict": "DATA_UNAVAILABLE", "reason": f"{_NSEBANK_PATH.name} missing"}
    bank_idx = pd.read_parquet(_NSEBANK_PATH)
    bank_idx.index = pd.to_datetime(bank_idx.index)
    bank_idx = bank_idx.sort_index()
    cohort_df = cohort_df.copy()
    cohort_df["sd_dt"] = pd.to_datetime(cohort_df["scan_date"])
    rets = []
    for sd in cohort_df["sd_dt"].unique():
        ts = pd.Timestamp(sd)
        slc = bank_idx.loc[:ts]
        if len(slc) < 61:
            rets.append((sd, np.nan))
            continue
        last_close = float(slc["Close"].iloc[-1])
        prev_close = float(slc["Close"].iloc[-61])
        ret = (last_close / prev_close - 1) if prev_close > 0 else np.nan
        rets.append((sd, ret))
    ret_df = pd.DataFrame(rets, columns=["sd_dt", "nbank_60d_ret"])
    cohort_df = cohort_df.merge(ret_df, on="sd_dt", how="left")
    negative = cohort_df[cohort_df["nbank_60d_ret"] < 0]
    positive = cohort_df[cohort_df["nbank_60d_ret"] >= 0]
    neg_stats = compute_cohort_stats(negative, cohort_filter={})
    pos_stats = compute_cohort_stats(positive, cohort_filter={})
    n_neg = neg_stats["n_win"] + neg_stats["n_loss"]
    n_pos = pos_stats["n_win"] + pos_stats["n_loss"]
    verdict, delta, p_val = _classify_diff_verdict(
        neg_stats["wr_excl_flat"], n_neg, pos_stats["wr_excl_flat"], n_pos)
    return {
        "negative_60d_ret_subset": neg_stats,
        "positive_60d_ret_subset": pos_stats,
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_negative_resolved": n_neg, "n_positive_resolved": n_pos,
        "approximation_note": (
            "Per Caveat 1, RBI rate cycle data unavailable; using ^NSEBANK 60-day "
            "return as proxy. Negative 60-day return ≈ bear-leaning macro ≈ rate-cut "
            "expectation window. Imperfect proxy; actual rate-cycle data is policy-meeting calendar."
        ),
    }


# ── Section 2c — Sample-window bias (sub-period WR variance) ─────────

def section_2c_sample_window_bias(cohort_df: pd.DataFrame, regime_df: pd.DataFrame) -> dict:
    sub_periods = identify_bear_subperiods(regime_df)
    cohort_df = cohort_df.copy()
    cohort_df["bear_subperiod"] = cohort_df["scan_date"].apply(
        lambda d: assign_subperiod_to_signal(d, sub_periods))
    sub_period_stats = []
    for sp in sub_periods:
        sub_signals = cohort_df[cohort_df["bear_subperiod"] == sp["label"]]
        s = compute_cohort_stats(sub_signals, cohort_filter={})
        n = s["n_win"] + s["n_loss"]
        sub_period_stats.append({
            "label": sp["label"],
            "n_signals": len(sub_signals),
            "n_resolved": s["n_resolved"],
            "wr_excl_flat": s["wr_excl_flat"],
            "n_resolved_excl_flat": n,
            "wilson_lower_95": s["wilson_lower_95"],
        })
    valid = [sp for sp in sub_period_stats
             if sp["wr_excl_flat"] is not None and sp["n_resolved_excl_flat"] >= 5]
    n_valid = len(valid)
    if n_valid < 3:
        verdict = "INSUFFICIENT_SUBPERIODS"
        wr_min = wr_max = wr_range = None
        single_window_flag = (n_valid <= 1)
    else:
        wr_values = [sp["wr_excl_flat"] for sp in valid]
        wr_min = round(min(wr_values), 4)
        wr_max = round(max(wr_values), 4)
        wr_range = round(wr_max - wr_min, 4)
        single_window_flag = False
        # If WR range across sub-periods > 0.20 → high variance (sample-window suspicion)
        if wr_range > 0.20:
            verdict = "HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT"
        elif wr_range > 0.10:
            verdict = "MODERATE_VARIANCE"
        else:
            verdict = "LOW_VARIANCE_STABLE"
    return {
        "n_subperiods_total": len(sub_periods),
        "n_subperiods_with_signals": n_valid,
        "single_window_flag": single_window_flag,
        "wr_min_across_subperiods": wr_min,
        "wr_max_across_subperiods": wr_max,
        "wr_range_across_subperiods": wr_range,
        "subperiod_breakdown": sub_period_stats,
        "verdict": verdict,
    }


# ── Section 3 — Tier evaluation ───────────────────────────────────────

def section_3_tier_evaluation(signals_df: pd.DataFrame) -> dict:
    parent = evaluate_hypothesis(
        signals_df,
        cohort_filter={"signal": "UP_TRI", "sector": "Bank", "regime": "Bear"},
        hypothesis_type="BOOST",
    )
    return {"parent_boost_evaluation": parent}


# ── Findings.md writer ────────────────────────────────────────────────

def _fmt_stats(s: dict, indent: str = "") -> str:
    if not s:
        return f"{indent}_no stats_\n"
    keys = ["n_total", "n_resolved", "n_open", "n_win", "n_loss", "n_flat",
            "wr_excl_flat", "wilson_lower_95", "p_value_vs_50"]
    lines = []
    for k in keys:
        v = s.get(k)
        if v is not None:
            lines.append(f"{indent}- {k}: {v}")
    return "\n".join(lines) + "\n"


def _make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (f != f) else round(f, 6)
    if isinstance(obj, np.ndarray):
        return [_make_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, float) and obj != obj:
        return None
    return obj


def write_findings_md(results: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# INV-002 — UP_TRI × Bank × Bear validation (small-sample hypothesis)\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write("**Cohort filter:** signal=UP_TRI AND sector=Bank AND regime=Bear\n\n")
        f.write("**Hypothesis type (Lab tier evaluation):** BOOST\n\n")
        f.write("**Live evidence at registration:** n=8 W=8 L=0 → 100% WR\n\n")

        f.write("---\n\n")
        f.write("## ⚠️ Caveats carried forward\n\n")
        f.write("**Caveat 1 (sector indices missing):** Section 2b uses ^NSEBANK 60-day "
                "return as proxy for rate-cycle. Imperfect; actual RBI policy meeting "
                "calendar is out of scope.\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate):** Lifetime cohort n is moderate (~2.6K "
                "resolved); per-sub-period n may be small (some Bear sub-periods <30 signals). "
                "Sub-period findings at small n vulnerable to Caveat 2.\n\n")

        # Section 1
        f.write(_section_separator("Section 1 — Lifetime cohort baseline + Bear sub-period analysis"))
        s1 = results.get("section_1", {})
        if "ERROR" in s1:
            f.write(f"**ANALYSIS FAILED:** `{s1['ERROR']}`\n\n```\n{s1.get('traceback','')}\n```\n")
        else:
            f.write(f"**Total cohort signals:** {s1.get('n_total')}\n\n")
            f.write("**Lifetime stats:**\n\n")
            f.write(_fmt_stats(s1.get("lifetime", {})))
            f.write("\n**Train period (2011-01 → 2022-12):**\n\n")
            f.write(_fmt_stats(s1.get("train_stats", {})))
            f.write("\n**Test period (2023-01 → 2026-04):**\n\n")
            f.write(_fmt_stats(s1.get("test_stats", {})))
            f.write(f"\n**Bear sub-periods identified:** {s1.get('bear_subperiods_total')}\n\n")
            f.write("**Year-by-year breakdown:**\n\n")
            f.write("| Year | n_resolved | n_win | n_loss | n_flat | WR_excl_flat | Wilson_lower_95 |\n")
            f.write("|------|-----------|-------|--------|--------|--------------|------------------|\n")
            for y in s1.get("yearly_breakdown", []):
                f.write(f"| {y['year']} | {y['n_resolved']} | {y['n_win']} | "
                        f"{y['n_loss']} | {y['n_flat']} | {y['wr_excl_flat']} | "
                        f"{y['wilson_lower_95']} |\n")
            f.write("\n**Bear sub-period breakdown:**\n\n")
            f.write("| Label | Start | End | Days | Signals | n_resolved | WR_excl_flat | Wilson_lower_95 |\n")
            f.write("|-------|-------|-----|------|---------|-----------|--------------|------------------|\n")
            for sp in s1.get("bear_subperiods", []):
                f.write(f"| {sp['label']} | {sp['start']} | {sp['end']} | "
                        f"{sp['n_days']} | {sp['n_signals']} | {sp['n_resolved']} | "
                        f"{sp['wr_excl_flat']} | {sp['wilson_lower_95']} |\n")

        # Section 2
        f.write(_section_separator("Section 2 — Mechanism-candidate analysis"))
        for sec_name, label in [
            ("section_2a_oversold_rebound", "2a — Oversold rebound (Bank Nifty RSI-14 < 30)"),
            ("section_2b_rate_cycle_proxy", "2b — Rate-cycle correlation (Bank Nifty 60-day return proxy per Caveat 1)"),
            ("section_2c_sample_window_bias", "2c — Sample-window bias (Bear sub-period WR variance)"),
        ]:
            f.write(f"### {label}\n\n")
            data = results.get(sec_name, {})
            if "ERROR" in data:
                f.write(f"**ANALYSIS FAILED:** `{data['ERROR']}`\n\n```\n{data.get('traceback','')}\n```\n\n")
            else:
                verdict = data.get("verdict", "?")
                f.write(f"**Verdict:** `{verdict}`\n\n")
                if "delta_wr" in data and data.get("delta_wr") is not None:
                    f.write(f"**Δ WR (subset A vs B):** {data['delta_wr']} ({_round_pct(data['delta_wr'])} pp)\n\n")
                if "p_value_2prop" in data and data.get("p_value_2prop") is not None:
                    f.write(f"**p-value (2-prop z-test):** {data['p_value_2prop']}\n\n")
                f.write("**Details:**\n\n")
                f.write("```json\n")
                f.write(json.dumps(_make_json_safe(data), indent=2))
                f.write("\n```\n\n")

        # Section 3
        f.write(_section_separator("Section 3 — Tier evaluation (parent BOOST)"))
        s3 = results.get("section_3", {})
        if "ERROR" in s3:
            f.write(f"**ANALYSIS FAILED:** `{s3['ERROR']}`\n\n```\n{s3.get('traceback','')}\n```\n\n")
        else:
            parent = s3.get("parent_boost_evaluation", {})
            f.write(f"**Parent cohort BOOST tier verdict:** `{parent.get('tier', '?')}`\n\n")
            f.write(f"**Train→Test drift (pp):** {parent.get('drift_pp')}\n\n")
            f.write("**Train stats:**\n\n")
            f.write(_fmt_stats(parent.get("train_stats", {})))
            f.write("\n**Test stats:**\n\n")
            f.write(_fmt_stats(parent.get("test_stats", {})))
            f.write("\n**Decision log:**\n\n")
            for line in parent.get("decision_log", []):
                f.write(f"- {line}\n")
            f.write("\n")

        # Section 4 — Headline
        f.write(_section_separator("Section 4 — Headline findings (data only; NO promotion calls)"))
        f.write("Verdicts surfaced by section:\n\n")
        f.write("| Section | Verdict |\n|---------|--------|\n")
        for sec_name, label in [
            ("section_1", "1 - Lifetime baseline + Bear sub-period"),
            ("section_2a_oversold_rebound", "2a - Oversold rebound"),
            ("section_2b_rate_cycle_proxy", "2b - Rate-cycle proxy"),
            ("section_2c_sample_window_bias", "2c - Sample-window bias"),
            ("section_3", "3 - Tier evaluation"),
        ]:
            d = results.get(sec_name, {})
            if "ERROR" in d:
                v = "ANALYSIS_FAILED"
            elif sec_name == "section_1":
                v = f"{d.get('bear_subperiods_total','?')} sub-periods identified"
            elif sec_name == "section_3":
                v = d.get("parent_boost_evaluation", {}).get("tier", "?")
            else:
                v = d.get("verdict", "?")
            f.write(f"| {label} | `{v}` |\n")

        f.write("\n## Open questions for next investigation (deferred to user review)\n\n")
        f.write("- Section 2c sub-period variance verdict drives sample-window-bias decision:\n")
        f.write("  - LOW_VARIANCE_STABLE → cohort genuinely profits across multiple Bear regimes (Tier S/A boost candidate per Section 3)\n")
        f.write("  - MODERATE_VARIANCE → some sub-period instability; lower confidence promotion\n")
        f.write("  - HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT → live n=8 likely Apr 2026-specific artifact; reject\n")
        f.write("  - INSUFFICIENT_SUBPERIODS → not enough independent Bear regimes to validate\n")
        f.write("- Section 3 BOOST tier verdict drives tier promotion candidate level (S/A/B/REJECT)\n")
        f.write("- If Section 2a Oversold CANDIDATE → consider RSI<30 as filter sub-cohort\n")
        f.write("- If Section 2b Rate-cycle CANDIDATE → flag for INV-NN with proper rate calendar (out of scope)\n")
        f.write("- Caveat 2 audit before promotion of any sub-period finding at marginal n\n")

        f.write("\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.\n")
        f.write("User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change\n")
        f.write("or main-branch promotion.\n")


# ── Main orchestrator ─────────────────────────────────────────────────

def _run_section(name: str, fn, *args, **kwargs) -> dict:
    print(f"[INV-002] running {name}…", flush=True)
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-002] {name} FAILED: {e}", flush=True)
        return {"ERROR": str(e), "traceback": tb}


def main():
    print(f"[INV-002] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"[INV-002] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    print(f"[INV-002] loaded {len(signals_df)} backtest signals", flush=True)
    print(f"[INV-002] loading {_REGIME_PATH}…", flush=True)
    regime_df = pd.read_parquet(_REGIME_PATH)
    print(f"[INV-002] loaded {len(regime_df)} regime rows", flush=True)

    cohort_df = filter_inv_002_cohort(signals_df)
    print(f"[INV-002] cohort size: {len(cohort_df)}", flush=True)

    results = {}
    results["section_1"] = _run_section(
        "section_1_lifetime_baseline", section_1_lifetime_baseline, cohort_df, regime_df)
    results["section_2a_oversold_rebound"] = _run_section(
        "section_2a_oversold_rebound", section_2a_oversold_rebound, cohort_df)
    results["section_2b_rate_cycle_proxy"] = _run_section(
        "section_2b_rate_cycle_proxy", section_2b_rate_cycle_proxy, cohort_df)
    results["section_2c_sample_window_bias"] = _run_section(
        "section_2c_sample_window_bias", section_2c_sample_window_bias, cohort_df, regime_df)
    results["section_3"] = _run_section(
        "section_3_tier_evaluation", section_3_tier_evaluation, signals_df)

    print(f"[INV-002] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(results, _OUTPUT_FINDINGS)
    print(f"[INV-002] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    main()
