"""
INV-006 — Exit timing optimization across UP_TRI / DOWN_TRI / BULL_PROXY signals.

Per pre-registered hypothesis in patterns.json: D6 exit (current default per
scanner.config TARGET_R_MULTIPLE=2.0 + 6-day hold) may be suboptimal. Investigation
tests 12 alternative exit variants across 3 signal types and surfaces which (if any)
beat D6 baseline at Lab tier eligibility.

Exit variants (12 total):
  Fixed-day (7): D2, D3, D4, D5, D7, D8, D10  (D6 is the baseline reference)
  Trailing-stop (3): 1.5×ATR-14, 2×ATR-14, 2.5×ATR-14
  Profit ladder (2):
    A — 50% at entry+2R, 50% at D6 open (initial stop = entry - 1×ATR)
    B — 33% at entry+1.5R, 33% at entry+2.5R, 34% trailing-2×ATR (initial stop = entry - 1×ATR)

Where R = 1 × ATR_14 at signal date (per safe-default 4 unit definition).

Outputs:
  - /lab/analyses/INV-006_findings.md (~30-50 KB)
  - /lab/logs/inv_006_run.log

Implementation notes:
  - Entry price reference = signal's entry_price (next-day open, per signal_replayer
    convention) — matches existing D6 baseline semantics so direct comparison valid
  - W/L/F threshold ±0.5% from entry (matches signal_replayer FLAT semantics)
  - Stop/target intraday checks: stop hit if any day's LOW ≤ stop_price; target hit
    if any day's HIGH ≥ target_price; exit at stop_price/target_price intraday
  - Trailing-stop update: each day, stop = max(prior_stop, today_close - mult×today_ATR_14)
  - Pre-load all stock parquets into dict[symbol, df_with_atr] once for performance
  - For ladder variants: weighted-average pnl across slices; W/L/F at ±0.5% on weighted avg

NO promotion calls. NO patterns.json changes. Findings.md is data-only.
"""
from __future__ import annotations

import json
import sys
import time
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
_CACHE_DIR = _LAB_ROOT / "cache"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-006_findings.md"

_ATR_PERIOD = 14
_FLAT_THRESHOLD_PCT = 0.5  # ±0.5% per signal_replayer convention
_LOOKAHEAD_DAYS = 11  # D0=entry + D1..D10

_FIXED_DAY_EXITS = [2, 3, 4, 5, 6, 7, 8, 10]  # D6 included as baseline ref
_TRAILING_MULTIPLIERS = [1.5, 2.0, 2.5]
_LADDER_VARIANTS = ["LADDER_A_50at2R_50atD6", "LADDER_B_33_33_34trailing"]

_BASELINE_EXIT = "D6"

_SIGNALS_TO_EVALUATE = ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]

_DIFF_THRESHOLD_PP = 0.03  # 3pp improvement to qualify "CANDIDATE"
_P_VALUE_DIFF_MAX = 0.05
_N_MIN_FOR_COMPARISON = 100


# ── Helpers ───────────────────────────────────────────────────────────

def _classify_outcome(pnl_pct: float) -> str:
    """W/L/F classification at ±0.5%."""
    if pnl_pct > _FLAT_THRESHOLD_PCT:
        return "WIN"
    if pnl_pct < -_FLAT_THRESHOLD_PCT:
        return "LOSS"
    return "FLAT"


