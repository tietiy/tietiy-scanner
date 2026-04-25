"""
upstream_health — reads chain_validator's system_health.json, translates to bridge format.

The bridge composer calls get_upstream_health() at start of compose to know which
upstream modules are healthy. If any are broken, the bridge:
  - Surfaces the problem in bridge_state.upstream_health
  - Sets bridge_state.phase_status to "DEGRADED" if has_critical_failure() returns True
  - Includes degraded_modules() output in alerts for Telegram

This module never writes anything. It only reads system_health.json and returns
transformed dicts. If system_health.json is missing/malformed, returns "unknown"
status for all modules — bridge can still compose, just without confidence in
upstream status.

See doc/bridge_design_v1.md §1.5 (graceful degradation) and §10 (bridge_state schema).
"""

import json
import os
from datetime import datetime
from typing import Optional


_HEALTH_FILENAME = "system_health.json"

_EXPECTED_MODULES = (
    "morning_scan",
    "open_validate",
    "eod_update",
    "outcome_eval",
    "pattern_miner",
    "rule_proposer",
    "contra_tracker",
)


def get_upstream_health(output_dir: str = "output",
                        market_date: Optional[str] = None) -> dict:
    """
    Reads system_health.json, returns flat module→status dict.
    On read/parse failure: all 7 modules → "unknown" + "_error" key
    explaining the reason.
    """
    health, err = _load_health(output_dir)
    if err:
        return _all_unknown(err)

    if not isinstance(health, dict):
        return _all_unknown(
            "system_health.json root is not an object")

    checks = health.get("checks")
    if not isinstance(checks, dict):
        return _all_unknown(
            "system_health.json missing 'checks' object")

    day_offset: Optional[int] = None
    if market_date and isinstance(health.get("date"), str):
        day_offset = _day_offset(health["date"], market_date)

    out: dict = {}
    for mod in _EXPECTED_MODULES:
        check = checks.get(mod)
        if not isinstance(check, dict):
            out[mod] = "unknown"
            continue
        out[mod] = _translate(check, day_offset)
    return out


def get_audit_health_block(output_dir: str = "output",
                           market_date: Optional[str] = None) -> dict:
    """
    SDR.audit.upstream_health_at_compose. Currently identical to
    get_upstream_health — separate function in case audit format
    diverges from live status format later.
    """
    return get_upstream_health(
        output_dir=output_dir, market_date=market_date)


def has_critical_failure(health_dict: dict) -> bool:
    """True if any upstream module shows 'error' status."""
    return any(
        v == "error"
        for k, v in health_dict.items()
        if not k.startswith("_")
    )


def degraded_modules(health_dict: dict) -> list:
    """Names of modules with 'error' or 'warn' status."""
    return [
        k for k, v in health_dict.items()
        if not k.startswith("_") and v in ("error", "warn")
    ]


def _load_health(output_dir: str):
    """Returns (parsed_dict, None) on success, (None, reason) on failure."""
    path = os.path.join(output_dir, _HEALTH_FILENAME)
    if not os.path.exists(path):
        return None, "system_health.json missing"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"system_health.json malformed JSON: {e}"
    except OSError as e:
        return None, f"system_health.json unreadable: {e}"


def _all_unknown(error_reason: str) -> dict:
    out = {m: "unknown" for m in _EXPECTED_MODULES}
    out["_error"] = error_reason
    return out


def _day_offset(report_date: str,
                market_date: str) -> Optional[int]:
    """
    Returns days(report - market). Negative = report is older than
    market_date. None if either string is unparseable.
    """
    try:
        rd = datetime.strptime(report_date, "%Y-%m-%d").date()
        md = datetime.strptime(market_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (rd - md).days


def _translate(check: dict,
               day_offset: Optional[int]) -> str:
    """
    Map a single chain_validator check dict into a bridge status string.

    chain_validator emits status ∈ {ok, warn, error}. We expand:
      - error                              → "error"
      - warn  + note contains "not yet"    → "not_yet_run"
      - warn  + other                      → "warn"
      - ok    + day_offset == 0 / unknown  → "ok"
      - ok    + day_offset == -1           → "ok_yesterday"
      - ok    + day_offset < -1            → "stale"
      - anything else                      → "unknown"
    """
    status = check.get("status")
    note = (check.get("note") or "").lower()

    if status == "error":
        return "error"
    if status == "warn":
        if "not yet" in note:
            return "not_yet_run"
        return "warn"
    if status == "ok":
        if day_offset is None or day_offset == 0:
            return "ok"
        if day_offset == -1:
            return "ok_yesterday"
        return "stale"
    return "unknown"
