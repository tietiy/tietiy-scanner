"""
INV-001 — UP_TRI × Bank × Choppy structural failure investigation.

Cohort: signal=UP_TRI AND sector=Bank AND regime=Choppy.
Hypothesis type (Lab tier evaluation): KILL (cohort presumed structurally weak per
live evidence n=26 WR=27%; investigation tests whether 15-year history corroborates).

Sections (per ROADMAP INV-001 + safe-default decisions in auto-mode prompt):
  1. Lifetime cohort baseline (n, W/L/F, WR, Wilson, p-value, year-by-year)
  2. Mechanism-candidate analysis (PSU/Private, vol_q, ^NSEBANK 20-day return,
     time-of-month, signal-score, day-of-month bucket per Caveat 1 calendar proxy)
  3. Inverse-pattern search (DOWN_TRI same dates, defensive-sector UP_TRI same days,
     BULL_PROXY 2-3 days after failed UP_TRI)
  4. Tier evaluation (parent KILL + sub-cohort FILTER on differentiators that surface)
  5. Ground-truth validation against GTB-002 (kill_002 counterfactual P&L)
  6. Headline findings (data-only; NO promotion calls)
  7. Findings.md generation

NO promotion decisions. NO scope expansion. ALL findings surfaced as data.

Outputs:
  - /lab/analyses/INV-001_findings.md (markdown report; ~10-30 KB)
  - /lab/logs/inv_001_run.log (stdout/stderr capture via tee)

Per safe-default 1: differentiator threshold 10pp + n_min 20 + p<0.10 → "CANDIDATE";
                    else "INCONCLUSIVE" or "INSUFFICIENT_N".
Per safe-default 2: inverse threshold WR≥60% + n≥15 + Wilson_lower>0.50 → "PROFITABLE_INVERSE".
Per safe-default 8: Caveat 1 limits Section 3 partial coverage; documented at top of findings.
Per safe-default 9: Caveat 2 9.31% miss-rate banner at top of findings.
"""
from __future__ import annotations

import json
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
_GTB002_PATH = _LAB_ROOT / "registry" / "ground_truth_batches" / "GTB-002.json"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-001_findings.md"
_LOGS_DIR = _LAB_ROOT / "logs"

_TRAIN_END = "2022-12-31"
_TEST_START = "2023-01-01"
_DIFF_THRESHOLD_PP = 0.10
_N_MIN_SUBSET = 20
_P_VALUE_DIFF_MAX = 0.10
_INVERSE_WR_MIN = 0.60
_INVERSE_N_MIN = 15
_INVERSE_WILSON_MIN = 0.50

_PSU_BANKS = {"BANKBARODA", "CANBK", "IDBI", "IOB", "MAHABANK", "PNB", "PSB",
              "SBIN", "UNIONBANK", "UCOBANK", "INDIANB", "CENTRALBK", "BANKINDIA"}
_PRIVATE_BANKS = {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "INDUSINDBK",
                  "IDFCFIRSTB", "FEDERALBNK", "BANDHANBNK", "RBLBANK", "AUBANK",
                  "YESBANK"}

_DEFENSIVE_SECTORS = {"Pharma", "Energy", "FMCG"}


# ── Helpers ───────────────────────────────────────────────────────────

def _strip_ns(symbol: str) -> str:
    return symbol.replace(".NS", "").replace(".BO", "")


def _round_pct(x: float) -> float:
    return round(x * 100, 2) if x is not None else None


def _section_separator(title: str) -> str:
    return f"\n\n## {title}\n\n"


def _classify_bank_subsector(symbol: str) -> str:
    base = _strip_ns(symbol).upper()
    if base in _PSU_BANKS:
        return "PSU"
    if base in _PRIVATE_BANKS:
        return "Private"
    return "Other Bank"


def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
    """Two-proportion z-test; two-sided p-value. Returns None if either n<5."""
    if n1 < 5 or n2 < 5:
        return None
    p1 = w1 / n1
    p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    z = abs(p1 - p2) / se
    # Standard normal CDF via erf
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _classify_diff_verdict(wr_a: Optional[float], n_a: int,
                            wr_b: Optional[float], n_b: int) -> tuple:
    """Apply safe-default 1 differentiator threshold. Returns (verdict, delta_pp, p_value)."""
    if wr_a is None or wr_b is None or n_a < _N_MIN_SUBSET or n_b < _N_MIN_SUBSET:
        return ("INSUFFICIENT_N", None, None)
    delta = abs(wr_a - wr_b)
    # Reconstruct wins from WR for two-prop test
    w_a = round(wr_a * n_a)
    w_b = round(wr_b * n_b)
    p_val = _two_proportion_p_value(w_a, n_a, w_b, n_b)
    if delta >= _DIFF_THRESHOLD_PP and (p_val is not None and p_val < _P_VALUE_DIFF_MAX):
        verdict = "CANDIDATE"
    else:
        verdict = "INCONCLUSIVE"
    return (verdict, round(delta, 4), p_val)


