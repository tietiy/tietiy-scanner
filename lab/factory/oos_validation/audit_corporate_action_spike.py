"""Phase 3 Step 3.5 — corporate_action_spike audit on rule_019.

Investigates whether rule_019's edge depends on trades with anomalously large
returns suggestive of corporate actions (splits, mergers, dividends) or
data glitches. enriched_signals lacks per-day return data, so thresholds
operate on aggregate pnl_pct (entry→exit return in percent units).

Thresholds (pnl_pct in PERCENT units):
  HARD:           pnl_pct >  30.0    (almost certainly corp action / major event)
  SOFT:    20.0 <= pnl_pct <= 30.0   (review needed)
  NEGATIVE:       pnl_pct < -20.0    (negative spikes — data hygiene flag)

Verdict:
  PASS:      hard_pct_of_total < 2.0% AND wr_change_pp < 1.0
  AMBIGUOUS: hard_pct_of_total < 5.0% AND wr_change_pp < 3.0
  FAIL:      otherwise

Output: lab/factory/oos_validation/output/corporate_action_spike_report.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from walkforward import (  # noqa: E402
    walkforward, build_windows, aggregate_stability, load_data, matches_rule, RULES_PATH,
)

# ============================================================
# Constants
# ============================================================
RULE_ID = "rule_019_bear_uptri_hot_refinement"

RECORDED_MEAN_LIFT_PP = 17.2208
RECORDED_PCT_POSITIVE = 0.7826
TOL_LIFT_PP = 0.5
TOL_POSITIVE = 0.02

# pnl_pct in PERCENT units in enriched_signals (e.g., -3.48 = -3.48%)
HARD_THRESHOLD_PCT = 30.0
SOFT_LOWER_PCT = 20.0
SOFT_UPPER_PCT = 30.0
NEGATIVE_THRESHOLD_PCT = -20.0

# Verdict thresholds
PASS_HARD_PCT_LIMIT = 2.0
PASS_WR_CHANGE_PP_LIMIT = 1.0
AMBIG_HARD_PCT_LIMIT = 5.0
AMBIG_WR_CHANGE_PP_LIMIT = 3.0

OUTPUT_DIR = _HERE / "output"
OUTPUT_FILE = OUTPUT_DIR / "corporate_action_spike_report.json"


# ============================================================
# Format helpers
# ============================================================
def _fmt_pp(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.4f}pp"


def _fmt_dec(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val):.6f}"


def _fmt_pct(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "NaN"
    return f"{float(val) * 100:.2f}%"


# ============================================================
# Loaders
# ============================================================
def load_rule_019() -> dict:
    rules = json.loads(RULES_PATH.read_text())["rules"]
    for r in rules:
        if r["id"] == RULE_ID:
            return r
    raise ValueError(f"{RULE_ID} not found in {RULES_PATH}")


# ============================================================
# Trade record builder
# ============================================================
def build_trade_records(df_subset: pd.DataFrame) -> list[dict]:
    """Convert filtered rule_019 match rows into JSON-friendly trade records."""
    records = []
    for _, row in df_subset.iterrows():
        pnl = row.get("pnl_pct")
        ed = row.get("exit_day")
        per_day = (
            float(pnl) / float(ed)
            if (pnl is not None and not pd.isna(pnl)
                and ed is not None and not pd.isna(ed) and float(ed) != 0)
            else None
        )
        won = row.get("won")
        records.append({
            "symbol": str(row.get("symbol")),
            "scan_date": str(row.get("scan_date")),
            "regime": str(row.get("regime")),
            "sub_regime": str(row.get("sub_regime")) if not pd.isna(row.get("sub_regime")) else None,
            "pnl_pct": float(pnl) if not pd.isna(pnl) else None,
            "exit_day": int(ed) if not pd.isna(ed) else None,
            "pnl_per_day": float(per_day) if per_day is not None else None,
            "outcome": str(row.get("outcome")),
            "won": int(won) if not pd.isna(won) else None,
            "entry_price": float(row.get("entry_price")) if not pd.isna(row.get("entry_price")) else None,
            "exit_price": float(row.get("exit_price")) if not pd.isna(row.get("exit_price")) else None,
        })
    return records


def _category_stats(df_subset: pd.DataFrame, total_pnl_resolved: int, label: str) -> dict:
    n = int(len(df_subset))
    pct_of_total = (n / total_pnl_resolved * 100) if total_pnl_resolved > 0 else None
    won_subset = df_subset[df_subset["won"].notna()]
    n_won_resolved = int(len(won_subset))
    wr_within = float(won_subset["won"].mean()) if n_won_resolved > 0 else None
    return {
        "label": label,
        "n_trades": n,
        "pct_of_total": pct_of_total,
        "n_won_resolved_in_subset": n_won_resolved,
        "win_rate_within_subset": wr_within,
    }


# ============================================================
# Walk-forward helper (mirrors prior steps)
# ============================================================
def run_walkforward_for_rule(rule: dict, df: pd.DataFrame, windows: list) -> dict:
    results = walkforward(rule, df, windows)
    return aggregate_stability(rule, results)


# ============================================================
# Verdict
# ============================================================
def make_verdict(hard_pct_of_total: float, wr_change_pp: float) -> dict:
    if hard_pct_of_total is None or wr_change_pp is None:
        return {
            "decision": "AMBIGUOUS",
            "rationale": "insufficient data — hard_pct_of_total or wr_change_pp is None",
        }

    abs_wr_change = abs(wr_change_pp)
    if hard_pct_of_total < PASS_HARD_PCT_LIMIT and abs_wr_change < PASS_WR_CHANGE_PP_LIMIT:
        return {
            "decision": "PASS",
            "rationale": (
                f"hard_pct_of_total {hard_pct_of_total:.2f}% < {PASS_HARD_PCT_LIMIT}% "
                f"AND |wr_change_pp| {abs_wr_change:.2f}pp < {PASS_WR_CHANGE_PP_LIMIT}pp "
                f"— edge robust to corp-action contamination"
            ),
        }
    if hard_pct_of_total < AMBIG_HARD_PCT_LIMIT and abs_wr_change < AMBIG_WR_CHANGE_PP_LIMIT:
        return {
            "decision": "AMBIGUOUS",
            "rationale": (
                f"hard_pct_of_total {hard_pct_of_total:.2f}% (between {PASS_HARD_PCT_LIMIT}% "
                f"and {AMBIG_HARD_PCT_LIMIT}%) and |wr_change_pp| {abs_wr_change:.2f}pp "
                f"(between {PASS_WR_CHANGE_PP_LIMIT} and {AMBIG_WR_CHANGE_PP_LIMIT}) "
                f"— material but not catastrophic; surface for review"
            ),
        }
    return {
        "decision": "FAIL",
        "rationale": (
            f"hard_pct_of_total {hard_pct_of_total:.2f}% >= {AMBIG_HARD_PCT_LIMIT}% "
            f"OR |wr_change_pp| {abs_wr_change:.2f}pp >= {AMBIG_WR_CHANGE_PP_LIMIT}pp "
            f"— significant corp-action contamination"
        ),
    }


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print(f"corporate_action_spike audit on {RULE_ID}")
    print("=" * 60)
    t_total = time.time()

    print("\nLoading data + rule + windows...")
    df_full = load_data()
    rule_019 = load_rule_019()
    windows = build_windows(df_full)
    print(f"  enriched_signals: {len(df_full):,} rows")
    print(f"  windows: {len(windows)}")

    # --- Sanity check
    print("\nSANITY CHECK: reproduce baseline on REAL data")
    real_agg = run_walkforward_for_rule(rule_019, df_full, windows)
    real_lift = real_agg.get("mean_lift")
    real_pct_positive = real_agg.get("pct_positive_windows")
    real_lift_pp = (real_lift * 100) if real_lift is not None else None
    print(f"  reproduced mean_lift: {_fmt_pp(real_lift_pp)} (recorded: {RECORDED_MEAN_LIFT_PP}pp; tol ±{TOL_LIFT_PP}pp)")
    print(f"  reproduced pct_positive: {_fmt_dec(real_pct_positive)} (recorded: {RECORDED_PCT_POSITIVE}; tol ±{TOL_POSITIVE})")
    reproduction_ok = (
        real_lift_pp is not None
        and abs(real_lift_pp - RECORDED_MEAN_LIFT_PP) <= TOL_LIFT_PP
        and real_pct_positive is not None
        and abs(real_pct_positive - RECORDED_PCT_POSITIVE) <= TOL_POSITIVE
    )
    if not reproduction_ok:
        print("\n  ✗ baseline reproduction FAILED — STOPPING")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps({
            "rule_id": RULE_ID,
            "baseline": {"reproduction_ok": False},
            "skipped_reason": "baseline reproduction failed",
        }, indent=2))
        sys.exit(1)
    print("  ✓ baseline reproduced within tolerance")

    # --- Identify rule_019 matches
    print("\nIdentifying rule_019 matches (df.apply)...")
    t0 = time.time()
    match_mask = df_full.apply(lambda row: matches_rule(row, rule_019), axis=1)
    df_matches = df_full[match_mask].copy()
    print(f"  rule_019 matches total: {len(df_matches):,} ({time.time()-t0:.1f}s)")

    df_pnl = df_matches[df_matches["pnl_pct"].notna()].copy()
    df_won = df_matches[df_matches["won"].notna()].copy()
    print(f"  pnl-resolved matches:   {len(df_pnl):,}")
    print(f"  won-resolved matches:   {len(df_won):,}")

    # --- Spike categorization
    pnl = df_pnl["pnl_pct"]
    hard_mask_local = pnl > HARD_THRESHOLD_PCT
    soft_mask_local = (pnl >= SOFT_LOWER_PCT) & (pnl <= SOFT_UPPER_PCT)
    neg_mask_local = pnl < NEGATIVE_THRESHOLD_PCT

    df_hard = df_pnl[hard_mask_local].copy()
    df_soft = df_pnl[soft_mask_local].copy()
    df_neg = df_pnl[neg_mask_local].copy()

    total_pnl_resolved = int(len(df_pnl))
    hard_stats = _category_stats(df_hard, total_pnl_resolved, "hard_threshold (pnl_pct > 30)")
    soft_stats = _category_stats(df_soft, total_pnl_resolved, "soft_threshold (20 <= pnl_pct <= 30)")
    neg_stats = _category_stats(df_neg, total_pnl_resolved, "negative_spike (pnl_pct < -20)")

    print("\nSPIKE CATEGORIES")
    for st in (hard_stats, soft_stats, neg_stats):
        wr_s = f"{st['win_rate_within_subset']:.4f}" if st["win_rate_within_subset"] is not None else "NaN"
        pct_s = f"{st['pct_of_total']:.2f}%" if st["pct_of_total"] is not None else "NaN"
        print(
            f"  {st['label']:<48} n={st['n_trades']:>4}  "
            f"pct={pct_s:>7}  won_resolved={st['n_won_resolved_in_subset']:>4}  "
            f"wr_within={wr_s}"
        )

    # --- Edge impact (WR-based)
    baseline_won = df_won["won"]
    baseline_wr = float(baseline_won.mean()) if len(baseline_won) > 0 else None

    # Clean = drop hard-threshold trades from won-resolved
    hard_match_idx = df_hard.index
    df_won_clean = df_won.drop(index=hard_match_idx, errors="ignore")
    clean_wr = float(df_won_clean["won"].mean()) if len(df_won_clean) > 0 else None

    if baseline_wr is not None and clean_wr is not None:
        wr_change_pp = (baseline_wr - clean_wr) * 100
    else:
        wr_change_pp = None

    print("\nEDGE IMPACT — WR-based")
    print(f"  baseline_wr  (won.sum() / n_won_resolved):           {_fmt_dec(baseline_wr)}")
    print(f"  clean_wr     (excluding hard-threshold trades):       {_fmt_dec(clean_wr)}")
    print(f"  wr_change_pp (baseline - clean, in pp):               {_fmt_dec(wr_change_pp)}")

    # --- Edge impact (Lift-based, secondary cross-check)
    print("\nEDGE IMPACT — Lift-based (drop hard-threshold rule_019 rows from df, re-run walkforward)")
    drop_idx = df_hard.index  # global df index of hard-threshold rule_019 matches
    df_clean = df_full.drop(index=drop_idx).copy()
    clean_agg = run_walkforward_for_rule(rule_019, df_clean, windows)
    clean_lift = clean_agg.get("mean_lift")
    clean_lift_pp = (clean_lift * 100) if clean_lift is not None else None
    if real_lift_pp is not None and clean_lift_pp is not None:
        lift_change_pp = real_lift_pp - clean_lift_pp
    else:
        lift_change_pp = None
    print(f"  baseline_lift_pp:        {_fmt_pp(real_lift_pp)}")
    print(f"  clean_lift_pp:           {_fmt_pp(clean_lift_pp)}")
    print(f"  lift_change_pp:          {_fmt_pp(lift_change_pp)}")

    # --- Verdict
    verdict = make_verdict(hard_stats["pct_of_total"], wr_change_pp)
    print(f"\nVERDICT: {verdict['decision']} — {verdict['rationale']}")

    # --- Trade lists
    hard_records = build_trade_records(df_hard.sort_values("pnl_pct", ascending=False))
    soft_records_first20 = build_trade_records(df_soft.sort_values("pnl_pct", ascending=False).head(20))
    neg_records = build_trade_records(df_neg.sort_values("pnl_pct", ascending=True))

    # --- Print hard-threshold list (always, all trades)
    print(f"\nHARD-THRESHOLD TRADES (n={len(hard_records)})")
    if hard_records:
        for r in hard_records:
            print(
                f"  {r['symbol']:<14} {r['scan_date']}  "
                f"pnl={r['pnl_pct']:+.2f}%  exit_day={r['exit_day']}  "
                f"per_day={r['pnl_per_day']:+.2f}%  "
                f"outcome={r['outcome']:<11}  won={r['won']}"
            )
    else:
        print("  (none)")

    # --- Print first 20 soft-threshold
    print(f"\nSOFT-THRESHOLD TRADES (showing first 20 of {soft_stats['n_trades']}, sorted desc by pnl_pct)")
    if soft_records_first20:
        for r in soft_records_first20:
            print(
                f"  {r['symbol']:<14} {r['scan_date']}  "
                f"pnl={r['pnl_pct']:+.2f}%  exit_day={r['exit_day']}  "
                f"per_day={r['pnl_per_day']:+.2f}%  "
                f"outcome={r['outcome']:<11}  won={r['won']}"
            )
    else:
        print("  (none)")

    # --- Print negative spikes (always, all)
    print(f"\nNEGATIVE-SPIKE TRADES (n={len(neg_records)})")
    if neg_records:
        for r in neg_records:
            print(
                f"  {r['symbol']:<14} {r['scan_date']}  "
                f"pnl={r['pnl_pct']:+.2f}%  exit_day={r['exit_day']}  "
                f"per_day={r['pnl_per_day']:+.2f}%  "
                f"outcome={r['outcome']:<11}  won={r['won']}"
            )
    else:
        print("  (none)")

    # --- Persist
    elapsed = round(time.time() - t_total, 2)
    out = {
        "rule_id": RULE_ID,
        "thresholds": {
            "hard_pct": HARD_THRESHOLD_PCT,
            "soft_lower_pct": SOFT_LOWER_PCT,
            "soft_upper_pct": SOFT_UPPER_PCT,
            "negative_pct": NEGATIVE_THRESHOLD_PCT,
            "pnl_pct_units": "percent (e.g., 30.0 means a 30% return)",
        },
        "verdict_thresholds": {
            "pass_hard_pct_limit": PASS_HARD_PCT_LIMIT,
            "pass_wr_change_pp_limit": PASS_WR_CHANGE_PP_LIMIT,
            "ambig_hard_pct_limit": AMBIG_HARD_PCT_LIMIT,
            "ambig_wr_change_pp_limit": AMBIG_WR_CHANGE_PP_LIMIT,
        },
        "totals": {
            "rule_019_matches": int(len(df_matches)),
            "pnl_resolved": int(len(df_pnl)),
            "won_resolved": int(len(df_won)),
        },
        "baseline": {
            "recorded_mean_lift_pp": RECORDED_MEAN_LIFT_PP,
            "recorded_pct_positive": RECORDED_PCT_POSITIVE,
            "reproduced_mean_lift": real_lift,
            "reproduced_mean_lift_pp": real_lift_pp,
            "reproduced_pct_positive": real_pct_positive,
            "reproduction_ok": True,
        },
        "spike_categories": {
            "hard_threshold": {**hard_stats, "trades": hard_records},
            "soft_threshold": {**soft_stats, "first_20_trades": soft_records_first20},
            "negative_spike": {**neg_stats, "trades": neg_records},
        },
        "edge_impact": {
            "wr_based": {
                "baseline_wr": baseline_wr,
                "clean_wr_excluding_hard": clean_wr,
                "wr_change_pp": wr_change_pp,
            },
            "lift_based": {
                "baseline_lift": real_lift,
                "baseline_lift_pp": real_lift_pp,
                "clean_lift_excluding_hard": clean_lift,
                "clean_lift_pp_excluding_hard": clean_lift_pp,
                "lift_change_pp": lift_change_pp,
            },
        },
        "verdict": verdict,
        "elapsed_seconds": elapsed,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total elapsed: {elapsed}s")


if __name__ == "__main__":
    main()
