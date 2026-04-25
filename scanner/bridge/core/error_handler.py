"""
error_handler — graceful degradation framework for the bridge.

Three severity levels, three behaviors:
- WARNING: query plugin crash or non-critical failure. Compose continues with
  empty result for that query. Audit logs the failure.
- DEGRADED: critical operation failed but compose can produce partial state.
  bridge_state.phase_status = "DEGRADED". User sees orange banner.
- FATAL: compose cannot continue. emergency_state() builds a minimal valid
  bridge_state. User sees red banner + Telegram error notification.

Composer pattern:
    error_handler.reset_error_log()
    try:
        result = error_handler.safe_run(query_plugin.run, *args,
                                         severity="WARNING",
                                         context="q_pattern_match")
        if result is None:
            # query failed, use empty default
            result = {}
        ...
    except Exception as e:
        # catastrophic failure — build emergency state
        state = error_handler.build_emergency_state(...)
        state_writer.write_state(state)

The bridge NEVER fails silently. Every error becomes either a warning, a
degraded compose, or an emergency state. User always knows what happened.

See doc/bridge_design_v1.md §1.5, §14.
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from scanner.bridge.rules.thresholds import (
    BRIDGE_STATE_SCHEMA_VERSION,
    CONTRA_BLOCK_SCHEMA_VERSION,
)


_VALID_SEVERITIES = ("WARNING", "DEGRADED", "FATAL")
_BRIDGE_VERSION = "1.0.0"

# Module-level mutable state. Mutated in place by reset_error_log()
# so that all references stay consistent across the compose.
_error_log: list = []

_logger = logging.getLogger(__name__)


def safe_run(func: Callable,
             *args: Any,
             severity: str = "WARNING",
             context: str = "",
             **kwargs: Any) -> Any:
    """
    Execute func(*args, **kwargs); catch any exception and log it.
    Returns func's return value on success, None on failure.

    Does NOT re-raise — even FATAL just logs and returns None. The
    composer inspects get_error_log() / has_fatal_errors() to decide
    whether to switch to emergency_state.
    """
    if severity not in _VALID_SEVERITIES:
        raise ValueError(
            f"severity must be one of "
            f"{_VALID_SEVERITIES}, got {severity!r}")

    try:
        return func(*args, **kwargs)
    except Exception as e:
        entry = {
            "severity": severity,
            "context": context,
            "exception_type": type(e).__name__,
            "exception_message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": _now_iso(),
        }
        _error_log.append(entry)
        _logger.warning(
            "[bridge.%s] %s: %s: %s",
            severity, context or "(no context)",
            type(e).__name__, e)
        return None


def get_error_log() -> list:
    """Returns a shallow copy of the error log (defensive)."""
    return list(_error_log)


def reset_error_log() -> None:
    """Clears the log in place (preserves identity for callers)."""
    _error_log.clear()


def has_fatal_errors() -> bool:
    return any(e["severity"] == "FATAL" for e in _error_log)


def has_degraded_errors() -> bool:
    return any(e["severity"] == "DEGRADED" for e in _error_log)


def has_warnings() -> bool:
    return any(e["severity"] == "WARNING" for e in _error_log)


def compute_phase_status(default_status: str = "OK") -> str:
    """FATAL > DEGRADED > default. WARNINGs do not degrade the phase."""
    if has_fatal_errors():
        return "ERROR"
    if has_degraded_errors():
        return "DEGRADED"
    return default_status


def build_emergency_state(phase: str,
                          market_date: str,
                          error_summary: str) -> dict:
    """
    Returns a minimal valid bridge_state dict for catastrophic failures.
    Satisfies state_writer._validate_state so it can still be written.
    """
    now = _now_iso()
    return {
        "schema_version": BRIDGE_STATE_SCHEMA_VERSION,
        "phase": phase,
        "phase_status": "ERROR",
        "phase_timestamp": now,
        "market_date": market_date,
        "banner": {
            "state": "ERROR",
            "color": "red",
            "message": "Bridge failed",
            "subtext": error_summary[:200],
        },
        "summary": {
            "total_signals_today": 0,
            "buckets": {
                "TAKE_FULL":  0,
                "TAKE_SMALL": 0,
                "WATCH":      0,
                "SKIP":       0,
            },
        },
        "signals": [],
        "open_positions": [],
        "contra": {
            "schema_version": CONTRA_BLOCK_SCHEMA_VERSION,
            "active_rules": [],
            "pending_shadows": [],
            "recent_resolutions": [],
            "alerts_this_cycle": [],
        },
        "alerts": [{
            "type": "compose_failure",
            "severity": "fatal",
            "message": error_summary[:500],
        }],
        "self_queries": [],
        "upstream_health": {},
        "audit": {
            "bridge_version": _BRIDGE_VERSION,
            "compose_started_at": now,
            "compose_completed_at": now,
            "queries_total": 0,
            "queries_failed": 0,
            "files_read": [],
            "warnings": [f"FATAL: {error_summary}"],
        },
    }


def build_telegram_error_message(phase: str,
                                 error_summary: str,
                                 error_log: Optional[list] = None
                                 ) -> str:
    """
    Markdown-formatted Telegram error message for compose failure.

    Composer prepends/appends Actions log link as needed (this module
    has no GitHub context). If error_log is provided, the message
    includes a compact tail of degraded/warning entries.
    """
    lines = [
        f"❌ *Bridge failed at {phase}*",
        f"Phase: {_now_iso()}",
        f"Error: {error_summary}",
    ]

    if error_log:
        degraded = [e for e in error_log
                    if e.get("severity") == "DEGRADED"]
        warnings = [e for e in error_log
                    if e.get("severity") == "WARNING"]
        if degraded or warnings:
            lines.append("")
            lines.append("Other issues this compose:")
            for e in degraded[:3]:
                lines.append(
                    f"  • DEGRADED {e.get('context', '?')}: "
                    f"{e.get('exception_message', '')}")
            for e in warnings[:3]:
                lines.append(
                    f"  • WARNING {e.get('context', '?')}: "
                    f"{e.get('exception_message', '')}")
            shown = min(3, len(degraded)) + min(3, len(warnings))
            extra = (len(degraded) + len(warnings)) - shown
            if extra > 0:
                lines.append(f"  ...and {extra} more")

    lines.append("")
    lines.append("Check GitHub Actions logs for the full traceback.")
    return "\n".join(lines)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
