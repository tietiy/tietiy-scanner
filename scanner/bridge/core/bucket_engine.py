"""
bucket_engine — the decision tree. Every signal walks 4 gates, first match wins.

Pure orchestration: calls rules/ matchers + reads pre-computed evidence dict.
Never does I/O. Never runs queries. Just walks the tree and returns a bucket.

The single most important business-logic file in the bridge. If you change the
decision tree, you change every recommendation the bridge produces. Touch with
care, accompanied by smoke tests.

See doc/bridge_design_v1.md §5 (decision tree), §6 (bucket examples).
"""

from typing import Any, Optional

from scanner.bridge.rules import validity_checker
from scanner.bridge.rules.thresholds import (
    COHORT_MODERATE_N,
    COHORT_MODERATE_SECTOR_WR,
    COHORT_MODERATE_WR,
    COHORT_STRONG_N,
    COHORT_STRONG_WR,
    COHORT_THIN_FALLBACK_N,
)


_THIN_FALLBACK_SECTOR_WR = 0.70
_THIN_FALLBACK_REGIME_WR = 0.65


# =====================================================================
# Public entry point
# =====================================================================

def assign_bucket(signal: dict, evidence: dict) -> dict:
    """Walk the 4-gate tree, first match wins. See module docstring.

    Reads boost_match and kill_match from the evidence dict (populated
    upstream by evidence_collector). bucket_engine no longer calls the
    matchers directly — single source of truth in the evidence dict.
    """
    evidence = evidence or {}

    # Gate 1 — KILL MATCH (read from evidence)
    kill_match = evidence.get("kill_match")
    if kill_match:
        return _build_skip_kill(signal, kill_match, evidence)

    # Gate 2 — VALIDITY
    is_valid, validity_reason = validity_checker.check(signal)
    if not is_valid:
        return _build_skip_validity(
            signal, validity_reason, evidence)

    # Gate 3 — BOOST MATCH (read from evidence)
    boost_match = evidence.get("boost_match")
    if boost_match:
        tier = boost_match.get("tier")
        if tier == "A":
            return _build_take_full_boost(
                signal, boost_match, evidence)
        if tier == "B":
            return _build_take_small_boost(
                signal, boost_match, evidence)
        # Unknown tier — fall through to evidence consensus

    # Gate 4 — EVIDENCE CONSENSUS
    return _gate4_evidence(signal, evidence)


# =====================================================================
# Gate 1 — kill match
# =====================================================================

def _build_skip_kill(signal: dict,
                     kill_match: dict,
                     evidence: dict) -> dict:
    kill_id = kill_match.get("kill_id", "kill_unknown")
    n  = kill_match.get("n")
    wr = kill_match.get("wr")
    avg_pnl = kill_match.get("avg_pnl")
    active_since = kill_match.get("active_since", "?")
    cohort_label = (
        f"{signal.get('signal_type','?')} × "
        f"{signal.get('sector','?')}"
    )

    short = (
        f"Killed by {kill_id} ({cohort_label}, "
        f"{_wins_n(wr, n)} WR)"
    )

    long_parts = [
        f"Hard-blocked by {kill_id} (active since {active_since}).",
        (
            f"Cohort {cohort_label} historical n={_fmt_n(n)}, "
            f"WR {_pct(wr)}%"
            + (
                f" (avg P&L {avg_pnl:+.2f}%)."
                if isinstance(avg_pnl, (int, float)) else "."
            )
        ),
    ]
    if kill_match.get("active_shadow"):
        long_parts.append(
            "Contra-tracker has recorded an inverted shadow trade for "
            "this signal; tracking continues toward review threshold."
        )
    long = " ".join(long_parts)

    return _result(
        bucket="SKIP",
        gate="GATE_1_KILL",
        short=short,
        long=long,
        boost_match=None,
        kill_match=kill_match,
        tier_label="blocked",
        evidence=evidence,
        has_kill_match=True,
    )


# =====================================================================
# Gate 2 — validity fail
# =====================================================================