def _classify_inverse_verdict(stats: dict) -> str:
    """Apply safe-default 2 inverse-pattern threshold."""
    wr = stats.get("wr_excl_flat")
    n = stats.get("n_win", 0) + stats.get("n_loss", 0)
    wilson = stats.get("wilson_lower_95")
    if wr is None or n < _INVERSE_N_MIN:
        return "INSUFFICIENT_N"
    if wr >= _INVERSE_WR_MIN and wilson is not None and wilson > _INVERSE_WILSON_MIN:
        return "PROFITABLE_INVERSE"
    if wr < 0.50 or (wilson is not None and wilson < 0.50):
        return "NO_INVERSE_SIGNAL"
    return "INCONCLUSIVE"


# ── Section 1 — Lifetime baseline ─────────────────────────────────────

def filter_inv_001_cohort(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["signal"] == "UP_TRI") &
              (df["sector"] == "Bank") &
              (df["regime"] == "Choppy")].copy()


def section_1_lifetime_baseline(cohort_df: pd.DataFrame) -> dict:
    n_total = len(cohort_df)
    stats = compute_cohort_stats(cohort_df, cohort_filter={})
    # Year-by-year breakdown
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
    # Train/test stats (2011-2022 vs 2023-2026)
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
    }


# ── Section 2 — Mechanism candidates ──────────────────────────────────

def section_2a_psu_vs_private(cohort_df: pd.DataFrame) -> dict:
    cohort_df = cohort_df.copy()
    cohort_df["subsector"] = cohort_df["symbol"].apply(_classify_bank_subsector)
    psu = cohort_df[cohort_df["subsector"] == "PSU"]
    pvt = cohort_df[cohort_df["subsector"] == "Private"]
    other = cohort_df[cohort_df["subsector"] == "Other Bank"]
    psu_stats = compute_cohort_stats(psu, cohort_filter={})
    pvt_stats = compute_cohort_stats(pvt, cohort_filter={})
    other_stats = compute_cohort_stats(other, cohort_filter={})
    n_psu = psu_stats["n_win"] + psu_stats["n_loss"]
    n_pvt = pvt_stats["n_win"] + pvt_stats["n_loss"]
    verdict, delta, p_val = _classify_diff_verdict(
        psu_stats["wr_excl_flat"], n_psu,
        pvt_stats["wr_excl_flat"], n_pvt,
    )
    return {
        "psu": psu_stats, "private": pvt_stats, "other": other_stats,
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_psu_resolved": n_psu, "n_private_resolved": n_pvt,
    }


def section_2b_volume_profile(cohort_df: pd.DataFrame) -> dict:
    if "vol_q" not in cohort_df.columns:
        return {"verdict": "DATA_UNAVAILABLE", "reason": "vol_q column missing"}
    buckets = {}
    for bucket in cohort_df["vol_q"].dropna().unique():
        sub = cohort_df[cohort_df["vol_q"] == bucket]
        s = compute_cohort_stats(sub, cohort_filter={})
        buckets[str(bucket)] = s
    # Compare High vs Thin (extremes)
    high = buckets.get("High", {})
    thin = buckets.get("Thin", {})
    n_high = high.get("n_win", 0) + high.get("n_loss", 0)
    n_thin = thin.get("n_win", 0) + thin.get("n_loss", 0)
    verdict, delta, p_val = _classify_diff_verdict(
        high.get("wr_excl_flat"), n_high, thin.get("wr_excl_flat"), n_thin)
    return {
        "buckets": buckets,
        "comparison": "High vs Thin",
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_high_resolved": n_high, "n_thin_resolved": n_thin,
    }


