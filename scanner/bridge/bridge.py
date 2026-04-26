"""
bridge — top-level CLI orchestrator.

Entry point GitHub Actions calls. Routes to phase-specific composer based on
--phase argument. Pre-flight check skips non-trading days. Top-level error
catch ensures a single exception doesn't take down the workflow without a
loggable summary.

CLI:
    python scanner/bridge/bridge.py --phase PRE_MARKET
    python scanner/bridge/bridge.py --phase PRE_MARKET --market-date 2026-04-29
    python scanner/bridge/bridge.py --version

Exit codes: 0 = success/skip, 1 = fatal, 2 = invalid args.

See doc/bridge_design_v1.md §13.5 (orchestrator).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


# Self-bootstrap so the script runs whether invoked as
# `python scanner/bridge/bridge.py` or `python -m scanner.bridge.bridge`.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


from scanner.bridge.core import state_writer  # noqa: E402
from scanner.bridge.rules.thresholds import (  # noqa: E402
    BRIDGE_STATE_SCHEMA_VERSION,
    CONTRA_BLOCK_SCHEMA_VERSION,
)


BRIDGE_VERSION = "1.0.0"
_IST = ZoneInfo("Asia/Kolkata")
_VALID_PHASES = ("PRE_MARKET", "POST_OPEN", "EOD")
_WAVE3_STUB_PHASES = ()


# =====================================================================
# Public CLI entry point
# =====================================================================

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bridge",
        description="TIE TIY Bridge orchestrator",
    )
    parser.add_argument("--phase", choices=list(_VALID_PHASES),
                        required=False,
                        help="Bridge phase (PRE_MARKET / POST_OPEN / EOD)")
    parser.add_argument("--market-date", default=None,
                        help="YYYY-MM-DD; defaults to today IST")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--version", action="store_true",
                        help="Print bridge version and exit")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse exits with code 2 on bad args; let it propagate
        return int(e.code or 2)

    if args.version:
        print(BRIDGE_VERSION)
        return 0

    if args.phase is None:
        parser.error("--phase is required (unless --version)")
        return 2  # parser.error already exited, but be explicit

    try:
        summary = run_phase(
            phase=args.phase,
            market_date=args.market_date,
            output_dir=args.output_dir,
            data_dir=args.data_dir,
        )
        emit_log("INFO", action="compose_complete", **summary)
        # Exit codes per spec
        status = summary.get("phase_status")
        if status in ("OK", "DEGRADED", "SKIPPED"):
            return 0
        return 1
    except Exception as e:
        # Catastrophic failure outside composer
        emit_log(
            "ERROR",
            action="bridge_crash",
            exception_type=type(e).__name__,
            exception_message=str(e),
            phase=args.phase,
        )
        return 1


# =====================================================================
# Phase routing
# =====================================================================

def run_phase(phase: str,
              market_date: Optional[str] = None,
              output_dir: str = "output",
              data_dir: str = "data") -> dict:
    """Run a single phase. Returns composer's summary dict."""
    md = market_date or _today_ist()

    # Pre-flight: trading-day check
    if not is_trading_day(md):
        return _skip_phase(phase, md, output_dir,
                           reason="non-trading day")

    if phase == "PRE_MARKET":
        from scanner.bridge.composers.premarket import compose
        return compose(
            market_date=md,
            output_dir=output_dir,
            data_dir=data_dir,
        )

    if phase == "POST_OPEN":
        from scanner.bridge.composers.postopen import compose
        return compose(
            market_date=md,
            output_dir=output_dir,
            data_dir=data_dir,
        )

    if phase == "EOD":
        from scanner.bridge.composers.eod import compose
        return compose(
            market_date=md,
            output_dir=output_dir,
            data_dir=data_dir,
        )

    if phase in _WAVE3_STUB_PHASES:
        return _stub_phase(phase, md, output_dir,
                           reason="not implemented in Wave 2")

    # Should be unreachable thanks to argparse choices, but defensive
    raise ValueError(f"unknown phase: {phase!r}")


# =====================================================================
# Calendar awareness
# =====================================================================

