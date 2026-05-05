"""shadow_ops/alerts.py — Step 9 of shadow_ops v1.

Structured alert emission + acknowledgment sidecar for operational hardening.

Per architecture doc §9.1 / §9.2 / §14.10:
  - 3 severity levels: CRITICAL, WARNING, INFO
  - Append-only file: <run_dir>/alerts.jsonl
  - Acknowledgment sidecar: <run_dir>/alerts_acknowledgments.jsonl (per §14.10)
  - Alerts also printed to stdout for ambient operator visibility
  - pre_scan_check.py reads both files to decide whether to block the next scan

Alert is NOT a journal Event — different file, no event_id-uniqueness invariant,
no JournalWriter integration. It's a parallel structure with its own conventions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shadow_ops.journal import _flock_exclusive


# ============================================================
# Constants
# ============================================================

ALERTS_FILENAME = "alerts.jsonl"
ACKS_FILENAME = "alerts_acknowledgments.jsonl"

VALID_ALERT_SEVERITY = frozenset({"CRITICAL", "WARNING", "INFO"})

VALID_ALERT_TYPES = frozenset({
    "DATA_INGEST_FAILURE",
    "DATA_INGEST_PARTIAL",
    "DATA_INGEST_STALE",
    "REGIME_CLASSIFIER_ERROR",
    "SCAN_ERROR",
    "SCAN_PARTIAL",
    "KILL_001_CLUSTER",
    "LIFECYCLE_ERROR",
    "LIFECYCLE_DAY_GAP",
    "CHECKSUM_MISMATCH",
    "PARQUET_SHA_DRIFT",
    "PRE_SCAN_CHECK_FAILURE",
    "PRE_SCAN_CHECK_BYPASSED",
})


# ============================================================
# Errors
# ============================================================

class AlertValidationError(ValueError):
    pass


class UnknownAlertIdError(KeyError):
    pass


# ============================================================
# Alert dataclass
# ============================================================

@dataclass
class Alert:
    alert_id: str
    timestamp_utc: str
    logical_date: str           # YYYY-MM-DD — the trading day this alert relates to
    severity: str               # CRITICAL | WARNING | INFO
    alert_type: str
    module: str                 # which shadow_ops module emitted it
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.alert_id, str) or not self.alert_id:
            raise AlertValidationError("alert_id must be non-empty string")
        if self.severity not in VALID_ALERT_SEVERITY:
            raise AlertValidationError(
                f"severity={self.severity!r} not in {sorted(VALID_ALERT_SEVERITY)}")
        if self.alert_type not in VALID_ALERT_TYPES:
            raise AlertValidationError(
                f"alert_type={self.alert_type!r} not in known types")
        if not isinstance(self.module, str) or not self.module:
            raise AlertValidationError("module must be non-empty string")
        if not isinstance(self.message, str) or not self.message:
            raise AlertValidationError("message must be non-empty string")
        # YYYY-MM-DD parse
        try:
            date.fromisoformat(self.logical_date)
        except (ValueError, TypeError):
            raise AlertValidationError(
                f"logical_date={self.logical_date!r} must be YYYY-MM-DD")
        # ISO 8601 timestamp parse
        try:
            datetime.fromisoformat(self.timestamp_utc)
        except (ValueError, TypeError):
            raise AlertValidationError(
                f"timestamp_utc={self.timestamp_utc!r} must be ISO 8601")
        if not isinstance(self.context, dict):
            raise AlertValidationError("context must be dict")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json_line(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Alert":
        valid_keys = {"alert_id", "timestamp_utc", "logical_date", "severity",
                      "alert_type", "module", "message", "context"}
        clean = {k: v for k, v in d.items() if k in valid_keys}
        clean.setdefault("context", {})
        return cls(**clean)


# ============================================================
# Path helpers
# ============================================================

def _alerts_path(run_dir: Path) -> Path:
    return Path(run_dir) / ALERTS_FILENAME


def _acks_path(run_dir: Path) -> Path:
    return Path(run_dir) / ACKS_FILENAME


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ============================================================
# Emission
# ============================================================

def _allocate_alert_id(run_dir: Path, logical_date: str) -> str:
    """Compute next alert_id for (run_dir, logical_date). Reads existing
    alerts.jsonl, counts matches with same logical_date prefix, returns
    `alert_<logical_date>_<seq:03d>` with seq = count + 1.

    Caller MUST hold the alerts.jsonl flock for this to be race-free.
    """
    path = _alerts_path(run_dir)
    count = 0
    if path.exists():
        prefix = f"alert_{logical_date}_"
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                aid = d.get("alert_id", "")
                if aid.startswith(prefix):
                    count += 1
    return f"alert_{logical_date}_{count + 1:03d}"


def emit_alert(run_dir: Path,
               severity: str,
               alert_type: str,
               module: str,
               message: str,
               *,
               context: Optional[Dict[str, Any]] = None,
               logical_date: Optional[str] = None) -> Alert:
    """Append a new Alert to <run_dir>/alerts.jsonl and print to stdout.

    Args:
      run_dir:       campaign run directory (created if missing)
      severity:      CRITICAL | WARNING | INFO
      alert_type:    one of VALID_ALERT_TYPES
      module:        emitting module name (e.g. "data_ingest")
      message:       human-readable
      context:       arbitrary structured diagnosis data (default {})
      logical_date:  YYYY-MM-DD; default today UTC

    Returns the Alert object that was written.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if logical_date is None:
        logical_date = _today_utc()

    alerts_path = _alerts_path(run_dir)
    with _flock_exclusive(alerts_path):
        alert = Alert(
            alert_id=_allocate_alert_id(run_dir, logical_date),
            timestamp_utc=_now_utc_iso(),
            logical_date=logical_date,
            severity=severity,
            alert_type=alert_type,
            module=module,
            message=message,
            context=dict(context) if context else {},
        )
        alert.validate()
        line = alert.to_json_line() + "\n"
        with open(alerts_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    # Stdout per arch §9.2
    print(f"[shadow_ops/alert] {alert.severity} {alert.alert_type} "
          f"({alert.module}): {alert.message}", file=sys.stderr)
    return alert


# ============================================================
# Reading
# ============================================================

def list_alerts(run_dir: Path) -> List[Alert]:
    """Return every alert in <run_dir>/alerts.jsonl. Returns [] if file missing."""
    p = _alerts_path(run_dir)
    if not p.exists():
        return []
    out: List[Alert] = []
    with open(p, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(Alert.from_dict(d))
    return out


def list_acknowledgments(run_dir: Path) -> List[Dict[str, Any]]:
    """Return every ack record. Returns [] if file missing."""
    p = _acks_path(run_dir)
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _ack_index(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    """alert_id → latest ack record (last write wins if duplicate acks)."""
    idx: Dict[str, Dict[str, Any]] = {}
    for rec in list_acknowledgments(run_dir):
        aid = rec.get("alert_id")
        if aid:
            idx[aid] = rec
    return idx


# ============================================================
# Acknowledgment
# ============================================================

def acknowledge_alert(run_dir: Path, alert_id: str,
                      *, reason: Optional[str] = None,
                      by: Optional[str] = None) -> Dict[str, Any]:
    """Append an ack record for alert_id to <run_dir>/alerts_acknowledgments.jsonl.

    Raises UnknownAlertIdError if no alert with that ID exists in alerts.jsonl.
    """
    run_dir = Path(run_dir)
    known = {a.alert_id for a in list_alerts(run_dir)}
    if alert_id not in known:
        raise UnknownAlertIdError(
            f"alert_id={alert_id!r} not found in {_alerts_path(run_dir)}")

    rec: Dict[str, Any] = {
        "alert_id": alert_id,
        "acknowledged_at_utc": _now_utc_iso(),
    }
    if by:
        rec["acknowledged_by"] = by
    if reason:
        rec["reason"] = reason

    acks_path = _acks_path(run_dir)
    with _flock_exclusive(acks_path):
        line = json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n"
        with open(acks_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    return rec


def unacknowledged_critical(run_dir: Path,
                            on_or_before_date: Optional[date] = None) -> List[Alert]:
    """Return CRITICAL alerts whose logical_date ≤ cutoff and which have no
    matching ack record. Default cutoff: today UTC."""
    cutoff = on_or_before_date or datetime.now(timezone.utc).date()
    cutoff_iso = cutoff.isoformat()
    acks = _ack_index(run_dir)
    out: List[Alert] = []
    for a in list_alerts(run_dir):
        if a.severity != "CRITICAL":
            continue
        if a.logical_date > cutoff_iso:
            continue
        if a.alert_id in acks:
            continue
        out.append(a)
    return out


# ============================================================
# CLI (`shadow_ops.alerts`)
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops alerts CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list alerts in a run dir")
    p_list.add_argument("--run-dir", type=str, required=True)
    p_list.add_argument("--severity", type=str, default=None,
                        help=f"filter by severity ({sorted(VALID_ALERT_SEVERITY)})")
    p_list.add_argument("--unacked-critical", action="store_true",
                        help="show only unacked CRITICAL alerts")

    p_ack = sub.add_parser("ack", help="acknowledge an alert")
    p_ack.add_argument("--run-dir", type=str, required=True)
    p_ack.add_argument("--alert-id", type=str, required=True)
    p_ack.add_argument("--reason", type=str, default=None)
    p_ack.add_argument("--by", type=str, default=None)

    args = ap.parse_args()
    run_dir = Path(args.run_dir)

    if args.cmd == "list":
        if args.unacked_critical:
            alerts = unacknowledged_critical(run_dir)
        else:
            alerts = list_alerts(run_dir)
            if args.severity:
                alerts = [a for a in alerts if a.severity == args.severity]
        for a in alerts:
            print(a.to_json_line())
        return 0

    if args.cmd == "ack":
        try:
            rec = acknowledge_alert(run_dir, args.alert_id,
                                     reason=args.reason, by=args.by)
        except UnknownAlertIdError as e:
            print(f"[alerts] {e}", file=sys.stderr)
            return 2
        print(json.dumps(rec, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(_main_cli())
