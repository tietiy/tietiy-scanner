"""
analyze_full — overnight stats report for signal_history.json.

Reads output/signal_history.json, computes 9 analytical sections, writes
a markdown report. Pure stdlib — no matplotlib, no pandas.

Sections:
  a. Overall WR + R-multiple aggregate
  b. WR by signal_type
  c. WR by score bucket
  d. WR by regime × signal_type
  e. WR by sector × signal_type (top 6 sectors)
  f. MAE/MFE distribution per outcome type
  g. Day-to-outcome distribution
  h. Best/worst single signals
  i. Pattern observations (n≥10, WR≥85% or WR≤30%)

Final: Top 3 actionable findings.

Run: .venv/bin/python scripts/analyze_full.py
Output: output/analysis_report_<date>.md
"""

import json
import os
import sys
from collections import defaultdict
from datetime import date


# ===================================================================
# Constants
# ===================================================================

WIN_OUTCOMES  = ("TARGET_HIT", "DAY6_WIN")
LOSS_OUTCOMES = ("STOP_HIT", "DAY6_LOSS")
FLAT_OUTCOMES = ("DAY6_FLAT",)
RESULT_FILTER = ("WON", "STOPPED", "EXITED")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(REPO, "output", "signal_history.json")


# ===================================================================
# Data loading
# ===================================================================

def load_resolved():
    """Load + filter resolved records. Returns (records, dropped_count)."""
    with open(HISTORY_PATH) as f:
        data = json.load(f)
    history = data.get("history") or []

    resolved = []
    dropped  = 0
    for r in history:
        if not isinstance(r, dict):
            dropped += 1
            continue
        outcome = r.get("outcome")
        result  = r.get("result")
        if outcome == "OPEN" or result == "PENDING":
            continue   # not a drop, just open
        if result not in RESULT_FILTER:
            dropped += 1
            continue
        if outcome not in (WIN_OUTCOMES + LOSS_OUTCOMES + FLAT_OUTCOMES):
            dropped += 1
            continue
        resolved.append(r)
    return resolved, dropped


def is_win(r):  return r.get("outcome") in WIN_OUTCOMES
def is_loss(r): return r.get("outcome") in LOSS_OUTCOMES
def is_flat(r): return r.get("outcome") in FLAT_OUTCOMES


def wr_pct(records):
    """Win rate as percentage. Returns None if empty."""
    if not records:
        return None
    n = len(records)
    wins = sum(1 for r in records if is_win(r))
    return round(wins / n * 100, 1)


def avg(values):
    """Mean of a list of numbers; ignores non-numeric."""
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return sum(nums) / len(nums)


def fmt(x, prec=2, suffix=""):
    """Format helper: '?' for None, else number with suffix."""
    if x is None:
        return "?"
    if isinstance(x, (int, float)):
        return f"{x:.{prec}f}{suffix}"
    return str(x)


def pct_str(wr):
    return f"{wr:.1f}%" if isinstance(wr, (int, float)) else "?"


