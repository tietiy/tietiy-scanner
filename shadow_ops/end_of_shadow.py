"""shadow_ops/end_of_shadow.py — Step 10 of shadow_ops v1.

Campaign-level review document. Aggregates a complete run_dir into a single
markdown file that supports the operator's deploy/extend/abort decision.

Output: <run_dir>/review.md  +  <run_dir>/review.md.checksum

Pure aggregation. Reads from journal events + Step 7 read model + alerts +
unified_rules_v4_1_FINAL.json. No external data, no canonical imports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shadow_ops.alerts import (
    list_acknowledgments,
    list_alerts,
    Alert,
)
from shadow_ops.daily_report import _md_table  # reuse the MD table helper
from shadow_ops.daily_scan import ACTIVE_RULE_IDS, DEFAULT_RULES_PATH
from shadow_ops.journal import JournalReader
from shadow_ops.read_model import (
    OUTPUT_FILENAME as READ_MODEL_FILENAME,
    regenerate_read_model,
)


# ============================================================
# Constants
# ============================================================

REVIEW_FILENAME = "review.md"
RUN_CONFIG_FILENAME = "run_config.json"

# Recommendation flag thresholds
MIN_TRADING_DAYS_COMPARABLE = 20
MIN_CARDS_COMPARABLE = 50
MIN_CARDS_INFORMATIONAL = 20
WR_DELTA_SE_FLAG = 2.0           # |delta| > N·SE flagged as divergent
FLAT_THRESHOLD_PCT = 0.5         # mirror lifecycle.py / canonical
HISTOGRAM_BAR_WIDTH = 20

RULE_019 = "rule_019_bear_uptri_hot_refinement"
RULE_031 = "rule_031_bear_uptri_it_hot"
KILL_001 = "kill_001"

R_BUCKETS: List[tuple] = [
    ("(-∞, -1.5)",   lambda r: r < -1.5),
    ("[-1.5, -1.0)", lambda r: -1.5 <= r < -1.0),
    ("[-1.0, -0.5)", lambda r: -1.0 <= r < -0.5),
    ("[-0.5,  0.0)", lambda r: -0.5 <= r < 0.0),
    ("[ 0.0, +0.5)", lambda r: 0.0 <= r < 0.5),
    ("[+0.5, +1.0)", lambda r: 0.5 <= r < 1.0),
    ("[+1.0, +1.5)", lambda r: 1.0 <= r < 1.5),
    ("[+1.5, +2.0]", lambda r: 1.5 <= r <= 2.0),
    ("(+2.0, +∞)",   lambda r: r > 2.0),
]


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class EndOfShadowResult:
    run_dir: str
    review_path: str
    review_sha256: str           # SHA of full review.md (matches sidecar)
    body_sha256: str             # SHA of body excluding HTML-comment timestamp line
    n_scans: int
    n_cards: int
    n_closed: int
    n_open: int
    elapsed_ms: int
    status: str = "OK"


# ============================================================
# Loaders
# ============================================================

def _load_currents(run_dir: Path) -> List[dict]:
    p = run_dir / READ_MODEL_FILENAME
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _load_run_config(run_dir: Path) -> Optional[dict]:
    p = run_dir / RUN_CONFIG_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _load_audit_calibration(rules_path: Path) -> Dict[str, dict]:
    """Returns {rule_id: {expected_wr, n_audit, tier, verdict, confidence_tier}}."""
    payload = json.loads(rules_path.read_text())
    out: Dict[str, dict] = {}
    for r in payload.get("rules", []):
        if r.get("id") in ACTIVE_RULE_IDS:
            out[r["id"]] = {
                "expected_wr":     r.get("expected_wr"),
                "n_audit":         (r.get("evidence") or {}).get("n"),
                "tier":            (r.get("evidence") or {}).get("tier"),
                "verdict":         r.get("verdict"),
                "confidence_tier": r.get("confidence_tier"),
            }
    return out


# ============================================================
# Aggregation helpers
# ============================================================

def _binomial_se_pp(p_audit: Optional[float], n_shadow_closed: int) -> Optional[float]:
    """Binomial SE in percentage points: sqrt(p*(1-p)/n)*100."""
    if p_audit is None or n_shadow_closed <= 0:
        return None
    if not (0.0 <= p_audit <= 1.0):
        return None
    return math.sqrt(p_audit * (1 - p_audit) / n_shadow_closed) * 100.0


def _is_closed(c: dict) -> bool:
    return c.get("current_state") in (
        "HYPOTHETICAL_FILLED", "HYPOTHETICAL_STOPPED", "EXPIRED")


def _wr_audit_comparable(currents: List[dict]) -> Optional[float]:
    """Fraction of CLOSED cards with realized_pnl_pct ≥ 0.5%. None if 0 closed."""
    closed = [c for c in currents if _is_closed(c)]
    if not closed:
        return None
    wins = sum(1 for c in closed
               if c.get("realized_pnl_pct") is not None
               and c["realized_pnl_pct"] >= FLAT_THRESHOLD_PCT)
    return wins / len(closed)


def _mean_r(currents: List[dict]) -> Optional[float]:
    rs = [c["realized_R"] for c in currents
          if c.get("realized_R") is not None]
    if not rs:
        return None
    return sum(rs) / len(rs)


def _delta_pp(shadow_wr: Optional[float],
              audit_wr: Optional[float]) -> Optional[float]:
    if shadow_wr is None or audit_wr is None:
        return None
    return (shadow_wr - audit_wr) * 100.0


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def _fmt_num(v: Optional[float], digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}"


def _fmt_signed_pp(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:+.1f}pp"


def _fmt_pm_pp(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"±{v:.1f}pp"


# ============================================================
# Section renderers
# ============================================================

def _render_header(run_dir: Path,
                   scans: List,
                   currents: List[dict],
                   run_config: Optional[dict]) -> str:
    n_open = sum(1 for c in currents
                 if c.get("current_state") in ("PROPOSED", "ACTIVE"))
    banner = (f"⚠ {n_open} cards still open — review reflects partial cohort\n\n"
              if n_open > 0 else "")
    if scans:
        scan_dates = sorted({s.scan_date for s in scans})
        first_scan, last_scan = scan_dates[0], scan_dates[-1]
        n_trading_days = len(scan_dates)
        try:
            cal_days = (date.fromisoformat(last_scan)
                        - date.fromisoformat(first_scan)).days + 1
        except ValueError:
            cal_days = "—"
        scans_by_date = {s.scan_date: s for s in scans}
        sha_start = scans_by_date[first_scan].git_commit_sha
        sha_end = scans_by_date[last_scan].git_commit_sha
    else:
        first_scan = last_scan = "—"
        n_trading_days = cal_days = 0
        sha_start = sha_end = "—"
    cfg_present = "present" if run_config else "not present"

    head = "# Shadow Ops End-of-Run Review\n\n" + banner
    body = (
        f"- Run directory: `{run_dir}`\n"
        f"- run_config.json: {cfg_present}\n"
        f"- Campaign start (earliest scan_date): {first_scan}\n"
        f"- Campaign end   (latest scan_date):   {last_scan}\n"
        f"- Total trading days scanned: {n_trading_days}\n"
        f"- Total calendar days:        {cal_days}\n"
        f"- Git commit at run start: `{sha_start}`\n"
        f"- Git commit at run end:   `{sha_end}`"
    )
    return head + body


def _render_scan_summary(scans: List) -> str:
    if not scans:
        return ""
    n = len(scans)
    by_status = Counter(s.scan_status for s in scans)
    by_regime = Counter(s.regime for s in scans)
    by_subreg = Counter(s.sub_regime or "—" for s in scans)
    rows = [
        ["Total scans",             n],
        ["OK / PARTIAL / ERROR",    f"{by_status.get('OK', 0)} / {by_status.get('PARTIAL', 0)} / {by_status.get('ERROR', 0)}"],
        ["Regime: Bear / Bull / Choppy",
         f"{by_regime.get('Bear', 0)} / {by_regime.get('Bull', 0)} / {by_regime.get('Choppy', 0)}"],
    ]
    if by_subreg:
        rows.append(["sub_regime breakdown",
                     ", ".join(f"{k}: {v}" for k, v in sorted(by_subreg.items()))])
    return "## Scan summary\n\n" + _md_table(["Metric", "Value"], rows)


def _render_cohort_summary(currents: List[dict]) -> str:
    if not currents:
        return ""
    total = len(currents)
    by_rule = Counter(c.get("rule_id", "—") for c in currents)
    by_sector = Counter(c.get("sector", "—") for c in currents)
    top3 = by_sector.most_common(3)
    top3_str = ", ".join(
        f"{s} {n} ({n/total*100:.1f}%)" for s, n in top3) or "—"
    by_state = Counter(c.get("current_state", "—") for c in currents)
    n_open = by_state.get("PROPOSED", 0) + by_state.get("ACTIVE", 0)
    n_target = by_state.get("HYPOTHETICAL_FILLED", 0)
    n_stop = by_state.get("HYPOTHETICAL_STOPPED", 0)
    n_expired = by_state.get("EXPIRED", 0)
    n_closed = n_target + n_stop + n_expired

    rules_str = ", ".join(f"{rid}: {n}" for rid, n in by_rule.most_common())
    rows = [
        ["Total trade cards proposed",                       total],
        ["Cards by rule_id",                                  rules_str],
        ["Top 3 sectors",                                     top3_str],
        ["Currently open (PROPOSED + ACTIVE)",                n_open],
        ["Closed",                                            n_closed],
        ["Closed by terminal: TARGET / STOP / EXPIRED",
         f"{n_target} / {n_stop} / {n_expired}"],
    ]
    return "## Trade card cohort summary\n\n" + _md_table(
        ["Metric", "Value"], rows)


def _render_outcomes_by_rule(currents: List[dict],
                              audit_calibration: Dict[str, dict]) -> str:
    if not currents:
        return ""
    all_r19 = [c for c in currents if c.get("rule_id") == RULE_019]
    with_031 = [c for c in all_r19 if c.get("rule_031_confirm") == 1]
    without_031 = [c for c in all_r19 if c.get("rule_031_confirm") == 0]

    def _row(label: str, cohort: List[dict],
             audit_rule_id: Optional[str]) -> List[Any]:
        n_cards = len(cohort)
        n_closed = sum(1 for c in cohort if _is_closed(c))
        n_open = sum(1 for c in cohort
                     if c.get("current_state") in ("PROPOSED", "ACTIVE"))
        wr = _wr_audit_comparable(cohort)
        mean_r = _mean_r(cohort)
        if audit_rule_id and audit_rule_id in audit_calibration:
            aud = audit_calibration[audit_rule_id]
            audit_wr = aud["expected_wr"]
            n_audit = aud["n_audit"]
            delta = _delta_pp(wr, audit_wr)
            se = _binomial_se_pp(audit_wr, n_closed)
        else:
            audit_wr = None
            n_audit = None
            delta = None
            se = None
        return [
            label, n_cards, n_closed, n_open,
            _fmt_pct(wr), _fmt_num(mean_r),
            _fmt_pct(audit_wr),
            n_audit if n_audit is not None else "—",
            _fmt_signed_pp(delta), _fmt_pm_pp(se),
        ]

    rows = [
        _row("rule_019 (all)",                  all_r19,    RULE_019),
        _row("rule_019 + rule_031_confirm=1",   with_031,   RULE_031),
        _row("rule_019 + rule_031_confirm=0",   without_031, None),
    ]
    md = "## Outcomes by rule\n\n" + _md_table(
        ["Rule subset", "Cards", "Closed", "Open",
         "WR (≥0.5%, closed only)", "Mean R (closed only)",
         "Audit expected_wr", "n_audit", "Delta", "1-SE"], rows)
    md += ("\n\nWR and Mean R are computed over CLOSED cards only. "
           "1-SE is the binomial standard error in percentage points using "
           "the audit's expected_wr as p and shadow's n_closed.")
    return md


def _render_kill_001_section(candidates: List,
                              audit_calibration: Dict[str, dict]) -> str:
    suppressed = [c for c in candidates if c.kill_001_match]
    n_total = len(suppressed)
    sym_counter = Counter(c.symbol for c in suppressed)
    top5 = sym_counter.most_common(5)
    aud = audit_calibration.get(KILL_001, {})
    audit_wr = aud.get("expected_wr")
    n_audit = aud.get("n_audit")
    parts = ["## kill_001 suppressions (operational diagnostic)\n"]
    parts.append(f"- Total suppressions across run: **{n_total}**")
    if top5:
        top_str = ", ".join(f"{s} ({n})" for s, n in top5)
        parts.append(f"- Top 5 suppressed symbols: {top_str}")
    if audit_wr is not None and n_audit is not None:
        parts.append(f"- Audit expected_wr if NOT suppressed: "
                     f"{audit_wr * 100:.1f}% (lifetime calibrated, n={n_audit})")
    parts.append(
        "- Interpretation: kill_001 suppresses DOWN_TRI / Bear / Bank signals "
        "that the audit calibrated as losing trades. Suppressions are operational "
        "visibility, not performance.")
    return "\n".join(parts)


def _render_sector_distribution(currents: List[dict]) -> str:
    if not currents:
        return ""
    by_sector: Dict[str, List[dict]] = {}
    for c in currents:
        by_sector.setdefault(c.get("sector", "—"), []).append(c)
    rows = []
    for sector, cohort in sorted(by_sector.items(),
                                  key=lambda kv: -len(kv[1])):
        n_cards = len(cohort)
        n_closed = sum(1 for c in cohort if _is_closed(c))
        wr = _wr_audit_comparable(cohort)
        mean_r = _mean_r(cohort)
        rows.append([sector, n_cards, n_closed,
                     _fmt_pct(wr), _fmt_num(mean_r)])
    return ("## Sector distribution of outcomes\n\n"
            + _md_table(
                ["Sector", "Cards", "Closed",
                 "WR (≥0.5%, closed only)", "Mean R (closed only)"],
                rows))


def _render_r_histogram(currents: List[dict]) -> str:
    closed = [c for c in currents if _is_closed(c)
              and c.get("realized_R") is not None]
    if not closed:
        return ""
    n = len(closed)
    counts = []
    for label, pred in R_BUCKETS:
        c = sum(1 for x in closed if pred(x["realized_R"]))
        counts.append((label, c))
    max_count = max(c for _, c in counts) or 1
    lines = [f"## realized_R distribution (closed cards only, N={n})\n",
             "```"]
    label_w = max(len(label) for label, _ in counts)
    for label, count in counts:
        bar = "#" * int(HISTOGRAM_BAR_WIDTH * count / max_count)
        lines.append(f"{label:<{label_w}}  {count:>4}  | {bar}")
    lines.append("```")
    return "\n".join(lines)


def _render_alerts_summary(alerts: List[Alert],
                           acks: List[dict]) -> str:
    if not alerts:
        return ""
    by_sev = Counter(a.severity for a in alerts)
    acked_ids = {a.get("alert_id") for a in acks}
    n_crit = by_sev.get("CRITICAL", 0)
    n_crit_acked = sum(1 for a in alerts
                       if a.severity == "CRITICAL" and a.alert_id in acked_ids)
    rows = [
        ["CRITICAL", by_sev.get("CRITICAL", 0),
         f"{n_crit_acked} / {n_crit}" if n_crit > 0 else "—"],
        ["WARNING",  by_sev.get("WARNING", 0), "—"],
        ["INFO",     by_sev.get("INFO", 0),    "—"],
    ]
    md = "## Alerts summary\n\n" + _md_table(
        ["Severity", "Count", "Acknowledged"], rows)
    unacked_crit = [a for a in alerts
                    if a.severity == "CRITICAL" and a.alert_id not in acked_ids]
    if unacked_crit:
        md += "\n\n### Unacknowledged CRITICAL alerts\n\n"
        for a in unacked_crit:
            md += f"- `{a.alert_id}` — {a.alert_type} — {a.message}\n"
    return md


def _render_data_quality(scans: List, alerts: List[Alert]) -> str:
    n_partial_scans = sum(1 for s in scans if s.scan_status == "PARTIAL")
    n_error_scans = sum(1 for s in scans if s.scan_status == "ERROR")
    by_atype = Counter(a.alert_type for a in alerts)

    failed_symbols: List[str] = []
    for a in alerts:
        if a.alert_type == "DATA_INGEST_FAILURE":
            for entry in a.context.get("failed_symbols", []):
                # Each entry may be a (symbol, reason) tuple or just a symbol
                if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                    failed_symbols.append(str(entry[0]))
                elif isinstance(entry, str):
                    failed_symbols.append(entry)
    top_failed = Counter(failed_symbols).most_common(5)

    rows = [
        ["Scans with PARTIAL status", n_partial_scans],
        ["Scans with ERROR status",   n_error_scans],
        ["DATA_INGEST_FAILURE alerts", by_atype.get("DATA_INGEST_FAILURE", 0)],
        ["DATA_INGEST_PARTIAL alerts", by_atype.get("DATA_INGEST_PARTIAL", 0)],
        ["DATA_INGEST_STALE alerts",   by_atype.get("DATA_INGEST_STALE", 0)],
        ["PARQUET_SHA_DRIFT alerts",   by_atype.get("PARQUET_SHA_DRIFT", 0)],
        ["LIFECYCLE_ERROR alerts",     by_atype.get("LIFECYCLE_ERROR", 0)],
        ["LIFECYCLE_DAY_GAP alerts",   by_atype.get("LIFECYCLE_DAY_GAP", 0)],
    ]
    md = "## Data quality issues\n\n" + _md_table(["Metric", "Count"], rows)
    if top_failed:
        md += "\n\n**Top failed symbols (across DATA_INGEST_FAILURE contexts):** "
        md += ", ".join(f"{s} ({n})" for s, n in top_failed)
    return md


def _significance_label(n_closed: int) -> str:
    if n_closed >= MIN_CARDS_COMPARABLE:
        return "comparable scale"
    if n_closed >= MIN_CARDS_INFORMATIONAL:
        return "informational"
    return "below threshold"


def _render_recommendation_flags(scans: List,
                                  currents: List[dict],
                                  alerts: List[Alert],
                                  acks: List[dict],
                                  audit_calibration: Dict[str, dict]) -> str:
    n_scan_dates = len({s.scan_date for s in scans}) if scans else 0
    total_cards = len(currents)
    closed = [c for c in currents if _is_closed(c)]
    n_closed = len(closed)
    n_open = sum(1 for c in currents
                 if c.get("current_state") in ("PROPOSED", "ACTIVE"))

    # rule_019 WR delta + SE → divergence flag
    r19 = [c for c in currents if c.get("rule_id") == RULE_019]
    r19_closed = sum(1 for c in r19 if _is_closed(c))
    r19_wr = _wr_audit_comparable(r19)
    aud19 = audit_calibration.get(RULE_019, {})
    audit_wr19 = aud19.get("expected_wr")
    delta_pp = _delta_pp(r19_wr, audit_wr19)
    se_pp = _binomial_se_pp(audit_wr19, r19_closed)
    if delta_pp is None or se_pp is None or se_pp == 0:
        delta_status = "n/a"
        delta_value = "—"
    else:
        ratio = abs(delta_pp) / se_pp
        if ratio > WR_DELTA_SE_FLAG:
            delta_status = f"divergent (~{ratio:.1f} SE)"
        else:
            delta_status = f"within ±{WR_DELTA_SE_FLAG:.0f} SE"
        delta_value = f"{delta_pp:+.1f}pp"

    # Unacked CRITICAL count
    acked_ids = {a.get("alert_id") for a in acks}
    n_unacked_crit = sum(1 for a in alerts
                         if a.severity == "CRITICAL"
                         and a.alert_id not in acked_ids)

    # Status labels
    days_status = ("comparable scale"
                   if n_scan_dates >= MIN_TRADING_DAYS_COMPARABLE
                   else "below threshold")
    cards_status = _significance_label(total_cards)
    closed_status = _significance_label(n_closed)
    open_status = "clean" if n_open == 0 else f"{n_open} still open"
    crit_status = "clean" if n_unacked_crit == 0 else "investigate"

    rows = [
        ["Trading days observed",          n_scan_dates,
         f"≥ {MIN_TRADING_DAYS_COMPARABLE}",  days_status],
        ["Total trade cards",               total_cards,
         f"≥ {MIN_CARDS_COMPARABLE}",         cards_status],
        ["Closed cards",                    n_closed,
         f"≥ {MIN_CARDS_COMPARABLE}",         closed_status],
        ["Currently still open",            n_open,
         "== 0",                              open_status],
        ["WR delta from audit (rule_019)",  delta_value,
         f"|delta| ≤ {WR_DELTA_SE_FLAG:.0f}·SE",  delta_status],
        ["Unacknowledged CRITICAL alerts",  n_unacked_crit,
         "== 0",                              crit_status],
    ]
    md = ("## Recommendation flags\n\n"
          "(Decision support only — operator decides deploy / extend / abort.)\n\n"
          + _md_table(["Flag", "Value", "Threshold", "Status"], rows))
    return md


def _render_footer_timestamp(now_iso: Optional[str] = None) -> str:
    ts = now_iso or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"<!-- review_generated_at: {ts} -->"


# ============================================================
# Atomic write + sidecar
# ============================================================

def _strip_timestamp_line(md: str) -> str:
    """Remove `<!-- review_generated_at: ... -->` line(s) for body comparison."""
    return "\n".join(l for l in md.splitlines()
                     if not l.lstrip().startswith("<!-- review_generated_at:"))


def _atomic_write_md(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return sha


def _write_checksum_sidecar(path: Path, sha_hex: str) -> None:
    Path(str(path) + ".checksum").write_text(sha_hex)


# ============================================================
# Public API
# ============================================================

def generate_review(run_dir: Path,
                    regenerate_read_model_first: bool = True,
                    rules_path: Path = DEFAULT_RULES_PATH) -> str:
    """Build markdown text. Doesn't write to disk."""
    run_dir = Path(run_dir)
    if regenerate_read_model_first:
        regenerate_read_model(run_dir)

    reader = JournalReader(run_dir)
    scans = reader.all_scan_events()
    candidates = reader.all_candidate_signals()
    currents = _load_currents(run_dir)
    alerts = list_alerts(run_dir)
    acks = list_acknowledgments(run_dir)
    audit_calibration = _load_audit_calibration(rules_path)
    run_config = _load_run_config(run_dir)

    parts: List[str] = [
        _render_header(run_dir, scans, currents, run_config),
        _render_scan_summary(scans),
        _render_cohort_summary(currents),
        _render_outcomes_by_rule(currents, audit_calibration),
        _render_kill_001_section(candidates, audit_calibration),
        _render_sector_distribution(currents),
        _render_r_histogram(currents),
        _render_alerts_summary(alerts, acks),
        _render_data_quality(scans, alerts),
        _render_recommendation_flags(scans, currents, alerts, acks,
                                      audit_calibration),
        _render_footer_timestamp(),
    ]
    return "\n\n".join(p for p in parts if p) + "\n"


