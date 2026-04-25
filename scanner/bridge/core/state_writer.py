"""
state_writer — single write chokepoint for the bridge.

All disk writes for the bridge funnel through write_state(). This guarantees:
- Atomicity (tmp file + rename, no partial writes)
- History capture (every compose archived)
- Retention (old history pruned automatically)
- Schema validation (malformed state never written)

No other bridge module writes files directly. If you find yourself writing to
disk anywhere else in scanner/bridge/, stop and refactor — write through here.

See doc/bridge_design_v1.md §1.4, §10.
"""

import json
import os
import re
from datetime import date, datetime
from typing import Optional

from scanner.bridge.rules.thresholds import (
    BRIDGE_STATE_HISTORY_RETENTION_DAYS,
    BRIDGE_STATE_SCHEMA_VERSION,
)


_VALID_PHASES = {"PRE_MARKET", "POST_OPEN", "EOD", "ERROR"}
_HISTORY_DIRNAME = "bridge_state_history"
_STATE_FILENAME = "bridge_state.json"
_HISTORY_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_.+\.json$")


def write_state(state: dict, output_dir: str = "output") -> dict:
    """
    Atomically writes bridge_state.json + creates dated history copy +
    cleans old history. Returns dict with paths and cleanup stats.

    Raises ValueError if state malformed; OSError if disk write fails
    (caller should route via error_handler).
    """
    _validate_state(state)

    history_dir = os.path.join(output_dir, _HISTORY_DIRNAME)
    os.makedirs(history_dir, exist_ok=True)

    payload = json.dumps(
        state,
        indent=2,
        sort_keys=False,
        ensure_ascii=False,
    )

    state_path = os.path.join(output_dir, _STATE_FILENAME)
    history_path = os.path.join(
        history_dir,
        _history_filename(state["market_date"], state["phase"]),
    )

    bytes_state   = _atomic_write(state_path, payload)
    bytes_history = _atomic_write(history_path, payload)

    deleted = _cleanup_history(
        history_dir, BRIDGE_STATE_HISTORY_RETENTION_DAYS)

    try:
        history_total = sum(
            1 for f in os.listdir(history_dir)
            if _HISTORY_NAME_RE.match(f)
        )
    except OSError:
        history_total = 0

    return {
        "state_file": state_path,
        "history_file": history_path,
        "history_files_deleted": deleted,
        "history_files_total": history_total,
        "bytes_written": bytes_state + bytes_history,
    }


def read_state(output_dir: str = "output") -> Optional[dict]:
    """
    Reads bridge_state.json. Returns None if not yet composed.
    Raises ValueError on malformed JSON.
    """
    path = os.path.join(output_dir, _STATE_FILENAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"bridge_state.json is malformed: {e}") from e


def _validate_state(state: dict) -> None:
    """Raises ValueError if state dict is malformed."""
    if not isinstance(state, dict):
        raise ValueError(
            f"state must be dict, got {type(state).__name__}")

    for required in (
        "schema_version", "phase",
        "phase_timestamp", "market_date",
    ):
        if required not in state:
            raise ValueError(
                f"state missing required field: {required!r}")

    if state["schema_version"] != BRIDGE_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version mismatch: state has "
            f"{state['schema_version']!r}, expected "
            f"{BRIDGE_STATE_SCHEMA_VERSION!r}")

    if state["phase"] not in _VALID_PHASES:
        raise ValueError(
            f"invalid phase: {state['phase']!r} "
            f"(expected one of {sorted(_VALID_PHASES)})")


def _atomic_write(target_path: str, content: str) -> int:
    """
    Writes content to a sibling tmp file, fsyncs, then os.rename.
    Tmp suffix includes pid so cross-process writes never collide.
    Returns bytes written.
    """
    parent = os.path.dirname(target_path) or "."
    os.makedirs(parent, exist_ok=True)

    tmp_path = f"{target_path}.{os.getpid()}.tmp"
    encoded = content.encode("utf-8")

    fd = os.open(
        tmp_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o644,
    )
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)

    os.rename(tmp_path, target_path)
    return len(encoded)


def _history_filename(market_date: str, phase: str) -> str:
    """Returns 'YYYY-MM-DD_PHASE.json'."""
    return f"{market_date}_{phase}.json"


def _cleanup_history(history_dir: str, retention_days: int) -> list:
    """
    Deletes history files older than retention_days based on the
    YYYY-MM-DD prefix in the filename. Files that don't parse as
    dates are left alone. Returns list of deleted filenames.
    """
    if not os.path.isdir(history_dir):
        return []

    today = date.today()
    deleted: list = []

    for fname in os.listdir(history_dir):
        m = _HISTORY_NAME_RE.match(fname)
        if not m:
            continue
        try:
            file_date = datetime.strptime(
                m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue

        age_days = (today - file_date).days
        if age_days > retention_days:
            full = os.path.join(history_dir, fname)
            try:
                os.remove(full)
                deleted.append(fname)
            except OSError:
                pass

    return deleted
