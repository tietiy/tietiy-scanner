"""shadow_ops/daily_report.py — Step 8 of shadow_ops v1.

Generate a markdown digest for an eval_date. Pure presentation over the event
log + Step 7 read model. No external data, no canonical imports.

Operator runs this after daily_scan + lifecycle for the day to see:
  - Today's scan summary
  - Today's transitions (entries, stops, targets, expiries)
  - Open cards (PROPOSED + ACTIVE)
  - Cumulative cohort outcomes since run start
  - Alerts (from alerts.jsonl if present)
  - Regime trend (last 5 scans)
  - Data lineage check

LOGICAL DATE FOR LIFECYCLE EVENTS:
  timestamp_utc is wall-clock — could be the next UTC day if the operator runs
  lifecycle late. We use the associated FillSimulation.fill_date as the
  logical date instead. Every audit-faithful lifecycle event (Step 5+) carries
  fill_event_id in trigger_data; verified across all 4 emit helpers in
  lifecycle.py.

Default output: <run_dir>/reports/<eval_date>.md.
Pass --stdout to print to terminal instead.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from shadow_ops.journal import JournalReader
from shadow_ops.schemas import (
    FillSimulation,
    LifecycleEvent,
    ScanEvent,
)


# ============================================================
# Constants
# ============================================================

CURRENTS_FILENAME = "trade_cards_current.jsonl"
ALERTS_FILENAME = "alerts.jsonl"
REPORTS_SUBDIR = "reports"
FLAT_THRESHOLD_PCT = 0.5     # mirror lifecycle.py / canonical


# ============================================================
# IO helpers
# ============================================================

def _load_currents(run_dir: Path) -> List[dict]:
    p = run_dir / CURRENTS_FILENAME
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _load_alerts(run_dir: Path) -> List[dict]:
    p = run_dir / ALERTS_FILENAME
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


# ============================================================
# Date / lookup helpers
# ============================================================

def _build_fill_lookup(fills: List[FillSimulation]) -> Dict[str, FillSimulation]:
    return {f.event_id: f for f in fills}


def _lifecycle_logical_date(lc: LifecycleEvent,
                            fills_by_event_id: Dict[str, FillSimulation]) -> str:
    """Logical (trading-day) date for a lifecycle event. Looks up the
    associated FillSimulation via fill_event_id in trigger_data and uses
    fill.fill_date. Falls back to timestamp_utc date prefix."""
    fid = lc.trigger_data.get("fill_event_id") if lc.trigger_data else None
    if fid and fid in fills_by_event_id:
        return fills_by_event_id[fid].fill_date
    return lc.timestamp_utc[:10]


def _lifecycle_events_on(lcs: List[LifecycleEvent],
                          eval_date: date,
                          fills_by_event_id: Dict[str, FillSimulation]) -> List[LifecycleEvent]:
    target = eval_date.isoformat()
    return [lc for lc in lcs
            if _lifecycle_logical_date(lc, fills_by_event_id) == target]


def _fills_on(fills: List[FillSimulation], eval_date: date) -> List[FillSimulation]:
    target = eval_date.isoformat()
    return [f for f in fills if f.fill_date == target]


def _alerts_on(alerts: List[dict], eval_date: date) -> List[dict]:
    """Filter alerts whose timestamp_utc starts with eval_date. Step 9 will
    finalize the alert schema; Step 8 best-effort matches on common shapes."""
    target = eval_date.isoformat()
    out = []
    for a in alerts:
        ts = a.get("timestamp_utc") or ""
        if ts.startswith(target):
            out.append(a)
    return out


def _find_scan_for_date(scans: List[ScanEvent], eval_date: date) -> Optional[ScanEvent]:
    target = eval_date.isoformat()
    for s in scans:
        if s.scan_date == target:
            return s
    return None


def _calendar_days(d1: date, d2: date) -> int:
    return abs((d1 - d2).days)


def _wlf_label(pnl_pct: Optional[float]) -> str:
    if pnl_pct is None:
        return "—"
    if abs(pnl_pct) < FLAT_THRESHOLD_PCT:
        return "FLAT"
    return "WIN" if pnl_pct > 0 else "LOSS"


def _safe_pct(numer: int, denom: int) -> str:
    if denom == 0:
        return "—"
    return f"{(numer / denom) * 100:.1f}%"


def _safe_num(values: List[Optional[float]]) -> str:
    """Mean over non-None values, or '—' if no values."""
    present = [v for v in values if v is not None]
    if not present:
        return "—"
    return f"{sum(present) / len(present):.4f}"


def _safe_pnl(values: List[Optional[float]]) -> str:
    present = [v for v in values if v is not None]
    if not present:
        return "—"
    return f"{sum(present) / len(present):.2f}%"


def _fmt_price(p: Optional[float]) -> str:
    """Display-layer price rounding to 2 decimals. Underlying JSON keeps
    full precision; this just cleans up the markdown table."""
    if p is None:
        return "—"
    return f"{p:.2f}"


# ============================================================
# Markdown table builder
# ============================================================

def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    """GitHub-flavored markdown table. Empty rows → ''."""
    if not rows:
        return ""
    head = "| " + " | ".join(headers) + " |"
    sep  = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in rows)
    return "\n".join([head, sep, body])


# ============================================================
# Section renderers
# ============================================================

def _render_header(eval_date: date, run_dir: Path,
                   today_scan: Optional[ScanEvent]) -> str:
    if today_scan is not None:
        sha = today_scan.git_commit_sha
        regime = f"{today_scan.regime}/{today_scan.sub_regime or '—'}"
        latest = (today_scan.sub_regime_inputs or {}).get(
            "nifty_close_latest_date", "—")
    else:
        sha, regime, latest = "—", "—", "—"
    return (
        f"# Shadow Ops Daily Report — {eval_date.isoformat()}\n\n"
        f"- Run directory: `{run_dir}`\n"
        f"- Git commit at scan time: `{sha}`\n"
        f"- Regime: {regime}\n"
        f"- Last data refresh: {latest}"
    )


def _render_scan_summary(today_scan: Optional[ScanEvent]) -> str:
    if today_scan is None:
        return ""
    rows = [
        ["Scan status",            today_scan.scan_status],
        ["Signals universe-wide",  today_scan.n_signals_universe],
        ["Signals post-filter",    today_scan.n_signals_post_filter],
        ["Elapsed",                f"{today_scan.scan_duration_ms} ms"],
    ]
    return "## Today's scan\n\n" + _md_table(["Field", "Value"], rows)


def _render_today_transitions(lcs_today: List[LifecycleEvent],
                              currents_by_id: Dict[str, dict]) -> str:
    if not lcs_today:
        return ""
    by_to_state: Dict[str, List[LifecycleEvent]] = {}
    for lc in lcs_today:
        by_to_state.setdefault(lc.to_state, []).append(lc)

    parts: List[str] = ["## Today's transitions"]

    entries = by_to_state.get("ACTIVE", [])
    if entries:
        rows = []
        for lc in entries:
            c = currents_by_id.get(lc.card_id, {})
            rows.append([
                f"`{lc.card_id}`",
                c.get("symbol", "—"),
                c.get("sector", "—"),
                _fmt_price(c.get("actual_entry_price")),
                c.get("actual_entry_date") or "—",
            ])
        parts.append(f"### Entries (PROPOSED → ACTIVE) — {len(entries)} cards\n\n"
                     + _md_table(
                         ["card_id", "symbol", "sector",
                          "actual_entry_price", "actual_entry_date"], rows))

    stops = by_to_state.get("HYPOTHETICAL_STOPPED", [])
    if stops:
        rows = []
        for lc in stops:
            c = currents_by_id.get(lc.card_id, {})
            rows.append([
                f"`{lc.card_id}`", c.get("symbol", "—"),
                c.get("exit_day", "—"),
                _fmt_price(c.get("actual_exit_price")),
                f"{c.get('realized_pnl_pct') or '—'}",
                f"{c.get('realized_R') or '—'}",
            ])
        parts.append(f"### Stops hit (ACTIVE → HYPOTHETICAL_STOPPED) — {len(stops)} cards\n\n"
                     + _md_table(
                         ["card_id", "symbol", "exit_day",
                          "actual_exit_price", "realized_pnl_pct", "realized_R"], rows))

    targets = by_to_state.get("HYPOTHETICAL_FILLED", [])
    if targets:
        rows = []
        for lc in targets:
            c = currents_by_id.get(lc.card_id, {})
            rows.append([
                f"`{lc.card_id}`", c.get("symbol", "—"),
                c.get("exit_day", "—"),
                _fmt_price(c.get("actual_exit_price")),
                f"{c.get('realized_pnl_pct') or '—'}",
                f"{c.get('realized_R') or '—'}",
            ])
        parts.append(f"### Targets hit (ACTIVE → HYPOTHETICAL_FILLED) — {len(targets)} cards\n\n"
                     + _md_table(
                         ["card_id", "symbol", "exit_day",
                          "actual_exit_price", "realized_pnl_pct", "realized_R"], rows))

    expiries = by_to_state.get("EXPIRED", [])
    if expiries:
        rows = []
        for lc in expiries:
            c = currents_by_id.get(lc.card_id, {})
            rows.append([
                f"`{lc.card_id}`", c.get("symbol", "—"),
                _fmt_price(c.get("actual_exit_price")),
                f"{c.get('realized_pnl_pct') or '—'}",
                _wlf_label(c.get("realized_pnl_pct")),
            ])
        parts.append(f"### D6 expirations (ACTIVE → EXPIRED) — {len(expiries)} cards\n\n"
                     + _md_table(
                         ["card_id", "symbol", "actual_exit_price",
                          "realized_pnl_pct", "W/L/F"], rows))

    return "\n\n".join(parts)


def _render_open_cards(currents: List[dict], eval_date: date) -> str:
    open_cards = [c for c in currents
                  if c.get("current_state") in ("PROPOSED", "ACTIVE")]
    if not open_cards:
        return ""
    open_cards.sort(key=lambda c: c.get("scan_date", ""), reverse=True)
    rows = []
    for c in open_cards:
        scan_d_str = c.get("scan_date", "")
        try:
            scan_d = date.fromisoformat(scan_d_str)
            days_open = _calendar_days(eval_date, scan_d)
        except ValueError:
            days_open = "—"
        rows.append([
            f"`{c.get('card_id', '—')}`", c.get("symbol", "—"),
            c.get("sector", "—"), c.get("rule_id", "—"),
            c.get("current_state", "—"), scan_d_str, days_open,
        ])
    return ("## Open trade cards\n\n"
            + _md_table(
                ["card_id", "symbol", "sector", "rule_id",
                 "current_state", "scan_date", "days_open (calendar)"], rows))


def _render_cumulative_cohort(currents: List[dict]) -> str:
    total = len(currents)
    by_state: Dict[str, int] = {}
    for c in currents:
        s = c.get("current_state", "PROPOSED")
        by_state[s] = by_state.get(s, 0) + 1

    n_open = by_state.get("PROPOSED", 0) + by_state.get("ACTIVE", 0)
    n_target = by_state.get("HYPOTHETICAL_FILLED", 0)
    n_stop = by_state.get("HYPOTHETICAL_STOPPED", 0)
    n_expired = by_state.get("EXPIRED", 0)
    n_closed = n_target + n_stop + n_expired

    closed_pnl = [c.get("realized_pnl_pct") for c in currents
                  if c.get("current_state") in
                     ("HYPOTHETICAL_FILLED", "HYPOTHETICAL_STOPPED", "EXPIRED")]
    closed_R = [c.get("realized_R") for c in currents
                if c.get("current_state") in
                   ("HYPOTHETICAL_FILLED", "HYPOTHETICAL_STOPPED", "EXPIRED")]
    n_pnl_gt_zero = sum(1 for v in closed_pnl if v is not None and v > 0)
    n_pnl_audit_win = sum(1 for v in closed_pnl
                          if v is not None and v >= FLAT_THRESHOLD_PCT)

    rows = [
        ["Total trade cards proposed",                    total],
        ["Currently open (PROPOSED + ACTIVE)",            n_open],
        ["Closed: target hit (HYPOTHETICAL_FILLED)",      n_target],
        ["Closed: stop hit (HYPOTHETICAL_STOPPED)",       n_stop],
        ["Closed: expired (D6)",                          n_expired],
        ["Total closed",                                  n_closed],
        ["Win rate (pnl > 0)",                            _safe_pct(n_pnl_gt_zero, n_closed)],
        ["Win rate (pnl ≥ 0.5%, audit-comparable)",       _safe_pct(n_pnl_audit_win, n_closed)],
        ["Mean realized_R (closed)",                      _safe_num(closed_R)],
        ["Mean realized_pnl_pct (closed)",                _safe_pnl(closed_pnl)],
    ]
    return "## Cumulative cohort outcomes\n\n" + _md_table(["Metric", "Value"], rows)


def _render_alerts(alerts: List[dict]) -> str:
    if not alerts:
        return ""
    bullets: List[str] = []
    for a in alerts:
        sev = a.get("severity", "INFO")
        typ = a.get("type", a.get("alert_type", "—"))
        msg = a.get("message", a.get("msg", ""))
        bullets.append(f"- [{sev}] {typ}: {msg}")
    return "## Alerts\n\n" + "\n".join(bullets)


def _render_regime_trend(scans: List[ScanEvent], n: int = 5) -> str:
    if not scans:
        return ""
    sorted_scans = sorted(scans, key=lambda s: s.scan_date, reverse=True)[:n]
    rows = [
        [s.scan_date, s.regime, s.sub_regime or "—", s.n_signals_post_filter]
        for s in sorted_scans
    ]
    return (f"## Recent regime trend (last {len(rows)} scans)\n\n"
            + _md_table(
                ["scan_date", "regime", "sub_regime", "n_signals_post_filter"], rows))


def _render_data_lineage(today_scan: Optional[ScanEvent],
                         fills_today: List[FillSimulation]) -> str:
    parts = ["## Data lineage check"]
    if today_scan is not None:
        sha = today_scan.git_commit_sha
        latest = (today_scan.sub_regime_inputs or {}).get(
            "nifty_close_latest_date", "—")
        parts.append(f"- Today's scan_event.git_commit_sha: `{sha}`")
        parts.append(f"- Today's scan_event.data_versions.nifty_close_latest_date: {latest}")
    else:
        parts.append("- No scan_event for this eval_date.")
    sample_fill = next(
        (f for f in fills_today if f.data_source_sha256), None)
    if sample_fill is not None:
        parts.append(f"- Sample fill data_source: `{sample_fill.data_source}`")
        parts.append(f"- Sample fill data_source_sha256: `{sample_fill.data_source_sha256}`")
    else:
        parts.append("- No fills emitted today (no parquet SHA reference).")
    return "\n".join(parts)


# ============================================================
# Public API
# ============================================================

def generate_daily_report(run_dir: Path,
                          eval_date: date,
                          regenerate_read_model: bool = True) -> str:
    """Produce markdown digest for eval_date.

    If regenerate_read_model=True (default), runs Step 7's regenerator first
    so the report reflects current event-log state. Returns markdown text.
    """
    run_dir = Path(run_dir)

    if regenerate_read_model:
        from shadow_ops.read_model import regenerate_read_model as _regen
        _regen(run_dir)

    reader = JournalReader(run_dir)
    scans = reader.all_scan_events()
    lcs = reader.all_lifecycle_events()
    fills = reader.all_fill_simulations()
    currents = _load_currents(run_dir)
    alerts = _load_alerts(run_dir)

    fills_by_event_id = _build_fill_lookup(fills)
    today_scan = _find_scan_for_date(scans, eval_date)
    lcs_today = _lifecycle_events_on(lcs, eval_date, fills_by_event_id)
    fills_today = _fills_on(fills, eval_date)
    alerts_today = _alerts_on(alerts, eval_date)
    currents_by_id = {c.get("card_id"): c for c in currents if c.get("card_id")}

    parts: List[str] = [
        _render_header(eval_date, run_dir, today_scan),
        _render_scan_summary(today_scan),
        _render_today_transitions(lcs_today, currents_by_id),
        _render_open_cards(currents, eval_date),
        _render_cumulative_cohort(currents),
        _render_alerts(alerts_today),
        _render_regime_trend(scans, n=5),
        _render_data_lineage(today_scan, fills_today),
    ]
    return "\n\n".join(p for p in parts if p) + "\n"


def default_report_path(run_dir: Path, eval_date: date) -> Path:
    return Path(run_dir) / REPORTS_SUBDIR / f"{eval_date.isoformat()}.md"


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops daily report")
    ap.add_argument("--run-dir", type=str, required=True,
                    help="path to a daily_scan run directory")
    ap.add_argument("--eval-date", type=str, default=None,
                    help="YYYY-MM-DD; defaults to today UTC")
    ap.add_argument("--out", type=str, default=None,
                    help="path to write markdown; default <run_dir>/reports/<eval_date>.md")
    ap.add_argument("--stdout", action="store_true",
                    help="print to stdout instead of writing to a file")
    ap.add_argument("--no-regen", action="store_true",
                    help="skip Step 7 read-model regeneration")
    args = ap.parse_args()

    eval_date = (date.fromisoformat(args.eval_date) if args.eval_date
                 else datetime.now(timezone.utc).date())

    try:
        md = generate_daily_report(
            Path(args.run_dir), eval_date,
            regenerate_read_model=not args.no_regen,
        )
    except Exception:
        traceback.print_exc()
        return 2

    if args.stdout:
        sys.stdout.write(md)
        return 0

    out_path = Path(args.out) if args.out else default_report_path(
        Path(args.run_dir), eval_date)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