def _build_skip_validity(signal: dict,
                         validity_reason: Optional[str],
                         evidence: dict) -> dict:
    reason = validity_reason or "validity gate failed"
    rr = signal.get("rr")
    age = signal.get("age_days")
    sigtype = signal.get("signal_type", "?")

    short = f"Invalid: {reason}"

    long = (
        f"Gate 2 (validity) rejected this signal: {reason}. "
        f"Signal_type={sigtype}, age_days={_fmt_n(age)}, "
        f"R:R={_fmt_rr(rr)}. Validity gate enforces the central "
        f"rules in thresholds (min R:R, max age per signal type, "
        f"entry_valid flag at L2)."
    )

    return _result(
        bucket="SKIP",
        gate="GATE_2_VALIDITY",
        short=short,
        long=long,
        boost_match=None,
        kill_match=None,
        tier_label="blocked",
        evidence=evidence,
        has_kill_match=False,
    )


# =====================================================================
# Gate 3 — boost match (Tier A or B)
# =====================================================================

def _build_take_full_boost(signal: dict,
                           boost_match: dict,
                           evidence: dict) -> dict:
    return _build_boost_result(
        signal, boost_match, evidence,
        bucket="TAKE_FULL",
        gate="GATE_3_BOOST_A",
        tier_letter="A",
        tier_label="Tier A",
    )


def _build_take_small_boost(signal: dict,
                            boost_match: dict,
                            evidence: dict) -> dict:
    return _build_boost_result(
        signal, boost_match, evidence,
        bucket="TAKE_SMALL",
        gate="GATE_3_BOOST_B",
        tier_letter="B",
        tier_label="Tier B",
    )


def _build_boost_result(signal: dict,
                        boost_match: dict,
                        evidence: dict,
                        *,
                        bucket: str,
                        gate: str,
                        tier_letter: str,
                        tier_label: str) -> dict:
    cohort_label = (
        f"{signal.get('signal_type','?')} × "
        f"{signal.get('sector','?')} × "
        f"{signal.get('regime','?')}"
    )

    # Prefer cohort stats from evidence.exact_cohort; fall back to
    # numbers carried on the boost rule itself.
    ec = evidence.get("exact_cohort") or {}
    n = ec.get("n", boost_match.get("n"))
    wr = ec.get("wr", boost_match.get("wr"))
    avg_pnl = ec.get("avg_pnl", boost_match.get("avg_pnl"))

    rr = signal.get("rr")

    short = (
        f"Tier {tier_letter} boost: {cohort_label} "
        f"({_wins_n(wr, n)} WR)"
    )

    intro = {
        "A": "Strongest validated cohort.",
        "B": "Validated cohort, smaller-conviction tier.",
    }.get(tier_letter, "Validated cohort.")

    promotion_date = boost_match.get("promotion_date")
    promotion_clause = (
        f" Pattern entered Validated tier {promotion_date}."
        if promotion_date else ""
    )

    pnl_clause = (
        f", avg P&L {avg_pnl:+.2f}%"
        if isinstance(avg_pnl, (int, float)) else ""
    )

    counter_clause = (
        " Counter-evidence flags raised — consult evidence panel."
        if _has_counter_flags(evidence) else " No counter-evidence flags."
    )

    long = (
        f"{intro} Cohort {cohort_label} historical n={_fmt_n(n)}, "
        f"WR {_pct(wr)}%{pnl_clause}.{promotion_clause} "
        f"R:R {_fmt_rr(rr)} acceptable.{counter_clause}"
    )

    return _result(
        bucket=bucket,
        gate=gate,
        short=short,
        long=long,
        boost_match=boost_match,
        kill_match=None,
        tier_label=tier_label,
        evidence=evidence,
        has_kill_match=False,
    )


# =====================================================================
# Gate 4 — evidence consensus
# =====================================================================