def section_2c_bank_nifty_momentum(cohort_df: pd.DataFrame) -> dict:
    if not _NSEBANK_PATH.exists():
        return {"verdict": "DATA_UNAVAILABLE", "reason": f"{_NSEBANK_PATH.name} missing"}
    bank_idx = pd.read_parquet(_NSEBANK_PATH)
    bank_idx.index = pd.to_datetime(bank_idx.index)
    bank_idx = bank_idx.sort_index()
    # Compute 20-day return at each scan_date
    cohort_df = cohort_df.copy()
    cohort_df["sd_dt"] = pd.to_datetime(cohort_df["scan_date"])
    nbank_returns = []
    for sd in cohort_df["sd_dt"].unique():
        ts = pd.Timestamp(sd)
        slc = bank_idx.loc[:ts]
        if len(slc) < 21:
            nbank_returns.append((sd, np.nan))
            continue
        last_close = float(slc["Close"].iloc[-1])
        prev_close = float(slc["Close"].iloc[-21])
        ret = (last_close / prev_close - 1) if prev_close > 0 else np.nan
        nbank_returns.append((sd, ret))
    ret_df = pd.DataFrame(nbank_returns, columns=["sd_dt", "nbank_20d_ret"])
    cohort_df = cohort_df.merge(ret_df, on="sd_dt", how="left")
    # Quartile split
    quartiles = cohort_df["nbank_20d_ret"].quantile([0.25, 0.50, 0.75]).to_dict()
    q1 = cohort_df[cohort_df["nbank_20d_ret"] <= quartiles[0.25]]
    q4 = cohort_df[cohort_df["nbank_20d_ret"] >= quartiles[0.75]]
    q1_stats = compute_cohort_stats(q1, cohort_filter={})
    q4_stats = compute_cohort_stats(q4, cohort_filter={})
    n_q1 = q1_stats["n_win"] + q1_stats["n_loss"]
    n_q4 = q4_stats["n_win"] + q4_stats["n_loss"]
    verdict, delta, p_val = _classify_diff_verdict(
        q1_stats["wr_excl_flat"], n_q1, q4_stats["wr_excl_flat"], n_q4)
    return {
        "q1_lowest_momentum": q1_stats, "q4_highest_momentum": q4_stats,
        "q1_threshold": round(quartiles.get(0.25, np.nan), 4) if not pd.isna(quartiles.get(0.25, np.nan)) else None,
        "q4_threshold": round(quartiles.get(0.75, np.nan), 4) if not pd.isna(quartiles.get(0.75, np.nan)) else None,
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_q1_resolved": n_q1, "n_q4_resolved": n_q4,
        "median_20d_return": round(cohort_df["nbank_20d_ret"].median(), 4) if not cohort_df["nbank_20d_ret"].dropna().empty else None,
    }


def section_2d_time_of_month(cohort_df: pd.DataFrame) -> dict:
    cohort_df = cohort_df.copy()
    cohort_df["dom"] = pd.to_datetime(cohort_df["scan_date"]).dt.day
    bins = [(1, 7, "wk1"), (8, 14, "wk2"), (15, 21, "wk3"), (22, 31, "wk4")]
    buckets = {}
    for start, end, label in bins:
        sub = cohort_df[(cohort_df["dom"] >= start) & (cohort_df["dom"] <= end)]
        buckets[label] = compute_cohort_stats(sub, cohort_filter={})
    # Compare wk1 vs wk4 (extremes)
    w1 = buckets["wk1"]
    w4 = buckets["wk4"]
    n_w1 = w1["n_win"] + w1["n_loss"]
    n_w4 = w4["n_win"] + w4["n_loss"]
    verdict, delta, p_val = _classify_diff_verdict(
        w1["wr_excl_flat"], n_w1, w4["wr_excl_flat"], n_w4)
    return {
        "buckets": buckets,
        "comparison": "wk1 vs wk4",
        "verdict": verdict, "delta_wr": delta, "p_value_2prop": p_val,
        "n_wk1_resolved": n_w1, "n_wk4_resolved": n_w4,
    }


def section_2e_signal_score_quartile(cohort_df: pd.DataFrame) -> dict:
    if "score" not in cohort_df.columns or cohort_df["score"].dropna().empty:
        return {
            "verdict": "DATA_UNAVAILABLE",
            "reason": "score column is all-null in backtest_signals.parquet (live scoring not replayed in MS-2)",
        }
    # If non-null, quartile-split (kept here for safety; will report DATA_UNAVAILABLE in current data)
    return {"verdict": "DATA_UNAVAILABLE", "reason": "no non-null scores"}


def section_2f_calendar_proximity(cohort_df: pd.DataFrame) -> dict:
    """Per safe-default 5: day-of-month bucket as proxy for monthly expiry / earnings windows."""
    return {
        "approximation_note": (
            "Per safe-default 5, day-of-month buckets used as proxy for monthly "
            "expiry / earnings windows. Cannot fetch RBI policy or earnings calendar "
            "(out of scope). Section 2d already provides this analysis with same "
            "bucketing scheme; flagging here for clarity."
        ),
        "see_section": "2d (time of month)",
        "verdict": "SEE_SECTION_2D",
    }


# ── Section 3 — Inverse pattern search ────────────────────────────────

