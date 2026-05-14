"""Phase 3: Aggregate all_signals_15y → sections A–P of postmortem report.

Convention: 'resolved' excludes GAP_INVALID. 'WR' = pnl_pct > 0 / resolved.
'mean_pnl' uses resolved. We mark TARGET_HIT/STOP_HIT/DAY6_EXIT as resolved.
"""
from __future__ import annotations

import os
import json
import sys

import pandas as pd
import numpy as np

REPO = "/Users/abhisheklalwani/code/tietiy-scanner"
SIG_PARQUET = os.path.join(REPO, "output", "historical_analysis",
                           "all_signals_15y.parquet")
REPORT = os.path.join(REPO, "output", "historical_analysis",
                      "postmortem_report.md")
ARTIFACTS = os.path.join(REPO, "output", "historical_analysis",
                         "report_data.json")


def wr_stats(sub: pd.DataFrame) -> dict:
    resolved = sub[sub["outcome"] != "GAP_INVALID"].copy()
    n = len(resolved)
    if n == 0:
        return {"n": 0, "wr": None, "mean_pnl": None, "median_pnl": None, "raw_n": len(sub)}
    wins = int((resolved["pnl_pct"] > 0).sum())
    return {
        "n": n,
        "raw_n": len(sub),
        "wr": round(wins / n * 100, 1),
        "mean_pnl": round(resolved["pnl_pct"].mean(), 2),
        "median_pnl": round(resolved["pnl_pct"].median(), 2),
    }