def _gate4_evidence(signal: dict, evidence: dict) -> dict:
    ec = evidence.get("exact_cohort") or {}
    sec = evidence.get("sector_recent_30d") or {}
    reg = evidence.get("regime_baseline") or {}

    ec_n  = _as_num(ec.get("n"), 0)
    ec_wr = _as_num(ec.get("wr"), 0.0)
    sec_n  = _as_num(sec.get("n"), 0)
    sec_wr = _as_num(sec.get("wr"), 0.0)
    reg_wr = _as_num(reg.get("wr"), 0.0)

    has_warnings = _has_counter_flags(evidence)

    # Strong cohort → TAKE_SMALL
    if (ec_n >= COHORT_STRONG_N
            and ec_wr >= COHORT_STRONG_WR
            and not has_warnings):
        return _build_gate4_strong(signal, evidence, ec, sec)

    # Moderate cohort → WATCH
    if (ec_n >= COHORT_MODERATE_N
            and ec_wr >= COHORT_MODERATE_WR
            and sec_n >= 5
            and sec_wr >= COHORT_MODERATE_SECTOR_WR
            and not has_warnings):
        return _build_gate4_moderate(signal, evidence, ec, sec)

    # Thin fallback → WATCH
    if (ec_n < COHORT_THIN_FALLBACK_N
            and sec_wr >= _THIN_FALLBACK_SECTOR_WR
            and reg_wr >= _THIN_FALLBACK_REGIME_WR):
        return _build_gate4_thin(signal, evidence, ec, sec, reg)

    # Default → SKIP
    return _build_gate4_default_skip(
        signal, evidence, ec, sec, has_warnings)


def _build_gate4_strong(signal, evidence, ec, sec) -> dict:
    short = (
        f"Cohort strong: n={_fmt_n(ec.get('n'))} "
        f"WR {_pct(ec.get('wr'))}% in this exact context"
    )
    long = (
        f"No active boost rule for this combination, but exact cohort "
        f"(signal_type × sector × regime × age) shows "
        f"n={_fmt_n(ec.get('n'))}, WR {_pct(ec.get('wr'))}%, "
        f"avg P&L {_fmt_pnl(ec.get('avg_pnl'))}. "
        f"Sector_recent_30d also supportive at "
        f"{_pct(sec.get('wr'))}% WR (n={_fmt_n(sec.get('n'))}). "
        f"No cluster warnings, no anti-patterns detected. "
        f"Worth a smaller position based on evidence consensus."
    )
    return _result(
        bucket="TAKE_SMALL",
        gate="GATE_4_STRONG_COHORT",
        short=short, long=long,
        boost_match=None, kill_match=None,
        tier_label="strong cohort",
        evidence=evidence, has_kill_match=False,
    )


def _build_gate4_moderate(signal, evidence, ec, sec) -> dict:
    short = (
        f"Cohort moderate: n={_fmt_n(ec.get('n'))} "
        f"WR {_pct(ec.get('wr'))}%, sector "
        f"{_pct(sec.get('wr'))}%"
    )
    long = (
        f"No boost. Exact cohort n={_fmt_n(ec.get('n'))}, "
        f"WR {_pct(ec.get('wr'))}% — moderate conviction. "
        f"Sector_recent_30d supportive at "
        f"{_pct(sec.get('wr'))}% WR (n={_fmt_n(sec.get('n'))}). "
        f"No counter-evidence flags. Insufficient signal to size up; "
        f"tracking on watchlist."
    )
    return _result(
        bucket="WATCH",
        gate="GATE_4_MODERATE_COHORT",
        short=short, long=long,
        boost_match=None, kill_match=None,
        tier_label="watching",
        evidence=evidence, has_kill_match=False,
    )