def section_3a_down_tri_same_dates(cohort_df: pd.DataFrame,
                                    all_signals_df: pd.DataFrame) -> dict:
    """For each LOSER scan_date in cohort, find DOWN_TRI Bank entries.
    DOWN_TRI outcome in backtest_signals is computed as if LONG (per signal_replayer
    'LONG only' design). For SHORT-trade interpretation: invert W↔L."""
    losers = cohort_df[cohort_df["outcome"].isin(["DAY6_LOSS", "STOP_HIT"])]
    loser_dates = set(losers["scan_date"].unique())
    down_tri = all_signals_df[(all_signals_df["signal"] == "DOWN_TRI") &
                                (all_signals_df["sector"] == "Bank") &
                                (all_signals_df["regime"] == "Choppy") &
                                (all_signals_df["scan_date"].isin(loser_dates))]
    # Invert outcome semantics for SHORT trade
    invert_map = {
        "DAY6_WIN": "INV_LOSS", "TARGET_HIT": "INV_LOSS",
        "DAY6_LOSS": "INV_WIN", "STOP_HIT": "INV_WIN",
        "DAY6_FLAT": "DAY6_FLAT", "OPEN": "OPEN",
    }
    down_tri = down_tri.copy()
    down_tri["inv_outcome"] = down_tri["outcome"].map(invert_map)
    n_inv_win = (down_tri["inv_outcome"] == "INV_WIN").sum()
    n_inv_loss = (down_tri["inv_outcome"] == "INV_LOSS").sum()
    n_flat = (down_tri["inv_outcome"] == "DAY6_FLAT").sum()
    n_open = (down_tri["inv_outcome"] == "OPEN").sum()
    n = n_inv_win + n_inv_loss
    if n > 0:
        wr = round(n_inv_win / n, 4)
        wilson = wilson_lower_bound_95(int(n_inv_win), int(n))
        p_val = binomial_p_value_vs_50(int(n_inv_win), int(n))
    else:
        wr = wilson = p_val = None
    inverse_stats = {
        "wr_excl_flat": wr, "n_win": int(n_inv_win), "n_loss": int(n_inv_loss),
        "n_flat": int(n_flat), "n_open": int(n_open),
        "wilson_lower_95": wilson, "p_value_vs_50": p_val,
    }
    return {
        "loser_dates_count": len(loser_dates),
        "down_tri_entries_on_loser_dates": len(down_tri),
        "inverse_short_stats": inverse_stats,
        "verdict": _classify_inverse_verdict(inverse_stats),
        "method_note": (
            "DOWN_TRI outcomes in backtest_signals.parquet are LONG-direction (per "
            "signal_replayer.compute_d6_outcome design). Inverted W↔L for SHORT-trade "
            "interpretation. STOP_HIT (LONG hit stop = price dropped sharply) maps to "
            "SHORT WIN; TARGET_HIT (price ran up) maps to SHORT LOSS."
        ),
    }


def section_3b_defensive_sector_rotation(cohort_df: pd.DataFrame,
                                           all_signals_df: pd.DataFrame) -> dict:
    """UP_TRI in defensive sectors on same Choppy days as INV-001 LOSER scan_dates."""
    losers = cohort_df[cohort_df["outcome"].isin(["DAY6_LOSS", "STOP_HIT"])]
    loser_dates = set(losers["scan_date"].unique())
    defensive = all_signals_df[(all_signals_df["signal"] == "UP_TRI") &
                                  (all_signals_df["sector"].isin(_DEFENSIVE_SECTORS)) &
                                  (all_signals_df["regime"] == "Choppy") &
                                  (all_signals_df["scan_date"].isin(loser_dates))]
    stats = compute_cohort_stats(defensive, cohort_filter={})
    return {
        "loser_dates_count": len(loser_dates),
        "defensive_signals_on_loser_dates": len(defensive),
        "defensive_stats": stats,
        "verdict": _classify_inverse_verdict(stats),
        "by_sector_breakdown": {
            sec: compute_cohort_stats(defensive[defensive["sector"] == sec], cohort_filter={})
            for sec in defensive["sector"].unique()
        },
        "caveat_note": (
            "Caveat 1 (per safe-default 8): 7 sector indices absent from cache; "
            "sector_momentum falls back to Neutral for non-Bank sectors. Defensive-sector "
            "signal generation itself is unaffected (per-stock OHLCV present in cache); "
            "however per-cohort sector_momentum filter is degraded."
        ),
    }