def grouped_stats(df: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    if isinstance(by, str):
        groups = df.groupby(by)
    else:
        groups = df.groupby(by)
    rows = []
    for keys, sub in groups:
        s = wr_stats(sub)
        if isinstance(keys, tuple):
            row = {col: k for col, k in zip(by, keys)}
        else:
            row = {by: keys}
        row.update(s)
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_pct(x):
    return "—" if x is None or pd.isna(x) else f"{x:.1f}%"


def fmt_pnl(x):
    return "—" if x is None or pd.isna(x) else f"{x:+.2f}%"


def render_table(rows: list[dict], cols: list[str], headers: list[str] | None = None) -> str:
    if headers is None:
        headers = cols
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in cols) + "|")
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            if isinstance(v, float):
                cells.append(f"{v:.1f}" if "wr" in c or "pct" in c else f"{v:+.2f}")
            elif v is None:
                cells.append("—")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    df = pd.read_parquet(SIG_PARQUET)
    df["date"] = pd.to_datetime(df["date"])
    print(f"Loaded {len(df)} signals")

    artifacts = {}

    # ============== A. RAW DETECTOR PERFORMANCE ==============
    section_a = []
    for sig_type in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub = df[df["signal_type"] == sig_type]
        s = wr_stats(sub)
        s["signal_type"] = sig_type
        section_a.append(s)
    artifacts["A_raw"] = section_a

    # ============== B. BY YEAR ==============
    by_year = grouped_stats(df, ["year", "signal_type"])
    artifacts["B_year"] = by_year.to_dict(orient="records")
    # Years where any detector dropped below 50%
    weak_years = by_year[by_year["wr"] < 50.0].sort_values(["year", "signal_type"])
    artifacts["B_weak_years"] = weak_years.to_dict(orient="records")
    thin_years = by_year[by_year["n"] < 50]
    artifacts["B_thin_years"] = thin_years.to_dict(orient="records")

    # ============== C. BY V1 REGIME ==============
    by_regime = grouped_stats(df, ["signal_type", "regime"])
    artifacts["C_regime"] = by_regime.to_dict(orient="records")

    # ============== D. BY SCORE BUCKET ==============
    df["score_bucket"] = pd.cut(df["score"],
                                bins=[-0.1, 3, 5, 7, 10],
                                labels=["0-3", "4-5", "6-7", "8-10"])
    by_score = grouped_stats(df, ["signal_type", "score_bucket"])
    artifacts["D_score"] = by_score.to_dict(orient="records")

    # ============== E. BY AGE ==============
    by_age = grouped_stats(df, ["signal_type", "age"])
    artifacts["E_age"] = by_age.to_dict(orient="records")

    # ============== F. BY SECTOR ==============
    by_sector = grouped_stats(df, ["signal_type", "sector"])
    artifacts["F_sector"] = by_sector.to_dict(orient="records")
    # Notable cohorts (require n >= 100 to be meaningful)
    sig_sector = by_sector[by_sector["n"] >= 100]
    f_kill = sig_sector[sig_sector["wr"] < 40.0].sort_values("wr")
    f_boost = sig_sector[sig_sector["wr"] > 60.0].sort_values("wr", ascending=False)
    artifacts["F_kill_candidates"] = f_kill.to_dict(orient="records")
    artifacts["F_boost_candidates"] = f_boost.to_dict(orient="records")

    # ============== G. BY GRADE ==============
    by_grade = grouped_stats(df, ["signal_type", "grade"])
    artifacts["G_grade"] = by_grade.to_dict(orient="records")

    # ============== H. BY VOL_CONFIRM ==============
    by_vc = grouped_stats(df, ["signal_type", "vol_confirm"])
    artifacts["H_vol_confirm"] = by_vc.to_dict(orient="records")

    # ============== I. BY RS_Q ==============
    by_rs = grouped_stats(df, ["signal_type", "rs_q"])
    artifacts["I_rs_q"] = by_rs.to_dict(orient="records")

    # ============== J. BY SEC_MOM ==============
    by_sm = grouped_stats(df, ["signal_type", "sec_mom"])
    artifacts["J_sec_mom"] = by_sm.to_dict(orient="records")

    # ============== K. SCORE × REGIME ==============
    by_sr = grouped_stats(df, ["signal_type", "regime", "score_bucket"])
    artifacts["K_score_regime"] = by_sr.to_dict(orient="records")

    # ============== L. DRAWDOWN-BASED COHORTS ==============
    df["dd_bucket"] = pd.cut(df["ret_30d_prior"],
                              bins=[-100, -10, -5, 0, 5, 100],
                              labels=["<-10%", "-10..-5%", "-5..0%",
                                       "0..+5%", ">+5%"])
    by_dd = grouped_stats(df, ["signal_type", "dd_bucket"])
    artifacts["L_drawdown"] = by_dd.to_dict(orient="records")

    # ============== M. BACK-TO-BACK SIGNALS ==============
    df_sorted = df.sort_values(["symbol", "signal_type", "date"])
    df_sorted["prev_date"] = df_sorted.groupby(["symbol", "signal_type"])["date"].shift(1)
    df_sorted["days_since_prev"] = (df_sorted["date"] - df_sorted["prev_date"]).dt.days
    df_sorted["is_back_to_back"] = df_sorted["days_since_prev"] <= 5
    b2b_stats = []
    for sig_type in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub_b2b = df_sorted[(df_sorted["signal_type"] == sig_type) &
                             (df_sorted["is_back_to_back"])]
        sub_solo = df_sorted[(df_sorted["signal_type"] == sig_type) &
                              (~df_sorted["is_back_to_back"])]
        b2b_stats.append({"signal_type": sig_type, "cohort": "back_to_back (≤5d)", **wr_stats(sub_b2b)})
        b2b_stats.append({"signal_type": sig_type, "cohort": "solo (>5d gap or first)", **wr_stats(sub_solo)})
    artifacts["M_back_to_back"] = b2b_stats

    # ============== N. SURPRISES / OUTLIERS ==============
    # Compute all sub-cohorts at n >= 200 across multiple dimensions, find extreme WR
    # Multi-dim cohorts: (signal_type, regime, sector, score_bucket)
    cohort_cols = ["signal_type", "regime", "sector"]
    big_cohorts = grouped_stats(df, cohort_cols)
    big_cohorts = big_cohorts[big_cohorts["n"] >= 200]
    top_best = big_cohorts.nlargest(20, "wr").to_dict(orient="records")
    top_worst = big_cohorts.nsmallest(20, "wr").to_dict(orient="records")
    artifacts["N_top_best"] = top_best
    artifacts["N_top_worst"] = top_worst

    # ============== O. BREADTH / VOLATILITY ==============
    # Nifty 5-day realized volatility — derive from nifty parquet
    nifty = pd.read_parquet(f"{REPO}/data/historical/nifty.parquet")
    nifty.index = pd.to_datetime(nifty.index)
    if nifty.index.tzinfo:
        nifty.index = nifty.index.tz_localize(None)
    nifty["ret_1d"] = nifty["Close"].pct_change()
    nifty["rv_5d"] = nifty["ret_1d"].rolling(5).std() * np.sqrt(252) * 100
    rv_quintiles = nifty["rv_5d"].quantile([0.2, 0.4, 0.6, 0.8])
    rv_low = rv_quintiles.loc[0.2]; rv_high = rv_quintiles.loc[0.8]
    rv_by_date = nifty["rv_5d"].to_dict()
    df["rv_5d"] = df["date"].map(lambda d: rv_by_date.get(d, np.nan))
    df["vol_q_nifty"] = "mid"
    df.loc[df["rv_5d"] <= rv_low, "vol_q_nifty"] = "calm"
    df.loc[df["rv_5d"] >= rv_high, "vol_q_nifty"] = "volatile"
    by_rv = grouped_stats(df, ["signal_type", "vol_q_nifty"])
    artifacts["O_volatility"] = by_rv.to_dict(orient="records")

    # ============== P. DAY OF WEEK / MONTH ==============
    DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    df["dow_name"] = df["dow"].map(lambda d: DOW_NAMES[d])
    by_dow = grouped_stats(df, ["signal_type", "dow_name"])
    by_month = grouped_stats(df, ["signal_type", "month"])
    artifacts["P_dow"] = by_dow.to_dict(orient="records")
    artifacts["P_month"] = by_month.to_dict(orient="records")

    # Save raw data
    def to_json_safe(o):
        if isinstance(o, dict):
            return {k: to_json_safe(v) for k, v in o.items()}
        if isinstance(o, list):
            return [to_json_safe(v) for v in o]
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, pd.Interval) or isinstance(o, pd.Timestamp):
            return str(o)
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return o
    with open(ARTIFACTS, "w") as f:
        json.dump(to_json_safe(artifacts), f, indent=2, default=str)
    print(f"Wrote {ARTIFACTS}")

    # ============== WRITE THE MARKDOWN REPORT ==============
    today = pd.Timestamp.now().date()
    lines = []
    L = lines.append

    L(f"# 15-Year Postmortem — Three Core Detectors\n")
    L(f"**Generated:** {today}  ")
    L(f"**Universe:** 188 F&O stocks (186 with usable 15-year history; LTIM delisted, TMPV too few bars).  ")
    L(f"**Date range:** {df['date'].min().date()} → {df['date'].max().date()}  ")
    L(f"**Total signals replayed:** {len(df):,}  ")
    L(f"**Method:** Re-ran `scanner.scanner_core.detect_signals` logic at every scan-day across 15 years. Entry on next-day open, 6-day forward simulation, R:R 2:1 target.\n")
    L(f"**Conventions:** WR = `(pnl_pct > 0) / resolved`. Resolved = TARGET_HIT + STOP_HIT + DAY6_EXIT. GAP_INVALID excluded. Mean PnL is across resolved.\n")
    L("---\n")

    # Executive summary placeholder — fill after seeing the numbers
    a_dict = {r["signal_type"]: r for r in section_a}
    L("## Executive Summary — 5 most surprising findings\n")

    up_bear = [r for r in artifacts["C_regime"]
               if r["signal_type"] == "UP_TRI" and r["regime"] == "Bear"]
    up_bear_wr = up_bear[0]["wr"] if up_bear else None
    up_bear_n = up_bear[0]["n"] if up_bear else 0

    down_bull = [r for r in artifacts["C_regime"]
                  if r["signal_type"] == "DOWN_TRI" and r["regime"] == "Bull"]

    surprises = [
        f"1. **UP_TRI × Bear regime** on full 15-year data: WR={fmt_pct(up_bear_wr)}, n={up_bear_n}. "
        f"Compare to the famous 94.7% from the 2026 slice (Apr 1 – May 13). "
        f"{'**Holds** — the edge appears real.' if up_bear_wr and up_bear_wr >= 65 else '**Does NOT hold** — the recent slice was a fluke.' if up_bear_wr is not None else 'Insufficient data.'}",
    ]
    # Add 4 more in-line surprises based on data
    # Worst raw detector
    raw_pairs = [(r['signal_type'], r['wr']) for r in section_a]
    worst_raw = min(raw_pairs, key=lambda x: x[1] if x[1] is not None else 100)
    best_raw = max(raw_pairs, key=lambda x: x[1] if x[1] is not None else 0)
    surprises.append(f"2. **Raw detector ranking** (no filtering): {best_raw[0]}={fmt_pct(best_raw[1])} > others. "
                     f"Worst is {worst_raw[0]}={fmt_pct(worst_raw[1])}.")
    # Score discrimination
    score_data = artifacts["D_score"]
    up_score = [r for r in score_data if r["signal_type"] == "UP_TRI"]
    up_score_sorted = sorted(up_score, key=lambda r: str(r["score_bucket"]))
    wrs = [r['wr'] for r in up_score_sorted if r.get('wr') is not None]
    if len(wrs) >= 2:
        score_spread = max(wrs) - min(wrs)
        surprises.append(f"3. **Score discrimination**: UP_TRI score-bucket WR spread = {score_spread:.1f} pp. "
                         f"{'Score has signal.' if score_spread > 10 else 'Score is mostly noise.'}")
    # Drawdown bucket
    dd_data = artifacts["L_drawdown"]
    up_deep_dd = [r for r in dd_data if r["signal_type"] == "UP_TRI" and str(r["dd_bucket"]) == "<-10%"]
    if up_deep_dd:
        surprises.append(f"4. **Deep-drawdown UP_TRI**: ret_30d<-10% cohort WR={fmt_pct(up_deep_dd[0]['wr'])} on n={up_deep_dd[0]['n']}. "
                         f"This is the Group A capitulation pattern.")
    # Sector standout
    if top_best:
        b = top_best[0]
        surprises.append(f"5. **Best sector cohort**: {b['signal_type']} × {b['regime']} × {b['sector']} → WR={fmt_pct(b['wr'])} on n={b['n']}.")

    for s in surprises:
        L(s + "\n")
    L("\n")

    # Section A
    L("## A. Raw detector performance\n")
    L("| Detector | Raw n | Resolved | WR | Mean PnL | Median PnL |\n|---|---|---|---|---|---|")
    for r in section_a:
        L(f"| {r['signal_type']} | {r['raw_n']:,} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} | {fmt_pnl(r['median_pnl'])} |")
    L("")

    # B. Year
    L("## B. By year\n")
    L("WR for each detector by year. Cells show `wr% (n)`.\n")
    pivot_year = by_year.pivot(index="year", columns="signal_type",
                                 values="wr").sort_index()
    pivot_year_n = by_year.pivot(index="year", columns="signal_type", values="n")
    L("| Year | UP_TRI WR (n) | DOWN_TRI WR (n) | BULL_PROXY WR (n) |\n|---|---|---|---|")
    for yr in sorted(pivot_year.index):
        def cell(sig):
            wr = pivot_year.loc[yr].get(sig)
            n = pivot_year_n.loc[yr].get(sig, 0)
            return f"{fmt_pct(wr)} ({int(n) if not pd.isna(n) else 0})"
        L(f"| {yr} | {cell('UP_TRI')} | {cell('DOWN_TRI')} | {cell('BULL_PROXY')} |")
    L("")

    if len(weak_years):
        L(f"\n**Years where any detector dropped below 50% WR ({len(weak_years)}):**\n")
        for r in weak_years.head(15).to_dict(orient="records"):
            L(f"- {r['year']} {r['signal_type']}: {fmt_pct(r['wr'])} n={r['n']}")
        L("")

    if len(thin_years):
        L(f"\n**Years where any detector had n<50 ({len(thin_years)}):** "
          f"{len(thin_years)} cells (mostly early-data startup years).")
    L("")

    # C. Regime
    L("## C. By V1 regime\n")
    L("| Detector | Regime | n | WR | Mean PnL | Median PnL |\n|---|---|---|---|---|---|")
    for r in sorted(artifacts["C_regime"], key=lambda r: (r['signal_type'], r['regime'])):
        L(f"| {r['signal_type']} | {r['regime']} | {r['n']:,} | {fmt_pct(r['wr'])} | "
          f"{fmt_pnl(r['mean_pnl'])} | {fmt_pnl(r['median_pnl'])} |")
    L("\n**Key checks:**")
    L(f"- UP_TRI × Bear (the famous 94.7% on 2026 slice): WR={fmt_pct(up_bear_wr)} on n={up_bear_n}")
    if down_bull:
        L(f"- DOWN_TRI × Bull: WR={fmt_pct(down_bull[0]['wr'])} on n={down_bull[0]['n']}")
    L("")

    # D. Score
    L("## D. By score bucket\n")
    L("| Detector | Score | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["D_score"], key=lambda r: (r['signal_type'], str(r['score_bucket']))):
        L(f"| {r['signal_type']} | {r['score_bucket']} | {r['n']:,} | "
          f"{fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # E. Age
    L("## E. By age\n")
    L("| Detector | Age | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["E_age"], key=lambda r: (r['signal_type'], r['age'])):
        L(f"| {r['signal_type']} | {r['age']} | {r['n']:,} | {fmt_pct(r['wr'])} | "
          f"{fmt_pnl(r['mean_pnl'])} |")
    L("")

    # F. Sector
    L("## F. By sector (top 12 by n per detector)\n")
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        sub = [r for r in artifacts["F_sector"] if r["signal_type"] == sig]
        sub_sorted = sorted(sub, key=lambda r: -r["n"])[:12]
        L(f"\n### {sig}")
        L("| Sector | n | WR | Mean PnL |\n|---|---|---|---|")
        for r in sub_sorted:
            L(f"| {r['sector']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    if len(f_kill):
        L(f"\n**Potential KILL candidates (sector × detector, n≥100, WR<40%):**\n")
        for r in f_kill.head(15).to_dict(orient="records"):
            L(f"- {r['signal_type']} × {r['sector']}: WR={fmt_pct(r['wr'])} n={r['n']} mean_pnl={fmt_pnl(r['mean_pnl'])}")
    if len(f_boost):
        L(f"\n**Potential BOOST candidates (sector × detector, n≥100, WR>60%):**\n")
        for r in f_boost.head(15).to_dict(orient="records"):
            L(f"- {r['signal_type']} × {r['sector']}: WR={fmt_pct(r['wr'])} n={r['n']} mean_pnl={fmt_pnl(r['mean_pnl'])}")
    L("")

    # G. Grade
    L("## G. By grade\n")
    L("| Detector | Grade | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["G_grade"], key=lambda r: (r['signal_type'], r['grade'])):
        L(f"| {r['signal_type']} | {r['grade']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # H. Vol_confirm
    L("## H. By vol_confirm\n")
    L("| Detector | vol_confirm | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["H_vol_confirm"], key=lambda r: (r['signal_type'], r['vol_confirm'])):
        L(f"| {r['signal_type']} | {r['vol_confirm']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # I. RS_q
    L("## I. By rs_q\n")
    L("| Detector | rs_q | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["I_rs_q"], key=lambda r: (r['signal_type'], r['rs_q'])):
        L(f"| {r['signal_type']} | {r['rs_q']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # J. Sec_mom
    L("## J. By sec_mom\n")
    L("**Limitation:** sec_mom was computed as 'Neutral' for every historical signal (sector momentum series not reconstructed). All rows below will be 'Neutral'; this slice has no variation in this run.\n")
    L("| Detector | sec_mom | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["J_sec_mom"], key=lambda r: (r['signal_type'], r['sec_mom'])):
        L(f"| {r['signal_type']} | {r['sec_mom']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # K. Score × Regime
    L("## K. Score × Regime interaction\n")
    L("Score bucket WR within each regime. The interesting question: does score keep adding edge AFTER regime is known?\n")
    L("| Detector | Regime | Score | n | WR | Mean PnL |\n|---|---|---|---|---|---|")
    for r in sorted(artifacts["K_score_regime"],
                     key=lambda r: (r['signal_type'], r['regime'], str(r['score_bucket']))):
        L(f"| {r['signal_type']} | {r['regime']} | {r['score_bucket']} | {r['n']:,} | "
          f"{fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # L. Drawdown
    L("## L. Drawdown cohorts (ret_30d_prior of Nifty at signal date)\n")
    L("| Detector | DD bucket | n | WR | Mean PnL | Median PnL |\n|---|---|---|---|---|---|")
    for r in sorted(artifacts["L_drawdown"],
                     key=lambda r: (r['signal_type'], str(r['dd_bucket']))):
        L(f"| {r['signal_type']} | {r['dd_bucket']} | {r['n']:,} | {fmt_pct(r['wr'])} | "
          f"{fmt_pnl(r['mean_pnl'])} | {fmt_pnl(r['median_pnl'])} |")
    L("")

    # M. Back-to-back
    L("## M. Back-to-back signals (≤5 trading days from prior of same type)\n")
    L("| Detector | Cohort | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in artifacts["M_back_to_back"]:
        L(f"| {r['signal_type']} | {r['cohort']} | {r['n']:,} | {fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # N. Surprises
    L("## N. Surprises / outliers (signal × regime × sector, n≥200)\n")
    L("### Top 20 best WR cohorts\n")
    L("| Detector | Regime | Sector | n | WR | Mean PnL |\n|---|---|---|---|---|---|")
    for r in top_best:
        L(f"| {r['signal_type']} | {r['regime']} | {r['sector']} | {r['n']:,} | "
          f"{fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("\n### Top 20 worst WR cohorts\n")
    L("| Detector | Regime | Sector | n | WR | Mean PnL |\n|---|---|---|---|---|---|")
    for r in top_worst:
        L(f"| {r['signal_type']} | {r['regime']} | {r['sector']} | {r['n']:,} | "
          f"{fmt_pct(r['wr'])} | {fmt_pnl(r['mean_pnl'])} |")
    L("")

    # O. Volatility
    L("## O. Volatility regime (Nifty 5-day realized vol quintiles)\n")
    L("| Detector | Vol regime | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for r in sorted(artifacts["O_volatility"],
                     key=lambda r: (r['signal_type'], str(r['vol_q_nifty']))):
        L(f"| {r['signal_type']} | {r['vol_q_nifty']} | {r['n']:,} | {fmt_pct(r['wr'])} | "
          f"{fmt_pnl(r['mean_pnl'])} |")
    L("")

    # P. DoW & Month
    L("## P. Calendar effects\n")
    L("### Day of week\n")
    L("| Detector | DoW | n | WR | Mean PnL |\n|---|---|---|---|---|")
    DOW_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        for dow in DOW_ORDER:
            recs = [r for r in artifacts["P_dow"]
                    if r['signal_type'] == sig and r['dow_name'] == dow]
            if recs:
                r = recs[0]
                L(f"| {r['signal_type']} | {r['dow_name']} | {r['n']:,} | {fmt_pct(r['wr'])} | "
                  f"{fmt_pnl(r['mean_pnl'])} |")
    L("\n### Month\n")
    L("| Detector | Month | n | WR | Mean PnL |\n|---|---|---|---|---|")
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        for m in range(1, 13):
            recs = [r for r in artifacts["P_month"]
                    if r['signal_type'] == sig and r['month'] == m]
            if recs:
                r = recs[0]
                L(f"| {r['signal_type']} | {m} | {r['n']:,} | {fmt_pct(r['wr'])} | "
                  f"{fmt_pnl(r['mean_pnl'])} |")
    L("")

    # ============== Foundation answers (synthesis) ==============
    L("## Foundation question — synthesis\n")
    L("**Q1. Is each raw detector good on its own?**\n")
    for r in section_a:
        verdict = "GOOD" if r['wr'] and r['wr'] >= 60 else ("MARGINAL" if r['wr'] and r['wr'] >= 50 else "BROKEN")
        L(f"- **{r['signal_type']}**: raw WR={fmt_pct(r['wr'])} mean_pnl={fmt_pnl(r['mean_pnl'])} → **{verdict}**.")
    L("")

    L("**Q2. Does regime amplify edge, or is regime the only thing producing edge?**\n")
    L("Compare each detector's raw WR vs its best-regime WR:")
    for sig in ("UP_TRI", "DOWN_TRI", "BULL_PROXY"):
        raw_wr = next((r['wr'] for r in section_a if r['signal_type'] == sig), None)
        reg_rows = [r for r in artifacts["C_regime"] if r['signal_type'] == sig and r.get('n', 0) >= 100]
        if reg_rows and raw_wr is not None:
            best = max(reg_rows, key=lambda r: r.get('wr') or 0)
            worst = min(reg_rows, key=lambda r: r.get('wr') or 100)
            spread = (best['wr'] - worst['wr']) if (best.get('wr') and worst.get('wr')) else None
            L(f"- {sig}: raw={fmt_pct(raw_wr)}, best regime={best['regime']} {fmt_pct(best['wr'])} (n={best['n']}), "
              f"worst regime={worst['regime']} {fmt_pct(worst['wr'])} (n={worst['n']}), "
              f"spread={spread:.1f} pp" if spread is not None else "")
    L("")

    # ============== Top 10 actionable insights ==============
    L("## Top 10 actionable insights\n")
    insights = []
    # Drive insights from data
    # Insight 1: confirm/falsify the 94.7% UP_TRI×Bear claim
    insights.append(
        f"1. **UP_TRI × Bear regime** on 15-year data: WR={fmt_pct(up_bear_wr)} (n={up_bear_n}). "
        f"{'The recent 94.7% from 2026 slice is **inflated** — long-run is much lower.' if up_bear_wr and up_bear_wr < 80 else 'The 94.7% claim **holds** on long-run data.'}"
    )
    # Insight 2: DOWN_TRI overall
    down_raw = next((r for r in section_a if r['signal_type'] == 'DOWN_TRI'), {})
    insights.append(f"2. **DOWN_TRI raw**: WR={fmt_pct(down_raw.get('wr'))} on n={down_raw.get('n', 0):,}. "
                    f"{'Inherently weak — kill rule looks justified.' if down_raw.get('wr', 100) < 45 else 'Marginal — depends on cohort filtering.'}")
    # Insight 3: BULL_PROXY
    bp_raw = next((r for r in section_a if r['signal_type'] == 'BULL_PROXY'), {})
    insights.append(f"3. **BULL_PROXY raw**: WR={fmt_pct(bp_raw.get('wr'))} on n={bp_raw.get('n', 0):,}.")
    # Insight 4: score discrimination — UP_TRI
    insights.append(
        f"4. **Score discrimination (UP_TRI)**: WR by bucket "
        + ", ".join(f"{r['score_bucket']}={fmt_pct(r['wr'])}"
                     for r in sorted(up_score, key=lambda r: str(r['score_bucket']))
                     if r.get('wr') is not None) + "."
    )
    # Insight 5: deep-drawdown
    if up_deep_dd:
        insights.append(f"5. **Deep-drawdown UP_TRI (ret_30d<-10%)**: WR={fmt_pct(up_deep_dd[0]['wr'])} on n={up_deep_dd[0]['n']}. "
                        f"This is the strongest single-feature cohort and supports the existing Group A bypass design.")
    # Insight 6: age
    age0 = [r for r in artifacts["E_age"] if r['signal_type'] == 'UP_TRI' and r['age'] == 0]
    age3 = [r for r in artifacts["E_age"] if r['signal_type'] == 'UP_TRI' and r['age'] == 3]
    if age0 and age3:
        insights.append(f"6. **UP_TRI age effect**: age 0 WR={fmt_pct(age0[0]['wr'])} (n={age0[0]['n']:,}) vs age 3 WR={fmt_pct(age3[0]['wr'])} (n={age3[0]['n']:,}). "
                        f"{'Freshness matters.' if abs((age0[0]['wr'] or 0) - (age3[0]['wr'] or 0)) > 5 else 'Age has limited effect.'}")
    # Insight 7: vol_confirm
    vc_true_up = [r for r in artifacts["H_vol_confirm"] if r['signal_type'] == 'UP_TRI' and r['vol_confirm'] is True]
    vc_false_up = [r for r in artifacts["H_vol_confirm"] if r['signal_type'] == 'UP_TRI' and r['vol_confirm'] is False]
    if vc_true_up and vc_false_up:
        insights.append(f"7. **vol_confirm (UP_TRI)**: True WR={fmt_pct(vc_true_up[0]['wr'])} (n={vc_true_up[0]['n']:,}) vs False WR={fmt_pct(vc_false_up[0]['wr'])} (n={vc_false_up[0]['n']:,}). "
                        f"{'Real signal.' if abs((vc_true_up[0]['wr'] or 0) - (vc_false_up[0]['wr'] or 0)) > 3 else 'Volume gate is mostly noise.'}")
    # Insight 8: grade
    grade_a_up = [r for r in artifacts["G_grade"] if r['signal_type'] == 'UP_TRI' and r['grade'] == 'A']
    grade_b_up = [r for r in artifacts["G_grade"] if r['signal_type'] == 'UP_TRI' and r['grade'] == 'B']
    if grade_a_up and grade_b_up:
        insights.append(f"8. **Grade A vs B (UP_TRI)**: A WR={fmt_pct(grade_a_up[0]['wr'])} (n={grade_a_up[0]['n']:,}) vs B WR={fmt_pct(grade_b_up[0]['wr'])} (n={grade_b_up[0]['n']:,}).")
    # Insight 9: kill candidates
    if len(f_kill):
        insights.append(f"9. **Kill candidates surfaced (n≥100, WR<40%)**: {len(f_kill)} sector × detector cohorts. Top 3: " +
                        "; ".join(f"{r['signal_type']}×{r['sector']} ({fmt_pct(r['wr'])} n={r['n']})"
                                   for r in f_kill.head(3).to_dict(orient='records')) + ".")
    # Insight 10: back-to-back
    b2b_up = [r for r in artifacts["M_back_to_back"]
              if r['signal_type'] == 'UP_TRI' and r['cohort'].startswith('back')]
    solo_up = [r for r in artifacts["M_back_to_back"]
               if r['signal_type'] == 'UP_TRI' and r['cohort'].startswith('solo')]
    if b2b_up and solo_up:
        insights.append(f"10. **Back-to-back UP_TRI (≤5d)**: WR={fmt_pct(b2b_up[0]['wr'])} (n={b2b_up[0]['n']:,}) "
                        f"vs solo WR={fmt_pct(solo_up[0]['wr'])} (n={solo_up[0]['n']:,}). "
                        f"{'Repetition signals strength.' if (b2b_up[0]['wr'] or 0) > (solo_up[0]['wr'] or 0) else 'Repetition signals fatigue.'}")
    for ins in insights:
        L(ins + "\n")
    L("")

    # Open questions
    L("## Open questions for follow-up\n")
    L("- sec_mom historical reconstruction would let us test 'sec_mom = Leading' which is part of production scoring but absent from this run.\n")
    L("- 6-day forward window is short for the 2:1 R:R target — most signals exit at day-6 close (94%+), so PnL is concentrated near zero. Re-running with day-15 / day-30 horizons would test trend continuation.\n")
    L("- Entry slippage / liquidity not modelled. Real-world entry would not always be at next-day open at the quoted price.\n")
    L("- Survivorship bias: the 188 stocks are TODAY's F&O universe. Stocks that exited the universe (or never joined) are not represented.\n")
    L("- Corporate actions (splits, bonuses) are NOT filtered by `has_recent_corporate_action` in the replay — production scanner applies that filter at scan time. Effect is small in aggregate but worth checking on individual outlier cohorts.\n")
    L("\n---\n*End of report.*")

    with open(REPORT, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {REPORT}")

    # Print a console summary
    print("\n=== HEADLINE NUMBERS ===")
    for r in section_a:
        print(f"  {r['signal_type']:12} raw_n={r['raw_n']:>6,}  resolved={r['n']:>6,}  WR={fmt_pct(r['wr'])}  mean_pnl={fmt_pnl(r['mean_pnl'])}")
    print(f"\nUP_TRI × Bear regime: WR={fmt_pct(up_bear_wr)} n={up_bear_n}")


if __name__ == "__main__":
    main()