def _build_gate4_thin(signal, evidence, ec, sec, reg) -> dict:
    short = (
        f"Thin cohort fallback: sector "
        f"{_pct(sec.get('wr'))}%, regime "
        f"{_pct(reg.get('wr'))}%"
    )
    long = (
        f"Exact cohort thin (n={_fmt_n(ec.get('n'))} "
        f"< {COHORT_THIN_FALLBACK_N}). Falling back to broader signals: "
        f"sector_recent_30d at {_pct(sec.get('wr'))}% WR "
        f"(n={_fmt_n(sec.get('n'))}) and regime_baseline at "
        f"{_pct(reg.get('wr'))}% WR provide directional support. "
        f"Watchlist-only — too thin to size."
    )
    return _result(
        bucket="WATCH",
        gate="GATE_4_THIN_FALLBACK",
        short=short, long=long,
        boost_match=None, kill_match=None,
        tier_label="watching (thin)",
        evidence=evidence, has_kill_match=False,
    )


def _build_gate4_default_skip(signal, evidence, ec, sec,
                              has_warnings: bool) -> dict:
    ec_n  = _as_num(ec.get("n"), 0)
    ec_wr = _as_num(ec.get("wr"), 0.0)

    short = (
        f"Insufficient evidence: n={_fmt_n(ec.get('n'))}, "
        f"WR {_pct(ec.get('wr'))}%"
    )

    # Report the actual reason this signal fell through every gate.
    causes = []
    if has_warnings:
        causes.append("counter-evidence flags present")
    if ec_n < COHORT_MODERATE_N:
        causes.append(
            f"cohort thin (n={_fmt_n(ec.get('n'))} "
            f"< {COHORT_MODERATE_N})")
    elif ec_wr < COHORT_MODERATE_WR:
        causes.append(
            f"cohort WR weak ({_pct(ec.get('wr'))}% "
            f"< {int(COHORT_MODERATE_WR * 100)}%)")
    causes.append(
        f"sector_recent_30d at {_pct(sec.get('wr'))}% WR "
        f"insufficient for thin-evidence fallback")

    long = (
        f"No boost match. "
        + "; ".join(causes)
        + ". No edge found — skipping with logged reasoning."
    )
    return _result(
        bucket="SKIP",
        gate="GATE_4_DEFAULT_SKIP",
        short=short, long=long,
        boost_match=None, kill_match=None,
        tier_label=None,
        evidence=evidence, has_kill_match=False,
    )


# =====================================================================
# Helpers
# =====================================================================

def _result(*, bucket: str, gate: str, short: str, long: str,
            boost_match: Optional[dict],
            kill_match: Optional[dict],
            tier_label: Optional[str],
            evidence: dict,
            has_kill_match: bool) -> dict:
    ec = evidence.get("exact_cohort") or {}
    return {
        "bucket": bucket,
        "bucket_reason_short": short,
        "bucket_reason_long": long,
        "gate_fired": gate,
        "boost_match": boost_match,
        "kill_match": kill_match,
        "tier_label": tier_label,
        "confidence_inputs": {
            "exact_cohort_n": ec.get("n"),
            "has_kill_match": has_kill_match,
        },
    }


def _has_counter_flags(evidence: dict) -> bool:
    cw = evidence.get("cluster_warnings") or []
    ap = evidence.get("anti_pattern_check")
    return bool(cw) or bool(ap)


def _as_num(v: Any, default: float) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    return default


def _pct(wr: Optional[float]) -> str:
    if not isinstance(wr, (int, float)):
        return "?"
    return f"{wr * 100:.0f}"


def _wins_n(wr: Optional[float], n: Optional[int]) -> str:
    if not isinstance(n, (int, float)):
        return "?/?"
    n_int = int(n)
    if not isinstance(wr, (int, float)):
        return f"?/{n_int}"
    return f"{round(wr * n_int)}/{n_int}"


def _fmt_n(n: Any) -> str:
    if isinstance(n, (int, float)):
        return str(int(n))
    return "?"


def _fmt_pnl(pnl: Any) -> str:
    if isinstance(pnl, (int, float)):
        return f"{pnl:+.2f}%"
    return "?"


def _fmt_rr(rr: Any) -> str:
    if isinstance(rr, (int, float)):
        return f"{rr:.2f}"
    return "?"