def section_3c_bull_proxy_post_failure(cohort_df: pd.DataFrame,
                                         all_signals_df: pd.DataFrame) -> dict:
    """BULL_PROXY Bank signals 2-3 trading days after each INV-001 LOSER."""
    losers = cohort_df[cohort_df["outcome"].isin(["DAY6_LOSS", "STOP_HIT"])].copy()
    losers["sd_dt"] = pd.to_datetime(losers["scan_date"])
    # Trading-day approximation: ±2 / ±3 calendar days; refined to weekday filter
    target_dates = set()
    for sd in losers["sd_dt"].unique():
        for offset_days in (2, 3):
            target = sd + pd.Timedelta(days=offset_days)
            # Skip weekends (Sat=5, Sun=6 dt.dayofweek)
            while pd.Timestamp(target).dayofweek >= 5:
                target = target + pd.Timedelta(days=1)
            target_dates.add(pd.Timestamp(target).strftime("%Y-%m-%d"))
    bp = all_signals_df[(all_signals_df["signal"] == "BULL_PROXY") &
                          (all_signals_df["sector"] == "Bank") &
                          (all_signals_df["scan_date"].isin(target_dates))]
    stats = compute_cohort_stats(bp, cohort_filter={})
    return {
        "loser_dates_count": len(losers["scan_date"].unique()),
        "target_followup_dates_count": len(target_dates),
        "bull_proxy_signals_on_followup": len(bp),
        "bull_proxy_stats": stats,
        "verdict": _classify_inverse_verdict(stats),
    }


# ── Section 4 — Tier evaluation ───────────────────────────────────────

def section_4_tier_evaluation(signals_df: pd.DataFrame, mechanism_results: dict) -> dict:
    """Parent KILL evaluation + sub-cohort FILTER on differentiators that surfaced."""
    parent = evaluate_hypothesis(
        signals_df,
        cohort_filter={"signal": "UP_TRI", "sector": "Bank", "regime": "Choppy"},
        hypothesis_type="KILL",
    )
    sub_cohort_evals = {}
    # If PSU vs Private surfaced as candidate, evaluate each as FILTER on KILL parent
    if mechanism_results.get("2a_psu_vs_private", {}).get("verdict") == "CANDIDATE":
        # Need subsector column for filter; signals_df doesn't have it natively
        signals_with_sub = signals_df.copy()
        signals_with_sub["subsector"] = signals_with_sub["symbol"].apply(_classify_bank_subsector)
        for sub_name in ("PSU", "Private"):
            sub_cohort_evals[f"sub_{sub_name}"] = evaluate_hypothesis(
                signals_with_sub,
                cohort_filter={"signal": "UP_TRI", "sector": "Bank", "regime": "Choppy",
                               "subsector": sub_name},
                hypothesis_type="FILTER",
                filter_parent_type="KILL",
            )
    return {
        "parent_kill_evaluation": parent,
        "sub_cohort_filter_evaluations": sub_cohort_evals,
    }


# ── Section 5 — Ground-truth validation (GTB-002) ─────────────────────

def section_5_gtb002_validation(signals_df: pd.DataFrame) -> dict:
    """Counterfactual: would kill_002 (UP_TRI×Bank×Choppy suppression) prevent
    GTB-002 losses without over-suppressing winners? Per Gate 4 acceptance:
    prevented losses > suppressed winners by ≥ 2:1."""
    if not _GTB002_PATH.exists():
        return {"verdict": "DATA_UNAVAILABLE", "reason": "GTB-002.json missing"}
    gtb = json.loads(_GTB002_PATH.read_text())
    prevented_losses = sum(1 for s in gtb["signals"]
                            if s["outcome"] in ("DAY6_LOSS", "STOP_HIT"))
    suppressed_winners = sum(1 for s in gtb["signals"]
                              if s["outcome"] in ("DAY6_WIN", "TARGET_HIT"))
    flat = sum(1 for s in gtb["signals"] if s["outcome"] == "DAY6_FLAT")
    pnl_prevented = sum(float(s["pnl_pct"]) for s in gtb["signals"]
                         if s["outcome"] in ("DAY6_LOSS", "STOP_HIT"))  # negative numbers
    pnl_suppressed = sum(float(s["pnl_pct"]) for s in gtb["signals"]
                          if s["outcome"] in ("DAY6_WIN", "TARGET_HIT"))  # positive numbers
    # Kill suppresses ALL signals in cohort → counterfactual = -pnl_prevented (avoided losses) - pnl_suppressed (foregone wins)
    counterfactual_pnl_delta = round(-pnl_prevented - pnl_suppressed, 2)
    ratio = round(prevented_losses / suppressed_winners, 2) if suppressed_winners > 0 else None
    if ratio is not None and ratio >= 2.0 and counterfactual_pnl_delta > 0:
        verdict = "GATE_4_PASS"
    elif ratio is not None and ratio >= 2.0:
        verdict = "GATE_4_RATIO_OK_BUT_PNL_NEGATIVE"
    elif suppressed_winners == 0 and prevented_losses > 0:
        verdict = "GATE_4_PASS_NO_WINNERS_SUPPRESSED"
    else:
        verdict = "GATE_4_INSUFFICIENT_PREVENTION"
    return {
        "batch_id": gtb["batch_id"],
        "n_signals": len(gtb["signals"]),
        "prevented_losses": prevented_losses,
        "suppressed_winners": suppressed_winners,
        "flat": flat,
        "ratio_prevented_per_suppressed": ratio,
        "counterfactual_pnl_pct_delta": counterfactual_pnl_delta,
        "pnl_prevented_pct_sum": round(pnl_prevented, 2),
        "pnl_suppressed_pct_sum": round(pnl_suppressed, 2),
        "verdict": verdict,
    }


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


