"""Brain derive — materialize 4 derived views from truth files.

No LLM, no proposals yet — pure-Python deterministic logic per
brain_design_v1.md §1 constraint 3 + §4 Step 3.

Derivers:
  - derive_cohort_health(history) → cohort_health.json
  - derive_regime_watch(history, weekly_intelligence) → regime_watch.json
  - derive_portfolio_exposure(truth, output_dir) → portfolio_exposure.json
  - derive_ground_truth_gaps(history, mini_rules, patterns) → ground_truth_gaps.json

Per-deriver failure isolation (P-10): one deriver crashing leaves the
other 3 written. Idempotency (P-8): running twice same day produces
identical output except generated_at.

R-multiple: imports canonical _calc_r_multiple from outcome_evaluator
(per Step 3 design audit C-1; same pattern as recover_stuck_signals.py).
Standing warning r_multiple_under_day6_dominance fires once per run if
any cohort reaches n>=15 (per locked C-3 trigger).

Tier classifier rules locked verbatim from brain_design §3 (S/M/W/Candidate
with R-multiple gates for S/M).

See doc/brain_design_v1.md §3 (tier classifier) + §4 Step 3 (deriver
contracts) + project_anchor_v1.md §6.8 (signal_history vs patterns count).
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from statistics import mean
from typing import Optional

from scanner.brain import brain_input, brain_state
from scanner.outcome_evaluator import _calc_r_multiple


_IST = timezone(timedelta(hours=5, minutes=30))
_WIN_OUTCOMES = {"TARGET_HIT", "DAY6_WIN"}
_LOSS_OUTCOMES = {"STOP_HIT", "DAY6_LOSS"}
_FLAT_OUTCOMES = {"DAY6_FLAT"}
_N_MIN_FOR_INCLUSION = 3
_N_MIN_FOR_TIER_W = 10
_N_MIN_FOR_TIER_M = 15
_N_MIN_FOR_TIER_S = 25
_N_MIN_FOR_TEMPORAL_SPLIT = 10
_N_MIN_FOR_R_MULT_WARNING = 15  # C-3 trigger: any cohort n>=15 → warning
_THIN_RULE_THRESHOLD = 5
_CONCENTRATION_THRESHOLD_SHARE = 0.10
_REGIME_CONCENTRATION_THRESHOLD_SHARE = 0.80
_WILSON_Z_95 = 1.96


def run_all(output_dir: str = "output",
            data_dir: str = "data") -> dict:
    """
    Loads truth files once, runs 4 derivers, writes 4 JSONs via
    brain_state. Returns {"views": {...}, "errors": [...]}.

    Per P-10: each deriver failure isolated; other derivers complete.
    """
    truth = brain_input.load_truth_files(output_dir, data_dir)
    history = (truth.get("signal_history") or {}).get("history", []) or []
    weekly_intel = truth.get("weekly_intelligence", {}) or {}
    mini_rules = truth.get("mini_scanner_rules", {}) or {}
    patterns = truth.get("patterns", {}) or {}

    views = {}
    errors = []
    derivers = [
        ("cohort_health",       _derive_cohort_health,       (history,)),
        ("regime_watch",        _derive_regime_watch,        (history, weekly_intel)),
        ("portfolio_exposure",  _derive_portfolio_exposure,  (history, output_dir)),
        ("ground_truth_gaps",   _derive_ground_truth_gaps,   (history, mini_rules, patterns)),
    ]
    for name, fn, args in derivers:
        try:
            data = fn(*args)
            result = brain_state.write_brain_artifact(name, data, output_dir)
            views[name] = result
        except Exception as e:
            errors.append({"view": name, "error": f"{type(e).__name__}: {e}"})
            print(f"[brain_derive] ERROR in {name}: {type(e).__name__}: {e}",
                  file=sys.stderr)
    return {"views": views, "errors": errors}


# =====================================================================
# Helpers
# =====================================================================

def _today_ist_date() -> str:
    return datetime.now(_IST).date().isoformat()


def _cohort_id(filter_dict: dict) -> str:
    """Deterministic, human-readable, sorted-keys, no collision possible."""
    parts = [f"{k}={filter_dict[k]}" for k in sorted(filter_dict.keys())]
    return "__".join(parts)


def _wilson_lower_bound(wins: int, n: int) -> float:
    """Wilson 95% lower bound per brain_design §3 formula.

    (p̂ + z²/(2n) − z·sqrt((p̂(1−p̂) + z²/(4n))/n)) / (1 + z²/n)
    with z = 1.96.
    """
    if n <= 0:
        return 0.0
    p = wins / n
    z = _WILSON_Z_95
    z2 = z * z
    numer = p + z2 / (2 * n) - z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    denom = 1 + z2 / n
    return round(numer / denom, 4)


def _outcome_counts(records: list) -> tuple[int, int, int]:
    """(wins, losses, flat) per WIN/LOSS/FLAT outcome enums."""
    w = sum(1 for r in records if r.get("outcome") in _WIN_OUTCOMES)
    l = sum(1 for r in records if r.get("outcome") in _LOSS_OUTCOMES)
    f = sum(1 for r in records if r.get("outcome") in _FLAT_OUTCOMES)
    return w, l, f


def _r_multiple_for_record(r: dict) -> Optional[float]:
    """Read pre-computed r_multiple if present; otherwise compute via
    canonical _calc_r_multiple. Returns None if computation fails.
    """
    if r.get("r_multiple") is not None:
        try:
            return float(r["r_multiple"])
        except (TypeError, ValueError):
            return None
    # Recompute via canonical formula
    return _calc_r_multiple(
        r.get("entry"),
        r.get("stop"),
        r.get("outcome_price"),
        r.get("direction"),
        outcome_type=r.get("outcome"),
    )


def _cohort_r_multiple(records: list) -> tuple[Optional[float], int]:
    """Returns (mean R-multiple rounded to 2 decimals, count of records
    contributing). None if no records have computable r_multiple.
    """
    rs = []
    for r in records:
        v = _r_multiple_for_record(r)
        if v is not None:
            rs.append(v)
    if not rs:
        return None, 0
    return round(mean(rs), 2), len(rs)


def _temporal_split_drift_pp(records: list) -> Optional[float]:
    """First-half WR minus second-half WR (in pp). Records sorted by
    outcome_date ascending. Returns None if n<10 (per locked threshold).
    """
    if len(records) < _N_MIN_FOR_TEMPORAL_SPLIT:
        return None
    sorted_recs = sorted(records, key=lambda r: r.get("outcome_date") or "")
    half = len(sorted_recs) // 2
    first, second = sorted_recs[:half], sorted_recs[half:]
    fw, fl, ff = _outcome_counts(first)
    sw, sl, sf = _outcome_counts(second)
    f_total = fw + fl + ff
    s_total = sw + sl + sf
    if f_total == 0 or s_total == 0:
        return None
    f_wr = fw / f_total
    s_wr = sw / s_total
    return round((f_wr - s_wr) * 100, 1)


def _classify_tier(stats: dict) -> str:
    """Verbatim from brain_design §3 + project_anchor §3 tier rules.

    Tier S: n>=25 AND wr>=0.85 AND wilson>=0.75 AND edge>=20pp
            AND r_mult>=1.0 AND |drift|<=10pp
    Tier M: n>=15 AND wr>=0.75 AND wilson>=0.65 AND edge>=10pp AND r_mult>=0.5
    Tier W: n>=10 AND wr>=0.65 AND edge>=5pp
    Candidate: n<10 OR (n>=10 AND (wr<0.65 OR edge<5))
    """
    n = stats["n"]
    wr = stats["wr"]
    wilson = stats["wr_wilson_lower"]
    edge = stats["edge_vs_baseline_pp"]
    r_mult = stats.get("r_multiple")  # may be None
    drift = stats.get("first_half_minus_second_half_wr_pp")  # may be None

    if n < _N_MIN_FOR_TIER_W:
        return "Candidate"
    if wr < 0.65 or edge < 5:
        return "Candidate"
    # n >= 10 AND wr >= 0.65 AND edge >= 5 → at least Tier W
    if (n >= _N_MIN_FOR_TIER_S and wr >= 0.85 and wilson is not None
            and wilson >= 0.75 and edge >= 20
            and r_mult is not None and r_mult >= 1.0
            and drift is not None and abs(drift) <= 10):
        return "S"
    if (n >= _N_MIN_FOR_TIER_M and wr >= 0.75 and wilson is not None
            and wilson >= 0.65 and edge >= 10
            and r_mult is not None and r_mult >= 0.5):
        return "M"
    return "W"


def _compute_signal_type_baseline(history: list, signal_type: str) -> dict:
    """Per-signal-type baseline (filter signal == X, outcome != OPEN)."""
    sub = [r for r in history
           if r.get("signal") == signal_type
           and (r.get("outcome") or "OPEN") != "OPEN"]
    n = len(sub)
    w, l, f = _outcome_counts(sub)
    total = w + l + f
    wr = round(w / total, 4) if total > 0 else 0.0
    pnls = [r.get("pnl_pct") for r in sub if r.get("pnl_pct") is not None]
    avg_pnl = round(mean(pnls), 2) if pnls else 0.0
    return {"n": n, "wr": wr, "avg_pnl_pct": avg_pnl}


# =====================================================================
# Derivers
# =====================================================================

def _derive_cohort_health(history: list) -> dict:
    """Cohort health view. 2 axes: signal+regime, signal+sector. Per
    K-1 lock + brain_design §3 tier classifier."""
    resolved = [r for r in history if (r.get("outcome") or "OPEN") != "OPEN"]

    # Per-signal-type baselines (computed once)
    signal_types = sorted({r.get("signal") for r in resolved if r.get("signal")})
    baselines = {st: _compute_signal_type_baseline(history, st)
                 for st in signal_types}

    cohorts = []
    by_axis = {
        "signal+regime": ("signal_type", "regime"),
        "signal+sector": ("signal_type", "sector"),
    }
    for axis_name, (k1, k2) in by_axis.items():
        # k1 maps to record field 'signal' (k2 maps directly)
        groups = defaultdict(list)
        for r in resolved:
            sig = r.get("signal")
            other_field = "regime" if axis_name == "signal+regime" else "sector"
            other = r.get(other_field)
            if sig and other:
                groups[(sig, other)].append(r)

        for (sig, other), members in sorted(groups.items()):
            n = len(members)
            if n < _N_MIN_FOR_INCLUSION:
                continue
            other_field = "regime" if axis_name == "signal+regime" else "sector"
            cohort_filter = {"signal_type": sig, other_field: other}
            cohort_id = _cohort_id(cohort_filter)
            w, l, f = _outcome_counts(members)
            total_outcomes = w + l + f
            wr = round(w / total_outcomes, 4) if total_outcomes > 0 else 0.0
            wilson = _wilson_lower_bound(w, total_outcomes)
            pnls = [r.get("pnl_pct") for r in members if r.get("pnl_pct") is not None]
            avg_pnl = round(mean(pnls), 2) if pnls else 0.0
            r_mult, r_mult_count = _cohort_r_multiple(members)
            baseline = baselines.get(sig, {"wr": 0.0})
            edge_pp = round((wr - baseline["wr"]) * 100, 1)

            entry = {
                "cohort_id": cohort_id,
                "cohort_axis": axis_name,
                "cohort_filter": cohort_filter,
                "n": n,
                "wins": w,
                "losses": l,
                "flat": f,
                "wr": wr,
                "wr_wilson_lower": wilson,
                "avg_pnl_pct": avg_pnl,
                "edge_vs_baseline_pp": edge_pp,
            }
            if r_mult is not None:
                entry["r_multiple"] = r_mult
                entry["r_multiple_count"] = r_mult_count

            # tier classification needs drift only for Tier S
            drift = _temporal_split_drift_pp(members)
            stats_for_tier = dict(entry)
            stats_for_tier["first_half_minus_second_half_wr_pp"] = drift
            tier = _classify_tier(stats_for_tier)
            entry["tier"] = tier
            # Per K-2: drift field present only when tier == "S"
            if tier == "S" and drift is not None:
                entry["first_half_minus_second_half_wr_pp"] = drift
            cohorts.append(entry)

    cohorts.sort(key=lambda c: c["cohort_id"])

    # Aggregate r_multiple across all resolved records (per user spec)
    all_r = []
    for r in resolved:
        v = _r_multiple_for_record(r)
        if v is not None:
            all_r.append(v)
    aggregate_r_mult = round(mean(all_r), 2) if all_r else None

    # C-3 standing warning: fires once if any cohort n>=15
    warnings = []
    if any(c["n"] >= _N_MIN_FOR_R_MULT_WARNING for c in cohorts):
        warnings.append({
            "level": "warn",
            "code": "r_multiple_under_day6_dominance",
            "message": ("R-multiple thresholds for Tier S/M classification "
                        "are under review per exit_logic_redesign track "
                        "(D-8). 35/36 of Apr-27 resolutions exited via "
                        "Day-6 forced exit, capping observable R-multiple. "
                        "Tier S/M may underclassify cohorts."),
            "context": {
                "decision_ref": "project_anchor_v1.md §7 D-8",
                "drift_audit_commit": "c278a32",
                "evidence": "35/36 Apr-27 resolutions via Day-6 forced exit",
            }
        })

    return {
        "as_of_date": _today_ist_date(),
        "_metadata": {
            "n_min_for_inclusion": _N_MIN_FOR_INCLUSION,
            "wilson_confidence": 0.95,
            "tier_classifier_ref": "doc/brain_design_v1.md §3",
            "axes_evaluated": ["signal+regime", "signal+sector"],
            "source_files": ["signal_history.json"],
            "cohort_aggregate_r_multiple_mean": aggregate_r_mult,
            "warnings": warnings,
        },
        "total_resolved": len(resolved),
        "baselines": baselines,
        "cohorts": cohorts,
        "_ext": {},
    }


def _derive_regime_watch(history: list, weekly_intel: dict) -> dict:
    """Regime watch view per K/N locks. Reads weekly_intelligence as
    authoritative current regime + slope/ret20."""
    regime_block = weekly_intel.get("regime", {}) or {}
    latest = regime_block.get("latest", {}) or {}
    current_regime = latest.get("regime") or "Unknown"
    weekly_intel_source_date = latest.get("date") or weekly_intel.get("generated_at", "")[:10]

    # 7-day distribution windows from signal_history (by signal date)
    today = datetime.now(_IST).date()
    sorted_dates = sorted(
        {r.get("date") for r in history if r.get("date")},
        reverse=True
    )
    recent_7 = sorted_dates[:7]
    prior_7 = sorted_dates[7:14]

    def regime_count_for_dates(dates):
        ct = Counter()
        for d in dates:
            for r in history:
                if r.get("date") == d and r.get("regime"):
                    ct[r["regime"]] += 1
                    break  # one entry per date
        return dict(ct)

    recent_dist = regime_count_for_dates(recent_7)
    prior_dist = regime_count_for_dates(prior_7)

    # Stability classifier
    if recent_7 and len(set(
        next((r.get("regime") for r in history if r.get("date") == d
              and r.get("regime")), None)
        for d in recent_7
    ) - {None}) == 1:
        stability = "stable"
    elif len(recent_dist) > 1:
        stability = "shifting"
    else:
        stability = "unclear"

    days_in_current = sum(1 for d in recent_7
                          if any(r.get("date") == d
                                 and r.get("regime") == current_regime
                                 for r in history))

    age_days = None
    try:
        src_dt = datetime.strptime(weekly_intel_source_date[:10], "%Y-%m-%d").date()
        age_days = (today - src_dt).days
    except (ValueError, TypeError):
        age_days = None

    warnings = []
    if age_days is not None and age_days > 7:
        warnings.append({
            "level": "warn",
            "code": "weekly_intel_stale",
            "message": f"weekly_intelligence dated {weekly_intel_source_date}; {age_days} days stale",
            "context": {"source_date": weekly_intel_source_date, "age_days": age_days},
        })

    return {
        "as_of_date": _today_ist_date(),
        "_metadata": {
            "stability_classifier": ("stable if same regime ≥5 of last 5 trading days; "
                                     "shifting if any regime change in last 7 trading days; "
                                     "unclear otherwise"),
            "source_files": ["signal_history.json", "weekly_intelligence_latest.json"],
            "warnings": warnings,
        },
        "current_regime": current_regime,
        "regime_stability": stability,
        "days_in_current_regime": days_in_current,
        "recent_distribution_7d": recent_dist,
        "prior_distribution_7d": prior_dist,
        "weekly_intelligence_snapshot": {
            "slope": latest.get("slope"),
            "avg_ret20": latest.get("ret20"),
            "above_ema50": latest.get("above_ema50"),
            "source_date": weekly_intel_source_date,
        },
        "weekly_intelligence_age_days": age_days,
        "transition_evidence": [],
        "_ext": {},
    }


def _derive_portfolio_exposure(history: list, output_dir: str) -> dict:
    """Portfolio exposure view.

    Reads bridge_state_history EOD archive primary + signal_history fallback.
    Rationale: bridge L4 archive's open_positions[] reflects 6-day-trading-window
    filter; signal_history outcome=='OPEN' includes records with M-13 oddity
    (outcome_date set but outcome still OPEN). Bridge alignment preferred for
    portfolio metrics; signal_history fallback used only when archive missing
    (e.g., manual dispatch days) with warnings.degraded_input flag set.
    """
    today_iso = _today_ist_date()
    archive_path = os.path.join(output_dir, "bridge_state_history",
                                f"{today_iso}_EOD.json")
    open_records = []
    active_source = "primary"
    warnings = []

    if os.path.exists(archive_path):
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                archive = json.load(f)
            open_records = archive.get("open_positions", []) or []
        except (json.JSONDecodeError, OSError) as e:
            warnings.append({
                "level": "warn",
                "code": "eod_archive_unreadable",
                "message": f"bridge L4 archive {archive_path} unreadable; falling back to signal_history",
                "context": {"error": f"{type(e).__name__}: {e}"},
            })
            open_records = [r for r in history if (r.get("outcome") or "OPEN") == "OPEN"]
            active_source = "fallback"
    else:
        warnings.append({
            "level": "warn",
            "code": "eod_archive_missing",
            "message": f"bridge L4 archive missing for {today_iso}; falling back to signal_history filter",
            "context": {"expected_path": archive_path},
        })
        open_records = [r for r in history if (r.get("outcome") or "OPEN") == "OPEN"]
        active_source = "fallback"

    total = len(open_records)
    by_signal_type = Counter()
    by_sector = Counter()
    by_regime = Counter()
    by_3way = Counter()
    for r in open_records:
        sig = r.get("signal") or r.get("signal_type")
        sec = r.get("sector")
        reg = r.get("regime")
        if sig: by_signal_type[sig] += 1
        if sec: by_sector[sec] += 1
        if reg: by_regime[reg] += 1
        if sig and reg and sec:
            by_3way[(sig, reg, sec)] += 1

    concentrations = []
    for (sig, reg, sec), count in by_3way.most_common():
        share = round(count / total, 4) if total > 0 else 0.0
        if share >= _CONCENTRATION_THRESHOLD_SHARE:
            concentrations.append({
                "concentration_label": f"{sig} × {reg} × {sec}",
                "concentration_filter": {"signal_type": sig, "regime": reg, "sector": sec},
                "count": count,
                "share": share,
            })

    # Always-present regime_concentration object per K-3 lock
    if total > 0 and by_regime:
        dom_regime, dom_count = by_regime.most_common(1)[0]
        observed = round(dom_count / total, 4)
    else:
        dom_regime, observed = None, 0.0
    triggered = observed >= _REGIME_CONCENTRATION_THRESHOLD_SHARE
    regime_concentration = {
        "triggered": triggered,
        "threshold": _REGIME_CONCENTRATION_THRESHOLD_SHARE,
        "observed": observed,
        "axis": "by_regime",
    }
    if triggered and dom_regime:
        regime_concentration["dominant_regime"] = dom_regime

    return {
        "as_of_date": today_iso,
        "_metadata": {
            "concentration_threshold_share": _CONCENTRATION_THRESHOLD_SHARE,
            "regime_concentration_threshold_share": _REGIME_CONCENTRATION_THRESHOLD_SHARE,
            "primary_source": "bridge_state_history/<as_of_date>_EOD.json",
            "fallback_source": "signal_history.json (filter outcome==OPEN)",
            "active_source": active_source,
            "warnings": warnings,
        },
        "total_open": total,
        "by_signal_type": dict(by_signal_type),
        "by_sector": dict(by_sector),
        "by_regime": dict(by_regime),
        "regime_concentration": regime_concentration,
        "concentrations": concentrations,
        "_ext": {},
    }


def _derive_ground_truth_gaps(history: list, mini_rules: dict, patterns: dict) -> dict:
    """Ground-truth gaps: thin rules + thin patterns."""
    thin_rules = []
    rule_kinds = ("boost_patterns", "kill_patterns", "watch_patterns", "warn_patterns")
    for kind in rule_kinds:
        for rule in mini_rules.get(kind, []) or []:
            if not isinstance(rule, dict):
                continue
            ev = rule.get("evidence", {}) or {}
            n = ev.get("n")
            if n is None:
                continue
            try:
                n_int = int(n)
            except (TypeError, ValueError):
                continue
            if n_int < _THIN_RULE_THRESHOLD:
                thin_rules.append({
                    "rule_source_kind": kind.rstrip("s"),
                    "rule_id": rule.get("id", "?"),
                    "n": n_int,
                    "cohort_filter": {
                        k: rule.get(k) for k in ("signal", "sector", "regime")
                        if rule.get(k) is not None
                    },
                })

    thin_patterns = []
    for p in patterns.get("patterns", []) or []:
        if not isinstance(p, dict):
            continue
        n = p.get("n")
        try:
            n_int = int(n) if n is not None else None
        except (TypeError, ValueError):
            n_int = None
        if n_int is not None and n_int < 10:  # below preliminary tier
            thin_patterns.append({
                "pattern_id": p.get("pattern_id") or p.get("id") or "?",
                "n": n_int,
                "tier": "below_preliminary" if n_int < 10 else (p.get("tier") or "preliminary"),
            })

    return {
        "as_of_date": _today_ist_date(),
        "_metadata": {
            "n_threshold_thin": _THIN_RULE_THRESHOLD,
            "source_files": ["signal_history.json", "mini_scanner_rules.json", "patterns.json"],
            "warnings": [],
        },
        "thin_rules": thin_rules,
        "thin_patterns": thin_patterns,
        "summary": {
            "n_thin_rules": len(thin_rules),
            "n_thin_patterns": len(thin_patterns),
        },
        "_ext": {},
    }
