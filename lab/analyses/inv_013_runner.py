"""
INV-013 — DOWN_TRI exit timing direction-aware investigation.

Per pre-registered hypothesis (patterns.json INV-013): INV-006 DOWN_TRI exit
timing was invalidated by runner bug (LONG-only pnl + stop semantics applied
to SHORT-direction signals). After fixing runner with direction-aware logic,
identify whether D6 is optimal exit for DOWN_TRI signals or whether some other
variant beats it.

This is a DIRECTION-AWARE rebuild of the INV-006 runner pattern, fixing the
LONG-only bug. Reuses INV-006 schema where possible but with correct SHORT
semantics for DOWN_TRI.

Direction-aware semantics (per signal_replayer.compute_d6_outcome verified):
  SHORT pnl: (entry - exit) / entry × 100  (positive when price falls)
  SHORT stop: hit if high ≥ stop_price (stop placed ABOVE entry)
  SHORT target: hit if low ≤ target_price (target placed BELOW entry)

Exit variants (12 total; same as INV-006):
  Fixed-day (8): D2, D3, D4, D5, D6 (baseline), D7, D8, D10
  Trailing-stop (3): 1.5×ATR-14, 2×ATR-14, 2.5×ATR-14 (initial stop ABOVE entry,
    trails DOWNWARD as price falls)
  Profit ladder (2):
    A — 50% at entry-2R, 50% at D6 open (initial stop = entry + 1×ATR ABOVE)
    B — 33% at entry-1.5R, 33% at entry-2.5R, 34% trailing-2×ATR

Where R = 1 × ATR_14 at signal date.

Pipeline (parallels INV-006 but DOWN_TRI-only):
  1. Pre-load all stock parquets with ATR-14 column
  2. For each DOWN_TRI signal: compute outcomes for 12 variants using SHORT semantics
  3. Aggregate by variant → 12 cells
  4. Per-cell: compute_cohort_stats + train/test split + hypothesis_tester
  5. Compare each variant to D6 baseline (same SHORT semantics)
  6. Section 4 cross-references INV-006 invalidated DOWN_TRI numbers

Outputs:
  - /lab/analyses/INV-013_findings.md
  - /lab/logs/inv_013_run.log

NO promotion calls. NO patterns.json changes. Findings.md is data-only.
"""
from __future__ import annotations

import json
import math
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
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-013_findings.md"

_ATR_PERIOD = 14
_FLAT_THRESHOLD_PCT = 0.5
_LOOKAHEAD_DAYS = 11

_FIXED_DAY_EXITS = [2, 3, 4, 5, 6, 7, 8, 10]
_TRAILING_MULTIPLIERS = [1.5, 2.0, 2.5]
_LADDER_VARIANTS = ["LADDER_A_50at2R_50atD6", "LADDER_B_33_33_34trailing"]

_BASELINE_EXIT = "D6"

_DIFF_THRESHOLD_PP = 0.03
_P_VALUE_DIFF_MAX = 0.05
_N_MIN_FOR_COMPARISON = 100


# ── Helpers ───────────────────────────────────────────────────────────

def _classify_outcome(pnl_pct: float) -> str:
    if pnl_pct > _FLAT_THRESHOLD_PCT:
        return "WIN"
    if pnl_pct < -_FLAT_THRESHOLD_PCT:
        return "LOSS"
    return "FLAT"


def _compute_atr14(df: pd.DataFrame) -> pd.Series:
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
    z = abs(p1 - p2) / se
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return round(max(0.0, min(1.0, p)), 6)


def _classify_variant_vs_baseline(variant_wr: Optional[float], variant_n: int,
                                    baseline_wr: Optional[float], baseline_n: int) -> tuple:
    if (variant_wr is None or baseline_wr is None
            or variant_n < _N_MIN_FOR_COMPARISON
            or baseline_n < _N_MIN_FOR_COMPARISON):
        return ("INSUFFICIENT_N", None, None)
    delta = variant_wr - baseline_wr
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
    cache = {}
    print(f"[INV-013] preloading parquets from {_CACHE_DIR}…", flush=True)
    n_loaded = 0; n_skipped = 0
    for p in sorted(_CACHE_DIR.glob("*.parquet")):
        if p.name.startswith("_index_"):
            n_skipped += 1; continue
        try:
            df = pd.read_parquet(p)
            df = df.sort_index()
            if not all(col in df.columns for col in ["Open", "High", "Low", "Close"]):
                n_skipped += 1; continue
            df["ATR_14"] = _compute_atr14(df)
            symbol = p.stem.replace("_NS", ".NS")
            cache[symbol] = df
            n_loaded += 1
        except Exception as e:
            print(f"  skip {p.name}: {e}", flush=True)
            n_skipped += 1
    print(f"[INV-013] cache loaded: {n_loaded} stocks, {n_skipped} skipped", flush=True)
    return cache


# ── Direction-aware per-signal evaluator (SHORT) ─────────────────────