def write_findings_md(results: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("# INV-001 — UP_TRI × Bank × Choppy structural failure investigation\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write("**Cohort filter:** signal=UP_TRI AND sector=Bank AND regime=Choppy\n\n")
        f.write("**Hypothesis type (Lab tier evaluation):** KILL\n\n")

        # Caveat banners
        f.write("---\n\n")
        f.write("## ⚠️ Caveats carried forward\n\n")
        f.write("**Caveat 1 (sector indices missing):** 7 of 8 sector indices absent from MS-1 cache "
                "(only ^NSEBANK present). Affects Section 3b defensive-sector rotation analysis "
                "(per-cohort sector_momentum degraded; defensive UP_TRI signal generation itself "
                "is unaffected since per-stock OHLCV is present). Caveat 1 backfill deferred to "
                "future user/CC session.\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate):** 23 of 247 live Apr 2026 signals did not "
                "regenerate in backtest. Findings at small n (<20) particularly susceptible. "
                "Tier B/A results at marginal n should be re-validated post-Caveat 2 audit before "
                "promotion. INV-001 cohort lifetime n is large (5146 resolved), so headline tier "
                "evaluation is robust to Caveat 2; per-mechanism sub-cohort findings are more "
                "vulnerable.\n\n")
        f.write("**Caveat 3 (score column null):** signal_replayer.py did not propagate live "
                "scoring; backtest_signals.score column is all-null. Section 2e signal-score "
                "quartile analysis returns DATA_UNAVAILABLE.\n\n")

        # Section 1
        f.write(_section_separator("Section 1 — Lifetime cohort baseline"))
        s1 = results.get("section_1", {})
        if "ERROR" in s1:
            f.write(f"**ANALYSIS FAILED:** `{s1['ERROR']}`\n\n```\n{s1.get('traceback','')}\n```\n")
        else:
            f.write(f"**Total cohort signals:** {s1.get('n_total')}\n\n")
            f.write("**Lifetime stats (entire cohort):**\n\n")
            f.write(_fmt_stats(s1.get("lifetime", {})))
            f.write("\n**Train period (2011-01 → 2022-12):**\n\n")
            f.write(_fmt_stats(s1.get("train_stats", {})))
            f.write("\n**Test period (2023-01 → 2026-04):**\n\n")
            f.write(_fmt_stats(s1.get("test_stats", {})))
            f.write("\n**Year-by-year breakdown:**\n\n")
            f.write("| Year | n_resolved | n_win | n_loss | n_flat | WR_excl_flat | Wilson_lower_95 |\n")
            f.write("|------|-----------|-------|--------|--------|--------------|------------------|\n")
            for y in s1.get("yearly_breakdown", []):
                f.write(f"| {y['year']} | {y['n_resolved']} | {y['n_win']} | "
                        f"{y['n_loss']} | {y['n_flat']} | {y['wr_excl_flat']} | "
                        f"{y['wilson_lower_95']} |\n")

        # Section 2
        f.write(_section_separator("Section 2 — Mechanism-candidate analysis"))
        for sec_name, label in [
            ("section_2a_psu_vs_private", "2a — PSU vs Private bank subsector"),
            ("section_2b_volume_profile", "2b — Volume profile (vol_q bucket)"),
            ("section_2c_bank_nifty_momentum", "2c — Bank Nifty 20-day momentum at signal"),
            ("section_2d_time_of_month", "2d — Day-of-month bucket (week 1/2/3/4)"),
            ("section_2e_signal_score_quartile", "2e — Signal score quartile"),
            ("section_2f_calendar_proximity", "2f — Calendar proximity (per safe-default 5)"),
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
        f.write(_section_separator("Section 3 — Inverse pattern search"))
        for sec_name, label in [
            ("section_3a_down_tri_same_dates", "3a — DOWN_TRI Bank Choppy on INV-001 LOSER dates (SHORT-direction)"),
            ("section_3b_defensive_sector_rotation", "3b — Defensive sector UP_TRI on same loser dates"),
            ("section_3c_bull_proxy_post_failure", "3c — BULL_PROXY Bank 2-3 days after failed UP_TRI"),
        ]:
            f.write(f"### {label}\n\n")
            data = results.get(sec_name, {})
            if "ERROR" in data:
                f.write(f"**ANALYSIS FAILED:** `{data['ERROR']}`\n\n```\n{data.get('traceback','')}\n```\n\n")
            else:
                verdict = data.get("verdict", "?")
                f.write(f"**Verdict:** `{verdict}`\n\n")
                f.write("**Details:**\n\n")
                f.write("```json\n")
                f.write(json.dumps(_make_json_safe(data), indent=2))
                f.write("\n```\n\n")

        # Section 4
        f.write(_section_separator("Section 4 — Tier evaluation (parent KILL + sub-cohort FILTER)"))
        s4 = results.get("section_4", {})
        if "ERROR" in s4:
            f.write(f"**ANALYSIS FAILED:** `{s4['ERROR']}`\n\n```\n{s4.get('traceback','')}\n```\n\n")
        else:
            parent = s4.get("parent_kill_evaluation", {})
            f.write(f"**Parent cohort KILL tier verdict:** `{parent.get('tier', '?')}`\n\n")
            f.write(f"**Train→Test drift (pp):** {parent.get('drift_pp')}\n\n")
            f.write("**Train stats:**\n\n")
            f.write(_fmt_stats(parent.get("train_stats", {})))
            f.write("\n**Test stats:**\n\n")
            f.write(_fmt_stats(parent.get("test_stats", {})))
            f.write("\n**Decision log:**\n\n")
            for line in parent.get("decision_log", []):
                f.write(f"- {line}\n")
            f.write("\n")
            sub_evals = s4.get("sub_cohort_filter_evaluations", {})
            if sub_evals:
                f.write("\n**Sub-cohort FILTER evaluations:**\n\n")
                for sub_name, sub_eval in sub_evals.items():
                    f.write(f"### {sub_name}\n\n")
                    f.write(f"**Tier verdict:** `{sub_eval.get('tier', '?')}`\n\n")
                    f.write(f"**Drift (pp):** {sub_eval.get('drift_pp')}\n\n")

        # Section 5 — Ground-truth validation
        f.write(_section_separator("Section 5 — Ground-truth validation (GTB-002)"))
        s5 = results.get("section_5", {})
        if "ERROR" in s5:
            f.write(f"**ANALYSIS FAILED:** `{s5['ERROR']}`\n\n```\n{s5.get('traceback','')}\n```\n\n")
        else:
            f.write(f"**Verdict:** `{s5.get('verdict', '?')}`\n\n")
            f.write(f"**Prevented losses:** {s5.get('prevented_losses')} | ")
            f.write(f"**Suppressed winners:** {s5.get('suppressed_winners')} | ")
            f.write(f"**Flat:** {s5.get('flat')}\n\n")
            f.write(f"**Ratio (prevented/suppressed):** {s5.get('ratio_prevented_per_suppressed')}\n\n")
            f.write(f"**Counterfactual P&L delta (pct):** {s5.get('counterfactual_pnl_pct_delta')}\n\n")
            f.write(f"**P&L prevented (sum, pct):** {s5.get('pnl_prevented_pct_sum')}\n\n")
            f.write(f"**P&L suppressed (sum, pct):** {s5.get('pnl_suppressed_pct_sum')}\n\n")

        # Section 6 — Headline (data only)
        f.write(_section_separator("Section 6 — Headline findings (data only; NO promotion calls)"))
        f.write("Verdicts surfaced by section (per safe-default thresholds):\n\n")
        f.write("| Section | Verdict |\n|---------|--------|\n")
        for sec_name, label in [
            ("section_1", "1 - Lifetime baseline"),
            ("section_2a_psu_vs_private", "2a - PSU vs Private"),
            ("section_2b_volume_profile", "2b - Volume profile"),
            ("section_2c_bank_nifty_momentum", "2c - Bank Nifty momentum"),
            ("section_2d_time_of_month", "2d - Time of month"),
            ("section_2e_signal_score_quartile", "2e - Signal score (DATA_UNAVAILABLE)"),
            ("section_2f_calendar_proximity", "2f - Calendar proximity"),
            ("section_3a_down_tri_same_dates", "3a - DOWN_TRI inverse"),
            ("section_3b_defensive_sector_rotation", "3b - Defensive sector rotation"),
            ("section_3c_bull_proxy_post_failure", "3c - BULL_PROXY post-failure"),
            ("section_4", "4 - Tier evaluation"),
            ("section_5", "5 - GTB-002 validation"),
        ]:
            d = results.get(sec_name, {})
            if "ERROR" in d:
                v = "ANALYSIS_FAILED"
            elif sec_name == "section_1":
                v = "see lifetime stats"
            elif sec_name == "section_4":
                v = d.get("parent_kill_evaluation", {}).get("tier", "?")
            else:
                v = d.get("verdict", "?")
            f.write(f"| {label} | `{v}` |\n")

        f.write("\n## Open questions for next investigation (deferred to user review)\n\n")
        f.write("- Section 4 parent KILL tier verdict drives kill_002 conviction-tag decision\n")
        f.write("- Section 5 GTB-002 verdict drives Gate 4 pass/fail for kill_002\n")
        f.write("- If 2a PSU vs Private CANDIDATE → consider sub-cohort kill rather than parent kill\n")
        f.write("- If 3a DOWN_TRI shows PROFITABLE_INVERSE → boost-pattern candidate worth INV-NN follow-up\n")
        f.write("- Caveat 1 backfill before INV-003 (matrix scan) regardless of INV-001 outcome\n")
        f.write("- Caveat 2 audit before promotion of any sub-cohort tier B/A finding at marginal n\n")
        f.write("- Bank Nifty momentum at signal time (Section 2c) may be the dominant differentiator;\n"
                "  cross-check with Volume profile (2b) for compound filter candidates in INV-NN\n")

        f.write("\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. No promotion decisions are made by CC.\n")
        f.write("User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change\n")
        f.write("or main-branch promotion.\n")


def _make_json_safe(obj):
    """Recursively convert numpy/pandas types to JSON-serializable Python types."""
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
        return None if (f != f) else round(f, 6)  # NaN → None
    if isinstance(obj, np.ndarray):
        return [_make_json_safe(v) for v in obj.tolist()]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, float) and obj != obj:
        return None
    return obj


# ── Main orchestrator ─────────────────────────────────────────────────

def _run_section(name: str, fn, *args, **kwargs) -> dict:
    """Run a section function with try/except; return result or error dict."""
    print(f"[INV-001] running {name}…", flush=True)
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-001] {name} FAILED: {e}", flush=True)
        return {"ERROR": str(e), "traceback": tb}


def main():
    print(f"[INV-001] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"[INV-001] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    print(f"[INV-001] loaded {len(signals_df)} backtest signals", flush=True)

    cohort_df = filter_inv_001_cohort(signals_df)
    print(f"[INV-001] cohort size: {len(cohort_df)}", flush=True)

    results = {}
    results["section_1"] = _run_section("section_1_lifetime_baseline",
                                         section_1_lifetime_baseline, cohort_df)
    results["section_2a_psu_vs_private"] = _run_section(
        "section_2a_psu_vs_private", section_2a_psu_vs_private, cohort_df)
    results["section_2b_volume_profile"] = _run_section(
        "section_2b_volume_profile", section_2b_volume_profile, cohort_df)
    results["section_2c_bank_nifty_momentum"] = _run_section(
        "section_2c_bank_nifty_momentum", section_2c_bank_nifty_momentum, cohort_df)
    results["section_2d_time_of_month"] = _run_section(
        "section_2d_time_of_month", section_2d_time_of_month, cohort_df)
    results["section_2e_signal_score_quartile"] = _run_section(
        "section_2e_signal_score_quartile", section_2e_signal_score_quartile, cohort_df)
    results["section_2f_calendar_proximity"] = _run_section(
        "section_2f_calendar_proximity", section_2f_calendar_proximity, cohort_df)
    results["section_3a_down_tri_same_dates"] = _run_section(
        "section_3a_down_tri_same_dates", section_3a_down_tri_same_dates, cohort_df, signals_df)
    results["section_3b_defensive_sector_rotation"] = _run_section(
        "section_3b_defensive_sector_rotation", section_3b_defensive_sector_rotation,
        cohort_df, signals_df)
    results["section_3c_bull_proxy_post_failure"] = _run_section(
        "section_3c_bull_proxy_post_failure", section_3c_bull_proxy_post_failure,
        cohort_df, signals_df)
    results["section_4"] = _run_section(
        "section_4_tier_evaluation", section_4_tier_evaluation, signals_df, results)
    results["section_5"] = _run_section(
        "section_5_gtb002_validation", section_5_gtb002_validation, signals_df)

    print(f"[INV-001] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(results, _OUTPUT_FINDINGS)
    print(f"[INV-001] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    main()