def is_trading_day(market_date: str) -> bool:
    """True if market_date is a trading day. Uses scanner.calendar_utils
    when available, else weekday-only check."""
    try:
        from scanner.calendar_utils import is_trading_day as cal_is_trading
        return bool(cal_is_trading(market_date))
    except Exception:
        # Fallback: weekday-only (no holiday awareness)
        try:
            d = datetime.strptime(market_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return False
        return d.weekday() < 5  # 0=Mon, 6=Sun


# =====================================================================
# Skip / stub state writers
# =====================================================================

def _skip_phase(phase: str,
                market_date: str,
                output_dir: str,
                reason: str) -> dict:
    """Non-trading-day path: write a SKIPPED bridge_state, return summary."""
    state = _build_skip_state(phase, market_date, reason)
    try:
        state_writer.write_state(state, output_dir=output_dir)
        state_file = os.path.join(output_dir, "bridge_state.json")
    except Exception as e:
        emit_log(
            "ERROR",
            action="skip_state_write_failed",
            exception_type=type(e).__name__,
            exception_message=str(e),
        )
        state_file = ""

    return {
        "phase":                phase,
        "phase_status":         "SKIPPED",
        "market_date":          market_date,
        "signals_count":        0,
        "buckets":              {"TAKE_FULL": 0, "TAKE_SMALL": 0,
                                 "WATCH": 0, "SKIP": 0},
        "open_positions_count": 0,
        "alerts_count":         0,
        "errors_logged":        0,
        "state_file_written":   state_file,
        "duration_ms":          0,
        "skip_reason":          reason,
    }


def _stub_phase(phase: str,
                market_date: str,
                output_dir: str,
                reason: str) -> dict:
    """Wave 3 stub phases: log + return stub summary. No state write
    since the composer doesn't exist yet — leaves any prior state in
    place rather than overwriting with a stub."""
    emit_log(
        "INFO",
        action="phase_not_implemented",
        phase=phase,
        market_date=market_date,
        reason=reason,
    )
    return {
        "phase":                phase,
        "phase_status":         "SKIPPED",  # treated as no-op exit-0
        "market_date":          market_date,
        "signals_count":        0,
        "buckets":              {"TAKE_FULL": 0, "TAKE_SMALL": 0,
                                 "WATCH": 0, "SKIP": 0},
        "open_positions_count": 0,
        "alerts_count":         0,
        "errors_logged":        0,
        "state_file_written":   "",
        "duration_ms":          0,
        "skip_reason":          reason,
    }


def _build_skip_state(phase: str,
                      market_date: str,
                      reason: str) -> dict:
    """Minimal valid bridge_state dict for non-trading-day phase."""
    now = _now_iso()
    return {
        "schema_version":  BRIDGE_STATE_SCHEMA_VERSION,
        "phase":           phase,
        "phase_status":    "SKIPPED",
        "phase_timestamp": now,
        "market_date":     market_date,
        "banner": {
            "state":   "SKIPPED",
            "color":   "neutral",
            "message": "Market closed today",
            "subtext": reason,
        },
        "summary": {
            "total_signals_today": 0,
            "buckets": {"TAKE_FULL": 0, "TAKE_SMALL": 0,
                        "WATCH": 0, "SKIP": 0},
            "open_positions_count": 0,
        },
        "signals":         [],
        "open_positions":  [],
        "contra": {
            "schema_version":     CONTRA_BLOCK_SCHEMA_VERSION,
            "active_rules":       [],
            "pending_shadows":    [],
            "recent_resolutions": [],
            "alerts_this_cycle":  [],
        },
        "alerts":          [],
        "self_queries":    [],
        "upstream_health": {},
        "audit": {
            "bridge_version":       BRIDGE_VERSION,
            "compose_started_at":   now,
            "compose_completed_at": now,
            "compose_duration_ms":  0,
            "warnings":             [f"SKIPPED: {reason}"],
        },
    }


# =====================================================================
# Structured logging
# =====================================================================

def emit_log(level: str, **fields) -> None:
    """One JSON line to stdout for GitHub Actions / log scrapers."""
    record = {
        "timestamp": _now_iso(),
        "level":     level,
        "component": "bridge",
        **fields,
    }
    try:
        line = json.dumps(record, default=str, ensure_ascii=False)
    except Exception:
        # Fall back to string repr if JSON serialization fails
        line = json.dumps({
            "timestamp": _now_iso(),
            "level":     "ERROR",
            "component": "bridge",
            "message":   "log serialization failed",
            "fields_repr": repr(fields),
        })
    print(line, flush=True)


# =====================================================================
# Helpers
# =====================================================================

def _today_ist() -> str:
    return datetime.now(_IST).date().isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# Script entry point
# =====================================================================

if __name__ == "__main__":
    sys.exit(main())
