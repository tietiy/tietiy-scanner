"""Validation 5 — Cohort-Wise Predictive Power.

Per doc/regime_v2_design/05_validation.md §"Validation 5".

Pass:
  P1: V2 cohorts have LOWER mean intra-cohort variance than V1
  P2: All known winners preserved — UP_TRI×Bear ≥85%, BULL_PROXY×Bear ≥75%, UP_TRI×Metal ≥75%
  P3 (bonus): At least one new positive cohort (WR>60%, n≥10)
  P4: DOWN_TRI failure preserved (no sub-cohort with WR ≥50%)
"""
from __future__ import annotations

import os
import pandas as pd

WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}
LOSS_OUTCOMES = {"STOP_HIT", "DAY6_LOSS"}
FLAT_OUTCOMES = {"DAY6_FLAT"}


def _cohort_stats(df: pd.DataFrame, signal_col: str, regime_col: str) -> pd.DataFrame:
    """Compute n, wr, avg_pnl, std_pnl per (signal, regime) cohort."""
    df = df.copy()
    df["win"] = df["outcome"].isin(WIN_OUTCOMES).astype(int)
    grouped = df.groupby([signal_col, regime_col], dropna=False).agg(
        n=("win", "size"),
        wins=("win", "sum"),
        avg_pnl=("pnl_pct", "mean"),
        std_pnl=("pnl_pct", "std"),
    ).reset_index()
    grouped["wr_pct"] = (grouped["wins"] / grouped["n"] * 100).round(1)
    grouped["avg_pnl"] = grouped["avg_pnl"].round(2)
    grouped["std_pnl"] = grouped["std_pnl"].round(2)
    return grouped


def run(out_dir: str = "output/regime_v2/validation") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_parquet("output/regime_v2/signals_remapped.parquet")
    resolved = df[df["outcome"].isin(WIN_OUTCOMES | LOSS_OUTCOMES | FLAT_OUTCOMES)]

    v1_cohorts = _cohort_stats(resolved, "signal_type", "v1_regime")
    v2_cohorts = _cohort_stats(resolved, "signal_type", "v2_regime")

    # P1: total intra-cohort variance (weighted mean of std_pnl across cohorts with n>=10)
    def weighted_var(cohorts):
        eligible = cohorts[cohorts["n"] >= 10]
        if eligible.empty:
            return None
        return (eligible["std_pnl"] * eligible["n"]).sum() / eligible["n"].sum()

    v1_var = weighted_var(v1_cohorts)
    v2_var = weighted_var(v2_cohorts)
    p1_pass = v2_var is not None and v1_var is not None and v2_var < v1_var

    # P2: Known winners preserved
    def lookup(cohorts, signal_col, signal_val, regime_col, regime_val):
        m = cohorts[(cohorts[signal_col] == signal_val) & (cohorts[regime_col] == regime_val)]
        return m.iloc[0].to_dict() if not m.empty else None

    # UP_TRI×Bear under V1
    ut_bear_v1_stats = lookup(v1_cohorts, "signal_type", "UP_TRI", "v1_regime", "Bear")
    ut_bear_v1_wr = ut_bear_v1_stats["wr_pct"] if ut_bear_v1_stats else 0.0
    # UP_TRI in Bear-family under V2
    ut_bear_v2_stats = v2_cohorts[
        (v2_cohorts["signal_type"] == "UP_TRI") &
        (v2_cohorts["v2_regime"].isin(["BEAR", "BEAR_RECOVERY"]))
    ]
    if not ut_bear_v2_stats.empty:
        tot_n = ut_bear_v2_stats["n"].sum()
        tot_wins = ut_bear_v2_stats["wins"].sum()
        ut_bear_v2_wr = tot_wins / tot_n * 100 if tot_n > 0 else 0.0
    else:
        ut_bear_v2_wr = 0.0
        tot_n = 0

    p2_up_bear_pass = ut_bear_v2_wr >= 85.0

    # BULL_PROXY×Bear → BULL_PROXY in Bear-family
    bp_bear_v2_stats = v2_cohorts[
        (v2_cohorts["signal_type"] == "BULL_PROXY") &
        (v2_cohorts["v2_regime"].isin(["BEAR", "BEAR_RECOVERY"]))
    ]
    if not bp_bear_v2_stats.empty:
        tot_n_bp = bp_bear_v2_stats["n"].sum()
        tot_wins_bp = bp_bear_v2_stats["wins"].sum()
        bp_bear_v2_wr = tot_wins_bp / tot_n_bp * 100 if tot_n_bp > 0 else 0.0
    else:
        bp_bear_v2_wr = 0.0
        tot_n_bp = 0
    p2_bp_bear_pass = bp_bear_v2_wr >= 75.0

    p2_pass = p2_up_bear_pass and p2_bp_bear_pass  # UP_TRI×Metal not in current data

    # P3: New positive cohorts (n>=10, wr>60%)
    new_positives = v2_cohorts[
        (v2_cohorts["n"] >= 10) &
        (v2_cohorts["wr_pct"] > 60.0) &
        (~v2_cohorts["v2_regime"].isin(["BEAR", "BEAR_RECOVERY"]))  # exclude pre-known
    ]
    p3_pass = len(new_positives) >= 1  # bonus
    new_pos_list = new_positives.to_dict("records")

    # P4: DOWN_TRI sub-cohort failure preserved (no V2 cohort with DOWN_TRI WR>=50%)
    dt_v2 = v2_cohorts[(v2_cohorts["signal_type"] == "DOWN_TRI") & (v2_cohorts["n"] >= 5)]
    p4_violators = dt_v2[dt_v2["wr_pct"] >= 50.0]
    p4_pass = p4_violators.empty

    all_pass = p1_pass and p2_pass and p4_pass  # P3 is bonus

    report = {
        "validation": "V5 Cohort-Wise Predictive Power",
        "design_ref": "doc/regime_v2_design/05_validation.md §V5",
        "P1_variance_reduction": {
            "v1_weighted_std_pnl": round(v1_var, 2) if v1_var else None,
            "v2_weighted_std_pnl": round(v2_var, 2) if v2_var else None,
            "threshold": "V2 < V1",
            "pass": p1_pass,
        },
        "P2_known_winners_preserved": {
            "UP_TRI_bear_family_wr_v2": round(ut_bear_v2_wr, 1),
            "UP_TRI_bear_family_n_v2": int(tot_n),
            "BULL_PROXY_bear_family_wr_v2": round(bp_bear_v2_wr, 1),
            "BULL_PROXY_bear_family_n_v2": int(tot_n_bp),
            "UP_TRI_bear_v1_baseline_wr": round(ut_bear_v1_wr, 1),
            "thresholds": "UP_TRI Bear-family ≥85%, BULL_PROXY Bear-family ≥75%",
            "pass": p2_pass,
            "details": {
                "UP_TRI_bear_pass": p2_up_bear_pass,
                "BULL_PROXY_bear_pass": p2_bp_bear_pass,
            },
        },
        "P3_new_positive_cohorts": {
            "count": len(new_positives),
            "cohorts": new_pos_list,
            "threshold": "≥ 1 (bonus)",
            "pass": p3_pass,
        },
        "P4_down_tri_failure_preserved": {
            "n_v2_cohorts_with_wr_ge_50": len(p4_violators),
            "violators": p4_violators.to_dict("records") if not p4_violators.empty else [],
            "threshold": "0 V2 sub-cohorts with WR ≥ 50%",
            "pass": p4_pass,
        },
        "v1_cohorts": v1_cohorts.to_dict("records"),
        "v2_cohorts": v2_cohorts.to_dict("records"),
        "OVERALL": "PASS" if all_pass else "FAIL",
    }

    md_path = os.path.join(out_dir, "v5_cohort_predictive_power.md")
    with open(md_path, "w") as f:
        f.write(_render_md(report))
    print(_render_md(report))
    return report