def percentile(sorted_values, p):
    """p in [0, 100]. Linear interp."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


# ===================================================================
# Section a. Overall WR + R-multiple aggregate
# ===================================================================

def section_a(records):
    n = len(records)
    wins = sum(1 for r in records if is_win(r))
    losses = sum(1 for r in records if is_loss(r))
    flats = sum(1 for r in records if is_flat(r))
    wr = wr_pct(records)

    pnl_avg = avg([r.get("pnl_pct") for r in records])
    pnl_total = sum(r.get("pnl_pct") for r in records
                    if isinstance(r.get("pnl_pct"), (int, float)))
    r_mult_avg = avg([r.get("r_multiple") for r in records])

    out = []
    out.append("## a. Overall WR + R-multiple aggregate\n")
    out.append("| Metric | Value |")
    out.append("|---|---|")
    out.append(f"| Resolved signals (n) | {n} |")
    out.append(f"| Wins (TARGET_HIT + DAY6_WIN) | {wins} |")
    out.append(f"| Losses (STOP_HIT + DAY6_LOSS) | {losses} |")
    out.append(f"| Flat (DAY6_FLAT) | {flats} |")
    out.append(f"| Win rate | {pct_str(wr)} |")
    out.append(f"| Avg P&L per trade | {fmt(pnl_avg, 2, '%')} |")
    out.append(f"| Sum P&L (all trades) | {fmt(pnl_total, 1, '%')} |")
    out.append(f"| Avg R-multiple | {fmt(r_mult_avg, 2)} |")
    out.append("")
    obs = (
        f"**Observation:** {n} resolved trades. {wr}% WR with avg "
        f"{fmt(pnl_avg, 2, '%')} P&L per trade. R-multiple averages "
        f"{fmt(r_mult_avg, 2)}, "
        + (
            "below 1.5 target — sized correctly, edge in volume not magnitude."
            if isinstance(r_mult_avg, (int, float)) and r_mult_avg < 1.5
            else "near or above 1.5 target."
        )
    )
    out.append(obs)
    return "\n".join(out)


# ===================================================================
# Section b. WR by signal_type
# ===================================================================

def section_b(records):
    by_type = defaultdict(list)
    for r in records:
        sig = r.get("signal") or r.get("signal_type") or "?"
        by_type[sig].append(r)

    out = []
    out.append("## b. WR by signal_type\n")
    out.append("| Signal type | n | Wins | Losses | Flat | WR | Avg P&L |")
    out.append("|---|---|---|---|---|---|---|")
    rows = []
    for sig, recs in by_type.items():
        n = len(recs)
        w = sum(1 for r in recs if is_win(r))
        l = sum(1 for r in recs if is_loss(r))
        f = sum(1 for r in recs if is_flat(r))
        rows.append((n, sig, w, l, f, wr_pct(recs),
                     avg([r.get("pnl_pct") for r in recs])))
    rows.sort(key=lambda x: -x[0])
    for n, sig, w, l, f, wr, p in rows:
        out.append(
            f"| {sig} | {n} | {w} | {l} | {f} | "
            f"{pct_str(wr)} | {fmt(p, 2, '%')} |")
    out.append("")
    if rows:
        top = rows[0]
        out.append(
            f"**Observation:** {top[1]} dominates volume with n={top[0]}; "
            f"WR {pct_str(top[5])}.")
    return "\n".join(out)


# ===================================================================
# Section c. WR by score bucket
# ===================================================================

def section_c(records):
    buckets = {"3-4": [], "5-6": [], "7-8": [], "9-10": [], "other": []}
    for r in records:
        s = r.get("score")
        if not isinstance(s, (int, float)):
            buckets["other"].append(r)
            continue
        si = int(s)
        if   3 <= si <= 4:  buckets["3-4"].append(r)
        elif 5 <= si <= 6:  buckets["5-6"].append(r)
        elif 7 <= si <= 8:  buckets["7-8"].append(r)
        elif 9 <= si <= 10: buckets["9-10"].append(r)
        else:               buckets["other"].append(r)

    out = []
    out.append("## c. WR by score bucket\n")
    out.append("| Score bucket | n | WR | Avg P&L | Avg R-mult |")
    out.append("|---|---|---|---|---|")
    nonmono = []
    last_wr = None
    for label in ("3-4", "5-6", "7-8", "9-10", "other"):
        recs = buckets[label]
        if not recs and label == "other":
            continue
        n = len(recs)
        wr = wr_pct(recs)
        p  = avg([r.get("pnl_pct") for r in recs])
        rm = avg([r.get("r_multiple") for r in recs])
        out.append(
            f"| {label} | {n} | {pct_str(wr)} | "
            f"{fmt(p, 2, '%')} | {fmt(rm, 2)} |")
        if (label != "other" and last_wr is not None
                and isinstance(wr, (int, float))
                and wr < last_wr):
            nonmono.append((label, wr))
        if isinstance(wr, (int, float)) and label != "other":
            last_wr = wr
    out.append("")
    if nonmono:
        msg = ", ".join(f"bucket {b} ({pct_str(w)})" for b, w in nonmono)
        out.append(
            f"**Observation:** Score is non-monotonic with WR — {msg} "
            f"is below the prior bucket. Confirms SCR-01 hypothesis.")
    else:
        out.append(
            "**Observation:** Score correlates monotonically with WR "
            "across buckets.")
    return "\n".join(out)


# ===================================================================
# Section d. WR by regime × signal_type
# ===================================================================

def section_d(records):
    grid = defaultdict(lambda: defaultdict(list))
    regimes = set()
    sigs = set()
    for r in records:
        regime = r.get("regime") or "?"
        sig = r.get("signal") or r.get("signal_type") or "?"
        grid[regime][sig].append(r)
        regimes.add(regime)
        sigs.add(sig)

    sigs = sorted(sigs)
    regime_order = ["Bull", "Bear", "Choppy"]
    regimes_present = [r for r in regime_order if r in regimes] + \
        sorted(r for r in regimes if r not in regime_order)

    out = []
    out.append("## d. WR by regime × signal_type\n")
    out.append("| Regime \\ Signal | " + " | ".join(sigs) + " |")
    out.append("|---" + ("|---" * len(sigs)) + "|")
    standout = []
    for regime in regimes_present:
        cells = []
        for sig in sigs:
            recs = grid[regime][sig]
            if not recs:
                cells.append("—")
                continue
            n = len(recs)
            wr = wr_pct(recs)
            cells.append(f"{pct_str(wr)} (n={n})")
            if (isinstance(wr, (int, float)) and n >= 15
                    and (wr >= 85 or wr <= 30)):
                standout.append((regime, sig, wr, n))
        out.append(f"| **{regime}** | " + " | ".join(cells) + " |")
    out.append("")
    if standout:
        bits = "; ".join(
            f"{regime} × {sig} = {pct_str(wr)} (n={n})"
            for regime, sig, wr, n in standout)
        out.append(
            f"**Observation:** Strong regime × signal cells: {bits}.")
    else:
        out.append(
            "**Observation:** No single regime × signal cell hits "
            "WR ≥85% or ≤30% with n ≥15.")
    return "\n".join(out)


# ===================================================================
# Section e. WR by sector × signal_type (top 6 sectors)
# ===================================================================

def section_e(records):
    sector_count = defaultdict(int)
    for r in records:
        sec = r.get("sector") or "?"
        sector_count[sec] += 1
    top6 = sorted(sector_count.items(), key=lambda x: -x[1])[:6]
    top6_names = [s for s, _ in top6]

    grid = defaultdict(lambda: defaultdict(list))
    sigs = set()
    for r in records:
        sec = r.get("sector") or "?"
        if sec not in top6_names:
            continue
        sig = r.get("signal") or r.get("signal_type") or "?"
        grid[sec][sig].append(r)
        sigs.add(sig)
    sigs = sorted(sigs)

    out = []
    out.append("## e. WR by sector × signal_type (top 6 sectors)\n")
    out.append("| Sector \\ Signal | " + " | ".join(sigs) + " | total |")
    out.append("|---" + ("|---" * (len(sigs) + 1)) + "|")
    standout = []
    for sec in top6_names:
        cells = []
        total = 0
        for sig in sigs:
            recs = grid[sec][sig]
            total += len(recs)
            if not recs:
                cells.append("—")
                continue
            n = len(recs)
            wr = wr_pct(recs)
            cells.append(f"{pct_str(wr)} (n={n})")
            if (isinstance(wr, (int, float)) and n >= 10
                    and (wr >= 85 or wr <= 30)):
                standout.append((sec, sig, wr, n))
        out.append(
            f"| **{sec}** | " + " | ".join(cells) + f" | {total} |")
    out.append("")
    if standout:
        bits = "; ".join(
            f"{sec} × {sig} = {pct_str(wr)} (n={n})"
            for sec, sig, wr, n in standout)
        out.append(
            f"**Observation:** Sector × signal standouts (n ≥10): {bits}.")
    else:
        out.append(
            "**Observation:** No sector × signal cell hits "
            "WR ≥85% or ≤30% with n ≥10 — most sectors land mid-band.")
    return "\n".join(out)


# ===================================================================
# Section f. MAE/MFE distribution per outcome type
# ===================================================================

def section_f(records):
    by_outcome = defaultdict(list)
    for r in records:
        oc = r.get("outcome") or "?"
        by_outcome[oc].append(r)

    out = []
    out.append("## f. MAE / MFE distribution per outcome type\n")
    out.append("| Outcome | n | MAE p25 / median / p75 | MFE p25 / median / p75 |")
    out.append("|---|---|---|---|")

    outcome_order = list(WIN_OUTCOMES) + list(LOSS_OUTCOMES) + list(FLAT_OUTCOMES)
    for oc in outcome_order:
        recs = by_outcome.get(oc) or []
        if not recs:
            continue
        n = len(recs)
        mae_sorted = sorted(
            r.get("mae_pct") for r in recs
            if isinstance(r.get("mae_pct"), (int, float))
        )
        mfe_sorted = sorted(
            r.get("mfe_pct") for r in recs
            if isinstance(r.get("mfe_pct"), (int, float))
        )
        if mae_sorted:
            mae_str = (
                f"{percentile(mae_sorted, 25):.1f}% / "
                f"{percentile(mae_sorted, 50):.1f}% / "
                f"{percentile(mae_sorted, 75):.1f}%"
            )
        else:
            mae_str = "?"
        if mfe_sorted:
            mfe_str = (
                f"{percentile(mfe_sorted, 25):.1f}% / "
                f"{percentile(mfe_sorted, 50):.1f}% / "
                f"{percentile(mfe_sorted, 75):.1f}%"
            )
        else:
            mfe_str = "?"
        out.append(f"| {oc} | {n} | {mae_str} | {mfe_str} |")
    out.append("")
    out.append(
        "**Observation:** MAE shows worst drawdown reached during the "
        "trade; MFE shows best favorable excursion. Stop hits with "
        "high MFE indicate the trade went favorable first then "
        "reversed — candidates for trailing-stop study.")
    return "\n".join(out)


# ===================================================================
# Section g. Day-to-outcome distribution
# ===================================================================

def section_g(records):
    bucket = defaultdict(int)
    total = 0
    for r in records:
        d = r.get("days_to_outcome")
        if not isinstance(d, (int, float)):
            continue
        di = int(d)
        if 1 <= di <= 6:
            bucket[di] += 1
        else:
            bucket["other"] += 1
        total += 1

    out = []
    out.append("## g. Day-to-outcome distribution\n")
    out.append("| Day | Resolutions | % of resolved |")
    out.append("|---|---|---|")
    for d in (1, 2, 3, 4, 5, 6):
        n = bucket.get(d, 0)
        pct = (n / total * 100) if total else 0
        out.append(f"| Day {d} | {n} | {pct:.1f}% |")
    if bucket.get("other"):
        n = bucket["other"]
        pct = (n / total * 100) if total else 0
        out.append(f"| other | {n} | {pct:.1f}% |")
    out.append("")
    if total:
        d1_pct = bucket.get(1, 0) / total * 100
        d6_pct = bucket.get(6, 0) / total * 100
        out.append(
            f"**Observation:** Day 1 = {d1_pct:.1f}% of resolutions, "
            f"Day 6 (forced exit) = {d6_pct:.1f}%. "
            + (
                "Heavy Day-1 tail suggests fast-reversion or fast-target trades."
                if d1_pct > 25
                else "Resolutions distribute across the 6-day window."
            )
        )
    return "\n".join(out)


# ===================================================================
# Section h. Best / worst single signals
# ===================================================================

def section_h(records):
    sortable = [
        r for r in records
        if isinstance(r.get("pnl_pct"), (int, float))
    ]
    by_pnl = sorted(sortable, key=lambda r: -r["pnl_pct"])
    top5    = by_pnl[:5]
    bottom5 = sorted(sortable, key=lambda r: r["pnl_pct"])[:5]

    def row(r):
        sym = (r.get("symbol") or "?").replace(".NS", "")
        sig = r.get("signal") or "?"
        sec = r.get("sector") or "?"
        reg = r.get("regime") or "?"
        d   = r.get("date") or "?"
        oc  = r.get("outcome") or "?"
        pnl = r.get("pnl_pct")
        return (
            f"| {d} | {sym} | {sig} | {sec} | {reg} | "
            f"{oc} | {fmt(pnl, 2, '%')} |"
        )

    out = []
    out.append("## h. Best / worst single signals\n")
    out.append("### Top 5 wins (by pnl_pct)\n")
    out.append("| Date | Symbol | Signal | Sector | Regime | Outcome | P&L |")
    out.append("|---|---|---|---|---|---|---|")
    for r in top5:
        out.append(row(r))
    out.append("")
    out.append("### Top 5 losses (by pnl_pct)\n")
    out.append("| Date | Symbol | Signal | Sector | Regime | Outcome | P&L |")
    out.append("|---|---|---|---|---|---|---|")
    for r in bottom5:
        out.append(row(r))
    out.append("")
    if top5 and bottom5:
        out.append(
            f"**Observation:** Best win {top5[0]['pnl_pct']:+.1f}% "
            f"({(top5[0].get('symbol') or '?').replace('.NS','')}); "
            f"worst loss {bottom5[0]['pnl_pct']:+.1f}% "
            f"({(bottom5[0].get('symbol') or '?').replace('.NS','')}). "
            f"Asymmetry is expected with stops capping losses.")
    return "\n".join(out)


# ===================================================================
# Section i. Pattern observations (n ≥10, WR ≥85% or ≤30%)
# ===================================================================

def section_i(records):
    """Cross-tab signal × sector × regime, surface high-conviction cells."""
    from itertools import product as cartesian

    grid = defaultdict(list)
    for r in records:
        key = (
            r.get("signal") or "?",
            r.get("sector") or "?",
            r.get("regime") or "?",
        )
        grid[key].append(r)

    high = []
    low  = []
    for (sig, sec, reg), recs in grid.items():
        n = len(recs)
        if n < 10:
            continue
        wr = wr_pct(recs)
        if not isinstance(wr, (int, float)):
            continue
        if wr >= 85:
            high.append((sig, sec, reg, n, wr))
        elif wr <= 30:
            low.append((sig, sec, reg, n, wr))

    high.sort(key=lambda x: (-x[4], -x[3]))
    low.sort(key=lambda x: (x[4], -x[3]))

    out = []
    out.append("## i. Pattern observations (n ≥10)\n")
    out.append("### High-conviction patterns (WR ≥85%)\n")
    if high:
        out.append("| Signal | Sector | Regime | n | WR |")
        out.append("|---|---|---|---|---|")
        for sig, sec, reg, n, wr in high:
            out.append(f"| {sig} | {sec} | {reg} | {n} | {pct_str(wr)} |")
    else:
        out.append("_None at n ≥10._")
    out.append("")
    out.append("### Low-conviction / kill candidate patterns (WR ≤30%)\n")
    if low:
        out.append("| Signal | Sector | Regime | n | WR |")
        out.append("|---|---|---|---|---|")
        for sig, sec, reg, n, wr in low:
            out.append(f"| {sig} | {sec} | {reg} | {n} | {pct_str(wr)} |")
    else:
        out.append("_None at n ≥10._")
    out.append("")
    out.append(
        f"**Observation:** {len(high)} high-conviction and "
        f"{len(low)} low-conviction (signal × sector × regime) cells "
        f"with n ≥10. Cross-check against `boost_patterns` and "
        f"`kill_patterns` in `data/mini_scanner_rules.json`.")
    return "\n".join(out)


# ===================================================================
# Final: Top 3 actionable findings (synthesized from sections above)
# ===================================================================

def top_3_findings(records, b_rows=None):
    """Synthesize 3 cautious bullets. Skip claims based on n<20."""
    bullets = []

    # 1. Overall WR contextualization
    n = len(records)
    wr = wr_pct(records)
    pnl = avg([r.get("pnl_pct") for r in records])
    rm  = avg([r.get("r_multiple") for r in records])
    if isinstance(wr, (int, float)) and n >= 20:
        if isinstance(rm, (int, float)) and rm < 1.0:
            bullets.append(
                f"**System-level R-multiple {fmt(rm,2)} below 1.0** at "
                f"{wr}% WR (n={n}). Edge lives in win rate, not "
                f"magnitude — consistent with prior R-multiple = 0.44 "
                f"finding (prop_005 motivation). Revisit stop/target "
                f"rebalance design BEFORE assuming win rate alone "
                f"suffices.")
        elif isinstance(pnl, (int, float)) and pnl < 0:
            bullets.append(
                f"**Aggregate avg P&L is {fmt(pnl,2,'%')} despite "
                f"{wr}% WR (n={n}).** Loss magnitude exceeds win "
                f"magnitude — verify stops are placed correctly.")

    # 2. Signal-type-level breakdown (n≥20 for any sig)
    by_sig = defaultdict(list)
    for r in records:
        sig = r.get("signal") or r.get("signal_type") or "?"
        by_sig[sig].append(r)
    big_sig_rows = []
    for sig, recs in by_sig.items():
        if len(recs) < 20:
            continue
        wr_s = wr_pct(recs)
        if isinstance(wr_s, (int, float)):
            big_sig_rows.append((sig, len(recs), wr_s))
    big_sig_rows.sort(key=lambda x: -x[2])
    if len(big_sig_rows) >= 2:
        hi = big_sig_rows[0]
        lo = big_sig_rows[-1]
        if hi[2] - lo[2] >= 30:
            bullets.append(
                f"**Signal-type stratification dominates:** "
                f"{hi[0]} {pct_str(hi[2])} WR (n={hi[1]}) vs "
                f"{lo[0]} {pct_str(lo[2])} WR (n={lo[1]}). "
                f"Signal-type is the strongest single discriminator "
                f"in the dataset; refine sub-stratifications only "
                f"after this gap stabilizes.")

    # 3. High-conviction patterns (signal × sector × regime, n≥20)
    grid = defaultdict(list)
    for r in records:
        key = (
            r.get("signal") or "?",
            r.get("sector") or "?",
            r.get("regime") or "?",
        )
        grid[key].append(r)
    big_wins = []
    for key, recs in grid.items():
        if len(recs) < 20:
            continue
        wr_c = wr_pct(recs)
        if isinstance(wr_c, (int, float)) and wr_c >= 85:
            big_wins.append((key, len(recs), wr_c))
    big_wins.sort(key=lambda x: (-x[2], -x[1]))
    if big_wins:
        cells = "; ".join(
            f"{k[0]} × {k[1]} × {k[2]} ({wr}% n={n})"
            for k, n, wr in big_wins[:3]
        )
        bullets.append(
            f"**High-conviction cells with n ≥20:** {cells}. These "
            f"are validated boost-pattern candidates — cross-check "
            f"`mini_scanner_rules.json` to ensure they're already "
            f"surfaced as TAKE_FULL.")

    # 3. Low-conviction patterns (kill candidates, n≥20)
    big_losses = []
    for key, recs in grid.items():
        if len(recs) < 20:
            continue
        wr_c = wr_pct(recs)
        if isinstance(wr_c, (int, float)) and wr_c <= 35:
            big_losses.append((key, len(recs), wr_c))
    big_losses.sort(key=lambda x: (x[2], -x[1]))
    if big_losses:
        cells = "; ".join(
            f"{k[0]} × {k[1]} × {k[2]} ({wr}% n={n})"
            for k, n, wr in big_losses[:3]
        )
        bullets.append(
            f"**Low-conviction cells with n ≥20:** {cells}. Kill-rule "
            f"candidates — verify against `proposed_rules.json` to see "
            f"if rule_proposer has already flagged them.")

    # Fallback if we have fewer than 3 confident findings
    if len(bullets) < 3:
        bullets.append(
            f"**Sample size {n} resolutions** is sufficient for "
            f"signal-type-level conclusions but borderline for sector "
            f"× regime cross-tabs. Most sub-cohort cells have n <20 — "
            f"continue accumulating data before refining boost/kill "
            f"rules at finer granularity.")

    out = ["## Top 3 actionable findings\n"]
    for i, b in enumerate(bullets[:3], 1):
        out.append(f"{i}. {b}")
    return "\n".join(out)


# ===================================================================
# Main
# ===================================================================

def main():
    records, dropped = load_resolved()
    print(f"[analyze] Loaded {len(records)} resolved records "
          f"(dropped {dropped} malformed/non-canonical)")

    today = date.today().isoformat()
    report_path = os.path.join(
        REPO, "output", f"analysis_report_{today}.md")

    sections = [
        f"# TIE TIY Full Analysis Report — {today}\n",
        f"_Generated by `scripts/analyze_full.py` against "
        f"`output/signal_history.json`._\n",
        f"_Resolved sample: **{len(records)}** records "
        f"(dropped {dropped} malformed)._\n",
        "---\n",
        section_a(records),
        "\n---\n",
        section_b(records),
        "\n---\n",
        section_c(records),
        "\n---\n",
        section_d(records),
        "\n---\n",
        section_e(records),
        "\n---\n",
        section_f(records),
        "\n---\n",
        section_g(records),
        "\n---\n",
        section_h(records),
        "\n---\n",
        section_i(records),
        "\n---\n",
        top_3_findings(records),
        "\n",
        "_Report end._",
    ]

    with open(report_path, "w") as f:
        f.write("\n".join(sections))

    print(f"[analyze] Wrote {report_path}")
    print(f"[analyze] Bytes: {os.path.getsize(report_path)}")


if __name__ == "__main__":
    main()