def write_review(run_dir: Path,
                 out_path: Optional[Path] = None,
                 regenerate_read_model_first: bool = True,
                 rules_path: Path = DEFAULT_RULES_PATH) -> EndOfShadowResult:
    """Generate review markdown + write to disk + update sidecar."""
    t0 = time.monotonic()
    run_dir = Path(run_dir)
    md = generate_review(run_dir, regenerate_read_model_first, rules_path)
    target = Path(out_path) if out_path else run_dir / REVIEW_FILENAME
    full_sha = _atomic_write_md(target, md)
    _write_checksum_sidecar(target, full_sha)
    body_sha = hashlib.sha256(_strip_timestamp_line(md).encode("utf-8")).hexdigest()

    # Counts for the result
    reader = JournalReader(run_dir)
    n_scans = len(reader.all_scan_events())
    currents = _load_currents(run_dir)
    n_cards = len(currents)
    n_closed = sum(1 for c in currents if _is_closed(c))
    n_open = sum(1 for c in currents
                 if c.get("current_state") in ("PROPOSED", "ACTIVE"))

    return EndOfShadowResult(
        run_dir=str(run_dir),
        review_path=str(target),
        review_sha256=full_sha,
        body_sha256=body_sha,
        n_scans=n_scans,
        n_cards=n_cards,
        n_closed=n_closed,
        n_open=n_open,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
        status="OK",
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops end-of-shadow review")
    ap.add_argument("--run-dir", type=str, required=True)
    ap.add_argument("--out", type=str, default=None,
                    help="path to write markdown; default <run_dir>/review.md")
    ap.add_argument("--no-regen", action="store_true",
                    help="skip Step 7 read-model regeneration")
    args = ap.parse_args()

    try:
        result = write_review(
            run_dir=Path(args.run_dir),
            out_path=Path(args.out) if args.out else None,
            regenerate_read_model_first=not args.no_regen,
        )
    except Exception:
        traceback.print_exc()
        return 2

    print(json.dumps(asdict(result), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