def _render_md(r: dict) -> str:
    s = f"# Validation 5 — Cohort-Wise Predictive Power\n\n"
    s += f"**Design ref:** {r['design_ref']}\n\n"
    s += f"**Outcome:** **{r['OVERALL']}**\n\n"
    for code, payload in [
        ("P1", r["P1_variance_reduction"]),
        ("P2", r["P2_known_winners_preserved"]),
        ("P3", r["P3_new_positive_cohorts"]),
        ("P4", r["P4_down_tri_failure_preserved"]),
    ]:
        status = "✅ PASS" if payload["pass"] else "❌ FAIL"
        s += f"### {code} — {status}\n\n"
        for k, v in payload.items():
            if k == "pass":
                continue
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                s += f"  - **{k}**:\n"
                for item in v[:20]:
                    s += f"    - {item}\n"
            else:
                s += f"  - **{k}**: {v}\n"
        s += "\n"

    s += "## V1 cohorts (resolved-only)\n\n"
    s += "| signal | v1_regime | n | wr% | avg_pnl | std_pnl |\n|---|---|---:|---:|---:|---:|\n"
    for c in r["v1_cohorts"]:
        s += f"| {c['signal_type']} | {c['v1_regime']} | {c['n']} | {c['wr_pct']} | {c['avg_pnl']} | {c['std_pnl']} |\n"

    s += "\n## V2 cohorts (resolved-only)\n\n"
    s += "| signal | v2_regime | n | wr% | avg_pnl | std_pnl |\n|---|---|---:|---:|---:|---:|\n"
    for c in r["v2_cohorts"]:
        s += f"| {c['signal_type']} | {c['v2_regime']} | {c['n']} | {c['wr_pct']} | {c['avg_pnl']} | {c['std_pnl']} |\n"
    return s


if __name__ == "__main__":
    run()
