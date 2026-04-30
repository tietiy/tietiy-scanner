"""
INV-003 — Sector × regime × signal profitability matrix scan.

Per ROADMAP INV-003: scan every (sector, regime, signal) triple. For each cohort:
  - compute_cohort_stats lifetime
  - if n_excl_flat ≥ 30: run evaluate_hypothesis for both BOOST and KILL hypothesis_type
  - record per-cohort tier verdict + train/test stats + drift

NOTE on dimensionality: ROADMAP spec says "11 sectors × 3 regimes × 3 signals = 99
cohorts" but actual backtest_signals.parquet has 13 sectors (Auto, Bank, CapGoods,
Chem, Consumer, Energy, FMCG, Health, IT, Infra, Metal, Other, Pharma) yielding
13 × 3 × 3 = 117 cohorts. Honoring actual data; deviation surfaced in findings.

Outputs:
  - /lab/analyses/INV-003_findings.md (matrix report; ~30-50 KB)
  - /lab/logs/inv_003_run.log (stdout/stderr)

Section schema:
  A — Boost candidates (Tier S/A/B BOOST)
  B — Kill candidates (Tier S/A/B KILL)
  C — REJECT cohorts (n adequate but no tier)
  D — INSUFFICIENT_N cohorts
  E — Headline findings + INV-001 cross-reference
  F — Open questions for user review

NO promotion calls. NO patterns.json changes. Findings.md is data-only.
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
    evaluate_hypothesis,
)

# ── Constants ─────────────────────────────────────────────────────────

_SIGNALS_PATH = _LAB_ROOT / "output" / "backtest_signals.parquet"
_OUTPUT_FINDINGS = _LAB_ROOT / "analyses" / "INV-003_findings.md"

_TRAIN_END = "2022-12-31"
_TEST_START = "2023-01-01"
_N_MIN_RESOLVED = 30  # below this → INSUFFICIENT_N (per spec + safe-default)

_SIGNALS_AXIS = ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]
_REGIMES_AXIS = ["Bear", "Choppy", "Bull"]


# ── Per-cohort evaluation ─────────────────────────────────────────────

def evaluate_cohort(signals_df: pd.DataFrame,
                     sector: str, regime: str, signal: str) -> dict:
    """Evaluate a single (sector, regime, signal) cohort.
    Returns dict with lifetime stats + boost/kill tier verdicts."""
    cohort = signals_df[(signals_df["sector"] == sector) &
                          (signals_df["regime"] == regime) &
                          (signals_df["signal"] == signal)]
    lifetime_stats = compute_cohort_stats(cohort, cohort_filter={})
    n_excl_flat = lifetime_stats["n_win"] + lifetime_stats["n_loss"]

    result = {
        "sector": sector, "regime": regime, "signal": signal,
        "n_total": lifetime_stats["n_total"],
        "n_resolved": lifetime_stats["n_resolved"],
        "n_excl_flat": n_excl_flat,
        "n_win": lifetime_stats["n_win"],
        "n_loss": lifetime_stats["n_loss"],
        "n_flat": lifetime_stats["n_flat"],
        "n_open": lifetime_stats["n_open"],
        "wr_excl_flat": lifetime_stats["wr_excl_flat"],
        "wilson_lower_95": lifetime_stats["wilson_lower_95"],
        "p_value_vs_50": lifetime_stats["p_value_vs_50"],
        "boost_tier": None, "boost_train_wr": None, "boost_test_wr": None,
        "boost_train_n": None, "boost_test_n": None, "boost_drift_pp": None,
        "kill_tier": None, "kill_train_wr": None, "kill_test_wr": None,
        "kill_train_n": None, "kill_test_n": None, "kill_drift_pp": None,
        "status": None, "error": None,
    }

    if n_excl_flat < _N_MIN_RESOLVED:
        result["status"] = "INSUFFICIENT_N"
        return result

    try:
        boost_eval = evaluate_hypothesis(
            signals_df,
            cohort_filter={"sector": sector, "regime": regime, "signal": signal},
            hypothesis_type="BOOST",
        )
        result["boost_tier"] = boost_eval["tier"]
        result["boost_train_wr"] = boost_eval["train_stats"]["wr_excl_flat"]
        result["boost_test_wr"] = boost_eval["test_stats"]["wr_excl_flat"]
        result["boost_train_n"] = (boost_eval["train_stats"]["n_win"]
                                     + boost_eval["train_stats"]["n_loss"])
        result["boost_test_n"] = (boost_eval["test_stats"]["n_win"]
                                    + boost_eval["test_stats"]["n_loss"])
        result["boost_drift_pp"] = boost_eval["drift_pp"]
    except Exception as e:
        result["error"] = f"BOOST eval failed: {e}"

    try:
        kill_eval = evaluate_hypothesis(
            signals_df,
            cohort_filter={"sector": sector, "regime": regime, "signal": signal},
            hypothesis_type="KILL",
        )
        result["kill_tier"] = kill_eval["tier"]
        result["kill_train_wr"] = kill_eval["train_stats"]["wr_excl_flat"]
        result["kill_test_wr"] = kill_eval["test_stats"]["wr_excl_flat"]
        result["kill_train_n"] = (kill_eval["train_stats"]["n_win"]
                                    + kill_eval["train_stats"]["n_loss"])
        result["kill_test_n"] = (kill_eval["test_stats"]["n_win"]
                                   + kill_eval["test_stats"]["n_loss"])
        result["kill_drift_pp"] = kill_eval["drift_pp"]
    except Exception as e:
        prior = result["error"] or ""
        result["error"] = (prior + " | KILL eval failed: " + str(e)).strip(" |")

    if result["boost_tier"] in ("S", "A", "B"):
        result["status"] = f"BOOST_TIER_{result['boost_tier']}"
    elif result["kill_tier"] in ("S", "A", "B"):
        result["status"] = f"KILL_TIER_{result['kill_tier']}"
    else:
        result["status"] = "REJECT"
    return result


# ── Findings.md writer ────────────────────────────────────────────────

def _fmt_row_table(r: dict, hyp_type: str) -> str:
    """Format one matrix row for boost or kill section."""
    if hyp_type == "BOOST":
        prefix = "boost"
    else:
        prefix = "kill"
    return (f"| {r['sector']} | {r['regime']} | {r['signal']} | "
            f"{r[f'{prefix}_train_n']} | {r[f'{prefix}_train_wr']} | "
            f"{r[f'{prefix}_test_n']} | {r[f'{prefix}_test_wr']} | "
            f"{r[f'{prefix}_drift_pp']} | {r[f'{prefix}_tier']} |")


def write_findings_md(results: list[dict], output_path: Path,
                       sectors: list[str], regimes: list[str],
                       signals: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Categorize cohorts
    boost_candidates = [r for r in results if r.get("boost_tier") in ("S", "A", "B")]
    kill_candidates = [r for r in results if r.get("kill_tier") in ("S", "A", "B")]
    reject_cohorts = [r for r in results
                       if r.get("status") == "REJECT"]
    insufficient = [r for r in results if r.get("status") == "INSUFFICIENT_N"]
    error_cohorts = [r for r in results if r.get("error")]

    # Sort: boost by train_wr desc; kill by train_wr asc; reject by distance from 0.5
    boost_candidates.sort(key=lambda r: -(r.get("boost_train_wr") or 0))
    kill_candidates.sort(key=lambda r: (r.get("kill_train_wr") or 1.0))
    reject_cohorts.sort(key=lambda r: -abs((r.get("wr_excl_flat") or 0.5) - 0.5))

    n_total = len(results)
    boost_by_tier = {"S": 0, "A": 0, "B": 0}
    for r in boost_candidates:
        boost_by_tier[r["boost_tier"]] += 1
    kill_by_tier = {"S": 0, "A": 0, "B": 0}
    for r in kill_candidates:
        kill_by_tier[r["kill_tier"]] += 1

    with open(output_path, "w") as f:
        f.write("# INV-003 — Sector × regime × signal profitability matrix\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write("**Branch:** backtest-lab\n\n")
        f.write(f"**Cohorts evaluated:** {n_total} ({len(sectors)} sectors × "
                f"{len(regimes)} regimes × {len(signals)} signals)\n\n")
        f.write(f"**Sectors:** {', '.join(sectors)}\n\n")
        f.write(f"**Regimes:** {', '.join(regimes)}\n\n")
        f.write(f"**Signals:** {', '.join(signals)}\n\n")

        # Caveats
        f.write("---\n\n")
        f.write("## ⚠️ Caveats carried forward\n\n")
        f.write("**Caveat 1 (sector indices) RESOLVED:** all 8 indexed sectors now "
                "have real Leading/Neutral/Lagging classification. Chem sector remains "
                "100% Neutral (no `^CNXCHEM` ticker on Yahoo Finance — outside scope).\n\n")
        f.write("**Caveat 2 (9.31% MS-2 miss-rate):** active. Sub-cohort findings at "
                "marginal n (n=30-50) particularly susceptible — Tier B/A results at "
                "marginal n should be re-validated post-Caveat 2 audit before promotion.\n\n")
        f.write("**Dimensionality deviation:** ROADMAP INV-003 spec said 11 sectors × 3 "
                "regimes × 3 signals = 99 cohorts. Actual backtest_signals.parquet has "
                f"{len(sectors)} sectors yielding {n_total} cohorts. Honoring actual data; "
                "extra sectors (CapGoods, Consumer, Health, Other beyond the original 11) "
                "are documented but their indices are NOT in cache → sector_momentum falls "
                "back to Neutral for those sectors only.\n\n")

        # Section A — Boost candidates
        f.write("---\n\n")
        f.write("## Section A — Boost candidates (Tier S/A/B BOOST)\n\n")
        f.write(f"**Surfaced:** {len(boost_candidates)} cohorts "
                f"(S={boost_by_tier['S']} A={boost_by_tier['A']} B={boost_by_tier['B']})\n\n")
        if boost_candidates:
            f.write("| Sector | Regime | Signal | Train_n | Train_WR | Test_n | Test_WR | Drift_pp | Tier |\n")
            f.write("|--------|--------|--------|---------|----------|--------|---------|---------|------|\n")
            for r in boost_candidates:
                f.write(_fmt_row_table(r, "BOOST") + "\n")
        else:
            f.write("_No boost candidates surfaced._\n")
        f.write("\n")

        # Section B — Kill candidates
        f.write("---\n\n")
        f.write("## Section B — Kill candidates (Tier S/A/B KILL)\n\n")
        f.write(f"**Surfaced:** {len(kill_candidates)} cohorts "
                f"(S={kill_by_tier['S']} A={kill_by_tier['A']} B={kill_by_tier['B']})\n\n")
        if kill_candidates:
            f.write("| Sector | Regime | Signal | Train_n | Train_WR | Test_n | Test_WR | Drift_pp | Tier |\n")
            f.write("|--------|--------|--------|---------|----------|--------|---------|---------|------|\n")
            for r in kill_candidates:
                f.write(_fmt_row_table(r, "KILL") + "\n")
        else:
            f.write("_No kill candidates surfaced._\n")
        f.write("\n")

        # Section C — REJECT cohorts (n adequate, no tier)
        f.write("---\n\n")
        f.write(f"## Section C — REJECT cohorts ({len(reject_cohorts)} — n adequate, no tier)\n\n")
        f.write("Sorted by lifetime WR distance from coin-flip (most extreme first).\n\n")
        if reject_cohorts:
            f.write("| Sector | Regime | Signal | Lifetime n | Lifetime WR | Wilson_lower | "
                    "Boost drift_pp | Kill drift_pp |\n")
            f.write("|--------|--------|--------|-----------|-------------|--------------|"
                    "----------------|---------------|\n")
            for r in reject_cohorts:
                f.write(f"| {r['sector']} | {r['regime']} | {r['signal']} | "
                        f"{r['n_excl_flat']} | {r['wr_excl_flat']} | "
                        f"{r['wilson_lower_95']} | {r['boost_drift_pp']} | "
                        f"{r['kill_drift_pp']} |\n")
        else:
            f.write("_No reject cohorts (all evaluations either qualified or insufficient_n)._\n")
        f.write("\n")

        # Section D — INSUFFICIENT_N
        f.write("---\n\n")
        f.write(f"## Section D — INSUFFICIENT_N cohorts ({len(insufficient)} — n_excl_flat < {_N_MIN_RESOLVED})\n\n")
        if insufficient:
            f.write("| Sector | Regime | Signal | n_total | n_resolved | n_excl_flat |\n")
            f.write("|--------|--------|--------|---------|-----------|-------------|\n")
            for r in insufficient:
                f.write(f"| {r['sector']} | {r['regime']} | {r['signal']} | "
                        f"{r['n_total']} | {r['n_resolved']} | {r['n_excl_flat']} |\n")
        else:
            f.write("_No cohorts below INSUFFICIENT_N threshold._\n")
        f.write("\n")

        # Errors (if any)
        if error_cohorts:
            f.write("---\n\n")
            f.write(f"## ⚠️ Cohort evaluation errors ({len(error_cohorts)})\n\n")
            for r in error_cohorts:
                f.write(f"- **{r['sector']} × {r['regime']} × {r['signal']}**: `{r['error']}`\n")
            f.write("\n")

        # Section E — Headline findings
        f.write("---\n\n")
        f.write("## Section E — Headline findings\n\n")
        f.write(f"- **Total cohorts evaluated:** {n_total}\n")
        f.write(f"- **Boost candidates:** {len(boost_candidates)} "
                f"(S={boost_by_tier['S']} A={boost_by_tier['A']} B={boost_by_tier['B']})\n")
        f.write(f"- **Kill candidates:** {len(kill_candidates)} "
                f"(S={kill_by_tier['S']} A={kill_by_tier['A']} B={kill_by_tier['B']})\n")
        f.write(f"- **REJECT cohorts:** {len(reject_cohorts)}\n")
        f.write(f"- **INSUFFICIENT_N:** {len(insufficient)}\n")
        f.write(f"- **Eval errors:** {len(error_cohorts)}\n\n")

        # Most extreme
        all_evaluated = [r for r in results if r.get("wr_excl_flat") is not None
                          and r.get("status") != "INSUFFICIENT_N"]
        if all_evaluated:
            extremes_high = sorted(all_evaluated, key=lambda r: -(r["wr_excl_flat"] or 0))[:5]
            extremes_low = sorted(all_evaluated, key=lambda r: (r["wr_excl_flat"] or 1.0))[:5]
            f.write("**Most extreme cohorts by lifetime WR (informational only — does NOT mean tier qualified):**\n\n")
            f.write("Top 5 highest WR (boost-shaped):\n\n")
            f.write("| Sector | Regime | Signal | n | WR | Wilson_lower | Boost tier | Kill tier |\n")
            f.write("|--------|--------|--------|---|-----|-------------|----------|----------|\n")
            for r in extremes_high:
                f.write(f"| {r['sector']} | {r['regime']} | {r['signal']} | "
                        f"{r['n_excl_flat']} | {r['wr_excl_flat']} | {r['wilson_lower_95']} | "
                        f"{r['boost_tier']} | {r['kill_tier']} |\n")
            f.write("\nTop 5 lowest WR (kill-shaped):\n\n")
            f.write("| Sector | Regime | Signal | n | WR | Wilson_lower | Boost tier | Kill tier |\n")
            f.write("|--------|--------|--------|---|-----|-------------|----------|----------|\n")
            for r in extremes_low:
                f.write(f"| {r['sector']} | {r['regime']} | {r['signal']} | "
                        f"{r['n_excl_flat']} | {r['wr_excl_flat']} | {r['wilson_lower_95']} | "
                        f"{r['boost_tier']} | {r['kill_tier']} |\n")
            f.write("\n")

        # Cross-reference INV-001 (UP_TRI × Bank × Choppy)
        inv001_cell = next((r for r in results
                             if r["signal"] == "UP_TRI"
                             and r["sector"] == "Bank"
                             and r["regime"] == "Choppy"), None)
        f.write("**INV-001 cross-reference (UP_TRI × Bank × Choppy):**\n\n")
        if inv001_cell:
            f.write(f"- INV-003 cell verdict: `{inv001_cell.get('status')}`\n")
            f.write(f"- INV-003 boost tier: `{inv001_cell.get('boost_tier')}`\n")
            f.write(f"- INV-003 kill tier: `{inv001_cell.get('kill_tier')}`\n")
            f.write(f"- Lifetime WR (excl flat): {inv001_cell.get('wr_excl_flat')}; "
                    f"n={inv001_cell.get('n_excl_flat')}; Wilson lower {inv001_cell.get('wilson_lower_95')}\n")
            f.write(f"- INV-001 standalone investigation reached parent KILL tier `REJECT` "
                    f"(15-yr drift 6.52pp). INV-003 cell verdict here should match that result "
                    f"if cohort filters and tier evaluators are consistent.\n\n")
        else:
            f.write("- Cell not found in matrix (unexpected).\n\n")

        # INV-002 cross-reference
        inv002_cell = next((r for r in results
                             if r["signal"] == "UP_TRI"
                             and r["sector"] == "Bank"
                             and r["regime"] == "Bear"), None)
        f.write("**INV-002 cross-reference (UP_TRI × Bank × Bear):**\n\n")
        if inv002_cell:
            f.write(f"- INV-003 cell verdict: `{inv002_cell.get('status')}`\n")
            f.write(f"- INV-003 boost tier: `{inv002_cell.get('boost_tier')}`\n")
            f.write(f"- INV-003 kill tier: `{inv002_cell.get('kill_tier')}`\n")
            f.write(f"- Lifetime WR: {inv002_cell.get('wr_excl_flat')}; "
                    f"n={inv002_cell.get('n_excl_flat')}\n")
            f.write(f"- INV-002 standalone reached parent BOOST tier `REJECT` "
                    f"(HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT). INV-003 cell verdict here should match.\n\n")
        else:
            f.write("- Cell not found in matrix (unexpected).\n\n")

        # Section F — Open questions
        f.write("---\n\n")
        f.write("## Section F — Open questions for user review\n\n")
        f.write("The following questions are surfaced for user judgment in a separate session. "
                "CC does NOT make promotion calls.\n\n")
        f.write("1. **Boost candidates → potential mechanism INV follow-ups:** Each boost-tier "
                "cohort surfaced in Section A is a candidate for INV-006/007/008+ mechanism "
                "investigation. User decides which (if any) to pre-register based on cohort "
                "tradeable structure + business context.\n\n")
        f.write("2. **Kill candidates → potential `mini_scanner_rules.kill_patterns` promotion:** "
                "Kill-tier cohorts in Section B may warrant promotion to active suppression. User "
                "applies Gate 4 (ground-truth validation) + Gate 5 (mechanism) + Gate 7 (user "
                "review) before any patterns.json transition.\n\n")
        f.write("3. **kill_002 path with INV-003 context:** Does any other Bank × Choppy or "
                "broader cohort better explain the Apr 2026 cluster than the original kill_002 "
                "candidate? See Section E INV-001 cross-reference + cluster verification from "
                "prior Phase 4 (60d_ret subset analysis).\n\n")
        f.write("4. **Caveat 2 audit before promotion:** Each surfaced candidate at marginal n "
                "(say n_excl_flat < 100) should be re-validated after Caveat 2 (9.31% MS-2 "
                "miss-rate) audit. Caveat 2 audit deferred to separate session.\n\n")
        f.write("5. **patterns.json INV-003 status update:** PRE_REGISTERED → COMPLETED is a "
                "user-only transition; CC does not modify patterns.json beyond founding state.\n\n")

        f.write("---\n\n")
        f.write("## Promotion decisions deferred to user review (per Lab Discipline Principle 6)\n\n")
        f.write("This findings.md is **data + structured analysis only**. No promotion decisions "
                "are made by CC. User reviews end-to-end + applies Gate 7 (user review) before "
                "any patterns.json status change or main-branch promotion.\n")


# ── Main orchestrator ─────────────────────────────────────────────────

def main():
    print(f"[INV-003] starting at {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"[INV-003] loading {_SIGNALS_PATH}…", flush=True)
    signals_df = pd.read_parquet(_SIGNALS_PATH)
    print(f"[INV-003] loaded {len(signals_df)} backtest signals", flush=True)

    sectors = sorted(signals_df["sector"].dropna().unique().tolist())
    print(f"[INV-003] sectors: {sectors}", flush=True)
    print(f"[INV-003] regimes: {_REGIMES_AXIS}", flush=True)
    print(f"[INV-003] signals: {_SIGNALS_AXIS}", flush=True)
    n_total = len(sectors) * len(_REGIMES_AXIS) * len(_SIGNALS_AXIS)
    print(f"[INV-003] matrix size: {n_total} cohorts", flush=True)

    results = []
    for sec_i, sector in enumerate(sectors):
        for regime in _REGIMES_AXIS:
            for signal in _SIGNALS_AXIS:
                idx = len(results) + 1
                try:
                    r = evaluate_cohort(signals_df, sector, regime, signal)
                    results.append(r)
                    if idx % 10 == 0 or idx == n_total:
                        print(f"[INV-003] {idx}/{n_total} done "
                              f"(latest: {sector} × {regime} × {signal} → {r['status']})",
                              flush=True)
                except Exception as e:
                    tb = traceback.format_exc()
                    results.append({
                        "sector": sector, "regime": regime, "signal": signal,
                        "status": "EVAL_CRASH", "error": str(e),
                        "n_total": None, "n_resolved": None, "n_excl_flat": None,
                        "n_win": None, "n_loss": None, "n_flat": None, "n_open": None,
                        "wr_excl_flat": None, "wilson_lower_95": None, "p_value_vs_50": None,
                        "boost_tier": None, "boost_train_wr": None, "boost_test_wr": None,
                        "boost_train_n": None, "boost_test_n": None, "boost_drift_pp": None,
                        "kill_tier": None, "kill_train_wr": None, "kill_test_wr": None,
                        "kill_train_n": None, "kill_test_n": None, "kill_drift_pp": None,
                    })
                    print(f"[INV-003] {idx}/{n_total} CRASHED: {sector} × {regime} × {signal}: {e}",
                          flush=True)
                    print(tb, flush=True)

    print(f"[INV-003] writing findings → {_OUTPUT_FINDINGS}", flush=True)
    write_findings_md(results, _OUTPUT_FINDINGS, sectors, _REGIMES_AXIS, _SIGNALS_AXIS)
    print(f"[INV-003] complete at {datetime.now(timezone.utc).isoformat()}", flush=True)


if __name__ == "__main__":
    main()