def _compute_atr14(df: pd.DataFrame) -> pd.Series:
    """ATR-14 via simple rolling mean of true range (Wilder smoothing approximation)."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(_ATR_PERIOD, min_periods=_ATR_PERIOD).mean()


def _two_proportion_p_value(w1: int, n1: int, w2: int, n2: int) -> Optional[float]:
    if n1 < 5 or n2 < 5:
        return None
    p1 = w1 / n1
    p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    se = (p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 1.0
    import math
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _classify_variant_vs_baseline(variant_wr: Optional[float], variant_n: int,
                                    baseline_wr: Optional[float], baseline_n: int) -> tuple:
    """Apply safe-default 1 candidate-vs-baseline rule. Returns (verdict, delta_pp, p_value)."""
    if (variant_wr is None or baseline_wr is None
            or variant_n < _N_MIN_FOR_COMPARISON
            or baseline_n < _N_MIN_FOR_COMPARISON):
        return ("INSUFFICIENT_N", None, None)
    delta = variant_wr - baseline_wr  # signed
    w_v = round(variant_wr * variant_n)
    w_b = round(baseline_wr * baseline_n)
    p_val = _two_proportion_p_value(w_v, variant_n, w_b, baseline_n)
    if delta >= _DIFF_THRESHOLD_PP and p_val is not None and p_val < _P_VALUE_DIFF_MAX:
        verdict = "BEATS_BASELINE"
    elif delta <= -_DIFF_THRESHOLD_PP and p_val is not None and p_val < _P_VALUE_DIFF_MAX:
        verdict = "WORSE_THAN_BASELINE"
    else:
        verdict = "MARGINAL_OR_EQUIVALENT"
    return (verdict, round(delta, 4), p_val)


# ── Cache pre-load ────────────────────────────────────────────────────

def preload_cache() -> dict:
    """Load all stock parquets with ATR-14 column added. Skip _index_* files."""
    cache = {}
    print(f"[INV-006] preloading parquets from {_CACHE_DIR}…", flush=True)
    n_loaded = 0
    n_skipped = 0
    for p in sorted(_CACHE_DIR.glob("*.parquet")):
        if p.name.startswith("_index_"):
            n_skipped += 1
            continue
        try:
            df = pd.read_parquet(p)
            df = df.sort_index()
            if not all(col in df.columns for col in ["Open", "High", "Low", "Close"]):
                n_skipped += 1
                continue
            df["ATR_14"] = _compute_atr14(df)
            # Symbol convention: filename FOO_NS.parquet → symbol FOO.NS
            symbol = p.stem.replace("_NS", ".NS")
            cache[symbol] = df
            n_loaded += 1
        except Exception as e:
            print(f"  skip {p.name}: {e}", flush=True)
            n_skipped += 1
    print(f"[INV-006] cache loaded: {n_loaded} stocks, {n_skipped} skipped", flush=True)
    return cache


# ── Per-signal exit-variant evaluation ────────────────────────────────

def evaluate_signal_all_variants(signal_row: pd.Series, cache: dict) -> dict:
    """Compute outcomes for one signal across all 12 exit variants.
    Returns dict {variant_id: {"pnl_pct": float, "outcome": "WIN"|"LOSS"|"FLAT"|"OPEN", "exit_day": int}}.
    """
    symbol = signal_row["symbol"]
    entry_date = signal_row.get("entry_date")
    entry_price_ref = signal_row.get("entry_price")
    if symbol not in cache or entry_date is None or pd.isna(entry_date):
        return {}
    df = cache[symbol]
    try:
        entry_ts = pd.Timestamp(entry_date)
        if entry_ts not in df.index:
            return {}
        entry_idx = df.index.get_loc(entry_ts)
    except (KeyError, TypeError):
        return {}

    # Need at least 10 trading days post-entry (idx 0..10)
    if entry_idx + _LOOKAHEAD_DAYS > len(df):
        return {}

    window = df.iloc[entry_idx : entry_idx + _LOOKAHEAD_DAYS]
    entry_price = float(window["Open"].iloc[0])
    if entry_price <= 0:
        return {}

    # ATR at entry (use ATR from day before entry to avoid look-ahead within entry day)
    atr_at_entry = float(df["ATR_14"].iloc[max(entry_idx - 1, 0)])
    if pd.isna(atr_at_entry) or atr_at_entry <= 0:
        # ATR unavailable — skip ATR-based variants but compute fixed-day
        atr_valid = False
    else:
        atr_valid = True

    results = {}

    # ── Fixed-day exits ──
    for n_day in _FIXED_DAY_EXITS:
        if n_day >= len(window):
            results[f"D{n_day}"] = {"pnl_pct": None, "outcome": "OPEN", "exit_day": None}
            continue
        exit_price = float(window["Open"].iloc[n_day])
        pnl_pct = (exit_price / entry_price - 1) * 100
        results[f"D{n_day}"] = {
            "pnl_pct": round(pnl_pct, 4),
            "outcome": _classify_outcome(pnl_pct),
            "exit_day": n_day,
        }

    # ── Trailing-stop variants ──
    for mult in _TRAILING_MULTIPLIERS:
        var_id = f"TRAIL_{mult}xATR"
        if not atr_valid:
            results[var_id] = {"pnl_pct": None, "outcome": "ATR_UNAVAILABLE", "exit_day": None}
            continue
        stop = entry_price - mult * atr_at_entry
        exit_price = None
        exit_day = None
        for i in range(1, len(window)):
            atr_today = float(window["ATR_14"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            day_close = float(window["Close"].iloc[i])
            if day_low <= stop:
                exit_price = stop
                exit_day = i
                break
            if not pd.isna(atr_today) and atr_today > 0:
                stop = max(stop, day_close - mult * atr_today)
        if exit_price is None:
            # Never hit — exit at D10 close
            exit_price = float(window["Close"].iloc[-1])
            exit_day = _LOOKAHEAD_DAYS - 1
        pnl_pct = (exit_price / entry_price - 1) * 100
        results[var_id] = {
            "pnl_pct": round(pnl_pct, 4),
            "outcome": _classify_outcome(pnl_pct),
            "exit_day": exit_day,
        }

    # ── Ladder variants ──
    if atr_valid:
        R = atr_at_entry  # 1 ATR unit per safe-default 4
        initial_stop = entry_price - R
        # Variant A: 50% at entry+2R, 50% at D6 open
        target_a = entry_price + 2 * R
        slice1_pnl = None
        for i in range(1, len(window)):
            day_high = float(window["High"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            if day_low <= initial_stop:
                slice1_pnl = (initial_stop / entry_price - 1) * 100
                break
            if day_high >= target_a:
                slice1_pnl = (target_a / entry_price - 1) * 100
                break
        if slice1_pnl is None:
            # Never hit either; close at D6 open
            d6_price = float(window["Open"].iloc[6]) if len(window) > 6 else float(window["Close"].iloc[-1])
            slice1_pnl = (d6_price / entry_price - 1) * 100
        slice2_pnl = None
        for i in range(1, len(window)):
            day_low = float(window["Low"].iloc[i])
            if day_low <= initial_stop:
                slice2_pnl = (initial_stop / entry_price - 1) * 100
                break
        if slice2_pnl is None:
            d6_price = float(window["Open"].iloc[6]) if len(window) > 6 else float(window["Close"].iloc[-1])
            slice2_pnl = (d6_price / entry_price - 1) * 100
        ladder_a_pnl = 0.5 * slice1_pnl + 0.5 * slice2_pnl
        results["LADDER_A_50at2R_50atD6"] = {
            "pnl_pct": round(ladder_a_pnl, 4),
            "outcome": _classify_outcome(ladder_a_pnl),
            "exit_day": 6,
        }

        # Variant B: 33% at 1.5R, 33% at 2.5R, 34% trailing 2x ATR
        target_b1 = entry_price + 1.5 * R
        target_b2 = entry_price + 2.5 * R
        sb1 = None; sb2 = None
        for i in range(1, len(window)):
            day_high = float(window["High"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            if day_low <= initial_stop and (sb1 is None or sb2 is None):
                # Stop on remaining slices
                if sb1 is None:
                    sb1 = (initial_stop / entry_price - 1) * 100
                if sb2 is None:
                    sb2 = (initial_stop / entry_price - 1) * 100
                break
            if sb1 is None and day_high >= target_b1:
                sb1 = (target_b1 / entry_price - 1) * 100
            if sb2 is None and day_high >= target_b2:
                sb2 = (target_b2 / entry_price - 1) * 100
            if sb1 is not None and sb2 is not None:
                break
        if sb1 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb1 = (d10_close / entry_price - 1) * 100
        if sb2 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb2 = (d10_close / entry_price - 1) * 100
        # Slice 3: trailing 2x ATR (independent simulation)
        stop3 = entry_price - 2 * atr_at_entry
        sb3 = None
        for i in range(1, len(window)):
            atr_today = float(window["ATR_14"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            day_close = float(window["Close"].iloc[i])
            if day_low <= stop3:
                sb3 = (stop3 / entry_price - 1) * 100
                break
            if not pd.isna(atr_today) and atr_today > 0:
                stop3 = max(stop3, day_close - 2 * atr_today)
        if sb3 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb3 = (d10_close / entry_price - 1) * 100
        ladder_b_pnl = 0.33 * sb1 + 0.33 * sb2 + 0.34 * sb3
        results["LADDER_B_33_33_34trailing"] = {
            "pnl_pct": round(ladder_b_pnl, 4),
            "outcome": _classify_outcome(ladder_b_pnl),
            "exit_day": 10,
        }
    else:
        results["LADDER_A_50at2R_50atD6"] = {"pnl_pct": None, "outcome": "ATR_UNAVAILABLE",
                                              "exit_day": None}
        results["LADDER_B_33_33_34trailing"] = {"pnl_pct": None, "outcome": "ATR_UNAVAILABLE",
                                                  "exit_day": None}

    return results


# ── Main matrix scan ──────────────────────────────────────────────────

def run_matrix(signals_df: pd.DataFrame, cache: dict) -> dict:
    """For each (signal_type, variant) pair, accumulate outcomes and compute stats.
    Returns dict {signal_type: {variant_id: {"outcomes": [...], "stats": {...}}}}.
    """
    # Limit to evaluable signals (have entry_date and entry_price)
    evaluable = signals_df[
        signals_df["entry_date"].notna() & signals_df["entry_price"].notna()
        & signals_df["signal"].isin(_SIGNALS_TO_EVALUATE)
    ].copy()
    print(f"[INV-006] evaluable signals: {len(evaluable)}", flush=True)

    # Per (signal_type, variant) accumulators: list of {scan_date, symbol, outcome, pnl_pct, exit_day}
    bucket_rows = {sig: {} for sig in _SIGNALS_TO_EVALUATE}

    n_evaluated = 0
    n_skipped = 0
    t0 = time.time()
    for idx, signal_row in evaluable.iterrows():
        outcomes = evaluate_signal_all_variants(signal_row, cache)
        if not outcomes:
            n_skipped += 1
            continue
        sig_type = signal_row["signal"]
        for variant_id, oc in outcomes.items():
            if variant_id not in bucket_rows[sig_type]:
                bucket_rows[sig_type][variant_id] = []
            bucket_rows[sig_type][variant_id].append({
                "scan_date": signal_row["scan_date"],
                "symbol": signal_row["symbol"],
                "sector": signal_row.get("sector"),
                "regime": signal_row.get("regime"),
                "outcome": oc["outcome"],
                "pnl_pct": oc["pnl_pct"],
                "exit_day": oc["exit_day"],
            })
        n_evaluated += 1
        if n_evaluated % 10000 == 0:
            elapsed = time.time() - t0
            print(f"[INV-006] evaluated {n_evaluated}/{len(evaluable)} "
                  f"({elapsed:.1f}s elapsed; {n_skipped} skipped)", flush=True)

    elapsed = time.time() - t0
    print(f"[INV-006] matrix scan done: {n_evaluated} evaluated, "
          f"{n_skipped} skipped, {elapsed:.1f}s", flush=True)

    # Convert accumulators to per-cell stats
    results = {sig: {} for sig in _SIGNALS_TO_EVALUATE}
    for sig_type, variants in bucket_rows.items():
        for variant_id, rows in variants.items():
            df_v = pd.DataFrame(rows)
            n_total = len(df_v)
            n_open = (df_v["outcome"] == "OPEN").sum()
            n_atr_unavail = (df_v["outcome"] == "ATR_UNAVAILABLE").sum()
            n_win = (df_v["outcome"] == "WIN").sum()
            n_loss = (df_v["outcome"] == "LOSS").sum()
            n_flat = (df_v["outcome"] == "FLAT").sum()
            n_resolved = n_win + n_loss + n_flat
            n_excl_flat = n_win + n_loss
            wr_excl_flat = round(n_win / n_excl_flat, 4) if n_excl_flat > 0 else None
            wilson = wilson_lower_bound_95(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
            p_val = binomial_p_value_vs_50(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
            avg_pnl = round(df_v[df_v["outcome"].isin(["WIN", "LOSS", "FLAT"])]["pnl_pct"].mean(), 4) \
                if n_resolved > 0 else None
            results[sig_type][variant_id] = {
                "n_total": int(n_total), "n_open": int(n_open),
                "n_atr_unavailable": int(n_atr_unavail),
                "n_resolved": int(n_resolved), "n_win": int(n_win),
                "n_loss": int(n_loss), "n_flat": int(n_flat),
                "n_excl_flat": int(n_excl_flat),
                "wr_excl_flat": wr_excl_flat,
                "wilson_lower_95": wilson,
                "p_value_vs_50": p_val,
                "avg_pnl_pct": avg_pnl,
                "rows_df": df_v,  # kept for tier evaluation
            }

    return results


# ── Tier evaluation per (signal × variant) ────────────────────────────

def run_tier_evals(matrix_results: dict, signals_df_indexed: pd.DataFrame) -> dict:
    """Run hypothesis_tester (BOOST + KILL) on each (signal × variant) cohort.
    Adds 'tier_eval' field to each cell."""
    for sig_type, variants in matrix_results.items():
        for variant_id, cell in variants.items():
            df_v = cell["rows_df"]
            if cell["n_excl_flat"] < 30:
                cell["tier_eval"] = {"boost_tier": "INSUFFICIENT_N",
                                       "kill_tier": "INSUFFICIENT_N"}
                continue
            # Map our W/L/F labels → hypothesis_tester's expected labels
            # (compute_cohort_stats matches against {DAY6_WIN, TARGET_HIT, DAY6_LOSS,
            # STOP_HIT, DAY6_FLAT, OPEN}). ATR_UNAVAILABLE → OPEN (excluded from WR).
            df_eval = df_v.copy()
            df_eval["outcome"] = df_eval["outcome"].map({
                "WIN": "DAY6_WIN", "LOSS": "DAY6_LOSS", "FLAT": "DAY6_FLAT",
                "OPEN": "OPEN", "ATR_UNAVAILABLE": "OPEN",
            })
            try:
                boost = evaluate_hypothesis(
                    df_eval, cohort_filter={}, hypothesis_type="BOOST")
                kill = evaluate_hypothesis(
                    df_eval, cohort_filter={}, hypothesis_type="KILL")
                cell["tier_eval"] = {
                    "boost_tier": boost["tier"],
                    "boost_train_wr": boost["train_stats"]["wr_excl_flat"],
                    "boost_test_wr": boost["test_stats"]["wr_excl_flat"],
                    "boost_train_n": (boost["train_stats"]["n_win"]
                                       + boost["train_stats"]["n_loss"]),
                    "boost_test_n": (boost["test_stats"]["n_win"]
                                      + boost["test_stats"]["n_loss"]),
                    "boost_drift_pp": boost["drift_pp"],
                    "kill_tier": kill["tier"],
                    "kill_train_wr": kill["train_stats"]["wr_excl_flat"],
                    "kill_test_wr": kill["test_stats"]["wr_excl_flat"],
                    "kill_drift_pp": kill["drift_pp"],
                }
            except Exception as e:
                cell["tier_eval"] = {"error": str(e)}
    return matrix_results




# ── Findings.md writer ────────────────────────────────────────────────

def _ordered_variants() -> list[str]:
    out = [f"D{n}" for n in _FIXED_DAY_EXITS]
    out += [f"TRAIL_{m}xATR" for m in _TRAILING_MULTIPLIERS]
    out += _LADDER_VARIANTS
    return out


def write_findings_md(matrix: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    variants = _ordered_variants()
    with open(output_path, "w") as f:
        f.write("# INV-006 — Exit timing optimization (12 variants × 3 signal types)\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write(f"**Signal types tested:** {', '.join(_SIGNALS_TO_EVALUATE)}\n\n")
        f.write(f"**Exit variants:** {len(variants)} ({', '.join(variants)})\n\n")
        f.write(f"**Baseline:** D6 (current scanner.config default)\n\n")

        # Caveats
        f.write("---\n\n## ⚠️ Caveats\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate):** active. Variant cohorts share parent "
                "signal universe with INV-001/002/003 → same Caveat 2 vulnerability at margin.\n\n")
        f.write("**Caveat 5 (ATR-based variants):** ATR-14 computed on cached parquets via "
                "rolling mean of true range (Wilder approximation). For signals where ATR is "
                "NaN at entry (first 14 days of each stock's history), ATR-based variants "
                "report `n_atr_unavailable`.\n\n")
        f.write("**Caveat 6 (LONG-only outcomes):** Per signal_replayer, all signals "
                "(including DOWN_TRI) have LONG-direction outcomes. INV-006 inherits this; "
                "DOWN_TRI variant results are LONG-direction, not the natural SHORT trade. "
                "Inverting for SHORT interpretation is a separate analysis.\n\n")

        # ── Section 1 — Methodology ──
        f.write("---\n\n## Section 1 — Methodology\n\n")
        f.write(f"**Pipeline:** for each of 105987 backtest signals, compute outcomes "
                f"across 12 exit variants. Per (signal_type × variant) cell: lifetime "
                f"stats + train/test OOS split (train 2011-2022 / test 2023-2026) + "
                f"hypothesis_tester evaluation. Compare each variant to D6 baseline.\n\n")
        f.write("**Variants tested:**\n")
        f.write("- **Fixed-day:** D2, D3, D4, D5, **D6 (baseline)**, D7, D8, D10 — exit at OPEN of N-th trading day post-entry.\n")
        f.write("- **Trailing-stop:** 1.5×ATR, 2.0×ATR, 2.5×ATR — initial stop = entry - mult×ATR_14_at_signal; daily update stop = max(prior, today_close - mult×today_ATR_14); exit at stop_price intraday on hit.\n")
        f.write("- **Ladder A:** 50% sold at entry+2R OR initial stop hit; 50% held to D6 OPEN. R = 1 ATR_14 unit.\n")
        f.write("- **Ladder B:** 33% at entry+1.5R; 33% at entry+2.5R; 34% trailing-2×ATR. Common initial stop = entry - 1×ATR for first two slices.\n\n")
        f.write("**W/L/F threshold:** ±0.5% from entry (matches signal_replayer FLAT semantics).\n\n")
        f.write(f"**Candidate threshold (vs D6 baseline):** Δ WR ≥ {_DIFF_THRESHOLD_PP*100}pp "
                f"AND p < {_P_VALUE_DIFF_MAX} AND n ≥ {_N_MIN_FOR_COMPARISON} → BEATS_BASELINE.\n\n")

        # ── Section 2 — Per-cell results ──
        for sig_type in _SIGNALS_TO_EVALUATE:
            f.write(f"---\n\n## Section 2 — {sig_type} variant results\n\n")
            cells = matrix.get(sig_type, {})
            baseline = cells.get(_BASELINE_EXIT, {})
            baseline_wr = baseline.get("wr_excl_flat")
            baseline_n = baseline.get("n_excl_flat", 0)
            f.write(f"**D6 baseline:** n_excl_flat={baseline_n}, "
                    f"WR={baseline_wr}, Wilson={baseline.get('wilson_lower_95')}, "
                    f"avg_pnl={baseline.get('avg_pnl_pct')}\n\n")
            f.write("| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | "
                    "Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | "
                    "p-value | Verdict |\n")
            f.write("|---------|-------------|-----|--------------|-------------|"
                    "----------|---------|----------|----------|----------|"
                    "--------------|---------|--------|\n")
            for variant_id in variants:
                cell = cells.get(variant_id, {})
                n_excl = cell.get("n_excl_flat", 0)
                wr = cell.get("wr_excl_flat")
                wilson = cell.get("wilson_lower_95")
                avg = cell.get("avg_pnl_pct")
                te = cell.get("tier_eval", {})
                if "error" in te:
                    train_wr = test_wr = drift = boost_tier = kill_tier = "ERR"
                else:
                    train_wr = te.get("boost_train_wr")
                    test_wr = te.get("boost_test_wr")
                    drift = te.get("boost_drift_pp")
                    boost_tier = te.get("boost_tier")
                    kill_tier = te.get("kill_tier")
                if variant_id == _BASELINE_EXIT:
                    verdict = "BASELINE"
                    delta_pp = 0.0
                    p_val_str = "—"
                else:
                    verdict, delta, p_val = _classify_variant_vs_baseline(
                        wr, n_excl, baseline_wr, baseline_n)
                    delta_pp = delta * 100 if delta is not None else None
                    p_val_str = p_val if p_val is not None else "—"
                f.write(f"| {variant_id} | {n_excl} | {wr} | {wilson} | {avg} | "
                        f"{train_wr} | {test_wr} | {drift} | {boost_tier} | {kill_tier} | "
                        f"{delta_pp} | {p_val_str} | {verdict} |\n")
            f.write("\n")

        # ── Section 3 — Headline findings ──
        f.write("---\n\n## Section 3 — Headline findings\n\n")
        # For each signal: which variants BEAT the baseline?
        for sig_type in _SIGNALS_TO_EVALUATE:
            cells = matrix.get(sig_type, {})
            baseline = cells.get(_BASELINE_EXIT, {})
            baseline_wr = baseline.get("wr_excl_flat")
            baseline_n = baseline.get("n_excl_flat", 0)
            beats = []
            worse = []
            marginal = []
            for variant_id in variants:
                if variant_id == _BASELINE_EXIT:
                    continue
                cell = cells.get(variant_id, {})
                wr = cell.get("wr_excl_flat")
                n_excl = cell.get("n_excl_flat", 0)
                verdict, delta, p_val = _classify_variant_vs_baseline(
                    wr, n_excl, baseline_wr, baseline_n)
                summary = (variant_id, wr, delta, p_val)
                if verdict == "BEATS_BASELINE":
                    beats.append(summary)
                elif verdict == "WORSE_THAN_BASELINE":
                    worse.append(summary)
                elif verdict == "MARGINAL_OR_EQUIVALENT":
                    marginal.append(summary)
            f.write(f"### {sig_type}\n\n")
            f.write(f"- **D6 baseline WR:** {baseline_wr} (n={baseline_n}, "
                    f"avg_pnl={baseline.get('avg_pnl_pct')})\n")
            f.write(f"- **Variants beating baseline:** {len(beats)}\n")
            for v in beats:
                f.write(f"  - `{v[0]}` WR={v[1]} (Δ={(v[2]*100):+.2f} pp, p={v[3]})\n")
            f.write(f"- **Variants worse than baseline:** {len(worse)}\n")
            for v in worse:
                f.write(f"  - `{v[0]}` WR={v[1]} (Δ={(v[2]*100):+.2f} pp, p={v[3]})\n")
            f.write(f"- **Marginal / equivalent:** {len(marginal)}\n\n")

        # Universal best?
        f.write("### Universal best exit?\n\n")
        # Find variant with highest WR avg across all 3 signal types
        avg_wr_per_variant = {}
        for variant_id in variants:
            wrs = []
            for sig_type in _SIGNALS_TO_EVALUATE:
                cell = matrix.get(sig_type, {}).get(variant_id, {})
                if cell.get("wr_excl_flat") is not None:
                    wrs.append(cell["wr_excl_flat"])
            if wrs:
                avg_wr_per_variant[variant_id] = round(sum(wrs) / len(wrs), 4)
        sorted_avg = sorted(avg_wr_per_variant.items(), key=lambda x: -x[1])
        f.write(f"Avg WR across 3 signal types per variant (top 5):\n\n")
        f.write("| Variant | Avg WR (3 signals) |\n|---------|--------------------|\n")
        for v, wr in sorted_avg[:5]:
            f.write(f"| {v} | {wr} |\n")
        f.write(f"\n**Highest avg WR variant:** `{sorted_avg[0][0]}` "
                f"(avg WR {sorted_avg[0][1]} across UP_TRI/DOWN_TRI/BULL_PROXY)\n\n")
        f.write(f"**D6 baseline avg WR:** {avg_wr_per_variant.get(_BASELINE_EXIT)}\n\n")

        # ── Section 4 — Open questions for user review ──
        f.write("---\n\n## Section 4 — Open questions for user review\n\n")
        f.write("CC does NOT make promotion decisions. The following questions are "
                "surfaced for user judgment in a separate session.\n\n")
        f.write("1. **Per-signal optimal exit:** for each signal type, which variant (if any) "
                "shows BEATS_BASELINE? Decision: switch that signal's exit logic in "
                "scanner.config — separate main-branch session.\n\n")
        f.write("2. **Universal best exit candidate:** does Section 3's highest-avg-WR variant "
                "beat D6 across ALL signal types? If yes → unified exit migration; if only one "
                "or two signals → signal-specific exit rules.\n\n")
        f.write("3. **Risk-adjusted comparison:** WR improvement alone may not justify exit "
                "migration if avg_pnl_pct is materially worse (lower WR with bigger wins can "
                "outperform higher WR with smaller wins). User considers WR + avg_pnl jointly.\n\n")
        f.write("4. **Caveat 2 audit dependency:** any BEATS_BASELINE variant at marginal n "
                "needs Caveat 2 audit before promotion to scanner.config update.\n\n")
        f.write("5. **patterns.json INV-006 status:** PRE_REGISTERED → COMPLETED is user-only.\n\n")

        f.write("---\n\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. No promotion "
                "decisions are made by CC.\n")


# ── Main orchestrator ─────────────────────────────────────────────────

def main():
    print(f"[INV-006] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"[INV-006] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    print(f"[INV-006] loaded {len(signals_df)} backtest signals", flush=True)

    cache = preload_cache()
    matrix = run_matrix(signals_df, cache)
    matrix = run_tier_evals(matrix, signals_df)
    print(f"[INV-006] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(matrix, _OUTPUT_FINDINGS)
    print(f"[INV-006] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-006] FATAL: {e}\n{tb}", flush=True)
        # Write minimal findings stub so user has audit trail even on crash
        try:
            _OUTPUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
            with open(_OUTPUT_FINDINGS, "w") as f:
                f.write(f"# INV-006 — CRASH at {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write(f"```\n{tb}\n```\n")
        except Exception:
            pass
        raise