def evaluate_short_signal_all_variants(signal_row: pd.Series, cache: dict) -> dict:
    """Compute outcomes for one DOWN_TRI signal across all 12 exit variants
    using SHORT-direction semantics:
      pnl = (entry - exit) / entry × 100
      stop_hit: high ≥ stop_price (stop ABOVE entry; trails DOWNWARD)
      target_hit: low ≤ target_price (target BELOW entry)
    """
    symbol = signal_row["symbol"]
    entry_date = signal_row.get("entry_date")
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

    if entry_idx + _LOOKAHEAD_DAYS > len(df):
        return {}

    window = df.iloc[entry_idx : entry_idx + _LOOKAHEAD_DAYS]
    entry_price = float(window["Open"].iloc[0])
    if entry_price <= 0:
        return {}

    atr_at_entry = float(df["ATR_14"].iloc[max(entry_idx - 1, 0)])
    atr_valid = not (pd.isna(atr_at_entry) or atr_at_entry <= 0)

    results = {}

    # ── Fixed-day exits — SHORT semantics: pnl = (entry - exit) / entry × 100 ──
    for n_day in _FIXED_DAY_EXITS:
        if n_day >= len(window):
            results[f"D{n_day}"] = {"pnl_pct": None, "outcome": "OPEN", "exit_day": None}
            continue
        exit_price = float(window["Open"].iloc[n_day])
        pnl_pct = (entry_price - exit_price) / entry_price * 100  # SHORT
        results[f"D{n_day}"] = {
            "pnl_pct": round(pnl_pct, 4),
            "outcome": _classify_outcome(pnl_pct),
            "exit_day": n_day,
        }

    # ── Trailing-stop variants — SHORT semantics: stop ABOVE entry, trails DOWN ──
    for mult in _TRAILING_MULTIPLIERS:
        var_id = f"TRAIL_{mult}xATR"
        if not atr_valid:
            results[var_id] = {"pnl_pct": None, "outcome": "ATR_UNAVAILABLE", "exit_day": None}
            continue
        # SHORT: initial stop = entry + mult × ATR (ABOVE entry)
        stop = entry_price + mult * atr_at_entry
        exit_price = None
        exit_day = None
        for i in range(1, len(window)):
            atr_today = float(window["ATR_14"].iloc[i])
            day_high = float(window["High"].iloc[i])
            day_close = float(window["Close"].iloc[i])
            # SHORT stop hit: high ≥ stop_price
            if day_high >= stop:
                exit_price = stop
                exit_day = i
                break
            # SHORT trail: stop = min(prior_stop, today_close + mult × today_ATR)
            # (trail DOWNWARD as price falls)
            if not pd.isna(atr_today) and atr_today > 0:
                stop = min(stop, day_close + mult * atr_today)
        if exit_price is None:
            # Never hit — exit at D10 close
            exit_price = float(window["Close"].iloc[-1])
            exit_day = _LOOKAHEAD_DAYS - 1
        pnl_pct = (entry_price - exit_price) / entry_price * 100  # SHORT
        results[var_id] = {
            "pnl_pct": round(pnl_pct, 4),
            "outcome": _classify_outcome(pnl_pct),
            "exit_day": exit_day,
        }

    # ── Ladder variants — SHORT semantics ──
    if atr_valid:
        R = atr_at_entry  # 1 ATR unit
        # SHORT: initial stop ABOVE entry; targets BELOW entry
        initial_stop = entry_price + R

        # Variant A: 50% at entry-2R (target BELOW entry), 50% at D6 open
        target_a = entry_price - 2 * R  # SHORT target below entry
        slice1_pnl = None
        for i in range(1, len(window)):
            day_high = float(window["High"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            # SHORT stop hit: high ≥ initial_stop (above entry)
            if day_high >= initial_stop:
                slice1_pnl = (entry_price - initial_stop) / entry_price * 100
                break
            # SHORT target hit: low ≤ target_a (below entry)
            if day_low <= target_a:
                slice1_pnl = (entry_price - target_a) / entry_price * 100
                break
        if slice1_pnl is None:
            d6_price = float(window["Open"].iloc[6]) if len(window) > 6 else float(window["Close"].iloc[-1])
            slice1_pnl = (entry_price - d6_price) / entry_price * 100

        slice2_pnl = None
        for i in range(1, len(window)):
            day_high = float(window["High"].iloc[i])
            if day_high >= initial_stop:
                slice2_pnl = (entry_price - initial_stop) / entry_price * 100
                break
        if slice2_pnl is None:
            d6_price = float(window["Open"].iloc[6]) if len(window) > 6 else float(window["Close"].iloc[-1])
            slice2_pnl = (entry_price - d6_price) / entry_price * 100
        ladder_a_pnl = 0.5 * slice1_pnl + 0.5 * slice2_pnl
        results["LADDER_A_50at2R_50atD6"] = {
            "pnl_pct": round(ladder_a_pnl, 4),
            "outcome": _classify_outcome(ladder_a_pnl),
            "exit_day": 6,
        }

        # Variant B: 33% at entry-1.5R, 33% at entry-2.5R, 34% trailing-2x ATR
        target_b1 = entry_price - 1.5 * R
        target_b2 = entry_price - 2.5 * R
        sb1 = None; sb2 = None
        for i in range(1, len(window)):
            day_high = float(window["High"].iloc[i])
            day_low = float(window["Low"].iloc[i])
            if day_high >= initial_stop and (sb1 is None or sb2 is None):
                if sb1 is None:
                    sb1 = (entry_price - initial_stop) / entry_price * 100
                if sb2 is None:
                    sb2 = (entry_price - initial_stop) / entry_price * 100
                break
            if sb1 is None and day_low <= target_b1:
                sb1 = (entry_price - target_b1) / entry_price * 100
            if sb2 is None and day_low <= target_b2:
                sb2 = (entry_price - target_b2) / entry_price * 100
            if sb1 is not None and sb2 is not None:
                break
        if sb1 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb1 = (entry_price - d10_close) / entry_price * 100
        if sb2 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb2 = (entry_price - d10_close) / entry_price * 100

        # Slice 3: trailing 2x ATR (SHORT semantics)
        stop3 = entry_price + 2 * atr_at_entry
        sb3 = None
        for i in range(1, len(window)):
            atr_today = float(window["ATR_14"].iloc[i])
            day_high = float(window["High"].iloc[i])
            day_close = float(window["Close"].iloc[i])
            if day_high >= stop3:
                sb3 = (entry_price - stop3) / entry_price * 100
                break
            if not pd.isna(atr_today) and atr_today > 0:
                stop3 = min(stop3, day_close + 2 * atr_today)
        if sb3 is None:
            d10_close = float(window["Close"].iloc[-1])
            sb3 = (entry_price - d10_close) / entry_price * 100

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


# ── Matrix scan ───────────────────────────────────────────────────────

def run_matrix(signals_df: pd.DataFrame, cache: dict) -> dict:
    dt = signals_df[
        (signals_df["signal"] == "DOWN_TRI")
        & signals_df["entry_date"].notna()
        & signals_df["entry_price"].notna()
    ].copy()
    print(f"[INV-013] DOWN_TRI evaluable signals: {len(dt)}", flush=True)

    bucket_rows = {}  # variant_id → list of {pnl_pct, outcome, exit_day, scan_date, atr_at_entry}
    n_eval = 0; n_skipped = 0
    t0 = time.time()
    for idx, row in dt.iterrows():
        outcomes = evaluate_short_signal_all_variants(row, cache)
        if not outcomes:
            n_skipped += 1; continue
        # Cache atr_at_entry for R-mult downstream
        symbol = row["symbol"]
        atr_e = None
        if symbol in cache:
            df = cache[symbol]
            try:
                ed_ts = pd.Timestamp(row["entry_date"])
                if ed_ts in df.index:
                    eidx = df.index.get_loc(ed_ts)
                    atr_e = float(df["ATR_14"].iloc[max(eidx - 1, 0)])
                    if pd.isna(atr_e):
                        atr_e = None
            except Exception:
                pass
        for variant_id, oc in outcomes.items():
            if variant_id not in bucket_rows:
                bucket_rows[variant_id] = []
            bucket_rows[variant_id].append({
                "scan_date": row["scan_date"],
                "symbol": symbol,
                "outcome": oc["outcome"],
                "pnl_pct": oc["pnl_pct"],
                "exit_day": oc["exit_day"],
                "entry_price": float(row["entry_price"]),
                "atr_at_entry": atr_e,
            })
        n_eval += 1
        if n_eval % 5000 == 0:
            print(f"[INV-013] {n_eval}/{len(dt)} ({time.time()-t0:.1f}s; {n_skipped} skipped)",
                  flush=True)

    print(f"[INV-013] matrix done: {n_eval} evaluated, {n_skipped} skipped, "
          f"{time.time()-t0:.1f}s", flush=True)

    # Aggregate per variant
    results = {}
    for variant_id, rows in bucket_rows.items():
        df_v = pd.DataFrame(rows)
        n_total = len(df_v)
        n_open = (df_v["outcome"] == "OPEN").sum()
        n_atr_unavail = (df_v["outcome"] == "ATR_UNAVAILABLE").sum()
        n_win = (df_v["outcome"] == "WIN").sum()
        n_loss = (df_v["outcome"] == "LOSS").sum()
        n_flat = (df_v["outcome"] == "FLAT").sum()
        n_resolved = n_win + n_loss + n_flat
        n_excl_flat = n_win + n_loss
        wr = round(n_win / n_excl_flat, 4) if n_excl_flat > 0 else None
        wilson = wilson_lower_bound_95(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
        p_val = binomial_p_value_vs_50(int(n_win), int(n_excl_flat)) if n_excl_flat > 0 else None
        resolved_df = df_v[df_v["outcome"].isin(["WIN", "LOSS", "FLAT"])]
        avg_pnl = round(resolved_df["pnl_pct"].mean(), 4) if len(resolved_df) > 0 else None
        # R-mult per signal (where atr available)
        r_mults = []
        for _, r in resolved_df.iterrows():
            ae = r.get("atr_at_entry")
            ep = r.get("entry_price")
            if ae and ae > 0 and ep and ep > 0:
                atr_pct = (ae / ep) * 100
                if atr_pct > 0:
                    r_mults.append(r["pnl_pct"] / atr_pct)
        avg_r_mult = round(float(np.mean(r_mults)), 4) if r_mults else None
        results[variant_id] = {
            "n_total": int(n_total), "n_open": int(n_open),
            "n_atr_unavailable": int(n_atr_unavail),
            "n_resolved": int(n_resolved), "n_win": int(n_win),
            "n_loss": int(n_loss), "n_flat": int(n_flat),
            "n_excl_flat": int(n_excl_flat),
            "wr_excl_flat": wr,
            "wilson_lower_95": wilson,
            "p_value_vs_50": p_val,
            "avg_pnl_pct": avg_pnl,
            "avg_r_mult": avg_r_mult,
            "rows_df": df_v,
        }
    return results


# ── Tier evaluation per variant ───────────────────────────────────────

def run_tier_evals(matrix_results: dict) -> dict:
    for variant_id, cell in matrix_results.items():
        df_v = cell["rows_df"]
        if cell["n_excl_flat"] < 30:
            cell["tier_eval"] = {"boost_tier": "INSUFFICIENT_N",
                                   "kill_tier": "INSUFFICIENT_N"}
            continue
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


# ── Drawdown analysis (parallel to INV-006 drawdown supplementary) ────

def compute_drawdown_per_signal(signals_df: pd.DataFrame, cache: dict) -> pd.DataFrame:
    """For each DOWN_TRI signal, compute MAE (max adverse excursion) over D6 + D10
    windows. SHORT-direction MAE = highest HIGH during window vs entry (positive
    = adverse for SHORT)."""
    dt = signals_df[
        (signals_df["signal"] == "DOWN_TRI")
        & signals_df["entry_date"].notna()
        & signals_df["entry_price"].notna()
    ].copy()
    records = []
    for _, row in dt.iterrows():
        sym = row["symbol"]
        if sym not in cache:
            continue
        df = cache[sym]
        ed = row.get("entry_date")
        if ed is None or pd.isna(ed):
            continue
        ed_ts = pd.Timestamp(ed)
        if ed_ts not in df.index:
            continue
        idx = df.index.get_loc(ed_ts)
        if idx + _LOOKAHEAD_DAYS > len(df):
            continue
        window = df.iloc[idx : idx + _LOOKAHEAD_DAYS]
        entry_price = float(window["Open"].iloc[0])
        if entry_price <= 0:
            continue
        # SHORT MAE: highest HIGH during window (adverse direction)
        highs_d1_d6 = window["High"].iloc[1:7]
        highs_d1_d10 = window["High"].iloc[1:11]
        # Adverse pct = (high - entry) / entry × 100 (positive = bad for SHORT)
        mae_d6_pct = (float(highs_d1_d6.max()) - entry_price) / entry_price * 100
        mae_d10_pct = (float(highs_d1_d10.max()) - entry_price) / entry_price * 100
        # D6 / D10 SHORT pnl
        d6_open = float(window["Open"].iloc[6])
        d10_open = float(window["Open"].iloc[10])
        pnl_d6 = (entry_price - d6_open) / entry_price * 100
        pnl_d10 = (entry_price - d10_open) / entry_price * 100
        # Stop hit detection (using row['stop'] which is correct SHORT stop ABOVE entry)
        stop_price = float(row["stop"]) if not pd.isna(row.get("stop")) else None
        stop_hit_d6 = None; stop_hit_d10 = None
        if stop_price is not None and stop_price > 0:
            for i in range(1, 11):
                if float(window["High"].iloc[i]) >= stop_price:
                    if i <= 6 and stop_hit_d6 is None:
                        stop_hit_d6 = i
                    if stop_hit_d10 is None:
                        stop_hit_d10 = i
                    if stop_hit_d6 is not None:
                        break
            if stop_hit_d6 is None and stop_hit_d10 is None:
                for i in range(7, 11):
                    if float(window["High"].iloc[i]) >= stop_price:
                        stop_hit_d10 = i
                        break
        days_d6 = stop_hit_d6 if stop_hit_d6 is not None else 6
        days_d10 = stop_hit_d10 if stop_hit_d10 is not None else 10
        records.append({
            "scan_date": row["scan_date"], "symbol": sym,
            "mae_d6": mae_d6_pct, "mae_d10": mae_d10_pct,
            "stop_hit_d6": stop_hit_d6 is not None,
            "stop_hit_d10": stop_hit_d10 is not None,
            "stop_hit_d710_only": (stop_hit_d6 is None and stop_hit_d10 is not None),
            "days_d6": days_d6, "days_d10": days_d10,
            "pnl_d6": pnl_d6, "pnl_d10": pnl_d10,
        })
    return pd.DataFrame(records)


# ── Findings.md writer ────────────────────────────────────────────────

def _ordered_variants() -> list[str]:
    out = [f"D{n}" for n in _FIXED_DAY_EXITS]
    out += [f"TRAIL_{m}xATR" for m in _TRAILING_MULTIPLIERS]
    out += _LADDER_VARIANTS
    return out


def write_findings_md(matrix: dict, drawdown_df: pd.DataFrame,
                       output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    variants = _ordered_variants()
    baseline = matrix.get(_BASELINE_EXIT, {})
    baseline_wr = baseline.get("wr_excl_flat")
    baseline_n = baseline.get("n_excl_flat", 0)
    baseline_avg_pnl = baseline.get("avg_pnl_pct")
    baseline_r = baseline.get("avg_r_mult")

    with open(output_path, "w") as f:
        f.write("# INV-013 — DOWN_TRI exit timing direction-aware investigation\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write("**Cohort:** signal=DOWN_TRI; direction=SHORT (verified per audit)\n\n")
        f.write(f"**Variants:** {len(variants)} ({', '.join(variants)})\n\n")
        f.write("**Baseline:** D6 (current scanner.config default)\n\n")

        # Caveats
        f.write("---\n\n## ⚠️ Caveats\n\n")
        f.write("**Direction-aware fix:** This investigation rebuilds the INV-006 runner "
                "pattern with SHORT-direction semantics for DOWN_TRI signals. SHORT pnl = "
                "(entry - exit) / entry × 100; SHORT stop_hit when high ≥ stop_price; SHORT "
                "target_hit when low ≤ target_price. Trailing stops placed ABOVE entry, "
                "trail DOWNWARD as price falls.\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate)** inherited from MS-2 cross-validation; "
                "DOWN_TRI subset of universe; user re-validates surfaced candidates "
                "post-Caveat 2 audit before promotion.\n\n")
        f.write("**ATR computation:** ATR-14 computed from cached OHLC parquets via rolling "
                "mean of true range (Wilder approximation; same as INV-006). For signals "
                "where ATR is NaN at entry (first 14 days of cache), ATR-based variants "
                "report `n_atr_unavailable`.\n\n")

        # ── Section 1 — Methodology ──
        f.write("---\n\n## Section 1 — Methodology + direction-aware logic\n\n")
        f.write("**Pipeline:**\n")
        f.write("1. Filter backtest_signals.parquet to signal='DOWN_TRI' (n=19961; all direction='SHORT')\n")
        f.write("2. Pre-load 188 stock parquets with ATR-14 column\n")
        f.write("3. For each signal, compute outcomes for 12 exit variants using SHORT semantics:\n")
        f.write("   - Fixed-day exits (D2-D10): exit at OPEN of N-th trading day; "
                "pnl = (entry - exit) / entry × 100\n")
        f.write("   - Trailing-stop variants: initial stop = entry + mult × ATR (ABOVE entry); "
                "each day stop = min(prior, today_close + mult × today_ATR); "
                "stop hit when high ≥ stop\n")
        f.write("   - Ladder A: 50% at entry-2R (SHORT target below entry), 50% at D6 OPEN\n")
        f.write("   - Ladder B: 33% at entry-1.5R + 33% at entry-2.5R + 34% trailing-2×ATR\n")
        f.write("4. Aggregate by variant; compute lifetime stats; train/test OOS split + "
                "hypothesis_tester.\n")
        f.write("5. Compare each variant to D6 baseline (same SHORT semantics — apples-to-apples).\n\n")
        f.write(f"**Candidate threshold:** Δ WR ≥ {_DIFF_THRESHOLD_PP*100}pp + p < {_P_VALUE_DIFF_MAX} + "
                f"n ≥ {_N_MIN_FOR_COMPARISON} → BEATS_BASELINE.\n\n")

        # ── Section 2 — Per-variant results ──
        f.write("---\n\n## Section 2 — Per-variant results (DOWN_TRI; SHORT semantics)\n\n")
        f.write(f"**D6 baseline:** n_excl_flat={baseline_n}, "
                f"WR={baseline_wr}, Wilson={baseline.get('wilson_lower_95')}, "
                f"avg_pnl={baseline_avg_pnl}%, R-mult={baseline_r}\n\n")
        f.write("| Variant | n_excl_flat | WR | Wilson_lower | Avg_pnl_pct | Avg_R-mult | "
                "Train_WR | Test_WR | Drift_pp | BoostTier | KillTier | Δ vs D6 (pp) | "
                "p-value | Verdict |\n")
        f.write("|---------|-------------|-----|--------------|-------------|------------|"
                "----------|---------|----------|----------|----------|"
                "--------------|---------|--------|\n")
        for v in variants:
            cell = matrix.get(v, {})
            n_ex = cell.get("n_excl_flat", 0)
            wr = cell.get("wr_excl_flat")
            wilson = cell.get("wilson_lower_95")
            avg = cell.get("avg_pnl_pct")
            r_mult = cell.get("avg_r_mult")
            te = cell.get("tier_eval", {})
            if "error" in te:
                train_wr = test_wr = drift = boost_t = kill_t = "ERR"
            else:
                train_wr = te.get("boost_train_wr")
                test_wr = te.get("boost_test_wr")
                drift = te.get("boost_drift_pp")
                boost_t = te.get("boost_tier")
                kill_t = te.get("kill_tier")
            if v == _BASELINE_EXIT:
                verdict = "BASELINE"; delta_pp = 0.0; p_str = "—"
            else:
                verdict, delta, p_val = _classify_variant_vs_baseline(
                    wr, n_ex, baseline_wr, baseline_n)
                delta_pp = round(delta * 100, 2) if delta is not None else None
                p_str = p_val if p_val is not None else "—"
            f.write(f"| {v} | {n_ex} | {wr} | {wilson} | {avg} | {r_mult} | "
                    f"{train_wr} | {test_wr} | {drift} | {boost_t} | {kill_t} | "
                    f"{delta_pp} | {p_str} | {verdict} |\n")
        f.write("\n")

        # ── Section 3 — Drawdown + capital efficiency ──
        f.write("---\n\n## Section 3 — Drawdown + capital efficiency (D6 vs D10)\n\n")
        if drawdown_df.empty:
            f.write("_No drawdown records (insufficient post-entry windows)._\n\n")
        else:
            n = len(drawdown_df)
            f.write(f"**Records:** {n} DOWN_TRI signals with full 11-day post-entry window.\n\n")
            f.write("**MAE (max adverse excursion) — for SHORT, highest HIGH vs entry "
                    "(positive = bad for SHORT):**\n\n")
            f.write("| Window | n | mean | median | p25 | p75 | p95 worst |\n")
            f.write("|--------|---|------|--------|-----|-----|-----------|\n")
            for col, label in [("mae_d6", "D6"), ("mae_d10", "D10")]:
                arr = drawdown_df[col].dropna().values
                if len(arr) == 0: continue
                f.write(f"| {label} | {len(arr)} | "
                        f"{np.mean(arr):+.3f}% | "
                        f"{np.median(arr):+.3f}% | "
                        f"{np.percentile(arr, 25):+.3f}% | "
                        f"{np.percentile(arr, 75):+.3f}% | "
                        f"{np.percentile(arr, 95):+.3f}% |\n")
            f.write("\n")
            f.write("**Stop-out frequency (SHORT-direction stop ABOVE entry):**\n\n")
            f.write("| Stop window | n | pct |\n|---|---|---|\n")
            n_stop_d6 = int(drawdown_df["stop_hit_d6"].sum())
            n_addl = int(drawdown_df["stop_hit_d710_only"].sum())
            n_stop_d10_total = int(drawdown_df["stop_hit_d10"].sum())
            f.write(f"| Stop in D1-D6 | {n_stop_d6} | {n_stop_d6/n*100:.2f}% |\n")
            f.write(f"| Additional stop in D7-D10 | {n_addl} | {n_addl/n*100:.2f}% |\n")
            f.write(f"| Total stop by D10 | {n_stop_d10_total} | {n_stop_d10_total/n*100:.2f}% |\n\n")
            f.write("**Per-trade pnl distribution (SHORT pnl):**\n\n")
            f.write("| Variant | p5 | p25 | p50 | p75 | p95 | mean | std |\n")
            f.write("|---------|------|------|------|------|------|------|------|\n")
            for col, label in [("pnl_d6", "D6"), ("pnl_d10", "D10")]:
                arr = drawdown_df[col].dropna().values
                if len(arr) == 0: continue
                f.write(f"| {label} | "
                        f"{np.percentile(arr, 5):+.3f}% | "
                        f"{np.percentile(arr, 25):+.3f}% | "
                        f"{np.percentile(arr, 50):+.3f}% | "
                        f"{np.percentile(arr, 75):+.3f}% | "
                        f"{np.percentile(arr, 95):+.3f}% | "
                        f"{np.mean(arr):+.3f}% | "
                        f"{np.std(arr, ddof=1):+.3f}% |\n")
            f.write("\n")
            f.write("**Capital efficiency (Σ pnl / Σ days held):**\n\n")
            f.write("| Variant | n | Σ pnl% | Σ days | pnl/day | avg days |\n")
            f.write("|---------|---|---------|---------|----------|----------|\n")
            for pnl_col, days_col, label in [("pnl_d6", "days_d6", "D6"),
                                              ("pnl_d10", "days_d10", "D10")]:
                sum_pnl = drawdown_df[pnl_col].sum()
                sum_days = drawdown_df[days_col].sum()
                pnl_per_day = sum_pnl / sum_days if sum_days > 0 else 0
                avg_days = sum_days / n if n > 0 else 0
                f.write(f"| {label} | {n} | {sum_pnl:+.1f}% | {sum_days} | "
                        f"{pnl_per_day:+.5f}% | {avg_days:.2f} |\n")
            f.write("\n")

        # ── Section 4 — Comparison to invalidated INV-006 DOWN_TRI ──
        f.write("---\n\n## Section 4 — Comparison to invalidated INV-006 DOWN_TRI numbers\n\n")
        f.write("INV-006 reported DOWN_TRI variants using LONG-only pnl + stop logic, which "
                "INVERTS the sign for SHORT-direction signals. INV-013 corrects this. The "
                "table below cross-references what INV-006 reported (invalid) vs what INV-013 "
                "now reports (correct).\n\n")
        f.write("| Variant | INV-006 reported WR (INVALID — LONG-direction) | INV-013 corrected WR (SHORT-direction) | Sign inversion check |\n")
        f.write("|---------|------------------------------------------------|-----------------------------------------|----------------------|\n")
        # INV-006 hardcoded DOWN_TRI WR (from prior findings):
        inv6_invalid = {
            "D6": 0.5347,
            "TRAIL_1.5xATR": 0.4366,
            "TRAIL_2.0xATR": 0.4756,
            "TRAIL_2.5xATR": 0.5012,
            "LADDER_A_50at2R_50atD6": 0.4167,
            "LADDER_B_33_33_34trailing": 0.4441,
        }
        for v in variants:
            inv6 = inv6_invalid.get(v)
            cell = matrix.get(v, {})
            inv13 = cell.get("wr_excl_flat")
            if inv6 is not None and inv13 is not None:
                # If INV-006 was inverted, expect INV-006 WR + INV-013 WR ≈ 1 (not exact due to FLAT handling)
                sum_check = round(inv6 + inv13, 4)
                check_note = f"sum={sum_check} (~1.0 indicates inversion)" if abs(sum_check - 1.0) < 0.1 else f"sum={sum_check}"
            else:
                check_note = "—"
            f.write(f"| {v} | {inv6 if inv6 is not None else '—'} | {inv13} | {check_note} |\n")
        f.write("\n*Sum ≈ 1.0 indicates the INV-006 number was the LONG-direction inversion "
                "of the SHORT semantics (W/L flip; FLAT handling causes minor deviation). "
                "INV-013 numbers are the corrected SHORT-direction values.*\n\n")

        # ── Section 5 — Headline ──
        f.write("---\n\n## Section 5 — Headline findings (data only; NO promotion calls)\n\n")
        beats = []; worse = []; marginal = []
        for v in variants:
            if v == _BASELINE_EXIT: continue
            cell = matrix.get(v, {})
            wr = cell.get("wr_excl_flat"); n_ex = cell.get("n_excl_flat", 0)
            verdict, delta, p_val = _classify_variant_vs_baseline(
                wr, n_ex, baseline_wr, baseline_n)
            summary = (v, wr, delta, p_val, cell.get("avg_pnl_pct"), cell.get("avg_r_mult"))
            if verdict == "BEATS_BASELINE": beats.append(summary)
            elif verdict == "WORSE_THAN_BASELINE": worse.append(summary)
            elif verdict == "MARGINAL_OR_EQUIVALENT": marginal.append(summary)
        f.write(f"- **D6 baseline (SHORT-direction, corrected):** WR {baseline_wr}, "
                f"n_excl_flat {baseline_n}, avg_pnl {baseline_avg_pnl}%, R-mult {baseline_r}\n")
        f.write(f"- **Variants BEAT D6 on WR (≥3pp + p<0.05 + n≥100):** {len(beats)}\n")
        for v in beats:
            f.write(f"  - `{v[0]}` WR={v[1]} (Δ={(v[2]*100):+.2f}pp, p={v[3]}, "
                    f"avg_pnl={v[4]}%, R-mult={v[5]})\n")
        f.write(f"- **Variants WORSE than D6:** {len(worse)}\n")
        for v in worse:
            f.write(f"  - `{v[0]}` WR={v[1]} (Δ={(v[2]*100):+.2f}pp, p={v[3]})\n")
        f.write(f"- **Marginal / equivalent:** {len(marginal)}\n\n")

        # Pnl-jointly comparison (parallel to INV-006 supplementary)
        f.write("**Pnl improvement check (≥10% relative + p<0.05 vs D6 avg_pnl):**\n\n")
        pnl_beats = []
        if baseline_avg_pnl is not None and baseline_avg_pnl != 0:
            for v in variants:
                if v == _BASELINE_EXIT: continue
                cell = matrix.get(v, {})
                v_avg = cell.get("avg_pnl_pct")
                if v_avg is None: continue
                rel = (v_avg - baseline_avg_pnl) / abs(baseline_avg_pnl) * 100
                # Welch t-test on per-trade pnl
                df_v = cell.get("rows_df")
                df_b = baseline.get("rows_df")
                if df_v is None or df_b is None: continue
                a = df_v[df_v["outcome"].isin(["WIN", "LOSS", "FLAT"])]["pnl_pct"].values
                b = df_b[df_b["outcome"].isin(["WIN", "LOSS", "FLAT"])]["pnl_pct"].values
                if len(a) < 2 or len(b) < 2: continue
                m1, m2 = np.mean(a), np.mean(b)
                v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
                se = (v1 / len(a) + v2 / len(b)) ** 0.5
                if se > 0:
                    z = (m1 - m2) / se
                    p_pnl = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
                else:
                    p_pnl = 1.0
                if rel >= 10 and p_pnl < 0.05 and len(a) >= _N_MIN_FOR_COMPARISON:
                    pnl_beats.append((v, v_avg, rel, p_pnl))
        f.write(f"Variants beating D6 on pnl (≥10% relative + p<0.05): {len(pnl_beats)}\n")
        for v, vp, rel, p in pnl_beats:
            f.write(f"  - `{v}` avg_pnl={vp:+.3f}% (vs D6 {baseline_avg_pnl:+.3f}%; "
                    f"rel={rel:+.1f}%; p={p:.4f})\n")
        f.write("\n")

        # Synthesized headline
        if beats:
            top = max(beats, key=lambda x: abs(x[2] or 0))
            headline = (f"INV-013 surfaces {len(beats)} variant(s) beating D6 on WR. "
                        f"Strongest: `{top[0]}` (Δ {(top[2]*100):+.2f}pp, p={top[3]}). "
                        f"User reviews per-cell tier eligibility before any migration call.")
        elif pnl_beats:
            top = max(pnl_beats, key=lambda x: abs(x[2]))
            headline = (f"INV-013 finds 0 variants beating D6 on WR but {len(pnl_beats)} "
                        f"beating on pnl (≥10% relative + p<0.05). Strongest: "
                        f"`{top[0]}` (rel {top[2]:+.1f}%, p={top[3]:.4f}). "
                        f"Pattern parallels INV-006 UP_TRI/BULL_PROXY where longer holds "
                        f"capture more pnl per winning trade.")
        else:
            headline = ("INV-013 finds 0 variants beating D6 on WR or pnl. "
                        "DOWN_TRI D6 confirmed as competitive baseline; no exit-timing "
                        "migration warranted. Direction-aware fix produces clean negative "
                        "result (vs INV-006 inverted findings).")
        f.write(f"**Headline:** {headline}\n\n")

        # ── Section 6 — Open questions ──
        f.write("---\n\n## Section 6 — Open questions for user review\n\n")
        f.write("1. **DOWN_TRI exit migration:** does Section 2 surface any BEATS_BASELINE "
                "variant that warrants scanner.config HOLDING_DAYS update for SHORT signals? "
                "User decides per cell.\n\n")
        f.write("2. **Cross-signal unification (with INV-006):** UP_TRI × D10 was identified "
                "as plausibly net-positive in INV-006 supplementary. If INV-013 also surfaces "
                "D10 (or another variant) for DOWN_TRI, consider unified migration; if "
                "DOWN_TRI prefers different exit, signal-specific config required.\n\n")
        f.write("3. **Drawdown trade-off (Section 3):** longer holds widen the MAE distribution "
                "for SHORT trades the same way as for LONG. User weighs WR/pnl improvement "
                "against deeper tail risk.\n\n")
        f.write("4. **Caveat 2 audit dependency:** any BEATS_BASELINE variant at marginal n "
                "needs Caveat 2 audit before promotion.\n\n")
        f.write("5. **patterns.json INV-013 status:** PRE_REGISTERED → COMPLETED is "
                "user-only transition.\n\n")

        f.write("---\n\n## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. "
                "No promotion decisions are made by CC.\n")


# ── Main orchestrator ─────────────────────────────────────────────────

def main():
    print(f"[INV-013] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"[INV-013] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    print(f"[INV-013] loaded {len(signals_df)} signals", flush=True)

    # Sanity: verify all DOWN_TRI are direction='SHORT'
    dt = signals_df[signals_df["signal"] == "DOWN_TRI"]
    long_dt = dt[dt["direction"] != "SHORT"]
    if len(long_dt) > 0:
        raise SystemExit(f"T5 SANITY FAIL: {len(long_dt)} DOWN_TRI signals with direction != SHORT")
    print(f"[INV-013] DOWN_TRI sanity: {len(dt)} signals, all direction=SHORT ✓", flush=True)

    cache = preload_cache()
    matrix = run_matrix(signals_df, cache)
    matrix = run_tier_evals(matrix)

    print(f"[INV-013] computing drawdown analysis…", flush=True)
    drawdown_df = compute_drawdown_per_signal(signals_df, cache)
    print(f"[INV-013] drawdown records: {len(drawdown_df)}", flush=True)

    # Summary print
    baseline = matrix.get(_BASELINE_EXIT, {})
    print(f"[INV-013] D6 baseline: n_excl_flat={baseline.get('n_excl_flat')}, "
          f"WR={baseline.get('wr_excl_flat')}, avg_pnl={baseline.get('avg_pnl_pct')}%",
          flush=True)

    print(f"[INV-013] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(matrix, drawdown_df, _OUTPUT_FINDINGS)
    print(f"[INV-013] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[INV-013] FATAL: {e}\n{tb}", flush=True)
        try:
            _OUTPUT_FINDINGS.parent.mkdir(parents=True, exist_ok=True)
            with open(_OUTPUT_FINDINGS, "w") as f:
                f.write(f"# INV-013 — CRASH at {datetime.now(timezone.utc).isoformat()}\n\n")
                f.write(f"```\n{tb}\n```\n")
        except Exception:
            pass
        raise
